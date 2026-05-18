# Converter Architecture

**Version:** 1.0  
**Date:** 2026-05-18  
**Status:** DRAFT

---

## 1. Overview

The converter system transforms EDI files into various output formats. Each converter is a plugin that implements a standard interface.

## 2. Converter Interface

```python
# dispatch/converters/convert_base.py
def edi_convert(
    edi_process: dict,        # EDI processing context
    output_filename: str,      # Target output path
    settings_dict: dict,       # Global settings
    parameters_dict: dict,     # Converter-specific parameters
    upc_lookup: dict = None,   # UPC lookup table
) -> tuple[bool, str, list[str]]:
    """Convert EDI file to target format.
    
    Returns:
        Tuple of (success, output_path, errors)
    """
```

## 3. Converter Registry

**Location:** `dispatch/converters/registry.py`

```python
class ConverterRegistry:
    """Discovers and manages converter plugins."""
    
    @classmethod
    def get_converter(cls, format_name: str):
        """Get converter by format name."""
        if format_name not in cls.BUILTIN_CONVERTERS:
            raise ValueError(f"Unknown format: {format_name}")
        
        module_path = cls.BUILTIN_CONVERTERS[format_name]
        return import_module(module_path)
```

## 4. Built-in Converters

| Format | Module | Description |
|--------|--------|-------------|
| scannerware | `convert_to_scannerware.py` | Scanner-ready inventory format |
| csv | `convert_to_csv.py` | Generic CSV output |
| estore_einvoice | `convert_to_estore_einvoice.py` | eStore eInvoice XML |
| estore_einvoice_generic | `convert_to_estore_einvoice_generic.py` | Generic eInvoice XML |
| fintech | `convert_to_fintech.py` | FinTech specific format |
| jolley_custom | `convert_to_jolley_custom.py` | Jolley distribution format |
| simplified_csv | `convert_to_simplified_csv.py` | Simplified CSV |
| stewarts_custom | `convert_to_stewarts_custom.py` | Stewart's distribution format |
| tweaks | `convert_to_tweaks.py` | EDI tweaks output |
| yellowdog_csv | `convert_to_yellowdog_csv.py` | YellowDog CSV format |
| scansheet_type_a | `convert_to_scansheet_type_a.py` | Scansheet type A format |

## 5. Converter Base Class

```python
# dispatch/converters/convert_base.py
class ConverterBase:
    """Base class for converters providing common functionality."""
    
    def __init__(self):
        self._edi_process = None
        self._output_filename = None
        self._settings_dict = None
        self._parameters_dict = None
        self._upc_lookup = None
    
    def setup(self, edi_process, output_filename, settings, parameters, upc_lookup=None):
        """Initialize converter with processing context."""
        self._edi_process = edi_process
        self._output_filename = output_filename
        self._settings_dict = settings
        self._parameters_dict = parameters
        self._upc_lookup = upc_lookup or {}
    
    def convert(self) -> tuple[bool, str, list]:
        """Execute conversion. Override in subclasses."""
        raise NotImplementedError
```

## 6. Converter Mixins

**Location:** `dispatch/converters/mixins.py`

Provides reusable functionality for converters:

```python
class EDIParseMixin:
    """Mixin providing EDI parsing utilities."""
    
    def parse_edi(self, content: str) -> dict:
        """Parse EDI content into structured dict."""
        ...

class CustomerLookupMixin:
    """Mixin providing customer lookup service."""
    
    def get_customer_info(self, customer_id: str) -> dict:
        """Look up customer information."""
        ...

class UPCLookupMixin:
    """Mixin providing UPC lookup service."""
    
    def get_upc_info(self, upc: str) -> dict:
        """Look up UPC/barcode information."""
        ...
```

## 7. Adding a New Converter

### Step 1: Create converter module

```python
# dispatch/converters/convert_to_myformat.py
from dispatch.converters.convert_base import edi_convert

def edi_convert(edi_process, output_filename, settings_dict, parameters_dict, upc_lookup=None):
    """Convert EDI to MyFormat."""
    # Implementation
    return (True, output_filename, [])
```

### Step 2: Register in registry

```python
# dispatch/converters/registry.py
BUILTIN_CONVERTERS = {
    # ... existing formats ...
    'myformat': 'dispatch.converters.convert_to_myformat',
}
```

### Step 3: Add configuration plugin (optional)

```python
# interface/plugins/myformat_configuration_plugin.py
class MyFormatConfigurationPlugin:
    """Configuration UI for my format."""
    ...
```

### Step 4: Add tests

```python
# tests/unit/test_convert_to_myformat.py
def test_myformat_conversion():
    ...
```

## 8. Related Documents

- [PROCESSING_PIPELINE.md](PROCESSING_PIPELINE.md) - Pipeline integration
- [PLUGIN_API.md](PLUGIN_API.md) - Plugin interfaces
- [BACKEND_ARCHITECTURE.md](BACKEND_ARCHITECTURE.md) - Backend architecture
