"""Retry mixin for backend operations.

This module provides a reusable mixin class that implements
retry logic with exponential backoff for backend operations.
"""

import logging
import time
from typing import Any, Callable, TypeVar

from core.constants import DEFAULT_MAX_RETRIES
from core.structured_logging import get_logger, log_with_context

logger = get_logger(__name__)

T = TypeVar("T")


class BackendRetryMixin:
    """Mixin providing retry logic with exponential backoff.

    This mixin can be used by backend classes to add automatic
    retry functionality with configurable attempts and backoff.

    Example:
        class MyBackend(BackendRetryMixin):
            def send_file(self, filename):
                return self.retry_operation(
                    operation=lambda: self._do_send(filename),
                    max_retries=10,
                    operation_name="send_file"
                )

    """

    def retry_operation(
        self,
        operation: Callable[[], T],
        max_retries: int = DEFAULT_MAX_RETRIES,
        operation_name: str = "operation",
        initial_backoff: float = 2.0,
        max_backoff: float = 60.0,
        cleanup: Callable[[], None] | None = None,
    ) -> T:
        """Execute an operation with retry logic and exponential backoff.

        Args:
            operation: Callable that performs the operation.
                      Should raise exception on failure.
            max_retries: Maximum number of retry attempts (default: 10)
            operation_name: Name of operation for logging (default: "operation")
            initial_backoff: Initial backoff in seconds (default: 2.0)
            max_backoff: Maximum backoff in seconds (default: 60.0)
            cleanup: Optional cleanup callable to run after each attempt
                    (runs even on success, in finally block)

        Returns:
            The return value from the successful operation

        Raises:
            Exception: The exception from the last failed attempt if all
                      retries are exhausted

        """
        counter = 0

        while True:
            try:
                return operation()
            except Exception as e:
                if counter >= max_retries:
                    logger.error(
                        "Operation '%s' failed after %d retries: %s",
                        operation_name,
                        max_retries,
                        e,
                    )
                    raise

                counter += 1
                backoff = min(initial_backoff**counter, max_backoff)

                logger.debug(
                    "Operation '%s' failed (attempt %d/%d): %s. Retrying in %.1fs...",
                    operation_name,
                    counter,
                    max_retries,
                    e,
                    backoff,
                )

                time.sleep(backoff)
            finally:
                if cleanup is not None:
                    try:
                        cleanup()
                    except Exception as cleanup_error:
                        logger.debug(
                            "Cleanup error in '%s': %s", operation_name, cleanup_error
                        )

    def with_logging(
        self,
        operation: Callable[[], T],
        logger_instance: Any,
        operation_name: str,
        context: dict[str, Any] | None = None,
    ) -> T:
        """Execute an operation with structured logging.

        Args:
            operation: Callable that performs the operation
            logger_instance: Logger instance to use
            operation_name: Name of operation for logging
            context: Optional context dictionary for logging

        Returns:
            The return value from the operation

        """
        if context is None:
            context = {}

        log_with_context(
            logger_instance,
            logging.INFO,
            f"Starting {operation_name}",
            operation=operation_name,
            context=context,
        )

        try:
            result = operation()
            log_with_context(
                logger_instance,
                logging.INFO,
                f"{operation_name} completed successfully",
                operation=operation_name,
                context=context,
            )
            return result
        except Exception as e:
            log_with_context(
                logger_instance,
                logging.ERROR,
                f"{operation_name} failed: {e}",
                operation=operation_name,
                context={**context, "error": str(e)},
            )
            raise


# Module-level helper for functional-style backends
def retry_with_backoff(
    operation: Callable[[], T],
    max_retries: int = 10,
    operation_name: str = "operation",
    initial_backoff: float = 2.0,
    max_backoff: float = 60.0,
    logger_instance: Any | None = None,
) -> T:
    """Execute an operation with retry logic and exponential backoff.

    Functional version for use in module-level do() functions.

    Args:
        operation: Callable that performs the operation
        max_retries: Maximum number of retry attempts
        operation_name: Name of operation for logging
        initial_backoff: Initial backoff in seconds
        max_backoff: Maximum backoff in seconds
        logger_instance: Optional logger instance for debug logging

    Returns:
        The return value from the successful operation

    Raises:
        Exception: The exception from the last failed attempt

    """
    if logger_instance is None:
        logger_instance = logger

    counter = 0

    while True:
        try:
            return operation()
        except Exception as e:
            if counter >= max_retries:
                logger_instance.error(
                    "Operation '%s' failed after %d retries: %s",
                    operation_name,
                    max_retries,
                    e,
                )
                raise

            counter += 1
            backoff = min(initial_backoff**counter, max_backoff)

            logger_instance.debug(
                "Operation '%s' failed (attempt %d/%d): %s. Retrying in %.1fs...",
                operation_name,
                counter,
                max_retries,
                e,
                backoff,
            )

            time.sleep(backoff)
