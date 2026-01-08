"""
FTP file system implementation
"""

from typing import List, Dict, Any
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)

try:
    from ftplib import FTP, FTP_TLS

    FTP_AVAILABLE = True
except ImportError:
    FTP_AVAILABLE = False

from .base import RemoteFileSystem


class FTPFileSystem(RemoteFileSystem):
    """FTP file system implementation"""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 21,
        use_tls: bool = True,
    ):
        """
        Initialize FTP file system

        Args:
            host: FTP server hostname or IP
            username: FTP username
            password: FTP password
            port: FTP port (default: 21)
            use_tls: Use FTP over TLS (default: True)
        """
        if not FTP_AVAILABLE:
            raise Exception("ftplib not available")

        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.use_tls = use_tls
        self.ftp = None

    def _connect(self):
        """Establish FTP connection"""
        if self.ftp is None:
            try:
                # Try FTP_TLS first, fallback to FTP
                ftp_providers = [FTP_TLS, FTP] if self.use_tls else [FTP]

                for provider in ftp_providers:
                    try:
                        self.ftp = provider()
                        self.ftp.connect(self.host, self.port)
                        self.ftp.login(self.username, self.password)
                        logger.info(f"Connected to FTP server: {self.host}")
                        break
                    except Exception:
                        if provider != ftp_providers[-1]:
                            logger.info(f"Falling back to non-TLS...")
                            continue
                        else:
                            raise

            except Exception as e:
                logger.error(f"FTP connection failed: {e}")
                raise Exception(f"Failed to connect to FTP server: {e}")

    def list_files(self, path: str) -> List[Dict[str, Any]]:
        """List files in FTP directory"""
        self._connect()

        files = []
        try:
            # Change to directory
            self.ftp.cwd(path)

            # List files
            file_list = self.ftp.nlst()

            for filename in file_list:
                # Get file size and modification time
                try:
                    size = self.ftp.size(filename)
                    # Note: FTP doesn't reliably provide modification time
                    # without using MDTM command which varies by server
                    files.append(
                        {
                            "name": filename,
                            "size": size,
                            "modified": datetime.now(),  # Approximate
                        }
                    )
                except Exception as e:
                    logger.warning(f"Could not get info for {filename}: {e}")

        except Exception as e:
            logger.error(f"Failed to list FTP files: {e}")

        return files

    def download_file(self, remote_path: str, local_path: str) -> bool:
        """Download file from FTP server"""
        self._connect()

        try:
            with open(local_path, "wb") as f:
                self.ftp.retrbinary(f"RETR {remote_path}", f.write)
            logger.info(f"Downloaded FTP file: {remote_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to download FTP file: {e}")
            return False

    def file_exists(self, path: str) -> bool:
        """Check if file exists in FTP server"""
        self._connect()

        try:
            # Try to get file size
            self.ftp.size(path)
            return True
        except Exception:
            return False

    def get_file_info(self, path: str) -> Dict[str, Any]:
        """Get file metadata from FTP server"""
        self._connect()

        try:
            size = self.ftp.size(path)
            return {
                "name": os.path.basename(path),
                "size": size,
                "modified": datetime.now(),  # Approximate
            }
        except Exception as e:
            logger.error(f"Failed to get FTP file info: {e}")
            raise Exception(f"Failed to get file info: {e}")

    def close(self):
        """Close FTP connection"""
        if self.ftp:
            try:
                self.ftp.quit()
                self.ftp = None
            except Exception as e:
                logger.error(f"Error closing FTP connection: {e}")
