"""Plugin configuration system.

This module defines the configuration schema for plugins (convert and send).
Each plugin can declare its configuration fields using a declarative class attribute.

Example:
    class MyConverter(BaseConverter):
        PLUGIN_ID = "csv"
        PLUGIN_NAME = "CSV Format"
        PLUGIN_DESCRIPTION = "Standard CSV output format"

        CONFIG_FIELDS = [
            {
                'key': 'include_headers',
                'label': 'Include Headers',
                'type': 'boolean',
                'default': False,
                'help': 'Include column headers in the CSV output'
            },
            {
                'key': 'division_id',
                'label': 'Division ID',
                'type': 'string',
                'default': '',
                'required': True,
                'help': 'The division identifier'
            }
        ]
"""

from typing import Any, Dict, List, Literal, Optional, Union
from dataclasses import dataclass, field


@dataclass
class ConfigField:
    """Represents a single configuration field for a plugin.

    Attributes:
        key: Unique identifier for this field (used in parameters_dict).
        label: Human-readable label for the UI.
        type: Field type (boolean, string, integer, select, etc.).
        default: Default value for the field.
        required: Whether this field is required.
        help: Help text/tooltip for the user.
        options: List of options for select/radio fields.
        min_value: Minimum value for numeric fields.
        max_value: Maximum value for numeric fields.
        placeholder: Placeholder text for text fields.
        validator: Optional validation regex or callable.
        visible_if: Conditional visibility (dict with field: value pairs).
    """

    key: str
    label: str
    type: Literal[
        "boolean", "string", "integer", "float", "select", "multiselect", "text"
    ]
    default: Any
    required: bool = False
    help: str = ""
    options: List[Union[str, tuple]] = field(default_factory=list)
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    placeholder: str = ""
    validator: Optional[str] = None
    visible_if: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate field configuration."""
        if self.type == "select" and not self.options:
            raise ValueError(f"Field '{self.key}' of type 'select' must have options")

        if self.type == "boolean" and not isinstance(self.default, bool):
            raise ValueError(
                f"Field '{self.key}' of type 'boolean' must have boolean default"
            )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConfigField":
        """Create ConfigField from dictionary."""
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert ConfigField to dictionary."""
        return {
            "key": self.key,
            "label": self.label,
            "type": self.type,
            "default": self.default,
            "required": self.required,
            "help": self.help,
            "options": self.options,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "placeholder": self.placeholder,
            "validator": self.validator,
            "visible_if": self.visible_if,
        }


class PluginConfigMixin:
    """Mixin class for plugins with declarative configuration.

    Plugins should define:
        PLUGIN_ID: Unique identifier (used in database/file system)
        PLUGIN_NAME: Display name shown in UI
        PLUGIN_DESCRIPTION: Brief description of what the plugin does
        CONFIG_FIELDS: List of ConfigField definitions or dicts
    """

    PLUGIN_ID: Optional[str] = None
    PLUGIN_NAME: Optional[str] = None
    PLUGIN_DESCRIPTION: str = ""
    CONFIG_FIELDS: List[Union[ConfigField, Dict[str, Any]]] = []

    @classmethod
    def get_config_fields(cls) -> List[ConfigField]:
        """Get parsed configuration fields for this plugin.

        Returns:
            List of ConfigField objects.
        """
        fields = []
        for field_def in cls.CONFIG_FIELDS:
            if isinstance(field_def, dict):
                fields.append(ConfigField.from_dict(field_def))
            elif isinstance(field_def, ConfigField):
                fields.append(field_def)
            else:
                raise TypeError(f"Invalid field definition: {field_def}")
        return fields

    @classmethod
    def get_default_config(cls) -> Dict[str, Any]:
        """Get default configuration values for this plugin.

        Returns:
            Dictionary of default values keyed by field key.
        """
        return {field.key: field.default for field in cls.get_config_fields()}

    @classmethod
    def validate_config(cls, config: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate configuration values.

        Args:
            config: Configuration dictionary to validate.

        Returns:
            Tuple of (is_valid, error_messages).
        """
        errors = []
        fields = cls.get_config_fields()

        for field in fields:
            value = config.get(field.key)

            # Check required fields
            if field.required and (value is None or value == ""):
                errors.append(f"{field.label} is required")
                continue

            # Skip further validation if field is empty and not required
            if value is None or value == "":
                continue

            # Type validation
            if field.type == "boolean" and not isinstance(value, bool):
                errors.append(f"{field.label} must be a boolean")
            elif field.type == "integer":
                if not isinstance(value, int):
                    try:
                        value = int(value)
                    except (ValueError, TypeError):
                        errors.append(f"{field.label} must be an integer")
                        continue

                if field.min_value is not None and value < field.min_value:
                    errors.append(f"{field.label} must be at least {field.min_value}")
                if field.max_value is not None and value > field.max_value:
                    errors.append(f"{field.label} must be at most {field.max_value}")

            elif field.type == "float":
                if not isinstance(value, (int, float)):
                    try:
                        value = float(value)
                    except (ValueError, TypeError):
                        errors.append(f"{field.label} must be a number")
                        continue

                if field.min_value is not None and value < field.min_value:
                    errors.append(f"{field.label} must be at least {field.min_value}")
                if field.max_value is not None and value > field.max_value:
                    errors.append(f"{field.label} must be at most {field.max_value}")

            elif field.type == "select":
                valid_options = [
                    opt if isinstance(opt, str) else opt[0] for opt in field.options
                ]
                if value not in valid_options:
                    errors.append(f"{field.label} has invalid value")

        return len(errors) == 0, errors

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value from parameters_dict.

        Args:
            key: Configuration key.
            default: Default value if key not found.

        Returns:
            Configuration value.
        """
        if hasattr(self, "parameters_dict"):
            params = getattr(self, "parameters_dict")
            if isinstance(params, dict):
                return params.get(key, default)
        return default


class PluginRegistry:
    """Registry for discovering and managing plugins."""

    _convert_plugins: Dict[str, type] = {}
    _send_plugins: Dict[str, type] = {}

    @classmethod
    def register_convert_plugin(cls, plugin_class: type) -> None:
        """Register a convert plugin.

        Args:
            plugin_class: Plugin class with PLUGIN_ID attribute.
        """
        if not hasattr(plugin_class, "PLUGIN_ID") or not plugin_class.PLUGIN_ID:
            raise ValueError(f"Plugin {plugin_class.__name__} must define PLUGIN_ID")

        cls._convert_plugins[plugin_class.PLUGIN_ID] = plugin_class

    @classmethod
    def register_send_plugin(cls, plugin_class: type) -> None:
        """Register a send plugin.

        Args:
            plugin_class: Plugin class with PLUGIN_ID attribute.
        """
        if not hasattr(plugin_class, "PLUGIN_ID") or not plugin_class.PLUGIN_ID:
            raise ValueError(f"Plugin {plugin_class.__name__} must define PLUGIN_ID")

        cls._send_plugins[plugin_class.PLUGIN_ID] = plugin_class

    @classmethod
    def get_convert_plugin(cls, plugin_id: str) -> Optional[type]:
        """Get a convert plugin by ID.

        Args:
            plugin_id: Plugin identifier.

        Returns:
            Plugin class or None.
        """
        return cls._convert_plugins.get(plugin_id)

    @classmethod
    def get_send_plugin(cls, plugin_id: str) -> Optional[type]:
        """Get a send plugin by ID.

        Args:
            plugin_id: Plugin identifier.

        Returns:
            Plugin class or None.
        """
        return cls._send_plugins.get(plugin_id)

    @classmethod
    def list_convert_plugins(cls) -> List[tuple[str, str, str]]:
        """List all registered convert plugins.

        Returns:
            List of (plugin_id, plugin_name, description) tuples.
        """
        return [
            (plugin_id, plugin_class.PLUGIN_NAME, plugin_class.PLUGIN_DESCRIPTION)
            for plugin_id, plugin_class in sorted(cls._convert_plugins.items())
        ]

    @classmethod
    def list_send_plugins(cls) -> List[tuple[str, str, str]]:
        """List all registered send plugins.

        Returns:
            List of (plugin_id, plugin_name, description) tuples.
        """
        return [
            (plugin_id, plugin_class.PLUGIN_NAME, plugin_class.PLUGIN_DESCRIPTION)
            for plugin_id, plugin_class in sorted(cls._send_plugins.items())
        ]

    @classmethod
    def discover_plugins(cls) -> None:
        """Discover and register all available plugins.

        This method scans for convert_to_* and *_backend modules
        and registers their plugin classes.
        """
        import importlib
        import glob
        import os

        # Discover convert plugins
        for filepath in glob.glob("convert_to_*.py"):
            module_name = os.path.splitext(os.path.basename(filepath))[0]
            try:
                module = importlib.import_module(module_name)
                # Look for classes that inherit from BaseConverter
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and hasattr(attr, "PLUGIN_ID")
                        and attr.PLUGIN_ID is not None
                        and hasattr(attr, "convert")
                    ):  # Has convert method
                        cls.register_convert_plugin(attr)
            except Exception as e:
                print(f"Failed to load convert plugin {module_name}: {e}")

        # Discover send plugins
        for filepath in glob.glob("*_backend.py"):
            if filepath == "send_base.py":
                continue
            module_name = os.path.splitext(os.path.basename(filepath))[0]
            try:
                module = importlib.import_module(module_name)
                # Look for classes that inherit from BaseSendBackend
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and hasattr(attr, "PLUGIN_ID")
                        and attr.PLUGIN_ID is not None
                        and hasattr(attr, "send")
                    ):  # Has send method
                        cls.register_send_plugin(attr)
            except Exception as e:
                print(f"Failed to load send plugin {module_name}: {e}")


def get_plugin_config(
    plugin_type: Literal["convert", "send"], plugin_id: str
) -> Optional[List[ConfigField]]:
    """Get configuration fields for a plugin.

    Args:
        plugin_type: Type of plugin ('convert' or 'send').
        plugin_id: Plugin identifier.

    Returns:
        List of ConfigField objects or None if plugin not found.
    """
    if plugin_type == "convert":
        plugin_class = PluginRegistry.get_convert_plugin(plugin_id)
    elif plugin_type == "send":
        plugin_class = PluginRegistry.get_send_plugin(plugin_id)
    else:
        return None

    if plugin_class is None:
        return None

    return plugin_class.get_config_fields()
