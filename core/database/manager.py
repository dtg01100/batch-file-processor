"""
Framework-agnostic DatabaseManager.

Handles database initialization, migrations, and table access without any Qt dependency.
"""

import datetime
import os
from typing import Any, Optional

from .connection import DatabaseConnection, Table, connect, connect_memory
import backup_increment
import folders_database_migrator


class DatabaseManager:
    """Database connection manager with version migration and table access.

    Attributes:
        database_connection: sqlite3 database connection wrapper.
        session_database: Session-scoped in-memory database for temporary operations.
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
        if not os.path.isfile(self._database_path):
            self._create_initial_database()

        self._connect_to_database()
        self._check_version_and_migrate()

    def _create_initial_database(self) -> None:
        try:
            print("creating initial database file...")
            from .schema import create_database

            create_database(
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
        try:
            self.database_connection = connect(self._database_path)
            self.session_database = connect_memory()
        except Exception as error:
            self._log_connection_error(error)
            raise SystemExit from error

    def _check_version_and_migrate(self) -> None:
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
        backup_increment.do_backup(self._database_path)

        folders_database_migrator.upgrade_database(
            self.database_connection,
            self._config_folder,
            self._platform,
            int(self._database_version),
        )

    def _initialize_table_references(self) -> None:
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
        try:
            self.database_connection = connect(self._database_path)
            self.session_database = connect_memory()
        except Exception as error:
            self._log_connection_error(error)
            raise SystemExit from error

        self._initialize_table_references()

    def close(self) -> None:
        if self.database_connection:
            self.database_connection.close()
        if self.session_database:
            self.session_database.close()

    def _log_critical_error(self, error: Exception) -> None:
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
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
