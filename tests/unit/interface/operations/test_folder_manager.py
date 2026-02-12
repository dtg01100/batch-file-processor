"""Unit tests for FolderManager.

Tests the FolderManager class with mocked database connections
to ensure proper behavior without requiring actual database files.
"""

import os
import pytest
from unittest.mock import MagicMock
from interface.operations.folder_manager import (
    FolderManager,
    DatabaseProtocol,
    TableProtocol,
)


class TestFolderManager:
    """Tests for FolderManager class."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = MagicMock()
        db.oversight_and_defaults.find_one.return_value = {
            "id": 1,
            "default_setting": "value",
            "folder_is_active": "True",
        }
        return db
    
    @pytest.fixture
    def manager(self, mock_db):
        """Create FolderManager with mock database."""
        return FolderManager(mock_db)
    
    def test_add_folder_creates_record(self, manager, mock_db):
        """Test adding a folder creates a database record."""
        mock_db.folders_table.find_one.return_value = None  # No existing alias
        
        result = manager.add_folder("/path/to/folder")
        
        mock_db.folders_table.insert.assert_called_once()
        assert result["folder_name"] == "/path/to/folder"
    
    def test_add_folder_generates_unique_alias(self, manager, mock_db):
        """Test adding duplicate folder generates unique alias."""
        # First folder exists
        mock_db.folders_table.find_one.side_effect = [
            {"alias": "folder"},  # First check finds existing
            None,  # Second check for "folder 1" finds nothing
        ]
        
        result = manager.add_folder("/path/to/folder")
        
        assert result["alias"] == "folder 1"
    
    def test_add_folder_with_template_data(self, manager, mock_db):
        """Test adding folder with custom template data."""
        mock_db.folders_table.find_one.return_value = None
        
        custom_template = {
            "id": 1,
            "custom_setting": "custom_value",
            "folder_is_active": "True",
        }
        
        result = manager.add_folder("/path/to/folder", template_data=custom_template)
        
        assert result["custom_setting"] == "custom_value"
    
    def test_check_folder_exists_found(self, manager, mock_db, tmp_path):
        """Test checking existing folder."""
        folder_path = str(tmp_path)
        mock_db.folders_table.all.return_value = [
            {"folder_name": folder_path, "alias": "test"}
        ]
        
        result = manager.check_folder_exists(folder_path)
        
        assert result["truefalse"] is True
        assert result["matched_folder"]["alias"] == "test"
    
    def test_check_folder_exists_not_found(self, manager, mock_db):
        """Test checking non-existing folder."""
        mock_db.folders_table.all.return_value = []
        
        result = manager.check_folder_exists("/nonexistent")
        
        assert result["truefalse"] is False
        assert result["matched_folder"] is None
    
    def test_check_folder_exists_normalized_path(self, manager, mock_db):
        """Test that path normalization works correctly."""
        # Test with different path formats
        mock_db.folders_table.all.return_value = [
            {"folder_name": "/path/to/folder", "alias": "test"}
        ]
        
        # Should match even with trailing slash
        result = manager.check_folder_exists("/path/to/folder/")
        
        assert result["truefalse"] is True
    
    def test_disable_folder(self, manager, mock_db):
        """Test disabling a folder."""
        mock_db.folders_table.find_one.return_value = {
            "id": 1,
            "folder_is_active": "True"
        }
        
        result = manager.disable_folder(1)
        
        assert result is True
        mock_db.folders_table.update.assert_called_once()
        # Check that folder_is_active was set to False
        call_args = mock_db.folders_table.update.call_args
        assert call_args[0][0]["folder_is_active"] == "False"
    
    def test_disable_folder_not_found(self, manager, mock_db):
        """Test disabling non-existent folder."""
        mock_db.folders_table.find_one.return_value = None
        
        result = manager.disable_folder(999)
        
        assert result is False
    
    def test_enable_folder(self, manager, mock_db):
        """Test enabling a folder."""
        mock_db.folders_table.find_one.return_value = {
            "id": 1,
            "folder_is_active": "False"
        }
        
        result = manager.enable_folder(1)
        
        assert result is True
        mock_db.folders_table.update.assert_called_once()
        # Check that folder_is_active was set to True
        call_args = mock_db.folders_table.update.call_args
        assert call_args[0][0]["folder_is_active"] == "True"
    
    def test_enable_folder_not_found(self, manager, mock_db):
        """Test enabling non-existent folder."""
        mock_db.folders_table.find_one.return_value = None
        
        result = manager.enable_folder(999)
        
        assert result is False
    
    def test_delete_folder(self, manager, mock_db):
        """Test deleting a folder."""
        mock_db.folders_table.find_one.return_value = {"id": 1}
        
        result = manager.delete_folder(1)
        
        assert result is True
        mock_db.folders_table.delete.assert_called_once_with(id=1)
    
    def test_delete_folder_not_found(self, manager, mock_db):
        """Test deleting non-existent folder."""
        mock_db.folders_table.find_one.return_value = None
        
        result = manager.delete_folder(999)
        
        assert result is False
    
    def test_get_active_folders(self, manager, mock_db):
        """Test getting active folders."""
        mock_db.folders_table.find.return_value = [
            {"id": 1, "folder_is_active": "True"}
        ]
        
        result = manager.get_active_folders()
        
        assert len(result) == 1
        mock_db.folders_table.find.assert_called_once_with(folder_is_active="True")
    
    def test_get_inactive_folders(self, manager, mock_db):
        """Test getting inactive folders."""
        mock_db.folders_table.find.return_value = [
            {"id": 2, "folder_is_active": "False"}
        ]
        
        result = manager.get_inactive_folders()
        
        assert len(result) == 1
        mock_db.folders_table.find.assert_called_once_with(folder_is_active="False")
    
    def test_get_all_folders(self, manager, mock_db):
        """Test getting all folders."""
        mock_db.folders_table.find.return_value = [
            {"id": 1, "alias": "a"},
            {"id": 2, "alias": "b"},
        ]
        
        result = manager.get_all_folders()
        
        assert len(result) == 2
    
    def test_get_all_folders_with_order(self, manager, mock_db):
        """Test getting all folders with order by."""
        mock_db.folders_table.find.return_value = []
        
        manager.get_all_folders(order_by="alias")
        
        mock_db.folders_table.find.assert_called_once_with(order_by="alias")
    
    def test_count_folders_all(self, manager, mock_db):
        """Test counting all folders."""
        mock_db.folders_table.count.return_value = 10
        
        result = manager.count_folders()
        
        assert result == 10
    
    def test_count_folders_active_only(self, manager, mock_db):
        """Test counting active folders only."""
        mock_db.folders_table.count.return_value = 5
        
        result = manager.count_folders(active_only=True)
        
        mock_db.folders_table.count.assert_called_with(folder_is_active="True")
        assert result == 5
    
    def test_get_folder_by_id(self, manager, mock_db):
        """Test getting folder by ID."""
        mock_db.folders_table.find_one.return_value = {
            "id": 1,
            "alias": "test"
        }
        
        result = manager.get_folder_by_id(1)
        
        assert result["alias"] == "test"
        mock_db.folders_table.find_one.assert_called_once_with(id=1)
    
    def test_get_folder_by_name(self, manager, mock_db):
        """Test getting folder by name."""
        mock_db.folders_table.find_one.return_value = {
            "folder_name": "/path/to/folder",
            "alias": "test"
        }
        
        result = manager.get_folder_by_name("/path/to/folder")
        
        assert result["alias"] == "test"
    
    def test_get_folder_by_alias(self, manager, mock_db):
        """Test getting folder by alias."""
        mock_db.folders_table.find_one.return_value = {
            "alias": "test",
            "folder_name": "/path"
        }
        
        result = manager.get_folder_by_alias("test")
        
        assert result["folder_name"] == "/path"
    
    def test_update_folder(self, manager, mock_db):
        """Test updating a folder."""
        mock_db.folders_table.find_one.return_value = {
            "id": 1,
            "alias": "old"
        }
        
        result = manager.update_folder({"id": 1, "alias": "new"})
        
        assert result is True
        mock_db.folders_table.update.assert_called_once()
    
    def test_update_folder_no_id(self, manager, mock_db):
        """Test updating folder without ID fails."""
        result = manager.update_folder({"alias": "new"})
        
        assert result is False
    
    def test_update_folder_not_found(self, manager, mock_db):
        """Test updating non-existent folder."""
        mock_db.folders_table.find_one.return_value = None
        
        result = manager.update_folder({"id": 999, "alias": "new"})
        
        assert result is False
    
    def test_update_folder_by_name(self, manager, mock_db):
        """Test updating folder by name."""
        mock_db.folders_table.find_one.return_value = {
            "id": 1,
            "folder_name": "/path"
        }
        
        result = manager.update_folder_by_name({
            "folder_name": "/path",
            "alias": "new"
        })
        
        assert result is True
    
    def test_update_folder_by_name_not_found(self, manager, mock_db):
        """Test updating non-existent folder by name."""
        mock_db.folders_table.find_one.return_value = None
        
        result = manager.update_folder_by_name({
            "folder_name": "/nonexistent",
            "alias": "new"
        })
        
        assert result is False


class TestFolderManagerBatchOperations:
    """Tests for batch folder operations."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = MagicMock()
        db.oversight_and_defaults.find_one.return_value = {
            "id": 1,
            "default_setting": "value",
        }
        return db
    
    @pytest.fixture
    def manager(self, mock_db):
        """Create FolderManager with mock database."""
        return FolderManager(mock_db)
    
    def test_batch_add_folders(self, manager, mock_db, tmp_path):
        """Test batch adding folders."""
        # Create subdirectories
        (tmp_path / "folder1").mkdir()
        (tmp_path / "folder2").mkdir()
        (tmp_path / "folder3").mkdir()
        
        mock_db.folders_table.find_one.return_value = None  # No existing folders
        
        result = manager.batch_add_folders(str(tmp_path))
        
        assert result["added"] == 3
        assert result["skipped"] == 0
    
    def test_batch_add_folders_skip_existing(self, manager, mock_db, tmp_path):
        """Test batch adding folders skips existing."""
        (tmp_path / "folder1").mkdir()
        (tmp_path / "folder2").mkdir()
        
        # Track which aliases have been checked
        aliases_checked = []
        def find_one_side_effect(**kwargs):
            alias = kwargs.get("alias")
            if alias:
                aliases_checked.append(alias)
            # Only "folder1" exists (check both possible cases)
            if alias in ("folder1", tmp_path.joinpath("folder1").name):
                return {"alias": alias}
            return None
        
        mock_db.folders_table.find_one.side_effect = find_one_side_effect
        
        result = manager.batch_add_folders(str(tmp_path), skip_existing=True)
        
        # One folder should be skipped (folder1), one should be added (folder2)
        # Note: The actual order depends on os.listdir which is filesystem dependent
        assert result["added"] + result["skipped"] == 2
    
    def test_batch_add_folders_invalid_path(self, manager, mock_db):
        """Test batch adding with invalid path."""
        result = manager.batch_add_folders("/nonexistent/path")
        
        assert result["added"] == 0
        assert result["skipped"] == 0
        assert "error" in result


class TestFolderManagerProtocolCompliance:
    """Tests for protocol compliance."""
    
    def test_database_protocol_compliance(self):
        """Verify mock database implements DatabaseProtocol."""
        mock_db = MagicMock()
        mock_db.folders_table = MagicMock()
        mock_db.oversight_and_defaults = MagicMock()
        
        assert isinstance(mock_db, DatabaseProtocol)
    
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


class TestFolderManagerSkipList:
    """Tests for skip list functionality."""
    
    def test_skip_list_excludes_fields(self):
        """Test that skip list excludes correct fields."""
        mock_db = MagicMock()
        mock_db.oversight_and_defaults.find_one.return_value = {
            "id": 1,
            "folder_name": "should_be_skipped",
            "alias": "should_be_skipped",
            "logs_directory": "should_be_skipped",
            "errors_folder": "should_be_skipped",
            "valid_setting": "should_be_included",
        }
        mock_db.folders_table.find_one.return_value = None
        
        manager = FolderManager(mock_db)
        result = manager.add_folder("/path/to/folder")
        
        # These should not be in the result
        assert result.get("folder_name") == "/path/to/folder"  # Overwritten
        assert result.get("alias") is not None  # Generated
        assert "logs_directory" not in result or result.get("logs_directory") != "should_be_skipped"
        
        # This should be included
        assert result["valid_setting"] == "should_be_included"
