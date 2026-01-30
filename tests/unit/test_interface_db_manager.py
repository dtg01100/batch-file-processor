"""
Comprehensive unit tests for the interface database manager module.

These tests cover the DatabaseManager, DatabaseConnection, and Table classes
with extensive mocking of Qt SQL dependencies.
"""

import datetime
import os
import sys
from io import StringIO
from unittest.mock import MagicMock, Mock, patch, call, mock_open

import pytest

# Import the module under test
from interface.database.database_manager import (
    DatabaseManager,
    DatabaseConnection,
    Table,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_qsqldatabase():
    """Create a mock QSqlDatabase."""
    db = MagicMock()
    db.isOpen.return_value = True
    db.open.return_value = True
    db.close.return_value = None
    db.setDatabaseName.return_value = None
    db.lastError.return_value = MagicMock(text=MagicMock(return_value="Mock error"))
    return db


@pytest.fixture
def mock_qsqlquery():
    """Create a mock QSqlQuery."""
    query = MagicMock()
    query.exec.return_value = True
    query.prepare.return_value = None
    query.addBindValue.return_value = None
    query.next.return_value = False
    query.value.return_value = "test_value"
    query.record.return_value = MagicMock()
    query.lastError.return_value = MagicMock(text=MagicMock(return_value="Mock query error"))
    return query


@pytest.fixture
def sample_database_config():
    """Provide sample database configuration."""
    return {
        "database_path": "/test/db.sqlite",
        "config_folder": "/test/config",
        "platform": "linux",
        "app_version": "1.0.0",
        "database_version": "2",
    }


@pytest.fixture
def sample_table_data():
    """Provide sample table data."""
    return [
        {"id": 1, "name": "Test 1", "value": 100},
        {"id": 2, "name": "Test 2", "value": 200},
        {"id": 3, "name": "Test 3", "value": 300},
    ]


# =============================================================================
# Table Class Tests
# =============================================================================

class TestTable:
    """Tests for the Table class."""

    def test_initialization(self, mock_qsqldatabase):
        """Test Table initializes with correct database and table name."""
        table = Table(mock_qsqldatabase, "test_table")
        
        assert table.db is mock_qsqldatabase
        assert table.table_name == "test_table"

    def test_dict_to_where_empty(self, mock_qsqldatabase):
        """Test _dict_to_where with empty kwargs."""
        table = Table(mock_qsqldatabase, "test_table")
        
        where_clause, values = table._dict_to_where()
        
        assert where_clause == ""
        assert values == []

    def test_dict_to_where_single_condition(self, mock_qsqldatabase):
        """Test _dict_to_where with single condition."""
        table = Table(mock_qsqldatabase, "test_table")
        
        where_clause, values = table._dict_to_where(id=1)
        
        assert where_clause == ' WHERE "id" = ?'
        assert values == [1]

    def test_dict_to_where_multiple_conditions(self, mock_qsqldatabase):
        """Test _dict_to_where with multiple conditions."""
        table = Table(mock_qsqldatabase, "test_table")
        
        where_clause, values = table._dict_to_where(id=1, name="test", active=True)
        
        assert ' WHERE ' in where_clause
        assert '"id" = ?' in where_clause
        assert '"name" = ?' in where_clause
        assert '"active" = ?' in where_clause
        assert 1 in values
        assert "test" in values
        assert True in values

    def test_dict_to_set(self, mock_qsqldatabase):
        """Test _dict_to_set conversion."""
        table = Table(mock_qsqldatabase, "test_table")
        data = {"id": 1, "name": "test", "value": 100}
        
        columns, placeholders, values = table._dict_to_set(data)
        
        assert '"id"' in columns
        assert '"name"' in columns
        assert '"value"' in columns
        assert placeholders == "?, ?, ?"
        assert values == [1, "test", 100]

    def test_find_all(self, mock_qsqldatabase, mock_qsqlquery):
        """Test find() returns all rows."""
        table = Table(mock_qsqldatabase, "test_table")
        
        # Mock query execution
        mock_qsqlquery.exec.return_value = True
        mock_qsqlquery.next.side_effect = [True, True, False]
        
        # Mock record
        mock_record = MagicMock()
        mock_record.count.return_value = 2
        mock_record.fieldName.side_effect = ["id", "name"]
        mock_qsqlquery.record.return_value = mock_record
        mock_qsqlquery.value.side_effect = [1, "test1", 2, "test2"]
        
        with patch("interface.database.database_manager.QSqlQuery", return_value=mock_qsqlquery):
            results = table.find()
        
        assert len(results) == 2
        assert results[0]["id"] == 1
        assert results[0]["name"] == "test1"
        assert results[1]["id"] == 2
        assert results[1]["name"] == "test2"

    def test_find_with_conditions(self, mock_qsqldatabase, mock_qsqlquery):
        """Test find() with WHERE conditions."""
        table = Table(mock_qsqldatabase, "test_table")
        
        mock_qsqlquery.exec.return_value = True
        mock_qsqlquery.next.return_value = False
        
        with patch("interface.database.database_manager.QSqlQuery", return_value=mock_qsqlquery):
            results = table.find(id=1, active=True)
        
        mock_qsqlquery.prepare.assert_called_once()
        call_args = mock_qsqlquery.prepare.call_args[0][0]
        assert 'WHERE' in call_args
        assert '"id" = ?' in call_args
        assert '"active" = ?' in call_args

    def test_find_with_order_by(self, mock_qsqldatabase, mock_qsqlquery):
        """Test find() with ORDER BY clause."""
        table = Table(mock_qsqldatabase, "test_table")
        
        mock_qsqlquery.exec.return_value = True
        mock_qsqlquery.next.return_value = False
        
        with patch("interface.database.database_manager.QSqlQuery", return_value=mock_qsqlquery):
            results = table.find(order_by="name")
        
        call_args = mock_qsqlquery.prepare.call_args[0][0]
        assert 'ORDER BY "name"' in call_args

    def test_find_one_returns_single_row(self, mock_qsqldatabase, mock_qsqlquery):
        """Test find_one() returns single row."""
        table = Table(mock_qsqldatabase, "test_table")
        
        mock_qsqlquery.exec.return_value = True
        mock_qsqlquery.next.side_effect = [True, False]
        
        mock_record = MagicMock()
        mock_record.count.return_value = 2
        mock_record.fieldName.side_effect = ["id", "name"]
        mock_qsqlquery.record.return_value = mock_record
        mock_qsqlquery.value.side_effect = [1, "test1"]
        
        with patch("interface.database.database_manager.QSqlQuery", return_value=mock_qsqlquery):
            result = table.find_one(id=1)
        
        assert result["id"] == 1
        assert result["name"] == "test1"

    def test_find_one_returns_none(self, mock_qsqldatabase, mock_qsqlquery):
        """Test find_one() returns None when no match."""
        table = Table(mock_qsqldatabase, "test_table")
        
        mock_qsqlquery.exec.return_value = True
        mock_qsqlquery.next.return_value = False
        
        with patch("interface.database.database_manager.QSqlQuery", return_value=mock_qsqlquery):
            result = table.find_one(id=999)
        
        assert result is None

    def test_all_delegates_to_find(self, mock_qsqldatabase, mock_qsqlquery):
        """Test all() delegates to find()."""
        table = Table(mock_qsqldatabase, "test_table")
        
        mock_qsqlquery.exec.return_value = True
        mock_qsqlquery.next.return_value = False
        
        with patch("interface.database.database_manager.QSqlQuery", return_value=mock_qsqlquery):
            results = table.all()
        
        assert isinstance(results, list)

    def test_insert(self, mock_qsqldatabase, mock_qsqlquery):
        """Test insert() creates new row."""
        table = Table(mock_qsqldatabase, "test_table")
        
        mock_qsqlquery.exec.return_value = True
        data = {"id": 1, "name": "test", "value": 100}
        
        with patch("interface.database.database_manager.QSqlQuery", return_value=mock_qsqlquery):
            table.insert(data)
        
        mock_qsqlquery.prepare.assert_called_once()
        call_args = mock_qsqlquery.prepare.call_args[0][0]
        assert "INSERT INTO" in call_args
        assert "test_table" in call_args
        assert mock_qsqlquery.addBindValue.call_count == 3

    def test_insert_many(self, mock_qsqldatabase, mock_qsqlquery):
        """Test insert_many() inserts multiple rows."""
        table = Table(mock_qsqldatabase, "test_table")
        
        mock_qsqlquery.exec.return_value = True
        records = [
            {"id": 1, "name": "test1"},
            {"id": 2, "name": "test2"},
        ]
        
        with patch("interface.database.database_manager.QSqlQuery", return_value=mock_qsqlquery):
            table.insert_many(records)
        
        assert mock_qsqlquery.exec.call_count == 2

    def test_update(self, mock_qsqldatabase, mock_qsqlquery):
        """Test update() modifies rows."""
        table = Table(mock_qsqldatabase, "test_table")
        
        mock_qsqlquery.exec.return_value = True
        data = {"id": 1, "name": "updated", "value": 200}
        
        with patch("interface.database.database_manager.QSqlQuery", return_value=mock_qsqlquery):
            table.update(data, ["id"])
        
        mock_qsqlquery.prepare.assert_called_once()
        call_args = mock_qsqlquery.prepare.call_args[0][0]
        assert "UPDATE" in call_args
        assert "SET" in call_args
        assert "WHERE" in call_args

    def test_update_no_set_values(self, mock_qsqldatabase, mock_qsqlquery):
        """Test update() with no non-key values does nothing."""
        table = Table(mock_qsqldatabase, "test_table")
        
        data = {"id": 1}  # Only key, no values to set
        
        with patch("interface.database.database_manager.QSqlQuery", return_value=mock_qsqlquery):
            table.update(data, ["id"])
        
        mock_qsqlquery.prepare.assert_not_called()

    def test_delete_with_conditions(self, mock_qsqldatabase, mock_qsqlquery):
        """Test delete() with conditions."""
        table = Table(mock_qsqldatabase, "test_table")
        
        mock_qsqlquery.exec.return_value = True
        
        with patch("interface.database.database_manager.QSqlQuery", return_value=mock_qsqlquery):
            table.delete(id=1)
        
        mock_qsqlquery.prepare.assert_called_once()
        call_args = mock_qsqlquery.prepare.call_args[0][0]
        assert "DELETE FROM" in call_args
        assert "WHERE" in call_args

    def test_delete_all(self, mock_qsqldatabase, mock_qsqlquery):
        """Test delete() without conditions deletes all rows."""
        table = Table(mock_qsqldatabase, "test_table")
        
        mock_qsqlquery.exec.return_value = True
        
        with patch("interface.database.database_manager.QSqlQuery", return_value=mock_qsqlquery):
            table.delete()
        
        mock_qsqlquery.exec.assert_called_once()
        call_args = mock_qsqlquery.exec.call_args[0][0]
        assert "DELETE FROM" in call_args
        assert "WHERE" not in call_args

    def test_count(self, mock_qsqldatabase, mock_qsqlquery):
        """Test count() returns row count."""
        table = Table(mock_qsqldatabase, "test_table")
        
        mock_qsqlquery.exec.return_value = True
        mock_qsqlquery.next.return_value = True
        mock_qsqlquery.value.return_value = 42
        
        with patch("interface.database.database_manager.QSqlQuery", return_value=mock_qsqlquery):
            result = table.count()
        
        assert result == 42
        mock_qsqlquery.prepare.assert_called_once()
        call_args = mock_qsqlquery.prepare.call_args[0][0]
        assert "COUNT(*)" in call_args

    def test_count_with_conditions(self, mock_qsqldatabase, mock_qsqlquery):
        """Test count() with WHERE conditions."""
        table = Table(mock_qsqldatabase, "test_table")
        
        mock_qsqlquery.exec.return_value = True
        mock_qsqlquery.next.return_value = True
        mock_qsqlquery.value.return_value = 5
        
        with patch("interface.database.database_manager.QSqlQuery", return_value=mock_qsqlquery):
            result = table.count(active=True)
        
        assert result == 5
        call_args = mock_qsqlquery.prepare.call_args[0][0]
        assert "WHERE" in call_args

    def test_distinct(self, mock_qsqldatabase, mock_qsqlquery):
        """Test distinct() returns unique values."""
        table = Table(mock_qsqldatabase, "test_table")
        
        mock_qsqlquery.exec.return_value = True
        mock_qsqlquery.next.side_effect = [True, True, True, False]
        mock_qsqlquery.value.side_effect = ["value1", "value2", "value3"]
        
        with patch("interface.database.database_manager.QSqlQuery", return_value=mock_qsqlquery):
            results = table.distinct("category")
        
        assert results == ["value1", "value2", "value3"]

    def test_create_column_string(self, mock_qsqldatabase, mock_qsqlquery):
        """Test create_column() with String type."""
        table = Table(mock_qsqldatabase, "test_table")
        
        mock_qsqlquery.exec.return_value = True
        
        with patch("interface.database.database_manager.QSqlQuery", return_value=mock_qsqlquery):
            table.create_column("new_col", str)
        
        call_args = mock_qsqlquery.exec.call_args[0][0]
        assert "ALTER TABLE" in call_args
        assert "ADD COLUMN" in call_args
        assert "new_col" in call_args

    def test_create_column_integer(self, mock_qsqldatabase, mock_qsqlquery):
        """Test create_column() with Integer type."""
        table = Table(mock_qsqldatabase, "test_table")
        
        mock_qsqlquery.exec.return_value = True
        
        with patch("interface.database.database_manager.QSqlQuery", return_value=mock_qsqlquery):
            table.create_column("new_col", int)
        
        call_args = mock_qsqlquery.exec.call_args[0][0]
        assert "INTEGER" in call_args

    def test_iter(self, mock_qsqldatabase, mock_qsqlquery):
        """Test __iter__ allows iteration over table."""
        table = Table(mock_qsqldatabase, "test_table")
        
        mock_qsqlquery.exec.return_value = True
        mock_qsqlquery.next.return_value = False
        
        with patch("interface.database.database_manager.QSqlQuery", return_value=mock_qsqlquery):
            results = list(table)
        
        assert isinstance(results, list)


# =============================================================================
# DatabaseConnection Tests
# =============================================================================

class TestDatabaseConnection:
    """Tests for the DatabaseConnection class."""

    def test_initialization(self, mock_qsqldatabase):
        """Test DatabaseConnection initializes with database."""
        conn = DatabaseConnection(mock_qsqldatabase)
        
        assert conn.db is mock_qsqldatabase

    def test_getitem_returns_table(self, mock_qsqldatabase):
        """Test __getitem__ returns Table instance."""
        conn = DatabaseConnection(mock_qsqldatabase)
        
        table = conn["test_table"]
        
        assert isinstance(table, Table)
        assert table.table_name == "test_table"
        assert table.db is mock_qsqldatabase

    def test_query_execution(self, mock_qsqldatabase, mock_qsqlquery):
        """Test query() executes raw SQL."""
        conn = DatabaseConnection(mock_qsqldatabase)
        
        mock_qsqlquery.exec.return_value = True
        
        with patch("interface.database.database_manager.QSqlQuery", return_value=mock_qsqlquery):
            conn.query("SELECT * FROM test")
        
        mock_qsqlquery.exec.assert_called_once_with("SELECT * FROM test")

    def test_close(self, mock_qsqldatabase):
        """Test close() closes database connection."""
        conn = DatabaseConnection(mock_qsqldatabase)
        
        conn.close()
        
        mock_qsqldatabase.close.assert_called_once()

    def test_create_table_stub(self, mock_qsqldatabase):
        """Test create_table() is a stub for compatibility."""
        conn = DatabaseConnection(mock_qsqldatabase)
        
        # Should not raise
        conn.create_table("new_table")


# =============================================================================
# DatabaseManager Tests
# =============================================================================

class TestDatabaseManagerInitialization:
    """Tests for DatabaseManager initialization."""

    @patch("interface.database.database_manager.os.path.isfile")
    @patch("interface.database.database_manager.create_database")
    @patch("interface.database.database_manager.folders_database_migrator")
    @patch("interface.database.database_manager.backup_increment")
    @patch("interface.database.database_manager.QSqlDatabase")
    def test_initialization_creates_database_if_not_exists(
        self, mock_qsqldb_class, mock_backup, mock_migrator, mock_create_db, mock_isfile,
        sample_database_config
    ):
        """Test DatabaseManager creates database if file doesn't exist."""
        mock_isfile.return_value = False
        mock_db = MagicMock()
        mock_db.open.return_value = True
        mock_qsqldb_class.addDatabase.return_value = mock_db
        
        mock_create_db.do.return_value = None
        
        with patch("interface.database.database_manager.QSqlQuery") as mock_query_class:
            mock_query = MagicMock()
            mock_query.exec.return_value = True
            mock_query_class.return_value = mock_query
            
            # Mock version table query
            mock_version_table = MagicMock()
            mock_version_table.find_one.return_value = {
                "id": 1,
                "version": "2",
                "os": "linux"
            }
            
            with patch.object(DatabaseManager, '_initialize_table_references'):
                with patch.object(DatabaseManager, '_check_version_and_migrate'):
                    db_manager = DatabaseManager(**sample_database_config)
        
        mock_create_db.do.assert_called_once()

    @patch("interface.database.database_manager.os.path.isfile")
    @patch("interface.database.database_manager.QSqlDatabase")
    def test_initialization_connects_to_existing_database(
        self, mock_qsqldb_class, mock_isfile, sample_database_config
    ):
        """Test DatabaseManager connects to existing database."""
        mock_isfile.return_value = True
        mock_db = MagicMock()
        mock_db.open.return_value = True
        mock_qsqldb_class.addDatabase.return_value = mock_db
        
        with patch("interface.database.database_manager.QSqlQuery") as mock_query_class:
            mock_query = MagicMock()
            mock_query.exec.return_value = True
            mock_query_class.return_value = mock_query
            
            with patch.object(DatabaseManager, '_initialize_table_references'):
                with patch.object(DatabaseManager, '_check_version_and_migrate'):
                    db_manager = DatabaseManager(**sample_database_config)
        
        mock_qsqldb_class.addDatabase.assert_called()

    @patch("interface.database.database_manager.os.path.isfile")
    @patch("interface.database.database_manager.QSqlDatabase")
    def test_database_connection_failure(
        self, mock_qsqldb_class, mock_isfile, sample_database_config
    ):
        """Test DatabaseManager handles database connection failure."""
        mock_isfile.return_value = True
        mock_db = MagicMock()
        mock_db.open.return_value = False
        mock_db.lastError.return_value = MagicMock(
            text=MagicMock(return_value="Connection failed")
        )
        mock_qsqldb_class.addDatabase.return_value = mock_db
        
        with pytest.raises(SystemExit):
            with patch("interface.database.database_manager.print"):
                db_manager = DatabaseManager(**sample_database_config)


class TestDatabaseManagerVersionChecking:
    """Tests for DatabaseManager version checking."""

    @patch("interface.database.database_manager.os.path.isfile")
    @patch("interface.database.database_manager.QSqlDatabase")
    @patch("interface.database.database_manager.backup_increment")
    @patch("interface.database.database_manager.folders_database_migrator")
    def test_version_mismatch_triggers_migration(
        self, mock_migrator, mock_backup, mock_qsqldb_class, mock_isfile,
        sample_database_config
    ):
        """Test version mismatch triggers database migration."""
        mock_isfile.return_value = True
        mock_db = MagicMock()
        mock_db.open.return_value = True
        mock_qsqldb_class.addDatabase.return_value = mock_db
        
        with patch("interface.database.database_manager.QSqlQuery") as mock_query_class:
            mock_query = MagicMock()
            mock_query.exec.return_value = True
            mock_query_class.return_value = mock_query
            
            # Create db_manager and manually test version check
            db_conn = MagicMock()
            db_conn.query = MagicMock()
            
            # Setup version table mock - old version
            version_table = MagicMock()
            version_table.find_one.return_value = {
                "id": 1,
                "version": "1",  # Old version
                "os": "linux"
            }
            db_conn.__getitem__ = MagicMock(return_value=version_table)
            
            with patch.object(DatabaseManager, '_connect_to_database'):
                with patch("interface.database.database_manager.print"):
                    db_manager = DatabaseManager(**sample_database_config)
                    db_manager.database_connection = db_conn
                    db_manager._check_version_and_migrate()
        
        mock_backup.do_backup.assert_called_once()

    @patch("interface.database.database_manager.os.path.isfile")
    @patch("interface.database.database_manager.QSqlDatabase")
    def test_newer_database_version_exits(
        self, mock_qsqldb_class, mock_isfile, sample_database_config
    ):
        """Test newer database version causes SystemExit."""
        mock_isfile.return_value = True
        mock_db = MagicMock()
        mock_db.open.return_value = True
        mock_qsqldb_class.addDatabase.return_value = mock_db
        
        with patch("interface.database.database_manager.QSqlQuery") as mock_query_class:
            mock_query = MagicMock()
            mock_query.exec.return_value = True
            mock_query_class.return_value = mock_query
            
            db_conn = MagicMock()
            
            # Setup version table mock - newer version
            version_table = MagicMock()
            version_table.find_one.return_value = {
                "id": 1,
                "version": "99",  # Newer than app version "2"
                "os": "linux"
            }
            db_conn.__getitem__ = MagicMock(return_value=version_table)
            
            with patch.object(DatabaseManager, '_connect_to_database'):
                with pytest.raises(SystemExit):
                    with patch("interface.database.database_manager.print"):
                        db_manager = DatabaseManager(**sample_database_config)
                        db_manager.database_connection = db_conn
                        db_manager._check_version_and_migrate()

    @patch("interface.database.database_manager.os.path.isfile")
    @patch("interface.database.database_manager.QSqlDatabase")
    def test_os_mismatch_exits(
        self, mock_qsqldb_class, mock_isfile, sample_database_config
    ):
        """Test OS mismatch causes SystemExit."""
        mock_isfile.return_value = True
        mock_db = MagicMock()
        mock_db.open.return_value = True
        mock_qsqldb_class.addDatabase.return_value = mock_db
        
        with patch("interface.database.database_manager.QSqlQuery") as mock_query_class:
            mock_query = MagicMock()
            mock_query.exec.return_value = True
            mock_query_class.return_value = mock_query
            
            db_conn = MagicMock()
            
            # Setup version table mock - different OS
            version_table = MagicMock()
            version_table.find_one.return_value = {
                "id": 1,
                "version": "2",
                "os": "windows"  # Different from config "linux"
            }
            db_conn.__getitem__ = MagicMock(return_value=version_table)
            
            with patch.object(DatabaseManager, '_connect_to_database'):
                with pytest.raises(SystemExit):
                    with patch("interface.database.database_manager.print"):
                        db_manager = DatabaseManager(**sample_database_config)
                        db_manager.database_connection = db_conn
                        db_manager._check_version_and_migrate()


class TestDatabaseManagerTableReferences:
    """Tests for DatabaseManager table reference initialization."""

    def test_initialize_table_references(self):
        """Test table references are initialized correctly."""
        db_conn = MagicMock()
        
        with patch.object(DatabaseManager, '__init__', lambda x, **kwargs: None):
            db_manager = DatabaseManager.__new__(DatabaseManager)
            db_manager.database_connection = db_conn
            db_manager._database_path = "/test/db.sqlite"
            db_manager._config_folder = "/test/config"
            db_manager._platform = "linux"
            db_manager._app_version = "1.0.0"
            db_manager._database_version = "2"
            
            db_manager.folders_table = None
            db_manager.emails_table = None
            db_manager.emails_table_batch = None
            db_manager.sent_emails_removal_queue = None
            db_manager.oversight_and_defaults = None
            db_manager.processed_files = None
            db_manager.settings = None
            
            db_manager._initialize_table_references()
        
        assert db_manager.folders_table is not None
        assert db_manager.emails_table is not None
        assert db_manager.emails_table_batch is not None
        assert db_manager.sent_emails_removal_queue is not None
        assert db_manager.oversight_and_defaults is not None
        assert db_manager.processed_files is not None
        assert db_manager.settings is not None


class TestDatabaseManagerOperations:
    """Tests for DatabaseManager operations."""

    def test_get_template_returns_first_record(self):
        """Test get_template() returns first administrative record."""
        with patch.object(DatabaseManager, '__init__', lambda x, **kwargs: None):
            db_manager = DatabaseManager.__new__(DatabaseManager)
            
            mock_table = MagicMock()
            mock_table.all.return_value = [
                {"id": 1, "setting": "value1"},
                {"id": 2, "setting": "value2"},
            ]
            db_manager.oversight_and_defaults = mock_table
            
            result = db_manager.get_template()
        
        assert result["id"] == 1
        assert result["setting"] == "value1"

    def test_get_template_returns_none_when_empty(self):
        """Test get_template() returns None when no records."""
        with patch.object(DatabaseManager, '__init__', lambda x, **kwargs: None):
            db_manager = DatabaseManager.__new__(DatabaseManager)
            
            mock_table = MagicMock()
            mock_table.all.return_value = []
            db_manager.oversight_and_defaults = mock_table
            
            result = db_manager.get_template()
        
        assert result is None

    def test_get_template_returns_none_when_no_table(self):
        """Test get_template() returns None when table is None."""
        with patch.object(DatabaseManager, '__init__', lambda x, **kwargs: None):
            db_manager = DatabaseManager.__new__(DatabaseManager)
            db_manager.oversight_and_defaults = None
            
            result = db_manager.get_template()
        
        assert result is None

    @patch("interface.database.database_manager.QSqlDatabase")
    def test_reload_reconnects_database(self, mock_qsqldb_class):
        """Test reload() reconnects to database."""
        mock_db = MagicMock()
        mock_db.open.return_value = True
        mock_qsqldb_class.addDatabase.return_value = mock_db
        
        with patch.object(DatabaseManager, '__init__', lambda x, **kwargs: None):
            db_manager = DatabaseManager.__new__(DatabaseManager)
            db_manager._database_path = "/test/db.sqlite"
            db_manager._app_version = "1.0.0"
            db_manager.database_connection = None
            db_manager.session_database = None
            
            with patch("interface.database.database_manager.QSqlQuery") as mock_query_class:
                mock_query = MagicMock()
                mock_query.exec.return_value = True
                mock_query_class.return_value = mock_query
                
                with patch.object(db_manager, '_initialize_table_references'):
                    with patch("interface.database.database_manager.print"):
                        db_manager.reload()
        
        assert db_manager.database_connection is not None

    def test_close_closes_connection(self):
        """Test close() closes database connection."""
        with patch.object(DatabaseManager, '__init__', lambda x, **kwargs: None):
            db_manager = DatabaseManager.__new__(DatabaseManager)
            
            mock_conn = MagicMock()
            mock_conn.close = MagicMock()
            db_manager.database_connection = mock_conn
            
            db_manager.close()
        
        mock_conn.close.assert_called_once()


class TestDatabaseManagerContextManager:
    """Tests for DatabaseManager context manager."""

    @patch("interface.database.database_manager.os.path.isfile")
    @patch("interface.database.database_manager.QSqlDatabase")
    def test_context_manager_entry(self, mock_qsqldb_class, mock_isfile):
        """Test context manager __enter__ returns self."""
        mock_isfile.return_value = True
        mock_db = MagicMock()
        mock_db.open.return_value = True
        mock_qsqldb_class.addDatabase.return_value = mock_db
        
        with patch("interface.database.database_manager.QSqlQuery") as mock_query_class:
            mock_query = MagicMock()
            mock_query.exec.return_value = True
            mock_query_class.return_value = mock_query
            
            with patch.object(DatabaseManager, '_initialize_table_references'):
                with patch.object(DatabaseManager, '_check_version_and_migrate'):
                    db_manager = DatabaseManager(
                        database_path="/test/db.sqlite",
                        config_folder="/test/config",
                        platform="linux",
                        app_version="1.0.0",
                        database_version="2",
                    )
                    
                    result = db_manager.__enter__()
        
        assert result is db_manager

    @patch("interface.database.database_manager.os.path.isfile")
    @patch("interface.database.database_manager.QSqlDatabase")
    def test_context_manager_exit(self, mock_qsqldb_class, mock_isfile):
        """Test context manager __exit__ closes connection."""
        mock_isfile.return_value = True
        mock_db = MagicMock()
        mock_db.open.return_value = True
        mock_qsqldb_class.addDatabase.return_value = mock_db
        
        with patch("interface.database.database_manager.QSqlQuery") as mock_query_class:
            mock_query = MagicMock()
            mock_query.exec.return_value = True
            mock_query_class.return_value = mock_query
            
            with patch.object(DatabaseManager, '_initialize_table_references'):
                with patch.object(DatabaseManager, '_check_version_and_migrate'):
                    db_manager = DatabaseManager(
                        database_path="/test/db.sqlite",
                        config_folder="/test/config",
                        platform="linux",
                        app_version="1.0.0",
                        database_version="2",
                    )
                    
                    mock_conn = MagicMock()
                    db_manager.database_connection = mock_conn
                    
                    db_manager.__exit__(None, None, None)
        
        mock_conn.close.assert_called_once()


class TestDatabaseManagerErrorHandling:
    """Tests for DatabaseManager error handling."""

    def test_log_critical_error(self):
        """Test _log_critical_error writes to log file."""
        with patch.object(DatabaseManager, '__init__', lambda x, **kwargs: None):
            db_manager = DatabaseManager.__new__(DatabaseManager)
            db_manager._app_version = "1.0.0"
            
            mock_file = mock_open()
            with patch("builtins.open", mock_file):
                with patch("interface.database.database_manager.print"):
                    error = Exception("Test error")
                    db_manager._log_critical_error(error)
        
        mock_file.assert_called_once_with("critical_error.log", "a", encoding="utf-8")

    def test_log_connection_error(self):
        """Test _log_connection_error writes to log file."""
        with patch.object(DatabaseManager, '__init__', lambda x, **kwargs: None):
            db_manager = DatabaseManager.__new__(DatabaseManager)
            db_manager._app_version = "1.0.0"
            
            mock_file = mock_open()
            with patch("builtins.open", mock_file):
                with patch("interface.database.database_manager.print"):
                    error = Exception("Connection error")
                    db_manager._log_connection_error(error)
        
        mock_file.assert_called_once()

    def test_log_critical_error_handles_write_failure(self):
        """Test _log_critical_error handles write failure."""
        with patch.object(DatabaseManager, '__init__', lambda x, **kwargs: None):
            db_manager = DatabaseManager.__new__(DatabaseManager)
            db_manager._app_version = "1.0.0"
            
            with patch("builtins.open", side_effect=IOError("Write failed")):
                with patch("interface.database.database_manager.print"):
                    error = Exception("Test error")
                    with pytest.raises(SystemExit):
                        db_manager._log_critical_error(error)


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_table_query_error(self, mock_qsqldatabase, mock_qsqlquery):
        """Test Table handles query execution error."""
        table = Table(mock_qsqldatabase, "test_table")
        
        mock_qsqlquery.exec.return_value = False
        
        with patch("interface.database.database_manager.QSqlQuery", return_value=mock_qsqlquery):
            with pytest.raises(RuntimeError) as exc_info:
                table.find()
            
            assert "Query failed" in str(exc_info.value)

    def test_table_insert_error(self, mock_qsqldatabase, mock_qsqlquery):
        """Test Table handles insert error."""
        table = Table(mock_qsqldatabase, "test_table")
        
        mock_qsqlquery.exec.return_value = False
        
        with patch("interface.database.database_manager.QSqlQuery", return_value=mock_qsqlquery):
            with pytest.raises(RuntimeError) as exc_info:
                table.insert({"id": 1})
            
            assert "Insert failed" in str(exc_info.value)

    def test_table_update_error(self, mock_qsqldatabase, mock_qsqlquery):
        """Test Table handles update error."""
        table = Table(mock_qsqldatabase, "test_table")
        
        mock_qsqlquery.exec.return_value = False
        
        with patch("interface.database.database_manager.QSqlQuery", return_value=mock_qsqlquery):
            with pytest.raises(RuntimeError) as exc_info:
                table.update({"id": 1, "name": "test"}, ["id"])
            
            assert "Update failed" in str(exc_info.value)

    def test_table_delete_error(self, mock_qsqldatabase, mock_qsqlquery):
        """Test Table handles delete error."""
        table = Table(mock_qsqldatabase, "test_table")
        
        mock_qsqlquery.exec.return_value = False
        
        with patch("interface.database.database_manager.QSqlQuery", return_value=mock_qsqlquery):
            with pytest.raises(RuntimeError) as exc_info:
                table.delete(id=1)
            
            assert "Delete failed" in str(exc_info.value)

    def test_table_count_error(self, mock_qsqldatabase, mock_qsqlquery):
        """Test Table handles count error."""
        table = Table(mock_qsqldatabase, "test_table")
        
        mock_qsqlquery.exec.return_value = False
        
        with patch("interface.database.database_manager.QSqlQuery", return_value=mock_qsqlquery):
            with pytest.raises(RuntimeError) as exc_info:
                table.count()
            
            assert "Count failed" in str(exc_info.value)

    def test_table_distinct_error(self, mock_qsqldatabase, mock_qsqlquery):
        """Test Table handles distinct error."""
        table = Table(mock_qsqldatabase, "test_table")
        
        mock_qsqlquery.exec.return_value = False
        
        with patch("interface.database.database_manager.QSqlQuery", return_value=mock_qsqlquery):
            with pytest.raises(RuntimeError) as exc_info:
                table.distinct("column")
            
            assert "Distinct query failed" in str(exc_info.value)

    def test_create_column_with_unknown_type(self, mock_qsqldatabase, mock_qsqlquery):
        """Test create_column defaults to TEXT for unknown types."""
        table = Table(mock_qsqldatabase, "test_table")
        
        mock_qsqlquery.exec.return_value = True
        
        with patch("interface.database.database_manager.QSqlQuery", return_value=mock_qsqlquery):
            table.create_column("new_col", list)  # Unknown type
        
        call_args = mock_qsqlquery.exec.call_args[0][0]
        assert "TEXT" in call_args


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
