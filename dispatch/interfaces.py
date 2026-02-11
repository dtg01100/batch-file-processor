"""Protocol interfaces for dependency injection.

This module defines Protocol classes for the main dependencies in the dispatch
system, enabling loose coupling and testability through dependency injection.
"""

from typing import Protocol, runtime_checkable, Any, Optional


@runtime_checkable
class DatabaseInterface(Protocol):
    """Protocol for database operations.
    
    Implementations should provide CRUD operations for database records.
    """
    
    def find(self, **kwargs) -> list[dict]:
        """Find records matching the given criteria.
        
        Args:
            **kwargs: Field name/value pairs to filter by
            
        Returns:
            List of matching records as dictionaries
        """
        ...
    
    def find_one(self, **kwargs) -> Optional[dict]:
        """Find a single record matching the given criteria.
        
        Args:
            **kwargs: Field name/value pairs to filter by
            
        Returns:
            Single matching record or None if not found
        """
        ...
    
    def insert(self, record: dict) -> None:
        """Insert a new record into the database.
        
        Args:
            record: Dictionary of field name/value pairs to insert
        """
        ...
    
    def insert_many(self, records: list[dict]) -> None:
        """Insert multiple records into the database.
        
        Args:
            records: List of dictionaries to insert
        """
        ...
    
    def update(self, record: dict, keys: list) -> None:
        """Update an existing record.
        
        Args:
            record: Dictionary with updated values and key fields
            keys: List of field names to use as keys for matching
        """
        ...
    
    def count(self, **kwargs) -> int:
        """Count records matching the given criteria.
        
        Args:
            **kwargs: Field name/value pairs to filter by
            
        Returns:
            Number of matching records
        """
        ...
    
    def query(self, sql: str) -> Any:
        """Execute a raw SQL query.
        
        Args:
            sql: SQL query string
            
        Returns:
            Query result (implementation-specific)
        """
        ...


@runtime_checkable
class FileSystemInterface(Protocol):
    """Protocol for file system operations.
    
    Implementations should provide file and directory operations,
    abstracting away direct file system access for testing.
    """
    
    def list_files(self, path: str) -> list[str]:
        """List all files in a directory.
        
        Args:
            path: Directory path to list
            
        Returns:
            List of file paths (absolute or relative based on implementation)
        """
        ...
    
    def read_file(self, path: str) -> bytes:
        """Read file contents as bytes.
        
        Args:
            path: Path to the file
            
        Returns:
            File contents as bytes
            
        Raises:
            FileNotFoundError: If file does not exist
            IOError: If file cannot be read
        """
        ...
    
    def read_file_text(self, path: str, encoding: str = 'utf-8') -> str:
        """Read file contents as text.
        
        Args:
            path: Path to the file
            encoding: Text encoding (default: utf-8)
            
        Returns:
            File contents as string
        """
        ...
    
    def write_file(self, path: str, data: bytes) -> None:
        """Write bytes to a file.
        
        Args:
            path: Path to the file
            data: Bytes to write
        """
        ...
    
    def write_file_text(self, path: str, data: str, encoding: str = 'utf-8') -> None:
        """Write text to a file.
        
        Args:
            path: Path to the file
            data: String to write
            encoding: Text encoding (default: utf-8)
        """
        ...
    
    def file_exists(self, path: str) -> bool:
        """Check if a file exists.
        
        Args:
            path: Path to check
            
        Returns:
            True if file exists, False otherwise
        """
        ...
    
    def dir_exists(self, path: str) -> bool:
        """Check if a directory exists.
        
        Args:
            path: Path to check
            
        Returns:
            True if directory exists, False otherwise
        """
        ...
    
    def mkdir(self, path: str) -> None:
        """Create a directory.
        
        Args:
            path: Directory path to create
        """
        ...
    
    def makedirs(self, path: str) -> None:
        """Create a directory and all parent directories.
        
        Args:
            path: Directory path to create
        """
        ...
    
    def copy_file(self, src: str, dst: str) -> None:
        """Copy a file.
        
        Args:
            src: Source file path
            dst: Destination file path
        """
        ...
    
    def remove_file(self, path: str) -> None:
        """Remove a file.
        
        Args:
            path: Path to the file to remove
        """
        ...
    
    def get_absolute_path(self, path: str) -> str:
        """Get the absolute path.
        
        Args:
            path: Relative or absolute path
            
        Returns:
            Absolute path
        """
        ...


@runtime_checkable
class BackendInterface(Protocol):
    """Protocol for send backends.
    
    Implementations should handle sending files to various destinations
    (FTP, email, copy, etc.).
    """
    
    def send(self, params: dict, settings: dict, filename: str) -> None:
        """Send a file using this backend.
        
        Args:
            params: Folder-specific parameters
            settings: Global application settings
            filename: Path to the file to send
            
        Raises:
            Exception: If send operation fails
        """
        ...
    
    def validate(self, params: dict) -> list[str]:
        """Validate backend configuration.
        
        Args:
            params: Folder-specific parameters
            
        Returns:
            List of validation error messages (empty if valid)
        """
        ...
    
    def get_name(self) -> str:
        """Get the backend name for logging.
        
        Returns:
            Human-readable backend name
        """
        ...


@runtime_checkable
class ValidatorInterface(Protocol):
    """Protocol for file validators.
    
    Implementations should validate file contents and report issues.
    """
    
    def validate(self, file_path: str) -> tuple[bool, list[str]]:
        """Validate a file.
        
        Args:
            file_path: Path to the file to validate
            
        Returns:
            Tuple of (is_valid, errors) where errors is a list of
            error messages (empty if valid)
        """
        ...
    
    def validate_with_warnings(self, file_path: str) -> tuple[bool, list[str], list[str]]:
        """Validate a file and return both errors and warnings.
        
        Args:
            file_path: Path to the file to validate
            
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        ...


@runtime_checkable
class ErrorHandlerInterface(Protocol):
    """Protocol for error handling.
    
    Implementations should record errors to appropriate destinations
    (database, log files, etc.).
    """
    
    def record_error(
        self,
        folder: str,
        filename: str,
        error: Exception,
        context: Optional[dict] = None
    ) -> None:
        """Record an error.
        
        Args:
            folder: Folder where error occurred
            filename: File being processed when error occurred
            error: The exception that was raised
            context: Optional additional context
        """
        ...
    
    def get_errors(self) -> list[dict]:
        """Get all recorded errors.
        
        Returns:
            List of error records
        """
        ...
    
    def clear_errors(self) -> None:
        """Clear all recorded errors."""
        ...


@runtime_checkable
class LogInterface(Protocol):
    """Protocol for logging operations.
    
    Implementations should provide logging capabilities.
    """
    
    def write(self, message: str) -> None:
        """Write a message to the log.
        
        Args:
            message: Message to write
        """
        ...
    
    def writelines(self, lines: list[str]) -> None:
        """Write multiple lines to the log.
        
        Args:
            lines: Lines to write
        """
        ...
    
    def get_value(self) -> str:
        """Get the current log contents.
        
        Returns:
            Log contents as string
        """
        ...
    
    def close(self) -> None:
        """Close the log."""
        ...
