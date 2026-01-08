"""
Remote file system abstraction layer
Supports: Local, SMB, SFTP, FTP
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from pathlib import Path
import tempfile
import os


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
