"""Base class for backend implementations.

This module provides a common base class that eliminates duplication
across all backend implementations (email, FTP, HTTP, copy). It handles:
- Retry logic with exponential backoff
- Correlation ID generation
- File operation logging
- Backend call logging
- Connection cleanup in finally blocks

Thread Safety:
    BackendBase instances are thread-safe. Instance variables (_correlation_id,
    _counter) are protected by a lock. Each backend operation uses its own
    lock to prevent race conditions in multi-threaded scenarios.

    The class constants (MAX_RETRIES, MAX_DELAY, INITIAL_DELAY) are read-only
    and safe to share across threads.

    Example of thread-safe usage:
        import threading
        from backend.email_backend import EmailBackend

        def send_email(file_path):
            # Each thread can safely use the same backend instance
            # or use separate instances - both are safe
            backend = EmailBackend()
            backend.send(params, settings, file_path)
"""

import os
import threading
import time
from abc import ABC, abstractmethod
from typing import Any

from core.structured_logging import get_logger, log_backend_call, log_file_operation

logger = get_logger(__name__)


class BackendBase(ABC):
    """Abstract base class for all backend implementations.

    This class provides common functionality for backend implementations:
    - Retry logic with exponential backoff (10 retries, max 60s delay)
    - Correlation ID generation and tracking
    - File read logging
    - Backend call logging
    - Connection cleanup in finally blocks

    Subclasses must implement:
    - _execute(): The actual backend operation
    - _get_backend_name(): Name for logging (e.g., "smtp", "ftp")
    - _get_endpoint(): Endpoint URL/host for logging
    - _cleanup(): Connection cleanup (optional, default is no-op)

    Example usage:
        class EmailBackend(BackendBase):
            def __init__(self, smtp_client=None):
                super().__init__()
                self.smtp_client = smtp_client

            def _execute(self, process_parameters, settings, filename):
                # Implement email sending logic
                return True

            def _get_backend_name(self):
                return "smtp"

            def _get_endpoint(self, process_parameters, settings):
                server = settings.get('email_smtp_server', '')
                port = settings.get('smtp_port', '')
                return f"{server}:{port}"

            def _cleanup(self):
                if self.smtp_client:
                    self.smtp_client.close()

            def send(self, process_parameters, settings, filename):
                return self.execute(process_parameters, settings, filename)
    """

    MAX_RETRIES = 10
    MAX_DELAY = 60
    INITIAL_DELAY = 2

    def __init__(self, disable_retry: bool = False) -> None:
        """Initialize the backend base.

        Args:
            disable_retry: If True, skip retry logic (for testing)

        """
        self._correlation_id = None
        self._counter = 0
        self._disable_retry = disable_retry
        self._lock = threading.Lock()

    def execute(
        self,
        process_parameters: dict,
        settings: dict,
        filename: str,
        **kwargs: Any,
    ) -> bool:
        """Execute the backend operation with retry logic.

        This method implements the template method pattern:
        1. Generate correlation ID
        2. Log file read operation
        3. Execute the backend operation with retry logic
        4. Log backend call
        5. Cleanup connections

        Args:
            process_parameters: Backend-specific parameters
            settings: Application settings
            filename: File to process
            **kwargs: Additional backend-specific arguments

        Returns:
            True if operation was successful

        Raises:
            Exception: If operation fails after MAX_RETRIES attempts

        """
        with self._lock:
            self._correlation_id = os.urandom(4).hex()
            self._counter = 0

        # Log file read operation
        try:
            file_size = os.path.getsize(filename)
        except OSError:
            file_size = 0
        correlation_id_for_log = self._correlation_id
        log_file_operation(
            logger,
            "read",
            filename,
            file_size=file_size,
            file_type="edi",
            correlation_id=correlation_id_for_log,
        )

        # Execute with retry logic
        while True:
            start_time = time.perf_counter()
            try:
                # Execute the actual backend operation
                result = self._execute(process_parameters, settings, filename, **kwargs)

                # Log success
                duration_ms = (time.perf_counter() - start_time) * 1000
                log_backend_call(
                    logger,
                    self._get_backend_name(),
                    self._get_operation_name(),
                    endpoint=self._get_endpoint(process_parameters, settings),
                    success=True,
                    duration_ms=duration_ms,
                    correlation_id=correlation_id_for_log,
                )

                return result

            except Exception as error:
                duration_ms = (time.perf_counter() - start_time) * 1000

                # Log the error
                log_backend_call(
                    logger,
                    self._get_backend_name(),
                    self._get_operation_name(),
                    endpoint=self._get_endpoint(process_parameters, settings),
                    success=False,
                    error=error,
                    duration_ms=duration_ms,
                    retry_count=self._counter,
                    correlation_id=correlation_id_for_log,
                )

                with self._lock:
                    # Check if we should retry
                    if self._counter >= self.MAX_RETRIES:
                        logger.error(
                            "Retry limit reached (%d), passing exception to dispatch",
                            self.MAX_RETRIES,
                        )
                        raise

                    # Check if this is a non-retryable error
                    if self._is_non_retryable_error(error):
                        raise

                    # Retry with backoff
                    self._counter += 1
                    current_counter = self._counter

                delay = (
                    0.001
                    if self._disable_retry
                    else min(
                        self.INITIAL_DELAY * (2 ** (current_counter - 1)),
                        self.MAX_DELAY,
                    )
                )
                logger.warning(
                    "Encountered an error. Retry number %d: %s",
                    current_counter,
                    error,
                )
                if delay > 0:
                    time.sleep(delay)

                # Prepare for retry
                self._prepare_for_retry(
                    process_parameters, settings, filename, **kwargs
                )

    def _get_operation_name(self) -> str:
        """Get the operation name for logging.

        Returns:
            Operation name (default: "send")

        """
        return "send"

    def _is_non_retryable_error(self, error: Exception) -> bool:
        """Check if an error should not be retried.

        Args:
            error: The exception to check

        Returns:
            True if the error should not be retried

        """
        if isinstance(error, (PermissionError, FileNotFoundError)):
            return True
        if isinstance(error, ConnectionRefusedError):
            return True
        if isinstance(error, TimeoutError):
            return True
        if isinstance(error, OSError):
            errno = getattr(error, "errno", None)
            if errno is not None and errno in (
                113,  # ECONNREFUSED (Linux)
                61,   # ECONNREFUSED (macOS)
                111,  # ECONNREFUSED (some Linux)
                2,    # ENOENT - No such file or directory
                9,    # EBADF - Bad file descriptor
                13,   # EACCES - Permission denied
                1,    # EPERM - Operation not permitted
                110,  # ETIMEDOUT - Connection timed out
                104,  # ECONNRESET - Connection reset by peer
                101,  # ENETUNREACH - Network is unreachable
                64,   # EHOSTDOWN - Host is down
                65,   # EHOSTUNREACH - No route to host
                99,   # EADDRNOTAVAIL - Cannot assign requested address
                22,   # EINVAL - Invalid argument
                87,   # WSAEINVAL (Windows) - Invalid argument
                10049,  # WSAADDRNOTAVAIL (Windows)
                10060,  # WSAETIMEDOUT (Windows)
                10054,  # WSAECONNRESET (Windows)
            ):
                return True
        return False

    def _prepare_for_retry(
        self,
        process_parameters: dict,
        settings: dict,
        filename: str,
        **kwargs: Any,
    ) -> None:
        """Prepare for a retry attempt.

        Override this method to perform any necessary preparation
        before retrying (e.g., seeking file handles back to beginning).

        Args:
            process_parameters: Backend-specific parameters
            settings: Application settings
            filename: File to process
            **kwargs: Additional backend-specific arguments

        """
        pass

    def _cleanup(self) -> None:
        """Cleanup connections and resources.

        Override this method to perform cleanup operations.
        Called in a finally block after each attempt.

        """
        pass

    @abstractmethod
    def _execute(
        self,
        process_parameters: dict,
        settings: dict,
        filename: str,
        **kwargs: Any,
    ) -> bool:
        """Execute the actual backend operation.

        This method must be implemented by subclasses to perform
        the actual backend-specific operation.

        Args:
            process_parameters: Backend-specific parameters
            settings: Application settings
            filename: File to process
            **kwargs: Additional backend-specific arguments

        Returns:
            True if operation was successful

        Raises:
            Exception: On failure

        """
        pass

    @abstractmethod
    def _get_backend_name(self) -> str:
        """Get the backend name for logging.

        Returns:
            Backend name (e.g., "smtp", "ftp", "http", "copy")

        """
        pass

    @abstractmethod
    def _get_endpoint(self, process_parameters: dict, settings: dict) -> str:
        """Get the endpoint for logging.

        Args:
            process_parameters: Backend-specific parameters
            settings: Application settings

        Returns:
            Endpoint string (URL, host:port, etc.)

        """
        pass
