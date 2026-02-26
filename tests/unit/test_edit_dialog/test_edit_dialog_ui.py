"""UI Dialog Integration tests for EditFoldersDialog refactoring."""

import pytest
from unittest.mock import MagicMock, patch, call
from typing import Dict, Any, Optional, List, Callable

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from interface.models.folder_configuration import FolderConfiguration
from interface.operations.folder_data_extractor import FolderDataExtractor, ExtractedDialogFields
from interface.validation.folder_settings_validator import FolderSettingsValidator, ValidationResult
from interface.services.ftp_service import MockFTPService


class TestEditFoldersDialogClassAttributes:
    """Test suite for EditFoldersDialog class attributes."""
    
    def test_default_ftp_service_is_none(self):
        """Test that default FTP service is None."""
        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog
        
        assert EditFoldersDialog.DEFAULT_FTP_SERVICE is None
    
    def test_default_validator_class(self):
        """Test that default validator class is set."""
        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog
        
        assert EditFoldersDialog.DEFAULT_VALIDATOR_CLASS == FolderSettingsValidator
    
    def test_default_extractor_class(self):
        """Test that default extractor class is set."""
        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog
        
        assert EditFoldersDialog.DEFAULT_EXTRACTOR_CLASS == FolderDataExtractor


class TestFolderConfigurationFromExtractedFields:
    """Test suite for converting extracted fields to configuration."""
    
    def test_extracted_to_folder_configuration(self):
        """Test converting extracted fields to folder configuration."""
        extracted = ExtractedDialogFields(
            folder_name='/test/folder',
            alias='test-alias',
            folder_is_active='True',
            process_backend_ftp=True,
            ftp_server='ftp.example.com',
            ftp_port=21,
            ftp_folder='/uploads/',
            ftp_username='testuser',
            ftp_password='testpass',
            process_backend_email=True,
            email_to='test@example.com',
            email_subject_line='Test Subject'
        )
        
        # Create configuration from extracted fields
        config_data = {
            'folder_name': extracted.folder_name,
            'folder_is_active': extracted.folder_is_active,
            'alias': extracted.alias,
            'process_backend_ftp': extracted.process_backend_ftp,
            'ftp_server': extracted.ftp_server,
            'ftp_port': extracted.ftp_port,
            'ftp_folder': extracted.ftp_folder,
            'ftp_username': extracted.ftp_username,
            'ftp_password': extracted.ftp_password,
            'process_backend_email': extracted.process_backend_email,
            'email_to': extracted.email_to,
            'email_subject_line': extracted.email_subject_line
        }
        
        config = FolderConfiguration.from_dict(config_data)
        
        assert config.folder_name == '/test/folder'
        assert config.folder_is_active == 'True'
        assert config.alias == 'test-alias'
        assert config.process_backend_ftp is True
        assert config.ftp is not None
        assert config.ftp.server == 'ftp.example.com'
        assert config.ftp.port == 21
        assert config.process_backend_email is True
        assert config.email is not None
        assert config.email.recipients == 'test@example.com'
    
    def test_roundtrip_extracted_to_config_to_dict(self):
        """Test roundtrip: extracted -> config -> dict."""
        extracted = ExtractedDialogFields(
            folder_name='test_folder',
            ftp_server='ftp.example.com',
            ftp_port=990,
            ftp_folder='/secure/',
            ftp_username='admin',
            ftp_password='secret',
            email_to='user@example.com',
            email_subject_line='Invoice'
        )
        
        # Convert to dict format
        config_data = {
            'folder_name': extracted.folder_name,
            'ftp_server': extracted.ftp_server,
            'ftp_port': extracted.ftp_port,
            'ftp_folder': extracted.ftp_folder,
            'ftp_username': extracted.ftp_username,
            'ftp_password': extracted.ftp_password,
            'email_to': extracted.email_to,
            'email_subject_line': extracted.email_subject_line
        }
        
        # Create configuration
        config = FolderConfiguration.from_dict(config_data)
        
        # Convert back to dict
        result = config.to_dict()
        
        assert result['folder_name'] == 'test_folder'
        assert result['ftp_server'] == 'ftp.example.com'
        assert result['ftp_port'] == 990
        assert result['ftp_folder'] == '/secure/'
        assert result['email_to'] == 'user@example.com'


class TestValidationWithExtractedFields:
    """Test suite for validation with extracted fields."""
    
    def test_validate_ftp_extracted_fields(self):
        """Test validating FTP settings from extracted fields."""
        validator = FolderSettingsValidator(
            ftp_service=MockFTPService(should_succeed=True),
            existing_aliases=[]
        )
        
        result = validator.validate_ftp_settings(
            server='ftp.example.com',
            port='21',
            folder='/uploads/',
            username='testuser',
            password='testpass',
            enabled=True
        )
        
        assert result.is_valid is True
    
    def test_validate_email_extracted_fields(self):
        """Test validating email settings from extracted fields."""
        validator = FolderSettingsValidator(
            ftp_service=MockFTPService(should_succeed=True),
            existing_aliases=[]
        )
        
        result = validator.validate_email_settings(
            recipients='test@example.com, other@example.com',
            enabled=True
        )
        
        assert result.is_valid is True
    
    def test_validate_alias_extracted_fields(self):
        """Test validating alias from extracted fields."""
        validator = FolderSettingsValidator(
            ftp_service=MockFTPService(should_succeed=True),
            existing_aliases=['existing_alias']
        )
        
        # Should fail - alias already exists
        result = validator.validate_alias(
            alias='existing_alias',
            folder_name='new_folder',
            current_alias='different'
        )
        
        assert result.is_valid is False
    
    def test_validate_alias_allows_editing(self):
        """Test that editing current alias is allowed."""
        validator = FolderSettingsValidator(
            ftp_service=MockFTPService(should_succeed=True),
            existing_aliases=['my_alias']
        )
        
        # Should pass - same as current
        result = validator.validate_alias(
            alias='my_alias',
            folder_name='new_folder',
            current_alias='my_alias'
        )
        
        assert result.is_valid is True


class TestDialogValidationFlow:
    """Test suite for dialog validation flow."""
    
    def test_validation_result_structure(self):
        """Test ValidationResult structure."""
        result = ValidationResult()
        
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
    
    def test_validation_result_with_errors(self):
        """Test ValidationResult with errors."""
        result = ValidationResult()
        result.add_error("ftp_server", "Server is required")
        result.add_error("ftp_port", "Port must be a number")
        
        assert result.is_valid is False
        assert len(result.errors) == 2
        assert result.errors[0].field == "ftp_server"
        assert result.errors[0].message == "Server is required"
    
    def test_validation_result_with_warnings(self):
        """Test ValidationResult with warnings."""
        result = ValidationResult()
        result.add_warning("folder_name", "Consider using a shorter name")
        
        assert result.is_valid is True  # Warnings don't invalidate
        assert len(result.warnings) == 1
    
    def test_get_all_messages(self):
        """Test getting all messages from ValidationResult."""
        result = ValidationResult()
        result.add_error("field1", "Error 1")
        result.add_warning("field2", "Warning 1")
        result.add_error("field3", "Error 2")
        
        messages = result.get_all_messages()
        
        assert len(messages) == 3
        assert "Error 1" in messages
        assert "Warning 1" in messages
        assert "Error 2" in messages


class TestMockFTPService:
    """Test suite for MockFTPService."""
    
    def test_successful_connection(self):
        """Test mock FTP service with successful connection."""
        mock_ftp = MockFTPService(should_succeed=True)
        
        # The mock should be configured to succeed
        assert mock_ftp.should_succeed is True
    
    def test_failed_connection(self):
        """Test mock FTP service with failed connection."""
        mock_ftp = MockFTPService(
            should_succeed=False,
            fail_at="login",
            error_message="Invalid credentials"
        )
        
        assert mock_ftp.should_succeed is False
        assert mock_ftp.fail_at == "login"
        assert mock_ftp.error_message == "Invalid credentials"


class TestExtractedDialogFieldsIntegration:
    """Test suite for extracted fields integration."""
    
    def test_all_identity_fields(self):
        """Test all identity fields are properly defined."""
        fields = ExtractedDialogFields(
            folder_name='/path/to/folder',
            alias='my-alias',
            folder_is_active='True'
        )
        
        assert fields.folder_name == '/path/to/folder'
        assert fields.alias == 'my-alias'
        assert fields.folder_is_active == 'True'
    
    def test_all_backend_toggles(self):
        """Test all backend toggle fields."""
        fields = ExtractedDialogFields(
            process_backend_copy=True,
            process_backend_ftp=True,
            process_backend_email=False
        )
        
        assert fields.process_backend_copy is True
        assert fields.process_backend_ftp is True
        assert fields.process_backend_email is False
    
    def test_all_ftp_fields(self):
        """Test all FTP fields."""
        fields = ExtractedDialogFields(
            ftp_server='ftp.example.com',
            ftp_port=990,
            ftp_folder='/secure/',
            ftp_username='admin',
            ftp_password='secret'
        )
        
        assert fields.ftp_server == 'ftp.example.com'
        assert fields.ftp_port == 990
        assert fields.ftp_folder == '/secure/'
        assert fields.ftp_username == 'admin'
        assert fields.ftp_password == 'secret'
    
    def test_all_email_fields(self):
        """Test all email fields."""
        fields = ExtractedDialogFields(
            email_to='test@example.com, other@example.com',
            email_subject_line='Invoice Notification'
        )
        
        assert fields.email_to == 'test@example.com, other@example.com'
        assert fields.email_subject_line == 'Invoice Notification'
    
    def test_all_edi_fields(self):
        """Test all EDI fields."""
        fields = ExtractedDialogFields(
            process_edi='True',
            convert_to_format='csv',
            tweak_edi=True,
            split_edi=True,
            split_edi_include_invoices=True,
            split_edi_include_credits=False,
            prepend_date_files=True,
            rename_file='invoice_{date}.csv'
        )
        
        assert fields.process_edi == 'True'
        assert fields.convert_to_format == 'csv'
        assert fields.tweak_edi is True
        assert fields.split_edi is True
        assert fields.prepend_date_files is True
    
    def test_all_upc_override_fields(self):
        """Test all UPC override fields."""
        fields = ExtractedDialogFields(
            override_upc_bool=True,
            override_upc_level=2,
            override_upc_category_filter='1,2,3,ALL',
            upc_target_length=12
        )
        
        assert fields.override_upc_bool is True
        assert fields.override_upc_level == 2
        assert fields.override_upc_category_filter == '1,2,3,ALL'
        assert fields.upc_target_length == 12
    
    def test_all_invoice_date_fields(self):
        """Test all invoice date fields."""
        fields = ExtractedDialogFields(
            invoice_date_offset=5,
            invoice_date_custom_format=True,
            invoice_date_custom_format_string='%Y%m%d',
            retail_uom=True
        )
        
        assert fields.invoice_date_offset == 5
        assert fields.invoice_date_custom_format is True
        assert fields.invoice_date_custom_format_string == '%Y%m%d'
        assert fields.retail_uom is True


class TestFolderDataExtractorIntegration:
    """Test suite for FolderDataExtractor integration tests."""
    
    def test_extract_with_realistic_ftp_config(self):
        """Test extracting realistic FTP configuration."""
        fields = {
            'process_backend_ftp_check': self._mock_bool(True),
            'ftp_server_field': self._mock_text('ftp.company.com'),
            'ftp_port_field': self._mock_text('21'),
            'ftp_folder_field': self._mock_text('/incoming/'),
            'ftp_username_field': self._mock_text('ftp_user'),
            'ftp_password_field': self._mock_text('secure_pass'),
        }
        
        extractor = FolderDataExtractor(fields)
        extracted = extractor.extract_all()
        
        assert extracted.process_backend_ftp is True
        assert extracted.ftp_server == 'ftp.company.com'
        assert extracted.ftp_port == 21
        assert extracted.ftp_folder == '/incoming/'
        assert extracted.ftp_username == 'ftp_user'
        assert extracted.ftp_password == 'secure_pass'
    
    def test_extract_with_realistic_email_config(self):
        """Test extracting realistic email configuration."""
        fields = {
            'process_backend_email_check': self._mock_bool(True),
            'email_recepient_field': self._mock_text('billing@company.com'),
            'email_sender_subject_field': self._mock_text('Daily EDI Report'),
        }
        
        extractor = FolderDataExtractor(fields)
        extracted = extractor.extract_all()
        
        assert extracted.process_backend_email is True
        assert extracted.email_to == 'billing@company.com'
        assert extracted.email_subject_line == 'Daily EDI Report'
    
    def test_extract_with_edi_enabled(self):
        """Test extracting with EDI enabled."""
        fields = {
            'process_edi': self._mock_value('True'),
            'convert_formats_var': self._mock_value('csv'),
            'tweak_edi': self._mock_bool(True),
            'split_edi': self._mock_bool(False),
            'prepend_file_dates': self._mock_bool(False),
        }
        
        extractor = FolderDataExtractor(fields)
        extracted = extractor.extract_all()
        
        assert extracted.process_edi == 'True'
        assert extracted.convert_to_format == 'csv'
        assert extracted.tweak_edi is True
        assert extracted.split_edi is False
    
    def _mock_text(self, value):
        mock = MagicMock()
        mock.get.return_value = value
        return mock
    
    def _mock_value(self, value):
        mock = MagicMock()
        mock.get.return_value = value
        return mock
    
    def _mock_bool(self, value):
        mock = MagicMock()
        mock.get.return_value = value
        return mock


class TestFolderConfigurationIntegration:
    """Test suite for FolderConfiguration integration tests."""
    
    def test_full_ftp_configuration_roundtrip(self):
        """Test full FTP configuration roundtrip."""
        original_data = {
            'folder_name': 'ftp_incoming',
            'folder_is_active': 'True',
            'alias': 'ftp-main',
            'process_backend_ftp': True,
            'ftp_server': 'ftp.company.com',
            'ftp_port': 21,
            'ftp_username': 'user',
            'ftp_password': 'pass',
            'ftp_folder': '/incoming/'
        }
        
        config = FolderConfiguration.from_dict(original_data)
        result = config.to_dict()
        
        assert result['folder_name'] == 'ftp_incoming'
        assert result['folder_is_active'] == 'True'
        assert result['process_backend_ftp'] is True
        assert result['ftp_server'] == 'ftp.company.com'
        assert result['ftp_port'] == 21
        assert result['ftp_username'] == 'user'
        assert result['ftp_folder'] == '/incoming/'
    
    def test_full_email_configuration_roundtrip(self):
        """Test full email configuration roundtrip."""
        original_data = {
            'folder_name': 'email_reports',
            'process_backend_email': True,
            'email_to': 'reports@company.com',
            'email_subject_line': 'Daily Report'
        }
        
        config = FolderConfiguration.from_dict(original_data)
        result = config.to_dict()
        
        assert result['email_to'] == 'reports@company.com'
        assert result['email_subject_line'] == 'Daily Report'
    
    def test_full_edi_configuration_roundtrip(self):
        """Test full EDI configuration roundtrip."""
        original_data = {
            'folder_name': 'edi_processor',
            'process_edi': 'True',
            'convert_to_format': 'csv',
            'split_edi': True,
            'tweak_edi': True,
            'prepend_date_files': False
        }
        
        config = FolderConfiguration.from_dict(original_data)
        result = config.to_dict()
        
        assert result['process_edi'] == 'True'
        assert result['convert_to_format'] == 'csv'
        assert result['split_edi'] is True
        assert result['tweak_edi'] is True
    
    def test_with_upc_override(self):
        """Test configuration with UPC override."""
        original_data = {
            'folder_name': 'upc_config',
            'override_upc_bool': True,
            'override_upc_level': 2,
            'override_upc_category_filter': '1,2,3',
            'upc_target_length': 12
        }
        
        config = FolderConfiguration.from_dict(original_data)
        
        assert config.upc_override is not None
        assert config.upc_override.enabled is True
        assert config.upc_override.level == 2
        assert config.upc_override.category_filter == '1,2,3'
        
        result = config.to_dict()
        assert result['override_upc_bool'] is True
        assert result['override_upc_level'] == 2
