"""Tests for dispatch.services.file_processing_helpers."""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from dispatch.services.file_processing_helpers import FileProcessingHelpers


class TestFileProcessingHelpers:
    """Tests for FileProcessingHelpers class."""

    def test_folder_exists_with_real_folder(self):
        """Test folder_exists returns True for existing folder."""
        helpers = FileProcessingHelpers()
        with tempfile.TemporaryDirectory() as tmpdir:
            assert helpers.folder_exists(tmpdir) is True

    def test_folder_exists_with_nonexistent_folder(self):
        """Test folder_exists returns False for missing folder."""
        helpers = FileProcessingHelpers()
        assert helpers.folder_exists("/nonexistent/path/12345") is False

    def test_get_files_in_folder(self):
        """Test get_files_in_folder returns files."""
        helpers = FileProcessingHelpers()
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "file1.txt").write_text("content1")
            Path(tmpdir, "file2.txt").write_text("content2")

            files = helpers.get_files_in_folder(tmpdir)
            assert len(files) == 2
            assert all(os.path.isabs(f) for f in files)

    def test_get_files_in_folder_excludes_directories(self):
        """Test get_files_in_folder excludes subdirectories."""
        helpers = FileProcessingHelpers()
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "file.txt").write_text("content")
            Path(tmpdir, "subdir").mkdir()

            files = helpers.get_files_in_folder(tmpdir)
            assert len(files) == 1

    def test_calculate_checksum(self):
        """Test checksum calculation."""
        helpers = FileProcessingHelpers()
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("test content")
            temp_path = f.name

        try:
            checksum = helpers.calculate_checksum(temp_path)
            assert isinstance(checksum, str)
            assert len(checksum) == 32  # MD5 hex length
            assert checksum == helpers.calculate_checksum(temp_path)  # Consistent
        finally:
            os.unlink(temp_path)

    def test_extract_invoice_numbers(self):
        """Test invoice number extraction from EDI file."""
        helpers = FileProcessingHelpers()
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".edi") as f:
            f.write("AVENDOR00000000010101250000100000\n")
            f.write("Brecord data here\n")
            f.write("AVENDOR00000000020102250000200000\n")
            temp_path = f.name

        try:
            invoices = helpers.extract_invoice_numbers(temp_path)
            assert "0000000001" in invoices
            assert "0000000002" in invoices
        finally:
            os.unlink(temp_path)

    def test_cleanup_temp_artifacts(self):
        """Test cleanup removes temp files and directories."""
        helpers = FileProcessingHelpers()
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_file = os.path.join(tmpdir, "temp.txt")
            Path(temp_file).write_text("temp content")

            context = Mock()
            context.temp_files = [temp_file]
            context.temp_dirs = []

            helpers.cleanup_temp_artifacts(context)

            assert not os.path.exists(temp_file)
            assert context.temp_files == []

    def test_detect_enabled_backends(self):
        """Test backend detection from folder config."""
        helpers = FileProcessingHelpers()

        folder = {
            "enable_copy_backend": True,
            "enable_ftp_backend": "True",
            "enable_email_backend": False,
        }

        backends = helpers.detect_enabled_backends(folder)
        assert "copy" in backends
        assert "ftp" in backends
        assert "email" not in backends

    def test_detect_enabled_backends_none(self):
        """Test backend detection when none enabled."""
        helpers = FileProcessingHelpers()
        folder = {}
        backends = helpers.detect_enabled_backends(folder)
        assert backends == []

    def test_validate_rename_template_valid(self):
        """Test valid template passes validation."""
        helpers = FileProcessingHelpers()
        # Should not raise
        helpers.validate_rename_template("{filename}.bak")
        helpers.validate_rename_template("{alias}_{filename}")

    def test_validate_rename_template_empty(self):
        """Test empty template raises ValueError."""
        helpers = FileProcessingHelpers()
        with pytest.raises(ValueError, match="cannot be empty"):
            helpers.validate_rename_template("")

    def test_validate_rename_template_unbalanced_braces(self):
        """Test unbalanced braces raises ValueError."""
        helpers = FileProcessingHelpers()
        with pytest.raises(ValueError, match="Unbalanced braces"):
            helpers.validate_rename_template("{filename.bak")

    def test_apply_file_rename_no_template(self):
        """Test file rename returns original path when no template."""
        helpers = FileProcessingHelpers()
        context = Mock()
        context.effective_folder = {"rename_file_template": None}

        result = helpers.apply_file_rename("/path/to/file.txt", context)
        assert result == "/path/to/file.txt"

    def test_should_validate_enabled(self):
        """Test should_validate returns True when enabled."""
        helpers = FileProcessingHelpers()
        folder = {"validate_edi": True}
        assert helpers.should_validate(folder) is True

    def test_should_validate_disabled(self):
        """Test should_validate returns False when disabled."""
        helpers = FileProcessingHelpers()
        folder = {"validate_edi": False}
        assert helpers.should_validate(folder) is False

    def test_should_validate_default(self):
        """Test should_validate returns False by default."""
        helpers = FileProcessingHelpers()
        folder = {}
        assert helpers.should_validate(folder) is False
