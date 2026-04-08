"""FTP client implementations for send backends.

This module provides real and mock FTP client implementations
that conform to the FTPClientProtocol interface.
"""

import ftplib
import time
from typing import Any

from backend.protocols import FTPClientProtocol
from core.constants import FTP_TIMEOUT_SECONDS
from core.structured_logging import (
    get_logger,
    get_or_create_correlation_id,
    log_backend_call,
)

logger = get_logger(__name__)


class RealFTPClient:
    """Real FTP client using ftplib.

    This implementation wraps ftplib.FTP or ftplib.FTP_TLS
    for actual FTP connections.

    Attributes:
        use_tls: Whether to use TLS/SSL for the connection
        _connection: The underlying ftplib connection object

    """

    def __init__(self, *, use_tls: bool = False) -> None:
        """Initialize FTP client.

        Args:
            use_tls: If True, use FTP_TLS for secure connections

        """
        self.use_tls = use_tls
        self._connection: ftplib.FTP | ftplib.FTP_TLS | None = None

    def connect(self, host: str, port: int, timeout: float | None = None) -> None:
        """Connect to FTP server.

        Args:
            host: Server hostname or IP address
            port: Server port number
            timeout: Optional connection timeout in seconds

        """
        get_or_create_correlation_id()
        start_time = time.perf_counter()
        endpoint = f"{host}:{port}"
        logger.debug("FTP connecting to %s (TLS=%s)", endpoint, self.use_tls)
        log_backend_call(logger, "ftp", "connect", endpoint=endpoint, success=None)

        try:
            if self.use_tls:
                self._connection = ftplib.FTP_TLS()
            else:
                self._connection = ftplib.FTP()

            if timeout is not None:
                self._connection.connect(host, port, timeout)
            else:
                self._connection.connect(host, port, FTP_TIMEOUT_SECONDS)

            duration_ms = (time.perf_counter() - start_time) * 1000
            log_backend_call(
                logger,
                "ftp",
                "connect",
                endpoint=endpoint,
                success=True,
                duration_ms=duration_ms,
            )
            logger.debug("FTP connected to %s", endpoint)
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            log_backend_call(
                logger,
                "ftp",
                "connect",
                endpoint=endpoint,
                success=False,
                error=e,
                duration_ms=duration_ms,
            )
            raise

    def login(self, user: str, password: str) -> None:
        """Authenticate with FTP server.

        Args:
            user: Username for authentication
            password: Password for authentication

        Raises:
            ftplib.error_perm: If authentication fails

        """
        if self._connection is None:
            raise RuntimeError("Not connected to FTP server")
        start_time = time.perf_counter()
        logger.debug("FTP logging in as user: %s", user)
        log_backend_call(logger, "ftp", "login", context={"user": user}, success=None)

        try:
            self._connection.login(user, password)
            duration_ms = (time.perf_counter() - start_time) * 1000
            log_backend_call(
                logger,
                "ftp",
                "login",
                context={"user": user},
                success=True,
                duration_ms=duration_ms,
            )
            logger.debug("FTP login successful")
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            log_backend_call(
                logger,
                "ftp",
                "login",
                context={"user": user},
                success=False,
                error=e,
                duration_ms=duration_ms,
            )
            raise

    def cwd(self, directory: str) -> None:
        """Change working directory on FTP server.

        Args:
            directory: Directory path to change to

        Raises:
            ftplib.error_perm: If directory doesn't exist or no permission

        """
        if self._connection is None:
            raise RuntimeError("Not connected to FTP server")
        logger.debug("FTP changing directory to: %s", directory)
        self._connection.cwd(directory)

    def storbinary(self, cmd: str, fp: Any, blocksize: int = 8192) -> None:
        """Store a file in binary mode.

        Args:
            cmd: FTP command (e.g., "STOR filename")
            fp: File-like object to read data from
            blocksize: Block size for transfer

        """
        if self._connection is None:
            raise RuntimeError("Not connected to FTP server")
        filename = cmd.split()[-1] if " " in cmd else cmd
        start_time = time.perf_counter()
        logger.debug("FTP storing file: %s", filename)
        log_backend_call(logger, "ftp", "upload", endpoint=filename, success=None)

        try:
            self._connection.storbinary(cmd, fp, blocksize)
            duration_ms = (time.perf_counter() - start_time) * 1000
            log_backend_call(
                logger,
                "ftp",
                "upload",
                endpoint=filename,
                success=True,
                duration_ms=duration_ms,
            )
            logger.debug("FTP stored file: %s", filename)
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            log_backend_call(
                logger,
                "ftp",
                "upload",
                endpoint=filename,
                success=False,
                error=e,
                duration_ms=duration_ms,
            )
            raise

    def quit(self) -> None:
        """Send QUIT command and close connection gracefully."""
        if self._connection is not None:
            logger.debug("FTP disconnecting (quit)")
            try:
                self._connection.quit()
            except Exception as e:
                logger.debug("Failed to close FTP connection: %s", e)
            finally:
                self._connection = None

    def close(self) -> None:
        """Close connection unconditionally."""
        if self._connection is not None:
            logger.debug("FTP closing connection")
            try:
                self._connection.close()
            except Exception as e:
                logger.debug("Failed to close FTP connection: %s", e)
            finally:
                self._connection = None

    def set_pasv(self, *, passive: bool) -> None:
        """Set passive mode for data transfers.

        Args:
            passive: True for passive mode, False for active

        """
        if self._connection is None:
            raise RuntimeError("Not connected to FTP server")
        self._connection.set_pasv(passive)

    def nlst(self, directory: str = ".", *, passive: bool = True) -> list[str]:
        """List files in directory.

        Args:
            directory: Directory to list (default: current directory)
            passive: Whether to use passive mode

        Returns:
            List of file names

        """
        if self._connection is None:
            raise RuntimeError("Not connected to FTP server")
        self._connection.set_pasv(passive)
        return self._connection.nlst(directory)

    def retrbinary(self, cmd: str, callback: Any, blocksize: int = 8192) -> None:
        """Retrieve a file in binary mode.

        Args:
            cmd: FTP command (e.g., "RETR filename")
            callback: Function to call for each block of data
            blocksize: Block size for transfer

        """
        if self._connection is None:
            raise RuntimeError("Not connected to FTP server")
        filename = cmd.split()[-1] if " " in cmd else cmd
        start_time = time.perf_counter()
        logger.debug("FTP retrieving file: %s", filename)
        log_backend_call(logger, "ftp", "download", endpoint=filename, success=None)

        try:
            self._connection.retrbinary(cmd, callback, blocksize)
            duration_ms = (time.perf_counter() - start_time) * 1000
            log_backend_call(
                logger,
                "ftp",
                "download",
                endpoint=filename,
                success=True,
                duration_ms=duration_ms,
            )
            logger.debug("FTP retrieved file: %s", filename)
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            log_backend_call(
                logger,
                "ftp",
                "download",
                endpoint=filename,
                success=False,
                error=e,
                duration_ms=duration_ms,
            )
            raise

    def mkd(self, directory: str) -> str:
        """Create a directory on the FTP server.

        Args:
            directory: Directory path to create

        Returns:
            Path of created directory

        """
        if self._connection is None:
            raise RuntimeError("Not connected to FTP server")
        return self._connection.mkd(directory)

    def delete(self, filename: str) -> None:
        """Delete a file on the FTP server.

        Args:
            filename: File to delete

        """
        if self._connection is None:
            raise RuntimeError("Not connected to FTP server")
        start_time = time.perf_counter()
        logger.debug("FTP deleting file: %s", filename)
        log_backend_call(logger, "ftp", "delete", endpoint=filename, success=None)

        try:
            self._connection.delete(filename)
            duration_ms = (time.perf_counter() - start_time) * 1000
            log_backend_call(
                logger,
                "ftp",
                "delete",
                endpoint=filename,
                success=True,
                duration_ms=duration_ms,
            )
            logger.debug("FTP deleted file: %s", filename)
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            log_backend_call(
                logger,
                "ftp",
                "delete",
                endpoint=filename,
                success=False,
                error=e,
                duration_ms=duration_ms,
            )
            raise

    @property
    def connected(self) -> bool:
        """Check if connection is active."""
        return self._connection is not None


class MockFTPClient:
    """Mock FTP client for testing.

    This implementation records all operations for verification
    in tests without making actual FTP connections.

    Attributes:
        connections: List of (host, port, timeout) tuples from connect calls
        logins: List of (user, password) tuples from login calls
        files_sent: List of (cmd, data) tuples from storbinary calls
        directories_changed: List of directory paths from cwd calls
        errors: List of errors to raise on subsequent operations

    """

    def __init__(self) -> None:
        """Initialize mock FTP client with empty tracking lists."""
        self.connections: list[tuple[str, int, float | None]] = []
        self.logins: list[tuple[str, str]] = []
        self.files_sent: list[tuple[str, bytes]] = []
        self.directories_changed: list[str] = []
        self.passive_mode_settings: list[bool] = []
        self.nlst_results: list[str] = []
        self.directories_created: list[str] = []
        self.files_deleted: list[str] = []
        self.files_retrieved: list[tuple[str, bytes]] = []
        self.errors: list[Exception] = []
        self._connected = False
        self._current_error_index = 0
        self._nlst_return_value: list[str] = []
        self._file_contents: dict = {}

    def _raise_error_if_set(self) -> None:
        """Raise next error from errors list if available."""
        if self._current_error_index < len(self.errors):
            error = self.errors[self._current_error_index]
            self._current_error_index += 1
            raise error

    def connect(self, host: str, port: int, timeout: float | None = None) -> None:
        """Record connection attempt.

        Args:
            host: Server hostname
            port: Server port
            timeout: Connection timeout

        """
        self._raise_error_if_set()
        self.connections.append((host, port, timeout))
        self._connected = True

    def login(self, user: str, password: str) -> None:
        """Record login attempt.

        Args:
            user: Username
            password: Password

        """
        self._raise_error_if_set()
        self.logins.append((user, password))

    def cwd(self, directory: str) -> None:
        """Record directory change.

        Args:
            directory: Directory path

        """
        self._raise_error_if_set()
        self.directories_changed.append(directory)

    def storbinary(self, cmd: str, fp: Any, blocksize: int = 8192) -> None:
        """Record file storage.

        Args:
            cmd: FTP command
            fp: File-like object
            blocksize: Block size (ignored in mock)

        """
        self._raise_error_if_set()
        data = fp.read()
        if isinstance(data, str):
            data = data.encode("utf-8")
        self.files_sent.append((cmd, data))

    def quit(self) -> None:
        """Record quit command."""
        self._connected = False

    def close(self) -> None:
        """Record close command."""
        self._connected = False

    def set_pasv(self, *, passive: bool) -> None:
        """Record passive mode setting.

        Args:
            passive: Passive mode setting

        """
        self.passive_mode_settings.append(passive)

    def nlst(self, *, directory: str = "") -> list[str]:
        """Return mock file listing.

        Args:
            directory: Directory to list

        Returns:
            Pre-configured list of files

        """
        self._raise_error_if_set()
        self.nlst_results.append(directory)
        return self._nlst_return_value

    def retrbinary(self, cmd: str, callback: Any, blocksize: int = 8192) -> None:
        """Record file retrieval.

        Args:
            cmd: FTP command
            callback: Callback function
            blocksize: Block size (ignored in mock)

        """
        self._raise_error_if_set()
        filename = cmd.split()[-1] if " " in cmd else cmd
        content = self._file_contents.get(filename, b"")
        self.files_retrieved.append((cmd, content))
        callback(content)

    def mkd(self, directory: str) -> str:
        """Record directory creation.

        Args:
            directory: Directory path

        Returns:
            Directory path

        """
        self._raise_error_if_set()
        self.directories_created.append(directory)
        return directory

    def delete(self, filename: str) -> None:
        """Record file deletion.

        Args:
            filename: File to delete

        """
        self._raise_error_if_set()
        self.files_deleted.append(filename)

    def set_nlst_return_value(self, files: list[str]) -> None:
        """Set return value for nlst calls.

        Args:
            files: List of file names to return

        """
        self._nlst_return_value = files

    def set_file_contents(self, filename: str, content: bytes) -> None:
        """Set contents for a file to be retrieved.

        Args:
            filename: File name
            content: File contents

        """
        self._file_contents[filename] = content

    def add_error(self, error: Exception) -> None:
        """Add an error to be raised on next operation.

        Args:
            error: Exception to raise

        """
        self.errors.append(error)

    @property
    def connected(self) -> bool:
        """Check if mock connection is active."""
        return self._connected

    def reset(self) -> None:
        """Reset all tracking state."""
        self.connections.clear()
        self.logins.clear()
        self.files_sent.clear()
        self.directories_changed.clear()
        self.passive_mode_settings.clear()
        self.nlst_results.clear()
        self.directories_created.clear()
        self.files_deleted.clear()
        self.files_retrieved.clear()
        self.errors.clear()
        self._connected = False
        self._current_error_index = 0
        self._nlst_return_value = []
        self._file_contents.clear()


def create_ftp_client(
    *, use_tls: bool = False, mock: bool = False
) -> FTPClientProtocol:
    """Factory function to create FTP client.

    Args:
        use_tls: Whether to use TLS/SSL
        mock: If True, return MockFTPClient

    Returns:
        FTP client instance

    """
    if mock:
        return MockFTPClient()
    return RealFTPClient(use_tls=use_tls)
