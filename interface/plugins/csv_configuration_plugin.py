"""
CSV Configuration Plugin

Implements the ConfigurationPlugin interface for CSV format configuration.
Provides support for CSV-specific configuration fields and validation.
"""

from typing import List, Dict, Any, Optional

from .configuration_plugin import ConfigurationPlugin
from .config_schemas import FieldDefinition, FieldType, ConfigurationSchema
from .validation_framework import ValidationResult
from ..models.folder_configuration import ConvertFormat, CSVConfiguration
from .ui_abstraction import ConfigurationWidgetBuilder


class CSVConfigurationPlugin(ConfigurationPlugin):
    """
    CSV configuration plugin implementing the ConfigurationPlugin interface.
    
    Provides support for CSV format configuration with specific fields and validation.
    """
    
    @classmethod
    def get_name(cls) -> str:
        """
        Get the human-readable name of the plugin.
        
        Returns:
            str: Plugin name for display purposes
        """
        return "CSV Configuration"
    
    @classmethod
    def get_identifier(cls) -> str:
        """
        Get the unique identifier for the plugin.
        
        Returns:
            str: Unique plugin identifier
        """
        return "csv_configuration"
    
    @classmethod
    def get_description(cls) -> str:
        """
        Get a detailed description of the plugin's functionality.
        
        Returns:
            str: Plugin description
        """
        return "Provides CSV format configuration options for EDI conversion"
    
    @classmethod
    def get_version(cls) -> str:
        """
        Get the plugin version.
        
        Returns:
            str: Plugin version string
        """
        return "1.0.0"
    
    @classmethod
    def get_format_name(cls) -> str:
        """
        Get the human-readable name of the configuration format.
        
        Returns:
            str: Format name for display purposes
        """
        return "CSV"
    
    @classmethod
    def get_format_enum(cls) -> ConvertFormat:
        """
        Get the ConvertFormat enum value associated with this format.
        
        Returns:
            ConvertFormat: The format enum from folder_configuration
        """
        return ConvertFormat.CSV
    
    @classmethod
    def get_config_fields(cls) -> List[FieldDefinition]:
        """
        Get the list of field definitions for this configuration format.
        
        Returns:
            List[FieldDefinition]: List of field definitions that define the
            configuration schema for this format.
        """
        fields = [
            FieldDefinition(
                name="include_headers",
                field_type=FieldType.BOOLEAN,
                label="Include Headers",
                description="Whether to include headers in the CSV output",
                default=False
            ),
            FieldDefinition(
                name="filter_ampersand",
                field_type=FieldType.BOOLEAN,
                label="Filter Ampersand",
                description="Whether to filter ampersand characters in the output",
                default=False
            ),
            FieldDefinition(
                name="include_item_numbers",
                field_type=FieldType.BOOLEAN,
                label="Include Item Numbers",
                description="Whether to include item numbers in the CSV output",
                default=False
            ),
            FieldDefinition(
                name="include_item_description",
                field_type=FieldType.BOOLEAN,
                label="Include Item Description",
                description="Whether to include item descriptions in the CSV output",
                default=False
            ),
            FieldDefinition(
                name="simple_csv_sort_order",
                field_type=FieldType.STRING,
                label="Simple CSV Sort Order",
                description="Sort order for simple CSV format",
                default=""
            ),
            FieldDefinition(
                name="split_prepaid_sales_tax_crec",
                field_type=FieldType.BOOLEAN,
                label="Split Prepaid Sales Tax CREC",
                description="Whether to split prepaid sales tax CREC",
                default=False
            )
        ]
        return fields
    
    def validate_config(self, config: Dict[str, Any]) -> ValidationResult:
        """
        Validate configuration data against the format's schema.
        
        Args:
            config: Configuration data to validate
            
        Returns:
            ValidationResult: Result of the validation operation
        """
        schema = self.get_configuration_schema()
        if schema:
            return schema.validate(config)
        return ValidationResult(success=True, errors=[])
    
    def create_config(self, data: Dict[str, Any]) -> CSVConfiguration:
        """
        Create a configuration instance from raw data.
        
        Args:
            data: Raw data to create the configuration from
            
        Returns:
            CSVConfiguration: CSV configuration instance
        """
        return CSVConfiguration(
            include_headers=data.get("include_headers", False),
            filter_ampersand=data.get("filter_ampersand", False),
            include_item_numbers=data.get("include_item_numbers", False),
            include_item_description=data.get("include_item_description", False),
            simple_csv_sort_order=data.get("simple_csv_sort_order", ""),
            split_prepaid_sales_tax_crec=data.get("split_prepaid_sales_tax_crec", False)
        )
    
    def serialize_config(self, config: CSVConfiguration) -> Dict[str, Any]:
        """
        Serialize a configuration instance to dictionary format.
        
        Args:
            config: Configuration instance to serialize
            
        Returns:
            Dict[str, Any]: Serialized configuration data
        """
        return {
            "include_headers": config.include_headers,
            "filter_ampersand": config.filter_ampersand,
            "include_item_numbers": config.include_item_numbers,
            "include_item_description": config.include_item_description,
            "simple_csv_sort_order": config.simple_csv_sort_order,
            "split_prepaid_sales_tax_crec": config.split_prepaid_sales_tax_crec
        }
    
    def deserialize_config(self, data: Dict[str, Any]) -> CSVConfiguration:
        """
        Deserialize stored data into a configuration instance.
        
        Args:
            data: Stored data to deserialize
            
        Returns:
            CSVConfiguration: CSV configuration instance
        """
        return self.create_config(data)
    
    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize the plugin with configuration.
        
        Called when the plugin is first loaded.
        
        Args:
            config: Optional configuration dictionary
        """
        if config:
            self._config = self.create_config(config)
        else:
            self._config = self.create_config({})
    
    def activate(self) -> None:
        """
        Activate the plugin.
        
        Called when the plugin is activated for use.
        """
        pass
    
    def deactivate(self) -> None:
        """
        Deactivate the plugin.
        
        Called when the plugin is deactivated or the application shuts down.
        """
        pass
    
    def create_widget(self, parent: Any = None) -> Any:
        """
        Create a UI widget for configuring the plugin.
        
        The returned widget should be compatible with the current UI framework
        (either Qt or Tkinter).
        
        Args:
            parent: Optional parent widget
            
        Returns:
            Any: UI widget for plugin configuration
        """
        schema = self.get_configuration_schema()
        if schema:
            builder = ConfigurationWidgetBuilder()
            return builder.build_configuration_panel(schema, self._config.__dict__ if hasattr(self, '_config') else {}, parent)
        return None
