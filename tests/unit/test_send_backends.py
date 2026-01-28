import os
import tempfile
import unittest
from unittest.mock import MagicMock, mock_open, patch

import pytest

from batch_log_sender import do as batch_log_sender_do
from copy_backend import do as copy_backend_do
from email_backend import do as email_backend_do
from ftp_backend import do as ftp_backend_do


class TestSendBackends(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "test.txt")
        with open(self.test_file, "w") as f:
            f.write("test content")

    def tearDown(self):
        os.remove(self.test_file)
        os.rmdir(self.temp_dir)

    @patch("email_backend.smtplib.SMTP")
    def test_email_backend_success(self, mock_smtp):
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server

        process_parameters = {
            "email_subject_line": "Test Subject %datetime% %filename%",
            "email_to": "test@example.com",
        }
        settings = {
            "email_address": "from@example.com",
            "email_smtp_server": "smtp.example.com",
            "smtp_port": 587,
            "email_username": "user",
            "email_password": "pass",
        }

        email_backend_do(process_parameters, settings, self.test_file)

        mock_smtp.assert_called_once_with("smtp.example.com", 587)
        mock_server.ehlo.assert_called_once()
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user", "pass")
        mock_server.send_message.assert_called_once()
        mock_server.close.assert_called_once()

    @patch("email_backend.smtplib.SMTP")
    def test_email_backend_no_auth(self, mock_smtp):
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server

        process_parameters = {"email_subject_line": "", "email_to": "test@example.com"}
        settings = {
            "email_address": "from@example.com",
            "email_smtp_server": "smtp.example.com",
            "smtp_port": 587,
            "email_username": "",
            "email_password": "",
        }

        email_backend_do(process_parameters, settings, self.test_file)

        mock_server.login.assert_not_called()

    @patch("ftp_backend.ftplib.FTP_TLS")
    @patch("ftp_backend.ftplib.FTP")
    def test_ftp_backend_success_tls(self, mock_ftp, mock_ftp_tls):
        mock_ftp_instance = MagicMock()
        mock_ftp_tls.return_value = mock_ftp_instance

        process_parameters = {
            "ftp_server": "ftp.example.com",
            "ftp_port": 21,
            "ftp_username": "user",
            "ftp_password": "pass",
            "ftp_folder": "/",
        }
        settings = {}

        ftp_backend_do(process_parameters, settings, self.test_file)

        mock_ftp_tls.assert_called_once()
        mock_ftp_instance.connect.assert_called_once_with("ftp.example.com", 21)
        mock_ftp_instance.login.assert_called_once_with("user", "pass")
        mock_ftp_instance.storbinary.assert_called_once()
        mock_ftp_instance.close.assert_called_once()

    @patch("ftp_backend.ftplib.FTP_TLS")
    @patch("ftp_backend.ftplib.FTP")
    def test_ftp_backend_fallback_to_non_tls(self, mock_ftp, mock_ftp_tls):
        mock_ftp_tls_instance = MagicMock()
        mock_ftp_tls_instance.connect.side_effect = Exception("TLS failed")
        mock_ftp_tls.return_value = mock_ftp_tls_instance

        mock_ftp_instance = MagicMock()
        mock_ftp.return_value = mock_ftp_instance

        process_parameters = {
            "ftp_server": "ftp.example.com",
            "ftp_port": 21,
            "ftp_username": "user",
            "ftp_password": "pass",
            "ftp_folder": "/",
        }
        settings = {}

        ftp_backend_do(process_parameters, settings, self.test_file)

        mock_ftp.assert_called_once()
        mock_ftp_instance.connect.assert_called_once_with("ftp.example.com", 21)
        mock_ftp_instance.login.assert_called_once_with("user", "pass")
        mock_ftp_instance.storbinary.assert_called_once()
        mock_ftp_instance.close.assert_called_once()

    @patch("copy_backend.shutil.copy")
    def test_copy_backend_success(self, mock_copy):
        process_parameters = {"copy_to_directory": "/tmp/dest"}
        settings = {}

        copy_backend_do(process_parameters, settings, self.test_file)

        mock_copy.assert_called_once_with(self.test_file, "/tmp/dest")

    @patch("batch_log_sender.smtplib.SMTP")
    @patch("batch_log_sender.doingstuffoverlay")
    def test_batch_log_sender_success(self, mock_overlay, mock_smtp):
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server

        settings = {
            "email_address": "from@example.com",
            "email_username": "user",
            "email_password": "pass",
            "email_smtp_server": "smtp.example.com",
            "smtp_port": 587,
        }
        reporting = {"report_email_destination": "to@example.com"}
        emails_table = MagicMock()
        emails_table.count.return_value = 1
        emails_table.all.return_value = [{"log": self.test_file, "id": 1}]
        sent_emails_removal_queue = MagicMock()
        time = "2023-01-01 12:00:00"
        args = MagicMock()
        args.automatic = True
        root = MagicMock()
        batch_number = 1
        emails_count = 1
        total_emails = 1
        simple_output = MagicMock()
        run_summary_string = "Test summary"

        batch_log_sender_do(
            settings,
            reporting,
            emails_table,
            sent_emails_removal_queue,
            time,
            args,
            root,
            batch_number,
            emails_count,
            total_emails,
            simple_output,
            run_summary_string,
        )

        mock_smtp.assert_called_once_with("smtp.example.com", "587")
        mock_server.ehlo.assert_called_once()
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user", "pass")
        mock_server.send_message.assert_called_once()
        mock_server.close.assert_called_once()

    @patch("email_backend.smtplib.SMTP")
    def test_email_backend_retry_on_failure(self, mock_smtp):
        mock_server = MagicMock()
        mock_server.send_message.side_effect = [Exception("Send failed"), None]
        mock_smtp.return_value = mock_server

        process_parameters = {"email_subject_line": "", "email_to": "test@example.com"}
        settings = {
            "email_address": "from@example.com",
            "email_smtp_server": "smtp.example.com",
            "smtp_port": 587,
            "email_username": "",
            "email_password": "",
        }

        email_backend_do(process_parameters, settings, self.test_file)

        # Should be called twice: first fail, then success
        self.assertEqual(mock_server.send_message.call_count, 2)

    @patch("ftp_backend.ftplib.FTP_TLS")
    @patch("ftp_backend.ftplib.FTP")
    def test_ftp_backend_retry_on_failure(self, mock_ftp, mock_ftp_tls):
        mock_ftp_tls_instance = MagicMock()
        mock_ftp_tls_instance.connect.side_effect = Exception("Connection failed")
        mock_ftp_tls.return_value = mock_ftp_tls_instance

        mock_ftp_instance = MagicMock()
        mock_ftp_instance.connect.side_effect = Exception("Connection failed")
        mock_ftp.return_value = mock_ftp_instance

        process_parameters = {
            "ftp_server": "ftp.example.com",
            "ftp_port": 21,
            "ftp_username": "user",
            "ftp_password": "pass",
            "ftp_folder": "/",
        }
        settings = {}

        with self.assertRaises(Exception):
            ftp_backend_do(process_parameters, settings, self.test_file)

        # Should be called multiple times due to retries
        self.assertGreater(mock_ftp_tls_instance.connect.call_count, 1)
