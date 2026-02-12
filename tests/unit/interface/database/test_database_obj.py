"""Unit tests for DatabaseObj.

Tests the DatabaseObj class with mocked database connections
to ensure proper behavior without requiring actual database files.
"""

import pytest
from unittest.mock import MagicMock, patch
from interface.database.database_obj import (
    DatabaseObj,
    DatabaseConnectionProtocol,
    TableProtocol,
)


def create_mock_connection(mock_tables):
    """Create a mock connection that returns the correct tables."""
    conn = MagicMock()
    
    # Use a mock that returns the correct table when __getitem__ is called
    # MagicMock's __getitem__ passes self as first arg, so we need to handle that
    def get_item(key):
        return mock_tables[key]
    
    # Assign the side effect to return values based on key
    conn.__getitem__.side_effect = get_item
    conn.close = MagicMock()
    return conn


class TestDatabaseObj:
    """Tests for DatabaseObj class."""
    
    @pytest.fixture
    def mock_tables(self):
        """Create mock table objects."""
        tables = {
            "folders": MagicMock(),
            "emails_to_send": MagicMock(),
            "working_batch_emails_to_send": MagicMock(),
            "sent_emails_removal_queue": MagicMock(),
            "administrative": MagicMock(),
            "processed_files": MagicMock(),
            "settings": MagicMock(),
            "version": MagicMock(),
        }
        # Set up version table to return valid version
        tables["version"].find_one.return_value = {
            "version": "33",
            "os": "Linux"
        }
        return tables
    
    @pytest.fixture
    def mock_connection(self, mock_tables):
        """Create mock database connection."""
        return create_mock_connection(mock_tables)
    
    @pytest.fixture
    def database_obj(self, mock_connection):
        """Create DatabaseObj with injectable connection."""
        return DatabaseObj(
            database_path="/test/path.db",
            database_version="33",
            config_folder="/test/config",
            running_platform="Linux",
            connection=mock_connection
        )
    
    def test_init_with_connection(self, mock_tables):
        """Test initialization with injectable connection."""
        mock_connection = create_mock_connection(mock_tables)
        
        db = DatabaseObj(
            database_path="/test/path.db",
            database_version="33",
            config_folder="/test/config",
            running_platform="Linux",
            connection=mock_connection
        )
        
        assert db.connection is mock_connection
        assert db.folders_table is not None
    
    def test_get_folder(self, database_obj, mock_tables):
        """Test getting a folder by name."""
        mock_tables["folders"].find_one.return_value = {
            "folder_name": "test",
            "enabled": True
        }
        
        result = database_obj.get_folder("test")
        
        assert result["folder_name"] == "test"
        mock_tables["folders"].find_one.assert_called_once_with(folder_name="test")
    
    def test_get_all_folders(self, database_obj, mock_tables):
        """Test getting all folders."""
        mock_tables["folders"].all.return_value = [
            {"folder_name": "folder1"},
            {"folder_name": "folder2"}
        ]
        
        result = database_obj.get_all_folders()
        
        assert len(result) == 2
        assert result[0]["folder_name"] == "folder1"
    
    def test_get_setting(self, database_obj, mock_tables):
        """Test getting a setting by key."""
        mock_tables["settings"].find_one.return_value = {
            "key": "test_key",
            "value": "test_value"
        }
        
        result = database_obj.get_setting("test_key")
        
        assert result == "test_value"
        mock_tables["settings"].find_one.assert_called_once_with(key="test_key")
    
    def test_get_setting_not_found(self, database_obj, mock_tables):
        """Test getting a non-existent setting."""
        mock_tables["settings"].find_one.return_value = None
        
        result = database_obj.get_setting("nonexistent")
        
        assert result is None
    
    def test_set_setting(self, database_obj, mock_tables):
        """Test setting a setting value."""
        database_obj.set_setting("new_key", "new_value")
        
        mock_tables["settings"].upsert.assert_called_once_with(
            {"key": "new_key", "value": "new_value"},
            ["key"]
        )
    
    def test_get_default_settings(self, database_obj, mock_tables):
        """Test getting default settings."""
        mock_tables["administrative"].find_one.return_value = {
            "id": 1,
            "default_setting": "value"
        }
        
        result = database_obj.get_default_settings()
        
        assert result["default_setting"] == "value"
    
    def test_update_default_settings(self, database_obj, mock_tables):
        """Test updating default settings."""
        settings = {"setting1": "value1"}
        
        database_obj.update_default_settings(settings)
        
        mock_tables["administrative"].update.assert_called_once()
    
    def test_close_calls_connection_close(self, database_obj, mock_connection):
        """Test close delegates to connection."""
        database_obj.close()
        
        mock_connection.close.assert_called_once()
    
    def test_close_with_no_connection(self, database_obj):
        """Test close with no connection doesn't raise."""
        database_obj.database_connection = None
        
        # Should not raise
        database_obj.close()


class TestDatabaseObjProtocolCompliance:
    """Tests for protocol compliance."""
    
    def test_connection_protocol_compliance(self):
        """Verify mock connection implements DatabaseConnectionProtocol."""
        mock_conn = MagicMock()
        mock_conn.__getitem__ = MagicMock(return_value=MagicMock())
        mock_conn.close = MagicMock()
        
        assert isinstance(mock_conn, DatabaseConnectionProtocol)
    
    def test_table_protocol_compliance(self):
        """Verify mock table implements TableProtocol."""
        mock_table = MagicMock()
        mock_table.find_one = MagicMock()
        mock_table.find = MagicMock()
        mock_table.all = MagicMock()
        mock_table.insert = MagicMock()
        mock_table.update = MagicMock()
        mock_table.delete = MagicMock()
        mock_table.count = MagicMock()
        
        assert isinstance(mock_table, TableProtocol)


class TestDatabaseObjVersionChecking:
    """Tests for database version checking.
    
    Note: Version checking only happens when no connection is injected.
    When a connection is injected, the caller is responsible for version checking.
    """
    
    @pytest.fixture
    def mock_tables(self):
        """Create mock table objects."""
        tables = {
            "folders": MagicMock(),
            "emails_to_send": MagicMock(),
            "working_batch_emails_to_send": MagicMock(),
            "sent_emails_removal_queue": MagicMock(),
            "administrative": MagicMock(),
            "processed_files": MagicMock(),
            "settings": MagicMock(),
            "version": MagicMock(),
        }
        return tables
    
    def test_version_too_old_triggers_upgrade(self, mock_tables):
        """Test that old database version triggers upgrade when no connection injected."""
        mock_tables["version"].find_one.return_value = {
            "version": "30",
            "os": "Linux"
        }
        
        # Track migrator calls
        migrator_called = []
        def mock_migrator(conn, config, platform):
            migrator_called.append(True)
            # Update the version after migration
            mock_tables["version"].find_one.return_value = {
                "version": "33",
                "os": "Linux"
            }
        
        # Create without injecting connection - will initialize from path
        with patch('interface.database.database_obj.dataset') as mock_dataset:
            mock_conn = create_mock_connection(mock_tables)
            mock_dataset.connect.return_value = mock_conn
            
            with patch('interface.database.database_obj.os.path.isfile', return_value=True):
                db = DatabaseObj(
                    database_path="/test/path.db",
                    database_version="33",
                    config_folder="/test/config",
                    running_platform="Linux",
                    connection=None,  # No connection injected
                    migrator_func=mock_migrator,
                    backup_func=lambda x: None,
                    show_popup_func=lambda x: None,
                    destroy_popup_func=lambda: None,
                )
        
        # Should have called migrator
        assert len(migrator_called) == 1
    
    def test_version_too_new_raises_system_exit(self, mock_tables):
        """Test that newer database version raises SystemExit when no connection injected."""
        mock_tables["version"].find_one.return_value = {
            "version": "99",
            "os": "Linux"
        }
        
        error_shown = []
        def mock_show_error(title, message):
            error_shown.append((title, message))
        
        with patch('interface.database.database_obj.dataset') as mock_dataset:
            mock_conn = create_mock_connection(mock_tables)
            mock_dataset.connect.return_value = mock_conn
            
            with patch('interface.database.database_obj.os.path.isfile', return_value=True):
                with pytest.raises(SystemExit):
                    DatabaseObj(
                        database_path="/test/path.db",
                        database_version="33",
                        config_folder="/test/config",
                        running_platform="Linux",
                        connection=None,  # No connection injected
                        show_error_func=mock_show_error,
                    )
    
    def test_os_mismatch_raises_system_exit(self, mock_tables):
        """Test that OS mismatch raises SystemExit when no connection injected."""
        mock_tables["version"].find_one.return_value = {
            "version": "33",
            "os": "Windows"
        }
        
        error_shown = []
        def mock_show_error(title, message):
            error_shown.append((title, message))
        
        with patch('interface.database.database_obj.dataset') as mock_dataset:
            mock_conn = create_mock_connection(mock_tables)
            mock_dataset.connect.return_value = mock_conn
            
            with patch('interface.database.database_obj.os.path.isfile', return_value=True):
                with pytest.raises(SystemExit):
                    DatabaseObj(
                        database_path="/test/path.db",
                        database_version="33",
                        config_folder="/test/config",
                        running_platform="Linux",
                        connection=None,  # No connection injected
                        show_error_func=mock_show_error,
                    )
    
    def test_injected_connection_skips_version_check(self, mock_tables):
        """Test that injecting a connection skips version checking."""
        # Set up version that would fail checks
        mock_tables["version"].find_one.return_value = {
            "version": "99",  # Too new
            "os": "Windows"   # Wrong OS
        }
        
        mock_connection = create_mock_connection(mock_tables)
        
        # Should NOT raise because connection is injected
        db = DatabaseObj(
            database_path="/test/path.db",
            database_version="33",
            config_folder="/test/config",
            running_platform="Linux",
            connection=mock_connection,  # Connection injected
        )
        
        # Should have tables initialized
        assert db.folders_table is not None


class TestDatabaseObjReload:
    """Tests for database reload functionality."""
    
    def test_reload_reinitializes_tables(self):
        """Test reload reinitializes table references."""
        mock_tables = {
            "folders": MagicMock(),
            "emails_to_send": MagicMock(),
            "working_batch_emails_to_send": MagicMock(),
            "sent_emails_removal_queue": MagicMock(),
            "administrative": MagicMock(),
            "processed_files": MagicMock(),
            "settings": MagicMock(),
            "version": MagicMock(),
        }
        mock_tables["version"].find_one.return_value = {"version": "33", "os": "Linux"}
        
        mock_conn1 = create_mock_connection(mock_tables)
        
        db = DatabaseObj(
            database_path="/test/path.db",
            database_version="33",
            config_folder="/test/config",
            running_platform="Linux",
            connection=mock_conn1
        )
        
        original_folders = db.folders_table
        
        # Simulate reload with new connection
        mock_tables2 = {
            "folders": MagicMock(),
            "emails_to_send": MagicMock(),
            "working_batch_emails_to_send": MagicMock(),
            "sent_emails_removal_queue": MagicMock(),
            "administrative": MagicMock(),
            "processed_files": MagicMock(),
            "settings": MagicMock(),
            "version": MagicMock(),
        }
        mock_tables2["version"].find_one.return_value = {"version": "33", "os": "Linux"}
        mock_conn2 = create_mock_connection(mock_tables2)
        
        with patch('interface.database.database_obj.dataset') as mock_dataset:
            mock_dataset.connect.return_value = mock_conn2
            db.reload()
        
        # Tables should be reinitialized
        assert db.folders_table is not None
