"""
Plugin System Foundation

This module provides the core plugin architecture for extending the
application's functionality through dynamically discoverable plugins.

Key Components:
- PluginBase: Base interface for all plugins
- PluginManager: Dynamic plugin discovery and management
- Configuration schemas: Validation and configuration management
- UI abstraction layer: Framework-agnostic widget creation
"""

from .base_simple_configuration_plugin import BaseSimpleConfigurationPlugin
from .config_schemas import ConfigurationSchema, FieldDefinition, FieldType
from .configuration_plugin import ConfigurationPlugin
from .csv_configuration_plugin import CSVConfigurationPlugin
from .estore_einvoice_configuration_plugin import EStoreEInvoiceConfigurationPlugin
from .estore_einvoice_generic_configuration_plugin import (
    EStoreEInvoiceGenericConfigurationPlugin,
)
from .fintech_configuration_plugin import FintechConfigurationPlugin
from .jolley_custom_configuration_plugin import JolleyCustomConfigurationPlugin
from .plugin_base import PluginBase
from .plugin_manager import PluginManager
from .scannerware_configuration_plugin import ScannerWareConfigurationPlugin
from .scansheet_type_a_configuration_plugin import ScanSheetTypeAConfigurationPlugin
from .simplified_csv_configuration_plugin import SimplifiedCSVConfigurationPlugin
from .stewarts_custom_configuration_plugin import StewartsCustomConfigurationPlugin
from .validation_framework import ValidationResult, Validator
from .yellowdog_csv_configuration_plugin import YellowDogCSVConfigurationPlugin

__all__ = [
    "PluginBase",
    "PluginManager",
    "ConfigurationPlugin",
    "BaseSimpleConfigurationPlugin",
    "ConfigurationSchema",
    "FieldType",
    "FieldDefinition",
    "ValidationResult",
    "Validator",
    "CSVConfigurationPlugin",
    "SimplifiedCSVConfigurationPlugin",
    "FintechConfigurationPlugin",
    "ScannerWareConfigurationPlugin",
    "EStoreEInvoiceConfigurationPlugin",
    "EStoreEInvoiceGenericConfigurationPlugin",
    "JolleyCustomConfigurationPlugin",
    "StewartsCustomConfigurationPlugin",
    "YellowDogCSVConfigurationPlugin",
    "ScanSheetTypeAConfigurationPlugin",
]
