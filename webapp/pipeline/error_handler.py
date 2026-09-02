"""Error Handler component for dispatch processing.

This module provides centralized error handling and logging,
using dependency injection for testability.
"""

import datetime
import os
import sys
import time
from io import StringIO
from typing import Any

from core.structured_logging import get_logger, log_with_context
from webapp.pipeline.file_system import RealFileSystem
from webapp.pipeline.interfaces import DatabaseInterface, FileSystemInterface, RunLog

logger = get_logger(__name__)


# Legacy run-log line ending: the Windows run-log reader in the field expects
# \r\n between header lines. Centralise the constant so call sites do not have
# to know about the legacy format.
_LEGACY_RUN_LOG_LINE_ENDING = "\r\n"


def generate_edi_validation_report(errors: str) -> str:
    """Format an EDI validation report.

    Mirrors the legacy ``ReportGenerator.generate_edi_validation_report`` output
    that ``ErrorHandler.write_validation_report`` has been emitting since the
    report-format migration. Callers must not depend on any specific line
    ordering beyond the header being the first line.
    """
    timestamp = datetime.datetime.now().isoformat().replace(":", "-")
    return (
        f"EDI Validation Report - {timestamp}{_LEGACY_RUN_LOG_LINE_ENDING}"
        f"{'=' * 50}{_LEGACY_RUN_LOG_LINE_ENDING}"
        f"{errors}"
    )


def generate_processing_report(errors: str, version: str) -> str:
    """Format a processing report with program version and error block.

    Mirrors the legacy ``ReportGenerator.generate_processing_report`` output
    consumed by ``ErrorHandler.write_processing_report``.
    """
    return (
        f"Program Version = {version}{_LEGACY_RUN_LOG_LINE_ENDING}"
        f"{_LEGACY_RUN_LOG_LINE_ENDING}"
        f"Processing Errors{_LEGACY_RUN_LOG_LINE_ENDING}"
        f"{'=' * 30}{_LEGACY_RUN_LOG_LINE_ENDING}"
        f"{errors}"
    )


class ErrorHandler:
    """Centralized error handler for dispatch operations.

    This class manages error recording to multiple destinations
    (database, log files, in-memory buffers).

    Attributes:
        db: Optional database interface for error persistence
        log_path: Optional path for error log files
        errors: List of recorded errors
        error_log: In-memory buffer for error messages

    """

    def __init__(
        self,
        errors_folder: str | None = None,
        run_log: RunLog | None = None,
        run_log_directory: str | None = None,
        database: DatabaseInterface | None = None,
        log_path: str | None = None,
        file_system: FileSystemInterface | None = None,
        alert_dispatcher: Any = None,
    ) -> None:
        """Initialize the error handler.

        Args:
            database: Optional database interface for error persistence
            log_path: Optional path for error log files
            file_system: Optional file system interface (uses RealFileSystem if None)
            alert_dispatcher: Optional alert dispatcher for error alerts

        """
        self.errors_folder = errors_folder or ""
        self.run_log = run_log
        self.run_log_directory = run_log_directory or ""
        self.db = database
        self.log_path = log_path
        self.fs = file_system or RealFileSystem()
        self.errors: list[dict] = []
        self.error_log: StringIO = StringIO()

        self._alert_dispatcher = alert_dispatcher

    def record_error(
        self,
        folder: str,
        filename: str,
        error: Exception,
        context: dict | None = None,
        error_source: str = "Dispatch",
        severity: str = "",
    ) -> None:
        """Record an error to all configured destinations.

        Args:
            folder: Folder where error occurred
            filename: File being processed when error occurred
            error: The exception that was raised
            context: Optional additional context
            error_source: Source module/component name
            severity: Optional "major"/"minor" classification (matches the
                original EDI validator's distinction: format failures are
                major problems that block a file, UPC/pricing issues are
                minor problems that don't). Empty for pipeline exceptions.

        """
        import logging

        error_record = {
            "timestamp": time.ctime(),
            "folder": folder,
            "filename": filename,
            "error_message": str(error),
            "error_type": type(error).__name__,
            "error_source": error_source,
            "severity": severity,
            "context": context or {},
        }

        # Emit through Python logging framework
        log_with_context(
            logger,
            logging.ERROR,
            f"Error in {folder} processing {filename}: {error}",
            context={
                "folder": folder,
                "filename": filename,
                "error_type": type(error).__name__,
                "error_source": error_source,
                **(context or {}),
            },
            exc_info=True,
        )

        # Add to in-memory list
        self.errors.append(error_record)

        # Write to error log buffer
        self._write_to_log(error_record)

        # Persist to database if configured
        if self.db is not None:
            self._persist_to_database(error_record)

        # Fire alert if configured and allowed
        if self._alert_dispatcher is not None and (context or {}).get(
            "alert_on_failure", True
        ):
            try:
                import traceback as tb

                self._alert_dispatcher.dispatch_error_alert(
                    error_record={
                        "error_type": type(error).__name__,
                        "error_message": str(error),
                        "stack_trace": tb.format_exc(),
                    },
                    correlation_id=(context or {}).get("correlation_id", ""),
                    folder_alias=(context or {}).get("folder_alias", ""),
                    file_path=(context or {}).get("file_path", ""),
                    processing_context=context,
                )
            except Exception:
                # Errors in error recording are silently ignored to avoid
                # cascading failures. The original error is already logged
                # or will be recorded via other paths.
                logger.debug(
                    "Failed to dispatch error alert (non-fatal)",
                    exc_info=True,
                    extra={"folder_alias": (context or {}).get("folder_alias", "")},
                )

    def record_error_to_logs(
        self,
        run_log: RunLog,
        errors_log: StringIO,
        error_message: str,
        filename: str,
        error_source: str,
        *,
        threaded: bool = False,
    ) -> tuple:
        """Record error to run log and errors log (backward compatible).

        This method provides compatibility with the existing record_error.do()
        function signature.

        Args:
            run_log: Run log file or list (for threaded mode)
            errors_log: Errors log StringIO or list (for threaded mode)
            error_message: Error message string
            filename: File being processed
            error_source: Source module name
            threaded: If True, use list append; if False, use write

        Returns:
            Tuple of (run_log, errors_log) for threaded mode

        """
        message = self._format_error_message(error_message, filename, error_source)

        if not threaded:
            if hasattr(run_log, "write"):
                run_log.write(message)
            if hasattr(errors_log, "write"):
                errors_log.write(message)
        else:
            if isinstance(run_log, list):
                run_log.append(message)
            if isinstance(errors_log, list):
                errors_log.append(message)
            return run_log, errors_log

        return run_log, errors_log

    def _format_error_message(
        self, error_message: str, filename: str, error_source: str
    ) -> str:
        """Format an error message for logging.

        Args:
            error_message: The error message
            filename: File being processed
            error_source: Source module name

        Returns:
            Formatted error message string

        """
        # _LEGACY_RUN_LOG_LINE_ENDING: legacy Windows run-log reader compatibility
        return (
            f"At: {time.ctime()}{_LEGACY_RUN_LOG_LINE_ENDING}"
            f"From module: {error_source}{_LEGACY_RUN_LOG_LINE_ENDING}"
            f"For object: {filename}{_LEGACY_RUN_LOG_LINE_ENDING}"
            f"Error Message is:{_LEGACY_RUN_LOG_LINE_ENDING}"
            f"{error_message}{_LEGACY_RUN_LOG_LINE_ENDING}"
            f"{_LEGACY_RUN_LOG_LINE_ENDING}"
        )

    def _write_to_log(self, error_record: dict) -> None:
        """Write error record to in-memory log buffer.

        Args:
            error_record: Error record dictionary

        """
        message = self._format_error_message(
            error_record["error_message"],
            error_record["filename"],
            error_record["error_source"],
        )
        self.error_log.write(message)

    def _persist_to_database(self, error_record: dict) -> None:
        """Persist error record to database.

        Args:
            error_record: Error record dictionary

        """
        assert self.db is not None
        try:
            raw_conn = (
                self.db.raw_connection if hasattr(self.db, "raw_connection") else None
            )
            if raw_conn is not None:
                columns = [
                    "timestamp",
                    "folder",
                    "filename",
                    "error_message",
                    "error_type",
                    "error_source",
                    "severity",
                ]
                placeholders = ", ".join("?" for _ in columns)
                col_names = ", ".join(f'"{c}"' for c in columns)
                sql = (
                    f"INSERT INTO dispatch_errors ({col_names}) VALUES ({placeholders})"
                )
                params = (
                    error_record.get("timestamp", time.ctime()),
                    error_record.get("folder", ""),
                    error_record.get("filename", ""),
                    error_record.get("error_message", ""),
                    error_record.get("error_type", ""),
                    error_record.get("error_source", ""),
                    error_record.get("severity", ""),
                )
                raw_conn.execute(sql, params)
                raw_conn.commit()
            else:
                self.db.insert(error_record)
        except Exception as e:
            error_msg = f"Failed to persist error to database: {e}\n"
            if self.error_log:
                try:
                    self.error_log.write(error_msg)
                except Exception:  # fallback to stderr if error_log write also fails
                    sys.stderr.write(error_msg)
            else:
                sys.stderr.write(error_msg)

    def write_error_log_file(self, log_path: str, version: str | None = None) -> bool:
        """Write accumulated errors to a log file.

        Args:
            log_path: Path to write the log file
            version: Optional version string to include in log

        Returns:
            True if write was successful, False otherwise

        """
        try:
            # Ensure directory exists
            log_dir = os.path.dirname(log_path)
            if log_dir and not self.fs.dir_exists(log_dir):
                self.fs.makedirs(log_dir)

            # Build log content
            content = ""
            if version:
                content += f"Program Version = {version}\r\n\r\n"
            content += self.error_log.getvalue()

            # Write file
            self.fs.write_file_text(log_path, content)
            return True

        except (OSError, PermissionError):
            return False

    def get_errors(self) -> list[dict]:
        """Get all recorded errors.

        Returns:
            List of error record dictionaries

        """
        return self.errors.copy()

    def get_error_log(self) -> str:
        """Get the error log contents.

        Returns:
            Error log as string

        """
        return self.error_log.getvalue()

    def clear_errors(self) -> None:
        """Clear all recorded errors."""
        self.errors = []
        self.error_log = StringIO()

    def has_errors(self) -> bool:
        """Check if any errors have been recorded.

        Returns:
            True if errors have been recorded, False otherwise

        """
        return bool(self.errors)

    def get_error_count(self) -> int:
        """Get the number of recorded errors.

        Returns:
            Number of errors

        """
        return len(self.errors)

    def write_validation_report(self, errors: str) -> str:
        """Write an EDI validation report to a file.

        Args:
            errors: Error message string to include in the report.

        Returns:
            Path to the written validation report file.

        """
        validator_log_name = (
            f"Validator Log {datetime.datetime.now().isoformat().replace(':', '-')}.txt"
        )
        validator_log_path = os.path.join(self.run_log_directory, validator_log_name)
        content = generate_edi_validation_report(errors)
        self.fs.write_file_text(validator_log_path, content)
        return validator_log_path

    def write_processing_report(self, errors: str, version: str) -> str:
        """Write a processing report to a file.

        Args:
            errors: Error message string to include in the report.
            version: Program version string to display in the report header.

        Returns:
            Path to the written processing report file.

        """
        folder_log_name = (
            f"Folder Errors Log"
            f" {datetime.datetime.now().isoformat().replace(':', '-')}.txt"
        )
        folder_log_path = os.path.join(self.run_log_directory, folder_log_name)
        content = generate_processing_report(errors, version)
        self.fs.write_file_text(folder_log_path, content)
        return folder_log_path
