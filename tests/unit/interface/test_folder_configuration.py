"""Unit tests for interface/models/folder_configuration.py.

Tests:
- FTPConfiguration validation
- EmailConfiguration validation
- CopyConfiguration validation
- EDIConfiguration validation
- UPCOverrideConfiguration validation
- ARecordPaddingConfiguration validation
- InvoiceDateConfiguration validation
- CSVConfiguration data structure
- FolderConfiguration from_dict()
- FolderConfiguration to_dict()
- FolderConfiguration roundtrip
- Plugin configuration management
- Plugin configuration validation
"""

from unittest.mock import patch, MagicMock
from interface.models.folder_configuration import (
    FolderConfiguration,
    FTPConfiguration,
    EmailConfiguration,
    CopyConfiguration,
    EDIConfiguration,
    UPCOverrideConfiguration,
    ARecordPaddingConfiguration,
    InvoiceDateConfiguration,
    BackendSpecificConfiguration,
    CSVConfiguration,
    BackendType,
    ConvertFormat,
)


class TestFTPConfiguration:
    """Test suite for FTPConfiguration."""

    def test_create_default_ftp_config(self):
        """Test creating default FTP configuration."""
        config = FTPConfiguration()
        assert config.server == ""
        assert config.port == 21
        assert config.username == ""
        assert config.password == ""
        assert config.folder == ""

    def test_create_ftp_config_with_values(self):
        """Test creating FTP configuration with values."""
        config = FTPConfiguration(
            server="ftp.example.com",
            port=2121,
            username="user",
            password="pass",
            folder="/uploads/",
        )
        assert config.server == "ftp.example.com"
        assert config.port == 2121
        assert config.username == "user"
        assert config.password == "pass"
        assert config.folder == "/uploads/"

    def test_validate_missing_server(self):
        """Test validation fails when server is missing."""
        config = FTPConfiguration(
            server="", username="user", password="pass", folder="/uploads/"
        )
        errors = config.validate()
        assert "FTP Server Field Is Required" in errors

    def test_validate_missing_username(self):
        """Test validation fails when username is missing."""
        config = FTPConfiguration(
            server="ftp.example.com", username="", password="pass", folder="/uploads/"
        )
        errors = config.validate()
        assert "FTP Username Field Is Required" in errors

    def test_validate_missing_password(self):
        """Test validation fails when password is missing."""
        config = FTPConfiguration(
            server="ftp.example.com", username="user", password="", folder="/uploads/"
        )
        errors = config.validate()
        assert "FTP Password Field Is Required" in errors

    def test_validate_missing_folder(self):
        """Test validation fails when folder is missing."""
        config = FTPConfiguration(
            server="ftp.example.com", username="user", password="pass", folder=""
        )
        errors = config.validate()
        assert "FTP Folder Field Is Required" in errors

    def test_validate_folder_without_trailing_slash(self):
        """Test validation fails when folder doesn't end with slash."""
        config = FTPConfiguration(
            server="ftp.example.com",
            username="user",
            password="pass",
            folder="/uploads",
        )
        errors = config.validate()
        assert "FTP Folder Path Needs To End In /" in errors

    def test_validate_invalid_port_string(self):
        """Test validation fails when port is not a number."""
        config = FTPConfiguration(
            server="ftp.example.com",
            username="user",
            password="pass",
            folder="/uploads/",
            port="invalid",
        )
        errors = config.validate()
        assert "FTP Port Field Needs To Be A Number" in errors

    def test_validate_port_out_of_range(self):
        """Test validation fails when port is out of valid range."""
        config = FTPConfiguration(
            server="ftp.example.com",
            username="user",
            password="pass",
            folder="/uploads/",
            port=70000,
        )
        errors = config.validate()
        assert "FTP Port Field Needs To Be A Valid Port Number" in errors

    def test_validate_valid_port(self):
        """Test validation passes with valid port."""
        config = FTPConfiguration(
            server="ftp.example.com",
            username="user",
            password="pass",
            folder="/uploads/",
            port=2121,
        )
        errors = config.validate()
        assert len(errors) == 0

    def test_validate_complete_valid_config(self):
        """Test validation passes with complete valid configuration."""
        config = FTPConfiguration(
            server="ftp.example.com",
            port=2121,
            username="user",
            password="pass",
            folder="/uploads/",
        )
        errors = config.validate()
        assert len(errors) == 0


class TestEmailConfiguration:
    """Test suite for EmailConfiguration."""

    def test_create_default_email_config(self):
        """Test creating default email configuration."""
        config = EmailConfiguration()
        assert config.recipients == ""
        assert config.subject_line == ""
        assert config.sender_address is None

    def test_create_email_config_with_values(self):
        """Test creating email configuration with values."""
        config = EmailConfiguration(
            recipients="user1@example.com, user2@example.com",
            subject_line="Test Subject",
        )
        assert config.recipients == "user1@example.com, user2@example.com"
        assert config.subject_line == "Test Subject"

    def test_validate_missing_recipients(self):
        """Test validation fails when recipients is missing."""
        config = EmailConfiguration(recipients="")
        errors = config.validate()
        assert "Email Destination Address Field Is Required" in errors

    def test_validate_invalid_email_format(self):
        """Test validation fails with invalid email format."""
        config = EmailConfiguration(recipients="invalid-email")
        errors = config.validate()
        assert "Invalid Email Destination Address: invalid-email" in errors

    def test_validate_multiple_emails_one_invalid(self):
        """Test validation fails when one email in list is invalid."""
        config = EmailConfiguration(recipients="valid@example.com, invalid-email")
        errors = config.validate()
        assert "Invalid Email Destination Address: invalid-email" in errors

    def test_validate_valid_single_email(self):
        """Test validation passes with valid single email."""
        config = EmailConfiguration(recipients="user@example.com")
        errors = config.validate()
        assert len(errors) == 0

    def test_validate_valid_multiple_emails(self):
        """Test validation passes with valid multiple emails."""
        config = EmailConfiguration(recipients="user1@example.com, user2@example.com")
        errors = config.validate()
        assert len(errors) == 0

    def test_validate_email_format_with_special_chars(self):
        """Test validation passes with valid email containing special chars."""
        config = EmailConfiguration(recipients="user+test@example-domain.com")
        errors = config.validate()
        assert len(errors) == 0


class TestCopyConfiguration:
    """Test suite for CopyConfiguration."""

    def test_create_default_copy_config(self):
        """Test creating default copy configuration."""
        config = CopyConfiguration()
        assert config.destination_directory == ""

    def test_create_copy_config_with_value(self):
        """Test creating copy configuration with value."""
        config = CopyConfiguration(destination_directory="/backup/")
        assert config.destination_directory == "/backup/"

    def test_validate_missing_destination(self):
        """Test validation fails when destination is missing."""
        config = CopyConfiguration(destination_directory="")
        errors = config.validate()
        assert "Copy Backend Destination Is Currently Unset" in errors

    def test_validate_valid_destination(self):
        """Test validation passes with valid destination."""
        config = CopyConfiguration(destination_directory="/backup/")
        errors = config.validate()
        assert len(errors) == 0


class TestEDIConfiguration:
    """Test suite for EDIConfiguration."""

    def test_create_default_edi_config(self):
        """Test creating default EDI configuration."""
        config = EDIConfiguration()
        assert config.process_edi is False
        assert config.tweak_edi is False
        assert config.split_edi is False
        assert config.prepend_date_files is False
        assert config.convert_to_format == ""

    def test_create_edi_config_with_values(self):
        """Test creating EDI configuration with values."""
        config = EDIConfiguration(
            process_edi=True, tweak_edi=True, split_edi=True, convert_to_format="csv"
        )
        assert config.process_edi is True
        assert config.tweak_edi is True
        assert config.split_edi is True
        assert config.convert_to_format == "csv"

    def test_validate_prepend_date_without_split(self):
        """Test validation fails when prepend_date_files is True but split_edi is False."""
        config = EDIConfiguration(prepend_date_files=True, split_edi=False)
        errors = config.validate()
        assert "EDI needs to be split for prepending dates" in errors

    def test_validate_prepend_date_with_split(self):
        """Test validation passes when prepend_date_files and split_edi are both True."""
        config = EDIConfiguration(prepend_date_files=True, split_edi=True)
        errors = config.validate()
        assert len(errors) == 0

    def test_validate_default_config(self):
        """Test validation passes with default configuration."""
        config = EDIConfiguration()
        errors = config.validate()
        assert len(errors) == 0


class TestUPCOverrideConfiguration:
    """Test suite for UPCOverrideConfiguration."""

    def test_create_default_upc_override_config(self):
        """Test creating default UPC override configuration."""
        config = UPCOverrideConfiguration()
        assert config.enabled is False
        assert config.level == 1
        assert config.category_filter == ""
        assert config.target_length == 11

    def test_create_upc_override_config_with_values(self):
        """Test creating UPC override configuration with values."""
        config = UPCOverrideConfiguration(
            enabled=True, level=2, category_filter="1,2,3", target_length=12
        )
        assert config.enabled is True
        assert config.level == 2
        assert config.category_filter == "1,2,3"
        assert config.target_length == 12

    def test_validate_enabled_without_category_filter(self):
        """Test validation fails when enabled but category_filter is missing."""
        config = UPCOverrideConfiguration(enabled=True, category_filter="")
        errors = config.validate()
        assert "Override UPC Category Filter Is Required" in errors

    def test_validate_enabled_with_all_filter(self):
        """Test validation passes with ALL filter."""
        config = UPCOverrideConfiguration(enabled=True, category_filter="ALL")
        errors = config.validate()
        assert len(errors) == 0

    def test_validate_enabled_with_valid_categories(self):
        """Test validation passes with valid category numbers."""
        config = UPCOverrideConfiguration(enabled=True, category_filter="1,5,10,50")
        errors = config.validate()
        assert len(errors) == 0

    def test_validate_enabled_with_invalid_category_string(self):
        """Test validation fails with invalid category string."""
        config = UPCOverrideConfiguration(enabled=True, category_filter="abc,def")
        errors = config.validate()
        assert "Override UPC Category Filter Is Invalid" in errors

    def test_validate_enabled_with_category_out_of_range(self):
        """Test validation fails with category number out of range."""
        config = UPCOverrideConfiguration(enabled=True, category_filter="1,100,200")
        errors = config.validate()
        assert "Override UPC Category Filter Is Invalid" in errors

    def test_validate_disabled(self):
        """Test validation passes when disabled."""
        config = UPCOverrideConfiguration(enabled=False)
        errors = config.validate()
        assert len(errors) == 0


class TestARecordPaddingConfiguration:
    """Test suite for ARecordPaddingConfiguration."""

    def test_create_default_a_record_padding_config(self):
        """Test creating default A-record padding configuration."""
        config = ARecordPaddingConfiguration()
        assert config.enabled is False
        assert config.padding_text == ""
        assert config.padding_length == 6

    def test_create_a_record_padding_config_with_values(self):
        """Test creating A-record padding configuration with values."""
        config = ARecordPaddingConfiguration(
            enabled=True, padding_text="ABCDEF", padding_length=6, append_text="XYZ"
        )
        assert config.enabled is True
        assert config.padding_text == "ABCDEF"
        assert config.padding_length == 6

    def test_validate_padding_text_too_long(self):
        """Test validation fails when padding text exceeds length."""
        config = ARecordPaddingConfiguration(
            enabled=True, padding_text="ABCDEFG", padding_length=6
        )
        errors = config.validate()
        assert '"A" Record Padding Needs To Be At Most 6 Characters' in errors

    def test_validate_padding_text_wrong_length(self):
        """Test validation fails when padding text is not 6 characters."""
        config = ARecordPaddingConfiguration(
            enabled=True, padding_text="ABC", padding_length=6
        )
        errors = config.validate()
        assert '"A" Record Padding Needs To Be Six Characters' in errors

    def test_validate_valid_padding(self):
        """Test validation passes with valid padding."""
        config = ARecordPaddingConfiguration(
            enabled=True, padding_text="ABCDEF", padding_length=6
        )
        errors = config.validate()
        assert len(errors) == 0

    def test_validate_scannerware_format(self):
        """Test validation passes for ScannerWare format regardless of padding length."""
        config = ARecordPaddingConfiguration(
            enabled=True, padding_text="ABCDEF", padding_length=10
        )
        errors = config.validate(convert_format="ScannerWare")
        # ScannerWare handled separately, so no error
        assert len(errors) == 0

    def test_validate_disabled(self):
        """Test validation passes when disabled."""
        config = ARecordPaddingConfiguration(enabled=False)
        errors = config.validate()
        assert len(errors) == 0


class TestInvoiceDateConfiguration:
    """Test suite for InvoiceDateConfiguration."""

    def test_create_default_invoice_date_config(self):
        """Test creating default invoice date configuration."""
        config = InvoiceDateConfiguration()
        assert config.offset == 0
        assert config.custom_format_enabled is False
        assert config.custom_format_string == ""

    def test_create_invoice_date_config_with_values(self):
        """Test creating invoice date configuration with values."""
        config = InvoiceDateConfiguration(
            offset=5, custom_format_enabled=True, custom_format_string="%Y-%m-%d"
        )
        assert config.offset == 5
        assert config.custom_format_enabled is True
        assert config.custom_format_string == "%Y-%m-%d"

    def test_validate_offset_out_of_range_negative(self):
        """Test validation fails when offset is less than -14."""
        config = InvoiceDateConfiguration(offset=-15)
        errors = config.validate()
        assert "Invoice date offset not in valid range (-14 to 14)" in errors

    def test_validate_offset_out_of_range_positive(self):
        """Test validation fails when offset is greater than 14."""
        config = InvoiceDateConfiguration(offset=15)
        errors = config.validate()
        assert "Invoice date offset not in valid range (-14 to 14)" in errors

    def test_validate_valid_offset_negative(self):
        """Test validation passes with valid negative offset."""
        config = InvoiceDateConfiguration(offset=-10)
        errors = config.validate()
        assert len(errors) == 0

    def test_validate_valid_offset_positive(self):
        """Test validation passes with valid positive offset."""
        config = InvoiceDateConfiguration(offset=10)
        errors = config.validate()
        assert len(errors) == 0

    def test_validate_zero_offset(self):
        """Test validation passes with zero offset."""
        config = InvoiceDateConfiguration(offset=0)
        errors = config.validate()
        assert len(errors) == 0


class TestBackendSpecificConfiguration:
    """Test suite for BackendSpecificConfiguration."""

    def test_create_default_backend_specific_config(self):
        """Test creating default backend-specific configuration."""
        config = BackendSpecificConfiguration()
        assert config.estore_store_number == ""
        assert config.estore_vendor_oid == ""
        assert config.fintech_division_id == ""

    def test_create_backend_specific_config_with_estore_values(self):
        """Test creating backend-specific configuration with eStore values."""
        config = BackendSpecificConfiguration(
            estore_store_number="12345",
            estore_vendor_oid="VENDOR123",
            estore_vendor_namevendoroid="Test Vendor",
            estore_c_record_oid="CREC123",
        )
        assert config.estore_store_number == "12345"
        assert config.estore_vendor_oid == "VENDOR123"

    def test_create_backend_specific_config_with_fintech_values(self):
        """Test creating backend-specific configuration with Fintech values."""
        config = BackendSpecificConfiguration(fintech_division_id="DIV001")
        assert config.fintech_division_id == "DIV001"


class TestCSVConfiguration:
    """Test suite for CSVConfiguration."""

    def test_create_default_csv_config(self):
        """Test creating default CSV configuration."""
        config = CSVConfiguration()
        assert config.include_headers is False
        assert config.filter_ampersand is False
        assert config.include_item_numbers is False

    def test_create_csv_config_with_values(self):
        """Test creating CSV configuration with values."""
        config = CSVConfiguration(
            include_headers=True,
            filter_ampersand=True,
            include_item_numbers=True,
            include_item_description=True,
            simple_csv_sort_order="item_number",
        )
        assert config.include_headers is True
        assert config.filter_ampersand is True
        assert config.include_item_numbers is True


class TestFolderConfiguration:
    """Test suite for FolderConfiguration."""

    def test_create_default_folder_config(self):
        """Test creating default folder configuration."""
        config = FolderConfiguration()
        assert config.folder_name == ""
        assert config.folder_is_active is False
        assert config.alias == ""
        assert config.is_template is False

    def test_create_folder_config_with_basic_fields(self):
        """Test creating folder configuration with basic fields."""
        config = FolderConfiguration(
            folder_name="/home/user/test",
            folder_is_active=True,
            alias="Test Folder",
            process_backend_copy=True,
        )
        assert config.folder_name == "/home/user/test"
        assert config.folder_is_active is True
        assert config.alias == "Test Folder"
        assert config.process_backend_copy is True

    def test_create_folder_config_with_ftp(self):
        """Test creating folder configuration with FTP backend."""
        ftp_config = FTPConfiguration(
            server="ftp.example.com",
            port=2121,
            username="user",
            password="pass",
            folder="/uploads/",
        )
        config = FolderConfiguration(
            folder_name="/test", process_backend_ftp=True, ftp=ftp_config
        )
        assert config.ftp is not None
        assert config.ftp.server == "ftp.example.com"

    def test_create_folder_config_with_email(self):
        """Test creating folder configuration with email backend."""
        email_config = EmailConfiguration(
            recipients="user@example.com", subject_line="Test"
        )
        config = FolderConfiguration(
            folder_name="/test", process_backend_email=True, email=email_config
        )
        assert config.email is not None
        assert config.email.recipients == "user@example.com"

    def test_from_dict_basic_fields(self):
        """Test from_dict() with basic fields."""
        data = {
            "folder_name": "/home/user/test",
            "folder_is_active": "True",
            "alias": "Test Folder",
        }
        config = FolderConfiguration.from_dict(data)
        assert config.folder_name == "/home/user/test"
        assert config.folder_is_active is True
        assert config.alias == "Test Folder"

    def test_from_dict_with_ftp(self):
        """Test from_dict() with FTP configuration."""
        data = {
            "folder_name": "/test",
            "ftp_server": "ftp.example.com",
            "ftp_port": 2121,
            "ftp_username": "user",
            "ftp_password": "pass",
            "ftp_folder": "/uploads/",
        }
        config = FolderConfiguration.from_dict(data)
        assert config.ftp is not None
        assert config.ftp.server == "ftp.example.com"
        assert config.ftp.port == 2121

    def test_from_dict_with_email(self):
        """Test from_dict() with email configuration."""
        data = {
            "folder_name": "/test",
            "email_to": "user@example.com",
            "email_subject_line": "Test Subject",
        }
        config = FolderConfiguration.from_dict(data)
        assert config.email is not None
        assert config.email.recipients == "user@example.com"
        assert config.email.subject_line == "Test Subject"

    def test_from_dict_with_copy(self):
        """Test from_dict() with copy configuration."""
        data = {"folder_name": "/test", "copy_to_directory": "/backup/"}
        config = FolderConfiguration.from_dict(data)
        assert config.copy is not None
        assert config.copy.destination_directory == "/backup/"

    def test_from_dict_with_edi(self):
        """Test from_dict() with EDI configuration."""
        data = {
            "folder_name": "/test",
            "process_edi": "True",
            "tweak_edi": True,
            "split_edi": True,
            "convert_to_format": "csv",
        }
        config = FolderConfiguration.from_dict(data)
        assert config.edi is not None
        assert config.edi.process_edi is True
        assert config.edi.tweak_edi is True

    def test_from_dict_with_upc_override(self):
        """Test from_dict() with UPC override configuration."""
        data = {
            "folder_name": "/test",
            "override_upc_bool": True,
            "override_upc_level": 2,
            "override_upc_category_filter": "1,2,3",
        }
        config = FolderConfiguration.from_dict(data)
        assert config.upc_override is not None
        assert config.upc_override.enabled is True
        assert config.upc_override.level == 2

    def test_from_dict_with_a_record_padding(self):
        """Test from_dict() with A-record padding configuration."""
        data = {
            "folder_name": "/test",
            "pad_a_records": "True",
            "a_record_padding": "ABCDEF",
            "a_record_padding_length": 6,
        }
        config = FolderConfiguration.from_dict(data)
        assert config.a_record_padding is not None
        assert config.a_record_padding.enabled is True
        assert config.a_record_padding.padding_text == "ABCDEF"

    def test_from_dict_with_invoice_date(self):
        """Test from_dict() with invoice date configuration."""
        data = {
            "folder_name": "/test",
            "invoice_date_offset": 5,
            "invoice_date_custom_format": True,
            "invoice_date_custom_format_string": "%Y-%m-%d",
        }
        config = FolderConfiguration.from_dict(data)
        assert config.invoice_date is not None
        assert config.invoice_date.offset == 5
        assert config.invoice_date.custom_format_enabled is True

    def test_from_dict_with_backend_specific(self):
        """Test from_dict() with backend-specific configuration."""
        data = {
            "folder_name": "/test",
            "estore_store_number": "12345",
            "estore_Vendor_OId": "VENDOR123",
            "fintech_division_id": "DIV001",
        }
        config = FolderConfiguration.from_dict(data)
        assert config.backend_specific is not None
        assert config.backend_specific.estore_store_number == "12345"
        assert config.backend_specific.fintech_division_id == "DIV001"

    def test_from_dict_with_csv(self):
        """Test from_dict() with CSV configuration."""
        data = {
            "folder_name": "/test",
            "include_headers": "True",
            "filter_ampersand": "True",
            "simple_csv_sort_order": "item_number",
        }
        config = FolderConfiguration.from_dict(data)
        assert config.csv is not None
        assert config.csv.include_headers is True
        assert config.csv.filter_ampersand is True

    def test_from_dict_identifies_template(self):
        """Test from_dict() correctly identifies template folders."""
        data = {"folder_name": "template"}
        config = FolderConfiguration.from_dict(data)
        assert config.is_template is True

    def test_to_dict_basic_fields(self):
        """Test to_dict() with basic fields."""
        config = FolderConfiguration(
            folder_name="/test", folder_is_active=True, alias="Test"
        )
        data = config.to_dict()
        assert data["folder_name"] == "/test"
        assert data["folder_is_active"] is True
        assert data["alias"] == "Test"

    def test_to_dict_with_ftp(self):
        """Test to_dict() with FTP configuration."""
        ftp_config = FTPConfiguration(
            server="ftp.example.com",
            port=2121,
            username="user",
            password="pass",
            folder="/uploads/",
        )
        config = FolderConfiguration(folder_name="/test", ftp=ftp_config)
        data = config.to_dict()
        assert data["ftp_server"] == "ftp.example.com"
        assert data["ftp_port"] == 2121
        assert data["ftp_username"] == "user"

    def test_to_dict_with_email(self):
        """Test to_dict() with email configuration."""
        email_config = EmailConfiguration(
            recipients="user@example.com", subject_line="Test"
        )
        config = FolderConfiguration(folder_name="/test", email=email_config)
        data = config.to_dict()
        assert data["email_to"] == "user@example.com"
        assert data["email_subject_line"] == "Test"

    def test_to_dict_with_copy(self):
        """Test to_dict() with copy configuration."""
        copy_config = CopyConfiguration(destination_directory="/backup/")
        config = FolderConfiguration(folder_name="/test", copy=copy_config)
        data = config.to_dict()
        assert data["copy_to_directory"] == "/backup/"

    def test_to_dict_with_edi(self):
        """Test to_dict() with EDI configuration."""
        edi_config = EDIConfiguration(
            process_edi=True, tweak_edi=True, split_edi=True, convert_to_format="csv"
        )
        config = FolderConfiguration(folder_name="/test", edi=edi_config)
        data = config.to_dict()
        assert data["process_edi"] is True
        assert data["tweak_edi"] is True
        assert data["split_edi"] is True

    def test_to_dict_with_upc_override(self):
        """Test to_dict() with UPC override configuration."""
        upc_config = UPCOverrideConfiguration(
            enabled=True, level=2, category_filter="1,2,3"
        )
        config = FolderConfiguration(folder_name="/test", upc_override=upc_config)
        data = config.to_dict()
        assert data["override_upc_bool"] is True
        assert data["override_upc_level"] == 2
        assert data["override_upc_category_filter"] == "1,2,3"

    def test_to_dict_with_a_record_padding(self):
        """Test to_dict() with A-record padding configuration."""
        a_record_config = ARecordPaddingConfiguration(
            enabled=True, padding_text="ABCDEF", padding_length=6
        )
        config = FolderConfiguration(
            folder_name="/test", a_record_padding=a_record_config
        )
        data = config.to_dict()
        assert data["pad_a_records"] is True
        assert data["a_record_padding"] == "ABCDEF"
        assert data["a_record_padding_length"] == 6

    def test_to_dict_with_invoice_date(self):
        """Test to_dict() with invoice date configuration."""
        invoice_config = InvoiceDateConfiguration(
            offset=5, custom_format_enabled=True, custom_format_string="%Y-%m-%d"
        )
        config = FolderConfiguration(folder_name="/test", invoice_date=invoice_config)
        data = config.to_dict()
        assert data["invoice_date_offset"] == 5
        assert data["invoice_date_custom_format"] is True
        assert data["invoice_date_custom_format_string"] == "%Y-%m-%d"

    def test_to_dict_with_backend_specific(self):
        """Test to_dict() with backend-specific configuration."""
        backend_config = BackendSpecificConfiguration(
            estore_store_number="12345", fintech_division_id="DIV001"
        )
        config = FolderConfiguration(
            folder_name="/test", backend_specific=backend_config
        )
        data = config.to_dict()
        assert data["estore_store_number"] == "12345"
        assert data["fintech_division_id"] == "DIV001"

    def test_to_dict_with_csv(self):
        """Test to_dict() with CSV configuration."""
        csv_config = CSVConfiguration(
            include_headers=True,
            filter_ampersand=True,
            simple_csv_sort_order="item_number",
        )
        config = FolderConfiguration(folder_name="/test", csv=csv_config)
        data = config.to_dict()
        assert data["include_headers"] is True
        assert data["filter_ampersand"] is True
        assert data["simple_csv_sort_order"] == "item_number"

    def test_roundtrip_preserves_all_data(self):
        """Test that from_dict() and to_dict() roundtrip preserves all data."""
        original_data = {
            "folder_name": "/test",
            "folder_is_active": "True",
            "alias": "Test",
            "process_backend_copy": True,
            "process_backend_ftp": True,
            "process_backend_email": True,
            "ftp_server": "ftp.example.com",
            "ftp_port": 2121,
            "ftp_username": "user",
            "ftp_password": "pass",
            "ftp_folder": "/uploads/",
            "email_to": "user@example.com",
            "email_subject_line": "Test",
            "copy_to_directory": "/backup/",
            "process_edi": "True",
            "tweak_edi": True,
            "split_edi": True,
            "convert_to_format": "csv",
            "override_upc_bool": True,
            "override_upc_level": 2,
            "override_upc_category_filter": "1,2,3",
            "pad_a_records": "True",
            "a_record_padding": "ABCDEF",
            "a_record_padding_length": 6,
            "invoice_date_offset": 5,
            "invoice_date_custom_format": True,
            "invoice_date_custom_format_string": "%Y-%m-%d",
            "estore_store_number": "12345",
            "fintech_division_id": "DIV001",
            "include_headers": "True",
            "filter_ampersand": "True",
            "simple_csv_sort_order": "item_number",
            "plugin_configurations": {"csv": {"key": "value"}},
        }

        config = FolderConfiguration.from_dict(original_data)
        result_data = config.to_dict()

        # Check that all key fields are preserved
        assert result_data["folder_name"] == original_data["folder_name"]
        assert result_data["ftp_server"] == original_data["ftp_server"]
        assert result_data["email_to"] == original_data["email_to"]
        assert result_data["copy_to_directory"] == original_data["copy_to_directory"]
        assert (
            result_data["plugin_configurations"]
            == original_data["plugin_configurations"]
        )


class TestPluginConfigurationManagement:
    """Test suite for plugin configuration management."""

    def test_get_plugin_configuration_empty(self):
        """Test getting plugin configuration when none exists."""
        config = FolderConfiguration()
        result = config.get_plugin_configuration("csv")
        assert result is None

    def test_set_plugin_configuration(self):
        """Test setting plugin configuration."""
        config = FolderConfiguration()
        plugin_config = {"key1": "value1", "key2": "value2"}
        config.set_plugin_configuration("csv", plugin_config)

        result = config.get_plugin_configuration("csv")
        assert result is not None
        assert result == plugin_config

    def test_set_plugin_configuration_case_insensitive(self):
        """Test that plugin configuration format is case-insensitive."""
        config = FolderConfiguration()
        plugin_config = {"key": "value"}
        config.set_plugin_configuration("CSV", plugin_config)

        result = config.get_plugin_configuration("csv")
        assert result is not None
        assert result == plugin_config

    def test_remove_plugin_configuration(self):
        """Test removing plugin configuration."""
        config = FolderConfiguration()
        config.set_plugin_configuration("csv", {"key": "value"})
        config.remove_plugin_configuration("csv")

        result = config.get_plugin_configuration("csv")
        assert result is None

    def test_has_plugin_configuration(self):
        """Test checking if plugin configuration exists."""
        config = FolderConfiguration()
        assert config.has_plugin_configuration("csv") is False

        config.set_plugin_configuration("csv", {"key": "value"})
        assert config.has_plugin_configuration("csv") is True

    def test_has_plugin_configuration_case_insensitive(self):
        """Test that has_plugin_configuration is case-insensitive."""
        config = FolderConfiguration()
        config.set_plugin_configuration("CSV", {"key": "value"})

        assert config.has_plugin_configuration("csv") is True
        assert config.has_plugin_configuration("CSV") is True

    def test_multiple_plugin_configurations(self):
        """Test managing multiple plugin configurations."""
        config = FolderConfiguration()
        config.set_plugin_configuration("csv", {"csv_key": "csv_value"})
        config.set_plugin_configuration("scannerware", {"scanner_key": "scanner_value"})
        config.set_plugin_configuration("fintech", {"fintech_key": "fintech_value"})

        assert config.has_plugin_configuration("csv") is True
        assert config.has_plugin_configuration("scannerware") is True
        assert config.has_plugin_configuration("fintech") is True

        csv_result = config.get_plugin_configuration("csv")
        assert csv_result == {"csv_key": "csv_value"}

        scanner_result = config.get_plugin_configuration("scannerware")
        assert scanner_result == {"scanner_key": "scanner_value"}

    def test_plugin_configurations_in_roundtrip(self):
        """Test that plugin configurations survive roundtrip."""
        config = FolderConfiguration(folder_name="/test")
        config.set_plugin_configuration("csv", {"csv_key": "csv_value"})
        config.set_plugin_configuration("scannerware", {"scanner_key": "scanner_value"})

        data = config.to_dict()
        new_config = FolderConfiguration.from_dict(data)

        assert new_config.has_plugin_configuration("csv") is True
        assert new_config.has_plugin_configuration("scannerware") is True

        csv_result = new_config.get_plugin_configuration("csv")
        assert csv_result == {"csv_key": "csv_value"}


class TestPluginConfigurationValidation:
    """Test suite for plugin configuration validation."""

    def test_validate_plugin_configurations_empty(self):
        """Test validation with no plugin configurations."""
        config = FolderConfiguration()
        errors = config.validate_plugin_configurations()
        assert len(errors) == 0

    @patch("interface.plugins.plugin_manager.PluginManager")
    def test_validate_plugin_configurations_success(self, mock_plugin_manager):
        """Test validation succeeds with valid plugin configurations."""
        # Mock plugin manager and validation result
        mock_plugin = MagicMock()
        mock_validation = MagicMock()
        mock_validation.success = True
        mock_validation.errors = []
        mock_plugin.validate_config.return_value = mock_validation

        mock_pm_instance = MagicMock()
        mock_pm_instance.get_configuration_plugin_by_format_name.return_value = (
            mock_plugin
        )
        mock_plugin_manager.return_value = mock_pm_instance

        config = FolderConfiguration()
        config.set_plugin_configuration("csv", {"key": "value"})

        errors = config.validate_plugin_configurations()
        assert len(errors) == 0

    @patch("interface.plugins.plugin_manager.PluginManager")
    def test_validate_plugin_configurations_failure(self, mock_plugin_manager):
        """Test validation fails with invalid plugin configurations."""
        # Mock plugin manager and validation result
        mock_plugin = MagicMock()
        mock_validation = MagicMock()
        mock_validation.success = False
        mock_validation.errors = ["Invalid configuration"]
        mock_plugin.validate_config.return_value = mock_validation

        mock_pm_instance = MagicMock()
        mock_pm_instance.get_configuration_plugin_by_format_name.return_value = (
            mock_plugin
        )
        mock_plugin_manager.return_value = mock_pm_instance

        config = FolderConfiguration()
        config.set_plugin_configuration("csv", {"invalid": "config"})

        errors = config.validate_plugin_configurations()
        assert len(errors) > 0
        assert any("Plugin config for csv" in error for error in errors)

    @patch("interface.plugins.plugin_manager.PluginManager")
    def test_validate_plugin_configurations_no_plugin(self, mock_plugin_manager):
        """Test validation when no plugin found for format."""
        mock_pm_instance = MagicMock()
        mock_pm_instance.get_configuration_plugin_by_format_name.return_value = None
        mock_plugin_manager.return_value = mock_pm_instance

        config = FolderConfiguration()
        config.set_plugin_configuration("unknown_format", {"key": "value"})

        errors = config.validate_plugin_configurations()
        assert len(errors) > 0
        assert any(
            "No configuration plugin found for format" in error for error in errors
        )

    @patch("interface.plugins.plugin_manager.PluginManager")
    def test_validate_plugin_configurations_exception(self, mock_plugin_manager):
        """Test validation handles exceptions gracefully."""
        mock_plugin_manager.side_effect = Exception("Plugin manager error")

        config = FolderConfiguration()
        config.set_plugin_configuration("csv", {"key": "value"})

        errors = config.validate_plugin_configurations()
        assert len(errors) > 0
        assert any(
            "Error validating plugin configurations" in error for error in errors
        )


class TestEnums:
    """Test suite for enums."""

    def test_backend_type_enum(self):
        """Test BackendType enum values."""
        assert BackendType.COPY.value == "copy"
        assert BackendType.FTP.value == "ftp"
        assert BackendType.EMAIL.value == "email"

    def test_convert_format_enum(self):
        """Test ConvertFormat enum values."""
        assert ConvertFormat.CSV.value == "csv"
        assert ConvertFormat.SCANNERWARE.value == "ScannerWare"
        assert ConvertFormat.FINTECH.value == "fintech"
        assert ConvertFormat.DO_NOTHING.value == "do_nothing"

    def test_convert_format_enum_completeness(self):
        """Test that all expected convert formats are in enum."""
        expected_formats = [
            "csv",
            "ScannerWare",
            "ScanSheet_Type_A",
            "jolley_custom",
            "eStore_eInvoice",
            "eStore_eInvoice_Generic",
            "fintech",
            "stewarts_custom",
            "yellowdog_csv",
            "simplified_csv",
            "do_nothing",
        ]
        actual_formats = [fmt.value for fmt in ConvertFormat]
        for fmt in expected_formats:
            assert fmt in actual_formats
