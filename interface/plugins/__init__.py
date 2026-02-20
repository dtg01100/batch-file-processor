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

from .plugin_base import PluginBase
from .plugin_manager import PluginManager
from .configuration_plugin import ConfigurationPlugin
from .config_schemas import ConfigurationSchema, FieldType, FieldDefinition
from .validation_framework import ValidationResult, Validator
from .csv_configuration_plugin import CSVConfigurationPlugin
from .simplified_csv_configuration_plugin import SimplifiedCSVConfigurationPlugin
from .fintech_configuration_plugin import FintechConfigurationPlugin
from .scannerware_configuration_plugin import ScannerWareConfigurationPlugin
from .estore_einvoice_configuration_plugin import EStoreEInvoiceConfigurationPlugin
from .estore_einvoice_generic_configuration_plugin import EStoreEInvoiceGenericConfigurationPlugin
from .jolley_custom_configuration_plugin import JolleyCustomConfigurationPlugin
from .stewarts_custom_configuration_plugin import StewartsCustomConfigurationPlugin
from .yellowdog_csv_configuration_plugin import YellowDogCSVConfigurationPlugin
from .scansheet_type_a_configuration_plugin import ScanSheetTypeAConfigurationPlugin

__all__ = [
    'PluginBase',
    'PluginManager',
    'ConfigurationPlugin',
    'ConfigurationSchema',
    'FieldType',
    'FieldDefinition',
    'ValidationResult',
    'Validator',
    'CSVConfigurationPlugin',
    'SimplifiedCSVConfigurationPlugin',
    'FintechConfigurationPlugin',
    'ScannerWareConfigurationPlugin',
    'EStoreEInvoiceConfigurationPlugin',
    'EStoreEInvoiceGenericConfigurationPlugin',
    'JolleyCustomConfigurationPlugin',
    'StewartsCustomConfigurationPlugin',
    'YellowDogCSVConfigurationPlugin',
    'ScanSheetTypeAConfigurationPlugin'
]
