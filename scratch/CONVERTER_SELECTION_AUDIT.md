# Converter Selection Audit

**Date:** 2026-04-28  
**Status:** COMPLETE

## Summary

Converter selection logic has been analyzed. Current implementation uses a clean, consistent pattern that normalizes format names before module lookup.

## Converter Selection Mechanism

### Current Implementation

**Location:** `dispatch/pipeline/converter.py` → `EDIConverterStep._prepare_conversion()`

```python
module_name = f"dispatch.converters.convert_to_{convert_to_format}"
```

**Normalization:** `core/utils/format_utils.py` → `normalize_convert_to_format()`

```python
def normalize_convert_to_format(value: Any) -> str:
    """Normalize convert_to_format into a predictable module-friendly token."""
    if value is None:
        return ""
    normalized = str(value).strip().lower().replace(" ", "_").replace("-", "_")
    normalized = re.sub(r"[^a-z0-9_]", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized
```

### Conversion Examples

| User Input Format | Normalized | Module Loaded |
|-------------------|------------|---------------|
| `"scannerware"` | `scannerware` | `convert_to_scannerware.py` |
| `"ScannerWare"` | `scannerware` | `convert_to_scannerware.py` |
| `"Scannerware"` | `scannerware` | `convert_to_scannerware.py` |
| `"SCANNERWARE"` | `scannerware` | `convert_to_scannerware.py` |
| `"tweaks"` | `tweaks` | `convert_to_tweaks.py` |
| `"Tweaks"` | `tweaks` | `convert_to_tweaks.py` |
| `"  Tweaks  "` | `tweaks` | `convert_to_tweaks.py` |
| `"Estore eInvoice"` | `estore_einvoice` | `convert_to_estore_einvoice.py` |
| `"Estore_einvoice"` | `estore_einvoice` | `convert_to_estore_einvoice.py` |

### Auto-Discovery of Formats

**Location:** `dispatch/pipeline/converter.py` → `_discover_supported_formats()`

Formats are auto-discovered at module load time by scanning `dispatch/converters/` for modules matching `convert_to_*` pattern:

```python
def _discover_supported_formats() -> list[str]:
    formats = []
    converter_path = os.path.join(os.path.dirname(__file__), "..", "converters")
    for _, module_name, is_pkg in pkgutil.iter_modules([converter_path]):
        if module_name.startswith("convert_to_") and not is_pkg:
            format_name = module_name.replace("convert_to_", "")
            formats.append(format_name)
    return sorted(formats)
```

### Current Supported Formats

| Format | Module | Status |
|--------|--------|--------|
| csv | `convert_to_csv.py` | Listed in spec |
| estore_einvoice | `convert_to_estore_einvoice.py` | Listed in spec |
| estore_einvoice_generic | `convert_to_estore_einvoice_generic.py` | Listed in spec |
| fintech | `convert_to_fintech.py` | Listed in spec |
| jolley_custom | `convert_to_jolley_custom.py` | Listed in spec |
| scannerware | `convert_to_scannerware.py` | Listed in spec |
| scansheet_type_a | `convert_to_scansheet_type_a.py` | Listed in spec |
| simplified_csv | `convert_to_simplified_csv.py` | Listed in spec |
| stewarts_custom | `convert_to_stewarts_custom.py` | Listed in spec |
| tweaks | `convert_to_tweaks.py` | Listed in spec |
| yellowdog_csv | `convert_to_yellowdog_csv.py` | Listed in spec |

## Spec File Compliance

**File:** `main_interface.spec`

All 11 converter modules are explicitly listed in `hiddenimports`:
- ✓ `dispatch.converters.convert_to_csv`
- ✓ `dispatch.converters.convert_to_estore_einvoice`
- ✓ `dispatch.converters.convert_to_estore_einvoice_generic`
- ✓ `dispatch.converters.convert_to_fintech`
- ✓ `dispatch.converters.convert_to_jolley_custom`
- ✓ `dispatch.converters.convert_to_scannerware`
- ✓ `dispatch.converters.convert_to_scansheet_type_a`
- ✓ `dispatch.converters.convert_to_simplified_csv`
- ✓ `dispatch.converters.convert_to_stewarts_custom`
- ✓ `dispatch.converters.convert_to_tweaks`
- ✓ `dispatch.converters.convert_to_yellowdog_csv`

## EDI Tweaks Conversion Status

**Location:** `dispatch/converters/convert_to_tweaks.py`

The `tweaks` format is implemented as a proper converter plugin:
- ✓ Has `edi_convert()` function at module level
- ✓ Extends `BaseEDIConverter` class
- ✓ Uses `EDITweaker` for transformations
- ✓ Listed in spec file
- ✓ Auto-discovered via `_discover_supported_formats()`

## Key Findings

1. **Normalization is Applied Consistently**: All format names are normalized to lowercase with underscores before module lookup.

2. **Case Insensitivity**: The original concern about "ScannerWare" vs "Scannerware" is handled - both normalize to `scannerware`.

3. **No Format Aliases Found**: No alias resolution (like "edi" -> "810") was found in the current codebase. This may be a difference from the original if such aliases existed.

4. **Auto-Discovery Works**: `pkgutil.iter_modules` automatically finds all converter modules at startup.

5. **tweaks Format Fully Supported**: The tweaks converter is properly integrated as a first-class format.

## Recommendations

1. **Verify Format Aliases**: If the original had format aliases (e.g., "edi" -> "810"), verify this functionality is preserved elsewhere or document that it was removed.

2. **Consider Case-Sensitive Lookup Option**: If original behavior required exact case matching, current implementation deviates. However, current behavior (case-insensitive) is likely more user-friendly.

3. **All Converters Listed in Spec**: Good - no dynamic import issues for PyInstaller.

## Conclusion

Converter selection logic is **consistent and well-implemented**. The normalization approach is clean and handles case variations properly. The `tweaks` format is fully supported as a first-class conversion target.
