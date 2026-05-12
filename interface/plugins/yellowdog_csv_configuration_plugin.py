"""
YellowDog CSV Configuration Plugin

Implements the ConfigurationPlugin interface for YellowDog CSV format configuration.
"""

from ..models.folder_configuration import ConvertFormat
from .base_simple_configuration_plugin import BaseSimpleConfigurationPlugin


class YellowDogCSVConfigurationPlugin(BaseSimpleConfigurationPlugin):
    """YellowDog CSV configuration plugin."""

    @classmethod
    def get_name(cls) -> str:
        return "YellowDog CSV Configuration"

    @classmethod
    def get_identifier(cls) -> str:
        return "yellowdog_csv_configuration"

    @classmethod
    def get_format_name(cls) -> str:
        return "YellowDog CSV"

    @classmethod
    def get_format_enum(cls) -> ConvertFormat:
        return ConvertFormat.YELLOWDOG_CSV
