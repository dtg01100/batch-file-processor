"""
Plugin Manager Configuration Plugins Tests

Tests for PluginManager enhancements related to configuration plugins.
"""

import unittest
from unittest.mock import MagicMock, patch
from interface.plugins import PluginManager
from interface.plugins.plugin_base import PluginBase
from interface.plugins.csv_configuration_plugin import CSVConfigurationPlugin
from interface.models.folder_configuration import ConvertFormat


class TestPluginManagerConfigurationPlugins(unittest.TestCase):
    """Tests for PluginManager configuration plugin functionality."""

    def setUp(self):
        """Create a PluginManager instance for testing."""
        self.manager = PluginManager()

    def test_initialization(self):
        """Test that plugin manager initializes configuration plugin storage."""
        self.assertIsNotNone(self.manager._configuration_plugins)
        self.assertIsNotNone(self.manager._configuration_plugin_classes)
        self.assertEqual(len(self.manager._configuration_plugins), 0)
        self.assertEqual(len(self.manager._configuration_plugin_classes), 0)

    @patch(
        "interface.plugins.plugin_manager.PluginManager._discover_plugins_in_package"
    )
    @patch(
        "interface.plugins.plugin_manager.PluginManager._discover_plugins_in_directory"
    )
    def test_discover_configuration_plugins(self, mock_dir, mock_package):
        """Test that configuration plugins are discovered and stored."""

        # Create a mock configuration plugin class
        class MockConfigPlugin(CSVConfigurationPlugin):
            @classmethod
            def get_identifier(cls) -> str:
                return "mock_config_plugin"

            @classmethod
            def get_format_enum(cls) -> ConvertFormat:
                return ConvertFormat.CSV

        # Mock plugin discovery - directly add to plugin classes
        self.manager._plugin_classes[MockConfigPlugin.get_identifier()] = (
            MockConfigPlugin
        )
        self.manager._configuration_plugin_classes[ConvertFormat.CSV] = MockConfigPlugin

        self.assertIn(MockConfigPlugin.get_identifier(), self.manager._plugin_classes)
        self.assertIn(ConvertFormat.CSV, self.manager._configuration_plugin_classes)
        self.assertEqual(
            self.manager._configuration_plugin_classes[ConvertFormat.CSV],
            MockConfigPlugin,
        )

    def test_get_configuration_plugins(self):
        """Test getting all configuration plugins."""
        # Mock initialization
        with patch.object(self.manager, "_initialized", False):
            with patch.object(self.manager, "initialize_plugins"):
                plugins = self.manager.get_configuration_plugins()
                self.assertIsInstance(plugins, list)

    def test_get_configuration_plugin_by_format(self):
        """Test getting configuration plugin by format enum."""

        # Create and add a mock plugin
        class MockConfigPlugin(CSVConfigurationPlugin):
            @classmethod
            def get_identifier(cls) -> str:
                return "mock_config_plugin"

            @classmethod
            def get_format_enum(cls) -> ConvertFormat:
                return ConvertFormat.CSV

        self.manager._configuration_plugin_classes[ConvertFormat.CSV] = MockConfigPlugin

        with patch.object(self.manager, "_initialized", False):
            with patch.object(self.manager, "initialize_plugins") as mock_init:
                mock_init.return_value = [MockConfigPlugin.get_identifier()]

                # Create a mock plugin instance
                mock_instance = MockConfigPlugin()
                self.manager._configuration_plugins[ConvertFormat.CSV] = mock_instance

                plugin = self.manager.get_configuration_plugin_by_format(
                    ConvertFormat.CSV
                )
                self.assertIsNotNone(plugin)
                self.assertIsInstance(plugin, MockConfigPlugin)

    def test_get_configuration_plugin_by_format_name(self):
        """Test getting configuration plugin by format name."""

        # Create and add a mock plugin
        class MockConfigPlugin(CSVConfigurationPlugin):
            @classmethod
            def get_identifier(cls) -> str:
                return "mock_config_plugin"

            @classmethod
            def get_format_name(cls) -> str:
                return "Custom CSV"

            @classmethod
            def get_format_enum(cls) -> ConvertFormat:
                return ConvertFormat.CSV

        # Add to manager
        self.manager._configuration_plugin_classes[ConvertFormat.CSV] = MockConfigPlugin
        mock_instance = MockConfigPlugin()
        self.manager._configuration_plugins[ConvertFormat.CSV] = mock_instance

        # Test case sensitivity
        plugin1 = self.manager.get_configuration_plugin_by_format_name("custom csv")
        plugin2 = self.manager.get_configuration_plugin_by_format_name("CUSTOM CSV")
        plugin3 = self.manager.get_configuration_plugin_by_format_name("Custom CSV")

        self.assertIsNotNone(plugin1)
        self.assertIsNotNone(plugin2)
        self.assertIsNotNone(plugin3)
        self.assertEqual(plugin1, plugin2)
        self.assertEqual(plugin2, plugin3)

    def test_create_configuration_widget(self):
        """Test creating configuration widget for a specific format."""
        # Create mock plugin
        mock_plugin = MagicMock()
        mock_plugin.create_widget.return_value = MagicMock()

        self.manager._configuration_plugins[ConvertFormat.CSV] = mock_plugin

        with patch.object(self.manager, "_initialized", False):
            with patch.object(self.manager, "initialize_plugins"):
                widget = self.manager.create_configuration_widget(ConvertFormat.CSV)
                self.assertIsNotNone(widget)
                mock_plugin.create_widget.assert_called_once()

    def test_validate_configuration(self):
        """Test validating configuration for a specific format."""
        # Create mock plugin
        mock_plugin = MagicMock()
        mock_plugin.validate_config.return_value = MagicMock(success=True)

        self.manager._configuration_plugins[ConvertFormat.CSV] = mock_plugin

        with patch.object(self.manager, "_initialized", False):
            with patch.object(self.manager, "initialize_plugins"):
                config = {"key": "value"}
                validation = self.manager.validate_configuration(
                    ConvertFormat.CSV, config
                )
                self.assertTrue(validation.success)
                mock_plugin.validate_config.assert_called_once_with(config)

    def test_create_configuration(self):
        """Test creating configuration instance for a specific format."""
        # Create mock plugin
        mock_plugin = MagicMock()
        mock_plugin.create_config.return_value = MagicMock()

        self.manager._configuration_plugins[ConvertFormat.CSV] = mock_plugin

        with patch.object(self.manager, "_initialized", False):
            with patch.object(self.manager, "initialize_plugins"):
                config = {"key": "value"}
                result = self.manager.create_configuration(ConvertFormat.CSV, config)
                self.assertIsNotNone(result)
                mock_plugin.create_config.assert_called_once_with(config)

    def test_serialize_configuration(self):
        """Test serializing configuration instance."""
        # Create mock plugin
        mock_plugin = MagicMock()
        mock_plugin.serialize_config.return_value = {"key": "value"}

        self.manager._configuration_plugins[ConvertFormat.CSV] = mock_plugin

        with patch.object(self.manager, "_initialized", False):
            with patch.object(self.manager, "initialize_plugins"):
                config = MagicMock()
                result = self.manager.serialize_configuration(ConvertFormat.CSV, config)
                self.assertIsNotNone(result)
                self.assertEqual(result["key"], "value")
                mock_plugin.serialize_config.assert_called_once_with(config)

    def test_deserialize_configuration(self):
        """Test deserializing configuration data."""
        # Create mock plugin
        mock_plugin = MagicMock()
        mock_plugin.deserialize_config.return_value = MagicMock()

        self.manager._configuration_plugins[ConvertFormat.CSV] = mock_plugin

        with patch.object(self.manager, "_initialized", False):
            with patch.object(self.manager, "initialize_plugins"):
                config = {"key": "value"}
                result = self.manager.deserialize_configuration(
                    ConvertFormat.CSV, config
                )
                self.assertIsNotNone(result)
                mock_plugin.deserialize_config.assert_called_once_with(config)

    def test_get_configuration_fields(self):
        """Test getting configuration field definitions for a format."""

        # Create mock plugin class
        class MockConfigPlugin(CSVConfigurationPlugin):
            @classmethod
            def get_identifier(cls) -> str:
                return "mock_config_plugin"

            @classmethod
            def get_format_enum(cls) -> ConvertFormat:
                return ConvertFormat.CSV

        self.manager._configuration_plugin_classes[ConvertFormat.CSV] = MockConfigPlugin

        fields = self.manager.get_configuration_fields(ConvertFormat.CSV)
        self.assertIsNotNone(fields)
        self.assertTrue(len(fields) > 0)

    def test_unsupported_format_handling(self):
        """Test that unsupported formats return appropriate responses."""
        # Try to get a plugin for an invalid format
        plugin = self.manager.get_configuration_plugin_by_format(None)
        self.assertIsNone(plugin)

        # Try to validate invalid format
        validation = self.manager.validate_configuration(None, {})
        self.assertFalse(validation.success)
        self.assertIn("Unsupported format", str(validation.errors))

        # Try to create configuration for invalid format
        config = self.manager.create_configuration(None, {})
        self.assertIsNone(config)

        # Try to serialize for invalid format
        serialized = self.manager.serialize_configuration(None, None)
        self.assertEqual(serialized, {})

        # Try to deserialize for invalid format
        deserialized = self.manager.deserialize_configuration(None, {})
        self.assertIsNone(deserialized)

        # Try to get fields for invalid format
        fields = self.manager.get_configuration_fields(None)
        self.assertEqual(fields, [])

    def test_initialize_plugins_is_idempotent(self):
        """Test repeated initialization does not re-run plugin lifecycle."""

        class LifecyclePlugin(PluginBase):
            initialize_calls = 0
            activate_calls = 0

            @classmethod
            def get_name(cls) -> str:
                return "Lifecycle Plugin"

            @classmethod
            def get_identifier(cls) -> str:
                return "lifecycle_plugin"

            @classmethod
            def get_description(cls) -> str:
                return "Plugin used to verify lifecycle idempotency"

            @classmethod
            def get_version(cls) -> str:
                return "1.0.0"

            def initialize(self, config=None) -> None:
                type(self).initialize_calls += 1

            def activate(self) -> None:
                type(self).activate_calls += 1

            def deactivate(self) -> None:
                pass

            def create_widget(self, parent=None):
                return None

        self.manager._plugin_classes = {LifecyclePlugin.get_identifier(): LifecyclePlugin}

        first_initialized = self.manager.initialize_plugins()
        second_initialized = self.manager.initialize_plugins()

        self.assertEqual(first_initialized, [LifecyclePlugin.get_identifier()])
        self.assertEqual(second_initialized, [LifecyclePlugin.get_identifier()])
        self.assertEqual(LifecyclePlugin.initialize_calls, 1)
        self.assertEqual(LifecyclePlugin.activate_calls, 1)

    def test_initialize_order_is_initialize_then_activate_with_config(self):
        """Test plugin initialize is called before activate with passed config."""

        events = []
        expected_config = {"enabled": True, "threshold": 7}

        class OrderedLifecyclePlugin(PluginBase):
            @classmethod
            def get_name(cls) -> str:
                return "Ordered Lifecycle Plugin"

            @classmethod
            def get_identifier(cls) -> str:
                return "ordered_lifecycle_plugin"

            @classmethod
            def get_description(cls) -> str:
                return "Plugin used to verify initialize/activate call order"

            @classmethod
            def get_version(cls) -> str:
                return "1.0.0"

            def initialize(self, config=None) -> None:
                events.append(("initialize", config))

            def activate(self) -> None:
                events.append(("activate", None))

            def deactivate(self) -> None:
                pass

            def create_widget(self, parent=None):
                return None

        plugin_id = OrderedLifecyclePlugin.get_identifier()
        self.manager._plugin_classes = {plugin_id: OrderedLifecyclePlugin}

        self.manager.initialize_plugins(config={plugin_id: expected_config})

        self.assertEqual(events[0], ("initialize", expected_config))
        self.assertEqual(events[1], ("activate", None))

    def test_plugin_initialize_failure_does_not_block_other_plugins(self):
        """Test one plugin failure does not prevent others from initializing."""

        class FailingPlugin(PluginBase):
            @classmethod
            def get_name(cls) -> str:
                return "Failing Plugin"

            @classmethod
            def get_identifier(cls) -> str:
                return "failing_plugin"

            @classmethod
            def get_description(cls) -> str:
                return "Plugin that fails during initialize"

            @classmethod
            def get_version(cls) -> str:
                return "1.0.0"

            def initialize(self, config=None) -> None:
                raise RuntimeError("intentional init failure")

            def activate(self) -> None:
                pass

            def deactivate(self) -> None:
                pass

            def create_widget(self, parent=None):
                return None

        class HealthyPlugin(PluginBase):
            activated = False

            @classmethod
            def get_name(cls) -> str:
                return "Healthy Plugin"

            @classmethod
            def get_identifier(cls) -> str:
                return "healthy_plugin"

            @classmethod
            def get_description(cls) -> str:
                return "Plugin that should still initialize"

            @classmethod
            def get_version(cls) -> str:
                return "1.0.0"

            def initialize(self, config=None) -> None:
                self.config = config or {}

            def activate(self) -> None:
                type(self).activated = True

            def deactivate(self) -> None:
                pass

            def create_widget(self, parent=None):
                return None

        self.manager._plugin_classes = {
            FailingPlugin.get_identifier(): FailingPlugin,
            HealthyPlugin.get_identifier(): HealthyPlugin,
        }

        initialized = self.manager.initialize_plugins()

        self.assertIn(HealthyPlugin.get_identifier(), initialized)
        self.assertNotIn(FailingPlugin.get_identifier(), initialized)
        self.assertIn(HealthyPlugin.get_identifier(), self.manager._plugins)
        self.assertNotIn(FailingPlugin.get_identifier(), self.manager._plugins)
        self.assertTrue(HealthyPlugin.activated)


if __name__ == "__main__":
    unittest.main()
