"""
Plugin Interfaces

Defines focused interfaces following the Interface Segregation Principle.
These interfaces allow plugins to implement only the functionality they need.
"""

from abc import ABC
from typing import Any

from .config_schemas import ConfigurationSchema
from .validation_framework import ValidationResult


class IPlugin(ABC):
    """Core plugin interface - lifecycle and identification."""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        for method in ("get_name", "get_identifier", "get_description", "get_version"):
            if getattr(cls, method, None) is getattr(IPlugin, method, None):
                raise TypeError(
                    f"Class {cls.__name__} must implement {method}() class method"
                )
        if cls.initialize is IPlugin.initialize:
            raise TypeError(f"Class {cls.__name__} must implement initialize()")

    @classmethod
    def get_name(cls) -> str:
        """Get the human-readable name of the plugin."""
        raise NotImplementedError

    @classmethod
    def get_identifier(cls) -> str:
        """Get the unique identifier for the plugin."""
        raise NotImplementedError

    @classmethod
    def get_description(cls) -> str:
        """Get a detailed description of the plugin's functionality."""
        raise NotImplementedError

    @classmethod
    def get_version(cls) -> str:
        """Get the plugin version."""
        raise NotImplementedError

    def initialize(self, config: dict[str, Any] | None = None) -> None:
        """Initialize the plugin with configuration."""
        raise NotImplementedError

    def activate(self) -> None:
        """Activate the plugin."""
        raise NotImplementedError

    def deactivate(self) -> None:
        """Deactivate the plugin."""
        raise NotImplementedError


class IConfigurablePlugin(ABC):
    """Plugin interface for configuration management."""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if (
            cls.get_configuration_schema
            is IConfigurablePlugin.get_configuration_schema
        ):
            raise TypeError(
                f"Class {cls.__name__} must implement get_configuration_schema()"
            )

    @classmethod
    def get_configuration_schema(cls) -> ConfigurationSchema | None:
        """Get the configuration schema for the plugin."""
        raise NotImplementedError

    def validate_configuration(self, config: dict[str, Any]) -> ValidationResult:
        """Validate configuration against the plugin's schema."""
        raise NotImplementedError

    def update_configuration(self, config: dict[str, Any]) -> ValidationResult:
        """Update the plugin's configuration."""
        raise NotImplementedError


class IUIPlugin(ABC):
    """Plugin interface for UI widget creation."""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.create_widget is IUIPlugin.create_widget:
            raise TypeError(f"Class {cls.__name__} must implement create_widget()")

    def create_widget(self, parent: Any = None) -> Any:
        """Create a UI widget for configuring the plugin."""
        raise NotImplementedError


class IPluginCompatibility(ABC):
    """Plugin interface for compatibility checking."""

    @classmethod
    def is_compatible(cls) -> bool:
        """Check if the plugin is compatible with the current system."""
        return True

    @classmethod
    def get_dependencies(cls) -> list[str]:
        """Get the list of plugin dependencies."""
        return []