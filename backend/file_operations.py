"""File operations implementations for send backends.

This module provides real and mock file operation implementations
that conform to the FileOperationsProtocol interface.
"""

import os
import shutil
from typing import List, Optional

from backend.protocols import FileOperationsProtocol


class RealFileOperations:
    """Real file operations using shutil and os.
    
    This implementation provides actual filesystem operations
    for copying, moving, and managing files.
    """
    
    def copy(self, src: str, dst: str) -> None:
        """Copy a file.
        
        Args:
            src: Source file path
            dst: Destination file path
            
        Raises:
            FileNotFoundError: If source file doesn't exist
            PermissionError: If permission denied
        """
        shutil.copy(src, dst)
    
    def copy2(self, src: str, dst: str) -> None:
        """Copy a file with metadata preserved.
        
        Args:
            src: Source file path
            dst: Destination file path
        """
        shutil.copy2(src, dst)
    
    def copytree(self, src: str, dst: str, symlinks: bool = False) -> None:
        """Copy a directory tree.
        
        Args:
            src: Source directory path
            dst: Destination directory path
            symlinks: Whether to copy symlinks as symlinks
        """
        shutil.copytree(src, dst, symlinks=symlinks)
    
    def exists(self, path: str) -> bool:
        """Check if path exists.
        
        Args:
            path: Path to check
            
        Returns:
            True if path exists, False otherwise
        """
        return os.path.exists(path)
    
    def makedirs(self, path: str, exist_ok: bool = False) -> None:
        """Create directory and all parent directories.
        
        Args:
            path: Directory path to create
            exist_ok: If True, don't raise error if directory exists
        """
        os.makedirs(path, exist_ok=exist_ok)
    
    def remove(self, path: str) -> None:
        """Remove a file.
        
        Args:
            path: File path to remove
            
        Raises:
            FileNotFoundError: If file doesn't exist
            PermissionError: If permission denied
        """
        os.remove(path)
    
    def rmtree(self, path: str) -> None:
        """Remove directory and all contents.
        
        Args:
            path: Directory path to remove
        """
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
        return os.path.isfile(path)
    
    def isdir(self, path: str) -> bool:
        """Check if path is a directory.
        
        Args:
            path: Path to check
            
        Returns:
            True if path is a directory, False otherwise
        """
        return os.path.isdir(path)
    
    def listdir(self, path: str) -> List[str]:
        """List contents of a directory.
        
        Args:
            path: Directory path
            
        Returns:
            List of file and directory names
        """
        return os.listdir(path)
    
    def getsize(self, path: str) -> int:
        """Get file size in bytes.
        
        Args:
            path: File path
            
        Returns:
            File size in bytes
        """
        return os.path.getsize(path)
    
    def move(self, src: str, dst: str) -> None:
        """Move a file or directory.
        
        Args:
            src: Source path
            dst: Destination path
        """
        shutil.move(src, dst)
    
    def rename(self, src: str, dst: str) -> None:
        """Rename a file or directory.
        
        Args:
            src: Source path
            dst: Destination path
        """
        os.rename(src, dst)
    
    def stat(self, path: str) -> os.stat_result:
        """Get file status.
        
        Args:
            path: File path
            
        Returns:
            stat_result object
        """
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
    
    def __init__(self):
        """Initialize mock file operations with empty tracking state."""
        self.files_copied: List[tuple] = []
        self.files_copied2: List[tuple] = []
        self.trees_copied: List[tuple] = []
        self.directories_created: List[tuple] = []
        self.files_removed: List[str] = []
        self.directories_removed: List[str] = []
        self.files_moved: List[tuple] = []
        self.files_renamed: List[tuple] = []
        self._existing_paths: set = set()
        self._files: dict = {}  # path -> content
        self._directories: set = set()
        self._file_sizes: dict = {}
        self.errors: List[Exception] = []
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
    
    def copytree(self, src: str, dst: str, symlinks: bool = False) -> None:
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
    
    def makedirs(self, path: str, exist_ok: bool = False) -> None:
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
        # Simple implementation - split on /
        parts = path.replace('\\', '/').split('/')
        return parts[-1] if parts else ''
    
    def dirname(self, path: str) -> str:
        """Get directory name of path.
        
        Args:
            path: File path
            
        Returns:
            Directory name of path
        """
        # Simple implementation - split on /
        parts = path.replace('\\', '/').split('/')
        if len(parts) > 1:
            return '/'.join(parts[:-1])
        return ''
    
    def join(self, *paths: str) -> str:
        """Join path components.
        
        Args:
            *paths: Path components to join
            
        Returns:
            Joined path
        """
        return '/'.join(paths)
    
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
    
    def listdir(self, path: str) -> List[str]:
        """List contents of a directory.
        
        Args:
            path: Directory path
            
        Returns:
            List of file and directory names
        """
        # Return files that are direct children of this path
        results = []
        for file_path in self._files:
            if file_path.startswith(path + '/'):
                remaining = file_path[len(path) + 1:]
                if '/' not in remaining:
                    results.append(remaining)
        return results
    
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
            return len(content.encode('utf-8'))
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
        class MockStatResult:
            def __init__(self, size):
                self.st_size = size
                self.st_mode = 0o100644  # Regular file
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
        if path.startswith('/'):
            return path
        return '/' + path
    
    def add_existing_path(self, path: str) -> None:
        """Add a path to the mock filesystem.
        
        Args:
            path: Path to add
        """
        self._existing_paths.add(path)
    
    def add_file(self, path: str, content: str = '', size: Optional[int] = None) -> None:
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


def create_file_operations(mock: bool = False) -> FileOperationsProtocol:
    """Factory function to create file operations.
    
    Args:
        mock: If True, return MockFileOperations
        
    Returns:
        File operations instance
    """
    if mock:
        return MockFileOperations()
    return RealFileOperations()
