"""
Database schema version generators for migration testing.

This module creates database files at specific historical schema versions
to test that migrations work correctly from any version to current.

When adding a new migration version:
1. Add the new version to ALL_VERSIONS range
2. The system will automatically test it
"""

import os
import tempfile
from PyQt6.QtSql import QSqlDatabase, QSqlQuery
from PyQt6.QtWidgets import QApplication
import sys


_qapp_instance = None


def get_qapplication():
    """Get or create QApplication instance for Qt operations."""
    global _qapp_instance
    if _qapp_instance is None:
        _qapp_instance = QApplication.instance()
        if _qapp_instance is None:
            _qapp_instance = QApplication(sys.argv)
    return _qapp_instance


# All supported migration versions (5 is oldest, current is newest)
ALL_VERSIONS = list(range(5, 40))  # 5, 6, 7, ..., 39
CURRENT_VERSION = "39"


class DatabaseConnectionManager:
    """Context manager for safe QSqlDatabase connections."""

    def __init__(self, db_path: str, connection_name: str = ""):
        get_qapplication()
        self.db_path = db_path
        self.connection_name = (
            connection_name if connection_name else f"conn_{id(self)}"
        )
        self.db = None

    def __enter__(self):
        if QSqlDatabase.contains(self.connection_name):
            QSqlDatabase.removeDatabase(self.connection_name)

        self.db = QSqlDatabase.addDatabase("QSQLITE", self.connection_name)
        self.db.setDatabaseName(self.db_path)

        if not self.db.open():
            raise RuntimeError(f"Failed to open database: {self.db.lastError().text()}")

        query = QSqlQuery(self.db)
        query.exec("PRAGMA foreign_keys = ON")

        return self.db

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.db and self.db.isOpen():
            self.db.close()
        if QSqlDatabase.contains(self.connection_name):
            QSqlDatabase.removeDatabase(self.connection_name)


def create_baseline_v5_schema(db_path: str) -> None:
    """Create the baseline version 5 database schema.

    This is the oldest supported version. All newer versions are created
    by applying migrations to this baseline.
    """
    with DatabaseConnectionManager(db_path, "create_v5") as db:
        query = QSqlQuery(db)

        # Version table
        if not query.exec(
            "CREATE TABLE version (id INTEGER PRIMARY KEY, version TEXT, os TEXT)"
        ):
            raise RuntimeError(
                f"Failed to create version table: {query.lastError().text()}"
            )

        query.prepare("INSERT INTO version (version, os) VALUES (?, ?)")
        query.addBindValue("5")
        query.addBindValue("Linux")
        if not query.exec():
            raise RuntimeError(f"Failed to insert version: {query.lastError().text()}")

        # Folders table (minimal v5 schema)
        if not query.exec("""
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
        """):
            raise RuntimeError(
                f"Failed to create folders table: {query.lastError().text()}"
            )

        # Administrative table
        if not query.exec("""
            CREATE TABLE administrative (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_is_active TEXT,
                folder_name TEXT,
                alias TEXT,
                process_edi TEXT
            )
        """):
            raise RuntimeError(
                f"Failed to create administrative table: {query.lastError().text()}"
            )

        # Insert default admin record
        query.prepare(
            "INSERT INTO administrative (folder_is_active, folder_name, alias, process_edi) VALUES (?, ?, ?, ?)"
        )
        query.addBindValue("False")
        query.addBindValue("template")
        query.addBindValue("")
        query.addBindValue("False")
        if not query.exec():
            raise RuntimeError(
                f"Failed to insert admin record: {query.lastError().text()}"
            )

        # Processed files table
        if not query.exec("""
            CREATE TABLE processed_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT,
                file_checksum TEXT,
                folder_id INTEGER
            )
        """):
            raise RuntimeError(
                f"Failed to create processed_files table: {query.lastError().text()}"
            )

        # Emails table
        if not query.exec(
            "CREATE TABLE emails_to_send (id INTEGER PRIMARY KEY AUTOINCREMENT, log TEXT)"
        ):
            raise RuntimeError(
                f"Failed to create emails_to_send table: {query.lastError().text()}"
            )

        # Settings table
        if not query.exec("""
            CREATE TABLE settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                enable_email INTEGER,
                email_address TEXT,
                email_username TEXT,
                email_password TEXT,
                email_smtp_server TEXT,
                smtp_port INTEGER
            )
        """):
            raise RuntimeError(
                f"Failed to create settings table: {query.lastError().text()}"
            )


def migrate_to_version(db_path: str, target_version: int) -> None:
    """Migrate a database to a specific version using the actual migrator.

    Args:
        db_path: Path to database file (should start at v5)
        target_version: Version to migrate to (6-32)
    """
    if target_version < 5 or target_version > int(CURRENT_VERSION):
        raise ValueError(f"Invalid target version: {target_version}")

    if target_version == 5:
        return  # Already at v5

    # Import here to avoid circular dependencies
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    from interface.database.database_manager import DatabaseConnection
    import folders_database_migrator

    # Apply migrations incrementally until we reach target version
    with DatabaseConnectionManager(db_path, f"migrate_to_{target_version}") as db:
        db_conn = DatabaseConnection(db)

        # Keep migrating until we reach target or current
        while True:
            version_table = db_conn["version"]
            version_dict = version_table.find_one(id=1)
            current = int(version_dict["version"])

            if current >= target_version:
                break

            if current >= int(CURRENT_VERSION):
                break

            # Run migrations up to target version
            folders_database_migrator.upgrade_database(
                db_conn, None, "Linux", target_version
            )


def generate_database_at_version(version: int, db_path: str = "") -> str:
    """Generate a database at a specific schema version.

    This creates a v5 baseline and then migrates it to the target version
    using the actual migration code. This ensures we're testing real migrations.

    Args:
        version: Schema version to generate (5-32)
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
        os.unlink(db_path)  # Remove the empty file, will be created by baseline

    # Create v5 baseline
    create_baseline_v5_schema(db_path)

    # Migrate to target version if needed
    if version > 5:
        migrate_to_version(db_path, version)

    return db_path


def get_database_version(db_path: str) -> str:
    """Get the version of a database file.

    Args:
        db_path: Path to database file

    Returns:
        Version string (e.g., "5", "32")
    """
    with DatabaseConnectionManager(db_path, "get_version") as db:
        query = QSqlQuery(db)

        if not query.exec("SELECT version FROM version WHERE id=1"):
            raise RuntimeError(f"Failed to query version: {query.lastError().text()}")

        if not query.next():
            raise RuntimeError("No version record found")

        return str(query.value(0))


def verify_database_structure(db_path: str) -> dict:
    """Verify and return information about database structure.

    Returns:
        Dict with 'version', 'tables', 'columns' keys
    """
    with DatabaseConnectionManager(db_path, "verify_structure") as db:
        query = QSqlQuery(db)

        # Get version
        query.exec("SELECT version FROM version WHERE id=1")
        query.next()
        version = str(query.value(0))

        # Get tables
        query.exec("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = []
        while query.next():
            tables.append(query.value(0))

        # Get columns for each table
        columns = {}
        for table in tables:
            query.exec(f"PRAGMA table_info({table})")
            table_cols = []
            while query.next():
                table_cols.append(query.value(1))  # Column name
            columns[table] = table_cols

        return {"version": version, "tables": tables, "columns": columns}
