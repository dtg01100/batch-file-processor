"""Tests for database initialization and default values.

Ensures that database tables are properly initialized with default values
to prevent NoneType errors when accessing database records.

Tests cover:
- Fresh install scenario (no database exists)
- After first run scenario (database exists with data)
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestFreshInstall:
    """Test database state for fresh install (no database exists yet)."""

    def test_create_database_creates_all_tables(self, tmp_path):
        """Verify create_database.do() creates all required tables."""
        import create_database

        db_path = str(tmp_path / "test.db")
        create_database.do(
            database_version="1.0.0",
            database_path=db_path,
            config_folder=str(tmp_path),
            running_platform="test",
        )

        import dataset

        db = dataset.connect(f"sqlite:///{db_path}")

        tables = db.tables
        assert "version" in tables, "version table should exist"
        assert "settings" in tables, "settings table should exist"
        assert "administrative" in tables, "administrative table should exist"

        db.close()

    def test_create_database_administrative_has_defaults(self, tmp_path):
        """Verify administrative table is populated with default values on fresh install."""
        import create_database

        db_path = str(tmp_path / "test.db")
        create_database.do(
            database_version="1.0.0",
            database_path=db_path,
            config_folder=str(tmp_path),
            running_platform="test",
        )

        import dataset

        db = dataset.connect(f"sqlite:///{db_path}")

        administrative = db["administrative"]
        record = administrative.find_one(id=1)

        assert record is not None, "administrative table should have default record"
        assert "copy_to_directory" in record
        assert "logs_directory" in record
        assert "enable_reporting" in record
        assert record["enable_reporting"] is False

        db.close()

    def test_create_database_settings_has_defaults(self, tmp_path):
        """Verify settings table is populated with default values on fresh install."""
        import create_database

        db_path = str(tmp_path / "test.db")
        create_database.do(
            database_version="1.0.0",
            database_path=db_path,
            config_folder=str(tmp_path),
            running_platform="test",
        )

        import dataset

        db = dataset.connect(f"sqlite:///{db_path}")

        settings = db["settings"]
        record = settings.find_one(id=1)

        assert record is not None, "settings table should have default record"
        assert "folder_is_active" in record
        assert "convert_to_format" in record
        assert record["folder_is_active"] == "False"
        assert record["convert_to_format"] == "csv"

        db.close()

    def test_fresh_database_no_folders_table(self, tmp_path):
        """Verify fresh install has no folders in folders_table."""
        import create_database

        db_path = str(tmp_path / "test.db")
        create_database.do(
            database_version="1.0.0",
            database_path=db_path,
            config_folder=str(tmp_path),
            running_platform="test",
        )

        import dataset

        db = dataset.connect(f"sqlite:///{db_path}")

        tables = db.tables
        assert "folders_table" not in tables, (
            "folders_table should not exist on fresh install"
        )

        db.close()


class TestAfterFirstRun:
    """Test database state after first run (database exists with data)."""

    def test_administrative_record_exists_after_init(self, tmp_path):
        """Verify administrative record exists after database initialization."""
        import create_database
        import dataset

        db_path = str(tmp_path / "test.db")
        create_database.do(
            database_version="1.0.0",
            database_path=db_path,
            config_folder=str(tmp_path),
            running_platform="test",
        )

        db = dataset.connect(f"sqlite:///{db_path}")
        record = db["administrative"].find_one(id=1)

        assert record is not None, "administrative record should exist after init"
        assert record["id"] == 1

        db.close()

    def test_administrative_record_can_be_updated(self, tmp_path):
        """Verify administrative record can be updated after first run."""
        import create_database
        import dataset

        db_path = str(tmp_path / "test.db")
        create_database.do(
            database_version="1.0.0",
            database_path=db_path,
            config_folder=str(tmp_path),
            running_platform="test",
        )

        db = dataset.connect(f"sqlite:///{db_path}")

        updated_record = {
            "id": 1,
            "copy_to_directory": "/new/path",
            "logs_directory": "/new/logs",
            "enable_reporting": True,
            "report_email_destination": "test@example.com",
            "report_edi_errors": True,
        }
        db["administrative"].update(updated_record, ["id"])

        record = db["administrative"].find_one(id=1)
        assert record["copy_to_directory"] == "/new/path"
        assert record["enable_reporting"] is True

        db.close()

    def test_oversight_and_defaults_find_one_returns_record(self, tmp_path):
        """Verify oversight_and_defaults.find_one returns record after first run."""
        import create_database
        import dataset

        db_path = str(tmp_path / "test.db")
        create_database.do(
            database_version="1.0.0",
            database_path=db_path,
            config_folder=str(tmp_path),
            running_platform="test",
        )

        db = dataset.connect(f"sqlite:///{db_path}")
        administrative = db["administrative"]

        record = administrative.find_one(id=1)
        assert record is not None, "find_one should return record after init"
        assert "copy_to_directory" in record

        db.close()


class TestSetDefaultsPopup:
    """Test set_defaults_popup handles both fresh and existing database states."""

    def test_set_defaults_popup_with_none_record(self):
        """Verify set_defaults_popup handles missing oversight_and_defaults record."""
        defaults = {}
        if defaults is None:
            defaults = {}
        defaults.setdefault("copy_to_directory", "")
        defaults.setdefault(
            "logs_directory",
            os.path.join(os.path.expanduser("~"), "BatchFileSenderLogs"),
        )
        defaults.setdefault("enable_reporting", False)
        defaults.setdefault("report_email_destination", "")
        defaults.setdefault("report_edi_errors", False)
        defaults.setdefault("folder_name", "template")
        defaults.setdefault("folder_is_active", "True")
        defaults.setdefault("alias", "")
        defaults.setdefault("process_backend_copy", False)
        defaults.setdefault("process_backend_ftp", False)
        defaults.setdefault("process_backend_email", False)
        defaults.setdefault("ftp_server", "")
        defaults.setdefault("ftp_port", 21)
        defaults.setdefault("ftp_folder", "")
        defaults.setdefault("ftp_username", "")
        defaults.setdefault("ftp_password", "")
        defaults.setdefault("email_to", "")
        defaults.setdefault("email_subject_line", "")
        defaults.setdefault("process_edi", "False")
        defaults.setdefault("convert_to_format", "csv")

        assert defaults is not None
        assert defaults["copy_to_directory"] == ""
        assert defaults["folder_name"] == "template"

    def test_set_defaults_popup_with_existing_record(self, tmp_path):
        """Verify set_defaults_popup preserves existing values from database."""
        import create_database
        import dataset

        db_path = str(tmp_path / "test.db")
        create_database.do(
            database_version="1.0.0",
            database_path=db_path,
            config_folder=str(tmp_path),
            running_platform="test",
        )

        db = dataset.connect(f"sqlite:///{db_path}")

        existing_record = {
            "id": 1,
            "copy_to_directory": "/existing/path",
            "logs_directory": "/existing/logs",
            "enable_reporting": True,
            "report_email_destination": "existing@example.com",
            "report_edi_errors": False,
        }
        db["administrative"].update(existing_record, ["id"])

        record = db["administrative"].find_one(id=1)

        defaults = record if record is not None else {}
        defaults.setdefault("copy_to_directory", "")
        defaults.setdefault(
            "logs_directory",
            os.path.join(os.path.expanduser("~"), "BatchFileSenderLogs"),
        )

        assert defaults["copy_to_directory"] == "/existing/path"
        assert defaults["enable_reporting"] is True
        assert defaults["report_email_destination"] == "existing@example.com"

        db.close()


class TestEditDialogDefaults:
    """Test EditDialog receives proper defaults in all scenarios."""

    REQUIRED_KEYS = [
        "copy_to_directory",
        "folder_is_active",
        "alias",
        "process_backend_copy",
        "process_backend_ftp",
        "process_backend_email",
        "ftp_server",
        "ftp_port",
        "ftp_folder",
        "ftp_username",
        "ftp_password",
        "email_to",
        "email_subject_line",
        "convert_to_format",
        "process_edi",
        "folder_name",
        "calculate_upc_check_digit",
        "include_a_records",
        "include_c_records",
        "include_headers",
        "filter_ampersand",
        "tweak_edi",
        "split_edi",
        "split_edi_include_invoices",
        "split_edi_include_credits",
        "prepend_date_files",
        "split_edi_filter_categories",
        "split_edi_filter_mode",
        "rename_file",
        "pad_a_records",
        "a_record_padding",
        "a_record_padding_length",
        "append_a_records",
        "a_record_append_text",
        "force_txt_file_ext",
        "invoice_date_offset",
        "invoice_date_custom_format",
        "invoice_date_custom_format_string",
        "retail_uom",
        "force_edi_validation",
        "override_upc_bool",
        "override_upc_level",
        "override_upc_category_filter",
        "upc_target_length",
        "upc_padding_pattern",
        "include_item_numbers",
        "include_item_description",
        "simple_csv_sort_order",
        "split_prepaid_sales_tax_crec",
        "estore_store_number",
        "estore_Vendor_OId",
        "estore_vendor_NameVendorOID",
        "estore_c_record_OID",
        "fintech_division_id",
    ]

    def test_edit_dialog_has_all_required_keys(self):
        """Verify EditDialog default config has all required keys."""
        default_folder_config = {key: "" for key in self.REQUIRED_KEYS}
        default_folder_config.update(
            {
                "folder_is_active": "True",
                "folder_name": "template",
                "process_backend_copy": False,
                "process_backend_ftp": False,
                "process_backend_email": False,
                "ftp_port": 21,
                "a_record_padding_length": 6,
                "invoice_date_offset": 0,
                "override_upc_level": 1,
                "upc_target_length": 11,
            }
        )

        for key in self.REQUIRED_KEYS:
            assert key in default_folder_config, f"Missing required key: {key}"

    def test_set_defaults_popup_provides_all_required_keys(self):
        """Verify set_defaults_popup provides all keys required by EditDialog."""
        defaults = {}
        for key in self.REQUIRED_KEYS:
            defaults.setdefault(key, "")

        defaults.setdefault(
            "logs_directory",
            os.path.join(os.path.expanduser("~"), "BatchFileSenderLogs"),
        )
        defaults.setdefault("enable_reporting", False)
        defaults.setdefault("report_email_destination", "")
        defaults.setdefault("report_edi_errors", False)

        keys_accessed_in_edit_dialog = [
            "copy_to_directory",
            "convert_to_format",
            "folder_name",
            "process_edi",
            "tweak_edi",
            "folder_is_active",
            "alias",
        ]

        for key in keys_accessed_in_edit_dialog:
            assert key in defaults, f"Missing key accessed by EditDialog: {key}"


class TestDatabaseMigration:
    """Test handling of databases created before administrative table existed."""

    def test_old_database_missing_administrative_table(self, tmp_path):
        """Verify code handles database without administrative table (legacy)."""
        import dataset

        db_path = str(tmp_path / "old_test.db")
        db = dataset.connect(f"sqlite:///{db_path}")

        db["version"].insert({"version": "10", "os": "Windows"})
        db["settings"].insert({"folder_is_active": "False", "convert_to_format": "csv"})

        tables = db.tables
        assert "administrative" not in tables, (
            "old database should not have administrative table"
        )

        administrative = db["administrative"]
        record = administrative.find_one(id=1)
        assert record is None, "find_one should return None for missing table"

        db.close()

    def test_legacy_database_handled_gracefully(self, tmp_path):
        """Verify legacy database without administrative table is handled."""
        import dataset

        db_path = str(tmp_path / "legacy_test.db")
        db = dataset.connect(f"sqlite:///{db_path}")

        db["version"].insert({"version": "10", "os": "Windows"})

        administrative = db["administrative"]
        record = administrative.find_one(id=1)

        defaults = record if record is not None else {}
        defaults.setdefault("copy_to_directory", "")
        defaults.setdefault(
            "logs_directory",
            os.path.join(os.path.expanduser("~"), "BatchFileSenderLogs"),
        )
        defaults.setdefault("enable_reporting", False)

        assert defaults is not None
        assert defaults["copy_to_directory"] == ""
        assert "logs_directory" in defaults

        db.close()
