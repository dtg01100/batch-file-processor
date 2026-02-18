"""Shared fixtures for Qt UI tests.

pytest-qt is used for Qt widget testing. It automatically provides the
``qtbot`` fixture and manages the ``QApplication`` lifecycle.

Configuration in pytest.ini:
    qt_api = pyqt6
"""
import os
import pytest
from unittest.mock import MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture
def mock_database_obj():
    """Create a mock DatabaseObj with all required table attributes."""
    db = MagicMock()
    db.folders_table = MagicMock()
    db.emails_table = MagicMock()
    db.emails_table_batch = MagicMock()
    db.sent_emails_removal_queue = MagicMock()
    db.oversight_and_defaults = MagicMock()
    db.processed_files = MagicMock()
    db.settings = MagicMock()
    db.session_database = MagicMock()
    db.database_connection = MagicMock()

    db.folders_table.count.return_value = 0
    db.folders_table.find.return_value = iter([])
    db.processed_files.count.return_value = 0
    db.processed_files.distinct.return_value = []
    db.oversight_and_defaults.find_one.return_value = {
        "id": 1,
        "logs_directory": "/tmp/logs",
        "enable_reporting": "False",
        "report_email_destination": "",
        "report_edi_errors": False,
        "report_printing_fallback": "False",
        "single_add_folder_prior": "",
        "batch_add_folder_prior": "",
        "export_processed_folder_prior": "",
    }
    db.settings.find_one.return_value = {
        "id": 1,
        "odbc_driver": "",
        "as400_address": "",
        "as400_username": "",
        "as400_password": "",
        "enable_email": False,
        "email_address": "",
        "email_username": "",
        "email_password": "",
        "email_smtp_server": "",
        "smtp_port": "",
        "enable_interval_backups": False,
        "backup_counter_maximum": 100,
        "backup_counter": 0,
    }
    return db


@pytest.fixture
def mock_ui_service():
    """Create a mock UIServiceProtocol."""
    service = MagicMock()
    service.show_info = MagicMock()
    service.show_error = MagicMock()
    service.show_warning = MagicMock()
    service.ask_yes_no = MagicMock(return_value=False)
    service.ask_ok_cancel = MagicMock(return_value=False)
    service.ask_directory = MagicMock(return_value="")
    service.ask_open_filename = MagicMock(return_value="")
    service.ask_save_filename = MagicMock(return_value="")
    service.pump_events = MagicMock()
    return service


@pytest.fixture
def mock_progress_service():
    """Create a mock ProgressServiceProtocol."""
    service = MagicMock()
    service.show = MagicMock()
    service.hide = MagicMock()
    service.update_message = MagicMock()
    service.is_visible = MagicMock(return_value=False)
    return service


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
    """Create a mock folders table for FolderListWidget tests."""
    table = MagicMock()
    table.find.return_value = iter([])
    table.count.return_value = 0
    table.find_one.return_value = None
    return table


@pytest.fixture
def mock_resend_service():
    """Create a mock ResendService."""
    service = MagicMock()
    service.has_processed_files.return_value = False
    service.get_folder_list.return_value = []
    service.get_files_for_folder.return_value = []
    service.count_files_for_folder.return_value = 0
    service.set_resend_flag = MagicMock()
    return service


@pytest.fixture
def mock_maintenance_functions():
    """Create a mock MaintenanceFunctions."""
    mf = MagicMock()
    mf.set_all_active = MagicMock()
    mf.set_all_inactive = MagicMock()
    mf.clear_resend_flags = MagicMock()
    mf.clear_processed_files_log = MagicMock()
    mf.remove_inactive_folders = MagicMock()
    mf.mark_active_as_processed = MagicMock()
    mf.database_import_wrapper = MagicMock()
    mf._database_obj = MagicMock()
    mf._on_operation_start = None
    mf._on_operation_end = None
    return mf
