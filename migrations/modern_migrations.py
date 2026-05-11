import contextlib
import glob
import logging
import os
import sqlite3
import sqlite3 as _sqlite3

from migrations.migration_helpers import (
    CURRENT_SCHEMA_VERSION,
    _log_migration_step,
    _quote_identifier,
)

logger = logging.getLogger(__name__)


def migrate_v33_to_v50(database_connection, db_version, running_platform) -> None:
    """Apply all schema changes from v33 through v50 in a single pass.

    Thin wrapper around run_modern_migrations. Bumps version to "33"
    first so that the individual migration blocks can find matching
    version gates.
    """
    db_version_dict = db_version.find_one(id=1)
    # Bump to v33 so run_modern_migrations can find the first block
    if str(db_version_dict["version"]) == "32":
        db_version.update(dict(id=1, version="33"), ["id"])
        db_version_dict = db_version.find_one(id=1)
    run_modern_migrations(
        database_connection,
        None,
        running_platform,
        db_version,
        db_version_dict,
        target_version=None,
    )


def run_modern_migrations(
    database_connection,
    config_folder,
    running_platform,
    db_version,
    db_version_dict,
    target_version=None,
) -> dict:
    """Run all v33→v50 individual migrations. Returns updated db_version_dict."""
    # --- v33 → v34 ---
    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return db_version_dict

    if db_version_dict["version"] == "33":
        import datetime

        now = datetime.datetime.now().isoformat()

        cursor = database_connection.raw_connection.cursor()
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
        database_connection.raw_connection.commit()

        update_version = dict(id=1, version="34", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("33", "34")

    # --- v34 → v35 ---
    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return db_version_dict

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
            except sqlite3.OperationalError as e:
                logger.debug("Column %s may already exist: %s", col, e)
        try:
            cursor.execute(
                "ALTER TABLE 'processed_files' ADD COLUMN 'status' TEXT DEFAULT 'processed'"
            )
        except sqlite3.OperationalError as e:
            logger.debug("Column 'status' may already exist: %s", e)
        cursor.execute(
            "UPDATE 'processed_files' SET filename=file_name WHERE file_name IS NOT NULL AND filename IS NULL"
        )
        database_connection.raw_connection.commit()

        update_version = dict(id=1, version="35", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("34", "35")

    # --- v35 → v36 ---
    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return db_version_dict

    if db_version_dict["version"] == "35":
        cursor = database_connection.raw_connection.cursor()
        for ddl in [
            "CREATE INDEX IF NOT EXISTS idx_folders_active ON folders(folder_is_active)",
            "CREATE INDEX IF NOT EXISTS idx_folders_alias ON folders(alias)",
            "CREATE INDEX IF NOT EXISTS idx_processed_files_folder ON processed_files(folder_id)",
            "CREATE INDEX IF NOT EXISTS idx_processed_files_status ON processed_files(status)",
            "CREATE INDEX IF NOT EXISTS idx_processed_files_created ON processed_files(created_at)",
        ]:
            with contextlib.suppress(sqlite3.OperationalError):
                cursor.execute(ddl)
        database_connection.raw_connection.commit()

        update_version = dict(id=1, version="36", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("35", "36")

    # --- v36 → v37 ---
    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return db_version_dict

    if db_version_dict["version"] == "36":
        update_version = dict(id=1, version="37", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("36", "37")

    # --- v37 → v38 ---
    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return db_version_dict

    if db_version_dict["version"] == "37":
        database_connection.query("ALTER TABLE 'version' ADD COLUMN 'notes' TEXT")
        database_connection.query("""
            UPDATE 'version' SET notes='administrative table duplicates folders table. Use folders table for all operations. administrative table deprecated.'
        """)

        update_version = dict(id=1, version="38", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("37", "38")

    # --- v38 → v39 ---
    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return db_version_dict

    if db_version_dict["version"] == "38":
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

    # --- v39 → v40 ---
    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return db_version_dict

    if db_version_dict["version"] == "39":
        conn = database_connection.raw_connection

        def _rebuild_table_with_pk(table_name) -> None:
            cursor = conn.cursor()
            quoted_table = _quote_identifier(table_name)
            cursor.execute(f"PRAGMA table_info({quoted_table})")
            existing = [row[1] for row in cursor.fetchall()]
            if "id" in existing:
                return

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
            except sqlite3.Error:
                cursor.execute("ROLLBACK")
                raise

        _rebuild_table_with_pk("folders")
        _rebuild_table_with_pk("administrative")

        update_version = dict(id=1, version="40", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("39", "40")

    # --- v40 → v41 ---
    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return db_version_dict

    if str(db_version_dict["version"]) == "40":

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

    # --- v41 → v42 ---
    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return db_version_dict

    if db_version_dict["version"] == "41":
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
                database_connection.query(
                    f"UPDATE folders SET {quoted_field} = 1 WHERE {quoted_field} = 'True'"
                )
                database_connection.query(
                    f"UPDATE folders SET {quoted_field} = 0 WHERE {quoted_field} = 'False'"
                )
            except sqlite3.OperationalError as e:
                print(f"Error normalizing field {field} in folders: {e}")

        for field in boolean_fields:
            try:
                quoted_field = _quote_identifier(field)
                database_connection.query(
                    f"UPDATE administrative SET {quoted_field} = 1 WHERE {quoted_field} = 'True'"
                )
                database_connection.query(
                    f"UPDATE administrative SET {quoted_field} = 0 WHERE {quoted_field} = 'False'"
                )
            except sqlite3.OperationalError as e:
                print(f"Error normalizing field {field} in administrative: {e}")

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
        except sqlite3.OperationalError as e:
            print(f"Error normalizing settings table: {e}")

        update_version = dict(id=1, version="42", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("41", "42")

    # --- v42 → v43 ---
    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return db_version_dict

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
        except sqlite3.OperationalError as e:
            print(f"Error normalizing folder paths: {e}")

        update_version = dict(id=1, version="43", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("42", "43")

    # --- v43 → v44 ---
    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return db_version_dict

    if db_version_dict["version"] == "43":
        cursor = database_connection.raw_connection.cursor()
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
        database_connection.raw_connection.commit()

        update_version = dict(id=1, version="44", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("43", "44")

    # --- v44 → v45 ---
    db_version_dict = db_version.find_one(id=1)
    if db_version_dict and str(db_version_dict["version"]) == "44":
        cursor = database_connection.raw_connection.cursor()

        for table in ("folders", "administrative"):
            with contextlib.suppress(sqlite3.OperationalError):
                cursor.execute(f"""
                    UPDATE {table}
                    SET convert_to_format = 'tweaks',
                        process_edi       = 1,
                        tweak_edi         = 0
                    WHERE tweak_edi = 1
                      AND convert_to_format IS NOT NULL
                      AND convert_to_format != ''
                """)

            with contextlib.suppress(sqlite3.OperationalError):
                cursor.execute(f"""
                    UPDATE {table}
                    SET convert_to_format = 'tweaks',
                        process_edi       = 1,
                        tweak_edi         = 0
                    WHERE tweak_edi = 1
                      AND (convert_to_format IS NULL OR convert_to_format = '')
                """)

        database_connection.raw_connection.commit()

        update_version = dict(id=1, version="45", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("44", "45")

    # --- v45 → v46 ---
    db_version_dict = db_version.find_one(id=1)
    if db_version_dict and str(db_version_dict["version"]) == "45":
        cursor = database_connection.raw_connection.cursor()

        with contextlib.suppress(sqlite3.OperationalError):
            cursor.execute("""
                UPDATE folders
                SET convert_to_format = 'tweaks'
                WHERE tweak_edi = 1
                AND (convert_to_format IS NULL OR convert_to_format = '')
            """)

        with contextlib.suppress(sqlite3.OperationalError):
            cursor.execute("""
                UPDATE administrative
                SET convert_to_format = 'tweaks'
                WHERE tweak_edi = 1
                AND (convert_to_format IS NULL OR convert_to_format = '')
            """)

        with contextlib.suppress(sqlite3.OperationalError):
            cursor.execute("UPDATE folders SET tweak_edi = 0")

        with contextlib.suppress(sqlite3.OperationalError):
            cursor.execute("UPDATE administrative SET tweak_edi = 0")

        database_connection.raw_connection.commit()

        update_version = dict(id=1, version="46", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("45", "46")

    # --- v46 → v47 ---
    db_version_dict = db_version.find_one(id=1)
    if db_version_dict and str(db_version_dict["version"]) == "46":
        cursor = database_connection.raw_connection.cursor()

        affected = {
            r[0]
            for r in cursor.execute(
                "SELECT id FROM folders "
                "WHERE process_edi = '0' AND convert_to_format = 'tweaks'"
            ).fetchall()
        }

        if affected:
            backup_files = []
            if config_folder:
                backup_pattern = os.path.join(config_folder, "folders.db.bak-*")
                backup_files = sorted(glob.glob(backup_pattern))

            if backup_files:
                backup_path = backup_files[-1]
                try:
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
                    database_connection.raw_connection.commit()
                    print(
                        f"  Repaired {fixed} folders using backup "
                        f"{os.path.basename(backup_path)}"
                    )
                except sqlite3.OperationalError as e:
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

    # --- v47 → v48 ---
    db_version_dict = db_version.find_one(id=1)
    if db_version_dict and str(db_version_dict["version"]) == "47":
        update_version = dict(id=1, version="48", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("47", "48")

    # --- v48 → v49 ---
    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return db_version_dict

    def _existing_columns_v48(table_name):
        cursor = database_connection.raw_connection.cursor()
        quoted_table = _quote_identifier(table_name)
        cursor.execute(f"PRAGMA table_info({quoted_table})")
        return {row[1] for row in cursor.fetchall()}

    def _ensure_column_v48(table_name, column_name, sql_type, default_sql) -> None:
        if column_name in _existing_columns_v48(table_name):
            return
        quoted_table = _quote_identifier(table_name)
        quoted_column = _quote_identifier(column_name)
        conn = database_connection.raw_connection
        try:
            conn.execute(
                f"ALTER TABLE {quoted_table} ADD COLUMN {quoted_column} {sql_type}"
            )
        except sqlite3.OperationalError as e:
            raise RuntimeError(
                f"Failed to add column {quoted_column} to table {quoted_table}: {e}"
            ) from e
        try:
            conn.execute(f"UPDATE {quoted_table} SET {quoted_column} = {default_sql}")
        except sqlite3.OperationalError as e:
            raise RuntimeError(
                f"Failed to set default value for column {quoted_column} in table {quoted_table}: {e}"
            ) from e

    if str(db_version_dict["version"]) == "48":
        update_version = dict(id=1, version="49", os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("48", "49")

    # --- v49 → v50 ---
    db_version_dict = db_version.find_one(id=1)

    if str(db_version_dict["version"]) == "49":
        conn = database_connection.raw_connection
        try:
            conn.execute("BEGIN")
            for table_name in ("folders", "administrative"):
                _ensure_column_v48(table_name, "process_backend_http", "INTEGER", "0")
            conn.execute("COMMIT")
        except sqlite3.OperationalError as e:
            conn.execute("ROLLBACK")
            raise RuntimeError(f"Failed to add process_backend_http column: {e}") from e

        update_version = dict(id=1, version=CURRENT_SCHEMA_VERSION, os=running_platform)
        db_version.update(update_version, ["id"])
        _log_migration_step("49", CURRENT_SCHEMA_VERSION)

    # --- v50 repair (does NOT increment version) ---
    db_version_dict = db_version.find_one(id=1)

    if str(db_version_dict["version"]) == "50":
        conn = database_connection.raw_connection
        cursor = conn.cursor()

        def _column_exists(table_name, column_name):
            quoted_table = _quote_identifier(table_name)
            cursor.execute(f"PRAGMA table_info({quoted_table})")
            return column_name in {row[1] for row in cursor.fetchall()}

        required_http_columns = {
            "process_backend_http": ("INTEGER", "0"),
            "http_url": ("TEXT", "''"),
            "http_headers": ("TEXT", "''"),
            "http_field_name": ("TEXT", "'file'"),
            "http_auth_type": ("TEXT", "''"),
            "http_api_key": ("TEXT", "''"),
        }

        missing_by_table = {
            table_name: [
                col
                for col in required_http_columns
                if not _column_exists(table_name, col)
            ]
            for table_name in ("folders", "administrative")
        }

        if missing_by_table["folders"] or missing_by_table["administrative"]:
            print("  Repairing database: missing HTTP backend column(s)...")
            try:
                conn.execute("BEGIN")

                for table_name in ("folders", "administrative"):
                    quoted_table = _quote_identifier(table_name)
                    for column_name in missing_by_table[table_name]:
                        sql_type, default_sql = required_http_columns[column_name]
                        quoted_column = _quote_identifier(column_name)
                        conn.execute(
                            f"ALTER TABLE {quoted_table} ADD COLUMN {quoted_column} {sql_type}"
                        )
                        conn.execute(
                            f"UPDATE {quoted_table} SET {quoted_column} = {default_sql}"
                        )

                for table_name in ("folders", "administrative"):
                    quoted_table = _quote_identifier(table_name)
                    for column_name, (_, default_sql) in required_http_columns.items():
                        quoted_column = _quote_identifier(column_name)
                        conn.execute(
                            f"UPDATE {quoted_table} SET {quoted_column} = {default_sql} "
                            f"WHERE {quoted_column} IS NULL"
                        )

                conn.execute("COMMIT")
                print("  Repair complete: HTTP backend column(s) added.")
            except sqlite3.OperationalError as e:
                conn.execute("ROLLBACK")
                raise RuntimeError(f"Failed to repair HTTP backend columns: {e}") from e
        else:
            try:
                conn.execute("BEGIN")
                total_null_updates = 0
                for table_name in ("folders", "administrative"):
                    quoted_table = _quote_identifier(table_name)
                    for column_name, (_, default_sql) in required_http_columns.items():
                        quoted_column = _quote_identifier(column_name)
                        cursor.execute(
                            f"SELECT COUNT(*) FROM {quoted_table} WHERE {quoted_column} IS NULL"
                        )
                        null_count = cursor.fetchone()[0]
                        if null_count > 0:
                            total_null_updates += null_count
                            conn.execute(
                                f"UPDATE {quoted_table} SET {quoted_column} = {default_sql} "
                                f"WHERE {quoted_column} IS NULL"
                            )

                if total_null_updates > 0:
                    print(
                        f"  Repair complete: replaced {total_null_updates} NULL HTTP value(s) with defaults."
                    )
                conn.execute("COMMIT")
            except sqlite3.OperationalError as e:
                conn.execute("ROLLBACK")
                raise RuntimeError(
                    f"Failed to repair HTTP backend NULL values: {e}"
                ) from e

    return db_version_dict
