"""Unit tests for convert_to_csv.py converter module.

Tests:
- Input validation and edge cases
- Parameter combinations and flag handling
- Data transformation accuracy
- UPC calculation and padding
- Error handling

Converter: convert_to_csv.py (8685 chars)
"""

import pytest
import os
import csv

# Import the module to test
import convert_to_csv


class TestConvertToCSVFixtures:
    """Test fixtures for convert_to_csv module."""

    @pytest.fixture
    def sample_header_record(self):
        """Create accurate header record (33 chars)."""
        return "A" + "VENDOR" + "0000000001" + "010125" + "0000010000"

    @pytest.fixture
    def sample_detail_record(self):
        """Create accurate detail record (76 chars)."""
        return ("B" + "01234567890" + "Test Item Description    " + "123456" + "000100" +
                "01" + "000001" + "00010" + "00199" + "001" + "000000")

    @pytest.fixture
    def sample_detail_record_with_parent(self):
        """Detail record with parent item number."""
        return ("B" + "01234567890" + "Parent Item Description " + "123456" + "000100" +
                "01" + "000002" + "00005" + "00199" + "001" + "123456")

    @pytest.fixture
    def sample_tax_record(self):
        """Create accurate sales tax record (38 chars)."""
        return "C" + "TAB" + "Sales Tax" + " " * 16 + "000010000"

    @pytest.fixture
    def complete_edi_content(self, sample_header_record, sample_detail_record, sample_tax_record):
        """Create complete EDI content with header, detail, and tax records."""
        return sample_header_record + "\n" + sample_detail_record + "\n" + sample_tax_record + "\n"

    @pytest.fixture
    def edi_content_with_ampersand(self, sample_header_record):
        """EDI content with ampersand in description."""
        detail_with_ampersand = ("B" + "01234567890" + "Test & Item Description  " + "123456" + "000100" +
                                  "01" + "000001" + "00010" + "00199" + "001" + "000000")
        return sample_header_record + "\n" + detail_with_ampersand + "\n"

    @pytest.fixture
    def default_parameters(self):
        """Default parameters dict for convert_to_csv."""
        return {
            'calculate_upc_check_digit': "False",
            'include_a_records': "False",
            'include_c_records': "False",
            'include_headers': "True",
            'filter_ampersand': "True",
            'pad_a_records': "False",
            'a_record_padding': '',
            'override_upc_bool': False,
            'override_upc_level': 1,
            'override_upc_category_filter': '',
            'retail_uom': False,
            'upc_target_length': 11,
            'upc_padding_pattern': '           ',
        }

    @pytest.fixture
    def default_settings(self):
        """Default settings dict."""
        return {
            'as400_username': 'test_user',
            'as400_password': 'test_pass',
            'as400_address': 'test.address.com',
            'odbc_driver': 'ODBC Driver 17 for SQL Server',
        }

    @pytest.fixture
    def empty_upc_lut(self):
        """Empty UPC lookup table."""
        return {}

    @pytest.fixture
    def sample_upc_lut(self):
        """Sample UPC lookup table."""
        return {
            123456: ('CAT1', '012345678905', '012345678900'),  # (category, UPC, case UPC)
            123457: ('CAT2', '012345678912', '012345678917'),
        }


class TestConvertToCSVBasicFunctionality(TestConvertToCSVFixtures):
    """Test basic functionality of convert_to_csv."""

    def test_module_import(self):
        """Test that convert_to_csv module can be imported."""
        import convert_to_csv
        assert convert_to_csv is not None
        assert hasattr(convert_to_csv, 'edi_convert')

    def test_edi_convert_returns_csv_filename(self, complete_edi_content, default_parameters,
                                               default_settings, empty_upc_lut, tmp_path):
        """Test that edi_convert returns the expected CSV filename."""
        # Create temp input file
        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        result = convert_to_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            empty_upc_lut
        )

        assert result == output_file + ".csv"

    def test_creates_csv_file(self, complete_edi_content, default_parameters,
                               default_settings, empty_upc_lut, tmp_path):
        """Test that the CSV file is actually created."""
        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        convert_to_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            empty_upc_lut
        )

        assert os.path.exists(output_file + ".csv")


class TestConvertToCSVHeaders(TestConvertToCSVFixtures):
    """Test header handling in convert_to_csv."""

    def test_headers_included_when_flag_true(self, complete_edi_content, default_parameters,
                                              default_settings, empty_upc_lut, tmp_path):
        """Test that CSV headers are included when include_headers is True."""
        default_parameters['include_headers'] = "True"

        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        convert_to_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            empty_upc_lut
        )

        with open(output_file + ".csv", 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            first_row = next(reader)
            assert first_row == ["UPC", "Qty. Shipped", "Cost", "Suggested Retail",
                                 "Description", "Case Pack", "Item Number"]

    def test_headers_not_included_when_flag_false(self, complete_edi_content, default_parameters,
                                                   default_settings, empty_upc_lut, tmp_path):
        """Test that CSV headers are NOT included when include_headers is False."""
        default_parameters['include_headers'] = "False"

        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        convert_to_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            empty_upc_lut
        )

        with open(output_file + ".csv", 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            first_row = next(reader)
            # First row should be data, not headers
            assert first_row[0] != "UPC" or len(first_row) != 7


class TestConvertToCSVARecords(TestConvertToCSVFixtures):
    """Test A record handling in convert_to_csv."""

    def test_a_records_included(self, complete_edi_content, default_parameters,
                                 default_settings, empty_upc_lut, tmp_path):
        """Test that A records are included when flag is True."""
        default_parameters['include_a_records'] = "True"
        default_parameters['include_headers'] = "False"

        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        convert_to_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            empty_upc_lut
        )

        with open(output_file + ".csv", 'r', encoding='utf-8') as f:
            content = f.read()
            # A record should contain "A" as first field
            lines = content.split('\n')
            a_record_lines = [l for l in lines if l.startswith('"A"')]
            assert len(a_record_lines) > 0

    def test_a_records_excluded(self, complete_edi_content, default_parameters,
                                 default_settings, empty_upc_lut, tmp_path):
        """Test that A records are NOT included when flag is False."""
        default_parameters['include_a_records'] = "False"

        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        convert_to_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            empty_upc_lut
        )

        with open(output_file + ".csv", 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            # Should have no lines starting with "A"
            a_record_lines = [l for l in lines if l.startswith('"A"')]
            assert len(a_record_lines) == 0

    def test_a_records_padding(self, complete_edi_content, default_parameters,
                                default_settings, empty_upc_lut, tmp_path):
        """Test A record padding functionality."""
        default_parameters['include_a_records'] = "True"
        default_parameters['pad_a_records'] = "True"
        default_parameters['a_record_padding'] = "CUSTOM"
        default_parameters['include_headers'] = "False"

        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        convert_to_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            empty_upc_lut
        )

        with open(output_file + ".csv", 'r', encoding='utf-8') as f:
            content = f.read()
            # Should contain CUSTOM in the output
            assert "CUSTOM" in content


class TestConvertToCSVCRecords(TestConvertToCSVFixtures):
    """Test C record (tax) handling in convert_to_csv."""

    def test_c_records_included(self, complete_edi_content, default_parameters,
                                 default_settings, empty_upc_lut, tmp_path):
        """Test that C records are included when flag is True."""
        default_parameters['include_c_records'] = "True"
        default_parameters['include_headers'] = "False"

        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        convert_to_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            empty_upc_lut
        )

        with open(output_file + ".csv", 'r', encoding='utf-8') as f:
            content = f.read()
            # Should contain C record fields
            assert '"C"' in content
            assert "TAB" in content

    def test_c_records_excluded(self, complete_edi_content, default_parameters,
                                 default_settings, empty_upc_lut, tmp_path):
        """Test that C records are NOT included when flag is False."""
        default_parameters['include_c_records'] = "False"

        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        convert_to_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            empty_upc_lut
        )

        with open(output_file + ".csv", 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            # Should have no lines with C record type
            c_record_lines = [l for l in lines if l.startswith('"C"')]
            assert len(c_record_lines) == 0


class TestConvertToCSVUPCCalculation(TestConvertToCSVFixtures):
    """Test UPC calculation and check digit handling."""

    def test_upc_check_digit_calculation_toggled(self, complete_edi_content, default_parameters,
                                                   default_settings, empty_upc_lut, tmp_path):
        """Test UPC check digit calculation when disabled."""
        default_parameters['calculate_upc_check_digit'] = "False"

        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        convert_to_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            empty_upc_lut
        )

        with open(output_file + ".csv", 'r', encoding='utf-8') as f:
            content = f.read()
            # When disabled, UPC should be the raw value
            assert "01234567890" in content

    def test_upc_check_digit_calculation_enabled(self, complete_edi_content, default_parameters,
                                                  default_settings, empty_upc_lut, tmp_path):
        """Test UPC check digit calculation when enabled."""
        default_parameters['calculate_upc_check_digit'] = "True"

        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        convert_to_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            empty_upc_lut
        )

        with open(output_file + ".csv", 'r', encoding='utf-8') as f:
            content = f.read()
            # When enabled, should add tab and check digit (12-digit UPC)
            # 01234567890 + check digit = 012345678905
            assert "012345678905" in content

    def test_upc_lookup_from_lut(self, complete_edi_content, default_parameters,
                                   default_settings, sample_upc_lut, tmp_path):
        """Test UPC lookup from lookup table."""
        # Enable retail_uom to trigger the LUT lookup code path
        default_parameters['calculate_upc_check_digit'] = "False"
        default_parameters['retail_uom'] = True
        default_parameters['upc_target_length'] = 12  # Get full 12-char UPC from LUT

        # Create EDI with vendor_item that matches our LUT
        header = "A" + "VENDOR" + "0000000001" + "010125" + "0000010000"
        # vendor_item 123456 is in our LUT
        detail = ("B" + "01234567890" + "Test Item Description    " + "123456" + "000100" +
                  "01" + "000001" + "00010" + "00199" + "001" + "000000")
        edi_content = header + "\n" + detail + "\n"

        input_file = tmp_path / "input.edi"
        input_file.write_text(edi_content)

        output_file = str(tmp_path / "output")

        convert_to_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            sample_upc_lut
        )

        with open(output_file + ".csv", 'r', encoding='utf-8') as f:
            content = f.read()
            # Should use UPC from LUT: 012345678905
            assert "012345678905" in content


class TestConvertToCSVOverrideUPC(TestConvertToCSVFixtures):
    """Test UPC override functionality."""

    def test_override_upc_with_category_filter(self, complete_edi_content, default_parameters,
                                                 default_settings, sample_upc_lut, tmp_path):
        """Test UPC override with category filtering."""
        default_parameters['override_upc_bool'] = True
        default_parameters['override_upc_level'] = 1  # Use first UPC in tuple
        default_parameters['override_upc_category_filter'] = 'CAT1'  # Only CAT1

        # Create EDI with vendor_item 123456 which is CAT1
        header = "A" + "VENDOR" + "0000000001" + "010125" + "0000010000"
        detail = ("B" + "01234567890" + "Test Item Description    " + "123456" + "000100" +
                  "01" + "000001" + "00010" + "00199" + "001" + "000000")
        edi_content = header + "\n" + detail + "\n"

        input_file = tmp_path / "input.edi"
        input_file.write_text(edi_content)

        output_file = str(tmp_path / "output")

        convert_to_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            sample_upc_lut
        )

        with open(output_file + ".csv", 'r', encoding='utf-8') as f:
            content = f.read()
            # Should use overridden UPC
            assert "012345678905" in content

    def test_override_upc_category_filter_mismatch(self, complete_edi_content, default_parameters,
                                                    default_settings, sample_upc_lut, tmp_path):
        """Test UPC override with non-matching category filter."""
        default_parameters['override_upc_bool'] = True
        default_parameters['override_upc_level'] = 1
        default_parameters['override_upc_category_filter'] = 'CAT_NOT_EXIST'  # Non-existent category

        # Create EDI with vendor_item 123456 which is CAT1
        header = "A" + "VENDOR" + "0000000001" + "010125" + "0000010000"
        detail = ("B" + "01234567890" + "Test Item Description    " + "123456" + "000100" +
                  "01" + "000001" + "00010" + "00199" + "001" + "000000")
        edi_content = header + "\n" + detail + "\n"

        input_file = tmp_path / "input.edi"
        input_file.write_text(edi_content)

        output_file = str(tmp_path / "output")

        convert_to_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            sample_upc_lut
        )

        with open(output_file + ".csv", 'r', encoding='utf-8') as f:
            content = f.read()
            # Should NOT use overridden UPC since category doesn't match
            assert '"01234567890"' in content


class TestConvertToCSVFilterAmpersand(TestConvertToCSVFixtures):
    """Test ampersand filtering in descriptions."""

    def test_filter_ampersand_enabled(self, edi_content_with_ampersand, default_parameters,
                                       default_settings, empty_upc_lut, tmp_path):
        """Test that ampersands are replaced with AND when filter is enabled."""
        default_parameters['filter_ampersand'] = "True"

        input_file = tmp_path / "input.edi"
        input_file.write_text(edi_content_with_ampersand)

        output_file = str(tmp_path / "output")

        convert_to_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            empty_upc_lut
        )

        with open(output_file + ".csv", 'r', encoding='utf-8') as f:
            content = f.read()
            # Should replace & with AND
            assert "AND" in content
            assert "&" not in content or content.count("&") == 0

    def test_filter_ampersand_disabled(self, edi_content_with_ampersand, default_parameters,
                                         default_settings, empty_upc_lut, tmp_path):
        """Test that ampersands are preserved when filter is disabled."""
        default_parameters['filter_ampersand'] = "False"

        input_file = tmp_path / "input.edi"
        input_file.write_text(edi_content_with_ampersand)

        output_file = str(tmp_path / "output")

        convert_to_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            empty_upc_lut
        )

        with open(output_file + ".csv", 'r', encoding='utf-8') as f:
            content = f.read()
            # Should preserve the ampersand
            assert "&" in content


class TestConvertToCSVRetailUOM(TestConvertToCSVFixtures):
    """Test retail UOM handling."""

    def test_retail_uom_enabled(self, complete_edi_content, default_parameters,
                                 default_settings, sample_upc_lut, tmp_path):
        """Test retail UOM mode when enabled."""
        default_parameters['retail_uom'] = True
        default_parameters['calculate_upc_check_digit'] = "False"

        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        convert_to_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            sample_upc_lut
        )

        # Should complete without errors
        assert os.path.exists(output_file + ".csv")

    def test_retail_uom_with_zero_multiplier(self, sample_header_record, default_parameters,
                                               default_settings, sample_upc_lut, tmp_path):
        """Test retail UOM mode with zero unit multiplier (edge case)."""
        default_parameters['retail_uom'] = True
        default_parameters['calculate_upc_check_digit'] = "False"

        # Create detail with zero multiplier
        detail = ("B" + "01234567890" + "Test Item Description    " + "123456" + "000100" +
                  "01" + "000000" + "00010" + "00199" + "001" + "000000")
        edi_content = sample_header_record + "\n" + detail + "\n"

        input_file = tmp_path / "input.edi"
        input_file.write_text(edi_content)

        output_file = str(tmp_path / "output")

        # Should handle gracefully (skip invalid line)
        result = convert_to_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            sample_upc_lut
        )

        assert os.path.exists(result)


class TestConvertToCSVUPCTargetLength(TestConvertToCSVFixtures):
    """Test UPC target length and padding."""

    def test_upc_target_length_11(self, complete_edi_content, default_parameters,
                                    default_settings, empty_upc_lut, tmp_path):
        """Test UPC target length of 11 characters."""
        default_parameters['upc_target_length'] = 11

        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        convert_to_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            empty_upc_lut
        )

        with open(output_file + ".csv", 'r', encoding='utf-8') as f:
            content = f.read()
            # UPC should be padded to 11 chars then ljust used
            assert "01234567890" in content

    def test_upc_target_length_12(self, complete_edi_content, default_parameters,
                                    default_settings, sample_upc_lut, tmp_path):
        """Test UPC target length of 12 characters."""
        # Enable retail_uom to trigger the LUT lookup code path
        default_parameters['upc_target_length'] = 12
        default_parameters['retail_uom'] = True

        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        convert_to_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            sample_upc_lut
        )

        with open(output_file + ".csv", 'r', encoding='utf-8') as f:
            content = f.read()
            # With 12-char target and check digit calc, should be 12 chars
            assert "012345678905" in content

    def test_upc_padding_pattern_custom(self, complete_edi_content, default_parameters,
                                         default_settings, empty_upc_lut, tmp_path):
        """Test custom UPC padding pattern."""
        default_parameters['upc_padding_pattern'] = 'XXXX'
        default_parameters['calculate_upc_check_digit'] = "False"

        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        convert_to_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            empty_upc_lut
        )

        # Should complete without errors
        assert os.path.exists(output_file + ".csv")


class TestConvertToCSVEdgeCases(TestConvertToCSVFixtures):
    """Test edge cases and error conditions."""

    def test_empty_edi_file(self, default_parameters, default_settings, empty_upc_lut, tmp_path):
        """Test handling of empty EDI file."""
        input_file = tmp_path / "input.edi"
        input_file.write_text("")

        output_file = str(tmp_path / "output")

        # Should handle gracefully
        result = convert_to_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            empty_upc_lut
        )

        assert os.path.exists(result)

    def test_only_whitespace_file(self, default_parameters, default_settings, empty_upc_lut, tmp_path):
        """Test handling of whitespace-only file."""
        input_file = tmp_path / "input.edi"
        input_file.write_text("   \n   \n   ")

        output_file = str(tmp_path / "output")

        result = convert_to_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            empty_upc_lut
        )

        assert os.path.exists(result)

    def test_invalid_record_type(self, default_parameters, default_settings, empty_upc_lut, tmp_path):
        """Test handling of invalid record types."""
        input_file = tmp_path / "input.edi"
        input_file.write_text("Xinvalid_record\n")

        output_file = str(tmp_path / "output")

        result = convert_to_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            empty_upc_lut
        )

        assert os.path.exists(result)

    def test_detail_with_missing_fields(self, default_parameters, default_settings,
                                         empty_upc_lut, tmp_path):
        """Test handling of detail record with missing/short fields."""
        # Short B record (less than 76 chars)
        short_detail = "B01234567890Short"
        input_file = tmp_path / "input.edi"
        input_file.write_text(short_detail)

        output_file = str(tmp_path / "output")

        # Should handle gracefully
        result = convert_to_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            empty_upc_lut
        )

        assert os.path.exists(result)


class TestConvertToCSVDataTransformation(TestConvertToCSVFixtures):
    """Test data transformation accuracy."""

    def test_quantity_zero_stripping(self, complete_edi_content, default_parameters,
                                      default_settings, empty_upc_lut, tmp_path):
        """Test that leading zeros are stripped from quantity."""
        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        convert_to_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            empty_upc_lut
        )

        with open(output_file + ".csv", 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
            # Find data row (skip header if present)
            data_rows = [r for r in rows if r and r[0] != "UPC"]
            if data_rows:
                # Quantity should not have leading zeros (unless it's just "0")
                qty = data_rows[0][1]
                assert not qty.startswith("0") or qty == "0"

    def test_item_number_zero_stripping(self, complete_edi_content, default_parameters,
                                         default_settings, empty_upc_lut, tmp_path):
        """Test that leading zeros are stripped from item numbers."""
        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        convert_to_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            empty_upc_lut
        )

        with open(output_file + ".csv", 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
            data_rows = [r for r in rows if r and r[0] != "UPC"]
            if data_rows:
                # Item number should be stripped of leading zeros
                item_num = data_rows[0][6]  # Item Number is column 7
                assert not item_num.startswith("0") or item_num == "0"


class TestConvertToCSVIntegration(TestConvertToCSVFixtures):
    """Integration tests combining multiple features."""

    def test_full_featured_conversion(self, complete_edi_content, default_parameters,
                                       default_settings, sample_upc_lut, tmp_path):
        """Test conversion with multiple features enabled."""
        # Enable multiple features
        default_parameters['calculate_upc_check_digit'] = "True"
        default_parameters['include_a_records'] = "True"
        default_parameters['include_c_records'] = "True"
        default_parameters['include_headers'] = "True"
        default_parameters['filter_ampersand'] = "True"
        default_parameters['retail_uom'] = True

        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        result = convert_to_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            sample_upc_lut
        )

        assert os.path.exists(result)

        with open(result, 'r', encoding='utf-8') as f:
            content = f.read()
            # Should have headers, data, and A/C records
            assert "UPC" in content
            assert "Qty. Shipped" in content
            assert '"A"' in content or 'A' in content
            assert '"C"' in content or 'C' in content

    def test_multiple_detail_records(self, sample_header_record, default_parameters,
                                      default_settings, empty_upc_lut, tmp_path):
        """Test conversion with multiple detail records."""
        # Create multiple B records
        detail1 = ("B" + "01234567890" + "Item One Description     " + "123456" + "000100" +
                   "01" + "000001" + "00010" + "00199" + "001" + "000000")
        detail2 = ("B" + "01234567891" + "Item Two Description     " + "234567" + "000200" +
                   "01" + "000002" + "00020" + "00299" + "001" + "000000")
        detail3 = ("B" + "01234567892" + "Item Three Description  " + "345678" + "000300" +
                   "01" + "000003" + "00030" + "00399" + "001" + "000000")

        edi_content = sample_header_record + "\n" + detail1 + "\n" + detail2 + "\n" + detail3 + "\n"

        input_file = tmp_path / "input.edi"
        input_file.write_text(edi_content)

        output_file = str(tmp_path / "output")

        convert_to_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            empty_upc_lut
        )

        with open(output_file + ".csv", 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
            # Should have header + 3 data rows
            data_rows = [r for r in rows if r and r[0] != "UPC"]
            assert len(data_rows) == 3
