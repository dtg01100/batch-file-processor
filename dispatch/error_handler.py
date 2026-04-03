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

import scripts.record_error as record_error
from core.structured_logging import get_logger, log_with_context
from dispatch.interfaces import DatabaseInterface, FileSystemInterface

logger = get_logger(__name__)


class ErrorLogger:
    """Legacy error logger preserved for compatibility.

    This class wraps the scripts.record_error.do() function to provide
    an object-oriented interface for recording errors to both run logs
    and error logs.

    Note:
        New code should use ErrorHandler.record_error() instead, which
        provides richer context tracking and multiple destination support.

    Attributes:
        errors_folder: Path to the folder where error logs are stored.
        run_log: Run log file handle or buffer.
        folder_errors_log: In-memory buffer for folder-level errors.

    """

    def __init__(self, errors_folder: str = "", run_log: Any = None) -> None:
        """Initialize the error logger.

        Args:
            errors_folder: Path to folder for storing error logs.
            run_log: Optional run log file handle or buffer.

        """
        self.errors_folder = errors_folder
        self.run_log = run_log
        self.folder_errors_log = StringIO()

    def log_error(self, error_message: str, filename: str, module: str) -> None:
        """Record an error to both the run log and errors log.

        Args:
            error_message: The error message to record.
            filename: Name of the file being processed when the error occurred.
            module: Name of the module or component where the error originated.

        """
        record_error.do(
            self.run_log,
            self.folder_errors_log,
            error_message,
            filename,
            module,
        )

    def log_folder_error(
        self, error_message: str, folder_name: str, module: str = "Dispatch"
    ) -> None:
        """Record an error that occurred at the folder level.

        Args:
            error_message: The error message to record.
            folder_name: Name of the folder where the error occurred.
            module: Name of the module where the error originated (default: "Dispatch").

        """
        self.log_error(error_message, folder_name, module)

    def log_file_error(
        self, error_message: str, filename: str, module: str = "Dispatch"
    ) -> None:
        """Record an error that occurred while processing a specific file.

        Args:
            error_message: The error message to record.
            filename: Name of the file being processed when the error occurred.
            module: Name of the module where the error originated (default: "Dispatch").

        """
        self.log_error(error_message, filename, module)

    def get_errors(self) -> str:
        """Get the accumulated folder error log contents.

        Returns:
            String containing all folder error log entries.

        """
        return self.folder_errors_log.getvalue()

    def has_errors(self) -> bool:
        """Check if any folder errors have been recorded.

        Returns:
            True if error log is non-empty, False otherwise.

        """
        return len(self.get_errors()) > 0

    def close(self) -> None:
        """Close the folder error log StringIO buffer."""
        self.folder_errors_log.close()


class ReportGenerator:
    """Legacy report generator preserved for compatibility.

    This class generates simple text-based validation and processing
    reports with timestamps and error summaries.

    Note:
        New code should use structured logging via core.structured_logging
        instead of these legacy text reports.

    """

    @staticmethod
    def generate_edi_validation_report(errors: str) -> str:
        """Generate an EDI validation report with error details.

        Args:
            errors: Error message string to include in the report.

        Returns:
            Formatted report string with timestamp and error details.

        """
        timestamp = datetime.datetime.now().isoformat().replace(":", "-")
        report = f"EDI Validation Report - {timestamp}\r\n"
        report += "=" * 50 + "\r\n"
        report += errors
        return report

    @staticmethod
    def generate_processing_report(errors: str, version: str) -> str:
        """Generate a processing report with program version and errors.

        Args:
            errors: Error message string to include in the report.
            version: Program version string to display in the report header.

        Returns:
            Formatted report string with version and error details.

        """
        report = f"Program Version = {version}\r\n\r\n"
        report += "Processing Errors\r\n"
        report += "=" * 30 + "\r\n"
        report += errors
        return report


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
        run_log: Any = None,
        run_log_directory: str | None = None,
        database: DatabaseInterface | None = None,
        log_path: str | None = None,
        file_system: FileSystemInterface | None = None,
    ) -> None:
        """Initialize the error handler.

        Args:
            database: Optional database interface for error persistence
            log_path: Optional path for error log files
            file_system: Optional file system interface (uses RealFileSystem if None)

        """
        self.errors_folder = errors_folder or ""
        self.run_log = run_log
        self.run_log_directory = run_log_directory or ""
        self.db = database
        self.log_path = log_path
        self.fs = file_system or RealFileSystem()
        self.errors: list[dict] = []
        self.error_log: StringIO = StringIO()
        self.logger = ErrorLogger(self.errors_folder, self.run_log)
        self.report_generator = ReportGenerator()

    def record_error(
        self,
        folder: str,
        filename: str,
        error: Exception,
        context: dict | None = None,
        error_source: str = "Dispatch",
    ) -> None:
        """Record an error to all configured destinations.

        Args:
            folder: Folder where error occurred
            filename: File being processed when error occurred
            error: The exception that was raised
            context: Optional additional context
            error_source: Source module/component name

        """
        import logging

        error_record = {
            "timestamp": time.ctime(),
            "folder": folder,
            "filename": filename,
            "error_message": str(error),
            "error_type": type(error).__name__,
            "error_source": error_source,
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

    def record_error_to_logs(
        self,
        run_log: Any,
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
                run_log.write(message.encode())
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
        return (
            f"At: {time.ctime()}\r\n"
            f"From module: {error_source}\r\n"
            f"For object: {filename}\r\n"
            f"Error Message is:\r\n{error_message}\r\n\r\n"
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
        try:
            self.db.insert(error_record)
        except Exception as e:
            error_msg = f"Failed to persist error to database: {e}\n"
            if self.error_log:
                try:
                    self.error_log.write(error_msg)
                except Exception:
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
        return len(self.errors) > 0

    def get_error_count(self) -> int:
        """Get the number of recorded errors.

        Returns:
            Number of errors

        """
        return len(self.errors)

    def log_error(self, error_message: str, filename: str, module: str) -> None:
        """Delegate error logging to the legacy ErrorLogger.

        Args:
            error_message: The error message to record.
            filename: Name of the file being processed.
            module: Name of the module where the error originated.

        """
        self.logger.log_error(error_message, filename, module)

    def log_folder_error(
        self, error_message: str, folder_name: str, module: str = "Dispatch"
    ) -> None:
        """Delegate folder-level error logging to the legacy ErrorLogger.

        Args:
            error_message: The error message to record.
            folder_name: Name of the folder where the error occurred.
            module: Name of the module where the error originated.

        """
        self.logger.log_folder_error(error_message, folder_name, module)

    def log_file_error(
        self, error_message: str, filename: str, module: str = "Dispatch"
    ) -> None:
        """Delegate file-level error logging to the legacy ErrorLogger.

        Args:
            error_message: The error message to record.
            filename: Name of the file being processed.
            module: Name of the module where the error originated.

        """
        self.logger.log_file_error(error_message, filename, module)

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
        content = self.report_generator.generate_edi_validation_report(errors)
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
        folder_log_name = f"Folder Errors Log {datetime.datetime.now().isoformat().replace(':', '-')}.txt"
        folder_log_path = os.path.join(self.run_log_directory, folder_log_name)
        content = self.report_generator.generate_processing_report(errors, version)
        self.fs.write_file_text(folder_log_path, content)
        return folder_log_path


class RealFileSystem:
    """Real file system implementation for production use."""

    def read_file(self, path: str) -> bytes:
        """Read file contents as bytes."""
        with open(path, "rb") as f:
            return f.read()

    def read_file_text(self, path: str, encoding: str = "utf-8") -> str:
        """Read file contents as text."""
        with open(path, "r", encoding=encoding) as f:
            return f.read()

    def write_file(self, path: str, data: bytes) -> None:
        """Write bytes to a file."""
        with open(path, "wb") as f:
            f.write(data)

    def write_file_text(self, path: str, data: str, encoding: str = "utf-8") -> None:
        """Write text to a file."""
        with open(path, "w", encoding=encoding) as f:
            f.write(data)

    def file_exists(self, path: str) -> bool:
        """Check if a file exists."""
        return os.path.isfile(path)

    def dir_exists(self, path: str) -> bool:
        """Check if a directory exists."""
        return os.path.isdir(path)

    def mkdir(self, path: str) -> None:
        """Create a directory."""
        os.mkdir(path)

    def makedirs(self, path: str) -> None:
        """Create a directory and all parent directories."""
        os.makedirs(path, exist_ok=True)

    def list_files(self, path: str) -> list[str]:
        """List all files in a directory."""
        if not os.path.isdir(path):
            return []
        return [
            os.path.abspath(os.path.join(path, f))
            for f in os.listdir(path)
            if os.path.isfile(os.path.join(path, f))
        ]

    def copy_file(self, src: str, dst: str) -> None:
        """Copy a file."""
        import shutil

        shutil.copyfile(src, dst)

    def remove_file(self, path: str) -> None:
        """Remove a file."""
        os.remove(path)

    def get_absolute_path(self, path: str) -> str:
        """Get the absolute path."""
        return os.path.abspath(path)


# Backward-compatible function interface
def do(run_log, errors_log, error_message, filename, error_source, *, threaded=False):
    """Backward-compatible error recording function.

    This function provides compatibility with the existing record_error.do()
    function signature.

    Args:
        run_log: Run log file or list
        errors_log: Errors log StringIO or list
        error_message: Error message string
        filename: File being processed
        error_source: Source module name
        threaded: If True, use list append; if False, use write

    Returns:
        Tuple of (run_log, errors_log) for threaded mode, or None

    """
    handler = ErrorHandler()
    return handler.record_error_to_logs(
        run_log, errors_log, error_message, filename, error_source, threaded=threaded
    )
