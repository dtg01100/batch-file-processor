"""Shared fixtures for Qt UI tests.

pytest-qt is used for Qt widget testing. It automatically provides the
``qtbot`` fixture and manages the ``QApplication`` lifecycle.

Configuration in pytest.ini:
    qt_api = pyqt6
    QT_QPA_PLATFORM=offscreen

Note: Tests should use real Qt widgets, not mocks. Database operations
should use real DatabaseObj with temporary databases where possible.
"""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


# ---------------------------------------------------------------------------
# _SpyMaintenanceFunctions — thin spy subclass for maintenance dialog tests
# ---------------------------------------------------------------------------


class _SpyMaintenanceFunctions:
    """Thin spy wrapper that records which methods were called.

    Instantiated lazily inside mock_maintenance_functions to avoid importing
    MaintenanceFunctions at module load time.
    """

    # The actual class body is built at fixture-creation time; see fixture below.


def _build_spy_class():
    from interface.operations.maintenance_functions import MaintenanceFunctions

    class SpyMaintenanceFunctions(MaintenanceFunctions):
        """Thin spy wrapper that records which methods were called."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._called: set = set()

        def _record(self, name: str):
            self._called.add(name)

        def was_called(self, name: str) -> bool:
            return name in self._called

        def set_all_active(self):
            self._record("set_all_active")
            super().set_all_active()

        def set_all_inactive(self):
            self._record("set_all_inactive")
            super().set_all_inactive()

        def clear_resend_flags(self):
            self._record("clear_resend_flags")
            super().clear_resend_flags()

        def database_import_wrapper(self, path):
            self._record("database_import_wrapper")
            super().database_import_wrapper(path)

    return SpyMaintenanceFunctions


@pytest.fixture
def sample_folder_config():
    """Create a sample folder configuration dict.

    This is pure data - no fakes needed.
    """
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
def mock_database_obj(tmp_path):
    """Create a real database object for Qt tests using a temporary database.

    This fixture creates a real DatabaseObj with a temporary SQLite database,
    allowing tests to perform actual database operations without mocks.
    Each test gets an isolated database that is cleaned up automatically.

    Returns:
        DatabaseObj: A real database object with initialized tables including
        processed_files and folders_table.
    """
    from core.constants import CURRENT_DATABASE_VERSION
    from backend.database.database_obj import DatabaseObj

    db_path = tmp_path / "test_folders.db"

    db = DatabaseObj(
        database_path=str(db_path),
        database_version=CURRENT_DATABASE_VERSION,
        config_folder=str(tmp_path),
        running_platform="Linux",
    )

    return db


@pytest.fixture
def mock_maintenance_functions(tmp_path):
    from core.constants import CURRENT_DATABASE_VERSION
    from backend.database.database_obj import DatabaseObj

    db_path = tmp_path / "maint_test.db"
    db = DatabaseObj(
        database_path=str(db_path),
        database_version=CURRENT_DATABASE_VERSION,
        config_folder=str(tmp_path),
        running_platform="Linux",
    )
    SpyMaintenanceFunctions = _build_spy_class()
    mf = SpyMaintenanceFunctions(database_obj=db)
    yield mf
    db.close()
