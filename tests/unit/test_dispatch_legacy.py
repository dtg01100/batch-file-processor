"""
Comprehensive unit tests for dispatch.py legacy process() function.

This module tests the complex orchestration logic in the legacy dispatch.py
process() function with extensive mocking of external dependencies.
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime
from io import StringIO
from unittest.mock import MagicMock, mock_open, patch

import pytest

# Ensure project root is in path
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

import dispatch
from dispatch import generate_match_lists, generate_file_hash, process


class TestGenerateMatchLists(unittest.TestCase):
    """Tests for generate_match_lists function."""

    def test_basic_match_list_generation(self):
        """Test generating match lists with multiple entries."""
        folder_temp_processed_files_list = [
            {"file_name": "file1.txt", "file_checksum": "hash1", "resend_flag": False},
            {"file_name": "file2.txt", "file_checksum": "hash2", "resend_flag": True},
            {"file_name": "file3.txt", "file_checksum": "hash3", "resend_flag": False},
        ]

        folder_hash_dict, folder_name_dict, resend_flag_set = generate_match_lists(
            folder_temp_processed_files_list
        )

        self.assertEqual(
            folder_hash_dict,
            [("file1.txt", "hash1"), ("file2.txt", "hash2"), ("file3.txt", "hash3")],
        )
        self.assertEqual(
            folder_name_dict,
            [("hash1", "file1.txt"), ("hash2", "file2.txt"), ("hash3", "file3.txt")],
        )
        self.assertEqual(resend_flag_set, {"hash2"})

    def test_empty_list(self):
        """Test with empty processed files list."""
        folder_hash_dict, folder_name_dict, resend_flag_set = generate_match_lists([])

        self.assertEqual(folder_hash_dict, [])
        self.assertEqual(folder_name_dict, [])
        self.assertEqual(resend_flag_set, set())

    def test_all_resend_flags_true(self):
        """Test when all files have resend_flag set to True."""
        folder_temp_processed_files_list = [
            {"file_name": "file1.txt", "file_checksum": "hash1", "resend_flag": True},
            {"file_name": "file2.txt", "file_checksum": "hash2", "resend_flag": True},
        ]

        _, _, resend_flag_set = generate_match_lists(folder_temp_processed_files_list)

        self.assertEqual(resend_flag_set, {"hash1", "hash2"})

    def test_no_resend_flags(self):
        """Test when no files have resend_flag set."""
        folder_temp_processed_files_list = [
            {"file_name": "file1.txt", "file_checksum": "hash1", "resend_flag": False},
            {"file_name": "file2.txt", "file_checksum": "hash2", "resend_flag": False},
        ]

        _, _, resend_flag_set = generate_match_lists(folder_temp_processed_files_list)

        self.assertEqual(resend_flag_set, set())


class TestGenerateFileHash(unittest.TestCase):
    """Tests for generate_file_hash function."""

    @patch("dispatch.file_processor.hashlib.md5")
    def test_successful_hash_generation(self, mock_md5):
        """Test successful file hash generation."""
        mock_md5.return_value.hexdigest.return_value = "abc123hash"

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            temp_file = f.name

        try:
            source_file_struct = (
                temp_file,
                0,
                [],
                {},
                {},  # folder_name_dict - empty means no match
                set(),
            )

            file_name, file_hash, index_number, send_file = generate_file_hash(
                source_file_struct
            )

            self.assertEqual(file_name, temp_file)
            self.assertEqual(file_hash, "abc123hash")
            self.assertEqual(index_number, 0)
            self.assertTrue(send_file)  # New file, should send
        finally:
            os.unlink(temp_file)

    @patch("dispatch.file_processor.hashlib.md5")
    def test_existing_file_no_resend(self, mock_md5):
        """Test file that exists in processed list but no resend flag."""
        mock_md5.return_value.hexdigest.return_value = "existing_hash"

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            temp_file = f.name

        try:
            source_file_struct = (
                temp_file,
                1,
                [],
                {},
                {"existing_hash": "existing_file.txt"},  # Match found
                set(),  # No resend flag
            )

            file_name, file_hash, index_number, send_file = generate_file_hash(
                source_file_struct
            )

            self.assertFalse(send_file)  # Existing file, no resend
        finally:
            os.unlink(temp_file)

    @patch("dispatch.file_processor.hashlib.md5")
    def test_existing_file_with_resend(self, mock_md5):
        """Test file with resend flag set."""
        mock_md5.return_value.hexdigest.return_value = "resend_hash"

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            temp_file = f.name

        try:
            source_file_struct = (
                temp_file,
                2,
                [],
                {},
                {"resend_hash": "resend_file.txt"},
                {"resend_hash"},  # Resend flag set
            )

            file_name, file_hash, index_number, send_file = generate_file_hash(
                source_file_struct
            )

            self.assertTrue(send_file)  # Resend flag overrides existing
        finally:
            os.unlink(temp_file)

    @patch("dispatch.file_processor.hashlib.md5")
    @patch("dispatch.file_processor.time.sleep")
    def test_retry_logic_success(self, mock_sleep, mock_md5):
        """Test retry logic eventually succeeds."""
        mock_md5.side_effect = [
            Exception("File locked"),
            Exception("File locked"),
            MagicMock(hexdigest=MagicMock(return_value="success_hash")),
        ]

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            temp_file = f.name

        try:
            source_file_struct = (temp_file, 0, [], {}, {}, set())

            file_name, file_hash, index_number, send_file = generate_file_hash(
                source_file_struct
            )

            self.assertEqual(file_hash, "success_hash")
            self.assertEqual(mock_sleep.call_count, 2)
        finally:
            os.unlink(temp_file)

    @patch("dispatch.file_processor.hashlib.md5")
    @patch("dispatch.file_processor.time.sleep")
    def test_retry_logic_failure(self, mock_sleep, mock_md5):
        """Test retry logic exceeds max attempts and raises."""
        mock_md5.side_effect = Exception("Persistent error")

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            temp_file = f.name

        try:
            source_file_struct = (temp_file, 0, [], {}, {}, set())

            with self.assertRaises(Exception) as context:
                generate_file_hash(source_file_struct)

            self.assertEqual(mock_sleep.call_count, 5)  # Max retries
        finally:
            os.unlink(temp_file)


class TestDispatchProcessComplex(unittest.TestCase):
    """Complex tests for the main process() function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.errors_folder = os.path.join(self.temp_dir, "errors")
        os.makedirs(self.errors_folder, exist_ok=True)

        # Create test folder with files
        self.test_folder = os.path.join(self.temp_dir, "test_folder")
        os.makedirs(self.test_folder, exist_ok=True)

        # Create a test file
        self.test_file = os.path.join(self.test_folder, "test_edi.txt")
        with open(self.test_file, "w") as f:
            f.write("A123456789012345012345000012345\n")
            f.write("B1234567890Test Description     123450123450012345012340123\n")

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("dispatch.coordinator.query_runner")
    @patch("dispatch.coordinator.concurrent.futures.ProcessPoolExecutor")
    @patch("dispatch.coordinator.threading.Thread")
    def test_process_empty_database(
        self, mock_thread, mock_process_executor, mock_query_runner
    ):
        """Test process with no folders in database."""
        mock_query_runner_instance = MagicMock()
        mock_query_runner.return_value = mock_query_runner_instance
        mock_query_runner_instance.run_arbitrary_query.return_value = []

        mock_process_executor_instance = MagicMock()
        mock_process_executor.return_value.__enter__.return_value = (
            mock_process_executor_instance
        )
        mock_process_executor_instance.map.return_value = []

        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        database_connection = MagicMock()
        folders_database = MagicMock()
        folders_database.find.return_value = []
        folders_database.count.return_value = 0

        run_log = MagicMock()
        emails_table = MagicMock()
        processed_files = MagicMock()
        processed_files.find.return_value = []

        root = MagicMock()
        args = MagicMock()
        args.automatic = True

        settings = {
            "as400_username": "test",
            "as400_password": "test",
            "as400_address": "test",
            "odbc_driver": "test",
        }

        has_errors, summary = process(
            database_connection,
            folders_database,
            run_log,
            emails_table,
            self.temp_dir,
            {"enable_reporting": "False", "report_edi_errors": False},
            processed_files,
            root,
            args,
            "1.0.0",
            {"errors_folder": self.errors_folder},
            settings,
        )

        self.assertFalse(has_errors)
        self.assertIn("0 processed", summary)

    @patch("dispatch.coordinator.query_runner")
    @patch("dispatch.coordinator.concurrent.futures.ProcessPoolExecutor")
    @patch("dispatch.coordinator.threading.Thread")
    @patch("dispatch.coordinator.os.path.isdir")
    def test_process_missing_folder_error(
        self, mock_isdir, mock_thread, mock_process_executor, mock_query_runner
    ):
        """Test process with missing folder increments error counter."""
        mock_query_runner_instance = MagicMock()
        mock_query_runner.return_value = mock_query_runner_instance
        mock_query_runner_instance.run_arbitrary_query.return_value = []

        mock_process_executor_instance = MagicMock()
        mock_process_executor.return_value.__enter__.return_value = (
            mock_process_executor_instance
        )
        mock_process_executor_instance.map.return_value = []

        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        mock_isdir.return_value = False  # Folder doesn't exist

        database_connection = MagicMock()
        folders_database = MagicMock()
        folders_database.find.return_value = [
            {
                "folder_name": "/nonexistent/folder",
                "alias": "missing_folder",
                "id": 1,
                "folder_is_active": "True",
            }
        ]
        folders_database.count.return_value = 1

        run_log = MagicMock()
        emails_table = MagicMock()
        processed_files = MagicMock()
        processed_files.find.return_value = []

        root = MagicMock()
        args = MagicMock()
        args.automatic = True

        settings = {
            "as400_username": "test",
            "as400_password": "test",
            "as400_address": "test",
            "odbc_driver": "test",
        }

        has_errors, summary = process(
            database_connection,
            folders_database,
            run_log,
            emails_table,
            self.temp_dir,
            {"enable_reporting": "False", "report_edi_errors": False},
            processed_files,
            root,
            args,
            "1.0.0",
            {"errors_folder": self.errors_folder},
            settings,
        )

        self.assertTrue(has_errors)
        self.assertIn("1 errors", summary)

    @patch("dispatch.coordinator.query_runner")
    @patch("dispatch.coordinator.concurrent.futures.ProcessPoolExecutor")
    @patch("dispatch.coordinator.threading.Thread")
    def test_process_with_upc_query(
        self, mock_thread, mock_process_executor, mock_query_runner
    ):
        """Test process fetches and uses UPC data from query."""
        mock_query_runner_instance = MagicMock()
        mock_query_runner.return_value = mock_query_runner_instance
        mock_query_runner_instance.run_arbitrary_query.return_value = [
            (12345, "CAT1", "UPC1", "UPC2", "UPC3", "UPC4"),
            (67890, "CAT2", "UPCA", "UPCB", "UPCC", "UPCD"),
        ]

        mock_process_executor_instance = MagicMock()
        mock_process_executor.return_value.__enter__.return_value = (
            mock_process_executor_instance
        )
        mock_process_executor_instance.map.return_value = []

        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        database_connection = MagicMock()
        folders_database = MagicMock()
        folders_database.find.return_value = []
        folders_database.count.return_value = 0

        run_log = MagicMock()
        emails_table = MagicMock()
        processed_files = MagicMock()
        processed_files.find.return_value = []

        root = MagicMock()
        args = MagicMock()
        args.automatic = True

        settings = {
            "as400_username": "test",
            "as400_password": "test",
            "as400_address": "test",
            "odbc_driver": "test",
        }

        has_errors, summary = process(
            database_connection,
            folders_database,
            run_log,
            emails_table,
            self.temp_dir,
            {"enable_reporting": "False", "report_edi_errors": False},
            processed_files,
            root,
            args,
            "1.0.0",
            {"errors_folder": self.errors_folder},
            settings,
        )

        # Verify UPC query was called
        mock_query_runner_instance.run_arbitrary_query.assert_called_once()


class TestDispatchInnerFunctions(unittest.TestCase):
    """Tests for inner functions and complex logic in dispatch."""

    def test_update_overlay_non_automatic(self):
        """Test update_overlay when not in automatic mode."""
        # This tests the update_overlay function behavior
        root = MagicMock()

        # Simulate calling update_overlay through process
        with patch("dispatch.coordinator.doingstuffoverlay") as mock_overlay:
            mock_overlay.update_overlay = MagicMock()

            # The update_overlay is defined inside process(), so we test it
            # through the behavior of process
            # This is a placeholder for testing the overlay update logic
            pass


class TestDispatchEdgeCases(unittest.TestCase):
    """Edge case tests for dispatch module."""

    @patch("dispatch.coordinator.query_runner")
    @patch("dispatch.coordinator.concurrent.futures.ProcessPoolExecutor")
    @patch("dispatch.coordinator.threading.Thread")
    def test_process_with_old_id_keyerror(
        self, mock_thread, mock_process_executor, mock_query_runner
    ):
        """Test process handles KeyError when 'old_id' doesn't exist."""
        mock_query_runner_instance = MagicMock()
        mock_query_runner.return_value = mock_query_runner_instance
        mock_query_runner_instance.run_arbitrary_query.return_value = []

        mock_process_executor_instance = MagicMock()
        mock_process_executor.return_value.__enter__.return_value = (
            mock_process_executor_instance
        )
        mock_process_executor_instance.map.return_value = []

        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        database_connection = MagicMock()
        folders_database = MagicMock()
        # Folder without 'old_id' key - should trigger KeyError handling
        folders_database.find.return_value = [
            {
                "folder_name": "/test/folder",
                "alias": "test",
                "id": 1,  # No 'old_id' key
            }
        ]
        folders_database.count.return_value = 1

        run_log = MagicMock()
        emails_table = MagicMock()
        processed_files = MagicMock()
        processed_files.find.return_value = []

        root = MagicMock()
        args = MagicMock()
        args.automatic = True

        settings = {
            "as400_username": "test",
            "as400_password": "test",
            "as400_address": "test",
            "odbc_driver": "test",
        }

        # Should not raise exception
        has_errors, summary = process(
            database_connection,
            folders_database,
            run_log,
            emails_table,
            tempfile.mkdtemp(),
            {"enable_reporting": "False", "report_edi_errors": False},
            processed_files,
            root,
            args,
            "1.0.0",
            {"errors_folder": tempfile.mkdtemp()},
            settings,
        )


if __name__ == "__main__":
    unittest.main()
