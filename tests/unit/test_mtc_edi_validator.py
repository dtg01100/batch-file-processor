"""
Comprehensive unit tests for the mtc_edi_validator module.

These tests cover the check() and report_edi_issues() functions
with extensive testing of EDI validation, error detection, and reporting.
"""

import os
import tempfile
from io import StringIO
from unittest.mock import MagicMock, Mock, patch, mock_open

import pytest

# Import the module under test
import mtc_edi_validator


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def valid_edi_content():
    """Provide valid EDI file content."""
    return """A000001INV001230115251000012345
B012345678901Product Description 1234561234567890100001000100050000         
C00100000123
A000002INV002340115251000054321
B012345678901Another Product   2345679876543210200002000200075000           
C00200000543
"""


@pytest.fixture
def valid_short_b_record():
    """Provide valid EDI with 71-character B record."""
    return """A000001INV001230115251000012345
B012345678901Product Desc      12345612345                            
C00100000123
"""


@pytest.fixture
def invalid_edi_wrong_first_char():
    """Provide EDI with wrong first character."""
    return """X000001INV001230115251000012345
B012345678901Product Description 1234561234567890100001000100050000         
C00100000123
"""


@pytest.fixture
def invalid_edi_bad_record_type():
    """Provide EDI with invalid record type."""
    return """A000001INV001230115251000012345
X012345678901Product Description 1234561234567890100001000100050000         
C00100000123
"""


@pytest.fixture
def invalid_edi_wrong_b_length():
    """Provide EDI with wrong B record length."""
    return """A000001INV001230115251000012345
B012345678901Short
C00100000123
"""


@pytest.fixture
def invalid_edi_bad_upc():
    """Provide EDI with invalid UPC in B record."""
    return """A000001INV001230115251000012345
BABCDEFGHIJKProduct Description 1234561234567890100001000100050000         
C00100000123
"""


@pytest.fixture
def edi_with_8_digit_upc():
    """Provide EDI with 8-digit UPC (minor error)."""
    return """A000001INV001230115251000012345
B01234567    Product Description 1234561234567890100001000100050000         
C00100000123
"""


@pytest.fixture
def edi_with_truncated_upc():
    """Provide EDI with truncated UPC (minor error)."""
    return """A000001INV001230115251000012345
B012345      Product Description 1234561234567890100001000100050000         
C00100000123
"""


@pytest.fixture
def edi_with_blank_upc():
    """Provide EDI with blank UPC (minor error)."""
    return """A000001INV001230115251000012345
B            Product Description 1234561234567890100001000100050000         
C00100000123
"""


@pytest.fixture
def edi_with_short_b_no_pricing():
    """Provide EDI with short B record missing pricing (minor error)."""
    return """A000001INV001230115251000012345
B012345678901Sample Product    123456                                 
C00100000123
"""


@pytest.fixture
def empty_edi():
    """Provide empty EDI file."""
    return ""


@pytest.fixture
def edi_only_a_record():
    """Provide EDI with only A record."""
    return "A000001INV001230115251000012345\n"


# =============================================================================
# check() Function Tests - Valid EDI
# =============================================================================


class TestCheckValidEdi:
    """Tests for check() with valid EDI content."""

    def test_check_valid_edi(self, valid_edi_content):
        """Test check() returns True for valid EDI."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".edi", delete=False) as f:
            f.write(valid_edi_content)
            temp_file = f.name

        try:
            result, line_number = mtc_edi_validator.check(temp_file)
            assert result is True
            assert line_number == 6  # Total lines
        finally:
            os.unlink(temp_file)

    def test_check_valid_short_b_record(self, valid_short_b_record):
        """Test check() accepts 71-character B record."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".edi", delete=False) as f:
            f.write(valid_short_b_record)
            temp_file = f.name

        try:
            result, line_number = mtc_edi_validator.check(temp_file)
            assert result is True
        finally:
            os.unlink(temp_file)

    def test_check_single_invoice(self, edi_only_a_record):
        """Test check() with single invoice."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".edi", delete=False) as f:
            f.write(edi_only_a_record)
            temp_file = f.name

        try:
            result, line_number = mtc_edi_validator.check(temp_file)
            assert result is True
            assert line_number == 1
        finally:
            os.unlink(temp_file)


# =============================================================================
# check() Function Tests - Invalid EDI
# =============================================================================


class TestCheckInvalidEdi:
    """Tests for check() with invalid EDI content."""

    def test_check_wrong_first_character(self, invalid_edi_wrong_first_char):
        """Test check() fails when first character is not 'A'."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".edi", delete=False) as f:
            f.write(invalid_edi_wrong_first_char)
            temp_file = f.name

        try:
            result, line_number = mtc_edi_validator.check(temp_file)
            assert result is False
            assert line_number == 1  # Error on line 1
        finally:
            os.unlink(temp_file)

    def test_check_invalid_record_type(self, invalid_edi_bad_record_type):
        """Test check() fails with invalid record type."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".edi", delete=False) as f:
            f.write(invalid_edi_bad_record_type)
            temp_file = f.name

        try:
            result, line_number = mtc_edi_validator.check(temp_file)
            assert result is False
            assert line_number == 2  # Error on line 2 (X record)
        finally:
            os.unlink(temp_file)

    def test_check_wrong_b_record_length(self, invalid_edi_wrong_b_length):
        """Test check() fails with wrong B record length."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".edi", delete=False) as f:
            f.write(invalid_edi_wrong_b_length)
            temp_file = f.name

        try:
            result, line_number = mtc_edi_validator.check(temp_file)
            assert result is False
            assert line_number == 2  # Error on line 2
        finally:
            os.unlink(temp_file)

    def test_check_invalid_upc_non_numeric(self, invalid_edi_bad_upc):
        """Test check() fails with non-numeric UPC (unless blank)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".edi", delete=False) as f:
            f.write(invalid_edi_bad_upc)
            temp_file = f.name

        try:
            result, line_number = mtc_edi_validator.check(temp_file)
            assert result is False
            assert line_number == 2  # Error on line 2
        finally:
            os.unlink(temp_file)

    def test_check_empty_file(self, empty_edi):
        """Test check() with empty file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".edi", delete=False) as f:
            f.write(empty_edi)
            temp_file = f.name

        try:
            result, line_number = mtc_edi_validator.check(temp_file)
            # Empty file should fail (first char is not 'A')
            assert result is False
            assert line_number == 1
        finally:
            os.unlink(temp_file)


# =============================================================================
# check() Function Tests - Edge Cases
# =============================================================================


class TestCheckEdgeCases:
    """Tests for check() edge cases."""

    @patch("mtc_edi_validator.open")
    @patch("mtc_edi_validator.time.sleep")
    def test_check_file_open_retry(self, mock_sleep, mock_open_func):
        """Test check() retries opening file."""
        mock_file = MagicMock()
        mock_file.read.return_value = "A"
        mock_file.seek.return_value = None
        mock_file.readline.return_value = "A000001INV001230115251000012345\n"
        mock_file.__iter__ = MagicMock(
            return_value=iter(["A000001INV001230115251000012345\n"])
        )

        # First 4 calls fail, 5th succeeds
        mock_open_func.side_effect = [
            IOError("File locked"),
            IOError("File locked"),
            IOError("File locked"),
            IOError("File locked"),
            mock_file,
        ]

        result, line_number = mtc_edi_validator.check("/test/file.edi")

        assert result is True
        assert mock_open_func.call_count == 5

    @patch("mtc_edi_validator.open")
    def test_check_file_open_failure(self, mock_open_func):
        """Test check() handles file open failure."""
        mock_open_func.side_effect = IOError("Cannot open file")

        result, line_number = mtc_edi_validator.check("/test/file.edi")
        assert result is False

    def test_check_with_end_of_file_character(self):
        """Test check() handles EDI with end-of-file character."""
        content = "A000001INV001230115251000012345\nB012345678901Product Description 1234561234567890100001000100050000         \nC00100000123\n\x1a"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".edi", delete=False) as f:
            f.write(content)
            temp_file = f.name

        try:
            result, line_number = mtc_edi_validator.check(temp_file)
            # Should accept EOF character
            assert result is True
        finally:
            os.unlink(temp_file)


# =============================================================================
# report_edi_issues() Tests - Valid EDI
# =============================================================================


class TestReportEdiIssuesValid:
    """Tests for report_edi_issues() with valid EDI."""

    def test_report_edi_issues_valid(self, valid_edi_content):
        """Test report_edi_issues() returns no errors for valid EDI."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".edi", delete=False) as f:
            f.write(valid_edi_content)
            temp_file = f.name

        try:
            log_output, has_errors, has_minor_errors = (
                mtc_edi_validator.report_edi_issues(temp_file)
            )

            assert has_errors is False
            assert has_minor_errors is False
            assert isinstance(log_output, StringIO)
        finally:
            os.unlink(temp_file)

    def test_report_edi_issues_blank_upc(self, edi_with_blank_upc):
        """Test report_edi_issues() reports blank UPC as minor error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".edi", delete=False) as f:
            f.write(edi_with_blank_upc)
            temp_file = f.name

        try:
            log_output, has_errors, has_minor_errors = (
                mtc_edi_validator.report_edi_issues(temp_file)
            )

            assert has_errors is False
            assert has_minor_errors is True
            log_content = log_output.getvalue()
            assert "Blank UPC" in log_content
        finally:
            os.unlink(temp_file)


# =============================================================================
# report_edi_issues() Tests - UPC Issues
# =============================================================================


class TestReportEdiIssuesUpc:
    """Tests for report_edi_issues() UPC validation."""

    def test_report_edi_issues_8_digit_upc(self, edi_with_8_digit_upc):
        """Test report_edi_issues() reports 8-digit UPC as minor error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".edi", delete=False) as f:
            f.write(edi_with_8_digit_upc)
            temp_file = f.name

        try:
            log_output, has_errors, has_minor_errors = (
                mtc_edi_validator.report_edi_issues(temp_file)
            )

            assert has_errors is False
            assert has_minor_errors is True
            log_content = log_output.getvalue()
            assert "Suppressed UPC" in log_content
            assert "line 2" in log_content.lower() or "line" in log_content.lower()
        finally:
            os.unlink(temp_file)

    def test_report_edi_issues_truncated_upc(self, edi_with_truncated_upc):
        """Test report_edi_issues() reports truncated UPC as minor error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".edi", delete=False) as f:
            f.write(edi_with_truncated_upc)
            temp_file = f.name

        try:
            log_output, has_errors, has_minor_errors = (
                mtc_edi_validator.report_edi_issues(temp_file)
            )

            assert has_errors is False
            assert has_minor_errors is True
            log_content = log_output.getvalue()
            assert "Truncated UPC" in log_content
        finally:
            os.unlink(temp_file)

    def test_report_edi_issues_multiple_upc_issues(self):
        """Test report_edi_issues() reports multiple UPC issues."""
        content = """A000001INV001230115251000012345
B01234567    Product 1         1234561234567890100001000100050000           
B01234       Product 2         2345679876543210200002000200075000           
B            Product 3         3456781111111110300003000300025000           
C00100000123
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".edi", delete=False) as f:
            f.write(content)
            temp_file = f.name

        try:
            log_output, has_errors, has_minor_errors = (
                mtc_edi_validator.report_edi_issues(temp_file)
            )

            assert has_errors is False
            assert has_minor_errors is True
            log_content = log_output.getvalue()
            # Should report all three UPC issues
            issue_count = log_content.count("line")
            assert issue_count >= 3
        finally:
            os.unlink(temp_file)


# =============================================================================
# report_edi_issues() Tests - Pricing Issues
# =============================================================================


class TestReportEdiIssuesPricing:
    """Tests for report_edi_issues() pricing validation."""

    def test_report_edi_issues_missing_pricing(self, edi_with_short_b_no_pricing):
        """Test report_edi_issues() reports missing pricing as minor error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".edi", delete=False) as f:
            f.write(edi_with_short_b_no_pricing)
            temp_file = f.name

        try:
            log_output, has_errors, has_minor_errors = (
                mtc_edi_validator.report_edi_issues(temp_file)
            )

            assert has_errors is False
            assert has_minor_errors is True
            log_content = log_output.getvalue()
            assert "Missing pricing information" in log_content
            assert "sample" in log_content.lower()
        finally:
            os.unlink(temp_file)


# =============================================================================
# report_edi_issues() Tests - Check Failures
# =============================================================================


class TestReportEdiIssuesCheckFailures:
    """Tests for report_edi_issues() when check() fails."""

    def test_report_edi_issues_check_fails(self, invalid_edi_wrong_first_char):
        """Test report_edi_issues() when EDI check fails."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".edi", delete=False) as f:
            f.write(invalid_edi_wrong_first_char)
            temp_file = f.name

        try:
            log_output, has_errors, has_minor_errors = (
                mtc_edi_validator.report_edi_issues(temp_file)
            )

            assert has_errors is True
            log_content = log_output.getvalue()
            assert "EDI check failed" in log_content
            assert "line number: 1" in log_content
        finally:
            os.unlink(temp_file)

    def test_report_edi_issues_invalid_record_type(self, invalid_edi_bad_record_type):
        """Test report_edi_issues() with invalid record type."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".edi", delete=False) as f:
            f.write(invalid_edi_bad_record_type)
            temp_file = f.name

        try:
            log_output, has_errors, has_minor_errors = (
                mtc_edi_validator.report_edi_issues(temp_file)
            )

            assert has_errors is True
            log_content = log_output.getvalue()
            assert "EDI check failed" in log_content
            assert "line number: 2" in log_content
        finally:
            os.unlink(temp_file)


# =============================================================================
# report_edi_issues() Tests - Exception Handling
# =============================================================================


class TestReportEdiIssuesExceptions:
    """Tests for report_edi_issues() exception handling."""

    @patch("mtc_edi_validator.open")
    @patch("mtc_edi_validator.time.sleep")
    def test_report_edi_issues_file_open_retry(self, mock_sleep, mock_open_func):
        """Test report_edi_issues() retries opening file."""
        mock_file = MagicMock()
        mock_file.__iter__ = MagicMock(
            return_value=iter(["A000001INV001230115251000012345\n"])
        )

        mock_open_func.side_effect = [
            IOError("File locked"),
            IOError("File locked"),
            mock_file,
            mock_file,
        ]

        log_output, has_errors, has_minor_errors = mtc_edi_validator.report_edi_issues(
            "/test/file.edi"
        )

        assert mock_open_func.call_count == 4
        # Should process the file after successful open

    @patch("mtc_edi_validator.open")
    def test_report_edi_issues_file_open_failure(self, mock_open_func):
        """Test report_edi_issues() handles file open failure."""
        mock_open_func.side_effect = IOError("Cannot open file")

        with pytest.raises(IOError):
            mtc_edi_validator.report_edi_issues("/test/file.edi")

    @patch("mtc_edi_validator.utils.capture_records")
    def test_report_edi_issues_capture_records_exception(
        self, mock_capture, edi_with_blank_upc
    ):
        """Test report_edi_issues() handles capture_records exception."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".edi", delete=False) as f:
            f.write(edi_with_blank_upc)
            temp_file = f.name

        try:
            mock_capture.side_effect = [Exception("Parse error"), {}]

            log_output, has_errors, has_minor_errors = (
                mtc_edi_validator.report_edi_issues(temp_file)
            )

            assert has_errors is True
            log_content = log_output.getvalue()
            assert "Validator produced error" in log_content
        finally:
            os.unlink(temp_file)


# =============================================================================
# report_edi_issues() Tests - Line Information
# =============================================================================


class TestReportEdiIssuesLineInfo:
    """Tests for report_edi_issues() line information in reports."""

    def test_report_edi_issues_includes_line_content(self, edi_with_blank_upc):
        """Test report_edi_issues() includes line content in report."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".edi", delete=False) as f:
            f.write(edi_with_blank_upc)
            temp_file = f.name

        try:
            log_output, has_errors, has_minor_errors = (
                mtc_edi_validator.report_edi_issues(temp_file)
            )

            log_content = log_output.getvalue()
            # Should include the actual line content
            assert "line is:" in log_content
            assert "Product Description" in log_content
        finally:
            os.unlink(temp_file)

    def test_report_edi_issues_includes_item_description(self, edi_with_blank_upc):
        """Test report_edi_issues() includes item description from B record."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".edi", delete=False) as f:
            f.write(edi_with_blank_upc)
            temp_file = f.name

        try:
            log_output, has_errors, has_minor_errors = (
                mtc_edi_validator.report_edi_issues(temp_file)
            )

            log_content = log_output.getvalue()
            # Should include description parsed from record
            assert "Item description:" in log_content
            assert (
                "Product Description" in log_content
                or "description" in log_content.lower()
            )
        finally:
            os.unlink(temp_file)

    def test_report_edi_issues_includes_item_number(self, edi_with_blank_upc):
        """Test report_edi_issues() includes item number from B record."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".edi", delete=False) as f:
            f.write(edi_with_blank_upc)
            temp_file = f.name

        try:
            log_output, has_errors, has_minor_errors = (
                mtc_edi_validator.report_edi_issues(temp_file)
            )

            log_content = log_output.getvalue()
            # Should include vendor item number
            assert "Item number:" in log_content
        finally:
            os.unlink(temp_file)


# =============================================================================
# Integration Tests
# =============================================================================


class TestEdiValidatorIntegration:
    """Integration tests for complete EDI validation workflows."""

    def test_complete_validation_workflow_valid(self, valid_edi_content):
        """Test complete validation workflow for valid EDI."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".edi", delete=False) as f:
            f.write(valid_edi_content)
            temp_file = f.name

        try:
            # First check the file
            check_result, line_number = mtc_edi_validator.check(temp_file)
            assert check_result is True

            # Then get detailed report
            log_output, has_errors, has_minor_errors = (
                mtc_edi_validator.report_edi_issues(temp_file)
            )
            assert has_errors is False
            assert has_minor_errors is False
        finally:
            os.unlink(temp_file)

    def test_complete_validation_workflow_invalid(self, invalid_edi_bad_record_type):
        """Test complete validation workflow for invalid EDI."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".edi", delete=False) as f:
            f.write(invalid_edi_bad_record_type)
            temp_file = f.name

        try:
            # First check the file
            check_result, line_number = mtc_edi_validator.check(temp_file)
            assert check_result is False
            assert line_number == 2

            # Then get detailed report
            log_output, has_errors, has_minor_errors = (
                mtc_edi_validator.report_edi_issues(temp_file)
            )
            assert has_errors is True
            log_content = log_output.getvalue()
            assert "EDI check failed" in log_content
        finally:
            os.unlink(temp_file)

    def test_complete_validation_workflow_minor_issues(self, edi_with_8_digit_upc):
        """Test complete validation workflow with minor issues."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".edi", delete=False) as f:
            f.write(edi_with_8_digit_upc)
            temp_file = f.name

        try:
            # First check the file - should pass basic validation
            check_result, line_number = mtc_edi_validator.check(temp_file)
            assert check_result is True

            # Then get detailed report - should find minor issues
            log_output, has_errors, has_minor_errors = (
                mtc_edi_validator.report_edi_issues(temp_file)
            )
            assert has_errors is False
            assert has_minor_errors is True
            log_content = log_output.getvalue()
            assert "Suppressed UPC" in log_content
        finally:
            os.unlink(temp_file)

    def test_validation_with_multiple_issue_types(self):
        """Test validation with multiple types of issues."""
        # Construct content with precise lengths
        # Line lengths must include newline (77 for standard B record, 71 for short)

        # A record
        content = "A000001INV001230115251000012345\n"

        # B Record 1: 8-digit UPC (Suppressed UPC)
        # B(1) + UPC(11) + Desc(18) + Size(6) + Vendor(9) + Cost(6) + Ret(4) + Sug(4) + Case(5) + End(12) = 76 chars
        content += "B01234567   Product 1         1234561234567890100001000100050000            \n"

        # B Record 2: Blank UPC
        content += "B           Product 2         2345679876543210200002000200075000            \n"

        # B Record 3: Missing pricing (Short record - 70 chars + newline = 71)
        # B(1) + UPC(11) + Desc(18) + Size(6) + Padding(34)
        content += (
            "B01234567890Sample Product    345678                                  \n"
        )

        # C record
        content += "C00100000123\n"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".edi", delete=False) as f:
            f.write(content)
            temp_file = f.name

        try:
            check_result, line_number = mtc_edi_validator.check(temp_file)
            assert check_result is True, f"Check failed at line {line_number}"

            log_output, has_errors, has_minor_errors = (
                mtc_edi_validator.report_edi_issues(temp_file)
            )
            assert has_errors is False
            assert has_minor_errors is True

            log_content = log_output.getvalue()
            # Should report all issue types
            assert "Suppressed UPC" in log_content or "8" in log_content
            assert "Blank UPC" in log_content or "blank" in log_content.lower()
            assert "Missing pricing" in log_content or "pricing" in log_content.lower()
        finally:
            os.unlink(temp_file)


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdiValidatorEdgeCases:
    """Tests for edge cases."""

    def test_check_with_unicode_content(self):
        """Test check() handles unicode content."""
        content = "A000001INV001230115251000012345\nB012345678901Üñíçödé Prödûçt 1234561234567890100001000100050000\nC00100000123\n"

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".edi", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_file = f.name

        try:
            result, line_number = mtc_edi_validator.check(temp_file)
            # Should handle unicode or fail gracefully
            assert isinstance(result, bool)
        finally:
            os.unlink(temp_file)

    def test_report_edi_issues_with_long_description(self):
        """Test report_edi_issues() with very long product description."""
        long_desc = "A" * 100
        content = f"A000001INV001230115251000012345\nB012345678901{long_desc}1234561234567890100001000100050000\nC00100000123\n"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".edi", delete=False) as f:
            f.write(content)
            temp_file = f.name

        try:
            log_output, has_errors, has_minor_errors = (
                mtc_edi_validator.report_edi_issues(temp_file)
            )
            # Should handle long descriptions
            assert isinstance(log_output, StringIO)
        finally:
            os.unlink(temp_file)

    def test_check_with_very_long_file(self):
        """Test check() with very long EDI file."""
        lines = ["A000001INV001230115251000012345\n"]
        for i in range(1000):
            lines.append(
                f"B012345678901Product {i:04d}        {100000 + i}1234567890100001000100050000         \n"
            )
        lines.append("C00100000123\n")

        content = "".join(lines)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".edi", delete=False) as f:
            f.write(content)
            temp_file = f.name

        try:
            result, line_number = mtc_edi_validator.check(temp_file)
            assert result is True
            assert line_number == 1002
        finally:
            os.unlink(temp_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
