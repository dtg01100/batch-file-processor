"""
Simple functional tests for dispatch module.

Tests the helper functions that can be easily tested without complex mocking.
"""

import os
import sys
import tempfile
import unittest

import pytest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from dispatch import generate_match_lists


class TestGenerateMatchLists(unittest.TestCase):
    def test_basic_functionality(self):
        folder_temp_processed_files_list = [
            {"file_name": "file1.txt", "file_checksum": "hash1", "resend_flag": False},
            {"file_name": "file2.txt", "file_checksum": "hash2", "resend_flag": True},
        ]

        folder_hash_dict, folder_name_dict, resend_flag_set = generate_match_lists(
            folder_temp_processed_files_list
        )

        assert folder_hash_dict == [("file1.txt", "hash1"), ("file2.txt", "hash2")]
        assert folder_name_dict == [("hash1", "file1.txt"), ("hash2", "file2.txt")]
        assert resend_flag_set == {"hash2"}

    def test_empty_list(self):
        folder_hash_dict, folder_name_dict, resend_flag_set = generate_match_lists([])

        assert folder_hash_dict == []
        assert folder_name_dict == []
        assert resend_flag_set == set()

    def test_no_resend_flags(self):
        folder_temp_processed_files_list = [
            {"file_name": "file1.txt", "file_checksum": "hash1", "resend_flag": False}
        ]

        folder_hash_dict, folder_name_dict, resend_flag_set = generate_match_lists(
            folder_temp_processed_files_list
        )

        assert resend_flag_set == set()

    def test_all_resend_flags(self):
        folder_temp_processed_files_list = [
            {"file_name": "file1.txt", "file_checksum": "hash1", "resend_flag": True},
            {"file_name": "file2.txt", "file_checksum": "hash2", "resend_flag": True},
        ]

        folder_hash_dict, folder_name_dict, resend_flag_set = generate_match_lists(
            folder_temp_processed_files_list
        )

        assert resend_flag_set == {"hash1", "hash2"}

    def test_multiple_files(self):
        folder_temp_processed_files_list = [
            {
                "file_name": f"file{i}.txt",
                "file_checksum": f"hash{i}",
                "resend_flag": i % 2 == 0,
            }
            for i in range(10)
        ]

        folder_hash_dict, folder_name_dict, resend_flag_set = generate_match_lists(
            folder_temp_processed_files_list
        )

        assert len(folder_hash_dict) == 10
        assert len(folder_name_dict) == 10
        assert len(resend_flag_set) == 5


if __name__ == "__main__":
    unittest.main()
