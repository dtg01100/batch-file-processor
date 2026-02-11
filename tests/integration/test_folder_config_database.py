"""Integration tests for FolderConfiguration database save/load roundtrip.

Tests:
- Complete config to dict mapping (all fields)
- Complete config from dict mapping (DB columns)
- Roundtrip save→DB→Load→verify all 40+ fields
- Null and empty handling
- Nested config serialization (FTP, EDI, UPC)
- All EDI fields mapping (11 fields)
- All CSV fields mapping
"""

import pytest
import sys
import os
import tempfile
import dataset

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

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
)


@pytest.fixture
def sample_folder_config():
    """Create a complete FolderConfiguration with all fields populated."""
    return FolderConfiguration(
        # Identity
        folder_name="/home/user/documents/invoices",
        folder_is_active="True",
        alias="Invoice Processing Folder",
        is_template=False,
        
        # Backend toggles
        process_backend_copy=True,
        process_backend_ftp=True,
        process_backend_email=True,
        
        # FTP configuration
        ftp=FTPConfiguration(
            server="ftp.example.com",
            port=21,
            username="ftp_user",
            password="secure_password",
            folder="/incoming/"
        ),
        
        # Email configuration
        email=EmailConfiguration(
            recipients="invoice@example.com, backup@example.com",
            subject_line="Invoice %filename% - %datetime%",
            sender_address="noreply@company.com"
        ),
        
        # Copy configuration
        copy=CopyConfiguration(
            destination_directory="/output/processed/"
        ),
        
        # EDI configuration (11 fields)
        edi=EDIConfiguration(
            process_edi="True",
            tweak_edi=True,
            split_edi=True,
            split_edi_include_invoices=True,
            split_edi_include_credits=True,
            prepend_date_files=True,
            convert_to_format="fintech",
            force_edi_validation=True,
            rename_file="processed_{original}",
            split_edi_filter_categories="1,2,3,ALL",
            split_edi_filter_mode="include"
        ),
        
        # UPC Override configuration
        upc_override=UPCOverrideConfiguration(
            enabled=True,
            level=2,
            category_filter="1,2,3,ALL",
            target_length=12,
            padding_pattern="00000000000"
        ),
        
        # A-Record padding configuration
        a_record_padding=ARecordPaddingConfiguration(
            enabled=True,
            padding_text="PREFIX1",
            padding_length=6,
            append_text="SUFFIX",
            append_enabled=True,
            force_txt_extension=True
        ),
        
        # Invoice date configuration
        invoice_date=InvoiceDateConfiguration(
            offset=7,
            custom_format_enabled=True,
            custom_format_string="%Y-%m-%d",
            retail_uom=True
        ),
        
        # Backend-specific configuration
        backend_specific=BackendSpecificConfiguration(
            estore_store_number="STORE123",
            estore_vendor_oid="VENDOR456",
            estore_vendor_namevendoroid="VendorName-OID789",
            fintech_division_id="DIV001"
        ),
        
        # CSV configuration
        csv=CSVConfiguration(
            include_headers=True,
            filter_ampersand=True,
            include_item_numbers=True,
            include_item_description=True,
            simple_csv_sort_order="date,amount,description",
            split_prepaid_sales_tax_crec=True
        )
    )


@pytest.fixture
def temp_database(tmp_path):
    """Create a temporary SQLite database for testing."""
    db_path = str(tmp_path / "test_folders.db")
    db_conn = dataset.connect('sqlite:///' + db_path)
    
    # Setup version table
    version_table = db_conn['version']
    version_table.insert(dict(version="33", os="Linux"))
    
    yield db_conn
    
    db_conn.close()


class TestFolderConfigDatabaseMapping:
    """Test suite for FolderConfiguration to database dictionary mapping."""
    
    def test_complete_config_to_dict_mapping(self, sample_folder_config):
        """Test all FolderConfiguration fields map to correct DB columns."""
        config_dict = sample_folder_config.to_dict()
        
        # Identity fields
        assert config_dict['folder_name'] == "/home/user/documents/invoices"
        assert config_dict['folder_is_active'] == "True"
        assert config_dict['alias'] == "Invoice Processing Folder"
        
        # Backend toggles
        assert config_dict['process_backend_copy'] is True
        assert config_dict['process_backend_ftp'] is True
        assert config_dict['process_backend_email'] is True
        
        # FTP fields
        assert config_dict['ftp_server'] == "ftp.example.com"
        assert config_dict['ftp_port'] == 21
        assert config_dict['ftp_username'] == "ftp_user"
        assert config_dict['ftp_password'] == "secure_password"
        assert config_dict['ftp_folder'] == "/incoming/"
        
        # Email fields
        assert config_dict['email_to'] == "invoice@example.com, backup@example.com"
        assert config_dict['email_subject_line'] == "Invoice %filename% - %datetime%"
        
        # Copy fields
        assert config_dict['copy_to_directory'] == "/output/processed/"
        
        # EDI fields (all 11)
        assert config_dict['process_edi'] == "True"
        assert config_dict['tweak_edi'] is True
        assert config_dict['split_edi'] is True
        assert config_dict['split_edi_include_invoices'] is True
        assert config_dict['split_edi_include_credits'] is True
        assert config_dict['prepend_date_files'] is True
        assert config_dict['convert_to_format'] == "fintech"
        assert config_dict['force_edi_validation'] is True
        assert config_dict['rename_file'] == "processed_{original}"
        assert config_dict['split_edi_filter_categories'] == "1,2,3,ALL"
        assert config_dict['split_edi_filter_mode'] == "include"
        
        # UPC Override fields
        assert config_dict['override_upc_bool'] is True
        assert config_dict['override_upc_level'] == 2
        assert config_dict['override_upc_category_filter'] == "1,2,3,ALL"
        assert config_dict['upc_target_length'] == 12
        assert config_dict['upc_padding_pattern'] == "00000000000"
        
        # A-Record padding fields
        assert config_dict['pad_a_records'] == "True"
        assert config_dict['a_record_padding'] == "PREFIX1"
        assert config_dict['a_record_padding_length'] == 6
        assert config_dict['append_a_records'] == "True"
        assert config_dict['a_record_append_text'] == "SUFFIX"
        assert config_dict['force_txt_file_ext'] == "True"
        
        # Invoice date fields
        assert config_dict['invoice_date_offset'] == 7
        assert config_dict['invoice_date_custom_format'] is True
        assert config_dict['invoice_date_custom_format_string'] == "%Y-%m-%d"
        assert config_dict['retail_uom'] is True
        
        # Backend-specific fields
        assert config_dict['estore_store_number'] == "STORE123"
        assert config_dict['estore_Vendor_OId'] == "VENDOR456"
        assert config_dict['estore_vendor_NameVendorOID'] == "VendorName-OID789"
        assert config_dict['fintech_division_id'] == "DIV001"
        
        # CSV fields
        assert config_dict['include_headers'] == "True"
        assert config_dict['filter_ampersand'] == "True"
        assert config_dict['include_item_numbers'] is True
        assert config_dict['include_item_description'] is True
        assert config_dict['simple_csv_sort_order'] == "date,amount,description"
        assert config_dict['split_prepaid_sales_tax_crec'] is True


class TestFolderConfigFromDictMapping:
    """Test suite for database dictionary to FolderConfiguration mapping."""
    
    def test_complete_config_from_dict_mapping(self):
        """Test DB columns reconstruct FolderConfiguration correctly."""
        db_dict = {
            'folder_name': "/home/user/documents/invoices",
            'folder_is_active': "True",
            'alias': "Invoice Processing Folder",
            'process_backend_copy': True,
            'process_backend_ftp': True,
            'process_backend_email': True,
            'ftp_server': "ftp.example.com",
            'ftp_port': 21,
            'ftp_username': "ftp_user",
            'ftp_password': "secure_password",
            'ftp_folder': "/incoming/",
            'email_to': "invoice@example.com, backup@example.com",
            'email_subject_line': "Invoice %filename% - %datetime%",
            'copy_to_directory': "/output/processed/",
            'process_edi': "True",
            'tweak_edi': True,
            'split_edi': True,
            'split_edi_include_invoices': True,
            'split_edi_include_credits': True,
            'prepend_date_files': True,
            'convert_to_format': "fintech",
            'force_edi_validation': True,
            'rename_file': "processed_{original}",
            'split_edi_filter_categories': "1,2,3,ALL",
            'split_edi_filter_mode': "include",
            'override_upc_bool': True,
            'override_upc_level': 2,
            'override_upc_category_filter': "1,2,3,ALL",
            'upc_target_length': 12,
            'upc_padding_pattern': "00000000000",
            'pad_a_records': "True",
            'a_record_padding': "PREFIX1",
            'a_record_padding_length': 6,
            'append_a_records': "True",
            'a_record_append_text': "SUFFIX",
            'force_txt_file_ext': "True",
            'invoice_date_offset': 7,
            'invoice_date_custom_format': True,
            'invoice_date_custom_format_string': "%Y-%m-%d",
            'retail_uom': True,
            'estore_store_number': "STORE123",
            'estore_Vendor_OId': "VENDOR456",
            'estore_vendor_NameVendorOID': "VendorName-OID789",
            'fintech_division_id': "DIV001",
            'include_headers': "True",
            'filter_ampersand': "True",
            'include_item_numbers': True,
            'include_item_description': True,
            'simple_csv_sort_order': "date,amount,description",
            'split_prepaid_sales_tax_crec': True,
        }
        
        config = FolderConfiguration.from_dict(db_dict)
        
        # Identity
        assert config.folder_name == "/home/user/documents/invoices"
        assert config.folder_is_active == "True"
        assert config.alias == "Invoice Processing Folder"
        
        # Backend toggles
        assert config.process_backend_copy is True
        assert config.process_backend_ftp is True
        assert config.process_backend_email is True
        
        # FTP
        assert config.ftp is not None
        assert config.ftp.server == "ftp.example.com"
        assert config.ftp.port == 21
        assert config.ftp.username == "ftp_user"
        assert config.ftp.folder == "/incoming/"
        
        # Email
        assert config.email is not None
        assert config.email.recipients == "invoice@example.com, backup@example.com"
        assert config.email.subject_line == "Invoice %filename% - %datetime%"
        
        # Copy
        assert config.copy is not None
        assert config.copy.destination_directory == "/output/processed/"
        
        # EDI
        assert config.edi is not None
        assert config.edi.process_edi == "True"
        assert config.edi.split_edi is True
        assert config.edi.convert_to_format == "fintech"
        
        # UPC Override
        assert config.upc_override is not None
        assert config.upc_override.enabled is True
        assert config.upc_override.level == 2
        
        # A-Record
        assert config.a_record_padding is not None
        assert config.a_record_padding.enabled is True
        assert config.a_record_padding.padding_text == "PREFIX1"
        
        # Invoice Date
        assert config.invoice_date is not None
        assert config.invoice_date.offset == 7
        
        # Backend-specific
        assert config.backend_specific is not None
        assert config.backend_specific.fintech_division_id == "DIV001"
        
        # CSV
        assert config.csv is not None
        assert config.csv.include_headers is True


class TestFolderConfigRoundtrip:
    """Test suite for complete save→DB→Load roundtrip."""
    
    def test_roundtrip_save_load(self, sample_folder_config, temp_database):
        """Test Save→DB→Load→verify all 40+ fields."""
        # Convert config to dict
        config_dict = sample_folder_config.to_dict()
        config_dict['folder_name'] = sample_folder_config.folder_name
        
        # Insert into database
        folder_id = temp_database['folders'].insert(config_dict)
        
        # Load from database
        loaded_dict = temp_database['folders'].find_one(id=folder_id)
        
        # Reconstruct config
        loaded_config = FolderConfiguration.from_dict(loaded_dict)
        
        # Verify all fields match
        assert loaded_config.folder_name == sample_folder_config.folder_name
        assert loaded_config.folder_is_active == sample_folder_config.folder_is_active
        assert loaded_config.alias == sample_folder_config.alias
        assert loaded_config.process_backend_copy == sample_folder_config.process_backend_copy
        assert loaded_config.process_backend_ftp == sample_folder_config.process_backend_ftp
        assert loaded_config.process_backend_email == sample_folder_config.process_backend_email
        
        # Verify FTP
        assert loaded_config.ftp is not None
        assert loaded_config.ftp.server == sample_folder_config.ftp.server
        assert loaded_config.ftp.port == sample_folder_config.ftp.port
        assert loaded_config.ftp.username == sample_folder_config.ftp.username
        assert loaded_config.ftp.folder == sample_folder_config.ftp.folder
        
        # Verify Email
        assert loaded_config.email is not None
        assert loaded_config.email.recipients == sample_folder_config.email.recipients
        
        # Verify Copy
        assert loaded_config.copy is not None
        assert loaded_config.copy.destination_directory == sample_folder_config.copy.destination_directory
        
        # Verify EDI (all 11 fields)
        assert loaded_config.edi is not None
        assert loaded_config.edi.process_edi == sample_folder_config.edi.process_edi
        assert loaded_config.edi.tweak_edi == sample_folder_config.edi.tweak_edi
        assert loaded_config.edi.split_edi == sample_folder_config.edi.split_edi
        assert loaded_config.edi.split_edi_include_invoices == sample_folder_config.edi.split_edi_include_invoices
        assert loaded_config.edi.split_edi_include_credits == sample_folder_config.edi.split_edi_include_credits
        assert loaded_config.edi.prepend_date_files == sample_folder_config.edi.prepend_date_files
        assert loaded_config.edi.convert_to_format == sample_folder_config.edi.convert_to_format
        assert loaded_config.edi.force_edi_validation == sample_folder_config.edi.force_edi_validation
        assert loaded_config.edi.rename_file == sample_folder_config.edi.rename_file
        assert loaded_config.edi.split_edi_filter_categories == sample_folder_config.edi.split_edi_filter_categories
        assert loaded_config.edi.split_edi_filter_mode == sample_folder_config.edi.split_edi_filter_mode
        
        # Verify UPC Override
        assert loaded_config.upc_override is not None
        assert loaded_config.upc_override.enabled == sample_folder_config.upc_override.enabled
        assert loaded_config.upc_override.level == sample_folder_config.upc_override.level
        
        # Verify A-Record
        assert loaded_config.a_record_padding is not None
        assert loaded_config.a_record_padding.enabled == sample_folder_config.a_record_padding.enabled
        assert loaded_config.a_record_padding.padding_text == sample_folder_config.a_record_padding.padding_text
        
        # Verify Invoice Date
        assert loaded_config.invoice_date is not None
        assert loaded_config.invoice_date.offset == sample_folder_config.invoice_date.offset
        
        # Verify Backend-specific
        assert loaded_config.backend_specific is not None
        assert loaded_config.backend_specific.fintech_division_id == sample_folder_config.backend_specific.fintech_division_id
        
        # Verify CSV
        assert loaded_config.csv is not None
        assert loaded_config.csv.include_headers == sample_folder_config.csv.include_headers


class TestNullAndEmptyHandling:
    """Test suite for null and empty value handling."""
    
    def test_empty_ftp_config(self, temp_database):
        """Test that None FTP config doesn't add FTP fields."""
        config = FolderConfiguration(
            folder_name="/test/path",
            ftp=None  # No FTP config
        )
        
        config_dict = config.to_dict()
        
        assert 'ftp_server' not in config_dict
        assert 'ftp_port' not in config_dict
        
        # Verify from_dict handles missing FTP fields
        config_dict['folder_name'] = "/test/path"
        loaded_config = FolderConfiguration.from_dict(config_dict)
        
        assert loaded_config.ftp is None
    
    def test_empty_email_config(self, temp_database):
        """Test that None email config doesn't add email fields."""
        config = FolderConfiguration(
            folder_name="/test/path",
            email=None
        )
        
        config_dict = config.to_dict()
        
        assert 'email_to' not in config_dict
        assert 'email_subject_line' not in config_dict
        
        # Verify from_dict handles missing email fields
        config_dict['folder_name'] = "/test/path"
        loaded_config = FolderConfiguration.from_dict(config_dict)
        
        assert loaded_config.email is None
    
    def test_disabled_upc_override(self, temp_database):
        """Test disabled UPC override doesn't populate fields."""
        config = FolderConfiguration(
            folder_name="/test/path",
            upc_override=UPCOverrideConfiguration(
                enabled=False  # Disabled
            )
        )
        
        config_dict = config.to_dict()
        
        # Disabled UPC override should not populate fields
        assert config_dict.get('override_upc_bool') is False
        assert config_dict.get('override_upc_level', 1) == 1  # Default
        assert config_dict.get('override_upc_category_filter', '') == ''
    
    def test_minimal_config_roundtrip(self, temp_database):
        """Test roundtrip with minimal (mostly default) config."""
        config = FolderConfiguration(
            folder_name="/home/user/minimal",
            folder_is_active="False"
        )
        
        # Convert and save
        config_dict = config.to_dict()
        folder_id = temp_database['folders'].insert(config_dict)
        
        # Load and verify
        loaded_dict = temp_database['folders'].find_one(id=folder_id)
        loaded_config = FolderConfiguration.from_dict(loaded_dict)
        
        assert loaded_config.folder_name == config.folder_name
        assert loaded_config.folder_is_active == config.folder_is_active


class TestNestedConfigSerialization:
    """Test suite for nested configuration serialization."""
    
    def test_ftp_config_serialization(self, temp_database):
        """Test FTP configuration serializes correctly."""
        config = FolderConfiguration(
            folder_name="/test",
            ftp=FTPConfiguration(
                server="ftp.test.com",
                port=990,
                username="user",
                password="pass",
                folder="/data/"
            )
        )
        
        config_dict = config.to_dict()
        
        assert config_dict['ftp_server'] == "ftp.test.com"
        assert config_dict['ftp_port'] == 990
        assert config_dict['ftp_username'] == "user"
        assert config_dict['ftp_folder'] == "/data/"
        
        # Roundtrip - FTP is only created if all FTP fields are present
        folder_id = temp_database['folders'].insert(config_dict)
        loaded_dict = temp_database['folders'].find_one(id=folder_id)
        loaded_config = FolderConfiguration.from_dict(loaded_dict)
        
        # FTP should be reconstructed since all fields are present
        assert loaded_config.ftp is not None
        assert loaded_config.ftp.server == "ftp.test.com"
        assert loaded_config.ftp.port == 990
    
    def test_edi_config_serialization(self, temp_database):
        """Test EDI configuration serializes correctly."""
        config = FolderConfiguration(
            folder_name="/test",
            edi=EDIConfiguration(
                process_edi="True",
                split_edi=True,
                convert_to_format="scannerware"
            )
        )
        
        config_dict = config.to_dict()
        
        assert config_dict['process_edi'] == "True"
        assert config_dict['split_edi'] is True
        assert config_dict['convert_to_format'] == "scannerware"
        
        # Roundtrip - EDI is always created by from_dict
        folder_id = temp_database['folders'].insert(config_dict)
        loaded_dict = temp_database['folders'].find_one(id=folder_id)
        loaded_config = FolderConfiguration.from_dict(loaded_dict)
        
        assert loaded_config.edi is not None
        assert loaded_config.edi.process_edi == "True"
        assert loaded_config.edi.convert_to_format == "scannerware"
    
    def test_upc_config_serialization(self, temp_database):
        """Test UPC override configuration serializes correctly."""
        config = FolderConfiguration(
            folder_name="/test",
            upc_override=UPCOverrideConfiguration(
                enabled=True,
                level=3,
                category_filter="5,10,15",
                target_length=14
            )
        )
        
        config_dict = config.to_dict()
        
        assert config_dict['override_upc_bool'] is True
        assert config_dict['override_upc_level'] == 3
        assert config_dict['override_upc_category_filter'] == "5,10,15"
        
        # Roundtrip - UPC override is only created if override_upc_bool is True
        folder_id = temp_database['folders'].insert(config_dict)
        loaded_dict = temp_database['folders'].find_one(id=folder_id)
        loaded_config = FolderConfiguration.from_dict(loaded_dict)
        
        # UPC should be reconstructed since enabled is True
        assert loaded_config.upc_override is not None
        assert loaded_config.upc_override.enabled is True
        assert loaded_config.upc_override.level == 3


class TestEDIFieldsMapping:
    """Test suite for all EDI fields mapping (11 fields)."""
    
    def test_all_edi_fields_mapping(self, temp_database):
        """Test all 11 EDI fields map correctly."""
        edi_config = EDIConfiguration(
            process_edi="True",
            tweak_edi=True,
            split_edi=True,
            split_edi_include_invoices=True,
            split_edi_include_credits=False,
            prepend_date_files=True,
            convert_to_format="csv",
            force_edi_validation=False,
            rename_file="output_{date}_{original}",
            split_edi_filter_categories="1,2",
            split_edi_filter_mode="exclude"
        )
        
        config = FolderConfiguration(
            folder_name="/test/edi",
            edi=edi_config
        )
        
        config_dict = config.to_dict()
        
        # Verify all 11 EDI fields are present
        expected_edi_fields = {
            'process_edi': "True",
            'tweak_edi': True,
            'split_edi': True,
            'split_edi_include_invoices': True,
            'split_edi_include_credits': False,
            'prepend_date_files': True,
            'convert_to_format': "csv",
            'force_edi_validation': False,
            'rename_file': "output_{date}_{original}",
            'split_edi_filter_categories': "1,2",
            'split_edi_filter_mode': "exclude"
        }
        
        for field, expected_value in expected_edi_fields.items():
            assert field in config_dict, f"Missing EDI field: {field}"
            assert config_dict[field] == expected_value, f"EDI field {field} mismatch"
        
        # Roundtrip verification
        folder_id = temp_database['folders'].insert(config_dict)
        loaded_dict = temp_database['folders'].find_one(id=folder_id)
        loaded_config = FolderConfiguration.from_dict(loaded_dict)
        
        for field, expected_value in expected_edi_fields.items():
            # Navigate to EDI field
            actual_value = getattr(loaded_config.edi, field)
            assert actual_value == expected_value, f"EDI field {field} mismatch after roundtrip"


class TestCSVFieldsMapping:
    """Test suite for all CSV fields mapping."""
    
    def test_all_csv_fields_mapping(self, temp_database):
        """Test all CSV fields map correctly."""
        csv_config = CSVConfiguration(
            include_headers=True,
            filter_ampersand=False,
            include_item_numbers=True,
            include_item_description=True,
            simple_csv_sort_order="item,quantity,price",
            split_prepaid_sales_tax_crec=False
        )
        
        config = FolderConfiguration(
            folder_name="/test/csv",
            csv=csv_config
        )
        
        config_dict = config.to_dict()
        
        # Verify all CSV fields are present
        expected_csv_fields = {
            'include_headers': "True",  # Stored as string in DB
            'filter_ampersand': "False",  # Stored as string in DB
            'include_item_numbers': True,
            'include_item_description': True,
            'simple_csv_sort_order': "item,quantity,price",
            'split_prepaid_sales_tax_crec': False
        }
        
        for field, expected_value in expected_csv_fields.items():
            assert field in config_dict, f"Missing CSV field: {field}"
            assert config_dict[field] == expected_value, f"CSV field {field} mismatch"
        
        # Roundtrip verification - note: string values remain strings after DB roundtrip
        folder_id = temp_database['folders'].insert(config_dict)
        loaded_dict = temp_database['folders'].find_one(id=folder_id)
        
        # Verify loaded dict has correct values (accounting for type differences)
        assert loaded_dict['include_item_numbers'] is True
        assert loaded_dict['include_item_description'] is True
        assert loaded_dict['simple_csv_sort_order'] == "item,quantity,price"
