"""FTP Service abstraction for testable FTP operations."""

import ftplib
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FTPConnectionResult:
    """Result of an FTP connection test."""

    success: bool
    error_message: str | None = None
    error_type: str | None = None  # "server", "login", "cwd", "unknown"


class FTPServiceProtocol:
    """Protocol defining the FTP service interface."""

    def test_connection(
        self, server: str, port: int, username: str, password: str, folder: str
    ) -> FTPConnectionResult:
        """Test FTP connection credentials."""
        raise NotImplementedError


class FTPService(FTPServiceProtocol):
    """Real FTP service implementation."""

    def test_connection(
        self, server: str, port: int, username: str, password: str, folder: str
    ) -> FTPConnectionResult:
        """
        Test FTP connection credentials.

        Args:
            server: FTP server hostname
            port: FTP port number
            username: FTP username
            password: FTP password
            folder: FTP folder path to test

        Returns:
            FTPConnectionResult indicating success or failure with error details

        """
        ftp = ftplib.FTP()

        try:
            # Test server connection
            ftp.connect(str(server), int(port))

            try:
                # Test login
                ftp.login(username, password)

                try:
                    # Test folder access
                    ftp.cwd(folder)
                    return FTPConnectionResult(success=True)

                except Exception as e:
                    logger.debug("FTP cwd failed: %s", e)
                    return FTPConnectionResult(
                        success=False,
                        error_message="FTP Folder Field Incorrect",
                        error_type="cwd",
                    )

            except Exception as e:
                logger.debug("FTP login failed: %s", e)
                return FTPConnectionResult(
                    success=False,
                    error_message="FTP Username or Password Incorrect",
                    error_type="login",
                )

        except Exception as e:
            logger.debug("FTP server connection failed: %s", e)
            return FTPConnectionResult(
                success=False,
                error_message="FTP Server or Port Field Incorrect",
                error_type="server",
            )

        finally:
            try:
                ftp.close()
            except Exception:
                logger.debug(
                    "Failed to close FTP connection during cleanup", exc_info=True
                )

    def connect(
        self, server: str, port: int, username: str, password: str
    ) -> ftplib.FTP:
        """Create and return an FTP connection."""
        ftp = ftplib.FTP()
        ftp.connect(str(server), int(port))
        ftp.login(username, password)
        return ftp


class MockFTPService(FTPServiceProtocol):
    """Mock FTP service for testing."""

    def __init__(
        self,
        *,
        should_succeed: bool = True,
        fail_at: str | None = None,
        error_message: str = "Mock FTP Error",
    ) -> None:
        """
        Initialize mock FTP service.

        Args:
            should_succeed: Whether connections should succeed
            fail_at: Stage to fail at ("connect", "login", "cwd")
            error_message: Error message to return on failure

        """
        self.should_succeed = should_succeed
        self.fail_at = fail_at
        self.error_message = error_message
        self.connection_attempts = []

    def test_connection(
        self, server: str, port: int, username: str, password: str, folder: str
    ) -> FTPConnectionResult:
        """Record connection attempt and return configured result."""
        self.connection_attempts.append(
            {"server": server, "port": port, "username": username, "folder": folder}
        )

        if self.should_succeed:
            return FTPConnectionResult(success=True)

        error_type = self.fail_at or "unknown"
        return FTPConnectionResult(
            success=False, error_message=self.error_message, error_type=error_type
        )

    def connect(
        self, server: str, port: int, username: str, password: str
    ) -> "MockFTPConnection":
        """Return a mock FTP connection."""
        return MockFTPConnection()


class MockFTPConnection:
    """Mock FTP connection for testing."""

    def __init__(self) -> None:
        self.cwd_calls = []
        self.closed = False

    def cwd(self, path: str) -> None:
        """Record CWD call."""
        self.cwd_calls.append(path)

    def close(self) -> None:
        """Mark connection as closed."""
        self.closed = True
