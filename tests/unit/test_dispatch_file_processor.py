"""
Comprehensive unit tests for the dispatch file processor module.

These tests cover the FileDiscoverer, HashGenerator, and FileFilter classes
with extensive mocking of external dependencies.
"""

import os
import tempfile
from unittest.mock import MagicMock, Mock, patch, mock_open

import pytest

# Import the module under test
from dispatch.file_processor import (
    FileDiscoverer,
    HashGenerator,
    FileFilter,
    generate_match_lists,
    generate_file_hash,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_processed_files():
    """Provide sample processed files data."""
    return [
        {"file_name": "file1.txt", "file_checksum": "hash1", "resend_flag": False},
        {"file_name": "file2.txt", "file_checksum": "hash2", "resend_flag": True},
        {"file_name": "file3.txt", "file_checksum": "hash3", "resend_flag": False},
    ]


@pytest.fixture
def sample_file_list():
    """Provide sample list of file paths."""
    return [
        "/test/folder/file1.txt",
        "/test/folder/file2.txt",
        "/test/folder/file3.txt",
    ]


# =============================================================================
# FileDiscoverer Tests
# =============================================================================

class TestFileDiscoverer:
    """Tests for the FileDiscoverer class."""

    def test_discover_files_success(self):
        """Test successful file discovery."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            for i in range(3):
                with open(os.path.join(temp_dir, f"file{i}.txt"), "w") as f:
                    f.write(f"content {i}")

            # Create a subdirectory (should not be included)
            os.makedirs(os.path.join(temp_dir, "subdir"))

            result = FileDiscoverer.discover_files(temp_dir)

            assert len(result) == 3
            assert all(os.path.isfile(f) for f in result)
            assert all(f.endswith(".txt") for f in result)

    def test_discover_files_empty_directory(self):
        """Test file discovery in empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = FileDiscoverer.discover_files(temp_dir)

            assert result == []

    def test_discover_files_nonexistent_directory(self):
        """Test file discovery in non-existent directory."""
        result = FileDiscoverer.discover_files("/nonexistent/path/12345")

        assert result == []

    def test_discover_files_with_subdirectories(self):
        """Test that subdirectories are not included in results."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file
            with open(os.path.join(temp_dir, "file.txt"), "w") as f:
                f.write("content")

            # Create subdirectory with file
            subdir = os.path.join(temp_dir, "subdir")
            os.makedirs(subdir)
            with open(os.path.join(subdir, "subfile.txt"), "w") as f:
                f.write("sub content")

            result = FileDiscoverer.discover_files(temp_dir)

            # Should only include top-level file, not subdir or its contents
            assert len(result) == 1
            assert "file.txt" in result[0]

    def test_discover_files_returns_absolute_paths(self):
        """Test that discovered files have absolute paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with open(os.path.join(temp_dir, "test.txt"), "w") as f:
                f.write("content")

            result = FileDiscoverer.discover_files(temp_dir)

            assert len(result) == 1
            assert os.path.isabs(result[0])

    def test_discover_files_with_special_chars(self):
        """Test file discovery with special characters in filenames."""
        with tempfile.TemporaryDirectory() as temp_dir:
            filenames = ["file with spaces.txt", "file-with-dashes.txt", "file_with_underscores.txt"]
            for filename in filenames:
                with open(os.path.join(temp_dir, filename), "w") as f:
                    f.write("content")

            result = FileDiscoverer.discover_files(temp_dir)

            assert len(result) == 3


# =============================================================================
# HashGenerator Tests
# =============================================================================

class TestHashGenerator:
    """Tests for the HashGenerator class."""

    def test_generate_file_hash_success(self):
        """Test successful hash generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("test content")

            result = HashGenerator.generate_file_hash(test_file)

            # MD5 hash of "test content" (without trailing newline)
            expected_hash = "6ae8a75555209fd68c448d0da9a3943f"
            assert result == expected_hash
            assert len(result) == 32  # MD5 hex digest length

    def test_generate_file_hash_different_content(self):
        """Test that different content produces different hashes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file1 = os.path.join(temp_dir, "file1.txt")
            file2 = os.path.join(temp_dir, "file2.txt")

            with open(file1, "w") as f:
                f.write("content A")
            with open(file2, "w") as f:
                f.write("content B")

            hash1 = HashGenerator.generate_file_hash(file1)
            hash2 = HashGenerator.generate_file_hash(file2)

            assert hash1 != hash2

    def test_generate_file_hash_same_content(self):
        """Test that same content produces same hash."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file1 = os.path.join(temp_dir, "file1.txt")
            file2 = os.path.join(temp_dir, "file2.txt")

            with open(file1, "w") as f:
                f.write("same content")
            with open(file2, "w") as f:
                f.write("same content")

            hash1 = HashGenerator.generate_file_hash(file1)
            hash2 = HashGenerator.generate_file_hash(file2)

            assert hash1 == hash2

    def test_generate_file_hash_binary_content(self):
        """Test hash generation with binary content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "binary.bin")
            with open(test_file, "wb") as f:
                f.write(bytes(range(256)))

            result = HashGenerator.generate_file_hash(test_file)

            assert len(result) == 32
            assert all(c in "0123456789abcdef" for c in result)

    def test_generate_file_hash_empty_file(self):
        """Test hash generation with empty file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "empty.txt")
            with open(test_file, "w") as f:
                pass  # Create empty file

            result = HashGenerator.generate_file_hash(test_file)

            # MD5 hash of empty content
            assert result == "d41d8cd98f00b204e9800998ecf8427e"

    def test_generate_file_hash_large_file(self):
        """Test hash generation with large file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "large.txt")
            with open(test_file, "w") as f:
                f.write("x" * 1000000)  # 1MB of data

            result = HashGenerator.generate_file_hash(test_file)

            assert len(result) == 32

    @patch("dispatch.file_processor.time.sleep")
    @patch("dispatch.file_processor.hashlib.md5")
    def test_generate_file_hash_retry_success(self, mock_md5, mock_sleep):
        """Test hash generation with retry success."""
        mock_md5.side_effect = [
            Exception("File locked"),
            Exception("Still locked"),
            MagicMock(hexdigest=MagicMock(return_value="abc123"))
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("content")

            result = HashGenerator.generate_file_hash(test_file, max_retries=5)

            assert result == "abc123"
            assert mock_sleep.call_count == 2

    @patch("dispatch.file_processor.time.sleep")
    @patch("dispatch.file_processor.hashlib.md5")
    def test_generate_file_hash_retry_exceeded(self, mock_md5, mock_sleep):
        """Test hash generation when retry limit exceeded."""
        mock_md5.side_effect = Exception("File access denied")

        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("content")

            with pytest.raises(Exception) as exc_info:
                HashGenerator.generate_file_hash(test_file, max_retries=3)

            assert "File access denied" in str(exc_info.value)
            assert mock_sleep.call_count == 3

    @patch("dispatch.file_processor.time.sleep")
    def test_generate_file_hash_retry_timing(self, mock_sleep):
        """Test that retry timing increases exponentially."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("content")

            with patch("dispatch.file_processor.hashlib.md5") as mock_md5:
                mock_md5.side_effect = [
                    Exception("Error 1"),
                    Exception("Error 2"),
                    MagicMock(hexdigest=MagicMock(return_value="hash"))
                ]

                HashGenerator.generate_file_hash(test_file, max_retries=5)

                # Check exponential backoff: 1^2=1, 2^2=4
                assert mock_sleep.call_args_list[0][0][0] == 1
                assert mock_sleep.call_args_list[1][0][0] == 4


# =============================================================================
# FileFilter Tests
# =============================================================================

class TestFileFilter:
    """Tests for the FileFilter class."""

    def test_generate_match_lists_empty(self):
        """Test generating match lists with empty input."""
        result = FileFilter.generate_match_lists([])

        folder_hash_dict, folder_name_dict, resend_flag_set = result
        assert folder_hash_dict == []
        assert folder_name_dict == []
        assert resend_flag_set == set()

    def test_generate_match_lists_with_data(self, sample_processed_files):
        """Test generating match lists with sample data."""
        folder_hash_dict, folder_name_dict, resend_flag_set = FileFilter.generate_match_lists(sample_processed_files)

        assert len(folder_hash_dict) == 3
        assert ("file1.txt", "hash1") in folder_hash_dict
        assert ("file2.txt", "hash2") in folder_hash_dict
        assert ("file3.txt", "hash3") in folder_hash_dict

        assert len(folder_name_dict) == 3
        assert ("hash1", "file1.txt") in folder_name_dict
        assert ("hash2", "file2.txt") in folder_name_dict
        assert ("hash3", "file3.txt") in folder_name_dict

        assert resend_flag_set == {"hash2"}  # Only file2 has resend_flag=True

    def test_generate_match_lists_no_resend_flags(self):
        """Test generating match lists with no resend flags."""
        files = [
            {"file_name": "file1.txt", "file_checksum": "hash1", "resend_flag": False},
            {"file_name": "file2.txt", "file_checksum": "hash2", "resend_flag": False},
        ]

        _, _, resend_flag_set = FileFilter.generate_match_lists(files)

        assert resend_flag_set == set()

    def test_generate_match_lists_all_resend_flags(self):
        """Test generating match lists with all resend flags."""
        files = [
            {"file_name": "file1.txt", "file_checksum": "hash1", "resend_flag": True},
            {"file_name": "file2.txt", "file_checksum": "hash2", "resend_flag": True},
        ]

        _, _, resend_flag_set = FileFilter.generate_match_lists(files)

        assert resend_flag_set == {"hash1", "hash2"}

    def test_should_send_file_new_file(self):
        """Test should_send_file for new file (not in processed list)."""
        folder_name_dict = {"hash1": "file1.txt"}
        resend_flag_set = set()

        result = FileFilter.should_send_file("new_hash", folder_name_dict, resend_flag_set)

        assert result is True

    def test_should_send_file_existing_file(self):
        """Test should_send_file for existing file (already processed)."""
        folder_name_dict = {"hash1": "file1.txt"}
        resend_flag_set = set()

        result = FileFilter.should_send_file("hash1", folder_name_dict, resend_flag_set)

        assert result is False

    def test_should_send_file_resend_flag(self):
        """Test should_send_file for file with resend flag."""
        folder_name_dict = {"hash1": "file1.txt"}
        resend_flag_set = {"hash1"}

        result = FileFilter.should_send_file("hash1", folder_name_dict, resend_flag_set)

        assert result is True

    def test_should_send_file_empty_dicts(self):
        """Test should_send_file with empty dictionaries."""
        result = FileFilter.should_send_file("any_hash", {}, set())

        assert result is True

    def test_process_files_for_sending(self):
        """Test processing files for sending."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            files = []
            for i in range(3):
                filepath = os.path.join(temp_dir, f"file{i+1}.txt")
                with open(filepath, "w") as f:
                    f.write(f"content {i}")
                files.append(filepath)

            # Mock processed files: file1 already processed, file2 has resend flag
            processed_files = [
                {"file_name": "file1.txt", "file_checksum": "hash1", "resend_flag": False},
                {"file_name": "file2.txt", "file_checksum": "hash2", "resend_flag": True},
            ]

            with patch("dispatch.file_processor.HashGenerator.generate_file_hash") as mock_hash:
                mock_hash.side_effect = ["hash1", "hash2", "hash3"]

                result = FileFilter.process_files_for_sending(files, processed_files)

                # file1: already processed, no resend flag - should NOT be sent
                # file2: already processed, has resend flag - should be sent
                # file3: new file - should be sent
                assert len(result) == 2
                indices = [r[0] for r in result]
                assert 1 in indices  # file2
                assert 2 in indices  # file3
                assert 0 not in indices  # file1

    def test_process_files_for_sending_all_new(self):
        """Test processing files when all are new."""
        with tempfile.TemporaryDirectory() as temp_dir:
            files = []
            for i in range(3):
                filepath = os.path.join(temp_dir, f"file{i}.txt")
                with open(filepath, "w") as f:
                    f.write(f"content {i}")
                files.append(filepath)

            with patch("dispatch.file_processor.HashGenerator.generate_file_hash") as mock_hash:
                mock_hash.side_effect = ["hash1", "hash2", "hash3"]

                result = FileFilter.process_files_for_sending(files, [])

                assert len(result) == 3

    def test_process_files_for_sending_all_processed(self):
        """Test processing files when all are already processed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            files = []
            for i in range(3):
                filepath = os.path.join(temp_dir, f"file{i}.txt")
                with open(filepath, "w") as f:
                    f.write(f"content {i}")
                files.append(filepath)

            processed_files = [
                {"file_name": "file0.txt", "file_checksum": "hash1", "resend_flag": False},
                {"file_name": "file1.txt", "file_checksum": "hash2", "resend_flag": False},
                {"file_name": "file2.txt", "file_checksum": "hash3", "resend_flag": False},
            ]

            with patch("dispatch.file_processor.HashGenerator.generate_file_hash") as mock_hash:
                mock_hash.side_effect = ["hash1", "hash2", "hash3"]

                result = FileFilter.process_files_for_sending(files, processed_files)

                assert len(result) == 0


# =============================================================================
# Backward Compatibility Tests
# =============================================================================

class TestBackwardCompatibility:
    """Tests for backward compatibility functions."""

    def test_generate_match_lists_function(self, sample_processed_files):
        """Test standalone generate_match_lists function."""
        folder_hash_dict, folder_name_dict, resend_flag_set = generate_match_lists(sample_processed_files)

        assert len(folder_hash_dict) == 3
        assert len(folder_name_dict) == 3
        assert resend_flag_set == {"hash2"}

    def test_generate_file_hash_function(self):
        """Test standalone generate_file_hash function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("test content")

            source_file_struct = (
                test_file,
                0,
                [],
                {},
                {},
                set()
            )

            file_name, file_hash, index_number, send_file = generate_file_hash(source_file_struct)

            assert file_name == test_file
            assert len(file_hash) == 32
            assert index_number == 0
            assert send_file is True  # New file should be sent

    def test_generate_file_hash_function_existing_file(self):
        """Test generate_file_hash with existing file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("test content")

            source_file_struct = (
                test_file,
                1,
                [],
                {},
                {"d41d8cd98f00b204e9800998ecf8427e": "test.txt"},  # hash to filename
                set()
            )

            # Need to use actual hash
            import hashlib
            with open(test_file, 'rb') as f:
                actual_hash = hashlib.md5(f.read()).hexdigest()

            source_file_struct = (
                test_file,
                1,
                [],
                {},
                {actual_hash: "test.txt"},
                set()
            )

            file_name, file_hash, index_number, send_file = generate_file_hash(source_file_struct)

            assert index_number == 1
            assert send_file is False  # Existing file should not be sent

    def test_generate_file_hash_function_resend_flag(self):
        """Test generate_file_hash with resend flag."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("test content")

            import hashlib
            with open(test_file, 'rb') as f:
                actual_hash = hashlib.md5(f.read()).hexdigest()

            source_file_struct = (
                test_file,
                2,
                [],
                {},
                {actual_hash: "test.txt"},
                {actual_hash}  # Resend flag set
            )

            file_name, file_hash, index_number, send_file = generate_file_hash(source_file_struct)

            assert index_number == 2
            assert send_file is True  # Should send due to resend flag


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_discover_files_permission_denied(self):
        """Test file discovery with permission denied."""
        with patch("dispatch.file_processor.os.path.isdir", return_value=False):
            result = FileDiscoverer.discover_files("/restricted")

            assert result == []

    def test_generate_match_lists_missing_keys(self):
        """Test generate_match_lists with missing keys in records."""
        files = [
            {"file_name": "file1.txt", "file_checksum": "hash1"},  # No resend_flag
            {"file_checksum": "hash2", "resend_flag": True},  # No file_name
        ]

        folder_hash_dict, folder_name_dict, resend_flag_set = FileFilter.generate_match_lists(files)

        # Should handle missing keys gracefully
        assert len(folder_hash_dict) == 1  # Only first record has file_name
        assert len(folder_name_dict) == 1
        assert resend_flag_set == set()  # Second record has no file_name

    def test_generate_match_lists_none_values(self):
        """Test generate_match_lists with None values."""
        files = [
            {"file_name": "file1.txt", "file_checksum": "hash1", "resend_flag": None},
            {"file_name": "file2.txt", "file_checksum": "hash2", "resend_flag": True},
        ]

        _, _, resend_flag_set = FileFilter.generate_match_lists(files)

        assert resend_flag_set == {"hash2"}  # None should not be included

    def test_should_send_file_none_hash(self):
        """Test should_send_file with None hash."""
        result = FileFilter.should_send_file(None, {"hash1": "file1.txt"}, set())

        # None is not in the dict, so should send
        assert result is True

    def test_generate_file_hash_unicode_content(self):
        """Test hash generation with unicode content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "unicode.txt")
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("Unicode content: éèàù")

            result = HashGenerator.generate_file_hash(test_file)

            assert len(result) == 32

    def test_process_files_for_sending_empty_list(self):
        """Test processing empty file list."""
        result = FileFilter.process_files_for_sending([], [])

        assert result == []

    def test_generate_match_lists_duplicate_hashes(self):
        """Test generate_match_lists with duplicate hashes."""
        files = [
            {"file_name": "file1.txt", "file_checksum": "same_hash", "resend_flag": False},
            {"file_name": "file2.txt", "file_checksum": "same_hash", "resend_flag": True},
        ]

        folder_hash_dict, folder_name_dict, resend_flag_set = FileFilter.generate_match_lists(files)

        # Both entries should be in the lists
        assert len(folder_hash_dict) == 2
        assert len(resend_flag_set) == 1
        assert "same_hash" in resend_flag_set


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
