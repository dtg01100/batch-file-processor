"""
Test cases for PluginBase interface.

Tests the base plugin interface and lifecycle management.
"""

import unittest
from typing import Any, Dict
from unittest.mock import patch

from interface.plugins import PluginBase
from interface.plugins.config_schemas import (
    ConfigurationSchema,
    FieldDefinition,
    FieldType,
)


class TestPlugin(PluginBase):
    """
    Test plugin implementation for testing purposes.
    """

    @classmethod
    def get_name(cls) -> str:
        return "Test Plugin"

    @classmethod
    def get_identifier(cls) -> str:
        return "test_plugin"

    @classmethod
    def get_description(cls) -> str:
        return "A test plugin for testing purposes"

    @classmethod
    def get_version(cls) -> str:
        return "1.0.0"

    def initialize(self, config: Dict[str, Any] = None) -> None:
        self.config = config or {}

    def activate(self) -> None:
        self.active = True

    def deactivate(self) -> None:
        self.active = False

    def create_widget(self, parent: Any = None) -> Any:
        return None


class TestPluginWithConfig(TestPlugin):
    """
    Test plugin with configuration schema.
    """

    @classmethod
    def get_configuration_schema(cls) -> ConfigurationSchema:
        fields = [
            FieldDefinition(
                name="test_field",
                field_type=FieldType.STRING,
                label="Test Field",
                description="A test configuration field",
                default="default",
                required=True,
            ),
            FieldDefinition(
                name="numeric_field",
                field_type=FieldType.INTEGER,
                label="Numeric Field",
                description="A numeric configuration field",
                default=42,
                required=False,
                min_value=0,
                max_value=100,
            ),
        ]
        return ConfigurationSchema(fields)


class TestPluginBase(unittest.TestCase):
    """
    Tests for PluginBase interface.
    """

    def test_plugin_creation(self):
        """Test basic plugin instantiation."""
        plugin = TestPlugin()
        self.assertIsNotNone(plugin)

    def test_plugin_static_properties(self):
        """Test plugin static properties."""
        self.assertEqual(TestPlugin.get_name(), "Test Plugin")
        self.assertEqual(TestPlugin.get_identifier(), "test_plugin")
        self.assertEqual(
            TestPlugin.get_description(), "A test plugin for testing purposes"
        )
        self.assertEqual(TestPlugin.get_version(), "1.0.0")

    def test_plugin_lifecycle(self):
        """Test plugin lifecycle methods."""
        plugin = TestPlugin()

        # Test initialize
        config = {"key": "value"}
        plugin.initialize(config)
        self.assertEqual(plugin.config, config)

        # Test activate/deactivate
        plugin.activate()
        self.assertTrue(plugin.active)
        plugin.deactivate()
        self.assertFalse(plugin.active)

    def test_plugin_configuration(self):
        """Test plugin configuration management."""
        plugin = TestPluginWithConfig()

        # Test default configuration
        default_config = plugin.get_default_configuration()
        self.assertEqual(default_config["test_field"], "default")
        self.assertEqual(default_config["numeric_field"], 42)

        # Test valid configuration
        valid_config = {"test_field": "test_value", "numeric_field": 50}
        validation = plugin.validate_configuration(valid_config)
        self.assertTrue(validation.success)

        # Test invalid configuration
        invalid_config = {"test_field": None}
        validation = plugin.validate_configuration(invalid_config)
        self.assertFalse(validation.success)
        self.assertIn("required", str(validation.errors[0]).lower())

        # Test configuration update
        result = plugin.update_configuration(valid_config)
        self.assertTrue(result.success)
        self.assertEqual(plugin.config["test_field"], "test_value")
        self.assertEqual(plugin.config["numeric_field"], 50)

    def test_invalid_configuration_update(self):
        """Test updating with invalid configuration."""
        plugin = TestPluginWithConfig()

        # Store initial config
        initial_config = plugin.get_default_configuration()
        plugin.initialize(initial_config)

        # Try to update with invalid config
        invalid_config = {"test_field": None}
        result = plugin.update_configuration(invalid_config)
        self.assertFalse(result.success)

        # Verify config wasn't updated
        self.assertEqual(plugin.config, initial_config)

    def test_compatibility_check(self):
        """Test plugin compatibility check."""
        self.assertTrue(TestPlugin.is_compatible())

    def test_dependencies(self):
        """Test plugin dependencies."""
        self.assertEqual(TestPlugin.get_dependencies(), [])

    def test_validate_configuration_without_schema_succeeds(self):
        """Test validation succeeds when plugin does not define a schema."""
        plugin = TestPlugin()

        result = plugin.validate_configuration({"any": "value"})

        self.assertTrue(result.success)
        self.assertEqual(result.errors, [])

    def test_get_default_configuration_without_schema_returns_empty_dict(self):
        """Test default configuration is empty when no schema is defined."""
        plugin = TestPlugin()

        defaults = plugin.get_default_configuration()

        self.assertEqual(defaults, {})

    def test_update_configuration_invalid_does_not_call_initialize(self):
        """Test invalid update does not invoke initialize."""
        plugin = TestPluginWithConfig()

        with patch.object(plugin, "initialize") as mock_initialize:
            result = plugin.update_configuration({"test_field": None})

        self.assertFalse(result.success)
        mock_initialize.assert_not_called()

    def test_update_configuration_valid_calls_initialize_once(self):
        """Test valid update invokes initialize exactly once."""
        plugin = TestPluginWithConfig()
        valid_config = {"test_field": "value", "numeric_field": 10}

        with patch.object(plugin, "initialize") as mock_initialize:
            result = plugin.update_configuration(valid_config)

        self.assertTrue(result.success)
        mock_initialize.assert_called_once_with(valid_config)


if __name__ == "__main__":
    unittest.main()
