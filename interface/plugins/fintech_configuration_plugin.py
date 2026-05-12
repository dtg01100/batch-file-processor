"""
Fintech Configuration Plugin

Implements the ConfigurationPlugin interface for Fintech format configuration.
"""

from typing import Any

from ..models.folder_configuration import ConvertFormat
from .base_simple_configuration_plugin import BaseSimpleConfigurationPlugin
from .config_schemas import FieldDefinition, FieldType


class FintechConfiguration:
    """Fintech configuration data class."""

    def __init__(self, fintech_division_id: str = "") -> None:
        self.fintech_division_id = fintech_division_id


class FintechConfigurationPlugin(BaseSimpleConfigurationPlugin):
    """Fintech configuration plugin."""

    @classmethod
    def get_name(cls) -> str:
        return "Fintech Configuration"

    @classmethod
    def get_identifier(cls) -> str:
        return "fintech_configuration"

    @classmethod
    def get_format_name(cls) -> str:
        return "Fintech"

    @classmethod
    def get_format_enum(cls) -> ConvertFormat:
        return ConvertFormat.FINTECH

    @classmethod
    def get_config_fields(cls) -> list[FieldDefinition]:
        return [
            FieldDefinition(
                name="fintech_division_id",
                field_type=FieldType.STRING,
                label="Division ID",
                description="The division ID to use for Fintech output",
                default="",
                min_length=1,
                max_length=50,
            )
        ]

    def create_config(self, data: dict[str, Any]) -> FintechConfiguration:
        return FintechConfiguration(
            fintech_division_id=data.get("fintech_division_id", "")
        )

    def serialize_config(self, config: FintechConfiguration) -> dict[str, Any]:
        return {"fintech_division_id": config.fintech_division_id}

    def deserialize_config(self, data: dict[str, Any]) -> FintechConfiguration:
        return self.create_config(data)
