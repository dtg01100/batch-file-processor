# Configuration Plugin Developer Guide

This guide explains how to create custom configuration plugins for the batch file processor.

## Creating a Configuration Plugin

### Step 1: Define the Plugin Class

Create a new file in `interface/plugins/` (e.g., `my_format_configuration_plugin.py`):

```python
from typing import List, Dict, Any, Optional
from .configuration_plugin import ConfigurationPlugin
from .config_schemas import FieldDefinition, FieldType, ConfigurationSchema
from .validation_framework import ValidationResult
from ..models.folder_configuration import ConvertFormat

class MyFormatConfigurationPlugin(ConfigurationPlugin):
    """Configuration plugin for MyFormat."""
    
    @classmethod
    def get_name(cls) -> str:
        return "My Format Configuration"
    
    @classmethod
    def get_identifier(cls) -> str:
        return "my_format_configuration"
    
    @classmethod
    def get_description(cls) -> str:
        return "Provides My Format configuration options"
    
    @classmethod
    def get_version(cls) -> str:
        return "1.0.0"
    
    @classmethod
    def get_format_name(cls) -> str:
        return "MyFormat"
    
    @classmethod
    def get_format_enum(cls) -> ConvertFormat:
        return ConvertFormat.MY_FORMAT
    
    @classmethod
    def get_config_fields(cls) -> List[FieldDefinition]:
        fields = [
            FieldDefinition(
                name="option_one",
                field_type=FieldType.BOOLEAN,
                label="Option One",
                description="Enable first option",
                default=False
            ),
            FieldDefinition(
                name="option_two",
                field_type=FieldType.STRING,
                label="Option Two",
                description="Second configuration option",
                default="",
                max_length=100
            ),
            FieldDefinition(
                name="selection",
                field_type=FieldType.SELECT,
                label="Selection",
                description="Choose an option",
                default="option_a",
                choices=[
                    {"value": "option_a", "label": "Option A"},
                    {"value": "option_b", "label": "Option B"},
                    {"value": "option_c", "label": "Option C"}
                ]
            ),
            FieldDefinition(
                name="numeric_value",
                field_type=FieldType.INTEGER,
                label="Numeric Value",
                description="Enter a number",
                default=0,
                min_value=0,
                max_value=100
            )
        ]
        return fields
```

### Step 2: Implement Required Methods

```python
    def validate_config(self, config: Dict[str, Any]) -> ValidationResult:
        """Validate configuration data."""
        schema = self.get_configuration_schema()
        if schema:
            return schema.validate(config)
        return ValidationResult(success=True, errors=[])
    
    def create_config(self, data: Dict[str, Any]):
        """Create configuration instance from raw data."""
        return MyFormatConfiguration(
            option_one=data.get("option_one", False),
            option_two=data.get("option_two", ""),
            selection=data.get("selection", "option_a"),
            numeric_value=data.get("numeric_value", 0)
        )
    
    def serialize_config(self, config) -> Dict[str, Any]:
        """Serialize configuration to dictionary."""
        if isinstance(config, dict):
            return config
        return {
            "option_one": config.option_one,
            "option_two": config.option_two,
            "selection": config.selection,
            "numeric_value": config.numeric_value
        }
    
    def deserialize_config(self, data: Dict[str, Any]):
        """Deserialize dictionary to configuration."""
        return self.create_config(data)
    
    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the plugin."""
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
    
    def create_widget(self, parent=None):
        """Create configuration widget."""
        schema = self.get_configuration_schema()
        if schema:
            from .ui_abstraction import ConfigurationWidgetBuilder
            builder = ConfigurationWidgetBuilder()
            config_dict = self._config.__dict__ if hasattr(self, '_config') else {}
            return builder.build_configuration_panel(schema, config_dict, parent)
        return None
```

### Step 3: Register the ConvertFormat Enum

If your format doesn't exist in `ConvertFormat`, add it:

```python
# In interface/models/folder_configuration.py
class ConvertFormat(Enum):
    CSV = "csv"
    # ... existing formats ...
    MY_FORMAT = "my_format"
```

### Step 4: Register Plugin with Section Registry

Option A: Automatic registration via PluginManager
```python
# The plugin will be auto-discovered when PluginManager.discover_plugins() is called
```

Option B: Manual section registration
```python
from interface.plugins.section_registry import SectionRegistry

# In your plugin's activate() method
SectionRegistry.register_plugin_section(
    MyFormatConfigurationPlugin.get_identifier(),
    MyFormatSection  # Your custom section class
)
```

## Field Types Reference

| FieldType | Description | Parameters |
|-----------|-------------|------------|
| `STRING` | Text input | `max_length`, `validators` |
| `INTEGER` | Whole number | `min_value`, `max_value`, `validators` |
| `FLOAT` | Decimal number | `min_value`, `max_value`, `validators` |
| `BOOLEAN` | Checkbox | - |
| `LIST` | List input | `validators` |
| `DICT` | Dictionary input | `validators` |
| `SELECT` | Dropdown selection | `choices` (required) |
| `MULTI_SELECT` | Multiple selection | `choices` (required) |

## Custom Validators

```python
from interface.plugins.validation_framework import Validator, ValidationResult

class MyCustomValidator(Validator):
    def validate(self, value) -> ValidationResult:
        if value and not value.startswith("valid_"):
            return ValidationResult(
                success=False,
                errors=["Value must start with 'valid_'"]
            )
        return ValidationResult(success=True, errors=[])

# Usage in FieldDefinition
FieldDefinition(
    name="custom_field",
    field_type=FieldType.STRING,
    label="Custom Field",
    validators=[MyCustomValidator()]
)
```

## Creating Custom Configuration Sections

For more complex configurations, create custom sections:

```python
from interface.plugins.section_registry import ConfigSectionBase, SectionRenderer

class MyFormatSection(ConfigSectionBase):
    """Custom configuration section for MyFormat."""
    
    @classmethod
    def get_section_id(cls) -> str:
        return "my_format_section"
    
    @classmethod
    def get_section_title(cls) -> str:
        return "My Format Settings"
    
    @classmethod
    def get_section_description(cls) -> str:
        return "Configure My Format specific options"
    
    @classmethod
    def get_schema(cls):
        fields = MyFormatConfigurationPlugin.get_config_fields()
        return ConfigurationSchema(fields)
    
    @classmethod
    def get_priority(cls) -> int:
        return 50  # Lower = appears first
    
    @classmethod
    def is_expanded_by_default(cls) -> bool:
        return True


class MyFormatSectionRenderer(SectionRenderer):
    """Renderer for MyFormat section."""
    
    def __init__(self):
        self._widget = None
    
    def render(self, parent, config=None):
        # Create and return Qt/Tkinter widget
        schema = MyFormatSection.get_schema()
        # Build widget using ConfigurationWidgetBuilder
        return widget
    
    def get_values(self) -> Dict[str, Any]:
        return self._widget.get_values() if self._widget else {}
    
    def set_values(self, config: Dict[str, Any]):
        if self._widget:
            self._widget.set_values(config)
    
    def validate(self) -> bool:
        return True
    
    def get_validation_errors(self) -> List[str]:
        return []


# Register section and renderer
SectionRegistry.register_section(MyFormatSection)
SectionRegistry.register_renderer(MyFormatSection, lambda: MyFormatSectionRenderer())
```

## Integration with FormGenerator

Add plugin sections to forms:

```python
from interface.form.form_generator import FormGeneratorFactory
from interface.plugins.config_schemas import ConfigurationSchema

# Create form generator
schema = ConfigurationSchema(fields)
form = FormGeneratorFactory.create_form_generator(schema, 'qt')

# Add plugin sections
form.add_plugin_section(
    section_id="my_format",
    schema=MyFormatConfigurationPlugin().get_configuration_schema(),
    config=initial_config
)

# Build form
widget = form.build_form(config=initial_config, parent=parent)

# Get values when saving
values = form.get_values()
plugin_values = form.get_plugin_section_values()

# Validate
result = form.validate()
plugin_result = form.validate_plugin_sections()
```

## Testing Your Plugin

```python
import pytest
from interface.plugins.plugin_manager import PluginManager
from interface.plugins.section_registry import SectionRegistry

class TestMyFormatPlugin:
    def test_plugin_discovery(self):
        manager = PluginManager()
        discovered = manager.discover_plugins()
        assert "my_format_configuration" in discovered
    
    def test_plugin_initialization(self):
        manager = PluginManager()
        manager.discover_plugins()
        manager.initialize_plugins()
        
        plugin = manager.get_configuration_plugin_by_format(
            ConvertFormat.MY_FORMAT
        )
        assert plugin is not None
    
    def test_validation(self):
        plugin = MyFormatConfigurationPlugin()
        result = plugin.validate_config({
            "option_one": True,
            "option_two": "test"
        })
        assert result.success
    
    def test_serialization(self):
        plugin = MyFormatConfigurationPlugin()
        config = plugin.create_config({
            "option_one": True,
            "option_two": "test"
        })
        serialized = plugin.serialize_config(config)
        assert serialized["option_one"] is True
```

## Migration Guide for Existing Plugins

If migrating from an older plugin system:

1. **Replace class inheritance**: Change from `Plugin` to `ConfigurationPlugin`
2. **Add required methods**: Implement all abstract methods listed above
3. **Convert field definitions**: Use `FieldDefinition` class instead of dictionaries
4. **Update configuration model**: Ensure your `create_config` returns the correct model type
5. **Register with ConvertFormat**: Add your format to the enum if not already present
6. **Test integration**: Verify plugin works with PluginManager and FormGenerator
