"""Unit tests for plugin interfaces (ISP fix).

Tests:
- IPlugin interface contracts
- IConfigurablePlugin interface contracts
- IUIPlugin interface contracts
- IPluginCompatibility interface contracts
- PluginBase implements all interfaces
"""

import pytest

from interface.plugins.interfaces import (
    IPlugin,
    IConfigurablePlugin,
    IUIPlugin,
    IPluginCompatibility,
)
from interface.plugins.plugin_base import PluginBase
from interface.plugins.config_schemas import ConfigurationSchema, FieldDefinition, FieldType
from interface.plugins.validation_framework import ValidationResult


class TestIPlugin:
    """Test suite for IPlugin interface."""

    def test_get_name_raises_not_implemented(self):
        """Test that get_name raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            IPlugin.get_name()

    def test_get_identifier_raises_not_implemented(self):
        """Test that get_identifier raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            IPlugin.get_identifier()

    def test_get_description_raises_not_implemented(self):
        """Test that get_description raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            IPlugin.get_description()

    def test_get_version_raises_not_implemented(self):
        """Test that get_version raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            IPlugin.get_version()

    def test_initialize_raises_not_implemented(self):
        """Test that initialize raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            IPlugin().initialize()

    def test_activate_raises_not_implemented(self):
        """Test that activate raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            IPlugin().activate()

    def test_deactivate_raises_not_implemented(self):
        """Test that deactivate raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            IPlugin().deactivate()


class TestIConfigurablePlugin:
    """Test suite for IConfigurablePlugin interface."""

    def test_get_configuration_schema_raises_not_implemented(self):
        """Test that get_configuration_schema raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            IConfigurablePlugin.get_configuration_schema()

    def test_validate_configuration_raises_not_implemented(self):
        """Test that validate_configuration raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            IConfigurablePlugin().validate_configuration({})

    def test_update_configuration_raises_not_implemented(self):
        """Test that update_configuration raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            IConfigurablePlugin().update_configuration({})


class TestIUIPlugin:
    """Test suite for IUIPlugin interface."""

    def test_create_widget_raises_not_implemented(self):
        """Test that create_widget raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            IUIPlugin().create_widget()


class TestIPluginCompatibility:
    """Test suite for IPluginCompatibility interface."""

    def test_is_compatible_defaults_to_true(self):
        """Test that is_compatible defaults to True."""
        assert IPluginCompatibility.is_compatible() is True

    def test_get_dependencies_defaults_to_empty_list(self):
        """Test that get_dependencies defaults to empty list."""
        assert IPluginCompatibility.get_dependencies() == []


class ConcreteTestPlugin(PluginBase):
    """Concrete plugin implementation for testing."""

    @classmethod
    def get_name(cls) -> str:
        return "Test Plugin"

    @classmethod
    def get_identifier(cls) -> str:
        return "test.plugin"

    @classmethod
    def get_description(cls) -> str:
        return "A test plugin for unit testing"

    @classmethod
    def get_version(cls) -> str:
        return "1.0.0"

    def initialize(self, config=None) -> None:
        pass

    def activate(self) -> None:
        pass

    def deactivate(self) -> None:
        pass

    def create_widget(self, parent=None):
        return None


class TestPluginBaseImplementsAllInterfaces:
    """Test suite verifying PluginBase implements all interfaces."""

    def test_plugin_base_is_subclass_of_iplugin(self):
        """Test that PluginBase is a subclass of IPlugin."""
        assert issubclass(PluginBase, IPlugin)

    def test_plugin_base_is_subclass_of_iconfigurableplugin(self):
        """Test that PluginBase is a subclass of IConfigurablePlugin."""
        assert issubclass(PluginBase, IConfigurablePlugin)

    def test_plugin_base_is_subclass_of_iuiplugin(self):
        """Test that PluginBase is a subclass of IUIPlugin."""
        assert issubclass(PluginBase, IUIPlugin)

    def test_plugin_base_is_subclass_of_iplugincompatibility(self):
        """Test that PluginBase is a subclass of IPluginCompatibility."""
        assert issubclass(PluginBase, IPluginCompatibility)

    def test_concrete_plugin_can_be_instantiated(self):
        """Test that a concrete plugin implementation can be instantiated."""
        plugin = ConcreteTestPlugin()
        assert plugin is not None

    def test_concrete_plugin_returns_correct_metadata(self):
        """Test that concrete plugin returns correct metadata."""
        assert ConcreteTestPlugin.get_name() == "Test Plugin"
        assert ConcreteTestPlugin.get_identifier() == "test.plugin"
        assert ConcreteTestPlugin.get_description() == "A test plugin for unit testing"
        assert ConcreteTestPlugin.get_version() == "1.0.0"

    def test_concrete_plugin_lifecycle_methods(self):
        """Test that concrete plugin lifecycle methods work."""
        plugin = ConcreteTestPlugin()
        plugin.initialize()
        plugin.activate()
        plugin.deactivate()

    def test_concrete_plugin_is_compatible(self):
        """Test that concrete plugin is compatible by default."""
        assert ConcreteTestPlugin.is_compatible() is True

    def test_concrete_plugin_get_dependencies(self):
        """Test that concrete plugin returns empty dependencies by default."""
        assert ConcreteTestPlugin.get_dependencies() == []


class TestPluginBaseDefaultMethods:
    """Test suite for PluginBase default method implementations."""

    def test_get_configuration_schema_defaults_to_none(self):
        """Test that get_configuration_schema defaults to None."""
        assert PluginBase.get_configuration_schema() is None

    def test_validate_configuration_with_no_schema(self):
        """Test that validate_configuration returns success with no schema."""
        plugin = ConcreteTestPlugin()
        result = plugin.validate_configuration({})
        assert result.success is True
        assert result.errors == []

    def test_validate_configuration_with_schema(self):
        """Test that validate_configuration works with a schema."""

        class PluginWithSchema(ConcreteTestPlugin):
            @classmethod
            def get_configuration_schema(cls) -> ConfigurationSchema | None:
                return ConfigurationSchema(
                    fields=[
                        FieldDefinition(
                            name="setting",
                            field_type=FieldType.STRING,
                            required=True,
                        )
                    ]
                )

        plugin = PluginWithSchema()
        result = plugin.validate_configuration({"setting": "value"})
        assert result.success is True

        result_fail = plugin.validate_configuration({})
        assert result_fail.success is False

    def test_update_configuration_with_valid_config(self):
        """Test that update_configuration works with valid config."""
        plugin = ConcreteTestPlugin()
        result = plugin.update_configuration({})
        assert result.success is True

    def test_get_default_configuration(self):
        """Test that get_default_configuration returns defaults."""
        plugin = ConcreteTestPlugin()
        defaults = plugin.get_default_configuration()
        assert defaults == {}

    def test_get_default_configuration_with_schema(self):
        """Test that get_default_configuration returns schema defaults."""

        class PluginWithDefaults(ConcreteTestPlugin):
            @classmethod
            def get_configuration_schema(cls) -> ConfigurationSchema | None:
                return ConfigurationSchema(
                    fields=[
                        FieldDefinition(
                            name="option",
                            field_type=FieldType.STRING,
                            default="default_value",
                        )
                    ]
                )

        plugin = PluginWithDefaults()
        defaults = plugin.get_default_configuration()
        assert defaults == {"option": "default_value"}
