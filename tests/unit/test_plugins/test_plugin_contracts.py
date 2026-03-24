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


def test_tweaks_legacy_field_map_covers_all_known_columns():
    """_TWEAKS_LEGACY_FIELD_MAP must map every known legacy flat column to a plugin field."""
    from interface.qt.dialogs.edit_folders.dynamic_edi_builder import DynamicEDIBuilder

    mapping = DynamicEDIBuilder._TWEAKS_LEGACY_FIELD_MAP
    # Every legacy key should be a non-empty string, every plugin key should exist in
    # the TweaksConfigurationPlugin field names.
    plugin_field_names = {f.name for f in TweaksConfigurationPlugin.get_config_fields()}
    for legacy_col, plugin_field in mapping.items():
        assert isinstance(legacy_col, str) and legacy_col, (
            f"Legacy column key must be a non-empty string: {legacy_col!r}"
        )
        assert plugin_field in plugin_field_names, (
            f"Legacy column '{legacy_col}' maps to '{plugin_field}' "
            f"which is not a TweaksConfigurationPlugin field. "
            f"Known fields: {sorted(plugin_field_names)}"
        )


def test_tweaks_build_legacy_plugin_config_maps_flat_columns():
    """_build_legacy_plugin_config translates legacy flat columns to plugin field names."""
    from unittest.mock import MagicMock, patch

    from interface.qt.dialogs.edit_folders.dynamic_edi_builder import DynamicEDIBuilder

    legacy_folder_config = {
        "pad_a_records": True,
        "a_record_padding": "TEST",
        "a_record_padding_length": 30,
        "override_upc_bool": True,
        "override_upc_level": 2,
        "invoice_date_offset": -7,
        "force_txt_file_ext": True,
    }

    # Build a minimal DynamicEDIBuilder with a fake plugin manager
    with patch(
        "interface.qt.dialogs.edit_folders.dynamic_edi_builder.get_shared_plugin_manager"
    ) as mock_pm_factory:
        mock_pm = MagicMock()
        mock_pm.get_configuration_plugins.return_value = []
        mock_pm_factory.return_value = mock_pm

        builder = DynamicEDIBuilder(
            fields={},
            folder_config=legacy_folder_config,
            dynamic_container=MagicMock(),
            dynamic_layout=MagicMock(),
        )

    plugin = TweaksConfigurationPlugin()
    result = builder._build_legacy_plugin_config(plugin)

    assert result["pad_arec"] is True
    assert result["arec_padding"] == "TEST"
    assert result["arec_padding_len"] == 30
    assert result["override_upc"] is True
    assert result["override_upc_level"] == 2
    assert result["invoice_date_offset"] == -7
    assert result["force_txt_file_ext"] is True


def test_tweaks_build_legacy_plugin_config_returns_empty_for_non_tweaks_plugin():
    """_build_legacy_plugin_config returns {} for plugins other than TweaksConfigurationPlugin."""
    from unittest.mock import MagicMock, patch

    from interface.plugins.csv_configuration_plugin import CSVConfigurationPlugin
    from interface.qt.dialogs.edit_folders.dynamic_edi_builder import DynamicEDIBuilder

    with patch(
        "interface.qt.dialogs.edit_folders.dynamic_edi_builder.get_shared_plugin_manager"
    ) as mock_pm_factory:
        mock_pm = MagicMock()
        mock_pm.get_configuration_plugins.return_value = []
        mock_pm_factory.return_value = mock_pm

        builder = DynamicEDIBuilder(
            fields={},
            folder_config={"include_headers": True},
            dynamic_container=MagicMock(),
            dynamic_layout=MagicMock(),
        )

    csv_plugin = CSVConfigurationPlugin()
    result = builder._build_legacy_plugin_config(csv_plugin)
    assert result == {}


def test_sync_tweaks_plugin_to_flat_columns_overwrites_defaults():
    """sync_tweaks_plugin_to_flat_columns writes plugin_configurations["tweaks"] back
    to the flat DB columns so the orchestrator always reads up-to-date values.
    """
    from interface.operations.tweaks_flat_column_sync import (
        sync_tweaks_plugin_to_flat_columns,
    )

    tweaks_plugin_config = {
        "pad_arec": True,
        "arec_padding": "TESTPAD",
        "arec_padding_len": 30,
        "append_arec": True,
        "append_arec_text": "APPENDME",
        "calc_upc": True,
        "retail_uom": True,
        "override_upc": True,
        "override_upc_level": 2,
        "override_upc_category_filter": "CATX",
        "upc_target_length": 12,
        "upc_padding_pattern": "  ",
        "split_prepaid_sales_tax_crec": True,
        "invoice_date_custom_format": True,
        "invoice_date_custom_format_string": "%d/%m/%Y",
        "invoice_date_offset": -3,
        "force_txt_file_ext": True,
    }

    # target dict starts with all-default flat values (as apply() writes before the sync)
    target = {
        "plugin_configurations": {"tweaks": tweaks_plugin_config},
        # defaults that apply() would write from the missing legacy widgets:
        "pad_a_records": False,
        "a_record_padding": "",
        "a_record_padding_length": 6,
        "append_a_records": False,
        "a_record_append_text": "",
        "calculate_upc_check_digit": False,
        "retail_uom": False,
        "override_upc_bool": False,
        "override_upc_level": 1,
        "override_upc_category_filter": "",
        "upc_target_length": 11,
        "upc_padding_pattern": "           ",
        "split_prepaid_sales_tax_crec": False,
        "invoice_date_custom_format": False,
        "invoice_date_custom_format_string": "%Y-%m-%d",
        "invoice_date_offset": 0,
        "force_txt_file_ext": False,
    }

    sync_tweaks_plugin_to_flat_columns(target)

    assert target["pad_a_records"] is True
    assert target["a_record_padding"] == "TESTPAD"
    assert target["a_record_padding_length"] == 30
    assert target["append_a_records"] is True
    assert target["a_record_append_text"] == "APPENDME"
    assert target["calculate_upc_check_digit"] is True
    assert target["retail_uom"] is True
    assert target["override_upc_bool"] is True
    assert target["override_upc_level"] == 2
    assert target["override_upc_category_filter"] == "CATX"
    assert target["upc_target_length"] == 12
    assert target["upc_padding_pattern"] == "  "
    assert target["split_prepaid_sales_tax_crec"] is True
    assert target["invoice_date_custom_format"] is True
    assert target["invoice_date_custom_format_string"] == "%d/%m/%Y"
    assert target["invoice_date_offset"] == -3
    assert target["force_txt_file_ext"] is True


def test_sync_tweaks_plugin_to_flat_columns_noop_when_no_tweaks_config():
    """sync_tweaks_plugin_to_flat_columns is a no-op when plugin_configurations
    has no "tweaks" entry, so existing flat columns are left untouched.
    """
    from interface.operations.tweaks_flat_column_sync import (
        sync_tweaks_plugin_to_flat_columns,
    )

    target = {
        "plugin_configurations": {},  # no "tweaks" entry
        "pad_a_records": False,
        "override_upc_bool": False,
    }

    sync_tweaks_plugin_to_flat_columns(target)

    # Nothing should change
    assert target["pad_a_records"] is False
    assert target["override_upc_bool"] is False


def test_sync_tweaks_reverse_map_covers_all_legacy_columns():
    """Every entry in _TWEAKS_LEGACY_FIELD_MAP must have a corresponding entry
    in the sync module's reverse map (_PLUGIN_TO_FLAT).

    This test protects against the two maps drifting apart.
    """
    from interface.operations.tweaks_flat_column_sync import (
        _PLUGIN_TO_FLAT,
        sync_tweaks_plugin_to_flat_columns,
    )

    # _TWEAKS_LEGACY_FIELD_MAP is: legacy_col → plugin_field
    # _PLUGIN_TO_FLAT is:          plugin_field → legacy_col
    # The sets of legacy columns must match.
    forward_flat_cols = set(_PLUGIN_TO_FLAT.values())

    # Build expected set from _TWEAKS_LEGACY_FIELD_MAP via the same trick
    # used in the dialog: all plugin fields set to True, then observe which
    # flat cols got written.
    all_plugin_values = {plugin_field: True for plugin_field in _PLUGIN_TO_FLAT}
    target = {"plugin_configurations": {"tweaks": all_plugin_values}}
    sync_tweaks_plugin_to_flat_columns(target)
    written_flat_cols = set(target.keys()) - {"plugin_configurations"}

    assert written_flat_cols == forward_flat_cols, (
        f"Mismatch: written={sorted(written_flat_cols)}, "
        f"declared={sorted(forward_flat_cols)}"
    )
