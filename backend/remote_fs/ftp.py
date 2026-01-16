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

    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """Upload file to FTP server"""
        self._connect()

        try:
            with open(local_path, "rb") as f:
                self.ftp.storbinary(f"STOR {remote_path}", f)
            logger.info(f"Uploaded FTP file: {remote_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload FTP file: {e}")
            return False

    def delete_file(self, remote_path: str) -> bool:
        """Delete file from FTP server"""
        self._connect()

        try:
            self.ftp.delete(remote_path)
            logger.info(f"Deleted FTP file: {remote_path}")
            return True
        except Exception:
            return False

    def create_directory(self, path: str) -> bool:
        """Create directory on FTP server"""
        self._connect()

        try:
            self.ftp.mkd(path)
            logger.info(f"Created FTP directory: {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create FTP directory: {e}")
            return False

    def delete_directory(self, path: str) -> bool:
        """Delete directory from FTP server"""
        self._connect()

        try:
            self.ftp.rmd(path)
            logger.info(f"Deleted FTP directory: {path}")
            return True
        except Exception:
            return False

    def upload_directory(self, local_dir: str, remote_dir: str) -> bool:
        """Upload entire directory to FTP server"""
        self._connect()

        try:
            # Create remote directory if it doesn't exist
            try:
                self.ftp.cwd(remote_dir)
            except Exception:
                self.ftp.mkd(remote_dir)
                self.ftp.cwd(remote_dir)

            for root, dirs, files in os.walk(local_dir):
                # Create remote subdirectories
                relative_path = os.path.relpath(root, local_dir)
                if relative_path != ".":
                    try:
                        self.ftp.cwd(relative_path)
                    except Exception:
                        self.ftp.mkd(relative_path)
                        self.ftp.cwd(relative_path)

                # Upload files
                for filename in files:
                    local_path = os.path.join(root, filename)
                    remote_path = filename
                    with open(local_path, "rb") as f:
                        self.ftp.storbinary(f"STOR {remote_path}", f)

                # Go back to remote directory
                if relative_path != ".":
                    self.ftp.cwd("..")
            
            logger.info(f"Uploaded FTP directory: {local_dir} to {remote_dir}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload FTP directory: {e}")
            return False

    def download_directory(self, remote_dir: str, local_dir: str) -> bool:
        """Download entire directory from FTP server"""
        self._connect()

        try:
            os.makedirs(local_dir, exist_ok=True)
            self.ftp.cwd(remote_dir)
            
            # List all items in directory
            file_list = self.ftp.nlst()
            
            for filename in file_list:
                remote_path = os.path.join(remote_dir, filename).replace("\\", "/")
                local_path = os.path.join(local_dir, filename)
                
                try:
                    # Try to change to directory (if it's a directory)
                    self.ftp.cwd(filename)
                    self.ftp.cwd("..")  # Go back
                    # It's a directory, download recursively
                    self.download_directory(remote_path, local_path)
                except Exception:
                    # It's a file, download it
                    with open(local_path, "wb") as f:
                        self.ftp.retrbinary(f"RETR {remote_path}", f.write)
            
            logger.info(f"Downloaded FTP directory: {remote_dir} to {local_dir}")
            return True
        except Exception as e:
            logger.error(f"Failed to download FTP directory: {e}")
            return False

    def get_file_hash(self, remote_path: str, hash_algorithm: str = "md5") -> str:
        """Get file hash for integrity verification"""
        self._connect()

        try:
            import hashlib
            hash_func = hashlib.new(hash_algorithm)
            
            # Download file in chunks to compute hash
            def callback(data):
                hash_func.update(data)
            
            self.ftp.retrbinary(f"RETR {remote_path}", callback)
            return hash_func.hexdigest()
        except Exception as e:
            logger.error(f"Failed to compute FTP file hash: {e}")
            raise Exception(f"Failed to get file hash: {e}")

    def directory_exists(self, path: str) -> bool:
        """Check if directory exists on FTP server"""
        self._connect()

        try:
            original_dir = self.ftp.pwd()
            self.ftp.cwd(path)
            self.ftp.cwd(original_dir)
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
