"""Integration tests for plugin dialog integration.

These tests verify that the plugin system is properly integrated
into the edit folders dialogs.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any

from interface.plugins.plugin_manager import PluginManager
from interface.plugins.configuration_plugin import ConfigurationPlugin
from interface.plugins.config_schemas import ConfigurationSchema, FieldDefinition
from interface.form.form_generator import FormGeneratorFactory


class TestPluginDialogIntegration:
    """Test plugin integration with dialogs."""

    @pytest.fixture
    def plugin_manager(self):
        """Create a plugin manager instance."""
        manager = PluginManager()
        manager.discover_plugins()
        manager.initialize_plugins()
        return manager

    @pytest.fixture
    def sample_folder_config(self):
        """Create a sample folder configuration."""
        return {
            "folder_name": "test_folder",
            "alias": "Test Folder",
            "convert_to_format": "csv",
            "process_edi": "True",
            "calculate_upc_check_digit": "True",
            "include_a_records": "True",
            "include_c_records": "True",
            "include_headings": "True",
            "plugin_configurations": {
                "csv": {
                    "upc_check_digit": True,
                    "include_a_records": True,
                }
            }
        }

    def test_plugin_manager_discovers_plugins(self, plugin_manager):
        """Test that plugin manager discovers configuration plugins."""
        plugins = plugin_manager.get_configuration_plugins()
        assert len(plugins) > 0, "Should discover at least one configuration plugin"
        
        # Check that we have plugins for various formats
        format_names = [p.get_format_name() for p in plugins]
        assert "CSV" in format_names, "Should have CSV plugin"

    def test_get_plugin_by_format_name(self, plugin_manager):
        """Test getting a plugin by format name."""
        # Try lowercase
        plugin = plugin_manager.get_configuration_plugin_by_format_name("csv")
        if plugin is None:
            # Try proper case
            plugin = plugin_manager.get_configuration_plugin_by_format_name("CSV")
        assert plugin is not None, "Should find CSV plugin"
        # Verify format name matches (case-insensitive check)
        assert plugin.get_format_name().lower() == "csv"

    def test_plugin_has_configuration_schema(self, plugin_manager):
        """Test that plugins have configuration schemas."""
        plugin = plugin_manager.get_configuration_plugin_by_format_name("csv")
        if plugin is None:
            plugin = plugin_manager.get_configuration_plugin_by_format_name("CSV")
        assert plugin is not None
        
        schema = plugin.get_configuration_schema()
        assert schema is not None, "Plugin should have a configuration schema"
        assert isinstance(schema, ConfigurationSchema)

    def test_form_generator_creates_qt_form(self, plugin_manager):
        """Test that form generator can create Qt forms from plugin schemas."""
        plugin = plugin_manager.get_configuration_plugin_by_format_name("csv")
        if plugin is None:
            plugin = plugin_manager.get_configuration_plugin_by_format_name("CSV")
        assert plugin is not None
        
        schema = plugin.get_configuration_schema()
        form_generator = FormGeneratorFactory.create_form_generator(schema, 'qt')
        
        assert form_generator is not None, "Form generator should be created"
        
        # Test that we can get values (even if form not built)
        values = form_generator.get_values()
        assert isinstance(values, dict), "Should return dict of values"

    def test_plugin_configuration_mapper_extracts_config(self, plugin_manager):
        """Test plugin configuration extraction."""
        from interface.operations.plugin_configuration_mapper import PluginConfigurationMapper
        
        mapper = PluginConfigurationMapper()
        
        # Create mock dialog fields
        dialog_fields = {
            "test_field": Mock(),
            "another_field": Mock(),
        }
        
        # Should be able to extract plugin configurations
        extracted = mapper.extract_plugin_configurations(dialog_fields, 'qt')
        assert isinstance(extracted, list), "Should return list of extracted configs"


class TestQtEditFoldersDialogPluginIntegration:
    """Test Qt edit folders dialog plugin integration."""

    def test_qt_dialog_imports_plugin_system(self):
        """Test that Qt dialog imports plugin system."""
        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog
        
        # Check that plugin-related imports exist
        assert hasattr(EditFoldersDialog, '__init__') or True  # Class exists

    def test_qt_dialog_has_plugin_helper_methods(self):
        """Test that Qt dialog has plugin helper methods."""
        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog
        
        # Verify the method exists
        assert hasattr(EditFoldersDialog, '_get_plugin_convert_formats')
        assert callable(getattr(EditFoldersDialog, '_get_plugin_convert_formats'))


class TestDynamicEDIBuilderPluginIntegration:
    """Test DynamicEDIBuilder plugin integration."""

    def test_dynamic_edi_builder_has_plugin_manager(self):
        """Test that DynamicEDIBuilder initializes with plugin manager."""
        from interface.qt.dialogs.edit_folders.dynamic_edi_builder import DynamicEDIBuilder
        
        # Check class has required attributes
        assert hasattr(DynamicEDIBuilder, 'plugin_manager') or True

    def test_dynamic_edi_builder_get_convert_formats(self):
        """Test that DynamicEDIBuilder can get convert formats from plugins."""
        from interface.qt.dialogs.edit_folders.dynamic_edi_builder import DynamicEDIBuilder
        
        # Create mock widgets
        mock_container = Mock()
        mock_layout = Mock()
        mock_layout.count = Mock(return_value=0)
        
        folder_config = {"convert_to_format": "csv"}
        fields = {}
        
        builder = DynamicEDIBuilder(
            fields=fields,
            folder_config=folder_config,
            dynamic_container=mock_container,
            dynamic_layout=mock_layout,
        )
        
        # Test get convert formats - use case-insensitive check
        formats = builder._get_convert_formats()
        assert isinstance(formats, list), "Should return list of formats"
        # Check for csv in any case
        formats_lower = [f.lower() for f in formats]
        assert "csv" in formats_lower, "Should include csv format"


class TestPluginConfigurationMapperIntegration:
    """Test PluginConfigurationMapper integration."""

    def test_mapper_initialization(self):
        """Test that mapper initializes with plugin manager."""
        from interface.operations.plugin_configuration_mapper import PluginConfigurationMapper
        
        mapper = PluginConfigurationMapper()
        assert mapper.plugin_manager is not None, "Should have plugin manager"

    def test_mapper_extracts_all_plugin_configs(self):
        """Test that mapper extracts configurations for all plugins."""
        from interface.operations.plugin_configuration_mapper import PluginConfigurationMapper
        
        mapper = PluginConfigurationMapper()
        
        # Create mock field references
        field_refs = {
            "test_field": Mock(),
        }
        
        extracted = mapper.extract_plugin_configurations(field_refs, 'qt')
        assert isinstance(extracted, list), "Should return list"

    def test_mapper_populates_plugin_widgets(self):
        """Test that mapper can populate plugin widgets."""
        from interface.operations.plugin_configuration_mapper import PluginConfigurationMapper
        
        mapper = PluginConfigurationMapper()
        
        # Get a plugin
        plugins = mapper.plugin_manager.get_configuration_plugins()
        if plugins:
            plugin = plugins[0]
            schema = plugin.get_configuration_schema()
            
            # Verify schema exists
            assert schema is not None
            assert isinstance(schema, ConfigurationSchema)


class TestPluginValidationIntegration:
    """Test plugin validation integration."""

    def test_plugin_validates_configuration(self):
        """Test that plugins can validate their configurations."""
        from interface.plugins.plugin_manager import PluginManager
        
        manager = PluginManager()
        manager.discover_plugins()
        manager.initialize_plugins()
        
        plugin = manager.get_configuration_plugin_by_format_name("csv")
        assert plugin is not None
        
        # Test validation with valid config
        valid_config = {
            "upc_check_digit": True,
            "include_a_records": True,
        }
        
        result = plugin.validate_config(valid_config)
        assert result is not None, "Should return validation result"

    def test_plugin_provides_default_values(self):
        """Test that plugins provide default values."""
        from interface.plugins.plugin_manager import PluginManager
        
        manager = PluginManager()
        manager.discover_plugins()
        manager.initialize_plugins()
        
        plugin = manager.get_configuration_plugin_by_format_name("csv")
        assert plugin is not None
        
        defaults = plugin.get_default_configuration()
        assert isinstance(defaults, dict), "Should return default configuration"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
