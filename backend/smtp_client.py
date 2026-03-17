"""SMTP client implementations for send backends.

This module provides real and mock SMTP client implementations
that conform to the SMTPClientProtocol interface.
"""

import logging
import smtplib
from typing import Any, Dict, List, Optional

from backend.protocols import SMTPClientProtocol

logger = logging.getLogger(__name__)


class RealSMTPClient:
    """Real SMTP client using smtplib.

    This implementation wraps smtplib.SMTP for actual SMTP connections.

    Attributes:
        config: Configuration dictionary with server settings
        _connection: The underlying smtplib.SMTP connection object
    """

    def __init__(self, config: Optional[dict] = None):
        """Initialize SMTP client.

        Args:
            config: Optional configuration dictionary with keys:
                - host: SMTP server hostname
                - port: SMTP server port
                - username: Authentication username
                - password: Authentication password
                - use_tls: Whether to use TLS (default True)
        """
        self.config = config or {}
        self._connection: Optional[smtplib.SMTP] = None

    def connect(self, host: str, port: int = 587, timeout: float = 30) -> None:
        """Connect to SMTP server.

        Args:
            host: Server hostname or IP address
            port: Server port number
            timeout: Connection timeout in seconds (default 30)
        """
        logger.debug("SMTP connecting to %s:%d", host, port)
        self._connection = smtplib.SMTP(host, port, timeout=timeout)
        logger.debug("SMTP connected to %s:%d", host, port)

    def starttls(self) -> None:
        """Upgrade connection to TLS.

        Raises:
            RuntimeError: If not connected to server
        """
        if self._connection is None:
            raise RuntimeError("Not connected to SMTP server")
        logger.debug("SMTP upgrading to TLS")
        self._connection.starttls()

    def login(self, user: str, password: str) -> None:
        """Authenticate with SMTP server.

        Args:
            user: Username for authentication
            password: Password for authentication

        Raises:
            smtplib.SMTPAuthenticationError: If authentication fails
            RuntimeError: If not connected to server
        """
        if self._connection is None:
            raise RuntimeError("Not connected to SMTP server")
        logger.debug("SMTP authenticating as: %s", user)
        self._connection.login(user, password)
        logger.debug("SMTP authentication successful")

    def sendmail(self, from_addr: str, to_addrs: list, msg: str) -> dict:
        """Send email message.

        Args:
            from_addr: Sender email address
            to_addrs: List of recipient email addresses
            msg: Email message content as string

        Returns:
            Dictionary of rejected recipients (empty if all accepted)

        Raises:
            RuntimeError: If not connected to server
        """
        if self._connection is None:
            raise RuntimeError("Not connected to SMTP server")
        logger.debug("SMTP sending email from %s to %s", from_addr, to_addrs)
        result = self._connection.sendmail(from_addr, to_addrs, msg)
        logger.info("SMTP email sent successfully to %s", to_addrs)
        return result

    def send_message(self, msg: Any) -> dict:
        """Send EmailMessage object.

        Args:
            msg: EmailMessage object to send

        Returns:
            Dictionary of rejected recipients (empty if all accepted)

        Raises:
            RuntimeError: If not connected to server
        """
        if self._connection is None:
            raise RuntimeError("Not connected to SMTP server")
        logger.debug(
            "SMTP sending message object from=%s to=%s",
            msg.get("From", ""),
            msg.get("To", ""),
        )
        result = self._connection.send_message(msg)
        logger.info("SMTP message sent successfully to %s", msg["To"])
        return result

    def quit(self) -> None:
        """Send QUIT command and close connection gracefully."""
        if self._connection is not None:
            logger.debug("SMTP disconnecting (quit)")
            try:
                self._connection.quit()
            except Exception as e:
                logger.debug("Failed to close SMTP connection: %s", e)
            finally:
                self._connection = None

    def close(self) -> None:
        """Close connection unconditionally."""
        if self._connection is not None:
            try:
                self._connection.close()
            except Exception as e:
                logger.debug("Failed to close SMTP connection: %s", e)
            finally:
                self._connection = None

    def ehlo(self) -> None:
        """Send EHLO command to server.

        Raises:
            RuntimeError: If not connected to server
        """
        if self._connection is None:
            raise RuntimeError("Not connected to SMTP server")
        self._connection.ehlo()

    def set_debuglevel(self, level: int) -> None:
        """Set debug output level.

        Args:
            level: Debug level (0 = no output, 1 = commands, 2 = commands + data)
        """
        if self._connection is None:
            raise RuntimeError("Not connected to SMTP server")
        self._connection.set_debuglevel(level)

    def noop(self) -> None:
        """Send NOOP command to keep connection alive.

        Raises:
            RuntimeError: If not connected to server
        """
        if self._connection is None:
            raise RuntimeError("Not connected to SMTP server")
        self._connection.noop()

    @property
    def connected(self) -> bool:
        """Check if connection is active."""
        return self._connection is not None

    @classmethod
    def from_config(cls, config: dict) -> "RealSMTPClient":
        """Create and connect SMTP client from config dictionary.

        Args:
            config: Configuration dictionary with keys:
                - host: SMTP server hostname (required)
                - port: SMTP server port (required)
                - username: Authentication username (optional)
                - password: Authentication password (optional)
                - use_tls: Whether to use TLS (default True)

        Returns:
            Connected and authenticated SMTP client
        """
        client = cls(config)
        client.connect(config["host"], config["port"])
        client.ehlo()

        use_tls = config.get("use_tls", True)
        if use_tls:
            client.starttls()
            client.ehlo()

        username = config.get("username", "")
        password = config.get("password", "")
        if username and password:
            client.login(username, password)

        return client


class MockSMTPClient:
    """Mock SMTP client for testing.

    This implementation records all operations for verification
    in tests without making actual SMTP connections.

    Attributes:
        connections: List of (host, port) tuples from connect calls
        logins: List of (user, password) tuples from login calls
        emails_sent: List of email data dictionaries
        starttls_called: Whether starttls was called
        quit_called: Whether quit was called
        close_called: Whether close was called
    """

    def __init__(self):
        """Initialize mock SMTP client with empty tracking state."""
        self.connections: List[tuple] = []
        self.logins: List[tuple] = []
        self.emails_sent: List[Dict[str, Any]] = []
        self.starttls_calls: int = 0
        self.ehlo_calls: int = 0
        self.quit_called: bool = False
        self.close_called: bool = False
        self.debug_level: Optional[int] = None
        self.errors: List[Exception] = []
        self._current_error_index: int = 0
        self._connected: bool = False

    def _raise_error_if_set(self) -> None:
        """Raise next error from errors list if available."""
        if self._current_error_index < len(self.errors):
            error = self.errors[self._current_error_index]
            self._current_error_index += 1
            raise error

    def connect(self, host: str, port: int) -> None:
        """Record connection attempt.

        Args:
            host: Server hostname
            port: Server port
        """
        self._raise_error_if_set()
        self.connections.append((host, port))
        self._connected = True

    def starttls(self) -> None:
        """Record starttls call."""
        self._raise_error_if_set()
        self.starttls_calls += 1

    def login(self, user: str, password: str) -> None:
        """Record login attempt.

        Args:
            user: Username
            password: Password
        """
        self._raise_error_if_set()
        self.logins.append((user, password))

    def sendmail(self, from_addr: str, to_addrs: list, msg: str) -> dict:
        """Record email send attempt.

        Args:
            from_addr: Sender email address
            to_addrs: List of recipient addresses
            msg: Email message content

        Returns:
            Empty dict (all recipients accepted)
        """
        self._raise_error_if_set()
        self.emails_sent.append(
            {"from": from_addr, "to": to_addrs, "msg": msg, "type": "raw"}
        )
        return {}

    def send_message(self, msg: Any) -> dict:
        """Record EmailMessage send attempt.

        Args:
            msg: EmailMessage object

        Returns:
            Empty dict (all recipients accepted)
        """
        self._raise_error_if_set()
        self.emails_sent.append(
            {
                "from": msg.get("From", ""),
                "to": msg.get("To", ""),
                "msg": msg,
                "type": "message",
            }
        )
        return {}

    def quit(self) -> None:
        """Record quit call."""
        self._raise_error_if_set()
        self.quit_called = True
        self._connected = False

    def close(self) -> None:
        """Record close call."""
        self._raise_error_if_set()
        self.close_called = True
        self._connected = False

    def ehlo(self) -> None:
        """Record ehlo call."""
        self._raise_error_if_set()
        self.ehlo_calls += 1

    def set_debuglevel(self, level: int) -> None:
        """Record debug level setting.

        Args:
            level: Debug level
        """
        self.debug_level = level

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
        self.emails_sent.clear()
        self.starttls_calls = 0
        self.ehlo_calls = 0
        self.quit_called = False
        self.close_called = False
        self.debug_level = None
        self.errors.clear()
        self._current_error_index = 0
        self._connected = False


def create_smtp_client(
    config: Optional[dict] = None, mock: bool = False
) -> SMTPClientProtocol:
    """Factory function to create SMTP client.

    Args:
        config: Optional configuration dictionary
        mock: If True, return MockSMTPClient

    Returns:
        SMTP client instance
    """
    if mock:
        return MockSMTPClient()
    return RealSMTPClient(config=config)
