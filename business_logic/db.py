"""business_logic.db

Thin centralized database access helpers.

Public API:
- init_db(db_path: str) -> None
- get_connection() -> Any
- import_records(source: str, /, **kwargs) -> int
- list_folders() -> list[str]
- close() -> None
"""
from typing import Any, Callable, Dict, List, Optional, Tuple
import os
import platform

import dataset
import sqlalchemy

import backup_increment
import folders_database_migrator

# Centralized logging
import logging
from business_logic.logging import setup_logging as _setup_logging

# Ensure logging is configured for this module
_setup_logging()
logger = logging.getLogger("batch_file_processor")

# Module-level connection object
_conn: Optional[Any] = None


def init_db(db_path: str) -> None:
    """Open or create the SQLite database at db_path and ensure schema/migrations.

    This function:
    - Ensures parent directory exists.
    - Connects to the SQLite database using dataset.
    - If no version row exists, inserts an initial administrative template, a
      template folder (then clears the folders table — preserves historical behavior),
      settings defaults and creates the processed_files columns.
    - If a version row exists, attempt to run the upgrade path.

    Args:
        db_path: File path for the SQLite database file.
    """
    global _conn
    if _conn is not None:
        return

    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    _conn = dataset.connect("sqlite:///" + db_path)

    # Check for existing version row
    try:
        version_table = _conn["version"]
        version_row = version_table.find_one(id=1)
    except Exception:
        logger.exception("Unable to read version row from database")
        version_row = None

    if version_row is None:
        # Insert initial data (kept the same defaults as the original code)
        version = _conn["version"]
        version.insert(dict(version="1", os=platform.system()))

        initial_db_dict = dict(
            folder_is_active="False",
            copy_to_directory=None,
            process_edi="False",
            convert_to_format="csv",
            calculate_upc_check_digit="False",
            include_a_records="False",
            include_c_records="False",
            include_headers="False",
            filter_ampersand="False",
            tweak_edi=False,
            pad_a_records="False",
            a_record_padding="",
            a_record_padding_length=6,
            invoice_date_custom_format_string="%Y%m%d",
            invoice_date_custom_format=False,
            reporting_email="",
            folder_name="template",
            alias="",
            report_email_destination="",
            process_backend_copy=False,
            process_backend_ftp=False,
            process_backend_email=False,
            ftp_server="",
            ftp_folder="/",
            ftp_username="",
            ftp_password="",
            email_to="",
            logs_directory=os.path.join(os.path.dirname(os.path.abspath(db_path)), "run_logs"),
            errors_folder=os.path.join(os.path.dirname(os.path.abspath(db_path)), "errors"),
            enable_reporting="False",
            report_printing_fallback="False",
            ftp_port=21,
            email_subject_line="",
            single_add_folder_prior=os.path.expanduser("~"),
            batch_add_folder_prior=os.path.expanduser("~"),
            export_processed_folder_prior=os.path.expanduser("~"),
            report_edi_errors=False,
            split_edi=False,
            split_edi_include_invoices=True,
            split_edi_include_credits=True,
            force_edi_validation=False,
            append_a_records="False",
            a_record_append_text="",
            force_txt_file_ext="False",
            invoice_date_offset=0,
            retail_uom=False,
            include_item_numbers=False,
            include_item_description=False,
            simple_csv_sort_order="upc_number,qty_of_units,unit_cost,description,vendor_item",
            split_prepaid_sales_tax_crec=False,
            estore_store_number=0,
            estore_Vendor_OId=0,
            estore_vendor_NameVendorOID="replaceme",
            estore_c_record_OID="",
            prepend_date_files=False,
            rename_file="",
            override_upc_bool=False,
            override_upc_level=1,
            override_upc_category_filter="ALL",
            fintech_division_id=0,
        )

        oversight_and_defaults = _conn["administrative"]
        folders_table = _conn["folders"]

        oversight_and_defaults.insert(initial_db_dict)
        folders_table.insert(initial_db_dict)
        # Original code removed folders rows after inserting template row; preserve that behavior
        try:
            _conn.query('DELETE FROM "folders"')
        except Exception:
            # If SQL dialect/permissions differ, ignore to be robust
            logger.exception("Failed to clear folders table after inserting template row")

        settings_table = _conn["settings"]
        settings_table.insert(
            dict(
                enable_email=False,
                email_address="",
                email_username="",
                email_password="",
                email_smtp_server="smtp.gmail.com",
                smtp_port=587,
                backup_counter=0,
                backup_counter_maximum=200,
                enable_interval_backups=True,
                odbc_driver="Select ODBC Driver...",
                as400_address="",
                as400_username="",
                as400_password="",
            )
        )

        # Ensure processed_files has expected columns
        processed_files = _conn["processed_files"]
        try:
            processed_files.create_column("file_name", sqlalchemy.types.String)
            processed_files.create_column("file_checksum", sqlalchemy.types.String)
            processed_files.create_column("copy_destination", sqlalchemy.types.String)
            processed_files.create_column("ftp_destination", sqlalchemy.types.String)
            processed_files.create_column("email_destination", sqlalchemy.types.String)
            processed_files.create_column("resend_flag", sqlalchemy.types.Boolean)
            processed_files.create_column("folder_id", sqlalchemy.types.Integer)
        except Exception:
            # Be tolerant of databases that auto-create columns or older dataset versions
            logger.exception("Failed to create processed_files columns (may be OK on some backends)")
    else:
        # Existing DB: attempt to run migrations to ensure schema is up to date.
        try:
            folders_database_migrator.upgrade_database(_conn, None, platform.system())
        except Exception:
            # Keep init robust — callers may handle errors further up
            logger.exception("Database migration failed during init_db")


def get_connection() -> Any:
    """Return the active dataset connection object.

    Raises:
        RuntimeError: if init_db has not been called.
    """
    if _conn is None:
        raise RuntimeError("Database is not initialized. Call init_db(db_path) first.")
    return _conn


def import_records(source: str, /, **kwargs) -> int:
    """Import/merge folders from a source DB into a target DB.

    Parameters:
        source: path to the incoming database file (the "new" DB to import from)
    Keyword arguments:
        original_database_path: path to the existing/original database to merge into (required)
        progress_callback: optional callable(progress_count: int) used by UI callers

    Returns:
        Number of processed folder entries (int).

    Notes:
        This function is a non-UI wrapper around the merging logic previously
        implemented in mover.DbMigrationThing. It performs a backup of the
        incoming DB, upgrades it if needed and merges active folders into the
        original DB.
    """
    original_database_path: Optional[str] = kwargs.get("original_database_path")
    progress_callback: Optional[Callable[[int], None]] = kwargs.get("progress_callback")

    if not original_database_path:
        raise ValueError("original_database_path is required")

    # Back up incoming DB (preserve historical behavior)
    modified_new_path = backup_increment.do_backup(source)

    new_db = dataset.connect("sqlite:///" + modified_new_path)
    original_db = dataset.connect("sqlite:///" + original_database_path)

    # If new DB older than original, attempt upgrade
    try:
        orig_ver = original_db["version"].find_one(id=1)
        new_ver = new_db["version"].find_one(id=1)
        if orig_ver is not None and new_ver is not None:
            if int(new_ver.get("version", 0)) < int(orig_ver.get("version", 0)):
                folders_database_migrator.upgrade_database(new_db, None, "Null")
    except Exception:
        # Continue even if version checking fails
        logger.exception("Version check/upgrade failed during import_records")

    new_folders_table = new_db["folders"]
    old_folders_table = original_db["folders"]

    try:
        total_to_process = new_folders_table.count(folder_is_active="True")
    except Exception:
        total_to_process = sum(1 for _ in new_folders_table.find(folder_is_active="True"))

    processed = 0

    def _test_line_for_match(line: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        line_match = False
        new_db_line = None
        try:
            for db_line in old_folders_table.find(folder_is_active="True"):
                try:
                    if os.path.samefile(db_line["folder_name"], line["folder_name"]):
                        new_db_line = db_line
                        line_match = True
                        break
                except Exception:
                    # samefile might fail on different platforms or missing paths
                    continue
        except Exception:
            logger.exception("Error while testing line for match in import_records")
        return line_match, new_db_line

    for line in new_folders_table.find(folder_is_active="True"):
        try:
            line_match, matching_row = _test_line_for_match(line)
            if line_match and matching_row is not None:
                update_db_line = matching_row
                if matching_row.get("process_backend_copy") is True:
                    update_db_line.update(
                        dict(
                            process_backend_copy=matching_row.get("process_backend_copy"),
                            copy_to_directory=matching_row.get("copy_to_directory"),
                            id=line["id"],
                        )
                    )
                if matching_row.get("process_backend_ftp") is True:
                    update_db_line.update(
                        dict(
                            ftp_server=matching_row.get("ftp_server"),
                            ftp_folder=matching_row.get("ftp_folder"),
                            ftp_username=matching_row.get("ftp_username"),
                            ftp_password=matching_row.get("ftp_password"),
                            ftp_port=matching_row.get("ftp_port"),
                            id=line["id"],
                        )
                    )
                if matching_row.get("process_backend_email") is True:
                    update_db_line.update(
                        dict(
                            email_to=matching_row.get("email_to"),
                            email_subject_line=matching_row.get("email_subject_line"),
                            id=line["id"],
                        )
                    )
                old_folders_table.update(update_db_line, ["id"])
            else:
                if "id" in line:
                    del line["id"]
                old_folders_table.insert(line)
        except Exception:
            # Keep tolerant: mirror previous behavior
            logger.exception("Error importing a folder line: %s", line)

        processed += 1
        if progress_callback:
            try:
                progress_callback(processed)
            except Exception:
                pass

    # Close temporary connection to incoming DB
    try:
        new_db.close()
    except Exception:
        logger.exception("Failed to close temporary new_db connection")

    return processed


def list_folders() -> List[str]:
    """Return the list of folder_name strings from the initialized DB.

    init_db must be called before using this helper.
    """
    conn = get_connection()
    folders = conn["folders"]
    return [row["folder_name"] for row in folders.all()]


def close() -> None:
    """Close the underlying database connection if open."""
    global _conn
    if _conn is None:
        return
    try:
        _conn.close()
    except Exception:
        try:
            engine = getattr(_conn, "engine", None)
            if engine is not None:
                engine.dispose()
        except Exception:
            logger.exception("Failed to dispose engine while closing database connection")
    _conn = None