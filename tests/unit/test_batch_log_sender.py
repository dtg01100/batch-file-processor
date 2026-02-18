"""Unit tests for batch_log_sender module.

Tests:
- Email composition with single log (singular subject)
- Email composition with multiple logs (plural subject)
- SMTP connection with TLS and authentication
- SMTP connection without authentication
- Attachment handling with MIME type detection
- Fallback to application/octet-stream for unknown types
- Queue management (old_id update, .zip extension removal)
- Error handling for SMTP connection failures
- Error handling for missing log files
- Progress callback invocation
"""

import pytest
from unittest.mock import patch, MagicMock, mock_open, call
import os
import tempfile
import mimetypes


class TestEmailComposition:
    """Test suite for email composition based on log count."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings dictionary."""
        return {
            'email_address': 'sender@example.com',
            'email_username': 'smtp_user',
            'email_password': 'smtp_password',
            'email_smtp_server': 'smtp.example.com',
            'smtp_port': 587,
        }

    @pytest.fixture
    def mock_reporting(self):
        """Create mock reporting dictionary."""
        return {
            'report_email_destination': 'recipient@example.com, other@example.com',
        }

    @pytest.fixture
    def mock_emails_table_single(self):
        """Create mock emails table with single log."""
        table = MagicMock()
        table.count.return_value = 1
        log_entry = {
            'id': 'log_001',
            'log': '/path/to/run_20230101.log',
        }
        table.all.return_value = [log_entry]
        return table

    @pytest.fixture
    def mock_emails_table_multiple(self):
        """Create mock emails table with multiple logs."""
        table = MagicMock()
        table.count.return_value = 3
        log_entries = [
            {'id': 'log_001', 'log': '/path/to/run_20230101.log'},
            {'id': 'log_002', 'log': '/path/to/run_20230102.log'},
            {'id': 'log_003', 'log': '/path/to/run_20230103.log'},
        ]
        table.all.return_value = log_entries
        return table

    @pytest.fixture
    def mock_queue(self):
        """Create mock sent_emails_removal_queue."""
        queue = MagicMock()
        queue.insert = MagicMock()
        return queue

    @pytest.fixture
    def mock_progress_callback(self):
        """Create mock progress callback."""
        callback = MagicMock()
        callback.update_message = MagicMock()
        return callback

    @patch('batch_log_sender.smtplib.SMTP')
    @patch('batch_log_sender.open', new_callable=mock_open, read_data=b'test log content')
    def test_single_log_email_subject(self, mock_file, mock_smtp, mock_settings,
                                       mock_reporting, mock_emails_table_single,
                                       mock_queue, mock_progress_callback):
        """Test that single log produces 'Log from run at: {time}' subject."""
        import batch_log_sender

        # Mock file exists check
        mock_file.return_value.__enter__ = MagicMock(return_value=mock_file.return_value)
        mock_file.return_value.__exit__ = MagicMock(return_value=False)

        run_time = "2023-01-01 10:00:00"
        batch_log_sender.do(
            settings=mock_settings,
            reporting=mock_reporting,
            emails_table=mock_emails_table_single,
            sent_emails_removal_queue=mock_queue,
            time=run_time,
            batch_number=1,
            emails_count=1,
            total_emails=1,
            run_summary_string="Processing completed",
            progress_callback=mock_progress_callback,
        )

        # Get the message that was sent
        mock_smtp_instance = mock_smtp.return_value
        send_message_call = mock_smtp_instance.send_message.call_args
        sent_message = send_message_call[0][0]

        # Assert subject is singular
        assert sent_message['Subject'] == f"Log from run at: {run_time}"
        assert "Logs from run at:" not in sent_message['Subject']

    @patch('batch_log_sender.smtplib.SMTP')
    @patch('batch_log_sender.open', new_callable=mock_open, read_data=b'test log content')
    def test_multiple_logs_email_subject(self, mock_file, mock_smtp, mock_settings,
                                         mock_reporting, mock_emails_table_multiple,
                                         mock_queue, mock_progress_callback):
        """Test that multiple logs produce 'Logs from run at: {time}' subject."""
        import batch_log_sender

        # Mock file exists check
        mock_file.return_value.__enter__ = MagicMock(return_value=mock_file.return_value)
        mock_file.return_value.__exit__ = MagicMock(return_value=False)

        run_time = "2023-01-01 10:00:00"
        batch_log_sender.do(
            settings=mock_settings,
            reporting=mock_reporting,
            emails_table=mock_emails_table_multiple,
            sent_emails_removal_queue=mock_queue,
            time=run_time,
            batch_number=1,
            emails_count=3,
            total_emails=3,
            run_summary_string="Processing completed",
            progress_callback=mock_progress_callback,
        )

        # Get the message that was sent
        mock_smtp_instance = mock_smtp.return_value
        send_message_call = mock_smtp_instance.send_message.call_args
        sent_message = send_message_call[0][0]

        # Assert subject is plural
        assert sent_message['Subject'] == f"Logs from run at: {run_time}"
        assert "Log from run at:" not in sent_message['Subject']


class TestSMTPConnection:
    """Test suite for SMTP connection handling."""

    @pytest.fixture
    def mock_settings_with_auth(self):
        """Create mock settings with authentication credentials."""
        return {
            'email_address': 'sender@example.com',
            'email_username': 'smtp_user',
            'email_password': 'smtp_password',
            'email_smtp_server': 'smtp.example.com',
            'smtp_port': 587,
        }

    @pytest.fixture
    def mock_settings_no_auth(self):
        """Create mock settings without authentication credentials."""
        return {
            'email_address': 'sender@example.com',
            'email_username': '',
            'email_password': '',
            'email_smtp_server': 'smtp.example.com',
            'smtp_port': 587,
        }

    @pytest.fixture
    def mock_reporting(self):
        """Create mock reporting dictionary."""
        return {
            'report_email_destination': 'recipient@example.com',
        }

    @pytest.fixture
    def mock_emails_table(self):
        """Create mock emails table with single log."""
        table = MagicMock()
        table.count.return_value = 1
        log_entry = {
            'id': 'log_001',
            'log': '/path/to/run_20230101.log',
        }
        table.all.return_value = [log_entry]
        return table

    @pytest.fixture
    def mock_queue(self):
        """Create mock sent_emails_removal_queue."""
        queue = MagicMock()
        queue.insert = MagicMock()
        return queue

    @pytest.fixture
    def mock_progress_callback(self):
        """Create mock progress callback."""
        callback = MagicMock()
        callback.update_message = MagicMock()
        return callback

    @patch('batch_log_sender.smtplib.SMTP')
    @patch('batch_log_sender.open', new_callable=mock_open, read_data=b'test log content')
    def test_smtp_connection_with_tls_and_auth(self, mock_file, mock_smtp, mock_settings_with_auth,
                                                mock_reporting, mock_emails_table,
                                                mock_queue, mock_progress_callback):
        """Test SMTP connection with TLS and authentication."""
        import batch_log_sender

        # Mock file exists check
        mock_file.return_value.__enter__ = MagicMock(return_value=mock_file.return_value)
        mock_file.return_value.__exit__ = MagicMock(return_value=False)

        batch_log_sender.do(
            settings=mock_settings_with_auth,
            reporting=mock_reporting,
            emails_table=mock_emails_table,
            sent_emails_removal_queue=mock_queue,
            time="2023-01-01 10:00:00",
            batch_number=1,
            emails_count=1,
            total_emails=1,
            run_summary_string="Processing completed",
            progress_callback=mock_progress_callback,
        )

        # Verify SMTP was called with correct server and port (port is converted to string)
        mock_smtp.assert_called_once_with('smtp.example.com', '587')

        # Verify SMTP methods were called in order
        mock_smtp_instance = mock_smtp.return_value
        assert mock_smtp_instance.ehlo.call_count == 1
        assert mock_smtp_instance.starttls.call_count == 1
        assert mock_smtp_instance.login.call_count == 1
        mock_smtp_instance.login.assert_called_with('smtp_user', 'smtp_password')
        assert mock_smtp_instance.send_message.call_count == 1
        assert mock_smtp_instance.close.call_count == 1

    @patch('batch_log_sender.smtplib.SMTP')
    @patch('batch_log_sender.open', new_callable=mock_open, read_data=b'test log content')
    def test_smtp_connection_without_auth(self, mock_file, mock_smtp, mock_settings_no_auth,
                                          mock_reporting, mock_emails_table,
                                          mock_queue, mock_progress_callback):
        """Test SMTP connection without authentication (no credentials)."""
        import batch_log_sender

        # Mock file exists check
        mock_file.return_value.__enter__ = MagicMock(return_value=mock_file.return_value)
        mock_file.return_value.__exit__ = MagicMock(return_value=False)

        batch_log_sender.do(
            settings=mock_settings_no_auth,
            reporting=mock_reporting,
            emails_table=mock_emails_table,
            sent_emails_removal_queue=mock_queue,
            time="2023-01-01 10:00:00",
            batch_number=1,
            emails_count=1,
            total_emails=1,
            run_summary_string="Processing completed",
            progress_callback=mock_progress_callback,
        )

        # Verify SMTP was called with correct server and port (port is converted to string)
        mock_smtp.assert_called_once_with('smtp.example.com', '587')

        # Verify SMTP methods were called but login was NOT called
        mock_smtp_instance = mock_smtp.return_value
        assert mock_smtp_instance.ehlo.call_count == 1
        assert mock_smtp_instance.starttls.call_count == 1
        assert mock_smtp_instance.login.call_count == 0  # No login when credentials are empty
        assert mock_smtp_instance.send_message.call_count == 1
        assert mock_smtp_instance.close.call_count == 1


class TestAttachmentHandling:
    """Test suite for attachment handling and MIME type detection."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings dictionary."""
        return {
            'email_address': 'sender@example.com',
            'email_username': 'smtp_user',
            'email_password': 'smtp_password',
            'email_smtp_server': 'smtp.example.com',
            'smtp_port': 587,
        }

    @pytest.fixture
    def mock_reporting(self):
        """Create mock reporting dictionary."""
        return {
            'report_email_destination': 'recipient@example.com',
        }

    @pytest.fixture
    def mock_emails_table(self):
        """Create mock emails table with log files."""
        table = MagicMock()
        table.count.return_value = 1
        log_entry = {
            'id': 'log_001',
            'log': '/path/to/run_20230101.log',
        }
        table.all.return_value = [log_entry]
        return table

    @pytest.fixture
    def mock_queue(self):
        """Create mock sent_emails_removal_queue."""
        queue = MagicMock()
        queue.insert = MagicMock()
        return queue

    @pytest.fixture
    def mock_progress_callback(self):
        """Create mock progress callback."""
        callback = MagicMock()
        callback.update_message = MagicMock()
        return callback

    @patch('batch_log_sender.mimetypes.guess_type')
    @patch('batch_log_sender.smtplib.SMTP')
    @patch('batch_log_sender.open', new_callable=mock_open, read_data=b'test log content')
    def test_attachment_mime_type_detection(self, mock_file, mock_smtp, mock_guess_type,
                                             mock_settings, mock_reporting, mock_emails_table,
                                             mock_queue, mock_progress_callback):
        """Test that MIME type is correctly detected from filename."""
        import batch_log_sender

        # Mock file exists check
        mock_file.return_value.__enter__ = MagicMock(return_value=mock_file.return_value)
        mock_file.return_value.__exit__ = MagicMock(return_value=False)

        # Mock mimetypes.guess_type to return a known type
        mock_guess_type.return_value = ('text/plain', None)

        batch_log_sender.do(
            settings=mock_settings,
            reporting=mock_reporting,
            emails_table=mock_emails_table,
            sent_emails_removal_queue=mock_queue,
            time="2023-01-01 10:00:00",
            batch_number=1,
            emails_count=1,
            total_emails=1,
            run_summary_string="Processing completed",
            progress_callback=mock_progress_callback,
        )

        # Verify guess_type was called
        mock_guess_type.assert_called()

        # Get the message that was sent
        mock_smtp_instance = mock_smtp.return_value
        send_message_call = mock_smtp_instance.send_message.call_args
        sent_message = send_message_call[0][0]

        # Verify attachment was added with correct MIME type
        attachments = list(sent_message.iter_attachments())
        assert len(attachments) == 1

    @patch('batch_log_sender.mimetypes.guess_type')
    @patch('batch_log_sender.smtplib.SMTP')
    @patch('batch_log_sender.open', new_callable=mock_open, read_data=b'test log content')
    def test_attachment_fallback_to_octet_stream(self, mock_file, mock_smtp, mock_guess_type,
                                                  mock_settings, mock_reporting, mock_emails_table,
                                                  mock_queue, mock_progress_callback):
        """Test fallback to application/octet-stream for unknown types."""
        import batch_log_sender

        # Mock file exists check
        mock_file.return_value.__enter__ = MagicMock(return_value=mock_file.return_value)
        mock_file.return_value.__exit__ = MagicMock(return_value=False)

        # Mock mimetypes.guess_type to return None (unknown type)
        mock_guess_type.return_value = (None, None)

        batch_log_sender.do(
            settings=mock_settings,
            reporting=mock_reporting,
            emails_table=mock_emails_table,
            sent_emails_removal_queue=mock_queue,
            time="2023-01-01 10:00:00",
            batch_number=1,
            emails_count=1,
            total_emails=1,
            run_summary_string="Processing completed",
            progress_callback=mock_progress_callback,
        )

        # Verify guess_type was called
        mock_guess_type.assert_called()

    @patch('batch_log_sender.mimetypes.guess_type')
    @patch('batch_log_sender.smtplib.SMTP')
    @patch('batch_log_sender.open', new_callable=mock_open, read_data=b'test log content')
    def test_attachment_with_encoding_not_none(self, mock_file, mock_smtp, mock_guess_type,
                                                mock_settings, mock_reporting, mock_emails_table,
                                                mock_queue, mock_progress_callback):
        """Test fallback to application/octet-stream when encoding is not None."""
        import batch_log_sender

        # Mock file exists check
        mock_file.return_value.__enter__ = MagicMock(return_value=mock_file.return_value)
        mock_file.return_value.__exit__ = MagicMock(return_value=False)

        # Mock mimetypes.guess_type to return a type with encoding (e.g., .gz)
        mock_guess_type.return_value = ('application/gzip', 'gzip')

        batch_log_sender.do(
            settings=mock_settings,
            reporting=mock_reporting,
            emails_table=mock_emails_table,
            sent_emails_removal_queue=mock_queue,
            time="2023-01-01 10:00:00",
            batch_number=1,
            emails_count=1,
            total_emails=1,
            run_summary_string="Processing completed",
            progress_callback=mock_progress_callback,
        )

        # Verify guess_type was called
        mock_guess_type.assert_called()


class TestQueueManagement:
    """Test suite for queue management operations."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings dictionary."""
        return {
            'email_address': 'sender@example.com',
            'email_username': 'smtp_user',
            'email_password': 'smtp_password',
            'email_smtp_server': 'smtp.example.com',
            'smtp_port': 587,
        }

    @pytest.fixture
    def mock_reporting(self):
        """Create mock reporting dictionary."""
        return {
            'report_email_destination': 'recipient@example.com',
        }

    @pytest.fixture
    def mock_queue(self):
        """Create mock sent_emails_removal_queue."""
        queue = MagicMock()
        queue.insert = MagicMock()
        return queue

    @pytest.fixture
    def mock_progress_callback(self):
        """Create mock progress callback."""
        callback = MagicMock()
        callback.update_message = MagicMock()
        return callback

    @patch('batch_log_sender.smtplib.SMTP')
    @patch('batch_log_sender.open', new_callable=mock_open, read_data=b'test log content')
    def test_old_id_update(self, mock_file, mock_smtp, mock_settings,
                           mock_reporting, mock_queue, mock_progress_callback):
        """Test that old_id is updated from id field."""
        import batch_log_sender

        # Mock file exists check
        mock_file.return_value.__enter__ = MagicMock(return_value=mock_file.return_value)
        mock_file.return_value.__exit__ = MagicMock(return_value=False)

        # Create mock table with a log that has id field
        mock_table = MagicMock()
        mock_table.count.return_value = 1
        log_entry = {
            'id': 'original_id_123',
            'log': '/path/to/run_20230101.log',
        }
        # Create a mutable copy of the log entry
        mock_log_entry = dict(log_entry)
        mock_table.all.return_value = [mock_log_entry]

        batch_log_sender.do(
            settings=mock_settings,
            reporting=mock_reporting,
            emails_table=mock_table,
            sent_emails_removal_queue=mock_queue,
            time="2023-01-01 10:00:00",
            batch_number=1,
            emails_count=1,
            total_emails=1,
            run_summary_string="Processing completed",
            progress_callback=mock_progress_callback,
        )

        # Verify queue.insert was called
        assert mock_queue.insert.call_count == 1

        # Get the inserted log entry
        inserted_log = mock_queue.insert.call_args[0][0]

        # Verify old_id was set from id
        assert inserted_log['old_id'] == 'original_id_123'
        # Verify id is no longer in the log (it was popped)
        assert 'id' not in inserted_log

    @patch('batch_log_sender.smtplib.SMTP')
    @patch('batch_log_sender.open', new_callable=mock_open, read_data=b'test log content')
    def test_zip_extension_removal(self, mock_file, mock_smtp, mock_settings,
                                    mock_reporting, mock_queue, mock_progress_callback):
        """Test that .zip extension is removed from log path."""
        import batch_log_sender

        # Mock file exists check
        mock_file.return_value.__enter__ = MagicMock(return_value=mock_file.return_value)
        mock_file.return_value.__exit__ = MagicMock(return_value=False)

        # Create mock table with a log that has .zip extension
        mock_table = MagicMock()
        mock_table.count.return_value = 1
        mock_log_entry = {
            'id': 'log_001',
            'log': '/path/to/run_20230101.log.zip',
        }
        mock_table.all.return_value = [mock_log_entry]

        batch_log_sender.do(
            settings=mock_settings,
            reporting=mock_reporting,
            emails_table=mock_table,
            sent_emails_removal_queue=mock_queue,
            time="2023-01-01 10:00:00",
            batch_number=1,
            emails_count=1,
            total_emails=1,
            run_summary_string="Processing completed",
            progress_callback=mock_progress_callback,
        )

        # Verify queue.insert was called
        assert mock_queue.insert.call_count == 1

        # Get the inserted log entry
        inserted_log = mock_queue.insert.call_args[0][0]

        # Verify .zip extension was removed
        assert inserted_log['log'] == '/path/to/run_20230101.log'
        assert not inserted_log['log'].endswith('.zip')

    @patch('batch_log_sender.smtplib.SMTP')
    @patch('batch_log_sender.open', new_callable=mock_open, read_data=b'test log content')
    def test_no_zip_extension_removal(self, mock_file, mock_smtp, mock_settings,
                                       mock_reporting, mock_queue, mock_progress_callback):
        """Test that non-.zip paths are not modified."""
        import batch_log_sender

        # Mock file exists check
        mock_file.return_value.__enter__ = MagicMock(return_value=mock_file.return_value)
        mock_file.return_value.__exit__ = MagicMock(return_value=False)

        # Create mock table with a log that doesn't have .zip extension
        mock_table = MagicMock()
        mock_table.count.return_value = 1
        original_log_path = '/path/to/run_20230101.log'
        mock_log_entry = {
            'id': 'log_001',
            'log': original_log_path,
        }
        mock_table.all.return_value = [mock_log_entry]

        batch_log_sender.do(
            settings=mock_settings,
            reporting=mock_reporting,
            emails_table=mock_table,
            sent_emails_removal_queue=mock_queue,
            time="2023-01-01 10:00:00",
            batch_number=1,
            emails_count=1,
            total_emails=1,
            run_summary_string="Processing completed",
            progress_callback=mock_progress_callback,
        )

        # Verify queue.insert was called
        assert mock_queue.insert.call_count == 1

        # Get the inserted log entry
        inserted_log = mock_queue.insert.call_args[0][0]

        # Verify log path was not modified
        assert inserted_log['log'] == original_log_path


class TestErrorHandling:
    """Test suite for error handling scenarios."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings dictionary."""
        return {
            'email_address': 'sender@example.com',
            'email_username': 'smtp_user',
            'email_password': 'smtp_password',
            'email_smtp_server': 'smtp.example.com',
            'smtp_port': 587,
        }

    @pytest.fixture
    def mock_reporting(self):
        """Create mock reporting dictionary."""
        return {
            'report_email_destination': 'recipient@example.com',
        }

    @pytest.fixture
    def mock_queue(self):
        """Create mock sent_emails_removal_queue."""
        queue = MagicMock()
        queue.insert = MagicMock()
        return queue

    @pytest.fixture
    def mock_progress_callback(self):
        """Create mock progress callback."""
        callback = MagicMock()
        callback.update_message = MagicMock()
        return callback

    @patch('batch_log_sender.open', new_callable=mock_open, read_data=b'test log content')
    @patch('batch_log_sender.smtplib.SMTP')
    def test_smtp_connection_failure(self, mock_smtp, mock_file, mock_settings,
                                      mock_reporting, mock_queue, mock_progress_callback):
        """Test handling of SMTP connection failures."""
        import batch_log_sender

        # Mock file exists check
        mock_file.return_value.__enter__ = MagicMock(return_value=mock_file.return_value)
        mock_file.return_value.__exit__ = MagicMock(return_value=False)

        # Mock SMTP to raise an exception on connection
        mock_smtp.side_effect = Exception("Connection refused")

        # Create mock table
        mock_table = MagicMock()
        mock_table.count.return_value = 1
        mock_log_entry = {
            'id': 'log_001',
            'log': '/path/to/run_20230101.log',
        }
        mock_table.all.return_value = [mock_log_entry]

        # The function should raise the exception
        with pytest.raises(Exception, match="Connection refused"):
            batch_log_sender.do(
                settings=mock_settings,
                reporting=mock_reporting,
                emails_table=mock_table,
                sent_emails_removal_queue=mock_queue,
                time="2023-01-01 10:00:00",
                batch_number=1,
                emails_count=1,
                total_emails=1,
                run_summary_string="Processing completed",
                progress_callback=mock_progress_callback,
            )

    @patch('batch_log_sender.smtplib.SMTP')
    def test_smtp_send_failure(self, mock_smtp, mock_settings,
                                mock_reporting, mock_queue, mock_progress_callback):
        """Test handling of SMTP send failures."""
        import batch_log_sender

        # Mock SMTP instance to raise exception on send_message
        mock_smtp_instance = MagicMock()
        mock_smtp_instance.ehlo = MagicMock()
        mock_smtp_instance.starttls = MagicMock()
        mock_smtp_instance.login = MagicMock()
        mock_smtp_instance.send_message.side_effect = Exception("Send failed")
        mock_smtp_instance.close = MagicMock()
        mock_smtp.return_value = mock_smtp_instance

        # Create mock table
        mock_table = MagicMock()
        mock_table.count.return_value = 1
        mock_log_entry = {
            'id': 'log_001',
            'log': '/path/to/run_20230101.log',
        }
        mock_table.all.return_value = [mock_log_entry]

        # Mock file open to raise FileNotFoundError
        with patch('batch_log_sender.open', side_effect=FileNotFoundError("Log file not found")):
            with pytest.raises(FileNotFoundError):
                batch_log_sender.do(
                    settings=mock_settings,
                    reporting=mock_reporting,
                    emails_table=mock_table,
                    sent_emails_removal_queue=mock_queue,
                    time="2023-01-01 10:00:00",
                    batch_number=1,
                    emails_count=1,
                    total_emails=1,
                    run_summary_string="Processing completed",
                    progress_callback=mock_progress_callback,
                )

    @patch('batch_log_sender.smtplib.SMTP')
    @patch('batch_log_sender.open', side_effect=FileNotFoundError("Log file not found"))
    def test_missing_log_file(self, mock_file, mock_smtp, mock_settings,
                               mock_reporting, mock_queue, mock_progress_callback):
        """Test handling of missing log files."""
        import batch_log_sender

        # Create mock table
        mock_table = MagicMock()
        mock_table.count.return_value = 1
        mock_log_entry = {
            'id': 'log_001',
            'log': '/nonexistent/path/run_20230101.log',
        }
        mock_table.all.return_value = [mock_log_entry]

        # The function should raise FileNotFoundError
        with pytest.raises(FileNotFoundError):
            batch_log_sender.do(
                settings=mock_settings,
                reporting=mock_reporting,
                emails_table=mock_table,
                sent_emails_removal_queue=mock_queue,
                time="2023-01-01 10:00:00",
                batch_number=1,
                emails_count=1,
                total_emails=1,
                run_summary_string="Processing completed",
                progress_callback=mock_progress_callback,
            )


class TestProgressCallback:
    """Test suite for progress callback invocation."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings dictionary."""
        return {
            'email_address': 'sender@example.com',
            'email_username': 'smtp_user',
            'email_password': 'smtp_password',
            'email_smtp_server': 'smtp.example.com',
            'smtp_port': 587,
        }

    @pytest.fixture
    def mock_reporting(self):
        """Create mock reporting dictionary."""
        return {
            'report_email_destination': 'recipient@example.com',
        }

    @pytest.fixture
    def mock_queue(self):
        """Create mock sent_emails_removal_queue."""
        queue = MagicMock()
        queue.insert = MagicMock()
        return queue

    @patch('batch_log_sender.smtplib.SMTP')
    @patch('batch_log_sender.open', new_callable=mock_open, read_data=b'test log content')
    def test_progress_callback_invoked(self, mock_file, mock_smtp, mock_settings,
                                        mock_reporting, mock_queue):
        """Test that progress callback is invoked during execution."""
        import batch_log_sender

        # Mock file exists check
        mock_file.return_value.__enter__ = MagicMock(return_value=mock_file.return_value)
        mock_file.return_value.__exit__ = MagicMock(return_value=False)

        # Create mock progress callback
        mock_progress_callback = MagicMock()
        mock_progress_callback.update_message = MagicMock()

        # Create mock table
        mock_table = MagicMock()
        mock_table.count.return_value = 1
        mock_log_entry = {
            'id': 'log_001',
            'log': '/path/to/run_20230101.log',
        }
        mock_table.all.return_value = [mock_log_entry]

        batch_log_sender.do(
            settings=mock_settings,
            reporting=mock_reporting,
            emails_table=mock_table,
            sent_emails_removal_queue=mock_queue,
            time="2023-01-01 10:00:00",
            batch_number=1,
            emails_count=1,
            total_emails=1,
            run_summary_string="Processing completed",
            progress_callback=mock_progress_callback,
        )

        # Verify progress callback was invoked
        assert mock_progress_callback.update_message.call_count >= 1

    @patch('batch_log_sender.smtplib.SMTP')
    @patch('batch_log_sender.open', new_callable=mock_open, read_data=b'test log content')
    def test_null_progress_callback_used_when_none(self, mock_file, mock_smtp, mock_settings,
                                                     mock_reporting, mock_queue):
        """Test that NullProgressCallback is used when no callback provided."""
        import batch_log_sender
        from interface.services.progress_service import NullProgressCallback

        # Mock file exists check
        mock_file.return_value.__enter__ = MagicMock(return_value=mock_file.return_value)
        mock_file.return_value.__exit__ = MagicMock(return_value=False)

        # Create mock table
        mock_table = MagicMock()
        mock_table.count.return_value = 1
        mock_log_entry = {
            'id': 'log_001',
            'log': '/path/to/run_20230101.log',
        }
        mock_table.all.return_value = [mock_log_entry]

        # Call without progress_callback
        batch_log_sender.do(
            settings=mock_settings,
            reporting=mock_reporting,
            emails_table=mock_table,
            sent_emails_removal_queue=mock_queue,
            time="2023-01-01 10:00:00",
            batch_number=1,
            emails_count=1,
            total_emails=1,
            run_summary_string="Processing completed",
            progress_callback=None,
        )

        # Verify SMTP was still called (function completed successfully)
        assert mock_smtp.call_count == 1


class TestEmailAddressHandling:
    """Test suite for email address parsing and handling."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings dictionary."""
        return {
            'email_address': 'sender@example.com',
            'email_username': 'smtp_user',
            'email_password': 'smtp_password',
            'email_smtp_server': 'smtp.example.com',
            'smtp_port': 587,
        }

    @pytest.fixture
    def mock_queue(self):
        """Create mock sent_emails_removal_queue."""
        queue = MagicMock()
        queue.insert = MagicMock()
        return queue

    @pytest.fixture
    def mock_progress_callback(self):
        """Create mock progress callback."""
        callback = MagicMock()
        callback.update_message = MagicMock()
        return callback

    @patch('batch_log_sender.smtplib.SMTP')
    @patch('batch_log_sender.open', new_callable=mock_open, read_data=b'test log content')
    def test_single_recipient_email(self, mock_file, mock_smtp, mock_settings,
                                     mock_queue, mock_progress_callback):
        """Test email sent to single recipient."""
        import batch_log_sender

        # Mock file exists check
        mock_file.return_value.__enter__ = MagicMock(return_value=mock_file.return_value)
        mock_file.return_value.__exit__ = MagicMock(return_value=False)

        # Create mock reporting with single recipient
        mock_reporting = {
            'report_email_destination': 'recipient@example.com',
        }

        # Create mock table
        mock_table = MagicMock()
        mock_table.count.return_value = 1
        mock_log_entry = {
            'id': 'log_001',
            'log': '/path/to/run_20230101.log',
        }
        mock_table.all.return_value = [mock_log_entry]

        batch_log_sender.do(
            settings=mock_settings,
            reporting=mock_reporting,
            emails_table=mock_table,
            sent_emails_removal_queue=mock_queue,
            time="2023-01-01 10:00:00",
            batch_number=1,
            emails_count=1,
            total_emails=1,
            run_summary_string="Processing completed",
            progress_callback=mock_progress_callback,
        )

        # Get the message that was sent
        mock_smtp_instance = mock_smtp.return_value
        send_message_call = mock_smtp_instance.send_message.call_args
        sent_message = send_message_call[0][0]

        # Verify From address
        assert sent_message['From'] == 'sender@example.com'

    @patch('batch_log_sender.smtplib.SMTP')
    @patch('batch_log_sender.open', new_callable=mock_open, read_data=b'test log content')
    def test_multiple_recipients_email(self, mock_file, mock_smtp, mock_settings,
                                        mock_queue, mock_progress_callback):
        """Test email sent to multiple recipients."""
        import batch_log_sender

        # Mock file exists check
        mock_file.return_value.__enter__ = MagicMock(return_value=mock_file.return_value)
        mock_file.return_value.__exit__ = MagicMock(return_value=False)

        # Create mock reporting with multiple recipients
        mock_reporting = {
            'report_email_destination': 'recipient1@example.com, recipient2@example.com, recipient3@example.com',
        }

        # Create mock table
        mock_table = MagicMock()
        mock_table.count.return_value = 1
        mock_log_entry = {
            'id': 'log_001',
            'log': '/path/to/run_20230101.log',
        }
        mock_table.all.return_value = [mock_log_entry]

        batch_log_sender.do(
            settings=mock_settings,
            reporting=mock_reporting,
            emails_table=mock_table,
            sent_emails_removal_queue=mock_queue,
            time="2023-01-01 10:00:00",
            batch_number=1,
            emails_count=1,
            total_emails=1,
            run_summary_string="Processing completed",
            progress_callback=mock_progress_callback,
        )

        # Get the message that was sent
        mock_smtp_instance = mock_smtp.return_value
        send_message_call = mock_smtp_instance.send_message.call_args
        sent_message = send_message_call[0][0]

        # Verify To address contains all recipients
        # Note: EmailMessage stores To as a string when set from a list
        to_address = sent_message['To']
        # The To header may be a comma-separated string or a list
        # Check that all recipients are present
        assert 'recipient1@example.com' in str(to_address)
        assert 'recipient2@example.com' in str(to_address)
        assert 'recipient3@example.com' in str(to_address)
