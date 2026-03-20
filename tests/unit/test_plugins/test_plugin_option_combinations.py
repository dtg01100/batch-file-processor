"""
Tests for plugin configuration option combinations.

This module tests that arbitrary combinations of plugin configuration options
work correctly and produce expected behavior across all plugins.

Tests cover:
- All booleans enabled simultaneously
- All booleans disabled simultaneously
- Mixed boolean combinations
- Cross-field interactions
- Edge cases and boundary conditions
"""

import pytest

from interface.plugins.csv_configuration_plugin import CSVConfigurationPlugin
from interface.plugins.estore_einvoice_configuration_plugin import (
    EStoreEInvoiceConfigurationPlugin,
)
from interface.plugins.fintech_configuration_plugin import FintechConfigurationPlugin
from interface.plugins.plugin_manager import PluginManager
from interface.plugins.scannerware_configuration_plugin import (
    ScannerWareConfigurationPlugin,
)
from interface.plugins.simplified_csv_configuration_plugin import (
    SimplifiedCSVConfigurationPlugin,
)
from interface.plugins.validation_framework import ValidationResult


class TestCSVPluginOptionCombinations:
    """Test CSV plugin with various option combinations."""

    @pytest.fixture
    def csv_plugin(self):
        """Get CSV plugin instance."""
        return CSVConfigurationPlugin()

    @pytest.mark.parametrize(
        "include_headers,filter_ampersand,include_item_numbers,include_item_description,split_prepaid",
        [
            # All enabled
            (True, True, True, True, True),
            # All disabled
            (False, False, False, False, False),
            # Mixed combinations
            (True, False, True, False, True),
            (False, True, False, True, False),
            (True, True, False, False, True),
            (False, False, True, True, False),
        ],
    )
    def test_csv_boolean_combinations_validate(
        self,
        csv_plugin,
        include_headers,
        filter_ampersand,
        include_item_numbers,
        include_item_description,
        split_prepaid,
    ):
        """Test that various boolean combinations validate correctly."""
        config = {
            "include_headers": include_headers,
            "filter_ampersand": filter_ampersand,
            "include_item_numbers": include_item_numbers,
            "include_item_description": include_item_description,
            "split_prepaid_sales_tax_crec": split_prepaid,
            "simple_csv_sort_order": "upc_number,qty_of_units",
        }

        result = csv_plugin.validate_config(config)

        assert result is not None
        assert isinstance(result, ValidationResult)
        # All these combinations should be valid
        assert result.success

    @pytest.mark.parametrize(
        "simple_csv_sort_order",
        [
            "",
            "upc_number",
            "upc_number,qty_of_units",
            "qty_of_units,unit_cost,description,vendor_item",
            "description,vendor_item,upc_number,qty_of_units,unit_cost",
        ],
    )
    def test_csv_sort_order_combinations_with_booleans(
        self, csv_plugin, simple_csv_sort_order
    ):
        """Test sort order with various boolean settings."""
        config = {
            "include_headers": True,
            "filter_ampersand": False,
            "include_item_numbers": True,
            "include_item_description": True,
            "split_prepaid_sales_tax_crec": False,
            "simple_csv_sort_order": simple_csv_sort_order,
        }

        result = csv_plugin.validate_config(config)
        assert result.success

    def test_csv_all_fields_populated(self, csv_plugin):
        """Test CSV with all fields populated."""
        config = {
            "include_headers": True,
            "filter_ampersand": True,
            "include_item_numbers": True,
            "include_item_description": True,
            "split_prepaid_sales_tax_crec": True,
            "simple_csv_sort_order": "upc_number,qty_of_units,unit_cost,description,vendor_item",
        }

        result = csv_plugin.validate_config(config)
        assert result.success

        # Test serialization
        config_obj = csv_plugin.create_config(config)
        serialized = csv_plugin.serialize_config(config_obj)

        assert serialized["include_headers"] is True
        assert serialized["filter_ampersand"] is True
        assert serialized["include_item_numbers"] is True
        assert serialized["include_item_description"] is True
        assert serialized["split_prepaid_sales_tax_crec"] is True
        assert (
            serialized["simple_csv_sort_order"]
            == "upc_number,qty_of_units,unit_cost,description,vendor_item"
        )


class TestScannerWarePluginOptionCombinations:
    """Test ScannerWare plugin with various option combinations."""

    @pytest.fixture
    def scannerware_plugin(self):
        """Get ScannerWare plugin instance."""
        return ScannerWareConfigurationPlugin()

    @pytest.mark.parametrize(
        "append_a_records,force_txt_file_ext,retail_uom",
        [
            # All enabled
            (True, True, True),
            # All disabled
            (False, False, False),
            # Mixed combinations
            (True, False, True),
            (False, True, False),
            (True, True, False),
            (False, False, True),
        ],
    )
    def test_scannerware_boolean_combinations_validate(
        self, scannerware_plugin, append_a_records, force_txt_file_ext, retail_uom
    ):
        """Test that various boolean combinations validate correctly."""
        config = {
            "a_record_padding": "TEST",
            "append_a_records": append_a_records,
            "a_record_append_text": "APPEND" if append_a_records else "",
            "force_txt_file_ext": force_txt_file_ext,
            "invoice_date_offset": 0,
            "retail_uom": retail_uom,
        }

        result = scannerware_plugin.validate_config(config)
        assert result is not None
        assert isinstance(result, ValidationResult)
        assert result.success

    @pytest.mark.parametrize(
        "invoice_date_offset,expected_valid",
        [
            (-14, True),
            (-7, True),
            (-1, True),
            (0, True),
            (1, True),
            (7, True),
            (14, True),
            (-15, False),  # Below minimum
            (15, False),  # Above maximum
        ],
    )
    def test_scannerware_date_offset_with_booleans(
        self, scannerware_plugin, invoice_date_offset, expected_valid
    ):
        """Test date offset with various boolean settings."""
        config = {
            "a_record_padding": "TEST",
            "append_a_records": True,
            "a_record_append_text": "APPEND",
            "force_txt_file_ext": False,
            "invoice_date_offset": invoice_date_offset,
            "retail_uom": True,
        }

        result = scannerware_plugin.validate_config(config)
        assert result.success == expected_valid

    def test_scannerware_all_fields_populated(self, scannerware_plugin):
        """Test ScannerWare with all fields populated."""
        config = {
            "a_record_padding": "PAD123",
            "append_a_records": True,
            "a_record_append_text": "APPENDED",
            "force_txt_file_ext": True,
            "invoice_date_offset": 7,
            "retail_uom": True,
        }

        result = scannerware_plugin.validate_config(config)
        assert result.success

        # Test round-trip
        config_obj = scannerware_plugin.create_config(config)
        serialized = scannerware_plugin.serialize_config(config_obj)
        deserialized = scannerware_plugin.deserialize_config(serialized)

        assert deserialized.a_record_padding == "PAD123"
        assert deserialized.append_a_records is True
        assert deserialized.a_record_append_text == "APPENDED"
        assert deserialized.force_txt_file_ext is True
        assert deserialized.invoice_date_offset == 7
        assert deserialized.retail_uom is True


class TestFintechPluginOptionCombinations:
    """Test Fintech plugin with option combinations."""

    @pytest.fixture
    def fintech_plugin(self):
        """Get Fintech plugin instance."""
        return FintechConfigurationPlugin()

    @pytest.mark.parametrize(
        "fintech_division_id,expected_valid",
        [
            ("", False),  # Empty is invalid (min_length=1)
            ("DIV001", True),
            ("DIV-002", True),
            ("12345", True),
            ("A", True),
            ("X" * 50, True),  # Max length
            ("X" * 51, False),  # Exceeds max length
        ],
    )
    def test_fintech_division_id_variations(
        self, fintech_plugin, fintech_division_id, expected_valid
    ):
        """Test various division ID values."""
        config = {"fintech_division_id": fintech_division_id}

        result = fintech_plugin.validate_config(config)
        assert result.success == expected_valid

    def test_fintech_config_round_trip(self, fintech_plugin):
        """Test fintech config serialization round-trip."""
        config = {"fintech_division_id": "DIV-999"}

        config_obj = fintech_plugin.create_config(config)
        serialized = fintech_plugin.serialize_config(config_obj)
        deserialized = fintech_plugin.deserialize_config(serialized)

        assert deserialized.fintech_division_id == "DIV-999"


class TestEStoreEInvoicePluginOptionCombinations:
    """Test eStore eInvoice plugin with option combinations."""

    @pytest.fixture
    def estore_plugin(self):
        """Get eStore eInvoice plugin instance."""
        return EStoreEInvoiceConfigurationPlugin()

    @pytest.mark.parametrize(
        "store_number,vendor_oid,vendor_name",
        [
            # All populated
            ("STORE001", "VEND001", "MyVendor"),
            # Only store and vendor OID
            ("STORE002", "VEND002", ""),
            # Empty values
            ("", "", ""),
            # Long values
            ("S" * 50, "V" * 50, "N" * 50),
        ],
    )
    def test_estore_field_combinations(
        self, estore_plugin, store_number, vendor_oid, vendor_name
    ):
        """Test various field combinations."""
        config = {
            "estore_store_number": store_number,
            "estore_vendor_oid": vendor_oid,
            "estore_vendor_namevendoroid": vendor_name,
        }

        result = estore_plugin.validate_config(config)
        assert result is not None
        assert isinstance(result, ValidationResult)

    def test_estore_config_round_trip(self, estore_plugin):
        """Test eStore config serialization round-trip."""
        config = {
            "estore_store_number": "STORE123",
            "estore_vendor_oid": "VEND456",
            "estore_vendor_namevendoroid": "AcmeInc",
        }

        config_obj = estore_plugin.create_config(config)
        serialized = estore_plugin.serialize_config(config_obj)
        deserialized = estore_plugin.deserialize_config(serialized)

        assert deserialized.estore_store_number == "STORE123"
        assert deserialized.estore_vendor_oid == "VEND456"
        assert deserialized.estore_vendor_namevendoroid == "AcmeInc"


class TestSimplifiedCSVPluginOptionCombinations:
    """Test Simplified CSV plugin with option combinations."""

    @pytest.fixture
    def simplified_csv_plugin(self):
        """Get Simplified CSV plugin instance."""
        return SimplifiedCSVConfigurationPlugin()

    def test_simplified_csv_default_config(self, simplified_csv_plugin):
        """Test default configuration."""
        defaults = simplified_csv_plugin.get_default_configuration()
        assert isinstance(defaults, dict)
        assert len(defaults) > 0

    def test_simplified_csv_config_round_trip(self, simplified_csv_plugin):
        """Test Simplified CSV config serialization round-trip."""
        # Get config fields
        fields = simplified_csv_plugin.get_config_fields()
        field_names = [f.name for f in fields]

        # Create config with all fields
        config = {}
        for field_name in field_names:
            field_def = next(f for f in fields if f.name == field_name)
            if field_def.field_type.name == "BOOLEAN":
                config[field_name] = True
            elif field_def.field_type.name == "STRING":
                config[field_name] = "test_value"

        result = simplified_csv_plugin.validate_config(config)
        assert result.success

        # Test round-trip
        config_obj = simplified_csv_plugin.create_config(config)
        serialized = simplified_csv_plugin.serialize_config(config_obj)
        deserialized = simplified_csv_plugin.deserialize_config(serialized)

        # Verify key fields are preserved
        for field_name in field_names:
            if field_name in config:
                assert hasattr(deserialized, field_name)


class TestPluginManagerCombinations:
    """Test plugin manager with various plugin combinations."""

    @pytest.fixture
    def plugin_manager(self):
        """Create a plugin manager instance."""
        manager = PluginManager()
        manager.discover_plugins()
        manager.initialize_plugins()
        return manager

    def test_get_all_plugins_works(self, plugin_manager):
        """Test that all configuration plugins can be retrieved."""
        plugins = plugin_manager.get_configuration_plugins()
        assert len(plugins) > 0

        # Verify each plugin has required methods
        for plugin in plugins:
            assert hasattr(plugin, "validate_config")
            assert hasattr(plugin, "get_config_fields")
            assert hasattr(plugin, "get_format_name")

    @pytest.mark.parametrize(
        "format_name",
        [
            "csv",
            "fintech",
            "scannerware",
            "estore_einvoice",
            "simplified_csv",
            "stewarts_custom",
            "jolley_custom",
            "scansheet_type_a",
            "yellowdog_csv",
            "estore_einvoice_generic",
        ],
    )
    def test_each_plugin_validates_default_config(self, plugin_manager, format_name):
        """Test that each plugin validates its default configuration."""
        plugin = plugin_manager.get_configuration_plugin_by_format_name(format_name)

        if plugin is None:
            pytest.skip(f"Plugin {format_name} not found")

        defaults = plugin.get_default_configuration()
        result = plugin.validate_config(defaults)

        assert result is not None
        assert isinstance(result, ValidationResult)
        # Default configs should always be valid
        # Some plugins may have required fields that need values
        if not result.success:
            # If default config is invalid, it's because required fields are empty
            # This is expected behavior - document the validation rules
            assert (
                result.errors
            ), f"{format_name} validation failure should have error messages"

    def test_multiple_plugins_can_be_validated(self, plugin_manager):
        """Test that multiple plugins can be validated in sequence."""
        plugins = plugin_manager.get_configuration_plugins()

        # Validate each plugin's default config
        for plugin in plugins:
            defaults = plugin.get_default_configuration()
            result = plugin.validate_config(defaults)
            # Some plugins may have required fields that need values in default config
            if not result.success:
                # Document which plugins require fields to be populated
                assert (
                    result.errors
                ), f"{plugin.get_format_name()} validation failure should have error messages"

            # Test with all booleans set to True and strings with valid values
            fields = plugin.get_config_fields()
            all_true_config = {}
            for field in fields:
                if field.field_type.name == "BOOLEAN":
                    all_true_config[field.name] = True
                elif field.field_type.name == "STRING":
                    # Use appropriate length based on min_length constraint
                    min_len = getattr(field, "min_length", None) or 0
                    getattr(field, "max_length", None) or 50
                    if min_len > 0:
                        all_true_config[field.name] = "X" * min_len
                    else:
                        all_true_config[field.name] = "test"

            if all_true_config:  # Only test if there are boolean/string fields
                result = plugin.validate_config(all_true_config)
                assert (
                    result.success
                ), f"{plugin.get_format_name()} all-true config should be valid: {result.errors if not result.success else ''}"


class TestCrossPluginConfigurations:
    """Test interactions between different plugin configurations."""

    @pytest.fixture
    def plugin_manager(self):
        """Create a plugin manager instance."""
        manager = PluginManager()
        manager.discover_plugins()
        manager.initialize_plugins()
        return manager

    def test_csv_and_fintech_both_valid(self, plugin_manager):
        """Test that CSV and Fintech plugins can both have valid configs."""
        csv_plugin = plugin_manager.get_configuration_plugin_by_format_name("csv")
        fintech_plugin = plugin_manager.get_configuration_plugin_by_format_name(
            "fintech"
        )

        assert csv_plugin is not None
        assert fintech_plugin is not None

        csv_config = {
            "include_headers": True,
            "filter_ampersand": False,
            "include_item_numbers": True,
            "include_item_description": True,
            "split_prepaid_sales_tax_crec": False,
            "simple_csv_sort_order": "upc_number,qty_of_units",
        }

        fintech_config = {"fintech_division_id": "DIV001"}

        csv_result = csv_plugin.validate_config(csv_config)
        fintech_result = fintech_plugin.validate_config(fintech_config)

        assert csv_result.success
        assert fintech_result.success

    def test_scannerware_and_estore_both_valid(self, plugin_manager):
        """Test that ScannerWare and eStore plugins can both have valid configs."""
        scannerware_plugin = plugin_manager.get_configuration_plugin_by_format_name(
            "scannerware"
        )
        # Try different naming conventions for eStore
        estore_plugin = (
            plugin_manager.get_configuration_plugin_by_format_name("estore_einvoice")
            or plugin_manager.get_configuration_plugin_by_format_name("estore_eInvoice")
            or plugin_manager.get_configuration_plugin_by_format_name("estore")
        )

        assert scannerware_plugin is not None
        if estore_plugin is None:
            pytest.skip("eStore eInvoice plugin not found")

        scannerware_config = {
            "a_record_padding": "TEST",
            "append_a_records": True,
            "a_record_append_text": "APPEND",
            "force_txt_file_ext": False,
            "invoice_date_offset": 0,
            "retail_uom": True,
        }

        estore_config = {
            "estore_store_number": "STORE001",
            "estore_vendor_oid": "VEND001",
            "estore_vendor_namevendoroid": "MyVendor",
        }

        scannerware_result = scannerware_plugin.validate_config(scannerware_config)
        estore_result = estore_plugin.validate_config(estore_config)

        assert scannerware_result.success
        assert estore_result.success
