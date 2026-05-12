"""
Jolley Custom Configuration Plugin

Implements the ConfigurationPlugin interface for Jolley Custom format configuration.
"""

from ..models.folder_configuration import ConvertFormat
from .base_simple_configuration_plugin import BaseSimpleConfigurationPlugin


class JolleyCustomConfigurationPlugin(BaseSimpleConfigurationPlugin):
    """Jolley Custom configuration plugin."""

    @classmethod
    def get_name(cls) -> str:
        return "Jolley Custom Configuration"

    @classmethod
    def get_identifier(cls) -> str:
        return "jolley_custom_configuration"

    @classmethod
    def get_format_name(cls) -> str:
        return "Jolley Custom"

    @classmethod
    def get_format_enum(cls) -> ConvertFormat:
        return ConvertFormat.JOLLEY_CUSTOM
