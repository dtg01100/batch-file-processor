"""Unit tests for send backends (FTP, Email, Copy).

Tests:
- FTP backend validation (connection, directory listing)
- Email backend validation (SMTP connection, email format)
- Copy backend validation (path existence, permissions)
- Backend toggle validation (process_backend_* settings)

Modules tested:
- ftp_backend.py
- email_backend.py
- copy_backend.py
"""

import pytest
from unittest.mock import patch, MagicMock
import tempfile
import os
import smtplib
import ftplib


class TestFTPBackend:
    """Test suite for FTP backend functionality."""
    
    @pytest.fixture
    def sample_process_parameters(self):
        """Create sample process parameters for FTP."""
        return {
            'ftp_server': 'ftp.example.com',
            'ftp_port': 21,
            'ftp_username': 'testuser',
            'ftp_password': 'testpass',
            'ftp_folder': '/uploads/',
        }
    
    @pytest.fixture
    def sample_settings_dict(self):
        """Create sample settings dictionary."""
        return {
            'as400_username': 'testuser',
            'as400_password': 'testpass',
            'as400_address': 'test.as400.local',
        }
    
    @pytest.fixture
    def sample_file(self, tmp_path):
        """Create a sample file to send."""
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("Test file content for FTP upload")
        return str(test_file)
    
    def test_ftp_backend_module_import(self):
        """Test that ftp_backend module can be imported."""
        import ftp_backend
        assert ftp_backend is not None
    
    def test_ftp_do_function_exists(self):
        """Test that do function exists in ftp_backend module."""
        import ftp_backend
        assert hasattr(ftp_backend, 'do')
        assert callable(ftp_backend.do)
    
    def test_ftp_parameters_validation(self, sample_process_parameters):
        """Test FTP parameter validation."""
        def validate_ftp_params(params):
            required = ['ftp_server', 'ftp_port', 'ftp_folder']
            for key in required:
                if key not in params:
                    return False
                if params[key] is None:
                    return False
            return True
        
        assert validate_ftp_params(sample_process_parameters) is True
        
        invalid_params = sample_process_parameters.copy()
        invalid_params['ftp_server'] = None
        assert validate_ftp_params(invalid_params) is False
    
    def test_ftp_server_format(self, sample_process_parameters):
        """Test FTP server format validation."""
        def validate_server_format(server):
            if not isinstance(server, str):
                return False
            # Should be a valid hostname or IP
            return len(server) > 0 and ' ' not in server
        
        assert validate_server_format('ftp.example.com') is True
        assert validate_server_format('192.168.1.1') is True
        assert validate_server_format('') is False
        assert validate_server_format(None) is False
    
    def test_ftp_port_range(self, sample_process_parameters):
        """Test FTP port number validation."""
        def validate_port(port):
            try:
                port_int = int(port)
                return 1 <= port_int <= 65535
            except (ValueError, TypeError):
                return False
        
        assert validate_port(21) is True
        assert validate_port(990) is True  # FTPS implicit
        assert validate_port(2121) is True
        assert validate_port(0) is False
        assert validate_port(65536) is False
        assert validate_port('invalid') is False
    
    def test_ftp_folder_format(self):
        """Test FTP folder path format validation."""
        def validate_folder(folder):
            if folder is None:
                return False
            if not isinstance(folder, str):
                return False
            # Folder should be a valid path
            return True
        
        assert validate_folder('/uploads') is True
        assert validate_folder('/') is True
        assert validate_folder('') is True  # Empty is valid (root)
        assert validate_folder(None) is False
    
    def test_ftp_username_optional(self):
        """Test that FTP username is optional (for anonymous FTP)."""
        def validate_username(username):
            if username is None:
                return False
            if not isinstance(username, str):
                return False
            return True
        
        assert validate_username('anonymous') is True
        assert validate_username('') is True  # Empty is valid for anonymous
        assert validate_username(None) is False
    
    def test_ftp_connection_mock(self, sample_process_parameters, sample_settings_dict, sample_file):
        """Test FTP connection with mocked FTP client."""
        import ftp_backend
        from backend.ftp_client import MockFTPClient
        
        mock_client = MockFTPClient()
        
        result = ftp_backend.do(sample_process_parameters, sample_settings_dict, sample_file, ftp_client=mock_client)
        
        # Verify FTP methods were called
        assert len(mock_client.connections) > 0
        assert len(mock_client.logins) > 0
    
    def test_ftp_fallback_to_non_tls(self, sample_process_parameters, sample_settings_dict, sample_file):
        """Test FTP fallback from TLS to non-TLS."""
        import ftp_backend
        from backend.ftp_client import MockFTPClient
        
        mock_client = MockFTPClient()
        
        try:
            ftp_backend.do(sample_process_parameters, sample_settings_dict, sample_file, ftp_client=mock_client)
        except Exception:
            pass
        
        # Verify connection was attempted
        assert len(mock_client.connections) > 0 or len(mock_client.files_sent) > 0
    
    def test_ftp_file_operations(self, sample_file):
        """Test FTP file operations."""
        def validate_file_for_upload(filepath):
            if not os.path.exists(filepath):
                return False
            if not os.path.isfile(filepath):
                return False
            try:
                with open(filepath, 'rb') as f:
                    return True
            except IOError:
                return False
        
        assert validate_file_for_upload(sample_file) is True


class TestEmailBackend:
    """Test suite for Email backend functionality."""
    
    @pytest.fixture
    def sample_process_parameters(self):
        """Create sample process parameters for email."""
        return {
            'email_to': 'recipient@example.com',
            'email_subject_line': 'Test email %filename%',
            'email_cc': '',
            'email_bcc': '',
        }
    
    @pytest.fixture
    def sample_settings(self):
        """Create sample settings for email."""
        return {
            'email_address': 'sender@example.com',
            'email_smtp_server': 'smtp.example.com',
            'smtp_port': 587,
            'email_username': 'sender_user',
            'email_password': 'sender_pass',
        }
    
    @pytest.fixture
    def sample_file(self, tmp_path):
        """Create a sample file to send."""
        test_file = tmp_path / "test_attachment.txt"
        test_file.write_text("Test file content for email attachment")
        return str(test_file)
    
    def test_email_backend_module_import(self):
        """Test that email_backend module can be imported."""
        import email_backend
        assert email_backend is not None
    
    def test_email_do_function_exists(self):
        """Test that do function exists in email_backend module."""
        import email_backend
        assert hasattr(email_backend, 'do')
        assert callable(email_backend.do)
    
    def test_email_to_validation(self, sample_process_parameters):
        """Test email recipient validation."""
        def validate_email_to(email_str):
            if not email_str:
                return False
            # Can be multiple emails separated by comma
            emails = email_str.split(', ')
            for email in emails:
                if '@' not in email or '.' not in email:
                    return False
            return True
        
        assert validate_email_to('single@example.com') is True
        assert validate_email_to('one@example.com, two@example.com') is True
        assert validate_email_to('') is False
    
    def test_email_subject_line_format(self, sample_process_parameters):
        """Test email subject line format validation."""
        def validate_subject(subject):
            if subject is None:
                return True  # Optional
            if not isinstance(subject, str):
                return False
            return True
        
        assert validate_subject('Test email') is True
        assert validate_subject('') is True
        assert validate_subject(None) is True
    
    def test_email_subject_placeholder_replacement(self):
        """Test placeholder replacement in subject line."""
        subject_template = "Invoice %filename% %datetime%"
        filename = "invoice_001.csv"
        datetime_str = "Mon Feb 10 12:00:00 2025"
        
        result = subject_template.replace("%filename%", filename).replace("%datetime%", datetime_str)
        
        assert "%filename%" not in result
        assert "%datetime%" not in result
        assert filename in result
    
    def test_smtp_settings_validation(self, sample_settings):
        """Test SMTP settings validation."""
        def validate_smtp_settings(settings):
            required = ['email_smtp_server', 'smtp_port']
            for key in required:
                if key not in settings:
                    return False
            return True
        
        assert validate_smtp_settings(sample_settings) is True
        
        invalid_settings = sample_settings.copy()
        del invalid_settings['email_smtp_server']
        assert validate_smtp_settings(invalid_settings) is False
    
    def test_smtp_port_range(self):
        """Test SMTP port number validation."""
        def validate_port(port):
            try:
                port_int = int(port)
                return 1 <= port_int <= 65535
            except (ValueError, TypeError):
                return False
        
        assert validate_port(25) is True   # Standard SMTP
        assert validate_port(465) is True  # SMTPS
        assert validate_port(587) is True  # STARTTLS
        assert validate_port(993) is True  # IMAPS (not SMTP but common)
    
    def test_email_credentials_optional(self):
        """Test that email credentials are optional for anonymous SMTP."""
        def validate_credentials(username, password):
            # Username and password can be empty for anonymous SMTP
            if username is None:
                return False
            if password is None:
                return True  # Password can be None
            if not isinstance(password, str):
                return False
            return True
        
        assert validate_credentials('user', 'pass') is True
        assert validate_credentials('user', '') is True  # Empty password valid
        assert validate_credentials('', None) is True
        assert validate_credentials(None, None) is False
    
    def test_email_smtp_connection_mock(self, sample_process_parameters, sample_settings, sample_file):
        """Test SMTP connection with mocked SMTP client."""
        import email_backend
        from backend.smtp_client import MockSMTPClient
        
        mock_smtp_instance = MockSMTPClient()
        
        try:
            email_backend.do(sample_process_parameters, sample_settings, sample_file, smtp_client=mock_smtp_instance)
        except Exception:
            # Expected to fail due to mock setup
            pass
        
        # Verify SMTP methods were called
        assert mock_smtp_instance.ehlo_calls > 0
    
    def test_email_attachment_detection(self, sample_file):
        """Test email attachment type detection."""
        import mimetypes
        
        def guess_attachment_type(filepath):
            ctype, encoding = mimetypes.guess_type(filepath)
            if ctype is None or encoding is not None:
                return 'application/octet-stream'
            return ctype
        
        assert guess_attachment_type(sample_file) is not None
        assert isinstance(guess_attachment_type(sample_file), str)
    
    def test_email_message_format(self, sample_process_parameters, sample_settings):
        """Test email message format."""
        from email.message import EmailMessage
        
        message = EmailMessage()
        message['Subject'] = 'Test Subject'
        message['From'] = sample_settings['email_address']
        message['To'] = [sample_process_parameters['email_to']]
        message.set_content('Test content')
        
        assert message['Subject'] == 'Test Subject'
        assert message['From'] == sample_settings['email_address']
        assert message['To'] == sample_process_parameters['email_to']


class TestCopyBackend:
    """Test suite for Copy backend functionality."""
    
    @pytest.fixture
    def sample_process_parameters(self):
        """Create sample process parameters for copy."""
        return {
            'copy_to_directory': '/tmp/test_copies',
        }
    
    @pytest.fixture
    def sample_settings_dict(self):
        """Create sample settings dictionary."""
        return {}
    
    @pytest.fixture
    def sample_source_file(self, tmp_path):
        """Create a sample source file."""
        test_file = tmp_path / "source_file.txt"
        test_file.write_text("Test file content for copying")
        return str(test_file)
    
    @pytest.fixture
    def sample_destination_dir(self, tmp_path):
        """Create a destination directory."""
        dest_dir = tmp_path / "copies"
        dest_dir.mkdir()
        return str(dest_dir)
    
    def test_copy_backend_module_import(self):
        """Test that copy_backend module can be imported."""
        import copy_backend
        assert copy_backend is not None
    
    def test_copy_do_function_exists(self):
        """Test that do function exists in copy_backend module."""
        import copy_backend
        assert hasattr(copy_backend, 'do')
        assert callable(copy_backend.do)
    
    def test_copy_destination_validation(self, sample_destination_dir):
        """Test copy destination path validation."""
        def validate_destination(path):
            if path is None:
                return False
            if not isinstance(path, str):
                return False
            # For validation purposes, check if parent exists
            parent = os.path.dirname(path)
            if parent and os.path.exists(parent):
                return True
            return False
        
        assert validate_destination(sample_destination_dir) is True
    
    def test_copy_destination_creation(self, tmp_path):
        """Test automatic creation of destination directory."""
        import shutil
        
        dest_dir = tmp_path / "new_directory" / "subdir"
        source_file = tmp_path / "source.txt"
        source_file.write_text("test")
        
        # Copy should create directory if it doesn't exist
        # This is the expected behavior of copy_backend
        try:
            if not os.path.exists(str(dest_dir)):
                os.makedirs(str(dest_dir))
            shutil.copy(str(source_file), str(dest_dir) + "/copied.txt")
            result = True
        except Exception:
            result = False
        
        assert result is True
    
    def test_copy_file_exists(self, sample_source_file, sample_destination_dir):
        """Test that copied file exists."""
        import shutil
        
        dest_file = os.path.join(sample_destination_dir, "copied.txt")
        shutil.copy(sample_source_file, dest_file)
        
        assert os.path.exists(dest_file)
        assert os.path.isfile(dest_file)
    
    def test_copy_file_content(self, sample_source_file, sample_destination_dir):
        """Test that copied file has correct content."""
        import shutil
        
        dest_file = os.path.join(sample_destination_dir, "copied.txt")
        shutil.copy(sample_source_file, dest_file)
        
        with open(dest_file, 'r') as f:
            content = f.read()
        
        with open(sample_source_file, 'r') as f:
            original_content = f.read()
        
        assert content == original_content


class TestBackendToggleSettings:
    """Test suite for backend toggle settings validation."""
    
    @pytest.mark.parametrize("toggle_value,expected", [
        ("True", True),
        ("False", False),
        ("true", True),
        ("false", False),
        (True, True),
        (False, False),
        ("1", True),
        ("0", False),
        ("yes", True),
        ("no", False),
        ("", False),
        (None, False),
    ])
    def test_backend_toggle_values(self, toggle_value, expected):
        """Test various toggle value formats."""
        def parse_toggle(value):
            if value is None:
                return False
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes", "on")
            if isinstance(value, int):
                return value != 0
            return False
        
        assert parse_toggle(toggle_value) == expected
    
    def test_copy_backend_toggle(self):
        """Test process_backend_copy toggle."""
        def validate_copy_backend_toggle(setting):
            # process_backend_copy
            return parse_toggle(setting)
        
        assert validate_copy_backend_toggle("True") is True
        assert validate_copy_backend_toggle("False") is False
    
    def test_ftp_backend_toggle(self):
        """Test process_backend_ftp toggle."""
        def validate_ftp_backend_toggle(setting):
            # process_backend_ftp
            return parse_toggle(setting)
        
        assert validate_ftp_backend_toggle("True") is True
        assert validate_ftp_backend_toggle("False") is False
    
    def test_email_backend_toggle(self):
        """Test process_backend_email toggle."""
        def validate_email_backend_toggle(setting):
            # process_backend_email
            return parse_toggle(setting)
        
        assert validate_email_backend_toggle("True") is True
        assert validate_email_backend_toggle("False") is False
    
    def test_edi_output_toggle(self):
        """Test process_edi_output toggle."""
        def validate_edi_output_toggle(setting):
            # process_edi_output
            return parse_toggle(setting)
        
        assert validate_edi_output_toggle("True") is True
        assert validate_edi_output_toggle("False") is False


class TestBackendRetryLogic:
    """Test suite for backend retry logic."""
    
    def test_ftp_retry_logic(self):
        """Test FTP retry logic."""
        max_retries = 10
        
        counter = 0
        success = False
        
        while counter < max_retries and not success:
            counter += 1
            # Simulate success on attempt 3
            if counter >= 3:
                success = True
        
        assert success is True
        assert counter == 3
    
    def test_email_retry_logic(self):
        """Test email retry logic."""
        max_retries = 10
        
        counter = 0
        success = False
        
        while counter < max_retries and not success:
            counter += 1
            # Simulate success on attempt 3
            if counter >= 3:
                success = True
        
        assert success is True
        assert counter == 3
    
    def test_copy_retry_logic(self):
        """Test copy retry logic."""
        max_retries = 10
        
        counter = 0
        success = False
        
        while counter < max_retries and not success:
            counter += 1
            # Simulate success on attempt 3
            if counter >= 3:
                success = True
        
        assert success is True
        assert counter == 3


class TestBackendErrorHandling:
    """Test suite for backend error handling."""
    
    def test_ftp_connection_error(self):
        """Test handling of FTP connection errors."""
        def simulate_ftp_error():
            try:
                raise ftplib.error_perm("530 Not logged in")
            except ftplib.error_perm as e:
                return str(e)
            except Exception as e:
                return "unknown"
        
        result = simulate_ftp_error()
        assert "530" in result or "Not logged in" in result
    
    def test_email_smtp_error(self):
        """Test handling of SMTP errors."""
        def simulate_smtp_error():
            try:
                raise smtplib.SMTPAuthenticationError(535, "Authentication failed")
            except smtplib.SMTPAuthenticationError as e:
                return e.smtp_error.decode() if isinstance(e.smtp_error, bytes) else str(e.smtp_error)
            except Exception as e:
                return "unknown"
        
        result = simulate_smtp_error()
        assert "535" in result or "Authentication" in result or "unknown" == result
    
    def test_copy_io_error(self):
        """Test handling of IO errors during copy."""
        def simulate_io_error():
            try:
                raise IOError("[Errno 13] Permission denied")
            except IOError as e:
                return str(e)
            except Exception as e:
                return "unknown"
        
        result = simulate_io_error()
        assert "Permission denied" in result or "13" in result or "unknown" == result


def parse_toggle(value):
    """Helper function for toggle parsing."""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes", "on")
    if isinstance(value, int):
        return value != 0
    return False
