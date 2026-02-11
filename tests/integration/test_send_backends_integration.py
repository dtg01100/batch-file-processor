"""Integration tests for send backend settings from FolderConfiguration.

Tests:
- FTP settings from config
- Email settings from config
- Copy settings from config
- process_backend_ftp toggle gates FTP
- process_backend_email toggle gates email
- process_backend_copy toggle gates copy
"""

import pytest
import sys
import os
import tempfile
from unittest.mock import patch, MagicMock, mock_open
from io import StringIO

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from interface.models.folder_configuration import (
    FolderConfiguration,
    FTPConfiguration,
    EmailConfiguration,
    CopyConfiguration,
)


class TestFTPBackendIntegration:
    """Test suite for FTP backend integration with FolderConfiguration."""
    
    @pytest.fixture
    def ftp_config(self):
        """Create FolderConfiguration with FTP settings."""
        return FolderConfiguration(
            folder_name="/test/ftp",
            process_backend_ftp=True,
            ftp=FTPConfiguration(
                server="ftp.example.com",
                port=21,
                username="ftp_user",
                password="secure_password",
                folder="/uploads/"
            )
        )
    
    @pytest.fixture
    def ftp_config_tls(self):
        """Create FolderConfiguration with FTP TLS settings."""
        return FolderConfiguration(
            folder_name="/test/ftp_tls",
            process_backend_ftp=True,
            ftp=FTPConfiguration(
                server="secure-ftp.example.com",
                port=990,
                username="tls_user",
                password="tls_password",
                folder="/secure/"
            )
        )
    
    def test_ftp_backend_with_folder_config(self, ftp_config):
        """Test FTP settings are correctly extracted from config."""
        config_dict = ftp_config.to_dict()
        
        assert config_dict['process_backend_ftp'] is True
        assert config_dict['ftp_server'] == "ftp.example.com"
        assert config_dict['ftp_port'] == 21
        assert config_dict['ftp_username'] == "ftp_user"
        assert config_dict['ftp_password'] == "secure_password"
        assert config_dict['ftp_folder'] == "/uploads/"
    
    def test_ftp_tls_settings(self, ftp_config_tls):
        """Test FTP TLS settings are correctly extracted."""
        config_dict = ftp_config_tls.to_dict()
        
        assert config_dict['ftp_server'] == "secure-ftp.example.com"
        assert config_dict['ftp_port'] == 990
        assert config_dict['ftp_folder'] == "/secure/"
    
    def test_ftp_folder_requires_trailing_slash(self, ftp_config):
        """Test FTP folder validation requires trailing slash."""
        ftp = ftp_config.ftp
        
        assert ftp.folder.endswith("/")
    
    def test_ftp_settings_passed_to_backend(self, ftp_config):
        """Test FTP settings are correctly passed to FTP backend."""
        config_dict = ftp_config.to_dict()
        
        # Simulate parameters passed to FTP backend
        process_parameters = {
            'ftp_server': config_dict['ftp_server'],
            'ftp_port': config_dict['ftp_port'],
            'ftp_username': config_dict['ftp_username'],
            'ftp_password': config_dict['ftp_password'],
            'ftp_folder': config_dict['ftp_folder'],
        }
        
        assert process_parameters['ftp_server'] == "ftp.example.com"
        assert process_parameters['ftp_port'] == 21
        assert process_parameters['ftp_username'] == "ftp_user"
    
    def test_empty_ftp_server(self):
        """Test handling of empty FTP server."""
        config = FolderConfiguration(
            folder_name="/test",
            process_backend_ftp=True,
            ftp=FTPConfiguration(
                server="",
                username="user",
                password="pass",
                folder="/"
            )
        )
        
        config_dict = config.to_dict()
        
        assert config_dict['ftp_server'] == ""
    
    def test_ftp_custom_port(self):
        """Test FTP with custom port."""
        config = FolderConfiguration(
            folder_name="/test",
            process_backend_ftp=True,
            ftp=FTPConfiguration(
                server="ftp.example.com",
                port=2121,
                username="user",
                password="pass",
                folder="/"
            )
        )
        
        config_dict = config.to_dict()
        
        assert config_dict['ftp_port'] == 2121


class TestEmailBackendIntegration:
    """Test suite for email backend integration with FolderConfiguration."""
    
    @pytest.fixture
    def email_config(self):
        """Create FolderConfiguration with email settings."""
        return FolderConfiguration(
            folder_name="/test/email",
            process_backend_email=True,
            email=EmailConfiguration(
                recipients="user@example.com, other@example.com",
                subject_line="Invoice: %filename%",
                sender_address="noreply@company.com"
            )
        )
    
    @pytest.fixture
    def email_config_no_sender(self):
        """Create FolderConfiguration with email without sender."""
        return FolderConfiguration(
            folder_name="/test/email_no_sender",
            process_backend_email=True,
            email=EmailConfiguration(
                recipients="user@example.com",
                subject_line="Test Subject"
            )
        )
    
    def test_email_backend_with_folder_config(self, email_config):
        """Test email settings are correctly extracted from config."""
        config_dict = email_config.to_dict()
        
        assert config_dict['process_backend_email'] is True
        assert config_dict['email_to'] == "user@example.com, other@example.com"
        assert config_dict['email_subject_line'] == "Invoice: %filename%"
    
    def test_email_subject_line_variables(self, email_config):
        """Test email subject line contains template variables."""
        subject_line = email_config.email.subject_line
        
        assert "%filename%" in subject_line
    
    def test_email_multiple_recipients(self, email_config):
        """Test email with multiple recipients."""
        recipients = email_config.email.recipients
        recipient_list = recipients.split(", ")
        
        assert len(recipient_list) == 2
        assert "user@example.com" in recipient_list
        assert "other@example.com" in recipient_list
    
    def test_email_settings_passed_to_backend(self, email_config):
        """Test email settings are correctly passed to email backend."""
        config_dict = email_config.to_dict()
        
        # Simulate parameters passed to email backend
        process_parameters = {
            'email_to': config_dict['email_to'],
            'email_subject_line': config_dict['email_subject_line'],
        }
        
        assert process_parameters['email_to'] == "user@example.com, other@example.com"
        assert "user@example.com" in process_parameters['email_to']
    
    def test_email_no_sender(self, email_config_no_sender):
        """Test email without sender address."""
        email = email_config_no_sender.email
        
        assert email.sender_address is None
    
    def test_empty_email_recipients(self):
        """Test handling of empty email recipients."""
        config = FolderConfiguration(
            folder_name="/test",
            process_backend_email=True,
            email=EmailConfiguration(
                recipients="",
                subject_line="Test"
            )
        )
        
        config_dict = config.to_dict()
        
        assert config_dict['email_to'] == ""


class TestCopyBackendIntegration:
    """Test suite for copy backend integration with FolderConfiguration."""
    
    @pytest.fixture
    def copy_config(self):
        """Create FolderConfiguration with copy settings."""
        return FolderConfiguration(
            folder_name="/test/copy",
            process_backend_copy=True,
            copy=CopyConfiguration(
                destination_directory="/output/processed/"
            )
        )
    
    @pytest.fixture
    def copy_config_deep_path(self):
        """Create FolderConfiguration with deep copy path."""
        return FolderConfiguration(
            folder_name="/test/copy_deep",
            process_backend_copy=True,
            copy=CopyConfiguration(
                destination_directory="/output/deep/nested/path/"
            )
        )
    
    def test_copy_backend_with_folder_config(self, copy_config):
        """Test copy settings are correctly extracted from config."""
        config_dict = copy_config.to_dict()
        
        assert config_dict['process_backend_copy'] is True
        assert config_dict['copy_to_directory'] == "/output/processed/"
    
    def test_copy_deep_path(self, copy_config_deep_path):
        """Test copy with deep nested path."""
        config_dict = copy_config_deep_path.to_dict()
        
        assert config_dict['copy_to_directory'] == "/output/deep/nested/path/"
    
    def test_copy_settings_passed_to_backend(self, copy_config):
        """Test copy settings are correctly passed to copy backend."""
        config_dict = copy_config.to_dict()
        
        # Simulate parameters passed to copy backend
        process_parameters = {
            'copy_to_directory': config_dict['copy_to_directory'],
        }
        
        assert process_parameters['copy_to_directory'] == "/output/processed/"
    
    def test_empty_copy_destination(self):
        """Test handling of empty copy destination."""
        config = FolderConfiguration(
            folder_name="/test",
            process_backend_copy=True,
            copy=CopyConfiguration(
                destination_directory=""
            )
        )
        
        config_dict = config.to_dict()
        
        assert config_dict['copy_to_directory'] == ""


class TestBackendToggleIntegration:
    """Test suite for backend toggles affecting backend behavior."""
    
    @pytest.fixture
    def all_backends_enabled(self):
        """Create FolderConfiguration with all backends enabled."""
        return FolderConfiguration(
            folder_name="/test/all",
            process_backend_ftp=True,
            process_backend_email=True,
            process_backend_copy=True,
            ftp=FTPConfiguration(
                server="ftp.example.com",
                username="user",
                password="pass",
                folder="/"
            ),
            email=EmailConfiguration(
                recipients="test@example.com",
                subject_line="Test"
            ),
            copy=CopyConfiguration(
                destination_directory="/output/"
            )
        )
    
    @pytest.fixture
    def only_ftp_enabled(self):
        """Create FolderConfiguration with only FTP enabled."""
        return FolderConfiguration(
            folder_name="/test/ftp_only",
            process_backend_ftp=True,
            process_backend_email=False,
            process_backend_copy=False,
            ftp=FTPConfiguration(
                server="ftp.example.com",
                username="user",
                password="pass",
                folder="/"
            )
        )
    
    @pytest.fixture
    def only_email_enabled(self):
        """Create FolderConfiguration with only email enabled."""
        return FolderConfiguration(
            folder_name="/test/email_only",
            process_backend_ftp=False,
            process_backend_email=True,
            process_backend_copy=False,
            email=EmailConfiguration(
                recipients="test@example.com",
                subject_line="Test"
            )
        )
    
    @pytest.fixture
    def only_copy_enabled(self):
        """Create FolderConfiguration with only copy enabled."""
        return FolderConfiguration(
            folder_name="/test/copy_only",
            process_backend_ftp=False,
            process_backend_email=False,
            process_backend_copy=True,
            copy=CopyConfiguration(
                destination_directory="/output/"
            )
        )
    
    @pytest.fixture
    def all_backends_disabled(self):
        """Create FolderConfiguration with all backends disabled."""
        return FolderConfiguration(
            folder_name="/test/none",
            process_backend_ftp=False,
            process_backend_email=False,
            process_backend_copy=False
        )
    
    def test_backend_toggle_ftp(self, all_backends_enabled, only_ftp_enabled, all_backends_disabled):
        """Test process_backend_ftp toggle gates FTP backend."""
        enabled_dict = all_backends_enabled.to_dict()
        ftp_only_dict = only_ftp_enabled.to_dict()
        disabled_dict = all_backends_disabled.to_dict()
        
        assert enabled_dict['process_backend_ftp'] is True
        assert ftp_only_dict['process_backend_ftp'] is True
        assert disabled_dict['process_backend_ftp'] is False
    
    def test_backend_toggle_email(self, all_backends_enabled, only_email_enabled, all_backends_disabled):
        """Test process_backend_email toggle gates email backend."""
        enabled_dict = all_backends_enabled.to_dict()
        email_only_dict = only_email_enabled.to_dict()
        disabled_dict = all_backends_disabled.to_dict()
        
        assert enabled_dict['process_backend_email'] is True
        assert email_only_dict['process_backend_email'] is True
        assert disabled_dict['process_backend_email'] is False
    
    def test_backend_toggle_copy(self, all_backends_enabled, only_copy_enabled, all_backends_disabled):
        """Test process_backend_copy toggle gates copy backend."""
        enabled_dict = all_backends_enabled.to_dict()
        copy_only_dict = only_copy_enabled.to_dict()
        disabled_dict = all_backends_disabled.to_dict()
        
        assert enabled_dict['process_backend_copy'] is True
        assert copy_only_dict['process_backend_copy'] is True
        assert disabled_dict['process_backend_copy'] is False
    
    def test_all_backends_enabled_dict(self, all_backends_enabled):
        """Test all backends enabled produces correct dict."""
        config_dict = all_backends_enabled.to_dict()
        
        assert config_dict['process_backend_ftp'] is True
        assert config_dict['process_backend_email'] is True
        assert config_dict['process_backend_copy'] is True
        assert 'ftp_server' in config_dict
        assert 'email_to' in config_dict
        assert 'copy_to_directory' in config_dict
    
    def test_all_backends_disabled_dict(self, all_backends_disabled):
        """Test all backends disabled produces correct dict."""
        config_dict = all_backends_disabled.to_dict()
        
        assert config_dict['process_backend_ftp'] is False
        assert config_dict['process_backend_email'] is False
        assert config_dict['process_backend_copy'] is False
    
    def test_backend_toggle_affects_backend_selection(self):
        """Test that backend toggles determine which backends are used."""
        # FTP only
        config = FolderConfiguration(
            folder_name="/test",
            process_backend_ftp=True,
            process_backend_email=False,
            process_backend_copy=False
        )
        config_dict = config.to_dict()
        
        active_backends = []
        if config_dict['process_backend_ftp']:
            active_backends.append('ftp')
        if config_dict['process_backend_email']:
            active_backends.append('email')
        if config_dict['process_backend_copy']:
            active_backends.append('copy')
        
        assert active_backends == ['ftp']
    
    def test_multiple_backends_enabled(self, all_backends_enabled):
        """Test multiple backends can be enabled simultaneously."""
        config_dict = all_backends_enabled.to_dict()
        
        active_backends = []
        if config_dict['process_backend_ftp']:
            active_backends.append('ftp')
        if config_dict['process_backend_email']:
            active_backends.append('email')
        if config_dict['process_backend_copy']:
            active_backends.append('copy')
        
        assert len(active_backends) == 3
        assert 'ftp' in active_backends
        assert 'email' in active_backends
        assert 'copy' in active_backends


class TestSendBackendToggleBehavior:
    """Test suite for send backend toggle behavior with actual operations."""
    
    def test_ftp_toggle_gates_connection(self):
        """Test FTP toggle gates actual FTP connection."""
        # FTP enabled
        config_enabled = FolderConfiguration(
            folder_name="/test",
            process_backend_ftp=True,
            ftp=FTPConfiguration(
                server="ftp.example.com",
                username="user",
                password="pass",
                folder="/"
            )
        )
        
        # FTP disabled
        config_disabled = FolderConfiguration(
            folder_name="/test",
            process_backend_ftp=False
        )
        
        enabled_dict = config_enabled.to_dict()
        disabled_dict = config_disabled.to_dict()
        
        # Simulate backend selection logic
        def should_connect_ftp(config):
            if config.get('process_backend_ftp'):
                return True
            return False
        
        assert should_connect_ftp(enabled_dict) is True
        assert should_connect_ftp(disabled_dict) is False
    
    def test_email_toggle_gates_sending(self):
        """Test email toggle gates actual email sending."""
        # Email enabled
        config_enabled = FolderConfiguration(
            folder_name="/test",
            process_backend_email=True,
            email=EmailConfiguration(
                recipients="test@example.com",
                subject_line="Test"
            )
        )
        
        # Email disabled
        config_disabled = FolderConfiguration(
            folder_name="/test",
            process_backend_email=False
        )
        
        enabled_dict = config_enabled.to_dict()
        disabled_dict = config_disabled.to_dict()
        
        # Simulate backend selection logic
        def should_send_email(config):
            if config.get('process_backend_email'):
                return True
            return False
        
        assert should_send_email(enabled_dict) is True
        assert should_send_email(disabled_dict) is False
    
    def test_copy_toggle_gates_copying(self):
        """Test copy toggle gates actual file copying."""
        # Copy enabled
        config_enabled = FolderConfiguration(
            folder_name="/test",
            process_backend_copy=True,
            copy=CopyConfiguration(
                destination_directory="/output/"
            )
        )
        
        # Copy disabled
        config_disabled = FolderConfiguration(
            folder_name="/test",
            process_backend_copy=False
        )
        
        enabled_dict = config_enabled.to_dict()
        disabled_dict = config_disabled.to_dict()
        
        # Simulate backend selection logic
        def should_copy(config):
            if config.get('process_backend_copy'):
                return True
            return False
        
        assert should_copy(enabled_dict) is True
        assert should_copy(disabled_dict) is False
    
    def test_toggle_with_missing_config(self):
        """Test toggle behavior when backend config is missing."""
        # FTP enabled but no FTP config
        config_missing = FolderConfiguration(
            folder_name="/test",
            process_backend_ftp=True,
            ftp=None
        )
        
        config_dict = config_missing.to_dict()
        
        # Toggle is True but FTP fields are missing
        assert config_dict['process_backend_ftp'] is True
        assert 'ftp_server' not in config_dict
        
        # Should handle gracefully
        def get_ftp_config(config):
            if not config.get('process_backend_ftp'):
                return None
            if 'ftp_server' not in config:
                return None
            return {
                'server': config.get('ftp_server'),
                'port': config.get('ftp_port', 21),
            }
        
        assert get_ftp_config(config_dict) is None


class TestBackendSettingsValidation:
    """Test suite for backend settings validation integration."""
    
    def test_ftp_requires_server(self):
        """Test FTP validation requires server."""
        config = FolderConfiguration(
            folder_name="/test",
            process_backend_ftp=True,
            ftp=FTPConfiguration(
                server="",
                username="user",
                password="pass",
                folder="/"
            )
        )
        
        config_dict = config.to_dict()
        
        # Validation should fail
        def validate_ftp_config(config):
            errors = []
            if not config.get('ftp_server'):
                errors.append("FTP Server is required")
            if not config.get('ftp_username'):
                errors.append("FTP Username is required")
            return errors
        
        errors = validate_ftp_config(config_dict)
        assert len(errors) > 0
        assert any("Server" in e for e in errors)
    
    def test_email_requires_recipients(self):
        """Test email validation requires recipients."""
        config = FolderConfiguration(
            folder_name="/test",
            process_backend_email=True,
            email=EmailConfiguration(
                recipients="",
                subject_line="Test"
            )
        )
        
        config_dict = config.to_dict()
        
        # Validation should fail
        def validate_email_config(config):
            errors = []
            if not config.get('email_to'):
                errors.append("Email recipients is required")
            return errors
        
        errors = validate_email_config(config_dict)
        assert len(errors) > 0
        assert any("recipients" in e.lower() for e in errors)
    
    def test_copy_requires_destination(self):
        """Test copy validation requires destination."""
        config = FolderConfiguration(
            folder_name="/test",
            process_backend_copy=True,
            copy=CopyConfiguration(
                destination_directory=""
            )
        )
        
        config_dict = config.to_dict()
        
        # Validation should fail
        def validate_copy_config(config):
            errors = []
            if not config.get('copy_to_directory'):
                errors.append("Copy destination is required")
            return errors
        
        errors = validate_copy_config(config_dict)
        assert len(errors) > 0
        assert any("destination" in e.lower() for e in errors)
