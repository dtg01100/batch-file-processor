"""
SFTP (SSH) file system implementation
"""

from typing import List, Dict, Any
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)

try:
    import paramiko

    SFTP_AVAILABLE = True
except ImportError:
    SFTP_AVAILABLE = False
    logger.warning("paramiko not available, install with: pip install paramiko")

from .base import RemoteFileSystem


class SFTPFileSystem(RemoteFileSystem):
    """SFTP (SSH) file system implementation"""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 22,
        private_key_path: str | None = None,
    ):
        """
        Initialize SFTP file system

        Args:
            host: SFTP server hostname or IP
            username: SFTP username
            password: SFTP password (or None if using key auth)
            port: SFTP port (default: 22)
            private_key_path: Path to private SSH key (optional)
        """
        if not SFTP_AVAILABLE:
            raise Exception("paramiko not installed")

        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.private_key_path = private_key_path
        self.ssh_client = None
        self.sftp = None

    def _connect(self):
        """Establish SFTP connection"""
        if self.sftp is None:
            try:
                self.ssh_client = paramiko.SSHClient()
                self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                # Authenticate with password or key
                if self.private_key_path:
                    private_key = paramiko.RSAKey.from_private_key_file(
                        self.private_key_path
                    )
                    self.ssh_client.connect(
                        self.host,
                        port=self.port,
                        username=self.username,
                        pkey=private_key,
                    )
                else:
                    self.ssh_client.connect(
                        self.host,
                        port=self.port,
                        username=self.username,
                        password=self.password,
                    )

                self.sftp = self.ssh_client.open_sftp()
                logger.info(f"Connected to SFTP server: {self.host}")

            except Exception as e:
                logger.error(f"SFTP connection failed: {e}")
                raise Exception(f"Failed to connect to SFTP server: {e}")

    def list_files(self, path: str) -> List[Dict[str, Any]]:
        """List files in SFTP directory"""
        self._connect()

        files = []
        try:
            attrs = self.sftp.listdir_attr(path)

            for attr in attrs:
                if not attr.filename.startswith("."):
                    files.append(
                        {
                            "name": attr.filename,
                            "size": attr.st_size,
                            "modified": datetime.fromtimestamp(attr.st_mtime),
                        }
                    )
        except Exception as e:
            logger.error(f"Failed to list SFTP files: {e}")

        return files

    def download_file(self, remote_path: str, local_path: str) -> bool:
        """Download file from SFTP server"""
        self._connect()

        try:
            self.sftp.get(remote_path, local_path)
            logger.info(f"Downloaded SFTP file: {remote_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to download SFTP file: {e}")
            return False

    def file_exists(self, path: str) -> bool:
        """Check if file exists in SFTP server"""
        self._connect()

        try:
            self.sftp.stat(path)
            return True
        except FileNotFoundError:
            return False
        except Exception as e:
            logger.error(f"Error checking SFTP file existence: {e}")
            return False

    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """Upload file to SFTP server"""
        self._connect()

        try:
            self.sftp.put(local_path, remote_path)
            logger.info(f"Uploaded SFTP file: {remote_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload SFTP file: {e}")
            return False

    def delete_file(self, remote_path: str) -> bool:
        """Delete file from SFTP server"""
        self._connect()

        try:
            self.sftp.remove(remote_path)
            logger.info(f"Deleted SFTP file: {remote_path}")
            return True
        except FileNotFoundError:
            return False
        except Exception as e:
            logger.error(f"Failed to delete SFTP file: {e}")
            return False

    def create_directory(self, path: str) -> bool:
        """Create directory on SFTP server"""
        self._connect()

        try:
            self.sftp.mkdir(path)
            logger.info(f"Created SFTP directory: {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create SFTP directory: {e}")
            return False

    def delete_directory(self, path: str) -> bool:
        """Delete directory from SFTP server"""
        self._connect()

        try:
            self.sftp.rmdir(path)
            logger.info(f"Deleted SFTP directory: {path}")
            return True
        except FileNotFoundError:
            return False
        except Exception as e:
            logger.error(f"Failed to delete SFTP directory: {e}")
            return False

    def upload_directory(self, local_dir: str, remote_dir: str) -> bool:
        """Upload entire directory to SFTP server"""
        self._connect()

        try:
            # Create remote directory if it doesn't exist
            try:
                self.sftp.stat(remote_dir)
            except FileNotFoundError:
                self.sftp.mkdir(remote_dir)

            for root, dirs, files in os.walk(local_dir):
                # Create remote subdirectories
                relative_path = os.path.relpath(root, local_dir)
                remote_subdir = os.path.join(remote_dir, relative_path).replace("\\", "/")
                
                if remote_subdir != remote_dir:
                    try:
                        self.sftp.stat(remote_subdir)
                    except FileNotFoundError:
                        self.sftp.mkdir(remote_subdir)

                # Upload files
                for filename in files:
                    local_path = os.path.join(root, filename)
                    remote_path = os.path.join(remote_subdir, filename).replace("\\", "/")
                    self.sftp.put(local_path, remote_path)
            
            logger.info(f"Uploaded SFTP directory: {local_dir} to {remote_dir}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload SFTP directory: {e}")
            return False

    def download_directory(self, remote_dir: str, local_dir: str) -> bool:
        """Download entire directory from SFTP server"""
        self._connect()

        try:
            os.makedirs(local_dir, exist_ok=True)
            
            for item in self.sftp.listdir_attr(remote_dir):
                remote_path = os.path.join(remote_dir, item.filename).replace("\\", "/")
                local_path = os.path.join(local_dir, item.filename)
                
                if item.st_mode & 0o040000:  # It's a directory
                    os.makedirs(local_path, exist_ok=True)
                    self.download_directory(remote_path, local_path)
                else:  # It's a file
                    self.sftp.get(remote_path, local_path)
            
            logger.info(f"Downloaded SFTP directory: {remote_dir} to {local_dir}")
            return True
        except Exception as e:
            logger.error(f"Failed to download SFTP directory: {e}")
            return False

    def get_file_hash(self, remote_path: str, hash_algorithm: str = "md5") -> str:
        """Get file hash for integrity verification"""
        self._connect()

        try:
            import hashlib
            hash_func = hashlib.new(hash_algorithm)
            
            with self.sftp.open(remote_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_func.update(chunk)
            
            return hash_func.hexdigest()
        except Exception as e:
            logger.error(f"Failed to compute SFTP file hash: {e}")
            raise Exception(f"Failed to get file hash: {e}")

    def directory_exists(self, path: str) -> bool:
        """Check if directory exists on SFTP server"""
        self._connect()

        try:
            attr = self.sftp.stat(path)
            return attr.st_mode & 0o040000  # Check if it's a directory
        except FileNotFoundError:
            return False
        except Exception as e:
            logger.error(f"Error checking SFTP directory existence: {e}")
            return False

    def get_file_info(self, path: str) -> Dict[str, Any]:
        """Get file metadata from SFTP server"""
        self._connect()

        try:
            attr = self.sftp.stat(path)
            return {
                "name": path.split("/")[-1],
                "size": attr.st_size,
                "modified": datetime.fromtimestamp(attr.st_mtime),
            }
        except Exception as e:
            logger.error(f"Failed to get SFTP file info: {e}")
            raise Exception(f"Failed to get file info: {e}")

    def close(self):
        """Close SFTP connection"""
        if self.sftp:
            try:
                self.sftp.close()
                self.sftp = None
            except Exception as e:
                logger.error(f"Error closing SFTP: {e}")

        if self.ssh_client:
            try:
                self.ssh_client.close()
                self.ssh_client = None
            except Exception as e:
                logger.error(f"Error closing SSH client: {e}")
