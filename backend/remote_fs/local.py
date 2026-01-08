"""
Local file system implementation (for testing and development)
"""

import os
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

    def file_exists(self, path: str) -> bool:
        """Check if file exists"""
        full_path = os.path.join(self.base_path, path)
        return os.path.exists(full_path)

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
