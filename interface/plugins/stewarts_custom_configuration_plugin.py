"""
Stewarts Custom Configuration Plugin

Implements the ConfigurationPlugin interface for Stewarts Custom format configuration.
"""

from ..models.folder_configuration import ConvertFormat
from .base_simple_configuration_plugin import BaseSimpleConfigurationPlugin


class StewartsCustomConfigurationPlugin(BaseSimpleConfigurationPlugin):
    """Stewarts Custom configuration plugin."""

    @classmethod
    def get_name(cls) -> str:
        return "Stewarts Custom Configuration"

    @classmethod
    def get_identifier(cls) -> str:
        return "stewarts_custom_configuration"

    @classmethod
    def get_format_name(cls) -> str:
        return "Stewarts Custom"

    @classmethod
    def get_format_enum(cls) -> ConvertFormat:
        return ConvertFormat.STEWARTS_CUSTOM
