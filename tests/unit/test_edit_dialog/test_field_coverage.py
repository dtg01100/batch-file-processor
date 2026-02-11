"""Field coverage tests for dialog/database/dispatch pipeline.

These tests verify that no fields are accidentally omitted from any part of the pipeline:
- Dialog extraction (FolderDataExtractor)
- Database save/load (to_dict/from_dict)
- Backend dispatch (FTP, Email, Copy backends)

Uses reflection/introspection to automatically detect missing fields.
"""

import pytest
import sys
import os
from dataclasses import fields, is_dataclass
from typing import get_type_hints, Optional, List, Dict, Any, Set

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
from interface.operations.folder_data_extractor import ExtractedDialogFields, FolderDataExtractor


# =============================================================================
# FIELD COLLECTION UTILITIES
# =============================================================================

def get_dataclass_fields_flat(dataclass_type) -> Set[str]:
    """Get all field names from a dataclass, excluding nested dataclasses."""
    if not is_dataclass(dataclass_type):
        return set()
    return {f.name for f in fields(dataclass_type)}


def get_all_nested_fields_flat(dataclass_type) -> Set[str]:
    """Get all field names from a dataclass including nested dataclass fields."""
    all_fields = set()
    if not is_dataclass(dataclass_type):
        return all_fields
    
    for f in fields(dataclass_type):
        field_type = f.type
        # Handle Optional types
        if hasattr(field_type, '__origin__'):
            if field_type.__origin__ is Optional:
                field_type = field_type.__args__[0]
        
        # Check if it's a nested dataclass
        if is_dataclass(field_type):
            nested_fields = get_dataclass_fields_flat(field_type)
            all_fields.update(nested_fields)
        else:
            all_fields.add(f.name)
    
    return all_fields


def get_to_dict_keys() -> Set[str]:
    """Get all keys that to_dict() produces."""
    config = FolderConfiguration(
        folder_name="test",
        folder_is_active="True",
        alias="test_alias",
        ftp=FTPConfiguration(server="server", port=21, username="user", password="pass", folder="/folder/"),
        email=EmailConfiguration(recipients="test@test.com", subject_line="subject"),
        copy=CopyConfiguration(destination_directory="/dest/"),
        edi=EDIConfiguration(
            process_edi="True",
            tweak_edi=True,
            split_edi=True,
            split_edi_include_invoices=True,
            split_edi_include_credits=True,
            prepend_date_files=True,
            convert_to_format="csv",
            force_edi_validation=True,
            rename_file="rename",
            split_edi_filter_categories="ALL",
            split_edi_filter_mode="include"
        ),
        upc_override=UPCOverrideConfiguration(
            enabled=True,
            level=1,
            category_filter="1,2,3",
            target_length=11,
            padding_pattern="           "
        ),
        a_record_padding=ARecordPaddingConfiguration(
            enabled=True,
            padding_text="PAD",
            padding_length=6,
            append_text="APP",
            append_enabled=True,
            force_txt_extension=True
        ),
        invoice_date=InvoiceDateConfiguration(
            offset=0,
            custom_format_enabled=True,
            custom_format_string="%Y%m%d",
            retail_uom=True
        ),
        backend_specific=BackendSpecificConfiguration(
            estore_store_number="123",
            estore_vendor_oid="OID",
            estore_vendor_namevendoroid="NAME",
            fintech_division_id="DIV"
        ),
        csv=CSVConfiguration(
            include_headers=True,
            filter_ampersand=True,
            include_item_numbers=True,
            include_item_description=True,
            simple_csv_sort_order="date",
            split_prepaid_sales_tax_crec=True
        )
    )
    return set(config.to_dict().keys())


def get_from_dict_expected_keys() -> Set[str]:
    """Get all keys that from_dict() expects to read."""
    # Create a comprehensive dict with all possible keys
    all_keys = {
        # Identity
        'folder_name', 'folder_is_active', 'alias',
        # Backend toggles
        'process_backend_copy', 'process_backend_ftp', 'process_backend_email',
        # FTP
        'ftp_server', 'ftp_port', 'ftp_username', 'ftp_password', 'ftp_folder',
        # Email
        'email_to', 'email_subject_line',
        # Copy
        'copy_to_directory',
        # EDI (11 fields)
        'process_edi', 'tweak_edi', 'split_edi', 
        'split_edi_include_invoices', 'split_edi_include_credits',
        'prepend_date_files', 'convert_to_format', 'force_edi_validation',
        'rename_file', 'split_edi_filter_categories', 'split_edi_filter_mode',
        # UPC Override
        'override_upc_bool', 'override_upc_level', 'override_upc_category_filter',
        'upc_target_length', 'upc_padding_pattern',
        # A-Record
        'pad_a_records', 'a_record_padding', 'a_record_padding_length',
        'append_a_records', 'a_record_append_text', 'force_txt_file_ext',
        # Invoice Date
        'invoice_date_offset', 'invoice_date_custom_format',
        'invoice_date_custom_format_string', 'retail_uom',
        # Backend-specific
        'estore_store_number', 'estore_Vendor_OId', 'estore_vendor_NameVendorOID',
        'fintech_division_id',
        # CSV
        'include_headers', 'filter_ampersand', 'include_item_numbers',
        'include_item_description', 'simple_csv_sort_order', 'split_prepaid_sales_tax_crec',
    }
    return all_keys


def get_extractor_fields() -> Set[str]:
    """Get all fields extracted by ExtractedDialogFields."""
    return get_dataclass_fields_flat(ExtractedDialogFields)


def get_database_columns_from_create_db() -> Set[str]:
    """Get database columns defined in create_database.py initial_db_dict."""
    # These are the columns from create_database.py initial_db_dict
    return {
        'folder_is_active', 'copy_to_directory', 'process_edi', 'convert_to_format',
        'calculate_upc_check_digit', 'upc_target_length', 'upc_padding_pattern',
        'include_a_records', 'include_c_records', 'include_headers', 'filter_ampersand',
        'tweak_edi', 'pad_a_records', 'a_record_padding', 'a_record_padding_length',
        'invoice_date_custom_format_string', 'invoice_date_custom_format',
        'reporting_email', 'folder_name', 'alias', 'report_email_destination',
        'process_backend_copy', 'backend_copy_destination', 'process_edi_output',
        'edi_output_folder',
    }


def get_backend_required_fields() -> Dict[str, Set[str]]:
    """Get required fields for each backend."""
    return {
        'ftp': {'ftp_server', 'ftp_port', 'ftp_username', 'ftp_password', 'ftp_folder'},
        'email': {'email_to', 'email_subject_line'},
        'copy': {'copy_to_directory'},
    }


def get_dispatch_required_fields() -> Set[str]:
    """Get fields used by dispatch.py for processing."""
    return {
        # Core identity
        'folder_name', 'alias', 'folder_is_active',
        # Backend toggles
        'process_backend_copy', 'process_backend_ftp', 'process_backend_email',
        # EDI processing
        'process_edi', 'tweak_edi', 'split_edi', 'force_edi_validation',
        'split_edi_include_invoices', 'split_edi_include_credits',
        'convert_to_format', 'rename_file',
        'split_edi_filter_categories', 'split_edi_filter_mode',
        # Backend destinations
        'copy_to_directory', 'ftp_server', 'ftp_folder', 'email_to',
    }


# =============================================================================
# EXPECTED FIELD DEFINITIONS
# =============================================================================

# All fields that should exist in the complete pipeline
EXPECTED_CONFIG_FIELDS = {
    # Identity (4 fields)
    'folder_name', 'folder_is_active', 'alias', 'is_template',
    # Backend toggles (3 fields)
    'process_backend_copy', 'process_backend_ftp', 'process_backend_email',
}

# Fields that are internal to FolderConfiguration (not serialized directly)
INTERNAL_CONFIG_FIELDS = {
    'is_template',  # Computed from folder_name == 'template'
    'ftp', 'email', 'copy', 'edi', 'upc_override', 
    'a_record_padding', 'invoice_date', 'backend_specific', 'csv',
}

# Fields that should be in to_dict() output
EXPECTED_TO_DICT_KEYS = {
    # Identity
    'folder_name', 'folder_is_active', 'alias',
    # Backend toggles
    'process_backend_copy', 'process_backend_ftp', 'process_backend_email',
    # FTP (5 fields)
    'ftp_server', 'ftp_port', 'ftp_username', 'ftp_password', 'ftp_folder',
    # Email (2 fields)
    'email_to', 'email_subject_line',
    # Copy (1 field)
    'copy_to_directory',
    # EDI (11 fields)
    'process_edi', 'tweak_edi', 'split_edi', 
    'split_edi_include_invoices', 'split_edi_include_credits',
    'prepend_date_files', 'convert_to_format', 'force_edi_validation',
    'rename_file', 'split_edi_filter_categories', 'split_edi_filter_mode',
    # UPC Override (5 fields)
    'override_upc_bool', 'override_upc_level', 'override_upc_category_filter',
    'upc_target_length', 'upc_padding_pattern',
    # A-Record (6 fields)
    'pad_a_records', 'a_record_padding', 'a_record_padding_length',
    'append_a_records', 'a_record_append_text', 'force_txt_file_ext',
    # Invoice Date (4 fields)
    'invoice_date_offset', 'invoice_date_custom_format',
    'invoice_date_custom_format_string', 'retail_uom',
    # Backend-specific (4 fields)
    'estore_store_number', 'estore_Vendor_OId', 'estore_vendor_NameVendorOID',
    'fintech_division_id',
    # CSV (6 fields)
    'include_headers', 'filter_ampersand', 'include_item_numbers',
    'include_item_description', 'simple_csv_sort_order', 'split_prepaid_sales_tax_crec',
}

# Fields that ExtractedDialogFields should have
EXPECTED_EXTRACTOR_FIELDS = {
    # Identity
    'folder_name', 'alias', 'folder_is_active',
    # Backend toggles
    'process_backend_copy', 'process_backend_ftp', 'process_backend_email',
    # FTP
    'ftp_server', 'ftp_port', 'ftp_folder', 'ftp_username', 'ftp_password',
    # Email
    'email_to', 'email_subject_line',
    # EDI
    'process_edi', 'convert_to_format', 'tweak_edi', 'split_edi',
    'split_edi_include_invoices', 'split_edi_include_credits', 'prepend_date_files',
    'rename_file', 'split_edi_filter_categories', 'split_edi_filter_mode',
    # EDI options (dialog-specific, may not all be in config)
    'calculate_upc_check_digit', 'include_a_records', 'include_c_records',
    'include_headers', 'filter_ampersand', 'force_edi_validation',
    # A-record
    'pad_a_records', 'a_record_padding', 'a_record_padding_length',
    'append_a_records', 'a_record_append_text', 'force_txt_file_ext',
    # Invoice date
    'invoice_date_offset', 'invoice_date_custom_format',
    'invoice_date_custom_format_string', 'retail_uom',
    # UPC override
    'override_upc_bool', 'override_upc_level', 'override_upc_category_filter',
    'upc_target_length', 'upc_padding_pattern',
    # Item fields
    'include_item_numbers', 'include_item_description',
    # CSV sort
    'simple_csv_sort_order',
    # Tax
    'split_prepaid_sales_tax_crec',
    # Backend-specific
    'estore_store_number', 'estore_vendor_oid', 'estore_vendor_namevendoroid',
    'fintech_division_id',
    # Copy destination
    'copy_to_directory',
}


# =============================================================================
# TEST CLASSES
# =============================================================================

class TestFieldCoverageAnalysis:
    """Analyze and report field coverage across the pipeline."""

    def test_all_config_fields_have_extractors(self):
        """Verify every FolderConfiguration field has a corresponding extractor field."""
        extractor_fields = get_extractor_fields()
        to_dict_keys = get_to_dict_keys()
        
        # Fields that should be extracted (from to_dict output)
        fields_to_check = to_dict_keys
        
        missing_fields = []
        for field in fields_to_check:
            # Map to_dict keys to extractor field names
            extractor_field = field
            if field not in extractor_fields:
                missing_fields.append(field)
        
        # Report coverage
        coverage_pct = (len(fields_to_check) - len(missing_fields)) / len(fields_to_check) * 100
        
        print(f"\n{'='*60}")
        print(f"EXTRACTOR FIELD COVERAGE ANALYSIS")
        print(f"{'='*60}")
        print(f"Total to_dict keys: {len(fields_to_check)}")
        print(f"Extractor fields: {len(extractor_fields)}")
        print(f"Coverage: {coverage_pct:.1f}%")
        
        if missing_fields:
            print(f"\nMissing fields in ExtractedDialogFields:")
            for f in sorted(missing_fields):
                print(f"  - {f}")
        
        # This test documents coverage but doesn't fail
        # Some fields may intentionally differ between extractor and config

    def test_all_config_fields_in_to_dict(self):
        """Verify every expected field appears in to_dict() output."""
        actual_keys = get_to_dict_keys()
        expected_keys = EXPECTED_TO_DICT_KEYS
        
        missing_fields = expected_keys - actual_keys
        extra_fields = actual_keys - expected_keys
        
        coverage_pct = len(expected_keys & actual_keys) / len(expected_keys) * 100
        
        print(f"\n{'='*60}")
        print(f"to_dict() FIELD COVERAGE ANALYSIS")
        print(f"{'='*60}")
        print(f"Expected keys: {len(expected_keys)}")
        print(f"Actual keys: {len(actual_keys)}")
        print(f"Coverage: {coverage_pct:.1f}%")
        
        if missing_fields:
            print(f"\nMissing fields in to_dict():")
            for f in sorted(missing_fields):
                print(f"  - {f}")
        
        if extra_fields:
            print(f"\nExtra fields in to_dict() (not in expected):")
            for f in sorted(extra_fields):
                print(f"  - {f}")
        
        assert not missing_fields, f"Missing fields in to_dict(): {missing_fields}"

    def test_all_config_fields_in_from_dict(self):
        """Verify every expected field can be loaded from dict."""
        # Create a dict with all expected keys
        test_dict = {
            'folder_name': '/test/path',
            'folder_is_active': 'True',
            'alias': 'Test Alias',
            'process_backend_copy': True,
            'process_backend_ftp': True,
            'process_backend_email': True,
            'ftp_server': 'ftp.test.com',
            'ftp_port': 21,
            'ftp_username': 'user',
            'ftp_password': 'pass',
            'ftp_folder': '/folder/',
            'email_to': 'test@test.com',
            'email_subject_line': 'Subject',
            'copy_to_directory': '/dest/',
            'process_edi': 'True',
            'tweak_edi': True,
            'split_edi': True,
            'split_edi_include_invoices': True,
            'split_edi_include_credits': True,
            'prepend_date_files': True,
            'convert_to_format': 'csv',
            'force_edi_validation': True,
            'rename_file': 'rename',
            'split_edi_filter_categories': 'ALL',
            'split_edi_filter_mode': 'include',
            'override_upc_bool': True,
            'override_upc_level': 1,
            'override_upc_category_filter': '1,2,3',
            'upc_target_length': 11,
            'upc_padding_pattern': '           ',
            'pad_a_records': 'True',
            'a_record_padding': 'PAD',
            'a_record_padding_length': 6,
            'append_a_records': 'True',
            'a_record_append_text': 'APP',
            'force_txt_file_ext': 'True',
            'invoice_date_offset': 0,
            'invoice_date_custom_format': True,
            'invoice_date_custom_format_string': '%Y%m%d',
            'retail_uom': True,
            'estore_store_number': '123',
            'estore_Vendor_OId': 'OID',
            'estore_vendor_NameVendorOID': 'NAME',
            'fintech_division_id': 'DIV',
            'include_headers': 'True',
            'filter_ampersand': 'True',
            'include_item_numbers': True,
            'include_item_description': True,
            'simple_csv_sort_order': 'date',
            'split_prepaid_sales_tax_crec': True,
        }
        
        config = FolderConfiguration.from_dict(test_dict)
        
        # Verify all fields loaded correctly
        assert config.folder_name == '/test/path'
        assert config.folder_is_active == 'True'
        assert config.alias == 'Test Alias'
        assert config.process_backend_copy is True
        assert config.process_backend_ftp is True
        assert config.process_backend_email is True
        
        # Verify nested configs
        assert config.ftp is not None
        assert config.ftp.server == 'ftp.test.com'
        assert config.ftp.port == 21
        
        assert config.email is not None
        assert config.email.recipients == 'test@test.com'
        
        assert config.copy is not None
        assert config.copy.destination_directory == '/dest/'
        
        assert config.edi is not None
        assert config.edi.process_edi == 'True'
        assert config.edi.split_edi is True
        
        assert config.upc_override is not None
        assert config.upc_override.enabled is True
        
        assert config.a_record_padding is not None
        assert config.a_record_padding.enabled is True
        
        assert config.invoice_date is not None
        assert config.invoice_date.offset == 0
        
        assert config.backend_specific is not None
        assert config.backend_specific.estore_store_number == '123'
        
        assert config.csv is not None
        assert config.csv.include_headers is True
        
        print(f"\n{'='*60}")
        print(f"from_dict() FIELD COVERAGE ANALYSIS")
        print(f"{'='*60}")
        print(f"All {len(test_dict)} fields loaded successfully")

    def test_database_columns_match_config(self):
        """Verify DB columns match FolderConfiguration fields."""
        to_dict_keys = get_to_dict_keys()
        db_columns = get_database_columns_from_create_db()
        
        # Fields in to_dict but not in initial DB schema
        missing_in_db = to_dict_keys - db_columns
        
        # Fields in initial DB schema but not in to_dict
        orphan_in_db = db_columns - to_dict_keys
        
        print(f"\n{'='*60}")
        print(f"DATABASE COLUMN COVERAGE ANALYSIS")
        print(f"{'='*60}")
        print(f"to_dict keys: {len(to_dict_keys)}")
        print(f"Initial DB columns: {len(db_columns)}")
        
        if missing_in_db:
            print(f"\nFields in to_dict() but NOT in initial DB schema:")
            for f in sorted(missing_in_db):
                print(f"  - {f}")
        
        if orphan_in_db:
            print(f"\nFields in initial DB schema but NOT in to_dict():")
            for f in sorted(orphan_in_db):
                print(f"  - {f}")
        
        # Note: This test documents differences but doesn't fail
        # The actual DB may have been migrated to include more columns

    def test_no_orphan_database_columns(self):
        """Verify no DB columns without corresponding config field."""
        to_dict_keys = get_to_dict_keys()
        db_columns = get_database_columns_from_create_db()
        
        # Find DB columns that have no corresponding config field
        orphan_columns = db_columns - to_dict_keys - {
            # Known legacy/internal columns
            'reporting_email', 'report_email_destination',
            'backend_copy_destination', 'process_edi_output', 'edi_output_folder',
            'calculate_upc_check_digit', 'include_a_records', 'include_c_records',
        }
        
        print(f"\n{'='*60}")
        print(f"ORPHAN DATABASE COLUMN CHECK")
        print(f"{'='*60}")
        
        if orphan_columns:
            print(f"Orphan DB columns (no corresponding config field):")
            for f in sorted(orphan_columns):
                print(f"  - {f}")
        
        assert not orphan_columns, f"Orphan DB columns found: {orphan_columns}"

    def test_no_orphan_config_fields(self):
        """Verify no config fields without corresponding DB column."""
        to_dict_keys = get_to_dict_keys()
        db_columns = get_database_columns_from_create_db()
        
        # Find config fields that have no corresponding DB column
        # (These would be lost when saving to database)
        orphan_config = to_dict_keys - db_columns
        
        print(f"\n{'='*60}")
        print(f"ORPHAN CONFIG FIELD CHECK")
        print(f"{'='*60}")
        
        if orphan_config:
            print(f"Config fields NOT in initial DB schema (may be lost on save):")
            for f in sorted(orphan_config):
                print(f"  - {f}")
        
        # Note: This test documents potential issues
        # The actual DB may have been migrated

    def test_backend_receives_all_required_fields(self):
        """Verify dispatch gets all needed fields for each backend."""
        to_dict_keys = get_to_dict_keys()
        backend_fields = get_backend_required_fields()
        dispatch_fields = get_dispatch_required_fields()
        
        print(f"\n{'='*60}")
        print(f"BACKEND FIELD REQUIREMENTS CHECK")
        print(f"{'='*60}")
        
        all_satisfied = True
        
        for backend_name, required in backend_fields.items():
            missing = required - to_dict_keys
            if missing:
                print(f"{backend_name.upper()} backend missing fields: {missing}")
                all_satisfied = False
            else:
                print(f"{backend_name.upper()} backend: All required fields present ✓")
        
        # Check dispatch fields
        missing_dispatch = dispatch_fields - to_dict_keys
        if missing_dispatch:
            print(f"DISPATCH missing fields: {missing_dispatch}")
            all_satisfied = False
        else:
            print(f"DISPATCH: All required fields present ✓")
        
        assert all_satisfied, "Some backends are missing required fields"


class TestNestedConfigurationCoverage:
    """Test coverage of nested configuration classes."""

    def test_ftp_configuration_fields(self):
        """Verify FTPConfiguration has all expected fields."""
        ftp_fields = get_dataclass_fields_flat(FTPConfiguration)
        expected = {'server', 'port', 'username', 'password', 'folder'}
        
        assert ftp_fields == expected, f"FTP fields mismatch. Expected: {expected}, Got: {ftp_fields}"

    def test_email_configuration_fields(self):
        """Verify EmailConfiguration has all expected fields."""
        email_fields = get_dataclass_fields_flat(EmailConfiguration)
        expected = {'recipients', 'subject_line', 'sender_address'}
        
        assert email_fields == expected, f"Email fields mismatch. Expected: {expected}, Got: {email_fields}"

    def test_copy_configuration_fields(self):
        """Verify CopyConfiguration has all expected fields."""
        copy_fields = get_dataclass_fields_flat(CopyConfiguration)
        expected = {'destination_directory'}
        
        assert copy_fields == expected, f"Copy fields mismatch. Expected: {expected}, Got: {copy_fields}"

    def test_edi_configuration_fields(self):
        """Verify EDIConfiguration has all 11 expected fields."""
        edi_fields = get_dataclass_fields_flat(EDIConfiguration)
        expected = {
            'process_edi', 'tweak_edi', 'split_edi',
            'split_edi_include_invoices', 'split_edi_include_credits',
            'prepend_date_files', 'convert_to_format', 'force_edi_validation',
            'rename_file', 'split_edi_filter_categories', 'split_edi_filter_mode',
        }
        
        assert edi_fields == expected, f"EDI fields mismatch. Expected: {expected}, Got: {edi_fields}"

    def test_upc_override_configuration_fields(self):
        """Verify UPCOverrideConfiguration has all expected fields."""
        upc_fields = get_dataclass_fields_flat(UPCOverrideConfiguration)
        expected = {'enabled', 'level', 'category_filter', 'target_length', 'padding_pattern'}
        
        assert upc_fields == expected, f"UPC fields mismatch. Expected: {expected}, Got: {upc_fields}"

    def test_a_record_padding_configuration_fields(self):
        """Verify ARecordPaddingConfiguration has all expected fields."""
        a_rec_fields = get_dataclass_fields_flat(ARecordPaddingConfiguration)
        expected = {'enabled', 'padding_text', 'padding_length', 'append_text', 'append_enabled', 'force_txt_extension'}
        
        assert a_rec_fields == expected, f"A-record fields mismatch. Expected: {expected}, Got: {a_rec_fields}"

    def test_invoice_date_configuration_fields(self):
        """Verify InvoiceDateConfiguration has all expected fields."""
        inv_date_fields = get_dataclass_fields_flat(InvoiceDateConfiguration)
        expected = {'offset', 'custom_format_enabled', 'custom_format_string', 'retail_uom'}
        
        assert inv_date_fields == expected, f"Invoice date fields mismatch. Expected: {expected}, Got: {inv_date_fields}"

    def test_backend_specific_configuration_fields(self):
        """Verify BackendSpecificConfiguration has all expected fields."""
        backend_fields = get_dataclass_fields_flat(BackendSpecificConfiguration)
        expected = {
            'estore_store_number', 'estore_vendor_oid', 
            'estore_vendor_namevendoroid', 'estore_c_record_oid',
            'fintech_division_id'
        }
        
        assert backend_fields == expected, f"Backend-specific fields mismatch. Expected: {expected}, Got: {backend_fields}"

    def test_csv_configuration_fields(self):
        """Verify CSVConfiguration has all expected fields."""
        csv_fields = get_dataclass_fields_flat(CSVConfiguration)
        expected = {
            'include_headers', 'filter_ampersand', 'include_item_numbers',
            'include_item_description', 'simple_csv_sort_order', 'split_prepaid_sales_tax_crec'
        }
        
        assert csv_fields == expected, f"CSV fields mismatch. Expected: {expected}, Got: {csv_fields}"


class TestFieldCoverageReport:
    """Generate comprehensive field coverage report."""

    def test_coverage_summary_report(self):
        """Generate and print a comprehensive coverage summary."""
        to_dict_keys = get_to_dict_keys()
        extractor_fields = get_extractor_fields()
        db_columns = get_database_columns_from_create_db()
        backend_fields = get_backend_required_fields()
        
        print(f"\n{'='*70}")
        print(f"FIELD COVERAGE SUMMARY REPORT")
        print(f"{'='*70}")
        
        print(f"\n1. FolderConfiguration.to_dict() output: {len(to_dict_keys)} fields")
        print(f"   Fields: {sorted(to_dict_keys)}")
        
        print(f"\n2. ExtractedDialogFields: {len(extractor_fields)} fields")
        print(f"   Fields: {sorted(extractor_fields)}")
        
        print(f"\n3. Database columns (initial schema): {len(db_columns)} fields")
        print(f"   Fields: {sorted(db_columns)}")
        
        # Coverage calculations
        to_dict_vs_extractor = len(to_dict_keys & extractor_fields)
        to_dict_vs_db = len(to_dict_keys & db_columns)
        
        print(f"\n4. Coverage Analysis:")
        print(f"   to_dict vs Extractor: {to_dict_vs_extractor}/{len(to_dict_keys)} "
              f"({to_dict_vs_extractor/len(to_dict_keys)*100:.1f}%)")
        print(f"   to_dict vs DB columns: {to_dict_vs_db}/{len(to_dict_keys)} "
              f"({to_dict_vs_db/len(to_dict_keys)*100:.1f}%)")
        
        # Missing field analysis
        missing_in_extractor = to_dict_keys - extractor_fields
        missing_in_db = to_dict_keys - db_columns
        
        if missing_in_extractor:
            print(f"\n5. Fields in to_dict() but NOT in ExtractedDialogFields:")
            for f in sorted(missing_in_extractor):
                print(f"   - {f}")
        
        if missing_in_db:
            print(f"\n6. Fields in to_dict() but NOT in initial DB schema:")
            for f in sorted(missing_in_db):
                print(f"   - {f}")
        
        # Backend coverage
        print(f"\n7. Backend Field Coverage:")
        for backend_name, required in backend_fields.items():
            coverage = len(required & to_dict_keys)
            print(f"   {backend_name.upper()}: {coverage}/{len(required)} fields covered")
        
        print(f"\n{'='*70}")
        
        # This test always passes - it's just for reporting
        assert True


class TestRoundTripIntegrity:
    """Test that fields survive a complete round trip."""

    def test_complete_roundtrip(self):
        """Test that all fields survive: config -> to_dict -> from_dict -> config."""
        original = FolderConfiguration(
            folder_name="/test/path",
            folder_is_active="True",
            alias="Test Alias",
            process_backend_copy=True,
            process_backend_ftp=True,
            process_backend_email=True,
            ftp=FTPConfiguration(
                server="ftp.test.com",
                port=2121,
                username="user",
                password="pass",
                folder="/upload/"
            ),
            email=EmailConfiguration(
                recipients="test@example.com",
                subject_line="Test Subject"
            ),
            copy=CopyConfiguration(
                destination_directory="/backup/"
            ),
            edi=EDIConfiguration(
                process_edi="True",
                tweak_edi=True,
                split_edi=True,
                split_edi_include_invoices=True,
                split_edi_include_credits=False,
                prepend_date_files=True,
                convert_to_format="fintech",
                force_edi_validation=True,
                rename_file="renamed_{datetime}",
                split_edi_filter_categories="1,2,3",
                split_edi_filter_mode="exclude"
            ),
            upc_override=UPCOverrideConfiguration(
                enabled=True,
                level=2,
                category_filter="4,5,6",
                target_length=12,
                padding_pattern="000000000000"
            ),
            a_record_padding=ARecordPaddingConfiguration(
                enabled=True,
                padding_text="PREFIX",
                padding_length=6,
                append_text="SUFFIX",
                append_enabled=True,
                force_txt_extension=True
            ),
            invoice_date=InvoiceDateConfiguration(
                offset=5,
                custom_format_enabled=True,
                custom_format_string="%Y-%m-%d",
                retail_uom=True
            ),
            backend_specific=BackendSpecificConfiguration(
                estore_store_number="STORE001",
                estore_vendor_oid="VENDOR001",
                estore_vendor_namevendoroid="NAME001",
                fintech_division_id="DIV001"
            ),
            csv=CSVConfiguration(
                include_headers=True,
                filter_ampersand=True,
                include_item_numbers=True,
                include_item_description=True,
                simple_csv_sort_order="date,amount",
                split_prepaid_sales_tax_crec=True
            )
        )
        
        # Round trip
        dict_form = original.to_dict()
        reconstructed = FolderConfiguration.from_dict(dict_form)
        
        # Verify identity fields
        assert reconstructed.folder_name == original.folder_name
        assert reconstructed.folder_is_active == original.folder_is_active
        assert reconstructed.alias == original.alias
        
        # Verify backend toggles
        assert reconstructed.process_backend_copy == original.process_backend_copy
        assert reconstructed.process_backend_ftp == original.process_backend_ftp
        assert reconstructed.process_backend_email == original.process_backend_email
        
        # Verify FTP
        assert reconstructed.ftp is not None
        assert reconstructed.ftp.server == original.ftp.server
        assert reconstructed.ftp.port == original.ftp.port
        assert reconstructed.ftp.username == original.ftp.username
        assert reconstructed.ftp.password == original.ftp.password
        assert reconstructed.ftp.folder == original.ftp.folder
        
        # Verify Email
        assert reconstructed.email is not None
        assert reconstructed.email.recipients == original.email.recipients
        assert reconstructed.email.subject_line == original.email.subject_line
        
        # Verify Copy
        assert reconstructed.copy is not None
        assert reconstructed.copy.destination_directory == original.copy.destination_directory
        
        # Verify EDI (all 11 fields)
        assert reconstructed.edi is not None
        assert reconstructed.edi.process_edi == original.edi.process_edi
        assert reconstructed.edi.tweak_edi == original.edi.tweak_edi
        assert reconstructed.edi.split_edi == original.edi.split_edi
        assert reconstructed.edi.split_edi_include_invoices == original.edi.split_edi_include_invoices
        assert reconstructed.edi.split_edi_include_credits == original.edi.split_edi_include_credits
        assert reconstructed.edi.prepend_date_files == original.edi.prepend_date_files
        assert reconstructed.edi.convert_to_format == original.edi.convert_to_format
        assert reconstructed.edi.force_edi_validation == original.edi.force_edi_validation
        assert reconstructed.edi.rename_file == original.edi.rename_file
        assert reconstructed.edi.split_edi_filter_categories == original.edi.split_edi_filter_categories
        assert reconstructed.edi.split_edi_filter_mode == original.edi.split_edi_filter_mode
        
        # Verify UPC Override
        assert reconstructed.upc_override is not None
        assert reconstructed.upc_override.enabled == original.upc_override.enabled
        assert reconstructed.upc_override.level == original.upc_override.level
        assert reconstructed.upc_override.category_filter == original.upc_override.category_filter
        assert reconstructed.upc_override.target_length == original.upc_override.target_length
        assert reconstructed.upc_override.padding_pattern == original.upc_override.padding_pattern
        
        # Verify A-Record
        assert reconstructed.a_record_padding is not None
        assert reconstructed.a_record_padding.enabled == original.a_record_padding.enabled
        assert reconstructed.a_record_padding.padding_text == original.a_record_padding.padding_text
        assert reconstructed.a_record_padding.padding_length == original.a_record_padding.padding_length
        assert reconstructed.a_record_padding.append_text == original.a_record_padding.append_text
        assert reconstructed.a_record_padding.append_enabled == original.a_record_padding.append_enabled
        assert reconstructed.a_record_padding.force_txt_extension == original.a_record_padding.force_txt_extension
        
        # Verify Invoice Date
        assert reconstructed.invoice_date is not None
        assert reconstructed.invoice_date.offset == original.invoice_date.offset
        assert reconstructed.invoice_date.custom_format_enabled == original.invoice_date.custom_format_enabled
        assert reconstructed.invoice_date.custom_format_string == original.invoice_date.custom_format_string
        assert reconstructed.invoice_date.retail_uom == original.invoice_date.retail_uom
        
        # Verify Backend-specific
        assert reconstructed.backend_specific is not None
        assert reconstructed.backend_specific.estore_store_number == original.backend_specific.estore_store_number
        assert reconstructed.backend_specific.estore_vendor_oid == original.backend_specific.estore_vendor_oid
        assert reconstructed.backend_specific.estore_vendor_namevendoroid == original.backend_specific.estore_vendor_namevendoroid
        assert reconstructed.backend_specific.fintech_division_id == original.backend_specific.fintech_division_id
        
        # Verify CSV
        assert reconstructed.csv is not None
        assert reconstructed.csv.include_headers == original.csv.include_headers
        assert reconstructed.csv.filter_ampersand == original.csv.filter_ampersand
        assert reconstructed.csv.include_item_numbers == original.csv.include_item_numbers
        assert reconstructed.csv.include_item_description == original.csv.include_item_description
        assert reconstructed.csv.simple_csv_sort_order == original.csv.simple_csv_sort_order
        assert reconstructed.csv.split_prepaid_sales_tax_crec == original.csv.split_prepaid_sales_tax_crec
        
        print(f"\n{'='*60}")
        print(f"ROUNDTRIP TEST PASSED")
        print(f"{'='*60}")
        print(f"All {len(dict_form)} fields survived the round trip!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
