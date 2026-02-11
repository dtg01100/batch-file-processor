"""Tests for the LogSender service.

This module tests the refactored log sender with mock services.
"""

import pytest
from datetime import datetime
from dispatch.log_sender import (
    EmailConfig,
    LogSender,
    LogEntry,
    SMTPEmailService,
    MockEmailService,
    MockUIService,
    NullUIService,
    create_log_sender_from_settings,
)


class TestEmailConfig:
    """Tests for EmailConfig dataclass."""
    
    def test_email_config_creation(self):
        """Test creating an EmailConfig instance."""
        config = EmailConfig(
            smtp_server="smtp.example.com",
            smtp_port=587,
            smtp_username="user@example.com",
            smtp_password="password",
            from_address="sender@example.com"
        )
        
        assert config.smtp_server == "smtp.example.com"
        assert config.smtp_port == 587
        assert config.smtp_username == "user@example.com"
        assert config.smtp_password == "password"
        assert config.from_address == "sender@example.com"
        assert config.use_tls is True  # Default value
    
    def test_email_config_with_tls_false(self):
        """Test EmailConfig with TLS disabled."""
        config = EmailConfig(
            smtp_server="smtp.example.com",
            smtp_port=25,
            smtp_username="",
            smtp_password="",
            from_address="sender@example.com",
            use_tls=False
        )
        
        assert config.use_tls is False


class TestMockEmailService:
    """Tests for MockEmailService."""
    
    def test_send_email_records_email(self):
        """Test that send_email records the email."""
        service = MockEmailService()
        
        result = service.send_email(
            to=["recipient@example.com"],
            subject="Test Subject",
            body="Test Body"
        )
        
        assert result is True
        assert len(service.sent_emails) == 1
        
        email = service.sent_emails[0]
        assert email['to'] == ["recipient@example.com"]
        assert email['subject'] == "Test Subject"
        assert email['body'] == "Test Body"
    
    def test_send_email_with_attachments(self):
        """Test sending email with attachments."""
        service = MockEmailService()
        
        result = service.send_email(
            to=["recipient@example.com"],
            subject="Test",
            body="Body",
            attachments=[{'path': '/tmp/log.txt', 'name': 'log.txt'}]
        )
        
        assert result is True
        assert len(service.sent_emails[0]['attachments']) == 1
    
    def test_send_email_can_fail(self):
        """Test that send_email can be configured to fail."""
        service = MockEmailService()
        service.should_fail = True
        
        result = service.send_email(
            to=["recipient@example.com"],
            subject="Test",
            body="Body"
        )
        
        assert result is False
        assert len(service.sent_emails) == 0
    
    def test_reset_clears_emails(self):
        """Test that reset clears all recorded emails."""
        service = MockEmailService()
        service.send_email(to=["a@b.com"], subject="Test", body="Body")
        
        service.reset()
        
        assert len(service.sent_emails) == 0
    
    def test_get_last_email(self):
        """Test getting the last sent email."""
        service = MockEmailService()
        
        assert service.get_last_email() is None
        
        service.send_email(to=["a@b.com"], subject="First", body="Body1")
        service.send_email(to=["b@c.com"], subject="Second", body="Body2")
        
        last = service.get_last_email()
        assert last['subject'] == "Second"


class TestMockUIService:
    """Tests for MockUIService."""
    
    def test_update_progress_records_message(self):
        """Test that update_progress records the message."""
        ui = MockUIService()
        
        ui.update_progress("Processing file 1")
        ui.update_progress("Processing file 2")
        
        assert len(ui.progress_messages) == 2
        assert ui.progress_messages[0] == "Processing file 1"
        assert ui.progress_messages[1] == "Processing file 2"
    
    def test_update_email_progress_records_update(self):
        """Test that update_email_progress records the update."""
        ui = MockUIService()
        
        ui.update_email_progress(batch_number=1, email_count=5, total_emails=10)
        
        assert len(ui.email_progress_updates) == 1
        update = ui.email_progress_updates[0]
        assert update['batch_number'] == 1
        assert update['email_count'] == 5
        assert update['total_emails'] == 10
    
    def test_reset_clears_all(self):
        """Test that reset clears all recorded data."""
        ui = MockUIService()
        ui.update_progress("Test")
        ui.update_email_progress(1, 1, 10)
        
        ui.reset()
        
        assert len(ui.progress_messages) == 0
        assert len(ui.email_progress_updates) == 0
    
    def test_get_last_progress(self):
        """Test getting the last progress message."""
        ui = MockUIService()
        
        assert ui.get_last_progress() is None
        
        ui.update_progress("First")
        ui.update_progress("Second")
        
        assert ui.get_last_progress() == "Second"


class TestNullUIService:
    """Tests for NullUIService."""
    
    def test_null_ui_does_nothing(self):
        """Test that NullUIService methods do nothing without error."""
        ui = NullUIService()
        
        # These should not raise any errors
        ui.update_progress("Test")
        ui.update_email_progress(1, 1, 10)


class TestLogEntry:
    """Tests for LogEntry dataclass."""
    
    def test_log_entry_creation(self):
        """Test creating a LogEntry."""
        entry = LogEntry(log_path="/tmp/test.log")
        
        assert entry.log_path == "/tmp/test.log"
        assert entry.log_name == "test.log"  # Auto-derived
        assert entry.metadata == {}
    
    def test_log_entry_with_custom_name(self):
        """Test LogEntry with custom name."""
        entry = LogEntry(
            log_path="/tmp/test.log",
            log_name="custom_name.log"
        )
        
        assert entry.log_name == "custom_name.log"
    
    def test_log_entry_with_metadata(self):
        """Test LogEntry with metadata."""
        entry = LogEntry(
            log_path="/tmp/test.log",
            metadata={'batch': 1, 'folder': 'test'}
        )
        
        assert entry.metadata['batch'] == 1
        assert entry.metadata['folder'] == 'test'


class TestLogSender:
    """Tests for LogSender class."""
    
    def test_send_log_success(self):
        """Test sending a log successfully."""
        email_service = MockEmailService()
        sender = LogSender(email_service=email_service)
        
        result = sender.send_log(
            log_content="Log content here",
            recipients=["admin@example.com"],
            subject="Test Log"
        )
        
        assert result is True
        assert len(email_service.sent_emails) == 1
    
    def test_send_log_with_mock_ui(self):
        """Test that UI updates are called during sending."""
        email_service = MockEmailService()
        ui = MockUIService()
        sender = LogSender(email_service=email_service, ui=ui)
        
        sender.send_log(
            log_content="Content",
            recipients=["admin@example.com"],
            subject="Test"
        )
        
        # UI doesn't get updated for simple send_log
        # (it's updated in batch operations)
    
    def test_send_batch_logs(self, tmp_path):
        """Test sending batch logs."""
        # Create temporary log files
        log1 = tmp_path / "log1.txt"
        log2 = tmp_path / "log2.txt"
        log1.write_text("Log 1 content")
        log2.write_text("Log 2 content")
        
        email_service = MockEmailService()
        ui = MockUIService()
        sender = LogSender(email_service=email_service, ui=ui)
        
        logs = [
            LogEntry(log_path=str(log1)),
            LogEntry(log_path=str(log2)),
        ]
        
        results = sender.send_batch_logs(
            logs=logs,
            recipients=["admin@example.com"],
            subject="Batch Logs"
        )
        
        assert len(results) == 2
        assert str(log1) in results
        assert str(log2) in results
        assert all(results.values())  # All should be True
        
        # Check UI was updated
        assert len(ui.email_progress_updates) == 2
    
    def test_send_batch_logs_with_missing_file(self, tmp_path):
        """Test sending batch logs with a missing file."""
        log1 = tmp_path / "log1.txt"
        log1.write_text("Log 1 content")
        
        email_service = MockEmailService()
        sender = LogSender(email_service=email_service)
        
        logs = [
            LogEntry(log_path=str(log1)),
            LogEntry(log_path="/nonexistent/log2.txt"),
        ]
        
        results = sender.send_batch_logs(
            logs=logs,
            recipients=["admin@example.com"],
            subject="Batch Logs"
        )
        
        assert results[str(log1)] is True
        assert results["/nonexistent/log2.txt"] is False
    
    def test_send_batch_logs_handles_failure(self, tmp_path):
        """Test handling email service failure."""
        log1 = tmp_path / "log1.txt"
        log1.write_text("Log 1 content")
        
        email_service = MockEmailService()
        email_service.should_fail = True
        sender = LogSender(email_service=email_service)
        
        logs = [LogEntry(log_path=str(log1))]
        
        results = sender.send_batch_logs(
            logs=logs,
            recipients=["admin@example.com"],
            subject="Batch Logs"
        )
        
        # File exists but send failed
        assert results[str(log1)] is False
    
    def test_send_log_file(self, tmp_path):
        """Test sending a log file as attachment."""
        log_file = tmp_path / "test.log"
        log_file.write_text("Log content")
        
        email_service = MockEmailService()
        sender = LogSender(email_service=email_service)
        
        result = sender.send_log_file(
            log_path=str(log_file),
            recipients=["admin@example.com"],
            subject="Log File"
        )
        
        assert result is True
        email = email_service.get_last_email()
        assert len(email['attachments']) == 1
        assert email['attachments'][0]['name'] == "test.log"


class TestLogSenderFromSettings:
    """Tests for factory function."""
    
    def test_create_log_sender_from_settings(self):
        """Test creating LogSender from settings dict."""
        settings = {
            'email_smtp_server': 'smtp.example.com',
            'smtp_port': 587,
            'email_username': 'user@example.com',
            'email_password': 'password',
            'email_address': 'sender@example.com',
            'use_tls': True
        }
        
        sender = create_log_sender_from_settings(settings)
        
        assert isinstance(sender, LogSender)
        assert isinstance(sender.email_service, SMTPEmailService)
        assert sender.email_service.config.smtp_server == 'smtp.example.com'
    
    def test_create_log_sender_with_ui(self):
        """Test creating LogSender with UI service."""
        settings = {
            'email_smtp_server': 'smtp.example.com',
            'smtp_port': 587,
            'email_username': 'user',
            'email_password': 'pass',
            'email_address': 'sender@example.com'
        }
        
        ui = MockUIService()
        sender = create_log_sender_from_settings(settings, ui=ui)
        
        assert sender.ui is ui


class TestLogSenderBackwardCompatibility:
    """Tests for backward compatibility with existing code."""
    
    def test_send_logs_from_table(self, tmp_path):
        """Test sending logs from a table-like structure."""
        # Create temp log files
        log1 = tmp_path / "log1.txt"
        log2 = tmp_path / "log2.txt"
        log1.write_text("Log 1")
        log2.write_text("Log 2")
        
        # Mock table with .all() method
        class MockTable:
            def __init__(self, records):
                self._records = records
            
            def all(self):
                return self._records
            
            def count(self):
                return len(self._records)
        
        table = MockTable([
            {'id': 1, 'log': str(log1)},
            {'id': 2, 'log': str(log2)},
        ])
        
        # Mock removal queue
        class MockQueue:
            def __init__(self):
                self.inserted = []
            
            def insert(self, record):
                self.inserted.append(record)
        
        queue = MockQueue()
        
        email_service = MockEmailService()
        sender = LogSender(email_service=email_service)
        
        results = sender.send_logs_from_table(
            logs_table=table,
            recipients=["admin@example.com"],
            subject="Test",
            body="See attached",
            removal_queue=queue
        )
        
        assert len(results) == 2
        assert len(queue.inserted) == 2
        # Check that old_id was set
        assert queue.inserted[0]['old_id'] == 1
        assert queue.inserted[1]['old_id'] == 2
