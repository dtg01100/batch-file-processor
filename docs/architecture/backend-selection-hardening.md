# Convert Backend Selection Hardening

This document details the fail-fast protections for EDI format conversion backends and provides guidance for agents working with this system.

## Philosophy

**Fail-fast is preferred over silent fallback.** An incorrect format should cause the run to fail rather than:
- Send the file in the wrong format
- Pass through unchanged without conversion
- Silently default to a different format

## Architecture Overview

The convert backend selection flow:

1. **User Selection**: User picks a format from UI dropdown (populated by `ConfigurationPlugin` classes)
2. **Storage**: Format stored in folder's `convert_to_format` database field
3. **Normalization**: Format normalized to module-friendly token (e.g., "CSV" → "csv")
4. **Validation**: Format checked against `SUPPORTED_FORMATS` whitelist
5. **Loading**: Dynamic import of `dispatch.converters.convert_to_{format}`
6. **Execution**: Module's `edi_convert()` function called
7. **Output verification**: If conversion requested but no output, error is raised

## Current Protections

### 1. Whitelist Validation

**Location**: `dispatch/pipeline/converter.py:48-60`

```python
SUPPORTED_FORMATS = [
    "csv",
    "estore_einvoice",
    "estore_einvoice_generic",
    "fintech",
    "jolley_custom",
    "scannerware",
    "scansheet_type_a",
    "simplified_csv",
    "stewarts_custom",
    "tweaks",
    "yellowdog_csv",
]
```

If a format is not in this list, the converter returns a failure result with an "Unsupported conversion format" error.

### 2. Module Interface Check

**Location**: `dispatch/pipeline/converter.py:469-487`

After loading the module, the system verifies that `edi_convert` function exists:

```python
if not hasattr(module, "edi_convert"):
    error_msg = f"Module {module_name} does not have edi_convert function"
    # ... error handling
```

### 3. No-Output Detection

**Location**: `dispatch/orchestrator.py:1063-1068`

If conversion was requested but the converter returns no output, a clear error is raised:

```python
elif str(convert_format).strip():
    raise RuntimeError(
        "Conversion was requested for "
        f"format '{convert_format}' but no converted output "
        "was produced"
    )
```

### 4. Plugin-Based UI Population

**Location**: `interface/plugins/plugin_manager.py`

The UI dropdown only shows formats that have registered `ConfigurationPlugin` classes. This prevents users from selecting arbitrary format names.

## Edge Cases and Agent Guidance

### Adding New Converters

When creating a new converter backend:

1. Add the format token to `SUPPORTED_FORMATS` in `dispatch/pipeline/converter.py`
2. Register a `ConfigurationPlugin` class for the format
3. Create the `convert_to_{format}.py` module with an `edi_convert` function

**Never** add runtime fallback logic to route to a different format when the requested one is unavailable.

### Database Migrations

When migrating legacy data:

- Validate `convert_to_format` values against `SUPPORTED_FORMATS`
- Unknown values should be cleared (set to "") rather than mapped to a default
- Log warnings for any values that cannot be preserved

### Legacy Data Handling

When processing folder configurations with legacy `convert_to_format` values:

| Value | Behavior |
|-------|----------|
| Empty string / None | No conversion performed |
| Whitelisted format | Normal conversion |
| Unknown format | Fail with clear error message |

**Never** silently convert unknown format to "csv" or any other default.

### UI Layer

- Only populate format dropdowns from `PluginManager.get_configuration_plugins()`
- Never hardcode format names in UI code
- The normalization function handles display-name to token mapping

## Testing Recommendations

When modifying convert backend selection logic, test these scenarios:

1. **Valid format**: Conversion proceeds normally
2. **Empty format**: No conversion, file passes through unchanged
3. **Unknown format**: Fails with clear error message
4. **Whitespace in format**: Should be normalized, not rejected
5. **Case variations**: Should be normalized (e.g., "CSV" → "csv")
6. **Module missing**: Fails with "does not have edi_convert function" error
7. **Module throws exception**: Fails with conversion error, not silent pass-through
8. **No output produced**: Fails with "no converted output was produced" error

## Key Files

| File | Purpose |
|------|---------|
| `dispatch/pipeline/converter.py` | Main conversion logic, whitelist validation |
| `dispatch/orchestrator.py` | Pipeline orchestration, no-output detection |
| `interface/plugins/plugin_manager.py` | Plugin registration, format name resolution |
| `interface/qt/dialogs/edit_folders/dynamic_edi_builder.py` | UI format dropdown population |

## Related Documentation

- [EDI Conversion Testing Quick Reference](../testing/CONVERT_TESTING_QUICK_REFERENCE.md)
- [Plugin Architecture](../PLUGIN_ARCHITECTURE.md)