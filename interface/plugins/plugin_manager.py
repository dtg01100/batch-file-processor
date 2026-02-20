"""
Plugin Manager

Responsible for dynamic plugin discovery, management, and lifecycle control.
"""

import importlib
import os
import pkgutil
from typing import Dict, List, Optional, Type, Any

from .plugin_base import PluginBase
from .folder_config_plugin import FolderConfigPlugin


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

    def get_folder_config_plugins(self) -> List[Type[FolderConfigPlugin]]:
        """
        Get all folder configuration plugin classes.

        Returns:
            List[Type[FolderConfigPlugin]]: List of folder configuration plugin classes
        """
        folder_plugins = []
        for plugin_class in self._plugin_classes.values():
            if issubclass(plugin_class, FolderConfigPlugin) and plugin_class is not FolderConfigPlugin:
                folder_plugins.append(plugin_class)
        return folder_plugins

    def get_initialized_folder_config_plugins(self) -> List[FolderConfigPlugin]:
        """
        Get all initialized folder configuration plugin instances.

        Returns:
            List[FolderConfigPlugin]: List of initialized folder configuration plugin instances
        """
        folder_plugins = []
        for plugin in self._plugins.values():
            if isinstance(plugin, FolderConfigPlugin):
                folder_plugins.append(plugin)
        return folder_plugins

    def get_folder_config_plugins_by_column(self, column: str) -> List[Type[FolderConfigPlugin]]:
        """
        Get folder configuration plugins by column.

        Args:
            column: Column identifier (LEFT, RIGHT, or CENTER)

        Returns:
            List[Type[FolderConfigPlugin]]: List of folder configuration plugin classes in the specified column
        """
        plugins = self.get_folder_config_plugins()
        return [
            plugin for plugin in plugins
            if plugin.get_column() == column
        ]

    def get_folder_config_plugins_by_section(self, column: str, section: str) -> List[Type[FolderConfigPlugin]]:
        """
        Get folder configuration plugins by column and section.

        Args:
            column: Column identifier (LEFT, RIGHT, or CENTER)
            section: Section name

        Returns:
            List[Type[FolderConfigPlugin]]: List of folder configuration plugin classes in the specified section
        """
        plugins = self.get_folder_config_plugins_by_column(column)
        return [
            plugin for plugin in plugins
            if plugin.get_section() == section
        ]

    def get_sorted_folder_config_plugins(self) -> List[Type[FolderConfigPlugin]]:
        """
        Get all folder configuration plugins sorted by their placement.

        Plugins are sorted first by column, then by section order, then by widget order.

        Returns:
            List[Type[FolderConfigPlugin]]: Sorted list of folder configuration plugin classes
        """
        plugins = self.get_folder_config_plugins()
        return sorted(
            plugins,
            key=lambda p: (
                p.get_column(),
                p.get_section_order(),
                p.get_section(),
                p.get_widget_order()
            )
        )

    def get_folder_config_sections(self, column: str) -> List[str]:
        """
        Get all unique section names for folder configuration plugins in a column.

        Args:
            column: Column identifier (LEFT, RIGHT, or CENTER)

        Returns:
            List[str]: List of unique section names
        """
        plugins = self.get_folder_config_plugins_by_column(column)
        sections = set()
        for plugin in plugins:
            sections.add(plugin.get_section())
        return list(sections)

    def get_sorted_folder_config_sections(self, column: str) -> List[str]:
        """
        Get sorted section names for folder configuration plugins in a column.

        Sections are sorted by their section order.

        Args:
            column: Column identifier (LEFT, RIGHT, or CENTER)

        Returns:
            List[str]: Sorted list of section names
        """
        plugins = self.get_folder_config_plugins_by_column(column)
        section_info = {}
        for plugin in plugins:
            section = plugin.get_section()
            if section not in section_info:
                section_info[section] = plugin.get_section_order()
        sorted_sections = sorted(
            section_info.items(),
            key=lambda x: x[1]
        )
        return [section for section, _ in sorted_sections]

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

    def _build_dependency_graph(self):
        """
        Build a simple dependency graph for plugins.
        
        Returns:
            List of plugin classes in dependency order
        """
        # For simplicity, return plugins in any order (no dependency resolution)
        return list(self._plugin_classes.values())

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
            except Exception as e:
                print(f"Error initializing plugin {plugin_class.get_name()}: {e}")

        self._initialized = True
        return initialized

