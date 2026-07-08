import datetime
import glob
import logging
import os
import sqlite3

from migrations.migration_helpers import (
    CURRENT_SCHEMA_VERSION,
    _log_migration_step,
    _normalize_legacy_v32_values,
    _quote_identifier,
)

logger = logging.getLogger(__name__)


def apply_v33_to_current(
    database_connection,
    config_folder,
    running_platform,
    db_version,
    db_version_dict,
    target_version=None,
) -> dict:
    """Apply all v33→current schema changes in a single consolidated pass.

    No production database exists above the v1.47 branch (≈v33), so every
    real-world upgrade is v32 → current. This function consolidates the
    20 individual v33→v51 blocks into one transaction.

    Honors ``target_version`` for test fixtures: if set to an intermediate
    value (e.g. "36", "42"), the consolidated transformation still runs
    to completion but the final version is bumped to ``target_version``
    instead of ``CURRENT_SCHEMA_VERSION``. This keeps historical
    intermediate-version tests meaningful while collapsing the
    production code path into a single linear function.
    """
    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return db_version_dict

    # Legacy migrations only know how to migrate from v5 onward. If the
    # DB is at a version legacy_migrations didn't recognize (e.g. v3),
    # leave it alone rather than running the v33+ transformation on
    # an unknown schema.
    try:
        current_version_int = int(db_version_dict["version"])
    except (TypeError, ValueError):
        current_version_int = 0
    if current_version_int < 32:
        return db_version_dict

    if str(db_version_dict["version"]) == "32":
        db_version.update(dict(id=1, version="33"), ["id"])
        db_version_dict = db_version.find_one(id=1)

    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return db_version_dict

    conn = database_connection.raw_connection
    cursor = conn.cursor()
    try:
        conn.execute("BEGIN")

        # --- v33 → v34: timestamps ---
        now = datetime.datetime.now().isoformat()
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
            except sqlite3.OperationalError as e:
                logger.debug("Column may already exist: %s", e)
        for table, timestamp_col in [
            ("folders", "created_at"),
            ("folders", "updated_at"),
            ("administrative", "created_at"),
            ("administrative", "updated_at"),
            ("processed_files", "created_at"),
            ("settings", "created_at"),
            ("settings", "updated_at"),
        ]:
            cursor.execute(
                f"UPDATE '{table}' SET {timestamp_col} = ? WHERE {timestamp_col} IS NULL",
                (now,),
            )

        # --- v34 → v35: processed_files columns ---
        for col in [
            "filename",
            "original_path",
            "processed_path",
            "error_message",
            "convert_format",
            "sent_to",
        ]:
            try:
                cursor.execute(
                    f"ALTER TABLE 'processed_files' ADD COLUMN '{col}' TEXT"
                )
            except sqlite3.OperationalError as e:
                logger.debug("Column %s may already exist: %s", col, e)
        try:
            cursor.execute(
                "ALTER TABLE 'processed_files' ADD COLUMN 'status' TEXT DEFAULT 'processed'"
            )
        except sqlite3.OperationalError as e:
            logger.debug("Column 'status' may already exist: %s", e)
        cursor.execute(
            "UPDATE 'processed_files' SET filename=file_name "
            "WHERE file_name IS NOT NULL AND filename IS NULL"
        )

        # --- v35 → v36: indexes ---
        for ddl in [
            "CREATE INDEX IF NOT EXISTS idx_folders_active ON folders(folder_is_active)",
            "CREATE INDEX IF NOT EXISTS idx_folders_alias ON folders(alias)",
            "CREATE INDEX IF NOT EXISTS idx_processed_files_folder ON processed_files(folder_id)",
            "CREATE INDEX IF NOT EXISTS idx_processed_files_status ON processed_files(status)",
            "CREATE INDEX IF NOT EXISTS idx_processed_files_created ON processed_files(created_at)",
        ]:
            try:
                cursor.execute(ddl)
            except sqlite3.OperationalError as e:
                logger.debug("Index creation skipped: %s", e)

        # --- v37 → v38: version.notes ---
        try:
            cursor.execute("ALTER TABLE 'version' ADD COLUMN 'notes' TEXT")
        except sqlite3.OperationalError as e:
            logger.debug("Column 'notes' may already exist: %s", e)
        cursor.execute("""
            UPDATE 'version'
            SET notes='administrative table duplicates folders table. Use folders table for all operations. administrative table deprecated.'
        """)

        # --- v38 → v39: edi_format ---
        for table in ("folders", "administrative"):
            try:
                cursor.execute(
                    f"ALTER TABLE '{table}' ADD COLUMN 'edi_format' TEXT"
                )
            except sqlite3.OperationalError as e:
                logger.debug("Column edi_format may already exist: %s", e)
            cursor.execute(
                f"UPDATE '{table}' SET 'edi_format' = 'default'"
            )

        # --- v39 → v40: rebuild folders + administrative with id PK ---
        def _existing_columns(table_name):
            quoted_table = _quote_identifier(table_name)
            cursor.execute(f"PRAGMA table_info({quoted_table})")
            return [row[1] for row in cursor.fetchall()]

        def _rebuild_table_with_pk(table_name) -> None:
            existing = _existing_columns(table_name)
            if "id" in existing:
                return

            quoted_table = _quote_identifier(table_name)
            old_columns = [
                (row[1], row[2]) for row in cursor.execute(
                    f"PRAGMA table_info({quoted_table})"
                ).fetchall()
            ]

            col_defs = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]
            for col_name, col_type in old_columns:
                col_defs.append(f"{_quote_identifier(col_name)} {col_type}")
            columns_sql = ", ".join(col_defs)

            old_cols = ", ".join([_quote_identifier(c[0]) for c in old_columns])
            new_table = _quote_identifier(f"{table_name}_new")

            cursor.execute(f"DROP TABLE IF EXISTS {new_table}")
            cursor.execute(f"CREATE TABLE {new_table} ({columns_sql})")
            cursor.execute(
                f"INSERT INTO {new_table} ({old_cols}) SELECT {old_cols} FROM {quoted_table}"
            )
            cursor.execute(f"DROP TABLE {quoted_table}")
            cursor.execute(f"ALTER TABLE {new_table} RENAME TO {quoted_table}")

        _rebuild_table_with_pk("folders")
        _rebuild_table_with_pk("administrative")

        # --- v40 → v41: backend columns ---
        def _ensure_column(table_name, column_name, sql_type, default_sql) -> None:
            if column_name in _existing_columns(table_name):
                return
            quoted_table = _quote_identifier(table_name)
            quoted_column = _quote_identifier(column_name)
            cursor.execute(
                f"ALTER TABLE {quoted_table} ADD COLUMN {quoted_column} {sql_type}"
            )
            cursor.execute(
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

        # --- v41 → v42: normalize 'True'/'False' string booleans ---
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
        for field in boolean_fields:
            try:
                quoted_field = _quote_identifier(field)
                cursor.execute(
                    f"UPDATE folders SET {quoted_field} = 1 WHERE {quoted_field} = 'True'"
                )
                cursor.execute(
                    f"UPDATE folders SET {quoted_field} = 0 WHERE {quoted_field} = 'False'"
                )
                cursor.execute(
                    f"UPDATE administrative SET {quoted_field} = 1 WHERE {quoted_field} = 'True'"
                )
                cursor.execute(
                    f"UPDATE administrative SET {quoted_field} = 0 WHERE {quoted_field} = 'False'"
                )
            except sqlite3.OperationalError as e:
                logger.debug("Error normalizing field %s: %s", field, e)

        for stmt in [
            "UPDATE settings SET enable_email = 1 WHERE enable_email = 'True'",
            "UPDATE settings SET enable_email = 0 WHERE enable_email = 'False'",
            "UPDATE settings SET enable_interval_backups = 1 WHERE enable_interval_backups = 'True'",
            "UPDATE settings SET enable_interval_backups = 0 WHERE enable_interval_backups = 'False'",
        ]:
            try:
                cursor.execute(stmt)
            except sqlite3.OperationalError as e:
                logger.debug("Error normalizing settings table: %s", e)

        # --- v42 → v43: normalize folder paths ---
        try:
            folders_table = database_connection["folders"]
            for folder in folders_table.all():
                folder_name = folder.get("folder_name")
                if folder_name and "\\" in folder_name:
                    normalized = folder_name.replace("\\", "/")
                    folders_table.update(
                        {"id": folder["id"], "folder_name": normalized}, ["id"]
                    )
        except sqlite3.OperationalError as e:
            logger.debug("Error normalizing folder paths: %s", e)

        # --- v43 → v44: upc columns ---
        for table in ("folders", "settings"):
            try:
                cursor.execute(
                    f"ALTER TABLE '{table}' ADD COLUMN 'upc_target_length' INTEGER DEFAULT 11"
                )
            except sqlite3.OperationalError as e:
                logger.debug("Column upc_target_length may already exist: %s", e)
            try:
                cursor.execute(
                    f"ALTER TABLE '{table}' ADD COLUMN 'upc_padding_pattern' TEXT"
                )
            except sqlite3.OperationalError as e:
                logger.debug("Column upc_padding_pattern may already exist: %s", e)

        # --- v44 → v45: promote tweak_edi=1 to convert_to_format='tweaks' ---
        for table in ("folders", "administrative"):
            try:
                cursor.execute(f"""
                    UPDATE {table}
                    SET convert_to_format = 'tweaks',
                        tweak_edi         = 0,
                        process_edi       = 1
                    WHERE tweak_edi = 1
                      AND convert_to_format IS NOT NULL
                      AND convert_to_format != ''
                """)
            except sqlite3.OperationalError as e:
                logger.debug("v44→v45 promotion A on %s: %s", table, e)
            try:
                cursor.execute(f"""
                    UPDATE {table}
                    SET convert_to_format = 'tweaks',
                        tweak_edi         = 0,
                        process_edi       = 1
                    WHERE tweak_edi = 1
                      AND (convert_to_format IS NULL OR convert_to_format = '')
                """)
            except sqlite3.OperationalError as e:
                logger.debug("v44→v45 promotion B on %s: %s", table, e)

        # --- v45 → v46: cleanup residual tweak_edi=1 + force administrative ---
        for table in ("folders", "administrative"):
            try:
                cursor.execute(f"""
                    UPDATE {table}
                    SET convert_to_format = 'tweaks'
                    WHERE tweak_edi = 1
                      AND (convert_to_format IS NULL OR convert_to_format = '')
                """)
            except sqlite3.OperationalError as e:
                logger.debug("v45→v46 cleanup on %s: %s", table, e)
        try:
            cursor.execute("""
                UPDATE folders
                SET tweak_edi = 0, process_edi = 1
                WHERE convert_to_format = 'tweaks'
            """)
        except sqlite3.OperationalError as e:
            logger.debug("v45→v46 tweaks promotion: %s", e)
        try:
            cursor.execute("UPDATE administrative SET tweak_edi = 0")
        except sqlite3.OperationalError as e:
            logger.debug("v45→v46 administrative tweak_edi reset: %s", e)

        # --- v46 → v47: backup repair for misconfigured tweaks folders ---
        try:
            affected = {
                r[0]
                for r in cursor.execute(
                    "SELECT id FROM folders "
                    "WHERE process_edi = '0' AND convert_to_format = 'tweaks'"
                ).fetchall()
            }
        except sqlite3.OperationalError as e:
            logger.debug("v46→v47 backup repair skipped (missing columns): %s", e)
            affected = set()

        if affected:
            backup_files = []
            if config_folder:
                backup_pattern = os.path.join(config_folder, "folders.db.bak-*")
                backup_files = sorted(glob.glob(backup_pattern))

            if backup_files:
                backup_path = backup_files[-1]
                try:
                    import sqlite3 as _sqlite3

                    back_conn = _sqlite3.connect(backup_path)
                    back_conn.row_factory = _sqlite3.Row

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
                    logger.debug(
                        "Repaired %d folders using backup %s",
                        fixed,
                        os.path.basename(backup_path),
                    )
                except sqlite3.OperationalError as e:
                    logger.warning("Could not repair from backup: %s", e)
            else:
                logger.warning(
                    "No backup file found; folders with process_edi='0' and "
                    "convert_to_format='tweaks' may have incorrect conversion "
                    "targets (manual review recommended)."
                )

        # --- v47 → v48, v48 → v49: no-op bumps (deliberate placeholders) ---

        # --- v49 → v50: HTTP backend (process_backend_http + payload columns) ---
        for table_name in ("folders", "administrative"):
            _ensure_column(table_name, "process_backend_http", "INTEGER", "0")
            _ensure_column(table_name, "http_url", "TEXT", "''")
            _ensure_column(table_name, "http_headers", "TEXT", "''")
            _ensure_column(table_name, "http_field_name", "TEXT", "'file'")
            _ensure_column(table_name, "http_auth_type", "TEXT", "''")
            _ensure_column(table_name, "http_api_key", "TEXT", "''")

        # --- v50 → v51: each_uom columns ---
        for table_name in ("folders", "administrative"):
            _ensure_column(
                table_name, "each_uom_categories", "TEXT", "'ALL'"
            )
            _ensure_column(
                table_name, "each_uom_mode", "TEXT", "'include'"
            )

        # Backfill NULL values for columns where _ensure_column was a no-op
        # (i.e. ensure_schema pre-created the column without a default).
        # This is the consolidated replacement for the v50/v51 repair block.
        _backfill_defaults = {
            ("folders", "process_backend_http"): "0",
            ("administrative", "process_backend_http"): "0",
            ("folders", "http_url"): "''",
            ("administrative", "http_url"): "''",
            ("folders", "http_headers"): "''",
            ("administrative", "http_headers"): "''",
            ("folders", "http_field_name"): "'file'",
            ("administrative", "http_field_name"): "'file'",
            ("folders", "http_auth_type"): "''",
            ("administrative", "http_auth_type"): "''",
            ("folders", "http_api_key"): "''",
            ("administrative", "http_api_key"): "''",
            ("folders", "each_uom_categories"): "'ALL'",
            ("administrative", "each_uom_categories"): "'ALL'",
            ("folders", "each_uom_mode"): "'include'",
            ("administrative", "each_uom_mode"): "'include'",
        }
        for (table_name, column_name), default_sql in _backfill_defaults.items():
            quoted_table = _quote_identifier(table_name)
            quoted_column = _quote_identifier(column_name)
            try:
                cursor.execute(
                    f"UPDATE {quoted_table} SET {quoted_column} = {default_sql} "
                    f"WHERE {quoted_column} IS NULL"
                )
            except sqlite3.OperationalError as e:
                logger.debug(
                    "Backfill skipped for %s.%s: %s", table_name, column_name, e
                )

        conn.execute("COMMIT")
    except sqlite3.Error as e:
        conn.execute("ROLLBACK")
        raise RuntimeError(f"Consolidated v33→current migration failed: {e}") from e

    final_version = (
        str(target_version)
        if target_version and int(target_version) < int(CURRENT_SCHEMA_VERSION)
        else CURRENT_SCHEMA_VERSION
    )
    update_version = dict(id=1, version=final_version, os=running_platform)
    db_version.update(update_version, ["id"])
    if final_version != "32":
        _log_migration_step("32", final_version)

    return db_version.find_one(id=1)


def migrate_v33_to_v50(database_connection, db_version, running_platform) -> None:
    """Backward-compatible wrapper for ``apply_v33_to_current``.

    Historical name preserved for external callers. Production flow goes
    through ``upgrade_database`` in ``folders_database_migrator``.
    """
    db_version_dict = db_version.find_one(id=1)
    apply_v33_to_current(
        database_connection,
        None,
        running_platform,
        db_version,
        db_version_dict,
        target_version=None,
    )


def _normalize_legacy_v32_values_at_compat(database_connection) -> None:
    """Backward-compatible export of the v32 normalization helper.

    Historical callers expect ``modern_migrations`` to expose the
    normalization step. Delegates to the canonical helper in
    ``migration_helpers``.
    """
    _normalize_legacy_v32_values(database_connection)
