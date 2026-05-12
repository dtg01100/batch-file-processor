"""
CSV Configuration Plugin

Implements the ConfigurationPlugin interface for CSV format configuration.
"""

from typing import Any

from ..models.folder_configuration import ConvertFormat, CSVConfiguration
from .base_simple_configuration_plugin import BaseSimpleConfigurationPlugin
from .config_schemas import FieldDefinition, FieldType


class CSVConfigurationPlugin(BaseSimpleConfigurationPlugin):
    """CSV configuration plugin."""

    @classmethod
    def get_name(cls) -> str:
        return "CSV Configuration"

    @classmethod
    def get_identifier(cls) -> str:
        return "csv_configuration"

    @classmethod
    def get_format_name(cls) -> str:
        return "CSV"

    @classmethod
    def get_format_enum(cls) -> ConvertFormat:
        return ConvertFormat.CSV

    @classmethod
    def get_config_fields(cls) -> list[FieldDefinition]:
        fields = [
            FieldDefinition(
                name="include_headers",
                field_type=FieldType.BOOLEAN,
                label="Include Headers",
                description="Whether to include headers in the CSV output",
                default=False,
            ),
            FieldDefinition(
                name="filter_ampersand",
                field_type=FieldType.BOOLEAN,
                label="Filter Ampersand",
                description="Whether to filter ampersand characters in the output",
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
                description="Sort order for simple CSV format",
                default="",
            ),
            FieldDefinition(
                name="split_prepaid_sales_tax_crec",
                field_type=FieldType.BOOLEAN,
                label="Split Prepaid Sales Tax CREC",
                description="Whether to split prepaid sales tax CREC",
                default=False,
            ),
        ]
        return fields

    def create_config(self, data: dict[str, Any]) -> CSVConfiguration:
        return CSVConfiguration(
            include_headers=data.get("include_headers", False),
            filter_ampersand=data.get("filter_ampersand", False),
            include_item_numbers=data.get("include_item_numbers", False),
            include_item_description=data.get("include_item_description", False),
            simple_csv_sort_order=data.get("simple_csv_sort_order", ""),
            split_prepaid_sales_tax_crec=data.get(
                "split_prepaid_sales_tax_crec", False
            ),
        )

    def serialize_config(self, config: CSVConfiguration) -> dict[str, Any]:
        if isinstance(config, dict):
            return {
                "include_headers": config.get("include_headers", False),
                "filter_ampersand": config.get("filter_ampersand", False),
                "include_item_numbers": config.get("include_item_numbers", False),
                "include_item_description": config.get(
                    "include_item_description", False
                ),
                "simple_csv_sort_order": config.get("simple_csv_sort_order", ""),
                "split_prepaid_sales_tax_crec": config.get(
                    "split_prepaid_sales_tax_crec", False
                ),
            }
        return {
            "include_headers": config.include_headers,
            "filter_ampersand": config.filter_ampersand,
            "include_item_numbers": config.include_item_numbers,
            "include_item_description": config.include_item_description,
            "simple_csv_sort_order": config.simple_csv_sort_order,
            "split_prepaid_sales_tax_crec": config.split_prepaid_sales_tax_crec,
        }

    def deserialize_config(self, data: dict[str, Any]) -> CSVConfiguration:
        if isinstance(data, CSVConfiguration):
            return data
        return self.create_config(data)
