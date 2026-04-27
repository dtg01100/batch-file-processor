"""FTP backend for sending files via FTP/FTPS.

This module sends files via FTP or FTPS (FTP over TLS) with
injectable client support for testing.
"""

import ftplib
import os
from typing import Any

from backend.backend_base import BackendBase
from backend.ftp_client import create_ftp_client
from backend.protocols import FTPClientProtocol
from core.structured_logging import get_logger, log_file_operation

logger = get_logger(__name__)


def _is_valid_ftp_path(path: str) -> bool:
    """Validate FTP path for security issues.

    Args:
        path: Path to validate

    Returns:
        True if path is safe for FTP operations
    """
    if not path:
        return False
    if ".." in path:
        return False
    return True


def _ensure_remote_directory(client: FTPClientProtocol, remote_dir: str) -> None:
    """Ensure the remote directory exists, creating it if necessary.

    Args:
        client: FTP client instance
        remote_dir: Remote directory path to ensure exists

    Raises:
        ValueError: If remote_dir is invalid or contains path traversal

    """
    if not _is_valid_ftp_path(remote_dir):
        raise ValueError(f"Invalid FTP folder path: {remote_dir}")

    if remote_dir and remote_dir != "/":
        path_parts = [
            part for part in remote_dir.replace("\\", "/").strip("/").split("/") if part
        ]

        current_path = ""
        for part in path_parts:
            current_path += "/" + part
            try:
                client.cwd(current_path)
            except (ftplib.error_perm, ftplib.error_temp, OSError):
                client.mkd(current_path)
                client.cwd(current_path)


def do(
    process_parameters: dict,
    settings_dict: dict,
    filename: str,
    ftp_client: FTPClientProtocol | None = None,
    disable_retry: bool = False,
) -> bool:
    """Send a file via FTP/FTPS.

    Args:
        process_parameters: Dictionary containing FTP connection parameters
        settings_dict: Settings dictionary (not used by FTP backend)
        filename: Local file path to send
        ftp_client: Optional injectable FTP client for testing
        disable_retry: If True, skip retry logic (for faster tests)

    Returns:
        True if file was sent successfully

    Raises:
        Exception: If file cannot be sent after 10 retries

    """
    backend = FTPBackend(ftp_client=ftp_client, disable_retry=disable_retry)
    return backend.send(process_parameters, settings_dict, filename)


class FTPBackend(BackendBase):
    """FTP backend class for object-oriented usage.

    Provides an object-oriented interface to the FTP backend
    with injectable client support.
    """

    def __init__(
        self, ftp_client: FTPClientProtocol | None = None, disable_retry: bool = False
    ) -> None:
        """Initialize FTP backend.

        Args:
            ftp_client: Optional injectable FTP client for testing.
            disable_retry: If True, skip retry logic (for testing)

        """
        super().__init__(disable_retry=disable_retry)
        self.ftp_client = ftp_client
        self._client = None
        self._use_tls_options = [False, True]
        self._current_tls_index = 0

    def _execute(
        self,
        process_parameters: dict,
        settings: dict,
        filename: str,
        **kwargs: Any,
    ) -> bool:
        """Send file via FTP/FTPS.

        Args:
            process_parameters: FTP connection parameters
            settings_dict: Settings dictionary
            filename: File to send

        Returns:
            True if file was sent successfully

        """
        filename_no_path = os.path.basename(filename)
        file_size = os.path.getsize(filename)

        # Use injected client or create default
        if self.ftp_client is not None:
            self._client = self.ftp_client
            # If client is injected, use it directly (for testing)
            return self._send_file(
                process_parameters, filename, filename_no_path, file_size
            )

        # Try TLS options in order (only for real clients)
        last_error = None
        for use_tls in self._use_tls_options:
            try:
                self._client = create_ftp_client(use_tls=use_tls)
                return self._send_file(
                    process_parameters, filename, filename_no_path, file_size
                )
            except Exception as error:
                last_error = error
                logger.debug(
                    "FTP %s connection failed, trying next option",
                    "TLS" if use_tls else "plain",
                )
                self._cleanup()

        # All TLS options failed
        if last_error:
            raise last_error
        return False

    def _send_file(
        self,
        process_parameters: dict,
        filename: str,
        filename_no_path: str,
        file_size: int,
    ) -> bool:
        """Perform the actual file send operation.

        Args:
            process_parameters: FTP connection parameters
            filename: Full path to file to send
            filename_no_path: Basename of file to send
            file_size: Size of file in bytes

        Returns:
            True if successful

        """
        client = self._client
        assert client is not None, "FTP client must be set before calling _send_file"

        logger.debug(
            "Connecting to ftp server: %s",
            process_parameters["ftp_server"],
        )
        client.connect(
            str(process_parameters["ftp_server"]),
            process_parameters["ftp_port"],
        )
        logger.debug("Logging in to %s", process_parameters["ftp_server"])
        client.login(
            process_parameters["ftp_username"],
            process_parameters["ftp_password"],
        )

        logger.debug("Sending File %s...", filename_no_path)

        _ensure_remote_directory(client, process_parameters["ftp_folder"])

        safe_filename = os.path.basename(filename_no_path)
        if not safe_filename or safe_filename.startswith("."):
            raise ValueError(f"Invalid filename for FTP upload: {filename_no_path}")

        with open(filename, "rb") as send_file:
            client.storbinary("stor " + safe_filename, send_file)

        logger.info("Successfully sent file %s", filename_no_path)
        log_file_operation(
            logger,
            "write",
            filename_no_path,
            file_size=file_size,
            file_type="edi",
            success=True,
            correlation_id=self._correlation_id,
        )
        return True

    def _get_backend_name(self) -> str:
        """Get backend name for logging."""
        return "ftp"

    def _get_endpoint(self, process_parameters: dict, settings: dict) -> str:
        """Get FTP endpoint for logging."""
        del settings  # unused, kept for base class interface
        server = process_parameters.get("ftp_server", "")
        port = process_parameters.get("ftp_port", "")
        folder = process_parameters.get("ftp_folder", "")
        return f"{server}:{port}/{folder}"

    def _cleanup(self) -> None:
        """Close FTP connection."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception as e:
                logger.debug("Failed to close FTP client: %s", e)

    def _prepare_for_retry(
        self,
        process_parameters: dict,
        settings: dict,
        filename: str,
        **kwargs: Any,
    ) -> None:
        """Prepare for retry by resetting state."""
        del process_parameters, settings, filename, kwargs  # unused
        self._client = None

    def send(
        self, process_parameters: dict, settings_dict: dict, filename: str
    ) -> bool:
        """Send a file via FTP.

        Args:
            process_parameters: FTP connection parameters
            settings_dict: Settings dictionary
            filename: File to send

        Returns:
            True if successful

        """
        try:
            return self.execute(process_parameters, settings_dict, filename)
        finally:
            self._cleanup()

    @staticmethod
    def create_client(*, use_tls: bool = False) -> FTPClientProtocol:
        """Create an FTP client.

        Args:
            use_tls: Whether to use TLS/SSL

        Returns:
            FTP client instance

        """
        return create_ftp_client(use_tls=use_tls)
