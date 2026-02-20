"""
eStore eInvoice Configuration Plugin

Implements the ConfigurationPlugin interface for eStore eInvoice format configuration.
Provides support for eStore eInvoice-specific configuration fields and validation.
"""

from typing import List, Dict, Any, Optional

from .configuration_plugin import ConfigurationPlugin
from .config_schemas import FieldDefinition, FieldType, ConfigurationSchema
from .validation_framework import ValidationResult
from ..models.folder_configuration import ConvertFormat
from .ui_abstraction import ConfigurationWidgetBuilder


class EStoreEInvoiceConfiguration:
    """eStore eInvoice configuration data class."""
    
    def __init__(
        self,
        estore_store_number: str = "",
        estore_vendor_oid: str = "",
        estore_vendor_namevendoroid: str = ""
    ):
        self.estore_store_number = estore_store_number
        self.estore_vendor_oid = estore_vendor_oid
        self.estore_vendor_namevendoroid = estore_vendor_namevendoroid


class EStoreEInvoiceConfigurationPlugin(ConfigurationPlugin):
    """
    eStore eInvoice configuration plugin implementing the ConfigurationPlugin interface.
    
    Provides support for eStore eInvoice format configuration with specific fields and validation.
    """
    
    @classmethod
    def get_name(cls) -> str:
        """Get the human-readable name of the plugin."""
        return "eStore eInvoice Configuration"
    
    @classmethod
    def get_identifier(cls) -> str:
        """Get the unique identifier for the plugin."""
        return "estore_einvoice_configuration"
    
    @classmethod
    def get_description(cls) -> str:
        """Get a detailed description of the plugin's functionality."""
        return "Provides eStore eInvoice format configuration options for EDI conversion"
    
    @classmethod
    def get_version(cls) -> str:
        """Get the plugin version."""
        return "1.0.0"
    
    @classmethod
    def get_format_name(cls) -> str:
        """Get the human-readable name of the configuration format."""
        return "eStore eInvoice"
    
    @classmethod
    def get_format_enum(cls) -> ConvertFormat:
        """Get the ConvertFormat enum value associated with this format."""
        return ConvertFormat.ESTORE_EINVOICE
    
    @classmethod
    def get_config_fields(cls) -> List[FieldDefinition]:
        """Get the list of field definitions for this configuration format."""
        fields = [
            FieldDefinition(
                name="estore_store_number",
                field_type=FieldType.STRING,
                label="Store Number",
                description="The store number for eStore eInvoice output",
                default="",
                min_length=1,
                max_length=50
            ),
            FieldDefinition(
                name="estore_vendor_oid",
                field_type=FieldType.STRING,
                label="Vendor OID",
                description="The vendor OID for eStore eInvoice output",
                default="",
                min_length=1,
                max_length=50
            ),
            FieldDefinition(
                name="estore_vendor_namevendoroid",
                field_type=FieldType.STRING,
                label="Vendor Name (Vendor OID)",
                description="The vendor name or vendor OID identifier for the output filename",
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
    
    def create_config(self, data: Dict[str, Any]) -> EStoreEInvoiceConfiguration:
        """Create a configuration instance from raw data."""
        return EStoreEInvoiceConfiguration(
            estore_store_number=data.get("estore_store_number", ""),
            estore_vendor_oid=data.get("estore_vendor_oid", ""),
            estore_vendor_namevendoroid=data.get("estore_vendor_namevendoroid", "")
        )
    
    def serialize_config(self, config: EStoreEInvoiceConfiguration) -> Dict[str, Any]:
        """Serialize a configuration instance to dictionary format."""
        return {
            "estore_store_number": config.estore_store_number,
            "estore_vendor_oid": config.estore_vendor_oid,
            "estore_vendor_namevendoroid": config.estore_vendor_namevendoroid
        }
    
    def deserialize_config(self, data: Dict[str, Any]) -> EStoreEInvoiceConfiguration:
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
