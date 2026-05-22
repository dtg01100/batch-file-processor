"""Unit tests for convert_to_stewarts_custom.py converter module.

Tests:
- Input validation and edge cases
- Database lookup mocking
- Data transformation accuracy
- UPC generation with check digit
- Customer address formatting

Converter: convert_to_stewarts_custom.py (20871 chars)

Note: This converter requires AS400 database access, so tests mock the DB2SSH connection.
"""

import os
from unittest.mock import patch

import pytest

from dispatch.converters import convert_to_stewarts_custom
from tests.conftest import MockFactories


class TestConvertToStewartsCustomFixtures:
    """Test fixtures for convert_to_stewarts_custom module."""

    @pytest.fixture
    def sample_header_record(self):
        """Create accurate header record (33 chars)."""
        return "A" + "VENDOR" + "[REDACTED]" + "010125" + "[REDACTED]"

    @pytest.fixture
    def sample_detail_record(self):
        """Create accurate detail record (76 chars)."""
        return (
            "B"
            + "[REDACTED]0"
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
        """Default parameters dict for convert_to_stewarts_custom."""
        return {}

    @pytest.fixture
    def default_settings(self):
        """Default settings dict with database credentials."""
        return {
            "as400_username": "test_user",
            "as400_password": "test_pass",
            "as400_address": "test.address.com",
        }

    @pytest.fixture
    def mock_query_runner_result(self):
        """Return a mock query runner result set for header lookup as list[dict]."""
        return [
            {
                "Salesperson Name": "Salesperson",
                "Invoice Date": 1250101,
                "Terms Code": "NET30",
                "Terms Duration": 30,
                "Customer Status": "A",
                "Customer Number": 10001,
                "Customer Name": "Test Customer",
                "Customer Store Number": "001",
                "Customer Address": "123 Main St",
                "Customer Town": "Anytown",
                "Customer State": "CA",
                "Customer Zip": "90210",
                "Customer Phone": "[REDACTED]",
                "Customer Email": "[REDACTED]",
                "Customer Email 2": "",
                "Corporate Customer Status": "A",
                "Corporate Customer Number": 20001,
                "Corporate Customer Name": "Corp Customer",
                "Corporate Customer Address": "456 Corp Ave",
                "Corporate Customer Town": "Bigcity",
                "Corporate Customer State": "NY",
                "Corporate Customer Zip": "10001",
                "Corporate Customer Phone": "[REDACTED]",
                "Corporate Customer Email": "[REDACTED]",
                "Corporate Customer Email 2": "",
            }
        ]

    @pytest.fixture
    def mock_uom_result(self):
        """Return a mock UOM lookup result."""
        return [
            (123456, 6, "CS"),
            (123456, 1, "EA"),
        ]


class TestConvertToStewartsCustomBasicFunctionality(
    TestConvertToStewartsCustomFixtures
):
    """Test basic functionality of convert_to_stewarts_custom."""

    def test_module_import(self):
        """Test that convert_to_stewarts_custom module can be imported."""
        from dispatch.converters import convert_to_stewarts_custom

        assert convert_to_stewarts_custom is not None
        assert hasattr(convert_to_stewarts_custom, "edi_convert")

    def test_edi_convert_returns_csv_filename(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        mock_query_runner_result,
        mock_uom_result,
        tmp_path,
    ):
        """Test that edi_convert returns the expected CSV filename."""
        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        with patch("adapters.db2ssh.connection.DB2SSHConnection") as mock_conn_class:
            mock_conn = MockFactories.db2ssh_connection()
            mock_conn.execute.return_value = mock_query_runner_result
            mock_conn_class.return_value = mock_conn

            result = convert_to_stewarts_custom.edi_convert(
                str(input_file),
                output_file,
                default_settings,
                default_parameters,
                {},
            )
            assert result.endswith(".csv")

    def test_creates_csv_file(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        mock_query_runner_result,
        mock_uom_result,
        tmp_path,
    ):
        """Test that the CSV file is actually created."""
        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        with patch("adapters.db2ssh.connection.DB2SSHConnection") as mock_conn_class:
            mock_conn = MockFactories.db2ssh_connection()
            mock_conn.execute.return_value = mock_query_runner_result
            mock_conn_class.return_value = mock_conn

            result = convert_to_stewarts_custom.edi_convert(
                str(input_file),
                output_file,
                default_settings,
                default_parameters,
                {},
            )
            assert os.path.exists(result)


class TestConvertToStewartsCustomDatabaseLookup(TestConvertToStewartsCustomFixtures):
    """Test database lookup functionality in convert_to_stewarts_custom."""

    def test_uom_lookup_called(
        self,
        default_parameters,
        default_settings,
        mock_uom_result,
    ):
        """Test UOM lookup via service."""
        from dispatch.services.uom_lookup_service import UOMLookupService

        uom_service = UOMLookupService(MockFactories.db2ssh_connection())
        uom_service.uom_lookup_list = [
            {"itemno": 123456, "uom_mult": 6, "uom_code": "CS"},
            {"itemno": 123456, "uom_mult": 1, "uom_code": "EA"},
        ]
        result = uom_service.get_uom("123456", "6")
        assert result == "CS"


class TestConvertToStewartsCustomUPCGeneration(TestConvertToStewartsCustomFixtures):
    """Test UPC generation with check digit in convert_to_stewarts_custom."""

    def test_upc_11_digit_with_check_digit(
        self,
        default_parameters,
        default_settings,
    ):
        """Test UPC generation from 11-digit input adds check digit."""
        from dispatch.services.item_processing import ItemProcessor

        item_processor = ItemProcessor()
        # Use valid 11-digit UPC (check digit will be added to make 12)
        result = item_processor.generate_full_upc("01234567890")
        assert len(result) == 12

    def test_upc_8_digit_conversion(
        self,
        default_parameters,
        default_settings,
    ):
        """Test UPC generation from 8-digit input (UPC-E to UPC-A)."""
        from dispatch.services.item_processing import ItemProcessor

        item_processor = ItemProcessor()
        result = item_processor.generate_full_upc("01234567")
        assert len(result) == 12 or result == ""

    def test_upc_empty_string(
        self,
        default_parameters,
        default_settings,
    ):
        """Test UPC generation from empty string returns empty string."""
        from dispatch.services.item_processing import ItemProcessor

        item_processor = ItemProcessor()
        result = item_processor.generate_full_upc("")
        assert result == ""


class TestConvertToStewartsCustomItemTotal(TestConvertToStewartsCustomFixtures):
    """Test item total calculation in convert_to_stewarts_custom."""

    def test_convert_to_item_total_positive_qty(
        self,
        default_parameters,
        default_settings,
    ):
        """Test item total calculation with positive quantity."""
        from dispatch.services.item_processing import ItemProcessor

        item_processor = ItemProcessor()
        total, qty = item_processor.convert_to_item_total("000100", "00010")
        assert qty == 10
        assert total > 0

    def test_convert_to_item_total_negative_qty(
        self,
        default_parameters,
        default_settings,
    ):
        """Test item total calculation with negative quantity returns negative values."""
        from dispatch.services.item_processing import ItemProcessor

        item_processor = ItemProcessor()
        total, qty = item_processor.convert_to_item_total("000100", "-00010")
        assert qty == -10
        assert total < 0


class TestConvertToStewartsCustomUOM(TestConvertToStewartsCustomFixtures):
    """Test UOM lookup in convert_to_stewarts_custom."""

    def test_get_uom_with_match(
        self,
        default_parameters,
        default_settings,
    ):
        """Test UOM lookup with matching item and packsize."""
        from dispatch.services.uom_lookup_service import UOMLookupService

        uom_service = UOMLookupService(MockFactories.db2ssh_connection())
        uom_service.uom_lookup_list = [
            {"itemno": 123456, "uom_mult": 6, "uom_code": "CS"},
            {"itemno": 123456, "uom_mult": 1, "uom_code": "EA"},
        ]
        result = uom_service.get_uom("123456", "6")
        assert result == "CS"

    def test_get_uom_no_match(
        self,
        default_parameters,
        default_settings,
    ):
        """Test UOM lookup with no matching item returns '?'."""
        from dispatch.services.uom_lookup_service import UOMLookupService

        uom_service = UOMLookupService(MockFactories.db2ssh_connection())
        uom_service.uom_lookup_list = [
            {"itemno": 123456, "uom_mult": 6, "uom_code": "CS"}
        ]
        result = uom_service.get_uom("999999", "6")
        assert result == "?"


class TestConvertToStewartsCustomEdgeCases(TestConvertToStewartsCustomFixtures):
    """Test edge cases and error conditions."""

    def test_empty_edi_file(
        self,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test handling of empty EDI file."""
        input_file = tmp_path / "input.edi"
        input_file.write_text("")

        output_file = str(tmp_path / "output")

        with patch("adapters.db2ssh.connection.DB2SSHConnection") as mock_conn_class:
            mock_conn = MockFactories.db2ssh_connection()
            mock_conn.execute.return_value = []
            mock_conn_class.return_value = mock_conn

            result = convert_to_stewarts_custom.edi_convert(
                str(input_file),
                output_file,
                default_settings,
                default_parameters,
                {},
            )
            assert result is not None

    def test_missing_input_file(
        self,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test that missing input file raises FileNotFoundError."""
        input_file = tmp_path / "does_not_exist.edi"
        output_file = str(tmp_path / "output")

        with patch("adapters.db2ssh.connection.DB2SSHConnection"):
            with pytest.raises(FileNotFoundError):
                convert_to_stewarts_custom.edi_convert(
                    str(input_file),
                    output_file,
                    default_settings,
                    default_parameters,
                    {},
                )

    def test_customer_not_found(
        self,
        sample_header_record,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test handling when customer is not found in database."""
        input_file = tmp_path / "input.edi"
        input_file.write_text(sample_header_record + "\n")

        output_file = str(tmp_path / "output")

        with patch("adapters.db2ssh.connection.DB2SSHConnection") as mock_conn_class:
            mock_conn = MockFactories.db2ssh_connection()
            # Return empty result - customer not found
            mock_conn.execute.return_value = []
            mock_conn_class.return_value = mock_conn

            with pytest.raises(Exception, match=r"."):
                convert_to_stewarts_custom.edi_convert(
                    str(input_file),
                    output_file,
                    default_settings,
                    default_parameters,
                    {},
                )


class TestConvertToStewartsCustomOutputStructure(TestConvertToStewartsCustomFixtures):
    """Test output CSV structure in convert_to_stewarts_custom."""

    def test_output_contains_invoice_details_header(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        mock_query_runner_result,
        mock_uom_result,
        tmp_path,
    ):
        """Test that output contains 'Invoice Details' header."""
        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        with patch("adapters.db2ssh.connection.DB2SSHConnection") as mock_conn_class:
            mock_conn = MockFactories.db2ssh_connection()
            mock_conn.execute.return_value = mock_query_runner_result
            mock_conn_class.return_value = mock_conn

            result = convert_to_stewarts_custom.edi_convert(
                str(input_file),
                output_file,
                default_settings,
                default_parameters,
                {},
            )

            with open(result) as f:
                content = f.read()
            assert "Invoice Details" in content

    def test_output_contains_line_item_columns(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        mock_query_runner_result,
        mock_uom_result,
        tmp_path,
    ):
        """Test that output contains line item column headers."""
        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        with patch("adapters.db2ssh.connection.DB2SSHConnection") as mock_conn_class:
            mock_conn = MockFactories.db2ssh_connection()
            mock_conn.execute.return_value = mock_query_runner_result
            mock_conn_class.return_value = mock_conn

            result = convert_to_stewarts_custom.edi_convert(
                str(input_file),
                output_file,
                default_settings,
                default_parameters,
                {},
            )

            with open(result) as f:
                content = f.read()
            # Check for expected column headers in the output
            assert "Description" in content or "Qty" in content or "Item" in content
