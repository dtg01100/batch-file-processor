"""
Tweaks Configuration Plugin

Implements the ConfigurationPlugin interface for Tweaks format configuration.
Provides support for Tweaks-specific configuration fields and validation based
on the EDITweaker's TweakerConfig options.
"""

from typing import Any, Dict, List, Optional

from ..models.folder_configuration import ConvertFormat
from .config_schemas import FieldDefinition, FieldType
from .configuration_plugin import ConfigurationPlugin
from .ui_abstraction import ConfigurationWidgetBuilder
from .validation_framework import ValidationResult


class TweaksConfiguration:
    """Tweaks configuration data class."""

    def __init__(
        self,
        pad_arec: bool = False,
        arec_padding: str = "",
        arec_padding_len: int = 0,
        append_arec: bool = False,
        append_arec_text: str = "",
        invoice_date_custom_format: bool = False,
        invoice_date_custom_format_string: str = "%Y-%m-%d",
        force_txt_file_ext: bool = False,
        calc_upc: bool = False,
        invoice_date_offset: int = 0,
        retail_uom: bool = False,
        override_upc: bool = False,
        override_upc_level: int = 1,
        override_upc_category_filter: str = "ALL",
        split_prepaid_sales_tax_crec: bool = False,
        upc_target_length: int = 11,
        upc_padding_pattern: str = "           ",
    ):
        self.pad_arec = pad_arec
        self.arec_padding = arec_padding
        self.arec_padding_len = arec_padding_len
        self.append_arec = append_arec
        self.append_arec_text = append_arec_text
        self.invoice_date_custom_format = invoice_date_custom_format
        self.invoice_date_custom_format_string = invoice_date_custom_format_string
        self.force_txt_file_ext = force_txt_file_ext
        self.calc_upc = calc_upc
        self.invoice_date_offset = invoice_date_offset
        self.retail_uom = retail_uom
        self.override_upc = override_upc
        self.override_upc_level = override_upc_level
        self.override_upc_category_filter = override_upc_category_filter
        self.split_prepaid_sales_tax_crec = split_prepaid_sales_tax_crec
        self.upc_target_length = upc_target_length
        self.upc_padding_pattern = upc_padding_pattern


class TweaksConfigurationPlugin(ConfigurationPlugin):
    """
    Tweaks configuration plugin implementing the ConfigurationPlugin interface.

    Provides support for Tweaks format configuration with specific fields
    based on EDITweaker's TweakerConfig options.
    """

    @classmethod
    def get_name(cls) -> str:
        """Get the human-readable name of the plugin."""
        return "Tweaks Configuration"

    @classmethod
    def get_identifier(cls) -> str:
        """Get the unique identifier for the plugin."""
        return "tweaks_configuration"

    @classmethod
    def get_description(cls) -> str:
        """Get a detailed description of the plugin's functionality."""
        return (
            "Provides Tweaks format configuration options for EDI tweaking "
            "including A-record padding, invoice date handling, UPC modifications"
        )

    @classmethod
    def get_version(cls) -> str:
        """Get the plugin version."""
        return "1.0.0"

    @classmethod
    def get_format_name(cls) -> str:
        """Get the human-readable name of the configuration format."""
        return "Tweaks"

    @classmethod
    def get_format_enum(cls) -> ConvertFormat:
        """Get the ConvertFormat enum value associated with this format."""
        return ConvertFormat.TWEAKS

    @classmethod
    def get_config_fields(cls) -> List[FieldDefinition]:
        """Get the list of field definitions for this configuration format."""
        fields = [
            # A-Record Padding
            FieldDefinition(
                name="pad_arec",
                field_type=FieldType.BOOLEAN,
                label="Pad A-Records",
                description="Whether to pad A records with custom text",
                default=False,
            ),
            FieldDefinition(
                name="arec_padding",
                field_type=FieldType.STRING,
                label="A-Record Padding Text",
                description="Text to use for A record padding",
                default="",
            ),
            FieldDefinition(
                name="arec_padding_len",
                field_type=FieldType.INTEGER,
                label="A-Record Padding Length",
                description="Length for A record padding",
                default=0,
                min_value=0,
                max_value=100,
            ),
            # A-Record Appending
            FieldDefinition(
                name="append_arec",
                field_type=FieldType.BOOLEAN,
                label="Append to A-Records",
                description="Whether to append text to A records",
                default=False,
            ),
            FieldDefinition(
                name="append_arec_text",
                field_type=FieldType.STRING,
                label="A-Record Append Text",
                description="Text to append to A records (use %po_str% for PO number lookup)",
                default="",
            ),
            # Invoice Date Handling
            FieldDefinition(
                name="invoice_date_custom_format",
                field_type=FieldType.BOOLEAN,
                label="Custom Invoice Date Format",
                description="Use custom date format for invoice dates",
                default=False,
            ),
            FieldDefinition(
                name="invoice_date_custom_format_string",
                field_type=FieldType.STRING,
                label="Invoice Date Format String",
                description="Python date format string (e.g., %%Y-%%m-%%d)",
                default="%Y-%m-%d",
            ),
            FieldDefinition(
                name="invoice_date_offset",
                field_type=FieldType.INTEGER,
                label="Invoice Date Offset (Days)",
                description="Days to offset invoice date (negative for past)",
                default=0,
                min_value=-365,
                max_value=365,
            ),
            # Output File Options
            FieldDefinition(
                name="force_txt_file_ext",
                field_type=FieldType.BOOLEAN,
                label="Force .txt Extension",
                description="Force .txt extension on output file",
                default=False,
            ),
            # UPC Options
            FieldDefinition(
                name="calc_upc",
                field_type=FieldType.BOOLEAN,
                label="Calculate UPC Check Digit",
                description="Calculate UPC check digit",
                default=False,
            ),
            FieldDefinition(
                name="retail_uom",
                field_type=FieldType.BOOLEAN,
                label="Retail UOM Conversion",
                description="Convert to retail UOM (case to each)",
                default=False,
            ),
            # UPC Override
            FieldDefinition(
                name="override_upc",
                field_type=FieldType.BOOLEAN,
                label="Override UPC from Lookup",
                description="Override UPC from lookup table",
                default=False,
            ),
            FieldDefinition(
                name="override_upc_level",
                field_type=FieldType.INTEGER,
                label="UPC Override Level",
                description="UPC level for override (1=pack, 2=case)",
                default=1,
                min_value=1,
                max_value=2,
            ),
            FieldDefinition(
                name="override_upc_category_filter",
                field_type=FieldType.STRING,
                label="UPC Override Category Filter",
                description="Category filter for UPC override (use ALL or comma-separated list)",
                default="ALL",
            ),
            # UPC Padding
            FieldDefinition(
                name="upc_target_length",
                field_type=FieldType.INTEGER,
                label="UPC Target Length",
                description="Target UPC length",
                default=11,
                min_value=6,
                max_value=14,
            ),
            FieldDefinition(
                name="upc_padding_pattern",
                field_type=FieldType.STRING,
                label="UPC Padding Pattern",
                description="Pattern for UPC padding (spaces for left padding)",
                default="           ",
            ),
            # Tax Handling
            FieldDefinition(
                name="split_prepaid_sales_tax_crec",
                field_type=FieldType.BOOLEAN,
                label="Split Prepaid Sales Tax CREC",
                description="Split prepaid sales tax into C records",
                default=False,
            ),
        ]
        return fields

    def validate_config(self, config: Dict[str, Any]) -> ValidationResult:
        """Validate configuration data against the format's schema."""
        schema = self.get_configuration_schema()
        if schema:
            return schema.validate(config)
        return ValidationResult(success=True, errors=[])

    def create_config(self, data: Dict[str, Any]) -> TweaksConfiguration:
        """Create a configuration instance from raw data."""
        return TweaksConfiguration(
            pad_arec=data.get("pad_arec", False),
            arec_padding=data.get("arec_padding", ""),
            arec_padding_len=data.get("arec_padding_len", 0),
            append_arec=data.get("append_arec", False),
            append_arec_text=data.get("append_arec_text", ""),
            invoice_date_custom_format=data.get("invoice_date_custom_format", False),
            invoice_date_custom_format_string=data.get(
                "invoice_date_custom_format_string", "%Y-%m-%d"
            ),
            force_txt_file_ext=data.get("force_txt_file_ext", False),
            calc_upc=data.get("calc_upc", False),
            invoice_date_offset=data.get("invoice_date_offset", 0),
            retail_uom=data.get("retail_uom", False),
            override_upc=data.get("override_upc", False),
            override_upc_level=data.get("override_upc_level", 1),
            override_upc_category_filter=data.get("override_upc_category_filter", "ALL"),
            split_prepaid_sales_tax_crec=data.get("split_prepaid_sales_tax_crec", False),
            upc_target_length=data.get("upc_target_length", 11),
            upc_padding_pattern=data.get("upc_padding_pattern", "           "),
        )

    def serialize_config(self, config: TweaksConfiguration) -> Dict[str, Any]:
        """Serialize a configuration instance to dictionary format."""
        if isinstance(config, dict):
            return config
        return {
            "pad_arec": config.pad_arec,
            "arec_padding": config.arec_padding,
            "arec_padding_len": config.arec_padding_len,
            "append_arec": config.append_arec,
            "append_arec_text": config.append_arec_text,
            "invoice_date_custom_format": config.invoice_date_custom_format,
            "invoice_date_custom_format_string": config.invoice_date_custom_format_string,
            "force_txt_file_ext": config.force_txt_file_ext,
            "calc_upc": config.calc_upc,
            "invoice_date_offset": config.invoice_date_offset,
            "retail_uom": config.retail_uom,
            "override_upc": config.override_upc,
            "override_upc_level": config.override_upc_level,
            "override_upc_category_filter": config.override_upc_category_filter,
            "split_prepaid_sales_tax_crec": config.split_prepaid_sales_tax_crec,
            "upc_target_length": config.upc_target_length,
            "upc_padding_pattern": config.upc_padding_pattern,
        }

    def deserialize_config(self, data: Dict[str, Any]) -> TweaksConfiguration:
        """Deserialize stored data into a configuration instance."""
        if isinstance(data, TweaksConfiguration):
            return data
        return self.create_config(data)

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the plugin with configuration."""
        if config:
            self._config = self.create_config(config)
        else:
            self._config = self.create_config({})

    def activate(self) -> None:
        """Activate the plugin."""

    def deactivate(self) -> None:
        """Deactivate the plugin."""

    def create_widget(self, parent: Any = None) -> Any:
        """Create a UI widget for configuring the plugin."""
        schema = self.get_configuration_schema()
        if schema:
            builder = ConfigurationWidgetBuilder()
            return builder.build_configuration_panel(
                schema,
                self._config.__dict__ if hasattr(self, "_config") else {},
                parent,
            )
        return None
