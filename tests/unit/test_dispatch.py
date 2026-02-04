"""
Tests for the dispatch module in batch-file-processor.

These tests cover the standalone helper functions and the main process() function
with appropriate mocking for external dependencies.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, mock_open, patch

import pytest

# Add parent directory to path so we can import dispatch
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

import legacy_dispatch as dispatch
from legacy_dispatch import generate_match_lists, generate_file_hash, process


class TestDispatchHelperFunctions(unittest.TestCase):
    """Tests for standalone helper functions in dispatch module"""

    def test_generate_match_lists_basic(self):
        """Test generate_match_lists with basic processed files scenario"""
        folder_temp_processed_files_list = [
            {"file_name": "file1.txt", "file_checksum": "hash1", "resend_flag": False},
            {"file_name": "file2.txt", "file_checksum": "hash2", "resend_flag": True},
        ]

        folder_hash_dict, folder_name_dict, resend_flag_set = generate_match_lists(
            folder_temp_processed_files_list
        )

        self.assertEqual(
            folder_hash_dict, [("file1.txt", "hash1"), ("file2.txt", "hash2")]
        )
        self.assertEqual(
            folder_name_dict, [("hash1", "file1.txt"), ("hash2", "file2.txt")]
        )
        self.assertEqual(resend_flag_set, {"hash2"})

    def test_generate_match_lists_empty(self):
        """Test generate_match_lists with empty processed files list"""
        folder_hash_dict, folder_name_dict, resend_flag_set = generate_match_lists([])

        self.assertEqual(folder_hash_dict, [])
        self.assertEqual(folder_name_dict, [])
        self.assertEqual(resend_flag_set, set())

    def test_generate_match_lists_no_resend_flags(self):
        """Test generate_match_lists with no resend flags"""
        folder_temp_processed_files_list = [
            {"file_name": "file1.txt", "file_checksum": "hash1", "resend_flag": False}
        ]

        folder_hash_dict, folder_name_dict, resend_flag_set = generate_match_lists(
            folder_temp_processed_files_list
        )

        self.assertEqual(resend_flag_set, set())

    @patch("legacy_dispatch.hashlib.md5")
    def test_generate_file_hash_success(self, mock_md5):
        """Test generate_file_hash with valid file and successful hash calculation"""
        mock_md5.return_value.hexdigest.return_value = "test_hash"

        test_file = tempfile.NamedTemporaryFile(mode="w", delete=False)
        test_file.write("test content")
        test_file.close()

        try:
            source_file_struct = (
                test_file.name,
                1,
                [],
                {},
                {"test_hash": "existing_file.txt"},
                set(),
            )

            file_name, generated_file_checksum, index_number, send_file = (
                generate_file_hash(source_file_struct)
            )

            self.assertEqual(file_name, test_file.name)
            self.assertEqual(generated_file_checksum, "test_hash")
            self.assertEqual(index_number, 1)
            self.assertFalse(send_file)
        finally:
            os.unlink(test_file.name)

    @patch("legacy_dispatch.hashlib.md5")
    def test_generate_file_hash_resend_flag(self, mock_md5):
        """Test generate_file_hash with resend flag set"""
        mock_md5.return_value.hexdigest.return_value = "test_hash"

        test_file = tempfile.NamedTemporaryFile(mode="w", delete=False)
        test_file.write("test content")
        test_file.close()

        try:
            source_file_struct = (
                test_file.name,
                1,
                [],
                {},
                {"test_hash": "existing_file.txt"},
                {"test_hash"},
            )

            file_name, generated_file_checksum, index_number, send_file = (
                generate_file_hash(source_file_struct)
            )

            self.assertTrue(send_file)
        finally:
            os.unlink(test_file.name)

    @patch("legacy_dispatch.hashlib.md5")
    def test_generate_file_hash_new_file(self, mock_md5):
        """Test generate_file_hash with new file (not in processed list)"""
        mock_md5.return_value.hexdigest.return_value = "new_hash"

        test_file = tempfile.NamedTemporaryFile(mode="w", delete=False)
        test_file.write("test content")
        test_file.close()

        try:
            source_file_struct = (test_file.name, 1, [], {}, {}, set())

            file_name, generated_file_checksum, index_number, send_file = (
                generate_file_hash(source_file_struct)
            )

            self.assertTrue(send_file)
        finally:
            os.unlink(test_file.name)

    @patch("legacy_dispatch.hashlib.md5")
    @patch("legacy_dispatch.time.sleep")
    def test_generate_file_hash_retry_logic(self, mock_sleep, mock_md5):
        """Test generate_file_hash retry logic on file access failure"""
        mock_md5.side_effect = [
            Exception("File access error"),
            Exception("File access error"),
            MagicMock(hexdigest=MagicMock(return_value="test_hash")),
        ]

        test_file = tempfile.NamedTemporaryFile(mode="w", delete=False)
        test_file.write("test content")
        test_file.close()

        try:
            source_file_struct = (test_file.name, 1, [], {}, {}, set())

            file_name, generated_file_checksum, index_number, send_file = (
                generate_file_hash(source_file_struct)
            )

            self.assertEqual(generated_file_checksum, "test_hash")
            self.assertEqual(mock_sleep.call_count, 2)
        finally:
            os.unlink(test_file.name)

    @patch("legacy_dispatch.hashlib.md5")
    @patch("legacy_dispatch.time.sleep")
    def test_generate_file_hash_retry_exceeded(self, mock_sleep, mock_md5):
        """Test generate_file_hash raises exception when retry limit exceeded"""
        mock_md5.side_effect = Exception("File access error")

        test_file = tempfile.NamedTemporaryFile(mode="w", delete=False)
        test_file.write("test content")
        test_file.close()

        try:
            source_file_struct = (test_file.name, 1, [], {}, {}, set())

            with self.assertRaises(Exception):
                generate_file_hash(source_file_struct)

            self.assertEqual(mock_sleep.call_count, 5)
        finally:
            os.unlink(test_file.name)


class TestDispatchProcessFunction(unittest.TestCase):
    """Tests for the main process() function in dispatch module"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "test.txt")
        with open(self.test_file, "w") as f:
            f.write("test content")

    def tearDown(self):
        os.remove(self.test_file)
        os.rmdir(self.temp_dir)

    @patch("legacy_dispatch.query_runner")
    @patch("legacy_dispatch.concurrent.futures.ProcessPoolExecutor")
    @patch("legacy_dispatch.threading.Thread")
    @patch("legacy_dispatch.concurrent.futures.ThreadPoolExecutor")
    def test_process_with_no_files(
        self,
        mock_thread_executor,
        mock_thread,
        mock_process_executor,
        mock_query_runner,
    ):
        """Test process function with no files to process"""
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

        mock_thread_executor_instance = MagicMock()
        mock_thread_executor.return_value.__enter__.return_value = (
            mock_thread_executor_instance
        )
        mock_thread_executor_instance.map.return_value = []

        database_connection = MagicMock()
        folders_database = MagicMock()
        folders_database.find.return_value = []
        folders_database.count.return_value = 0

        run_log = MagicMock()
        emails_table = MagicMock()
        run_log_directory = self.temp_dir
        reporting = MagicMock()
        processed_files = MagicMock()
        processed_files.find.return_value = []
        processed_files.count.return_value = 0
        processed_files.insert_many.return_value = None

        root = MagicMock()
        args = MagicMock()
        args.automatic = True

        version = "1.0.0"
        errors_folder = {"errors_folder": os.path.join(self.temp_dir, "errors")}
        settings = MagicMock()

        has_errors, run_summary = process(
            database_connection,
            folders_database,
            run_log,
            emails_table,
            run_log_directory,
            reporting,
            processed_files,
            root,
            args,
            version,
            errors_folder,
            settings,
        )

        self.assertFalse(has_errors)
        self.assertIn("processed", run_summary)

    @patch("legacy_dispatch.query_runner")
    @patch("legacy_dispatch.concurrent.futures.ProcessPoolExecutor")
    @patch("legacy_dispatch.threading.Thread")
    @patch("legacy_dispatch.concurrent.futures.ThreadPoolExecutor")
    @patch("legacy_dispatch.os.path.isdir")
    def test_process_missing_folder(
        self,
        mock_isdir,
        mock_thread_executor,
        mock_thread,
        mock_process_executor,
        mock_query_runner,
    ):
        """Test process function with missing folder"""
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

        mock_thread_executor_instance = MagicMock()
        mock_thread_executor.return_value.__enter__.return_value = (
            mock_thread_executor_instance
        )
        mock_thread_executor_instance.map.return_value = []

        mock_isdir.return_value = False

        database_connection = MagicMock()
        folders_database = MagicMock()
        folders_database.find.return_value = [
            {
                "folder_name": "/nonexistent/folder",
                "alias": "test",
                "id": 1,
                "folder_is_active": "True",
            }
        ]
        folders_database.count.return_value = 1

        run_log = MagicMock()
        emails_table = MagicMock()
        run_log_directory = self.temp_dir
        reporting = MagicMock()
        processed_files = MagicMock()
        processed_files.find.return_value = []
        processed_files.count.return_value = 0
        processed_files.insert_many.return_value = None

        root = MagicMock()
        args = MagicMock()
        args.automatic = True

        version = "1.0.0"
        errors_folder = {"errors_folder": os.path.join(self.temp_dir, "errors")}
        settings = MagicMock()

        has_errors, run_summary = process(
            database_connection,
            folders_database,
            run_log,
            emails_table,
            run_log_directory,
            reporting,
            processed_files,
            root,
            args,
            version,
            errors_folder,
            settings,
        )

        self.assertTrue(has_errors)
        self.assertIn("errors", run_summary)
        run_log.write.assert_called()

    @patch("legacy_dispatch.query_runner")
    @patch("legacy_dispatch.concurrent.futures.ProcessPoolExecutor")
    @patch("legacy_dispatch.threading.Thread")
    def test_process_no_new_files_simple(
        self, mock_thread, mock_process_executor, mock_query_runner
    ):
        """Test process function with no new files to send - simplified version"""
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
        run_log_directory = self.temp_dir
        reporting = MagicMock()
        processed_files = MagicMock()
        processed_files.find.return_value = []
        processed_files.count.return_value = 0
        processed_files.insert_many.return_value = None

        root = MagicMock()
        args = MagicMock()
        args.automatic = True

        version = "1.0.0"
        errors_folder = {"errors_folder": os.path.join(self.temp_dir, "errors")}
        settings = MagicMock()

        has_errors, run_summary = process(
            database_connection,
            folders_database,
            run_log,
            emails_table,
            run_log_directory,
            reporting,
            processed_files,
            root,
            args,
            version,
            errors_folder,
            settings,
        )

        self.assertFalse(has_errors)
        self.assertIn("processed", run_summary)


if __name__ == "__main__":
    unittest.main()
