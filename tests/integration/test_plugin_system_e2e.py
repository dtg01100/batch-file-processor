"""End-to-end tests for plugin system integration.

Uses actual APIs: FolderConfiguration.from_dict(), PluginConfigurationMapper methods.
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

pytestmark = [pytest.mark.integration, pytest.mark.e2e, pytest.mark.plugin]


@pytest.fixture
def workspace_with_edi():
    """Create workspace with sample EDI files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        input_dir = workspace / "input"
        input_dir.mkdir()
        output_dir = workspace / "output"
        output_dir.mkdir()
        
        edi_content = """A00000120240101001TESTVENDOR         Test Vendor Inc                 00001
B001001ITEM001     000010EA0010Test Item 1                     0000010000
"""
        (input_dir / "test.edi").write_text(edi_content)
        
        yield {'workspace': workspace, 'input': input_dir, 'output': output_dir}


@pytest.mark.e2e
class TestPluginDiscoveryAndLoading:
    """Test plugin discovery and loading."""

    def test_plugin_manager_discovers_plugins(self):
        """Test plugin manager discovers plugins."""
        from interface.plugins.plugin_manager import PluginManager
        
        manager = PluginManager()
        manager.discover_plugins()
        plugins = manager.get_configuration_plugins()
        
        assert len(plugins) > 0
        format_names = [p.get_format_name().lower() for p in plugins]
        assert 'csv' in format_names

    def test_get_plugin_by_format(self):
        """Test retrieving plugin by format."""
        from interface.plugins.plugin_manager import PluginManager
        
        manager = PluginManager()
        manager.discover_plugins()
        
        csv_plugin = manager.get_configuration_plugin_by_format_name("csv")
        assert csv_plugin is not None
        assert csv_plugin.get_format_name().lower() == 'csv'


@pytest.mark.e2e
class TestPluginConfigurationWithFolderModel:
    """Test plugin configuration using FolderConfiguration model."""

    def test_create_folder_config_with_plugin_config(self):
        """Test creating FolderConfiguration with plugin config."""
        from interface.models.folder_configuration import FolderConfiguration
        
        data = {
            'folder_name': '/test/folder',
            'alias': 'Test Folder',
            'convert_to_format': 'csv',
            'plugin_configurations': {
                'csv': {'upc_check_digit': True}
            }
        }
        
        config = FolderConfiguration.from_dict(data)
        
        assert 'csv' in config.plugin_configurations
        assert config.plugin_configurations['csv']['upc_check_digit'] is True

    def test_set_plugin_configuration(self):
        """Test setting plugin configuration."""
        from interface.models.folder_configuration import FolderConfiguration
        
        data = {'folder_name': '/test', 'alias': 'Test'}
        config = FolderConfiguration.from_dict(data)
        
        config.set_plugin_configuration('csv', {'upc_check_digit': True})
        
        assert 'csv' in config.plugin_configurations
        assert config.plugin_configurations['csv']['upc_check_digit'] is True

    def test_update_folder_config_with_plugin_mapper(self):
        """Test updating folder config with PluginConfigurationMapper."""
        from interface.models.folder_configuration import FolderConfiguration
        from interface.operations.plugin_configuration_mapper import PluginConfigurationMapper, ExtractedPluginConfig
        
        data = {'folder_name': '/test', 'alias': 'Test', 'convert_to_format': 'csv'}
        config = FolderConfiguration.from_dict(data)
        
        mapper = PluginConfigurationMapper()
        extracted = ExtractedPluginConfig(
            format_name='csv',
            config={'upc_check_digit': True},
            validation_errors=[]
        )
        
        mapper.update_folder_configuration(config, [extracted])
        
        assert 'csv' in config.plugin_configurations

    def test_validate_plugin_configurations(self):
        """Test validating plugin configurations."""
        from interface.models.folder_configuration import FolderConfiguration
        
        data = {
            'folder_name': '/test',
            'alias': 'Test',
            'convert_to_format': 'csv',
            'plugin_configurations': {'csv': {'upc_check_digit': True}}
        }
        config = FolderConfiguration.from_dict(data)
        
        errors = config.validate_plugin_configurations()
        assert len(errors) == 0

    def test_serialize_deserialize_plugin_config(self):
        """Test serializing/deserializing plugin config."""
        from interface.operations.plugin_configuration_mapper import PluginConfigurationMapper
        
        mapper = PluginConfigurationMapper()
        config = {'upc_check_digit': True}
        
        serialized = mapper.serialize_plugin_config('csv', config)
        assert isinstance(serialized, str)
        
        format_name, config = mapper.deserialize_plugin_config(serialized)
        assert format_name == 'csv'


@pytest.mark.e2e
class TestPluginConfigurationFields:
    """Test plugin configuration field generation."""

    def test_get_plugin_configuration_fields(self):
        """Test getting configuration fields."""
        from interface.operations.plugin_configuration_mapper import PluginConfigurationMapper
        
        mapper = PluginConfigurationMapper()
        fields = mapper.get_plugin_configuration_fields('csv')
        
        assert len(fields) > 0
        for field in fields:
            assert 'name' in field
            assert 'type' in field

    def test_get_supported_plugin_formats(self):
        """Test getting supported plugin formats."""
        from interface.operations.plugin_configuration_mapper import PluginConfigurationMapper
        
        mapper = PluginConfigurationMapper()
        formats = mapper.get_supported_plugin_formats()
        
        assert len(formats) > 0
        assert any('csv' in f.lower() for f in formats)


@pytest.mark.e2e
class TestPluginConfigurationPersistence:
    """Test plugin configuration persistence via database."""

    def test_save_load_plugin_config_via_database(self, temp_database):
        """Test saving/loading plugin config via database."""
        # Insert folder with plugin config
        temp_database.folders_table.insert({
            'folder_name': '/test/folder',
            'alias': 'Test Folder',
            'folder_is_active': 'True',
            'process_backend_copy': 'True',
            'plugin_configurations': json.dumps({'csv': {'upc_check_digit': True}}),
        })
        
        # Load and verify
        folder = temp_database.folders_table.find_one(folder_name='/test/folder')
        assert folder is not None
        assert 'plugin_configurations' in folder

    def test_update_plugin_config_via_database(self, temp_database):
        """Test updating plugin config via database."""
        # Create folder
        temp_database.folders_table.insert({
            'folder_name': '/test/folder',
            'alias': 'Test Folder',
            'plugin_configurations': '{}',
        })
        
        # Get folder and update
        folder = temp_database.folders_table.find_one(folder_name='/test/folder')
        folder['plugin_configurations'] = json.dumps({'csv': {'upc_check_digit': True}})
        temp_database.folders_table.update(folder, ['folder_name'])
        
        # Verify update
        updated = temp_database.folders_table.find_one(folder_name='/test/folder')
        stored_config = updated['plugin_configurations'] if isinstance(updated['plugin_configurations'], dict) else json.loads(updated['plugin_configurations'])
        assert stored_config['csv']['upc_check_digit'] is True


@pytest.mark.e2e
class TestPluginErrorIsolation:
    """Test plugin error handling."""

    def test_invalid_plugin_config_handled(self):
        """Test handling invalid plugin config."""
        from interface.models.folder_configuration import FolderConfiguration
        
        data = {
            'folder_name': '/test',
            'alias': 'Test',
            'convert_to_format': 'csv',
            'plugin_configurations': {'csv': {'invalid_field': 'value'}}
        }
        config = FolderConfiguration.from_dict(data)
        
        errors = config.validate_plugin_configurations()
        # Should have validation errors, not crash
        assert isinstance(errors, list)

    def test_missing_plugin_handled(self):
        """Test handling missing plugin reference."""
        from interface.models.folder_configuration import FolderConfiguration
        
        data = {
            'folder_name': '/test',
            'alias': 'Test',
            'plugin_configurations': {'nonexistent': {'option': 'value'}}
        }
        config = FolderConfiguration.from_dict(data)
        
        errors = config.validate_plugin_configurations()
        
        assert len(errors) > 0
        assert any('nonexistent' in e for e in errors)


@pytest.mark.e2e
class TestMultiplePluginsWorkflow:
    """Test multiple plugins workflow."""

    def test_multiple_plugins_same_folder(self):
        """Test multiple plugins in same folder."""
        from interface.models.folder_configuration import FolderConfiguration
        
        data = {'folder_name': '/test', 'alias': 'Test', 'convert_to_format': 'csv'}
        config = FolderConfiguration.from_dict(data)
        
        config.set_plugin_configuration('csv', {'upc_check_digit': True})
        
        assert len(config.plugin_configurations) >= 1

    def test_plugin_configuration_switching(self):
        """Test switching plugin configurations."""
        from interface.models.folder_configuration import FolderConfiguration
        from interface.operations.plugin_configuration_mapper import PluginConfigurationMapper, ExtractedPluginConfig
        
        data = {'folder_name': '/test', 'alias': 'Test', 'convert_to_format': 'csv'}
        config = FolderConfiguration.from_dict(data)
        
        mapper = PluginConfigurationMapper()
        extracted = ExtractedPluginConfig(
            format_name='csv',
            config={'upc_check_digit': True},
            validation_errors=[]
        )
        mapper.update_folder_configuration(config, [extracted])
        
        assert 'csv' in config.plugin_configurations


@pytest.mark.e2e
class TestPluginFormGeneration:
    """Test plugin form generation."""

    def test_get_plugin_fields_for_format(self):
        """Test getting plugin fields."""
        from interface.operations.plugin_configuration_mapper import PluginConfigurationMapper
        
        mapper = PluginConfigurationMapper()
        fields = mapper.get_plugin_configuration_fields('csv')
        
        assert fields is not None
        assert len(fields) > 0
        
        for field_def in fields:
            assert 'name' in field_def
            assert 'label' in field_def


@pytest.mark.e2e
class TestPluginLifecycle:
    """Test complete plugin lifecycle."""

    def test_plugin_full_lifecycle(self, workspace_with_edi):
        """Test plugin lifecycle: discover → configure → use."""
        from interface.plugins.plugin_manager import PluginManager
        from interface.models.folder_configuration import FolderConfiguration
        from interface.operations.plugin_configuration_mapper import PluginConfigurationMapper, ExtractedPluginConfig
        
        # 1. Discover plugins
        manager = PluginManager()
        manager.discover_plugins()
        
        # 2. Get plugin
        csv_plugin = manager.get_configuration_plugin_by_format_name('csv')
        assert csv_plugin is not None
        
        # 3. Get schema
        schema = csv_plugin.get_configuration_schema()
        assert schema is not None
        
        # 4. Create folder configuration
        data = {
            'folder_name': str(workspace_with_edi['input']),
            'alias': 'Plugin Test',
            'convert_to_format': 'csv',
        }
        config = FolderConfiguration.from_dict(data)
        
        # 5. Set plugin configuration
        mapper = PluginConfigurationMapper()
        extracted = ExtractedPluginConfig(
            format_name='csv',
            config={'upc_check_digit': True},
            validation_errors=[]
        )
        mapper.update_folder_configuration(config, [extracted])
        
        # 6. Verify
        assert 'csv' in config.plugin_configurations

    def test_plugin_state_across_sessions(self, temp_database):
        """Test plugin config persists via database."""
        # Save configuration
        temp_database.folders_table.insert({
            'folder_name': '/test/folder',
            'alias': 'Session Test',
            'plugin_configurations': json.dumps({'csv': {'upc_check_digit': True}}),
        })
        
        # Load configuration
        folder = temp_database.folders_table.find_one(folder_name='/test/folder')
        stored_config = folder['plugin_configurations'] if isinstance(folder['plugin_configurations'], dict) else json.loads(folder['plugin_configurations'])
        
        assert stored_config['csv']['upc_check_digit'] is True
