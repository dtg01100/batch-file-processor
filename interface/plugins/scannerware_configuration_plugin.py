"""
ScannerWare Configuration Plugin

Implements the ConfigurationPlugin interface for ScannerWare format configuration.
Provides support for ScannerWare-specific configuration fields and validation.
"""

from typing import List, Dict, Any, Optional

from .configuration_plugin import ConfigurationPlugin
from .config_schemas import FieldDefinition, FieldType, ConfigurationSchema
from .validation_framework import ValidationResult
from ..models.folder_configuration import ConvertFormat
from .ui_abstraction import ConfigurationWidgetBuilder


class ScannerWareConfiguration:
    """ScannerWare configuration data class."""
    
    def __init__(
        self,
        a_record_padding: str = "",
        append_a_records: bool = False,
        a_record_append_text: str = "",
        force_txt_file_ext: bool = False,
        invoice_date_offset: int = 0,
        retail_uom: bool = False
    ):
        self.a_record_padding = a_record_padding
        self.append_a_records = append_a_records
        self.a_record_append_text = a_record_append_text
        self.force_txt_file_ext = force_txt_file_ext
        self.invoice_date_offset = invoice_date_offset
        self.retail_uom = retail_uom


class ScannerWareConfigurationPlugin(ConfigurationPlugin):
    """
    ScannerWare configuration plugin implementing the ConfigurationPlugin interface.
    
    Provides support for ScannerWare format configuration with specific fields and validation.
    """
    
    @classmethod
    def get_name(cls) -> str:
        """Get the human-readable name of the plugin."""
        return "ScannerWare Configuration"
    
    @classmethod
    def get_identifier(cls) -> str:
        """Get the unique identifier for the plugin."""
        return "scannerware_configuration"
    
    @classmethod
    def get_description(cls) -> str:
        """Get a detailed description of the plugin's functionality."""
        return "Provides ScannerWare format configuration options for EDI conversion"
    
    @classmethod
    def get_version(cls) -> str:
        """Get the plugin version."""
        return "1.0.0"
    
    @classmethod
    def get_format_name(cls) -> str:
        """Get the human-readable name of the configuration format."""
        return "ScannerWare"
    
    @classmethod
    def get_format_enum(cls) -> ConvertFormat:
        """Get the ConvertFormat enum value associated with this format."""
        return ConvertFormat.SCANNERWARE
    
    @classmethod
    def get_config_fields(cls) -> List[FieldDefinition]:
        """Get the list of field definitions for this configuration format."""
        fields = [
            FieldDefinition(
                name="a_record_padding",
                field_type=FieldType.STRING,
                label="A-Record Padding",
                description="Padding text for A-records (6 characters)",
                default="",
                min_length=0,
                max_length=6
            ),
            FieldDefinition(
                name="append_a_records",
                field_type=FieldType.BOOLEAN,
                label="Append A-Records",
                description="Whether to append text to A-records",
                default=False
            ),
            FieldDefinition(
                name="a_record_append_text",
                field_type=FieldType.STRING,
                label="A-Record Append Text",
                description="Text to append to A-records when append_a_records is enabled",
                default=""
            ),
            FieldDefinition(
                name="force_txt_file_ext",
                field_type=FieldType.BOOLEAN,
                label="Force TXT File Extension",
                description="Force output file to have .txt extension instead of .edi",
                default=False
            ),
            FieldDefinition(
                name="invoice_date_offset",
                field_type=FieldType.INTEGER,
                label="Invoice Date Offset",
                description="Number of days to offset the invoice date (negative or positive)",
                default=0,
                min_value=-14,
                max_value=14
            ),
            FieldDefinition(
                name="retail_uom",
                field_type=FieldType.BOOLEAN,
                label="Retail UOM",
                description="Use retail unit of measure (each) instead of case",
                default=False
            )
        ]
        return fields
    
    def validate_config(self, config: Dict[str, Any]) -> ValidationResult:
        """Validate configuration data against the format's schema."""
        schema = self.get_configuration_schema()
        if schema:
            return schema.validate(config)
        return ValidationResult(success=True, errors=[])
    
    def create_config(self, data: Dict[str, Any]) -> ScannerWareConfiguration:
        """Create a configuration instance from raw data."""
        return ScannerWareConfiguration(
            a_record_padding=data.get("a_record_padding", ""),
            append_a_records=data.get("append_a_records", False),
            a_record_append_text=data.get("a_record_append_text", ""),
            force_txt_file_ext=data.get("force_txt_file_ext", False),
            invoice_date_offset=data.get("invoice_date_offset", 0),
            retail_uom=data.get("retail_uom", False)
        )
    
    def serialize_config(self, config: ScannerWareConfiguration) -> Dict[str, Any]:
        """Serialize a configuration instance to dictionary format."""
        return {
            "a_record_padding": config.a_record_padding,
            "append_a_records": config.append_a_records,
            "a_record_append_text": config.a_record_append_text,
            "force_txt_file_ext": config.force_txt_file_ext,
            "invoice_date_offset": config.invoice_date_offset,
            "retail_uom": config.retail_uom
        }
    
    def deserialize_config(self, data: Dict[str, Any]) -> ScannerWareConfiguration:
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
