"""
Base Plugin Interface

Defines the core plugin interface that all plugins must implement.
This includes lifecycle methods, configuration schema definition,
validation, and UI widget creation.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

from .config_schemas import ConfigurationSchema
from .validation_framework import ValidationResult


class PluginBase(ABC):
    """
    Base interface for all plugins.

    This abstract base class defines the standard methods that all
    plugins must implement to integrate with the system.
    """

    @classmethod
    @abstractmethod
    def get_name(cls) -> str:
        """
        Get the human-readable name of the plugin.

        Returns:
            str: Plugin name for display purposes
        """
        pass

    @classmethod
    @abstractmethod
    def get_identifier(cls) -> str:
        """
        Get the unique identifier for the plugin.

        This should be a unique string that identifies the plugin
        across all versions and installations.

        Returns:
            str: Unique plugin identifier
        """
        pass

    @classmethod
    @abstractmethod
    def get_description(cls) -> str:
        """
        Get a detailed description of the plugin's functionality.

        Returns:
            str: Plugin description
        """
        pass

    @classmethod
    @abstractmethod
    def get_version(cls) -> str:
        """
        Get the plugin version.

        Returns:
            str: Plugin version string
        """
        pass

    @classmethod
    def get_configuration_schema(cls) -> Optional[ConfigurationSchema]:
        """
        Get the configuration schema for the plugin.

        Returns a schema that defines the configuration fields
        required by the plugin. Defaults to None if no configuration
        is needed.

        Returns:
            Optional[ConfigurationSchema]: Configuration schema or None
        """
        return None

    @abstractmethod
    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize the plugin with configuration.

        Called when the plugin is first loaded.

        Args:
            config: Optional configuration dictionary
        """
        pass

    @abstractmethod
    def activate(self) -> None:
        """
        Activate the plugin.

        Called when the plugin is activated for use.
        """
        pass

    @abstractmethod
    def deactivate(self) -> None:
        """
        Deactivate the plugin.

        Called when the plugin is deactivated or the application shuts down.
        """
        pass

    def validate_configuration(self, config: Dict[str, Any]) -> ValidationResult:
        """
        Validate configuration against the plugin's schema.

        Args:
            config: Configuration to validate

        Returns:
            ValidationResult: Validation result
        """
        schema = self.get_configuration_schema()
        if schema is not None:
            return schema.validate(config)
        return ValidationResult(success=True, errors=[])

    def get_default_configuration(self) -> Dict[str, Any]:
        """
        Get the default configuration values for the plugin.

        Returns:
            Dict[str, Any]: Default configuration values
        """
        schema = self.get_configuration_schema()
        if schema is not None:
            return schema.get_defaults()
        return {}

    @abstractmethod
    def create_widget(self, parent: Any = None) -> Any:
        """
        Create a UI widget for configuring the plugin.

        The returned widget should be compatible with the current UI framework
        (either Qt or Tkinter).

        Args:
            parent: Optional parent widget

        Returns:
            Any: UI widget for plugin configuration
        """
        pass

    def update_configuration(self, config: Dict[str, Any]) -> ValidationResult:
        """
        Update the plugin's configuration.

        Args:
            config: New configuration values

        Returns:
            ValidationResult: Validation result of the new configuration
        """
        validation = self.validate_configuration(config)
        if validation.success:
            self.initialize(config)
        return validation

    @classmethod
    def is_compatible(cls) -> bool:
        """
        Check if the plugin is compatible with the current system.

        Defaults to True. Plugins can override this method to check
        for specific dependencies or system requirements.

        Returns:
            bool: True if compatible, False otherwise
        """
        return True

    @classmethod
    def get_dependencies(cls) -> List[str]:
        """
        Get the list of plugin dependencies.

        Returns a list of plugin identifiers that this plugin depends on.
        Defaults to empty list.

        Returns:
            List[str]: List of dependency plugin identifiers
        """
        return []
