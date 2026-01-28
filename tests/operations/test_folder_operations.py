"""
Tests for FolderOperations
"""

import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.fixture
def mock_db_manager():
    """Create a mock database manager."""
    db = Mock()
    db.oversight_and_defaults = Mock()
    db.folders_table = Mock()
    db.emails_table = Mock()
    db.processed_files = Mock()
    return db


class TestFolderOperationsImport:
    """Test FolderOperations can be imported."""

    def test_import(self):
        """Test FolderOperations can be imported."""
        from interface.operations.folder_operations import FolderOperations

        assert FolderOperations is not None


class TestFolderOperationsInit:
    """Test FolderOperations initialization."""

    def test_init(self, mock_db_manager):
        """Test FolderOperations can be initialized."""
        from interface.operations.folder_operations import FolderOperations

        ops = FolderOperations(mock_db_manager)
        assert ops.db_manager == mock_db_manager


class TestFolderOperationsAddFolder:
    """Test add_folder functionality."""

    def test_add_folder_creates_unique_alias(self, mock_db_manager):
        """Test add_folder creates unique alias when name exists."""
        from interface.operations.folder_operations import FolderOperations

        # Mock template settings
        mock_db_manager.oversight_and_defaults.find_one.return_value = {
            "id": 1,
            "folder_name": "template",
            "alias": "template",
            "logs_directory": "/logs",
            "setting1": "value1",
        }

        # First call returns existing, second returns None (unique)
        mock_db_manager.folders_table.find_one.side_effect = [
            {"id": 1, "alias": "TestFolder"},  # First alias exists
            None,  # Second alias (TestFolder 1) doesn't exist
            {"id": 2},  # Return after insert
        ]

        mock_db_manager.folders_table.insert.return_value = None

        ops = FolderOperations(mock_db_manager)
        result = ops.add_folder("/path/to/TestFolder")

        # Should have inserted with alias "TestFolder 1"
        assert mock_db_manager.folders_table.insert.called
        call_args = mock_db_manager.folders_table.insert.call_args[0][0]
        assert call_args["alias"] == "TestFolder 1"
        assert call_args["folder_name"] == "/path/to/TestFolder"

    def test_add_folder_uses_basename(self, mock_db_manager):
        """Test add_folder uses basename of path for alias."""
        from interface.operations.folder_operations import FolderOperations

        mock_db_manager.oversight_and_defaults.find_one.return_value = {
            "id": 1,
            "setting1": "value1",
        }
        mock_db_manager.folders_table.find_one.side_effect = [None, {"id": 1}]
        mock_db_manager.folders_table.insert.return_value = None

        ops = FolderOperations(mock_db_manager)
        ops.add_folder("/path/to/MyFolder")

        call_args = mock_db_manager.folders_table.insert.call_args[0][0]
        assert call_args["alias"] == "MyFolder"


class TestFolderOperationsBatchAdd:
    """Test batch_add_folders functionality."""

    def test_batch_add_folders(self, mock_db_manager):
        """Test batch_add_folders adds multiple folders."""
        from interface.operations.folder_operations import FolderOperations

        mock_db_manager.oversight_and_defaults.find_one.return_value = {"id": 1}
        mock_db_manager.folders_table.find_one.side_effect = [
            None,
            {"id": 1},  # Folder 1 doesn't exist, then returns after insert
            {"id": 2},  # Folder 2 already exists
            None,
            {"id": 3},  # Folder 3 doesn't exist, then returns after insert
        ]
        mock_db_manager.folders_table.insert.return_value = None

        ops = FolderOperations(mock_db_manager)
        with patch.object(
            ops, "folder_exists_by_path", side_effect=[False, True, False]
        ):
            added_ids, added, skipped = ops.batch_add_folders(
                ["/path/folder1", "/path/folder2", "/path/folder3"]
            )

        assert added == 2
        assert skipped == 1


class TestFolderOperationsUpdate:
    """Test update_folder functionality."""

    def test_update_folder_success(self, mock_db_manager):
        """Test update_folder updates existing folder."""
        from interface.operations.folder_operations import FolderOperations

        mock_db_manager.folders_table.find_one.return_value = {"id": 1, "alias": "test"}
        mock_db_manager.folders_table.update.return_value = None

        ops = FolderOperations(mock_db_manager)
        result = ops.update_folder(1, {"id": 1, "alias": "updated"})

        assert result is True
        mock_db_manager.folders_table.update.assert_called_once()

    def test_update_folder_not_found(self, mock_db_manager):
        """Test update_folder returns False for non-existent folder."""
        from interface.operations.folder_operations import FolderOperations

        mock_db_manager.folders_table.find_one.return_value = None

        ops = FolderOperations(mock_db_manager)
        result = ops.update_folder(999, {"id": 999})

        assert result is False
        mock_db_manager.folders_table.update.assert_not_called()


class TestFolderOperationsDelete:
    """Test delete_folder functionality."""

    def test_delete_folder_removes_related_records(self, mock_db_manager):
        """Test delete_folder removes folder and related records."""
        from interface.operations.folder_operations import FolderOperations

        mock_db_manager.folders_table.delete.return_value = None
        mock_db_manager.processed_files.delete.return_value = None
        mock_db_manager.emails_table.delete.return_value = None

        ops = FolderOperations(mock_db_manager)
        result = ops.delete_folder(1)

        assert result is True
        mock_db_manager.processed_files.delete.assert_called_once_with(folder_id=1)
        mock_db_manager.emails_table.delete.assert_called_once_with(folder_id=1)
        mock_db_manager.folders_table.delete.assert_called_once_with(id=1)


class TestFolderOperationsQuery:
    """Test query functionality."""

    def test_get_folder(self, mock_db_manager):
        """Test get_folder returns folder by id."""
        from interface.operations.folder_operations import FolderOperations

        expected = {"id": 1, "alias": "test"}
        mock_db_manager.folders_table.find_one.return_value = expected

        ops = FolderOperations(mock_db_manager)
        result = ops.get_folder(1)

        assert result == expected
        mock_db_manager.folders_table.find_one.assert_called_once_with(id=1)

    def test_get_all_folders(self, mock_db_manager):
        """Test get_all_folders returns all folders."""
        from interface.operations.folder_operations import FolderOperations

        expected = [{"id": 1, "alias": "folder1"}, {"id": 2, "alias": "folder2"}]
        mock_db_manager.folders_table.find.return_value = expected

        ops = FolderOperations(mock_db_manager)
        result = ops.get_all_folders()

        assert result == expected
        mock_db_manager.folders_table.find.assert_called_once_with(order_by="alias")

    def test_get_active_folders(self, mock_db_manager):
        """Test get_active_folders returns only active folders."""
        from interface.operations.folder_operations import FolderOperations

        expected = [{"id": 1, "alias": "active1", "folder_is_active": "True"}]
        mock_db_manager.folders_table.find.return_value = expected

        ops = FolderOperations(mock_db_manager)
        result = ops.get_active_folders()

        assert result == expected
        mock_db_manager.folders_table.find.assert_called_once_with(
            folder_is_active="True"
        )

    def test_get_inactive_folders(self, mock_db_manager):
        """Test get_inactive_folders returns only inactive folders."""
        from interface.operations.folder_operations import FolderOperations

        expected = [{"id": 2, "alias": "inactive1", "folder_is_active": "False"}]
        mock_db_manager.folders_table.find.return_value = expected

        ops = FolderOperations(mock_db_manager)
        result = ops.get_inactive_folders()

        assert result == expected
        mock_db_manager.folders_table.find.assert_called_once_with(
            folder_is_active="False"
        )


class TestFolderOperationsActiveState:
    """Test folder active state management."""

    def test_set_folder_active(self, mock_db_manager):
        """Test set_folder_active sets folder to active."""
        from interface.operations.folder_operations import FolderOperations

        mock_db_manager.folders_table.find_one.return_value = {
            "id": 1,
            "alias": "test",
            "folder_is_active": "False",
        }
        mock_db_manager.folders_table.update.return_value = None

        ops = FolderOperations(mock_db_manager)
        result = ops.set_folder_active(1, True)

        assert result is True
        # Check that update was called with folder_is_active = 'True'
        call_args = mock_db_manager.folders_table.update.call_args[0][0]
        assert call_args["folder_is_active"] == "True"

    def test_disable_folder(self, mock_db_manager):
        """Test disable_folder sets folder to inactive."""
        from interface.operations.folder_operations import FolderOperations

        mock_db_manager.folders_table.find_one.return_value = {
            "id": 1,
            "folder_is_active": "True",
        }
        mock_db_manager.folders_table.update.return_value = None

        ops = FolderOperations(mock_db_manager)
        result = ops.disable_folder(1)

        assert result is True
        call_args = mock_db_manager.folders_table.update.call_args[0][0]
        assert call_args["folder_is_active"] == "False"

    def test_enable_folder(self, mock_db_manager):
        """Test enable_folder sets folder to active."""
        from interface.operations.folder_operations import FolderOperations

        mock_db_manager.folders_table.find_one.return_value = {
            "id": 1,
            "folder_is_active": "False",
        }
        mock_db_manager.folders_table.update.return_value = None

        ops = FolderOperations(mock_db_manager)
        result = ops.enable_folder(1)

        assert result is True
        call_args = mock_db_manager.folders_table.update.call_args[0][0]
        assert call_args["folder_is_active"] == "True"


class TestFolderOperationsCounts:
    """Test folder count operations."""

    def test_get_folder_count_all(self, mock_db_manager):
        """Test get_folder_count returns total count."""
        from interface.operations.folder_operations import FolderOperations

        mock_db_manager.folders_table.count.return_value = 10

        ops = FolderOperations(mock_db_manager)
        result = ops.get_folder_count()

        assert result == 10
        mock_db_manager.folders_table.count.assert_called_once_with()

    def test_get_folder_count_active_only(self, mock_db_manager):
        """Test get_folder_count with active_only returns active count."""
        from interface.operations.folder_operations import FolderOperations

        mock_db_manager.folders_table.count.return_value = 5

        ops = FolderOperations(mock_db_manager)
        result = ops.get_folder_count(active_only=True)

        assert result == 5
        mock_db_manager.folders_table.count.assert_called_once_with(
            folder_is_active="True"
        )
