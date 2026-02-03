"""
Database schema creation using sqlite3.

Framework-agnostic replacement for the Qt-based create_database.py.
"""

import datetime
import os
import sqlite3


def create_database(
    database_version: str,
    database_path: str,
    config_folder: str,
    running_platform: str,
) -> None:
    """Create initial database schema."""
    try:
        connection = sqlite3.connect(database_path)
    except sqlite3.OperationalError as e:
        raise RuntimeError(f"Failed to open database: {e}") from e
    connection.execute("PRAGMA foreign_keys = ON")
    cursor = connection.cursor()

    cursor.execute(
        "CREATE TABLE version (id INTEGER PRIMARY KEY, version TEXT, os TEXT)"
    )
    cursor.execute(
        "INSERT INTO version (version, os) VALUES (?, ?)",
        (database_version, running_platform),
    )

    initial_db_dict = {
        "folder_is_active": 1,  # Native boolean: 1=True, 0=False
        "copy_to_directory": None,
        "process_edi": 0,  # Native boolean
        "convert_to_format": "csv",
        "calculate_upc_check_digit": 0,  # Native boolean
        "include_a_records": 0,  # Native boolean
        "include_c_records": 0,  # Native boolean
        "include_headers": 0,  # Native boolean
        "filter_ampersand": 0,  # Native boolean
        "tweak_edi": False,
        "pad_a_records": 0,  # Native boolean
        "a_record_padding": "",
        "a_record_padding_length": 6,
        "invoice_date_custom_format_string": "%Y%m%d",
        "invoice_date_custom_format": False,
        "reporting_email": "",
        "folder_name": "template",
        "alias": "",
        "report_email_destination": "",
        "process_backend_copy": False,
        "process_backend_ftp": False,
        "process_backend_email": False,
        "ftp_server": "",
        "ftp_folder": "/",
        "ftp_username": "",
        "ftp_password": "",
        "email_to": "",
        "logs_directory": os.path.join(config_folder, "run_logs"),
        "errors_folder": os.path.join(config_folder, "errors"),
        "enable_reporting": 0,  # Native boolean
        "report_printing_fallback": 0,  # Native boolean
        "ftp_port": 21,
        "email_subject_line": "",
        "single_add_folder_prior": os.path.expanduser("~"),
        "batch_add_folder_prior": os.path.expanduser("~"),
        "export_processed_folder_prior": os.path.expanduser("~"),
        "report_edi_errors": False,
        "split_edi": False,
        "split_edi_include_invoices": True,
        "split_edi_include_credits": True,
        "force_edi_validation": False,
        "append_a_records": 0,  # Native boolean
        "a_record_append_text": "",
        "force_txt_file_ext": 0,  # Native boolean
        "invoice_date_offset": 0,
        "retail_uom": False,
        "include_item_numbers": False,
        "include_item_description": False,
        "simple_csv_sort_order": "upc_number,qty_of_units,unit_cost,description,vendor_item",
        "split_prepaid_sales_tax_crec": False,
        "estore_store_number": 0,
        "estore_Vendor_OId": 0,
        "estore_vendor_NameVendorOID": "replaceme",
        "estore_c_record_OID": "",
        "prepend_date_files": False,
        "rename_file": "",
        "override_upc_bool": False,
        "override_upc_level": 1,
        "override_upc_category_filter": "ALL",
        "fintech_division_id": 0,
        "plugin_config": None,
        "edi_format": "default",
        "created_at": datetime.datetime.now().isoformat(),
        "updated_at": datetime.datetime.now().isoformat(),
    }

    def get_sql_type(value):
        if isinstance(value, str):
            return "TEXT"
        elif isinstance(value, (int, bool)):
            return "INTEGER"
        return "TEXT"

    table_columns = ", ".join(
        [f'"id" INTEGER PRIMARY KEY AUTOINCREMENT'] + [f'"{k}" {get_sql_type(v)}' for k, v in initial_db_dict.items()]
    )

    cursor.execute(f"CREATE TABLE administrative ({table_columns})")
    # Create folders table with id column first, then copy data
    cursor.execute(f"CREATE TABLE folders ({table_columns})")

    def insert_dict(table_name, data_dict):
        columns = ", ".join([f'"{k}"' for k in data_dict.keys()])
        placeholders = ", ".join(["?"] * len(data_dict))
        cursor.execute(
            f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})",
            tuple(data_dict.values()),
        )

    insert_dict("administrative", initial_db_dict)
    insert_dict("folders", initial_db_dict)
    cursor.execute('DELETE FROM "folders"')

    settings_dict = {
        "enable_email": False,
        "email_address": "",
        "email_username": "",
        "email_password": "",
        "email_smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "backup_counter": 0,
        "backup_counter_maximum": 200,
        "enable_interval_backups": True,
        "odbc_driver": "Select ODBC Driver...",
        "as400_address": "",
        "as400_username": "",
        "as400_password": "",
        "created_at": datetime.datetime.now().isoformat(),
        "updated_at": datetime.datetime.now().isoformat(),
    }

    settings_columns = ", ".join(
        [f'"{k}" {get_sql_type(v)}' for k, v in settings_dict.items()]
    )

    cursor.execute(f"CREATE TABLE settings ({settings_columns})")
    insert_dict("settings", settings_dict)

    cursor.execute(
        """CREATE TABLE processed_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folder_id INTEGER,
            filename TEXT,
            original_path TEXT,
            processed_path TEXT,
            status TEXT,
            error_message TEXT,
            convert_format TEXT,
            sent_to TEXT,
            created_at TEXT,
            processed_at TEXT,
            file_name TEXT,
            file_checksum TEXT,
            copy_destination TEXT,
            ftp_destination TEXT,
            email_destination TEXT,
            resend_flag INTEGER
        )"""
    )

    cursor.execute(
        "CREATE TABLE emails_to_send (id INTEGER PRIMARY KEY AUTOINCREMENT, log TEXT)"
    )
    cursor.execute(
        "CREATE TABLE working_batch_emails_to_send (id INTEGER PRIMARY KEY AUTOINCREMENT, log TEXT)"
    )
    cursor.execute(
        "CREATE TABLE sent_emails_removal_queue (id INTEGER PRIMARY KEY AUTOINCREMENT, log TEXT)"
    )

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_folders_active ON folders(folder_is_active)"
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_folders_alias ON folders(alias)")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_processed_files_folder ON processed_files(folder_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_processed_files_status ON processed_files(status)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_processed_files_created ON processed_files(created_at)"
    )

    connection.commit()
    connection.close()
