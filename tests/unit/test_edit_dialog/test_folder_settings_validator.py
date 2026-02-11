"""Folder Settings Validator tests for EditFoldersDialog refactoring."""

import pytest
from unittest.mock import MagicMock

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from interface.validation.folder_settings_validator import (
    FolderSettingsValidator,
    ValidationResult,
    ValidationError,
)
from interface.services.ftp_service import MockFTPService


class TestFolderSettingsValidator:
    """Test suite for FolderSettingsValidator."""

    @pytest.fixture
    def mock_ftp_service(self):
        """Create mock FTP service for testing."""
        return MockFTPService(should_succeed=True)

    @pytest.fixture
    def validator(self, mock_ftp_service):
        """Create validator with mock dependencies."""
        return FolderSettingsValidator(
            ftp_service=mock_ftp_service,
            existing_aliases=["existing_alias", "another_alias"]
        )

    def test_validate_ftp_settings_valid(self, validator, mock_ftp_service):
        """Test valid FTP settings pass validation."""
        result = validator.validate_ftp_settings(
            server="ftp.example.com",
            port="21",
            folder="/uploads/",
            username="testuser",
            password="testpass",
            enabled=True
        )

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_ftp_settings_missing_server(self, validator):
        """Test validation fails when server is missing."""
        result = validator.validate_ftp_settings(
            server="",
            port="21",
            folder="/uploads/",
            username="testuser",
            password="testpass",
            enabled=True
        )

        assert result.is_valid is False
        assert any(e.field == "ftp_server" for e in result.errors)

    def test_validate_ftp_settings_invalid_port(self, validator):
        """Test validation fails when port is invalid."""
        result = validator.validate_ftp_settings(
            server="ftp.example.com",
            port="invalid",
            folder="/uploads/",
            username="testuser",
            password="testpass",
            enabled=True
        )

        assert result.is_valid is False
        assert any(e.field == "ftp_port" for e in result.errors)

    def test_validate_ftp_settings_missing_trailing_slash(self, validator):
        """Test validation fails when folder missing trailing slash."""
        result = validator.validate_ftp_settings(
            server="ftp.example.com",
            port="21",
            folder="uploads",
            username="testuser",
            password="testpass",
            enabled=True
        )

        assert result.is_valid is False
        assert any("end in" in e.message.lower() or "trailing" in e.message.lower() for e in result.errors)

    def test_validate_ftp_settings_disabled(self, validator):
        """Test validation passes when FTP is disabled."""
        result = validator.validate_ftp_settings(
            server="",
            port="",
            folder="",
            username="",
            password="",
            enabled=False
        )

        assert result.is_valid is True

    def test_validate_ftp_connection_failure(self):
        """Test validation fails when FTP connection fails."""
        # Create validator with mock FTP service that fails
        mock_ftp_service = MockFTPService(
            should_succeed=False,
            fail_at="login",
            error_message="FTP Username or Password Incorrect"
        )
        validator = FolderSettingsValidator(
            ftp_service=mock_ftp_service,
            existing_aliases=[]
        )

        result = validator.validate_ftp_settings(
            server="ftp.example.com",
            port="21",
            folder="/uploads/",
            username="wronguser",
            password="wrongpass",
            enabled=True
        )

        assert result.is_valid is False
        assert any("login" in e.message.lower() or "password" in e.message.lower()
                   for e in result.errors)

    def test_validate_email_valid(self, validator):
        """Test valid email settings pass validation."""
        result = validator.validate_email_settings(
            recipients="test@example.com, another@example.com",
            enabled=True
        )

        assert result.is_valid is True

    def test_validate_email_invalid_address(self, validator):
        """Test validation fails for invalid email address."""
        result = validator.validate_email_settings(
            recipients="invalid-email",
            enabled=True
        )

        assert result.is_valid is False
        assert any("email" in e.field.lower() for e in result.errors)

    def test_validate_email_disabled(self, validator):
        """Test validation passes when email is disabled."""
        result = validator.validate_email_settings(
            recipients="",
            enabled=False
        )

        assert result.is_valid is True

    def test_validate_alias_unique(self, validator):
        """Test alias uniqueness validation."""
        # This alias exists in our fixture
        result = validator.validate_alias(
            alias="existing_alias",
            folder_name="test_folder",
            current_alias="different_alias"
        )

        assert result.is_valid is False
        assert any("already in use" in e.message.lower() for e in result.errors)

    def test_validate_alias_allows_current(self, validator):
        """Test editing current alias is allowed."""
        result = validator.validate_alias(
            alias="existing_alias",
            folder_name="test_folder",
            current_alias="existing_alias"  # Same as current
        )

        assert result.is_valid is True

    def test_validate_alias_too_long(self, validator):
        """Test alias length validation."""
        result = validator.validate_alias(
            alias="a" * 51,  # Max is 50
            folder_name="test_folder"
        )

        assert result.is_valid is False
        assert any("too long" in e.message.lower() for e in result.errors)

    def test_validate_alias_template(self, validator):
        """Test alias validation passes for template."""
        result = validator.validate_alias(
            alias="template_alias",
            folder_name="template"
        )

        assert result.is_valid is True

    def test_validate_invoice_date_offset_valid(self, validator):
        """Test valid invoice date offset."""
        for offset in range(-14, 15):
            result = validator.validate_invoice_date_offset(offset)
            assert result.is_valid is True, f"Offset {offset} should be valid"

    def test_validate_invoice_date_offset_invalid(self, validator):
        """Test invalid invoice date offset."""
        result = validator.validate_invoice_date_offset(20)
        assert result.is_valid is False

        result = validator.validate_invoice_date_offset(-15)
        assert result.is_valid is False

    def test_validate_upc_override_valid(self, validator):
        """Test valid UPC override settings."""
        result = validator.validate_upc_override(
            enabled=True,
            category_filter="1,2,3,ALL"
        )

        assert result.is_valid is True

    def test_validate_upc_override_missing_filter(self, validator):
        """Test validation fails when category filter missing."""
        result = validator.validate_upc_override(
            enabled=True,
            category_filter=""
        )

        assert result.is_valid is False
        assert any("category filter" in e.message.lower() for e in result.errors)

    def test_validate_upc_override_disabled(self, validator):
        """Test validation passes when UPC override is disabled."""
        result = validator.validate_upc_override(
            enabled=False,
            category_filter=""
        )

        assert result.is_valid is True

    def test_validate_copy_settings_valid(self, validator):
        """Test valid copy settings pass validation."""
        result = validator.validate_copy_settings(
            destination="/tmp/destination",
            enabled=True
        )

        assert result.is_valid is True

    def test_validate_copy_settings_missing_destination(self, validator):
        """Test validation fails when destination is missing."""
        result = validator.validate_copy_settings(
            destination="",
            enabled=True
        )

        assert result.is_valid is False
        assert any("destination" in e.message.lower() for e in result.errors)

    def test_validate_copy_settings_disabled(self, validator):
        """Test validation passes when copy is disabled."""
        result = validator.validate_copy_settings(
            destination="",
            enabled=False
        )

        assert result.is_valid is True

    def test_validate_backend_specific_fintech_valid(self, validator):
        """Test valid fintech settings pass validation."""
        result = validator.validate_backend_specific(
            convert_format="fintech",
            division_id="123"
        )

        assert result.is_valid is True

    def test_validate_backend_specific_fintech_invalid(self, validator):
        """Test fintech division ID validation."""
        result = validator.validate_backend_specific(
            convert_format="fintech",
            division_id="abc"
        )

        assert result.is_valid is False
        assert any("fintech" in e.message.lower() for e in result.errors)

    def test_validate_backend_specific_other_format(self, validator):
        """Test other formats pass without fintech validation."""
        result = validator.validate_backend_specific(
            convert_format="csv",
            division_id="not-required"
        )

        assert result.is_valid is True

    def test_validate_edi_split_requirements_prepend_dates(self, validator):
        """Test EDI split validation for prepending dates."""
        result = validator.validate_edi_split_requirements(
            convert_format="csv",
            split_edi=False,
            prepend_dates=True,
            tweak_edi=False
        )

        assert result.is_valid is False
        assert any("prepending dates" in e.message.lower() for e in result.errors)

    def test_validate_edi_split_requirements_jolley(self, validator):
        """Test EDI split validation for jolley_custom."""
        result = validator.validate_edi_split_requirements(
            convert_format="jolley_custom",
            split_edi=False,
            prepend_dates=False,
            tweak_edi=False
        )

        assert result.is_valid is False
        assert any("jolley_custom" in e.message.lower() for e in result.errors)


class TestValidationResult:
    """Test suite for ValidationResult."""

    def test_empty_result_is_valid(self):
        """Test that empty result is valid."""
        result = ValidationResult()
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_add_error_marks_invalid(self):
        """Test that adding an error marks result as invalid."""
        result = ValidationResult()
        result.add_error("test_field", "Test error message")

        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0].field == "test_field"
        assert result.errors[0].message == "Test error message"

    def test_add_warning(self):
        """Test adding a warning."""
        result = ValidationResult()
        result.add_warning("test_field", "Test warning message")

        assert result.is_valid is True  # Warnings don't invalidate
        assert len(result.warnings) == 1
        assert result.warnings[0].message == "Test warning message"

    def test_get_all_messages(self):
        """Test getting all messages."""
        result = ValidationResult()
        result.add_error("field1", "Error 1")
        result.add_warning("field2", "Warning 1")
        result.add_error("field3", "Error 2")

        messages = result.get_all_messages()

        assert len(messages) == 3
        assert "Error 1" in messages
        assert "Warning 1" in messages
        assert "Error 2" in messages
