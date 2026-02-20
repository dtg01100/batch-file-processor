"""
Simplified CSV Configuration Plugin

Implements the ConfigurationPlugin interface for Simplified CSV format configuration.
Provides support for Simplified CSV-specific configuration fields and validation.
"""

from typing import List, Dict, Any, Optional

from .configuration_plugin import ConfigurationPlugin
from .config_schemas import FieldDefinition, FieldType, ConfigurationSchema
from .validation_framework import ValidationResult
from ..models.folder_configuration import ConvertFormat
from .ui_abstraction import ConfigurationWidgetBuilder


class SimplifiedCSVConfiguration:
    """Simplified CSV configuration data class."""
    
    def __init__(
        self,
        retail_uom: bool = False,
        include_headers: bool = False,
        include_item_numbers: bool = False,
        include_item_description: bool = False,
        simple_csv_sort_order: str = ""
    ):
        self.retail_uom = retail_uom
        self.include_headers = include_headers
        self.include_item_numbers = include_item_numbers
        self.include_item_description = include_item_description
        self.simple_csv_sort_order = simple_csv_sort_order


class SimplifiedCSVConfigurationPlugin(ConfigurationPlugin):
    """
    Simplified CSV configuration plugin implementing the ConfigurationPlugin interface.
    
    Provides support for Simplified CSV format configuration with specific fields and validation.
    """
    
    @classmethod
    def get_name(cls) -> str:
        """Get the human-readable name of the plugin."""
        return "Simplified CSV Configuration"
    
    @classmethod
    def get_identifier(cls) -> str:
        """Get the unique identifier for the plugin."""
        return "simplified_csv_configuration"
    
    @classmethod
    def get_description(cls) -> str:
        """Get a detailed description of the plugin's functionality."""
        return "Provides Simplified CSV format configuration options for EDI conversion"
    
    @classmethod
    def get_version(cls) -> str:
        """Get the plugin version."""
        return "1.0.0"
    
    @classmethod
    def get_format_name(cls) -> str:
        """Get the human-readable name of the configuration format."""
        return "Simplified CSV"
    
    @classmethod
    def get_format_enum(cls) -> ConvertFormat:
        """Get the ConvertFormat enum value associated with this format."""
        return ConvertFormat.SIMPLIFIED_CSV
    
    @classmethod
    def get_config_fields(cls) -> List[FieldDefinition]:
        """Get the list of field definitions for this configuration format."""
        fields = [
            FieldDefinition(
                name="retail_uom",
                field_type=FieldType.BOOLEAN,
                label="Retail UOM",
                description="Use retail unit of measure (each) instead of case",
                default=False
            ),
            FieldDefinition(
                name="include_headers",
                field_type=FieldType.BOOLEAN,
                label="Include Headers",
                description="Whether to include headers in the CSV output",
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
                description="Sort order for simple CSV format (comma-separated column names)",
                default=""
            )
        ]
        return fields
    
    def validate_config(self, config: Dict[str, Any]) -> ValidationResult:
        """Validate configuration data against the format's schema."""
        schema = self.get_configuration_schema()
        if schema:
            return schema.validate(config)
        return ValidationResult(success=True, errors=[])
    
    def create_config(self, data: Dict[str, Any]) -> SimplifiedCSVConfiguration:
        """Create a configuration instance from raw data."""
        return SimplifiedCSVConfiguration(
            retail_uom=data.get("retail_uom", False),
            include_headers=data.get("include_headers", False),
            include_item_numbers=data.get("include_item_numbers", False),
            include_item_description=data.get("include_item_description", False),
            simple_csv_sort_order=data.get("simple_csv_sort_order", "")
        )
    
    def serialize_config(self, config: SimplifiedCSVConfiguration) -> Dict[str, Any]:
        """Serialize a configuration instance to dictionary format."""
        return {
            "retail_uom": config.retail_uom,
            "include_headers": config.include_headers,
            "include_item_numbers": config.include_item_numbers,
            "include_item_description": config.include_item_description,
            "simple_csv_sort_order": config.simple_csv_sort_order
        }
    
    def deserialize_config(self, data: Dict[str, Any]) -> SimplifiedCSVConfiguration:
        """Deserialize stored data into a configuration instance."""
        return self.create_config(data)
    
    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the plugin with configuration."""
        if config:
            self._config = self.create_config(config)
        else:
            self._config = self.create_config({})
    
    def activate(self) -> None:
        """Activate the plugin."""
        pass
    
    def deactivate(self) -> None:
        """Deactivate the plugin."""
        pass
    
    def create_widget(self, parent: Any = None) -> Any:
        """Create a UI widget for configuring the plugin."""
        schema = self.get_configuration_schema()
        if schema:
            builder = ConfigurationWidgetBuilder()
            return builder.build_configuration_panel(schema, self._config.__dict__ if hasattr(self, '_config') else {}, parent)
        return None
