import logging
import os

logger = logging.getLogger(__name__)

# Magic string constants
CSV_SORT_ORDER = "upc_number,qty_of_units,unit_cost,description,vendor_item"
REPLACEME_PLACEHOLDER = "replaceme"


def _quote_identifier(name: str) -> str:
    """Quote a SQL identifier, escaping any embedded quotes."""
    escaped = name.replace('"', '""')
    return f'"{escaped}"'


def _add_column_safe(db, table_name, column_name, default_sql, sql_type="TEXT") -> None:
    """Add a column to a table if it doesn't already exist.

    Args:
        db: A sqlite_wrapper.Database connection.
        table_name: Name of the table to alter.
        column_name: Name of the column to add.
        default_sql: SQL literal for the default value (e.g. '"default_val"', '0').
        sql_type: SQL column type (default "TEXT").

    """
    cursor = db.raw_connection.cursor()
    quoted_table = _quote_identifier(table_name)
    cursor.execute(f"PRAGMA table_info({quoted_table})")
    existing = {row[1] for row in cursor.fetchall()}
    if column_name in existing:
        return
    quoted_column = _quote_identifier(column_name)
    db.query(f"ALTER TABLE {quoted_table} ADD COLUMN {quoted_column} {sql_type}")
    db.query(f"UPDATE {quoted_table} SET {quoted_column} = {default_sql}")


def _log_migration_step(from_version, to_version) -> None:
    """Log migration step progress."""
    print(f"  Migrating: v{from_version} → v{to_version}")


def upgrade_database(
    database_connection, config_folder, running_platform, target_version=None
) -> None:
    db_version = database_connection["version"]
    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if db_version_dict["version"] == "5":
        folders_table = database_connection["folders"]
        folders_table.create_column("convert_to_format", "String")
        convert_to_csv_list = folders_table.find(process_edi=1)
        for line in convert_to_csv_list:
            line["convert_to_format"] = "csv"
            folders_table.update(line, ["id"])
        administrative_section = database_connection["administrative"]
        administrative_section.create_column("convert_to_format", "String")
        administrative_section_update_dict = administrative_section.find_one(id=1)
        administrative_section_update_dict["convert_to_format"] = "csv"
        administrative_section.update(administrative_section_update_dict, ["id"])

        update_version = dict(id=1, version="6")
        db_version.update(update_version, ["id"])
        _log_migration_step("5", "6")

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if db_version_dict["version"] == "6":
        processed_table = database_connection["processed_files"]
        processed_table.create_column("resend_flag", "Boolean")
        database_connection.raw_connection.execute(
            "UPDATE processed_files SET resend_flag = 0"
        )
        database_connection.commit()

        update_version = dict(id=1, version="7")
        db_version.update(update_version, ["id"])

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if db_version_dict["version"] == "7":
        folders_table = database_connection["folders"]
        administrative_section = database_connection["administrative"]
        administrative_section.create_column("tweak_edi", "Boolean")
        administrative_section_update_dict = administrative_section.find_one(id=1)
        administrative_section_update_dict["tweak_edi"] = 0
        administrative_section.update(administrative_section_update_dict, ["id"])

        folders_table.create_column("tweak_edi", "Boolean")
        for line in folders_table.all():
            if line["pad_a_records"] == 0:
                line["tweak_edi"] = 0
                folders_table.update(line, ["id"])
            else:
                line["tweak_edi"] = 1
                folders_table.update(line, ["id"])
        update_version = dict(id=1, version="8")
        db_version.update(update_version, ["id"])

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if db_version_dict["version"] == "8":
        administrative_section = database_connection["administrative"]

        administrative_section.create_column("single_add_folder_prior", "String")
        administrative_section.create_column("batch_add_folder_prior", "String")
        administrative_section.create_column("export_processed_folder_prior", "String")

        administrative_section_update_dict = dict(
            id=1,
            single_add_folder_prior=os.path.join(os.getcwd()),
            batch_add_folder_prior=os.path.join(os.getcwd()),
            export_processed_folder_prior=os.path.join(os.getcwd()),
        )

        administrative_section.update(administrative_section_update_dict, ["id"])
        update_version = dict(id=1, version="9")
        db_version.update(update_version, ["id"])
        _log_migration_step("8", "9")

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if db_version_dict["version"] == "9":
        administrative_section = database_connection["administrative"]
        administrative_section.create_column("report_edi_errors", "Boolean")
        administrative_section_update_dict = dict(id=1, report_edi_errors=0)
        administrative_section.update(administrative_section_update_dict, ["id"])
        update_version = dict(id=1, version="10")
        db_version.update(update_version, ["id"])
        _log_migration_step("9", "10")

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if db_version_dict["version"] == "10":
        folders_table = database_connection["folders"]
        administrative_section = database_connection["administrative"]
        administrative_section.create_column("split_edi", "Boolean")
        administrative_section_update_dict = administrative_section.find_one(id=1)
        administrative_section_update_dict["split_edi"] = 0
        administrative_section.update(administrative_section_update_dict, ["id"])

        folders_table.create_column("split_edi", "Boolean")
        for line in folders_table.all():
            line["split_edi"] = 0
            folders_table.update(line, ["id"])
        update_version = dict(id=1, version="11")
        db_version.update(update_version, ["id"])

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if db_version_dict["version"] == "11":
        administrative_section = database_connection["administrative"]

        database_connection.query("DROP TABLE IF EXISTS settings")
        database_connection.query(
            """
            CREATE TABLE settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                enable_email INTEGER,
                email_address TEXT,
                email_username TEXT,
                email_password TEXT,
                email_smtp_server TEXT,
                smtp_port INTEGER,
                backup_counter INTEGER,
                backup_counter_maximum INTEGER,
                enable_interval_backups INTEGER
            )
        """
        )

        settings_table = database_connection["settings"]
        administrative_section_dict = administrative_section.find_one(id=1)

        email_state = (
            1 if administrative_section_dict.get("enable_reporting") == 1 else 0
        )

        settings_table.insert(
            dict(
                enable_email=email_state,
                email_address=administrative_section_dict.get(
                    "report_email_address", ""
                ),
                email_username=administrative_section_dict.get(
                    "report_email_username", ""
                ),
                email_password=administrative_section_dict.get(
                    "report_email_password", ""
                ),
                email_smtp_server=administrative_section_dict.get(
                    "report_email_smtp_server", "smtp.gmail.com"
                ),
                smtp_port=int(
                    administrative_section_dict.get("reporting_smtp_port", 587)
                ),
                backup_counter=0,
                backup_counter_maximum=200,
                enable_interval_backups=1,
            )
        )
        update_version = dict(id=1, version="12")
        db_version.update(update_version, ["id"])
        _log_migration_step("11", "12")

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if db_version_dict["version"] == "12":
        administrative_section = database_connection["administrative"]
        config_folder_path = config_folder if config_folder else os.getcwd()

        administrative_section.create_column("logs_directory", "String")
        administrative_section.create_column("edi_converter_scratch_folder", "String")
        administrative_section.create_column("errors_folder", "String")

        administrative_section_update_dict = dict(
            id=1,
            logs_directory=os.path.join(config_folder_path, "run_logs"),
            edi_converter_scratch_folder=os.path.join(
                config_folder_path, "edi_converter_scratch_folder"
            ),
            errors_folder=os.path.join(config_folder_path, "errors"),
        )
        administrative_section.update(administrative_section_update_dict, ["id"])
        update_version = dict(id=1, version="13")
        db_version.update(update_version, ["id"])
        _log_migration_step("12", "13")

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if db_version_dict["version"] == "13":
        database_connection.query(
            'update "folders" set "convert_to_format"="", "process_edi"=0 where "convert_to_format"="insight"'
        )
        update_version = dict(id=1, version="14", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("13", "14")

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if db_version_dict["version"] == "14":
        database_connection.query(
            "alter table 'folders' add column 'force_edi_validation'"
        )
        database_connection.query('UPDATE "folders" SET "force_edi_validation" = 0')
        database_connection.query(
            "alter table 'administrative' add column 'force_edi_validation'"
        )
        database_connection.query(
            'UPDATE "administrative" SET "force_edi_validation" = 0'
        )
        update_version = dict(id=1, version="15", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("14", "15")

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if db_version_dict["version"] == "15":
        database_connection.query("alter table 'folders' add column 'append_a_records'")
        database_connection.query('UPDATE "folders" SET "append_a_records" = 0')
        database_connection.query(
            "alter table 'folders' add column 'a_record_append_text'"
        )
        database_connection.query('UPDATE "folders" SET "a_record_append_text" = ""')
        database_connection.query(
            "alter table 'folders' add column 'force_txt_file_ext'"
        )
        database_connection.query('UPDATE "folders" SET "force_txt_file_ext" = 0')
        database_connection.query(
            "alter table 'administrative' add column 'append_a_records'"
        )
        database_connection.query('UPDATE "administrative" SET "append_a_records" = 0')
        database_connection.query(
            "alter table 'administrative' add column 'a_record_append_text'"
        )
        database_connection.query(
            'UPDATE "administrative" SET "a_record_append_text" = ""'
        )
        database_connection.query(
            "alter table 'administrative' add column 'force_txt_file_ext'"
        )
        database_connection.query(
            'UPDATE "administrative" SET "force_txt_file_ext" = 0'
        )
        update_version = dict(id=1, version="16", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("15", "16")

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if db_version_dict["version"] == "16":
        database_connection.query(
            "alter table 'folders' add column 'invoice_date_offset'"
        )
        database_connection.query('UPDATE "folders" SET "invoice_date_offset" = 0')
        database_connection.query(
            "alter table 'administrative' add column 'invoice_date_offset'"
        )
        database_connection.query(
            'UPDATE "administrative" SET "invoice_date_offset" = 0'
        )
        update_version = dict(id=1, version="17", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("16", "17")

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if db_version_dict["version"] == "17":
        database_connection.query("alter table 'settings' add column 'odbc_driver'")
        database_connection.query(
            'UPDATE "settings" SET "odbc_driver" = "Select ODBC Driver..."'
        )
        database_connection.query("alter table 'settings' add column 'as400_username'")
        database_connection.query('UPDATE "settings" SET "as400_username" = ""')
        database_connection.query("alter table 'settings' add column 'as400_password'")
        database_connection.query('UPDATE "settings" SET "as400_password" = ""')
        database_connection.query("alter table 'settings' add column 'as400_address'")
        database_connection.query('UPDATE "settings" SET "as400_address" = ""')
        update_version = dict(id=1, version="18", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("17", "18")

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if db_version_dict["version"] == "18":
        database_connection.query("alter table 'folders' add column 'retail_uom'")
        database_connection.query('UPDATE "folders" SET "retail_uom" = 0')
        database_connection.query(
            "alter table 'administrative' add column 'retail_uom'"
        )
        database_connection.query('UPDATE "administrative" SET "retail_uom" = 0')
        update_version = dict(id=1, version="19", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("18", "19")

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if db_version_dict["version"] == "19":
        database_connection.query("alter table 'folders' add column 'force_each_upc'")
        database_connection.query('UPDATE "folders" SET "force_each_upc" = 0')
        database_connection.query(
            "alter table 'administrative' add column 'force_each_upc'"
        )
        database_connection.query('UPDATE "administrative" SET "force_each_upc" = 0')
        update_version = dict(id=1, version="20", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("19", "20")

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if db_version_dict["version"] == "20":
        database_connection.query(
            "alter table 'folders' add column 'include_item_numbers'"
        )
        database_connection.query('UPDATE "folders" SET "include_item_numbers" = 0')
        database_connection.query(
            "alter table 'administrative' add column 'include_item_numbers'"
        )
        database_connection.query(
            'UPDATE "administrative" SET "include_item_numbers" = 0'
        )
        update_version = dict(id=1, version="21", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("20", "21")

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if db_version_dict["version"] == "21":
        try:
            database_connection.query(
                "alter table 'folders' add column 'include_item_description'"
            )
            database_connection.query(
                'UPDATE "folders" SET "include_item_description" = 0'
            )
        except RuntimeError:
            logger.debug("Column already exists, skipping (idempotent)")
        database_connection.query(
            "alter table 'administrative' add column 'include_item_description'"
        )
        database_connection.query(
            'UPDATE "administrative" SET "include_item_description" = 0'
        )
        update_version = dict(id=1, version="22", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("21", "22")

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if db_version_dict["version"] == "22":
        try:
            database_connection.query(
                "alter table 'folders' add column 'simple_csv_sort_order'"
            )
            database_connection.query(
                'UPDATE "folders" SET "simple_csv_sort_order" = CSV_SORT_ORDER'
            )
        except RuntimeError:
            logger.debug("Column already exists, skipping (idempotent)")
        database_connection.query(
            "alter table 'administrative' add column 'simple_csv_sort_order'"
        )
        database_connection.query(
            'UPDATE "administrative" SET "simple_csv_sort_order" = CSV_SORT_ORDER'
        )
        update_version = dict(id=1, version="23", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("22", "23")

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if db_version_dict["version"] == "23":
        database_connection.query(
            "alter table 'folders' add column 'a_record_padding_length'"
        )
        database_connection.query('UPDATE "folders" SET "a_record_padding_length" = 6')
        database_connection.query(
            "alter table 'administrative' add column 'a_record_padding_length'"
        )
        database_connection.query(
            'UPDATE "administrative" SET "a_record_padding_length" = 6'
        )
        database_connection.query(
            "alter table 'folders' add column 'invoice_date_custom_format_string'"
        )
        database_connection.query(
            'UPDATE "folders" SET "invoice_date_custom_format_string" = "%Y%m%d"'
        )
        database_connection.query(
            "alter table 'administrative' add column 'invoice_date_custom_format_string'"
        )
        database_connection.query(
            'UPDATE "administrative" SET "invoice_date_custom_format_string" = "%Y%m%d"'
        )
        database_connection.query(
            "alter table 'folders' add column 'invoice_date_custom_format'"
        )
        database_connection.query(
            'UPDATE "folders" SET "invoice_date_custom_format" = 0'
        )
        database_connection.query(
            "alter table 'administrative' add column 'invoice_date_custom_format'"
        )
        database_connection.query(
            'UPDATE "administrative" SET "invoice_date_custom_format" = 0'
        )
        update_version = dict(id=1, version="24", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("23", "24")

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if db_version_dict["version"] == "24":
        try:
            database_connection.query(
                "alter table 'folders' add column 'split_prepaid_sales_tax_crec'"
            )
            database_connection.query(
                'UPDATE "folders" SET "split_prepaid_sales_tax_crec" = 0'
            )
        except RuntimeError:
            logger.debug("Column already exists, skipping (idempotent)")
        database_connection.query(
            "alter table 'administrative' add column 'split_prepaid_sales_tax_crec'"
        )
        database_connection.query(
            'UPDATE "administrative" SET "split_prepaid_sales_tax_crec" = 0'
        )
        update_version = dict(id=1, version="25", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("24", "25")

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if db_version_dict["version"] == "25":
        try:
            database_connection.query(
                "alter table 'folders' add column 'estore_store_number'"
            )
            database_connection.query('UPDATE "folders" SET "estore_store_number" = 0')
            database_connection.query(
                "alter table 'folders' add column 'estore_Vendor_OId'"
            )
            database_connection.query('UPDATE "folders" SET "estore_Vendor_OId" = 0')
            database_connection.query(
                "alter table 'folders' add column 'estore_vendor_NameVendorOID'"
            )
            database_connection.query(
                'UPDATE "folders" SET "estore_vendor_NameVendorOID" = REPLACEME_PLACEHOLDER'
            )
        except RuntimeError:
            logger.debug("Column already exists, skipping (idempotent)")
        database_connection.query(
            "alter table 'administrative' add column 'estore_store_number'"
        )
        database_connection.query(
            'UPDATE "administrative" SET "estore_store_number" = 0'
        )
        database_connection.query(
            "alter table 'administrative' add column 'estore_Vendor_OId'"
        )
        database_connection.query('UPDATE "administrative" SET "estore_Vendor_OId" = 0')
        database_connection.query(
            "alter table 'administrative' add column 'estore_vendor_NameVendorOID'"
        )
        database_connection.query(
            "UPDATE 'administrative' SET 'estore_vendor_NameVendorOID' = REPLACEME_PLACEHOLDER"
        )
        update_version = dict(id=1, version="26", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("25", "26")

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if db_version_dict["version"] == "26":
        database_connection.query(
            "alter table 'folders' add column 'prepend_date_files'"
        )
        database_connection.query('UPDATE "folders" SET "prepend_date_files" = 0')
        database_connection.query(
            "alter table 'administrative' add column 'prepend_date_files'"
        )
        database_connection.query(
            'UPDATE "administrative" SET "prepend_date_files" = 0'
        )
        update_version = dict(id=1, version="27", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("26", "27")

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if db_version_dict["version"] == "27":
        database_connection.query("alter table 'folders' add column 'rename_file'")
        database_connection.query('UPDATE "folders" SET "rename_file" = ""')
        database_connection.query(
            "alter table 'administrative' add column 'rename_file'"
        )
        database_connection.query('UPDATE "administrative" SET "rename_file" = ""')
        update_version = dict(id=1, version="28", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("27", "28")

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if db_version_dict["version"] == "28":
        database_connection.query(
            "alter table 'folders' add column 'estore_c_record_OID'"
        )
        database_connection.query('UPDATE "folders" SET "estore_c_record_OID" = 10025')
        database_connection.query(
            "alter table 'administrative' add column 'estore_c_record_OID'"
        )
        database_connection.query(
            'UPDATE "administrative" SET "estore_c_record_OID" = 0'
        )
        update_version = dict(id=1, version="29", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("28", "29")

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if db_version_dict["version"] == "29":
        database_connection.query(
            "alter table 'folders' add column 'override_upc_bool'"
        )
        database_connection.query('UPDATE "folders" set "override_upc_bool"=0')
        database_connection.query(
            "alter table 'folders' add column 'override_upc_level'"
        )
        database_connection.query('UPDATE "folders" set "override_upc_level"=1')
        database_connection.query(
            "alter table 'folders' add column 'override_upc_category_filter'"
        )
        database_connection.query(
            'UPDATE "folders" set "override_upc_category_filter"="ALL"'
        )
        database_connection.query(
            'update "folders" set "override_upc_bool"=1, "override_upc_level"=1 where "force_each_upc"=1'
        )
        database_connection.query(
            "alter table 'administrative' add column 'override_upc_bool'"
        )
        database_connection.query('UPDATE "administrative" set "override_upc_bool"=0')
        database_connection.query(
            "alter table 'administrative' add column 'override_upc_level'"
        )
        database_connection.query('UPDATE "administrative" set "override_upc_level"=1')
        database_connection.query(
            "alter table 'administrative' add column 'override_upc_category_filter'"
        )
        database_connection.query(
            'UPDATE "administrative" set "override_upc_category_filter"="ALL"'
        )
        update_version = dict(id=1, version="30", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("29", "30")

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if db_version_dict["version"] == "30":
        database_connection.query(
            "alter table 'folders' add column 'split_edi_include_invoices'"
        )
        database_connection.query('UPDATE "folders" set "split_edi_include_invoices"=1')
        database_connection.query(
            "alter table 'folders' add column 'split_edi_include_credits'"
        )
        database_connection.query('UPDATE "folders" set "split_edi_include_credits"=1')
        database_connection.query(
            "alter table 'administrative' add column 'split_edi_include_invoices'"
        )
        database_connection.query(
            'UPDATE "administrative" set "split_edi_include_invoices"=1'
        )
        database_connection.query(
            "alter table 'administrative' add column 'split_edi_include_credits'"
        )
        database_connection.query(
            'UPDATE "administrative" set "split_edi_include_credits"=1'
        )
        update_version = dict(id=1, version="31", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("30", "31")

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if db_version_dict["version"] == "31":
        database_connection.query(
            "alter table 'folders' add column 'fintech_division_id'"
        )
        database_connection.query('UPDATE "folders" set "fintech_division_id"=0')
        database_connection.query(
            "alter table 'administrative' add column 'fintech_division_id'"
        )
        database_connection.query('UPDATE "administrative" set "fintech_division_id"=0')
        update_version = dict(id=1, version="32", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("31", "32")

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if db_version_dict["version"] == "32":
        from migrations.add_plugin_config_column import apply_migration

        if not apply_migration(database_connection):
            raise RuntimeError("Plugin config migration failed")

        update_version = dict(id=1, version="33", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("32", "33")

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if db_version_dict["version"] == "33":
        import datetime

        now = datetime.datetime.now().isoformat()

        cursor = database_connection.raw_connection.cursor()
        # Use DEFAULT clause so existing rows get the value without a full-table UPDATE.
        # Wrap each ALTER in try/except — ensure_schema may have already added the column.
        for stmt in [
            f"ALTER TABLE 'folders' ADD COLUMN 'created_at' TEXT DEFAULT '{now}'",
            f"ALTER TABLE 'folders' ADD COLUMN 'updated_at' TEXT DEFAULT '{now}'",
            f"ALTER TABLE 'administrative' ADD COLUMN 'created_at' TEXT DEFAULT '{now}'",
            f"ALTER TABLE 'administrative' ADD COLUMN 'updated_at' TEXT DEFAULT '{now}'",
            f"ALTER TABLE 'processed_files' ADD COLUMN 'created_at' TEXT DEFAULT '{now}'",
            "ALTER TABLE 'processed_files' ADD COLUMN 'processed_at' TEXT",
            f"ALTER TABLE 'settings' ADD COLUMN 'created_at' TEXT DEFAULT '{now}'",
            f"ALTER TABLE 'settings' ADD COLUMN 'updated_at' TEXT DEFAULT '{now}'",
        ]:
            try:
                cursor.execute(stmt)
            except Exception:
                pass  # column already exists
        database_connection.raw_connection.commit()

        update_version = dict(id=1, version="34", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("33", "34")

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if db_version_dict["version"] == "34":
        cursor = database_connection.raw_connection.cursor()
        for col in [
            "filename",
            "original_path",
            "processed_path",
            "error_message",
            "convert_format",
            "sent_to",
        ]:
            try:
                cursor.execute(f"ALTER TABLE 'processed_files' ADD COLUMN '{col}' TEXT")
            except Exception:
                pass  # column already exists
        try:
            cursor.execute(
                "ALTER TABLE 'processed_files' ADD COLUMN 'status' TEXT DEFAULT 'processed'"
            )
        except Exception:
            pass  # column already exists
        cursor.execute(
            "UPDATE 'processed_files' SET filename=file_name WHERE file_name IS NOT NULL AND filename IS NULL"
        )
        database_connection.raw_connection.commit()

        update_version = dict(id=1, version="35", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("34", "35")

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if db_version_dict["version"] == "35":
        cursor = database_connection.raw_connection.cursor()
        for ddl in [
            "CREATE INDEX IF NOT EXISTS idx_folders_active ON folders(folder_is_active)",
            "CREATE INDEX IF NOT EXISTS idx_folders_alias ON folders(alias)",
            "CREATE INDEX IF NOT EXISTS idx_processed_files_folder ON processed_files(folder_id)",
            "CREATE INDEX IF NOT EXISTS idx_processed_files_status ON processed_files(status)",
            "CREATE INDEX IF NOT EXISTS idx_processed_files_created ON processed_files(created_at)",
        ]:
            try:
                cursor.execute(ddl)
            except Exception:
                pass  # column referenced by index may not exist in this DB variant
        database_connection.raw_connection.commit()

        update_version = dict(id=1, version="36", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("35", "36")

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if db_version_dict["version"] == "36":
        update_version = dict(id=1, version="37", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("36", "37")

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if db_version_dict["version"] == "37":
        database_connection.query("ALTER TABLE 'version' ADD COLUMN 'notes' TEXT")
        database_connection.query(
            """
            UPDATE 'version' SET notes='administrative table duplicates folders table. Use folders table for all operations. administrative table deprecated.'
        """
        )

        update_version = dict(id=1, version="38", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("37", "38")

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if db_version_dict["version"] == "38":
        # Add edi_format field to both folders and administrative tables
        database_connection.query("ALTER TABLE 'folders' ADD COLUMN 'edi_format' TEXT")
        database_connection.query('UPDATE "folders" SET "edi_format" = "default"')

        database_connection.query(
            "ALTER TABLE 'administrative' ADD COLUMN 'edi_format' TEXT"
        )
        database_connection.query(
            'UPDATE "administrative" SET "edi_format" = "default"'
        )

        update_version = dict(id=1, version="39", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("38", "39")

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if db_version_dict["version"] == "39":
        conn = database_connection.raw_connection

        def _rebuild_table_with_pk(table_name) -> None:
            """Atomically rebuild *table_name* to add INTEGER PRIMARY KEY id.

            Wrapped in an explicit BEGIN/COMMIT so that if anything fails after
            the old table has been dropped but before the rename completes, the
            whole operation is rolled back and no data is lost.
            """
            cursor = conn.cursor()
            quoted_table = _quote_identifier(table_name)
            cursor.execute(f"PRAGMA table_info({quoted_table})")
            existing = [row[1] for row in cursor.fetchall()]
            if "id" in existing:
                return  # already has primary key – nothing to do

            cursor.execute(f"PRAGMA table_info({quoted_table})")
            old_columns = [(row[1], row[2]) for row in cursor.fetchall()]

            col_defs = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]
            for col_name, col_type in old_columns:
                col_defs.append(f"{_quote_identifier(col_name)} {col_type}")
            columns_sql = ", ".join(col_defs)

            old_cols = ", ".join([_quote_identifier(c[0]) for c in old_columns])
            new_table = _quote_identifier(f"{table_name}_new")

            cursor.execute("BEGIN")
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {new_table}")
                cursor.execute(f"CREATE TABLE {new_table} ({columns_sql})")
                cursor.execute(
                    f"INSERT INTO {new_table} ({old_cols}) SELECT {old_cols} FROM {quoted_table}"
                )
                cursor.execute(f"DROP TABLE {quoted_table}")
                cursor.execute(f"ALTER TABLE {new_table} RENAME TO {quoted_table}")
                cursor.execute("COMMIT")
            except Exception:
                cursor.execute("ROLLBACK")
                raise

        _rebuild_table_with_pk("folders")
        _rebuild_table_with_pk("administrative")

        update_version = dict(id=1, version="40", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("39", "40")

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if str(db_version_dict["version"]) == "40":
        # Add missing backend columns to folders and administrative tables
        # without overwriting real values already present in legacy databases.
        def _existing_columns(table_name):
            cursor = database_connection.raw_connection.cursor()
            quoted_table = _quote_identifier(table_name)
            cursor.execute(f"PRAGMA table_info({quoted_table})")
            return {row[1] for row in cursor.fetchall()}

        def _ensure_column(table_name, column_name, sql_type, default_sql) -> None:
            if column_name in _existing_columns(table_name):
                return
            quoted_table = _quote_identifier(table_name)
            quoted_column = _quote_identifier(column_name)
            database_connection.query(
                f"ALTER TABLE {quoted_table} ADD COLUMN {quoted_column} {sql_type}"
            )
            database_connection.query(
                f"UPDATE {quoted_table} SET {quoted_column} = {default_sql}"
            )

        for table_name in ("folders", "administrative"):
            _ensure_column(table_name, "process_backend_email", "INTEGER", "0")
            _ensure_column(table_name, "process_backend_ftp", "INTEGER", "0")
            _ensure_column(table_name, "email_to", "TEXT", "''")
            _ensure_column(table_name, "ftp_server", "TEXT", "''")
            _ensure_column(table_name, "ftp_port", "INTEGER", "21")
            _ensure_column(table_name, "ftp_folder", "TEXT", "''")
            _ensure_column(table_name, "ftp_username", "TEXT", "''")
            _ensure_column(table_name, "ftp_password", "TEXT", "''")

        update_version = dict(id=1, version="41", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("40", "41")

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if db_version_dict["version"] == "41":
        # Normalize string boolean values (True/False) to integer values (1/0)
        boolean_fields = [
            "folder_is_active",
            "process_edi",
            "calculate_upc_check_digit",
            "include_a_records",
            "include_c_records",
            "include_headers",
            "filter_ampersand",
            "pad_a_records",
            "tweak_edi",
            "split_edi",
            "force_edi_validation",
            "append_a_records",
            "force_txt_file_ext",
            "prepend_date_files",
            "override_upc_bool",
            "split_edi_include_invoices",
            "split_edi_include_credits",
            "process_backend_copy",
            "process_edi_output",
            "process_backend_email",
            "process_backend_ftp",
        ]

        # Normalize folders table
        for field in boolean_fields:
            try:
                quoted_field = _quote_identifier(field)
                # Replace True with 1
                database_connection.query(
                    f"UPDATE folders SET {quoted_field} = 1 WHERE {quoted_field} = 'True'"
                )
                # Replace False with 0
                database_connection.query(
                    f"UPDATE folders SET {quoted_field} = 0 WHERE {quoted_field} = 'False'"
                )
            except Exception as e:
                print(f"Error normalizing field {field} in folders: {e}")
                # Skip fields that don't exist in this version

        # Normalize administrative table
        for field in boolean_fields:
            try:
                quoted_field = _quote_identifier(field)
                # Replace True with 1
                database_connection.query(
                    f"UPDATE administrative SET {quoted_field} = 1 WHERE {quoted_field} = 'True'"
                )
                # Replace False with 0
                database_connection.query(
                    f"UPDATE administrative SET {quoted_field} = 0 WHERE {quoted_field} = 'False'"
                )
            except Exception as e:
                print(f"Error normalizing field {field} in administrative: {e}")
                # Skip fields that don't exist in this version

        # Normalize settings table
        try:
            database_connection.query(
                "UPDATE settings SET enable_email = 1 WHERE enable_email = 'True'"
            )
            database_connection.query(
                "UPDATE settings SET enable_email = 0 WHERE enable_email = 'False'"
            )
            database_connection.query(
                "UPDATE settings SET enable_interval_backups = 1 WHERE enable_interval_backups = 'True'"
            )
            database_connection.query(
                "UPDATE settings SET enable_interval_backups = 0 WHERE enable_interval_backups = 'False'"
            )
        except Exception as e:
            print(f"Error normalizing settings table: {e}")

        update_version = dict(id=1, version="42", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("41", "42")

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if db_version_dict["version"] == "42":
        try:
            folders_table = database_connection["folders"]
            for folder in folders_table.all():
                folder_name = folder.get("folder_name")
                if folder_name and "\\" in folder_name:
                    normalized = folder_name.replace("\\", "/")
                    folders_table.update(
                        {"id": folder["id"], "folder_name": normalized}, ["id"]
                    )
        except Exception as e:
            print(f"Error normalizing folder paths: {e}")

        update_version = dict(id=1, version="43", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("42", "43")

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if db_version_dict["version"] == "43":
        # Add upc_target_length (default 11) and upc_padding_pattern to folders
        # and settings tables.  Both columns were present in the schema definition
        # but were never added via a migration, so existing upgraded databases are
        # missing them, causing sqlite3.OperationalError on folder save.
        cursor = database_connection.raw_connection.cursor()
        for table in ("folders", "settings"):
            try:
                cursor.execute(
                    f"ALTER TABLE '{table}' ADD COLUMN 'upc_target_length' INTEGER DEFAULT 11"
                )
            except Exception:
                pass  # column already exists
            try:
                cursor.execute(
                    f"ALTER TABLE '{table}' ADD COLUMN 'upc_padding_pattern' TEXT"
                )
            except Exception:
                pass  # column already exists
        database_connection.raw_connection.commit()

        update_version = dict(id=1, version="44", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("43", "44")

    db_version_dict = db_version.find_one(id=1)
    if db_version_dict and str(db_version_dict["version"]) == "44":
        # Make convert_to_format the single source of truth for conversion mode.
        #
        # tweak_edi is a now-deprecated flag that formerly ran a separate "tweaks"
        # post-processing step.  Rules for retiring it:
        #
        #   • tweak_edi=1 + process_edi=1/NULL + convert_to_format non-empty:
        #     Stored format IS the intended target.  Honour it: ensure process_edi=1
        #     so conversion runs, then clear tweak_edi.
        #
        #   • tweak_edi=1 + process_edi=1/NULL + convert_to_format empty/null:
        #     The folder wanted EDI tweaks.  Set convert_to_format='tweaks',
        #     ensure process_edi=1, and clear tweak_edi.
        #
        #   • tweak_edi=1 + process_edi=0 (explicitly disabled):
        #     The user disabled EDI processing.  Respect that choice: only clear
        #     the deprecated tweak_edi flag; do NOT change process_edi or
        #     convert_to_format.  The folder continues to pass through files.
        cursor = database_connection.raw_connection.cursor()

        for table in ("folders", "administrative"):
            try:
                # Case A (enabled): real format already stored and processing was
                # enabled or unset – honour the stored format.
                # Do NOT touch folders where process_edi was explicitly set to 0;
                # those folders intentionally disabled conversion and must keep
                # passing through.
                cursor.execute(
                    f"""
                    UPDATE {table}
                    SET process_edi = 1,
                        tweak_edi   = 0
                    WHERE tweak_edi = 1
                      AND convert_to_format IS NOT NULL
                      AND convert_to_format != ''
                      AND (process_edi IS NULL OR process_edi != 0)
                """
                )
            except Exception:
                pass  # Column may not exist in older schemas

            try:
                # Case A (disabled): real format stored but processing was
                # explicitly off.  Only retire the deprecated tweak_edi flag;
                # leave process_edi=0 and convert_to_format untouched.
                cursor.execute(
                    f"""
                    UPDATE {table}
                    SET tweak_edi = 0
                    WHERE tweak_edi = 1
                      AND convert_to_format IS NOT NULL
                      AND convert_to_format != ''
                      AND process_edi = 0
                """
                )
            except Exception:
                pass  # Column may not exist in older schemas

            try:
                # Case B (enabled): no format stored – the intent was EDI tweaks.
                # Only promote when processing was enabled or unset.
                cursor.execute(
                    f"""
                    UPDATE {table}
                    SET convert_to_format = 'tweaks',
                        process_edi       = 1,
                        tweak_edi         = 0
                    WHERE tweak_edi = 1
                      AND (convert_to_format IS NULL OR convert_to_format = '')
                      AND (process_edi IS NULL OR process_edi != 0)
                """
                )
            except Exception:
                pass  # Column may not exist in older schemas

            try:
                # Case B (disabled): no format stored and processing was
                # explicitly off.  Only retire the deprecated tweak_edi flag.
                cursor.execute(
                    f"""
                    UPDATE {table}
                    SET tweak_edi = 0
                    WHERE tweak_edi = 1
                      AND (convert_to_format IS NULL OR convert_to_format = '')
                      AND process_edi = 0
                """
                )
            except Exception:
                pass  # Column may not exist in older schemas

        database_connection.raw_connection.commit()

        update_version = dict(id=1, version="45", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("44", "45")

    db_version_dict = db_version.find_one(id=1)
    if db_version_dict and str(db_version_dict["version"]) == "45":
        cursor = database_connection.raw_connection.cursor()

        try:
            cursor.execute(
                """
                UPDATE folders
                SET convert_to_format = 'tweaks'
                WHERE tweak_edi = 1
                AND (convert_to_format IS NULL OR convert_to_format = '')
            """
            )
        except Exception:
            pass

        try:
            cursor.execute(
                """
                UPDATE administrative
                SET convert_to_format = 'tweaks'
                WHERE tweak_edi = 1
                AND (convert_to_format IS NULL OR convert_to_format = '')
            """
            )
        except Exception:
            pass

        try:
            cursor.execute("UPDATE folders SET tweak_edi = 0")
        except Exception:
            pass

        try:
            cursor.execute("UPDATE administrative SET tweak_edi = 0")
        except Exception:
            pass

        database_connection.raw_connection.commit()

        update_version = dict(id=1, version="46", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("45", "46")

    db_version_dict = db_version.find_one(id=1)
    if db_version_dict and str(db_version_dict["version"]) == "46":
        # Repair convert_to_format values corrupted by the original v44→v45
        # migration (commit 8d86e0884).  That migration cleared convert_to_format
        # for every folder with tweak_edi=1 regardless of whether process_edi was
        # explicitly 0 (disabled).  A subsequent v45→v46 step then stamped them
        # all with 'tweaks', leaving disabled folders (process_edi='0') with the
        # nonsensical format 'tweaks'.
        #
        # The pre-migration backup the app creates before running migrations
        # contains the original values.  We locate the most recent backup and
        # restore convert_to_format for every affected row.
        import glob
        import sqlite3 as _sqlite3

        cursor = database_connection.raw_connection.cursor()

        backup_files = []
        if config_folder:
            backup_pattern = os.path.join(config_folder, "folders.db.bak-*")
            backup_files = sorted(glob.glob(backup_pattern))

        if backup_files:
            backup_path = backup_files[-1]
            try:
                back_conn = _sqlite3.connect(backup_path)
                back_conn.row_factory = _sqlite3.Row

                # Identify the corrupted rows in production.
                # Signature: process_edi='0' AND convert_to_format='tweaks'
                # (disabled folders should never legitimately be 'tweaks')
                affected = {
                    r[0]
                    for r in cursor.execute(
                        "SELECT id FROM folders "
                        "WHERE process_edi = '0' AND convert_to_format = 'tweaks'"
                    ).fetchall()
                }

                fixed = 0
                for row in back_conn.execute(
                    "SELECT id, convert_to_format FROM folders"
                ):
                    if row["id"] in affected:
                        cursor.execute(
                            "UPDATE folders SET convert_to_format = ? WHERE id = ?",
                            (row["convert_to_format"] or "", row["id"]),
                        )
                        fixed += 1

                back_conn.close()
                database_connection.raw_connection.commit()
                print(
                    f"  Repaired {fixed} folders using backup "
                    f"{os.path.basename(backup_path)}"
                )
            except Exception as e:
                print(f"  Warning: could not repair from backup: {e}")
        else:
            print(
                "  Warning: no backup file found; folders with "
                "process_edi='0' and convert_to_format='tweaks' may have "
                "incorrect conversion targets (manual review recommended)."
            )

        update_version = dict(id=1, version="47", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("46", "47")

    db_version_dict = db_version.find_one(id=1)
    if db_version_dict and str(db_version_dict["version"]) == "47":
        # Fix folders where process_edi is explicitly False/0 but a
        # convert_to_format is configured.  This state is contradictory: the UI
        # displays the EDI checkbox as enabled whenever convert_to_format is
        # non-empty (edit_folders_dialog.py), so users believe processing is on,
        # but the orchestrator respects the explicit False and skips conversion
        # entirely.  The intended state is process_edi=True for any folder that
        # has a conversion target set.
        #
        # We treat "do_nothing" as a legitimate disabled-conversion format and
        # leave those folders alone.
        cursor = database_connection.raw_connection.cursor()

        try:
            cursor.execute(
                """
                UPDATE folders
                SET process_edi = 1
                WHERE (
                    process_edi = 0
                    OR process_edi = 'False'
                    OR process_edi = 'false'
                )
                AND convert_to_format IS NOT NULL
                AND TRIM(convert_to_format) != ''
                AND LOWER(TRIM(convert_to_format)) != 'do_nothing'
                """
            )
            fixed = cursor.rowcount
        except Exception as e:
            fixed = 0
            print(f"  Warning: v48 migration encountered an error: {e}")

        database_connection.raw_connection.commit()
        print(
            f"  Repaired {fixed} folder(s) with process_edi=False "
            "but a conversion target configured."
        )

        update_version = dict(id=1, version="48", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("47", "48")

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    def _existing_columns(table_name):
        cursor = database_connection.raw_connection.cursor()
        quoted_table = _quote_identifier(table_name)
        cursor.execute(f"PRAGMA table_info({quoted_table})")
        return {row[1] for row in cursor.fetchall()}

    def _ensure_column(table_name, column_name, sql_type, default_sql) -> None:
        if column_name in _existing_columns(table_name):
            return
        quoted_table = _quote_identifier(table_name)
        quoted_column = _quote_identifier(column_name)
        conn = database_connection.raw_connection
        try:
            conn.execute(
                f"ALTER TABLE {quoted_table} ADD COLUMN {quoted_column} {sql_type}"
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to add column {quoted_column} to table {quoted_table}: {e}"
            ) from e
        try:
            conn.execute(f"UPDATE {quoted_table} SET {quoted_column} = {default_sql}")
        except Exception as e:
            raise RuntimeError(
                f"Failed to set default value for column {quoted_column} in table {quoted_table}: {e}"
            ) from e

    if str(db_version_dict["version"]) == "48":
        update_version = dict(id=1, version="49", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("48", "49")

    db_version_dict = db_version.find_one(id=1)

    if str(db_version_dict["version"]) == "49":
        for table_name in ("folders", "administrative"):
            _ensure_column(table_name, "process_backend_http", "INTEGER", "0")

        update_version = dict(id=1, version="50", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("49", "50")
