"""
Supplementary comprehensive unit tests for interface/operations/maintenance.py module.

Tests additional functionality not covered in tests/operations/test_maintenance_operations.py.
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, mock_open, patch

import pytest

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from interface.operations.maintenance import MaintenanceOperations


class TestMaintenanceOperationsExtended(unittest.TestCase):
    """Extended tests for MaintenanceOperations."""

    def setUp(self):
        """Set up test fixtures."""
        self.db_manager = MagicMock()
        self.db_manager.folders_table = MagicMock()
        self.db_manager.processed_files = MagicMock()
        self.db_manager.emails_table = MagicMock()
        self.db_manager.database_connection = MagicMock()

        self.ops = MaintenanceOperations(self.db_manager)

    def test_mark_all_as_processed_empty_folder(self):
        """Test mark_all_as_processed with empty folder."""
        self.db_manager.folders_table.find.return_value = [{
            'id': 1,
            'alias': 'test_folder',
            'folder_name': '/test/folder'
        }]

        with (patch('os.chdir'),
              patch('os.getcwd', return_value='/test'),
              patch('os.listdir', return_value=[])):
            count = self.ops.mark_all_as_processed(folder_id=1)

        self.assertEqual(count, 0)

    def test_mark_all_as_processed_filters_existing_files(self):
        """Test mark_all_as_processed filters already processed files."""
        self.db_manager.folders_table.find_one.return_value = {
            'id': 1,
            'alias': 'test_folder',
            'folder_name': '/test/folder'
        }
        # Simulate that all files are already processed
        self.db_manager.processed_files.find_one.return_value = {'id': 1}

        with patch('os.chdir'), \
             patch('os.getcwd', return_value='/test'), \
             patch('os.listdir', return_value=['file1.txt', 'file2.txt']), \
             patch('os.path.isfile', return_value=True), \
             patch('os.path.abspath', side_effect=lambda x: f'/test/folder/{x}'), \
             patch('builtins.open', mock_open(read_data=b'content')):

            count = self.ops.mark_all_as_processed(folder_id=1)

        # No new files should be marked
        self.assertEqual(count, 0)
        self.db_manager.processed_files.insert.assert_not_called()

    def test_remove_inactive_folders_empty(self):
        """Test remove_inactive_folders when no inactive folders."""
        self.db_manager.folders_table.find.return_value = []

        count = self.ops.remove_inactive_folders()

        self.assertEqual(count, 0)
        self.db_manager.folders_table.delete.assert_not_called()

    def test_remove_inactive_folders_deletes_related_records(self):
        """Test remove_inactive_folders deletes related processed_files and emails."""
        self.db_manager.folders_table.find.return_value = [
            {'id': 1, 'alias': 'folder1'},
            {'id': 2, 'alias': 'folder2'}
        ]

        count = self.ops.remove_inactive_folders()

        self.assertEqual(count, 2)
        # Should delete related records for each folder
        self.assertEqual(self.db_manager.processed_files.delete.call_count, 2)
        self.assertEqual(self.db_manager.emails_table.delete.call_count, 2)
        self.assertEqual(self.db_manager.folders_table.delete.call_count, 2)

    def test_set_all_active_no_change(self):
        """Test set_all_active when all folders already active."""
        # All folders already active, so no change
        self.db_manager.folders_table.count.side_effect = [5, 5]

        count = self.ops.set_all_active()

        self.assertEqual(count, 0)

    def test_set_all_inactive_no_change(self):
        """Test set_all_inactive when all folders already inactive."""
        # All folders already inactive
        self.db_manager.folders_table.count.side_effect = [5, 5]

        count = self.ops.set_all_inactive()

        self.assertEqual(count, 0)

    def test_clear_resend_flags_none_to_clear(self):
        """Test clear_resend_flags when no flags set."""
        self.db_manager.processed_files.count.side_effect = [0, 0]

        count = self.ops.clear_resend_flags()

        self.assertEqual(count, 0)

    def test_clear_resend_flags_partial_clear(self):
        """Test clear_resend_flags clears some but not all."""
        self.db_manager.processed_files.count.side_effect = [10, 3]  # 7 cleared

        count = self.ops.clear_resend_flags()

        self.assertEqual(count, 7)

    def test_clear_emails_queue_empty(self):
        """Test clear_emails_queue when queue is empty."""
        self.db_manager.emails_table.count.return_value = 0

        count = self.ops.clear_emails_queue()

        self.assertEqual(count, 0)
        self.db_manager.emails_table.delete.assert_called_once()

    def test_clear_processed_files_with_days(self):
        """Test clear_processed_files with days parameter."""
        # Create records with different dates
        old_date = datetime.now() - timedelta(days=10)
        new_date = datetime.now() - timedelta(days=1)

        self.db_manager.processed_files.all.return_value = [
            {'id': 1, 'sent_date_time': old_date},
            {'id': 2, 'sent_date_time': old_date},
            {'id': 3, 'sent_date_time': new_date},  # Not old enough
        ]

        count = self.ops.clear_processed_files(days=7)

        self.assertEqual(count, 2)
        # Should delete old records
        self.db_manager.processed_files.delete.assert_any_call(id=1)
        self.db_manager.processed_files.delete.assert_any_call(id=2)

    def test_clear_processed_files_all_records(self):
        """Test clear_processed_files with no days (clear all)."""
        self.db_manager.processed_files.count.return_value = 50

        count = self.ops.clear_processed_files()

        self.assertEqual(count, 50)
        self.db_manager.processed_files.delete.assert_called_once()

    def test_clear_all_processed_files(self):
        """Test clear_all_processed_files."""
        self.db_manager.processed_files.count.return_value = 100

        count = self.ops.clear_all_processed_files()

        self.assertEqual(count, 100)
        self.db_manager.processed_files.delete.assert_called_once()

    def test_resend_failed_files_none_failed(self):
        """Test resend_failed_files when no failed files."""
        self.db_manager.processed_files.find.return_value = []

        count = self.ops.resend_failed_files()

        self.assertEqual(count, 0)

    def test_resend_failed_files_multiple(self):
        """Test resend_failed_files with multiple failed files."""
        self.db_manager.processed_files.find.return_value = [
            {'id': 1, 'file_name': 'file1.txt'},
            {'id': 2, 'file_name': 'file2.txt'},
            {'id': 3, 'file_name': 'file3.txt'}
        ]

        count = self.ops.resend_failed_files()

        self.assertEqual(count, 3)
        self.assertEqual(self.db_manager.processed_files.update.call_count, 3)

    def test_get_processed_files_count(self):
        """Test get_processed_files_count."""
        self.db_manager.processed_files.count.return_value = 42

        count = self.ops.get_processed_files_count()

        self.assertEqual(count, 42)

    def test_get_inactive_folders_count(self):
        """Test get_inactive_folders_count."""
        self.db_manager.folders_table.count.return_value = 5

        count = self.ops.get_inactive_folders_count()

        self.assertEqual(count, 5)
        self.db_manager.folders_table.count.assert_called_once_with(folder_is_active="False")

    def test_get_active_folders_count(self):
        """Test get_active_folders_count."""
        self.db_manager.folders_table.count.return_value = 10

        count = self.ops.get_active_folders_count()

        self.assertEqual(count, 10)
        self.db_manager.folders_table.count.assert_called_once_with(folder_is_active="True")

    def test_get_pending_emails_count(self):
        """Test get_pending_emails_count."""
        self.db_manager.emails_table.count.return_value = 3

        count = self.ops.get_pending_emails_count()

        self.assertEqual(count, 3)

    def test_get_resend_files_count(self):
        """Test get_resend_files_count."""
        self.db_manager.processed_files.count.return_value = 7

        count = self.ops.get_resend_files_count()

        self.assertEqual(count, 7)
        self.db_manager.processed_files.count.assert_called_once_with(resend_flag=True)


class TestMaintenanceOperationsEdgeCases(unittest.TestCase):
    """Edge case tests for MaintenanceOperations."""

    def setUp(self):
        """Set up test fixtures."""
        self.db_manager = MagicMock()
        self.db_manager.folders_table = MagicMock()
        self.db_manager.processed_files = MagicMock()
        self.db_manager.emails_table = MagicMock()
        self.db_manager.database_connection = MagicMock()

        self.ops = MaintenanceOperations(self.db_manager)

    def test_mark_all_as_processed_folder_not_found(self):
        """Test mark_all_as_processed when folder not found."""
        self.db_manager.folders_table.find_one.return_value = None

        with patch('os.chdir'), patch('os.getcwd', return_value='/test'):
            count = self.ops.mark_all_as_processed(folder_id=999)

        self.assertEqual(count, 0)

    def test_mark_all_as_processed_no_folders_active(self):
        """Test mark_all_as_processed when no active folders."""
        self.db_manager.folders_table.find.return_value = []

        with patch('os.chdir'), patch('os.getcwd', return_value='/test'):
            count = self.ops.mark_all_as_processed()

        self.assertEqual(count, 0)

    def test_clear_processed_files_with_invalid_date(self):
        """Test clear_processed_files handles records without valid dates."""
        self.db_manager.processed_files.all.return_value = [
            {'id': 1, 'sent_date_time': 'invalid_date'},
            {'id': 2, 'sent_date_time': None},
            {'id': 3},  # No date field
        ]

        count = self.ops.clear_processed_files(days=7)

        # Should not crash, may or may not delete depending on comparison
        # Just verify it doesn't raise an exception

    def test_clear_processed_files_string_date_comparison(self):
        """Test clear_processed_files with string dates."""
        # This tests the edge case where dates might be strings
        old_date = datetime.now() - timedelta(days=10)

        self.db_manager.processed_files.all.return_value = [
            {'id': 1, 'sent_date_time': old_date},
        ]

        count = self.ops.clear_processed_files(days=7)

        self.assertEqual(count, 1)


class TestMaintenanceOperationsIntegration(unittest.TestCase):
    """Integration-style tests for MaintenanceOperations."""

    def setUp(self):
        """Set up test fixtures."""
        self.db_manager = MagicMock()
        self.db_manager.folders_table = MagicMock()
        self.db_manager.processed_files = MagicMock()
        self.db_manager.emails_table = MagicMock()
        self.db_manager.database_connection = MagicMock()

        self.ops = MaintenanceOperations(self.db_manager)

    def test_multiple_operations_sequence(self):
        """Test running multiple operations in sequence."""
        # Set up mocks
        self.db_manager.folders_table.count.side_effect = [
            5, 10,  # set_all_active: 5 active, 10 after
            0, 5,   # set_all_inactive: 0 inactive, 5 after
        ]

        # Run operations
        activated = self.ops.set_all_active()
        deactivated = self.ops.set_all_inactive()

        self.assertEqual(activated, 5)
        self.assertEqual(deactivated, 5)

    def test_clear_operations_sequence(self):
        """Test clear operations in sequence."""
        self.db_manager.processed_files.count.side_effect = [10, 0]
        self.db_manager.emails_table.count.return_value = 5

        flags_cleared = self.ops.clear_resend_flags()
        emails_cleared = self.ops.clear_emails_queue()

        self.assertEqual(flags_cleared, 10)
        self.assertEqual(emails_cleared, 5)


class TestMaintenanceOperationsMarkAsProcessedComplex(unittest.TestCase):
    """Complex tests for mark_all_as_processed."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

        self.db_manager = MagicMock()
        self.db_manager.folders_table = MagicMock()
        self.db_manager.processed_files = MagicMock()
        self.db_manager.emails_table = MagicMock()
        self.db_manager.database_connection = MagicMock()

        self.ops = MaintenanceOperations(self.db_manager)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_mark_all_as_processed_multiple_folders(self):
        """Test mark_all_as_processed with multiple folders."""
        self.db_manager.folders_table.find.return_value = [
            {'id': 1, 'alias': 'folder1', 'folder_name': self.temp_dir},
            {'id': 2, 'alias': 'folder2', 'folder_name': self.temp_dir}
        ]

        # Create test files
        with open(os.path.join(self.temp_dir, 'file1.txt'), 'w') as f:
            f.write('content1')
        with open(os.path.join(self.temp_dir, 'file2.txt'), 'w') as f:
            f.write('content2')

        self.db_manager.processed_files.find_one.return_value = None

        count = self.ops.mark_all_as_processed()

        # Should process both folders
        self.assertEqual(count, 4)  # 2 files x 2 folders


if __name__ == '__main__':
    unittest.main()
