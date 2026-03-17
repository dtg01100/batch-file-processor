"""FTP backend for sending files via FTP/FTPS.

This module sends files via FTP or FTPS (FTP over TLS) with
injectable client support for testing.
"""

import logging
import os
import time
from typing import Optional

from backend.ftp_client import create_ftp_client
from backend.protocols import FTPClientProtocol

logger = logging.getLogger(__name__)


def do(
    process_parameters: dict,
    settings_dict: dict,
    filename: str,
    ftp_client: Optional[FTPClientProtocol] = None,
) -> bool:
    """Send a file via FTP/FTPS.

    Args:
        process_parameters: Dictionary containing FTP connection parameters:
            - ftp_server: FTP server hostname
            - ftp_port: FTP server port
            - ftp_username: FTP username
            - ftp_password: FTP password
            - ftp_folder: Remote directory path
        settings_dict: Settings dictionary (not used by FTP backend)
        filename: Local file path to send
        ftp_client: Optional injectable FTP client for testing.
                   If None, creates real FTP clients.

    Returns:
        True if file was sent successfully

    Raises:
        Exception: If file cannot be sent after 10 retries
    """
    file_pass = False
    counter = 0

    # Try TLS first, then fall back to non-TLS
    use_tls_options = [True, False]

    while not file_pass:
        try:
            with open(filename, "rb") as send_file:
                filename_no_path = os.path.basename(filename)

                for provider_index, use_tls in enumerate(use_tls_options):
                    # Create client - either injected or real
                    if ftp_client is not None:
                        client = ftp_client
                    else:
                        client = create_ftp_client(use_tls=use_tls)

                    try:
                        logger.debug(
                            "Connecting to ftp server: %s",
                            process_parameters["ftp_server"],
                        )
                        client.connect(
                            str(process_parameters["ftp_server"]),
                            process_parameters["ftp_port"],
                        )
                        logger.debug(
                            "Logging in to %s", process_parameters["ftp_server"]
                        )
                        client.login(
                            process_parameters["ftp_username"],
                            process_parameters["ftp_password"],
                        )
                        logger.debug("Sending File %s...", filename_no_path)

                        # Ensure remote directory exists
                        remote_dir = process_parameters["ftp_folder"]
                        if remote_dir and remote_dir != "/":
                            # Normalize path separators and remove leading/trailing slashes for processing
                            path_parts = [
                                part
                                for part in remote_dir.replace("\\", "/")
                                .strip("/")
                                .split("/")
                                if part
                            ]
                            current_path = ""

                            for part in path_parts:
                                current_path += "/" + part
                                try:
                                    client.cwd(current_path)
                                except Exception:
                                    # Directory doesn't exist, create it
                                    client.mkd(current_path)
                                    client.cwd(current_path)

                        client.storbinary("stor " + filename_no_path, send_file)
                        logger.info("Successfully sent file %s", filename_no_path)
                        file_pass = True
                        break
                    except Exception as error:
                        logger.warning("FTP error: %s", error)
                        if provider_index + 1 == len(use_tls_options):
                            raise
                        logger.debug("Falling back to non-TLS...")
                        # Reset file pointer for retry
                        send_file.seek(0)
                    finally:
                        try:
                            client.close()
                        except Exception:
                            pass

        except Exception as ftp_error:
            if counter == 10:
                logger.error("Retried 10 times, passing exception to dispatch")
                raise
            counter += 1
            logger.warning(
                "Encountered an error. Retry number %d: %s", counter, ftp_error
            )
            time.sleep(2)

    return file_pass


class FTPBackend:
    """FTP backend class for object-oriented usage.

    Provides an object-oriented interface to the FTP backend
    with injectable client support.

    Attributes:
        ftp_client: FTP client instance (injectable for testing)
    """

    def __init__(self, ftp_client: Optional[FTPClientProtocol] = None):
        """Initialize FTP backend.

        Args:
            ftp_client: Optional injectable FTP client for testing.
        """
        self.ftp_client = ftp_client

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
        return do(process_parameters, settings_dict, filename, self.ftp_client)

    @staticmethod
    def create_client(use_tls: bool = False) -> FTPClientProtocol:
        """Create an FTP client.

        Args:
            use_tls: Whether to use TLS/SSL

        Returns:
            FTP client instance
        """
        return create_ftp_client(use_tls=use_tls)
