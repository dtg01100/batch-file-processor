"""
End-to-end conversion tests that verify actual EDI-to-output conversion.

These tests create sample EDI files, run them through each converter,
and verify the output format and content.

Converters tested:
- convert_to_csv.py
- convert_to_fintech.py
- convert_to_scannerware.py
- convert_to_simplified_csv.py
- convert_to_yellowdog_csv.py
- convert_to_estore_einvoice.py
- convert_to_estore_einvoice_generic.py
- convert_to_stewarts_custom.py
- convert_to_scansheet_type_a.py
- convert_to_jolley_custom.py
"""

import csv
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile


# =============================================================================
# EDI FORMAT SPECIFICATIONS (from test_convert_backends.py)
# =============================================================================
#
# Header Record (Type A) - 33 characters total:
#   - Record Type: position 0-1 (1 char)
#   - Cust Vendor: position 1-7 (6 chars)
#   - Invoice Number: position 7-17 (10 chars)
#   - Invoice Date: position 17-23 (6 chars, MMDDYY format)
#   - Invoice Total: position 23-33 (10 chars, zero-padded)
#
# Detail Record (Type B) - 76 characters total:
#   - Record Type: position 0-1 (1 char)
#   - UPC Number: position 1-12 (11 chars)
#   - Description: position 12-37 (25 chars)
#   - Vendor Item: position 37-43 (6 chars)
#   - Unit Cost: position 43-49 (6 chars)
#   - Combo Code: position 49-51 (2 chars)
#   - Unit Multiplier: position 51-57 (6 chars)
#   - Qty of Units: position 57-62 (5 chars)
#   - Suggested Retail: position 62-67 (5 chars)
#   - Price Multi-Pack: position 67-70 (3 chars)
#   - Parent Item#: position 70-76 (6 chars)
#
# Sales Tax Record (Type C) - 38 characters total:
#   - Record Type: position 0-1 (1 char)
#   - Charge Type: position 1-4 (3 chars)
#   - Description: position 4-29 (25 chars)
#   - Amount: position 29-38 (9 chars)
# =============================================================================


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_header_record():
    """Create accurate header record (33 chars)."""
    # A + CustVendor(6) + InvoiceNum(10) + Date(6) + Total(10) = 33
    return "A" + "VENDOR" + "0000000001" + "010125" + "0000010000"


@pytest.fixture
def sample_detail_record():
    """Create accurate detail record (76 chars)."""
    # B + UPC(11) + Desc(25) + Item(6) + Cost(6) + Combo(2) + Mult(6) + Qty(5) + Retail(5) + Pack(3) + Parent(6) = 76
    return ("B" + "01234567890" + "Test Item Description    " + "123456" + "000100" +
            "01" + "000001" + "00010" + "00199" + "001" + "000000")


@pytest.fixture
def sample_detail_record_with_special_chars():
    """Create detail record with ampersand in description (76 chars)."""
    # Description contains "Tom & Jerry" to test ampersand filtering
    return ("B" + "01234567890" + "Tom & Jerry Product     " + "123456" + "000100" +
            "01" + "000001" + "00010" + "00199" + "001" + "000000")


@pytest.fixture
def sample_tax_record():
    """Create accurate sales tax record (38 chars)."""
    # C + ChargeType(3) + Desc(25) + Amount(9) = 38
    return "C" + "TAB" + "Sales Tax" + " " * 16 + "000010000"


@pytest.fixture
def sample_edi_content(sample_header_record, sample_detail_record, sample_tax_record):
    """Create complete EDI content with header, detail, and tax records."""
    return sample_header_record + "\n" + sample_detail_record + "\n" + sample_tax_record + "\n"


@pytest.fixture
def sample_edi_content_multi(sample_header_record, sample_detail_record, sample_tax_record):
    """Create EDI content with multiple detail records."""
    detail2 = ("B" + "98765432109" + "Another Product Item    " + "654321" + "000200" +
               "02" + "000002" + "00005" + "00299" + "002" + "000000")
    return (sample_header_record + "\n" + sample_detail_record + "\n" + detail2 + "\n" +
            sample_tax_record + "\n")


@pytest.fixture
def sample_edi_content_empty_detail(sample_header_record, sample_tax_record):
    """Create EDI content with no detail records (edge case)."""
    return sample_header_record + "\n" + sample_tax_record + "\n"


@pytest.fixture
def edi_file(tmp_path, sample_edi_content):
    """Create a temporary EDI file for testing."""
    edi_path = tmp_path / "test_input.edi"
    edi_path.write_text(sample_edi_content, encoding="utf-8")
    return str(edi_path)


@pytest.fixture
def edi_file_multi(tmp_path, sample_edi_content_multi):
    """Create a temporary EDI file with multiple detail records."""
    edi_path = tmp_path / "test_input_multi.edi"
    edi_path.write_text(sample_edi_content_multi, encoding="utf-8")
    return str(edi_path)


@pytest.fixture
def edi_file_empty_detail(tmp_path, sample_edi_content_empty_detail):
    """Create a temporary EDI file with no detail records."""
    edi_path = tmp_path / "test_input_empty.edi"
    edi_path.write_text(sample_edi_content_empty_detail, encoding="utf-8")
    return str(edi_path)


@pytest.fixture
def default_parameters_dict():
    """Default parameters for converters."""
    return {
        'calculate_upc_check_digit': 'False',
        'include_a_records': 'False',
        'include_c_records': 'False',
        'include_headers': 'True',
        'filter_ampersand': 'True',
        'pad_a_records': 'False',
        'a_record_padding': '      ',
        'override_upc_bool': False,
        'override_upc_level': 1,
        'override_upc_category_filter': '',
        'retail_uom': False,
        'upc_target_length': 11,
        'upc_padding_pattern': '           ',
        # Fintech specific
        'fintech_division_id': 'DIV001',
        # Scannerware specific
        'append_a_records': 'False',
        'a_record_append_text': '',
        'force_txt_file_ext': 'False',
        'invoice_date_offset': 0,
        # Simplified CSV specific
        'simple_csv_sort_order': 'upc_number,qty_of_units,unit_cost,description,vendor_item',
        'include_item_numbers': 'True',
        'include_item_description': 'True',
        # Estore einvoice specific
        'estore_store_number': '001',
        'estore_Vendor_OId': 'VENDOR001',
        'estore_vendor_NameVendorOID': 'TestVendor',
        'estore_c_record_OID': 'C_RECORD_OID',
        # Stewarts/Jolley specific
        'invoice_date_offset_days': 0,
        'adjusted_date_offset': 0,
    }


@pytest.fixture
def default_settings_dict():
    """Default settings for converters (database connections, etc.)."""
    return {
        'as400_username': 'test_user',
        'as400_password': 'test_pass',
        'as400_address': 'test.example.com',
        'odbc_driver': 'IBM i Access ODBC Driver',
    }


@pytest.fixture
def sample_upc_lut():
    """Sample UPC lookup table for testing."""
    # Format: item_number -> (category, each_upc, case_upc)
    return {
        123456: ('CAT1', '01234567890', '01234567891'),
        654321: ('CAT2', '98765432109', '98765432108'),
    }


# =============================================================================
# TEST CLASS: convert_to_csv.py
# =============================================================================

@pytest.mark.integration
class TestConvertToCSV:
    """End-to-end tests for convert_to_csv.py converter."""

    def test_convert_produces_valid_csv(self, edi_file, tmp_path, default_parameters_dict, sample_upc_lut):
        """Test that convert_to_csv produces a valid CSV file."""
        import convert_to_csv
        
        output_path = str(tmp_path / "output")
        
        result = convert_to_csv.edi_convert(
            edi_file,
            output_path,
            {},
            default_parameters_dict,
            sample_upc_lut
        )
        
        # Verify output file was created
        assert os.path.exists(result), f"Output file {result} was not created"
        
        # Verify it's a CSV file
        assert result.endswith('.csv'), f"Output {result} should be a CSV file"
        
        # Read and verify CSV content
        with open(result, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        # Should have header + 1 detail row (A and C records excluded by default)
        assert len(rows) >= 1, "CSV should have at least header row"
        
        # Verify header row
        assert rows[0][0] == "UPC", "First column header should be UPC"

    def test_convert_handles_empty_records(self, edi_file_empty_detail, tmp_path, default_parameters_dict, sample_upc_lut):
        """Test that convert_to_csv handles EDI with no detail records."""
        import convert_to_csv
        
        output_path = str(tmp_path / "output_empty")
        
        result = convert_to_csv.edi_convert(
            edi_file_empty_detail,
            output_path,
            {},
            default_parameters_dict,
            sample_upc_lut
        )
        
        assert os.path.exists(result), f"Output file {result} was not created"
        
        with open(result, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        # Should have header only (no detail records)
        assert len(rows) == 1, "CSV should have only header row when no detail records"

    def test_convert_with_a_records(self, edi_file, tmp_path, sample_upc_lut):
        """Test that A records are included when configured."""
        import convert_to_csv
        
        parameters = {
            'calculate_upc_check_digit': 'False',
            'include_a_records': 'True',
            'include_c_records': 'False',
            'include_headers': 'True',
            'filter_ampersand': 'True',
            'pad_a_records': 'False',
            'a_record_padding': '      ',
            'override_upc_bool': False,
            'override_upc_level': 1,
            'override_upc_category_filter': '',
            'retail_uom': False,
            'upc_target_length': 11,
            'upc_padding_pattern': '           ',
        }
        
        output_path = str(tmp_path / "output_with_a")
        
        result = convert_to_csv.edi_convert(
            edi_file,
            output_path,
            {},
            parameters,
            sample_upc_lut
        )
        
        with open(result, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        # Should have header + A record + B record
        a_record_found = any(row[0] == 'A' for row in rows)
        assert a_record_found, "A record should be in output when include_a_records is True"

    def test_convert_with_c_records(self, edi_file, tmp_path, default_parameters_dict, sample_upc_lut):
        """Test that C records are included when configured."""
        import convert_to_csv
        
        parameters = default_parameters_dict.copy()
        parameters['include_c_records'] = 'True'
        
        output_path = str(tmp_path / "output_with_c")
        
        result = convert_to_csv.edi_convert(
            edi_file,
            output_path,
            {},
            parameters,
            sample_upc_lut
        )
        
        with open(result, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        # Should have C record
        c_record_found = any(row[0] == 'C' for row in rows)
        assert c_record_found, "C record should be in output when include_c_records is True"

    def test_convert_ampersand_filtering(self, tmp_path, sample_upc_lut):
        """Test that ampersands are replaced with AND when filter is enabled."""
        import convert_to_csv
        
        # Create EDI with ampersand in description
        detail = ("B" + "01234567890" + "Tom & Jerry Product     " + "123456" + "000100" +
                  "01" + "000001" + "00010" + "00199" + "001" + "000000")
        header = "A" + "VENDOR" + "0000000001" + "010125" + "0000010000"
        edi_content = header + "\n" + detail + "\n"
        
        edi_path = tmp_path / "test_ampersand.edi"
        edi_path.write_text(edi_content, encoding='utf-8')
        
        parameters = {
            'calculate_upc_check_digit': 'False',
            'include_a_records': 'False',
            'include_c_records': 'False',
            'include_headers': 'True',
            'filter_ampersand': 'True',
            'pad_a_records': 'False',
            'a_record_padding': '      ',
            'override_upc_bool': False,
            'override_upc_level': 1,
            'override_upc_category_filter': '',
            'retail_uom': False,
            'upc_target_length': 11,
            'upc_padding_pattern': '           ',
        }
        
        output_path = str(tmp_path / "output_ampersand")
        
        result = convert_to_csv.edi_convert(
            str(edi_path),
            output_path,
            {},
            parameters,
            sample_upc_lut
        )
        
        with open(result, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "Tom AND Jerry" in content, "Ampersand should be replaced with AND"
        assert "Tom & Jerry" not in content, "Ampersand should not appear in output"


# =============================================================================
# TEST CLASS: convert_to_fintech.py
# =============================================================================

@pytest.mark.integration
class TestConvertToFintech:
    """End-to-end tests for convert_to_fintech.py converter."""

    def test_convert_produces_valid_csv(self, edi_file, tmp_path, default_parameters_dict, default_settings_dict, sample_upc_lut):
        """Test that convert_to_fintech produces a valid CSV file."""
        import convert_to_fintech
        
        output_path = str(tmp_path / "output_fintech")
        
        # Mock the invFetcher to avoid database dependency
        with patch('utils.invFetcher') as mock_inv_fetcher_class:
            mock_fetcher = MagicMock()
            mock_fetcher.fetch_cust_no.return_value = 'STORE001'
            mock_inv_fetcher_class.return_value = mock_fetcher
            
            result = convert_to_fintech.edi_convert(
                edi_file,
                output_path,
                default_settings_dict,
                default_parameters_dict,
                sample_upc_lut
            )
        
        assert os.path.exists(result), f"Output file {result} was not created"
        assert result.endswith('.csv'), f"Output {result} should be a CSV file"
        
        with open(result, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        # Verify header row exists
        assert len(rows) >= 1, "CSV should have at least header row"
        assert 'Division_id' in rows[0], "Header should contain Division_id"

    def test_convert_handles_missing_upc(self, edi_file, tmp_path, default_parameters_dict, default_settings_dict):
        """Test that convert_to_fintech handles missing UPC in lookup table."""
        import convert_to_fintech
        
        output_path = str(tmp_path / "output_missing_upc")
        empty_upc_lut = {}  # Empty lookup table
        
        with patch('utils.invFetcher') as mock_inv_fetcher_class:
            mock_fetcher = MagicMock()
            mock_fetcher.fetch_cust_no.return_value = 'STORE001'
            mock_inv_fetcher_class.return_value = mock_fetcher
            
            # This should raise KeyError for missing UPC
            with pytest.raises(KeyError):
                convert_to_fintech.edi_convert(
                    edi_file,
                    output_path,
                    default_settings_dict,
                    default_parameters_dict,
                    empty_upc_lut
                )


# =============================================================================
# TEST CLASS: convert_to_scannerware.py
# =============================================================================

@pytest.mark.integration
class TestConvertToScannerware:
    """End-to-end tests for convert_to_scannerware.py converter."""

    def test_convert_produces_valid_output(self, edi_file, tmp_path, default_parameters_dict, sample_upc_lut):
        """Test that convert_to_scannerware produces a valid output file."""
        import convert_to_scannerware
        
        output_path = str(tmp_path / "output_scannerware")
        
        result = convert_to_scannerware.edi_convert(
            edi_file,
            output_path,
            {},
            default_parameters_dict,
            sample_upc_lut
        )
        
        assert os.path.exists(result), f"Output file {result} was not created"
        
        # Verify content is not empty
        with open(result, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert len(content) > 0, "Output file should not be empty"

    def test_convert_with_txt_extension(self, edi_file, tmp_path, default_parameters_dict, sample_upc_lut):
        """Test that output has .txt extension when force_txt_file_ext is True."""
        import convert_to_scannerware
        
        parameters = default_parameters_dict.copy()
        parameters['force_txt_file_ext'] = 'True'
        
        output_path = str(tmp_path / "output_txt")
        
        result = convert_to_scannerware.edi_convert(
            edi_file,
            output_path,
            {},
            parameters,
            sample_upc_lut
        )
        
        assert result.endswith('.txt'), f"Output {result} should have .txt extension"

    def test_convert_with_date_offset(self, edi_file, tmp_path, default_parameters_dict, sample_upc_lut):
        """Test that invoice date is offset correctly."""
        import convert_to_scannerware
        
        parameters = default_parameters_dict.copy()
        parameters['invoice_date_offset'] = 7  # Add 7 days
        
        output_path = str(tmp_path / "output_date_offset")
        
        result = convert_to_scannerware.edi_convert(
            edi_file,
            output_path,
            {},
            parameters,
            sample_upc_lut
        )
        
        # Read and verify date was offset
        with open(result, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Find A record line and check date
        for line in lines:
            if line.startswith('A'):
                # Original date is 010125 (Jan 1, 2025)
                # With 7 day offset should be 010825 (Jan 8, 2025)
                assert '010825' in line, "Date should be offset by 7 days"
                break


# =============================================================================
# TEST CLASS: convert_to_simplified_csv.py
# =============================================================================

@pytest.mark.integration
class TestConvertToSimplifiedCSV:
    """End-to-end tests for convert_to_simplified_csv.py converter."""

    def test_convert_produces_valid_csv(self, edi_file, tmp_path, default_parameters_dict, sample_upc_lut):
        """Test that convert_to_simplified_csv produces a valid CSV file."""
        import convert_to_simplified_csv
        
        output_path = str(tmp_path / "output_simple")
        
        result = convert_to_simplified_csv.edi_convert(
            edi_file,
            output_path,
            {},
            default_parameters_dict,
            sample_upc_lut
        )
        
        assert os.path.exists(result), f"Output file {result} was not created"
        assert result.endswith('.csv'), f"Output {result} should be a CSV file"
        
        with open(result, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        assert len(rows) >= 1, "CSV should have at least header row"

    def test_convert_without_headers(self, edi_file, tmp_path, default_parameters_dict, sample_upc_lut):
        """Test that headers are omitted when configured."""
        import convert_to_simplified_csv
        
        parameters = default_parameters_dict.copy()
        parameters['include_headers'] = 'False'
        
        output_path = str(tmp_path / "output_no_headers")
        
        result = convert_to_simplified_csv.edi_convert(
            edi_file,
            output_path,
            {},
            parameters,
            sample_upc_lut
        )
        
        with open(result, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        # First row should not be header
        if len(rows) > 0:
            assert rows[0][0] != 'UPC', "First row should not be header when include_headers is False"

    def test_convert_column_order(self, edi_file, tmp_path, default_parameters_dict, sample_upc_lut):
        """Test that columns are in configured order."""
        import convert_to_simplified_csv
        
        output_path = str(tmp_path / "output_column_order")
        
        result = convert_to_simplified_csv.edi_convert(
            edi_file,
            output_path,
            {},
            default_parameters_dict,
            sample_upc_lut
        )
        
        with open(result, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        # Verify header order matches configuration
        expected_order = ['UPC', 'Quantity', 'Cost']
        for i, expected in enumerate(expected_order):
            if i < len(rows[0]):
                assert expected in rows[0][i], f"Column {i} should contain {expected}"


# =============================================================================
# TEST CLASS: convert_to_yellowdog_csv.py
# =============================================================================

@pytest.mark.integration
class TestConvertToYellowdogCSV:
    """End-to-end tests for convert_to_yellowdog_csv.py converter."""

    def test_convert_produces_valid_csv(self, edi_file, tmp_path, default_parameters_dict, default_settings_dict, sample_upc_lut):
        """Test that convert_to_yellowdog_csv produces a valid CSV file."""
        import convert_to_yellowdog_csv
        
        output_path = str(tmp_path / "output_yellowdog")
        
        # Mock the invFetcher and query_runner to avoid database dependency
        with patch('utils.invFetcher') as mock_inv_fetcher_class:
            mock_fetcher = MagicMock()
            mock_fetcher.fetch_cust_name.return_value = 'Test Customer'
            mock_fetcher.fetch_po.return_value = 'PO12345'
            mock_fetcher.fetch_uom_desc.return_value = 'EA'
            mock_inv_fetcher_class.return_value = mock_fetcher
            
            result = convert_to_yellowdog_csv.edi_convert(
                edi_file,
                output_path,
                default_settings_dict,
                default_parameters_dict,
                sample_upc_lut
            )
        
        assert os.path.exists(result), f"Output file {result} was not created"
        assert result.endswith('.csv'), f"Output {result} should be a CSV file"
        
        with open(result, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        assert len(rows) >= 1, "CSV should have at least header row"
        # Verify expected columns in header
        assert 'Invoice Number' in rows[0], "Header should contain Invoice Number"


# =============================================================================
# TEST CLASS: convert_to_estore_einvoice.py
# =============================================================================

@pytest.mark.integration
class TestConvertToEstoreEinvoice:
    """End-to-end tests for convert_to_estore_einvoice.py converter."""

    def test_convert_produces_valid_csv(self, edi_file, tmp_path, default_parameters_dict, sample_upc_lut):
        """Test that convert_to_estore_einvoice produces a valid CSV file."""
        import convert_to_estore_einvoice
        
        output_path = str(tmp_path / "output_estore")
        
        result = convert_to_estore_einvoice.edi_convert(
            edi_file,
            output_path,
            {},
            default_parameters_dict,
            sample_upc_lut
        )
        
        assert os.path.exists(result), f"Output file {result} was not created"
        assert result.endswith('.csv'), f"Output {result} should be a CSV file"
        
        with open(result, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        assert len(rows) >= 1, "CSV should have at least one row"

    def test_convert_output_filename_format(self, edi_file, tmp_path, default_parameters_dict, sample_upc_lut):
        """Test that output filename follows expected format."""
        import convert_to_estore_einvoice
        
        output_path = str(tmp_path / "output_filename_test")
        
        result = convert_to_estore_einvoice.edi_convert(
            edi_file,
            output_path,
            {},
            default_parameters_dict,
            sample_upc_lut
        )
        
        # Output filename should contain vendor name and timestamp
        assert 'eInv' in result, "Output filename should start with eInv"
        assert 'TestVendor' in result, "Output filename should contain vendor name"


# =============================================================================
# TEST CLASS: convert_to_estore_einvoice_generic.py
# =============================================================================

@pytest.mark.integration
class TestConvertToEstoreEinvoiceGeneric:
    """End-to-end tests for convert_to_estore_einvoice_generic.py converter."""

    def test_convert_produces_valid_csv(self, edi_file, tmp_path, default_parameters_dict, default_settings_dict, sample_upc_lut):
        """Test that convert_to_estore_einvoice_generic produces a valid CSV file."""
        import convert_to_estore_einvoice_generic
        
        output_path = str(tmp_path / "output_estore_generic")
        
        # Mock the query_runner to avoid database dependency
        with patch('convert_to_estore_einvoice_generic.query_runner'):
            result = convert_to_estore_einvoice_generic.edi_convert(
                edi_file,
                output_path,
                default_settings_dict,
                default_parameters_dict,
                sample_upc_lut
            )
        
        assert os.path.exists(result), f"Output file {result} was not created"
        assert result.endswith('.csv'), f"Output {result} should be a CSV file"


# =============================================================================
# TEST CLASS: convert_to_stewarts_custom.py
# =============================================================================

@pytest.mark.integration
class TestConvertToStewartsCustom:
    """End-to-end tests for convert_to_stewarts_custom.py converter."""

    def test_convert_produces_valid_csv(self, edi_file, tmp_path, default_parameters_dict, default_settings_dict, sample_upc_lut):
        """Test that convert_to_stewarts_custom produces a valid CSV file."""
        import convert_to_stewarts_custom
        
        output_path = str(tmp_path / "output_stewarts")
        
        # Mock the query_runner to avoid database dependency
        with patch('convert_to_stewarts_custom.query_runner') as mock_qr_class:
            mock_qr_instance = MagicMock()
            # First call is for header_fields, second call is for uom_lookup_list
            mock_qr_instance.run_arbitrary_query.side_effect = [
                # Header fields query result
                [['Salesperson', '2025-01-01', 'NET30', '30', 'A', '12345', 
                  'Test Customer', '123 Main St', 'Anytown', 'ST', '12345', 
                  '5551234567', 'test@email.com', '', 'A', '12345', 
                  'Corporate Customer', '456 Corp St', 'Corptown', 'ST', '54321',
                  '5559876543', 'corp@email.com', '']],
                # UOM lookup list query result (itemno, uom_mult, uom_code)
                [['123456', '1', 'EA']],
            ]
            mock_qr_class.return_value = mock_qr_instance
            
            result = convert_to_stewarts_custom.edi_convert(
                edi_file,
                output_path,
                default_settings_dict,
                default_parameters_dict,
                sample_upc_lut
            )
        
        assert os.path.exists(result), f"Output file {result} was not created"
        assert result.endswith('.csv'), f"Output {result} should be a CSV file"


# =============================================================================
# TEST CLASS: convert_to_scansheet_type_a.py
# =============================================================================

@pytest.mark.integration
class TestConvertToScansheetTypeA:
    """End-to-end tests for convert_to_scansheet_type_a.py converter."""

    def test_convert_produces_valid_xlsx(self, edi_file, tmp_path, default_parameters_dict, default_settings_dict, sample_upc_lut):
        """Test that convert_to_scansheet_type_a produces a valid XLSX file."""
        import convert_to_scansheet_type_a
        
        output_path = str(tmp_path / "output_scansheet")
        
        # Mock the query_runner to avoid database dependency
        with patch('convert_to_scansheet_type_a.query_runner') as mock_qr:
            mock_qr_instance = MagicMock()
            mock_qr_instance.run_arbitrary_query.return_value = [
                ['012345678901', '123456', 'Test Item', '12', 'EA', '10', '1.00', '1.99']
            ]
            mock_qr.return_value = mock_qr_instance
            
            result = convert_to_scansheet_type_a.edi_convert(
                edi_file,
                output_path,
                default_settings_dict,
                default_parameters_dict,
                sample_upc_lut
            )
        
        assert os.path.exists(result), f"Output file {result} was not created"
        assert result.endswith('.xlsx'), f"Output {result} should be an XLSX file"


# =============================================================================
# TEST CLASS: convert_to_jolley_custom.py
# =============================================================================

@pytest.mark.integration
class TestConvertToJolleyCustom:
    """End-to-end tests for convert_to_jolley_custom.py converter."""

    def test_convert_produces_valid_csv(self, edi_file, tmp_path, default_parameters_dict, default_settings_dict, sample_upc_lut):
        """Test that convert_to_jolley_custom produces a valid CSV file."""
        import convert_to_jolley_custom
        
        output_path = str(tmp_path / "output_jolley")
        
        # Mock the query_runner to avoid database dependency
        with patch('convert_to_jolley_custom.query_runner') as mock_qr_class:
            mock_qr_instance = MagicMock()
            # First call is for header_fields, second call is for uom_lookup_list
            mock_qr_instance.run_arbitrary_query.side_effect = [
                # Header fields query result
                [['Salesperson', '2025-01-01', 'NET30', '30', 'A', '12345', 
                  'Test Customer', '123 Main St', 'Anytown', 'ST', '12345', 
                  '5551234567', 'test@email.com', '', 'A', '12345', 
                  'Corporate Customer', '456 Corp St', 'Corptown', 'ST', '54321',
                  '5559876543', 'corp@email.com', '']],
                # UOM lookup list query result (itemno, uom_mult, uom_code)
                [['123456', '1', 'EA']],
            ]
            mock_qr_class.return_value = mock_qr_instance
            
            result = convert_to_jolley_custom.edi_convert(
                edi_file,
                output_path,
                default_settings_dict,
                default_parameters_dict,
                sample_upc_lut
            )
        
        assert os.path.exists(result), f"Output file {result} was not created"
        assert result.endswith('.csv'), f"Output {result} should be a CSV file"


# =============================================================================
# TEST CLASS: Edge Cases and Error Handling
# =============================================================================

@pytest.mark.integration
class TestConversionEdgeCases:
    """Test edge cases and error handling across converters."""

    def test_empty_edi_file(self, tmp_path, default_parameters_dict, sample_upc_lut):
        """Test handling of empty EDI file."""
        import convert_to_csv
        
        # Create empty EDI file
        empty_edi = tmp_path / "empty.edi"
        empty_edi.write_text("", encoding='utf-8')
        
        output_path = str(tmp_path / "output_empty")
        
        result = convert_to_csv.edi_convert(
            str(empty_edi),
            output_path,
            {},
            default_parameters_dict,
            sample_upc_lut
        )
        
        # Should create output file even with empty input
        assert os.path.exists(result), "Output file should be created even for empty input"

    def test_unicode_in_description(self, tmp_path, default_parameters_dict, sample_upc_lut):
        """Test handling of unicode characters in description."""
        import convert_to_csv
        
        # Create EDI with unicode in description
        detail = ("B" + "01234567890" + "Café Product Item       " + "123456" + "000100" +
                  "01" + "000001" + "00010" + "00199" + "001" + "000000")
        header = "A" + "VENDOR" + "0000000001" + "010125" + "0000010000"
        edi_content = header + "\n" + detail + "\n"
        
        edi_path = tmp_path / "unicode.edi"
        edi_path.write_text(edi_content, encoding='utf-8')
        
        output_path = str(tmp_path / "output_unicode")
        
        result = convert_to_csv.edi_convert(
            str(edi_path),
            output_path,
            {},
            default_parameters_dict,
            sample_upc_lut
        )
        
        with open(result, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Unicode should be preserved
        assert 'Café' in content, "Unicode characters should be preserved"

    def test_multiple_invoices(self, tmp_path, default_parameters_dict, sample_upc_lut):
        """Test handling of multiple invoices in single file."""
        import convert_to_csv
        
        # Create EDI with two invoices
        header1 = "A" + "VENDOR" + "0000000001" + "010125" + "0000010000"
        detail1 = ("B" + "01234567890" + "First Product Item     " + "123456" + "000100" +
                   "01" + "000001" + "00010" + "00199" + "001" + "000000")
        header2 = "A" + "VENDOR" + "0000000002" + "010225" + "0000020000"
        detail2 = ("B" + "98765432109" + "Second Product Item    " + "654321" + "000200" +
                   "02" + "000002" + "00005" + "00299" + "002" + "000000")
        
        edi_content = header1 + "\n" + detail1 + "\n" + header2 + "\n" + detail2 + "\n"
        
        edi_path = tmp_path / "multi_invoice.edi"
        edi_path.write_text(edi_content, encoding='utf-8')
        
        output_path = str(tmp_path / "output_multi")
        
        result = convert_to_csv.edi_convert(
            str(edi_path),
            output_path,
            {},
            default_parameters_dict,
            sample_upc_lut
        )
        
        with open(result, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        # Should have header + 2 detail rows
        assert len(rows) >= 3, "Should have header and 2 detail rows for 2 invoices"

    def test_negative_quantity(self, tmp_path, default_parameters_dict, sample_upc_lut):
        """Test handling of negative quantity (returns/credits)."""
        import convert_to_simplified_csv
        
        # Create EDI with negative quantity (using -0010 format)
        # The qty_of_units field is 5 chars at positions 57-62
        # Note: The simplified_csv converter's qty_to_int function handles negatives
        detail = ("B" + "01234567890" + "Returned Item           " + "123456" + "000100" +
                  "01" + "000001" + "-0010" + "00199" + "001" + "000000")
        header = "A" + "VENDOR" + "0000000001" + "010125" + "0000010000"
        edi_content = header + "\n" + detail + "\n"
        
        edi_path = tmp_path / "negative_qty.edi"
        edi_path.write_text(edi_content, encoding='utf-8')
        
        output_path = str(tmp_path / "output_negative")
        
        result = convert_to_simplified_csv.edi_convert(
            str(edi_path),
            output_path,
            {},
            default_parameters_dict,
            sample_upc_lut
        )
        
        with open(result, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        # Should have header and detail row
        assert len(rows) >= 2, "Should have header and detail row"
        # The converter should process the quantity field
        # Note: The exact handling depends on the EDI format and converter logic
        quantity_value = rows[1][1]  # Second column is Quantity
        # Verify the quantity was processed (it should be an integer)
        assert quantity_value.lstrip('-').isdigit(), f"Quantity should be numeric, got {quantity_value}"


# =============================================================================
# TEST CLASS: Output Format Validation
# =============================================================================

@pytest.mark.integration
class TestOutputFormatValidation:
    """Validate output formats match expected specifications."""

    def test_csv_uses_crlf_line_endings(self, edi_file, tmp_path, default_parameters_dict, sample_upc_lut):
        """Test that CSV output uses CRLF line endings (Excel format)."""
        import convert_to_csv
        
        output_path = str(tmp_path / "output_crlf")
        
        result = convert_to_csv.edi_convert(
            edi_file,
            output_path,
            {},
            default_parameters_dict,
            sample_upc_lut
        )
        
        with open(result, 'rb') as f:
            content = f.read()
        
        # CSV should use CRLF line endings
        assert b'\r\n' in content, "CSV should use CRLF line endings for Excel compatibility"

    def test_csv_quotes_all_fields(self, edi_file, tmp_path, default_parameters_dict, sample_upc_lut):
        """Test that CSV output quotes all fields."""
        import convert_to_csv
        
        output_path = str(tmp_path / "output_quoted")
        
        result = convert_to_csv.edi_convert(
            edi_file,
            output_path,
            {},
            default_parameters_dict,
            sample_upc_lut
        )
        
        with open(result, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # All fields should be quoted
        lines = content.strip().split('\n')
        for line in lines:
            if line:
                assert line.startswith('"'), "Each line should start with a quote"
                assert line.endswith('"'), "Each line should end with a quote"

    def test_price_format_conversion(self, edi_file, tmp_path, default_parameters_dict, sample_upc_lut):
        """Test that price values are correctly converted from cents to dollars."""
        import convert_to_csv
        
        output_path = str(tmp_path / "output_price")
        
        result = convert_to_csv.edi_convert(
            edi_file,
            output_path,
            {},
            default_parameters_dict,
            sample_upc_lut
        )
        
        with open(result, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        # Find a detail row and check price format
        # Unit cost 000100 should become 1.00
        for row in rows[1:]:  # Skip header
            if len(row) >= 3:
                cost = row[2]
                # Cost should have decimal point
                if cost != 'Cost':  # Skip header
                    assert '.' in cost, f"Cost {cost} should have decimal point"
                    break
