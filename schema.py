"""Centralized schema definitions and helper to ensure tables exist.

This module provides a single source of truth for table layouts used by
create_database and migrations. It intentionally uses simple SQL CREATE
statements with permissive types (TEXT/INTEGER) so it can be applied
against older databases without failing.
"""

import typing


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
            backup_counter INTEGER,
            backup_counter_maximum INTEGER,
            enable_interval_backups INTEGER,
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
            edi_format TEXT
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
            md5 TEXT,
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
            sent_to TEXT
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

    for s in stmts:
        try:
            database_connection.query(s)
        except Exception:
            # be tolerant: older dataset impl or DB state may raise; ensure best-effort
            try:
                # Some dataset shims expose ._conn for raw sqlite3.Connection
                raw = getattr(database_connection, "_conn", None)
                if raw is not None:
                    raw.execute(s)
                    raw.commit()
            except Exception:
                # last resort: skip silently to avoid breaking upgrades
                pass
