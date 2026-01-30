"""Tests for plugin_config module."""

import os
import sys
import unittest
from typing import Any, Dict

import pytest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from plugin_config import ConfigField, PluginConfigMixin


class TestConfigField(unittest.TestCase):
    """Tests for ConfigField dataclass."""

    def test_basic_field_creation(self):
        """Test creating a basic config field."""
        field = ConfigField(
            key="test_field", label="Test Field", type="string", default="default_value"
        )
        assert field.key == "test_field"
        assert field.label == "Test Field"
        assert field.type == "string"
        assert field.default == "default_value"
        assert field.required is False

    def test_boolean_field_validation(self):
        """Test boolean field requires boolean default."""
        with pytest.raises(ValueError, match="must have boolean default"):
            ConfigField(
                key="bool_field", label="Boolean", type="boolean", default="not_a_bool"
            )

    def test_boolean_field_with_valid_default(self):
        """Test boolean field with valid default."""
        field = ConfigField(
            key="bool_field", label="Boolean", type="boolean", default=True
        )
        assert field.default is True

    def test_select_field_requires_options(self):
        """Test select field requires options."""
        with pytest.raises(ValueError, match="must have options"):
            ConfigField(
                key="select_field",
                label="Select",
                type="select",
                default="option1",
                options=[],
            )

    def test_select_field_with_options(self):
        """Test select field with valid options."""
        field = ConfigField(
            key="select_field",
            label="Select",
            type="select",
            default="option1",
            options=["option1", "option2", "option3"],
        )
        assert field.options == ["option1", "option2", "option3"]

    def test_field_from_dict(self):
        """Test creating field from dictionary."""
        field_dict = {
            "key": "test_key",
            "label": "Test Label",
            "type": "integer",
            "default": 42,
            "required": True,
            "help": "Help text",
            "min_value": 0,
            "max_value": 100,
        }
        field = ConfigField.from_dict(field_dict)
        assert field.key == "test_key"
        assert field.label == "Test Label"
        assert field.default == 42
        assert field.required is True
        assert field.min_value == 0
        assert field.max_value == 100

    def test_field_to_dict(self):
        """Test converting field to dictionary."""
        field = ConfigField(
            key="test_key",
            label="Test Label",
            type="string",
            default="test",
            required=True,
            help="Test help",
        )
        field_dict = field.to_dict()
        assert field_dict["key"] == "test_key"
        assert field_dict["label"] == "Test Label"
        assert field_dict["type"] == "string"
        assert field_dict["default"] == "test"
        assert field_dict["required"] is True
        assert field_dict["help"] == "Test help"

    def test_numeric_field_with_ranges(self):
        """Test numeric field with min/max values."""
        field = ConfigField(
            key="numeric",
            label="Numeric",
            type="integer",
            default=50,
            min_value=0,
            max_value=100,
        )
        assert field.min_value == 0
        assert field.max_value == 100

    def test_field_with_validator(self):
        """Test field with custom validator."""
        field = ConfigField(
            key="email",
            label="Email",
            type="string",
            default="",
            validator=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        )
        assert field.validator is not None

    def test_field_with_visible_if(self):
        """Test field with conditional visibility."""
        field = ConfigField(
            key="dependent_field",
            label="Dependent",
            type="string",
            default="",
            visible_if={"enable_feature": True},
        )
        assert field.visible_if == {"enable_feature": True}


class TestPluginConfigMixin(unittest.TestCase):
    """Tests for PluginConfigMixin."""

    def test_get_config_fields_from_dicts(self):
        """Test getting config fields defined as dictionaries."""

        class TestPlugin(PluginConfigMixin):
            PLUGIN_ID = "test"
            PLUGIN_NAME = "Test Plugin"
            CONFIG_FIELDS = [
                {
                    "key": "field1",
                    "label": "Field 1",
                    "type": "string",
                    "default": "value1",
                },
                {
                    "key": "field2",
                    "label": "Field 2",
                    "type": "boolean",
                    "default": False,
                },
            ]

        fields = TestPlugin.get_config_fields()
        assert len(fields) == 2
        assert fields[0].key == "field1"
        assert fields[1].key == "field2"

    def test_get_config_fields_from_objects(self):
        """Test getting config fields defined as ConfigField objects."""

        class TestPlugin(PluginConfigMixin):
            PLUGIN_ID = "test"
            PLUGIN_NAME = "Test Plugin"
            CONFIG_FIELDS = [
                ConfigField(
                    key="field1", label="Field 1", type="string", default="value1"
                ),
                ConfigField(
                    key="field2", label="Field 2", type="boolean", default=False
                ),
            ]

        fields = TestPlugin.get_config_fields()
        assert len(fields) == 2
        assert isinstance(fields[0], ConfigField)
        assert isinstance(fields[1], ConfigField)

    def test_get_default_config(self):
        """Test getting default configuration values."""

        class TestPlugin(PluginConfigMixin):
            CONFIG_FIELDS = [
                ConfigField(
                    key="field1", label="Field 1", type="string", default="default1"
                ),
                ConfigField(key="field2", label="Field 2", type="integer", default=42),
                ConfigField(
                    key="field3", label="Field 3", type="boolean", default=True
                ),
            ]

        defaults = TestPlugin.get_default_config()
        assert defaults == {"field1": "default1", "field2": 42, "field3": True}

    def test_validate_config_required_field(self):
        """Test validation of required fields."""

        class TestPlugin(PluginConfigMixin):
            CONFIG_FIELDS = [
                ConfigField(
                    key="required_field",
                    label="Required",
                    type="string",
                    default="",
                    required=True,
                )
            ]

        valid, errors = TestPlugin.validate_config({})
        assert not valid
        assert len(errors) == 1
        assert "Required is required" in errors

    def test_validate_config_boolean_type(self):
        """Test validation of boolean type."""

        class TestPlugin(PluginConfigMixin):
            CONFIG_FIELDS = [
                ConfigField(
                    key="bool_field",
                    label="Boolean Field",
                    type="boolean",
                    default=False,
                )
            ]

        valid, errors = TestPlugin.validate_config({"bool_field": "not_bool"})
        assert not valid
        assert "Boolean Field must be a boolean" in errors

    def test_validate_config_integer_type(self):
        """Test validation of integer type."""

        class TestPlugin(PluginConfigMixin):
            CONFIG_FIELDS = [
                ConfigField(
                    key="int_field", label="Integer Field", type="integer", default=0
                )
            ]

        # Valid integer
        valid, errors = TestPlugin.validate_config({"int_field": 42})
        assert valid
        assert len(errors) == 0

        # Invalid integer
        valid, errors = TestPlugin.validate_config({"int_field": "not_int"})
        assert not valid
        assert "Integer Field must be an integer" in errors

    def test_validate_config_integer_range(self):
        """Test validation of integer min/max values."""

        class TestPlugin(PluginConfigMixin):
            CONFIG_FIELDS = [
                ConfigField(
                    key="ranged_int",
                    label="Ranged Integer",
                    type="integer",
                    default=50,
                    min_value=0,
                    max_value=100,
                )
            ]

        # Below minimum
        valid, errors = TestPlugin.validate_config({"ranged_int": -1})
        assert not valid
        assert "must be at least 0" in errors[0]

        # Above maximum
        valid, errors = TestPlugin.validate_config({"ranged_int": 101})
        assert not valid
        assert "must be at most 100" in errors[0]

        # Within range
        valid, errors = TestPlugin.validate_config({"ranged_int": 50})
        assert valid

    def test_validate_config_float_type(self):
        """Test validation of float type."""

        class TestPlugin(PluginConfigMixin):
            CONFIG_FIELDS = [
                ConfigField(
                    key="float_field", label="Float Field", type="float", default=0.0
                )
            ]

        # Valid float
        valid, errors = TestPlugin.validate_config({"float_field": 3.14})
        assert valid

        # Valid integer (coerced to float)
        valid, errors = TestPlugin.validate_config({"float_field": 42})
        assert valid

        # Invalid float
        valid, errors = TestPlugin.validate_config({"float_field": "not_float"})
        assert not valid
        assert "Float Field must be a number" in errors

    def test_validate_config_select_type(self):
        """Test validation of select type."""

        class TestPlugin(PluginConfigMixin):
            CONFIG_FIELDS = [
                ConfigField(
                    key="select_field",
                    label="Select Field",
                    type="select",
                    default="option1",
                    options=["option1", "option2", "option3"],
                )
            ]

        # Valid option
        valid, errors = TestPlugin.validate_config({"select_field": "option2"})
        assert valid

        # Invalid option
        valid, errors = TestPlugin.validate_config({"select_field": "invalid"})
        assert not valid
        assert "has invalid value" in errors[0]

    def test_validate_config_select_with_tuple_options(self):
        """Test validation of select with tuple options (value, label)."""

        class TestPlugin(PluginConfigMixin):
            CONFIG_FIELDS = [
                ConfigField(
                    key="select_field",
                    label="Select Field",
                    type="select",
                    default="opt1",
                    options=[("opt1", "Option 1"), ("opt2", "Option 2")],
                )
            ]

        # Valid option (using value)
        valid, errors = TestPlugin.validate_config({"select_field": "opt1"})
        assert valid

        # Invalid option
        valid, errors = TestPlugin.validate_config({"select_field": "invalid"})
        assert not valid

    def test_validate_config_skip_optional_empty_fields(self):
        """Test that optional empty fields are not validated."""

        class TestPlugin(PluginConfigMixin):
            CONFIG_FIELDS = [
                ConfigField(
                    key="optional_int",
                    label="Optional Int",
                    type="integer",
                    default=0,
                    required=False,
                )
            ]

        # Empty optional field should pass
        valid, errors = TestPlugin.validate_config({"optional_int": ""})
        assert valid
        assert len(errors) == 0

    def test_invalid_field_definition_type(self):
        """Test that invalid field definition types raise TypeError."""

        class TestPlugin(PluginConfigMixin):
            CONFIG_FIELDS = ["invalid_field_definition"]

        with pytest.raises(TypeError, match="Invalid field definition"):
            TestPlugin.get_config_fields()

    def test_empty_config_fields(self):
        """Test plugin with no config fields."""

        class TestPlugin(PluginConfigMixin):
            PLUGIN_ID = "test"
            PLUGIN_NAME = "Test"
            CONFIG_FIELDS = []

        fields = TestPlugin.get_config_fields()
        assert len(fields) == 0

        defaults = TestPlugin.get_default_config()
        assert defaults == {}

        valid, errors = TestPlugin.validate_config({})
        assert valid
        assert len(errors) == 0


if __name__ == "__main__":
    unittest.main()
