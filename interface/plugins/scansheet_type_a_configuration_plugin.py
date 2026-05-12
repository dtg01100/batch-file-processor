"""
ScanSheet Type A Configuration Plugin

Implements the ConfigurationPlugin interface for ScanSheet Type A format configuration.
"""

from ..models.folder_configuration import ConvertFormat
from .base_simple_configuration_plugin import BaseSimpleConfigurationPlugin


class ScanSheetTypeAConfigurationPlugin(BaseSimpleConfigurationPlugin):
    """ScanSheet Type A configuration plugin."""

    @classmethod
    def get_name(cls) -> str:
        return "ScanSheet Type A Configuration"

    @classmethod
    def get_identifier(cls) -> str:
        return "scansheet_type_a_configuration"

    @classmethod
    def get_format_name(cls) -> str:
        return "ScanSheet Type A"

    @classmethod
    def get_format_enum(cls) -> ConvertFormat:
        return ConvertFormat.SCANSHEET_TYPE_A
