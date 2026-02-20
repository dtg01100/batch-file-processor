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

__all__ = [
    'PluginBase',
    'PluginManager',
    'ConfigurationPlugin',
    'ConfigurationSchema',
    'FieldType',
    'FieldDefinition',
    'ValidationResult',
    'Validator'
]
