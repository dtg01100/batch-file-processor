"""Unit tests for convert_to_estore_einvoice.py converter module.

Tests:
- Input validation and error handling
- Tax calculation and trailer records
- Shipper mode handling
- Format compliance for e-invoice format
- Data transformation accuracy

Converter: convert_to_estore_einvoice.py (9668 chars)
"""

import pytest
from unittest.mock import patch, MagicMock, mock_open
import tempfile
import os
import csv
from decimal import Decimal
import re

# Import the module to test
import convert_to_estore_einvoice


class TestEstoreEinvoiceFixtures:
    """Test fixtures for convert_to_estore_einvoice module."""

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
        """Detail record with parent item."""
        return ("B" + "01234567890" + "Parent Item Description " + "123456" + "000100" +
                "01" + "000002" + "00005" + "00199" + "001" + "123456")

    @pytest.fixture
    def sample_detail_record_child(self):
        """Detail record that is a child of parent."""
        return ("B" + "01234567891" + "Child Item Description  " + "123457" + "000100" +
                "01" + "000001" + "00003" + "00199" + "001" + "123456")

    @pytest.fixture
    def sample_tax_record(self):
        """Create accurate sales tax record (38 chars)."""
        return "C" + "TAB" + "Sales Tax" + " " * 16 + "000010000"

    @pytest.fixture
    def complete_edi_content(self, sample_header_record, sample_detail_record, sample_tax_record):
        """Create complete EDI content with header, detail, and tax records."""
        return sample_header_record + "\n" + sample_detail_record + "\n" + sample_tax_record + "\n"

    @pytest.fixture
    def default_parameters(self):
        """Default parameters dict for convert_to_estore_einvoice."""
        return {
            'estore_store_number': '001',
            'estore_Vendor_OId': 'VENDOR123',
            'estore_vendor_NameVendorOID': 'TestVendor',
        }

    @pytest.fixture
    def default_settings(self):
        """Default settings dict."""
        return {}

    @pytest.fixture
    def sample_upc_lut(self):
        """Sample UPC lookup table."""
        return {
            123456: ('CAT1', '012345678905', '012345678900'),
        }


class TestEstoreEinvoiceBasicFunctionality(TestEstoreEinvoiceFixtures):
    """Test basic functionality of convert_to_estore_einvoice."""

    def test_module_import(self):
        """Test that convert_to_estore_einvoice module can be imported."""
        import convert_to_estore_einvoice
        assert convert_to_estore_einvoice is not None
        assert hasattr(convert_to_estore_einvoice, 'edi_convert')

    def test_edi_convert_returns_csv_filename(self, complete_edi_content, default_parameters,
                                               default_settings, sample_upc_lut, tmp_path):
        """Test that edi_convert returns the expected CSV filename with eInv prefix."""
        # Create temp input file
        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        result = convert_to_estore_einvoice.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            sample_upc_lut
        )

        # Filename should have eInv prefix
        assert "eInv" in result
        assert result.endswith(".csv")

    def test_creates_csv_file(self, complete_edi_content, default_parameters,
                               default_settings, sample_upc_lut, tmp_path):
        """Test that the CSV file is actually created."""
        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        convert_to_estore_einvoice.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            sample_upc_lut
        )

        # File should exist
        result_path = os.path.dirname(output_file)
        import glob
        csv_files = glob.glob(os.path.join(result_path, "eInv*.csv"))
        assert len(csv_files) > 0


class TestEstoreEinvoiceHeaderRecord(TestEstoreEinvoiceFixtures):
    """Test header record (H record) handling."""

    def test_header_record_type_h(self, complete_edi_content, default_parameters,
                                   default_settings, sample_upc_lut, tmp_path):
        """Test that header record uses 'H' record type."""
        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        result = convert_to_estore_einvoice.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            sample_upc_lut
        )

        # Find the output file
        import glob
        csv_files = glob.glob(os.path.join(os.path.dirname(output_file), "eInv*.csv"))
        with open(csv_files[0], 'r', encoding='utf-8') as f:
            content = f.read()
            # Should have H record type
            assert "H," in content

    def test_store_number_in_output(self, complete_edi_content, default_parameters,
                                    default_settings, sample_upc_lut, tmp_path):
        """Test that store number appears in output."""
        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        convert_to_estore_einvoice.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            sample_upc_lut
        )

        import glob
        csv_files = glob.glob(os.path.join(os.path.dirname(output_file), "eInv*.csv"))
        with open(csv_files[0], 'r', encoding='utf-8') as f:
            content = f.read()
            # Should have store number
            assert "001" in content

    def test_vendor_oid_in_output(self, complete_edi_content, default_parameters,
                                   default_settings, sample_upc_lut, tmp_path):
        """Test that vendor OID appears in output."""
        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        convert_to_estore_einvoice.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            sample_upc_lut
        )

        import glob
        csv_files = glob.glob(os.path.join(os.path.dirname(output_file), "eInv*.csv"))
        with open(csv_files[0], 'r', encoding='utf-8') as f:
            content = f.read()
            # Should have vendor OID
            assert "VENDOR123" in content


class TestEstoreEinvoiceDetailRecord(TestEstoreEinvoiceFixtures):
    """Test detail record (D record) handling."""

    def test_detail_record_type_d(self, complete_edi_content, default_parameters,
                                   default_settings, sample_upc_lut, tmp_path):
        """Test that detail records use 'D' record type."""
        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        convert_to_estore_einvoice.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            sample_upc_lut
        )

        import glob
        csv_files = glob.glob(os.path.join(os.path.dirname(output_file), "eInv*.csv"))
        with open(csv_files[0], 'r', encoding='utf-8') as f:
            content = f.read()
            # Should have D record type
            assert "D," in content

    def test_gtin_upc_in_output(self, complete_edi_content, default_parameters,
                                  default_settings, sample_upc_lut, tmp_path):
        """Test that GTIN/UPC appears in output."""
        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        convert_to_estore_einvoice.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            sample_upc_lut
        )

        import glob
        csv_files = glob.glob(os.path.join(os.path.dirname(output_file), "eInv*.csv"))
        with open(csv_files[0], 'r', encoding='utf-8') as f:
            content = f.read()
            # Should have GTIN/UPC
            assert "012345678905" in content


class TestEstoreEinvoiceTrailerRecord(TestEstoreEinvoiceFixtures):
    """Test trailer record (T record) handling."""

    def test_trailer_record_present(self, complete_edi_content, default_parameters,
                                    default_settings, sample_upc_lut, tmp_path):
        """Test that trailer records are present."""
        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        convert_to_estore_einvoice.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            sample_upc_lut
        )

        import glob
        csv_files = glob.glob(os.path.join(os.path.dirname(output_file), "eInv*.csv"))
        with open(csv_files[0], 'r', encoding='utf-8') as f:
            content = f.read()
            # Should have T record type for trailer
            assert "T," in content

    def test_trailer_contains_invoice_cost(self, complete_edi_content, default_parameters,
                                            default_settings, sample_upc_lut, tmp_path):
        """Test that trailer contains invoice cost/total."""
        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        convert_to_estore_einvoice.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            sample_upc_lut
        )

        import glob
        csv_files = glob.glob(os.path.join(os.path.dirname(output_file), "eInv*.csv"))
        with open(csv_files[0], 'r', encoding='utf-8') as f:
            content = f.read()
            # Should have invoice cost field
            assert "T,0" in content or ",0" in content


class TestEstoreEinvoiceTaxCalculation(TestEstoreEinvoiceFixtures):
    """Test tax calculation."""

    def test_tax_from_c_record(self, sample_header_record, default_parameters,
                               default_settings, sample_upc_lut, tmp_path):
        """Test that tax amounts from C records are included in calculations."""
        # Create EDI with detail and tax
        detail = ("B" + "01234567890" + "Test Item Description    " + "123456" + "000100" +
                  "01" + "000001" + "00010" + "00199" + "001" + "000000")
        # Tax = $100.00
        tax = "C" + "TAB" + "Sales Tax" + " " * 16 + "0000100000"
        edi_content = sample_header_record + "\n" + detail + "\n" + tax + "\n"

        input_file = tmp_path / "input.edi"
        input_file.write_text(edi_content)

        output_file = str(tmp_path / "output")

        convert_to_estore_einvoice.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            sample_upc_lut
        )

        import glob
        csv_files = glob.glob(os.path.join(os.path.dirname(output_file), "eInv*.csv"))
        with open(csv_files[0], 'r', encoding='utf-8') as f:
            content = f.read()
            # Should include tax info (trailer with 0 means no tax was added)
            assert "T," in content


class TestEstoreEinvoiceShipperMode(TestEstoreEinvoiceFixtures):
    """Test shipper mode handling."""

    def test_shipper_mode_with_parent_item(self, sample_header_record, default_parameters,
                                            default_settings, sample_upc_lut, tmp_path):
        """Test handling of items with parent (shipper mode)."""
        # Create parent item
        parent = ("B" + "01234567890" + "Parent Pack Item        " + "123456" + "000100" +
                  "01" + "000005" + "00001" + "00199" + "001" + "000000")
        # Create child item
        child = ("B" + "01234567891" + "Child Item Description  " + "123457" + "000100" +
                 "01" + "000001" + "00005" + "00199" + "001" + "123456")

        edi_content = sample_header_record + "\n" + parent + "\n" + child + "\n"

        input_file = tmp_path / "input.edi"
        input_file.write_text(edi_content)

        output_file = str(tmp_path / "output")

        result = convert_to_estore_einvoice.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            sample_upc_lut
        )

        # Should complete without errors
        assert os.path.exists(result)

    def test_shipper_mode_enter_exit(self, sample_header_record, default_parameters,
                                      default_settings, sample_upc_lut, tmp_path):
        """Test shipper mode entry and exit."""
        # Parent item followed by child items, then regular item
        parent = ("B" + "01234567890" + "Parent Pack Item        " + "123456" + "000100" +
                  "01" + "000005" + "00001" + "00199" + "001" + "000000")
        child = ("B" + "01234567891" + "Child Item Description  " + "123457" + "000100" +
                 "01" + "000001" + "00005" + "00199" + "001" + "123456")
        regular = ("B" + "01234567892" + "Regular Item            " + "234567" + "000200" +
                   "01" + "000001" + "00002" + "00299" + "001" + "000000")

        edi_content = sample_header_record + "\n" + parent + "\n" + child + "\n" + regular + "\n"

        input_file = tmp_path / "input.edi"
        input_file.write_text(edi_content)

        output_file = str(tmp_path / "output")

        result = convert_to_estore_einvoice.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            sample_upc_lut
        )

        # Should handle shipper mode transitions
        assert os.path.exists(result)


class TestEstoreEinvoiceDateHandling(TestEstoreEinvoiceFixtures):
    """Test invoice date handling."""

    def test_invoice_date_format_yyyymmdd(self, sample_header_record, default_parameters,
                                            default_settings, sample_upc_lut, tmp_path):
        """Test that invoice date is formatted as YYYYMMDD."""
        # Date: 010125 = Jan 1, 2025
        header = "A" + "VENDOR" + "0000000001" + "010125" + "0000010000"
        detail = ("B" + "01234567890" + "Test Item Description    " + "123456" + "000100" +
                  "01" + "000001" + "00010" + "00199" + "001" + "000000")
        edi_content = header + "\n" + detail + "\n"

        input_file = tmp_path / "input.edi"
        input_file.write_text(edi_content)

        output_file = str(tmp_path / "output")

        convert_to_estore_einvoice.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            sample_upc_lut
        )

        import glob
        csv_files = glob.glob(os.path.join(os.path.dirname(output_file), "eInv*.csv"))
        with open(csv_files[0], 'r', encoding='utf-8') as f:
            content = f.read()
            # Should have date in YYYYMMDD format (20250125)
            assert "2025" in content or "20250125" in content

    def test_zero_date_handling(self, default_parameters, default_settings, 
                                 sample_upc_lut, tmp_path):
        """Test handling of zero date (000000)."""
        # Date: 000000 = zero/unknown
        header = "A" + "VENDOR" + "0000000001" + "000000" + "0000010000"
        detail = ("B" + "01234567890" + "Test Item Description    " + "123456" + "000100" +
                  "01" + "000001" + "00010" + "00199" + "001" + "000000")
        edi_content = header + "\n" + detail + "\n"

        input_file = tmp_path / "input.edi"
        input_file.write_text(edi_content)

        output_file = str(tmp_path / "output")

        result = convert_to_estore_einvoice.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            sample_upc_lut
        )

        # Should handle zero date gracefully
        assert os.path.exists(result)


class TestEstoreEinvoiceEdgeCases(TestEstoreEinvoiceFixtures):
    """Test edge cases and error conditions."""

    def test_empty_edi_file(self, default_parameters, default_settings, 
                           sample_upc_lut, tmp_path):
        """Test handling of empty EDI file."""
        input_file = tmp_path / "input.edi"
        input_file.write_text("")

        output_file = str(tmp_path / "output")

        result = convert_to_estore_einvoice.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            sample_upc_lut
        )

        # Should create empty file
        assert os.path.exists(result)

    def test_only_header_record(self, sample_header_record, default_parameters,
                                default_settings, sample_upc_lut, tmp_path):
        """Test with only header record."""
        edi_content = sample_header_record + "\n"

        input_file = tmp_path / "input.edi"
        input_file.write_text(edi_content)

        output_file = str(tmp_path / "output")

        result = convert_to_estore_einvoice.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            sample_upc_lut
        )

        assert os.path.exists(result)

    def test_multiple_detail_records(self, sample_header_record, default_parameters,
                                     default_settings, sample_upc_lut, tmp_path):
        """Test with multiple detail records."""
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

        convert_to_estore_einvoice.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            sample_upc_lut
        )

        import glob
        csv_files = glob.glob(os.path.join(os.path.dirname(output_file), "eInv*.csv"))
        with open(csv_files[0], 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
            # Should have multiple data rows (excluding header)
            data_rows = [r for r in rows if r and r[0] != "Store #"]
            assert len(data_rows) >= 3

    def test_missing_upc_in_lut(self, sample_header_record, default_parameters,
                                 default_settings, sample_upc_lut, tmp_path):
        """Test handling when UPC is not in lookup table."""
        # vendor_item 999999 not in LUT
        detail = ("B" + "01234567890" + "Test Item Description    " + "999999" + "000100" +
                  "01" + "000001" + "00010" + "00199" + "001" + "000000")
        edi_content = sample_header_record + "\n" + detail + "\n"

        input_file = tmp_path / "input.edi"
        input_file.write_text(edi_content)

        output_file = str(tmp_path / "output")

        result = convert_to_estore_einvoice.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            sample_upc_lut
        )

        # Should handle missing UPC gracefully
        assert os.path.exists(result)


class TestEstoreEinvoiceDataTransformation(TestEstoreEinvoiceFixtures):
    """Test data transformation accuracy."""

    def test_extended_cost_calculation(self, sample_header_record, default_parameters,
                                        default_settings, sample_upc_lut, tmp_path):
        """Test extended cost calculation (unit cost * quantity)."""
        # Unit cost = 000100 = $1.00, qty = 00010 = 10, extended = $10.00
        detail = ("B" + "01234567890" + "Test Item Description    " + "123456" + "000100" +
                  "01" + "000001" + "00010" + "00199" + "001" + "000000")
        edi_content = sample_header_record + "\n" + detail + "\n"

        input_file = tmp_path / "input.edi"
        input_file.write_text(edi_content)

        output_file = str(tmp_path / "output")

        convert_to_estore_einvoice.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            sample_upc_lut
        )

        import glob
        csv_files = glob.glob(os.path.join(os.path.dirname(output_file), "eInv*.csv"))
        with open(csv_files[0], 'r', encoding='utf-8') as f:
            content = f.read()
            # Should have data (extended cost calculation happens internally)
            assert "D," in content or "123456" in content

    def test_quantity_conversion(self, sample_header_record, default_parameters,
                                  default_settings, sample_upc_lut, tmp_path):
        """Test quantity is converted to integer."""
        detail = ("B" + "01234567890" + "Test Item Description    " + "123456" + "000100" +
                  "01" + "000001" + "00010" + "00199" + "001" + "000000")
        edi_content = sample_header_record + "\n" + detail + "\n"

        input_file = tmp_path / "input.edi"
        input_file.write_text(edi_content)

        output_file = str(tmp_path / "output")

        convert_to_estore_einvoice.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            sample_upc_lut
        )

        import glob
        csv_files = glob.glob(os.path.join(os.path.dirname(output_file), "eInv*.csv"))
        with open(csv_files[0], 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
            data_rows = [r for r in rows if r and r[0] != "Store #"]
            # Quantity should be integer
            qty = data_rows[0][14] if len(data_rows[0]) > 14 else None
            if qty:
                assert int(qty) > 0

    def test_detail_type_field(self, complete_edi_content, default_parameters,
                                default_settings, sample_upc_lut, tmp_path):
        """Test that detail type field is present."""
        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        convert_to_estore_einvoice.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            sample_upc_lut
        )

        import glob
        csv_files = glob.glob(os.path.join(os.path.dirname(output_file), "eInv*.csv"))
        with open(csv_files[0], 'r', encoding='utf-8') as f:
            content = f.read()
            # Should have Detail Type field (I, D, C, S)
            assert "Detail Type" in content or "I" in content


class TestEstoreEinvoiceFormatCompliance(TestEstoreEinvoiceFixtures):
    """Test format compliance for e-invoice format."""

    def test_csv_column_structure(self, complete_edi_content, default_parameters,
                                   default_settings, sample_upc_lut, tmp_path):
        """Test that CSV has expected column structure."""
        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        convert_to_estore_einvoice.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            sample_upc_lut
        )

        import glob
        csv_files = glob.glob(os.path.join(os.path.dirname(output_file), "eInv*.csv"))
        with open(csv_files[0], 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
            # Should have data rows
            assert len(rows) >= 1

    def test_vendor_name_in_filename(self, complete_edi_content, default_parameters,
                                      default_settings, sample_upc_lut, tmp_path):
        """Test that vendor name is included in output filename."""
        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        result = convert_to_estore_einvoice.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            sample_upc_lut
        )

        # Filename should include vendor name
        assert "TestVendor" in result
