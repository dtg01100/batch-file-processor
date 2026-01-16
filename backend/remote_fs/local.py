"""
Local file system implementation (for testing and development)
"""

import os
import hashlib
from typing import List, Dict, Any
from datetime import datetime
from .base import RemoteFileSystem


class LocalFileSystem(RemoteFileSystem):
    """Local file system implementation"""

    def __init__(self, base_path: str):
        """
        Initialize local file system

        Args:
            base_path: Base directory path
        """
        self.base_path = base_path
        if not os.path.exists(base_path):
            raise Exception(f"Base path does not exist: {base_path}")

    def list_files(self, path: str) -> List[Dict[str, Any]]:
        """List files in directory"""
        full_path = os.path.join(self.base_path, path)
        files = []

        if not os.path.exists(full_path):
            return files

        for item in os.listdir(full_path):
            item_path = os.path.join(full_path, item)
            if os.path.isfile(item_path):
                stat = os.stat(item_path)
                files.append(
                    {
                        "name": item,
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime),
                    }
                )

        return files

    def download_file(self, remote_path: str, local_path: str) -> bool:
        """Copy file from remote (local source) to local destination"""
        source_path = os.path.join(self.base_path, remote_path)

        if not os.path.exists(source_path):
            return False

        try:
            import shutil

            shutil.copy2(source_path, local_path)
            return True
        except Exception as e:
            print(f"Error copying file: {e}")
            return False

    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """Upload file from local to remote (local destination)"""
        destination_path = os.path.join(self.base_path, remote_path)
        destination_dir = os.path.dirname(destination_path)

        try:
            import shutil
            os.makedirs(destination_dir, exist_ok=True)
            shutil.copy2(local_path, destination_path)
            return True
        except Exception as e:
            print(f"Error uploading file: {e}")
            return False

    def delete_file(self, remote_path: str) -> bool:
        """Delete remote file"""
        full_path = os.path.join(self.base_path, remote_path)

        if not os.path.exists(full_path):
            return False

        try:
            os.remove(full_path)
            return True
        except Exception as e:
            print(f"Error deleting file: {e}")
            return False

    def create_directory(self, path: str) -> bool:
        """Create remote directory"""
        full_path = os.path.join(self.base_path, path)

        try:
            os.makedirs(full_path, exist_ok=True)
            return True
        except Exception as e:
            print(f"Error creating directory: {e}")
            return False

    def delete_directory(self, path: str) -> bool:
        """Delete remote directory"""
        full_path = os.path.join(self.base_path, path)

        if not os.path.exists(full_path):
            return False

        try:
            import shutil
            shutil.rmtree(full_path)
            return True
        except Exception as e:
            print(f"Error deleting directory: {e}")
            return False

    def upload_directory(self, local_dir: str, remote_dir: str) -> bool:
        """Upload entire directory to remote"""
        destination_path = os.path.join(self.base_path, remote_dir)

        try:
            import shutil
            shutil.copytree(local_dir, destination_path, dirs_exist_ok=True)
            return True
        except Exception as e:
            print(f"Error uploading directory: {e}")
            return False

    def download_directory(self, remote_dir: str, local_dir: str) -> bool:
        """Download entire directory from remote"""
        source_path = os.path.join(self.base_path, remote_dir)

        if not os.path.exists(source_path):
            return False

        try:
            import shutil
            shutil.copytree(source_path, local_dir, dirs_exist_ok=True)
            return True
        except Exception as e:
            print(f"Error downloading directory: {e}")
            return False

    def get_file_hash(self, remote_path: str, hash_algorithm: str = "md5") -> str:
        """Get file hash for integrity verification"""
        full_path = os.path.join(self.base_path, remote_path)

        if not os.path.exists(full_path):
            raise Exception(f"File not found: {remote_path}")

        try:
            hash_func = hashlib.new(hash_algorithm)
            with open(full_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_func.update(chunk)
            return hash_func.hexdigest()
        except Exception as e:
            raise Exception(f"Error computing file hash: {e}")

    def file_exists(self, path: str) -> bool:
        """Check if file exists"""
        full_path = os.path.join(self.base_path, path)
        return os.path.exists(full_path)

    def directory_exists(self, path: str) -> bool:
        """Check if directory exists"""
        full_path = os.path.join(self.base_path, path)
        return os.path.isdir(full_path)

    def get_file_info(self, path: str) -> Dict[str, Any]:
        """Get file metadata"""
        full_path = os.path.join(self.base_path, path)

        if not os.path.exists(full_path):
            raise Exception(f"File not found: {path}")

        stat = os.stat(full_path)
        return {
            "name": os.path.basename(path),
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime),
        }
