"""Folder Configuration Model tests for EditFoldersDialog refactoring."""

import pytest

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

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
    
    def test_default_values(self):
        """Test default values for FTPConfiguration."""
        config = FTPConfiguration()
        
        assert config.server == ""
        assert config.port == 21
        assert config.username == ""
        assert config.password == ""
        assert config.folder == ""
    
    def test_custom_values(self):
        """Test custom values for FTPConfiguration."""
        config = FTPConfiguration(
            server="ftp.example.com",
            port=990,
            username="testuser",
            password="testpass",
            folder="/uploads/"
        )
        
        assert config.server == "ftp.example.com"
        assert config.port == 990
        assert config.username == "testuser"
        assert config.password == "testpass"
        assert config.folder == "/uploads/"
    
    def test_validate_valid_config(self):
        """Test validation passes for valid FTP config."""
        config = FTPConfiguration(
            server="ftp.example.com",
            username="user",
            password="pass",
            folder="/uploads/"
        )
        
        errors = config.validate()
        
        assert len(errors) == 0
    
    def test_validate_missing_server(self):
        """Test validation fails when server is missing."""
        config = FTPConfiguration(
            server="",
            username="user",
            password="pass",
            folder="/uploads/"
        )
        
        errors = config.validate()
        
        assert len(errors) > 0
        assert any("Server" in e for e in errors)
    
    def test_validate_missing_username(self):
        """Test validation fails when username is missing."""
        config = FTPConfiguration(
            server="ftp.example.com",
            username="",
            password="pass",
            folder="/uploads/"
        )
        
        errors = config.validate()
        
        assert len(errors) > 0
        assert any("Username" in e for e in errors)
    
    def test_validate_missing_password(self):
        """Test validation fails when password is missing."""
        config = FTPConfiguration(
            server="ftp.example.com",
            username="user",
            password="",
            folder="/uploads/"
        )
        
        errors = config.validate()
        
        assert len(errors) > 0
        assert any("Password" in e for e in errors)
    
    def test_validate_missing_folder(self):
        """Test validation fails when folder is missing."""
        config = FTPConfiguration(
            server="ftp.example.com",
            username="user",
            password="pass",
            folder=""
        )
        
        errors = config.validate()
        
        assert len(errors) > 0
        assert any("Folder" in e for e in errors)
    
    def test_validate_folder_without_trailing_slash(self):
        """Test validation fails when folder doesn't end with /."""
        config = FTPConfiguration(
            server="ftp.example.com",
            username="user",
            password="pass",
            folder="uploads"
        )
        
        errors = config.validate()
        
        assert len(errors) > 0
        assert any("end in" in e.lower() or "trailing" in e.lower() for e in errors)
    
    def test_validate_invalid_port(self):
        """Test validation fails for invalid port."""
        config = FTPConfiguration(
            server="ftp.example.com",
            port=70000,
            username="user",
            password="pass",
            folder="/uploads/"
        )
        
        errors = config.validate()
        
        assert len(errors) > 0
        assert any("Port" in e for e in errors)
    
    def test_validate_non_numeric_port(self):
        """Test validation fails for non-numeric port."""
        config = FTPConfiguration(
            server="ftp.example.com",
            port="invalid",
            username="user",
            password="pass",
            folder="/uploads/"
        )
        
        errors = config.validate()
        
        assert len(errors) > 0
        assert any("number" in e.lower() for e in errors)


class TestEmailConfiguration:
    """Test suite for EmailConfiguration."""
    
    def test_default_values(self):
        """Test default values for EmailConfiguration."""
        config = EmailConfiguration()
        
        assert config.recipients == ""
        assert config.subject_line == ""
        assert config.sender_address is None
    
    def test_custom_values(self):
        """Test custom values for EmailConfiguration."""
        config = EmailConfiguration(
            recipients="test@example.com, other@example.com",
            subject_line="Test Subject",
            sender_address="sender@example.com"
        )
        
        assert config.recipients == "test@example.com, other@example.com"
        assert config.subject_line == "Test Subject"
        assert config.sender_address == "sender@example.com"
    
    def test_validate_valid_email(self):
        """Test validation passes for valid email."""
        config = EmailConfiguration(
            recipients="test@example.com"
        )
        
        errors = config.validate()
        
        assert len(errors) == 0
    
    def test_validate_multiple_valid_emails(self):
        """Test validation passes for multiple valid emails."""
        config = EmailConfiguration(
            recipients="test@example.com, other@example.com, third@example.com"
        )
        
        errors = config.validate()
        
        assert len(errors) == 0
    
    def test_validate_missing_recipients(self):
        """Test validation fails when recipients are missing."""
        config = EmailConfiguration(recipients="")
        
        errors = config.validate()
        
        assert len(errors) > 0
        assert any("Required" in e for e in errors)
    
    def test_validate_invalid_email(self):
        """Test validation fails for invalid email."""
        config = EmailConfiguration(recipients="invalid-email")
        
        errors = config.validate()
        
        assert len(errors) > 0
        assert any("Invalid" in e for e in errors)

    def test_validate_email_with_special_chars(self):
        """Test validation passes for email with special characters."""
        config = EmailConfiguration(
            recipients="test+tag@example-domain.co.uk"
        )
        
        errors = config.validate()
        
        # Should pass (special chars are valid in local part)
        assert len(errors) == 0


class TestCopyConfiguration:
    """Test suite for CopyConfiguration."""
    
    def test_default_values(self):
        """Test default values for CopyConfiguration."""
        config = CopyConfiguration()
        
        assert config.destination_directory == ""
    
    def test_custom_values(self):
        """Test custom values for CopyConfiguration."""
        config = CopyConfiguration(
            destination_directory="/output/path"
        )
        
        assert config.destination_directory == "/output/path"
    
    def test_validate_valid(self):
        """Test validation passes for valid copy config."""
        config = CopyConfiguration(
            destination_directory="/output/path"
        )
        
        errors = config.validate()
        
        assert len(errors) == 0
    
    def test_validate_missing_destination(self):
        """Test validation fails when destination is missing."""
        config = CopyConfiguration(destination_directory="")
        
        errors = config.validate()
        
        assert len(errors) > 0
        assert any("destination" in e.lower() for e in errors)


class TestEDIConfiguration:
    """Test suite for EDIConfiguration."""
    
    def test_default_values(self):
        """Test default values for EDIConfiguration."""
        config = EDIConfiguration()
        
        assert config.process_edi == "False"
        assert config.tweak_edi is False
        assert config.split_edi is False
        assert config.split_edi_include_invoices is False
        assert config.split_edi_include_credits is False
        assert config.prepend_date_files is False
        assert config.convert_to_format == ""
        assert config.force_edi_validation is False
        assert config.rename_file == ""
        assert config.split_edi_filter_categories == "ALL"
        assert config.split_edi_filter_mode == "include"
    
    def test_validate_prepend_without_split(self):
        """Test validation fails when prepending dates without splitting."""
        config = EDIConfiguration(
            split_edi=False,
            prepend_date_files=True
        )
        
        errors = config.validate()
        
        assert len(errors) > 0
        assert any("split" in e.lower() for e in errors)
    
    def test_validate_prepend_with_split(self):
        """Test validation passes when prepending dates with splitting."""
        config = EDIConfiguration(
            split_edi=True,
            prepend_date_files=True
        )
        
        errors = config.validate()
        
        assert len(errors) == 0


class TestUPCOverrideConfiguration:
    """Test suite for UPCOverrideConfiguration."""
    
    def test_default_values(self):
        """Test default values for UPCOverrideConfiguration."""
        config = UPCOverrideConfiguration()
        
        assert config.enabled is False
        assert config.level == 1
        assert config.category_filter == ""
        assert config.target_length == 11
        assert config.padding_pattern == "           "
    
    def test_validate_disabled(self):
        """Test validation passes when UPC override is disabled."""
        config = UPCOverrideConfiguration(
            enabled=False,
            category_filter=""
        )
        
        errors = config.validate()
        
        assert len(errors) == 0
    
    def test_validate_enabled_missing_filter(self):
        """Test validation fails when enabled but filter is missing."""
        config = UPCOverrideConfiguration(
            enabled=True,
            category_filter=""
        )
        
        errors = config.validate()
        
        assert len(errors) > 0
        assert any("category filter" in e.lower() for e in errors)
    
    def test_validate_enabled_valid_filter(self):
        """Test validation passes when enabled with valid filter."""
        config = UPCOverrideConfiguration(
            enabled=True,
            category_filter="1,2,3,ALL"
        )
        
        errors = config.validate()
        
        assert len(errors) == 0
    
    def test_validate_enabled_invalid_category(self):
        """Test validation fails when category is invalid."""
        config = UPCOverrideConfiguration(
            enabled=True,
            category_filter="1,150,ALL"  # 150 is out of range
        )
        
        errors = config.validate()
        
        assert len(errors) > 0
        assert any("category filter" in e.lower() for e in errors)


class TestARecordPaddingConfiguration:
    """Test suite for ARecordPaddingConfiguration."""
    
    def test_default_values(self):
        """Test default values for ARecordPaddingConfiguration."""
        config = ARecordPaddingConfiguration()
        
        assert config.enabled is False
        assert config.padding_text == ""
        assert config.padding_length == 6
        assert config.append_text == ""
        assert config.append_enabled is False
        assert config.force_txt_extension is False
    
    def test_validate_valid_padding(self):
        """Test validation passes for valid padding."""
        config = ARecordPaddingConfiguration(
            enabled=True,
            padding_text="123456",
            padding_length=6
        )
        
        errors = config.validate()
        
        assert len(errors) == 0
    
    def test_validate_padding_too_long(self):
        """Test validation fails when padding text is too long."""
        config = ARecordPaddingConfiguration(
            enabled=True,
            padding_text="123456789",
            padding_length=6
        )
        
        errors = config.validate()
        
        assert len(errors) > 0
        assert any("padding" in e.lower() for e in errors)
    
    def test_validate_padding_not_six_chars(self):
        """Test validation fails when padding is not 6 chars."""
        config = ARecordPaddingConfiguration(
            enabled=True,
            padding_text="12345",
            padding_length=6
        )
        
        errors = config.validate()
        
        assert len(errors) > 0
        assert any("six" in e.lower() for e in errors)


class TestInvoiceDateConfiguration:
    """Test suite for InvoiceDateConfiguration."""
    
    def test_default_values(self):
        """Test default values for InvoiceDateConfiguration."""
        config = InvoiceDateConfiguration()
        
        assert config.offset == 0
        assert config.custom_format_enabled is False
        assert config.custom_format_string == ""
        assert config.retail_uom is False
    
    def test_validate_valid_offset(self):
        """Test validation passes for valid offsets."""
        config = InvoiceDateConfiguration()
        
        for offset in range(-14, 15):
            errors = config.validate()
            assert len(errors) == 0, f"Offset {offset} should be valid"
    
    def test_validate_offset_too_high(self):
        """Test validation fails for offset too high."""
        config = InvoiceDateConfiguration(offset=15)
        
        errors = config.validate()
        
        assert len(errors) > 0
        assert any("offset" in e.lower() for e in errors)
    
    def test_validate_offset_too_low(self):
        """Test validation fails for offset too low."""
        config = InvoiceDateConfiguration(offset=-15)
        
        errors = config.validate()
        
        assert len(errors) > 0
        assert any("offset" in e.lower() for e in errors)


class TestFolderConfiguration:
    """Test suite for FolderConfiguration."""
    
    def test_default_values(self):
        """Test default values for FolderConfiguration."""
        config = FolderConfiguration()
        
        # Identity
        assert config.folder_name == ""
        assert config.folder_is_active == "False"
        assert config.alias == ""
        assert config.is_template is False
        
        # Backend toggles
        assert config.process_backend_copy is False
        assert config.process_backend_ftp is False
        assert config.process_backend_email is False
        
        # Backend configs
        assert config.ftp is None
        assert config.email is None
        assert config.copy is None
        
        # EDI - None by default, created via from_dict or explicitly
        assert config.edi is None
        
        # UPC Override
        assert config.upc_override is None
        
        # A-Record - None by default
        assert config.a_record_padding is None
        
        # Invoice Date - None by default
        assert config.invoice_date is None
        
        # Backend-specific - None by default
        assert config.backend_specific is None
        
        # CSV - None by default
        assert config.csv is None
    
    def test_from_dict_minimal(self):
        """Test from_dict with minimal data."""
        data = {
            'folder_name': 'test_folder'
        }
        
        config = FolderConfiguration.from_dict(data)
        
        assert config.folder_name == 'test_folder'
        assert config.folder_is_active == 'False'
        assert config.alias == ""
        assert config.is_template is False
    
    def test_from_dict_full_ftp(self):
        """Test from_dict with full FTP configuration."""
        data = {
            'folder_name': 'test_folder',
            'folder_is_active': 'True',
            'alias': 'test-alias',
            'process_backend_ftp': True,
            'ftp_server': 'ftp.example.com',
            'ftp_port': 21,
            'ftp_username': 'user',
            'ftp_password': 'pass',
            'ftp_folder': '/uploads/'
        }
        
        config = FolderConfiguration.from_dict(data)
        
        assert config.folder_name == 'test_folder'
        assert config.folder_is_active == 'True'
        assert config.alias == 'test-alias'
        assert config.process_backend_ftp is True
        assert config.ftp is not None
        assert config.ftp.server == 'ftp.example.com'
        assert config.ftp.port == 21
        assert config.ftp.username == 'user'
        assert config.ftp.password == 'pass'
        assert config.ftp.folder == '/uploads/'
    
    def test_from_dict_full_email(self):
        """Test from_dict with full email configuration."""
        data = {
            'folder_name': 'test_folder',
            'process_backend_email': True,
            'email_to': 'test@example.com',
            'email_subject_line': 'Test Subject'
        }
        
        config = FolderConfiguration.from_dict(data)
        
        assert config.process_backend_email is True
        assert config.email is not None
        assert config.email.recipients == 'test@example.com'
        assert config.email.subject_line == 'Test Subject'
    
    def test_from_dict_copy(self):
        """Test from_dict with copy configuration."""
        data = {
            'folder_name': 'test_folder',
            'process_backend_copy': True,
            'copy_to_directory': '/output/path'
        }
        
        config = FolderConfiguration.from_dict(data)
        
        assert config.process_backend_copy is True
        assert config.copy is not None
        assert config.copy.destination_directory == '/output/path'
    
    def test_from_dict_edi(self):
        """Test from_dict with EDI configuration."""
        data = {
            'folder_name': 'test_folder',
            'process_edi': 'True',
            'split_edi': True,
            'convert_to_format': 'csv',
            'tweak_edi': True
        }
        
        config = FolderConfiguration.from_dict(data)
        
        assert config.edi is not None
        assert config.edi.process_edi == 'True'
        assert config.edi.split_edi is True
        assert config.edi.convert_to_format == 'csv'
        assert config.edi.tweak_edi is True
    
    def test_from_dict_upc_override(self):
        """Test from_dict with UPC override configuration."""
        data = {
            'folder_name': 'test_folder',
            'override_upc_bool': True,
            'override_upc_level': 2,
            'override_upc_category_filter': '1,2,3',
            'upc_target_length': 12
        }
        
        config = FolderConfiguration.from_dict(data)
        
        assert config.upc_override is not None
        assert config.upc_override.enabled is True
        assert config.upc_override.level == 2
        assert config.upc_override.category_filter == '1,2,3'
        assert config.upc_override.target_length == 12
    
    def test_from_dict_a_record_padding(self):
        """Test from_dict with A-record padding configuration."""
        data = {
            'folder_name': 'test_folder',
            'pad_a_records': 'True',
            'a_record_padding': '123456',
            'a_record_padding_length': 6,
            'append_a_records': 'True',
            'a_record_append_text': 'APPEND'
        }
        
        config = FolderConfiguration.from_dict(data)
        
        assert config.a_record_padding is not None
        assert config.a_record_padding.enabled is True
        assert config.a_record_padding.padding_text == '123456'
        assert config.a_record_padding.append_enabled is True
        assert config.a_record_padding.append_text == 'APPEND'
    
    def test_from_dict_invoice_date(self):
        """Test from_dict with invoice date configuration."""
        data = {
            'folder_name': 'test_folder',
            'invoice_date_offset': 5,
            'invoice_date_custom_format': True,
            'invoice_date_custom_format_string': '%Y%m%d',
            'retail_uom': True
        }
        
        config = FolderConfiguration.from_dict(data)
        
        assert config.invoice_date is not None
        assert config.invoice_date.offset == 5
        assert config.invoice_date.custom_format_enabled is True
        assert config.invoice_date.custom_format_string == '%Y%m%d'
        assert config.invoice_date.retail_uom is True
    
    def test_from_dict_backend_specific(self):
        """Test from_dict with backend-specific configuration."""
        data = {
            'folder_name': 'test_folder',
            'estore_store_number': '123',
            'estore_Vendor_OId': 'vendor123',
            'fintech_division_id': 'div456'
        }
        
        config = FolderConfiguration.from_dict(data)
        
        assert config.backend_specific is not None
        assert config.backend_specific.estore_store_number == '123'
        assert config.backend_specific.estore_vendor_oid == 'vendor123'
        assert config.backend_specific.fintech_division_id == 'div456'
    
    def test_from_dict_csv(self):
        """Test from_dict with CSV configuration."""
        data = {
            'folder_name': 'test_folder',
            'include_headers': 'True',
            'filter_ampersand': 'True',
            'include_item_numbers': True,
            'include_item_description': True
        }
        
        config = FolderConfiguration.from_dict(data)
        
        assert config.csv is not None
        assert config.csv.include_headers is True
        assert config.csv.filter_ampersand is True
        assert config.csv.include_item_numbers is True
        assert config.csv.include_item_description is True
    
    def test_from_dict_template(self):
        """Test from_dict detects template."""
        data = {
            'folder_name': 'template'
        }
        
        config = FolderConfiguration.from_dict(data)
        
        assert config.is_template is True
    
    def test_to_dict_minimal(self):
        """Test to_dict with minimal configuration."""
        config = FolderConfiguration(folder_name='test')
        
        result = config.to_dict()
        
        assert result['folder_name'] == 'test'
        assert result['folder_is_active'] == 'False'
        assert 'ftp_server' not in result
        assert 'email_to' not in result
    
    def test_to_dict_with_ftp(self):
        """Test to_dict with FTP configuration."""
        config = FolderConfiguration(
            folder_name='test',
            process_backend_ftp=True,
            ftp=FTPConfiguration(
                server='ftp.example.com',
                port=21,
                username='user',
                password='pass',
                folder='/uploads/'
            )
        )
        
        result = config.to_dict()
        
        assert result['ftp_server'] == 'ftp.example.com'
        assert result['ftp_port'] == 21
        assert result['ftp_username'] == 'user'
        assert result['ftp_password'] == 'pass'
        assert result['ftp_folder'] == '/uploads/'
    
    def test_to_dict_with_email(self):
        """Test to_dict with email configuration."""
        config = FolderConfiguration(
            folder_name='test',
            process_backend_email=True,
            email=EmailConfiguration(
                recipients='test@example.com',
                subject_line='Subject'
            )
        )
        
        result = config.to_dict()
        
        assert result['email_to'] == 'test@example.com'
        assert result['email_subject_line'] == 'Subject'
    
    def test_to_dict_with_copy(self):
        """Test to_dict with copy configuration."""
        config = FolderConfiguration(
            folder_name='test',
            process_backend_copy=True,
            copy=CopyConfiguration(
                destination_directory='/output/path'
            )
        )
        
        result = config.to_dict()
        
        assert result['copy_to_directory'] == '/output/path'
    
    def test_to_dict_with_edi(self):
        """Test to_dict with EDI configuration."""
        config = FolderConfiguration(
            folder_name='test',
            edi=EDIConfiguration(
                process_edi='True',
                split_edi=True,
                convert_to_format='csv'
            )
        )
        
        result = config.to_dict()
        
        assert result['process_edi'] == 'True'
        assert result['split_edi'] is True
        assert result['convert_to_format'] == 'csv'
    
    def test_to_dict_with_upc_override(self):
        """Test to_dict with UPC override configuration."""
        config = FolderConfiguration(
            folder_name='test',
            upc_override=UPCOverrideConfiguration(
                enabled=True,
                level=2,
                category_filter='1,2,3'
            )
        )
        
        result = config.to_dict()
        
        assert result['override_upc_bool'] is True
        assert result['override_upc_level'] == 2
        assert result['override_upc_category_filter'] == '1,2,3'
    
    def test_roundtrip_from_dict_to_dict(self):
        """Test that from_dict followed by to_dict preserves data."""
        original_data = {
            'folder_name': 'test_folder',
            'folder_is_active': 'True',
            'alias': 'test-alias',
            'process_backend_ftp': True,
            'ftp_server': 'ftp.example.com',
            'ftp_port': 21,
            'ftp_username': 'user',
            'ftp_password': 'pass',
            'ftp_folder': '/uploads/',
            'process_backend_email': True,
            'email_to': 'test@example.com',
            'email_subject_line': 'Subject',
            'process_backend_copy': True,
            'copy_to_directory': '/output/path',
            'process_edi': 'True',
            'convert_to_format': 'csv'
        }
        
        config = FolderConfiguration.from_dict(original_data)
        result = config.to_dict()
        
        assert result['folder_name'] == original_data['folder_name']
        assert result['folder_is_active'] == original_data['folder_is_active']
        assert result['ftp_server'] == original_data['ftp_server']
        assert result['email_to'] == original_data['email_to']
        assert result['copy_to_directory'] == original_data['copy_to_directory']


class TestBackendSpecificConfiguration:
    """Test suite for BackendSpecificConfiguration."""
    
    def test_default_values(self):
        """Test default values for BackendSpecificConfiguration."""
        config = BackendSpecificConfiguration()
        
        assert config.estore_store_number == ""
        assert config.estore_vendor_oid == ""
        assert config.estore_vendor_namevendoroid == ""
        assert config.fintech_division_id == ""
    
    def test_custom_values(self):
        """Test custom values for BackendSpecificConfiguration."""
        config = BackendSpecificConfiguration(
            estore_store_number='123',
            estore_vendor_oid='vendor123',
            estore_vendor_namevendoroid='vendor_name_oid',
            fintech_division_id='div456'
        )
        
        assert config.estore_store_number == '123'
        assert config.estore_vendor_oid == 'vendor123'
        assert config.estore_vendor_namevendoroid == 'vendor_name_oid'
        assert config.fintech_division_id == 'div456'


class TestCSVConfiguration:
    """Test suite for CSVConfiguration."""
    
    def test_default_values(self):
        """Test default values for CSVConfiguration."""
        config = CSVConfiguration()
        
        assert config.include_headers is False
        assert config.filter_ampersand is False
        assert config.include_item_numbers is False
        assert config.include_item_description is False
        assert config.simple_csv_sort_order == ""
        assert config.split_prepaid_sales_tax_crec is False
    
    def test_custom_values(self):
        """Test custom values for CSVConfiguration."""
        config = CSVConfiguration(
            include_headers=True,
            filter_ampersand=True,
            include_item_numbers=True,
            include_item_description=True,
            simple_csv_sort_order='name,quantity,price',
            split_prepaid_sales_tax_crec=True
        )
        
        assert config.include_headers is True
        assert config.filter_ampersand is True
        assert config.include_item_numbers is True
        assert config.include_item_description is True
        assert config.simple_csv_sort_order == 'name,quantity,price'
        assert config.split_prepaid_sales_tax_crec is True


class TestBackendType:
    """Test suite for BackendType enum."""
    
    def test_enum_values(self):
        """Test BackendType enum values."""
        assert BackendType.COPY.value == "copy"
        assert BackendType.FTP.value == "ftp"
        assert BackendType.EMAIL.value == "email"


class TestConvertFormat:
    """Test suite for ConvertFormat enum."""
    
    def test_enum_values(self):
        """Test ConvertFormat enum values."""
        assert ConvertFormat.CSV.value == "csv"
        assert ConvertFormat.SCANNERWARE.value == "ScannerWare"
        assert ConvertFormat.FINTECH.value == "fintech"
        assert ConvertFormat.DO_NOTHING.value == "do_nothing"
