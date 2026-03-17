"""Unit tests for settings validation logic in the batch file processor.

Tests the FolderSettingsValidator class methods:
- validate_ftp_settings
- validate_email_settings
- validate_copy_settings
- validate_alias
- validate_invoice_date_offset
"""

import pytest

from interface.validation.folder_settings_validator import FolderSettingsValidator

pytestmark = [pytest.mark.unit]


class TestFolderSettingsValidatorFTP:
    """Tests for FolderSettingsValidator.validate_ftp_settings()."""

    def setup_method(self):
        self.validator = FolderSettingsValidator()

    def _valid_ftp_params(self):
        return dict(
            server="ftp.example.com",
            port="21",
            folder="/uploads/",
            username="ftpuser",
            password="secret",
            enabled=True,
        )

    def test_disabled_ftp_always_valid(self):
        result = self.validator.validate_ftp_settings(
            server="", port="", folder="", username="", password="", enabled=False
        )
        assert result.is_valid

    def test_valid_ftp_settings_pass(self):
        result = self.validator.validate_ftp_settings(**self._valid_ftp_params())
        assert result.is_valid

    def test_missing_server_adds_error(self):
        params = self._valid_ftp_params()
        params["server"] = ""
        result = self.validator.validate_ftp_settings(**params)
        assert not result.is_valid
        fields = [e.field for e in result.errors]
        assert "ftp_server" in fields

    def test_folder_without_trailing_slash_adds_error(self):
        params = self._valid_ftp_params()
        params["folder"] = "/uploads"
        result = self.validator.validate_ftp_settings(**params)
        assert not result.is_valid
        fields = [e.field for e in result.errors]
        assert "ftp_folder" in fields

    def test_non_numeric_port_adds_error(self):
        params = self._valid_ftp_params()
        params["port"] = "notaport"
        result = self.validator.validate_ftp_settings(**params)
        assert not result.is_valid
        fields = [e.field for e in result.errors]
        assert "ftp_port" in fields

    def test_out_of_range_port_adds_error(self):
        params = self._valid_ftp_params()
        params["port"] = "99999"
        result = self.validator.validate_ftp_settings(**params)
        assert not result.is_valid
        fields = [e.field for e in result.errors]
        assert "ftp_port" in fields

    def test_missing_username_adds_error(self):
        params = self._valid_ftp_params()
        params["username"] = ""
        result = self.validator.validate_ftp_settings(**params)
        assert not result.is_valid
        assert any(e.field == "ftp_username" for e in result.errors)

    def test_missing_password_adds_error(self):
        params = self._valid_ftp_params()
        params["password"] = ""
        result = self.validator.validate_ftp_settings(**params)
        assert not result.is_valid
        assert any(e.field == "ftp_password" for e in result.errors)


class TestFolderSettingsValidatorEmail:
    """Tests for FolderSettingsValidator.validate_email_settings()."""

    def setup_method(self):
        self.validator = FolderSettingsValidator()

    def test_disabled_email_always_valid(self):
        result = self.validator.validate_email_settings(recipients="", enabled=False)
        assert result.is_valid

    def test_valid_single_recipient_passes(self):
        result = self.validator.validate_email_settings(
            recipients="user@example.com", enabled=True
        )
        assert result.is_valid

    def test_valid_multiple_recipients_pass(self):
        result = self.validator.validate_email_settings(
            recipients="a@example.com, b@example.com", enabled=True
        )
        assert result.is_valid

    def test_empty_recipients_adds_error(self):
        result = self.validator.validate_email_settings(recipients="", enabled=True)
        assert not result.is_valid
        assert any(e.field == "email_recipient" for e in result.errors)

    def test_invalid_email_address_adds_error(self):
        result = self.validator.validate_email_settings(
            recipients="notanemail", enabled=True
        )
        assert not result.is_valid
        assert any(e.field == "email_recipient" for e in result.errors)


class TestFolderSettingsValidatorCopy:
    """Tests for FolderSettingsValidator.validate_copy_settings()."""

    def setup_method(self):
        self.validator = FolderSettingsValidator()

    def test_disabled_copy_always_valid(self):
        result = self.validator.validate_copy_settings(destination="", enabled=False)
        assert result.is_valid

    def test_valid_destination_passes(self):
        result = self.validator.validate_copy_settings(
            destination="/backup/output/", enabled=True
        )
        assert result.is_valid

    def test_empty_destination_adds_error(self):
        result = self.validator.validate_copy_settings(destination="", enabled=True)
        assert not result.is_valid
        assert any(e.field == "copy_destination" for e in result.errors)


class TestFolderSettingsValidatorAlias:
    """Tests for FolderSettingsValidator.validate_alias()."""

    def test_template_folder_skips_validation(self):
        validator = FolderSettingsValidator(existing_aliases=["x" * 60])
        result = validator.validate_alias(
            alias="x" * 60, folder_name="template", current_alias=None
        )
        assert result.is_valid

    def test_alias_too_long_adds_error(self):
        validator = FolderSettingsValidator()
        result = validator.validate_alias(
            alias="a" * 51, folder_name="somefolder", current_alias=None
        )
        assert not result.is_valid
        assert any(e.field == "alias" for e in result.errors)

    def test_alias_at_max_length_is_valid(self):
        validator = FolderSettingsValidator()
        result = validator.validate_alias(
            alias="a" * 50, folder_name="somefolder", current_alias=None
        )
        assert result.is_valid

    def test_duplicate_alias_adds_error(self):
        validator = FolderSettingsValidator(existing_aliases=["taken"])
        result = validator.validate_alias(
            alias="taken", folder_name="somefolder", current_alias=None
        )
        assert not result.is_valid
        assert any(e.field == "alias" for e in result.errors)

    def test_editing_same_alias_is_valid(self):
        """Renaming a folder to its own current alias should not be an error."""
        validator = FolderSettingsValidator(existing_aliases=["myalias"])
        result = validator.validate_alias(
            alias="myalias", folder_name="somefolder", current_alias="myalias"
        )
        assert result.is_valid


class TestFolderSettingsValidatorInvoiceDateOffset:
    """Tests for FolderSettingsValidator.validate_invoice_date_offset()."""

    def setup_method(self):
        self.validator = FolderSettingsValidator()

    @pytest.mark.parametrize("offset", [-14, -1, 0, 1, 14])
    def test_valid_offsets_pass(self, offset):
        result = self.validator.validate_invoice_date_offset(offset)
        assert result.is_valid

    @pytest.mark.parametrize("offset", [-15, 15, 100, -100])
    def test_out_of_range_offsets_add_error(self, offset):
        result = self.validator.validate_invoice_date_offset(offset)
        assert not result.is_valid
        assert any(e.field == "invoice_date_offset" for e in result.errors)
