"""
Form Generator and Dynamic UI Rendering Tests for Plugins

Tests for the form generator and dynamic UI rendering system specifically
related to plugin configuration.
"""

import unittest
from unittest.mock import MagicMock, patch
import pytest
from interface.plugins.config_schemas import ConfigurationSchema, FieldDefinition, FieldType
from interface.plugins.csv_configuration_plugin import CSVConfigurationPlugin
from interface.form import FormGeneratorFactory
from interface.plugins import PluginManager
from interface.models.folder_configuration import ConvertFormat


class TestFormGeneratorForPlugins(unittest.TestCase):
    """Tests for form generator with plugin configuration schemas."""
    
    def test_form_generator_with_csv_config_schema(self):
        """Test that form generator can handle CSV configuration schema."""
        schema = CSVConfigurationPlugin.get_configuration_schema()
        self.assertIsNotNone(schema)
        
        # Test Qt form generator
        qt_generator = FormGeneratorFactory.create_form_generator(schema, 'qt')
        self.assertIsNotNone(qt_generator)
        
        # Test Tkinter form generator
        tk_generator = FormGeneratorFactory.create_form_generator(schema, 'tkinter')
        self.assertIsNotNone(tk_generator)
    
    def test_csv_config_schema_completeness(self):
        """Test that CSV configuration schema has all required fields."""
        schema = CSVConfigurationPlugin.get_configuration_schema()
        self.assertIsNotNone(schema)
        
        # Check all fields are properly defined
        field_names = [field.name for field in schema.fields]
        expected_fields = [
            'include_headers', 'filter_ampersand', 'include_item_numbers',
            'include_item_description', 'simple_csv_sort_order', 
            'split_prepaid_sales_tax_crec'
        ]
        
        for expected_field in expected_fields:
            self.assertIn(expected_field, field_names, 
                        f"Expected field {expected_field} not found in CSV configuration schema")
    
    def test_csv_config_field_types(self):
        """Test that CSV configuration fields have correct types."""
        schema = CSVConfigurationPlugin.get_configuration_schema()
        
        fields = {field.name: field for field in schema.fields}
        
        # Check boolean fields
        self.assertEqual(fields['include_headers'].field_type, FieldType.BOOLEAN)
        self.assertEqual(fields['filter_ampersand'].field_type, FieldType.BOOLEAN)
        self.assertEqual(fields['include_item_numbers'].field_type, FieldType.BOOLEAN)
        self.assertEqual(fields['include_item_description'].field_type, FieldType.BOOLEAN)
        self.assertEqual(fields['split_prepaid_sales_tax_crec'].field_type, FieldType.BOOLEAN)
        
        # Check string fields
        self.assertEqual(fields['simple_csv_sort_order'].field_type, FieldType.STRING)
    
    def test_csv_config_default_values(self):
        """Test that CSV configuration fields have appropriate default values."""
        schema = CSVConfigurationPlugin.get_configuration_schema()
        
        fields = {field.name: field for field in schema.fields}
        
        # All boolean fields should default to False
        self.assertFalse(fields['include_headers'].default)
        self.assertFalse(fields['filter_ampersand'].default)
        self.assertFalse(fields['include_item_numbers'].default)
        self.assertFalse(fields['include_item_description'].default)
        self.assertFalse(fields['split_prepaid_sales_tax_crec'].default)
        
        # String field should have empty string default
        self.assertEqual(fields['simple_csv_sort_order'].default, "")
    
    def test_get_default_configuration(self):
        """Test getting default configuration from plugin schema."""
        plugin = CSVConfigurationPlugin()
        default_config = plugin.get_default_configuration()
        
        self.assertIsNotNone(default_config)
        self.assertEqual(len(default_config), 6)
        
        # Check all default values
        self.assertFalse(default_config['include_headers'])
        self.assertFalse(default_config['filter_ampersand'])
        self.assertFalse(default_config['include_item_numbers'])
        self.assertFalse(default_config['include_item_description'])
        self.assertEqual(default_config['simple_csv_sort_order'], "")
        self.assertFalse(default_config['split_prepaid_sales_tax_crec'])
    
    def test_schema_validation_for_csv_config(self):
        """Test schema validation for CSV configuration."""
        schema = CSVConfigurationPlugin.get_configuration_schema()
        
        # Test valid configuration
        valid_config = {
            'include_headers': True,
            'filter_ampersand': False,
            'include_item_numbers': True,
            'include_item_description': False,
            'simple_csv_sort_order': 'asc',
            'split_prepaid_sales_tax_crec': True
        }
        
        validation = schema.validate(valid_config)
        self.assertTrue(validation.success)
        self.assertEqual(len(validation.errors), 0)
    
    def test_empty_config_validation(self):
        """Test validation of empty configuration."""
        schema = CSVConfigurationPlugin.get_configuration_schema()
        
        validation = schema.validate({})
        self.assertTrue(validation.success)  # No required fields, so empty should be valid
        self.assertEqual(len(validation.errors), 0)


class TestPluginUIRendering(unittest.TestCase):
    """Tests for plugin UI widget creation and rendering."""
    
    @patch('interface.plugins.csv_configuration_plugin.ConfigurationWidgetBuilder')
    def test_create_widget_method(self, mock_builder):
        """Test that create_widget method works correctly."""
        # Create mock widget builder
        mock_instance = MagicMock()
        mock_builder_instance = MagicMock()
        mock_builder.return_value = mock_builder_instance
        mock_builder_instance.build_configuration_panel.return_value = mock_instance
        
        plugin = CSVConfigurationPlugin()
        widget = plugin.create_widget()
        
        self.assertIsNotNone(widget)
        mock_builder_instance.build_configuration_panel.assert_called_once()
    
    @patch('interface.plugins.csv_configuration_plugin.ConfigurationWidgetBuilder')
    def test_create_widget_with_parent(self, mock_builder):
        """Test creating widget with parent widget."""
        # Create mock widget builder
        mock_instance = MagicMock()
        mock_builder_instance = MagicMock()
        mock_builder.return_value = mock_builder_instance
        mock_builder_instance.build_configuration_panel.return_value = mock_instance
        
        plugin = CSVConfigurationPlugin()
        parent = MagicMock()
        widget = plugin.create_widget(parent)
        
        self.assertIsNotNone(widget)
        mock_builder_instance.build_configuration_panel.assert_called_once()
        
        # Verify parent was passed
        call_args = mock_builder_instance.build_configuration_panel.call_args
        self.assertEqual(call_args[0][2], parent)
    
    @patch('interface.plugins.csv_configuration_plugin.ConfigurationWidgetBuilder')
    def test_create_widget_with_config(self, mock_builder):
        """Test creating widget with existing configuration."""
        # Create mock widget builder
        mock_instance = MagicMock()
        mock_builder_instance = MagicMock()
        mock_builder.return_value = mock_builder_instance
        mock_builder_instance.build_configuration_panel.return_value = mock_instance
        
        plugin = CSVConfigurationPlugin()
        test_config = {
            'include_headers': True,
            'filter_ampersand': True
        }
        plugin.initialize(test_config)
        
        widget = plugin.create_widget()
        
        self.assertIsNotNone(widget)
        mock_builder_instance.build_configuration_panel.assert_called_once()
        
        # Verify configuration was passed
        call_args = mock_builder_instance.build_configuration_panel.call_args
        self.assertEqual(call_args[0][1]['include_headers'], True)
        self.assertEqual(call_args[0][1]['filter_ampersand'], True)


@patch('interface.plugins.csv_configuration_plugin.ConfigurationWidgetBuilder')
class TestPluginManagerUIFunctionality(unittest.TestCase):
    """Tests for PluginManager UI functionality."""
    
    def setUp(self):
        """Create a PluginManager instance for testing."""
        self.manager = PluginManager()
    
    def test_create_configuration_widget_from_manager(self, mock_builder):
        """Test creating configuration widget via plugin manager."""
        # Create mock widget builder
        mock_instance = MagicMock()
        mock_builder_instance = MagicMock()
        mock_builder.return_value = mock_builder_instance
        mock_builder_instance.build_configuration_panel.return_value = mock_instance
        
        # Create and add a mock plugin
        class MockConfigPlugin(CSVConfigurationPlugin):
            @classmethod
            def get_identifier(cls) -> str:
                return "mock_config_plugin"
        
        self.manager._configuration_plugins[ConvertFormat.CSV] = MockConfigPlugin()
        
        widget = self.manager.create_configuration_widget(ConvertFormat.CSV)
        
        self.assertIsNotNone(widget)


if __name__ == "__main__":
    unittest.main()
