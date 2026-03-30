"""Structured logging utilities for convert and tweak instrumentation.

This module provides comprehensive structured logging capabilities including:
- Correlation ID propagation across threads/async boundaries
- Sensitive data redaction helpers
- Decorators for automatic entry/exit/error logging
- Structured JSON log output with consistent field names
- Helper functions for common logging patterns

Usage:
    from core.structured_logging import (
        get_logger,                    # Get logger with structured extras
        get_structured_logger,         # Get pre-configured structured logger
        get_correlation_id, set_correlation_id,
        redact_sensitive_data, logged,
        StructuredLogAdapter,          # Auto correlation_id injection
        log_with_context,              # Context-rich logging
        log_file_operation,            # File operation logging
        log_backend_call,              # Backend call logging
    )

    # Simple usage
    logger = get_logger(__name__)
    logger.info("Processing started", extra={"file_id": "abc123"})

    # Pre-configured structured logger
    logger = get_structured_logger(__name__, operation="convert")

    # Adapter with auto correlation_id
    logger = StructuredLogAdapter(get_logger(__name__))

    @logged
    def my_convert_function(input_path, output_path, settings):
        # Function automatically logs entry, exit, and errors
        pass
"""

from __future__ import annotations

import functools
import hashlib
import inspect
import json
import logging
import os
import re
import time
import traceback
import uuid
from collections.abc import MutableMapping
from contextvars import ContextVar
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Callable, TypeVar

# Correlation ID context variable - thread/async-safe
_correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)

# Trace ID context variable for distributed tracing
_trace_id_var: ContextVar[str | None] = ContextVar("trace_id", default=None)

# Component context for identifying which subsystem is logging
_component_var: ContextVar[str | None] = ContextVar("component", default=None)

# Operation context for identifying the current operation
_operation_var: ContextVar[str | None] = ContextVar("operation", default=None)

# =============================================================================
# Configuration
# =============================================================================

LOG_PAYLOADS_ON_DEBUG: bool = os.environ.get("BFS_LOG_PAYLOADS", "").lower() == "true"
"""Whether to log full payloads at debug level. Default False to reduce noise."""

DEFAULT_VISIBLE_CHARS: int = 4
"""Default number of visible characters when redacting strings."""

MAX_LOG_STRING_LENGTH: int = 1000
"""Maximum length for string values in logs."""

# =============================================================================
# Redaction Patterns and Helpers
# =============================================================================

REDACTION_PATTERNS: frozenset[str] = frozenset(
    {
        # Credentials
        "password",
        "passwd",
        "pwd",
        "secret",
        "secret_key",
        "token",
        "access_token",
        "refresh_token",
        "api_key",
        "apikey",
        "api_secret",
        "private_key",
        "privatekey",
        "ssh_key",
        "key_id",
        "keyid",
        # Database
        "as400_password",
        "db_password",
        "database_password",
        "connection_string",
        "conn_string",
        # Network/FTP
        "ftp_password",
        "ftp_username",
        "ftp_user",
        "ftp_pass",
        "sftp_password",
        "sftp_username",
        # SMTP
        "smtp_password",
        "email_password",
        "mail_password",
        # OAuth/Auth
        "oauth_token",
        "oauth_secret",
        "bearer_token",
        "auth_token",
        "id_token",
        "csrf_token",
        "session_id",
        "session_token",
        # Certificates
        "certificate",
        "cert",
        "cert_data",
        "private_key_data",
        "ssl_key",
        # PII - Personal
        "ssn",
        "social_security",
        "social_security_number",
        "tax_id",
        "ein",
        "tin",
        "passport",
        "passport_number",
        "driver_license",
        "dob",
        "birth_date",
        "date_of_birth",
        # PII - Contact
        "phone",
        "phone_number",
        "mobile",
        "email",
        "email_address",
        "home_address",
        "address",
        "zip_code",
        "postal_code",
        # Financial
        "credit_card",
        "cc_number",
        "card_number",
        "cvv",
        "cvc",
        "bank_account",
        "account_number",
        "routing_number",
        "iban",
        "swift",
        "bic",
        "account_routing",
        # General security
        "auth",
        "authorization",
        "credential",
        "credentials",
        "key",
        "signature",
        "signed_data",
        "encrypted_data",
        "decrypted",
        "plaintext",
    }
)
"""Set of key names that contain sensitive data and should be redacted."""

# Regex patterns for detecting sensitive values in strings
REDACTION_VALUE_PATTERNS: list[re.Pattern] = [
    # AWS keys
    re.compile(r"AKIA[0-9A-Z]{16}", re.IGNORECASE),
    # Generic API keys (common formats)
    re.compile(r"[a-zA-Z0-9_-]{32,}", re.IGNORECASE),
    # JWT tokens
    re.compile(r"eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*"),
    # Bearer tokens in strings
    re.compile(r"Bearer\s+[a-zA-Z0-9_-]+", re.IGNORECASE),
]


def redact_string(s: str, visible_chars: int = DEFAULT_VISIBLE_CHARS) -> str:
    """Redact a string showing only the last N characters.

    Args:
        s: String to redact
        visible_chars: Number of characters to show at the end (default 4)

    Returns:
        Redacted string like "****abc123" or "****" if empty/None

    """
    if not s:
        return "****"
    if len(s) <= visible_chars:
        return "*" * len(s)
    return "*" * (len(s) - visible_chars) + s[-visible_chars:]


def redact_value(value: Any, visible_chars: int = DEFAULT_VISIBLE_CHARS) -> Any:
    """Redact a value based on its type.

    Note: For backward compatibility, ALL strings are redacted by default.
    This is intentional to ensure consistent log output.

    Args:
        value: Value to redact
        visible_chars: Number of chars to show for strings

    Returns:
        Redacted value appropriate to the input type

    """
    if value is None:
        return None
    if isinstance(value, str):
        # Redact all strings for backward compatibility
        return redact_string(value, visible_chars)
    if isinstance(value, dict):
        return redact_sensitive_data(value, visible_chars)
    if isinstance(value, (list, tuple)):
        return [redact_value(v, visible_chars) for v in value]
    if isinstance(value, Path):
        return str(value)
    return value


def redact_sensitive_data(
    data: dict[str, Any],
    visible_chars: int = DEFAULT_VISIBLE_CHARS,
) -> dict[str, Any]:
    """Redact sensitive fields from a dictionary.

    Args:
        data: Dictionary potentially containing sensitive data
        visible_chars: Number of characters to show for redacted strings

    Returns:
        New dictionary with sensitive values redacted

    Example:
        >>> data = {"username": "john", "password": "secret123"}
        >>> redact_sensitive_data(data)
        {'username': 'john', 'password': '****3123'}

    """
    if not isinstance(data, dict):
        return data

    result: dict[str, Any] = {}
    for key, value in data.items():
        key_lower = key.lower()
        # Check if key matches any redaction pattern
        if any(pattern in key_lower for pattern in REDACTION_PATTERNS):
            result[key] = redact_value(value, visible_chars)
        else:
            result[key] = redact_value(value, visible_chars)
    return result


def hash_sensitive_value(value: str) -> str:
    """Create a SHA256 hash of a sensitive value for safe logging.

    Args:
        value: The sensitive value to hash

    Returns:
        Truncated hash string (first 16 chars)

    """
    if not value:
        return "****"
    return hashlib.sha256(value.encode()).hexdigest()[:16]


# =============================================================================
# Correlation ID Management
# =============================================================================


def get_correlation_id() -> str | None:
    """Get the current correlation ID from context.

    Returns:
        Current correlation ID or None if not set

    """
    return _correlation_id_var.get()


def set_correlation_id(correlation_id: str | None) -> None:
    """Set the correlation ID in the current context.

    Args:
        correlation_id: Correlation ID to set, or None to clear

    """
    _correlation_id_var.set(correlation_id)


def clear_correlation_id() -> None:
    """Clear the correlation ID from the current context."""
    _correlation_id_var.set(None)


def generate_correlation_id() -> str:
    """Generate a new unique correlation ID.

    Returns:
        A new UUID-based correlation ID

    """
    return uuid.uuid4().hex[:16]


def get_or_create_correlation_id() -> str:
    """Get existing correlation ID or create a new one.

    Returns:
        Existing correlation ID if set, otherwise a new one

    """
    corr_id = _correlation_id_var.get()
    if corr_id:
        return corr_id
    new_id = generate_correlation_id()
    _correlation_id_var.set(new_id)
    return new_id


def get_trace_id() -> str | None:
    """Get the current trace ID from context.

    Returns:
        Current trace ID or None if not set

    """
    return _trace_id_var.get()


def set_trace_id(trace_id: str | None) -> None:
    """Set the trace ID in the current context.

    Args:
        trace_id: Trace ID to set, or None to clear

    """
    _trace_id_var.set(trace_id)


def get_component() -> str | None:
    """Get the current component from context.

    Returns:
        Current component name or None if not set

    """
    return _component_var.get()


def set_component(component: str | None) -> None:
    """Set the component in the current context.

    Args:
        component: Component name to set, or None to clear

    """
    _component_var.set(component)


def get_operation() -> str | None:
    """Get the current operation from context.

    Returns:
        Current operation name or None if not set

    """
    return _operation_var.get()


def set_operation(operation: str | None) -> None:
    """Set the operation in the current context.

    Args:
        operation: Operation name to set, or None to clear

    """
    _operation_var.set(operation)


# =============================================================================
# Logger Factory Functions
# =============================================================================


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name.

    This is the primary factory function for obtaining loggers.
    It ensures consistent logger configuration across the application.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance

    """
    return logging.getLogger(name)


def get_structured_logger(
    name: str,
    *,
    component: str | None = None,
    operation: str | None = None,
    correlation_id: str | None = None,
) -> logging.Logger:
    """Get a logger pre-configured with structured logging context.

    This logger will automatically include the specified context fields
    in all log records via the extra parameter.

    Args:
        name: Logger name (typically __name__)
        component: Component/subsystem name (e.g., "convert", "dispatch")
        operation: Operation being performed (e.g., "edi_conversion")
        correlation_id: Correlation ID to use, or None to use current

    Returns:
        Logger pre-configured with structured context

    Example:
        >>> logger = get_structured_logger(
        ...     __name__, component="convert", operation="edi"
        ... )
        >>> logger.info("Starting")  # Auto-includes component and operation

    """
    logger = get_logger(name)

    # Store context for this logger
    if component:
        set_component(component)
    if operation:
        set_operation(operation)
    if correlation_id:
        set_correlation_id(correlation_id)
    elif not get_correlation_id():
        set_correlation_id(generate_correlation_id())

    return logger


# =============================================================================
# StructuredLogAdapter - Auto correlation_id injection
# =============================================================================


class StructuredLogAdapter(logging.LoggerAdapter):
    """Logger adapter that automatically adds correlation_id to all log records.

    This adapter wraps a logger and automatically injects correlation_id
    and other context fields into every log record's extra dict.

    Example:
        >>> base_logger = get_logger(__name__)
        >>> logger = StructuredLogAdapter(base_logger)
        >>> set_correlation_id("abc123")
        >>> logger.info("Processing started")  # correlation_id auto-included

    """

    def __init__(
        self,
        logger: logging.Logger,
        *,
        extra: dict[str, Any] | None = None,
        auto_correlation: bool = True,
        auto_component: bool = True,
        auto_operation: bool = True,
    ) -> None:
        """Initialize the adapter.

        Args:
            logger: The underlying logger to wrap
            extra: Default extra fields to include in all logs
            auto_correlation: Whether to auto-inject correlation_id
            auto_component: Whether to auto-inject component
            auto_operation: Whether to auto-inject operation

        """
        super().__init__(logger, extra or {})
        self.auto_correlation = auto_correlation
        self.auto_component = auto_component
        self.auto_operation = auto_operation

    def process(
        self, msg: str, kwargs: MutableMapping[str, Any]
    ) -> tuple[str, MutableMapping[str, Any]]:  # type: ignore[override]
        """Process the logging message and keyword arguments.

        Injects context variables into the extra dict.
        """
        # Ensure extra dict exists
        extra: dict[str, Any] = dict(kwargs.get("extra") or {})
        kwargs["extra"] = extra

        # Auto-inject correlation_id
        if self.auto_correlation and "correlation_id" not in extra:
            corr_id = get_correlation_id()
            if corr_id:
                extra["correlation_id"] = corr_id

        # Auto-inject trace_id
        if "trace_id" not in extra:
            trace_id = get_trace_id()
            if trace_id:
                extra["trace_id"] = trace_id

        # Auto-inject component
        if self.auto_component and "component" not in extra:
            component = get_component()
            if component:
                extra["component"] = component

        # Auto-inject operation
        if self.auto_operation and "operation" not in extra:
            operation = get_operation()
            if operation:
                extra["operation"] = operation

        # Merge with default extra
        if self.extra:
            for key, value in self.extra.items():
                if key not in extra:
                    extra[key] = value

        return msg, kwargs


# =============================================================================
# Helper Functions for Common Logging Patterns
# =============================================================================


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    *,
    correlation_id: str | None = None,
    component: str | None = None,
    operation: str | None = None,
    context: dict[str, Any] | None = None,
    exc_info: bool = False,
    **kwargs: Any,
) -> None:
    """Log a message with rich context.

    Args:
        logger: Logger to use
        level: Log level (e.g., logging.INFO)
        message: Log message
        correlation_id: Correlation ID, or None to use current
        component: Component name, or None to use current
        operation: Operation name, or None to use current
        context: Additional context dict to include
        exc_info: Whether to include exception info
        **kwargs: Additional fields to include

    Example:
        >>> log_with_context(
        ...     logger,
        ...     logging.INFO,
        ...     "Processing complete",
        ...     operation="convert",
        ...     context={"records_processed": 100}
        ... )

    """
    extra: dict[str, Any] = {
        "correlation_id": correlation_id or get_correlation_id(),
        "trace_id": get_trace_id(),
        "component": component or get_component(),
        "operation": operation or get_operation(),
    }

    # Remove None values
    extra = {k: v for k, v in extra.items() if v is not None}

    # Add context
    if context:
        sanitized_context = redact_sensitive_data(context)
        extra["context"] = sanitized_context

    # Add additional kwargs
    extra.update(kwargs)

    logger.log(level, message, extra=extra, exc_info=exc_info)


def log_file_operation(
    logger: logging.Logger,
    operation: str,
    file_path: str | Path,
    *,
    file_size: int | None = None,
    file_type: str | None = None,
    success: bool | None = None,
    error: Exception | None = None,
    duration_ms: float | None = None,
    correlation_id: str | None = None,
    **kwargs: Any,
) -> None:
    """Log a file operation with standardized fields.

    Args:
        logger: Logger to use
        operation: Operation type ("read", "write", "copy", "delete", "validate")
        file_path: Path to the file
        file_size: File size in bytes (optional)
        file_type: File type/extension (optional)
        success: Whether operation succeeded (optional)
        error: Exception if operation failed (optional)
        duration_ms: Operation duration in milliseconds (optional)
        correlation_id: Correlation ID (optional)
        **kwargs: Additional fields

    Example:
        >>> log_file_operation(logger, "read", "/path/to/file.csv", file_size=1024)

    """
    path = Path(file_path)

    extra: dict[str, Any] = {
        "correlation_id": correlation_id or get_correlation_id(),
        "trace_id": get_trace_id(),
        "file_operation": operation,
        "file_path": str(path),
        "file_name": path.name,
    }

    if file_size is not None:
        extra["file_size"] = file_size
    if file_type:
        extra["file_type"] = file_type
    else:
        extra["file_type"] = path.suffix.lstrip(".") if path.suffix else None
    if success is not None:
        extra["success"] = success
    if duration_ms is not None:
        extra["duration_ms"] = round(duration_ms, 2)

    extra.update(kwargs)

    if error:
        extra["error"] = {"type": type(error).__name__, "message": str(error)}
        logger.error(
            "[FILE ERROR] %s failed for %s: %s",
            operation,
            path.name,
            str(error),
            extra=extra,
            exc_info=True,
        )
    elif success:
        logger.info(
            "[FILE] %s completed for %s (%s bytes)",
            operation,
            path.name,
            file_size or "?",
            extra=extra,
        )
    else:
        logger.debug(
            "[FILE] %s started for %s",
            operation,
            path.name,
            extra=extra,
        )


def log_backend_call(
    logger: logging.Logger,
    backend_type: str,
    operation: str,
    *,
    endpoint: str | None = None,
    request_size: int | None = None,
    response_size: int | None = None,
    status_code: int | str | None = None,
    success: bool | None = None,
    error: Exception | None = None,
    duration_ms: float | None = None,
    retry_count: int | None = None,
    correlation_id: str | None = None,
    **kwargs: Any,
) -> None:
    """Log a backend service call with standardized fields.

    Args:
        logger: Logger to use
        backend_type: Backend type ("ftp", "smtp", "sftp", "api", "database")
        operation: Operation being performed ("upload", "send", "query", etc.)
        endpoint: Target endpoint/URL/path (optional)
        request_size: Request payload size in bytes (optional)
        response_size: Response size in bytes (optional)
        status_code: Response status code (optional)
        success: Whether call succeeded (optional)
        error: Exception if call failed (optional)
        duration_ms: Call duration in milliseconds (optional)
        retry_count: Number of retries (optional)
        correlation_id: Correlation ID (optional)
        **kwargs: Additional fields

    Example:
        >>> log_backend_call(
        ...     logger,
        ...     "ftp",
        ...     "upload",
        ...     endpoint="ftp.example.com/inbox",
        ...     success=True,
        ...     duration_ms=500
        ... )

    """
    extra: dict[str, Any] = {
        "correlation_id": correlation_id or get_correlation_id(),
        "trace_id": get_trace_id(),
        "backend_type": backend_type,
        "backend_operation": operation,
    }

    if endpoint:
        extra["endpoint"] = endpoint
    if request_size is not None:
        extra["request_size"] = request_size
    if response_size is not None:
        extra["response_size"] = response_size
    if status_code is not None:
        extra["status_code"] = status_code
    if success is not None:
        extra["success"] = success
    if duration_ms is not None:
        extra["duration_ms"] = round(duration_ms, 2)
    if retry_count is not None:
        extra["retry_count"] = retry_count

    extra.update(kwargs)

    # Determine log level based on outcome
    if error:
        extra["error"] = {"type": type(error).__name__, "message": str(error)}
        logger.error(
            "[BACKEND ERROR] %s %s failed: %s",
            backend_type,
            operation,
            str(error),
            extra=extra,
            exc_info=True,
        )
    elif success is False:
        logger.warning(
            "[BACKEND] %s %s failed with status %s",
            backend_type,
            operation,
            status_code or "unknown",
            extra=extra,
        )
    elif success:
        logger.info(
            "[BACKEND] %s %s completed in %.2fms",
            backend_type,
            operation,
            duration_ms or 0,
            extra=extra,
        )
    else:
        logger.debug(
            "[BACKEND] %s %s started",
            backend_type,
            operation,
            extra=extra,
        )


def log_database_call(
    logger: logging.Logger,
    operation: str,
    *,
    query_type: str | None = None,
    table: str | None = None,
    row_count: int | None = None,
    duration_ms: float | None = None,
    success: bool | None = None,
    error: Exception | None = None,
    connection_id: str | None = None,
    correlation_id: str | None = None,
    **kwargs: Any,
) -> None:
    """Log a database operation with standardized fields.

    Args:
        logger: Logger to use
        operation: Operation being performed ("query", "execute", "connect", "close")
        query_type: Type of SQL ("SELECT", "INSERT", "UPDATE", "DELETE", etc.)
        table: Table being accessed (optional)
        row_count: Number of rows affected/returned (optional)
        duration_ms: Operation duration in milliseconds (optional)
        success: Whether operation succeeded (optional)
        error: Exception if operation failed (optional)
        connection_id: Connection identifier (optional)
        correlation_id: Correlation ID (optional)
        **kwargs: Additional fields

    Example:
        >>> log_database_call(
        ...     logger,
        ...     "query",
        ...     query_type="SELECT",
        ...     table="folders",
        ...     row_count=5,
        ...     duration_ms=45.2,
        ...     success=True
        ... )

    """
    extra: dict[str, Any] = {
        "correlation_id": correlation_id or get_correlation_id(),
        "trace_id": get_trace_id(),
        "db_operation": operation,
    }

    if query_type:
        extra["query_type"] = query_type
    if table:
        extra["table"] = table
    if row_count is not None:
        extra["row_count"] = row_count
    if duration_ms is not None:
        extra["duration_ms"] = round(duration_ms, 2)
    if success is not None:
        extra["success"] = success
    if connection_id:
        extra["connection_id"] = connection_id

    extra.update(kwargs)

    # Determine log level based on outcome
    if error:
        extra["error"] = {"type": type(error).__name__, "message": str(error)}
        logger.error(
            "[DB ERROR] %s %s%s failed: %s",
            operation,
            f"{query_type} " if query_type else "",
            f"on {table}" if table else "",
            str(error),
            extra=extra,
            exc_info=True,
        )
    elif success is False:
        logger.warning(
            "[DB] %s %s%s failed",
            operation,
            f"{query_type} " if query_type else "",
            f"on {table}" if table else "",
            extra=extra,
        )
    elif success:
        logger.info(
            "[DB] %s %s%s completed in %.2fms (%s rows)",
            operation,
            f"{query_type} " if query_type else "",
            f"on {table}" if table else "",
            duration_ms or 0,
            row_count if row_count is not None else "?",
            extra=extra,
        )
    else:
        logger.debug(
            "[DB] %s %s%s started",
            operation,
            f"{query_type} " if query_type else "",
            f"on {table}" if table else "",
            extra=extra,
        )


# =============================================================================
# Structured Logger
# =============================================================================


class StructuredLogger:
    """Helper class for creating structured log entries.

    Provides methods for creating consistent structured log entries
    with correlation IDs, timing, and sanitized data.
    """

    @staticmethod
    def _get_logger_name(module: str) -> str:
        """Get the logger name for a module.

        Args:
            module: Module name (typically __name__)

        Returns:
            Logger name

        """
        return module

    @staticmethod
    def _build_base_fields(
        module: str,
        function: str,
    ) -> dict[str, Any]:
        """Build base fields for all log entries.

        Args:
            module: Module name
            function: Function name

        Returns:
            Dictionary with base structured fields

        """
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "logger": module,
            "mod": module,
            "function": function,
            "correlation_id": get_correlation_id(),
            "trace_id": get_trace_id(),
            "component": get_component(),
            "operation": get_operation(),
        }

    @staticmethod
    def log_entry(
        logger: logging.Logger,
        func_name: str,
        module: str,
        args: tuple[Any, ...] | None = None,
        kwargs: dict[str, Any] | None = None,
    ) -> None:
        """Log function entry with sanitized arguments.

        Args:
            logger: Logger instance to use
            func_name: Name of the function being entered
            module: Module name (typically __name__)
            args: Positional arguments (will be sanitized)
            kwargs: Keyword arguments (will be sanitized)

        """
        if not logger.isEnabledFor(logging.DEBUG):
            return

        fields = StructuredLogger._build_base_fields(module, func_name)
        fields["level"] = "DEBUG"
        fields["event"] = "entry"

        # Sanitize and summarize inputs
        sanitized_args = []
        if args:
            for arg in args:
                if isinstance(arg, str) and len(arg) > 100:
                    sanitized_args.append(f"<{len(arg)} chars>")
                else:
                    sanitized_args.append(redact_value(arg))

        sanitized_kwargs = {}
        if kwargs:
            sanitized_kwargs = redact_sensitive_data(kwargs)

        fields["input_summary"] = {
            "args": sanitized_args,
            "kwargs": sanitized_kwargs,
        }
        fields["duration_ms"] = 0

        # Log as JSON for structured parsing
        logger.debug(
            "[ENTRY] %s(%s)",
            func_name,
            ", ".join(str(a) for a in sanitized_args[:3]),
            extra=fields,
        )

    @staticmethod
    def log_exit(
        logger: logging.Logger,
        func_name: str,
        module: str,
        result: Any | None = None,
        duration_ms: float = 0,
    ) -> None:
        """Log function exit with result and timing.

        Args:
            logger: Logger instance to use
            func_name: Name of the function being exited
            module: Module name (typically __name__)
            result: Function return value (will be sanitized)
            duration_ms: Execution duration in milliseconds

        """
        if not logger.isEnabledFor(logging.DEBUG):
            return

        fields = StructuredLogger._build_base_fields(module, func_name)
        fields["level"] = "DEBUG"
        fields["event"] = "exit"
        fields["duration_ms"] = round(duration_ms, 2)

        # Sanitize result
        if result is not None:
            if isinstance(result, str) and len(result) > 100:
                result_summary = f"<{len(result)} chars>"
            elif isinstance(result, dict):
                result_summary = redact_sensitive_data(result)
            else:
                result_summary = redact_value(result)
            fields["output_summary"] = result_summary
        else:
            fields["output_summary"] = None

        logger.debug(
            "[EXIT] %s completed in %.2fms",
            func_name,
            duration_ms,
            extra=fields,
        )

    @staticmethod
    def log_error(
        logger: logging.Logger,
        func_name: str,
        module: str,
        error: Exception,
        context: dict[str, Any] | None = None,
        duration_ms: float = 0,
    ) -> None:
        """Log error with full context.

        Args:
            logger: Logger instance to use
            func_name: Name of the function where error occurred
            module: Module name (typically __name__)
            error: The exception that was raised
            context: Additional context about the error
            duration_ms: Execution duration in milliseconds before error

        """
        fields = StructuredLogger._build_base_fields(module, func_name)
        fields["level"] = "ERROR"
        fields["event"] = "error"
        fields["duration_ms"] = round(duration_ms, 2)
        fields["error"] = {
            "type": type(error).__name__,
            "message": str(error),
        }

        if context:
            fields["context"] = redact_sensitive_data(context)
        else:
            fields["context"] = {}

        logger.error(
            "[ERROR] %s failed: %s",
            func_name,
            str(error),
            exc_info=True,
            extra=fields,
        )

    @staticmethod
    def log_debug(
        logger: logging.Logger,
        func_name: str,
        module: str,
        message: str,
        **kwargs: Any,
    ) -> None:
        """Log debug message with structured fields.

        Args:
            logger: Logger instance to use
            func_name: Name of the function
            module: Module name (typically __name__)
            message: Debug message
            **kwargs: Additional structured fields to log

        """
        if not logger.isEnabledFor(logging.DEBUG):
            return

        fields = StructuredLogger._build_base_fields(module, func_name)
        fields["level"] = "DEBUG"
        fields["event"] = "debug"

        # Sanitize any kwargs that might contain sensitive data
        for key, value in kwargs.items():
            if "password" in key.lower() or "token" in key.lower():
                kwargs[key] = redact_value(value)
            elif isinstance(value, dict):
                kwargs[key] = redact_sensitive_data(value)

        fields.update(kwargs)

        logger.debug(message, extra=fields)

    @staticmethod
    def log_intermediate(
        logger: logging.Logger,
        func_name: str,
        module: str,
        step: str,
        data_shape: dict[str, Any] | None = None,
        decision: str | None = None,
    ) -> None:
        """Log intermediate transformation step within a conversion/tweak pipeline.

        Args:
            logger: Logger instance to use
            func_name: Name of the function
            module: Module name
            step: Name of the step (e.g., "parse_records", "apply_transform")
            data_shape: Dict describing data shape
                (e.g., {"records": 50, "type": "list"})
            decision: Any branch decision made (e.g., "using_retail_uom", "skipped")

        """
        if not logger.isEnabledFor(logging.DEBUG):
            return

        fields = StructuredLogger._build_base_fields(module, func_name)
        fields["level"] = "DEBUG"
        fields["event"] = "intermediate"
        fields["step"] = step

        if data_shape:
            fields["data_shape"] = data_shape

        if decision:
            fields["decision"] = decision

        msg = f"[STEP] {func_name}:{step}"
        if decision:
            msg += f" ({decision})"
        if data_shape:
            msg += f" - {data_shape}"

        logger.debug(msg, extra=fields)


# =============================================================================
# Decorator for Automatic Instrumentation
# =============================================================================

T = TypeVar("T")


def logged(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to automatically log function entry, exit, and errors.

    This decorator wraps a function to provide automatic structured logging:
    - Logs entry with sanitized arguments at DEBUG level
    - Logs exit with result and duration at DEBUG level
    - Logs errors with full context at ERROR level
    - Propagates correlation IDs through the call

    Args:
        func: Function to instrument

    Returns:
        Wrapped function with automatic logging

    Example:
        @logged
        def convert_edi(input_path, output_path, settings):
            # Entry and exit are automatically logged
            pass

    """
    func_name = func.__name__
    module = func.__module__

    @functools.wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> T:
        # Get logger using our wrapper to ensure consistency
        logger = get_logger(module)

        # Log entry
        StructuredLogger.log_entry(logger, func_name, module, args, kwargs)

        # Track timing
        start_time = time.perf_counter()

        try:
            result = func(*args, **kwargs)

            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log exit
            StructuredLogger.log_exit(logger, func_name, module, result, duration_ms)

            return result

        except Exception as e:
            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log error
            StructuredLogger.log_error(
                logger,
                func_name,
                module,
                e,
                {"args": args, "kwargs": kwargs},
                duration_ms,
            )

            # Re-raise the exception
            raise

    @functools.wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> T:
        # Get logger using our wrapper to ensure consistency
        logger = get_logger(module)

        # Log entry
        StructuredLogger.log_entry(logger, func_name, module, args, kwargs)

        # Track timing
        start_time = time.perf_counter()

        try:
            result = await func(*args, **kwargs)  # type: ignore[misc]

            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log exit
            StructuredLogger.log_exit(logger, func_name, module, result, duration_ms)

            return result

        except Exception as e:
            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log error
            StructuredLogger.log_error(
                logger,
                func_name,
                module,
                e,
                {"args": args, "kwargs": kwargs},
                duration_ms,
            )

            # Re-raise the exception
            raise

    # Return appropriate wrapper based on function type
    if inspect.iscoroutinefunction(func):
        return async_wrapper  # type: ignore[return-value]
    return sync_wrapper  # type: ignore[return-value]


# =============================================================================
# Context Manager for Correlation ID Scoping
# =============================================================================


class CorrelationContext:
    """Context manager for temporarily setting a correlation ID.

    Example:
        with CorrelationContext("my-correlation-id"):
            # All logs within this block will have the correlation ID
            process_files()

    """

    def __init__(self, correlation_id: str | None = None) -> None:
        """Initialize context manager.

        Args:
            correlation_id: Correlation ID to set, or None to generate new

        """
        self.correlation_id = correlation_id or generate_correlation_id()
        self.previous_id: str | None = None

    def __enter__(self) -> str:
        """Enter context and set correlation ID."""
        self.previous_id = get_correlation_id()
        set_correlation_id(self.correlation_id)
        return self.correlation_id

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context and restore previous correlation ID."""
        set_correlation_id(self.previous_id)


# =============================================================================
# JSON Formatter for Structured Logs
# =============================================================================


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs log records as JSON.

    This formatter creates consistent JSON-structured log entries
    suitable for log aggregation systems like ELK, Splunk, etc.

    Handles additional field types:
    - datetime/date objects (ISO format)
    - Decimal (float conversion)
    - bytes (base64-like truncated)
    - Enum (name/value)
    - Path objects (string representation)
    - Exceptions (type, message, stack trace)
    - Dataclasses (as dict)

    Example log output:
        {"timestamp": "2024-01-15T10:30:00Z", "level": "INFO", "logger": "module",
         "function": "convert", "correlation_id": "abc123", ...}
    """

    def __init__(
        self,
        *,
        fmt: str | None = None,
        datefmt: str | None = None,
        style: str = "%",
        validate: bool = True,
        indent: int | None = None,
        sort_keys: bool = False,
        ensure_ascii: bool = False,
    ) -> None:
        """Initialize the formatter.

        Args:
            fmt: Format string (unused, for compatibility)
            datefmt: Date format (unused, for compatibility)
            style: Format style (unused, for compatibility)
            validate: Whether to validate format (unused, for compatibility)
            indent: JSON indentation (None for compact, int for pretty-print)
            sort_keys: Whether to sort JSON keys
            ensure_ascii: Whether to escape non-ASCII characters

        """
        super().__init__(fmt, datefmt, style)  # type: ignore[arg-type]
        self.indent = indent
        self.sort_keys = sort_keys
        self.ensure_ascii = ensure_ascii

    def _serialize_value(self, value: Any) -> Any:
        """Serialize a value to a JSON-compatible type.

        Args:
            value: The value to serialize

        Returns:
            JSON-compatible representation of the value

        """
        if value is None:
            return None

        # Primitive types
        if isinstance(value, (str, int, float, bool)):
            return value

        # datetime/date
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()

        # Decimal
        if isinstance(value, Decimal):
            return float(value)

        # bytes
        if isinstance(value, bytes):
            if len(value) > 100:
                return f"<bytes:{len(value)}>"
            try:
                return value.decode("utf-8", errors="replace")
            except Exception:
                return f"<bytes:{len(value)}>"

        # Enum
        if isinstance(value, Enum):
            return {"name": value.name, "value": value.value}

        # Path
        if isinstance(value, Path):
            return str(value)

        # Exception
        if isinstance(value, BaseException):
            return {
                "type": type(value).__name__,
                "message": str(value),
                "traceback": (
                    traceback.format_exception(type(value), value, value.__traceback__)
                    if value.__traceback__ and LOG_PAYLOADS_ON_DEBUG
                    else None
                ),
            }

        # Dataclass
        if is_dataclass(value) and not isinstance(value, type):
            return self._serialize_value(asdict(value))

        # dict
        if isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}

        # list/tuple/set
        if isinstance(value, (list, tuple, set)):
            return [self._serialize_value(v) for v in value]

        # Fallback: string representation
        try:
            return str(value)
        except Exception:
            return "<unserializable>"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON string representation

        """
        # Build base fields from record
        log_data: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Standard fields - use getattr to safely access extra attributes
        if getattr(record, "correlation_id", None):
            log_data["correlation_id"] = getattr(record, "correlation_id")
        if getattr(record, "trace_id", None):
            log_data["trace_id"] = getattr(record, "trace_id")
        if getattr(record, "component", None):
            log_data["component"] = getattr(record, "component")
        if getattr(record, "operation", None):
            log_data["operation"] = getattr(record, "operation")
        if getattr(record, "module", None):
            log_data["module"] = getattr(record, "module")
        if getattr(record, "function", None):
            log_data["function"] = getattr(record, "function")
        if getattr(record, "duration_ms", None) is not None:
            log_data["duration_ms"] = getattr(record, "duration_ms")

        # Error info
        if getattr(record, "error", None):
            log_data["error"] = self._serialize_value(getattr(record, "error"))

        # Input/output summaries
        if getattr(record, "input_summary", None):
            log_data["input_summary"] = self._serialize_value(
                getattr(record, "input_summary")
            )
        if getattr(record, "output_summary", None):
            log_data["output_summary"] = self._serialize_value(
                getattr(record, "output_summary")
            )

        # Event type
        if getattr(record, "event", None):
            log_data["event"] = getattr(record, "event")

        # Context
        if getattr(record, "context", None):
            log_data["context"] = self._serialize_value(getattr(record, "context"))

        # File operation fields
        if getattr(record, "file_operation", None):
            log_data["file_operation"] = getattr(record, "file_operation")
            if getattr(record, "file_path", None):
                log_data["file_path"] = getattr(record, "file_path")
            if getattr(record, "file_name", None):
                log_data["file_name"] = getattr(record, "file_name")
            if getattr(record, "file_size", None):
                log_data["file_size"] = getattr(record, "file_size")
            if getattr(record, "file_type", None):
                log_data["file_type"] = getattr(record, "file_type")

        # Backend call fields
        if getattr(record, "backend_type", None):
            log_data["backend_type"] = getattr(record, "backend_type")
            if getattr(record, "backend_operation", None):
                log_data["backend_operation"] = getattr(record, "backend_operation")
            if getattr(record, "endpoint", None):
                log_data["endpoint"] = getattr(record, "endpoint")
            if getattr(record, "status_code", None):
                log_data["status_code"] = getattr(record, "status_code")
            if getattr(record, "request_size", None):
                log_data["request_size"] = getattr(record, "request_size")
            if getattr(record, "response_size", None):
                log_data["response_size"] = getattr(record, "response_size")
            if getattr(record, "retry_count", None) is not None:
                log_data["retry_count"] = getattr(record, "retry_count")

        # Success indicator
        if getattr(record, "success", None) is not None:
            log_data["success"] = getattr(record, "success")

        # Step and decision
        if getattr(record, "step", None):
            log_data["step"] = getattr(record, "step")
        if getattr(record, "decision", None):
            log_data["decision"] = getattr(record, "decision")
        if getattr(record, "data_shape", None):
            log_data["data_shape"] = getattr(record, "data_shape")

        # Exception info from record
        if record.exc_info:
            exc_type, exc_value, exc_tb = record.exc_info
            log_data["exception"] = {
                "type": exc_type.__name__ if exc_type else None,
                "message": str(exc_value) if exc_value else None,
            }
            if LOG_PAYLOADS_ON_DEBUG and exc_tb:
                log_data["exception"]["traceback"] = "".join(
                    traceback.format_exception(exc_type, exc_value, exc_tb)
                )

        # Source location
        log_data["source"] = {
            "pathname": record.pathname,
            "lineno": record.lineno,
            "funcName": record.funcName,
        }

        # Serialize to JSON
        return json.dumps(
            log_data,
            indent=self.indent,
            sort_keys=self.sort_keys,
            ensure_ascii=self.ensure_ascii,
            default=self._serialize_value,
        )
