"""
Plugin Configuration Mapper and FolderConfiguration Tests

Tests for the plugin configuration mapper and FolderConfiguration integration
with plugin configurations.
"""

import unittest
from unittest.mock import MagicMock, patch
from interface.models.folder_configuration import FolderConfiguration, ConvertFormat, CSVConfiguration, EDIConfiguration
from interface.plugins import PluginManager
from interface.plugins.csv_configuration_plugin import CSVConfigurationPlugin


class TestPluginConfigurationMapper(unittest.TestCase):
    """Tests for plugin configuration mapping and conversion."""
    
    def setUp(self):
        """Create test instances."""
        self.manager = PluginManager()
        self.csv_plugin = CSVConfigurationPlugin()
    
    def test_csv_configuration_creation(self):
        """Test CSV configuration creation from plugin."""
        config_data = {
            'include_headers': True,
            'filter_ampersand': False,
            'include_item_numbers': True,
            'include_item_description': False,
            'simple_csv_sort_order': 'asc',
            'split_prepaid_sales_tax_crec': True
        }
        
        config = self.csv_plugin.create_config(config_data)
        self.assertIsNotNone(config)
        self.assertIsInstance(config, CSVConfiguration)
        self.assertEqual(config.include_headers, config_data['include_headers'])
        self.assertEqual(config.filter_ampersand, config_data['filter_ampersand'])
        self.assertEqual(config.include_item_numbers, config_data['include_item_numbers'])
        self.assertEqual(config.include_item_description, config_data['include_item_description'])
        self.assertEqual(config.simple_csv_sort_order, config_data['simple_csv_sort_order'])
        self.assertEqual(config.split_prepaid_sales_tax_crec, config_data['split_prepaid_sales_tax_crec'])
    
    def test_csv_configuration_serialization(self):
        """Test CSV configuration serialization."""
        config = CSVConfiguration(
            include_headers=True,
            filter_ampersand=True,
            include_item_numbers=False,
            include_item_description=True,
            simple_csv_sort_order='desc',
            split_prepaid_sales_tax_crec=False
        )
        
        serialized = self.csv_plugin.serialize_config(config)
        self.assertIsNotNone(serialized)
        self.assertIsInstance(serialized, dict)
        self.assertEqual(serialized['include_headers'], config.include_headers)
        self.assertEqual(serialized['filter_ampersand'], config.filter_ampersand)
        self.assertEqual(serialized['include_item_numbers'], config.include_item_numbers)
        self.assertEqual(serialized['include_item_description'], config.include_item_description)
        self.assertEqual(serialized['simple_csv_sort_order'], config.simple_csv_sort_order)
        self.assertEqual(serialized['split_prepaid_sales_tax_crec'], config.split_prepaid_sales_tax_crec)
    
    def test_csv_configuration_deserialization(self):
        """Test CSV configuration deserialization."""
        config_data = {
            'include_headers': False,
            'filter_ampersand': True,
            'include_item_numbers': False,
            'include_item_description': True,
            'simple_csv_sort_order': 'custom',
            'split_prepaid_sales_tax_crec': True
        }
        
        config = self.csv_plugin.deserialize_config(config_data)
        self.assertIsNotNone(config)
        self.assertIsInstance(config, CSVConfiguration)
        self.assertEqual(config.include_headers, config_data['include_headers'])
        self.assertEqual(config.filter_ampersand, config_data['filter_ampersand'])
        self.assertEqual(config.include_item_numbers, config_data['include_item_numbers'])
        self.assertEqual(config.include_item_description, config_data['include_item_description'])
        self.assertEqual(config.simple_csv_sort_order, config_data['simple_csv_sort_order'])
        self.assertEqual(config.split_prepaid_sales_tax_crec, config_data['split_prepaid_sales_tax_crec'])


class TestFolderConfigurationWithPlugins(unittest.TestCase):
    """Tests for FolderConfiguration with plugin configurations."""
    
    def setUp(self):
        """Create test instances."""
        self.folder_config = FolderConfiguration(
            folder_name="Test Folder",
            folder_is_active="True",
            alias="Test",
            edi=EDIConfiguration(convert_to_format=ConvertFormat.CSV.value)
        )
        
        self.csv_config = {
            'include_headers': True,
            'filter_ampersand': True,
            'include_item_numbers': False,
            'include_item_description': True,
            'simple_csv_sort_order': 'asc',
            'split_prepaid_sales_tax_crec': True
        }
    
    def test_folder_configuration_creation(self):
        """Test FolderConfiguration creation with plugin config."""
        self.assertIsNotNone(self.folder_config)
        self.assertEqual(self.folder_config.folder_name, "Test Folder")
        self.assertEqual(self.folder_config.folder_is_active, "True")
        self.assertEqual(self.folder_config.alias, "Test")
        self.assertIsNotNone(self.folder_config.edi)
        self.assertEqual(self.folder_config.edi.convert_to_format, ConvertFormat.CSV.value)
    
    def test_set_plugin_configuration(self):
        """Test setting and getting plugin configuration."""
        self.folder_config.set_plugin_configuration(ConvertFormat.CSV.value, self.csv_config)
        
        stored_config = self.folder_config.get_plugin_configuration(ConvertFormat.CSV.value)
        self.assertIsNotNone(stored_config)
        self.assertIsInstance(stored_config, dict)
        self.assertEqual(stored_config['include_headers'], self.csv_config['include_headers'])
        self.assertEqual(stored_config['filter_ampersand'], self.csv_config['filter_ampersand'])
        self.assertEqual(stored_config['include_item_numbers'], self.csv_config['include_item_numbers'])
        self.assertEqual(stored_config['include_item_description'], self.csv_config['include_item_description'])
        self.assertEqual(stored_config['simple_csv_sort_order'], self.csv_config['simple_csv_sort_order'])
        self.assertEqual(stored_config['split_prepaid_sales_tax_crec'], self.csv_config['split_prepaid_sales_tax_crec'])
    
    def test_get_nonexistent_plugin_configuration(self):
        """Test getting plugin configuration that doesn't exist."""
        config = self.folder_config.get_plugin_configuration(ConvertFormat.CSV.value)
        self.assertIsNone(config)
    
    def test_has_plugin_configuration(self):
        """Test checking if plugin configuration exists."""
        self.assertFalse(ConvertFormat.CSV.value in self.folder_config.plugin_configurations)
        
        self.folder_config.set_plugin_configuration(ConvertFormat.CSV.value, self.csv_config)
        self.assertTrue(ConvertFormat.CSV.value in self.folder_config.plugin_configurations)
    
    def test_remove_plugin_configuration(self):
        """Test removing plugin configuration."""
        self.folder_config.set_plugin_configuration(ConvertFormat.CSV.value, self.csv_config)
        self.assertTrue(ConvertFormat.CSV.value in self.folder_config.plugin_configurations)
        
        self.folder_config.remove_plugin_configuration(ConvertFormat.CSV.value)
        self.assertFalse(ConvertFormat.CSV.value in self.folder_config.plugin_configurations)
        self.assertIsNone(self.folder_config.get_plugin_configuration(ConvertFormat.CSV.value))
    
    def test_multiple_plugin_configurations(self):
        """Test storing multiple plugin configurations."""
        # Create another configuration type (if available)
        csv_config2 = {
            'include_headers': False,
            'filter_ampersand': False,
            'include_item_numbers': True,
            'include_item_description': False,
            'simple_csv_sort_order': 'desc',
            'split_prepaid_sales_tax_crec': False
        }
        
        # Test storing configurations for different formats
        self.folder_config.set_plugin_configuration(ConvertFormat.CSV.value, self.csv_config)
        self.folder_config.set_plugin_configuration(ConvertFormat.SCANNERWARE.value, csv_config2)
        
        self.assertEqual(len(self.folder_config.plugin_configurations), 2)
        self.assertIn(ConvertFormat.CSV.value.lower(), self.folder_config.plugin_configurations)
        self.assertIn(ConvertFormat.SCANNERWARE.value.lower(), self.folder_config.plugin_configurations)


class TestFolderConfigurationSerialization(unittest.TestCase):
    """Tests for FolderConfiguration serialization and deserialization with plugins."""
    
    def setUp(self):
        """Create test instances."""
        self.folder_config = FolderConfiguration(
            folder_name="Test Folder",
            folder_is_active="True",
            alias="Test",
            edi=EDIConfiguration(convert_to_format=ConvertFormat.CSV.value)
        )
        
        self.csv_config = {
            'include_headers': True,
            'filter_ampersand': True,
            'include_item_numbers': False,
            'include_item_description': True,
            'simple_csv_sort_order': 'asc',
            'split_prepaid_sales_tax_crec': True
        }
    
    @patch('interface.plugins.plugin_manager.PluginManager')
    def test_folder_config_to_dict(self, mock_manager):
        """Test converting FolderConfiguration to dictionary."""
        # Set up mock plugin manager
        mock_instance = MagicMock()
        mock_manager.return_value = mock_instance
        mock_instance.serialize_configuration.return_value = self.csv_config
        
        self.folder_config.set_plugin_configuration(ConvertFormat.CSV.value, self.csv_config)
        
        config_dict = self.folder_config.to_dict()
        
        self.assertIsNotNone(config_dict)
        self.assertIsInstance(config_dict, dict)
        
        # Check core properties
        self.assertEqual(config_dict['folder_name'], "Test Folder")
        self.assertEqual(config_dict['folder_is_active'], "True")
        self.assertEqual(config_dict['alias'], "Test")
        self.assertEqual(config_dict['convert_to_format'], ConvertFormat.CSV.value)
        
        # Check plugin configuration
        self.assertIn('plugin_configurations', config_dict)
        self.assertIsInstance(config_dict['plugin_configurations'], dict)
        self.assertIn(ConvertFormat.CSV.value.lower(), config_dict['plugin_configurations'])
        
        csv_config_dict = config_dict['plugin_configurations'][ConvertFormat.CSV.value.lower()]
        self.assertEqual(csv_config_dict['include_headers'], True)
        self.assertEqual(csv_config_dict['filter_ampersand'], True)
    
    @patch('interface.plugins.plugin_manager.PluginManager')
    def test_from_dict_with_plugin_config(self, mock_manager):
        """Test creating FolderConfiguration from dictionary with plugin config."""
        # Set up mock plugin manager
        mock_instance = MagicMock()
        mock_manager.return_value = mock_instance
        mock_instance.deserialize_configuration.return_value = self.csv_config
        
        config_dict = {
            'folder_name': "Test Folder",
            'folder_is_active': "True",
            'alias': "Test",
            'convert_to_format': ConvertFormat.CSV.value,
            'plugin_configurations': {
                ConvertFormat.CSV.value.lower(): self.csv_config
            }
        }
        
        folder_config = FolderConfiguration.from_dict(config_dict)
        
        self.assertIsNotNone(folder_config)
        self.assertEqual(folder_config.folder_name, "Test Folder")
        self.assertEqual(folder_config.folder_is_active, "True")
        self.assertEqual(folder_config.alias, "Test")
        self.assertEqual(folder_config.edi.convert_to_format, ConvertFormat.CSV.value)
        
        # Verify plugin configuration was restored
        restored_config = folder_config.get_plugin_configuration(ConvertFormat.CSV.value)
        self.assertIsNotNone(restored_config)
        self.assertEqual(restored_config['include_headers'], self.csv_config['include_headers'])
        self.assertEqual(restored_config['filter_ampersand'], self.csv_config['filter_ampersand'])


if __name__ == "__main__":
    unittest.main()
