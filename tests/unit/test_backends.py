import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, mock_open, patch

import pytest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

import copy_backend
import email_backend
import ftp_backend


class TestCopyBackend(unittest.TestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(delete=False)
        self.temp_file.write(b"test content")
        self.temp_file.close()

        self.process_params = {
            "copy_to_directory": "/tmp/dest",
        }
        self.settings = {}

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    def test_plugin_metadata(self):
        assert copy_backend.CopySendBackend.PLUGIN_ID == "copy"
        assert copy_backend.CopySendBackend.PLUGIN_NAME == "Copy to Directory"
        assert len(copy_backend.CopySendBackend.CONFIG_FIELDS) > 0

    @patch("shutil.copy")
    def test_copy_backend_do(self, mock_copy):
        copy_backend.do(self.process_params, self.settings, self.temp_file.name)
        mock_copy.assert_called_once_with(self.temp_file.name, "/tmp/dest")

    @patch("shutil.copy")
    def test_copy_backend_instance(self, mock_copy):
        backend = copy_backend.CopySendBackend(
            self.process_params, self.settings, self.temp_file.name
        )
        backend.send()
        mock_copy.assert_called_once()

    @patch("shutil.copy")
    def test_copy_backend_get_config_value(self, mock_copy):
        backend = copy_backend.CopySendBackend(
            self.process_params, self.settings, self.temp_file.name
        )
        dest = backend.get_config_value("copy_to_directory", "")
        assert dest == "/tmp/dest"


class TestEmailBackend(unittest.TestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
        self.temp_file.write(b"test content")
        self.temp_file.close()

        self.process_params = {
            "email_to": "test@example.com",
            "email_cc": "",
            "email_subject_line": "Test Subject",
        }
        self.settings = {
            "email_address": "from@example.com",
            "email_smtp_server": "smtp.example.com",
            "smtp_port": "587",
            "email_username": "user",
            "email_password": "pass",
        }

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    def test_plugin_metadata(self):
        assert email_backend.EmailSendBackend.PLUGIN_ID == "email"
        assert email_backend.EmailSendBackend.PLUGIN_NAME == "Email Delivery"
        assert len(email_backend.EmailSendBackend.CONFIG_FIELDS) > 0

    @patch("smtplib.SMTP")
    def test_email_backend_do(self, mock_smtp):
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server

        email_backend.do(self.process_params, self.settings, self.temp_file.name)

        mock_smtp.assert_called_once()
        mock_server.ehlo.assert_called_once()
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user", "pass")
        mock_server.send_message.assert_called_once()
        mock_server.close.assert_called_once()

    @patch("smtplib.SMTP")
    def test_email_backend_subject_with_template(self, mock_smtp):
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server

        self.process_params["email_subject_line"] = "File: %filename% at %datetime%"
        email_backend.do(self.process_params, self.settings, self.temp_file.name)

        mock_server.send_message.assert_called_once()
        call_args = mock_server.send_message.call_args[0][0]
        assert os.path.basename(self.temp_file.name) in call_args["Subject"]

    @patch("smtplib.SMTP")
    def test_email_backend_no_auth(self, mock_smtp):
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server

        self.settings["email_username"] = ""
        self.settings["email_password"] = ""

        email_backend.do(self.process_params, self.settings, self.temp_file.name)

        mock_server.login.assert_not_called()
        mock_server.send_message.assert_called_once()

    @patch("smtplib.SMTP")
    def test_email_backend_multiple_recipients(self, mock_smtp):
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server

        self.process_params["email_to"] = "test1@example.com, test2@example.com"
        email_backend.do(self.process_params, self.settings, self.temp_file.name)

        mock_server.send_message.assert_called_once()
        call_args = mock_server.send_message.call_args[0][0]
        assert "To" in call_args


class TestFTPBackend(unittest.TestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(delete=False)
        self.temp_file.write(b"test content")
        self.temp_file.close()

        self.process_params = {
            "ftp_server": "ftp.example.com",
            "ftp_port": 21,
            "ftp_username": "user",
            "ftp_password": "pass",
            "ftp_folder": "/remote/path/",
            "ftp_passive": True,
        }
        self.settings = {}

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    def test_plugin_metadata(self):
        assert ftp_backend.FTPSendBackend.PLUGIN_ID == "ftp"
        assert ftp_backend.FTPSendBackend.PLUGIN_NAME == "FTP Transfer"
        assert len(ftp_backend.FTPSendBackend.CONFIG_FIELDS) > 0

    @patch("ftplib.FTP_TLS")
    def test_ftp_backend_do_with_tls(self, mock_ftp_tls):
        mock_ftp = MagicMock()
        mock_ftp_tls.return_value = mock_ftp

        ftp_backend.do(self.process_params, self.settings, self.temp_file.name)

        mock_ftp_tls.assert_called_once()
        mock_ftp.connect.assert_called_once_with("ftp.example.com", 21)
        mock_ftp.login.assert_called_once_with("user", "pass")
        mock_ftp.storbinary.assert_called_once()
        mock_ftp.close.assert_called_once()

    @patch("ftplib.FTP")
    @patch("ftplib.FTP_TLS")
    def test_ftp_backend_fallback_to_non_tls(self, mock_ftp_tls, mock_ftp):
        mock_tls_instance = MagicMock()
        mock_tls_instance.connect.side_effect = Exception("TLS not supported")
        mock_ftp_tls.return_value = mock_tls_instance

        mock_ftp_instance = MagicMock()
        mock_ftp.return_value = mock_ftp_instance

        ftp_backend.do(self.process_params, self.settings, self.temp_file.name)

        mock_ftp_tls.assert_called_once()
        mock_ftp.assert_called_once()
        mock_ftp_instance.connect.assert_called_once()
        mock_ftp_instance.login.assert_called_once()
        mock_ftp_instance.close.assert_called_once()

    @patch("ftplib.FTP")
    @patch("ftplib.FTP_TLS")
    def test_ftp_backend_both_fail_raises_exception(self, mock_ftp_tls, mock_ftp):
        mock_tls_instance = MagicMock()
        mock_tls_instance.connect.side_effect = Exception("TLS failed")
        mock_ftp_tls.return_value = mock_tls_instance

        mock_ftp_instance = MagicMock()
        mock_ftp_instance.connect.side_effect = Exception("FTP failed")
        mock_ftp.return_value = mock_ftp_instance

        with self.assertRaises(Exception):
            ftp_backend.do(self.process_params, self.settings, self.temp_file.name)

    @patch("ftplib.FTP_TLS")
    def test_ftp_backend_custom_port(self, mock_ftp_tls):
        mock_ftp = MagicMock()
        mock_ftp_tls.return_value = mock_ftp

        self.process_params["ftp_port"] = 2121
        ftp_backend.do(self.process_params, self.settings, self.temp_file.name)

        mock_ftp.connect.assert_called_once_with("ftp.example.com", 2121)


if __name__ == "__main__":
    unittest.main()
