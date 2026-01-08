"""
Factory for creating remote file system instances
"""

import logging
from typing import Dict, Any
from .base import RemoteFileSystem
from .local import LocalFileSystem
from .smb import SMBFileSystem
from .sftp import SFTPFileSystem
from .ftp import FTPFileSystem

logger = logging.getLogger(__name__)


def create_file_system(
    connection_type: str, params: Dict[str, Any]
) -> RemoteFileSystem:
    """
    Factory function to create file system instances

    Args:
        connection_type: Type of connection (local, smb, sftp, ftp)
        params: Connection parameters (host, username, password, etc.)

    Returns:
        RemoteFileSystem instance

    Raises:
        Exception: If connection type is invalid or parameters are missing
    """
    connection_type = connection_type.lower()

    if connection_type == "local":
        return LocalFileSystem(base_path=params.get("path", "."))

    elif connection_type == "smb":
        required_params = ["host", "username", "password", "share"]
        for param in required_params:
            if param not in params:
                raise Exception(f"Missing required parameter: {param}")

        return SMBFileSystem(
            host=params["host"],
            username=params["username"],
            password=params["password"],
            share=params["share"],
            port=params.get("port", 445),
        )

    elif connection_type == "sftp":
        required_params = ["host", "username", "password"]
        for param in required_params:
            if param not in params:
                raise Exception(f"Missing required parameter: {param}")

        return SFTPFileSystem(
            host=params["host"],
            username=params["username"],
            password=params["password"],
            port=params.get("port", 22),
            private_key_path=params.get("private_key_path"),
        )

    elif connection_type == "ftp":
        required_params = ["host", "username", "password"]
        for param in required_params:
            if param not in params:
                raise Exception(f"Missing required parameter: {param}")

        return FTPFileSystem(
            host=params["host"],
            username=params["username"],
            password=params["password"],
            port=params.get("port", 21),
            use_tls=params.get("use_tls", True),
        )

    else:
        raise Exception(f"Invalid connection type: {connection_type}")
