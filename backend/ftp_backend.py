"""FTP backend for sending files via FTP/FTPS.

This module sends files via FTP or FTPS (FTP over TLS) with
injectable client support for testing.
"""

import ftplib
import os
import time

from backend.ftp_client import create_ftp_client
from backend.protocols import FTPClientProtocol
from core.structured_logging import (
    get_logger,
    log_backend_call,
    log_file_operation,
)

logger = get_logger(__name__)


def _ensure_remote_directory(client: FTPClientProtocol, remote_dir: str) -> None:
    """Ensure the remote directory exists, creating it if necessary.

    Args:
        client: FTP client instance
        remote_dir: Remote directory path to ensure exists

    """
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


def _try_tls_connection(
    *,
    use_tls: bool,
    process_parameters: dict,
    ftp_client: FTPClientProtocol | None,
) -> FTPClientProtocol:
    if ftp_client is not None:
        client = ftp_client
    else:
        client = create_ftp_client(use_tls=use_tls)

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
    return client


def _handle_ftp_error(
    error: Exception,
    provider_index: int,
    use_tls_options: list,
    send_file,
    logger,
) -> None:
    """Handle FTP error and determine if fallback to next TLS option is possible.

    Args:
        error: The exception that occurred
        provider_index: Index of current TLS option in use_tls_options
        use_tls_options: List of TLS options being tried
        send_file: File object to seek back to beginning for retry
        logger: Logger instance

    Raises:
        Exception: If all TLS options have been exhausted

    """
    if provider_index + 1 == len(use_tls_options):
        raise
    logger.debug("Falling back to non-TLS...")
    send_file.seek(0)


def do(
    process_parameters: dict,
    settings_dict: dict,
    filename: str,
    ftp_client: FTPClientProtocol | None = None,
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
    correlation_id = os.urandom(4).hex()

    use_tls_options = [True, False]

    log_file_operation(
        logger,
        "read",
        filename,
        file_type="edi",
        correlation_id=correlation_id,
    )

    while not file_pass:
        try:
            with open(filename, "rb") as send_file:
                filename_no_path = os.path.basename(filename)
                file_size = os.path.getsize(filename)

                for provider_index, use_tls in enumerate(use_tls_options):
                    try:
                        start_time = time.perf_counter()
                        client = _try_tls_connection(
                            use_tls=use_tls,
                            process_parameters=process_parameters,
                            ftp_client=ftp_client,
                        )
                        logger.debug("Sending File %s...", filename_no_path)

                        _ensure_remote_directory(
                            client, process_parameters["ftp_folder"]
                        )

                        client.storbinary("stor " + filename_no_path, send_file)
                        duration_ms = (time.perf_counter() - start_time) * 1000
                        logger.info("Successfully sent file %s", filename_no_path)
                        log_backend_call(
                            logger,
                            "ftp",
                            "upload",
                            endpoint=f"{process_parameters.get('ftp_server', '')}:{process_parameters.get('ftp_port', '')}/{process_parameters.get('ftp_folder', '')}",
                            success=True,
                            duration_ms=duration_ms,
                            correlation_id=correlation_id,
                        )
                        log_file_operation(
                            logger,
                            "write",
                            filename_no_path,
                            file_size=file_size,
                            file_type="edi",
                            success=True,
                            correlation_id=correlation_id,
                        )
                        file_pass = True
                        break
                    except Exception as error:
                        duration_ms = (time.perf_counter() - start_time) * 1000
                        logger.warning("FTP error: %s", error)
                        log_backend_call(
                            logger,
                            "ftp",
                            "upload",
                            endpoint=f"{process_parameters.get('ftp_server', '')}:{process_parameters.get('ftp_port', '')}",
                            success=False,
                            error=error,
                            duration_ms=duration_ms,
                            retry_count=counter,
                            correlation_id=correlation_id,
                        )
                        _handle_ftp_error(
                            error,
                            provider_index,
                            use_tls_options,
                            send_file,
                            logger,
                        )
                    finally:
                        try:
                            client.close()
                        except Exception as e:
                            logger.debug("Failed to close FTP client: %s", e)

        except Exception as ftp_error:
            if counter == 10:
                logger.error("Retried 10 times, passing exception to dispatch")
                log_backend_call(
                    logger,
                    "ftp",
                    "upload",
                    endpoint=f"{process_parameters.get('ftp_server', '')}",
                    success=False,
                    error=ftp_error,
                    retry_count=counter,
                    correlation_id=correlation_id,
                )
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

    def __init__(self, ftp_client: FTPClientProtocol | None = None) -> None:
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
    def create_client(*, use_tls: bool = False) -> FTPClientProtocol:
        """Create an FTP client.

        Args:
            use_tls: Whether to use TLS/SSL

        Returns:
            FTP client instance

        """
        return create_ftp_client(use_tls=use_tls)
