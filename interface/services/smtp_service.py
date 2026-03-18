"""SMTP connection testing service.

Provides toolkit-agnostic SMTP validation, decoupled from any UI framework.
"""

import errno
from typing import Optional, Protocol, Tuple, runtime_checkable


@runtime_checkable
class SMTPServiceProtocol(Protocol):
    """Protocol for SMTP connection testing."""

    def test_connection(
        self,
        smtp_server: str,
        smtp_port: str,
        username: str = "",
        password: str = "",
    ) -> Tuple[bool, Optional[str]]:
        """Test SMTP server connection.

        Args:
            smtp_server: SMTP server hostname
            smtp_port: SMTP server port
            username: Optional SMTP username
            password: Optional SMTP password

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        ...


class SMTPService:
    """Real SMTP connection testing service."""

    @staticmethod
    def _format_error(error: Exception) -> str:
        """Format SMTP errors into user-friendly messages.

        Traverses wrapped exceptions (``__cause__`` / ``__context__``) so nested
        socket errors are surfaced correctly.
        """
        visited: set[int] = set()
        current: Optional[BaseException] = error

        while current is not None and id(current) not in visited:
            visited.add(id(current))

            if isinstance(current, OSError):
                if current.errno == errno.ENETUNREACH:
                    return (
                        "Network is unreachable (Errno 101). "
                        "Check internet/VPN connectivity and SMTP server settings."
                    )
                if current.errno == errno.EHOSTUNREACH:
                    return (
                        "SMTP host is unreachable. "
                        "Verify server hostname, DNS, and network access."
                    )

            current = current.__cause__ or current.__context__

        return str(error)

    def test_connection(
        self,
        smtp_server: str,
        smtp_port: str,
        username: str = "",
        password: str = "",
    ) -> Tuple[bool, Optional[str]]:
        """Test SMTP server connection."""
        import smtplib

        try:
            server = smtplib.SMTP(smtp_server, int(smtp_port), timeout=15)
            server.ehlo()
            server.starttls()
            if username != "" and password != "":
                server.login(username, password)
            server.quit()
            return True, None
        except Exception as e:
            return False, self._format_error(e)


class MockSMTPService:
    """Mock SMTP service for testing."""

    def __init__(self, success: bool = True, error_message: Optional[str] = None):
        self._success = success
        self._error_message = error_message
        self.last_call = None

    def test_connection(
        self,
        smtp_server: str,
        smtp_port: str,
        username: str = "",
        password: str = "",
    ) -> Tuple[bool, Optional[str]]:
        self.last_call = {
            "smtp_server": smtp_server,
            "smtp_port": smtp_port,
            "username": username,
            "password": password,
        }
        return self._success, self._error_message
