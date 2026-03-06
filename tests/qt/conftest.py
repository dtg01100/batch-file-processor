"""Shared fixtures for Qt UI tests.

pytest-qt is used for Qt widget testing. It automatically provides the
``qtbot`` fixture and manages the ``QApplication`` lifecycle.

Configuration in pytest.ini:
    qt_api = pyqt6
"""
import os
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from tests.fakes import (
    FakeDatabaseObj,
    FakeUIService,
    FakeProgressService,
    FakeMaintenanceFunctions,
    FakeResendService,
    FakeTable,
)


@pytest.fixture
def mock_database_obj():
    """Create a fake DatabaseObj with all required table attributes."""
    return FakeDatabaseObj()


@pytest.fixture
def fake_database_obj():
    """Create a fake DatabaseObj with a more descriptive name."""
    return FakeDatabaseObj()


@pytest.fixture
def mock_ui_service():
    """Create a fake UI service."""
    return FakeUIService()


@pytest.fixture
def mock_progress_service():
    """Create a fake progress service."""
    return FakeProgressService()


@pytest.fixture
def sample_folder_config():
    """Create a sample folder configuration dict."""
    return {
        "id": 1,
        "folder_name": "/path/to/folder",
        "alias": "Test Folder",
        "folder_is_active": "True",
        "process_backend_copy": False,
        "process_backend_ftp": False,
        "process_backend_email": False,
        "copy_to_directory": "",
        "ftp_server": "",
        "ftp_port": 21,
        "ftp_folder": "",
        "ftp_username": "",
        "ftp_password": "",
        "email_to": "",
        "email_subject_line": "",
        "process_edi": "False",
        "convert_to_format": "csv",
        "tweak_edi": False,
        "split_edi": False,
        "split_edi_include_invoices": False,
        "split_edi_include_credits": False,
        "prepend_date_files": False,
        "rename_file": "",
        "split_edi_filter_categories": "ALL",
        "split_edi_filter_mode": "include",
        "calculate_upc_check_digit": "False",
        "include_a_records": "False",
        "include_c_records": "False",
        "include_headers": "False",
        "filter_ampersand": "False",
        "force_edi_validation": False,
        "pad_a_records": "False",
        "a_record_padding": "",
        "a_record_padding_length": 6,
        "append_a_records": "False",
        "a_record_append_text": "",
        "force_txt_file_ext": "False",
        "invoice_date_offset": 0,
        "invoice_date_custom_format": False,
        "invoice_date_custom_format_string": "",
        "retail_uom": False,
        "override_upc_bool": False,
        "override_upc_level": 1,
        "override_upc_category_filter": "",
        "upc_target_length": 11,
        "upc_padding_pattern": "           ",
        "include_item_numbers": False,
        "include_item_description": False,
        "simple_csv_sort_order": "",
        "split_prepaid_sales_tax_crec": False,
        "estore_store_number": "",
        "estore_Vendor_OId": "",
        "estore_vendor_NameVendorOID": "",
        "estore_c_record_OID": "",
        "fintech_division_id": "",
    }


@pytest.fixture
def mock_folders_table():
    """Create a fake folders table for FolderListWidget tests."""
    return FakeTable()


@pytest.fixture
def mock_resend_service():
    """Create a fake ResendService."""
    return FakeResendService()


@pytest.fixture
def mock_maintenance_functions():
    """Create a fake MaintenanceFunctions."""
    return FakeMaintenanceFunctions()
