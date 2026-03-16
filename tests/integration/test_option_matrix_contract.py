"""Coverage contract tests for conversion/tweak option matrices.

Purpose:
- Ensure model option fields are explicitly mapped
- Ensure mapped option keys are either tested or intentionally excluded
- Ensure conversion format matrix keeps pace with supported converter formats

These tests are lightweight and are intended to fail fast when new options are
introduced without corresponding matrix updates.
"""

from __future__ import annotations

from dataclasses import fields

import pytest

from dispatch.pipeline.converter import SUPPORTED_FORMATS
from interface.models.folder_configuration import (
    ARecordPaddingConfiguration,
    BackendSpecificConfiguration,
    CSVConfiguration,
    EDIConfiguration,
    InvoiceDateConfiguration,
    UPCOverrideConfiguration,
)
from tests.integration.option_matrix import (
    COMBINATION_MATRIX_OPTION_KEYS,
    CSV_OPTION_CASES,
    EXCLUDED_CONVERSION_TWEAK_OPTION_KEYS,
    FORMAT_OPTION_CASES,
    SIMPLIFIED_CSV_OPTION_CASES,
    REQUIRED_COMBINATION_OPTION_KEYS,
    TRACKED_CONVERSION_TWEAK_OPTION_KEYS,
    TWEAK_OPTION_CASES,
)

pytestmark = [pytest.mark.integration]


MODEL_FIELD_TO_DB_KEY: dict[type, dict[str, str]] = {
    EDIConfiguration: {
        "process_edi": "process_edi",
        "tweak_edi": "tweak_edi",
        "split_edi": "split_edi",
        "split_edi_include_invoices": "split_edi_include_invoices",
        "split_edi_include_credits": "split_edi_include_credits",
        "prepend_date_files": "prepend_date_files",
        "convert_to_format": "convert_to_format",
        "force_edi_validation": "force_edi_validation",
        "rename_file": "rename_file",
        "split_edi_filter_categories": "split_edi_filter_categories",
        "split_edi_filter_mode": "split_edi_filter_mode",
    },
    UPCOverrideConfiguration: {
        "enabled": "override_upc_bool",
        "level": "override_upc_level",
        "category_filter": "override_upc_category_filter",
        "target_length": "upc_target_length",
        "padding_pattern": "upc_padding_pattern",
    },
    ARecordPaddingConfiguration: {
        "enabled": "pad_a_records",
        "padding_text": "a_record_padding",
        "padding_length": "a_record_padding_length",
        "append_text": "a_record_append_text",
        "append_enabled": "append_a_records",
        "force_txt_extension": "force_txt_file_ext",
    },
    InvoiceDateConfiguration: {
        "offset": "invoice_date_offset",
        "custom_format_enabled": "invoice_date_custom_format",
        "custom_format_string": "invoice_date_custom_format_string",
        "retail_uom": "retail_uom",
    },
    CSVConfiguration: {
        "include_headers": "include_headers",
        "filter_ampersand": "filter_ampersand",
        "include_item_numbers": "include_item_numbers",
        "include_item_description": "include_item_description",
        "simple_csv_sort_order": "simple_csv_sort_order",
        "split_prepaid_sales_tax_crec": "split_prepaid_sales_tax_crec",
    },
    BackendSpecificConfiguration: {
        "estore_store_number": "estore_store_number",
        "estore_vendor_oid": "estore_Vendor_OId",
        "estore_vendor_namevendoroid": "estore_vendor_NameVendorOID",
        "estore_c_record_oid": "estore_c_record_OID",
        "fintech_division_id": "fintech_division_id",
    },
}


def test_model_field_to_db_key_mapping_is_complete() -> None:
    """Every field in tracked config dataclasses must be explicitly mapped."""
    for model_cls, mapping in MODEL_FIELD_TO_DB_KEY.items():
        model_fields = {f.name for f in fields(model_cls)}
        mapped_fields = set(mapping.keys())
        assert mapped_fields == model_fields, (
            f"Update MODEL_FIELD_TO_DB_KEY for {model_cls.__name__}. "
            f"Missing: {sorted(model_fields - mapped_fields)}, "
            f"Extra: {sorted(mapped_fields - model_fields)}"
        )


def test_all_mapped_options_are_accounted_for() -> None:
    """Mapped option keys must be either tested by matrix or intentionally excluded."""
    mapped_keys = {
        db_key for mapping in MODEL_FIELD_TO_DB_KEY.values() for db_key in mapping.values()
    }
    covered_or_excluded = (
        TRACKED_CONVERSION_TWEAK_OPTION_KEYS | EXCLUDED_CONVERSION_TWEAK_OPTION_KEYS
    )
    missing = mapped_keys - covered_or_excluded
    assert not missing, (
        "New conversion/tweak option keys were added without test-matrix handling: "
        f"{sorted(missing)}. Add coverage or list in EXCLUDED_CONVERSION_TWEAK_OPTION_KEYS."
    )


def test_supported_formats_are_represented_in_format_matrix() -> None:
    """Every converter-supported format should appear in FORMAT_OPTION_CASES."""
    matrix_formats = {fmt for fmt, _options in FORMAT_OPTION_CASES}
    missing = set(SUPPORTED_FORMATS) - matrix_formats
    assert not missing, (
        "FORMAT_OPTION_CASES missing supported formats: "
        f"{sorted(missing)}. Add at least one scenario per format."
    )


def test_boolean_option_cases_include_both_states() -> None:
    """Critical boolean option matrices should include both True and False states."""
    from collections import defaultdict

    seen_states: dict[str, set[bool]] = defaultdict(set)
    for option, value, _expected in CSV_OPTION_CASES:
        seen_states[option].add(bool(value))
    for option, value in SIMPLIFIED_CSV_OPTION_CASES:
        seen_states[option].add(bool(value))
    for option, value in TWEAK_OPTION_CASES:
        seen_states[option].add(bool(value))

    missing_two_state = [
        option for option, states in seen_states.items() if states != {False, True}
    ]
    assert not missing_two_state, (
        "Options missing True/False coverage: "
        f"{sorted(missing_two_state)}"
    )


def test_required_combination_option_keys_are_present() -> None:
    """High-value interaction options must appear in combination matrices."""
    missing = REQUIRED_COMBINATION_OPTION_KEYS - COMBINATION_MATRIX_OPTION_KEYS
    assert not missing, (
        "Combination matrix missing required interaction keys: "
        f"{sorted(missing)}. Add scenarios to OPTION_COMBINATION_CASES or FORMAT_OPTION_CASES."
    )


def test_real_world_scenarios_use_shared_option_matrices() -> None:
    """Main option scenario tests must parametrize from shared matrix constants."""
    from tests.integration import test_real_world_scenarios as scenarios

    expected_values_by_function = {
        "test_csv_option_individual": CSV_OPTION_CASES,
        "test_simplified_csv_option_individual": SIMPLIFIED_CSV_OPTION_CASES,
        "test_tweaking_option_individual": TWEAK_OPTION_CASES,
        "test_option_combinations": scenarios.OPTION_COMBINATION_CASES,
        "test_all_formats_with_options": FORMAT_OPTION_CASES,
    }

    for func_name, expected_values in expected_values_by_function.items():
        func = getattr(scenarios, func_name)
        marks = getattr(func, "pytestmark", [])
        parametrize_marks = [m for m in marks if m.name == "parametrize"]
        assert parametrize_marks, f"{func_name} missing @pytest.mark.parametrize"
        actual_values = parametrize_marks[0].args[1]
        assert actual_values == expected_values, (
            f"{func_name} must use shared matrix constants; found non-matching values."
        )
