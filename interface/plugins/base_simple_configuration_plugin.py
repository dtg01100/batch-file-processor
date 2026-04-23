"""
Base Simple Configuration Plugin

Provides a base class for configuration plugins with minimal boilerplate.
Subclasses only need to implement get_name(), get_identifier(), get_format_name(),
and get_format_enum().
"""

from abc import abstractmethod
from typing import Any

from ..models.folder_configuration import ConvertFormat
from .config_schemas import FieldDefinition
from .configuration_plugin import ConfigurationPlugin
from .ui_abstraction import ConfigurationWidgetBuilder
from .validation_framework import ValidationResult


class BaseSimpleConfigurationPlugin(ConfigurationPlugin):
    """
    Base class for simple configuration plugins with minimal boilerplate.

    Subclasses must implement:
        - get_name(): Human-readable plugin name
        - get_identifier(): Unique plugin identifier
        - get_format_name(): Human-readable format name
        - get_format_enum(): ConvertFormat enum value

    Subclasses may optionally override:
        - get_description(): Plugin description (defaults to
      "{name} format configuration options for EDI conversion")
        - get_version(): Plugin version (defaults to "1.0.0")
        - get_config_fields(): Configuration fields (defaults to empty list)
        - create_config(): Create config instance (defaults to simple dict-like class)
    """

    @classmethod
    @abstractmethod
    def get_name(cls) -> str:
        """Get the human-readable name of the plugin."""

    @classmethod
    @abstractmethod
    def get_identifier(cls) -> str:
        """Get the unique identifier for the plugin."""

    @classmethod
    @abstractmethod
    def get_format_name(cls) -> str:
        """Get the human-readable name of the configuration format."""

    @classmethod
    @abstractmethod
    def get_format_enum(cls) -> ConvertFormat:
        """Get the ConvertFormat enum value associated with this format."""

    @classmethod
    def get_description(cls) -> str:
        """Get a detailed description of the plugin's functionality."""
        return (
            f"Provides {cls.get_format_name()}"
            f" format configuration options for EDI conversion"
        )

    @classmethod
    def get_version(cls) -> str:
        """Get the plugin version."""
        return "1.0.0"

    @classmethod
    def get_config_fields(cls) -> list[FieldDefinition]:
        """Get the list of field definitions for this configuration format."""
        return []

    def validate_config(self, config: dict[str, Any]) -> ValidationResult:
        """Validate configuration data against the format's schema."""
        schema = self.get_configuration_schema()
        if schema:
            return schema.validate(config)
        return ValidationResult(success=True, errors=[])

    def create_config(self, data: dict[str, Any]) -> Any:
        """Create a configuration instance from raw data."""
        return type("SimpleConfig", (), {"__init__": lambda self: None})()

    def serialize_config(self, config: Any) -> dict[str, Any]:
        """Serialize a configuration instance to dictionary format."""
        if hasattr(config, "__dict__"):
            return config.__dict__.copy()
        return {}

    def deserialize_config(self, data: dict[str, Any]) -> Any:
        """Deserialize stored data into a configuration instance."""
        return self.create_config(data)

    def initialize(self, config: dict[str, Any] | None = None) -> None:
        """Initialize the plugin with configuration."""
        if config:
            self._config = self.create_config(config)
        else:
            self._config = self.create_config({})

    def activate(self) -> None:
        """Activate the plugin."""

    def deactivate(self) -> None:
        """Deactivate the plugin."""

    def create_widget(self, parent: Any = None) -> Any:
        """Create a UI widget for configuring the plugin."""
        schema = self.get_configuration_schema()
        if schema:
            builder = ConfigurationWidgetBuilder()
            return builder.build_configuration_panel(
                schema,
                self._config.__dict__ if hasattr(self, "_config") else {},
                parent,
            )
        return None
