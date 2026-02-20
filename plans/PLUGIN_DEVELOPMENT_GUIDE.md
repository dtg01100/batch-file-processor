# Plugin Development Guide

## Overview

The Batch File Processor plugin system provides a flexible architecture for extending and customizing the application's functionality. Plugins allow developers to add support for new file formats, data validation rules, UI widgets, and integration points without modifying the core application code.

## Plugin System Architecture

The plugin system follows a layered architecture with the following components:

### Core Plugin Interfaces

1. **PluginBase**: The base abstract class that all plugins must implement. It defines the core lifecycle methods, configuration schema, and UI widget creation interface.

2. **ConfigurationPlugin**: Extends PluginBase to provide format-specific configuration handling. This interface adds support for schema definition, validation, serialization, and deserialization of configuration data.

3. **PluginManager**: Responsible for dynamic plugin discovery, management, and lifecycle control. Handles plugin instantiation, dependency resolution, and configuration management.

4. **ConfigurationSchema**: Defines the configuration fields and validation rules for plugins using a declarative syntax.

### Plugin Discovery and Loading

Plugins are discovered from:
- Plugin directories specified in the configuration
- The `interface.plugins` package
- External plugin modules in designated directories

The PluginManager dynamically loads plugins, resolves dependencies, and manages their lifecycle.

## Creating ConfigurationPlugin Implementations

### Step-by-Step Guide

Follow these steps to create a new ConfigurationPlugin:

1. **Create the Plugin Class**
2. **Implement Required Methods**
3. **Define Configuration Fields**
4. **Implement Validation Logic**
5. **Implement Serialization Methods**
6. **Create the UI Widget**
7. **Register the Plugin**

### Example: Custom Configuration Plugin

```python
"""
Custom Configuration Plugin
Implements the ConfigurationPlugin interface for a custom format.
"""

from typing import List, Dict, Any, Optional

from interface.plugins.configuration_plugin import ConfigurationPlugin
from interface.plugins.config_schemas import FieldDefinition, FieldType
from interface.plugins.validation_framework import ValidationResult
from interface.models.folder_configuration import ConvertFormat
from interface.plugins.ui_abstraction import ConfigurationWidgetBuilder


class CustomConfigurationPlugin(ConfigurationPlugin):
    """
    Custom configuration plugin implementing the ConfigurationPlugin interface.
    """
    
    @classmethod
    def get_name(cls) -> str:
        """Get the human-readable name of the plugin."""
        return "Custom Configuration"
    
    @classmethod
    def get_identifier(cls) -> str:
        """Get the unique identifier for the plugin."""
        return "custom_configuration"
    
    @classmethod
    def get_description(cls) -> str:
        """Get a detailed description of the plugin's functionality."""
        return "Provides custom format configuration options"
    
    @classmethod
    def get_version(cls) -> str:
        """Get the plugin version."""
        return "1.0.0"
    
    @classmethod
    def get_format_name(cls) -> str:
        """Get the human-readable name of the configuration format."""
        return "Custom Format"
    
    @classmethod
    def get_format_enum(cls) -> ConvertFormat:
        """Get the ConvertFormat enum value associated with this format."""
        return ConvertFormat.CUSTOM
    
    @classmethod
    def get_config_fields(cls) -> List[FieldDefinition]:
        """Get the list of field definitions for this configuration format."""
        fields = [
            FieldDefinition(
                name="field1",
                field_type=FieldType.STRING,
                label="Field 1",
                description="First configuration field",
                default="default value",
                required=True,
                max_length=50
            ),
            FieldDefinition(
                name="field2",
                field_type=FieldType.INTEGER,
                label="Field 2",
                description="Second configuration field",
                default=42,
                required=True,
                min_value=0,
                max_value=100
            ),
            FieldDefinition(
                name="field3",
                field_type=FieldType.BOOLEAN,
                label="Field 3",
                description="Third configuration field",
                default=False
            ),
            FieldDefinition(
                name="field4",
                field_type=FieldType.SELECT,
                label="Field 4",
                description="Fourth configuration field (select)",
                default="option1",
                choices=[
                    {"label": "Option 1", "value": "option1"},
                    {"label": "Option 2", "value": "option2"},
                    {"label": "Option 3", "value": "option3"}
                ]
            ),
            FieldDefinition(
                name="field5",
                field_type=FieldType.MULTI_SELECT,
                label="Field 5",
                description="Fifth configuration field (multi-select)",
                default=["option1"],
                choices=[
                    {"label": "Option 1", "value": "option1"},
                    {"label": "Option 2", "value": "option2"},
                    {"label": "Option 3", "value": "option3"}
                ]
            )
        ]
        return fields
    
    def validate_config(self, config: Dict[str, Any]) -> ValidationResult:
        """Validate configuration data against the format's schema."""
        schema = self.get_configuration_schema()
        if schema:
            return schema.validate(config)
        return ValidationResult(success=True, errors=[])
    
    def create_config(self, data: Dict[str, Any]) -> Any:
        """Create a configuration instance from raw data."""
        class CustomConfiguration:
            def __init__(self, field1, field2, field3, field4, field5):
                self.field1 = field1
                self.field2 = field2
                self.field3 = field3
                self.field4 = field4
                self.field5 = field5
        
        return CustomConfiguration(
            field1=data.get("field1", "default value"),
            field2=data.get("field2", 42),
            field3=data.get("field3", False),
            field4=data.get("field4", "option1"),
            field5=data.get("field5", ["option1"])
        )
    
    def serialize_config(self, config: Any) -> Dict[str, Any]:
        """Serialize a configuration instance to dictionary format."""
        return {
            "field1": config.field1,
            "field2": config.field2,
            "field3": config.field3,
            "field4": config.field4,
            "field5": config.field5
        }
    
    def deserialize_config(self, data: Dict[str, Any]) -> Any:
        """Deserialize stored data into a configuration instance."""
        return self.create_config(data)
    
    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the plugin with configuration."""
        if config:
            self._config = self.create_config(config)
        else:
            self._config = self.create_config({})
    
    def activate(self) -> None:
        """Activate the plugin."""
        pass
    
    def deactivate(self) -> None:
        """Deactivate the plugin."""
        pass
    
    def create_widget(self, parent: Any = None) -> Any:
        """Create a UI widget for configuring the plugin."""
        schema = self.get_configuration_schema()
        if schema:
            builder = ConfigurationWidgetBuilder()
            return builder.build_configuration_panel(
                schema, 
                self._config.__dict__ if hasattr(self, '_config') else {}, 
                parent
            )
        return None
```

## Configuration Schema Definition

The configuration schema defines the fields and validation rules for plugins. Fields are defined using `FieldDefinition` objects with various properties:

### Field Types

The system supports the following field types:

| Type | Description |
|------|-------------|
| STRING | Text field |
| INTEGER | Integer number field |
| FLOAT | Floating-point number field |
| BOOLEAN | Boolean (true/false) field |
| LIST | List of values |
| DICT | Dictionary of key-value pairs |
| SELECT | Single select dropdown |
| MULTI_SELECT | Multi-select dropdown |

### Validation Properties

Each field can have validation properties:

- `required`: Whether the field is required (default: False)
- `min_value` / `max_value`: Numeric range validation
- `min_length` / `max_length`: String length validation
- `choices`: Available choices for select fields
- `validators`: Custom validation functions

### Example Field Definitions

```python
from interface.plugins.config_schemas import FieldDefinition, FieldType
from interface.plugins.validation_framework import Validator

# String field with validation
string_field = FieldDefinition(
    name="api_key",
    field_type=FieldType.STRING,
    label="API Key",
    description="API key for authentication",
    required=True,
    min_length=10,
    max_length=50
)

# Numeric field with range validation
numeric_field = FieldDefinition(
    name="timeout",
    field_type=FieldType.INTEGER,
    label="Timeout",
    description="Connection timeout in seconds",
    default=30,
    min_value=1,
    max_value=300
)

# Select field with choices
select_field = FieldDefinition(
    name="log_level",
    field_type=FieldType.SELECT,
    label="Log Level",
    description="Logging verbosity level",
    default="INFO",
    choices=[
        {"label": "Debug", "value": "DEBUG"},
        {"label": "Info", "value": "INFO"},
        {"label": "Warning", "value": "WARNING"},
        {"label": "Error", "value": "ERROR"}
    ]
)

# Custom validator example
class EmailValidator(Validator):
    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, str):
            return ValidationResult(success=False, errors=["Email must be a string"])
        if "@" not in value or "." not in value:
            return ValidationResult(success=False, errors=["Invalid email format"])
        return ValidationResult(success=True, errors=[])

email_field = FieldDefinition(
    name="email",
    field_type=FieldType.STRING,
    label="Email",
    description="Email address",
    required=True,
    validators=[EmailValidator()]
)
```

## Widget Creation and Integration

The plugin system provides a UI abstraction layer that allows plugins to create configuration widgets that work with both Qt and Tkinter frameworks.

### Using ConfigurationWidgetBuilder

The `ConfigurationWidgetBuilder` class simplifies widget creation by automatically generating a configuration panel from a schema:

```python
from interface.plugins.ui_abstraction import ConfigurationWidgetBuilder

def create_widget(self, parent: Any = None) -> Any:
    """Create a UI widget for configuring the plugin."""
    schema = self.get_configuration_schema()
    if schema:
        builder = ConfigurationWidgetBuilder()
        return builder.build_configuration_panel(schema, self._config.__dict__, parent)
    return None
```

### Custom Widget Creation

For more complex scenarios, you can create custom widgets directly:

```python
def create_widget(self, parent: Any = None) -> Any:
    """Create a custom UI widget for configuring the plugin."""
    if self._is_qt:
        # Create Qt widget
        from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit
        widget = QWidget(parent)
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("Custom Configuration"))
        # Add custom fields
        return widget
    else:
        # Create Tkinter widget
        import tkinter as tk
        from tkinter import ttk
        widget = ttk.Frame(parent)
        label = ttk.Label(widget, text="Custom Configuration")
        label.pack()
        # Add custom fields
        return widget
```

## Validation and Lifecycle Management

### Validation Framework

The validation framework provides a structured way to validate configuration data. Each field type has built-in validation, and custom validators can be created by implementing the `Validator` interface:

```python
from interface.plugins.validation_framework import Validator, ValidationResult

class PositiveNumberValidator(Validator):
    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, (int, float)):
            return ValidationResult(success=False, errors=["Value must be a number"])
        if value <= 0:
            return ValidationResult(success=False, errors=["Value must be positive"])
        return ValidationResult(success=True, errors=[])
```

### Plugin Lifecycle

Plugins have the following lifecycle methods:

1. **initialize()**: Called when the plugin is first loaded
2. **activate()**: Called when the plugin is activated for use
3. **deactivate()**: Called when the plugin is deactivated or the application shuts down
4. **update_configuration()**: Called when configuration is updated

### Configuration Management

Plugins can manage their configuration using:

```python
def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
    """Initialize the plugin with configuration."""
    if config:
        self._config = self.create_config(config)
    else:
        self._config = self.create_config({})

def update_configuration(self, config: Dict[str, Any]) -> ValidationResult:
    """Update the plugin's configuration."""
    validation = self.validate_configuration(config)
    if validation.success:
        self.initialize(config)
    return validation
```

## Plugin Types

### Configuration Plugins

Configuration plugins handle format-specific configuration for EDI conversion:

```python
class CSVConfigurationPlugin(ConfigurationPlugin):
    @classmethod
    def get_format_enum(cls) -> ConvertFormat:
        return ConvertFormat.CSV
    
    def create_config(self, data: Dict[str, Any]) -> CSVConfiguration:
        return CSVConfiguration(**data)
```

### Generic Plugins

Generic plugins extend PluginBase directly for custom functionality:

```python
from interface.plugins.plugin_base import PluginBase

class CustomPlugin(PluginBase):
    @classmethod
    def get_name(cls) -> str:
        return "Custom Plugin"
    
    @classmethod
    def get_identifier(cls) -> str:
        return "custom_plugin"
    
    # Implement lifecycle methods
    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        pass
    
    def activate(self) -> None:
        pass
    
    def deactivate(self) -> None:
        pass
    
    def create_widget(self, parent: Any = None) -> Any:
        return None
```

## Plugin Manager Usage

The PluginManager handles plugin discovery, initialization, and management:

```python
from interface.plugins.plugin_manager import PluginManager

# Initialize plugin manager
plugin_manager = PluginManager()

# Discover plugins
discovered_plugins = plugin_manager.discover_plugins()

# Initialize plugins
plugin_manager.initialize_plugins()

# Get configuration plugins
config_plugins = plugin_manager.get_configuration_plugins()

# Get plugin by format
csv_plugin = plugin_manager.get_configuration_plugin_by_format(ConvertFormat.CSV)

# Create configuration widget
widget = plugin_manager.create_configuration_widget(ConvertFormat.CSV)

# Validate configuration
validation = plugin_manager.validate_configuration(ConvertFormat.CSV, config_data)
```

## Troubleshooting Tips

### Plugin Discovery Issues

1. **Check plugin directory structure**: Ensure plugins are in the correct directory structure with `__init__.py` files
2. **Verify import paths**: Check that plugin files can be imported correctly
3. **Check plugin class definitions**: Ensure plugins extend PluginBase or ConfigurationPlugin
4. **Check for errors in discovery**: Look for error messages in the console

### Configuration Validation Issues

1. **Check schema definition**: Verify field types and validation rules
2. **Test validation directly**: Use `plugin.validate_configuration(config)` to test
3. **Check field names**: Ensure configuration keys match field names
4. **Test default values**: Verify default values are correctly handled

### Widget Creation Issues

1. **Check UI framework compatibility**: Ensure widgets work with both Qt and Tkinter
2. **Verify widget construction**: Check that parent widget parameters are handled
3. **Test widget display**: Ensure widgets are properly sized and laid out
4. **Check for missing dependencies**: Verify required UI framework packages are installed

### Performance Issues

1. **Optimize initialization**: Avoid heavy operations in initialize()
2. **Cache configuration**: Cache validated configurations
3. **Optimize widget creation**: Avoid recreating widgets unnecessarily
4. **Profile plugin code**: Use Python profiling tools to identify bottlenecks

### Debugging Plugins

1. **Enable debug logging**: Use logging module to track plugin activity
2. **Check for exceptions**: Wrap plugin methods in try-except blocks
3. **Print debug information**: Add print statements to track execution flow
4. **Use debugger**: Attach a debugger to examine plugin state

### Common Mistakes

1. **Forgetting to implement abstract methods**: Ensure all @abstractmethod methods are implemented
2. **Duplicate plugin identifiers**: Each plugin must have a unique identifier
3. **Incorrect format enum mapping**: Verify that get_format_enum() returns a valid ConvertFormat value
4. **Missing field definitions**: Ensure get_config_fields() returns all required fields
5. **Invalid field types**: Use only supported FieldType values

## Advanced Topics

### Plugin Dependencies

Plugins can declare dependencies on other plugins:

```python
@classmethod
def get_dependencies(cls) -> List[str]:
    """Get the list of plugin dependencies."""
    return ["csv_configuration", "custom_plugin"]
```

### Plugin Compatibility Checks

Plugins can check system compatibility:

```python
@classmethod
def is_compatible(cls) -> bool:
    """Check if the plugin is compatible with the current system."""
    try:
        import some_dependency
        return True
    except ImportError:
        return False
```

### Dynamic Plugin Loading

Plugins can be loaded dynamically from external directories:

```python
plugin_manager = PluginManager()
plugin_manager.add_plugin_directory("/path/to/external/plugins")
plugin_manager.discover_plugins()
```

### Unit Testing Plugins

Plugins should be tested to ensure they function correctly:

```python
import unittest
from interface.plugins.plugin_manager import PluginManager

class TestCSVConfigurationPlugin(unittest.TestCase):
    def setUp(self):
        self.plugin_manager = PluginManager()
        self.plugin_manager.discover_plugins()
    
    def test_plugin_discovery(self):
        plugins = self.plugin_manager.get_configuration_plugins()
        self.assertGreater(len(plugins), 0)
    
    def test_csv_plugin_exists(self):
        plugin = self.plugin_manager.get_configuration_plugin_by_format(ConvertFormat.CSV)
        self.assertIsNotNone(plugin)
    
    def test_validation(self):
        plugin = self.plugin_manager.get_configuration_plugin_by_format(ConvertFormat.CSV)
        config = {
            "include_headers": True,
            "filter_ampersand": False,
            "include_item_numbers": True
        }
        validation = plugin.validate_configuration(config)
        self.assertTrue(validation.success)
    
    def test_config_creation(self):
        plugin = self.plugin_manager.get_configuration_plugin_by_format(ConvertFormat.CSV)
        config = {
            "include_headers": True,
            "filter_ampersand": False,
            "include_item_numbers": True
        }
        csv_config = plugin.create_config(config)
        self.assertIsNotNone(csv_config)
        self.assertTrue(csv_config.include_headers)

if __name__ == "__main__":
    unittest.main()
```

## Best Practices

1. **Keep plugins focused**: Each plugin should handle a specific functionality
2. **Use meaningful identifiers**: Choose unique and descriptive plugin identifiers
3. **Provide clear documentation**: Document plugin purpose and usage
4. **Validate configuration**: Implement robust validation for configuration fields
5. **Handle errors gracefully**: Implement error handling for all plugin operations
6. **Test thoroughly**: Write unit tests for each plugin
7. **Maintain compatibility**: Ensure plugins work with both Qt and Tkinter
8. **Keep dependencies minimal**: Minimize external dependencies
9. **Follow coding standards**: Adhere to project coding guidelines
10. **Version control**: Use semantic versioning for plugin updates

## Summary

The Batch File Processor plugin system provides a robust architecture for extending the application's functionality. By following the guidelines in this document, you can create powerful plugins that integrate seamlessly with the system. Whether you're adding support for new file formats, implementing custom validation logic, or creating specialized UI widgets, the plugin system provides the flexibility you need.