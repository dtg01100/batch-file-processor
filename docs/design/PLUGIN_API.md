# Plugin API Reference

**Version:** 1.0  
**Date:** 2026-05-18  
**Status:** DRAFT

---

## 1. Overview

The system uses a plugin architecture for converters and configuration. Plugins provide extensibility without modifying core code.

## 2. Converter Plugins

### 2.1 Interface

```python
# dispatch/converters/convert_base.py
def edi_convert(
    edi_process: dict,
    output_filename: str,
    settings_dict: dict,
    parameters_dict: dict,
    upc_lookup: dict = None,
) -> tuple[bool, str, list[str]]:
    """Convert EDI to target format.
    
    Args:
        edi_process: EDI processing context dict
        output_filename: Target output file path
        settings_dict: Global application settings
        parameters_dict: Converter-specific parameters
        upc_lookup: Optional UPC lookup table
    
    Returns:
        Tuple of (success, output_path, errors)
    """
```

### 2.2 Registration

```python
# dispatch/converters/registry.py
BUILTIN_CONVERTERS = {
    'scannerware': 'dispatch.converters.convert_to_scannerware',
    'csv': 'dispatch.converters.convert_to_csv',
    # ... more formats
}
```

## 3. Configuration Plugins

### 3.1 ConfigurationPlugin Interface

```python
# interface/plugins/interfaces.py
class ConfigurationPlugin(Protocol):
    @property
    def name(self) -> str:
        """Plugin display name."""
    
    @property
    def format(self) -> str:
        """Format identifier."""
    
    def get_sections(self) -> List[ConfigSection]:
        """Get configuration sections."""
    
    def validate(self, values: dict) -> ValidationResult:
        """Validate configuration values."""
    
    def to_plugin_config(self, values: dict) -> str:
        """Serialize to plugin config format."""
    
    def from_plugin_config(self, config: str) -> dict:
        """Deserialize from plugin config format."""
```

### 3.2 ConfigSection Structure

```python
@dataclass
class ConfigSection:
    title: str
    fields: List[ConfigField]

@dataclass
class ConfigField:
    key: str
    label: str
    field_type: str  # 'text', 'checkbox', 'select', etc.
    default: Any
    required: bool = False
    options: List[str] = None  # For select fields
```

## 4. Backend Plugins

### 4.1 Backend Interface

```python
# backend/backend_base.py
def do(
    process_parameters: dict,
    settings_dict: dict,
    filename: str,
    disable_retry: bool = False,
) -> bool:
    """Send file via backend.
    
    Returns:
        True if successful
    """
```

### 4.2 Backend Registration

```python
# dispatch/send_manager.py - BackendFactory
BACKENDS = {
    'email': backend.email_backend,
    'ftp': backend.ftp_backend,
    'copy': backend.copy_backend,
    'http': backend.http_backend,
}
```

## 5. Adding a New Plugin

### Converter Plugin

1. Create module at `dispatch/converters/convert_to_<name>.py`
2. Implement `edi_convert()` function
3. Register in `registry.py`
4. Add tests

### Configuration Plugin

1. Create plugin at `interface/plugins/<name>_configuration_plugin.py`
2. Implement `ConfigurationPlugin` protocol
3. Register in `section_registry.py`
4. Add form generator tests

## 6. Related Documents

- [CONVERTER_ARCHITECTURE.md](CONVERTER_ARCHITECTURE.md) - Converter design
- [BACKEND_ARCHITECTURE.md](BACKEND_ARCHITECTURE.md) - Backend design
