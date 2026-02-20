"""
Fintech Configuration Plugin

Implements the ConfigurationPlugin interface for Fintech format configuration.
Provides support for Fintech-specific configuration fields and validation.
"""

from typing import List, Dict, Any, Optional

from .configuration_plugin import ConfigurationPlugin
from .config_schemas import FieldDefinition, FieldType, ConfigurationSchema
from .validation_framework import ValidationResult
from ..models.folder_configuration import ConvertFormat
from .ui_abstraction import ConfigurationWidgetBuilder


class FintechConfiguration:
    """Fintech configuration data class."""
    
    def __init__(
        self,
        fintech_division_id: str = ""
    ):
        self.fintech_division_id = fintech_division_id


class FintechConfigurationPlugin(ConfigurationPlugin):
    """
    Fintech configuration plugin implementing the ConfigurationPlugin interface.
    
    Provides support for Fintech format configuration with specific fields and validation.
    """
    
    @classmethod
    def get_name(cls) -> str:
        """Get the human-readable name of the plugin."""
        return "Fintech Configuration"
    
    @classmethod
    def get_identifier(cls) -> str:
        """Get the unique identifier for the plugin."""
        return "fintech_configuration"
    
    @classmethod
    def get_description(cls) -> str:
        """Get a detailed description of the plugin's functionality."""
        return "Provides Fintech format configuration options for EDI conversion"
    
    @classmethod
    def get_version(cls) -> str:
        """Get the plugin version."""
        return "1.0.0"
    
    @classmethod
    def get_format_name(cls) -> str:
        """Get the human-readable name of the configuration format."""
        return "Fintech"
    
    @classmethod
    def get_format_enum(cls) -> ConvertFormat:
        """Get the ConvertFormat enum value associated with this format."""
        return ConvertFormat.FINTECH
    
    @classmethod
    def get_config_fields(cls) -> List[FieldDefinition]:
        """Get the list of field definitions for this configuration format."""
        fields = [
            FieldDefinition(
                name="fintech_division_id",
                field_type=FieldType.STRING,
                label="Division ID",
                description="The division ID to use for Fintech output",
                default="",
                min_length=1,
                max_length=50
            )
        ]
        return fields
    
    def validate_config(self, config: Dict[str, Any]) -> ValidationResult:
        """Validate configuration data against the format's schema."""
        schema = self.get_configuration_schema()
        if schema:
            return schema.validate(config)
        return ValidationResult(success=True, errors=[])
    
    def create_config(self, data: Dict[str, Any]) -> FintechConfiguration:
        """Create a configuration instance from raw data."""
        return FintechConfiguration(
            fintech_division_id=data.get("fintech_division_id", "")
        )
    
    def serialize_config(self, config: FintechConfiguration) -> Dict[str, Any]:
        """Serialize a configuration instance to dictionary format."""
        return {
            "fintech_division_id": config.fintech_division_id
        }
    
    def deserialize_config(self, data: Dict[str, Any]) -> FintechConfiguration:
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
