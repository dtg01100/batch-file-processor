"""
Folder Configuration Plugin Type

Defines a specialized plugin interface for folder configuration sections.
This extends the base PluginBase with additional methods for:
1. Defining widget placement (column, section)
2. Providing configuration schema for plugin settings
3. Handling data extraction and population
4. Validating plugin configuration

Folder configuration plugins are used to dynamically extend the folder
configuration UI with custom sections and functionality.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple

from .plugin_base import PluginBase
from .config_schemas import ConfigurationSchema
from .validation_framework import ValidationResult


class FolderConfigPlugin(PluginBase, ABC):
    """
    Base interface for folder configuration plugins.

    Extends the base PluginBase with additional methods specific to
    folder configuration sections.
    """

    # Widget placement constants
    class Column(ABC):
        """
        Represents the column where the plugin's widget should appear.
        """
        LEFT = "left"
        RIGHT = "right"
        CENTER = "center"

    @classmethod
    @abstractmethod
    def get_column(cls) -> str:
        """
        Get the column where the plugin's widget should appear.

        Returns one of the Column constants indicating the column
        position in the folder configuration UI.

        Returns:
            str: Column identifier (LEFT, RIGHT, or CENTER)
        """
        pass

    @classmethod
    @abstractmethod
    def get_section(cls) -> str:
        """
        Get the section name where the plugin's widget should appear.

        Sections are logical groupings within a column. Plugins with
        the same section name will be grouped together.

        Returns:
            str: Section name for widget grouping
        """
        pass

    @classmethod
    @abstractmethod
    def get_section_order(cls) -> int:
        """
        Get the display order of the section within the column.

        Lower values appear first.

        Returns:
            int: Section display order
        """
        pass

    @classmethod
    @abstractmethod
    def get_widget_order(cls) -> int:
        """
        Get the display order of the widget within its section.

        Lower values appear first.

        Returns:
            int: Widget display order within section
        """
        pass

    @abstractmethod
    def extract_data(self, folder_path: str) -> Dict[str, Any]:
        """
        Extract configuration data from a folder.

        This method is called when the folder is first selected or
        when configuration data needs to be re-extracted.

        Args:
            folder_path: Path to the folder being configured

        Returns:
            Dict[str, Any]: Extracted configuration data
        """
        pass

    @abstractmethod
    def populate_widget(self, data: Dict[str, Any]) -> None:
        """
        Populate the plugin's widget with configuration data.

        This method is called to update the widget with existing
        configuration data.

        Args:
            data: Configuration data to populate the widget with
        """
        pass

    @abstractmethod
    def get_widget_data(self) -> Dict[str, Any]:
        """
        Get the current configuration data from the widget.

        This method is called to retrieve the current state of the
        widget when saving configuration.

        Returns:
            Dict[str, Any]: Current widget configuration data
        """
        pass

    def validate_folder_configuration(self, folder_path: str, config: Dict[str, Any]) -> ValidationResult:
        """
        Validate the plugin's configuration for a specific folder.

        This method can be overridden to provide folder-specific
        validation logic.

        Args:
            folder_path: Path to the folder being configured
            config: Configuration to validate

        Returns:
            ValidationResult: Validation result
        """
        return self.validate_configuration(config)

    @classmethod
    def is_folder_config_plugin(cls) -> bool:
        """
        Check if this plugin is a folder configuration plugin.

        Returns:
            bool: True (always true for FolderConfigPlugin instances)
        """
        return True

    @classmethod
    def get_placement_info(cls) -> Dict[str, Any]:
        """
        Get complete placement information for the plugin's widget.

        Returns:
            Dict[str, Any]: Placement information including column, section,
                and order details
        """
        return {
            "column": cls.get_column(),
            "section": cls.get_section(),
            "section_order": cls.get_section_order(),
            "widget_order": cls.get_widget_order()
        }
