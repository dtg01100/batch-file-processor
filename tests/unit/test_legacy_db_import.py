"""Tests for importing legacy v33 settings database files.

Tests the migration path for databases created before the v32->v33 migration
was changed, ensuring old database files can be imported and upgraded to
the current schema version (v41).
"""

import os
import pytest
import dataset

import folders_database_migrator


def _create_old_v33_database(db_path, platform="Linux"):
    """Create a database matching the schema at commit 9446b3de (old v33).

    This replicates the database state after running the OLD v32->v33 migration
    which added split_edi_filter_categories and split_edi_filter_mode columns,
    but did NOT add plugin_config.
    """
    db = dataset.connect('sqlite:///' + db_path)

    db['version'].insert(dict(version="33", os=platform))

    db['administrative'].insert(dict(
        id=1,
        copy_to_directory="",
        logs_directory="/tmp/logs",
        enable_reporting=False,
        report_email_destination="",
        report_edi_errors=False,
        convert_to_format="csv",
        tweak_edi=False,
        split_edi=False,
        force_edi_validation=0,
        append_a_records="False",
        a_record_append_text="",
        force_txt_file_ext="False",
        invoice_date_offset=0,
        retail_uom=0,
        force_each_upc=0,
        include_item_numbers=0,
        include_item_description=0,
        simple_csv_sort_order="upc_number,qty_of_units,unit_cost,description,vendor_item",
        a_record_padding_length=6,
        invoice_date_custom_format_string="%Y%m%d",
        invoice_date_custom_format=0,
        split_prepaid_sales_tax_crec=0,
        estore_store_number=0,
        estore_Vendor_OId=0,
        estore_vendor_NameVendorOID="replaceme",
        prepend_date_files=0,
        rename_file="",
        estore_c_record_OID=0,
        override_upc_bool=False,
        override_upc_level=1,
        override_upc_category_filter="ALL",
        split_edi_include_invoices=True,
        split_edi_include_credits=True,
        fintech_division_id=0,
        split_edi_filter_categories="ALL",
        split_edi_filter_mode="include",
        edi_converter_scratch_folder="/tmp/scratch",
        errors_folder="/tmp/errors",
        single_add_folder_prior="/tmp",
        batch_add_folder_prior="/tmp",
        export_processed_folder_prior="/tmp",
    ))

    db['settings'].insert(dict(
        id=1,
        enable_email=0,
        email_address="",
        email_username="",
        email_password="",
        email_smtp_server="smtp.gmail.com",
        smtp_port=587,
        backup_counter=0,
        backup_counter_maximum=200,
        enable_interval_backups=1,
        odbc_driver="Select ODBC Driver...",
        as400_username="",
        as400_password="",
        as400_address="",
    ))

    db['folders'].insert(dict(
        id=1,
        folder_name="/tmp/test_folder_1",
        alias="Test Folder 1",
        folder_is_active="True",
        copy_to_directory="/tmp/output",
        process_edi="True",
        convert_to_format="csv",
        calculate_upc_check_digit="False",
        upc_target_length=11,
        upc_padding_pattern="           ",
        include_a_records="False",
        include_c_records="False",
        include_headers="False",
        filter_ampersand="False",
        tweak_edi=False,
        pad_a_records="False",
        a_record_padding="",
        a_record_padding_length=6,
        invoice_date_custom_format_string="%Y%m%d",
        invoice_date_custom_format=0,
        reporting_email="",
        report_email_destination="",
        process_backend_copy=False,
        backend_copy_destination=None,
        process_edi_output=False,
        edi_output_folder=None,
        split_edi=False,
        force_edi_validation=0,
        append_a_records="False",
        a_record_append_text="",
        force_txt_file_ext="False",
        invoice_date_offset=0,
        retail_uom=0,
        force_each_upc=0,
        include_item_numbers=0,
        include_item_description=0,
        simple_csv_sort_order="upc_number,qty_of_units,unit_cost,description,vendor_item",
        split_prepaid_sales_tax_crec=0,
        estore_store_number=0,
        estore_Vendor_OId=0,
        estore_vendor_NameVendorOID="replaceme",
        prepend_date_files=0,
        rename_file="",
        estore_c_record_OID=10025,
        override_upc_bool=False,
        override_upc_level=1,
        override_upc_category_filter="ALL",
        split_edi_include_invoices=True,
        split_edi_include_credits=True,
        fintech_division_id=0,
        split_edi_filter_categories="ALL",
        split_edi_filter_mode="include",
    ))

    db['folders'].insert(dict(
        id=2,
        folder_name="/tmp/test_folder_2",
        alias="Test Folder 2 (Inactive)",
        folder_is_active="False",
        copy_to_directory=None,
        process_edi="False",
        convert_to_format="csv",
        calculate_upc_check_digit="False",
        upc_target_length=11,
        upc_padding_pattern="           ",
        include_a_records="False",
        include_c_records="False",
        include_headers="False",
        filter_ampersand="False",
        tweak_edi=False,
        pad_a_records="False",
        a_record_padding="",
        reporting_email="",
        report_email_destination="",
        process_backend_copy=False,
        backend_copy_destination=None,
        process_edi_output=False,
        edi_output_folder=None,
        split_edi_filter_categories="ALL",
        split_edi_filter_mode="include",
    ))

    db.query(
        "CREATE TABLE IF NOT EXISTS processed_files ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "file_name TEXT, md5 TEXT, resend_flag INTEGER, folder_id INTEGER)"
    )

    db.close()
    return db_path


def _create_v32_database(db_path, platform="Linux"):
    """Create a database at v32 (before the split v32->v33 migration).

    This tests the migration path through the fixed v32->v33 step.
    """
    db = dataset.connect('sqlite:///' + db_path)

    db['version'].insert(dict(version="32", os=platform))

    db['administrative'].insert(dict(
        id=1,
        copy_to_directory="",
        logs_directory="/tmp/logs",
        enable_reporting=False,
        report_email_destination="",
        report_edi_errors=False,
        convert_to_format="csv",
        tweak_edi=False,
        split_edi=False,
        force_edi_validation=0,
        append_a_records="False",
        a_record_append_text="",
        force_txt_file_ext="False",
        invoice_date_offset=0,
        retail_uom=0,
        force_each_upc=0,
        include_item_numbers=0,
        include_item_description=0,
        simple_csv_sort_order="upc_number,qty_of_units,unit_cost,description,vendor_item",
        a_record_padding_length=6,
        invoice_date_custom_format_string="%Y%m%d",
        invoice_date_custom_format=0,
        split_prepaid_sales_tax_crec=0,
        estore_store_number=0,
        estore_Vendor_OId=0,
        estore_vendor_NameVendorOID="replaceme",
        prepend_date_files=0,
        rename_file="",
        estore_c_record_OID=0,
        override_upc_bool=False,
        override_upc_level=1,
        override_upc_category_filter="ALL",
        split_edi_include_invoices=True,
        split_edi_include_credits=True,
        fintech_division_id=0,
        edi_converter_scratch_folder="/tmp/scratch",
        errors_folder="/tmp/errors",
        single_add_folder_prior="/tmp",
        batch_add_folder_prior="/tmp",
        export_processed_folder_prior="/tmp",
    ))

    db['settings'].insert(dict(
        id=1,
        enable_email=0,
        email_address="",
        email_username="",
        email_password="",
        email_smtp_server="smtp.gmail.com",
        smtp_port=587,
        backup_counter=0,
        backup_counter_maximum=200,
        enable_interval_backups=1,
        odbc_driver="Select ODBC Driver...",
        as400_username="",
        as400_password="",
        as400_address="",
    ))

    db['folders'].insert(dict(
        id=1,
        folder_name="/tmp/test_v32_folder",
        alias="V32 Test Folder",
        folder_is_active="True",
        process_edi="True",
        convert_to_format="csv",
        calculate_upc_check_digit="False",
        upc_target_length=11,
        include_a_records="False",
        include_c_records="False",
        include_headers="False",
        filter_ampersand="False",
        tweak_edi=False,
        pad_a_records="False",
        a_record_padding="",
        process_backend_copy=False,
        backend_copy_destination=None,
        process_edi_output=False,
        edi_output_folder=None,
        split_edi=False,
        force_edi_validation=0,
        fintech_division_id=0,
    ))

    db.query(
        "CREATE TABLE IF NOT EXISTS processed_files ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "file_name TEXT, md5 TEXT, resend_flag INTEGER, folder_id INTEGER)"
    )

    db.close()
    return db_path


class TestOldV33DatabaseMigration:
    """Test migration of old v33 databases (from commit 9446b3de) to current schema."""

    def test_old_v33_migrates_to_v41(self, tmp_path):
        """An old v33 database should be upgradable to v41."""
        db_path = str(tmp_path / "old_v33.db")
        _create_old_v33_database(db_path)

        db = dataset.connect('sqlite:///' + db_path)
        folders_database_migrator.upgrade_database(db, str(tmp_path), "Linux")

        version = db['version'].find_one(id=1)
        assert version['version'] == "42"
        db.close()

    def test_old_v33_gains_plugin_config_column(self, tmp_path):
        """Old v33 databases should gain plugin_config during migration."""
        db_path = str(tmp_path / "old_v33.db")
        _create_old_v33_database(db_path)

        db = dataset.connect('sqlite:///' + db_path)
        folders_database_migrator.upgrade_database(db, str(tmp_path), "Linux")

        folder = db['folders'].find_one(id=1)
        assert 'plugin_config' in folder
        assert folder['plugin_config'] == ""

        admin = db['administrative'].find_one(id=1)
        assert 'plugin_config' in admin
        assert admin['plugin_config'] == ""
        db.close()

    def test_old_v33_preserves_filter_columns(self, tmp_path):
        """Old v33 databases should preserve split_edi_filter columns during migration."""
        db_path = str(tmp_path / "old_v33.db")
        _create_old_v33_database(db_path)

        db = dataset.connect('sqlite:///' + db_path)
        folders_database_migrator.upgrade_database(db, str(tmp_path), "Linux")

        folder = db['folders'].find_one(id=1)
        assert 'split_edi_filter_categories' in folder
        assert folder['split_edi_filter_categories'] == "ALL"
        assert 'split_edi_filter_mode' in folder
        assert folder['split_edi_filter_mode'] == "include"
        db.close()

    def test_old_v33_preserves_folder_data(self, tmp_path):
        """Migrating an old v33 database should preserve all folder configuration data."""
        db_path = str(tmp_path / "old_v33.db")
        _create_old_v33_database(db_path)

        db = dataset.connect('sqlite:///' + db_path)
        folders_database_migrator.upgrade_database(db, str(tmp_path), "Linux")

        folder = db['folders'].find_one(id=1)
        assert folder['folder_name'] == "/tmp/test_folder_1"
        assert folder['alias'] == "Test Folder 1"
        assert folder['convert_to_format'] == "csv"
        db.close()

    def test_old_v33_gets_timestamps(self, tmp_path):
        """Old v33 databases should get created_at/updated_at timestamps (v33->v34)."""
        db_path = str(tmp_path / "old_v33.db")
        _create_old_v33_database(db_path)

        db = dataset.connect('sqlite:///' + db_path)
        folders_database_migrator.upgrade_database(db, str(tmp_path), "Linux")

        folder = db['folders'].find_one(id=1)
        assert 'created_at' in folder
        assert folder['created_at'] is not None
        assert 'updated_at' in folder
        assert folder['updated_at'] is not None
        db.close()

    def test_old_v33_gets_edi_format(self, tmp_path):
        """Old v33 databases should get edi_format field (v38->v39)."""
        db_path = str(tmp_path / "old_v33.db")
        _create_old_v33_database(db_path)

        db = dataset.connect('sqlite:///' + db_path)
        folders_database_migrator.upgrade_database(db, str(tmp_path), "Linux")

        folder = db['folders'].find_one(id=1)
        assert 'edi_format' in folder
        assert folder['edi_format'] == "default"
        db.close()

    def test_old_v33_boolean_normalization(self, tmp_path):
        """Old v33 databases should have string booleans normalized to integer-like values (v40->v41)."""
        db_path = str(tmp_path / "old_v33.db")
        _create_old_v33_database(db_path)

        db = dataset.connect('sqlite:///' + db_path)
        folders_database_migrator.upgrade_database(db, str(tmp_path), "Linux")

        folder = db['folders'].find_one(id=1)
        assert folder['folder_is_active'] in (0, 1, '0', '1')
        assert folder['process_edi'] in (0, 1, '0', '1')
        assert str(folder['folder_is_active']) != "True"
        assert str(folder['process_edi']) != "False"
        db.close()

    def test_old_v33_settings_table_preserved(self, tmp_path):
        """Settings table data should be preserved through migration."""
        db_path = str(tmp_path / "old_v33.db")
        _create_old_v33_database(db_path)

        db = dataset.connect('sqlite:///' + db_path)
        folders_database_migrator.upgrade_database(db, str(tmp_path), "Linux")

        settings = db['settings'].find_one(id=1)
        assert settings['email_smtp_server'] == "smtp.gmail.com"
        assert settings['smtp_port'] == 587
        assert settings['odbc_driver'] == "Select ODBC Driver..."
        db.close()


class TestV32DatabaseMigration:
    """Test migration from v32 through the fixed v32->v33 step."""

    def test_v32_migrates_to_v41(self, tmp_path):
        """A v32 database should be upgradable to v41 through the fixed migration."""
        db_path = str(tmp_path / "v32.db")
        _create_v32_database(db_path)

        db = dataset.connect('sqlite:///' + db_path)
        folders_database_migrator.upgrade_database(db, str(tmp_path), "Linux")

        version = db['version'].find_one(id=1)
        assert version['version'] == "42"
        db.close()

    def test_v32_gets_all_v33_columns(self, tmp_path):
        """A v32 database should get both filter columns AND plugin_config at v33."""
        db_path = str(tmp_path / "v32.db")
        _create_v32_database(db_path)

        db = dataset.connect('sqlite:///' + db_path)
        folders_database_migrator.upgrade_database(db, str(tmp_path), "Linux", target_version="33")

        version = db['version'].find_one(id=1)
        assert version['version'] == "33"

        folder = db['folders'].find_one(id=1)
        assert 'split_edi_filter_categories' in folder
        assert folder['split_edi_filter_categories'] == "ALL"
        assert 'split_edi_filter_mode' in folder
        assert folder['split_edi_filter_mode'] == "include"
        assert 'plugin_config' in folder
        assert folder['plugin_config'] == ""

        admin = db['administrative'].find_one(id=1)
        assert 'split_edi_filter_categories' in admin
        assert 'split_edi_filter_mode' in admin
        assert 'plugin_config' in admin
        db.close()

    def test_v32_preserves_existing_data(self, tmp_path):
        """v32->v33 migration should not lose existing folder data."""
        db_path = str(tmp_path / "v32.db")
        _create_v32_database(db_path)

        db = dataset.connect('sqlite:///' + db_path)
        folders_database_migrator.upgrade_database(db, str(tmp_path), "Linux")

        folder = db['folders'].find_one(id=1)
        assert folder['folder_name'] == "/tmp/test_v32_folder"
        assert folder['alias'] == "V32 Test Folder"
        db.close()


class TestAddColumnSafe:
    """Test the _add_column_safe helper function."""

    def test_adds_new_column(self, tmp_path):
        """_add_column_safe should add a column that doesn't exist."""
        db_path = str(tmp_path / "test.db")
        db = dataset.connect('sqlite:///' + db_path)
        db['test_table'].insert(dict(id=1, name="test"))

        folders_database_migrator._add_column_safe(db, "test_table", "new_col", '"default_val"')

        db.close()
        db = dataset.connect('sqlite:///' + db_path)
        row = db['test_table'].find_one(id=1)
        assert 'new_col' in row
        assert row['new_col'] == "default_val"
        db.close()

    def test_skips_existing_column(self, tmp_path):
        """_add_column_safe should not fail if column already exists."""
        db_path = str(tmp_path / "test.db")
        db = dataset.connect('sqlite:///' + db_path)
        db['test_table'].insert(dict(id=1, name="test", existing_col="original"))

        folders_database_migrator._add_column_safe(db, "test_table", "existing_col", '"new_default"')

        row = db['test_table'].find_one(id=1)
        assert row['existing_col'] == "original"
        db.close()

    def test_handles_integer_default(self, tmp_path):
        """_add_column_safe should work with integer defaults."""
        db_path = str(tmp_path / "test.db")
        db = dataset.connect('sqlite:///' + db_path)
        db['test_table'].insert(dict(id=1, name="test"))

        folders_database_migrator._add_column_safe(db, "test_table", "int_col", "42")

        db.close()
        db = dataset.connect('sqlite:///' + db_path)
        row = db['test_table'].find_one(id=1)
        assert row['int_col'] == 42
        db.close()


class TestMigrationIdempotency:
    """Test that running migration on an already-current database is safe."""

    def test_migration_noop_on_current_version(self, tmp_path):
        """Running upgrade on a v41 database should not change anything."""
        db_path = str(tmp_path / "old_v33.db")
        _create_old_v33_database(db_path)

        db = dataset.connect('sqlite:///' + db_path)
        folders_database_migrator.upgrade_database(db, str(tmp_path), "Linux")

        version = db['version'].find_one(id=1)
        assert version['version'] == "42"

        folders_database_migrator.upgrade_database(db, str(tmp_path), "Linux")

        version = db['version'].find_one(id=1)
        assert version['version'] == "42"
        db.close()

    def test_old_v33_to_v33_target_preserves_both_column_sets(self, tmp_path):
        """Migrating old v33 with target_version=33 should return early."""
        db_path = str(tmp_path / "old_v33.db")
        _create_old_v33_database(db_path)

        db = dataset.connect('sqlite:///' + db_path)
        folders_database_migrator.upgrade_database(db, str(tmp_path), "Linux", target_version="33")

        version = db['version'].find_one(id=1)
        assert version['version'] == "33"
        db.close()

    def test_full_migration_from_old_v33_then_upgrade_again(self, tmp_path):
        """A fully migrated old v33 DB should handle re-migration gracefully."""
        db_path = str(tmp_path / "old_v33.db")
        _create_old_v33_database(db_path)

        db = dataset.connect('sqlite:///' + db_path)
        folders_database_migrator.upgrade_database(db, str(tmp_path), "Linux")
        assert db['version'].find_one(id=1)['version'] == "42"

        db.close()
        db = dataset.connect('sqlite:///' + db_path)
        folders_database_migrator.upgrade_database(db, str(tmp_path), "Linux")
        assert db['version'].find_one(id=1)['version'] == "42"

        folder = db['folders'].find_one(id=1)
        assert 'plugin_config' in folder
        assert 'split_edi_filter_categories' in folder
        assert 'split_edi_filter_mode' in folder
        assert 'edi_format' in folder
        assert 'created_at' in folder
        db.close()
