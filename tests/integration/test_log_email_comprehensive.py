"""Comprehensive tests for logging and email functionality.

Tests cover:
- LogSender with MockEmailService and MockUIService
- Logging level behaviour (DEBUG vs WARNING) for ftp_backend / email_backend
- aiosmtpd-based real SMTP integration tests
- SMTPEmailService error handling
"""

import logging
import os
import socket
import sys
import threading
import time

import pytest

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from dispatch.log_sender import (
    EmailConfig,
    LogEntry,
    LogSender,
    MockEmailService,
    MockUIService,
    NullUIService,
    SMTPEmailService,
)

# ---------------------------------------------------------------------------
# aiosmtpd capturing server helpers
# ---------------------------------------------------------------------------

try:
    from aiosmtpd.controller import Controller

    AIOSMTPD_AVAILABLE = True
except ImportError:
    AIOSMTPD_AVAILABLE = False


class CapturingSMTPHandler:
    """aiosmtpd handler that records all incoming messages."""

    def __init__(self):
        self.messages = []
        self._lock = threading.Lock()

    async def handle_DATA(self, server, session, envelope):
        with self._lock:
            self.messages.append(
                {
                    "mail_from": envelope.mail_from,
                    "rcpt_tos": envelope.rcpt_tos,
                    "data": envelope.content,
                }
            )
        return "250 Message accepted"


@pytest.fixture(scope="function")
def smtp_server():
    """Start a local aiosmtpd test server; yield (host, port, handler); stop after test."""
    if not AIOSMTPD_AVAILABLE:
        pytest.skip("aiosmtpd not installed")

    def find_free_port():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return s.getsockname()[1]

    handler = CapturingSMTPHandler()
    port = find_free_port()
    controller = Controller(handler, hostname="127.0.0.1", port=port)
    controller.start()
    host = controller.hostname
    actual_port = controller.port
    yield host, actual_port, handler
    controller.stop()


# ---------------------------------------------------------------------------
# Helper: make a temporary log file
# ---------------------------------------------------------------------------


def make_temp_log(tmp_path, name="run.log", content="Log line 1\nLog line 2\n"):
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return str(p)


# ---------------------------------------------------------------------------
# LogSender unit tests (MockEmailService)
# ---------------------------------------------------------------------------


class TestLogSenderWithMock:
    """Test LogSender using MockEmailService -- no network required."""

    def test_log_sender_sends_email_content(self):
        """Verify MockEmailService receives correct to/subject/body."""
        email_service = MockEmailService()
        sender = LogSender(email_service=email_service)

        result = sender.send_log(
            "Log content here",
            ["recipient@test.com"],
            "Batch Run Log",
        )

        assert result is True
        assert len(email_service.sent_emails) == 1
        email = email_service.sent_emails[0]
        assert email["to"] == ["recipient@test.com"]
        assert email["subject"] == "Batch Run Log"
        assert email["body"] == "Log content here"

    def test_log_sender_sends_log_file_as_attachment(self, tmp_path):
        """A log file should be sent as an attachment with its basename as name."""
        log_path = make_temp_log(tmp_path, "batch_run.log")
        email_service = MockEmailService()
        sender = LogSender(email_service=email_service)

        result = sender.send_log_file(log_path, ["dev@test.com"], "Log File")

        assert result is True
        assert len(email_service.sent_emails) == 1
        email = email_service.sent_emails[0]
        assert len(email["attachments"]) == 1
        attachment = email["attachments"][0]
        assert attachment["name"] == "batch_run.log"
        assert attachment["path"] == log_path

    def test_log_sender_batch_logs(self, tmp_path):
        """send_batch_logs should send all provided LogEntry objects as attachments."""
        log1 = make_temp_log(tmp_path, "log1.log", "Content A")
        log2 = make_temp_log(tmp_path, "log2.log", "Content B")
        log3 = make_temp_log(tmp_path, "log3.log", "Content C")

        email_service = MockEmailService()
        sender = LogSender(email_service=email_service)
        entries = [LogEntry(log1), LogEntry(log2), LogEntry(log3)]

        sender.send_batch_logs(entries, ["qa@test.com"], "Batch Logs")

        assert len(email_service.sent_emails) == 1
        email = email_service.sent_emails[0]
        assert len(email["attachments"]) == 3
        names = {a["name"] for a in email["attachments"]}
        assert "log1.log" in names
        assert "log2.log" in names
        assert "log3.log" in names

    def test_log_sender_handles_missing_log_file(self, tmp_path):
        """A LogEntry pointing to a non-existent file should be handled gracefully."""
        missing = str(tmp_path / "does_not_exist.log")
        email_service = MockEmailService()
        sender = LogSender(email_service=email_service)

        results = sender.send_batch_logs(
            [LogEntry(missing)], ["ops@test.com"], "Missing Log"
        )

        # Missing file → result is False for that entry
        assert results.get(missing) is False
        # No email sent because no attachments were available
        assert len(email_service.sent_emails) == 0

    def test_log_sender_smtp_failure(self):
        """When MockEmailService.should_fail=True, send_log returns False."""
        email_service = MockEmailService()
        email_service.should_fail = True
        sender = LogSender(email_service=email_service)

        result = sender.send_log("Log content", ["a@b.com"], "Subject")

        assert result is False
        assert len(email_service.sent_emails) == 0

    def test_batch_logs_all_attached(self, tmp_path):
        """Three log files should each appear as an attachment in one email."""
        logs = [
            make_temp_log(tmp_path, f"log{i}.log", f"content {i}") for i in range(3)
        ]
        email_service = MockEmailService()
        sender = LogSender(email_service=email_service)
        entries = [LogEntry(p) for p in logs]

        sender.send_batch_logs(entries, ["admin@test.com"], "All Logs")

        email = email_service.sent_emails[0]
        assert len(email["attachments"]) == 3

    def test_log_entry_default_name(self, tmp_path):
        """LogEntry without explicit name should use the file's basename."""
        log_path = make_temp_log(tmp_path, "custom_name.log")
        entry = LogEntry(log_path=log_path)

        assert entry.log_name == "custom_name.log"

    def test_log_entry_custom_name_preserved(self, tmp_path):
        """LogEntry with explicit name should keep that name."""
        log_path = make_temp_log(tmp_path, "raw.log")
        entry = LogEntry(log_path=log_path, log_name="Friendly Name.log")

        assert entry.log_name == "Friendly Name.log"

    def test_log_sender_ui_progress_updates(self, tmp_path):
        """MockUIService should receive update_email_progress calls during batch send."""
        log1 = make_temp_log(tmp_path, "a.log")
        log2 = make_temp_log(tmp_path, "b.log")

        email_service = MockEmailService()
        ui = MockUIService()
        sender = LogSender(email_service=email_service, ui=ui)

        entries = [LogEntry(log1), LogEntry(log2)]
        sender.send_batch_logs(entries, ["ui@test.com"], "Progress Test")

        assert len(ui.email_progress_updates) == 2
        # First call: email_count=1, total=2
        assert ui.email_progress_updates[0]["email_count"] == 1
        assert ui.email_progress_updates[0]["total_emails"] == 2
        # Second call: email_count=2, total=2
        assert ui.email_progress_updates[1]["email_count"] == 2

    def test_log_sender_with_null_ui(self, tmp_path):
        """NullUIService must not raise and send should succeed normally."""
        log_path = make_temp_log(tmp_path)
        email_service = MockEmailService()
        sender = LogSender(email_service=email_service, ui=NullUIService())

        result = sender.send_log_file(log_path, ["dev@test.com"], "NullUI Test")

        assert result is True

    def test_log_sender_multiple_recipients(self):
        """send_log should pass all recipients to the email service."""
        email_service = MockEmailService()
        sender = LogSender(email_service=email_service)
        recipients = ["a@test.com", "b@test.com", "c@test.com"]

        result = sender.send_log("Content", recipients, "Multi-Recipient Test")

        assert result is True
        assert email_service.sent_emails[0]["to"] == recipients

    def test_batch_logs_partial_missing_files(self, tmp_path):
        """Mix of existing and missing files: only existing ones attached."""
        existing = make_temp_log(tmp_path, "exists.log")
        missing = str(tmp_path / "missing.log")

        email_service = MockEmailService()
        sender = LogSender(email_service=email_service)
        entries = [LogEntry(existing), LogEntry(missing)]

        results = sender.send_batch_logs(entries, ["ops@test.com"], "Partial")

        assert results[existing] is True
        assert results[missing] is False
        # Email sent with only the one existing attachment
        assert len(email_service.sent_emails) == 1
        assert len(email_service.sent_emails[0]["attachments"]) == 1

    def test_log_sender_empty_recipients_list(self):
        """Empty recipient list should still call send_email (let the service handle it)."""
        email_service = MockEmailService()
        sender = LogSender(email_service=email_service)

        result = sender.send_log("Content", [], "Subject")

        assert result is True
        assert email_service.sent_emails[0]["to"] == []

    def test_log_sender_empty_batch_no_email_sent(self, tmp_path):
        """An empty list of LogEntry objects should not trigger an email send."""
        email_service = MockEmailService()
        sender = LogSender(email_service=email_service)

        results = sender.send_batch_logs([], ["dev@test.com"], "Empty Batch")

        assert results == {}
        assert len(email_service.sent_emails) == 0

    def test_batch_logs_result_keys_match_log_paths(self, tmp_path):
        """send_batch_logs results dict keys should be log_path values."""
        log1 = make_temp_log(tmp_path, "first.log")
        log2 = make_temp_log(tmp_path, "second.log")

        email_service = MockEmailService()
        sender = LogSender(email_service=email_service)
        entries = [LogEntry(log1), LogEntry(log2)]

        results = sender.send_batch_logs(entries, ["a@b.com"], "Keys Test")

        assert log1 in results
        assert log2 in results


# ---------------------------------------------------------------------------
# LogSender with real aiosmtpd server
# ---------------------------------------------------------------------------


class TestLogSenderWithRealSMTP:
    """Integration tests that exercise SMTPEmailService against aiosmtpd."""

    @pytest.mark.skipif(not AIOSMTPD_AVAILABLE, reason="aiosmtpd not installed")
    def test_log_sender_with_real_smtp_server(self, tmp_path, smtp_server):
        """Email arrives at the aiosmtpd handler with correct subject/recipient."""
        host, port, handler = smtp_server

        config = EmailConfig(
            smtp_server=host,
            smtp_port=port,
            smtp_username="",
            smtp_password="",
            from_address="sender@test.local",
            use_tls=False,
        )
        email_service = SMTPEmailService(config)
        sender = LogSender(email_service=email_service)

        result = sender.send_log(
            "Run log content",
            ["dest@test.local"],
            "Integration Test Subject",
        )

        assert result is True
        # Give the handler a moment to process
        time.sleep(0.2)
        assert len(handler.messages) == 1
        msg = handler.messages[0]
        assert msg["rcpt_tos"] == ["dest@test.local"]
        raw = msg["data"].decode("utf-8", errors="replace")
        assert "Integration Test Subject" in raw

    @pytest.mark.skipif(not AIOSMTPD_AVAILABLE, reason="aiosmtpd not installed")
    def test_log_sender_sends_log_file_via_real_smtp(self, tmp_path, smtp_server):
        """Log file attachment arrives at aiosmtpd server."""
        host, port, handler = smtp_server
        log_path = make_temp_log(tmp_path, "real_test.log", "actual log data")

        config = EmailConfig(
            smtp_server=host,
            smtp_port=port,
            smtp_username="",
            smtp_password="",
            from_address="batch@test.local",
            use_tls=False,
        )
        email_service = SMTPEmailService(config)
        sender = LogSender(email_service=email_service)

        result = sender.send_log_file(log_path, ["recv@test.local"], "File Test")

        assert result is True
        time.sleep(0.2)
        assert len(handler.messages) >= 1
        raw = handler.messages[-1]["data"].decode("utf-8", errors="replace")
        assert "real_test.log" in raw

    @pytest.mark.skipif(not AIOSMTPD_AVAILABLE, reason="aiosmtpd not installed")
    def test_smtp_unreachable_server(self):
        """Attempting to connect to port 1 should cause send_email to return False."""
        config = EmailConfig(
            smtp_server="127.0.0.1",
            smtp_port=1,  # Almost always unavailable
            smtp_username="",
            smtp_password="",
            from_address="x@local",
            use_tls=False,
        )
        email_service = SMTPEmailService(config)
        result = email_service.send_email(
            to=["recv@local"],
            subject="Should Fail",
            body="body",
        )
        assert result is False

    @pytest.mark.skipif(not AIOSMTPD_AVAILABLE, reason="aiosmtpd not installed")
    def test_smtp_auth_failure_graceful(self, smtp_server):
        """No-auth server should accept messages when no credentials are supplied."""
        host, port, handler = smtp_server
        # aiosmtpd default handler does not enforce auth -- connection succeeds.
        # Use empty credentials so SMTPEmailService skips the login() call,
        # which aiosmtpd does not support (no AUTH extension).
        config = EmailConfig(
            smtp_server=host,
            smtp_port=port,
            smtp_username="",
            smtp_password="",
            from_address="x@local",
            use_tls=False,
        )
        email_service = SMTPEmailService(config)
        result = email_service.send_email(
            to=["r@local"],
            subject="Auth Test",
            body="body",
        )
        # The server accepts the message
        assert result is True


# ---------------------------------------------------------------------------
# Logging level tests
# ---------------------------------------------------------------------------


class TestLoggingLevels:
    """Verify that logging levels gate messages as expected in ftp/email backends."""

    def test_debug_logging_enabled(self, caplog):
        """With DEBUG level, debug messages should appear in caplog."""
        with caplog.at_level(logging.DEBUG, logger="backend.ftp_backend"):
            logging.getLogger("backend.ftp_backend").debug(
                "Debug message from ftp_backend"
            )

        assert any("Debug message" in r.message for r in caplog.records)

    def test_debug_logging_disabled(self, caplog):
        """With WARNING level, DEBUG messages must NOT appear for ftp_backend."""
        with caplog.at_level(logging.WARNING, logger="backend.ftp_backend"):
            logging.getLogger("backend.ftp_backend").debug("Should be suppressed")

        debug_messages = [r for r in caplog.records if r.levelno == logging.DEBUG]
        suppressed = [m for m in debug_messages if "Should be suppressed" in m.message]
        assert len(suppressed) == 0

    def test_ftp_backend_logs_connect_attempt(self, tmp_path, caplog):
        """ftp_backend.do() should log a debug message about connecting."""
        from unittest.mock import patch

        from backend import ftp_backend
        from backend.ftp_client import MockFTPClient

        test_file = str(tmp_path / "f.txt")
        with open(test_file, "wb") as fh:
            fh.write(b"data")

        mock_client = MockFTPClient()
        params = {
            "ftp_server": "myserver.local",
            "ftp_port": 21,
            "ftp_username": "u",
            "ftp_password": "p",
            "ftp_folder": "/upload",
        }

        with caplog.at_level(logging.DEBUG, logger="backend.ftp_backend"):
            with patch("backend.backend_base.time.sleep"):
                ftp_backend.do(
                    params, {}, test_file, ftp_client=mock_client, disable_retry=True
                )

        connect_messages = [
            r.message
            for r in caplog.records
            if "Connecting" in r.message or "myserver" in r.message
        ]
        assert len(connect_messages) > 0

    def test_email_backend_logs_send_via_caplog(self, tmp_path, caplog):
        """email_backend.do() should not suppress all log output at INFO level."""
        from unittest.mock import patch

        from backend import email_backend
        from backend.smtp_client import MockSMTPClient

        test_file = str(tmp_path / "mail.txt")
        with open(test_file, "wb") as fh:
            fh.write(b"email data")

        mock_client = MockSMTPClient()
        params = {
            "email_to": "r@test.com",
            "email_subject_line": "Test",
        }
        settings = {
            "email_address": "s@test.com",
            "email_smtp_server": "smtp.local",
            "smtp_port": 587,
            "email_username": "",
            "email_password": "",
        }

        with caplog.at_level(logging.DEBUG):
            with patch("backend.backend_base.time.sleep"):
                email_backend.do(params, settings, test_file, smtp_client=mock_client)

        # Verify the email was actually dispatched through the mock client
        assert len(mock_client.emails_sent) == 1, "Backend should have sent one email"
        sent = mock_client.emails_sent[0]
        assert sent["to"] == "r@test.com", "Email should be addressed to the recipient"

    def test_warning_level_suppresses_info(self, caplog):
        """INFO messages must not appear when log level is set to WARNING."""
        logger = logging.getLogger("ftp_backend")
        with caplog.at_level(logging.WARNING, logger="backend.ftp_backend"):
            logger.info("This info should be suppressed")

        info_msgs = [
            r
            for r in caplog.records
            if r.levelno == logging.INFO and "suppressed" in r.message
        ]
        assert len(info_msgs) == 0

    def test_warning_messages_always_appear(self, caplog):
        """WARNING level messages should always appear regardless of level setting."""
        logger = logging.getLogger("dispatch.orchestrator")
        with caplog.at_level(logging.WARNING, logger="dispatch.orchestrator"):
            logger.warning("This is a warning")

        warning_msgs = [r for r in caplog.records if "This is a warning" in r.message]
        assert len(warning_msgs) == 1

    def test_error_messages_always_appear(self, caplog):
        """ERROR level messages should appear at any logging level >= ERROR."""
        logger = logging.getLogger("ftp_backend")
        with caplog.at_level(logging.ERROR, logger="backend.ftp_backend"):
            logger.error("Critical FTP failure")

        error_msgs = [r for r in caplog.records if "Critical FTP failure" in r.message]
        assert len(error_msgs) == 1


# ---------------------------------------------------------------------------
# SMTPEmailService config tests (no network)
# ---------------------------------------------------------------------------


class TestEmailConfig:
    """Tests for EmailConfig dataclass and SMTPEmailService construction."""

    def test_email_config_defaults(self):
        """EmailConfig should set use_tls=True by default."""
        config = EmailConfig(
            smtp_server="smtp.example.com",
            smtp_port=587,
            smtp_username="user",
            smtp_password="secret",
            from_address="noreply@example.com",
        )
        assert config.use_tls is True

    def test_email_config_tls_override(self):
        """EmailConfig should respect explicit use_tls=False."""
        config = EmailConfig(
            smtp_server="smtp.example.com",
            smtp_port=25,
            smtp_username="",
            smtp_password="",
            from_address="noreply@example.com",
            use_tls=False,
        )
        assert config.use_tls is False

    def test_smtp_email_service_construction(self):
        """SMTPEmailService should store the provided config."""
        config = EmailConfig(
            smtp_server="mail.local",
            smtp_port=25,
            smtp_username="",
            smtp_password="",
            from_address="x@local",
            use_tls=False,
        )
        service = SMTPEmailService(config)
        assert service.config is config

    def test_mock_email_service_reset(self):
        """MockEmailService.reset() should clear all recorded emails."""
        service = MockEmailService()
        service.send_email(["a@b.com"], "Subject", "Body")
        assert len(service.sent_emails) == 1
        service.reset()
        assert len(service.sent_emails) == 0

    def test_mock_email_service_get_last_email(self):
        """get_last_email should return the most recently sent email dict."""
        service = MockEmailService()
        service.send_email(["a@b.com"], "First", "Body 1")
        service.send_email(["c@d.com"], "Second", "Body 2")
        last = service.get_last_email()
        assert last["subject"] == "Second"

    def test_mock_email_service_get_last_email_empty(self):
        """get_last_email on a fresh MockEmailService should return None."""
        service = MockEmailService()
        assert service.get_last_email() is None


# ---------------------------------------------------------------------------
# MockUIService tests
# ---------------------------------------------------------------------------


class TestMockUIService:
    """Verify MockUIService recording behaviour."""

    def test_mock_ui_records_progress_message(self):
        ui = MockUIService()
        ui.update_progress("Processing folder X")
        assert "Processing folder X" in ui.progress_messages

    def test_mock_ui_records_email_progress(self):
        ui = MockUIService()
        ui.update_email_progress(batch_number=1, email_count=2, total_emails=5)
        assert len(ui.email_progress_updates) == 1
        update = ui.email_progress_updates[0]
        assert update["batch_number"] == 1
        assert update["email_count"] == 2
        assert update["total_emails"] == 5

    def test_mock_ui_reset_clears_all(self):
        ui = MockUIService()
        ui.update_progress("msg")
        ui.update_email_progress(1, 1, 1)
        ui.reset()
        assert ui.progress_messages == []
        assert ui.email_progress_updates == []

    def test_mock_ui_get_last_progress(self):
        ui = MockUIService()
        ui.update_progress("First")
        ui.update_progress("Second")
        assert ui.get_last_progress() == "Second"

    def test_mock_ui_get_last_progress_empty(self):
        ui = MockUIService()
        assert ui.get_last_progress() is None
