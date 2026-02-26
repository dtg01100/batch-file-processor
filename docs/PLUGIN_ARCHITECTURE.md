# Plugin Architecture Documentation

## Overview

The batch file processor uses a modular plugin architecture to support multiple configuration formats for EDI conversion. The system is designed around several key components that work together to provide a flexible, extensible configuration system for the Edit Folders Dialog.

## Architecture Components

```
┌─────────────────────────────────────────────────────────────────┐
│                     Edit Folders Dialog                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │ Form Generator  │  │ Section Registry │  │ Plugin Manager │ │
│  └────────┬────────┘  └────────┬─────────┘  └───────┬────────┘ │
│           │                     │                     │          │
│           └─────────────────────┼─────────────────────┘          │
│                                 │                                │
│                    ┌────────────▼────────────┐                   │
│                    │  ConfigurationPlugin   │                   │
│                    │  (Interface)            │                   │
│                    └────────────┬────────────┘                   │
│                                 │                                │
│           ┌─────────────────────┼─────────────────────┐          │
│           │                     │                     │          │
│  ┌────────▼────────┐  ┌────────▼────────┐  ┌────────▼────────┐ │
│  │ CSV Plugin      │  │ Estore Plugin   │  │ Custom Plugins  │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### PluginBase

The foundation interface for all plugins. All plugins must implement:

- `get_name()` - Human-readable plugin name
- `get_identifier()` - Unique plugin identifier
- `get_description()` - Plugin functionality description
- `get_version()` - Plugin version string
- `initialize(config)` - Initialize with optional configuration
- `activate()` - Activate the plugin for use
- `deactivate()` - Deactivate the plugin
- `create_widget(parent)` - Create UI widget for configuration

### ConfigurationPlugin

Extends `PluginBase` with format-specific configuration capabilities:

- `get_format_name()` - Human-readable format name
- `get_format_enum()` - ConvertFormat enum value
- `get_config_fields()` - List of FieldDefinition objects
- `validate_config(config)` - Validate configuration data
- `create_config(data)` - Create configuration instance from data
- `serialize_config(config)` - Serialize configuration to dictionary
- `deserialize_config(data)` - Deserialize data to configuration instance

### PluginManager

Manages plugin discovery and lifecycle:

- `discover_plugins()` - Find all available plugins
- `initialize_plugins(config)` - Initialize all plugins
- `get_configuration_plugin_by_format(format)` - Get plugin for specific format
- `create_configuration_widget(format, parent)` - Create UI widget
- `validate_configuration(format, config)` - Validate configuration
- `serialize_configuration(format, config)` - Serialize configuration
- `deserialize_configuration(format, data)` - Deserialize configuration

### SectionRegistry

Manages configuration UI sections:

- `register_section(section_class)` - Register a configuration section
- `get_section(section_id)` - Get section by ID
- `get_all_sections()` - Get all sections sorted by priority
- `register_plugin_section(plugin_id, section_class)` - Register plugin section
- `get_sections_by_plugin(plugin_id)` - Get sections for specific plugin
- `register_renderer(section_id, factory)` - Register section renderer

### FormGenerator

Dynamically generates forms from ConfigurationSchema:

- `build_form(config, parent)` - Build form from schema
- `get_values()` - Get current form values
- `set_values(config)` - Set form values
- `validate()` - Validate entire form
- `add_plugin_section(section_id, schema, config)` - Add plugin section
- `get_plugin_section_values()` - Get values from plugin sections
- `set_plugin_section_values(configs)` - Set values for plugin sections

### ConfigurationSchema & FieldDefinition

Define configuration structure:

**FieldDefinition** represents a single configuration field:
- `name` - Field identifier
- `field_type` - Type (STRING, INTEGER, BOOLEAN, LIST, DICT, SELECT, etc.)
- `label` - Human-readable label
- `description` - Field description
- `default` - Default value
- `required` - Whether field is required
- `validators` - Custom validation functions
- `choices` - Available choices for SELECT fields
- `min_value`, `max_value` - Numeric constraints
- `min_length`, `max_length` - String length constraints

**ConfigurationSchema** contains:
- `fields` - List of FieldDefinition objects
- `validate(config)` - Validate configuration against schema
- `get_defaults()` - Get default values
- `get_required_fields()` - Get list of required fields

## Integration with Edit Folders Dialog

The plugin system integrates with the Edit Folders Dialog through:

1. **Format Selection** - User selects conversion format
2. **Plugin Discovery** - PluginManager finds appropriate plugin
3. **Widget Creation** - Plugin creates configuration widget
4. **Form Generation** - FormGenerator incorporates plugin sections
5. **Validation** - Configuration validated through plugin
6. **Serialization** - Configuration serialized for storage

## State Management

Plugin sections maintain state through:

- **Plugin-level state** - Stored in plugin instance via `initialize()`
- **Form-level state** - Managed by FormGenerator
- **Section-level state** - Managed by SectionRenderer

Values flow:
1. Plugin provides schema via `get_config_fields()`
2. FormGenerator builds UI from schema
3. User interacts with form
4. Values retrieved via `get_values()` or `get_plugin_section_values()`
5. Plugin validates via `validate_config()`
6. Plugin serializes via `serialize_config()` for storage
