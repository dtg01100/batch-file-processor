"""Tests for dispatch/file_utils.py module."""

import datetime
import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from dispatch.file_utils import (
    build_output_filename,
    filter_files_by_checksum,
    build_error_log_filename,
    get_file_extension,
    strip_invalid_filename_chars,
    ensure_directory_exists,
    list_files_in_directory,
    build_processed_file_record,
)


class TestBuildOutputFilename:
    """Tests for build_output_filename function."""
    
    def test_no_rename_template(self):
        """Test with no rename template."""
        result = build_output_filename(
            original="test_file.edi",
            format="Fintech",
            params={}
        )
        
        assert result == "test_file.edi"
    
    def test_with_datetime_placeholder(self):
        """Test with datetime placeholder in rename template."""
        with patch('dispatch.file_utils.datetime') as mock_datetime:
            mock_datetime.datetime.now.return_value = datetime.datetime(2024, 1, 15, 10, 30, 0)
            mock_datetime.datetime.strftime = datetime.datetime.strftime
            
            result = build_output_filename(
                original="test_file.edi",
                format="Fintech",
                params={'rename_file': 'invoice_%datetime%'}
            )
        
        assert 'invoice_20240115' in result
        assert '.edi' in result
    
    def test_with_prefix_and_suffix(self):
        """Test with prefix and suffix from EDI splitting."""
        result = build_output_filename(
            original="test_file.edi",
            format="Fintech",
            params={'rename_file': 'output'},
            filename_prefix="INV_",
            filename_suffix="_001"
        )
        
        assert result.startswith("INV_")
        # The suffix is added after the extension, so the result is INV_output.edi_001
        assert "_001" in result
    
    def test_strips_invalid_characters(self):
        """Test that invalid characters are stripped."""
        result = build_output_filename(
            original="test file.edi",
            format="Fintech",
            params={'rename_file': 'output@#$%.txt'}
        )
        
        # Invalid chars should be stripped
        assert '@' not in result
        assert '#' not in result
        assert '$' not in result
        assert '%' not in result
    
    def test_preserves_extension(self):
        """Test that file extension is preserved."""
        result = build_output_filename(
            original="test_file.edi",
            format="Fintech",
            params={'rename_file': 'renamed'}
        )
        
        assert result.endswith('.edi')
    
    def test_empty_rename_template(self):
        """Test with empty rename template."""
        result = build_output_filename(
            original="test_file.edi",
            format="Fintech",
            params={'rename_file': '   '}  # Whitespace only
        )
        
        assert result == "test_file.edi"


class TestFilterFilesByChecksum:
    """Tests for filter_files_by_checksum function."""
    
    def test_empty_files_list(self):
        """Test with empty files list."""
        result = filter_files_by_checksum([], {'hash1', 'hash2'})
        
        assert result == []
    
    def test_empty_checksums_set(self):
        """Test with empty checksums set."""
        files = ['/path/file1.txt', '/path/file2.txt']
        
        result = filter_files_by_checksum(files, set())
        
        assert result == files
    
    def test_filters_matching_files(self):
        """Test that files in checksums set are filtered out."""
        files = ['/path/file1.txt', '/path/file2.txt', '/path/file3.txt']
        checksums = {'/path/file1.txt', '/path/file3.txt'}
        
        result = filter_files_by_checksum(files, checksums)
        
        assert result == ['/path/file2.txt']
    
    def test_no_matching_files(self):
        """Test when no files match checksums."""
        files = ['/path/file1.txt', '/path/file2.txt']
        checksums = {'/other/file3.txt', '/other/file4.txt'}
        
        result = filter_files_by_checksum(files, checksums)
        
        assert result == files
    
    def test_all_files_filtered(self):
        """Test when all files are filtered out."""
        files = ['/path/file1.txt', '/path/file2.txt']
        checksums = {'/path/file1.txt', '/path/file2.txt'}
        
        result = filter_files_by_checksum(files, checksums)
        
        assert result == []


class TestBuildErrorLogFilename:
    """Tests for build_error_log_filename function."""
    
    def test_basic_construction(self):
        """Test basic filename construction."""
        with patch('dispatch.file_utils.time') as mock_time:
            mock_time.ctime.return_value = "Mon Jan 15 10-30-00 2024"
            
            result = build_error_log_filename(
                alias="Test Folder",
                errors_folder="/var/errors",
                folder_name="/data/input"
            )
        
        assert "/var/errors" in result
        assert "input" in result  # basename of folder_name
        assert "Test Folder errors" in result
        assert ".txt" in result
    
    def test_strips_invalid_chars_from_alias(self):
        """Test that invalid characters are stripped from alias."""
        result = build_error_log_filename(
            alias="Test@Folder#123!",
            errors_folder="/var/errors",
            folder_name="/data/input",
            timestamp="fixed-timestamp"
        )
        
        assert "@" not in result
        assert "#" not in result
        assert "!" not in result
        assert "TestFolder123" in result
    
    def test_custom_timestamp(self):
        """Test with custom timestamp."""
        result = build_error_log_filename(
            alias="TestFolder",
            errors_folder="/var/errors",
            folder_name="/data/input",
            timestamp="2024-01-15_10-30-00"
        )
        
        assert "2024-01-15_10-30-00" in result
    
    def test_colons_replaced_in_timestamp(self):
        """Test that colons are replaced in timestamp."""
        with patch('dispatch.file_utils.time') as mock_time:
            mock_time.ctime.return_value = "Mon Jan 15 10:30:00 2024"
            
            result = build_error_log_filename(
                alias="TestFolder",
                errors_folder="/var/errors",
                folder_name="/data/input"
            )
        
        # Colons should be replaced with dashes
        assert "10:30:00" not in result


class TestGetFileExtension:
    """Tests for get_file_extension function."""
    
    def test_simple_extension(self):
        """Test with simple extension."""
        assert get_file_extension("file.txt") == "txt"
    
    def test_multiple_dots(self):
        """Test with multiple dots in filename."""
        assert get_file_extension("file.name.edi") == "edi"
    
    def test_no_extension(self):
        """Test with no extension."""
        assert get_file_extension("filename") == ""
    
    def test_with_path(self):
        """Test with full path."""
        assert get_file_extension("/path/to/file.edi") == "edi"
    
    def test_hidden_file(self):
        """Test with hidden file (dot prefix)."""
        assert get_file_extension(".hidden") == ""


class TestStripInvalidFilenameChars:
    """Tests for strip_invalid_filename_chars function."""
    
    def test_valid_filename(self):
        """Test with already valid filename."""
        result = strip_invalid_filename_chars("valid_file.txt")
        assert result == "valid_file.txt"
    
    def test_strips_special_chars(self):
        """Test that special characters are stripped."""
        result = strip_invalid_filename_chars("file@#$%^&*.txt")
        
        assert "@" not in result
        assert "#" not in result
        assert "$" not in result
        assert "%" not in result
        assert "^" not in result
        assert "&" not in result
        assert "*" not in result
    
    def test_preserves_allowed_chars(self):
        """Test that allowed characters are preserved."""
        result = strip_invalid_filename_chars("File Name_123.txt")
        
        assert " " in result  # Space is allowed
        assert "_" in result  # Underscore is allowed
        assert "." in result  # Dot is allowed
    
    def test_empty_string(self):
        """Test with empty string."""
        assert strip_invalid_filename_chars("") == ""


class TestEnsureDirectoryExists:
    """Tests for ensure_directory_exists function."""
    
    def test_existing_directory(self):
        """Test with existing directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = ensure_directory_exists(tmpdir)
            assert result is True
    
    def test_creates_new_directory(self):
        """Test creating new directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = os.path.join(tmpdir, "new_subdir")
            
            result = ensure_directory_exists(new_dir)
            
            assert result is True
            assert os.path.isdir(new_dir)
    
    def test_creates_nested_directories(self):
        """Test creating nested directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_dir = os.path.join(tmpdir, "level1", "level2", "level3")
            
            result = ensure_directory_exists(nested_dir)
            
            assert result is True
            assert os.path.isdir(nested_dir)


class TestListFilesInDirectory:
    """Tests for list_files_in_directory function."""
    
    def test_empty_directory(self):
        """Test with empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = list_files_in_directory(tmpdir)
            assert result == []
    
    def test_files_only(self):
        """Test listing files only."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files
            file1 = os.path.join(tmpdir, "file1.txt")
            file2 = os.path.join(tmpdir, "file2.edi")
            open(file1, 'w').close()
            open(file2, 'w').close()
            
            result = list_files_in_directory(tmpdir, files_only=True)
            
            assert len(result) == 2
            assert all(os.path.isfile(f) for f in result)
    
    def test_includes_subdirectories(self):
        """Test listing with subdirectories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create file and subdirectory
            file1 = os.path.join(tmpdir, "file1.txt")
            subdir = os.path.join(tmpdir, "subdir")
            open(file1, 'w').close()
            os.mkdir(subdir)
            
            result = list_files_in_directory(tmpdir, files_only=False)
            
            assert len(result) == 2
    
    def test_nonexistent_directory(self):
        """Test with nonexistent directory."""
        result = list_files_in_directory("/nonexistent/path")
        assert result == []
    
    def test_returns_absolute_paths(self):
        """Test that absolute paths are returned."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = os.path.join(tmpdir, "file1.txt")
            open(file1, 'w').close()
            
            result = list_files_in_directory(tmpdir)
            
            assert all(os.path.isabs(f) for f in result)


class TestBuildProcessedFileRecord:
    """Tests for build_processed_file_record function."""
    
    def test_basic_record(self):
        """Test basic record construction."""
        with patch('dispatch.file_utils.datetime') as mock_datetime:
            mock_datetime.datetime.now.return_value = datetime.datetime(2024, 1, 15, 10, 30, 0)
            mock_datetime.datetime.strftime = datetime.datetime.strftime
            
            result = build_processed_file_record(
                original_filename="/path/to/file.edi",
                folder_id=1,
                folder_alias="TestFolder",
                file_checksum="abc123",
                params={}
            )
        
        assert result['file_name'] == "/path/to/file.edi"
        assert result['folder_id'] == 1
        assert result['folder_alias'] == "TestFolder"
        assert result['file_checksum'] == "abc123"
        assert result['resend_flag'] is False
    
    def test_copy_backend_destination(self):
        """Test copy destination when backend enabled."""
        params = {
            'process_backend_copy': True,
            'copy_to_directory': '/backup/files'
        }
        
        result = build_processed_file_record(
            original_filename="/path/to/file.edi",
            folder_id=1,
            folder_alias="TestFolder",
            file_checksum="abc123",
            params=params
        )
        
        assert result['copy_destination'] == "/backup/files"
    
    def test_copy_backend_disabled(self):
        """Test copy destination when backend disabled."""
        params = {
            'process_backend_copy': False,
            'copy_to_directory': '/backup/files'
        }
        
        result = build_processed_file_record(
            original_filename="/path/to/file.edi",
            folder_id=1,
            folder_alias="TestFolder",
            file_checksum="abc123",
            params=params
        )
        
        assert result['copy_destination'] == "N/A"
    
    def test_ftp_destination(self):
        """Test FTP destination when backend enabled."""
        params = {
            'process_backend_ftp': True,
            'ftp_server': 'ftp.example.com',
            'ftp_folder': '/uploads'
        }
        
        result = build_processed_file_record(
            original_filename="/path/to/file.edi",
            folder_id=1,
            folder_alias="TestFolder",
            file_checksum="abc123",
            params=params
        )
        
        assert result['ftp_destination'] == "ftp.example.com/uploads"
    
    def test_email_destination(self):
        """Test email destination when backend enabled."""
        params = {
            'process_backend_email': True,
            'email_to': 'user@example.com'
        }
        
        result = build_processed_file_record(
            original_filename="/path/to/file.edi",
            folder_id=1,
            folder_alias="TestFolder",
            file_checksum="abc123",
            params=params
        )
        
        assert result['email_destination'] == "user@example.com"
    
    def test_all_backends_disabled(self):
        """Test all destinations when all backends disabled."""
        result = build_processed_file_record(
            original_filename="/path/to/file.edi",
            folder_id=1,
            folder_alias="TestFolder",
            file_checksum="abc123",
            params={}
        )
        
        assert result['copy_destination'] == "N/A"
        assert result['ftp_destination'] == "N/A"
        assert result['email_destination'] == "N/A"
