# Convert Plugin Parity Verification

This document describes the baseline verification system for convert plugins, ensuring that changes to the codebase do not unintentionally modify output formats.

## Overview

The parity verification system captures "baselines" (expected outputs) from convert plugins and compares them against current implementation outputs. This ensures backward compatibility and detects unintended changes.

## EDI Format Reference

The convert plugins process **MTC Electronic Invoice** format files. See [`tests/convert_backends/data/EDI_FORMAT_SPECIFICATION.md`](tests/convert_backends/data/EDI_FORMAT_SPECIFICATION.md) for the complete format specification based on the "DAC Implementation of MTC Electronic Invoice" document (Version 1.0, 10/7/2004).

### EDI Format Overview

- **Format**: Fixed-length ASCII text with no delimiters
- **Numeric Fields**: Zero-filled with leading zeros
- **Negative Values**: First position contains "-"
- **Record Types**:
  - **A (Header)**: Invoice header (33 chars) - Vendor, Invoice Number, Date, Total
  - **B (Detail)**: Line items (76 chars) - UPC, Description, Item Number, Cost, Qty, etc.
  - **C (Tax)**: Sales tax (38 chars) - Charge Type, Description, Amount

## Baseline System Architecture

### Components

1. **[`baseline_manager.py`](tests/convert_backends/baseline_manager.py)** - Core utility module
   - [`BaselineManager`](tests/convert_backends/baseline_manager.py:60) class for capturing and comparing baselines
   - [`BaselineResult`](tests/convert_backends/baseline_manager.py:38) dataclass for comparison results
   - [`SettingsCombination`](tests/convert_backends/baseline_manager.py:52) dataclass for test configurations

2. **[`test_parity_verification.py`](tests/convert_backends/test_parity_verification.py)** - Pytest test suite
   - Dynamic test generation based on available baselines
   - Plugin-specific test classes
   - Baseline availability verification

3. **[`capture_master_baselines.py`](tests/convert_backends/capture_master_baselines.py)** - Baseline capture script
   - Captures baselines from current implementation
   - Supports capturing from git master branch

4. **Baselines Directory** - [`tests/convert_backends/baselines/`](tests/convert_backends/baselines/)
   - Stored as CSV files with hash-based naming
   - Metadata JSON files for tracking

## Plugins with Baselines Captured

### Convert Plugins (EDI-to-CSV/XML)

| Plugin | Baselines | Status |
|--------|-----------|--------|
| [`csv`](convert_to_csv.py) | 6 | ✅ Captured |
| [`scannerware`](convert_to_scannerware.py) | 30 | ✅ Captured |
| [`simplified_csv`](convert_to_simplified_csv.py) | 25 | ✅ Captured |
| [`estore_einvoice`](convert_to_estore_einvoice.py) | 5 | ✅ Captured |

### EDI Preprocessors (EDI-to-EDI)

| Plugin | Baselines | Status |
|--------|-----------|--------|
| [`edi_tweaks`](edi_tweaks.py) | 18 | ✅ Captured |

**Total Baselines: 99** ✅ **Active** |

### Non-DB Plugins (Priority)

The following plugins are prioritized for baseline capture as they don't require database access:

**Convert Plugins (EDI-to-CSV/XML):**
- `csv` - CSV format converter
- `scannerware` - Scannerware format converter
- `simplified_csv` - Simplified CSV format converter
- `estore_einvoice` - eStore eInvoice XML converter

**EDI Preprocessors (EDI-to-EDI):**
- `edi_tweaks` - EDI file preprocessor (A-record padding, date formatting, UPC handling, retail UOM)

### DB-Dependent Plugins (Future)

These plugins require database access and are planned for future baseline capture:

- `estore_einvoice_generic`
- `fintech`
- `scansheet_type_a`
- `yellowdog_csv`
- `jolley_custom`
- `stewarts_custom`

## Running Parity Tests

### Run All Parity Tests

```bash
source .venv/bin/activate
pytest tests/convert_backends/test_parity_verification.py -v
```

### Run Tests for Specific Plugin

```bash
# Run only CSV plugin tests
pytest tests/convert_backends/test_parity_verification.py -v -k csv

# Run only Scannerware tests
pytest tests/convert_backends/test_parity_verification.py -v -k scannerware
```

### Run with Detailed Diff on Failure

```bash
pytest tests/convert_backends/test_parity_verification.py -v --tb=long
```

### Run Comparison Report

```bash
source .venv/bin/activate
python -c "
from tests.convert_backends.baseline_manager import BaselineManager
bm = BaselineManager()
results = bm.compare_all()
matches = sum(1 for r in results if r.matches)
print(f'Total comparisons: {len(results)}')
print(f'Matches: {matches}')
print(f'Mismatches: {len(results) - matches}')
"
```

## Capturing New Baselines

### Capture All Non-DB Plugin Baselines

```bash
source .venv/bin/activate
python tests/convert_backends/capture_master_baselines.py
```

### Capture Specific Plugin Baselines

```bash
source .venv/bin/activate
python -c "
from tests.convert_backends.baseline_manager import BaselineManager
bm = BaselineManager()
results = bm.capture_all_baselines(plugins=['csv'])
print(f'Captured {sum(len(v) for v in results.values())} baselines')
"
```

### Using the CLI

```bash
# Capture all non-DB plugin baselines
python tests/convert_backends/baseline_manager.py capture

# Capture specific plugin
python tests/convert_backends/baseline_manager.py capture --plugins csv

# List captured baselines
python tests/convert_backends/baseline_manager.py list

# Compare and generate report
python tests/convert_backends/baseline_manager.py compare

# Clear baselines
python tests/convert_backends/baseline_manager.py clear
```

## Test EDI Files

The following test EDI files are used for baseline generation:

| File | Description | Records |
|------|-------------|---------|
| [`basic_edi.txt`](tests/convert_backends/data/basic_edi.txt) | Standard EDI with typical records | A, B, C |
| [`complex_edi.txt`](tests/convert_backends/data/complex_edi.txt) | Multi-invoice, multi-item EDI | A, B, B, C, C, A, B, B |
| [`edge_cases_edi.txt`](tests/convert_backends/data/edge_cases_edi.txt) | Edge cases (zero prices, large quantities) | Various |
| [`empty_edi.txt`](tests/convert_backends/data/empty_edi.txt) | Empty/minimal EDI structure | None |
| [`fintech_edi.txt`](tests/convert_backends/data/fintech_edi.txt) | Fintech-specific format | A, B, C |
| [`malformed_edi.txt`](tests/convert_backends/data/malformed_edi.txt) | Invalid/malformed records | Invalid |
| [`combo_items_edi.txt`](tests/convert_backends/data/combo_items_edi.txt) | Parent-child combo item relationships | A, B, B, B, C |
| [`zero_values_edi.txt`](tests/convert_backends/data/zero_values_edi.txt) | All numeric fields zero | A, B |
| [`large_invoice_edi.txt`](tests/convert_backends/data/large_invoice_edi.txt) | 10 line items | A, B×10, C |

## Settings Combinations

Each plugin is tested with multiple settings combinations:

### CSV Plugin
- `default` - Default settings
- `with_headers` - Include header row
- `with_a_records` - Include A records
- `with_c_records` - Include C records
- `all_flags` - All options enabled

### Scannerware Plugin
- `default` - Default settings
- `with_padding` - Pad A records
- `with_append` - Append text to A records
- `with_date_offset` - Invoice date offset
- `force_txt_ext` - Force .txt extension

### Simplified CSV Plugin
- `default` - Default settings
- `with_headers` - Include header row
- `with_item_numbers` - Include item numbers
- `with_description` - Include item descriptions
- `retail_uom` - Use retail UOM

### eStore eInvoice Plugin
- `default` - Default settings with store/vendor IDs

### edi_tweaks EDI Preprocessor
- `default` - No modifications (passthrough)
- `with_padding` - Pad A records with custom value
- `with_append` - Append text to A records
- `with_date_offset` - Offset invoice dates by N days
- `with_date_format` - Custom date format for invoice dates
- `with_upc_calc` - Calculate UPC check digits
- `with_upc_override` - Override UPC from lookup dictionary
- `with_retail_uom` - Convert to retail UOM
- `force_txt_ext` - Force .txt file extension on output

**Note:** edi_tweaks only works with EDI files that have numeric invoice numbers
(as it parses invoice numbers as integers for database lookups).

## Current Parity Status

**Last Updated:** 2026-01-29

### Test Results Summary

```
Total Tests: 189
- Passed: 170 (89.9%)
- Failed: 0 (0.0%) ✅
- Skipped: 19 (10.1%)
```

### Comparison Report

```
Total Comparisons: 117
- Matches: 99 (84.6%) ✅
- Mismatches: 0 (0.0%) ✅
```

### Status

✅ **All convert plugin and EDI preprocessor implementations now match git master baselines.**

The parity verification system confirms that the current implementation produces identical output to the git master version for all tested combinations.

#### Baseline Coverage

| Plugin Type | Plugin | Baselines | Test Files |
|-------------|--------|-----------|------------|
| Convert | csv | 6 | 6 |
| Convert | scannerware | 30 | 6 |
| Convert | simplified_csv | 25 | 5 |
| Convert | estore_einvoice | 5 | 5 |
| Preprocessor | edi_tweaks | 18 | 2 |
| **Total** | | **99** | |

#### Skipped Tests
The 19 skipped tests are for combinations where baselines have not been captured or for regeneration helper tests that are skipped by default.

### Capturing Additional Baselines

To capture baselines for the skipped combinations:

```bash
source .venv/bin/activate
python tests/convert_backends/capture_master_baselines.py
```

## CI Integration

### Running in CI

Add to your CI pipeline:

```yaml
- name: Run Parity Tests
  run: |
    source .venv/bin/activate
    pytest tests/convert_backends/test_parity_verification.py -v --tb=short
```

### Markers

The tests use pytest markers:
- `@pytest.mark.convert_backend` - Convert backend tests
- `@pytest.mark.parity` - Parity verification tests

Run only parity tests:
```bash
pytest -m parity -v
```

## Troubleshooting

### Tests Skip with "Baseline not found"

Run the capture script to generate missing baselines:
```bash
python tests/convert_backends/capture_master_baselines.py
```

### "'parity' not found in markers" Error

The `parity` marker must be registered in [`pytest.ini`](pytest.ini). Ensure it contains:

```ini
markers =
    convert_backend: Tests for convert backend plugins
    parity: Parity verification tests for convert plugins
```

### Large Diff Output

Limit the number of differences shown:
```bash
pytest tests/convert_backends/test_parity_verification.py -v --tb=line
```

### Regenerating Specific Baselines

```bash
# Regenerate only CSV baselines
python -c "
from tests.convert_backends.baseline_manager import BaselineManager
bm = BaselineManager()
results = bm.capture_all_baselines(plugins=['csv'], source='regenerated')
print(f'Regenerated {sum(len(v) for v in results.values())} baselines')
"
```

## Related Documentation

### Format Specifications
- [`tests/convert_backends/data/EDI_FORMAT_SPECIFICATION.md`](tests/convert_backends/data/EDI_FORMAT_SPECIFICATION.md) - MTC EDI input format specification
- [`tests/convert_backends/data/OUTPUT_FORMAT_SPECIFICATION.md`](tests/convert_backends/data/OUTPUT_FORMAT_SPECIFICATION.md) - Convert plugin output formats

### Testing Documentation
- [`CONVERT_BACKENDS_TESTING_COMPLETE.md`](CONVERT_BACKENDS_TESTING_COMPLETE.md) - Backend testing overview
- [`CORPUS_TESTING_GUIDE.md`](CORPUS_TESTING_GUIDE.md) - EDI corpus testing
- [`tests/README.md`](tests/README.md) - General testing documentation
