"""
Plugin Manager

Responsible for dynamic plugin discovery, management, and lifecycle control.
"""

import importlib
import os
import pkgutil
from typing import Dict, List, Optional, Type, Any

from .plugin_base import PluginBase
from .configuration_plugin import ConfigurationPlugin
from ..models.folder_configuration import ConvertFormat
from .validation_framework import ValidationResult
from .config_schemas import FieldDefinition


class PluginManager:
    """
    Dynamic plugin discovery and management system.

    Handles:
    - Plugin discovery from specified directories
    - Plugin instantiation and lifecycle management
    - Configuration management
    - Dependency resolution
    """

    def __init__(self, plugin_directories: Optional[List[str]] = None):
        """
        Initialize the plugin manager.

        Args:
            plugin_directories: Optional list of directories to search for plugins.
                If None, uses default plugin directories.
        """
        self._plugin_directories = plugin_directories or []
        self._plugins: Dict[str, PluginBase] = {}
        self._plugin_classes: Dict[str, Type[PluginBase]] = {}
        self._configurations: Dict[str, Dict[str, Any]] = {}
        self._initialized = False
        # Configuration plugin specific storage
        self._configuration_plugins: Dict[ConvertFormat, ConfigurationPlugin] = {}
        self._configuration_plugin_classes: Dict[ConvertFormat, Type[ConfigurationPlugin]] = {}

    def add_plugin_directory(self, directory: str) -> None:
        """
        Add a directory to the plugin search path.

        Args:
            directory: Path to directory containing plugins
        """
        if directory not in self._plugin_directories:
            self._plugin_directories.append(directory)

    def discover_plugins(self) -> List[str]:
        """
        Discover all available plugins in configured directories.

        Returns:
            List[str]: List of discovered plugin identifiers
        """
        discovered = []

        # Search in plugin directories
        for directory in self._plugin_directories:
            if os.path.exists(directory):
                self._discover_plugins_in_directory(directory, discovered)

        # Search in package
        self._discover_plugins_in_package('interface.plugins', discovered)

        return discovered

    def _discover_plugins_in_directory(self, directory: str, discovered: List[str]) -> None:
        """
        Discover plugins in a specific directory.

        Args:
            directory: Directory to search
            discovered: List to append discovered plugins to
        """
        for root, _, files in os.walk(directory):
            for file_name in files:
                if file_name.endswith('.py') and not file_name.startswith('__'):
                    module_path = os.path.join(root, file_name)
                    try:
                        self._load_plugin_module(module_path, discovered)
                    except Exception as e:
                        print(f"Error loading plugin module {module_path}: {e}")

    def _discover_plugins_in_package(self, package_name: str, discovered: List[str]) -> None:
        """
        Discover plugins in a Python package.

        Args:
            package_name: Package name to search
            discovered: List to append discovered plugins to
        """
        try:
            package = importlib.import_module(package_name)
            if hasattr(package, '__path__'):
                for _, name, is_pkg in pkgutil.iter_modules(package.__path__):
                    if not is_pkg:
                        module_name = f"{package_name}.{name}"
                        try:
                            self._load_plugin_module_by_name(module_name, discovered)
                        except Exception as e:
                            print(f"Error loading plugin module {module_name}: {e}")
        except ImportError as e:
            print(f"Error importing package {package_name}: {e}")

    def _load_plugin_module(self, module_path: str, discovered: List[str]) -> None:
        """
        Load a plugin module from file path.

        Args:
            module_path: Path to plugin module
            discovered: List to append discovered plugins to
        """
        module_name = os.path.splitext(os.path.basename(module_path))[0]
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self._extract_plugins_from_module(module, discovered)

    def _load_plugin_module_by_name(self, module_name: str, discovered: List[str]) -> None:
        """
        Load a plugin module by name.

        Args:
            module_name: Module name to load
            discovered: List to append discovered plugins to
        """
        module = importlib.import_module(module_name)
        self._extract_plugins_from_module(module, discovered)

    def _extract_plugins_from_module(self, module: Any, discovered: List[str]) -> None:
        """
        Extract plugin classes from a module.

        Args:
            module: Module to examine
            discovered: List to append discovered plugins to
        """
        for name, obj in module.__dict__.items():
            if (
                isinstance(obj, type) and
                issubclass(obj, PluginBase) and
                obj is not PluginBase and
                not obj.__name__.startswith('_')
            ):
                plugin_id = obj.get_identifier()
                if plugin_id not in self._plugin_classes:
                    self._plugin_classes[plugin_id] = obj
                    discovered.append(plugin_id)
                
                # If it's a ConfigurationPlugin, also store in configuration plugin maps
                if (
                    isinstance(obj, type) and
                    issubclass(obj, ConfigurationPlugin) and
                    obj is not ConfigurationPlugin and
                    not obj.__name__.startswith('_')
                ):
                    try:
                        format_enum = obj.get_format_enum()
                        if format_enum not in self._configuration_plugin_classes:
                            self._configuration_plugin_classes[format_enum] = obj
                    except Exception as e:
                        print(f"Error extracting configuration plugin {name}: {e}")

    def get_configuration_plugins(self) -> List[ConfigurationPlugin]:
        """
        Get all available configuration plugins.

        Returns:
            List[ConfigurationPlugin]: List of all configuration plugin instances
        """
        if not self._initialized:
            self.initialize_plugins()
        
        return list(self._configuration_plugins.values())

    def get_configuration_plugin_by_format(self, format_enum: ConvertFormat) -> Optional[ConfigurationPlugin]:
        """
        Get configuration plugin by format enum.

        Args:
            format_enum: ConvertFormat enum value

        Returns:
            Optional[ConfigurationPlugin]: Configuration plugin instance or None if not found
        """
        if not self._initialized:
            self.initialize_plugins()
        
        return self._configuration_plugins.get(format_enum)

    def get_configuration_plugin_by_format_name(self, format_name: str) -> Optional[ConfigurationPlugin]:
        """
        Get configuration plugin by format name.

        Args:
            format_name: Format name string

        Returns:
            Optional[ConfigurationPlugin]: Configuration plugin instance or None if not found
        """
        if not self._initialized:
            self.initialize_plugins()
        
        for plugin in self._configuration_plugins.values():
            if plugin.get_format_name().lower() == format_name.lower():
                return plugin
        
        return None

    def create_configuration_widget(self, format_enum: ConvertFormat, parent: Any = None) -> Any:
        """
        Create a configuration widget for a specific format.

        Args:
            format_enum: ConvertFormat enum value
            parent: Optional parent widget

        Returns:
            Any: UI widget for configuration or None if format not supported
        """
        plugin = self.get_configuration_plugin_by_format(format_enum)
        if plugin:
            return plugin.create_widget(parent)
        
        return None

    def validate_configuration(self, format_enum: ConvertFormat, config: Dict[str, Any]) -> ValidationResult:
        """
        Validate configuration data for a specific format.

        Args:
            format_enum: ConvertFormat enum value
            config: Configuration data to validate

        Returns:
            ValidationResult: Result of the validation operation
        """
        plugin = self.get_configuration_plugin_by_format(format_enum)
        if plugin:
            return plugin.validate_config(config)
        
        from .validation_framework import ValidationResult
        return ValidationResult(success=False, errors=["Unsupported format"])

    def create_configuration(self, format_enum: ConvertFormat, data: Dict[str, Any]) -> Any:
        """
        Create a configuration instance for a specific format.

        Args:
            format_enum: ConvertFormat enum value
            data: Raw data to create the configuration from

        Returns:
            Any: Configuration instance specific to the format
        """
        plugin = self.get_configuration_plugin_by_format(format_enum)
        if plugin:
            return plugin.create_config(data)
        
        return None

    def serialize_configuration(self, format_enum: ConvertFormat, config: Any) -> Dict[str, Any]:
        """
        Serialize a configuration instance for a specific format.

        Args:
            format_enum: ConvertFormat enum value
            config: Configuration instance to serialize

        Returns:
            Dict[str, Any]: Serialized configuration data
        """
        plugin = self.get_configuration_plugin_by_format(format_enum)
        if plugin:
            return plugin.serialize_config(config)
        
        return {}

    def deserialize_configuration(self, format_enum: ConvertFormat, data: Dict[str, Any]) -> Any:
        """
        Deserialize configuration data for a specific format.

        Args:
            format_enum: ConvertFormat enum value
            data: Stored data to deserialize

        Returns:
            Any: Configuration instance specific to the format
        """
        plugin = self.get_configuration_plugin_by_format(format_enum)
        if plugin:
            return plugin.deserialize_config(data)
        
        return None

    def get_configuration_fields(self, format_enum: ConvertFormat):
        """
        Get the configuration field definitions for a specific format.

        Args:
            format_enum: ConvertFormat enum value

        Returns:
            List[FieldDefinition]: List of field definitions for the format
        """
        plugin_class = self._configuration_plugin_classes.get(format_enum)
        if plugin_class:
            return plugin_class.get_config_fields()
        
        return []

    def initialize_plugins(self, config: Optional[Dict[str, Dict[str, Any]]] = None) -> List[str]:
        """
        Initialize all discovered plugins.

        Args:
            config: Optional plugin configurations

        Returns:
            List[str]: List of initialized plugin identifiers
        """
        if self._initialized:
            return list(self._plugins.keys())

        config = config or {}
        initialized = []

        # Resolve dependencies
        dependency_graph = self._build_dependency_graph()
        
        # Initialize plugins
        for plugin_class in dependency_graph:
            try:
                plugin_id = plugin_class.get_identifier()
                plugin_config = config.get(plugin_id, {})
                plugin = plugin_class()
                plugin.initialize(plugin_config)
                plugin.activate()
                self._plugins[plugin_id] = plugin
                self._configurations[plugin_id] = plugin_config
                initialized.append(plugin_id)
                
                # If it's a ConfigurationPlugin, also store in configuration plugins map
                if isinstance(plugin, ConfigurationPlugin):
                    try:
                        format_enum = plugin_class.get_format_enum()
                        self._configuration_plugins[format_enum] = plugin
                    except Exception as e:
                        print(f"Error storing configuration plugin {plugin_id}: {e}")
                        
            except Exception as e:
                print(f"Error initializing plugin {plugin_class.get_name()}: {e}")

        self._initialized = True
        return initialized

    def _build_dependency_graph(self):
        """
        Build a simple dependency graph for plugins.

        Returns:
            List of plugin classes in dependency order
        """
        # For simplicity, return plugins in any order (no dependency resolution)
        return list(self._plugin_classes.values())

