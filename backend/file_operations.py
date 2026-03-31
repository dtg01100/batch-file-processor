"""File operations implementations for send backends.

This module provides real and mock file operation implementations
that conform to the FileOperationsProtocol interface.
"""

import os
import shutil
import time
from collections.abc import Callable

from backend.protocols import FileOperationsProtocol
from core.structured_logging import (
    get_logger,
    get_or_create_correlation_id,
    log_backend_call,
    log_file_operation,
)

logger = get_logger(__name__)


class RealFileOperations:
    """Real file operations using shutil and os.

    This implementation provides actual filesystem operations
    for copying, moving, and managing files.
    """

    def _execute_with_logging(
        self,
        operation: str,
        path: str,
        func: Callable,
        *args: object,
        endpoint: str | None = None,
        **kwargs: object,
    ) -> None:
        """Execute a file operation with consistent logging.

        Args:
            operation: Operation name for logging (e.g., "copy", "move", "delete")
            path: Primary file path
            func: Function to execute
            *args: Arguments to pass to func
            endpoint: Optional endpoint for backend logging (defaults to path)
            **kwargs: Keyword arguments to pass to func
        """
        get_or_create_correlation_id()
        start_time = time.perf_counter()
        endpoint = endpoint or path
        if operation == "copy":
            logger.debug("Copying file %s -> %s", args[0], args[1])
        elif operation == "move":
            logger.debug("Moving %s -> %s", args[0], args[1])
        else:
            logger.debug("%s %s", operation.capitalize(), path)
        log_file_operation(logger, operation, path, file_type=None, success=None)
        log_backend_call(logger, "file", operation, endpoint=endpoint, success=None)

        try:
            func(*args, **kwargs)
            duration_ms = (time.perf_counter() - start_time) * 1000
            log_file_operation(
                logger,
                operation,
                path,
                file_type=None,
                success=True,
                duration_ms=duration_ms,
            )
            log_backend_call(
                logger,
                "file",
                operation,
                endpoint=endpoint,
                success=True,
                duration_ms=duration_ms,
            )
            if operation == "copy":
                logger.debug("Copied file %s -> %s", args[0], args[1])
            elif operation == "move":
                logger.debug("Moved %s -> %s", args[0], args[1])
            else:
                logger.debug("%s successful: %s", operation.capitalize(), path)
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            log_file_operation(
                logger,
                operation,
                path,
                file_type=None,
                success=False,
                error=e,
                duration_ms=duration_ms,
            )
            log_backend_call(
                logger,
                "file",
                operation,
                endpoint=endpoint,
                success=False,
                error=e,
                duration_ms=duration_ms,
            )
            raise

    def copy(self, src: str, dst: str) -> None:
        """Copy a file.

        Args:
            src: Source file path
            dst: Destination file path

        Raises:
            FileNotFoundError: If source file doesn't exist
            PermissionError: If permission denied

        """
        self._execute_with_logging(
            "copy", src, shutil.copy, src, dst, endpoint=f"{src} -> {dst}"
        )

    def copy2(self, src: str, dst: str) -> None:
        """Copy a file with metadata preserved.

        Args:
            src: Source file path
            dst: Destination file path

        """
        logger.debug("Copying file with metadata %s -> %s", src, dst)
        shutil.copy2(src, dst)

    def copytree(self, src: str, dst: str, *, symlinks: bool = False) -> None:
        """Copy a directory tree.

        Args:
            src: Source directory path
            dst: Destination directory path
            symlinks: Whether to copy symlinks as symlinks

        """
        logger.debug(
            "Copying directory tree %s -> %s (symlinks=%s)", src, dst, symlinks
        )
        shutil.copytree(src, dst, symlinks=symlinks)

    def exists(self, path: str) -> bool:
        """Check if path exists.

        Args:
            path: Path to check

        Returns:
            True if path exists, False otherwise

        """
        logger.debug("Checking if path exists: %s", path)
        result = os.path.exists(path)
        return result

    def makedirs(self, path: str, *, exist_ok: bool = False) -> None:
        """Create directory and all parent directories.

        Args:
            path: Directory path to create
            exist_ok: If True, don't raise error if directory exists

        """
        logger.debug("Creating directories %s (exist_ok=%s)", path, exist_ok)
        os.makedirs(path, exist_ok=exist_ok)
        logger.debug("Created directories %s", path)

    def remove(self, path: str) -> None:
        """Remove a file.

        Args:
            path: File path to remove

        Raises:
            FileNotFoundError: If file doesn't exist
            PermissionError: If permission denied

        """
        self._execute_with_logging("delete", path, os.remove, path)

    def rmtree(self, path: str) -> None:
        """Remove directory and all contents.

        Args:
            path: Directory path to remove

        """
        logger.debug("Removing directory tree %s", path)
        shutil.rmtree(path)

    def basename(self, path: str) -> str:
        """Get base name of path.

        Args:
            path: File path

        Returns:
            Base name (final component) of path

        """
        return os.path.basename(path)

    def dirname(self, path: str) -> str:
        """Get directory name of path.

        Args:
            path: File path

        Returns:
            Directory name of path

        """
        return os.path.dirname(path)

    def join(self, *paths: str) -> str:
        """Join path components.

        Args:
            *paths: Path components to join

        Returns:
            Joined path

        """
        return os.path.join(*paths)

    def isfile(self, path: str) -> bool:
        """Check if path is a file.

        Args:
            path: Path to check

        Returns:
            True if path is a file, False otherwise

        """
        logger.debug("Checking if path is file: %s", path)
        result = os.path.isfile(path)
        return result

    def isdir(self, path: str) -> bool:
        """Check if path is a directory.

        Args:
            path: Path to check

        Returns:
            True if path is a directory, False otherwise

        """
        logger.debug("Checking if path is directory: %s", path)
        result = os.path.isdir(path)
        return result

    def listdir(self, path: str) -> list[str]:
        """List contents of a directory.

        Args:
            path: Directory path

        Returns:
            List of file and directory names

        """
        logger.debug("Listing directory: %s", path)
        result = os.listdir(path)
        return result

    def getsize(self, path: str) -> int:
        """Get file size in bytes.

        Args:
            path: File path

        Returns:
            File size in bytes

        """
        logger.debug("Getting size of: %s", path)
        result = os.path.getsize(path)
        return result

    def move(self, src: str, dst: str) -> None:
        """Move a file or directory.

        Args:
            src: Source path
            dst: Destination path

        """
        self._execute_with_logging(
            "move", src, shutil.move, src, dst, endpoint=f"{src} -> {dst}"
        )

    def rename(self, src: str, dst: str) -> None:
        """Rename a file or directory.

        Args:
            src: Source path
            dst: Destination path

        """
        logger.debug("Renaming %s -> %s", src, dst)
        shutil.move(src, dst)

    def stat(self, path: str) -> os.stat_result:
        """Get file status.

        Args:
            path: File path

        Returns:
            stat_result object

        """
        logger.debug("stat(%s)", path)
        return os.stat(path)

    def abspath(self, path: str) -> str:
        """Get absolute path.

        Args:
            path: Relative or absolute path

        Returns:
            Absolute path

        """
        return os.path.abspath(path)


class MockFileOperations:
    """Mock file operations for testing.

    This implementation records all operations for verification
    in tests without making actual filesystem changes.

    Attributes:
        files_copied: List of (src, dst) tuples from copy calls
        directories_created: List of directory paths from makedirs calls
        files_removed: List of file paths from remove calls
        directories_removed: List of directory paths from rmtree calls

    """

    def __init__(self) -> None:
        """Initialize mock file operations with empty tracking state."""
        self.files_copied: list[tuple] = []
        self.files_copied2: list[tuple] = []
        self.trees_copied: list[tuple] = []
        self.directories_created: list[tuple] = []
        self.files_removed: list[str] = []
        self.directories_removed: list[str] = []
        self.files_moved: list[tuple] = []
        self.files_renamed: list[tuple] = []
        self._existing_paths: set = set()
        self._files: dict = {}  # path -> content
        self._directories: set = set()
        self._file_sizes: dict = {}
        self.errors: list[Exception] = []
        self._current_error_index: int = 0

    def _raise_error_if_set(self) -> None:
        """Raise next error from errors list if available."""
        if self._current_error_index < len(self.errors):
            error = self.errors[self._current_error_index]
            self._current_error_index += 1
            raise error

    def copy(self, src: str, dst: str) -> None:
        """Record file copy.

        Args:
            src: Source file path
            dst: Destination file path

        """
        self._raise_error_if_set()
        self.files_copied.append((src, dst))
        self._existing_paths.add(dst)
        # Copy file content if it exists
        if src in self._files:
            self._files[dst] = self._files[src]

    def copy2(self, src: str, dst: str) -> None:
        """Record file copy with metadata.

        Args:
            src: Source file path
            dst: Destination file path

        """
        self._raise_error_if_set()
        self.files_copied2.append((src, dst))
        self._existing_paths.add(dst)

    def copytree(self, src: str, dst: str, *, symlinks: bool = False) -> None:
        """Record directory tree copy.

        Args:
            src: Source directory path
            dst: Destination directory path
            symlinks: Whether to copy symlinks

        """
        self._raise_error_if_set()
        self.trees_copied.append((src, dst, symlinks))
        self._directories.add(dst)
        self._existing_paths.add(dst)

    def exists(self, path: str) -> bool:
        """Check if path exists in mock filesystem.

        Args:
            path: Path to check

        Returns:
            True if path was added to existing paths

        """
        return path in self._existing_paths or path in self._directories

    def makedirs(self, path: str, *, exist_ok: bool = False) -> None:
        """Record directory creation.

        Args:
            path: Directory path to create
            exist_ok: If True, don't raise error if exists

        """
        self._raise_error_if_set()
        self.directories_created.append((path, exist_ok))
        self._directories.add(path)
        self._existing_paths.add(path)

    def remove(self, path: str) -> None:
        """Record file removal.

        Args:
            path: File path to remove

        """
        self._raise_error_if_set()
        self.files_removed.append(path)
        self._existing_paths.discard(path)
        self._files.pop(path, None)

    def rmtree(self, path: str) -> None:
        """Record directory tree removal.

        Args:
            path: Directory path to remove

        """
        self._raise_error_if_set()
        self.directories_removed.append(path)
        self._directories.discard(path)
        self._existing_paths.discard(path)

    def basename(self, path: str) -> str:
        """Get base name of path.

        Args:
            path: File path

        Returns:
            Base name (final component) of path

        """
        # Normalize backslashes so os.path works on all platforms
        return os.path.basename(path.replace("\\", "/"))

    def dirname(self, path: str) -> str:
        """Get directory name of path.

        Args:
            path: File path

        Returns:
            Directory name of path

        """
        # Normalize backslashes so os.path works on all platforms
        return os.path.dirname(path.replace("\\", "/"))

    def join(self, *paths: str) -> str:
        """Join path components.

        Args:
            *paths: Path components to join

        Returns:
            Joined path

        """
        return os.path.join(*paths)

    def isfile(self, path: str) -> bool:
        """Check if path is a file.

        Args:
            path: Path to check

        Returns:
            True if path is a file

        """
        return path in self._files

    def isdir(self, path: str) -> bool:
        """Check if path is a directory.

        Args:
            path: Path to check

        Returns:
            True if path is a directory

        """
        return path in self._directories

    def listdir(self, path: str) -> list[str]:
        """List contents of a directory.

        Args:
            path: Directory path

        Returns:
            List of file and directory names

        """
        # Return files that are direct children of this path
        prefix = os.path.join(path, "")
        return [
            file_path[len(prefix) :]
            for file_path in self._files
            if file_path.startswith(prefix) and os.sep not in file_path[len(prefix) :]
        ]

    def getsize(self, path: str) -> int:
        """Get file size in bytes.

        Args:
            path: File path

        Returns:
            File size in bytes

        """
        if path in self._file_sizes:
            return self._file_sizes[path]
        if path in self._files:
            content = self._files[path]
            if isinstance(content, bytes):
                return len(content)
            return len(content.encode("utf-8"))
        return 0

    def move(self, src: str, dst: str) -> None:
        """Record file move.

        Args:
            src: Source path
            dst: Destination path

        """
        self._raise_error_if_set()
        self.files_moved.append((src, dst))
        self._existing_paths.discard(src)
        self._existing_paths.add(dst)
        if src in self._files:
            self._files[dst] = self._files.pop(src)

    def rename(self, src: str, dst: str) -> None:
        """Record file rename.

        Args:
            src: Source path
            dst: Destination path

        """
        self._raise_error_if_set()
        self.files_renamed.append((src, dst))
        self._existing_paths.discard(src)
        self._existing_paths.add(dst)

    def stat(self, path: str) -> object:
        """Get mock file status.

        Args:
            path: File path

        Returns:
            Mock stat result

        """

        DEFAULT_FILE_MODE = 0o100644

        class MockStatResult:
            def __init__(self, size) -> None:
                self.st_size = size
                self.st_mode = DEFAULT_FILE_MODE
                self.st_mtime = 0
                self.st_atime = 0
                self.st_ctime = 0

        return MockStatResult(self.getsize(path))

    def abspath(self, path: str) -> str:
        """Get absolute path.

        Args:
            path: Relative or absolute path

        Returns:
            Absolute path (mock: just prefix with /)

        """
        if path.startswith("/"):
            return path
        return "/" + path.replace("\\", "/")

    def add_existing_path(self, path: str) -> None:
        """Add a path to the mock filesystem.

        Args:
            path: Path to add

        """
        self._existing_paths.add(path)

    def add_file(self, path: str, content: str = "", size: int | None = None) -> None:
        """Add a file to the mock filesystem.

        Args:
            path: File path
            content: File content
            size: Optional explicit size

        """
        self._files[path] = content
        self._existing_paths.add(path)
        if size is not None:
            self._file_sizes[path] = size

    def add_directory(self, path: str) -> None:
        """Add a directory to the mock filesystem.

        Args:
            path: Directory path

        """
        self._directories.add(path)
        self._existing_paths.add(path)

    def add_error(self, error: Exception) -> None:
        """Add an error to be raised on next operation.

        Args:
            error: Exception to raise

        """
        self.errors.append(error)

    def reset(self) -> None:
        """Reset all tracking state."""
        self.files_copied.clear()
        self.files_copied2.clear()
        self.trees_copied.clear()
        self.directories_created.clear()
        self.files_removed.clear()
        self.directories_removed.clear()
        self.files_moved.clear()
        self.files_renamed.clear()
        self._existing_paths.clear()
        self._files.clear()
        self._directories.clear()
        self._file_sizes.clear()
        self.errors.clear()
        self._current_error_index = 0


def create_file_operations(*, mock: bool = False) -> FileOperationsProtocol:
    """Factory function to create file operations.

    Args:
        mock: If True, return MockFileOperations

    Returns:
        File operations instance

    """
    if mock:
        return MockFileOperations()
    return RealFileOperations()
