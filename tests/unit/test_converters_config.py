"""Unit tests for ``converters_config.*`` typed configuration dataclasses.

Phase 11.x (per ``specs/webapp-phase-11-typed-config-and-records.md`` §6)
introduces typed configuration dataclasses for every converter. This file
consolidates the per-converter config test files that previously lived
alongside each converter's ``*_config.py``.

The dataclasses themselves live in
``webapp.pipeline.converters.converters_config``:

- ``X810ConverterConfig`` (4 params, 2 required)
- ``SimplifiedCsvConverterConfig`` (5 params, all optional)
- ``CSVConverterConfig`` (13 params, all optional)
- ``ScannerWareConverterConfig`` (5 params, all optional)
- ``EStoreEInvoiceGenericConverterConfig`` (4 params, all strings)
- ``EStoreEInvoiceConverterConfig`` (3 params, all strings)
- ``FintechConverterConfig`` (1 param)

Each converter retains its own converter-specific behavioural tests in
``test_convert_to_<name>.py`` — this file only covers the typed-config
contract (defaults, validation, normalisation).
"""

from __future__ import annotations

import pytest

from webapp.pipeline.converters.converters_config import (
    CSVConverterConfig,
    EStoreEInvoiceConverterConfig,
    EStoreEInvoiceGenericConverterConfig,
    FintechConverterConfig,
    ScannerWareConverterConfig,
    SimplifiedCsvConverterConfig,
    X810ConverterConfig,
)

# =============================================================================
# X810
# =============================================================================


class TestX810ConverterConfig:
    def test_minimum_required(self):
        cfg = X810ConverterConfig.from_parameters(
            {"x810_sender_id": "S1", "x810_receiver_id": "R1"}
        )
        assert cfg.sender_id == "S1"
        assert cfg.receiver_id == "R1"
        assert cfg.bill_to_name == ""
        assert cfg.isa_control == ""
        assert cfg.gs_control == ""
        assert cfg.st_control == ""

    def test_optional_fields(self):
        cfg = X810ConverterConfig.from_parameters(
            {
                "x810_sender_id": "S1",
                "x810_receiver_id": "R1",
                "x810_bill_to_name": "ACME",
                "x810_isa_control": "000000001",
                "x810_gs_control": "1",
                "x810_st_control": "0001",
            }
        )
        assert cfg.bill_to_name == "ACME"
        assert cfg.isa_control == "000000001"
        assert cfg.gs_control == "1"
        assert cfg.st_control == "0001"

    def test_missing_sender_raises(self):
        with pytest.raises(ValueError, match="x810_sender_id"):
            X810ConverterConfig.from_parameters({"x810_receiver_id": "R1"})

    def test_missing_receiver_raises(self):
        with pytest.raises(ValueError, match="x810_receiver_id"):
            X810ConverterConfig.from_parameters({"x810_sender_id": "S1"})

    def test_empty_string_treated_as_missing(self):
        with pytest.raises(ValueError, match="x810_sender_id"):
            X810ConverterConfig.from_parameters(
                {"x810_sender_id": "", "x810_receiver_id": "R1"}
            )


# =============================================================================
# Simplified CSV
# =============================================================================


class TestSimplifiedCsvConverterConfig:
    def test_empty_parameters_uses_defaults(self):
        cfg = SimplifiedCsvConverterConfig.from_parameters({})
        assert cfg.retail_uom is False
        assert cfg.include_headers is True
        assert cfg.include_item_numbers is True
        assert cfg.include_item_description is True
        assert cfg.column_layout == (
            "upc_number,qty_of_units,unit_cost,description,vendor_item"
        )
        assert cfg.each_uom_categories == "ALL"
        assert cfg.each_uom_mode == "include"

    def test_boolean_strings_are_normalised(self):
        cfg = SimplifiedCsvConverterConfig.from_parameters(
            {
                "retail_uom": "True",
                "include_headers": "False",
                "include_item_numbers": "0",
                "include_item_description": "off",
            }
        )
        assert cfg.retail_uom is True
        assert cfg.include_headers is False
        assert cfg.include_item_numbers is False
        assert cfg.include_item_description is False

    def test_legacy_include_headers_alias(self):
        """``simple_csv_include_headers`` is the legacy alias."""
        cfg = SimplifiedCsvConverterConfig.from_parameters(
            {"simple_csv_include_headers": "False"}
        )
        assert cfg.include_headers is False

    def test_include_headers_takes_precedence_over_alias(self):
        cfg = SimplifiedCsvConverterConfig.from_parameters(
            {"include_headers": "True", "simple_csv_include_headers": "False"}
        )
        assert cfg.include_headers is True

    def test_legacy_sort_order_alias(self):
        """``simple_csv_sort_order`` is the legacy alias for column_layout."""
        cfg = SimplifiedCsvConverterConfig.from_parameters(
            {"simple_csv_sort_order": "vendor_item,upc_number"}
        )
        assert cfg.column_layout == "vendor_item,upc_number"

    def test_empty_sort_order_falls_back_to_default(self):
        cfg = SimplifiedCsvConverterConfig.from_parameters(
            {"simple_csv_sort_order": ""}
        )
        assert cfg.column_layout == (
            "upc_number,qty_of_units,unit_cost,description,vendor_item"
        )

    def test_each_uom_parameters(self):
        cfg = SimplifiedCsvConverterConfig.from_parameters(
            {"each_uom_categories": "CANDY,DRINK", "each_uom_mode": "exclude"}
        )
        assert cfg.each_uom_categories == "CANDY,DRINK"
        assert cfg.each_uom_mode == "exclude"

    def test_each_uom_categories_empty_falls_back_to_ALL(self):
        cfg = SimplifiedCsvConverterConfig.from_parameters({"each_uom_categories": ""})
        assert cfg.each_uom_categories == "ALL"

    def test_each_uom_mode_empty_falls_back_to_include(self):
        cfg = SimplifiedCsvConverterConfig.from_parameters({"each_uom_mode": ""})
        assert cfg.each_uom_mode == "include"

    def test_column_layout_default_is_non_empty(self):
        cfg = SimplifiedCsvConverterConfig.from_parameters({})
        assert cfg.column_layout
        assert "," in cfg.column_layout


# =============================================================================
# Standard CSV
# =============================================================================


class TestCSVConverterConfig:
    def test_empty_parameters_uses_defaults(self):
        cfg = CSVConverterConfig.from_parameters({})
        assert cfg.calculate_upc_check_digit is False
        assert cfg.include_a_records is False
        assert cfg.include_c_records is False
        assert cfg.include_headers is True
        assert cfg.filter_ampersand is False
        assert cfg.pad_a_records is False
        assert cfg.a_record_padding == ""
        assert cfg.override_upc_bool is False
        assert cfg.override_upc_level == 1
        assert cfg.override_upc_category_filter == "ALL"
        assert cfg.retail_uom is False
        assert cfg.upc_target_length == 11
        assert cfg.upc_padding_pattern == " " * 11

    def test_boolean_strings_are_normalised(self):
        cfg = CSVConverterConfig.from_parameters(
            {
                "calculate_upc_check_digit": "True",
                "include_a_records": "1",
                "include_c_records": "yes",
                "include_headers": "false",
                "filter_ampersand": "0",
                "pad_a_records": "off",
                "override_upc_bool": "True",
                "retail_uom": "True",
            }
        )
        assert cfg.calculate_upc_check_digit is True
        assert cfg.include_a_records is True
        assert cfg.include_c_records is True
        assert cfg.include_headers is False
        assert cfg.filter_ampersand is False
        assert cfg.pad_a_records is False
        assert cfg.override_upc_bool is True
        assert cfg.retail_uom is True

    def test_string_parameters_pass_through(self):
        cfg = CSVConverterConfig.from_parameters(
            {
                "a_record_padding": "  PADDED  ",
                "override_upc_category_filter": "CANDY",
                "upc_padding_pattern": "XXXXXXXXXXX",
            }
        )
        assert cfg.a_record_padding == "  PADDED  "
        assert cfg.override_upc_category_filter == "CANDY"
        assert cfg.upc_padding_pattern == "XXXXXXXXXXX"

    def test_upc_target_length_parsed_as_int(self):
        cfg = CSVConverterConfig.from_parameters({"upc_target_length": "13"})
        assert cfg.upc_target_length == 13

    def test_upc_target_length_empty_falls_back_to_default(self):
        cfg = CSVConverterConfig.from_parameters({"upc_target_length": ""})
        assert cfg.upc_target_length == 11

    def test_upc_target_length_invalid_falls_back_to_default(self):
        cfg = CSVConverterConfig.from_parameters({"upc_target_length": "abc"})
        assert cfg.upc_target_length == 11

    def test_override_upc_level_default(self):
        cfg = CSVConverterConfig.from_parameters({})
        assert cfg.override_upc_level == 1

    def test_override_upc_level_explicit(self):
        cfg = CSVConverterConfig.from_parameters({"override_upc_level": "2"})
        assert cfg.override_upc_level == 2

    def test_a_record_padding_empty_string(self):
        cfg = CSVConverterConfig.from_parameters({"a_record_padding": ""})
        assert cfg.a_record_padding == ""

    def test_override_upc_category_filter_empty_falls_back_to_ALL(self):
        cfg = CSVConverterConfig.from_parameters({"override_upc_category_filter": ""})
        assert cfg.override_upc_category_filter == "ALL"


# =============================================================================
# ScannerWare
# =============================================================================


class TestScannerWareConverterConfig:
    def test_empty_parameters_uses_defaults(self):
        cfg = ScannerWareConverterConfig.from_parameters({})
        assert cfg.a_record_padding == ""
        assert cfg.append_a_records is False
        assert cfg.a_record_append_text == ""
        assert cfg.force_txt_file_ext is False
        assert cfg.invoice_date_offset == 0

    def test_string_fields_pass_through(self):
        cfg = ScannerWareConverterConfig.from_parameters(
            {"a_record_padding": "PAD  ", "a_record_append_text": "EXTRA"}
        )
        assert cfg.a_record_padding == "PAD  "
        assert cfg.a_record_append_text == "EXTRA"

    def test_boolean_strings_are_normalised(self):
        cfg = ScannerWareConverterConfig.from_parameters(
            {"append_a_records": "True", "force_txt_file_ext": "1"}
        )
        assert cfg.append_a_records is True
        assert cfg.force_txt_file_ext is True

    def test_boolean_falsy_strings(self):
        cfg = ScannerWareConverterConfig.from_parameters(
            {"append_a_records": "false", "force_txt_file_ext": "off"}
        )
        assert cfg.append_a_records is False
        assert cfg.force_txt_file_ext is False

    def test_invoice_date_offset_parsed_as_int(self):
        cfg = ScannerWareConverterConfig.from_parameters({"invoice_date_offset": "-3"})
        assert cfg.invoice_date_offset == -3

    def test_invoice_date_offset_empty_falls_back_to_zero(self):
        cfg = ScannerWareConverterConfig.from_parameters({"invoice_date_offset": ""})
        assert cfg.invoice_date_offset == 0

    def test_invoice_date_offset_invalid_falls_back_to_zero(self):
        cfg = ScannerWareConverterConfig.from_parameters(
            {"invoice_date_offset": "not-a-number"}
        )
        assert cfg.invoice_date_offset == 0

    def test_string_fields_empty_string_passes_through(self):
        cfg = ScannerWareConverterConfig.from_parameters(
            {"a_record_padding": "", "a_record_append_text": ""}
        )
        assert cfg.a_record_padding == ""
        assert cfg.a_record_append_text == ""


# =============================================================================
# EStore E-Invoice Generic
# =============================================================================


class TestEStoreEInvoiceGenericConverterConfig:
    def test_empty_parameters_uses_defaults(self):
        cfg = EStoreEInvoiceGenericConverterConfig.from_parameters({})
        assert cfg.store_number == ""
        assert cfg.vendor_oid == ""
        assert cfg.vendor_name == ""
        assert cfg.c_record_oid == ""

    def test_all_parameters(self):
        cfg = EStoreEInvoiceGenericConverterConfig.from_parameters(
            {
                "estore_store_number": "STORE001",
                "estore_Vendor_OId": "VENDOR-OID-123",
                "estore_vendor_NameVendorOID": "ACME Corp",
                "estore_c_record_OID": "CHARGE-OID-99",
            }
        )
        assert cfg.store_number == "STORE001"
        assert cfg.vendor_oid == "VENDOR-OID-123"
        assert cfg.vendor_name == "ACME Corp"
        assert cfg.c_record_oid == "CHARGE-OID-99"

    def test_legacy_vendor_oid_capitalisation_preserved(self):
        """``estore_Vendor_OId`` (mixed case) must be preserved verbatim."""
        cfg = EStoreEInvoiceGenericConverterConfig.from_parameters(
            {"estore_Vendor_OId": "ABC"}
        )
        assert cfg.vendor_oid == "ABC"

    def test_empty_string_fields_pass_through(self):
        cfg = EStoreEInvoiceGenericConverterConfig.from_parameters(
            {
                "estore_store_number": "",
                "estore_Vendor_OId": "",
                "estore_vendor_NameVendorOID": "",
                "estore_c_record_OID": "",
            }
        )
        assert cfg.store_number == ""
        assert cfg.vendor_oid == ""
        assert cfg.vendor_name == ""
        assert cfg.c_record_oid == ""

    def test_partial_parameters(self):
        cfg = EStoreEInvoiceGenericConverterConfig.from_parameters(
            {"estore_store_number": "PARTIAL01"}
        )
        assert cfg.store_number == "PARTIAL01"
        assert cfg.vendor_oid == ""
        assert cfg.vendor_name == ""
        assert cfg.c_record_oid == ""


# =============================================================================
# EStore E-Invoice
# =============================================================================


class TestEStoreEInvoiceConverterConfig:
    def test_empty_parameters_uses_defaults(self):
        cfg = EStoreEInvoiceConverterConfig.from_parameters({})
        assert cfg.store_number == ""
        assert cfg.vendor_oid == ""
        assert cfg.vendor_name == ""

    def test_all_parameters(self):
        cfg = EStoreEInvoiceConverterConfig.from_parameters(
            {
                "estore_store_number": "STORE001",
                "estore_Vendor_OId": "VENDOR-OID-123",
                "estore_vendor_NameVendorOID": "ACME Corp",
            }
        )
        assert cfg.store_number == "STORE001"
        assert cfg.vendor_oid == "VENDOR-OID-123"
        assert cfg.vendor_name == "ACME Corp"

    def test_legacy_vendor_oid_capitalisation_preserved(self):
        cfg = EStoreEInvoiceConverterConfig.from_parameters(
            {"estore_Vendor_OId": "ABC"}
        )
        assert cfg.vendor_oid == "ABC"

    def test_empty_string_fields_pass_through(self):
        cfg = EStoreEInvoiceConverterConfig.from_parameters(
            {
                "estore_store_number": "",
                "estore_Vendor_OId": "",
                "estore_vendor_NameVendorOID": "",
            }
        )
        assert cfg.store_number == ""
        assert cfg.vendor_oid == ""
        assert cfg.vendor_name == ""

    def test_partial_parameters(self):
        cfg = EStoreEInvoiceConverterConfig.from_parameters(
            {"estore_store_number": "PARTIAL01"}
        )
        assert cfg.store_number == "PARTIAL01"
        assert cfg.vendor_oid == ""
        assert cfg.vendor_name == ""


# =============================================================================
# Fintech
# =============================================================================


class TestFintechConverterConfig:
    def test_empty_parameters_uses_defaults(self):
        cfg = FintechConverterConfig.from_parameters({})
        assert cfg.division_id == ""

    def test_explicit_division_id(self):
        cfg = FintechConverterConfig.from_parameters({"fintech_division_id": "DIV001"})
        assert cfg.division_id == "DIV001"

    def test_empty_string_falls_back_to_default(self):
        cfg = FintechConverterConfig.from_parameters({"fintech_division_id": ""})
        assert cfg.division_id == ""

    def test_none_value_falls_back_to_default(self):
        cfg = FintechConverterConfig.from_parameters({"fintech_division_id": None})
        assert cfg.division_id == ""
