"""SMTP Service tests for connection validation and error formatting."""

import errno
from unittest.mock import MagicMock, patch

from interface.services.smtp_service import SMTPService


class TestSMTPService:
    """Test suite for SMTPService."""

    def test_successful_connection(self):
        """Successful SMTP connection should return (True, None)."""
        service = SMTPService()

        with patch("smtplib.SMTP") as smtp_cls:
            smtp_instance = MagicMock()
            smtp_cls.return_value = smtp_instance

            success, error = service.test_connection(
                smtp_server="smtp.example.com",
                smtp_port="587",
                username="user",
                password="pass",
            )

        assert success is True
        assert error is None
        smtp_cls.assert_called_once_with("smtp.example.com", 587, timeout=15)
        smtp_instance.ehlo.assert_called_once()
        smtp_instance.starttls.assert_called_once()
        smtp_instance.login.assert_called_once_with("user", "pass")
        smtp_instance.quit.assert_called_once()

    def test_network_unreachable_error_is_human_friendly(self):
        """Errno 101 should be mapped to a clear, actionable message."""
        service = SMTPService()

        with patch("smtplib.SMTP", side_effect=OSError(errno.ENETUNREACH, "down")):
            success, error = service.test_connection(
                smtp_server="smtp.example.com",
                smtp_port="587",
            )

        assert success is False
        assert error is not None
        assert "Network is unreachable" in error
        assert "Errno 101" in error
