"""
Database manager module for interface.py refactoring.

This module handles database connections, migrations, and table access.
Refactored from interface.py DatabaseObj class (lines 63-238).
Migrated from dataset to Qt SQL (QSqlDatabase/QSqlQuery).
"""

import datetime
import os
import sys
from typing import Any, Dict, List, Optional

# Add parent directory to path for imports from root level modules
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from PyQt6.QtSql import QSqlDatabase, QSqlQuery

import create_database
import folders_database_migrator
import backup_increment


class Table:
    """Wrapper class providing dataset-like API over Qt SQL."""

    def __init__(self, db: QSqlDatabase, table_name: str):
        self.db = db
        self.table_name = table_name

    def _dict_to_where(self, **kwargs) -> tuple[str, List[Any]]:
        """Convert kwargs to WHERE clause and bind values."""
        if not kwargs:
            return "", []
        conditions = []
        values = []
        for key, value in kwargs.items():
            conditions.append(f'"{key}" = ?')
            values.append(value)
        return " WHERE " + " AND ".join(conditions), values

    def _dict_to_set(self, data: Dict[str, Any]) -> tuple[str, str, List[Any]]:
        """Convert dict to column list, placeholders, and values for INSERT."""
        columns = [f'"{key}"' for key in data.keys()]
        placeholders = ["?"] * len(data)
        values = list(data.values())
        return ", ".join(columns), ", ".join(placeholders), values

    def find(self, order_by: Optional[str] = None, **kwargs) -> List[Dict[str, Any]]:
        """Find rows matching conditions."""
        where_clause, where_values = self._dict_to_where(**kwargs)
        order_clause = f' ORDER BY "{order_by}"' if order_by else ""
        query = QSqlQuery(self.db)
        query.prepare(f'SELECT * FROM "{self.table_name}"{where_clause}{order_clause}')
        for value in where_values:
            query.addBindValue(value)

        if not query.exec():
            raise RuntimeError(f"Query failed: {query.lastError().text()}")

        results = []
        record = query.record()
        while query.next():
            row = {}
            for i in range(record.count()):
                row[record.fieldName(i)] = query.value(i)
            results.append(row)
        return results

    def find_one(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Find single row matching conditions."""
        results = self.find(**kwargs)
        return results[0] if results else None

    def all(self) -> List[Dict[str, Any]]:
        """Get all rows."""
        return self.find()

    def insert(self, data: Dict[str, Any]) -> None:
        """Insert a single row."""
        columns, placeholders, values = self._dict_to_set(data)
        query = QSqlQuery(self.db)
        query.prepare(
            f'INSERT INTO "{self.table_name}" ({columns}) VALUES ({placeholders})'
        )
        for value in values:
            query.addBindValue(value)

        if not query.exec():
            raise RuntimeError(f"Insert failed: {query.lastError().text()}")

    def insert_many(self, records: List[Dict[str, Any]]) -> None:
        """Insert multiple rows."""
        for record in records:
            self.insert(record)

    def update(self, data: Dict[str, Any], keys: List[str]) -> None:
        """Update rows matching key columns."""
        set_parts = []
        set_values = []
        where_parts = []
        where_values = []

        for key, value in data.items():
            if key in keys:
                where_parts.append(f'"{key}" = ?')
                where_values.append(value)
            else:
                set_parts.append(f'"{key}" = ?')
                set_values.append(value)

        if not set_parts:
            return

        set_clause = ", ".join(set_parts)
        where_clause = " AND ".join(where_parts) if where_parts else "1=1"

        query = QSqlQuery(self.db)
        query.prepare(
            f'UPDATE "{self.table_name}" SET {set_clause} WHERE {where_clause}'
        )
        for value in set_values + where_values:
            query.addBindValue(value)

        if not query.exec():
            raise RuntimeError(f"Update failed: {query.lastError().text()}")

    def delete(self, **kwargs) -> None:
        """Delete rows matching conditions."""
        where_clause, where_values = self._dict_to_where(**kwargs)
        if not where_clause:
            query = QSqlQuery(self.db)
            if not query.exec(f'DELETE FROM "{self.table_name}"'):
                raise RuntimeError(f"Delete failed: {query.lastError().text()}")
            return

        query = QSqlQuery(self.db)
        query.prepare(f'DELETE FROM "{self.table_name}"{where_clause}')
        for value in where_values:
            query.addBindValue(value)

        if not query.exec():
            raise RuntimeError(f"Delete failed: {query.lastError().text()}")

    def drop(self) -> None:
        """Drop the table from the database."""
        query = QSqlQuery(self.db)
        if not query.exec(f'DROP TABLE IF EXISTS "{self.table_name}"'):
            raise RuntimeError(f"Drop table failed: {query.lastError().text()}")

    def count(self, **kwargs) -> int:
        """Count rows matching conditions."""
        where_clause, where_values = self._dict_to_where(**kwargs)
        query = QSqlQuery(self.db)
        query.prepare(f'SELECT COUNT(*) FROM "{self.table_name}"{where_clause}')
        for value in where_values:
            query.addBindValue(value)

        if not query.exec() or not query.next():
            raise RuntimeError(f"Count failed: {query.lastError().text()}")

        return query.value(0)

    def distinct(self, column: str) -> List[Any]:
        """Get distinct values for a column."""
        query = QSqlQuery(self.db)
        if not query.exec(f'SELECT DISTINCT "{column}" FROM "{self.table_name}"'):
            raise RuntimeError(f"Distinct query failed: {query.lastError().text()}")

        results = []
        while query.next():
            results.append(query.value(0))
        return results

    def create_column(self, column_name: str, column_type: Any) -> None:
        """Add a column to the table."""
        query = QSqlQuery(self.db)
        type_map = {
            "String": "TEXT",
            "Integer": "INTEGER",
            "Boolean": "INTEGER",
            "Float": "REAL",
        }
        type_str = str(column_type)
        if "'" in type_str:
            type_str = type_str.split("'")[1]
        sql_type = type_map.get(type_str, "TEXT")
        if not query.exec(
            f'ALTER TABLE "{self.table_name}" ADD COLUMN "{column_name}" {sql_type}'
        ):
            raise RuntimeError(f"Add column failed: {query.lastError().text()}")

    def __iter__(self):
        """Support iteration over rows."""
        return iter(self.all())


class DatabaseConnection:
    """Wrapper providing dataset-like database connection API."""

    def __init__(self, db: QSqlDatabase):
        self.db = db

    def __getitem__(self, table_name: str) -> Table:
        """Access tables by name like db['table_name']."""
        return Table(self.db, table_name)

    def query(self, sql: str) -> None:
        """Execute raw SQL query."""
        query = QSqlQuery(self.db)
        if not query.exec(sql):
            raise RuntimeError(f"Query failed: {query.lastError().text()}")

    def close(self) -> None:
        """Close the database connection."""
        if self.db.isOpen():
            self.db.close()

    def create_table(self, table_name: str) -> None:
        """Create a new table (stub for compatibility)."""
        pass


class DatabaseManager:
    """Database connection manager with version migration and table access.

    Attributes:
        database_connection: Qt SQL database connection wrapper.
        session_database: Session-scoped database for temporary operations.
        folders_table: Table for folder configurations.
        emails_table: Table for emails to send.
        emails_table_batch: Table for batch email operations.
        sent_emails_removal_queue: Table for tracking sent emails for removal.
        oversight_and_defaults: Table for administrative settings.
        processed_files: Table for processed file records.
        settings: Table for application settings.
    """

    def __init__(
        self,
        database_path: str,
        config_folder: str,
        platform: str,
        app_version: str,
        database_version: str,
    ):
        """
        Initialize the database manager.

        Args:
            database_path: Path to the SQLite database file.
            config_folder: Configuration directory path.
            platform: Current operating system platform.
            app_version: Application version string.
            database_version: Database schema version.
        """
        self._database_path = database_path
        self._config_folder = config_folder
        self._platform = platform
        self._app_version = app_version
        self._database_version = database_version
        self.database_connection: Optional[DatabaseConnection] = None
        self.session_database: Optional[DatabaseConnection] = None
        self.folders_table: Optional[Table] = None
        self.emails_table: Optional[Table] = None
        self.emails_table_batch: Optional[Table] = None
        self.sent_emails_removal_queue: Optional[Table] = None
        self.oversight_and_defaults: Optional[Table] = None
        self.processed_files: Optional[Table] = None
        self.settings: Optional[Table] = None

        self._initialize_database()

    def _initialize_database(self) -> None:
        """Initialize the database connection and tables."""
        if not os.path.isfile(self._database_path):
            self._create_initial_database()

        self._connect_to_database()
        self._check_version_and_migrate()

    def _create_initial_database(self) -> None:
        """Create the initial database file with schema."""
        try:
            print("creating initial database file...")
            create_database.do(
                self._database_version,
                self._database_path,
                self._config_folder,
                self._platform,
            )
            print("done")
        except Exception as error:
            self._log_critical_error(error)
            raise SystemExit from error

    def _connect_to_database(self) -> None:
        """Establish connection to the database."""
        try:
            db = QSqlDatabase.addDatabase("QSQLITE")
            db.setDatabaseName(self._database_path)
            if not db.open():
                raise RuntimeError(f"Failed to open database: {db.lastError().text()}")

            from PyQt6.QtSql import QSqlQuery

            query = QSqlQuery(db)
            query.exec("PRAGMA foreign_keys = ON")

            self.database_connection = DatabaseConnection(db)

            session_db = QSqlDatabase.addDatabase("QSQLITE", "session")
            session_db.setDatabaseName(":memory:")
            if not session_db.open():
                raise RuntimeError(
                    f"Failed to open session database: {session_db.lastError().text()}"
                )
            self.session_database = DatabaseConnection(session_db)
        except Exception as error:
            self._log_connection_error(error)
            raise SystemExit from error

    def _check_version_and_migrate(self) -> None:
        """Check database version and perform migrations if needed."""
        if self.database_connection is None:
            raise RuntimeError("Database connection not established")

        db_version = self.database_connection["version"]
        db_version_dict = db_version.find_one(id=1)

        if db_version_dict is None:
            raise RuntimeError("Version record not found")

        db_version_int = int(db_version_dict["version"])
        expected_version_int = int(self._database_version)

        if db_version_int < expected_version_int:
            print(
                f"Database schema update required: v{db_version_int} → v{expected_version_int}"
            )
            print("Creating backup before migration...")
            self._perform_migration()
            print(f"✓ Database successfully upgraded to v{expected_version_int}")

        if db_version_int > expected_version_int:
            print(
                f"ERROR: Database version (v{db_version_int}) is newer than application version (v{expected_version_int})"
            )
            print("Please update the application to a newer version.")
            raise SystemExit

        if db_version_dict["os"] != self._platform:
            error_message = (
                f"ERROR: OS mismatch detected.\n"
                f"Operating system detected: {self._platform}\n"
                f"Configuration creator OS: {db_version_dict['os']}\n"
                f"Folder paths are not portable between operating systems. Exiting."
            )
            print(error_message)
            raise SystemExit

        self._initialize_table_references()

    def _perform_migration(self) -> None:
        """Perform database migration."""
        backup_increment.do_backup(self._database_path)

        folders_database_migrator.upgrade_database(
            self.database_connection,
            self._config_folder,
            self._platform,
            int(self._database_version),
        )

    def _initialize_table_references(self) -> None:
        """Initialize references to all database tables."""
        if self.database_connection is None:
            raise RuntimeError("Database connection not established")

        self.folders_table = self.database_connection["folders"]
        self.emails_table = self.database_connection["emails_to_send"]
        self.emails_table_batch = self.database_connection[
            "working_batch_emails_to_send"
        ]
        self.sent_emails_removal_queue = self.database_connection[
            "sent_emails_removal_queue"
        ]
        self.oversight_and_defaults = self.database_connection["administrative"]
        self.processed_files = self.database_connection["processed_files"]
        self.settings = self.database_connection["settings"]

    def reload(self) -> None:
        """Reconnect to the database and refresh table references."""
        try:
            db = QSqlDatabase.addDatabase("QSQLITE")
            db.setDatabaseName(self._database_path)
            if not db.open():
                raise RuntimeError(f"Failed to open database: {db.lastError().text()}")
            self.database_connection = DatabaseConnection(db)

            session_db = QSqlDatabase.addDatabase("QSQLITE", "session_reload")
            session_db.setDatabaseName(":memory:")
            if not session_db.open():
                raise RuntimeError(
                    f"Failed to open session database: {session_db.lastError().text()}"
                )
            self.session_database = DatabaseConnection(session_db)
        except Exception as error:
            self._log_connection_error(error)
            raise SystemExit from error

        self._initialize_table_references()

    def close(self) -> None:
        """Close the database connection."""
        if self.database_connection:
            self.database_connection.close()

    def _log_critical_error(self, error: Exception) -> None:
        """Log a critical error to the error log file.

        Args:
            error: The exception that occurred.
        """
        try:
            print(str(error))
            with open("critical_error.log", "a", encoding="utf-8") as critical_log:
                critical_log.write("program version is " + self._app_version)
                critical_log.write(str(datetime.datetime.now()) + str(error) + "\r\n")
        except Exception as big_error:
            print(
                "error writing critical error log for error: "
                + str(error)
                + "\n"
                + "operation failed with error: "
                + str(big_error)
            )
            raise SystemExit from big_error

    def _log_connection_error(self, error: Exception) -> None:
        """Log a database connection error.

        Args:
            error: The exception that occurred.
        """
        try:
            print(str(error))
            with open(
                "critical_error.log", "a", encoding="utf-8"
            ) as connect_critical_log:
                connect_critical_log.write("program version is " + self._app_version)
                connect_critical_log.write(
                    str(datetime.datetime.now()) + str(error) + "\r\n"
                )
        except Exception as connect_big_error:
            print(
                "error writing critical error log for error: "
                + str(error)
                + "\n"
                + "operation failed with error: "
                + str(connect_big_error)
            )
            raise SystemExit from connect_big_error

    def __enter__(self) -> "DatabaseManager":
        """Context manager entry.

        Returns:
            Self for use in 'with' statements.
        """
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit.

        Args:
            exc_type: Exception type if an exception occurred.
            exc_val: Exception value if an exception occurred.
            exc_tb: Exception traceback if an exception occurred.
        """
        self.close()
