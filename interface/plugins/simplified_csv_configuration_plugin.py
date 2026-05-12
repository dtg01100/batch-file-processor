"""
Simplified CSV Configuration Plugin

Implements the ConfigurationPlugin interface for Simplified CSV format configuration.
"""

from typing import Any

from ..models.folder_configuration import ConvertFormat
from .base_simple_configuration_plugin import BaseSimpleConfigurationPlugin
from .config_schemas import FieldDefinition, FieldType


class SimplifiedCSVConfiguration:
    """Simplified CSV configuration data class."""

    def __init__(
        self,
        *,
        retail_uom: bool = False,
        include_headers: bool = False,
        include_item_numbers: bool = False,
        include_item_description: bool = False,
        simple_csv_sort_order: str = "",
    ) -> None:
        self.retail_uom = retail_uom
        self.include_headers = include_headers
        self.include_item_numbers = include_item_numbers
        self.include_item_description = include_item_description
        self.simple_csv_sort_order = simple_csv_sort_order


class SimplifiedCSVConfigurationPlugin(BaseSimpleConfigurationPlugin):
    """Simplified CSV configuration plugin."""

    @classmethod
    def get_name(cls) -> str:
        return "Simplified CSV Configuration"

    @classmethod
    def get_identifier(cls) -> str:
        return "simplified_csv_configuration"

    @classmethod
    def get_format_name(cls) -> str:
        return "Simplified CSV"

    @classmethod
    def get_format_enum(cls) -> ConvertFormat:
        return ConvertFormat.SIMPLIFIED_CSV

    @classmethod
    def get_config_fields(cls) -> list[FieldDefinition]:
        return [
            FieldDefinition(
                name="retail_uom",
                field_type=FieldType.BOOLEAN,
                label="Retail UOM",
                description="Use retail unit of measure (each) instead of case",
                default=False,
            ),
            FieldDefinition(
                name="include_headers",
                field_type=FieldType.BOOLEAN,
                label="Include Headers",
                description="Whether to include headers in the CSV output",
                default=False,
            ),
            FieldDefinition(
                name="include_item_numbers",
                field_type=FieldType.BOOLEAN,
                label="Include Item Numbers",
                description="Whether to include item numbers in the CSV output",
                default=False,
            ),
            FieldDefinition(
                name="include_item_description",
                field_type=FieldType.BOOLEAN,
                label="Include Item Description",
                description="Whether to include item descriptions in the CSV output",
                default=False,
            ),
            FieldDefinition(
                name="simple_csv_sort_order",
                field_type=FieldType.STRING,
                label="Simple CSV Sort Order",
                description=(
                    "Sort order for simple CSV format"
                    " (comma-separated column names)"
                ),
                default="",
            ),
        ]

    def create_config(self, data: dict[str, Any]) -> SimplifiedCSVConfiguration:
        return SimplifiedCSVConfiguration(
            retail_uom=data.get("retail_uom", False),
            include_headers=data.get("include_headers", False),
            include_item_numbers=data.get("include_item_numbers", False),
            include_item_description=data.get("include_item_description", False),
            simple_csv_sort_order=data.get("simple_csv_sort_order", ""),
        )

    def serialize_config(self, config: SimplifiedCSVConfiguration) -> dict[str, Any]:
        return {
            "retail_uom": config.retail_uom,
            "include_headers": config.include_headers,
            "include_item_numbers": config.include_item_numbers,
            "include_item_description": config.include_item_description,
            "simple_csv_sort_order": config.simple_csv_sort_order,
        }

    def deserialize_config(self, data: dict[str, Any]) -> SimplifiedCSVConfiguration:
        return self.create_config(data)
