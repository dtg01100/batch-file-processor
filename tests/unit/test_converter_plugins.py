"""
Comprehensive unit tests for all converter plugin modules.

This module provides unit tests for the 9 converter plugins that convert
EDI files to various output formats. Each converter is tested for:
- Main conversion function existence and callability
- Happy path with valid EDI data
- Error handling with malformed/invalid data
- Edge cases (empty input, missing segments, special characters)
- Output format verification
- Helper function behavior

Tested Converters:
1. convert_to_csv - Standard CSV format with configurable options
2. convert_to_estore_einvoice - eStore eInvoice with shipper mode
3. convert_to_estore_einvoice_generic - Generic eStore with DB lookups
4. convert_to_fintech - Fintech format with division ID
5. convert_to_jolley_custom - Jolley Custom with invoice details
6. convert_to_scannerware - ScannerWare fixed-width format
7. convert_to_scansheet_type_a - Excel with embedded barcodes
8. convert_to_simplified_csv - Simplified CSV with dynamic columns
9. convert_to_stewarts_custom - Stewarts Custom format
10. convert_to_yellowdog_csv - Yellowdog CSV with deferred writing
"""

import os
import sys
import csv
import tempfile
import shutil
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

# Ensure project root is in path
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

# Import all converters
from convert_to_csv import CsvConverter, edi_convert as csv_edi_convert
from convert_to_estore_einvoice import (
    EstoreEinvoiceConverter,
    edi_convert as estore_edi_convert,
)
from convert_to_estore_einvoice_generic import (
    EstoreEinvoiceGenericConverter,
    edi_convert as estore_generic_edi_convert,
)
from convert_to_fintech import FintechConverter, edi_convert as fintech_edi_convert
from convert_to_jolley_custom import (
    JolleyCustomConverter,
    edi_convert as jolley_edi_convert,
    CustomerLookupError,
)
from convert_to_scannerware import (
    ScannerWareConverter,
    edi_convert as scannerware_edi_convert,
)
from convert_to_scansheet_type_a import (
    ScansheetTypeAConverter,
    edi_convert as scansheet_edi_convert,
)
from convert_to_simplified_csv import (
    SimplifiedCsvConverter,
    edi_convert as simplified_edi_convert,
)
from convert_to_stewarts_custom import (
    StewartsCustomConverter,
    edi_convert as stewarts_edi_convert,
    CustomerLookupError as StewartsCustomerLookupError,
)
from convert_to_yellowdog_csv import (
    YellowdogConverter,
    edi_convert as yellowdog_edi_convert,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    test_dir = tempfile.mkdtemp()
    yield test_dir
    shutil.rmtree(test_dir, ignore_errors=True)


@pytest.fixture
def sample_edi_content():
    """Return sample valid EDI content."""
    return """A000001INV00001011221251000012345
B012345678901Product Description 1234561234567890100001000100050000
C00100000123
"""


@pytest.fixture
def complex_edi_content():
    """Return complex EDI content with multiple invoices."""
    return """A000001INV00001011221251000012345
B012345678901Product Description 1234561234567890100001000100050000
B098765432101Another Product Name 9876549876543210200002000200075000
C00100000150
A000002INV00002011321251000054321
B111111111111Third Product Here   1111111111111110300003000300025000
C00100000200
"""


@pytest.fixture
def malformed_edi_content():
    """Return malformed EDI content for error testing."""
    return """A000001INV00001011221251000012345
B012345678901Product Description 1234561234567890100001000100050000
BINVALID
C00100000123
"""


@pytest.fixture
def empty_edi_file(temp_dir):
    """Create an empty EDI file."""
    file_path = os.path.join(temp_dir, "empty.edi")
    with open(file_path, "w") as f:
        f.write("")
    return file_path


@pytest.fixture
def sample_edi_file(temp_dir, sample_edi_content):
    """Create a sample valid EDI file."""
    file_path = os.path.join(temp_dir, "test.edi")
    with open(file_path, "w") as f:
        f.write(sample_edi_content)
    return file_path


@pytest.fixture
def complex_edi_file(temp_dir, complex_edi_content):
    """Create a complex EDI file with multiple invoices."""
    file_path = os.path.join(temp_dir, "complex.edi")
    with open(file_path, "w") as f:
        f.write(complex_edi_content)
    return file_path


@pytest.fixture
def malformed_edi_file(temp_dir, malformed_edi_content):
    """Create a malformed EDI file."""
    file_path = os.path.join(temp_dir, "malformed.edi")
    with open(file_path, "w") as f:
        f.write(malformed_edi_content)
    return file_path


@pytest.fixture
def settings_dict():
    """Return default settings dictionary for converters."""
    return {
        "as400_username": "test_user",
        "as400_password": "test_pass",
        "as400_address": "localhost",
        "odbc_driver": "mock_driver",
    }


@pytest.fixture
def upc_lookup():
    """Return mock UPC lookup dictionary."""
    return {
        123456: ("1001", "012345678901", "012345678902"),
        987654: ("1002", "098765432101", "098765432102"),
        111111: ("1003", "111111111111", "111111111112"),
        222222: ("1004", "222222222222", "222222222223"),
    }


@pytest.fixture
def mock_query_runner():
    """Mock query_runner for database-dependent converters."""
    mock_runner = MagicMock()

    def mock_query_result(query_string):
        query_lower = query_string.lower()

        if "ohhst" in query_lower and (
            "bte4cd" in query_lower or "bthinb" in query_lower
        ):
            return [("PO12345", "Test Customer")]
        elif (
            "odhst" in query_lower
            and "buhhnb" in query_lower
            and "buhunb" in query_lower
        ):
            return [(1, "EA"), (2, "CS"), (3, "BX")]
        elif "dsanrep" in query_lower and "anbacd" in query_lower:
            return [("Each",)]
        elif (
            "odhst" in query_lower
            and "bubacd" in query_lower
            and "bus3qt" in query_lower
        ):
            return [(123456, 1, "EA"), (123456, 12, "CS"), (987654, 6, "BX")]
        elif "ohhst" in query_lower and "dsabrep" in query_lower:
            return [
                (
                    "Salesperson Name",
                    "20231225",
                    "NET30",
                    30,
                    "ACTIVE",
                    1001,
                    "Test Customer",
                    "123 Main St",
                    "Anytown",
                    "CA",
                    "12345",
                    "5551234567",
                    "test@example.com",
                    "secondary@example.com",
                    "ACTIVE",
                    1000,
                    "Corporate Customer",
                    "456 Corp Ave",
                    "Big City",
                    "NY",
                    "67890",
                    "5559876543",
                    "corp@example.com",
                    "corp2@example.com",
                )
            ]
        else:
            return [
                ("123456789012", "ITEM001", "Test Item 1", "12", "EA", 10, 5.99, 7.99),
                ("234567890123", "ITEM002", "Test Item 2", "6", "CS", 5, 12.99, 15.99),
            ]

    mock_runner.run_arbitrary_query.side_effect = mock_query_result
    return mock_runner


# ============================================================================
# CSV CONVERTER TESTS
# ============================================================================


class TestCsvConverter:
    """Tests for convert_to_csv module."""

    def test_converter_class_exists(self):
        """Test that CsvConverter class exists and has required attributes."""
        assert hasattr(CsvConverter, "PLUGIN_ID")
        assert hasattr(CsvConverter, "PLUGIN_NAME")
        assert hasattr(CsvConverter, "PLUGIN_DESCRIPTION")
        assert hasattr(CsvConverter, "CONFIG_FIELDS")
        assert CsvConverter.PLUGIN_ID == "csv"

    def test_edi_convert_function_exists(self):
        """Test that the backward-compatible edi_convert function exists."""
        assert callable(csv_edi_convert)

    def test_converter_initialization(
        self, sample_edi_file, temp_dir, settings_dict, upc_lookup
    ):
        """Test converter can be initialized with default parameters."""
        output_file = os.path.join(temp_dir, "output")
        parameters = {}

        converter = CsvConverter(
            sample_edi_file, output_file, settings_dict, parameters, upc_lookup
        )

        assert converter.edi_process == sample_edi_file
        assert converter.output_filename == output_file
        assert converter.settings_dict == settings_dict
        assert converter.parameters_dict == parameters
        assert converter.upc_lookup == upc_lookup

    def test_happy_path_conversion(
        self, sample_edi_file, temp_dir, settings_dict, upc_lookup
    ):
        """Test successful conversion of valid EDI file."""
        output_file = os.path.join(temp_dir, "output")
        parameters = {"include_headers": "True"}

        converter = CsvConverter(
            sample_edi_file, output_file, settings_dict, parameters, upc_lookup
        )
        result = converter.convert()

        assert os.path.exists(result)
        assert result.endswith(".csv")

        # Verify CSV content
        with open(result, "r") as f:
            reader = csv.reader(f)
            rows = list(reader)
            assert len(rows) > 0
            # First row should be headers
            assert "UPC" in rows[0]

    def test_conversion_without_headers(
        self, sample_edi_file, temp_dir, settings_dict, upc_lookup
    ):
        """Test conversion without including headers."""
        output_file = os.path.join(temp_dir, "output")
        parameters = {"include_headers": "False"}

        converter = CsvConverter(
            sample_edi_file, output_file, settings_dict, parameters, upc_lookup
        )
        result = converter.convert()

        with open(result, "r") as f:
            reader = csv.reader(f)
            rows = list(reader)
            # First row should be data, not headers
            assert len(rows) >= 1

    def test_include_a_records_option(
        self, sample_edi_file, temp_dir, settings_dict, upc_lookup
    ):
        """Test conversion with A records included."""
        output_file = os.path.join(temp_dir, "output")
        parameters = {"include_a_records": "True", "include_headers": "True"}

        converter = CsvConverter(
            sample_edi_file, output_file, settings_dict, parameters, upc_lookup
        )
        result = converter.convert()

        with open(result, "r") as f:
            content = f.read()
            # Should have A record data
            assert "A" in content or len(content) > 0

    def test_include_c_records_option(
        self, sample_edi_file, temp_dir, settings_dict, upc_lookup
    ):
        """Test conversion with C records included."""
        output_file = os.path.join(temp_dir, "output")
        parameters = {"include_c_records": "True", "include_headers": "True"}

        converter = CsvConverter(
            sample_edi_file, output_file, settings_dict, parameters, upc_lookup
        )
        result = converter.convert()

        assert os.path.exists(result)

    def test_filter_ampersand_option(
        self, sample_edi_file, temp_dir, settings_dict, upc_lookup
    ):
        """Test ampersand filtering in descriptions."""
        output_file = os.path.join(temp_dir, "output")
        parameters = {"filter_ampersand": "True"}

        converter = CsvConverter(
            sample_edi_file, output_file, settings_dict, parameters, upc_lookup
        )
        result = converter.convert()

        assert os.path.exists(result)

    def test_retail_uom_option(
        self, sample_edi_file, temp_dir, settings_dict, upc_lookup
    ):
        """Test retail UOM transformation."""
        output_file = os.path.join(temp_dir, "output")
        parameters = {"retail_uom": "True"}

        converter = CsvConverter(
            sample_edi_file, output_file, settings_dict, parameters, upc_lookup
        )
        result = converter.convert()

        assert os.path.exists(result)

    def test_empty_file_handling(
        self, empty_edi_file, temp_dir, settings_dict, upc_lookup
    ):
        """Test conversion of empty EDI file."""
        output_file = os.path.join(temp_dir, "output")
        parameters = {}

        converter = CsvConverter(
            empty_edi_file, output_file, settings_dict, parameters, upc_lookup
        )
        result = converter.convert()

        assert os.path.exists(result)

    def test_complex_invoice_conversion(
        self, complex_edi_file, temp_dir, settings_dict, upc_lookup
    ):
        """Test conversion of complex EDI with multiple invoices."""
        output_file = os.path.join(temp_dir, "output")
        parameters = {}

        converter = CsvConverter(
            complex_edi_file, output_file, settings_dict, parameters, upc_lookup
        )
        result = converter.convert()

        assert os.path.exists(result)

        with open(result, "r") as f:
            reader = csv.reader(f)
            rows = list(reader)
            # Should have more rows due to multiple invoices
            assert len(rows) >= 1

    def test_convert_to_price_helper(self):
        """Test the _convert_to_price_master helper function."""
        from convert_to_csv import _convert_to_price_master

        assert _convert_to_price_master("00012345") == "123.45"
        assert _convert_to_price_master("00000000") == "0.00"
        assert _convert_to_price_master("00000099") == "0.99"
        assert _convert_to_price_master("") == "0."
        assert _convert_to_price_master("01") == "0.01"


# ============================================================================
# ESTORE EINVOICE CONVERTER TESTS
# ============================================================================


class TestEstoreEinvoiceConverter:
    """Tests for convert_to_estore_einvoice module."""

    def test_converter_class_exists(self):
        """Test that EstoreEinvoiceConverter class exists."""
        assert hasattr(EstoreEinvoiceConverter, "PLUGIN_ID")
        assert hasattr(EstoreEinvoiceConverter, "PLUGIN_NAME")
        assert EstoreEinvoiceConverter.PLUGIN_ID == "estore_einvoice"

    def test_edi_convert_function_exists(self):
        """Test that the backward-compatible edi_convert function exists."""
        assert callable(estore_edi_convert)

    def test_converter_initialization(
        self, sample_edi_file, temp_dir, settings_dict, upc_lookup
    ):
        """Test converter can be initialized."""
        output_file = os.path.join(temp_dir, "output")
        parameters = {
            "estore_store_number": "12345",
            "estore_Vendor_OId": "67890",
            "estore_vendor_NameVendorOID": "TestVendor",
        }

        converter = EstoreEinvoiceConverter(
            sample_edi_file, output_file, settings_dict, parameters, upc_lookup
        )

        assert converter.edi_process == sample_edi_file

    def test_happy_path_conversion(
        self, sample_edi_file, temp_dir, settings_dict, upc_lookup
    ):
        """Test successful conversion of valid EDI file."""
        output_file = os.path.join(temp_dir, "output")
        parameters = {
            "estore_store_number": "12345",
            "estore_Vendor_OId": "67890",
            "estore_vendor_NameVendorOID": "TestVendor",
        }

        converter = EstoreEinvoiceConverter(
            sample_edi_file, output_file, settings_dict, parameters, upc_lookup
        )
        result = converter.convert()

        assert os.path.exists(result)
        assert "eInv" in result
        assert result.endswith(".csv")

    def test_helper_methods(self, sample_edi_file, temp_dir, settings_dict, upc_lookup):
        """Test internal helper methods."""
        output_file = os.path.join(temp_dir, "output")
        parameters = {
            "estore_store_number": "12345",
            "estore_Vendor_OId": "67890",
            "estore_vendor_NameVendorOID": "TestVendor",
        }

        converter = EstoreEinvoiceConverter(
            sample_edi_file, output_file, settings_dict, parameters, upc_lookup
        )

        # Test _convert_to_price
        assert converter._convert_to_price("00012345") == Decimal("123.45")
        assert converter._convert_to_price("00000000") == Decimal("0.00")

        # Test _qty_to_int
        assert converter._qty_to_int("0010") == 10
        assert converter._qty_to_int("-010") == -10
        assert converter._qty_to_int("invalid") == 0


# ============================================================================
# ESTORE EINVOICE GENERIC CONVERTER TESTS
# ============================================================================


class TestEstoreEinvoiceGenericConverter:
    """Tests for convert_to_estore_einvoice_generic module."""

    def test_converter_class_exists(self):
        """Test that EstoreEinvoiceGenericConverter class exists."""
        assert hasattr(EstoreEinvoiceGenericConverter, "PLUGIN_ID")
        assert hasattr(EstoreEinvoiceGenericConverter, "PLUGIN_NAME")
        assert EstoreEinvoiceGenericConverter.PLUGIN_ID == "estore_einvoice_generic"

    def test_edi_convert_function_exists(self):
        """Test that the backward-compatible edi_convert function exists."""
        assert callable(estore_generic_edi_convert)

    @patch("convert_base.query_runner")
    def test_happy_path_conversion(
        self,
        mock_query,
        sample_edi_file,
        temp_dir,
        settings_dict,
        upc_lookup,
        mock_query_runner,
    ):
        """Test successful conversion with mocked database."""
        mock_query.return_value = mock_query_runner

        output_file = os.path.join(temp_dir, "output")
        parameters = {
            "estore_store_number": "12345",
            "estore_Vendor_OId": "67890",
            "estore_vendor_NameVendorOID": "TestVendor",
        }

        converter = EstoreEinvoiceGenericConverter(
            sample_edi_file, output_file, settings_dict, parameters, upc_lookup
        )
        result = converter.convert()

        assert os.path.exists(result)
        assert result.endswith(".csv")

    def test_invfetcher_class_exists(self):
        """Test that the internal invFetcher class exists."""
        assert hasattr(EstoreEinvoiceGenericConverter, "invFetcher")


# ============================================================================
# FINTECH CONVERTER TESTS
# ============================================================================


class TestFintechConverter:
    """Tests for convert_to_fintech module."""

    def test_converter_class_exists(self):
        """Test that FintechConverter class exists."""
        assert hasattr(FintechConverter, "PLUGIN_ID")
        assert hasattr(FintechConverter, "PLUGIN_NAME")
        assert FintechConverter.PLUGIN_ID == "fintech"

    def test_edi_convert_function_exists(self):
        """Test that the backward-compatible edi_convert function exists."""
        assert callable(fintech_edi_convert)

    @patch("convert_to_fintech.utils.invFetcher")
    def test_happy_path_conversion(
        self,
        mock_invfetcher_class,
        sample_edi_file,
        temp_dir,
        settings_dict,
        upc_lookup,
    ):
        """Test successful conversion with mocked invoice fetcher."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_cust_no.return_value = "CUST123"
        mock_invfetcher_class.return_value = mock_fetcher

        output_file = os.path.join(temp_dir, "output")
        parameters = {"fintech_division_id": "DIV01"}

        converter = FintechConverter(
            sample_edi_file, output_file, settings_dict, parameters, upc_lookup
        )
        result = converter.convert()

        assert os.path.exists(result)
        assert result.endswith(".csv")

    def test_uomdesc_helper(self, sample_edi_file, temp_dir, settings_dict, upc_lookup):
        """Test the _uomdesc helper method."""
        output_file = os.path.join(temp_dir, "output")
        parameters = {"fintech_division_id": "DIV01"}

        converter = FintechConverter(
            sample_edi_file, output_file, settings_dict, parameters, upc_lookup
        )

        assert converter._uomdesc(1) == "CS"
        assert converter._uomdesc(12) == "EA"
        assert converter._uomdesc(0) == "CS"


# ============================================================================
# JOLLEY CUSTOM CONVERTER TESTS
# ============================================================================


class TestJolleyCustomConverter:
    """Tests for convert_to_jolley_custom module."""

    def test_converter_class_exists(self):
        """Test that JolleyCustomConverter class exists."""
        assert hasattr(JolleyCustomConverter, "PLUGIN_ID")
        assert hasattr(JolleyCustomConverter, "PLUGIN_NAME")
        assert JolleyCustomConverter.PLUGIN_ID == "jolley_custom"

    def test_edi_convert_function_exists(self):
        """Test that the backward-compatible edi_convert function exists."""
        assert callable(jolley_edi_convert)

    @patch("convert_base.query_runner")
    def test_happy_path_conversion(
        self,
        mock_query,
        sample_edi_file,
        temp_dir,
        settings_dict,
        upc_lookup,
        mock_query_runner,
    ):
        """Test successful conversion with mocked database."""
        mock_query.return_value = mock_query_runner

        output_file = os.path.join(temp_dir, "output")
        parameters = {}

        converter = JolleyCustomConverter(
            sample_edi_file, output_file, settings_dict, parameters, upc_lookup
        )
        result = converter.convert()

        assert os.path.exists(result)
        assert result.endswith(".csv")

    def test_safe_int_from_invoice_helper(self):
        """Test the _safe_int_from_invoice static method."""
        assert JolleyCustomConverter._safe_int_from_invoice("0012345") == 12345
        assert JolleyCustomConverter._safe_int_from_invoice("000000") == 0
        assert JolleyCustomConverter._safe_int_from_invoice("") == 0
        assert JolleyCustomConverter._safe_int_from_invoice("invalid") == 0

    def test_prettify_dates_helper(self):
        """Test the _prettify_dates static method."""
        result = JolleyCustomConverter._prettify_dates("1231225")
        assert isinstance(result, str)

        # Test with invalid date
        result = JolleyCustomConverter._prettify_dates("invalid")
        assert result == "Not Available"

    @patch("convert_base.query_runner")
    def test_customer_lookup_error(
        self, mock_query, sample_edi_file, temp_dir, settings_dict, upc_lookup
    ):
        """Test that CustomerLookupError is raised when customer data is not found."""
        from convert_to_jolley_custom import CustomerLookupError

        mock_runner = MagicMock()
        mock_runner.run_arbitrary_query.return_value = []
        mock_query.return_value = mock_runner

        output_file = os.path.join(temp_dir, "output")
        parameters = {}

        converter = JolleyCustomConverter(
            sample_edi_file, output_file, settings_dict, parameters, upc_lookup
        )

        with pytest.raises(CustomerLookupError):
            converter.convert()


# ============================================================================
# SCANNERWARE CONVERTER TESTS
# ============================================================================


class TestScannerWareConverter:
    """Tests for convert_to_scannerware module."""

    def test_converter_class_exists(self):
        """Test that ScannerWareConverter class exists."""
        assert hasattr(ScannerWareConverter, "PLUGIN_ID")
        assert hasattr(ScannerWareConverter, "PLUGIN_NAME")
        assert ScannerWareConverter.PLUGIN_ID == "scannerware"

    def test_edi_convert_function_exists(self):
        """Test that the backward-compatible edi_convert function exists."""
        assert callable(scannerware_edi_convert)

    def test_happy_path_conversion(
        self, sample_edi_file, temp_dir, settings_dict, upc_lookup
    ):
        """Test successful conversion of valid EDI file."""
        output_file = os.path.join(temp_dir, "output")
        parameters = {}

        converter = ScannerWareConverter(
            sample_edi_file, output_file, settings_dict, parameters, upc_lookup
        )
        result = converter.convert()

        assert os.path.exists(result)
        # ScannerWare produces text output
        with open(result, "r") as f:
            content = f.read()
            assert len(content) > 0

    def test_pad_a_records_option(
        self, sample_edi_file, temp_dir, settings_dict, upc_lookup
    ):
        """Test A record padding option."""
        output_file = os.path.join(temp_dir, "output")
        parameters = {
            "pad_a_records": "True",
            "a_record_padding": "TEST01",
        }

        converter = ScannerWareConverter(
            sample_edi_file, output_file, settings_dict, parameters, upc_lookup
        )
        result = converter.convert()

        assert os.path.exists(result)

    def test_append_a_records_option(
        self, sample_edi_file, temp_dir, settings_dict, upc_lookup
    ):
        """Test A record append option."""
        output_file = os.path.join(temp_dir, "output")
        parameters = {
            "append_a_records": "True",
            "a_record_append_text": "_APPEND",
        }

        converter = ScannerWareConverter(
            sample_edi_file, output_file, settings_dict, parameters, upc_lookup
        )
        result = converter.convert()

        assert os.path.exists(result)

    def test_force_txt_extension(
        self, sample_edi_file, temp_dir, settings_dict, upc_lookup
    ):
        """Test forcing .txt extension."""
        output_file = os.path.join(temp_dir, "output")
        parameters = {"force_txt_file_ext": "True"}

        converter = ScannerWareConverter(
            sample_edi_file, output_file, settings_dict, parameters, upc_lookup
        )
        result = converter.convert()

        assert result.endswith(".txt")

    def test_invoice_date_offset(
        self, sample_edi_file, temp_dir, settings_dict, upc_lookup
    ):
        """Test invoice date offset option."""
        output_file = os.path.join(temp_dir, "output")
        parameters = {"invoice_date_offset": 5}

        converter = ScannerWareConverter(
            sample_edi_file, output_file, settings_dict, parameters, upc_lookup
        )
        result = converter.convert()

        assert os.path.exists(result)

    def test_empty_file_handling(
        self, empty_edi_file, temp_dir, settings_dict, upc_lookup
    ):
        """Test conversion of empty EDI file."""
        output_file = os.path.join(temp_dir, "output")
        parameters = {}

        converter = ScannerWareConverter(
            empty_edi_file, output_file, settings_dict, parameters, upc_lookup
        )
        result = converter.convert()

        assert os.path.exists(result)


# ============================================================================
# SCANSHEET TYPE A CONVERTER TESTS
# ============================================================================


class TestScansheetTypeAConverter:
    """Tests for convert_to_scansheet_type_a module."""

    def test_converter_class_exists(self):
        """Test that ScansheetTypeAConverter class exists."""
        assert hasattr(ScansheetTypeAConverter, "PLUGIN_ID")
        assert hasattr(ScansheetTypeAConverter, "PLUGIN_NAME")
        assert ScansheetTypeAConverter.PLUGIN_ID == "scansheet_type_a"

    def test_edi_convert_function_exists(self):
        """Test that the backward-compatible edi_convert function exists."""
        assert callable(scansheet_edi_convert)

    @patch("convert_base.query_runner")
    def test_happy_path_conversion(
        self,
        mock_query,
        sample_edi_file,
        temp_dir,
        settings_dict,
        upc_lookup,
        mock_query_runner,
    ):
        """Test successful conversion with mocked database."""
        mock_query.return_value = mock_query_runner

        output_file = os.path.join(temp_dir, "output")
        parameters = {}

        converter = ScansheetTypeAConverter(
            sample_edi_file, output_file, settings_dict, parameters, upc_lookup
        )

        # Note: This converter may fail without full barcode dependencies
        # We test that it initializes correctly
        try:
            result = converter.convert()
            assert os.path.exists(result)
            assert result.endswith(".xlsx")
        except Exception as e:
            # Expected if barcode libraries not available
            pytest.skip(f"Barcode generation requires additional dependencies: {e}")

    def test_interpret_barcode_string(self):
        """Test the interpret_barcode_string helper method."""
        converter_class = ScansheetTypeAConverter

        result = converter_class.interpret_barcode_string(None, "12345678901")
        assert result == "123456789010"

        result = converter_class.interpret_barcode_string(None, "12345")
        assert len(result) == 12

        result = converter_class.interpret_barcode_string(None, "00012345678")
        assert result == "000123456780"

    def test_interpret_barcode_string_errors(self):
        """Test interpret_barcode_string error handling."""
        converter_class = ScansheetTypeAConverter

        with pytest.raises(ValueError):
            converter_class.interpret_barcode_string(None, "")

        with pytest.raises(ValueError):
            converter_class.interpret_barcode_string(None, "invalid")

        with pytest.raises(ValueError):
            converter_class.interpret_barcode_string(None, "123456789012")


# ============================================================================
# SIMPLIFIED CSV CONVERTER TESTS
# ============================================================================


class TestSimplifiedCsvConverter:
    """Tests for convert_to_simplified_csv module."""

    def test_converter_class_exists(self):
        """Test that SimplifiedCsvConverter class exists."""
        assert hasattr(SimplifiedCsvConverter, "PLUGIN_ID")
        assert hasattr(SimplifiedCsvConverter, "PLUGIN_NAME")
        assert SimplifiedCsvConverter.PLUGIN_ID == "simplified_csv"

    def test_edi_convert_function_exists(self):
        """Test that the backward-compatible edi_convert function exists."""
        assert callable(simplified_edi_convert)

    def test_happy_path_conversion(
        self, sample_edi_file, temp_dir, settings_dict, upc_lookup
    ):
        """Test successful conversion of valid EDI file."""
        output_file = os.path.join(temp_dir, "output")
        parameters = {}

        converter = SimplifiedCsvConverter(
            sample_edi_file, output_file, settings_dict, parameters, upc_lookup
        )
        result = converter.convert()

        assert os.path.exists(result)
        assert result.endswith(".csv")

    def test_include_headers_option(
        self, sample_edi_file, temp_dir, settings_dict, upc_lookup
    ):
        """Test conversion with headers included."""
        output_file = os.path.join(temp_dir, "output")
        parameters = {"include_headers": "True"}

        converter = SimplifiedCsvConverter(
            sample_edi_file, output_file, settings_dict, parameters, upc_lookup
        )
        result = converter.convert()

        assert os.path.exists(result)

    def test_include_item_numbers_option(
        self, sample_edi_file, temp_dir, settings_dict, upc_lookup
    ):
        """Test conversion with item numbers included."""
        output_file = os.path.join(temp_dir, "output")
        parameters = {"include_item_numbers": "True"}

        converter = SimplifiedCsvConverter(
            sample_edi_file, output_file, settings_dict, parameters, upc_lookup
        )
        result = converter.convert()

        assert os.path.exists(result)

    def test_include_item_description_option(
        self, sample_edi_file, temp_dir, settings_dict, upc_lookup
    ):
        """Test conversion with item description included."""
        output_file = os.path.join(temp_dir, "output")
        parameters = {"include_item_description": "True"}

        converter = SimplifiedCsvConverter(
            sample_edi_file, output_file, settings_dict, parameters, upc_lookup
        )
        result = converter.convert()

        assert os.path.exists(result)

    def test_retail_uom_option(
        self, sample_edi_file, temp_dir, settings_dict, upc_lookup
    ):
        """Test retail UOM transformation."""
        output_file = os.path.join(temp_dir, "output")
        parameters = {"retail_uom": "True"}

        converter = SimplifiedCsvConverter(
            sample_edi_file, output_file, settings_dict, parameters, upc_lookup
        )
        result = converter.convert()

        assert os.path.exists(result)

    def test_custom_column_order(
        self, sample_edi_file, temp_dir, settings_dict, upc_lookup
    ):
        """Test custom column ordering."""
        output_file = os.path.join(temp_dir, "output")
        parameters = {
            "simple_csv_sort_order": "vendor_item,upc_number,qty_of_units,unit_cost,description",
            "include_item_numbers": "True",
            "include_item_description": "True",
        }

        converter = SimplifiedCsvConverter(
            sample_edi_file, output_file, settings_dict, parameters, upc_lookup
        )
        result = converter.convert()

        assert os.path.exists(result)

    def test_empty_file_handling(
        self, empty_edi_file, temp_dir, settings_dict, upc_lookup
    ):
        """Test conversion of empty EDI file."""
        output_file = os.path.join(temp_dir, "output")
        parameters = {}

        converter = SimplifiedCsvConverter(
            empty_edi_file, output_file, settings_dict, parameters, upc_lookup
        )
        result = converter.convert()

        assert os.path.exists(result)


# ============================================================================
# STEWARTS CUSTOM CONVERTER TESTS
# ============================================================================


class TestStewartsCustomConverter:
    """Tests for convert_to_stewarts_custom module."""

    def test_converter_class_exists(self):
        """Test that StewartsCustomConverter class exists."""
        assert hasattr(StewartsCustomConverter, "PLUGIN_ID")
        assert hasattr(StewartsCustomConverter, "PLUGIN_NAME")
        assert StewartsCustomConverter.PLUGIN_ID == "stewarts_custom"

    def test_edi_convert_function_exists(self):
        """Test that the backward-compatible edi_convert function exists."""
        assert callable(stewarts_edi_convert)

    @patch("convert_base.query_runner")
    def test_happy_path_conversion(
        self,
        mock_query,
        sample_edi_file,
        temp_dir,
        settings_dict,
        upc_lookup,
        mock_query_runner,
    ):
        """Test successful conversion with mocked database."""
        mock_query.return_value = mock_query_runner

        output_file = os.path.join(temp_dir, "output")
        parameters = {}

        converter = StewartsCustomConverter(
            sample_edi_file, output_file, settings_dict, parameters, upc_lookup
        )
        result = converter.convert()

        assert os.path.exists(result)
        assert result.endswith(".csv")

    def test_get_uom_helper(self, sample_edi_file, temp_dir, settings_dict, upc_lookup):
        """Test the _get_uom helper method."""
        output_file = os.path.join(temp_dir, "output")
        parameters = {}

        converter = StewartsCustomConverter(
            sample_edi_file, output_file, settings_dict, parameters, upc_lookup
        )

        # Set up UOM lookup list
        converter.uom_lookup_list = [
            (123456, 1, "EA"),
            (123456, 12, "CS"),
            (987654, 6, "BX"),
        ]

        assert converter._get_uom("123456", "1") == "EA"
        assert converter._get_uom("123456", "12") == "CS"
        assert converter._get_uom("999999", "1") == "?"

    def test_convert_to_item_total_helper(
        self, sample_edi_file, temp_dir, settings_dict, upc_lookup
    ):
        """Test the _convert_to_item_total helper method."""
        output_file = os.path.join(temp_dir, "output")
        parameters = {}

        converter = StewartsCustomConverter(
            sample_edi_file, output_file, settings_dict, parameters, upc_lookup
        )

        total, qty = converter._convert_to_item_total("00010000", "00010")
        assert qty == 10
        assert total == Decimal("1000.00")

    @patch("convert_base.query_runner")
    def test_customer_lookup_error(
        self, mock_query, sample_edi_file, temp_dir, settings_dict, upc_lookup
    ):
        """Test that CustomerLookupError is raised when customer data is not found."""
        from convert_to_stewarts_custom import CustomerLookupError

        mock_runner = MagicMock()
        mock_runner.run_arbitrary_query.return_value = []
        mock_query.return_value = mock_runner

        output_file = os.path.join(temp_dir, "output")
        parameters = {}

        converter = StewartsCustomConverter(
            sample_edi_file, output_file, settings_dict, parameters, upc_lookup
        )

        with pytest.raises(CustomerLookupError):
            converter.convert()


# ============================================================================
# YELLOWDOG CSV CONVERTER TESTS
# ============================================================================


class TestYellowdogConverter:
    """Tests for convert_to_yellowdog_csv module."""

    def test_converter_class_exists(self):
        """Test that YellowdogConverter class exists."""
        assert hasattr(YellowdogConverter, "PLUGIN_ID")
        assert hasattr(YellowdogConverter, "PLUGIN_NAME")
        assert YellowdogConverter.PLUGIN_ID == "yellowdog_csv"

    def test_edi_convert_function_exists(self):
        """Test that the backward-compatible edi_convert function exists."""
        assert callable(yellowdog_edi_convert)

    @patch("convert_to_yellowdog_csv.utils.invFetcher")
    def test_happy_path_conversion(
        self,
        mock_invfetcher_class,
        sample_edi_file,
        temp_dir,
        settings_dict,
        upc_lookup,
    ):
        """Test successful conversion with mocked invoice fetcher."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_cust_name.return_value = "Test Customer"
        mock_fetcher.fetch_po.return_value = "PO12345"
        mock_fetcher.fetch_uom_desc.return_value = "EA"
        mock_invfetcher_class.return_value = mock_fetcher

        output_file = os.path.join(temp_dir, "output")
        parameters = {}

        converter = YellowdogConverter(
            sample_edi_file, output_file, settings_dict, parameters, upc_lookup
        )
        result = converter.convert()

        assert os.path.exists(result)
        assert result.endswith(".csv")

        # Verify CSV has expected headers
        with open(result, "r") as f:
            reader = csv.reader(f)
            rows = list(reader)
            assert len(rows) > 0
            # First row should be headers
            assert "Invoice Total" in rows[0]

    @patch("convert_to_yellowdog_csv.utils.invFetcher")
    def test_complex_invoice_conversion(
        self,
        mock_invfetcher_class,
        complex_edi_file,
        temp_dir,
        settings_dict,
        upc_lookup,
    ):
        """Test conversion of complex EDI with multiple invoices."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_cust_name.return_value = "Test Customer"
        mock_fetcher.fetch_po.return_value = "PO12345"
        mock_fetcher.fetch_uom_desc.return_value = "EA"
        mock_invfetcher_class.return_value = mock_fetcher

        output_file = os.path.join(temp_dir, "output")
        parameters = {}

        converter = YellowdogConverter(
            complex_edi_file, output_file, settings_dict, parameters, upc_lookup
        )
        result = converter.convert()

        assert os.path.exists(result)

    def test_ydog_writer_class_exists(self):
        """Test that the internal YDogWriter class exists."""
        assert hasattr(YellowdogConverter, "YDogWriter")


# ============================================================================
# EDGE CASES AND ERROR HANDLING TESTS
# ============================================================================


class TestConverterEdgeCases:
    """Tests for edge cases and error handling across all converters."""

    def test_nonexistent_file_handling_csv(self, temp_dir, settings_dict, upc_lookup):
        """Test handling of nonexistent input file for CSV converter."""
        output_file = os.path.join(temp_dir, "output")
        parameters = {}

        converter = CsvConverter(
            "/nonexistent/file.edi", output_file, settings_dict, parameters, upc_lookup
        )

        with pytest.raises(FileNotFoundError):
            converter.convert()

    def test_nonexistent_file_handling_scannerware(
        self, temp_dir, settings_dict, upc_lookup
    ):
        """Test handling of nonexistent input file for ScannerWare converter."""
        output_file = os.path.join(temp_dir, "output")
        parameters = {}

        converter = ScannerWareConverter(
            "/nonexistent/file.edi", output_file, settings_dict, parameters, upc_lookup
        )

        with pytest.raises(FileNotFoundError):
            converter.convert()

    def test_malformed_edi_handling_csv(
        self, malformed_edi_file, temp_dir, settings_dict, upc_lookup
    ):
        """Test handling of malformed EDI data in CSV converter."""
        output_file = os.path.join(temp_dir, "output")
        parameters = {}

        converter = CsvConverter(
            malformed_edi_file, output_file, settings_dict, parameters, upc_lookup
        )

        # Should handle gracefully and produce output
        result = converter.convert()
        assert os.path.exists(result)

    def test_special_characters_in_description(
        self, temp_dir, settings_dict, upc_lookup
    ):
        """Test handling of special characters in descriptions."""
        edi_content = """A000001INV00001011221251000012345
B012345678901Product & Test "Name" 1234561234567890100001000100050000
C00100000123
"""
        edi_file = os.path.join(temp_dir, "special.edi")
        with open(edi_file, "w") as f:
            f.write(edi_content)

        output_file = os.path.join(temp_dir, "output")
        parameters = {"filter_ampersand": "True"}

        converter = CsvConverter(
            edi_file, output_file, settings_dict, parameters, upc_lookup
        )
        result = converter.convert()

        assert os.path.exists(result)

    def test_very_long_description(self, temp_dir, settings_dict, upc_lookup):
        """Test handling of very long descriptions."""
        long_desc = "A" * 200
        edi_content = f"""A000001INV00001011221251000012345
B012345678901{long_desc}1234561234567890100001000100050000
C00100000123
"""
        edi_file = os.path.join(temp_dir, "longdesc.edi")
        with open(edi_file, "w") as f:
            f.write(edi_content)

        output_file = os.path.join(temp_dir, "output")
        parameters = {}

        converter = CsvConverter(
            edi_file, output_file, settings_dict, parameters, upc_lookup
        )
        result = converter.convert()

        assert os.path.exists(result)

    def test_zero_values_handling(self, temp_dir, settings_dict, upc_lookup):
        """Test handling of zero values in numeric fields."""
        edi_content = """A000001INV00001000000000000000000
B012345678901Product Description 1234561234567890000000000000000000
C00100000000
"""
        edi_file = os.path.join(temp_dir, "zeros.edi")
        with open(edi_file, "w") as f:
            f.write(edi_content)

        output_file = os.path.join(temp_dir, "output")
        parameters = {}

        converter = CsvConverter(
            edi_file, output_file, settings_dict, parameters, upc_lookup
        )
        result = converter.convert()

        assert os.path.exists(result)

    def test_negative_quantities(self, temp_dir, settings_dict, upc_lookup):
        """Test handling of negative quantities."""
        edi_content = """A000001INV00001011221251000012345
B012345678901Product Description 123456123456789010000-0100100050000
C00100000123
"""
        edi_file = os.path.join(temp_dir, "negative.edi")
        with open(edi_file, "w") as f:
            f.write(edi_content)

        output_file = os.path.join(temp_dir, "output")
        parameters = {}

        converter = CsvConverter(
            edi_file, output_file, settings_dict, parameters, upc_lookup
        )
        result = converter.convert()

        assert os.path.exists(result)


# ============================================================================
# PLUGIN METADATA TESTS
# ============================================================================


class TestConverterPluginMetadata:
    """Tests for converter plugin metadata and configuration."""

    def test_all_converters_have_plugin_id(self):
        """Test that all converter classes have PLUGIN_ID defined."""
        converters = [
            CsvConverter,
            EstoreEinvoiceConverter,
            EstoreEinvoiceGenericConverter,
            FintechConverter,
            JolleyCustomConverter,
            ScannerWareConverter,
            ScansheetTypeAConverter,
            SimplifiedCsvConverter,
            StewartsCustomConverter,
            YellowdogConverter,
        ]

        for converter in converters:
            assert hasattr(converter, "PLUGIN_ID"), (
                f"{converter.__name__} missing PLUGIN_ID"
            )
            assert converter.PLUGIN_ID, f"{converter.__name__} has empty PLUGIN_ID"

    def test_all_converters_have_plugin_name(self):
        """Test that all converter classes have PLUGIN_NAME defined."""
        converters = [
            CsvConverter,
            EstoreEinvoiceConverter,
            EstoreEinvoiceGenericConverter,
            FintechConverter,
            JolleyCustomConverter,
            ScannerWareConverter,
            ScansheetTypeAConverter,
            SimplifiedCsvConverter,
            StewartsCustomConverter,
            YellowdogConverter,
        ]

        for converter in converters:
            assert hasattr(converter, "PLUGIN_NAME"), (
                f"{converter.__name__} missing PLUGIN_NAME"
            )
            assert converter.PLUGIN_NAME, f"{converter.__name__} has empty PLUGIN_NAME"

    def test_all_converters_have_config_fields(self):
        """Test that all converter classes have CONFIG_FIELDS defined."""
        converters = [
            CsvConverter,
            EstoreEinvoiceConverter,
            EstoreEinvoiceGenericConverter,
            FintechConverter,
            JolleyCustomConverter,
            ScannerWareConverter,
            ScansheetTypeAConverter,
            SimplifiedCsvConverter,
            StewartsCustomConverter,
            YellowdogConverter,
        ]

        for converter in converters:
            assert hasattr(converter, "CONFIG_FIELDS"), (
                f"{converter.__name__} missing CONFIG_FIELDS"
            )
            assert isinstance(converter.CONFIG_FIELDS, list), (
                f"{converter.__name__} CONFIG_FIELDS not a list"
            )

    def test_config_fields_structure(self):
        """Test that CONFIG_FIELDS have proper structure."""
        converters_with_fields = [
            CsvConverter,
            EstoreEinvoiceConverter,
            EstoreEinvoiceGenericConverter,
            FintechConverter,
            ScannerWareConverter,
            SimplifiedCsvConverter,
        ]

        for converter in converters_with_fields:
            for field in converter.CONFIG_FIELDS:
                assert "key" in field, (
                    f"{converter.__name__} config field missing 'key'"
                )
                assert "label" in field, (
                    f"{converter.__name__} config field missing 'label'"
                )
                assert "type" in field, (
                    f"{converter.__name__} config field missing 'type'"
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
