"""Centralized logging configuration for the Batch File Sender application.

This module replaces the ad-hoc mix of print() statements and partial logging
usage throughout the codebase with a single, consistent configuration point.

Usage::

    # At application startup (e.g. in main_qt.py):
    from core.logging_config import setup_logging
    setup_logging()

    # In any module that needs logging:
    from core.logging_config import get_logger
    logger = get_logger(__name__)
    logger.info("Processing file %s", filename)

    # For run-log integration:
    from core.logging_config import RunLogHandler
    handler = RunLogHandler(run_log_file)
    logger.addHandler(handler)
"""

from __future__ import annotations

import logging
import os
import sys
from contextvars import ContextVar
from typing import IO, Any, Union

from core.structured_logging import (
    JSONFormatter,
    StructuredLogAdapter,
)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

DEFAULT_FORMAT: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
"""Format string used by the console and file handlers."""

DEFAULT_DATEFMT: str = "%Y-%m-%d %H:%M:%S"
"""Date format string for log timestamps."""

RUN_LOG_FORMAT: str = "%(message)s"
"""Format string for the run-log handler (no timestamps/levels)."""

# Valid level names accepted by BFS_LOG_LEVEL env var.
_VALID_LEVEL_NAMES: set[str] = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def get_logger(name: str) -> logging.Logger:
    """Return a logger with the given *name*.

    This is a thin convenience wrapper around :func:`logging.getLogger` so that
    application modules can import their logger from a single place::

        from core.logging_config import get_logger
        logger = get_logger(__name__)

    Using ``import logging; logging.getLogger(__name__)`` directly is equally
    valid and will return the exact same logger instance.
    """
    return logging.getLogger(name)


def get_structured_logger(name: str, extra: dict | None = None) -> StructuredLogAdapter:
    """Return a structured logger adapter with automatic context injection."""
    logger = get_logger(name)
    return StructuredLogAdapter(logger, extra=extra)


# ---------------------------------------------------------------------------
# setup_logging
# ---------------------------------------------------------------------------


def setup_logging(
    level: int | None = None,
    log_file: str | None = None,
) -> logging.Logger:
    """Configure the root logger for the application.

    This function is **idempotent**: calling it more than once will tear down
    all existing handlers on the root logger before re-applying the
    configuration, so it is safe to call from tests or application restarts.

    Parameters
    ----------
    level:
        Explicit logging level (e.g. ``logging.DEBUG``).  When provided this
        takes the highest priority.
    log_file:
        Optional path to a log file.  When given a
        :class:`logging.FileHandler` is added alongside the console handler.

    Returns
    -------
    logging.Logger
        The root logger instance.

    Level resolution priority (highest to lowest):
        1. Explicit *level* parameter
        2. ``BFS_LOG_LEVEL`` environment variable (DEBUG/INFO/WARNING/ERROR/CRITICAL)
        3. ``DISPATCH_DEBUG_MODE`` environment variable (``"true"`` → DEBUG)
        4. Default: ``logging.INFO``

    """
    root_logger = logging.getLogger()

    # ------------------------------------------------------------------
    # Idempotency: strip every handler currently on the root logger so we
    # start from a clean slate.
    # ------------------------------------------------------------------
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        handler.close()

    # ------------------------------------------------------------------
    # Determine effective level
    # ------------------------------------------------------------------
    effective_level = logging.INFO  # default

    # Priority 3: DISPATCH_DEBUG_MODE env var
    if os.environ.get("DISPATCH_DEBUG_MODE", "").lower() == "true":
        effective_level = logging.DEBUG

    # Priority 2: BFS_LOG_LEVEL env var
    env_level = os.environ.get("BFS_LOG_LEVEL", "").upper()
    if env_level in _VALID_LEVEL_NAMES:
        effective_level = getattr(logging, env_level)

    # Priority 1: explicit parameter
    if level is not None:
        effective_level = level

    root_logger.setLevel(effective_level)

    # ------------------------------------------------------------------
    # Shared formatter
    # ------------------------------------------------------------------
    use_json = os.environ.get("BFS_LOG_FORMAT", "").lower() == "json"
    if use_json:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(DEFAULT_FORMAT, datefmt=DEFAULT_DATEFMT)

    # ------------------------------------------------------------------
    # Console handler (stderr)
    # ------------------------------------------------------------------
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # ------------------------------------------------------------------
    # Optional file handler
    # ------------------------------------------------------------------
    if log_file is not None:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    return root_logger


def setup_structured_logging(
    level: int | None = None,
    log_file: str | None = None,
) -> logging.Logger:
    """Configure the root logger with JSON structured output.

    This is a convenience wrapper around setup_logging that forces JSON
    formatting regardless of the BFS_LOG_FORMAT environment variable.

    Parameters
    ----------
    level:
        Explicit logging level (e.g. ``logging.DEBUG``).
    log_file:
        Optional path to a log file.

    Returns
    -------
    logging.Logger
        The root logger instance.

    """
    # Temporarily force JSON format
    original_format = os.environ.get("BFS_LOG_FORMAT")
    os.environ["BFS_LOG_FORMAT"] = "json"
    try:
        return setup_logging(level=level, log_file=log_file)
    finally:
        if original_format is None:
            os.environ.pop("BFS_LOG_FORMAT", None)
        else:
            os.environ["BFS_LOG_FORMAT"] = original_format


# ---------------------------------------------------------------------------
# RunLogHandler
# ---------------------------------------------------------------------------


class RunLogHandler(logging.Handler):
    """Custom handler that writes log records to run-log file objects.

    The Batch File Sender maintains per-run log files that record what
    happened during a dispatch cycle.  This handler bridges the ``logging``
    module into that system so callers can simply use ``logger.info(...)``
    instead of writing directly to the file.

    The handler supports two back-end modes:

    * **File mode** -- *run_log* has a ``write`` attribute (a binary-mode
      file object).  Each formatted message is encoded to bytes and written
      with ``\\r\\n`` line endings.
    * **List mode** -- *run_log* has an ``append`` attribute (typically a
      plain ``list``).  This is used during threaded dispatch where results
      are collected in memory first.

    By default only records at ``INFO`` and above are emitted so that
    ``DEBUG`` chatter does not clutter the run logs.

    Parameters
    ----------
    run_log:
        A binary-mode file object **or** a list that collects log lines.
        May be ``None`` if the handler is created before a run starts;
        call :meth:`set_run_log` later to attach a target.
    level:
        Minimum level for this handler.  Defaults to ``logging.INFO``.

    """

    def __init__(
        self,
        run_log: Union[IO[bytes], list[str], None] = None,
        level: int = logging.INFO,
    ) -> None:
        super().__init__(level=level)
        self.run_log: Union[IO[bytes], list[str], None] = run_log
        self.setFormatter(logging.Formatter(RUN_LOG_FORMAT))

    # -- public API --------------------------------------------------------

    def set_run_log(self, run_log: Union[IO[bytes], list[str], None]) -> None:
        """Replace the current run-log target.

        Call this at the start of each new dispatch run to point the handler
        at the freshly opened log file (or list).
        """
        self.run_log = run_log

    # -- logging.Handler overrides -----------------------------------------

    def emit(self, record: logging.LogRecord) -> None:
        """Write a formatted log record to the run log.

        If no *run_log* is currently set the record is silently discarded.
        Records below this handler's level are also silently discarded.
        """
        if self.run_log is None:
            return

        if record.levelno < self.level:
            return

        try:
            message = self.format(record)

            if hasattr(self.run_log, "write"):
                self.run_log.write((message + "\r\n").encode())
            elif hasattr(self.run_log, "append"):
                self.run_log.append(message)
        except Exception:  # noqa: BLE001
            self.handleError(record)

    def close(self) -> None:
        """Release the run-log reference and perform base-class cleanup."""
        self.run_log = None
        super().close()


# ---------------------------------------------------------------------------
# RunLogAdapter
# ---------------------------------------------------------------------------


class RunLogAdapter(logging.LoggerAdapter):
    """Logger adapter that prepends folder/file context to messages.

    When dispatching files the application processes many folders in
    sequence.  This adapter automatically prefixes log messages with the
    current folder name (and optionally the file being processed) so that
    run-log entries are easy to correlate.

    Parameters
    ----------
    logger:
        The underlying logger to adapt.
    extra:
        Context dictionary.  Recognised keys:

        * ``"folder"`` -- name of the folder currently being processed.
        * ``"file"`` -- name of the file currently being processed.

    Example::

        adapter = RunLogAdapter(logger, {"folder": "ACME_Corp"})
        adapter.info("Sent invoice")
        # -> "[ACME_Corp] Sent invoice"

        adapter.extra["file"] = "INV_001.edi"
        adapter.info("Converted OK")
        # -> "[ACME_Corp/INV_001.edi] Converted OK"

    """

    def __init__(
        self,
        logger: logging.Logger,
        extra: dict[str, str] | None = None,
    ) -> None:
        super().__init__(logger, extra or {})

    def process(
        self,
        msg: str,
        kwargs: dict,
    ) -> tuple[str, dict]:
        """Prepend folder (and optionally file) context to *msg*."""
        folder: str | None = self.extra.get("folder")  # type: ignore[union-attr]
        file: str | None = self.extra.get("file")  # type: ignore[union-attr]

        if folder and file:
            msg = f"[{folder}/{file}] {msg}"
        elif folder:
            msg = f"[{folder}] {msg}"

        return msg, kwargs


# ---------------------------------------------------------------------------
# AuditLogger
# ---------------------------------------------------------------------------


class AuditLogger:
    """Structured audit logger for security-sensitive operations.

    The AuditLogger provides a dedicated logger for security-sensitive
    operations such as:
    - User authentication and authorization
    - Folder configuration changes
    - Settings modifications
    - File access and processing
    - Backend configuration changes
    - Export/delete operations

    All audit events are logged at INFO level with structured fields
    suitable for security information and event management (SIEM) systems.

    Parameters
    ----------
    name:
        Logger name for the audit logger (default: "audit")

    Example::
        audit = AuditLogger()
        audit.log_user_action("login", username="admin", success=True)
        audit.log_config_change("update_folder", folder="ACME_Corp", changed_by="admin")
        audit.log_file_access("process", file_path="/path/to/file.edi")

    """

    def __init__(self, name: str = "audit") -> None:
        """Initialize the audit logger.

        Args:
            name: Logger name for the audit logger

        """
        self._logger = logging.getLogger(name)
        self._correlation_id_var: ContextVar[str | None] = ContextVar(
            "audit_correlation_id", default=None
        )

    def _log(
        self,
        action: str,
        level: int,
        details: dict[str, Any] | None = None,
        *,
        exc_info: bool = False,
    ) -> None:
        """Internal log method with structured fields.

        Args:
            action: The audit action being performed
            level: Log level to use
            details: Additional details about the action
            exc_info: Whether to include exception info

        """
        extra: dict[str, Any] = {
            "audit_action": action,
            "audit_logger": True,
        }

        if details:
            extra["audit_details"] = details

        corr_id = self._correlation_id_var.get()
        if corr_id:
            extra["correlation_id"] = corr_id

        self._logger.log(level, f"[AUDIT] {action}", extra=extra, exc_info=exc_info)

    def set_correlation_id(self, correlation_id: str | None) -> None:
        """Set the correlation ID for audit entries in the current context.

        Args:
            correlation_id: Correlation ID to set, or None to clear

        """
        self._correlation_id_var.set(correlation_id)

    def log_user_action(
        self,
        action: str,
        username: str | None = None,
        *,
        success: bool = True,
        reason: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Log a user action event.

        Args:
            action: The action performed (e.g., "login", "logout", "view_settings")
            username: Username performing the action
            success: Whether the action succeeded
            reason: Reason for failure if success is False
            **kwargs: Additional context fields

        """
        details: dict[str, Any] = {"username": username, "success": success}
        if reason:
            details["reason"] = reason
        details.update(kwargs)

        level = logging.INFO if success else logging.WARNING
        self._log(action, level, details)

    def log_config_change(
        self,
        action: str,
        target_type: str,
        target_name: str | None = None,
        changed_by: str | None = None,
        changes: dict[str, tuple[Any, Any]] | None = None,
        **kwargs: Any,
    ) -> None:
        """Log a configuration change event.

        Args:
            action: The change action (e.g., "create", "update", "delete")
            target_type: Type of config target (e.g., "folder", "backend", "setting")
            target_name: Name of the target being modified
            changed_by: User who made the change
            changes: Dict of field -> (old_value, new_value) tuples
            **kwargs: Additional context fields

        """
        details: dict[str, Any] = {
            "target_type": target_type,
            "target_name": target_name,
            "changed_by": changed_by,
        }
        if changes:
            details["changes"] = {
                field: {"old": _safe_value(old), "new": _safe_value(new)}
                for field, (old, new) in changes.items()
            }
        details.update(kwargs)

        self._log(f"config_{action}", logging.INFO, details)

    def log_file_access(
        self,
        action: str,
        file_path: str | None = None,
        folder_alias: str | None = None,
        performed_by: str | None = None,
        *,
        success: bool = True,
        **kwargs: Any,
    ) -> None:
        """Log a file access event.

        Args:
            action: The file action (e.g., "read", "write", "delete", "process")
            file_path: Path to the file being accessed
            folder_alias: Alias of the folder containing the file
            performed_by: User or system component performing the action
            success: Whether the action succeeded
            **kwargs: Additional context fields

        """
        details: dict[str, Any] = {
            "file_path": file_path,
            "folder_alias": folder_alias,
            "performed_by": performed_by,
            "success": success,
        }
        details.update(kwargs)

        level = logging.INFO if success else logging.WARNING
        self._log(f"file_{action}", level, details)

    def log_backend_config(
        self,
        action: str,
        backend_type: str | None = None,
        backend_name: str | None = None,
        changed_by: str | None = None,
        *,
        success: bool = True,
        **kwargs: Any,
    ) -> None:
        """Log a backend configuration event.

        Args:
            action: The action (e.g., "configure", "test", "disable")
            backend_type: Type of backend (e.g., "ftp", "smtp", "copy")
            backend_name: Name/identifier of the backend
            changed_by: User who made the change
            success: Whether the action succeeded
            **kwargs: Additional context fields

        """
        details: dict[str, Any] = {
            "backend_type": backend_type,
            "backend_name": backend_name,
            "changed_by": changed_by,
            "success": success,
        }
        details.update(kwargs)

        level = logging.INFO if success else logging.WARNING
        self._log(f"backend_{action}", level, details)

    def log_security_event(
        self,
        event: str,
        severity: str = "medium",
        description: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Log a security-related event.

        Args:
            event: Type of security event
            severity: Severity level ("low", "medium", "high", "critical")
            description: Human-readable description
            **kwargs: Additional context fields

        """
        details: dict[str, Any] = {
            "severity": severity,
            "description": description,
        }
        details.update(kwargs)

        level_map = {
            "low": logging.INFO,
            "medium": logging.WARNING,
            "high": logging.ERROR,
            "critical": logging.CRITICAL,
        }
        level = level_map.get(severity.lower(), logging.WARNING)
        self._log(f"security_{event}", level, details)


def _safe_value(value: Any) -> Any:
    """Convert a value to a safe, serializable form for logging.

    Args:
        value: The value to convert

    Returns:
        A safe representation of the value

    """
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_safe_value(v) for v in value]
    if isinstance(value, dict):
        return {k: _safe_value(v) for k, v in value.items()}
    return str(value)


# Default audit logger instance
audit_logger = AuditLogger()
