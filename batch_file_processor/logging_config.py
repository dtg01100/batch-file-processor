"""Centralized logging configuration for the Batch File Sender application.

This module replaces the ad-hoc mix of print() statements and partial logging
usage throughout the codebase with a single, consistent configuration point.

Usage::

    # At application startup (e.g. in main_qt.py):
    from batch_file_processor.logging_config import setup_logging
    setup_logging()

    # In any module that needs logging:
    from batch_file_processor.logging_config import get_logger
    logger = get_logger(__name__)
    logger.info("Processing file %s", filename)

    # For run-log integration:
    from batch_file_processor.logging_config import RunLogHandler
    handler = RunLogHandler(run_log_file)
    logger.addHandler(handler)
"""

from __future__ import annotations

import logging
import os
import sys
from typing import IO, Union

from batch_file_processor.structured_logging import (
    JSONFormatter,
    StructuredLogAdapter,
    get_correlation_id,
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

        from batch_file_processor.logging_config import get_logger
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
