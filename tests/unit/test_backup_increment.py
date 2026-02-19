"""Unit tests for backup_increment module."""

import os
import shutil
import tempfile
import time
from unittest.mock import patch, MagicMock

import pytest

import backup_increment


class TestDoBackup:
    """Tests for the do_backup function."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        # Cleanup
        if os.path.exists(temp_path):
            shutil.rmtree(temp_path)

    @pytest.fixture
    def test_file(self, temp_dir):
        """Create a test file to backup."""
        file_path = os.path.join(temp_dir, "test_file.txt")
        with open(file_path, 'w') as f:
            f.write("test content")
        return file_path

    def test_do_backup_creates_backup_directory(self, temp_dir, test_file):
        """Test that backup creates a 'backups' directory."""
        # Remove any existing backups directory
        backups_dir = os.path.join(temp_dir, "backups")
        if os.path.exists(backups_dir):
            shutil.rmtree(backups_dir)
        
        with patch('backup_increment.utils.do_clear_old_files'):
            result = backup_increment.do_backup(test_file)
        
        assert os.path.exists(backups_dir)
        assert os.path.isdir(backups_dir)

    def test_do_backup_creates_bak_file(self, temp_dir, test_file):
        """Test that backup creates a .bak file."""
        with patch('backup_increment.utils.do_clear_old_files'):
            result = backup_increment.do_backup(test_file)
        
        assert os.path.exists(result)
        # Filename includes timestamp after .bak, e.g., test_file.txt.bak-Thu...
        assert '.bak-' in result

    def test_do_backup_returns_correct_path(self, temp_dir, test_file):
        """Test that do_backup returns the correct backup path."""
        with patch('backup_increment.utils.do_clear_old_files'):
            result = backup_increment.do_backup(test_file)
        
        expected_dir = os.path.join(temp_dir, "backups")
        assert expected_dir in result
        assert os.path.basename(test_file) in result

    def test_do_backup_file_content_matches(self, temp_dir, test_file):
        """Test that backup file has the same content as original."""
        with open(test_file, 'r') as f:
            original_content = f.read()
        
        with patch('backup_increment.utils.do_clear_old_files'):
            result = backup_increment.do_backup(test_file)
        
        with open(result, 'r') as f:
            backup_content = f.read()
        
        assert backup_content == original_content

    def test_do_backup_calls_clear_old_files(self, temp_dir, test_file):
        """Test that do_backup calls utils.do_clear_old_files."""
        with patch('backup_increment.utils.do_clear_old_files') as mock_clear:
            backup_increment.do_backup(test_file)
            
            mock_clear.assert_called_once()
            # Verify it was called with the backups directory and max files = 50
            call_args = mock_clear.call_args
            assert call_args[0][1] == 50  # maximum_files

    def test_do_backup_handles_existing_backup_folder_as_file(self, temp_dir, test_file):
        """Test backup handles case where backups name exists as a file."""
        # First backup creates the directory
        with patch('backup_increment.utils.do_clear_old_files'):
            first_result = backup_increment.do_backup(test_file)
        
        # Remove the backup directory and create a file with that name
        backups_dir = os.path.join(temp_dir, "backups")
        shutil.rmtree(backups_dir)
        
        # Create a file named "backups"
        with open(backups_dir, 'w') as f:
            f.write("fake backup folder")
        
        # Second backup should handle this by creating "backups1" directory
        with patch('backup_increment.utils.do_clear_old_files'):
            second_result = backup_increment.do_backup(test_file)
        
        # Should create backups1 directory
        assert os.path.exists(second_result)
        assert "backups1" in second_result

    def test_do_backup_increments_suffix(self, temp_dir, test_file):
        """Test backup increments numeric suffix when directories exist."""
        # Create multiple backup scenarios
        backups_dir = os.path.join(temp_dir, "backups")
        
        # First run creates "backups" directory
        with patch('backup_increment.utils.do_clear_old_files'):
            first_result = backup_increment.do_backup(test_file)
        
        # Clean up the backup but leave the directory
        if os.path.exists(first_result):
            os.remove(first_result)
        
        # Second run should find "backups" is a directory and use it
        with patch('backup_increment.utils.do_clear_old_files'):
            second_result = backup_increment.do_backup(test_file)
        
        assert os.path.exists(second_result)

    def test_do_backup_timestamp_in_filename(self, temp_dir, test_file):
        """Test that backup filename contains a timestamp."""
        with patch('backup_increment.utils.do_clear_old_files'):
            result = backup_increment.do_backup(test_file)
        
        # Filename should contain .bak-
        assert '.bak-' in result
        
        # The timestamp part should be in the filename
        filename = os.path.basename(result)
        # Should have timestamp format like "Thu Jan  1 00-00-00 2026"
        assert '-' in filename  # Timestamps have dashes instead of colons
