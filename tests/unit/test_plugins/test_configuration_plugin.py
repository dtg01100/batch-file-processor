"""
Configuration Plugin Tests

Tests for the ConfigurationPlugin interface and its implementations.
"""

import unittest
from typing import Dict, Any, List
from interface.plugins import ConfigurationPlugin
from interface.plugins.config_schemas import ConfigurationSchema, FieldDefinition, FieldType
from interface.plugins.csv_configuration_plugin import CSVConfigurationPlugin
from interface.plugins.validation_framework import ValidationResult
from interface.models.folder_configuration import ConvertFormat, CSVConfiguration


class TestConfigurationPluginInterface(unittest.TestCase):
    """Tests for the ConfigurationPlugin interface."""
    
    def test_interface_exists(self):
        """Test that ConfigurationPlugin interface is defined."""
        self.assertIsNotNone(ConfigurationPlugin)
        self.assertTrue(hasattr(ConfigurationPlugin, 'get_format_name'))
        self.assertTrue(hasattr(ConfigurationPlugin, 'get_format_enum'))
        self.assertTrue(hasattr(ConfigurationPlugin, 'get_config_fields'))
        self.assertTrue(hasattr(ConfigurationPlugin, 'validate_config'))
        self.assertTrue(hasattr(ConfigurationPlugin, 'create_config'))
        self.assertTrue(hasattr(ConfigurationPlugin, 'serialize_config'))
        self.assertTrue(hasattr(ConfigurationPlugin, 'deserialize_config'))
    
    def test_get_configuration_schema(self):
        """Test that get_configuration_schema creates a valid schema."""
        # Create a minimal test plugin
        class MinimalConfigPlugin(ConfigurationPlugin):
            @classmethod
            def get_name(cls) -> str:
                return "Minimal Config Plugin"
            
            @classmethod
            def get_identifier(cls) -> str:
                return "minimal_config"
            
            @classmethod
            def get_description(cls) -> str:
                return "A minimal configuration plugin"
            
            @classmethod
            def get_version(cls) -> str:
                return "1.0.0"
            
            @classmethod
            def get_format_name(cls) -> str:
                return "Minimal"
            
            @classmethod
            def get_format_enum(cls) -> ConvertFormat:
                return ConvertFormat.CSV
                
            @classmethod
            def get_config_fields(cls) -> List[FieldDefinition]:
                return [
                    FieldDefinition(
                        name="test_field",
                        field_type=FieldType.STRING,
                        label="Test Field",
                        description="A test field"
                    )
                ]
                
            def validate_config(self, config: Dict[str, Any]) -> ValidationResult:
                from interface.plugins.validation_framework import ValidationResult
                return ValidationResult(success=True, errors=[])
                
            def create_config(self, data: Dict[str, Any]) -> Any:
                return data
                
            def serialize_config(self, config: Any) -> Dict[str, Any]:
                return config
                
            def deserialize_config(self, data: Dict[str, Any]) -> Any:
                return data
                
            def initialize(self, config: Dict[str, Any] = None) -> None:
                pass
                
            def activate(self) -> None:
                pass
                
            def deactivate(self) -> None:
                pass
                
            def create_widget(self, parent: Any = None) -> Any:
                return None
        
        # Test that get_configuration_schema works
        schema = MinimalConfigPlugin.get_configuration_schema()
        self.assertIsNotNone(schema)
        self.assertIsInstance(schema, ConfigurationSchema)
        self.assertEqual(len(schema.fields), 1)
        self.assertEqual(schema.fields[0].name, "test_field")


class TestCSVConfigurationPlugin(unittest.TestCase):
    """Tests for CSVConfigurationPlugin implementation."""
    
    def setUp(self):
        """Create a CSVConfigurationPlugin instance for testing."""
        self.plugin = CSVConfigurationPlugin()
    
    def test_plugin_creation(self):
        """Test that CSVConfigurationPlugin can be instantiated."""
        self.assertIsNotNone(self.plugin)
        self.assertIsInstance(self.plugin, CSVConfigurationPlugin)
        self.assertIsInstance(self.plugin, ConfigurationPlugin)
    
    def test_static_properties(self):
        """Test plugin static properties."""
        self.assertEqual(CSVConfigurationPlugin.get_name(), "CSV Configuration")
        self.assertEqual(CSVConfigurationPlugin.get_identifier(), "csv_configuration")
        self.assertEqual(CSVConfigurationPlugin.get_description(), "Provides CSV format configuration options for EDI conversion")
        self.assertEqual(CSVConfigurationPlugin.get_version(), "1.0.0")
        self.assertEqual(CSVConfigurationPlugin.get_format_name(), "CSV")
        self.assertEqual(CSVConfigurationPlugin.get_format_enum(), ConvertFormat.CSV)
    
    def test_get_config_fields(self):
        """Test that get_config_fields returns valid field definitions."""
        fields = CSVConfigurationPlugin.get_config_fields()
        self.assertIsNotNone(fields)
        self.assertTrue(len(fields) > 0)
        self.assertIsInstance(fields, list)
        
        # Check that all fields are FieldDefinition instances
        for field in fields:
            self.assertIsInstance(field, FieldDefinition)
    
    def test_configuration_schema(self):
        """Test that configuration schema is created correctly."""
        schema = CSVConfigurationPlugin.get_configuration_schema()
        self.assertIsNotNone(schema)
        self.assertIsInstance(schema, ConfigurationSchema)
        
        # Check key fields exist
        field_names = [field.name for field in schema.fields]
        self.assertIn("include_headers", field_names)
        self.assertIn("filter_ampersand", field_names)
        self.assertIn("include_item_numbers", field_names)
        self.assertIn("include_item_description", field_names)
        self.assertIn("simple_csv_sort_order", field_names)
        self.assertIn("split_prepaid_sales_tax_crec", field_names)
    
    def test_validate_config(self):
        """Test configuration validation."""
        # Test valid configuration
        valid_config = {
            "include_headers": True,
            "filter_ampersand": False,
            "include_item_numbers": True,
            "include_item_description": False,
            "simple_csv_sort_order": "asc",
            "split_prepaid_sales_tax_crec": True
        }
        
        validation = self.plugin.validate_config(valid_config)
        self.assertTrue(validation.success)
        self.assertEqual(len(validation.errors), 0)
    
    def test_validate_invalid_config(self):
        """Test validation with invalid configuration data types."""
        invalid_config = {
            "include_headers": "not_boolean",
            "filter_ampersand": 123,
            "include_item_numbers": "true",
            "include_item_description": None,
            "simple_csv_sort_order": 42,
            "split_prepaid_sales_tax_crec": "false"
        }
        
        validation = self.plugin.validate_config(invalid_config)
        self.assertFalse(validation.success)
        self.assertTrue(len(validation.errors) > 0)
    
    def test_create_config(self):
        """Test creating CSV configuration instances."""
        config_data = {
            "include_headers": True,
            "filter_ampersand": True,
            "include_item_numbers": False,
            "include_item_description": True,
            "simple_csv_sort_order": "desc",
            "split_prepaid_sales_tax_crec": False
        }
        
        config = self.plugin.create_config(config_data)
        self.assertIsNotNone(config)
        self.assertIsInstance(config, CSVConfiguration)
        self.assertEqual(config.include_headers, config_data["include_headers"])
        self.assertEqual(config.filter_ampersand, config_data["filter_ampersand"])
        self.assertEqual(config.include_item_numbers, config_data["include_item_numbers"])
        self.assertEqual(config.include_item_description, config_data["include_item_description"])
        self.assertEqual(config.simple_csv_sort_order, config_data["simple_csv_sort_order"])
        self.assertEqual(config.split_prepaid_sales_tax_crec, config_data["split_prepaid_sales_tax_crec"])
    
    def test_create_config_with_defaults(self):
        """Test creating CSV configuration with default values."""
        config = self.plugin.create_config({})
        self.assertIsNotNone(config)
        self.assertFalse(config.include_headers)
        self.assertFalse(config.filter_ampersand)
        self.assertFalse(config.include_item_numbers)
        self.assertFalse(config.include_item_description)
        self.assertEqual(config.simple_csv_sort_order, "")
        self.assertFalse(config.split_prepaid_sales_tax_crec)
    
    def test_serialize_config(self):
        """Test serializing CSV configuration to dictionary."""
        config = CSVConfiguration(
            include_headers=True,
            filter_ampersand=False,
            include_item_numbers=True,
            include_item_description=False,
            simple_csv_sort_order="custom",
            split_prepaid_sales_tax_crec=True
        )
        
        serialized = self.plugin.serialize_config(config)
        self.assertIsNotNone(serialized)
        self.assertIsInstance(serialized, dict)
        self.assertEqual(serialized["include_headers"], config.include_headers)
        self.assertEqual(serialized["filter_ampersand"], config.filter_ampersand)
        self.assertEqual(serialized["include_item_numbers"], config.include_item_numbers)
        self.assertEqual(serialized["include_item_description"], config.include_item_description)
        self.assertEqual(serialized["simple_csv_sort_order"], config.simple_csv_sort_order)
        self.assertEqual(serialized["split_prepaid_sales_tax_crec"], config.split_prepaid_sales_tax_crec)
    
    def test_deserialize_config(self):
        """Test deserializing configuration data."""
        config_data = {
            "include_headers": True,
            "filter_ampersand": True,
            "include_item_numbers": False,
            "include_item_description": True,
            "simple_csv_sort_order": "asc",
            "split_prepaid_sales_tax_crec": False
        }
        
        config = self.plugin.deserialize_config(config_data)
        self.assertIsNotNone(config)
        self.assertIsInstance(config, CSVConfiguration)
        self.assertEqual(config.include_headers, config_data["include_headers"])
        self.assertEqual(config.filter_ampersand, config_data["filter_ampersand"])
        self.assertEqual(config.include_item_numbers, config_data["include_item_numbers"])
        self.assertEqual(config.include_item_description, config_data["include_item_description"])
        self.assertEqual(config.simple_csv_sort_order, config_data["simple_csv_sort_order"])
        self.assertEqual(config.split_prepaid_sales_tax_crec, config_data["split_prepaid_sales_tax_crec"])
    
    def test_plugin_lifecycle(self):
        """Test plugin lifecycle methods."""
        # Test initialize
        config_data = {
            "include_headers": True,
            "filter_ampersand": False
        }
        self.plugin.initialize(config_data)
        
        # Test activate/deactivate
        self.plugin.activate()
        self.plugin.deactivate()


if __name__ == "__main__":
    unittest.main()
