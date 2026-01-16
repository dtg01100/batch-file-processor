"""
Remote file system abstraction layer
Supports: Local, SMB, SFTP, FTP
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from pathlib import Path
import tempfile
import os
import logging

logger = logging.getLogger(__name__)


class RemoteFileSystem(ABC):
    """Base class for remote file system operations"""

    @abstractmethod
    def list_files(self, path: str) -> List[Dict[str, Any]]:
        """
        List files in a remote directory

        Args:
            path: Remote directory path

        Returns:
            List of file metadata dicts with keys:
                - name: File name
                - size: File size in bytes
                - modified: Last modified timestamp
        """
        pass

    @abstractmethod
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """
        Download a file from remote to local

        Args:
            remote_path: Remote file path
            local_path: Local destination path

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """
        Upload a file from local to remote

        Args:
            local_path: Local file path
            remote_path: Remote destination path

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def delete_file(self, remote_path: str) -> bool:
        """
        Delete a remote file

        Args:
            remote_path: Remote file path

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def create_directory(self, path: str) -> bool:
        """
        Create a remote directory

        Args:
            path: Remote directory path

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def delete_directory(self, path: str) -> bool:
        """
        Delete a remote directory

        Args:
            path: Remote directory path

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def upload_directory(self, local_dir: str, remote_dir: str) -> bool:
        """
        Upload an entire directory to remote system

        Args:
            local_dir: Local directory path
            remote_dir: Remote destination path

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def download_directory(self, remote_dir: str, local_dir: str) -> bool:
        """
        Download an entire directory from remote system

        Args:
            remote_dir: Remote directory path
            local_dir: Local destination path

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def get_file_hash(self, remote_path: str, hash_algorithm: str = "md5") -> str:
        """
        Get file hash for integrity verification

        Args:
            remote_path: Remote file path
            hash_algorithm: Hash algorithm (md5, sha1, sha256, etc.)

        Returns:
            File hash string
        """
        pass

    @abstractmethod
    def file_exists(self, path: str) -> bool:
        """
        Check if a file exists remotely

        Args:
            path: Remote file path

        Returns:
            True if file exists, False otherwise
        """
        pass

    @abstractmethod
    def directory_exists(self, path: str) -> bool:
        """
        Check if a directory exists remotely

        Args:
            path: Remote directory path

        Returns:
            True if directory exists, False otherwise
        """
        pass

    @abstractmethod
    def get_file_info(self, path: str) -> Dict[str, Any]:
        """
        Get file metadata

        Args:
            path: Remote file path

        Returns:
            Dict with keys: name, size, modified
        """
        pass

    def download_to_temp(self, remote_path: str) -> str:
        """
        Download a file to a temporary local location

        Args:
            remote_path: Remote file path

        Returns:
            Local temporary file path
        """
        temp_dir = tempfile.mkdtemp()
        filename = os.path.basename(remote_path)
        local_path = os.path.join(temp_dir, filename)

        if self.download_file(remote_path, local_path):
            return local_path
        else:
            raise Exception(f"Failed to download {remote_path}")

    def close(self):
        """Close connection and cleanup resources"""
        pass
