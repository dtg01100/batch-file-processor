"""Per-format converter configuration registry for the webapp.

The desktop app exposed a per-format plugin UI: each of the 11 convert
formats declared its configuration fields (types, defaults, options),
the folder editor rendered a dynamic section for the folder's selected
format, and the values were stored in the folder's
``plugin_configurations`` JSON dict keyed by (lowercased) format name.

The webapp carries ``plugin_configurations`` in its schema but had no
UI to edit it and nothing consumed it at run time. This module is the
single source of truth for the per-format field specs (ported from the
desktop's ``interface/plugins/*_configuration_plugin.py`` classes) and
provides the merge the runner needs so those values actually reach the
converters.

Field names use the same keys the converters read from
``parameters_dict`` (the flat folder columns), so a merged plugin
config overrides the flat columns without a translation layer.
"""

from __future__ import annotations

import contextlib
import json
from typing import Any

# Field type constants (wire values the browser renders).
TEXT = "string"
BOOL = "boolean"
INT = "integer"
SELECT = "select"

# format key (lowercased, matches convert_to_format + the
# plugin_configurations dict key) -> spec. ``display_name`` mirrors the
# desktop's get_format_name(); ``fields`` mirrors get_config_fields().
CONVERTER_FORMATS: dict[str, dict[str, Any]] = {
    "csv": {
        "display_name": "CSV",
        "fields": [
            {
                "key": "include_headers",
                "label": "Include Headers",
                "type": BOOL,
                "default": False,
            },
            {
                "key": "filter_ampersand",
                "label": "Filter Ampersand",
                "type": BOOL,
                "default": False,
            },
            {
                "key": "include_item_numbers",
                "label": "Include Item Numbers",
                "type": BOOL,
                "default": False,
            },
            {
                "key": "include_item_description",
                "label": "Include Item Description",
                "type": BOOL,
                "default": False,
            },
            {
                "key": "simple_csv_sort_order",
                "label": "Simple CSV Sort Order",
                "type": TEXT,
                "default": "",
            },
            {
                "key": "split_prepaid_sales_tax_crec",
                "label": "Split Prepaid Sales Tax CREC",
                "type": BOOL,
                "default": False,
            },
        ],
    },
    "scannerware": {
        "display_name": "ScannerWare",
        "fields": [
            {
                "key": "a_record_padding",
                "label": "A-Record Padding",
                "type": TEXT,
                "default": "",
                "max_length": 6,
            },
            {
                "key": "append_a_records",
                "label": "Append A-Records",
                "type": BOOL,
                "default": False,
            },
            {
                "key": "a_record_append_text",
                "label": "A-Record Append Text",
                "type": TEXT,
                "default": "",
            },
            {
                "key": "force_txt_file_ext",
                "label": "Force TXT File Extension",
                "type": BOOL,
                "default": False,
            },
            {
                "key": "invoice_date_offset",
                "label": "Invoice Date Offset",
                "type": INT,
                "default": 0,
                "min": -14,
                "max": 14,
            },
            {
                "key": "retail_uom",
                "label": "Retail UOM",
                "type": BOOL,
                "default": False,
            },
        ],
    },
    "simplified_csv": {
        "display_name": "Simplified CSV",
        "fields": [
            {
                "key": "retail_uom",
                "label": "Retail UOM",
                "type": BOOL,
                "default": False,
            },
            {
                "key": "include_headers",
                "label": "Include Headers",
                "type": BOOL,
                "default": False,
            },
            {
                "key": "include_item_numbers",
                "label": "Include Item Numbers",
                "type": BOOL,
                "default": False,
            },
            {
                "key": "include_item_description",
                "label": "Include Item Description",
                "type": BOOL,
                "default": False,
            },
            {
                "key": "simple_csv_sort_order",
                "label": "Simple CSV Sort Order",
                "type": TEXT,
                "default": "",
            },
        ],
    },
    "estore_einvoice": {
        "display_name": "eStore eInvoice",
        "fields": [
            {
                "key": "estore_store_number",
                "label": "Store Number",
                "type": TEXT,
                "default": "",
            },
            {
                "key": "estore_vendor_oid",
                "label": "Vendor OID",
                "type": TEXT,
                "default": "",
            },
            {
                "key": "estore_vendor_namevendoroid",
                "label": "Vendor Name (Vendor OID)",
                "type": TEXT,
                "default": "",
            },
        ],
    },
    "estore_einvoice_generic": {
        "display_name": "eStore eInvoice Generic",
        "fields": [
            {
                "key": "estore_store_number",
                "label": "Store Number",
                "type": TEXT,
                "default": "",
            },
            {
                "key": "estore_vendor_oid",
                "label": "Vendor OID",
                "type": TEXT,
                "default": "",
            },
            {
                "key": "estore_vendor_namevendoroid",
                "label": "Vendor Name (Vendor OID)",
                "type": TEXT,
                "default": "",
            },
            {
                "key": "estore_c_record_oid",
                "label": "C-Record OID",
                "type": TEXT,
                "default": "",
            },
        ],
    },
    "fintech": {
        "display_name": "Fintech",
        "fields": [
            {
                "key": "fintech_division_id",
                "label": "Division ID",
                "type": TEXT,
                "default": "",
            },
        ],
    },
    "tweaks": {
        "display_name": "Tweaks",
        "fields": [
            {
                "key": "pad_a_records",
                "label": "Pad A-Records",
                "type": BOOL,
                "default": False,
            },
            {
                "key": "a_record_padding",
                "label": "A-Record Padding Text",
                "type": TEXT,
                "default": "",
            },
            {
                "key": "a_record_padding_length",
                "label": "A-Record Padding Length",
                "type": SELECT,
                "default": 6,
                "options": [6, 30],
            },
            {
                "key": "append_a_records",
                "label": "Append to A-Records",
                "type": BOOL,
                "default": False,
            },
            {
                "key": "a_record_append_text",
                "label": "A-Record Append Text",
                "type": TEXT,
                "default": "",
            },
            {
                "key": "invoice_date_custom_format",
                "label": "Custom Invoice Date Format",
                "type": BOOL,
                "default": False,
            },
            {
                "key": "invoice_date_custom_format_string",
                "label": "Invoice Date Format String",
                "type": TEXT,
                "default": "",
            },
            {
                "key": "invoice_date_offset",
                "label": "Invoice Date Offset (Days)",
                "type": INT,
                "default": 0,
            },
            {
                "key": "force_txt_file_ext",
                "label": "Force .txt Extension",
                "type": BOOL,
                "default": False,
            },
            {
                "key": "calculate_upc_check_digit",
                "label": "Calculate UPC Check Digit",
                "type": BOOL,
                "default": False,
            },
            {
                "key": "retail_uom",
                "label": "Retail UOM Conversion",
                "type": BOOL,
                "default": False,
            },
            {
                "key": "split_prepaid_sales_tax_crec",
                "label": "Split Prepaid Sales Tax CREC",
                "type": BOOL,
                "default": False,
            },
            {
                "key": "override_upc_bool",
                "label": "Override UPC from Lookup",
                "type": BOOL,
                "default": False,
            },
            {
                "key": "override_upc_level",
                "label": "UPC Override Level",
                "type": INT,
                "default": 1,
            },
            {
                "key": "override_upc_category_filter",
                "label": "UPC Override Category Filter",
                "type": TEXT,
                "default": "",
            },
            {
                "key": "upc_target_length",
                "label": "UPC Target Length",
                "type": INT,
                "default": 11,
            },
            {
                "key": "upc_padding_pattern",
                "label": "UPC Padding Pattern",
                "type": TEXT,
                "default": "",
            },
        ],
    },
    # These formats are configured solely through the global AS400/UPC
    # settings and backend fields — no per-format fields (the desktop's
    # plugin classes for them declared empty field sets).
    "jolley_custom": {"display_name": "Jolley Custom", "fields": []},
    "stewarts_custom": {"display_name": "Stewarts Custom", "fields": []},
    "scansheet_type_a": {"display_name": "ScanSheet Type A", "fields": []},
    "yellowdog_csv": {"display_name": "YellowDog CSV", "fields": []},
}


def converter_spec(format_key: str) -> dict[str, Any] | None:
    """Return the spec for a format key, or None if unknown.

    Args:
        format_key: The ``convert_to_format`` value (case-insensitive).

    """
    return CONVERTER_FORMATS.get(format_key.lower())


def all_converter_specs() -> list[dict[str, Any]]:
    """Return every format spec for the API payload, keys normalized."""
    return [
        {"format": key, "display_name": spec["display_name"], "fields": spec["fields"]}
        for key, spec in CONVERTER_FORMATS.items()
    ]


def merge_plugin_config(folder: dict[str, Any]) -> dict[str, Any]:
    """Merge the folder's per-format plugin config into a copy.

    The ``plugin_configurations`` JSON dict stores, per format, the
    values the per-format UI collects. The converters read flat
    columns from the folder dict; this helper layers the config for the
    folder's ``convert_to_format`` on top so those values take effect
    at run time.

    Args:
        folder: A folder-row dict (raw or resolved).

    Returns:
        A shallow copy with the plugin config's keys overlaid. If the
        folder has no matching config (or no convert_to_format), the
        copy is returned unchanged.

    """
    out = dict(folder)
    convert_format = str(folder.get("convert_to_format", "") or "").strip().lower()
    # Only known formats merge (a typo'd convert_to_format must not
    # silently apply arbitrary columns as converter settings).
    if not convert_format or convert_format not in CONVERTER_FORMATS:
        return out
    config = folder.get("plugin_configurations") or {}
    if isinstance(config, str):
        # Stored as JSON text (legacy column) — tolerate it.
        with contextlib.suppress(json.JSONDecodeError, TypeError):
            config = json.loads(config)
    if not isinstance(config, dict):
        return out
    plugin = config.get(convert_format)
    if not isinstance(plugin, dict):
        # Tolerate a config keyed with a different case (the desktop
        # lowercased on set, but hand-edited rows may not).
        for key, value in config.items():
            if isinstance(value, dict) and str(key).lower() == convert_format:
                plugin = value
                break
    if not isinstance(plugin, dict):
        return out
    out.update(plugin)
    return out
