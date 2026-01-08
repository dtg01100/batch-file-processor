"""
SFTP (SSH) file system implementation
"""

from typing import List, Dict, Any
from datetime import datetime
import logging

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
        private_key_path: str = None,
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
