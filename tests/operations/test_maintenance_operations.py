"""
Tests for MaintenanceOperations
"""

import datetime
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.fixture
def mock_db_manager():
    """Create a mock database manager."""
    db = Mock()
    db.folders_table = Mock()
    db.processed_files = Mock()
    db.emails_table = Mock()
    db.database_connection = Mock()
    return db


class TestMaintenanceOperationsImport:
    """Test MaintenanceOperations can be imported."""

    def test_import(self):
        """Test MaintenanceOperations can be imported."""
        from interface.operations.maintenance import MaintenanceOperations

        assert MaintenanceOperations is not None


class TestMaintenanceOperationsInit:
    """Test MaintenanceOperations initialization."""

    def test_init(self, mock_db_manager):
        """Test MaintenanceOperations can be initialized."""
        from interface.operations.maintenance import MaintenanceOperations

        ops = MaintenanceOperations(mock_db_manager)
        assert ops.db_manager == mock_db_manager


class TestMaintenanceOperationsMarkAsProcessed:
    """Test mark_all_as_processed functionality."""

    @patch("os.chdir")
    @patch("os.getcwd")
    @patch("os.listdir")
    @patch("os.path.isfile")
    @patch("os.path.abspath")
    @patch("builtins.open", new_callable=mock_open, read_data=b"test content")
    def test_mark_all_as_processed_single_folder(
        self,
        mock_file,
        mock_abspath,
        mock_isfile,
        mock_listdir,
        mock_getcwd,
        mock_chdir,
        mock_db_manager,
    ):
        """Test mark_all_as_processed marks files in folder."""
        from interface.operations.maintenance import MaintenanceOperations

        # Setup mocks
        mock_getcwd.return_value = "/test/folder"
        mock_listdir.return_value = ["file1.txt", "file2.txt"]
        mock_isfile.return_value = True
        mock_abspath.side_effect = lambda x: f"/test/folder/{x}"

        mock_db_manager.folders_table.find_one.return_value = {
            "id": 1,
            "alias": "test_folder",
            "folder_name": "/test/folder",
        }
        mock_db_manager.processed_files.find_one.return_value = None
        mock_db_manager.processed_files.insert.return_value = None

        ops = MaintenanceOperations(mock_db_manager)
        count = ops.mark_all_as_processed(folder_id=1)

        # Should have marked 2 files as processed
        assert count == 2
        assert mock_db_manager.processed_files.insert.call_count == 2

    @patch("os.chdir")
    @patch("os.getcwd")
    def test_mark_all_as_processed_all_active(
        self, mock_getcwd, mock_chdir, mock_db_manager
    ):
        """Test mark_all_as_processed processes all active folders when no folder_id given."""
        from interface.operations.maintenance import MaintenanceOperations

        mock_getcwd.return_value = "/start"
        mock_db_manager.folders_table.find.return_value = [
            {"id": 1, "alias": "folder1", "folder_name": "/folder1"},
            {"id": 2, "alias": "folder2", "folder_name": "/folder2"},
        ]

        with (
            patch("os.listdir", return_value=[]),
            patch("os.path.isfile", return_value=True),
        ):
            ops = MaintenanceOperations(mock_db_manager)
            ops.mark_all_as_processed(folder_id=None)

            # Should have queried for active folders
            mock_db_manager.folders_table.find.assert_called_once_with(
                folder_is_active="True"
            )


class TestMaintenanceOperationsRemoveInactive:
    """Test remove_inactive_folders functionality."""

    def test_remove_inactive_folders(self, mock_db_manager):
        """Test remove_inactive_folders removes inactive folders."""
        from interface.operations.maintenance import MaintenanceOperations

        inactive_folders = [
            {"id": 1, "alias": "inactive1"},
            {"id": 2, "alias": "inactive2"},
            {"id": 3, "alias": "inactive3"},
        ]
        mock_db_manager.folders_table.find.return_value = inactive_folders
        mock_db_manager.folders_table.delete.return_value = None
        mock_db_manager.processed_files.delete.return_value = None
        mock_db_manager.emails_table.delete.return_value = None

        ops = MaintenanceOperations(mock_db_manager)
        count = ops.remove_inactive_folders()

        assert count == 3
        assert mock_db_manager.folders_table.delete.call_count == 3
        assert mock_db_manager.processed_files.delete.call_count == 3
        assert mock_db_manager.emails_table.delete.call_count == 3


class TestMaintenanceOperationsSetAllActive:
    """Test set_all_active functionality."""

    def test_set_all_active(self, mock_db_manager):
        """Test set_all_active sets all folders to active."""
        from interface.operations.maintenance import MaintenanceOperations

        mock_db_manager.folders_table.count.side_effect = [2, 5]  # Before and after
        mock_db_manager.database_connection.query.return_value = None

        ops = MaintenanceOperations(mock_db_manager)
        count = ops.set_all_active()

        assert count == 3  # 5 - 2 = 3 newly activated
        mock_db_manager.database_connection.query.assert_called_once()


class TestMaintenanceOperationsSetAllInactive:
    """Test set_all_inactive functionality."""

    def test_set_all_inactive(self, mock_db_manager):
        """Test set_all_inactive sets all folders to inactive."""
        from interface.operations.maintenance import MaintenanceOperations

        mock_db_manager.folders_table.count.side_effect = [3, 8]  # Before and after
        mock_db_manager.database_connection.query.return_value = None

        ops = MaintenanceOperations(mock_db_manager)
        count = ops.set_all_inactive()

        assert count == 5  # 8 - 3 = 5 newly deactivated
        mock_db_manager.database_connection.query.assert_called_once()


class TestMaintenanceOperationsClearOperations:
    """Test clear operations."""

    def test_clear_resend_flags(self, mock_db_manager):
        """Test clear_resend_flags clears all resend flags."""
        from interface.operations.maintenance import MaintenanceOperations

        mock_db_manager.processed_files.count.side_effect = [10, 0]  # Before and after
        mock_db_manager.database_connection.query.return_value = None

        ops = MaintenanceOperations(mock_db_manager)
        count = ops.clear_resend_flags()

        assert count == 10
        mock_db_manager.database_connection.query.assert_called_once()

    def test_clear_emails_queue(self, mock_db_manager):
        """Test clear_emails_queue clears all queued emails."""
        from interface.operations.maintenance import MaintenanceOperations

        mock_db_manager.emails_table.count.return_value = 5
        mock_db_manager.emails_table.delete.return_value = None

        ops = MaintenanceOperations(mock_db_manager)
        count = ops.clear_emails_queue()

        assert count == 5
        mock_db_manager.emails_table.delete.assert_called_once()

    def test_clear_all_processed_files(self, mock_db_manager):
        """Test clear_all_processed_files clears all processed file records."""
        from interface.operations.maintenance import MaintenanceOperations

        mock_db_manager.processed_files.count.return_value = 100
        mock_db_manager.processed_files.delete.return_value = None

        ops = MaintenanceOperations(mock_db_manager)
        count = ops.clear_all_processed_files()

        assert count == 100
        mock_db_manager.processed_files.delete.assert_called_once()


class TestMaintenanceOperationsCounts:
    """Test count operations."""

    def test_get_processed_files_count(self, mock_db_manager):
        """Test get_processed_files_count returns count."""
        from interface.operations.maintenance import MaintenanceOperations

        mock_db_manager.processed_files.count.return_value = 42

        ops = MaintenanceOperations(mock_db_manager)
        count = ops.get_processed_files_count()

        assert count == 42

    def test_get_inactive_folders_count(self, mock_db_manager):
        """Test get_inactive_folders_count returns count."""
        from interface.operations.maintenance import MaintenanceOperations

        mock_db_manager.folders_table.count.return_value = 7

        ops = MaintenanceOperations(mock_db_manager)
        count = ops.get_inactive_folders_count()

        assert count == 7
        mock_db_manager.folders_table.count.assert_called_once_with(
            folder_is_active="False"
        )

    def test_get_active_folders_count(self, mock_db_manager):
        """Test get_active_folders_count returns count."""
        from interface.operations.maintenance import MaintenanceOperations

        mock_db_manager.folders_table.count.return_value = 12

        ops = MaintenanceOperations(mock_db_manager)
        count = ops.get_active_folders_count()

        assert count == 12
        mock_db_manager.folders_table.count.assert_called_once_with(
            folder_is_active="True"
        )

    def test_get_pending_emails_count(self, mock_db_manager):
        """Test get_pending_emails_count returns count."""
        from interface.operations.maintenance import MaintenanceOperations

        mock_db_manager.emails_table.count.return_value = 5

        ops = MaintenanceOperations(mock_db_manager)
        count = ops.get_pending_emails_count()

        assert count == 5

    def test_get_resend_files_count(self, mock_db_manager):
        """Test get_resend_files_count returns count."""
        from interface.operations.maintenance import MaintenanceOperations

        mock_db_manager.processed_files.count.return_value = 3

        ops = MaintenanceOperations(mock_db_manager)
        count = ops.get_resend_files_count()

        assert count == 3
        mock_db_manager.processed_files.count.assert_called_once_with(resend_flag=True)


class TestMaintenanceOperationsEdgeCases:
    """Edge case tests for MaintenanceOperations."""

    def test_mark_all_as_processed_folder_not_found(self, mock_db_manager):
        """Test mark_all_as_processed when folder not found."""
        from interface.operations.maintenance import MaintenanceOperations

        mock_db_manager.folders_table.find_one.return_value = None

        with patch("os.chdir"), patch("os.getcwd", return_value="/test"):
            ops = MaintenanceOperations(mock_db_manager)
            count = ops.mark_all_as_processed(folder_id=999)

        assert count == 0

    def test_mark_all_as_processed_no_folders_active(self, mock_db_manager):
        """Test mark_all_as_processed when no active folders."""
        from interface.operations.maintenance import MaintenanceOperations

        mock_db_manager.folders_table.find.return_value = []

        with patch("os.chdir"), patch("os.getcwd", return_value="/test"):
            ops = MaintenanceOperations(mock_db_manager)
            count = ops.mark_all_as_processed()

        assert count == 0

    def test_remove_inactive_folders_empty(self, mock_db_manager):
        """Test remove_inactive_folders when no inactive folders."""
        from interface.operations.maintenance import MaintenanceOperations

        mock_db_manager.folders_table.find.return_value = []

        ops = MaintenanceOperations(mock_db_manager)
        count = ops.remove_inactive_folders()

        assert count == 0
        mock_db_manager.folders_table.delete.assert_not_called()

    def test_set_all_active_no_change(self, mock_db_manager):
        """Test set_all_active when all folders already active."""
        from interface.operations.maintenance import MaintenanceOperations

        mock_db_manager.folders_table.count.side_effect = [5, 5]

        ops = MaintenanceOperations(mock_db_manager)
        count = ops.set_all_active()

        assert count == 0

    def test_set_all_inactive_no_change(self, mock_db_manager):
        """Test set_all_inactive when all folders already inactive."""
        from interface.operations.maintenance import MaintenanceOperations

        mock_db_manager.folders_table.count.side_effect = [5, 5]

        ops = MaintenanceOperations(mock_db_manager)
        count = ops.set_all_inactive()

        assert count == 0

    def test_clear_resend_flags_none_to_clear(self, mock_db_manager):
        """Test clear_resend_flags when no flags set."""
        from interface.operations.maintenance import MaintenanceOperations

        mock_db_manager.processed_files.count.side_effect = [0, 0]

        ops = MaintenanceOperations(mock_db_manager)
        count = ops.clear_resend_flags()

        assert count == 0

    def test_clear_emails_queue_empty(self, mock_db_manager):
        """Test clear_emails_queue when queue is empty."""
        from interface.operations.maintenance import MaintenanceOperations

        mock_db_manager.emails_table.count.return_value = 0

        ops = MaintenanceOperations(mock_db_manager)
        count = ops.clear_emails_queue()

        assert count == 0
        mock_db_manager.emails_table.delete.assert_called_once()


class TestMaintenanceOperationsResend:
    """Tests for resend functionality."""

    def test_resend_failed_files_none_failed(self, mock_db_manager):
        """Test resend_failed_files when no failed files."""
        from interface.operations.maintenance import MaintenanceOperations

        mock_db_manager.processed_files.find.return_value = []

        ops = MaintenanceOperations(mock_db_manager)
        count = ops.resend_failed_files()

        assert count == 0

    def test_resend_failed_files_multiple(self, mock_db_manager):
        """Test resend_failed_files with multiple failed files."""
        from interface.operations.maintenance import MaintenanceOperations

        mock_db_manager.processed_files.find.return_value = [
            {"id": 1, "file_name": "file1.txt"},
            {"id": 2, "file_name": "file2.txt"},
            {"id": 3, "file_name": "file3.txt"},
        ]

        ops = MaintenanceOperations(mock_db_manager)
        count = ops.resend_failed_files()

        assert count == 3
        assert mock_db_manager.processed_files.update.call_count == 3


class TestMaintenanceOperationsClearProcessedFiles:
    """Tests for clear_processed_files functionality."""

    def test_clear_processed_files_with_days(self, mock_db_manager):
        """Test clear_processed_files with days parameter."""
        from interface.operations.maintenance import MaintenanceOperations

        old_date = datetime.datetime.now() - datetime.timedelta(days=10)
        new_date = datetime.datetime.now() - datetime.timedelta(days=1)

        mock_db_manager.processed_files.all.return_value = [
            {"id": 1, "sent_date_time": old_date},
            {"id": 2, "sent_date_time": old_date},
            {"id": 3, "sent_date_time": new_date},
        ]

        ops = MaintenanceOperations(mock_db_manager)
        count = ops.clear_processed_files(days=7)

        assert count == 2
        mock_db_manager.processed_files.delete.assert_any_call(id=1)
        mock_db_manager.processed_files.delete.assert_any_call(id=2)

    def test_clear_processed_files_all_records(self, mock_db_manager):
        """Test clear_processed_files with no days (clear all)."""
        from interface.operations.maintenance import MaintenanceOperations

        mock_db_manager.processed_files.count.return_value = 50

        ops = MaintenanceOperations(mock_db_manager)
        count = ops.clear_processed_files()

        assert count == 50
        mock_db_manager.processed_files.delete.assert_called_once()


class TestMaintenanceOperationsIntegrationStyle:
    """Integration-style tests for MaintenanceOperations."""

    def test_multiple_operations_sequence(self, mock_db_manager):
        """Test running multiple operations in sequence."""
        from interface.operations.maintenance import MaintenanceOperations

        mock_db_manager.folders_table.count.side_effect = [
            5,
            10,  # set_all_active: 5 active, 10 after
            0,
            5,  # set_all_inactive: 0 inactive, 5 after
        ]

        ops = MaintenanceOperations(mock_db_manager)
        activated = ops.set_all_active()
        deactivated = ops.set_all_inactive()

        assert activated == 5
        assert deactivated == 5

    def test_clear_operations_sequence(self, mock_db_manager):
        """Test clear operations in sequence."""
        from interface.operations.maintenance import MaintenanceOperations

        mock_db_manager.processed_files.count.side_effect = [10, 0]
        mock_db_manager.emails_table.count.return_value = 5

        ops = MaintenanceOperations(mock_db_manager)
        flags_cleared = ops.clear_resend_flags()
        emails_cleared = ops.clear_emails_queue()

        assert flags_cleared == 10
        assert emails_cleared == 5
