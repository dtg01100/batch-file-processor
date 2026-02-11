"""Error Handler component for dispatch processing.

This module provides centralized error handling and logging,
using dependency injection for testability.
"""

import os
import time
from io import StringIO
from typing import Optional, Protocol, runtime_checkable, Any

from dispatch.interfaces import DatabaseInterface, FileSystemInterface


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
        database: Optional[DatabaseInterface] = None,
        log_path: Optional[str] = None,
        file_system: Optional[FileSystemInterface] = None
    ):
        """Initialize the error handler.
        
        Args:
            database: Optional database interface for error persistence
            log_path: Optional path for error log files
            file_system: Optional file system interface (uses RealFileSystem if None)
        """
        self.db = database
        self.log_path = log_path
        self.fs = file_system or RealFileSystem()
        self.errors: list[dict] = []
        self.error_log: StringIO = StringIO()
    
    def record_error(
        self,
        folder: str,
        filename: str,
        error: Exception,
        context: Optional[dict] = None,
        error_source: str = "Dispatch"
    ) -> None:
        """Record an error to all configured destinations.
        
        Args:
            folder: Folder where error occurred
            filename: File being processed when error occurred
            error: The exception that was raised
            context: Optional additional context
            error_source: Source module/component name
        """
        error_record = {
            'timestamp': time.ctime(),
            'folder': folder,
            'filename': filename,
            'error_message': str(error),
            'error_type': type(error).__name__,
            'error_source': error_source,
            'context': context or {}
        }
        
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
        threaded: bool = False
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
            if hasattr(run_log, 'write'):
                run_log.write(message.encode())
            if hasattr(errors_log, 'write'):
                errors_log.write(message)
        else:
            if isinstance(run_log, list):
                run_log.append(message)
            if isinstance(errors_log, list):
                errors_log.append(message)
            return run_log, errors_log
        
        return run_log, errors_log
    
    def _format_error_message(
        self,
        error_message: str,
        filename: str,
        error_source: str
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
            error_record['error_message'],
            error_record['filename'],
            error_record['error_source']
        )
        self.error_log.write(message)
    
    def _persist_to_database(self, error_record: dict) -> None:
        """Persist error record to database.
        
        Args:
            error_record: Error record dictionary
        """
        try:
            self.db.insert(error_record)
        except Exception:
            # Don't raise - just log that persistence failed
            pass
    
    def write_error_log_file(
        self,
        log_path: str,
        version: Optional[str] = None
    ) -> bool:
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
            
        except Exception:
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


class RealFileSystem:
    """Real file system implementation for production use."""
    
    def read_file(self, path: str) -> bytes:
        """Read file contents as bytes."""
        with open(path, 'rb') as f:
            return f.read()
    
    def read_file_text(self, path: str, encoding: str = 'utf-8') -> str:
        """Read file contents as text."""
        with open(path, 'r', encoding=encoding) as f:
            return f.read()
    
    def write_file(self, path: str, data: bytes) -> None:
        """Write bytes to a file."""
        with open(path, 'wb') as f:
            f.write(data)
    
    def write_file_text(self, path: str, data: str, encoding: str = 'utf-8') -> None:
        """Write text to a file."""
        with open(path, 'w', encoding=encoding) as f:
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
def do(run_log, errors_log, error_message, filename, error_source, threaded=False):
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
        run_log, errors_log, error_message, filename, error_source, threaded
    )
