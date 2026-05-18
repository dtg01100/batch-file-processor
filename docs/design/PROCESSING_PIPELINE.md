# Processing Pipeline Design Document

**Version:** 1.0  
**Date:** 2026-05-18  
**Status:** DRAFT

---

## 1. Overview

The processing pipeline transforms input EDI files through a series of configurable stages before sending to backends.

## 2. Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Input File                                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           VALIDATOR STEP                                    │
│  - Verify EDI format structure                                              │
│  - Check required segments (ISA, GS, ST, etc.)                              │
│  - Validate segment syntax                                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼ (pass) or Error
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SPLITTER STEP                                     │
│  - Split multi-transaction EDI into individual transactions                 │
│  - Create separate output files per transaction                             │
│  - Skip if splitting disabled                                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼ (pass) or Error
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CONVERTER STEP                                      │
│  - Transform EDI to target format (including EDI "tweaks" as a converter)   │
│  - Format: scannerware, csv, estore_einvoice, fintech, etc.                 │
│  - Format: tweaks (applies EDI field modifications via convert_to_tweaks)   │
│  - Apply format-specific transformations                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼ (pass) or Error
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SEND MANAGER                                        │
│  - Dispatch to configured backends (FTP, Email, Copy, HTTP)                 │
│  - Handle backend failures with retry logic                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       DATABASE TRACKING                                      │
│  - Record processed file with hash and timestamp                             │
│  - Prevent duplicate processing                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 3. Pipeline Step Interface

All pipeline steps implement the `PipelineStep` protocol:

```python
# dispatch/pipeline/interfaces.py
class PipelineStep(Protocol):
    def execute(self, input_path: str, context: dict) -> tuple[bool, str, list[str]]:
        """Execute the pipeline step.
        
        Returns:
            Tuple of (success, output_path, errors)
        """
        ...
```

## 4. Step Implementations

### 4.1 Validator Step

**Module:** `dispatch/pipeline/validator.py`

```python
class ValidatorStep(PipelineStep):
    def __init__(self, validator: EDIValidator):
        self._validator = validator
    
    def execute(self, input_path: str, context: dict) -> tuple[bool, str, list]:
        """Validate EDI file format."""
        result = self._validator.validate(input_path)
        if not result.is_valid:
            return (False, input_path, result.errors)
        return (True, input_path, [])
```

### 4.2 Splitter Step

**Module:** `dispatch/pipeline/splitter.py`

```python
class SplitterStep(PipelineStep):
    def __init__(self, splitting_enabled: bool):
        self._splitting_enabled = splitting_enabled
    
    def execute(self, input_path: str, context: dict) -> tuple[bool, str, list]:
        """Split EDI file into transactions."""
        if not self._splitting_enabled:
            return (True, input_path, [])
        
        transactions = split_edi_file(input_path)
        output_paths = write_transactions(transactions)
        return (True, output_paths[0] if output_paths else input_path, [])
```

### 4.3 Converter Step

**Module:** `dispatch/pipeline/converter.py`

The converter step is a single pipeline step that dynamically loads the appropriate converter module
based on the `convert_to_format` folder setting. One of the available formats is `"tweaks"` — this is
**not** a separate `TweakerStep`; it is loaded into the same `ConverterStep` at runtime.

```python
# dispatch/pipeline/converter.py
class ConverterStep(PipelineStep):
    def __init__(self, converter_registry: ConverterRegistry):
        self._registry = converter_registry

    def execute(self, input_path: str, context: dict) -> tuple[bool, str, list]:
        """Convert EDI to target format."""
        format_name = context.get('format', 'csv')
        converter = self._registry.get(format_name)
        success, output_path, errors = converter.convert(input_path, context)
        return (success, output_path, errors)
```

#### 4.3.1 The "tweaks" Converter Format

EDI tweaking is exposed as the `"tweaks"` format in `dispatch/converters/convert_to_tweaks.py`.
When `convert_to_format = "tweaks"` the `ConverterStep` loads this module; there is **no** standalone
`TweakerStep` class.

```python
# dispatch/converters/convert_to_tweaks.py
CONVERTER_METADATA = {
    "format_name": "tweaks",
    "display_name": "tweaks",
    "description": "Apply EDI tweaks to EDI file",
    # Delegates to EDITweaker from core.edi.edi_tweaker
}
```

The `dispatch/pipeline/tweaker.py` module does **not** exist in the codebase.

#### 4.3.2 Supported Formats (Non-exhaustive)

The `ConverterRegistry` discovers all format converters via `dispatch/converters/registry.py`:

| Format | Converter Module |
|--------|-----------------|
| `csv` | `convert_to_csv.py` |
| `simplified_csv` | `convert_to_simplified_csv.py` |
| `scannerware` | `convert_to_scannerware.py` |
| `estore_einvoice` | `convert_to_estore_einvoice.py` |
| `estore_einvoice_generic` | `convert_to_estore_einvoice_generic.py` |
| `fintech` | `convert_to_fintech.py` |
| `jolley_custom` | `convert_to_jolley_custom.py` |
| `stewarts_custom` | `convert_to_stewarts_custom.py` |
| `yellowdog_csv` | `convert_to_yellowdog_csv.py` |
| `scansheet_type_a` | `convert_to_scansheet_type_a.py` |
| **`tweaks`** | **`convert_to_tweaks.py`** (EDI field-level modifications, delegates to `EDITweaker`) |

## 5. Pipeline Execution

```python
# dispatch/services/file_processor.py
class FileProcessor:
    def __init__(self, steps: List[PipelineStep]):
        self._steps = steps
    
    def process_file(self, file_path: str, context: dict) -> ProcessingResult:
        """Execute all pipeline steps."""
        current_path = file_path
        all_errors = []
        
        for step in self._steps:
            success, output_path, errors = step.execute(current_path, context)
            if not success:
                return ProcessingResult(success=False, errors=all_errors + errors)
            current_path = output_path
            all_errors.extend(errors)
        
        return ProcessingResult(success=True, output_path=current_path, errors=[])
```

## 6. Converter Registry

**Module:** `dispatch/converters/registry.py`

```python
class ConverterRegistry:
    """Discovers and manages converter plugins."""
    
    BUILTIN_CONVERTERS = {
        'scannerware': 'dispatch.converters.convert_to_scannerware',
        'csv': 'dispatch.converters.convert_to_csv',
        'estore_einvoice': 'dispatch.converters.convert_to_estore_einvoice',
        'estore_einvoice_generic': 'dispatch.converters.convert_to_estore_einvoice_generic',
        'fintech': 'dispatch.converters.convert_to_fintech',
        'jolley_custom': 'dispatch.converters.convert_to_jolley_custom',
        'simplified_csv': 'dispatch.converters.convert_to_simplified_csv',
        'stewarts_custom': 'dispatch.converters.convert_to_stewarts_custom',
        'tweaks': 'dispatch.converters.convert_to_tweaks',
        'yellowdog_csv': 'dispatch.converters.convert_to_yellowdog_csv',
        'scansheet_type_a': 'dispatch.converters.convert_to_scansheet_type_a',
    }
```

## 7. Related Documents

- [DATA_FLOW.md](DATA_FLOW.md) - Data movement through system
- [CONVERTER_ARCHITECTURE.md](CONVERTER_ARCHITECTURE.md) - Converter plugin system
- [EDI_PROCESSING.md](EDI_PROCESSING.md) - EDI parsing details
