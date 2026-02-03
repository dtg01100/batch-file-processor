"""
Database schema version generators for migration testing.

This module creates database files at specific historical schema versions
to test that migrations work correctly from any version to current.

When adding a new migration version:
1. Add the new version to ALL_VERSIONS range
2. The system will automatically test it
"""

import os
import sqlite3
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.database import DatabaseConnection

ALL_VERSIONS = list(range(5, 42))  # Now includes version 41
CURRENT_VERSION = "41"


@contextmanager
def sqlite_connection(db_path: str):
    """Context manager for sqlite3 connections with foreign keys enabled."""
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
    finally:
        connection.close()


class DatabaseConnectionManager:
    """Context manager providing DatabaseConnection wrapper over sqlite3."""

    def __init__(self, db_path: str, connection_name: str = ""):
        self.db_path = db_path
        self.connection_name = connection_name
        self._connection = None
        self._db_connection = None

    def __enter__(self) -> DatabaseConnection:
        self._connection = sqlite3.connect(self.db_path)
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._db_connection = DatabaseConnection(self._connection)
        return self._db_connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._connection:
            self._connection.close()


def create_baseline_v5_schema(db_path: str) -> None:
    """Create the baseline version 5 database schema.

    This is the oldest supported version. All newer versions are created
    by applying migrations to this baseline.
    """
    with sqlite_connection(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute(
            "CREATE TABLE version (id INTEGER PRIMARY KEY, version TEXT, os TEXT)"
        )
        cursor.execute(
            "INSERT INTO version (version, os) VALUES (?, ?)", ("5", "Linux")
        )

        cursor.execute("""
            CREATE TABLE folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_is_active TEXT,
                folder_name TEXT,
                alias TEXT,
                process_edi TEXT,
                calculate_upc_check_digit TEXT,
                include_a_records TEXT,
                include_c_records TEXT,
                include_headers TEXT,
                filter_ampersand TEXT,
                pad_a_records TEXT,
                a_record_padding TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE administrative (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_is_active TEXT,
                folder_name TEXT,
                alias TEXT,
                process_edi TEXT
            )
        """)

        cursor.execute(
            "INSERT INTO administrative (folder_is_active, folder_name, alias, process_edi) VALUES (?, ?, ?, ?)",
            ("False", "template", "", "False"),
        )

        cursor.execute("""
            CREATE TABLE processed_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT,
                file_checksum TEXT,
                folder_id INTEGER
            )
        """)

        cursor.execute(
            "CREATE TABLE emails_to_send (id INTEGER PRIMARY KEY AUTOINCREMENT, log TEXT)"
        )

        cursor.execute("""
            CREATE TABLE settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                enable_email INTEGER,
                email_address TEXT,
                email_username TEXT,
                email_password TEXT,
                email_smtp_server TEXT,
                smtp_port INTEGER
            )
        """)

        conn.commit()


def migrate_to_version(db_path: str, target_version: int) -> None:
    """Migrate a database to a specific version using the actual migrator.

    Args:
        db_path: Path to database file (should start at v5)
        target_version: Version to migrate to (6-39)
    """
    if target_version < 5 or target_version > int(CURRENT_VERSION):
        raise ValueError(f"Invalid target version: {target_version}")

    if target_version == 5:
        return

    import folders_database_migrator

    with DatabaseConnectionManager(db_path, f"migrate_to_{target_version}") as db_conn:
        while True:
            version_table = db_conn["version"]
            version_dict = version_table.find_one(id=1)
            if version_dict is None:
                raise RuntimeError("Version record not found")
            current = int(version_dict["version"])

            if current >= target_version:
                break

            if current >= int(CURRENT_VERSION):
                break

            folders_database_migrator.upgrade_database(
                db_conn, None, "Linux", target_version
            )


def generate_database_at_version(version: int, db_path: str = "") -> str:
    """Generate a database at a specific schema version.

    This creates a v5 baseline and then migrates it to the target version
    using the actual migration code. This ensures we're testing real migrations.

    Args:
        version: Schema version to generate (5-39)
        db_path: Optional path for database file. If empty, creates temp file.

    Returns:
        Path to generated database file

    Raises:
        ValueError: If version is not supported
    """
    if version not in ALL_VERSIONS:
        raise ValueError(f"Version {version} not in supported range {ALL_VERSIONS}")

    if not db_path:
        fd, db_path = tempfile.mkstemp(suffix=".db", prefix=f"test_v{version}_")
        os.close(fd)
        os.unlink(db_path)

    create_baseline_v5_schema(db_path)

    if version > 5:
        migrate_to_version(db_path, version)

    return db_path


def get_database_version(db_path: str) -> str:
    """Get the version of a database file.

    Args:
        db_path: Path to database file

    Returns:
        Version string (e.g., "5", "39")
    """
    with sqlite_connection(db_path) as conn:
        cursor = conn.execute("SELECT version FROM version WHERE id=1")
        row = cursor.fetchone()
        if not row:
            raise RuntimeError("No version record found")
        return str(row[0])


def verify_database_structure(db_path: str) -> dict:
    """Verify and return information about database structure.

    Returns:
        Dict with 'version', 'tables', 'columns' keys
    """
    with sqlite_connection(db_path) as conn:
        cursor = conn.execute("SELECT version FROM version WHERE id=1")
        row = cursor.fetchone()
        version = str(row[0])

        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]

        columns = {}
        for table in tables:
            cursor = conn.execute(f"PRAGMA table_info({table})")
            columns[table] = [row[1] for row in cursor.fetchall()]

        return {"version": version, "tables": tables, "columns": columns}
