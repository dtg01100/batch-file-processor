import os

from PyQt6.QtSql import QSqlDatabase, QSqlQuery
import datetime


def do(database_version, database_path, config_folder, running_platform):
    db = QSqlDatabase.addDatabase("QSQLITE")
    db.setDatabaseName(database_path)

    if not db.open():
        raise RuntimeError(f"Failed to open database: {db.lastError().text()}")

    from PyQt6.QtSql import QSqlQuery as QQuery

    pragma_query = QQuery(db)
    pragma_query.exec("PRAGMA foreign_keys = ON")

    query = QSqlQuery(db)

    if not query.exec(
        "CREATE TABLE version (id INTEGER PRIMARY KEY, version TEXT, os TEXT)"
    ):
        raise RuntimeError(
            f"Failed to create version table: {query.lastError().text()}"
        )

    query.prepare("INSERT INTO version (version, os) VALUES (?, ?)")
    query.addBindValue(database_version)
    query.addBindValue(running_platform)
    if not query.exec():
        raise RuntimeError(f"Failed to insert version: {query.lastError().text()}")

    initial_db_dict = {
        "folder_is_active": "False",
        "copy_to_directory": None,
        "process_edi": "False",
        "convert_to_format": "csv",
        "calculate_upc_check_digit": "False",
        "include_a_records": "False",
        "include_c_records": "False",
        "include_headers": "False",
        "filter_ampersand": "False",
        "tweak_edi": False,
        "pad_a_records": "False",
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
        "enable_reporting": "False",
        "report_printing_fallback": "False",
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
        "append_a_records": "False",
        "a_record_append_text": "",
        "force_txt_file_ext": "False",
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

    table_columns = ", ".join(
        [
            f'"{k}" {"TEXT" if isinstance(v, str) else "INTEGER" if isinstance(v, (int, bool)) else "TEXT"}'
            for k, v in initial_db_dict.items()
        ]
    )

    if not query.exec(f"CREATE TABLE administrative ({table_columns})"):
        raise RuntimeError(
            f"Failed to create administrative table: {query.lastError().text()}"
        )

    if not query.exec(f"CREATE TABLE folders ({table_columns})"):
        raise RuntimeError(
            f"Failed to create folders table: {query.lastError().text()}"
        )

    def insert_dict(table_name, data_dict):
        columns = ", ".join([f'"{k}"' for k in data_dict.keys()])
        placeholders = ", ".join(["?"] * len(data_dict))
        q = QSqlQuery(db)
        q.prepare(f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})")
        for value in data_dict.values():
            q.addBindValue(value)
        if not q.exec():
            raise RuntimeError(
                f"Failed to insert into {table_name}: {q.lastError().text()}"
            )

    insert_dict("administrative", initial_db_dict)
    insert_dict("folders", initial_db_dict)

    if not query.exec('DELETE FROM "folders"'):
        raise RuntimeError(f"Failed to delete from folders: {query.lastError().text()}")

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
        [
            f'"{k}" {"TEXT" if isinstance(v, str) else "INTEGER" if isinstance(v, (int, bool)) else "TEXT"}'
            for k, v in settings_dict.items()
        ]
    )

    if not query.exec(f"CREATE TABLE settings ({settings_columns})"):
        raise RuntimeError(
            f"Failed to create settings table: {query.lastError().text()}"
        )

    insert_dict("settings", settings_dict)

    if not query.exec(
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
    ):
        raise RuntimeError(
            f"Failed to create processed_files table: {query.lastError().text()}"
        )

    if not query.exec(
        "CREATE TABLE emails_to_send (id INTEGER PRIMARY KEY AUTOINCREMENT, log TEXT)"
    ):
        raise RuntimeError(
            f"Failed to create emails_to_send table: {query.lastError().text()}"
        )

    if not query.exec(
        "CREATE TABLE working_batch_emails_to_send (id INTEGER PRIMARY KEY AUTOINCREMENT, log TEXT)"
    ):
        raise RuntimeError(
            f"Failed to create working_batch_emails_to_send table: {query.lastError().text()}"
        )

    if not query.exec(
        "CREATE TABLE sent_emails_removal_queue (id INTEGER PRIMARY KEY AUTOINCREMENT, log TEXT)"
    ):
        raise RuntimeError(
            f"Failed to create sent_emails_removal_queue table: {query.lastError().text()}"
        )

    if not query.exec(
        "CREATE INDEX IF NOT EXISTS idx_folders_active ON folders(folder_is_active)"
    ):
        raise RuntimeError(f"Failed to create index: {query.lastError().text()}")

    if not query.exec("CREATE INDEX IF NOT EXISTS idx_folders_alias ON folders(alias)"):
        raise RuntimeError(f"Failed to create index: {query.lastError().text()}")

    if not query.exec(
        "CREATE INDEX IF NOT EXISTS idx_processed_files_folder ON processed_files(folder_id)"
    ):
        raise RuntimeError(f"Failed to create index: {query.lastError().text()}")

    if not query.exec(
        "CREATE INDEX IF NOT EXISTS idx_processed_files_status ON processed_files(status)"
    ):
        raise RuntimeError(f"Failed to create index: {query.lastError().text()}")

    if not query.exec(
        "CREATE INDEX IF NOT EXISTS idx_processed_files_created ON processed_files(created_at)"
    ):
        raise RuntimeError(f"Failed to create index: {query.lastError().text()}")

    db.close()
