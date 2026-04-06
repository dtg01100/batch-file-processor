# Converter Plugin Guide

This guide explains how to add new EDI conversion formats and extend existing ones. The system uses auto-discovery, so no manual registration is required.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Auto-Discovery System                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  dispatch/converters/            interface/plugins/                │
│  ┌──────────────────────┐       ┌──────────────────────────────┐   │
│  │ convert_to_*.py      │──────▶│ *_configuration_plugin.py    │   │
│  │ (backend processing) │       │ (GUI configuration)          │   │
│  └──────────────────────┘       └──────────────────────────────┘   │
│            │                              │                         │
│            ▼                              ▼                         │
│  dispatch/pipeline/converter.py    ConvertFormat enum               │
│  SUPPORTED_FORMATS (auto)         (auto-populated)                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Part 1: Adding a New Converter

### Step 1: Create the Backend Converter

Create `dispatch/converters/convert_to_<format_name>.py`:

```python
"""<Format Name> EDI Converter."""

from dispatch.converters.convert_base import (
    BaseEDIConverter,
    ConversionContext,
    EDIRecord,
)

def edi_convert(
    edi_process: str,
    output_filename: str,
    settings_dict: dict,
    parameters_dict: dict,
    upc_lut: dict,
) -> str:
    """Convert EDI file to <Format Name> format.
    
    Args:
        edi_process: Path to input EDI file
        output_filename: Base path for output (without extension)
        settings_dict: Application settings
        parameters_dict: Folder-specific conversion parameters
        upc_lut: UPC lookup table
    
    Returns:
        Path to the generated output file
    """
    converter = MyFormatConverter()
    return converter.edi_convert(
        edi_process, output_filename, settings_dict, parameters_dict, upc_lut
    )


class MyFormatConverter(BaseEDIConverter):
    """Converter for <Format Name> format."""
    
    def _initialize_output(self, context: ConversionContext) -> None:
        """Set up output file/writer."""
        context.output_file = open(context.get_output_path(".txt"), "w")
        # Initialize any format-specific state
    
    def process_a_record(self, record: EDIRecord, context: ConversionContext) -> None:
        """Process header record (optional - override only if needed)."""
        context.arec_header = record.fields
    
    def process_b_record(self, record: EDIRecord, context: ConversionContext) -> None:
        """Process line item record (REQUIRED)."""
        # Example: write line to output file
        context.output_file.write(f"{record.fields['item_number']}\n")
    
    def process_c_record(self, record: EDIRecord, context: ConversionContext) -> None:
        """Process charge record (optional - override only if needed)."""
        pass
    
    def _finalize_output(self, context: ConversionContext) -> None:
        """Clean up resources."""
        if context.output_file:
            context.output_file.close()
```

### Step 2: Create the GUI Configuration Plugin

Create `interface/plugins/<format_name>_configuration_plugin.py`:

```python
"""<Format Name> Configuration Plugin."""

from typing import Any

from ..models.folder_configuration import ConvertFormat
from .config_schemas import FieldDefinition, FieldType
from .configuration_plugin import ConfigurationPlugin
from .validation_framework import ValidationResult

class <FormatName>ConfigurationPlugin(ConfigurationPlugin):
    """Configuration plugin for <Format Name> format."""
    
    @classmethod
    def get_name(cls) -> str:
        return "<Format Name> Configuration"
    
    @classmethod
    def get_identifier(cls) -> str:
        return "<format_name>_configuration"
    
    @classmethod
    def get_description(cls) -> str:
        return "Provides <Format Name> format configuration options"
    
    @classmethod
    def get_version(cls) -> str:
        return "1.0.0"
    
    @classmethod
    def get_format_name(cls) -> str:
        return "<Format Name>"
    
    @classmethod
    def get_format_enum(cls) -> ConvertFormat:
        # The enum attribute name is derived from the backend module name
        # convert_to_scannerware -> SCANNERWARE
        # convert_to_scansheet_type_a -> SCANSHEET_TYPE_A
        return ConvertFormat.<FORMAT_NAME>
    
    @classmethod
    def get_config_fields(cls) -> list[FieldDefinition]:
        return [
            FieldDefinition(
                name="my_option",
                field_type=FieldType.BOOLEAN,
                label="My Option",
                description="Toggle my option",
                default=False,
            ),
        ]
    
    def validate_config(self, config: dict[str, Any]) -> ValidationResult:
        schema = self.get_configuration_schema()
        if schema:
            return schema.validate(config)
        return ValidationResult(success=True, errors=[])
    
    def initialize(self, config: dict[str, Any] | None = None) -> None:
        if config:
            self._config = config
    
    def activate(self) -> None:
        pass
    
    def deactivate(self) -> None:
        pass
```

### Step 3: Register the Plugin

Add to `interface/plugins/__init__.py`:
```python
from .<format_name>_configuration_plugin import <FormatName>ConfigurationPlugin

__all__ = [
    # ... existing exports ...
    "<FormatName>ConfigurationPlugin",
]
```

### Step 4: Add Display Value for Legacy Compatibility (if needed)

If the format name has special casing (e.g., "ScannerWare" vs "scannerware"), update the `DISPLAY_VALUES` mapping in `interface/models/folder_configuration.py`:

```python
DISPLAY_VALUES = {
    "scannerware": "ScannerWare",
    "scansheet_type_a": "ScanSheet_Type_A",
    # Add your format:
    "my_format": "My Format",
}
```

## Part 2: Extending an Existing Converter

### Adding New Parameters

1. **Backend**: Add parameter handling in `_initialize_output`:

```python
def _initialize_output(self, context: ConversionContext) -> None:
    params = context.parameters_dict
    context.user_data["my_new_param"] = params.get("my_new_param", "default")
```

2. **GUI**: Add field definition in `get_config_fields`:

```python
FieldDefinition(
    name="my_new_param",
    field_type=FieldType.STRING,
    label="My New Parameter",
    description="Description of the parameter",
    default="default",
),
```

### Adding New Record Processing

Override the appropriate hook method in your converter class:

```python
def process_d_record(self, record: EDIRecord, context: ConversionContext) -> None:
    """Process D records (if your format has them)."""
    # Implement processing logic
    pass
```

## BaseEDIConverter Hook Methods

| Method | Required | Description |
|--------|----------|-------------|
| `_initialize_output(context)` | Yes | Set up output file/writer |
| `process_b_record(record, context)` | Yes | Process line item records |
| `process_a_record(record, context)` | No | Process header records |
| `process_c_record(record, context)` | No | Process charge/tax records |
| `_finalize_output(context)` | No | Clean up resources |
| `_should_process_record_type(record_type)` | No | Filter which record types to process |

## ConversionContext Attributes

| Attribute | Type | Description |
|----------|------|-------------|
| `edi_filename` | str | Input EDI file path |
| `output_filename` | str | Base output filename (without extension) |
| `settings_dict` | dict | Application settings |
| `parameters_dict` | dict | Folder conversion parameters |
| `upc_lut` | dict | UPC lookup table |
| `arec_header` | dict | Current A record fields |
| `line_num` | int | Current line number |
| `records_processed` | int | Count of processed records |
| `output_file` | TextIO | Output file handle |
| `csv_writer` | CSV writer | Pre-configured CSV writer (if using CSV output) |
| `user_data` | dict | Custom state for converters |

## Testing Your Converter

### Backend Test
```python
from dispatch.converters.convert_to_myformat import MyFormatConverter

converter = MyFormatConverter()
result = converter.edi_convert(
    "input.edi",
    "output",
    settings={},
    parameters={},
    upc_lut={}
)
```

### Integration Test
```python
def test_myformat_converter():
    from dispatch.pipeline.converter import SUPPORTED_FORMATS
    assert "myformat" in SUPPORTED_FORMATS
```

## Troubleshooting

**Converter not found in SUPPORTED_FORMATS:**
- Ensure file is named `convert_to_<format>.py`
- Ensure file is in `dispatch/converters/` directory
- Check that module name matches expected pattern

**GUI plugin not appearing in dropdown:**
- Ensure plugin is registered in `interface/plugins/__init__.py`
- Check that `get_format_enum()` returns correct value
- Verify `ConvertFormat.<FORMAT_NAME>` exists (check the naming: `convert_to_foo` → `FOO`)

**Legacy display value mismatch:**
- If stored values use different casing, add entry to `DISPLAY_VALUES` in `folder_configuration.py`
