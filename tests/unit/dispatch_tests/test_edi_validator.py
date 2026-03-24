"""Tests for dispatch/edi_validator.py module."""

import logging
import os
import tempfile

from dispatch.edi_validator import EDIValidator, RealFileSystem


class MockFileSystem:
    """Mock file system for testing."""

    def __init__(self, files: dict[str, str] = None):
        """Initialize with optional file contents.

        Args:
            files: Dictionary mapping file paths to contents
        """
        self.files = files or {}

    def read_file_text(self, path: str, encoding: str = "utf-8") -> str:
        """Read file contents from mock."""
        if path not in self.files:
            raise FileNotFoundError(f"File not found: {path}")
        return self.files[path]


class TestEDIValidator:
    """Tests for EDIValidator class."""

    def test_validate_valid_edi_file(self, caplog):
        """Test validation of a valid EDI file."""
        # Create a valid EDI file content
        # A record (header), B record (detail), C record (footer)
        # B record must be exactly 76 chars with valid 11-digit numeric UPC
        # Format: B (1) + UPC (11) + padding (64) = 76 total
        edi_content = "AHEADER\nB12345678901" + " " * 64 + "\nCFOOTER\n"

        mock_fs = MockFileSystem({"/test/file.edi": edi_content})

        validator = EDIValidator(file_system=mock_fs)
        with caplog.at_level(logging.DEBUG, logger="dispatch.edi_validator"):
            is_valid, errors = validator.validate("/test/file.edi")

        # This test validates the format check logic
        # If the B record is exactly 76 chars with valid UPC, it should pass format check
        assert is_valid is True
        assert errors == []
        assert "validation passed" in caplog.text

    def test_validate_invalid_first_char(self, caplog):
        """Test validation fails when first char is not 'A'."""
        edi_content = "XHEADER\nB1234567890" + " " * 60 + "\n"

        mock_fs = MockFileSystem({"/test/file.edi": edi_content})

        validator = EDIValidator(file_system=mock_fs)
        with caplog.at_level(logging.DEBUG, logger="dispatch.edi_validator"):
            is_valid, errors = validator.validate("/test/file.edi")

        assert is_valid is False
        assert len(errors) > 0
        assert "line number" in errors[0].lower()
        assert "failed" in caplog.text

    def test_validate_invalid_record_type(self):
        """Test validation fails with invalid record type."""
        edi_content = "AHEADER\nXINVALID\nCFOOTER\n"

        mock_fs = MockFileSystem({"/test/file.edi": edi_content})

        validator = EDIValidator(file_system=mock_fs)
        is_valid, errors = validator.validate("/test/file.edi")

        assert is_valid is False

    def test_validate_b_record_wrong_length(self):
        """Test validation fails with B record of wrong length."""
        edi_content = "AHEADER\nB1234567890short\nCFOOTER\n"

        mock_fs = MockFileSystem({"/test/file.edi": edi_content})

        validator = EDIValidator(file_system=mock_fs)
        is_valid, errors = validator.validate("/test/file.edi")

        assert is_valid is False

    def test_validate_with_warnings(self):
        """Test validation with warnings (minor errors)."""
        # Create EDI with suppressed UPC (8 chars); 70-char B record (missing pricing format)
        edi_content = "AHEADER\nB12345678" + " " * 61 + "\nCFOOTER\n"

        mock_fs = MockFileSystem({"/test/file.edi": edi_content})

        validator = EDIValidator(file_system=mock_fs)
        is_valid, errors, warnings = validator.validate_with_warnings("/test/file.edi")

        # Should be valid but have warnings
        assert is_valid is True
        assert len(warnings) > 0
        assert "Suppressed UPC" in warnings[0]

    def test_validate_blank_upc(self):
        """Test validation detects blank UPC."""
        # 76-char B record with blank UPC (valid format, minor error)
        edi_content = "AHEADER\nB           " + " " * 64 + "\nCFOOTER\n"

        mock_fs = MockFileSystem({"/test/file.edi": edi_content})

        validator = EDIValidator(file_system=mock_fs)
        is_valid, errors, warnings = validator.validate_with_warnings("/test/file.edi")

        # Blank UPC is a minor error (warning), file is still valid
        assert is_valid is True
        assert any("Blank UPC" in w for w in warnings)

    def test_validate_missing_pricing(self):
        """Test validation detects missing pricing (70 char line)."""
        # 70-char B record (valid format, minor error for missing pricing)
        edi_content = "AHEADER\nB1234567890" + " " * 59 + "\nCFOOTER\n"

        mock_fs = MockFileSystem({"/test/file.edi": edi_content})

        validator = EDIValidator(file_system=mock_fs)
        is_valid, errors, warnings = validator.validate_with_warnings("/test/file.edi")

        assert is_valid is True
        assert any("Missing pricing" in w for w in warnings)

    def test_validate_file_not_found(self):
        """Test validation with non-existent file."""
        mock_fs = MockFileSystem({})

        validator = EDIValidator(file_system=mock_fs)
        is_valid, errors = validator.validate("/nonexistent/file.edi")

        assert is_valid is False
        assert len(errors) > 0

    def test_get_error_log(self):
        """Test getting error log contents."""
        edi_content = "XINVALID\n"

        mock_fs = MockFileSystem({"/test/file.edi": edi_content})

        validator = EDIValidator(file_system=mock_fs)
        validator.validate("/test/file.edi")

        log = validator.get_error_log()

        assert len(log) > 0

    def test_clear(self):
        """Test clearing validator state."""
        edi_content = "XINVALID\n"

        mock_fs = MockFileSystem({"/test/file.edi": edi_content})

        validator = EDIValidator(file_system=mock_fs)
        validator.validate("/test/file.edi")

        validator.clear()

        assert validator.has_errors is False
        assert validator.has_minor_errors is False
        assert validator.get_error_log() == ""

    def test_multiple_validations(self):
        """Test multiple validations reset state."""
        mock_fs = MockFileSystem(
            {"/test/valid.edi": "AHEADER\nCFOOTER\n", "/test/invalid.edi": "XINVALID\n"}
        )

        validator = EDIValidator(file_system=mock_fs)

        # First validation (invalid)
        is_valid1, _ = validator.validate("/test/invalid.edi")
        assert is_valid1 is False

        # Second validation (valid) should reset state
        is_valid2, _ = validator.validate("/test/valid.edi")
        assert is_valid2 is True


class TestRealFileSystem:
    """Tests for RealFileSystem class."""

    def test_read_file_text(self):
        """Test reading text file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("test content")
            temp_path = f.name

        try:
            fs = RealFileSystem()
            content = fs.read_file_text(temp_path)

            assert content == "test content"
        finally:
            os.unlink(temp_path)

    def test_read_file(self):
        """Test reading binary file."""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(b"\x00\x01\x02\x03")
            temp_path = f.name

        try:
            fs = RealFileSystem()
            content = fs.read_file(temp_path)

            assert content == b"\x00\x01\x02\x03"
        finally:
            os.unlink(temp_path)

    def test_write_file_text(self):
        """Test writing text file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            temp_path = f.name

        try:
            fs = RealFileSystem()
            fs.write_file_text(temp_path, "new content")

            with open(temp_path, "r") as f:
                assert f.read() == "new content"
        finally:
            os.unlink(temp_path)

    def test_write_file(self):
        """Test writing binary file."""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            temp_path = f.name

        try:
            fs = RealFileSystem()
            fs.write_file(temp_path, b"\xff\xfe\xfd")

            with open(temp_path, "rb") as f:
                assert f.read() == b"\xff\xfe\xfd"
        finally:
            os.unlink(temp_path)

    def test_file_exists(self):
        """Test file existence check."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            temp_path = f.name

        try:
            fs = RealFileSystem()

            assert fs.file_exists(temp_path) is True
            assert fs.file_exists("/nonexistent/file.txt") is False
        finally:
            os.unlink(temp_path)

    def test_dir_exists(self):
        """Test directory existence check."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fs = RealFileSystem()

            assert fs.dir_exists(tmpdir) is True
            assert fs.dir_exists("/nonexistent/directory") is False

    def test_list_files(self):
        """Test listing files in directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files
            file1 = os.path.join(tmpdir, "file1.txt")
            file2 = os.path.join(tmpdir, "file2.edi")
            open(file1, "w").close()
            open(file2, "w").close()

            fs = RealFileSystem()
            files = fs.list_files(tmpdir)

            assert len(files) == 2
            assert all(os.path.isabs(f) for f in files)

    def test_mkdir(self):
        """Test creating directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = os.path.join(tmpdir, "newdir")

            fs = RealFileSystem()
            fs.mkdir(new_dir)

            assert os.path.isdir(new_dir)

    def test_makedirs(self):
        """Test creating nested directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = os.path.join(tmpdir, "a", "b", "c")

            fs = RealFileSystem()
            fs.makedirs(nested)

            assert os.path.isdir(nested)

    def test_copy_file(self):
        """Test copying file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "source.txt")
            dst = os.path.join(tmpdir, "dest.txt")

            with open(src, "w") as f:
                f.write("content")

            fs = RealFileSystem()
            fs.copy_file(src, dst)

            assert os.path.exists(dst)
            with open(dst, "r") as f:
                assert f.read() == "content"

    def test_remove_file(self):
        """Test removing file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            temp_path = f.name

        fs = RealFileSystem()
        fs.remove_file(temp_path)

        assert not os.path.exists(temp_path)

    def test_get_absolute_path(self):
        """Test getting absolute path."""
        fs = RealFileSystem()

        result = fs.get_absolute_path("relative/path.txt")

        assert os.path.isabs(result)


class TestUPCRegressions:
    """Regression tests for UPC validation bug fixes.

    Covers:
    - Non-numeric UPC must be a non-fatal warning, not a hard failure.
    - Warning messages must include line number, UPC value, and item description.
    """

    # B record layout: B(1) + UPC(11) + description(25) + rest(39) = 76 chars
    # or 70-char variant: B(1) + UPC(11) + description(25) + rest(33) = 70 chars

    @staticmethod
    def _b_record(upc: str, description: str, length: int = 76) -> str:
        """Build a B record of the requested length."""
        upc_field = upc.ljust(11)[:11]
        desc_field = description.ljust(25)[:25]
        filler = " " * (length - 1 - 11 - 25)
        return "B" + upc_field + desc_field + filler

    def test_non_numeric_upc_is_not_fatal(self):
        """Regression: non-numeric UPC must not cause hard validation failure.

        Previously a non-numeric UPC (e.g. 'N4143303084') would return
        is_valid=False. It should instead return is_valid=True with a warning.
        """
        b_line = self._b_record("N4143303084", "SOME ITEM DESC")
        edi_content = f"AHEADER\n{b_line}\nCFOOTER\n"
        mock_fs = MockFileSystem({"/test/file.edi": edi_content})

        validator = EDIValidator(file_system=mock_fs)
        is_valid, errors = validator.validate("/test/file.edi")

        assert is_valid is True, "Non-numeric UPC should not be a fatal error"
        assert validator.has_minor_errors is True
        assert any("Non-numeric UPC" in e for e in errors)

    def test_non_numeric_upc_warning_includes_upc_value(self):
        """Regression: warning for non-numeric UPC must include the offending UPC."""
        b_line = self._b_record("N4143303084", "SOME ITEM DESC")
        edi_content = f"AHEADER\n{b_line}\nCFOOTER\n"
        mock_fs = MockFileSystem({"/test/file.edi": edi_content})

        validator = EDIValidator(file_system=mock_fs)
        _, errors = validator.validate("/test/file.edi")

        assert any("N4143303084" in e for e in errors), (
            "Warning should include the offending UPC value"
        )

    def test_non_numeric_upc_warning_includes_description(self):
        """Regression: warning for non-numeric UPC must include item description."""
        b_line = self._b_record("N4143303084", "TURK/PROV SUB ITEM")
        edi_content = f"AHEADER\n{b_line}\nCFOOTER\n"
        mock_fs = MockFileSystem({"/test/file.edi": edi_content})

        validator = EDIValidator(file_system=mock_fs)
        _, errors = validator.validate("/test/file.edi")

        assert any("TURK/PROV SUB ITEM" in e for e in errors), (
            "Warning should include the item description"
        )

    def test_non_numeric_upc_warning_via_validate_with_warnings(self):
        """Regression: non-numeric UPC appears in warnings via validate_with_warnings."""
        b_line = self._b_record("N4143303084", "SOME ITEM DESC")
        edi_content = f"AHEADER\n{b_line}\nCFOOTER\n"
        mock_fs = MockFileSystem({"/test/file.edi": edi_content})

        validator = EDIValidator(file_system=mock_fs)
        is_valid, errors, warnings = validator.validate_with_warnings("/test/file.edi")

        assert is_valid is True
        assert errors == []
        assert any("Non-numeric UPC" in w for w in warnings)
        assert any("N4143303084" in w for w in warnings)

    def test_suppressed_upc_warning_includes_context(self):
        """Warning for suppressed UPC must include UPC value and description."""
        upc_8 = "12345678"  # 8-char suppressed UPC, padded to 11 in field
        b_line = self._b_record(upc_8, "SUPPRESSED ITEM")
        edi_content = f"AHEADER\n{b_line}\nCFOOTER\n"
        mock_fs = MockFileSystem({"/test/file.edi": edi_content})

        validator = EDIValidator(file_system=mock_fs)
        is_valid, errors, warnings = validator.validate_with_warnings("/test/file.edi")

        assert is_valid is True
        assert any("Suppressed UPC" in w for w in warnings)
        assert any("12345678" in w for w in warnings)
        assert any("SUPPRESSED ITEM" in w for w in warnings)

    def test_blank_upc_warning_includes_context(self):
        """Warning for blank UPC must include line number and description."""
        b_line = self._b_record("           ", "BLANK UPC ITEM")
        edi_content = f"AHEADER\n{b_line}\nCFOOTER\n"
        mock_fs = MockFileSystem({"/test/file.edi": edi_content})

        validator = EDIValidator(file_system=mock_fs)
        is_valid, errors, warnings = validator.validate_with_warnings("/test/file.edi")

        assert is_valid is True
        assert any("Blank UPC" in w for w in warnings)
        assert any("BLANK UPC ITEM" in w for w in warnings)

    def test_missing_pricing_warning_includes_context(self):
        """Warning for missing pricing must include UPC value and description."""
        b_line = self._b_record("12345678901", "MISSING PRICE ITEM", length=70)
        edi_content = f"AHEADER\n{b_line}\nCFOOTER\n"
        mock_fs = MockFileSystem({"/test/file.edi": edi_content})

        validator = EDIValidator(file_system=mock_fs)
        is_valid, errors, warnings = validator.validate_with_warnings("/test/file.edi")

        assert is_valid is True
        assert any("Missing pricing" in w for w in warnings)
        assert any("12345678901" in w for w in warnings)
        assert any("MISSING PRICE" in w for w in warnings)

    def test_warning_includes_line_number(self):
        """Warning message must include the line number of the offending record."""
        b_line = self._b_record("N4143303084", "SOME ITEM")
        # Put two A/C lines before B so the B is on line 3
        edi_content = f"AHEADER\nASECOND\n{b_line}\nCFOOTER\n"
        mock_fs = MockFileSystem({"/test/file.edi": edi_content})

        validator = EDIValidator(file_system=mock_fs)
        _, errors = validator.validate("/test/file.edi")

        assert any("line 3" in e for e in errors), (
            "Warning should contain the correct line number"
        )


class TestEDIValidatorEdgeCases:
    """Edge case tests for EDIValidator."""

    def test_empty_file(self):
        """Test validation of empty file."""
        mock_fs = MockFileSystem({"/test/empty.edi": ""})

        validator = EDIValidator(file_system=mock_fs)
        is_valid, errors = validator.validate("/test/empty.edi")

        assert is_valid is False

    def test_single_line_file(self):
        """Test validation of single line file."""
        mock_fs = MockFileSystem({"/test/single.edi": "AHEADER"})

        validator = EDIValidator(file_system=mock_fs)
        is_valid, errors = validator.validate("/test/single.edi")

        assert is_valid is True

    def test_file_with_only_whitespace(self):
        """Test validation of file with only whitespace."""
        mock_fs = MockFileSystem({"/test/whitespace.edi": "   \n   \n   "})

        validator = EDIValidator(file_system=mock_fs)
        is_valid, errors = validator.validate("/test/whitespace.edi")

        assert is_valid is False

    def test_unicode_content(self):
        """Test validation with unicode content."""
        mock_fs = MockFileSystem(
            {"/test/unicode.edi": "AHEADER\nB1234567890" + " " * 59 + "\nCFOOTER\n"}
        )

        validator = EDIValidator(file_system=mock_fs)
        is_valid, errors = validator.validate("/test/unicode.edi")

        # Should handle unicode without error
        assert isinstance(is_valid, bool)
