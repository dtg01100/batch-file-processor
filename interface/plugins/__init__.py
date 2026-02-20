"""
Plugin System Foundation

This module provides the core plugin architecture for extending the
application's functionality through dynamically discoverable plugins.

Key Components:
- PluginBase: Base interface for all plugins
- FolderConfigPlugin: Specialized interface for folder configuration sections
- PluginManager: Dynamic plugin discovery and management
- Configuration schemas: Validation and configuration management
- UI abstraction layer: Framework-agnostic widget creation
"""

from .plugin_base import PluginBase
from .folder_config_plugin import FolderConfigPlugin
from .plugin_manager import PluginManager
from .config_schemas import ConfigurationSchema, FieldType
from .validation_framework import ValidationResult, Validator

__all__ = [
    'PluginBase',
    'FolderConfigPlugin',
    'PluginManager',
    'ConfigurationSchema',
    'FieldType',
    'ValidationResult',
    'Validator'
]
