"""
Comprehensive unit tests for the dispatch EDI validator module.

These tests cover the EDIValidator class and ValidationResult dataclass
with extensive mocking of external dependencies.
"""

import os
import tempfile
from io import StringIO
from unittest.mock import MagicMock, Mock, patch

import pytest

# Import the module under test
from dispatch.edi_validator import (
    ValidationResult,
    EDIValidator,
)


# =============================================================================
# ValidationResult Tests
# =============================================================================

class TestValidationResult:
    """Tests for the ValidationResult dataclass."""

    def test_initialization_default_values(self):
        """Test ValidationResult initialization with default values."""
        result = ValidationResult(has_errors=True)

        assert result.has_errors is True
        assert result.error_message == ""
        assert result.has_minor_errors is False

    def test_initialization_all_values(self):
        """Test ValidationResult initialization with all values."""
        result = ValidationResult(
            has_errors=True,
            error_message="Test error message",
            has_minor_errors=True
        )

        assert result.has_errors is True
        assert result.error_message == "Test error message"
        assert result.has_minor_errors is True

    def test_initialization_no_errors(self):
        """Test ValidationResult initialization with no errors."""
        result = ValidationResult(has_errors=False)

        assert result.has_errors is False
        assert result.error_message == ""
        assert result.has_minor_errors is False

    def test_initialization_minor_errors_only(self):
        """Test ValidationResult initialization with only minor errors."""
        result = ValidationResult(
            has_errors=False,
            error_message="Minor issues found",
            has_minor_errors=True
        )

        assert result.has_errors is False
        assert result.error_message == "Minor issues found"
        assert result.has_minor_errors is True


# =============================================================================
# EDIValidator Tests
# =============================================================================

class TestEDIValidator:
    """Tests for the EDIValidator class."""

    def test_initialization(self):
        """Test EDIValidator initialization."""
        validator = EDIValidator()

        assert isinstance(validator.errors, StringIO)
        assert validator.has_errors is False

    def test_validate_file_success_no_errors(self):
        """Test successful file validation with no errors."""
        validator = EDIValidator()

        with patch("dispatch.edi_validator.mtc_edi_validator.report_edi_issues") as mock_report:
            mock_output = StringIO()
            mock_report.return_value = (mock_output, False, False)

            result = validator.validate_file("/path/to/file.edi", "file.edi")

            assert isinstance(result, ValidationResult)
            assert result.has_errors is False
            assert result.has_minor_errors is False
            assert result.error_message == ""

    def test_validate_file_with_errors(self):
        """Test file validation with errors."""
        validator = EDIValidator()

        with patch("dispatch.edi_validator.mtc_edi_validator.report_edi_issues") as mock_report:
            mock_output = StringIO()
            mock_output.write("EDI validation error on line 5")
            mock_report.return_value = (mock_output, True, False)

            result = validator.validate_file("/path/to/file.edi", "file.edi")

            assert result.has_errors is True
            assert result.has_minor_errors is False
            assert "EDI validation error" in result.error_message

    def test_validate_file_with_minor_errors(self):
        """Test file validation with minor errors."""
        validator = EDIValidator()

        with patch("dispatch.edi_validator.mtc_edi_validator.report_edi_issues") as mock_report:
            mock_output = StringIO()
            mock_output.write("Minor EDI issue on line 3")
            mock_report.return_value = (mock_output, False, True)

            result = validator.validate_file("/path/to/file.edi", "file.edi")

            assert result.has_errors is False
            assert result.has_minor_errors is True
            assert "Minor EDI issue" in result.error_message

    def test_validate_file_with_both_error_types(self):
        """Test file validation with both major and minor errors."""
        validator = EDIValidator()

        with patch("dispatch.edi_validator.mtc_edi_validator.report_edi_issues") as mock_report:
            mock_output = StringIO()
            mock_output.write("Multiple EDI issues found")
            mock_report.return_value = (mock_output, True, True)

            result = validator.validate_file("/path/to/file.edi", "file.edi")

            assert result.has_errors is True
            assert result.has_minor_errors is True

    def test_validate_file_accumulates_errors(self):
        """Test that validate_file accumulates errors in validator."""
        validator = EDIValidator()

        with patch("dispatch.edi_validator.mtc_edi_validator.report_edi_issues") as mock_report:
            mock_output = StringIO()
            mock_output.write("Error 1")
            mock_report.return_value = (mock_output, True, False)

            validator.validate_file("/path/to/file1.edi", "file1.edi")

            mock_output2 = StringIO()
            mock_output2.write("Error 2")
            mock_report.return_value = (mock_output2, True, False)

            validator.validate_file("/path/to/file2.edi", "file2.edi")

            report = validator.get_validation_report()
            assert "Errors for file1.edi" in report
            assert "Errors for file2.edi" in report
            assert validator.has_errors is True

    def test_validate_file_exception_handling(self):
        """Test file validation exception handling."""
        validator = EDIValidator()

        with patch("dispatch.edi_validator.mtc_edi_validator.report_edi_issues") as mock_report:
            mock_report.side_effect = Exception("Validator crashed")

            result = validator.validate_file("/path/to/file.edi", "file.edi")

            assert result.has_errors is True
            assert "Error validating file" in result.error_message
            assert validator.has_errors is True

    def test_get_validation_report_empty(self):
        """Test getting empty validation report."""
        validator = EDIValidator()

        report = validator.get_validation_report()

        assert report == ""

    def test_get_validation_report_with_content(self):
        """Test getting validation report with content."""
        validator = EDIValidator()
        validator.errors.write("Error 1\n")
        validator.errors.write("Error 2\n")

        report = validator.get_validation_report()

        assert "Error 1" in report
        assert "Error 2" in report

    def test_close(self):
        """Test closing the validator."""
        validator = EDIValidator()
        validator.errors.write("Some error")

        validator.close()

        # After closing, the StringIO should be closed
        with pytest.raises(ValueError):
            validator.errors.write("More error")


# =============================================================================
# Integration Tests
# =============================================================================

class TestEDIValidatorIntegration:
    """Integration tests for EDI validation workflows."""

    def test_validate_multiple_files(self):
        """Test validating multiple files."""
        validator = EDIValidator()

        with patch("dispatch.edi_validator.mtc_edi_validator.report_edi_issues") as mock_report:
            # First file: no errors
            mock_output1 = StringIO()
            mock_report.return_value = (mock_output1, False, False)
            result1 = validator.validate_file("/path/to/file1.edi", "file1.edi")

            # Second file: minor errors
            mock_output2 = StringIO()
            mock_output2.write("Minor issue")
            mock_report.return_value = (mock_output2, False, True)
            result2 = validator.validate_file("/path/to/file2.edi", "file2.edi")

            # Third file: major errors
            mock_output3 = StringIO()
            mock_output3.write("Major issue")
            mock_report.return_value = (mock_output3, True, False)
            result3 = validator.validate_file("/path/to/file3.edi", "file3.edi")

            assert result1.has_errors is False
            assert result2.has_minor_errors is True
            assert result3.has_errors is True

            report = validator.get_validation_report()
            assert "file2.edi" in report
            assert "file3.edi" in report

    def test_validation_report_format(self):
        """Test validation report format."""
        validator = EDIValidator()

        with patch("dispatch.edi_validator.mtc_edi_validator.report_edi_issues") as mock_report:
            mock_output = StringIO()
            mock_output.write("Line 5: Invalid UPC\n")
            mock_output.write("Line 10: Missing field\n")
            mock_report.return_value = (mock_output, True, False)

            validator.validate_file("/path/to/test.edi", "test.edi")

            report = validator.get_validation_report()
            assert "Errors for test.edi:" in report
            assert "Line 5: Invalid UPC" in report
            assert "Line 10: Missing field" in report


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_validate_file_with_empty_output(self):
        """Test validation with empty output from validator."""
        validator = EDIValidator()

        with patch("dispatch.edi_validator.mtc_edi_validator.report_edi_issues") as mock_report:
            mock_output = StringIO()
            mock_report.return_value = (mock_output, True, False)

            result = validator.validate_file("/path/to/file.edi", "file.edi")

            assert result.has_errors is True
            assert result.error_message == ""

    def test_validate_file_with_very_long_filename(self):
        """Test validation with very long filename."""
        validator = EDIValidator()
        long_filename = "a" * 500 + ".edi"

        with patch("dispatch.edi_validator.mtc_edi_validator.report_edi_issues") as mock_report:
            mock_output = StringIO()
            mock_report.return_value = (mock_output, False, False)

            result = validator.validate_file(f"/path/to/{long_filename}", long_filename)

            assert result.has_errors is False

    def test_validate_file_with_special_chars_in_filename(self):
        """Test validation with special characters in filename."""
        validator = EDIValidator()
        special_filename = "file with spaces (v2.0).edi"

        with patch("dispatch.edi_validator.mtc_edi_validator.report_edi_issues") as mock_report:
            mock_output = StringIO()
            mock_output.write("Minor error")
            mock_report.return_value = (mock_output, False, True)

            result = validator.validate_file(f"/path/to/{special_filename}", special_filename)

            report = validator.get_validation_report()
            assert special_filename in report

    def test_validate_file_unicode_error_message(self):
        """Test validation with unicode error message."""
        validator = EDIValidator()

        with patch("dispatch.edi_validator.mtc_edi_validator.report_edi_issues") as mock_report:
            mock_output = StringIO()
            mock_output.write("Erreur avec accents: éèàù")
            mock_report.return_value = (mock_output, True, False)

            result = validator.validate_file("/path/to/file.edi", "file.edi")

            assert "Erreur avec accents" in result.error_message

    def test_multiple_validators_independent(self):
        """Test that multiple validators are independent."""
        validator1 = EDIValidator()
        validator2 = EDIValidator()

        with patch("dispatch.edi_validator.mtc_edi_validator.report_edi_issues") as mock_report:
            mock_output = StringIO()
            mock_output.write("Error")
            mock_report.return_value = (mock_output, True, False)

            validator1.validate_file("/path/to/file.edi", "file.edi")

            # validator2 should not have the errors
            assert validator2.has_errors is False
            assert validator2.get_validation_report() == ""

    def test_validator_reuse(self):
        """Test reusing validator for multiple validations."""
        validator = EDIValidator()

        with patch("dispatch.edi_validator.mtc_edi_validator.report_edi_issues") as mock_report:
            # First validation: error
            mock_output1 = StringIO()
            mock_output1.write("First error")
            mock_report.return_value = (mock_output1, True, False)
            result1 = validator.validate_file("/path/to/file1.edi", "file1.edi")

            # Second validation: no error
            mock_output2 = StringIO()
            mock_report.return_value = (mock_output2, False, False)
            result2 = validator.validate_file("/path/to/file2.edi", "file2.edi")

            # Third validation: minor error
            mock_output3 = StringIO()
            mock_output3.write("Minor error")
            mock_report.return_value = (mock_output3, False, True)
            result3 = validator.validate_file("/path/to/file3.edi", "file3.edi")

            # All results should be independent
            assert result1.has_errors is True
            assert result2.has_errors is False
            assert result3.has_minor_errors is True

            # Validator should have accumulated all errors
            report = validator.get_validation_report()
            assert "file1.edi" in report
            assert "file3.edi" in report

    def test_exception_in_error_reporting(self):
        """Test handling of exception during error reporting."""
        validator = EDIValidator()

        with patch("dispatch.edi_validator.mtc_edi_validator.report_edi_issues") as mock_report:
            mock_report.side_effect = [
                Exception("First call fails"),
                Exception("Second call fails too")
            ]

            # Both calls should handle exceptions gracefully
            result1 = validator.validate_file("/path/to/file1.edi", "file1.edi")
            result2 = validator.validate_file("/path/to/file2.edi", "file2.edi")

            assert result1.has_errors is True
            assert result2.has_errors is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
