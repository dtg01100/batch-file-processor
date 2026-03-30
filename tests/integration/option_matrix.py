"""Shared option matrices for conversion/tweak scenario tests.

Keeping these definitions centralized makes it easier to:
- reuse scenario lists across tests
- enforce option coverage contracts
- require explicit decisions for newly added options
"""

from __future__ import annotations

from typing import Final

# ---------------------------------------------------------------------------
# Individual option coverage
# ---------------------------------------------------------------------------

CSV_OPTION_CASES: Final[list[tuple[str, bool, str]]] = [
    ("include_headers", True, "headers_present"),
    ("include_headers", False, "no_headers"),
    ("include_a_records", True, "a_records_present"),
    ("include_a_records", False, "no_a_records"),
    ("include_c_records", True, "c_records_present"),
    ("include_c_records", False, "no_c_records"),
    ("calculate_upc_check_digit", True, "upc_prefixed_with_tab"),
    ("calculate_upc_check_digit", False, "upc_normal"),
    ("pad_a_records", True, "a_record_padded"),
    ("pad_a_records", False, "a_record_not_padded"),
    ("override_upc_bool", True, "upc_overridden"),
    ("override_upc_bool", False, "upc_original"),
    ("retail_uom", True, "retail_conversion"),
    ("retail_uom", False, "original_uom"),
]

SIMPLIFIED_CSV_OPTION_CASES: Final[list[tuple[str, bool]]] = [
    ("include_item_numbers", True),
    ("include_item_numbers", False),
    ("include_item_description", True),
    ("include_item_description", False),
]

# Include both True/False so tweak options are exercised in enabled and disabled states.
TWEAK_OPTION_CASES: Final[list[tuple[str, bool]]] = [
    ("calculate_upc_check_digit", True),
    ("calculate_upc_check_digit", False),
    ("pad_a_records", True),
    ("pad_a_records", False),
    ("append_a_records", True),
    ("append_a_records", False),
    ("invoice_date_custom_format", True),
    ("invoice_date_custom_format", False),
    ("force_txt_file_ext", True),
    ("force_txt_file_ext", False),
    ("retail_uom", True),
    ("retail_uom", False),
    ("override_upc_bool", True),
    ("override_upc_bool", False),
]


# ---------------------------------------------------------------------------
# Combination coverage
# ---------------------------------------------------------------------------

OPTION_COMBINATION_CASES: Final[list[tuple[str, dict[str, int | str], str]]] = [
    (
        "full_csv_all_options",
        {
            "convert_to_format": "csv",
            "include_headers": 1,
            "include_a_records": 1,
            "include_c_records": 1,
            "pad_a_records": 1,
            "a_record_padding": " " * 20,
            "a_record_padding_length": 20,
        },
        "CSV with all inclusion options enabled",
    ),
    (
        "csv_minimal",
        {
            "convert_to_format": "csv",
            "include_headers": 0,
            "include_a_records": 0,
            "include_c_records": 0,
        },
        "CSV with minimal options (B records only)",
    ),
    (
        "csv_with_upc_override",
        {
            "convert_to_format": "csv",
            "include_headers": 1,
            "override_upc_bool": 1,
            "override_upc_level": 1,
            "override_upc_category_filter": "ALL",
        },
        "CSV with UPC override from lookup table",
    ),
    (
        "csv_with_retail_uom",
        {
            "convert_to_format": "csv",
            "include_headers": 1,
            "retail_uom": 1,
        },
        "CSV with retail UOM conversion",
    ),
    (
        "tweak_and_convert_full",
        {
            "tweak_edi": 1,
            "convert_to_format": "csv",
            "calculate_upc_check_digit": 1,
            "upc_target_length": 11,
            "include_headers": 1,
            "pad_a_records": 1,
            "a_record_padding": " " * 20,
            "a_record_padding_length": 20,
        },
        "Full pipeline: tweak UPC + pad A + convert CSV",
    ),
    (
        "simplified_csv_full",
        {
            "convert_to_format": "simplified_csv",
            "include_headers": 1,
            "include_item_numbers": 1,
            "include_item_description": 1,
            "simple_csv_sort_order": "upc_number,qty_of_units,unit_cost",
        },
        "Simplified CSV with all columns and custom sort",
    ),
]


FORMAT_OPTION_CASES: Final[list[tuple[str, dict[str, int]]]] = [
    (
        "csv",
        {
            "include_headers": 1,
            "include_a_records": 1,
            "include_c_records": 1,
        },
    ),
    (
        "csv",
        {
            "include_headers": 0,
            "include_a_records": 0,
            "include_c_records": 0,
        },
    ),
    ("simplified_csv", {"include_headers": 1, "include_item_numbers": 1}),
    ("simplified_csv", {"include_headers": 0, "include_item_description": 1}),
    ("estore_einvoice", {}),
    ("estore_einvoice_generic", {}),
    ("fintech", {}),
    ("jolley_custom", {}),
    ("scannerware", {}),
    ("scansheet_type_a", {}),
    ("stewarts_custom", {}),
    ("yellowdog_csv", {}),
    ("tweaks", {}),
]


def _extract_option_keys_from_combo_overrides() -> set[str]:
    keys: set[str] = set()
    housekeeping = {
        "id",
        "folder_is_active",
        "process_backend_copy",
        "copy_to_directory",
        "process_edi",
    }
    for _, overrides, _ in OPTION_COMBINATION_CASES:
        for key in overrides:
            if key not in housekeeping:
                keys.add(key)
    return keys


def _extract_option_keys_from_format_options() -> set[str]:
    keys: set[str] = set()
    for _fmt, options in FORMAT_OPTION_CASES:
        keys.update(options.keys())
    return keys


TRACKED_CONVERSION_TWEAK_OPTION_KEYS: Final[set[str]] = (
    {opt for opt, _value, _expected in CSV_OPTION_CASES}
    | {opt for opt, _value in SIMPLIFIED_CSV_OPTION_CASES}
    | {opt for opt, _value in TWEAK_OPTION_CASES}
    | _extract_option_keys_from_combo_overrides()
    | _extract_option_keys_from_format_options()
    | {"convert_to_format", "tweak_edi", "a_record_append_text"}
)

# Keys that must appear in at least one matrix combination scenario.
# This is intentionally narrower than TRACKED_CONVERSION_TWEAK_OPTION_KEYS:
# it captures the options where interaction behavior matters most.
REQUIRED_COMBINATION_OPTION_KEYS: Final[set[str]] = {
    "convert_to_format",
    "tweak_edi",
    "include_headers",
    "include_a_records",
    "include_c_records",
    "calculate_upc_check_digit",
    "pad_a_records",
    "override_upc_bool",
    "retail_uom",
    "include_item_numbers",
    "include_item_description",
}

COMBINATION_MATRIX_OPTION_KEYS: Final[set[str]] = (
    _extract_option_keys_from_combo_overrides()
    | _extract_option_keys_from_format_options()
)

# Explicitly tracked but currently outside this conversion/tweak matrix scope.
# If product behavior changes, move items from this set into tracked option cases.
EXCLUDED_CONVERSION_TWEAK_OPTION_KEYS: Final[set[str]] = {
    "process_edi",
    "split_edi",
    "split_edi_include_invoices",
    "split_edi_include_credits",
    "prepend_date_files",
    "force_edi_validation",
    "rename_file",
    "split_edi_filter_categories",
    "split_edi_filter_mode",
    "upc_padding_pattern",
    "invoice_date_offset",
    "invoice_date_custom_format_string",
    "filter_ampersand",
    "split_prepaid_sales_tax_crec",
    "estore_store_number",
    "estore_Vendor_OId",
    "estore_vendor_NameVendorOID",
    "estore_c_record_OID",
    "fintech_division_id",
}
