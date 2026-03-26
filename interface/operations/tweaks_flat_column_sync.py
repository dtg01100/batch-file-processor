"""Utility for keeping Tweaks plugin_configurations in sync with legacy flat DB columns.

The orchestrator pipeline reads flat columns directly from the DB row and never
consults plugin_configurations.  When a folder whose convert_to_format is "tweaks"
is saved through the dialog, the Tweaks settings come from the plugin form —  the
legacy per-field widgets are absent, so apply() would overwrite the flat columns
with all-default values.  Calling sync_tweaks_plugin_to_flat_columns() after the
plugin_configurations block is written restores the correct values.

This module has no Qt dependency and can be imported freely in unit tests.
"""

from typing import Any

# Mapping: plugin field name (in plugin_configurations["tweaks"])
#       → legacy flat DB column name (read by the orchestrator)
_PLUGIN_TO_FLAT: dict[str, str] = {
    "pad_arec": "pad_a_records",
    "arec_padding": "a_record_padding",
    "arec_padding_len": "a_record_padding_length",
    "append_arec": "append_a_records",
    "append_arec_text": "a_record_append_text",
    "calc_upc": "calculate_upc_check_digit",
    "retail_uom": "retail_uom",
    "override_upc": "override_upc_bool",
    "override_upc_level": "override_upc_level",
    "override_upc_category_filter": "override_upc_category_filter",
    "upc_target_length": "upc_target_length",
    "upc_padding_pattern": "upc_padding_pattern",
    "split_prepaid_sales_tax_crec": "split_prepaid_sales_tax_crec",
    "invoice_date_custom_format": "invoice_date_custom_format",
    "invoice_date_custom_format_string": "invoice_date_custom_format_string",
    "invoice_date_offset": "invoice_date_offset",
    "force_txt_file_ext": "force_txt_file_ext",
}


def sync_tweaks_plugin_to_flat_columns(target: dict[str, Any]) -> None:
    """Write tweaks plugin_configurations values back to legacy flat DB columns.

    Modifies *target* in place.  If ``target["plugin_configurations"]["tweaks"]``
    is absent or empty, the function is a no-op.

    Args:
        target: The folder-config dict that apply() is building.  Must be the
                same dict that will be persisted to the database.

    """
    tweaks_config = target.get("plugin_configurations", {}).get("tweaks", {})
    if not tweaks_config:
        return

    for plugin_field, flat_col in _PLUGIN_TO_FLAT.items():
        if plugin_field in tweaks_config:
            target[flat_col] = tweaks_config[plugin_field]
