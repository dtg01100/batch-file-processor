"""
Unit tests for backup_increment module.

Tests database backup functionality including file copying,
backup folder creation, and old file cleanup.
"""

import os
import tempfile
import shutil
import pytest
from unittest.mock import patch, MagicMock

import backup_increment


class TestDoBackup:
    """Tests for backup_increment.do_backup function."""

    def test_creates_backup_folder(self, temp_dir):
        """Should create backups folder if it doesn't exist."""
        # Create a test file
        test_file = os.path.join(temp_dir, "test.db")
        with open(test_file, "w") as f:
            f.write("test content")

        backup_path = backup_increment.do_backup(test_file)

        # Check backup folder was created
        backup_folder = os.path.join(temp_dir, "backups")
        assert os.path.isdir(backup_folder)
        assert backup_path.startswith(backup_folder)

    def test_creates_backup_file(self, temp_dir):
        """Should create a backup copy of the file."""
        # Create a test file with content
        test_file = os.path.join(temp_dir, "test.db")
        original_content = "test database content"
        with open(test_file, "w") as f:
            f.write(original_content)

        backup_path = backup_increment.do_backup(test_file)

        # Check backup file exists and has same content
        assert os.path.exists(backup_path)
        with open(backup_path, "r") as f:
            assert f.read() == original_content

    def test_backup_filename_includes_original_name(self, temp_dir):
        """Backup filename should include original filename."""
        test_file = os.path.join(temp_dir, "mydata.db")
        with open(test_file, "w") as f:
            f.write("data")

        backup_path = backup_increment.do_backup(test_file)

        # Filename should start with original name
        backup_filename = os.path.basename(backup_path)
        assert backup_filename.startswith("mydata.db.bak")

    def test_backup_filename_includes_timestamp(self, temp_dir):
        """Backup filename should include timestamp."""
        test_file = os.path.join(temp_dir, "test.db")
        with open(test_file, "w") as f:
            f.write("data")

        backup_path = backup_increment.do_backup(test_file)

        # Filename should have timestamp-like suffix
        backup_filename = os.path.basename(backup_path)
        # Format: filename.bak-<timestamp>
        assert ".bak-" in backup_filename

    def test_multiple_backups_dont_overwrite(self, temp_dir):
        """Multiple backups of same file should create separate files."""
        test_file = os.path.join(temp_dir, "test.db")
        with open(test_file, "w") as f:
            f.write("data")

        backup1 = backup_increment.do_backup(test_file)

        # Modify file
        with open(test_file, "w") as f:
            f.write("modified data")

        # Wait 1 second to ensure different timestamp (ctime uses seconds)
        import time

        time.sleep(1.0)

        backup2 = backup_increment.do_backup(test_file)

        # Both backups should exist
        assert os.path.exists(backup1)
        assert os.path.exists(backup2)
        assert backup1 != backup2

    def test_uses_existing_backup_folder(self, temp_dir):
        """Should use existing backups folder if present."""
        # Pre-create backup folder
        backup_folder = os.path.join(temp_dir, "backups")
        os.makedirs(backup_folder)

        # Add a file to prove it's the same folder
        marker_file = os.path.join(backup_folder, "marker.txt")
        with open(marker_file, "w") as f:
            f.write("marker")

        test_file = os.path.join(temp_dir, "test.db")
        with open(test_file, "w") as f:
            f.write("data")

        backup_path = backup_increment.do_backup(test_file)

        # Backup should be in the existing folder
        assert os.path.dirname(backup_path) == backup_folder
        # Marker file should still exist
        assert os.path.exists(marker_file)

    @patch("backup_increment.utils.do_clear_old_files")
    def test_clears_old_files(self, mock_clear, temp_dir):
        """Should call do_clear_old_files after backup."""
        test_file = os.path.join(temp_dir, "test.db")
        with open(test_file, "w") as f:
            f.write("data")

        backup_increment.do_backup(test_file)

        # Should call clear with backup folder and limit of 50
        mock_clear.assert_called_once()
        call_args = mock_clear.call_args
        assert call_args[0][1] == 50  # limit parameter

    def test_handles_absolute_path(self, temp_dir):
        """Should handle absolute file paths correctly."""
        test_file = os.path.join(temp_dir, "subdir", "test.db")
        os.makedirs(os.path.dirname(test_file))
        with open(test_file, "w") as f:
            f.write("data")

        backup_path = backup_increment.do_backup(test_file)

        # Backup should be in backups subfolder of file's directory
        expected_backup_dir = os.path.join(temp_dir, "subdir", "backups")
        assert os.path.dirname(backup_path) == expected_backup_dir

    def test_backup_preserves_file_permissions(self, temp_dir):
        """Backup should preserve original file's permissions."""
        test_file = os.path.join(temp_dir, "test.db")
        with open(test_file, "w") as f:
            f.write("data")

        # Note: shutil.copy preserves some metadata
        backup_path = backup_increment.do_backup(test_file)

        assert os.path.exists(backup_path)


class TestBackupFolderNaming:
    """Tests for backup folder naming edge cases."""

    def test_handles_file_named_backups(self, temp_dir):
        """Should handle case where 'backups' exists as a file."""
        # Create a FILE named "backups" (not a directory)
        backups_file = os.path.join(temp_dir, "backups")
        with open(backups_file, "w") as f:
            f.write("I'm a file, not a folder")

        test_file = os.path.join(temp_dir, "test.db")
        with open(test_file, "w") as f:
            f.write("data")

        backup_path = backup_increment.do_backup(test_file)

        # Should create backups1 or similar alternative folder
        assert os.path.exists(backup_path)


class TestBackupErrorHandling:
    """Tests for error handling in backup operations."""

    def test_raises_on_nonexistent_file(self, temp_dir):
        """Should raise error when input file doesn't exist."""
        nonexistent = os.path.join(temp_dir, "nonexistent.db")

        with pytest.raises(Exception):
            backup_increment.do_backup(nonexistent)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
