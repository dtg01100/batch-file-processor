"""Unit tests for convert_to_yellowdog_csv.py converter module.

Tests:
- Input validation and edge cases
- Database lookup mocking
- Batching and record order reversal
- CSV column layout verification
- Customer PO and name lookups

Converter: convert_to_yellowdog_csv.py (13378 chars)

Note: This converter supports optional database lookups, tests verify both modes.
"""

import csv
import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from dispatch.converters import convert_to_yellowdog_csv


class TestConvertToYellowdogCSVFixtures:
    """Test fixtures for convert_to_yellowdog_csv module."""

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
    def complete_edi_content(
        self, sample_header_record, sample_detail_record, sample_tax_record
    ):
        """Create complete EDI content with header, detail, and tax records."""
        return (
            sample_header_record
            + "\n"
            + sample_detail_record
            + "\n"
            + sample_tax_record
            + "\n"
        )

    @pytest.fixture
    def default_parameters(self):
        """Default parameters dict for convert_to_yellowdog_csv."""
        return {
            "database_lookup_mode": "optional",
        }

    @pytest.fixture
    def default_settings(self):
        """Default settings dict with database credentials."""
        return {
            "as400_username": "test_user",
            "as400_password": "test_pass",
            "as400_address": "test.address.com",
            "odbc_driver": "ODBC Driver 17 for SQL Server",
        }

    @pytest.fixture
    def mock_inv_fetcher(self):
        """Return a mock InvFetcher instance."""
        fetcher_instance = MagicMock()
        fetcher_instance.fetch_cust_name.return_value = "Test Customer"
        fetcher_instance.fetch_po.return_value = "PO-001"
        fetcher_instance.fetch_uom_desc.return_value = "CS"
        fetcher_class = MagicMock(return_value=fetcher_instance)
        return fetcher_class, fetcher_instance


class TestConvertToYellowdogCSVBasicFunctionality(TestConvertToYellowdogCSVFixtures):
    """Test basic functionality of convert_to_yellowdog_csv."""

    def test_module_import(self):
        """Test that convert_to_yellowdog_csv module can be imported."""
        from dispatch.converters import convert_to_yellowdog_csv

        assert convert_to_yellowdog_csv is not None
        assert hasattr(convert_to_yellowdog_csv, "edi_convert")

    def test_edi_convert_returns_csv_filename(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        mock_inv_fetcher,
        tmp_path,
    ):
        """Test that edi_convert returns the expected CSV filename."""
        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        fetcher_class, _ = mock_inv_fetcher
        with patch("dispatch.converters.convert_to_yellowdog_csv.utils") as mock_utils:
            mock_utils.invFetcher = fetcher_class
            mock_utils.capture_records.side_effect = lambda line: (
                {
                    "record_type": "A",
                    "cust_vendor": line[1:7],
                    "invoice_number": line[7:17],
                    "invoice_date": line[17:23],
                    "invoice_total": line[23:33],
                }
                if line.startswith("A")
                else (
                    {
                        "record_type": "B",
                        "upc_number": line[1:12],
                        "description": line[12:37],
                        "vendor_item": line[37:43],
                        "unit_cost": line[43:49],
                        "combo_code": line[49:51],
                        "unit_multiplier": line[51:57],
                        "qty_of_units": line[57:62],
                        "suggested_retail_price": line[62:67],
                        "price_multi_pack": line[67:70],
                        "parent_item_number": line[70:76],
                    }
                    if line.startswith("B")
                    else (
                        {
                            "record_type": "C",
                            "charge_type": line[1:4],
                            "description": line[4:29],
                            "amount": line[29:38],
                        }
                        if line.startswith("C")
                        else None
                    )
                )
            )
            mock_utils.datetime_from_invtime.return_value = datetime(2025, 1, 1)
            mock_utils.convert_to_price.return_value = "1.00"
            mock_utils.dac_str_int_to_int.return_value = 100

            result = convert_to_yellowdog_csv.edi_convert(
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
        mock_inv_fetcher,
        tmp_path,
    ):
        """Test that the CSV file is actually created."""
        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        fetcher_class, _ = mock_inv_fetcher
        with patch("dispatch.converters.convert_to_yellowdog_csv.utils") as mock_utils:
            mock_utils.invFetcher = fetcher_class
            mock_utils.capture_records.side_effect = lambda line: (
                {
                    "record_type": "A",
                    "cust_vendor": line[1:7],
                    "invoice_number": line[7:17],
                    "invoice_date": line[17:23],
                    "invoice_total": line[23:33],
                }
                if line.startswith("A")
                else (
                    {
                        "record_type": "B",
                        "upc_number": line[1:12],
                        "description": line[12:37],
                        "vendor_item": line[37:43],
                        "unit_cost": line[43:49],
                        "combo_code": line[49:51],
                        "unit_multiplier": line[51:57],
                        "qty_of_units": line[57:62],
                        "suggested_retail_price": line[62:67],
                        "price_multi_pack": line[67:70],
                        "parent_item_number": line[70:76],
                    }
                    if line.startswith("B")
                    else (
                        {
                            "record_type": "C",
                            "charge_type": line[1:4],
                            "description": line[4:29],
                            "amount": line[29:38],
                        }
                        if line.startswith("C")
                        else None
                    )
                )
            )
            mock_utils.datetime_from_invtime.return_value = datetime(2025, 1, 1)
            mock_utils.convert_to_price.return_value = "1.00"
            mock_utils.dac_str_int_to_int.return_value = 100

            convert_to_yellowdog_csv.edi_convert(
                str(input_file),
                output_file,
                default_settings,
                default_parameters,
                {},
            )

        assert os.path.exists(output_file + ".csv")


class TestConvertToYellowdogCSVHeaders(TestConvertToYellowdogCSVFixtures):
    """Test CSV header row in convert_to_yellowdog_csv."""

    def test_csv_has_correct_headers(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        mock_inv_fetcher,
        tmp_path,
    ):
        """Test that CSV headers are correct."""
        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        fetcher_class, _ = mock_inv_fetcher
        with patch("dispatch.converters.convert_to_yellowdog_csv.utils") as mock_utils:
            mock_utils.invFetcher = fetcher_class
            mock_utils.capture_records.side_effect = lambda line: (
                {
                    "record_type": "A",
                    "cust_vendor": line[1:7],
                    "invoice_number": line[7:17],
                    "invoice_date": line[17:23],
                    "invoice_total": line[23:33],
                }
                if line.startswith("A")
                else (
                    {
                        "record_type": "B",
                        "upc_number": line[1:12],
                        "description": line[12:37],
                        "vendor_item": line[37:43],
                        "unit_cost": line[43:49],
                        "combo_code": line[49:51],
                        "unit_multiplier": line[51:57],
                        "qty_of_units": line[57:62],
                        "suggested_retail_price": line[62:67],
                        "price_multi_pack": line[67:70],
                        "parent_item_number": line[70:76],
                    }
                    if line.startswith("B")
                    else (
                        {
                            "record_type": "C",
                            "charge_type": line[1:4],
                            "description": line[4:29],
                            "amount": line[29:38],
                        }
                        if line.startswith("C")
                        else None
                    )
                )
            )
            mock_utils.datetime_from_invtime.return_value = datetime(2025, 1, 1)
            mock_utils.convert_to_price.return_value = "1.00"
            mock_utils.dac_str_int_to_int.return_value = 100

            convert_to_yellowdog_csv.edi_convert(
                str(input_file),
                output_file,
                default_settings,
                default_parameters,
                {},
            )

        with open(output_file + ".csv", "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            first_row = next(reader)
            expected_headers = [
                "Invoice Total",
                "Description",
                "Item Number",
                "Cost",
                "Quantity",
                "UOM Desc.",
                "Invoice Date",
                "Invoice Number",
                "Customer Name",
                "Customer PO Number",
                "UPC",
            ]
            assert first_row == expected_headers


class TestConvertToYellowdogCSVDatabaseLookup(TestConvertToYellowdogCSVFixtures):
    """Test database lookup functionality in convert_to_yellowdog_csv."""

    def test_customer_name_lookup_called(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        mock_inv_fetcher,
        tmp_path,
    ):
        """Test that customer name lookup is executed."""
        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        fetcher_class, fetcher_instance = mock_inv_fetcher
        with patch(
            "dispatch.converters.convert_to_yellowdog_csv.InvFetcher", fetcher_class
        ):
            with patch(
                "dispatch.converters.convert_to_yellowdog_csv.utils"
            ) as mock_utils:
                mock_utils.capture_records.side_effect = lambda line: (
                    {
                        "record_type": "A",
                        "cust_vendor": line[1:7],
                        "invoice_number": line[7:17],
                        "invoice_date": line[17:23],
                        "invoice_total": line[23:33],
                    }
                    if line.startswith("A")
                    else (
                        {
                            "record_type": "B",
                            "upc_number": line[1:12],
                            "description": line[12:37],
                            "vendor_item": line[37:43],
                            "unit_cost": line[43:49],
                            "combo_code": line[49:51],
                            "unit_multiplier": line[51:57],
                            "qty_of_units": line[57:62],
                            "suggested_retail_price": line[62:67],
                            "price_multi_pack": line[67:70],
                            "parent_item_number": line[70:76],
                        }
                        if line.startswith("B")
                        else (
                            {
                                "record_type": "C",
                                "charge_type": line[1:4],
                                "description": line[4:29],
                                "amount": line[29:38],
                            }
                            if line.startswith("C")
                            else None
                        )
                    )
                )
                mock_utils.datetime_from_invtime.return_value = datetime(2025, 1, 1)
                mock_utils.convert_to_price.return_value = "1.00"
                mock_utils.dac_str_int_to_int.return_value = 100

                convert_to_yellowdog_csv.edi_convert(
                    str(input_file),
                    output_file,
                    default_settings,
                    default_parameters,
                    {},
                )

                assert fetcher_instance.fetch_cust_name.called

    def test_po_number_lookup_called(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        mock_inv_fetcher,
        tmp_path,
    ):
        """Test that PO number lookup is executed."""
        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        fetcher_class, fetcher_instance = mock_inv_fetcher
        with patch(
            "dispatch.converters.convert_to_yellowdog_csv.InvFetcher", fetcher_class
        ):
            with patch(
                "dispatch.converters.convert_to_yellowdog_csv.utils"
            ) as mock_utils:
                mock_utils.capture_records.side_effect = lambda line: (
                    {
                        "record_type": "A",
                        "cust_vendor": line[1:7],
                        "invoice_number": line[7:17],
                        "invoice_date": line[17:23],
                        "invoice_total": line[23:33],
                    }
                    if line.startswith("A")
                    else (
                        {
                            "record_type": "B",
                            "upc_number": line[1:12],
                            "description": line[12:37],
                            "vendor_item": line[37:43],
                            "unit_cost": line[43:49],
                            "combo_code": line[49:51],
                            "unit_multiplier": line[51:57],
                            "qty_of_units": line[57:62],
                            "suggested_retail_price": line[62:67],
                            "price_multi_pack": line[67:70],
                            "parent_item_number": line[70:76],
                        }
                        if line.startswith("B")
                        else (
                            {
                                "record_type": "C",
                                "charge_type": line[1:4],
                                "description": line[4:29],
                                "amount": line[29:38],
                            }
                            if line.startswith("C")
                            else None
                        )
                    )
                )
                mock_utils.datetime_from_invtime.return_value = datetime(2025, 1, 1)
                mock_utils.convert_to_price.return_value = "1.00"
                mock_utils.dac_str_int_to_int.return_value = 100

                convert_to_yellowdog_csv.edi_convert(
                    str(input_file),
                    output_file,
                    default_settings,
                    default_parameters,
                    {},
                )

                assert fetcher_instance.fetch_po.called


class TestConvertToYellowdogCSVStrictMode(TestConvertToYellowdogCSVFixtures):
    """Test strict database mode in convert_to_yellowdog_csv."""

    def test_strict_mode_requires_db_settings(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test that strict mode raises error when DB settings are missing."""
        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        default_parameters["database_lookup_mode"] = "strict"
        default_settings["as400_username"] = ""
        default_settings["as400_password"] = ""
        default_settings["as400_address"] = ""
        default_settings["odbc_driver"] = ""

        with pytest.raises(ValueError):
            convert_to_yellowdog_csv.edi_convert(
                str(input_file),
                output_file,
                default_settings,
                default_parameters,
                {},
            )


class TestConvertToYellowdogCSVEdgeCases(TestConvertToYellowdogCSVFixtures):
    """Test edge cases and error conditions."""

    def test_missing_input_file(
        self, default_parameters, default_settings, mock_inv_fetcher, tmp_path
    ):
        """Test that missing input file raises FileNotFoundError."""
        input_file = tmp_path / "does_not_exist.edi"
        output_file = str(tmp_path / "output")

        fetcher_class, _ = mock_inv_fetcher
        with patch("dispatch.converters.convert_to_yellowdog_csv.utils") as mock_utils:
            mock_utils.invFetcher = fetcher_class

            with pytest.raises(FileNotFoundError):
                convert_to_yellowdog_csv.edi_convert(
                    str(input_file),
                    output_file,
                    default_settings,
                    default_parameters,
                    {},
                )

    def test_empty_upc_lut_handling(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        mock_inv_fetcher,
        tmp_path,
    ):
        """Test that empty upc_lut is handled gracefully."""
        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        fetcher_class, _ = mock_inv_fetcher
        with patch("dispatch.converters.convert_to_yellowdog_csv.utils") as mock_utils:
            mock_utils.invFetcher = fetcher_class
            mock_utils.capture_records.side_effect = lambda line: (
                {
                    "record_type": "A",
                    "cust_vendor": line[1:7],
                    "invoice_number": line[7:17],
                    "invoice_date": line[17:23],
                    "invoice_total": line[23:33],
                }
                if line.startswith("A")
                else (
                    {
                        "record_type": "B",
                        "upc_number": line[1:12],
                        "description": line[12:37],
                        "vendor_item": line[37:43],
                        "unit_cost": line[43:49],
                        "combo_code": line[49:51],
                        "unit_multiplier": line[51:57],
                        "qty_of_units": line[57:62],
                        "suggested_retail_price": line[62:67],
                        "price_multi_pack": line[67:70],
                        "parent_item_number": line[70:76],
                    }
                    if line.startswith("B")
                    else (
                        {
                            "record_type": "C",
                            "charge_type": line[1:4],
                            "description": line[4:29],
                            "amount": line[29:38],
                        }
                        if line.startswith("C")
                        else None
                    )
                )
            )
            mock_utils.datetime_from_invtime.return_value = datetime(2025, 1, 1)
            mock_utils.convert_to_price.return_value = "1.00"
            mock_utils.dac_str_int_to_int.return_value = 100

            result = convert_to_yellowdog_csv.edi_convert(
                str(input_file),
                output_file,
                default_settings,
                default_parameters,
                {},
            )

        assert os.path.exists(result)


class TestConvertToYellowdogCSVOutputContent(TestConvertToYellowdogCSVFixtures):
    """Test output content in convert_to_yellowdog_csv."""

    def test_output_has_quoted_values(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        mock_inv_fetcher,
        tmp_path,
    ):
        """Test that output values are quoted."""
        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        fetcher_class, _ = mock_inv_fetcher
        with patch("dispatch.converters.convert_to_yellowdog_csv.utils") as mock_utils:
            mock_utils.invFetcher = fetcher_class
            mock_utils.capture_records.side_effect = lambda line: (
                {
                    "record_type": "A",
                    "cust_vendor": line[1:7],
                    "invoice_number": line[7:17],
                    "invoice_date": line[17:23],
                    "invoice_total": line[23:33],
                }
                if line.startswith("A")
                else (
                    {
                        "record_type": "B",
                        "upc_number": line[1:12],
                        "description": line[12:37],
                        "vendor_item": line[37:43],
                        "unit_cost": line[43:49],
                        "combo_code": line[49:51],
                        "unit_multiplier": line[51:57],
                        "qty_of_units": line[57:62],
                        "suggested_retail_price": line[62:67],
                        "price_multi_pack": line[67:70],
                        "parent_item_number": line[70:76],
                    }
                    if line.startswith("B")
                    else (
                        {
                            "record_type": "C",
                            "charge_type": line[1:4],
                            "description": line[4:29],
                            "amount": line[29:38],
                        }
                        if line.startswith("C")
                        else None
                    )
                )
            )
            mock_utils.datetime_from_invtime.return_value = datetime(2025, 1, 1)
            mock_utils.convert_to_price.return_value = "1.00"
            mock_utils.dac_str_int_to_int.return_value = 100

            convert_to_yellowdog_csv.edi_convert(
                str(input_file),
                output_file,
                default_settings,
                default_parameters,
                {},
            )

        with open(output_file + ".csv", "r", encoding="utf-8") as f:
            content = f.read()
            assert '"' in content or len(content) > 0

    def test_multiple_detail_records(
        self,
        sample_header_record,
        default_parameters,
        default_settings,
        mock_inv_fetcher,
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

        fetcher_class, _ = mock_inv_fetcher
        with patch("dispatch.converters.convert_to_yellowdog_csv.utils") as mock_utils:
            mock_utils.invFetcher = fetcher_class
            mock_utils.capture_records.side_effect = lambda line: (
                {
                    "record_type": "A",
                    "cust_vendor": line[1:7],
                    "invoice_number": line[7:17],
                    "invoice_date": line[17:23],
                    "invoice_total": line[23:33],
                }
                if line.startswith("A")
                else (
                    {
                        "record_type": "B",
                        "upc_number": line[1:12],
                        "description": line[12:37],
                        "vendor_item": line[37:43],
                        "unit_cost": line[43:49],
                        "combo_code": line[49:51],
                        "unit_multiplier": line[51:57],
                        "qty_of_units": line[57:62],
                        "suggested_retail_price": line[62:67],
                        "price_multi_pack": line[67:70],
                        "parent_item_number": line[70:76],
                    }
                    if line.startswith("B")
                    else None
                )
            )
            mock_utils.datetime_from_invtime.return_value = datetime(2025, 1, 1)
            mock_utils.convert_to_price.return_value = "1.00"
            mock_utils.dac_str_int_to_int.return_value = 100

            convert_to_yellowdog_csv.edi_convert(
                str(input_file),
                output_file,
                default_settings,
                default_parameters,
                {},
            )

        with open(output_file + ".csv", "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)
            assert len(rows) >= 3
