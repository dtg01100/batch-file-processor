"""SMTP connection testing service.

Provides toolkit-agnostic SMTP validation, decoupled from any UI framework.
"""
from typing import Protocol, runtime_checkable, Optional, Tuple


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
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.ehlo()
            server.starttls()
            if username != "" and password != "":
                server.login(username, password)
            server.quit()
            return True, None
        except Exception as e:
            print(e)
            return False, str(e)


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
