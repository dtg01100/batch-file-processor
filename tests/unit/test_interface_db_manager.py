"""
Unit tests for sqlite3-based database manager implementation.

Covers Table, DatabaseConnection, and DatabaseManager using real sqlite3
in-memory databases with no Qt dependencies.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterator
from unittest.mock import MagicMock, mock_open, patch

import pytest

from interface.database.database_manager import (
    DatabaseConnection,
    DatabaseManager,
    Table,
)


def _create_in_memory_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _create_versioned_connection(version: str, os_name: str) -> DatabaseConnection:
    connection = _create_in_memory_connection()
    connection.execute(
        "CREATE TABLE version (id INTEGER PRIMARY KEY, version TEXT, os TEXT)"
    )
    connection.execute(
        "INSERT INTO version (id, version, os) VALUES (1, ?, ?)",
        (version, os_name),
    )
    connection.commit()
    return DatabaseConnection(connection)


@pytest.fixture
def sample_database_config(tmp_path: Path) -> dict[str, str]:
    return {
        "database_path": str(tmp_path / "db.sqlite"),
        "config_folder": str(tmp_path / "config"),
        "platform": "linux",
        "app_version": "1.0.0",
        "database_version": "2",
    }


@pytest.fixture
def sqlite_connection() -> Iterator[sqlite3.Connection]:
    connection = _create_in_memory_connection()
    connection.execute(
        "CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT, active INTEGER, value INTEGER)"
    )
    yield connection
    connection.close()


@pytest.fixture
def empty_table(sqlite_connection: sqlite3.Connection) -> Table:
    return Table(sqlite_connection, "test_table")


@pytest.fixture
def populated_table(empty_table: Table) -> Table:
    empty_table.insert_many(
        [
            {"id": 1, "name": "Test 1", "active": 1, "value": 100},
            {"id": 2, "name": "Test 2", "active": 0, "value": 200},
            {"id": 3, "name": "Test 3", "active": 1, "value": 300},
        ]
    )
    return empty_table


class TestTable:
    def test_initialization(self, sqlite_connection: sqlite3.Connection) -> None:
        table = Table(sqlite_connection, "test_table")

        assert table._table_name == "test_table"
        assert table._connection is sqlite_connection

    def test_dict_to_where_empty(self, empty_table: Table) -> None:
        where_clause, values = empty_table._dict_to_where()

        assert where_clause == ""
        assert values == []

    def test_dict_to_where_multiple_conditions(self, empty_table: Table) -> None:
        where_clause, values = empty_table._dict_to_where(
            id=1, name="test", active=True
        )

        assert '"id" = ?' in where_clause
        assert '"name" = ?' in where_clause
        assert '"active" = ?' in where_clause
        assert values == [1, "test", True]

    def test_dict_to_set(self, empty_table: Table) -> None:
        columns, placeholders, values = empty_table._dict_to_set(
            {"id": 1, "name": "test", "value": 100}
        )

        assert columns == '"id", "name", "value"'
        assert placeholders == "?, ?, ?"
        assert values == [1, "test", 100]

    def test_find_all(self, populated_table: Table) -> None:
        results = populated_table.find()

        assert len(results) == 3
        assert results[0]["id"] == 1
        assert results[1]["name"] == "Test 2"

    def test_find_with_conditions(self, populated_table: Table) -> None:
        results = populated_table.find(active=1)

        assert {row["id"] for row in results} == {1, 3}

    def test_find_with_order_by(self, populated_table: Table) -> None:
        results = populated_table.find(order_by="value")

        assert [row["value"] for row in results] == [100, 200, 300]

    def test_find_one_returns_single_row(self, populated_table: Table) -> None:
        result = populated_table.find_one(id=2)

        assert result == {
            "id": 2,
            "name": "Test 2",
            "active": 0,
            "value": 200,
        }

    def test_find_one_returns_none(self, populated_table: Table) -> None:
        assert populated_table.find_one(id=999) is None

    def test_all_delegates_to_find(self, populated_table: Table) -> None:
        results = populated_table.all()

        assert len(results) == 3

    def test_insert(self, empty_table: Table) -> None:
        empty_table.insert({"id": 10, "name": "Inserted", "active": 1, "value": 999})

        assert empty_table.count() == 1
        result = empty_table.find_one(id=10)
        assert result is not None
        assert result["name"] == "Inserted"

    def test_insert_many(self, empty_table: Table) -> None:
        empty_table.insert_many(
            [
                {"id": 1, "name": "First", "active": 1, "value": 10},
                {"id": 2, "name": "Second", "active": 0, "value": 20},
            ]
        )

        assert empty_table.count() == 2

    def test_update(self, populated_table: Table) -> None:
        populated_table.update({"id": 1, "name": "Updated", "value": 101}, ["id"])

        result = populated_table.find_one(id=1)
        assert result is not None
        assert result["name"] == "Updated"

    def test_update_no_set_values(self, populated_table: Table) -> None:
        populated_table.update({"id": 1}, ["id"])

        result = populated_table.find_one(id=1)
        assert result is not None
        assert result["name"] == "Test 1"

    def test_delete_with_conditions(self, populated_table: Table) -> None:
        populated_table.delete(id=2)

        assert populated_table.count() == 2
        assert populated_table.find_one(id=2) is None

    def test_delete_all(self, populated_table: Table) -> None:
        populated_table.delete()

        assert populated_table.count() == 0

    def test_count_with_conditions(self, populated_table: Table) -> None:
        assert populated_table.count(active=1) == 2

    def test_distinct(self, populated_table: Table) -> None:
        assert populated_table.distinct("active") == [1, 0]

    def test_create_column_with_known_type(self) -> None:
        connection = _create_in_memory_connection()
        connection.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY)")
        table = Table(connection, "sample")

        table.create_column("score", "Integer")

        columns = connection.execute("PRAGMA table_info(sample)").fetchall()
        column_types = {column[1]: column[2] for column in columns}
        assert column_types["score"] == "INTEGER"
        connection.close()

    def test_create_column_with_unknown_type_defaults_to_text(self) -> None:
        connection = _create_in_memory_connection()
        connection.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY)")
        table = Table(connection, "sample")

        table.create_column("metadata", list)

        columns = connection.execute("PRAGMA table_info(sample)").fetchall()
        column_types = {column[1]: column[2] for column in columns}
        assert column_types["metadata"] == "TEXT"
        connection.close()

    def test_iter(self, populated_table: Table) -> None:
        results = list(populated_table)

        assert len(results) == 3

    def test_drop(self) -> None:
        connection = _create_in_memory_connection()
        connection.execute("CREATE TABLE disposable (id INTEGER PRIMARY KEY)")
        table = Table(connection, "disposable")

        table.drop()

        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='disposable'"
        ).fetchall()
        assert tables == []
        connection.close()


class TestDatabaseConnection:
    def test_initialization(self, sqlite_connection: sqlite3.Connection) -> None:
        conn = DatabaseConnection(sqlite_connection)

        assert conn.raw_connection is sqlite_connection

    def test_getitem_returns_table(self, sqlite_connection: sqlite3.Connection) -> None:
        conn = DatabaseConnection(sqlite_connection)

        table = conn["test_table"]

        assert isinstance(table, Table)
        assert table._table_name == "test_table"
        assert table._connection is sqlite_connection

    def test_query_execution(self) -> None:
        connection = _create_in_memory_connection()
        conn = DatabaseConnection(connection)

        conn.query("CREATE TABLE qtest (id INTEGER PRIMARY KEY)")

        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='qtest'"
        ).fetchall()
        assert tables == [("qtest",)]
        connection.close()

    def test_close(self) -> None:
        connection = _create_in_memory_connection()
        conn = DatabaseConnection(connection)

        conn.close()

        with pytest.raises(sqlite3.ProgrammingError):
            connection.execute("SELECT 1")

    def test_create_table_stub(self, sqlite_connection: sqlite3.Connection) -> None:
        conn = DatabaseConnection(sqlite_connection)

        conn.create_table("new_table")


class TestDatabaseManagerInitialization:
    @patch("core.database.manager.os.path.isfile", return_value=False)
    @patch("core.database.schema.create_database")
    def test_initialization_creates_database_if_not_exists(
        self,
        mock_create_db,
        mock_isfile,
        sample_database_config,
    ) -> None:
        db_connection = _create_versioned_connection("2", "linux")
        session_connection = _create_versioned_connection("2", "linux")

        with patch("core.database.manager.connect", return_value=db_connection):
            with patch(
                "core.database.manager.connect_memory", return_value=session_connection
            ):
                db_manager = DatabaseManager(**sample_database_config)

        mock_create_db.assert_called_once()
        assert db_manager.database_connection is db_connection
        assert db_manager.session_database is session_connection

    def test_connect_failure_raises_system_exit(self, sample_database_config) -> None:
        with patch("core.database.manager.connect", side_effect=Exception("fail")):
            with patch.object(DatabaseManager, "_log_connection_error") as mock_log:
                with pytest.raises(SystemExit):
                    DatabaseManager(**sample_database_config)

        mock_log.assert_called_once()


class TestDatabaseManagerVersionChecking:
    def test_version_mismatch_triggers_migration(self, sample_database_config) -> None:
        db_connection = _create_versioned_connection("1", "linux")
        session_connection = _create_versioned_connection("1", "linux")

        with patch("core.database.manager.connect", return_value=db_connection):
            with patch(
                "core.database.manager.connect_memory", return_value=session_connection
            ):
                with patch(
                    "core.database.manager.backup_increment.do_backup"
                ) as mock_backup:
                    with patch(
                        "core.database.manager.folders_database_migrator.upgrade_database"
                    ) as mock_migrator:
                        DatabaseManager(**sample_database_config)

        mock_backup.assert_called_once_with(sample_database_config["database_path"])
        mock_migrator.assert_called_once()

    def test_newer_database_version_exits(self, sample_database_config) -> None:
        db_connection = _create_versioned_connection("99", "linux")
        session_connection = _create_versioned_connection("99", "linux")

        with patch("core.database.manager.connect", return_value=db_connection):
            with patch(
                "core.database.manager.connect_memory", return_value=session_connection
            ):
                with pytest.raises(SystemExit):
                    DatabaseManager(**sample_database_config)

    def test_os_mismatch_exits(self, sample_database_config) -> None:
        db_connection = _create_versioned_connection("2", "windows")
        session_connection = _create_versioned_connection("2", "windows")

        with patch("core.database.manager.connect", return_value=db_connection):
            with patch(
                "core.database.manager.connect_memory", return_value=session_connection
            ):
                with pytest.raises(SystemExit):
                    DatabaseManager(**sample_database_config)

    def test_version_record_missing_raises(self, sample_database_config) -> None:
        connection = _create_in_memory_connection()
        connection.execute(
            "CREATE TABLE version (id INTEGER PRIMARY KEY, version TEXT, os TEXT)"
        )
        connection.commit()
        db_connection = DatabaseConnection(connection)
        session_connection = _create_versioned_connection("2", "linux")

        with patch("core.database.manager.connect", return_value=db_connection):
            with patch(
                "core.database.manager.connect_memory", return_value=session_connection
            ):
                with pytest.raises(RuntimeError):
                    DatabaseManager(**sample_database_config)


class TestDatabaseManagerTableReferences:
    def test_initialize_table_references(self) -> None:
        db_conn = _create_versioned_connection("2", "linux")

        with patch.object(DatabaseManager, "__init__", lambda x, **kwargs: None):
            db_manager = DatabaseManager.__new__(DatabaseManager)
            db_manager.database_connection = db_conn

            db_manager._initialize_table_references()

        assert db_manager.folders_table is not None
        assert db_manager.emails_table is not None
        assert db_manager.emails_table_batch is not None
        assert db_manager.sent_emails_removal_queue is not None
        assert db_manager.oversight_and_defaults is not None
        assert db_manager.processed_files is not None
        assert db_manager.settings is not None


class TestDatabaseManagerOperations:
    def test_reload_reconnects_database(self, sample_database_config) -> None:
        db_connection = _create_versioned_connection("2", "linux")
        session_connection = _create_versioned_connection("2", "linux")

        with patch.object(DatabaseManager, "__init__", lambda x, **kwargs: None):
            db_manager = DatabaseManager.__new__(DatabaseManager)
            db_manager._database_path = sample_database_config["database_path"]
            db_manager._app_version = sample_database_config["app_version"]
            db_manager.database_connection = None
            db_manager.session_database = None

            with patch("core.database.manager.connect", return_value=db_connection):
                with patch(
                    "core.database.manager.connect_memory",
                    return_value=session_connection,
                ):
                    with patch.object(
                        db_manager, "_initialize_table_references"
                    ) as init_tables:
                        db_manager.reload()

        assert db_manager.database_connection is db_connection
        assert db_manager.session_database is session_connection
        init_tables.assert_called_once()

    def test_close_closes_connections(self) -> None:
        with patch.object(DatabaseManager, "__init__", lambda x, **kwargs: None):
            db_manager = DatabaseManager.__new__(DatabaseManager)
            db_manager.database_connection = MagicMock()
            db_manager.session_database = MagicMock()

            db_manager.close()

        db_manager.database_connection.close.assert_called_once()
        db_manager.session_database.close.assert_called_once()


class TestDatabaseManagerContextManager:
    def test_context_manager_entry(self, sample_database_config) -> None:
        db_connection = _create_versioned_connection("2", "linux")
        session_connection = _create_versioned_connection("2", "linux")

        with patch("core.database.manager.connect", return_value=db_connection):
            with patch(
                "core.database.manager.connect_memory", return_value=session_connection
            ):
                with patch("core.database.manager.os.path.isfile", return_value=True):
                    db_manager = DatabaseManager(**sample_database_config)

        assert db_manager.__enter__() is db_manager

    def test_context_manager_exit(self) -> None:
        with patch.object(DatabaseManager, "__init__", lambda x, **kwargs: None):
            db_manager = DatabaseManager.__new__(DatabaseManager)
            db_manager.close = MagicMock()

            db_manager.__exit__(None, None, None)

        db_manager.close.assert_called_once()


class TestDatabaseManagerErrorHandling:
    def test_log_critical_error(self) -> None:
        with patch.object(DatabaseManager, "__init__", lambda x, **kwargs: None):
            db_manager = DatabaseManager.__new__(DatabaseManager)
            db_manager._app_version = "1.0.0"

            mock_file = mock_open()
            with patch("builtins.open", mock_file):
                with patch("core.database.manager.print"):
                    db_manager._log_critical_error(Exception("Test error"))

        mock_file.assert_called_once_with("critical_error.log", "a", encoding="utf-8")

    def test_log_connection_error(self) -> None:
        with patch.object(DatabaseManager, "__init__", lambda x, **kwargs: None):
            db_manager = DatabaseManager.__new__(DatabaseManager)
            db_manager._app_version = "1.0.0"

            mock_file = mock_open()
            with patch("builtins.open", mock_file):
                with patch("core.database.manager.print"):
                    db_manager._log_connection_error(Exception("Connection error"))

        mock_file.assert_called_once()

    def test_log_critical_error_handles_write_failure(self) -> None:
        with patch.object(DatabaseManager, "__init__", lambda x, **kwargs: None):
            db_manager = DatabaseManager.__new__(DatabaseManager)
            db_manager._app_version = "1.0.0"

            with patch("builtins.open", side_effect=IOError("Write failed")):
                with patch("core.database.manager.print"):
                    with pytest.raises(SystemExit):
                        db_manager._log_critical_error(Exception("Test error"))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
