"""Centralized schema definitions and helper to ensure tables exist.

This module provides a single source of truth for table layouts used by
create_database and migrations. It intentionally uses simple SQL CREATE
statements with permissive types (TEXT/INTEGER) so it can be applied
against older databases without failing.
"""

import sqlite3
import time

from core.structured_logging import get_logger

logger = get_logger(__name__)


def _execute_sqlite_statement(conn, stmt, object_name=None) -> None:
    """Execute a schema statement on sqlite3.Connection with retries for locked DB."""
    max_attempts = 3
    delay_base = 0.1

    for attempt in range(max_attempts):
        try:
            logger.debug(
                "Executing SQLite schema statement (attempt=%d) for %s",
                attempt + 1,
                object_name or "unknown",
            )
            conn.execute(stmt)
            conn.commit()
            if object_name:
                logger.info("Schema object verified: %s", object_name)
            return
        except sqlite3.OperationalError as exc:
            msg = str(exc).lower()
            if "locked" in msg and attempt < max_attempts - 1:
                logger.warning(
                    "Database is locked on attempt %d for %s; retrying",
                    attempt + 1,
                    object_name or "unknown",
                )
                time.sleep(delay_base * (attempt + 1))
                continue
            if "duplicate column name" in msg or "already exists" in msg:
                if object_name:
                    logger.debug("Schema object already exists: %s", object_name)
                return
            logger.error(
                "Operational error executing schema statement for %s: %s",
                object_name or "unknown",
                exc,
            )
            raise
        except sqlite3.Error as exc:
            err_str = str(exc).lower()
            if "already exists" in err_str:
                if object_name:
                    logger.debug("Schema object already exists: %s", object_name)
                return
            logger.error(
                "SQLite error executing schema statement for %s: %s",
                object_name or "unknown",
                exc,
            )
            raise


def ensure_schema(database_connection) -> None:
    """Ensure core tables and columns exist. Uses database_connection.query()."""
    stmts = [
        # version table
        """
        CREATE TABLE IF NOT EXISTS version (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version TEXT,
            os TEXT,
            notes TEXT
        )
        """,
        # settings
        """
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            enable_email INTEGER,
            email_address TEXT,
            email_username TEXT,
            email_password TEXT,
            email_smtp_server TEXT,
            smtp_port INTEGER,
            ssh_key_filename TEXT,
            as400_address TEXT,
            as400_username TEXT,
            as400_password TEXT,
            backup_counter INTEGER,
            backup_counter_maximum INTEGER,
            enable_interval_backups INTEGER,
            folder_is_active INTEGER,
            copy_to_directory TEXT,
            convert_to_format TEXT,
            process_edi INTEGER,
            calculate_upc_check_digit INTEGER,
            upc_target_length INTEGER,
            upc_padding_pattern TEXT,
            include_a_records INTEGER,
            include_c_records INTEGER,
            include_headers INTEGER,
            filter_ampersand INTEGER,
            tweak_edi INTEGER,
            pad_a_records INTEGER,
            a_record_padding TEXT,
            a_record_padding_length INTEGER,
            invoice_date_custom_format_string TEXT,
            invoice_date_custom_format INTEGER,
            reporting_email TEXT,
            folder_name TEXT,
            alias TEXT,
            report_email_destination TEXT,
            process_backend_copy INTEGER,
            backend_copy_destination TEXT,
            process_edi_output INTEGER,
            edi_output_folder TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        # administrative (deprecated duplicate of folders, kept for compatibility)
        """
        CREATE TABLE IF NOT EXISTS administrative (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            copy_to_directory TEXT,
            logs_directory TEXT,
            enable_reporting INTEGER,
            report_email_destination TEXT,
            report_edi_errors INTEGER,
            report_printing_fallback INTEGER,
            convert_to_format TEXT,
            tweak_edi INTEGER,
            split_edi INTEGER,
            force_edi_validation INTEGER,
            append_a_records INTEGER,
            a_record_append_text TEXT,
            force_txt_file_ext INTEGER,
            invoice_date_offset INTEGER,
            retail_uom INTEGER,
            force_each_upc INTEGER,
            include_item_numbers INTEGER,
            include_item_description INTEGER,
            simple_csv_sort_order TEXT,
            a_record_padding_length INTEGER,
            invoice_date_custom_format_string TEXT,
            invoice_date_custom_format INTEGER,
            split_prepaid_sales_tax_crec INTEGER,
            estore_store_number INTEGER,
            estore_Vendor_OId INTEGER,
            estore_vendor_NameVendorOID TEXT,
            prepend_date_files INTEGER,
            rename_file TEXT,
            estore_c_record_OID INTEGER,
            override_upc_bool INTEGER,
            override_upc_level INTEGER,
            override_upc_category_filter TEXT,
            split_edi_include_invoices INTEGER,
            split_edi_include_credits INTEGER,
            fintech_division_id INTEGER,
            split_edi_filter_categories TEXT,
            split_edi_filter_mode TEXT,
            plugin_config TEXT,
            created_at TEXT,
            updated_at TEXT,
            edi_converter_scratch_folder TEXT,
            errors_folder TEXT,
            single_add_folder_prior TEXT,
            batch_add_folder_prior TEXT,
            export_processed_folder_prior TEXT,
            edi_format TEXT,
            process_backend_email INTEGER,
            process_backend_ftp INTEGER,
            email_to TEXT,
            ftp_server TEXT,
            ftp_port INTEGER,
            ftp_folder TEXT,
            ftp_username TEXT,
            ftp_password TEXT
        )
        """,
        # folders (main configuration table)
        """
        CREATE TABLE IF NOT EXISTS folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folder_name TEXT,
            alias TEXT,
            folder_is_active INTEGER,
            copy_to_directory TEXT,
            process_edi INTEGER,
            convert_to_format TEXT,
            calculate_upc_check_digit INTEGER,
            upc_target_length INTEGER,
            upc_padding_pattern TEXT,
            include_a_records INTEGER,
            include_c_records INTEGER,
            include_headers INTEGER,
            filter_ampersand INTEGER,
            tweak_edi INTEGER,
            pad_a_records INTEGER,
            a_record_padding TEXT,
            a_record_padding_length INTEGER,
            invoice_date_custom_format_string TEXT,
            invoice_date_custom_format INTEGER,
            reporting_email TEXT,
            report_email_destination TEXT,
            process_backend_copy INTEGER,
            backend_copy_destination TEXT,
            process_backend_email INTEGER,
            process_backend_ftp INTEGER,
            process_backend_http INTEGER,
            http_url TEXT,
            http_headers TEXT,
            http_field_name TEXT,
            http_auth_type TEXT,
            http_api_key TEXT,
            email_to TEXT,
            email_subject_line TEXT,
            ftp_server TEXT,
            ftp_port INTEGER,
            ftp_folder TEXT,
            ftp_username TEXT,
            ftp_password TEXT,
            process_edi_output INTEGER,
            edi_output_folder TEXT,
            split_edi INTEGER,
            force_edi_validation INTEGER,
            append_a_records INTEGER,
            a_record_append_text TEXT,
            force_txt_file_ext INTEGER,
            invoice_date_offset INTEGER,
            retail_uom INTEGER,
            force_each_upc INTEGER,
            include_item_numbers INTEGER,
            include_item_description INTEGER,
            simple_csv_sort_order TEXT,
            split_prepaid_sales_tax_crec INTEGER,
            estore_store_number INTEGER,
            estore_Vendor_OId INTEGER,
            estore_vendor_NameVendorOID TEXT,
            prepend_date_files INTEGER,
            rename_file TEXT,
            estore_c_record_OID INTEGER,
            override_upc_bool INTEGER,
            override_upc_level INTEGER,
            override_upc_category_filter TEXT,
            split_edi_include_invoices INTEGER,
            split_edi_include_credits INTEGER,
            fintech_division_id INTEGER,
            split_edi_filter_categories TEXT,
            split_edi_filter_mode TEXT,
            plugin_config TEXT,
            created_at TEXT,
            updated_at TEXT,
            filename TEXT,
            original_path TEXT,
            processed_path TEXT,
            status TEXT,
            error_message TEXT,
            convert_format TEXT,
            sent_to TEXT,
            edi_format TEXT
        )
        """,
        # processed_files (legacy tracking of processed files)
        """
        CREATE TABLE IF NOT EXISTS processed_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT,
            folder_alias TEXT,
            md5 TEXT,
            file_checksum TEXT,
            resend_flag INTEGER,
            folder_id INTEGER,
            created_at TEXT,
            processed_at TEXT,
            filename TEXT,
            original_path TEXT,
            processed_path TEXT,
            status TEXT,
            error_message TEXT,
            convert_format TEXT,
            sent_to TEXT,
            invoice_numbers TEXT
        )
        """,
        # emails_to_send (queue for emails to be sent)
        """
        CREATE TABLE IF NOT EXISTS emails_to_send (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folder_alias TEXT,
            log TEXT,
            folder_id INTEGER
        )
        """,
        # working_batch_emails_to_send (batch email operations)
        """
        CREATE TABLE IF NOT EXISTS working_batch_emails_to_send (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folder_alias TEXT,
            log TEXT,
            folder_id TEXT
        )
        """,
        # sent_emails_removal_queue (queue for sent email removal)
        """
        CREATE TABLE IF NOT EXISTS sent_emails_removal_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folder_alias TEXT,
            log TEXT,
            folder_id TEXT,
            old_id INTEGER
        )
        """,
    ]

    # Add normalized tables to improve separation of concerns while keeping
    # legacy tables for backward compatibility.
    stmts += [
        """
        PRAGMA foreign_keys = ON;
        """,
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            display_name TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS organizations (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            org_id TEXT,
            name TEXT NOT NULL,
            description TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE SET NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS files (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            original_filename TEXT NOT NULL,
            storage_path TEXT NOT NULL,
            size_bytes INTEGER,
            checksum TEXT,
            created_by TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS batches (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            name TEXT,
            status TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            started_at TEXT,
            completed_at TEXT,
            created_by TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS processors (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            version TEXT,
            config TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS processing_jobs (
            id TEXT PRIMARY KEY,
            batch_id TEXT,
            file_id TEXT,
            processor_id TEXT,
            status TEXT,
            scheduled_at TEXT,
            started_at TEXT,
            finished_at TEXT,
            attempts INTEGER DEFAULT 0,
            result TEXT,
            FOREIGN KEY (batch_id) REFERENCES batches(id) ON DELETE CASCADE,
            FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
            FOREIGN KEY (processor_id) REFERENCES processors(id) ON DELETE SET NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS job_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT,
            level TEXT,
            message TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (job_id) REFERENCES processing_jobs(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS tags (
            id TEXT PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS file_tags (
            file_id TEXT,
            tag_id TEXT,
            PRIMARY KEY (file_id, tag_id),
            FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_files_project_id ON files(project_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_batches_project_id ON batches(project_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_jobs_status ON processing_jobs(status)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_jobs_file_id ON processing_jobs(file_id)
        """,
    ]

    # Log schema initialization start
    logger.info("Initializing database schema")

    for s in stmts:
        # Extract table/index name for logging
        object_name = _extract_object_name(s)
        _apply_statement_to_connection(database_connection, s, object_name)

    # Ensure newer columns exist on legacy DBs. Adding columns with ALTER
    # is safe if they already exist because we catch errors.
    # Handle ALTER statements separately for compatibility and best-effort behavior.
    raw_conn = getattr(database_connection, "_conn", None)

    try:
        if raw_conn is not None and isinstance(raw_conn, sqlite3.Connection):
            _execute_sqlite_statement(
                raw_conn,
                "ALTER TABLE 'folders' ADD COLUMN 'plugin_configurations' TEXT",
            )
            _execute_sqlite_statement(
                raw_conn,
                'UPDATE "folders" SET "plugin_configurations" = "{}" '
                'WHERE "plugin_configurations" IS NULL',
            )
        else:
            database_connection.query(
                "ALTER TABLE 'folders' ADD COLUMN 'plugin_configurations' TEXT"
            )
            database_connection.query(
                'UPDATE "folders" SET "plugin_configurations" = "{}" '
                'WHERE "plugin_configurations" IS NULL'
            )

        logger.info("Migration: added plugin_configurations column to folders table")
    except Exception:
        logger.info(
            "Folders plugin_configurations column migration skipped (may already exist)"
        )

    try:
        if raw_conn is not None and isinstance(raw_conn, sqlite3.Connection):
            _execute_sqlite_statement(
                raw_conn,
                "ALTER TABLE 'processed_files' ADD COLUMN 'invoice_numbers' TEXT",
            )
        else:
            database_connection.query(
                "ALTER TABLE 'processed_files' ADD COLUMN 'invoice_numbers' TEXT"
            )

        logger.info("Migration: added invoice_numbers column to processed_files table")
    except Exception:
        logger.info(
            (
                "Processed_files invoice_numbers column"
                " migration skipped (may already exist)"
            )
        )

    logger.info("Database schema initialization complete")


def _extract_object_name(stmt: str) -> str | None:
    """Extract table or index name from a SQL statement for logging.

    Args:
        stmt: SQL statement

    Returns:
        Table/index name if extractable, None otherwise

    """
    import re

    stmt_upper = stmt.strip().upper()

    # Match CREATE TABLE <name>
    table_match = re.match(
        r"\s*CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([^\s(]+)", stmt_upper
    )
    if table_match:
        return f"TABLE {table_match.group(1)}"

    # Match CREATE INDEX <name>
    index_match = re.match(
        r"\s*CREATE\s+INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?([^\s(]+)", stmt_upper
    )
    if index_match:
        return f"INDEX {index_match.group(1)}"

    # Match PRAGMA
    if stmt_upper.startswith("PRAGMA"):
        return "PRAGMA"

    return None


def _apply_statement_to_connection(
    database_connection, stmt: str, object_name: str | None
) -> None:
    """Apply a schema statement to the provided database connection.

    Handles both wrapped dataset-style connections (with .query) and raw
    sqlite3.Connection objects stored in _conn. Logs failures but attempts
    several strategies for best-effort idempotent behavior.
    """
    raw_conn = getattr(database_connection, "_conn", None)

    if raw_conn is not None and isinstance(raw_conn, sqlite3.Connection):
        try:
            _execute_sqlite_statement(raw_conn, stmt, object_name=object_name)
        except sqlite3.OperationalError as exc:
            logger.warning(
                "Schema statement lock/operational issue: %s, %s",
                object_name or "unknown",
                exc,
            )
        except sqlite3.Error as exc:
            logger.warning(
                "Schema statement sqlite error: %s: %s",
                object_name or "unknown",
                exc,
            )
        return

    try:
        database_connection.query(stmt)
        if object_name:
            logger.debug("Schema object created/verified: %s", object_name)
    except Exception:
        # be tolerant: older dataset impl or DB state may raise; ensure best-effort
        try:
            if raw_conn is not None:
                raw_conn.execute(stmt)
                raw_conn.commit()
                if object_name:
                    logger.debug(
                        "Schema object created/verified (via raw conn): %s",
                        object_name,
                    )
        except Exception:
            logger.info(
                "Schema statement skipped (may already exist or DB locked): %s",
                object_name or "unknown",
            )
