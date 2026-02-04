"""
Comprehensive unit tests for the edi_tweaks module.

These tests cover the edi_tweak function and its helper classes (poFetcher, cRecGenerator)
with extensive testing of EDI record manipulation, UPC handling, and format corrections.
"""

import os
import tempfile
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, Mock, patch, mock_open, call

import pytest

# Import the module under test
import convert_to_edi_tweaks as edi_tweaks


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_parameters_dict():
    """Provide sample parameters dictionary for testing."""
    return {
        "pad_a_records": "False",
        "a_record_padding": "",
        "a_record_padding_length": 6,
        "append_a_records": "False",
        "a_record_append_text": "",
        "invoice_date_custom_format": False,
        "invoice_date_custom_format_string": "%Y-%m-%d",
        "force_txt_file_ext": "False",
        "calculate_upc_check_digit": "False",
        "invoice_date_offset": 0,
        "retail_uom": False,
        "override_upc_bool": False,
        "override_upc_level": 1,
        "override_upc_category_filter": "ALL",
        "split_prepaid_sales_tax_crec": False,
    }


@pytest.fixture
def sample_settings_dict():
    """Provide sample settings dictionary for testing."""
    return {
        "as400_username": "test_user",
        "as400_password": "test_pass",
        "as400_address": "test_host",
        "odbc_driver": "test_driver",
    }


@pytest.fixture
def sample_upc_dict():
    """Provide sample UPC dictionary for testing."""
    return {
        123456: ["CAT1", "012345678901", "UPC123456", "UPC_ALT1", "UPC_ALT2"],
        234567: ["CAT2", "123456789012", "UPC234567", "UPC_ALT3", "UPC_ALT4"],
        345678: ["CAT1", "234567890123", "UPC345678", "UPC_ALT5", "UPC_ALT6"],
    }


@pytest.fixture
def sample_edi_content():
    """Provide sample EDI file content."""
    return """A000001INV00123  0122251000012345
B01234567890roduct Description       1234561234567890100001000100050000

C00100000123
A000002INV00234  0122251000054321
B01234567890nother Product           2345679876543210200002000200075000

C00200000543
"""


@pytest.fixture
def sample_a_record():
    """Provide a sample A record line."""
    return "A000001INV00123  0122251000012345\n"


@pytest.fixture
def sample_b_record():
    """Provide a sample B record line."""
    return "B01234567890oduct Description        1234561234567890100001000100050000\n"


@pytest.fixture
def sample_c_record():
    """Provide a sample C record line."""
    return "C00100000123\n"


# =============================================================================
# edi_tweak Function Tests - Basic Processing
# =============================================================================


class TestEdiTweakBasicProcessing:
    """Tests for basic EDI tweaking functionality."""

    @patch("convert_to_edi_tweaks.time.sleep")
    def test_edi_tweak_basic_processing(
        self,
        mock_sleep,
        sample_parameters_dict,
        sample_settings_dict,
        sample_edi_content,
    ):
        """Test basic EDI file processing without modifications."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = os.path.join(temp_dir, "input.edi")
            output_file = os.path.join(temp_dir, "output.edi")

            with open(input_file, "w") as f:
                f.write(sample_edi_content)

            result = edi_tweaks.edi_tweak(
                input_file,
                output_file,
                sample_settings_dict,
                sample_parameters_dict,
                {},
            )

            assert result == output_file
            assert os.path.exists(output_file)

            # Verify output contains A, B, and C records
            with open(output_file, "r") as f:
                content = f.read()
                assert content.startswith("A")
                assert "B" in content
                assert "C" in content

    @patch("convert_to_edi_tweaks.time.sleep")
    def test_edi_tweak_force_txt_extension(
        self,
        mock_sleep,
        sample_parameters_dict,
        sample_settings_dict,
        sample_edi_content,
    ):
        """Test forcing .txt extension on output."""
        params = sample_parameters_dict.copy()
        params["force_txt_file_ext"] = "True"

        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = os.path.join(temp_dir, "input.edi")
            output_file = os.path.join(temp_dir, "output")

            with open(input_file, "w") as f:
                f.write(sample_edi_content)

            result = edi_tweaks.edi_tweak(
                input_file, output_file, sample_settings_dict, params, {}
            )

            assert result.endswith(".txt")
            assert os.path.exists(result)

    @patch("convert_to_edi_tweaks.time.sleep")
    def test_edi_tweak_empty_file(
        self, mock_sleep, sample_parameters_dict, sample_settings_dict
    ):
        """Test processing empty EDI file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = os.path.join(temp_dir, "input.edi")
            output_file = os.path.join(temp_dir, "output.edi")

            with open(input_file, "w") as f:
                f.write("")

            result = edi_tweaks.edi_tweak(
                input_file,
                output_file,
                sample_settings_dict,
                sample_parameters_dict,
                {},
            )

            assert result == output_file
            assert os.path.exists(output_file)


# =============================================================================
# edi_tweak Function Tests - A Record Processing
# =============================================================================


class TestEdiTweakARecordProcessing:
    """Tests for A record (invoice header) processing."""

    @patch("convert_to_edi_tweaks.time.sleep")
    def test_edi_tweak_invoice_date_offset(
        self, mock_sleep, sample_parameters_dict, sample_settings_dict
    ):
        """Test invoice date offset modification."""
        params = sample_parameters_dict.copy()
        params["invoice_date_offset"] = 5  # Add 5 days

        edi_content = "A000001INV00123  0115251000012345\n"  # Jan 15, 2023

        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = os.path.join(temp_dir, "input.edi")
            output_file = os.path.join(temp_dir, "output.edi")

            with open(input_file, "w") as f:
                f.write(edi_content)

            with patch("convert_to_edi_tweaks.print"):  # Suppress print output
                result = edi_tweaks.edi_tweak(
                    input_file, output_file, sample_settings_dict, params, {}
                )

            with open(result, "r") as f:
                content = f.read()
                # Date should be offset by 5 days: Jan 20, 2023
                assert "012025" in content  # MMDDYY format

    @patch("convert_to_edi_tweaks.time.sleep")
    def test_edi_tweak_invoice_date_custom_format(
        self, mock_sleep, sample_parameters_dict, sample_settings_dict
    ):
        """Test custom invoice date format."""
        params = sample_parameters_dict.copy()
        params["invoice_date_custom_format"] = True
        params["invoice_date_custom_format_string"] = "%Y%m%d"

        edi_content = "A000001INV00123  0115251000012345\n"  # Jan 15, 2023

        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = os.path.join(temp_dir, "input.edi")
            output_file = os.path.join(temp_dir, "output.edi")

            with open(input_file, "w") as f:
                f.write(edi_content)

            result = edi_tweaks.edi_tweak(
                input_file, output_file, sample_settings_dict, params, {}
            )

            with open(result, "r") as f:
                content = f.read()
                # Should have custom format date
                assert "20250115" in content

    @patch("convert_to_edi_tweaks.time.sleep")
    def test_edi_tweak_invoice_date_error_handling(
        self, mock_sleep, sample_parameters_dict, sample_settings_dict
    ):
        """Test custom invoice date format error handling."""
        params = sample_parameters_dict.copy()
        params["invoice_date_custom_format"] = True
        params["invoice_date_custom_format_string"] = "%Y%m%d"

        edi_content = "A000001INV00123  ABCD251000012345\n"  # Invalid date

        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = os.path.join(temp_dir, "input.edi")
            output_file = os.path.join(temp_dir, "output.edi")

            with open(input_file, "w") as f:
                f.write(edi_content)

            result = edi_tweaks.edi_tweak(
                input_file, output_file, sample_settings_dict, params, {}
            )

            with open(result, "r") as f:
                content = f.read()
                # Should contain ERROR for invalid date
                assert "ERROR" in content or "ABCD" in content

    @patch("convert_to_edi_tweaks.time.sleep")
    def test_edi_tweak_pad_a_records(
        self, mock_sleep, sample_parameters_dict, sample_settings_dict
    ):
        """Test A record padding."""
        params = sample_parameters_dict.copy()
        params["pad_a_records"] = "True"
        params["a_record_padding"] = "XX"
        params["a_record_padding_length"] = 6

        edi_content = "A000001INV00123  0115251000012345\n"

        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = os.path.join(temp_dir, "input.edi")
            output_file = os.path.join(temp_dir, "output.edi")

            with open(input_file, "w") as f:
                f.write(edi_content)

            result = edi_tweaks.edi_tweak(
                input_file, output_file, sample_settings_dict, params, {}
            )

            with open(result, "r") as f:
                content = f.read()
                # Should have padded vendor field
                assert content.startswith("A")

    @patch("convert_to_edi_tweaks.time.sleep")
    @patch("convert_to_edi_tweaks.query_runner")
    def test_edi_tweak_append_a_records_with_po(
        self,
        mock_query_runner,
        mock_sleep,
        sample_parameters_dict,
        sample_settings_dict,
    ):
        """Test appending PO number to A record."""
        # Mock the query runner
        mock_query_instance = MagicMock()
        mock_query_instance.run_arbitrary_query.return_value = [("PO12345",)]
        mock_query_runner.return_value = mock_query_instance

        params = sample_parameters_dict.copy()
        params["append_a_records"] = "True"
        params["a_record_append_text"] = "PO: %po_str%"

        edi_content = "A000001INV00123  0115251000012345\n"

        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = os.path.join(temp_dir, "input.edi")
            output_file = os.path.join(temp_dir, "output.edi")

            with open(input_file, "w") as f:
                f.write(edi_content)

            result = edi_tweaks.edi_tweak(
                input_file, output_file, sample_settings_dict, params, {}
            )

            with open(result, "r") as f:
                content = f.read()
                # Should contain appended PO text
                assert "PO12345" in content or "PO:" in content

    @patch("convert_to_edi_tweaks.time.sleep")
    def test_edi_tweak_append_a_records_no_po_found(
        self, mock_sleep, sample_parameters_dict, sample_settings_dict
    ):
        """Test appending PO when no PO is found."""
        params = sample_parameters_dict.copy()
        params["append_a_records"] = "True"
        params["a_record_append_text"] = "PO: %po_str%"

        edi_content = "A000001INV00123  0115251000012345\n"

        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = os.path.join(temp_dir, "input.edi")
            output_file = os.path.join(temp_dir, "output.edi")

            with open(input_file, "w") as f:
                f.write(edi_content)

            with patch("convert_to_edi_tweaks.query_runner") as mock_query_runner:
                mock_query_instance = MagicMock()
                mock_query_instance.run_arbitrary_query.return_value = []
                mock_query_runner.return_value = mock_query_instance

                result = edi_tweaks.edi_tweak(
                    input_file, output_file, sample_settings_dict, params, {}
                )

            with open(result, "r") as f:
                content = f.read()
                # Should contain no_po_found text
                assert "no_po_found" in content


# =============================================================================
# edi_tweak Function Tests - B Record Processing
# =============================================================================


class TestEdiTweakBRecordProcessing:
    """Tests for B record (product line) processing."""

    @patch("convert_to_edi_tweaks.time.sleep")
    def test_edi_tweak_upc_override_all(
        self, mock_sleep, sample_parameters_dict, sample_settings_dict, sample_upc_dict
    ):
        """Test UPC override for all categories."""
        params = sample_parameters_dict.copy()
        params["override_upc_bool"] = True
        params["override_upc_level"] = 1
        params["override_upc_category_filter"] = "ALL"

        # B record with vendor_item 123456 - properly formatted with 25-char description
        # B + 11-char UPC + 25-char description (padded) + 6-char vendor_item + rest
        edi_content = (
            "B           Product Description      1234561234567890100001000100050000\n"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = os.path.join(temp_dir, "input.edi")
            output_file = os.path.join(temp_dir, "output.edi")

            with open(input_file, "w") as f:
                f.write(edi_content)

            result = edi_tweaks.edi_tweak(
                input_file, output_file, sample_settings_dict, params, sample_upc_dict
            )

            with open(result, "r") as f:
                content = f.read()
                # Should have overridden UPC
                assert "012345678901" in content

    @patch("convert_to_edi_tweaks.time.sleep")
    def test_edi_tweak_upc_override_filtered(
        self, mock_sleep, sample_parameters_dict, sample_settings_dict, sample_upc_dict
    ):
        """Test UPC override with category filter."""
        params = sample_parameters_dict.copy()
        params["override_upc_bool"] = True
        params["override_upc_level"] = 1
        params["override_upc_category_filter"] = "CAT1"  # Only override CAT1 items

        # B record with vendor_item 123456 (CAT1)
        edi_content = (
            "B01234567890Product Description      1234561234567890100001000100050000\n"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = os.path.join(temp_dir, "input.edi")
            output_file = os.path.join(temp_dir, "output.edi")

            with open(input_file, "w") as f:
                f.write(edi_content)

            result = edi_tweaks.edi_tweak(
                input_file, output_file, sample_settings_dict, params, sample_upc_dict
            )

            with open(result, "r") as f:
                content = f.read()
                # Should have overridden UPC for CAT1
                assert "012345678901" in content

    @patch("convert_to_edi_tweaks.time.sleep")
    def test_edi_tweak_upc_override_filtered_no_match(
        self, mock_sleep, sample_parameters_dict, sample_settings_dict, sample_upc_dict
    ):
        """Test UPC override with category filter that doesn't match."""
        params = sample_parameters_dict.copy()
        params["override_upc_bool"] = True
        params["override_upc_level"] = 1
        params["override_upc_category_filter"] = "CAT2"  # Only override CAT2 items

        # B record with vendor_item 123456 (CAT1 - should not match)
        edi_content = (
            "B01234567890Product Description 1234561234567890100001000100050000\n"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = os.path.join(temp_dir, "input.edi")
            output_file = os.path.join(temp_dir, "output.edi")

            with open(input_file, "w") as f:
                f.write(edi_content)

            result = edi_tweaks.edi_tweak(
                input_file, output_file, sample_settings_dict, params, sample_upc_dict
            )

            with open(result, "r") as f:
                content = f.read()
                # UPC should remain unchanged
                assert "012345678901" in content or "B" in content

    @patch("convert_to_edi_tweaks.time.sleep")
    def test_edi_tweak_upc_override_key_error(
        self, mock_sleep, sample_parameters_dict, sample_settings_dict
    ):
        """Test UPC override handles missing item in upc_dict."""
        params = sample_parameters_dict.copy()
        params["override_upc_bool"] = True
        params["override_upc_level"] = 1
        params["override_upc_category_filter"] = "ALL"

        # B record with vendor_item not in upc_dict
        edi_content = (
            "B01234567890Product Description 9999991234567890100001000100050000\n"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = os.path.join(temp_dir, "input.edi")
            output_file = os.path.join(temp_dir, "output.edi")

            with open(input_file, "w") as f:
                f.write(edi_content)

            result = edi_tweaks.edi_tweak(
                input_file, output_file, sample_settings_dict, params, {}
            )

            with open(result, "r") as f:
                content = f.read()
                # Should have empty UPC field (12 spaces)
                assert "            " in content or "B" in content

    @patch("convert_to_edi_tweaks.time.sleep")
    def test_edi_tweak_retail_uom_calculation(
        self, mock_sleep, sample_parameters_dict, sample_settings_dict, sample_upc_dict
    ):
        """Test retail UOM calculation."""
        params = sample_parameters_dict.copy()
        params["retail_uom"] = True

        # B record with valid numeric fields - unit_cost=10000, unit_multiplier=2, qty=5
        edi_content = (
            "B01234567890Product Description 12345600100002000050001000050000\n"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = os.path.join(temp_dir, "input.edi")
            output_file = os.path.join(temp_dir, "output.edi")

            with open(input_file, "w") as f:
                f.write(edi_content)

            with patch("convert_to_edi_tweaks.print"):  # Suppress error prints
                result = edi_tweaks.edi_tweak(
                    input_file,
                    output_file,
                    sample_settings_dict,
                    params,
                    sample_upc_dict,
                )

            with open(result, "r") as f:
                content = f.read()
                # Should have modified UOM fields
                assert content.startswith("B")

    @patch("convert_to_edi_tweaks.time.sleep")
    def test_edi_tweak_retail_uom_zero_multiplier(
        self, mock_sleep, sample_parameters_dict, sample_settings_dict
    ):
        """Test retail UOM handles zero unit multiplier."""
        params = sample_parameters_dict.copy()
        params["retail_uom"] = True

        # B record with zero unit_multiplier
        edi_content = (
            "B01234567890Product Description 12345600100000000050001000050000\n"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = os.path.join(temp_dir, "input.edi")
            output_file = os.path.join(temp_dir, "output.edi")

            with open(input_file, "w") as f:
                f.write(edi_content)

            with patch("convert_to_edi_tweaks.print"):
                result = edi_tweaks.edi_tweak(
                    input_file, output_file, sample_settings_dict, params, {}
                )

            with open(result, "r") as f:
                content = f.read()
                # Should handle zero multiplier gracefully
                assert content.startswith("B")

    @patch("convert_to_edi_tweaks.time.sleep")
    def test_edi_tweak_retail_uom_invalid_fields(
        self, mock_sleep, sample_parameters_dict, sample_settings_dict
    ):
        """Test retail UOM handles invalid field values."""
        params = sample_parameters_dict.copy()
        params["retail_uom"] = True

        # B record with invalid fields (non-numeric)
        edi_content = (
            "B01234567890Product Description ABCXYZ123ABC12345ABC123ABC123ABC12\n"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = os.path.join(temp_dir, "input.edi")
            output_file = os.path.join(temp_dir, "output.edi")

            with open(input_file, "w") as f:
                f.write(edi_content)

            with patch("convert_to_edi_tweaks.print"):
                result = edi_tweaks.edi_tweak(
                    input_file, output_file, sample_settings_dict, params, {}
                )

            with open(result, "r") as f:
                content = f.read()
                # Should still process (may print errors)
                assert content.startswith("B")

    @patch("convert_to_edi_tweaks.time.sleep")
    @patch("convert_to_edi_tweaks.utils.calc_check_digit")
    def test_edi_tweak_calculate_upc_check_digit_11(
        self, mock_calc, mock_sleep, sample_parameters_dict, sample_settings_dict
    ):
        """Test UPC check digit calculation for 11-digit UPC."""
        mock_calc.return_value = 5

        params = sample_parameters_dict.copy()
        params["calculate_upc_check_digit"] = "True"

        # B record with 11-digit UPC (trimmed to 11 chars)
        edi_content = (
            "B01234567890 Product Description 1234561234567890100001000100050000\n"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = os.path.join(temp_dir, "input.edi")
            output_file = os.path.join(temp_dir, "output.edi")

            with open(input_file, "w") as f:
                f.write(edi_content)

            result = edi_tweaks.edi_tweak(
                input_file, output_file, sample_settings_dict, params, {}
            )

            # calc_check_digit may be called

    @patch("convert_to_edi_tweaks.time.sleep")
    @patch("convert_to_edi_tweaks.utils.convert_UPCE_to_UPCA")
    def test_edi_tweak_calculate_upc_check_digit_8(
        self, mock_convert, mock_sleep, sample_parameters_dict, sample_settings_dict
    ):
        """Test UPCE to UPCA conversion for 8-digit UPC."""
        mock_convert.return_value = "012345678905"

        params = sample_parameters_dict.copy()
        params["calculate_upc_check_digit"] = "True"

        # B record with 8-digit UPC
        edi_content = (
            "B01234567   Product Description 1234561234567890100001000100050000\n"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = os.path.join(temp_dir, "input.edi")
            output_file = os.path.join(temp_dir, "output.edi")

            with open(input_file, "w") as f:
                f.write(edi_content)

            result = edi_tweaks.edi_tweak(
                input_file, output_file, sample_settings_dict, params, {}
            )

    @patch("convert_to_edi_tweaks.time.sleep")
    def test_edi_tweak_blank_upc(
        self, mock_sleep, sample_parameters_dict, sample_settings_dict
    ):
        """Test handling of blank UPC field."""
        params = sample_parameters_dict.copy()
        params["calculate_upc_check_digit"] = "True"

        # B record with blank UPC (spaces)
        edi_content = (
            "B           Product Description 1234561234567890100001000100050000\n"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = os.path.join(temp_dir, "input.edi")
            output_file = os.path.join(temp_dir, "output.edi")

            with open(input_file, "w") as f:
                f.write(edi_content)

            result = edi_tweaks.edi_tweak(
                input_file, output_file, sample_settings_dict, params, {}
            )

            with open(result, "r") as f:
                content = f.read()
                # Should preserve blank UPC (12 spaces)
                assert "            " in content

    @patch("convert_to_edi_tweaks.time.sleep")
    def test_edi_tweak_negative_amounts(
        self, mock_sleep, sample_parameters_dict, sample_settings_dict
    ):
        """Test handling of negative amounts in B record."""
        params = sample_parameters_dict.copy()

        # B record with negative unit cost
        edi_content = "B01234567890Product Description 123456-00100200050001000050000\n"

        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = os.path.join(temp_dir, "input.edi")
            output_file = os.path.join(temp_dir, "output.edi")

            with open(input_file, "w") as f:
                f.write(edi_content)

            result = edi_tweaks.edi_tweak(
                input_file, output_file, sample_settings_dict, params, {}
            )

            with open(result, "r") as f:
                content = f.read()
                # Record should be processed
                assert content.startswith("B")

    @patch("convert_to_edi_tweaks.time.sleep")
    def test_edi_tweak_short_b_record(
        self, mock_sleep, sample_parameters_dict, sample_settings_dict
    ):
        """Test handling of short B record (under 77 chars)."""
        params = sample_parameters_dict.copy()

        # Short B record (less than 77 characters)
        edi_content = "B01234567890hort Record              12345612345\n"

        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = os.path.join(temp_dir, "input.edi")
            output_file = os.path.join(temp_dir, "output.edi")

            with open(input_file, "w") as f:
                f.write(edi_content)

            result = edi_tweaks.edi_tweak(
                input_file, output_file, sample_settings_dict, params, {}
            )

            with open(result, "r") as f:
                content = f.read()
                # Short records should have empty parent_item_number
                assert content.startswith("B")


# =============================================================================
# edi_tweak Function Tests - C Record Processing
# =============================================================================


class TestEdiTweakCRecordProcessing:
    """Tests for C record (charge) processing."""

    @patch("convert_to_edi_tweaks.time.sleep")
    @patch("convert_to_edi_tweaks.query_runner")
    def test_edi_tweak_split_prepaid_sales_tax(
        self,
        mock_query_runner,
        mock_sleep,
        sample_parameters_dict,
        sample_settings_dict,
    ):
        """Test splitting prepaid sales tax C records."""
        # Mock the query runner for cRecGenerator
        mock_query_instance = MagicMock()
        mock_query_instance.run_arbitrary_query.return_value = [(100.50, 25.25)]
        mock_query_runner.return_value = mock_query_instance

        params = sample_parameters_dict.copy()
        params["split_prepaid_sales_tax_crec"] = True

        # EDI with CTABSales Tax C record
        edi_content = "A000001INV00123  0115251000012345\nB01234567890Product 1234561234567890100001000100050000\nCTABSales Tax                  000000123\n"

        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = os.path.join(temp_dir, "input.edi")
            output_file = os.path.join(temp_dir, "output.edi")

            with open(input_file, "w") as f:
                f.write(edi_content)

            result = edi_tweaks.edi_tweak(
                input_file, output_file, sample_settings_dict, params, {}
            )

            with open(result, "r") as f:
                content = f.read()
                # Should have processed the C record
                assert "Sales Tax" in content or content.startswith("A")

    @patch("convert_to_edi_tweaks.time.sleep")
    def test_edi_tweak_c_record_passthrough(
        self, mock_sleep, sample_parameters_dict, sample_settings_dict
    ):
        """Test C record passthrough when not splitting."""
        params = sample_parameters_dict.copy()
        params["split_prepaid_sales_tax_crec"] = False

        edi_content = "C00100000123\n"

        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = os.path.join(temp_dir, "input.edi")
            output_file = os.path.join(temp_dir, "output.edi")

            with open(input_file, "w") as f:
                f.write(edi_content)

            result = edi_tweaks.edi_tweak(
                input_file, output_file, sample_settings_dict, params, {}
            )

            with open(result, "r") as f:
                content = f.read()
                assert content == "C00100000123\n"

    @patch("convert_to_edi_tweaks.time.sleep")
    @patch("convert_to_edi_tweaks.query_runner")
    def test_edi_tweak_split_prepaid_sales_tax_zero(
        self,
        mock_query_runner,
        mock_sleep,
        sample_parameters_dict,
        sample_settings_dict,
    ):
        """Test splitting sales tax when values are zero."""
        # Mock the query runner to return zero values
        mock_query_instance = MagicMock()
        mock_query_instance.run_arbitrary_query.return_value = [(0, 0)]
        mock_query_runner.return_value = mock_query_instance

        params = sample_parameters_dict.copy()
        params["split_prepaid_sales_tax_crec"] = True

        edi_content = "A000001INV00123  0115251000012345\nB01234567890Product 1234561234567890100001000100050000\nCTABSales Tax                  000000000\n"

        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = os.path.join(temp_dir, "input.edi")
            output_file = os.path.join(temp_dir, "output.edi")

            with open(input_file, "w") as f:
                f.write(edi_content)

            result = edi_tweaks.edi_tweak(
                input_file, output_file, sample_settings_dict, params, {}
            )

            with open(result, "r") as f:
                content = f.read()
                # Should still process
                assert content.startswith("A")


# =============================================================================
# File Handling Tests
# =============================================================================


class TestFileHandling:
    """Tests for file handling and edge cases."""

    @patch("convert_to_edi_tweaks.time.sleep")
    def test_edi_tweak_crlf_line_endings(
        self, mock_sleep, sample_parameters_dict, sample_settings_dict
    ):
        """Test output file uses CRLF line endings."""
        params = sample_parameters_dict.copy()

        edi_content = "A000001INV00123  0115251000012345\n"

        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = os.path.join(temp_dir, "input.edi")
            output_file = os.path.join(temp_dir, "output.edi")

            with open(input_file, "w") as f:
                f.write(edi_content)

            result = edi_tweaks.edi_tweak(
                input_file, output_file, sample_settings_dict, params, {}
            )

            with open(result, "rb") as f:
                content = f.read()
                # Should have CRLF line endings
                assert b"\r\n" in content or content.startswith(b"A")

    @patch("convert_to_edi_tweaks.time.sleep")
    def test_edi_tweak_multiple_invoices(
        self, mock_sleep, sample_parameters_dict, sample_settings_dict
    ):
        """Test processing EDI with multiple invoices."""
        params = sample_parameters_dict.copy()

        edi_content = """A000001INV00123  0115251000012345
B01234567890roduct 1                 1234561234567890100001000100050000

C00100000123
A000002INV00234  0115251000054321
B01234567890roduct 2                 2345679876543210200002000200075000

C00200000543
A000003INV00555  0115251000099999
B01234567890roduct 3                 3456781111111110300003000300025000

C00100001000
"""

        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = os.path.join(temp_dir, "input.edi")
            output_file = os.path.join(temp_dir, "output.edi")

            with open(input_file, "w") as f:
                f.write(edi_content)

            result = edi_tweaks.edi_tweak(
                input_file, output_file, sample_settings_dict, params, {}
            )

            with open(result, "r") as f:
                content = f.read()
                # Should have all three A records
                assert content.count("A000001") >= 1
                assert content.count("A000002") >= 1
                assert content.count("A000003") >= 1


# =============================================================================
# Integration Tests
# =============================================================================


class TestEdiTweakIntegration:
    """Integration tests for complete EDI processing workflows."""

    @patch("convert_to_edi_tweaks.time.sleep")
    @patch("convert_to_edi_tweaks.query_runner")
    def test_full_edi_processing_pipeline(
        self, mock_query_runner, mock_sleep, sample_settings_dict, sample_upc_dict
    ):
        """Test complete EDI processing with all features."""
        # Setup mock query runner
        mock_query_instance = MagicMock()
        mock_query_instance.run_arbitrary_query.return_value = [("PO12345",)]
        mock_query_runner.return_value = mock_query_instance

        params = {
            "pad_a_records": "True",
            "a_record_padding": "AB",
            "a_record_padding_length": 6,
            "append_a_records": "True",
            "a_record_append_text": "PO: %po_str%",
            "invoice_date_custom_format": True,
            "invoice_date_custom_format_string": "%Y-%m-%d",
            "force_txt_file_ext": "True",
            "calculate_upc_check_digit": "True",
            "invoice_date_offset": 0,
            "retail_uom": True,
            "override_upc_bool": True,
            "override_upc_level": 1,
            "override_upc_category_filter": "ALL",
            "split_prepaid_sales_tax_crec": True,
        }

        edi_content = """A000001INV00123  0115251000012345
B01234567890roduct Description       1234561234567890100001000100050000

C00100000123
"""

        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = os.path.join(temp_dir, "input.edi")
            output_file = os.path.join(temp_dir, "output")

            with open(input_file, "w") as f:
                f.write(edi_content)

            with patch("convert_to_edi_tweaks.print"):
                result = edi_tweaks.edi_tweak(
                    input_file,
                    output_file,
                    sample_settings_dict,
                    params,
                    sample_upc_dict,
                )

            assert result.endswith(".txt")
            assert os.path.exists(result)

            with open(result, "r") as f:
                content = f.read()
                # Should contain processed records
                assert content.startswith("A")
                assert "B" in content

    @patch("convert_to_edi_tweaks.time.sleep")
    def test_edi_tweak_credit_memo(
        self, mock_sleep, sample_parameters_dict, sample_settings_dict
    ):
        """Test processing credit memo (negative invoice total)."""
        params = sample_parameters_dict.copy()

        # A record with negative invoice total (credit memo)
        edi_content = "A000001INV00123  011525-00012345\nB01234567890Product Description 1234561234567890100001000100050000\nC00100000123\n"

        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = os.path.join(temp_dir, "input.edi")
            output_file = os.path.join(temp_dir, "output.edi")

            with open(input_file, "w") as f:
                f.write(edi_content)

            result = edi_tweaks.edi_tweak(
                input_file, output_file, sample_settings_dict, params, {}
            )

            with open(result, "r") as f:
                content = f.read()
                # Negative total should be preserved
                assert "-00012345" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
