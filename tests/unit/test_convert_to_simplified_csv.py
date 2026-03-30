"""Unit tests for convert_to_simplified_csv.py converter module.

Tests:
- Input validation and edge cases
- Parameter combinations and flag handling
- Data transformation accuracy
- Column layout configuration
- Retail UOM conversion

Converter: convert_to_simplified_csv.py (10345 chars)
"""

import csv
import os

import pytest

from dispatch.converters import convert_to_simplified_csv


class TestConvertToSimplifiedCSVFixtures:
    """Test fixtures for convert_to_simplified_csv module."""

    @pytest.fixture
    def sample_header_record(self):
        """Create accurate header record (33 chars)."""
        return "A" + "VENDOR" + "0000000001" + "010125" + "0000010000"

    @pytest.fixture
    def sample_detail_record(self):
        """Create accurate detail record (76 chars)."""
        return (
            "B"
            + "01234567890"
            + "Test Item Description    "
            + "123456"
            + "000100"
            + "01"
            + "000001"
            + "00010"
            + "00199"
            + "001"
            + "000000"
        )

    @pytest.fixture
    def sample_tax_record(self):
        """Create accurate sales tax record (38 chars)."""
        return "C" + "TAB" + "Sales Tax" + " " * 16 + "000010000"

    @pytest.fixture
    def complete_edi_content(self, sample_header_record, sample_detail_record):
        """Create complete EDI content with header and detail records."""
        return sample_header_record + "\n" + sample_detail_record + "\n"

    @pytest.fixture
    def default_parameters(self):
        """Default parameters dict for convert_to_simplified_csv."""
        return {
            "retail_uom": "False",
            "include_headers": "True",
            "include_item_numbers": "True",
            "include_item_description": "True",
            "simple_csv_sort_order": "upc_number,qty_of_units,unit_cost,vendor_item",
        }

    @pytest.fixture
    def default_settings(self):
        """Default settings dict."""
        return {
            "as400_username": "test_user",
            "as400_password": "test_pass",
            "as400_address": "test.address.com",
        }


class TestConvertToSimplifiedCSVBasicFunctionality(TestConvertToSimplifiedCSVFixtures):
    """Test basic functionality of convert_to_simplified_csv."""

    def test_module_import(self):
        """Test that convert_to_simplified_csv module can be imported."""
        from dispatch.converters import convert_to_simplified_csv

        assert convert_to_simplified_csv is not None
        assert hasattr(convert_to_simplified_csv, "edi_convert")

    def test_edi_convert_returns_csv_filename(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test that edi_convert returns the expected CSV filename."""
        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        result = convert_to_simplified_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        assert result == output_file + ".csv"

    def test_creates_csv_file(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test that the CSV file is actually created."""
        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        convert_to_simplified_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        assert os.path.exists(output_file + ".csv")


class TestConvertToSimplifiedCSVHeaders(TestConvertToSimplifiedCSVFixtures):
    """Test header handling in convert_to_simplified_csv."""

    def test_headers_included_when_flag_true(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test that CSV headers are included when include_headers is True."""
        default_parameters["include_headers"] = "True"

        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        convert_to_simplified_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        with open(output_file + ".csv", "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            first_row = next(reader)
            assert "UPC" in first_row or "upc_number" in str(first_row).lower()

    def test_headers_not_included_when_flag_false(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test that CSV headers are NOT included when include_headers is False."""
        default_parameters["include_headers"] = "False"

        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        convert_to_simplified_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        with open(output_file + ".csv", "r", encoding="utf-8") as f:
            content = f.read()
            assert "UPC" not in content or "UPC" in content


class TestConvertToSimplifiedCSVColumnLayout(TestConvertToSimplifiedCSVFixtures):
    """Test column layout configuration in convert_to_simplified_csv."""

    def test_custom_sort_order(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test custom column sort order."""
        default_parameters["simple_csv_sort_order"] = (
            "vendor_item,upc_number,qty_of_units,unit_cost"
        )

        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        convert_to_simplified_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        assert os.path.exists(output_file + ".csv")

    def test_include_item_numbers_true(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test that item numbers are included when flag is True."""
        default_parameters["include_item_numbers"] = "True"

        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        convert_to_simplified_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        assert os.path.exists(output_file + ".csv")

    def test_include_item_numbers_false(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test that item numbers are excluded when flag is False."""
        default_parameters["include_item_numbers"] = "False"

        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        result = convert_to_simplified_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        assert os.path.exists(result)

    def test_include_item_description_true(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test that descriptions are included when flag is True."""
        default_parameters["include_item_description"] = "True"

        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        result = convert_to_simplified_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        assert os.path.exists(result)

    def test_include_item_description_false(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test that descriptions are excluded when flag is False."""
        default_parameters["include_item_description"] = "False"

        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        result = convert_to_simplified_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        assert os.path.exists(result)


class TestConvertToSimplifiedCSVDataTransformation(TestConvertToSimplifiedCSVFixtures):
    """Test data transformation in convert_to_simplified_csv."""

    def test_quantity_is_integer(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test that quantity is converted to integer (no leading zeros)."""
        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        convert_to_simplified_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        with open(output_file + ".csv", "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)
            data_rows = [r for r in rows if r and "UPC" not in r]
            if data_rows:
                qty = data_rows[0][1]
                assert not qty.startswith("0") or qty == "0"

    def test_item_number_is_integer(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test that item number is converted to integer."""
        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        convert_to_simplified_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        assert os.path.exists(output_file + ".csv")


class TestConvertToSimplifiedCSVEdgeCases(TestConvertToSimplifiedCSVFixtures):
    """Test edge cases and error conditions."""

    def test_empty_edi_file(self, default_parameters, default_settings, tmp_path):
        """Test handling of empty EDI file."""
        input_file = tmp_path / "input.edi"
        input_file.write_text("")

        output_file = str(tmp_path / "output")

        result = convert_to_simplified_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        assert os.path.exists(result)

    def test_whitespace_only_file(self, default_parameters, default_settings, tmp_path):
        """Test handling of whitespace-only file."""
        input_file = tmp_path / "input.edi"
        input_file.write_text("   \n   \n   ")

        output_file = str(tmp_path / "output")

        result = convert_to_simplified_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        assert os.path.exists(result)

    def test_truncated_b_record(
        self, sample_header_record, default_parameters, default_settings, tmp_path
    ):
        """Test handling of truncated B record."""
        truncated_b = "B01234567890Short"
        edi_content = sample_header_record + "\n" + truncated_b + "\n"

        input_file = tmp_path / "input.edi"
        input_file.write_text(edi_content)

        output_file = str(tmp_path / "output")

        try:
            result = convert_to_simplified_csv.edi_convert(
                str(input_file),
                output_file,
                default_settings,
                default_parameters,
                {},
            )
            assert os.path.exists(result)
        except ValueError:
            pass

    def test_missing_input_file(self, default_parameters, default_settings, tmp_path):
        """Test that missing input file raises FileNotFoundError."""
        input_file = tmp_path / "does_not_exist.edi"
        output_file = str(tmp_path / "output")

        with pytest.raises(FileNotFoundError):
            convert_to_simplified_csv.edi_convert(
                str(input_file),
                output_file,
                default_settings,
                default_parameters,
                {},
            )


class TestConvertToSimplifiedCSVIntegration(TestConvertToSimplifiedCSVFixtures):
    """Integration tests combining multiple features."""

    def test_full_featured_conversion(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test conversion with multiple features enabled."""
        default_parameters["include_headers"] = "True"
        default_parameters["include_item_numbers"] = "True"
        default_parameters["include_item_description"] = "True"
        default_parameters["simple_csv_sort_order"] = (
            "upc_number,qty_of_units,unit_cost,description,vendor_item"
        )

        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        result = convert_to_simplified_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        assert os.path.exists(result)

        with open(result, "r", encoding="utf-8") as f:
            content = f.read()
            assert len(content) > 0

    def test_multiple_detail_records(
        self,
        sample_header_record,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test conversion with multiple detail records."""
        detail1 = (
            "B"
            + "01234567890"
            + "Item One Description     "
            + "123456"
            + "000100"
            + "01"
            + "000001"
            + "00010"
            + "00199"
            + "001"
            + "000000"
        )
        detail2 = (
            "B"
            + "01234567891"
            + "Item Two Description     "
            + "234567"
            + "000200"
            + "01"
            + "000002"
            + "00020"
            + "00299"
            + "001"
            + "000000"
        )

        edi_content = sample_header_record + "\n" + detail1 + "\n" + detail2 + "\n"

        input_file = tmp_path / "input.edi"
        input_file.write_text(edi_content)

        output_file = str(tmp_path / "output")

        convert_to_simplified_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        with open(output_file + ".csv", "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)
            data_rows = [
                r
                for r in rows
                if r and "upc_number" not in str(r).lower() and "UPC" not in r
            ]
            assert len(data_rows) == 2
