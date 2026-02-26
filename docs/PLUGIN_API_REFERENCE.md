# Plugin API Reference

This document provides detailed API documentation for the plugin system components.

## PluginBase

**Location:** `interface/plugins/plugin_base.py`

Base interface for all plugins.

### Class Methods

#### `get_name() -> str`
Human-readable name of the plugin.

#### `get_identifier() -> str`
Unique identifier for the plugin (used for registration and lookup).

#### `get_description() -> str`
Detailed description of the plugin's functionality.

#### `get_version() -> str`
Plugin version string.

#### `get_configuration_schema() -> Optional[ConfigurationSchema]`
Returns the configuration schema for the plugin. Defaults to None.

#### `is_compatible() -> bool`
Check if the plugin is compatible with the current system. Defaults to True.

#### `get_dependencies() -> List[str]`
Returns list of plugin identifiers this plugin depends on. Defaults to [].

### Instance Methods

#### `initialize(config: Optional[Dict[str, Any]] = None) -> None`
Initialize the plugin with optional configuration. Called when plugin is loaded.

#### `activate() -> None`
Activate the plugin for use.

#### `deactivate() -> None`
Deactivate the plugin (called on shutdown).

#### `create_widget(parent: Any = None) -> Any`
Create a UI widget for configuring the plugin. Returns framework-specific widget.

#### `validate_configuration(config: Dict[str, Any]) -> ValidationResult`
Validate configuration against the plugin's schema.

#### `get_default_configuration() -> Dict[str, Any]`
Get default configuration values.

#### `update_configuration(config: Dict[str, Any]) -> ValidationResult`
Update plugin configuration and reinitialize if valid.

---

## ConfigurationPlugin

**Location:** `interface/plugins/configuration_plugin.py`

Extends PluginBase with format-specific configuration capabilities.

### Class Methods

#### `get_format_name() -> str`
Human-readable name of the configuration format.

#### `get_format_enum() -> ConvertFormat`
The ConvertFormat enum value associated with this format.

#### `get_config_fields() -> List[FieldDefinition]`
List of field definitions for this configuration format.

#### `get_configuration_schema() -> Optional[ConfigurationSchema]`
Returns ConfigurationSchema built from get_config_fields().

### Instance Methods

#### `validate_config(config: Dict[str, Any]) -> ValidationResult`
Validate configuration data against the format's schema.

#### `create_config(data: Dict[str, Any]) -> Any`
Create a configuration instance from raw data.

#### `serialize_config(config: Any) -> Dict[str, Any]`
Serialize a configuration instance to dictionary format.

#### `deserialize_config(data: Dict[str, Any]) -> Any`
Deserialize stored data into a configuration instance.

---

## PluginManager

**Location:** `interface/plugins/plugin_manager.py`

Dynamic plugin discovery and management system.

### Constructor

#### `__init__(plugin_directories: Optional[List[str]] = None)`
Initialize the plugin manager. Optionally specify plugin directories.

### Methods

#### `add_plugin_directory(directory: str) -> None`
Add a directory to the plugin search path.

#### `discover_plugins() -> List[str]`
Discover all available plugins in configured directories. Returns list of plugin identifiers.

#### `initialize_plugins(config: Optional[Dict[str, Dict[str, Any]]] = None) -> List[str]`
Initialize all discovered plugins. Returns list of initialized plugin identifiers.

#### `get_configuration_plugins() -> List[ConfigurationPlugin]`
Get all available configuration plugin instances.

#### `get_configuration_plugin_by_format(format_enum: ConvertFormat) -> Optional[ConfigurationPlugin]`
Get configuration plugin by format enum.

#### `get_configuration_plugin_by_format_name(format_name: str) -> Optional[ConfigurationPlugin]`
Get configuration plugin by format name (case-insensitive).

#### `create_configuration_widget(format_enum: ConvertFormat, parent: Any = None) -> Any`
Create a configuration widget for a specific format.

#### `validate_configuration(format_enum: ConvertFormat, config: Dict[str, Any]) -> ValidationResult`
Validate configuration data for a specific format.

#### `create_configuration(format_enum: ConvertFormat, data: Dict[str, Any]) -> Any`
Create a configuration instance for a specific format.

#### `serialize_configuration(format_enum: ConvertFormat, config: Any) -> Dict[str, Any]`
Serialize a configuration instance.

#### `deserialize_configuration(format_enum: ConvertFormat, data: Dict[str, Any]) -> Any`
Deserialize configuration data.

#### `get_configuration_fields(format_enum: ConvertFormat) -> List[FieldDefinition]`
Get configuration field definitions for a specific format.

---

## SectionRegistry

**Location:** `interface/plugins/section_registry.py`

Registry for managing configuration UI sections.

### Class Methods

#### `register_section(section_class: Type[ConfigSectionBase]) -> None`
Register a configuration section.

#### `unregister_section(section_id: str) -> None`
Unregister a configuration section.

#### `get_section(section_id: str) -> Optional[Type[ConfigSectionBase]]`
Get a registered section by ID.

#### `get_all_sections() -> List[Type[ConfigSectionBase]]`
Get all registered sections sorted by priority.

#### `get_sections_by_plugin(plugin_id: str) -> List[Type[ConfigSectionBase]]`
Get all sections registered by a specific plugin.

#### `register_plugin_section(plugin_id: str, section_class: Type[ConfigSectionBase]) -> None`
Register a section as belonging to a specific plugin.

#### `register_renderer(section_id: str, renderer_factory: Callable) -> None`
Register a renderer factory for a section.

#### `get_renderer(section_id: str) -> Optional[Callable]`
Get the renderer factory for a section.

#### `clear() -> None`
Clear all registered sections and renderers.

#### `get_section_count() -> int`
Get total number of registered sections.

---

## ConfigSectionBase

**Location:** `interface/plugins/section_registry.py`

Base class for all configuration sections.

### Class Methods

#### `get_section_id() -> str`
Unique identifier for this section.

#### `get_section_title() -> str`
Human-readable title for display.

#### `get_section_description() -> str`
Description of this section.

#### `get_schema() -> ConfigurationSchema`
Configuration schema for this section.

#### `get_priority() -> int`
Display priority (lower = appears first, default: 100).

#### `is_expanded_by_default() -> bool`
Whether section should be expanded by default (default: True).

---

## SectionRenderer

**Location:** `interface/plugins/section_registry.py`

Abstract base class for rendering configuration sections.

### Methods

#### `render(parent: Any, config: Optional[Dict[str, Any]] = None) -> Any`
Render the section in the parent widget.

#### `get_values() -> Dict[str, Any]`
Get current configuration values from the rendered section.

#### `set_values(config: Dict[str, Any]) -> None`
Set configuration values in the rendered section.

#### `validate() -> bool`
Validate current configuration values.

#### `get_validation_errors() -> List[str]`
Get validation errors from the section.

---

## FormGenerator

**Location:** `interface/form/form_generator.py`

Base interface for form generators.

### Constructor

#### `__init__(schema: ConfigurationSchema, framework: str = 'qt')`
Initialize the form generator with schema and UI framework.

### Methods

#### `build_form(config: dict = None, parent: Any = None) -> Any`
Build the complete form from the schema.

#### `get_values() -> Dict[str, Any]`
Get current values from all form fields.

#### `set_values(config: Dict[str, Any]) -> None`
Set values for all form fields.

#### `validate() -> ValidationResult`
Validate the entire form.

#### `get_validation_errors() -> List[str]`
Get all validation errors from the form.

#### `set_field_visibility(field_name: str, visible: bool) -> None`
Set visibility of a specific field.

#### `set_field_enabled(field_name: str, enabled: bool) -> None`
Set enabled state of a specific field.

#### `get_field_value(field_name: str) -> Any`
Get current value of a specific field.

#### `set_field_value(field_name: str, value: Any) -> None`
Set value of a specific field.

#### `register_field_dependency(dependent_field: str, trigger_field: str, condition: Optional[callable] = None)`
Register a field dependency for dynamic visibility.

#### `add_plugin_section(section_id: str, schema: ConfigurationSchema, config: Optional[Dict[str, Any]] = None) -> None`
Add a plugin configuration section to the form.

#### `add_plugin_sections(sections: List[Dict[str, Any]]) -> None`
Add multiple plugin configuration sections.

#### `get_plugin_section_values() -> Dict[str, Dict[str, Any]]`
Get configuration values from all plugin sections.

#### `set_plugin_section_values(configs: Dict[str, Dict[str, Any]]) -> None`
Set configuration values for plugin sections.

#### `validate_plugin_sections() -> ValidationResult`
Validate all plugin sections.

---

## FieldDefinition

**Location:** `interface/plugins/config_schemas.py`

Definition of a single configuration field.

### Constructor Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | str | Field name (key in config dictionary) |
| `field_type` | FieldType | Type of the field |
| `label` | str | Human-readable label |
| `description` | str | Detailed description |
| `default` | Any | Default value |
| `required` | bool | Whether field is required |
| `validators` | List[Validator] | Custom validators |
| `choices` | List[Dict] | Available choices (SELECT/MULTI_SELECT) |
| `min_value` | Union[int, float] | Minimum value (numeric) |
| `max_value` | Union[int, float] | Maximum value (numeric) |
| `min_length` | int | Minimum length (string) |
| `max_length` | int | Maximum length (string) |

### Methods

#### `validate(value: Any) -> ValidationResult`
Validate a value against this field definition.

---

## ConfigurationSchema

**Location:** `interface/plugins/config_schemas.py`

Represents a complete configuration schema.

### Constructor

#### `__init__(fields: List[FieldDefinition])`
Initialize with list of field definitions.

### Methods

#### `get_field(name: str) -> Optional[FieldDefinition]`
Get a field definition by name.

#### `validate(config: Dict[str, Any]) -> ValidationResult`
Validate a configuration dictionary against this schema.

#### `get_defaults() -> Dict[str, Any]`
Get default configuration values.

#### `get_required_fields() -> List[str]`
Get list of required field names.

#### `get_field_types() -> Dict[str, FieldType]`
Get dictionary mapping field names to types.

#### `to_dict() -> Dict[str, Any]`
Convert schema to dictionary representation.

---

## FieldType Enum

**Location:** `interface/plugins/config_schemas.py`

Supported configuration field types.

| Value | Description |
|-------|-------------|
| `STRING` | Text input |
| `INTEGER` | Whole number |
| `FLOAT` | Decimal number |
| `BOOLEAN` | Checkbox |
| `LIST` | List input |
| `DICT` | Dictionary input |
| `SELECT` | Dropdown selection |
| `MULTI_SELECT` | Multiple selection |

---

## ValidationResult

**Location:** `interface/plugins/validation_framework.py`

Result of a validation operation.

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `success` | bool | Whether validation passed |
| `errors` | List[str] | List of error messages |

---

## FormGeneratorFactory

**Location:** `interface/form/form_generator.py`

Factory for creating form generator instances.

### Methods

#### `create_form_generator(schema: ConfigurationSchema, framework: str = 'qt') -> FormGenerator`
Create a form generator instance for the specified framework.

**Raises:** `ValueError` if framework is not supported.
