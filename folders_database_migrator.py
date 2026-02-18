import os


def _log_migration_step(from_version, to_version):
    """Log migration step progress."""
    print(f"  Migrating: v{from_version} → v{to_version}")


def _add_column_safe(database_connection, table_name, column_name, default_value):
    """Add a column to a table if it doesn't already exist.
    
    Args:
        database_connection: The dataset database connection
        table_name: Name of the table to alter
        column_name: Name of the column to add
        default_value: SQL expression for the default value (e.g., '"ALL"', '0', '""')
    """
    try:
        database_connection.query(
            f"ALTER TABLE '{table_name}' ADD COLUMN '{column_name}'"
        )
        database_connection.query(
            f'UPDATE "{table_name}" SET "{column_name}" = {default_value}'
        )
    except Exception:
        pass


def upgrade_database(
    database_connection, config_folder, running_platform, target_version=None
):
    db_version = database_connection["version"]
    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    starting_version = db_version_dict["version"]

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    if db_version_dict["version"] == "5":
        folders_table = database_connection["folders"]
        folders_table.create_column("convert_to_format", "String")
        convert_to_csv_list = folders_table.find(process_edi="True")
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
        for line in processed_table:
            line["resend_flag"] = False
            processed_table.update(line, ["id"])

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
        administrative_section_update_dict["tweak_edi"] = False
        administrative_section.update(administrative_section_update_dict, ["id"])

        folders_table.create_column("tweak_edi", "Boolean")
        for line in folders_table:
            if line["pad_a_records"] == "False":
                line["tweak_edi"] = False
                folders_table.update(line, ["id"])
            else:
                line["tweak_edi"] = True
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
        administrative_section_update_dict = dict(id=1, report_edi_errors=False)
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
        administrative_section_update_dict["split_edi"] = False
        administrative_section.update(administrative_section_update_dict, ["id"])

        folders_table.create_column("split_edi", "Boolean")
        for line in folders_table.all():
            line["split_edi"] = False
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
        database_connection.query("""
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
        """)

        settings_table = database_connection["settings"]
        administrative_section_dict = administrative_section.find_one(id=1)

        email_state = (
            1 if administrative_section_dict.get("enable_reporting") == "True" else 0
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
            'update "folders" set "convert_to_format"="", "process_edi"="False" where "convert_to_format"="insight"'
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
        database_connection.query('UPDATE "folders" SET "append_a_records" = "False"')
        database_connection.query(
            "alter table 'folders' add column 'a_record_append_text'"
        )
        database_connection.query('UPDATE "folders" SET "a_record_append_text" = ""')
        database_connection.query(
            "alter table 'folders' add column 'force_txt_file_ext'"
        )
        database_connection.query('UPDATE "folders" SET "force_txt_file_ext" = "False"')
        database_connection.query(
            "alter table 'administrative' add column 'append_a_records'"
        )
        database_connection.query(
            'UPDATE "administrative" SET "append_a_records" = "False"'
        )
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
            'UPDATE "administrative" SET "force_txt_file_ext" = "False"'
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
            pass
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
                'UPDATE "folders" SET "simple_csv_sort_order" = "upc_number,qty_of_units,unit_cost,description,vendor_item"'
            )
        except RuntimeError:
            pass
        database_connection.query(
            "alter table 'administrative' add column 'simple_csv_sort_order'"
        )
        database_connection.query(
            'UPDATE "administrative" SET "simple_csv_sort_order" = "upc_number,qty_of_units,unit_cost,description,vendor_item"'
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
            pass
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
                'UPDATE "folders" SET "estore_vendor_NameVendorOID" = "replaceme"'
            )
        except RuntimeError:
            pass
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
            "UPDATE 'administrative' SET 'estore_vendor_NameVendorOID' = 'replaceme'"
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
        database_connection.query('UPDATE "folders" set "override_upc_bool"=False')
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
            'update "folders" set "override_upc_bool"=True, "override_upc_level"=1 where "force_each_upc"=True'
        )
        database_connection.query(
            "alter table 'administrative' add column 'override_upc_bool'"
        )
        database_connection.query(
            'UPDATE "administrative" set "override_upc_bool"=False'
        )
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
        database_connection.query(
            'UPDATE "folders" set "split_edi_include_invoices"=True'
        )
        database_connection.query(
            "alter table 'folders' add column 'split_edi_include_credits'"
        )
        database_connection.query(
            'UPDATE "folders" set "split_edi_include_credits"=True'
        )
        database_connection.query(
            "alter table 'administrative' add column 'split_edi_include_invoices'"
        )
        database_connection.query(
            'UPDATE "administrative" set "split_edi_include_invoices"=True'
        )
        database_connection.query(
            "alter table 'administrative' add column 'split_edi_include_credits'"
        )
        database_connection.query(
            'UPDATE "administrative" set "split_edi_include_credits"=True'
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
        # v32→v33: Add category filter columns and plugin config column.
        # This replaces the old migration that was split across two different code paths:
        # - Original (commit 9446b3de): added split_edi_filter_categories/mode
        # - Later refactor: added plugin_config via external migrations/ module
        # We now add all three columns, tolerating pre-existing columns.
        _add_column_safe(database_connection, "folders", "split_edi_filter_categories", '"ALL"')
        _add_column_safe(database_connection, "folders", "split_edi_filter_mode", '"include"')
        _add_column_safe(database_connection, "administrative", "split_edi_filter_categories", '"ALL"')
        _add_column_safe(database_connection, "administrative", "split_edi_filter_mode", '"include"')
        _add_column_safe(database_connection, "folders", "plugin_config", '""')
        _add_column_safe(database_connection, "administrative", "plugin_config", '""')

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
        # Schema normalization for v33 databases.
        # Old v33 databases (from commit 9446b3de7e) have split_edi_filter_categories
        # and split_edi_filter_mode but lack plugin_config. Newer v33 databases have
        # plugin_config but may lack the filter columns. Ensure all columns exist
        # before proceeding to v33→v34.
        _add_column_safe(database_connection, "folders", "split_edi_filter_categories", '"ALL"')
        _add_column_safe(database_connection, "folders", "split_edi_filter_mode", '"include"')
        _add_column_safe(database_connection, "administrative", "split_edi_filter_categories", '"ALL"')
        _add_column_safe(database_connection, "administrative", "split_edi_filter_mode", '"include"')
        _add_column_safe(database_connection, "folders", "plugin_config", '""')
        _add_column_safe(database_connection, "administrative", "plugin_config", '""')

        import datetime

        now = datetime.datetime.now().isoformat()

        database_connection.query("ALTER TABLE 'folders' ADD COLUMN 'created_at' TEXT")
        database_connection.query("ALTER TABLE 'folders' ADD COLUMN 'updated_at' TEXT")
        database_connection.query(
            f"UPDATE 'folders' SET created_at='{now}', updated_at='{now}'"
        )

        database_connection.query(
            "ALTER TABLE 'administrative' ADD COLUMN 'created_at' TEXT"
        )
        database_connection.query(
            "ALTER TABLE 'administrative' ADD COLUMN 'updated_at' TEXT"
        )
        database_connection.query(
            f"UPDATE 'administrative' SET created_at='{now}', updated_at='{now}'"
        )

        database_connection.query(
            "ALTER TABLE 'processed_files' ADD COLUMN 'created_at' TEXT"
        )
        database_connection.query(
            "ALTER TABLE 'processed_files' ADD COLUMN 'processed_at' TEXT"
        )
        database_connection.query(f"UPDATE 'processed_files' SET created_at='{now}'")

        database_connection.query("ALTER TABLE 'settings' ADD COLUMN 'created_at' TEXT")
        database_connection.query("ALTER TABLE 'settings' ADD COLUMN 'updated_at' TEXT")
        database_connection.query(
            f"UPDATE 'settings' SET created_at='{now}', updated_at='{now}'"
        )

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
        database_connection.query(
            "ALTER TABLE 'processed_files' ADD COLUMN 'filename' TEXT"
        )
        database_connection.query(
            "ALTER TABLE 'processed_files' ADD COLUMN 'original_path' TEXT"
        )
        database_connection.query(
            "ALTER TABLE 'processed_files' ADD COLUMN 'processed_path' TEXT"
        )
        database_connection.query(
            "ALTER TABLE 'processed_files' ADD COLUMN 'status' TEXT"
        )
        database_connection.query(
            "ALTER TABLE 'processed_files' ADD COLUMN 'error_message' TEXT"
        )
        database_connection.query(
            "ALTER TABLE 'processed_files' ADD COLUMN 'convert_format' TEXT"
        )
        database_connection.query(
            "ALTER TABLE 'processed_files' ADD COLUMN 'sent_to' TEXT"
        )

        database_connection.query(
            "UPDATE 'processed_files' SET filename=file_name, status='processed' WHERE file_name IS NOT NULL"
        )

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
        database_connection.query(
            "CREATE INDEX IF NOT EXISTS idx_folders_active ON folders(folder_is_active)"
        )
        database_connection.query(
            "CREATE INDEX IF NOT EXISTS idx_folders_alias ON folders(alias)"
        )
        database_connection.query(
            "CREATE INDEX IF NOT EXISTS idx_processed_files_folder ON processed_files(folder_id)"
        )
        database_connection.query(
            "CREATE INDEX IF NOT EXISTS idx_processed_files_status ON processed_files(status)"
        )
        database_connection.query(
            "CREATE INDEX IF NOT EXISTS idx_processed_files_created ON processed_files(created_at)"
        )

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
        database_connection.query("""
            UPDATE 'version' SET notes='administrative table duplicates folders table. Use folders table for all operations. administrative table deprecated.'
        """)

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
        columns = [row['name'] for row in database_connection.query("PRAGMA table_info(folders)")]

        if "id" not in columns:
            old_columns = [(row['name'], row['type']) for row in database_connection.query("PRAGMA table_info(folders)")]

            col_defs = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]
            for col_name, col_type in old_columns:
                col_defs.append(f'"{col_name}" {col_type}')

            columns_sql = ", ".join(col_defs)

            database_connection.query(f"CREATE TABLE folders_new ({columns_sql})")

            old_cols = ", ".join([f'"{c[0]}"' for c in old_columns])
            database_connection.query(f"INSERT INTO folders_new ({old_cols}) SELECT {old_cols} FROM folders")

            database_connection.query("DROP TABLE folders")
            database_connection.query("ALTER TABLE folders_new RENAME TO folders")

        admin_columns = [row['name'] for row in database_connection.query("PRAGMA table_info(administrative)")]

        if "id" not in admin_columns:
            old_columns = [(row['name'], row['type']) for row in database_connection.query("PRAGMA table_info(administrative)")]

            col_defs = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]
            for col_name, col_type in old_columns:
                col_defs.append(f'"{col_name}" {col_type}')

            columns_sql = ", ".join(col_defs)

            database_connection.query(f"CREATE TABLE administrative_new ({columns_sql})")

            old_cols = ", ".join([f'"{c[0]}"' for c in old_columns])
            database_connection.query(f"INSERT INTO administrative_new ({old_cols}) SELECT {old_cols} FROM administrative")

            database_connection.query("DROP TABLE administrative")
            database_connection.query("ALTER TABLE administrative_new RENAME TO administrative")

        update_version = dict(id=1, version="40", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("39", "40")

    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    # Migration 40 → 41: Convert string booleans to native INTEGER (0/1)
    # This migration normalizes boolean storage across all tables.
    # String booleans ("True"/"False") are converted to INTEGER (1/0).
    if db_version_dict["version"] == "40":
        # List of boolean columns that need migration
        # These columns may contain "True"/"False" strings and need to be converted to 0/1
        boolean_columns = [
            "folder_is_active",
            "process_edi",
            "calculate_upc_check_digit",
            "include_a_records",
            "include_c_records",
            "include_headers",
            "filter_ampersand",
            "pad_a_records",
            "invoice_date_custom_format",
            "append_a_records",
            "force_txt_file_ext",
            "enable_reporting",
            "report_printing_fallback",
        ]

        # Migrate folders table
        for col in boolean_columns:
            try:
                database_connection.query(f"""
                    UPDATE folders
                    SET "{col}" = CASE
                        WHEN "{col}" = 'True' THEN 1
                        WHEN "{col}" = 'true' THEN 1
                        WHEN "{col}" = '1' THEN 1
                        WHEN "{col}" = 1 THEN 1
                        WHEN "{col}" IS NULL THEN 0
                        ELSE 0
                    END
                    WHERE "{col}" IN ('True', 'False', 'true', 'false', '0', '1')
                       OR typeof("{col}") = 'text'
                """)
            except Exception as e:
                # Column might not exist in this table; log and continue
                _log_migration_step(f"skip-{col}", f"folders-{col}-{str(e)}")

        # Migrate administrative table
        for col in boolean_columns:
            try:
                database_connection.query(f"""
                    UPDATE administrative
                    SET "{col}" = CASE
                        WHEN "{col}" = 'True' THEN 1
                        WHEN "{col}" = 'true' THEN 1
                        WHEN "{col}" = '1' THEN 1
                        WHEN "{col}" = 1 THEN 1
                        WHEN "{col}" IS NULL THEN 0
                        ELSE 0
                    END
                    WHERE "{col}" IN ('True', 'False', 'true', 'false', '0', '1')
                       OR typeof("{col}") = 'text'
                """)
            except Exception as e:
                # Column might not exist in this table; log and continue
                _log_migration_step(f"skip-{col}", f"admin-{col}-{str(e)}")

        # Migrate oversight/administrative table reporting-related fields
        oversight_bool_columns = ["enable_reporting", "report_printing_fallback"]
        for col in oversight_bool_columns:
            try:
                database_connection.query(f"""
                    UPDATE administrative
                    SET "{col}" = CASE
                        WHEN "{col}" = 'True' THEN 1
                        WHEN "{col}" = 'true' THEN 1
                        WHEN "{col}" = '1' THEN 1
                        WHEN "{col}" = 1 THEN 1
                        WHEN "{col}" IS NULL THEN 0
                        ELSE 0
                    END
                """)
            except Exception as e:
                _log_migration_step(f"skip-oversight-{col}", str(e))

        update_version = dict(id=1, version="41", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("40", "41")
