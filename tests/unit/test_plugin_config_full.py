"""
Supplementary comprehensive unit tests for plugin_config.py module.

Tests additional functionality not covered in tests/test_plugin_config.py.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from plugin_config import ConfigField, PluginConfigMixin, PluginRegistry, get_plugin_config


class TestConfigFieldValidation(unittest.TestCase):
    """Tests for ConfigField validation."""

    def test_boolean_field_must_have_boolean_default(self):
        """Test boolean field requires boolean default."""
        with self.assertRaises(ValueError) as context:
            ConfigField(
                key="test_bool",
                label="Test Boolean",
                type="boolean",
                default="not_a_boolean"
            )

        self.assertIn("boolean", str(context.exception))

    def test_select_field_must_have_options(self):
        """Test select field requires options."""
        with self.assertRaises(ValueError) as context:
            ConfigField(
                key="test_select",
                label="Test Select",
                type="select",
                default="",
                options=[]
            )

        self.assertIn("options", str(context.exception))

    def test_select_field_with_options_succeeds(self):
        """Test select field with options succeeds."""
        field = ConfigField(
            key="test_select",
            label="Test Select",
            type="select",
            default="option1",
            options=["option1", "option2", "option3"]
        )

        self.assertEqual(field.options, ["option1", "option2", "option3"])

    def test_field_from_dict_complete(self):
        """Test creating ConfigField from complete dictionary."""
        data = {
            "key": "complete_field",
            "label": "Complete Field",
            "type": "integer",
            "default": 50,
            "required": True,
            "help": "Help text",
            "options": [],
            "min_value": 0,
            "max_value": 100,
            "placeholder": "Enter value",
            "validator": r"^\d+$",
            "visible_if": {"other_field": "value"}
        }

        field = ConfigField.from_dict(data)

        self.assertEqual(field.key, "complete_field")
        self.assertEqual(field.type, "integer")
        self.assertEqual(field.default, 50)
        self.assertTrue(field.required)
        self.assertEqual(field.help, "Help text")
        self.assertEqual(field.min_value, 0)
        self.assertEqual(field.max_value, 100)
        self.assertEqual(field.placeholder, "Enter value")
        self.assertEqual(field.validator, r"^\d+$")
        self.assertEqual(field.visible_if, {"other_field": "value"})

    def test_field_to_dict(self):
        """Test converting ConfigField to dictionary."""
        field = ConfigField(
            key="test_field",
            label="Test Field",
            type="string",
            default="default_value",
            required=True,
            help="Help text"
        )

        data = field.to_dict()

        self.assertEqual(data["key"], "test_field")
        self.assertEqual(data["type"], "string")
        self.assertEqual(data["default"], "default_value")
        self.assertTrue(data["required"])
        self.assertEqual(data["help"], "Help text")


class TestPluginConfigMixinValidation(unittest.TestCase):
    """Tests for PluginConfigMixin validation."""

    def test_validate_config_required_field_present(self):
        """Test validation with required field present."""
        class TestPlugin(PluginConfigMixin):
            CONFIG_FIELDS = [
                {
                    "key": "required_field",
                    "label": "Required Field",
                    "type": "string",
                    "default": "",
                    "required": True
                }
            ]

        valid, errors = TestPlugin.validate_config({"required_field": "value"})

        self.assertTrue(valid)
        self.assertEqual(errors, [])

    def test_validate_config_required_field_missing(self):
        """Test validation with required field missing."""
        class TestPlugin(PluginConfigMixin):
            CONFIG_FIELDS = [
                {
                    "key": "required_field",
                    "label": "Required Field",
                    "type": "string",
                    "default": "",
                    "required": True
                }
            ]

        valid, errors = TestPlugin.validate_config({})

        self.assertFalse(valid)
        self.assertEqual(len(errors), 1)
        self.assertIn("required", errors[0].lower())

    def test_validate_config_integer_bounds(self):
        """Test validation of integer field bounds."""
        class TestPlugin(PluginConfigMixin):
            CONFIG_FIELDS = [
                {
                    "key": "int_field",
                    "label": "Integer Field",
                    "type": "integer",
                    "default": 10,
                    "min_value": 0,
                    "max_value": 100
                }
            ]

        # Valid value
        valid, errors = TestPlugin.validate_config({"int_field": 50})
        self.assertTrue(valid)

        # Below minimum
        valid, errors = TestPlugin.validate_config({"int_field": -5})
        self.assertFalse(valid)

        # Above maximum
        valid, errors = TestPlugin.validate_config({"int_field": 150})
        self.assertFalse(valid)

    def test_validate_config_float_bounds(self):
        """Test validation of float field bounds."""
        class TestPlugin(PluginConfigMixin):
            CONFIG_FIELDS = [
                {
                    "key": "float_field",
                    "label": "Float Field",
                    "type": "float",
                    "default": 1.5,
                    "min_value": 0.0,
                    "max_value": 10.0
                }
            ]

        # Valid value
        valid, errors = TestPlugin.validate_config({"float_field": 5.5})
        self.assertTrue(valid)

        # Below minimum
        valid, errors = TestPlugin.validate_config({"float_field": -1.0})
        self.assertFalse(valid)

        # Above maximum
        valid, errors = TestPlugin.validate_config({"float_field": 15.0})
        self.assertFalse(valid)

    def test_validate_config_boolean_type(self):
        """Test validation of boolean field type."""
        class TestPlugin(PluginConfigMixin):
            CONFIG_FIELDS = [
                {
                    "key": "bool_field",
                    "label": "Boolean Field",
                    "type": "boolean",
                    "default": False
                }
            ]

        # Valid boolean
        valid, errors = TestPlugin.validate_config({"bool_field": True})
        self.assertTrue(valid)

        # Invalid type
        valid, errors = TestPlugin.validate_config({"bool_field": "true"})
        self.assertFalse(valid)

    def test_validate_config_select_valid_option(self):
        """Test validation of select field with valid option."""
        class TestPlugin(PluginConfigMixin):
            CONFIG_FIELDS = [
                {
                    "key": "select_field",
                    "label": "Select Field",
                    "type": "select",
                    "default": "option1",
                    "options": ["option1", "option2", "option3"]
                }
            ]

        # Valid option
        valid, errors = TestPlugin.validate_config({"select_field": "option2"})
        self.assertTrue(valid)

        # Invalid option
        valid, errors = TestPlugin.validate_config({"select_field": "invalid"})
        self.assertFalse(valid)

    def test_validate_config_select_with_tuple_options(self):
        """Test validation of select field with tuple options."""
        class TestPlugin(PluginConfigMixin):
            CONFIG_FIELDS = [
                {
                    "key": "select_field",
                    "label": "Select Field",
                    "type": "select",
                    "default": "opt1",
                    "options": [("opt1", "Option 1"), ("opt2", "Option 2")]
                }
            ]

        # Valid option (first element of tuple)
        valid, errors = TestPlugin.validate_config({"select_field": "opt1"})
        self.assertTrue(valid)

    def test_get_config_value_from_parameters(self):
        """Test getting config value from parameters_dict."""
        class TestPlugin(PluginConfigMixin):
            CONFIG_FIELDS = [
                {"key": "param1", "label": "Param1", "type": "string", "default": "default1"}
            ]

        plugin = TestPlugin()
        plugin.parameters_dict = {"param1": "custom_value", "param2": "extra"}

        value = plugin.get_config_value("param1")
        self.assertEqual(value, "custom_value")

    def test_get_config_value_default(self):
        """Test getting config value returns default if not found."""
        class TestPlugin(PluginConfigMixin):
            CONFIG_FIELDS = []

        plugin = TestPlugin()
        plugin.parameters_dict = {}

        value = plugin.get_config_value("nonexistent", "fallback")
        self.assertEqual(value, "fallback")

    def test_get_config_value_no_parameters_dict(self):
        """Test getting config value when parameters_dict doesn't exist."""
        class TestPlugin(PluginConfigMixin):
            CONFIG_FIELDS = []

        plugin = TestPlugin()
        # Don't set parameters_dict

        value = plugin.get_config_value("key", "default")
        self.assertEqual(value, "default")


class TestPluginRegistry(unittest.TestCase):
    """Tests for PluginRegistry class."""

    def setUp(self):
        """Clear registry before each test."""
        PluginRegistry._convert_plugins.clear()
        PluginRegistry._send_plugins.clear()

    def tearDown(self):
        """Clear registry after each test."""
        PluginRegistry._convert_plugins.clear()
        PluginRegistry._send_plugins.clear()

    def test_register_convert_plugin_requires_plugin_id(self):
        """Test registering convert plugin requires PLUGIN_ID."""
        class NoPluginID:
            pass

        with self.assertRaises(ValueError) as context:
            PluginRegistry.register_convert_plugin(NoPluginID)

        self.assertIn("PLUGIN_ID", str(context.exception))

    def test_register_send_plugin_requires_plugin_id(self):
        """Test registering send plugin requires PLUGIN_ID."""
        class NoPluginID:
            pass

        with self.assertRaises(ValueError) as context:
            PluginRegistry.register_send_plugin(NoPluginID)

        self.assertIn("PLUGIN_ID", str(context.exception))

    def test_register_convert_plugin_with_none_plugin_id(self):
        """Test registering convert plugin with None PLUGIN_ID fails."""
        class NonePluginID:
            PLUGIN_ID = None

        with self.assertRaises(ValueError):
            PluginRegistry.register_convert_plugin(NonePluginID)

    def test_get_convert_plugin_not_found(self):
        """Test getting non-existent convert plugin returns None."""
        result = PluginRegistry.get_convert_plugin("nonexistent")
        self.assertIsNone(result)

    def test_get_send_plugin_not_found(self):
        """Test getting non-existent send plugin returns None."""
        result = PluginRegistry.get_send_plugin("nonexistent")
        self.assertIsNone(result)

    def test_list_convert_plugins_empty(self):
        """Test listing convert plugins when empty."""
        plugins = PluginRegistry.list_convert_plugins()
        self.assertEqual(plugins, [])

    def test_list_send_plugins_empty(self):
        """Test listing send plugins when empty."""
        plugins = PluginRegistry.list_send_plugins()
        self.assertEqual(plugins, [])

    def test_list_convert_plugins_sorted(self):
        """Test convert plugins are sorted by ID."""
        class PluginB:
            PLUGIN_ID = "b_plugin"
            PLUGIN_NAME = "Plugin B"
            PLUGIN_DESCRIPTION = "Description B"

        class PluginA:
            PLUGIN_ID = "a_plugin"
            PLUGIN_NAME = "Plugin A"
            PLUGIN_DESCRIPTION = "Description A"

        PluginRegistry.register_convert_plugin(PluginB)
        PluginRegistry.register_convert_plugin(PluginA)

        plugins = PluginRegistry.list_convert_plugins()

        # Should be sorted by PLUGIN_ID
        self.assertEqual(plugins[0][0], "a_plugin")
        self.assertEqual(plugins[1][0], "b_plugin")

    def test_list_send_plugins_sorted(self):
        """Test send plugins are sorted by ID."""
        class SendB:
            PLUGIN_ID = "b_send"
            PLUGIN_NAME = "Send B"
            PLUGIN_DESCRIPTION = "Description B"

        class SendA:
            PLUGIN_ID = "a_send"
            PLUGIN_NAME = "Send A"
            PLUGIN_DESCRIPTION = "Description A"

        PluginRegistry.register_send_plugin(SendB)
        PluginRegistry.register_send_plugin(SendA)

        plugins = PluginRegistry.list_send_plugins()

        # Should be sorted by PLUGIN_ID
        self.assertEqual(plugins[0][0], "a_send")
        self.assertEqual(plugins[1][0], "b_send")

    @patch('glob.glob')
    @patch('importlib.import_module')
    def test_discover_plugins_skips_send_base(self, mock_import, mock_glob):
        """Test discover_plugins skips send_base.py."""
        mock_glob.side_effect = [
            [],  # No convert plugins
            ['send_base.py', 'email_backend.py']  # send_base should be skipped
        ]

        # Mock the email_backend module
        mock_module = MagicMock()
        mock_import.return_value = mock_module

        PluginRegistry.discover_plugins()

        # Should not try to import send_base
        calls = [call for call in mock_import.call_args_list if 'send_base' in str(call)]
        self.assertEqual(len(calls), 0)


class TestGetPluginConfig(unittest.TestCase):
    """Tests for get_plugin_config function."""

    def setUp(self):
        """Clear registry before each test."""
        PluginRegistry._convert_plugins.clear()
        PluginRegistry._send_plugins.clear()

    def tearDown(self):
        """Clear registry after each test."""
        PluginRegistry._convert_plugins.clear()
        PluginRegistry._send_plugins.clear()

    def test_get_convert_plugin_config(self):
        """Test getting config for convert plugin."""
        class TestConverter(PluginConfigMixin):
            PLUGIN_ID = "test_converter"
            PLUGIN_NAME = "Test Converter"
            PLUGIN_DESCRIPTION = "Test"
            CONFIG_FIELDS = [
                {"key": "param1", "label": "Param1", "type": "string", "default": "value1"}
            ]

        PluginRegistry.register_convert_plugin(TestConverter)

        fields = get_plugin_config("convert", "test_converter")

        self.assertIsNotNone(fields)
        self.assertEqual(len(fields), 1)
        self.assertEqual(fields[0].key, "param1")

    def test_get_send_plugin_config(self):
        """Test getting config for send plugin."""
        class TestSender(PluginConfigMixin):
            PLUGIN_ID = "test_sender"
            PLUGIN_NAME = "Test Sender"
            PLUGIN_DESCRIPTION = "Test"
            CONFIG_FIELDS = [
                {"key": "param1", "label": "Param1", "type": "string", "default": "value1"}
            ]

        PluginRegistry.register_send_plugin(TestSender)

        fields = get_plugin_config("send", "test_sender")

        self.assertIsNotNone(fields)
        self.assertEqual(len(fields), 1)

    def test_get_plugin_config_invalid_type(self):
        """Test getting config with invalid plugin type."""
        with self.assertRaises(ValueError):
            get_plugin_config("invalid", "plugin_id")  # type: ignore

    def test_get_plugin_config_not_found(self):
        """Test getting config for non-existent plugin."""
        result = get_plugin_config("convert", "nonexistent")
        self.assertIsNone(result)


class TestPluginConfigMixinWithDictFields(unittest.TestCase):
    """Tests for PluginConfigMixin with dict-style field definitions."""

    def test_mixed_field_types(self):
        """Test mixin with mix of dict and ConfigField objects."""
        class TestPlugin(PluginConfigMixin):
            CONFIG_FIELDS = [
                {"key": "dict_field", "label": "Dict Field", "type": "string", "default": ""},
                ConfigField(key="object_field", label="Object Field", type="boolean", default=True)
            ]

        fields = TestPlugin.get_config_fields()

        self.assertEqual(len(fields), 2)
        self.assertEqual(fields[0].key, "dict_field")
        self.assertEqual(fields[1].key, "object_field")

    def test_invalid_field_type_raises(self):
        """Test that invalid field type raises TypeError."""
        class TestPlugin(PluginConfigMixin):
            CONFIG_FIELDS = ["invalid_field_definition"]

        with self.assertRaises(TypeError):
            TestPlugin.get_config_fields()


if __name__ == '__main__':
    unittest.main()
