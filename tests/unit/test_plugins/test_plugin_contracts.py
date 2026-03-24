"""Contract tests for concrete configuration plugins."""

import pytest

from interface.models.folder_configuration import ConvertFormat
from interface.plugins.config_schemas import ConfigurationSchema, FieldDefinition
from interface.plugins.configuration_plugin import ConfigurationPlugin
from interface.plugins.csv_configuration_plugin import CSVConfigurationPlugin
from interface.plugins.estore_einvoice_configuration_plugin import (
    EStoreEInvoiceConfigurationPlugin,
)
from interface.plugins.estore_einvoice_generic_configuration_plugin import (
    EStoreEInvoiceGenericConfigurationPlugin,
)
from interface.plugins.fintech_configuration_plugin import FintechConfigurationPlugin
from interface.plugins.jolley_custom_configuration_plugin import (
    JolleyCustomConfigurationPlugin,
)
from interface.plugins.scannerware_configuration_plugin import (
    ScannerWareConfigurationPlugin,
)
from interface.plugins.scansheet_type_a_configuration_plugin import (
    ScanSheetTypeAConfigurationPlugin,
)
from interface.plugins.simplified_csv_configuration_plugin import (
    SimplifiedCSVConfigurationPlugin,
)
from interface.plugins.stewarts_custom_configuration_plugin import (
    StewartsCustomConfigurationPlugin,
)
from interface.plugins.validation_framework import ValidationResult
from interface.plugins.yellowdog_csv_configuration_plugin import (
    YellowDogCSVConfigurationPlugin,
)
from interface.plugins.tweaks_configuration_plugin import (
    TweaksConfigurationPlugin,
)

PLUGIN_CASES = [
    (
        CSVConfigurationPlugin,
        ConvertFormat.CSV,
        {
            "include_headers": True,
            "filter_ampersand": False,
            "include_item_numbers": True,
            "include_item_description": False,
            "simple_csv_sort_order": "asc",
            "split_prepaid_sales_tax_crec": True,
        },
        [
            "include_headers",
            "filter_ampersand",
            "include_item_numbers",
            "include_item_description",
            "simple_csv_sort_order",
            "split_prepaid_sales_tax_crec",
        ],
    ),
    (
        SimplifiedCSVConfigurationPlugin,
        ConvertFormat.SIMPLIFIED_CSV,
        {
            "retail_uom": True,
            "include_headers": True,
            "include_item_numbers": True,
            "include_item_description": True,
            "simple_csv_sort_order": "upc_number",
        },
        [
            "retail_uom",
            "include_headers",
            "include_item_numbers",
            "include_item_description",
            "simple_csv_sort_order",
        ],
    ),
    (
        FintechConfigurationPlugin,
        ConvertFormat.FINTECH,
        {"fintech_division_id": "DIV-001"},
        ["fintech_division_id"],
    ),
    (
        ScannerWareConfigurationPlugin,
        ConvertFormat.SCANNERWARE,
        {
            "a_record_padding": "PAD123",
            "append_a_records": True,
            "a_record_append_text": "APPEND",
            "force_txt_file_ext": False,
            "invoice_date_offset": 0,
            "retail_uom": True,
        },
        [
            "a_record_padding",
            "append_a_records",
            "a_record_append_text",
            "force_txt_file_ext",
            "invoice_date_offset",
            "retail_uom",
        ],
    ),
    (
        ScanSheetTypeAConfigurationPlugin,
        ConvertFormat.SCANSHEET_A,
        {},
        [],
    ),
    (
        JolleyCustomConfigurationPlugin,
        ConvertFormat.JOLLEY_CUSTOM,
        {},
        [],
    ),
    (
        StewartsCustomConfigurationPlugin,
        ConvertFormat.STEWARTS_CUSTOM,
        {},
        [],
    ),
    (
        YellowDogCSVConfigurationPlugin,
        ConvertFormat.YELLOWDOG_CSV,
        {},
        [],
    ),
    (
        EStoreEInvoiceConfigurationPlugin,
        ConvertFormat.ESTORE_EINVOICE,
        {
            "estore_store_number": "STORE001",
            "estore_vendor_oid": "VENDOR001",
            "estore_vendor_namevendoroid": "MyVendor",
        },
        [
            "estore_store_number",
            "estore_vendor_oid",
            "estore_vendor_namevendoroid",
        ],
    ),
    (
        EStoreEInvoiceGenericConfigurationPlugin,
        ConvertFormat.ESTORE_EINVOICE_GENERIC,
        {
            "estore_store_number": "STORE001",
            "estore_vendor_oid": "VENDOR001",
            "estore_vendor_namevendoroid": "MyVendor",
            "estore_c_record_oid": "OID001",
        },
        [
            "estore_store_number",
            "estore_vendor_oid",
            "estore_vendor_namevendoroid",
            "estore_c_record_oid",
        ],
    ),
    (
        TweaksConfigurationPlugin,
        ConvertFormat.TWEAKS,
        {
            "pad_arec": True,
            "arec_padding": "PAD",
            "arec_padding_len": 6,
            "append_arec": True,
            "append_arec_text": "APPEND",
            "invoice_date_custom_format": False,
            "invoice_date_custom_format_string": "%Y-%m-%d",
            "invoice_date_offset": 0,
            "force_txt_file_ext": False,
            "calc_upc": True,
            "retail_uom": True,
            "split_prepaid_sales_tax_crec": True,
            "override_upc": False,
            "override_upc_level": 1,
            "override_upc_category_filter": "ALL",
            "upc_target_length": 11,
            "upc_padding_pattern": "           ",
        },
        [
            "pad_arec",
            "arec_padding",
            "arec_padding_len",
            "append_arec",
            "append_arec_text",
            "invoice_date_custom_format",
            "invoice_date_custom_format_string",
            "invoice_date_offset",
            "force_txt_file_ext",
            "calc_upc",
            "retail_uom",
            "split_prepaid_sales_tax_crec",
            "override_upc",
            "override_upc_level",
            "override_upc_category_filter",
            "upc_target_length",
            "upc_padding_pattern",
        ],
    ),
]


@pytest.mark.parametrize(
    "plugin_cls,expected_enum,valid_config,expected_field_names", PLUGIN_CASES
)
def test_plugin_metadata_and_format_contract(
    plugin_cls, expected_enum, valid_config, expected_field_names
):
    assert issubclass(plugin_cls, ConfigurationPlugin)

    name = plugin_cls.get_name()
    identifier = plugin_cls.get_identifier()
    description = plugin_cls.get_description()
    version = plugin_cls.get_version()
    format_name = plugin_cls.get_format_name()
    format_enum = plugin_cls.get_format_enum()

    assert isinstance(name, str) and name.strip()
    assert isinstance(identifier, str) and identifier.strip()
    assert isinstance(description, str) and description.strip()
    assert isinstance(version, str) and version.strip()

    assert isinstance(format_name, str) and format_name.strip()
    assert isinstance(format_enum, ConvertFormat)
    assert format_enum is expected_enum
    assert isinstance(format_enum.value, str) and format_enum.value


@pytest.mark.parametrize(
    "plugin_cls,expected_enum,valid_config,expected_field_names", PLUGIN_CASES
)
def test_config_fields_and_schema_contract(
    plugin_cls, expected_enum, valid_config, expected_field_names
):
    fields = plugin_cls.get_config_fields()

    assert isinstance(fields, list)
    assert all(isinstance(field, FieldDefinition) for field in fields)
    assert [field.name for field in fields] == expected_field_names

    schema = plugin_cls.get_configuration_schema()
    if expected_field_names:
        assert isinstance(schema, ConfigurationSchema)
        assert [field.name for field in schema.fields] == expected_field_names
    else:
        assert schema is None

    plugin = plugin_cls()
    expected_defaults = {
        field.name: field.default for field in fields if field.default is not None
    }
    assert plugin.get_default_configuration() == expected_defaults


@pytest.mark.parametrize(
    "plugin_cls,expected_enum,valid_config,expected_field_names", PLUGIN_CASES
)
def test_plugin_config_round_trip_contract(
    plugin_cls, expected_enum, valid_config, expected_field_names
):
    plugin = plugin_cls()

    validation = plugin.validate_config(valid_config)
    assert isinstance(validation, ValidationResult)
    assert validation.success, validation.errors

    created_config = plugin.create_config(valid_config)
    assert created_config is not None

    serialized = plugin.serialize_config(created_config)
    assert isinstance(serialized, dict)
    assert set(serialized.keys()) == set(expected_field_names)

    deserialized = plugin.deserialize_config(serialized)
    assert deserialized is not None
    assert plugin.serialize_config(deserialized) == serialized

    plugin.initialize(valid_config)
    assert hasattr(plugin, "_config")
    assert plugin.serialize_config(plugin._config) == serialized

    plugin.activate()
    plugin.deactivate()


def test_tweaks_plugin_arec_padding_len_is_select_with_6_and_30():
    """Regression test: arec_padding_len must be SELECT with choices [6, 30], not INTEGER."""
    from interface.plugins.config_schemas import FieldType

    fields = TweaksConfigurationPlugin.get_config_fields()

    arec_len_field = next((f for f in fields if f.name == "arec_padding_len"), None)
    assert arec_len_field is not None, "arec_padding_len field not found"
    assert arec_len_field.field_type == FieldType.SELECT, (
        f"arec_padding_len must be FieldType.SELECT, got {arec_len_field.field_type}"
    )
    assert arec_len_field.choices == [
        {"label": "6", "value": 6},
        {"label": "30", "value": 30},
    ], f"arec_padding_len choices must be [6, 30], got {arec_len_field.choices}"
    assert arec_len_field.default == 6, (
        f"arec_padding_len default must be 6, got {arec_len_field.default}"
    )
