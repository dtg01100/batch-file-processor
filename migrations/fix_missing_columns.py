#!/usr/bin/env python3
"""
Standalone script to fix missing process_backend_http columns in the database.

This script handles the case where migration v48->v49 failed partway through,
leaving the database at version 49 but missing the process_backend_http column
in one or both tables (folders, administrative).

Usage:
    python -m migrations.fix_missing_columns /path/to/database.db
"""

import argparse
import sqlite3
import sys


def _quote_identifier(name: str) -> str:
    """Quote a SQL identifier, escaping any embedded quotes."""
    escaped = name.replace('"', '""')
    return f'"{escaped}"'


def _column_exists(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    quoted_table = _quote_identifier(table_name)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({quoted_table})")
    existing_columns = {row[1] for row in cursor.fetchall()}
    return column_name in existing_columns


def _get_db_version(conn: sqlite3.Connection) -> int | None:
    """Get the current database version from the version table."""
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT version FROM version WHERE id = 1")
        row = cursor.fetchone()
        if row:
            return int(row[0])
    except Exception:
        pass
    return None


def _set_db_version(conn: sqlite3.Connection, version: int) -> None:
    """Set the database version in the version table."""
    quoted_version = _quote_identifier("version")
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE version SET {quoted_version} = ? WHERE id = 1", (str(version),)
    )


def _add_column(
    conn: sqlite3.Connection,
    table_name: str,
    column_name: str,
    sql_type: str,
    default_value,
) -> None:
    """Add a column to a table using raw_connection.execute() directly."""
    quoted_table = _quote_identifier(table_name)
    quoted_column = _quote_identifier(column_name)

    print(f"  Adding column {column_name} ({sql_type}) to table {table_name}...")
    conn.execute(f"ALTER TABLE {quoted_table} ADD COLUMN {quoted_column} {sql_type}")

    print(f"  Setting default value ({default_value}) for column {column_name}...")
    conn.execute(f"UPDATE {quoted_table} SET {quoted_column} = {default_value}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fix missing process_backend_http columns in the database."
    )
    parser.add_argument(
        "database_path",
        type=str,
        help="Path to the SQLite database file",
    )
    args = parser.parse_args()

    print(f"Connecting to database: {args.database_path}")

    conn = sqlite3.connect(args.database_path)
    try:
        db_version = _get_db_version(conn)
        print(f"Current database version: {db_version}")

        folders_has_column = _column_exists(conn, "folders", "process_backend_http")
        admin_has_column = _column_exists(
            conn, "administrative", "process_backend_http"
        )

        print(f"Column 'process_backend_http' in 'folders' table: {folders_has_column}")
        print(
            f"Column 'process_backend_http' in 'administrative' table: {admin_has_column}"
        )

        column_missing = not folders_has_column or not admin_has_column
        column_exists = folders_has_column and admin_has_column

        if column_missing and db_version == 49:
            print(
                "\nDatabase version is 49 but process_backend_http column is missing."
            )
            print(
                "This indicates a failed migration. Reverting version to 48 so the migration can run again..."
            )
            _set_db_version(conn, 48)
            db_version = 48
            print("Version reverted to 48.")
            column_missing = True

        if column_missing:
            print("\nAdding missing columns...")

            if not folders_has_column:
                _add_column(conn, "folders", "process_backend_http", "INTEGER", 0)

            if not admin_has_column:
                _add_column(
                    conn, "administrative", "process_backend_http", "INTEGER", 0
                )

        if column_exists and db_version == 48:
            print("\nColumn exists but version is 48. Updating version to 49...")
            _set_db_version(conn, 49)
            db_version = 49

        conn.commit()
        print("\nChanges committed successfully.")

        if db_version == 49:
            print("Database is now at version 49 with all required columns present.")
        else:
            print(
                f"Database is now at version {db_version}. Please run the migration again to complete the upgrade."
            )

        return 0

    except Exception as e:
        conn.rollback()
        print(f"\nError: {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
