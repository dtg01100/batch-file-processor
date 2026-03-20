# Conversion and Tweaks Testing - Quick Reference

## Overview

EDI tweaking is part of the conversion pipeline - it's another conversion target, not a separate step. When `tweak_edi=True` and no `convert_to_format` is set, the converter applies tweaks directly.

## Conversion Targets

| Target | Handler | Notes |
|--------|---------|-------|
| CSV | `convert_to_csv.py` | Standard EDI to CSV |
| Fintech | `convert_to_fintech.py` | CSV/TXT format |
| Scannerware | `convert_to_scannerware.py` | TXT format |
| Scansheet Type A | `convert_to_scansheet_type_a.py` | Custom format |
| Simplified CSV | `convert_to_simplified_csv.py` | Simplified CSV |
| Yellowdog CSV | `convert_to_yellowdog_csv.py` | Vendor-specific CSV |
| Jolley Custom | `convert_to_jolley_custom.py` | Custom format |
| Stewarts Custom | `convert_to_stewarts_custom.py` | Custom format |
| eStore Invoice | `convert_to_estore_einvoice.py` | XML/Custom |
| eStore Generic | `convert_to_estore_einvoice_generic.py` | XML/Custom |
| **EDI Tweaks** | `edi_tweaks.py` | In-place modifications via `EDIConverterStep._apply_tweak()` |

**Total: 11 conversion targets** (10 formats + EDI tweaks)

## All 11 Conversion Targets Requiring Tests

| Backend | File | Format | Complexity | Estimated Tests |
|---------|------|--------|------------|-----------------|
| CSV | `convert_to_csv.py` | CSV | Medium | 5-8 |
| Fintech | `convert_to_fintech.py` | CSV/TXT | Medium | 4-6 |
| Scannerware | `convert_to_scannerware.py` | TXT | High | 6-8 |
| Scansheet Type A | `convert_to_scansheet_type_a.py` | Custom | High | 6-8 |
| Simplified CSV | `convert_to_simplified_csv.py` | CSV | Medium | 4-6 |
| Yellowdog CSV | `convert_to_yellowdog_csv.py` | CSV | Low | 3-4 |
| Jolley Custom | `convert_to_jolley_custom.py` | Custom | High | 5-7 |
| Stewarts Custom | `convert_to_stewarts_custom.py` | Custom | High | 5-7 |
| eStore Invoice | `convert_to_estore_einvoice.py` | XML/Custom | Very High | 8-10 |
| eStore Generic | `convert_to_estore_einvoice_generic.py` | XML/Custom | Very High | 8-10 |
| **EDI Tweaks** | `EDIConverterStep._apply_tweak()` | EDI in-place | Medium | 6-8 |

**Total: 60-80 tests for full coverage**

---

## EDI Tweaks Testing

EDI tweaks are applied via `EDIConverterStep._apply_tweak()` when `tweak_edi=True` and no `convert_to_format` is set. Tweaks modify EDI content in-place without format conversion.

### Tweak Settings

| Setting | Purpose |
|---------|---------|
| `tweak_edi` | Enable EDI tweaks |
| `pad_a_records` | Pad A record cust_vendor field |
| `a_record_padding` | Padding string (e.g., "test") |
| `a_record_padding_length` | Target width for padding |
| `calculate_upc_check_digit` | Add check digit to 11-char UPCs |
| `override_upc_bool` | Replace UPC from AS400 lookup |
| `override_upc_level` | UPC lookup column index (0-based) |
| `override_upc_category_filter` | Filter by category (empty or "ALL" = no filter) |
| `upc_target_length` | Target UPC length (11, 12, or 13) |
| `upc_padding_pattern` | Character for UPC padding (default: space) |

### UPC Length Handling

| Input | Target | Action |
|-------|--------|--------|
| 11 chars | 12 or 13 | Add check digit, then pad if needed |
| 12 chars | 13 | Pad with `upc_padding_pattern[0]` |
| 12 chars | 12 | Valid as-is |
| 13 chars | 13 | Valid as-is |
| 8 chars (UPC-E) | Any | Convert to UPCA first |

### Real-World Test Run

```bash
# Clear processed files
sqlite3 ~/.local/share/"Batch File Sender"/folders.db "DELETE FROM processed_files;"

# Clear output
rm -rf outdir/*

# Run with debug
DEBUG=1 python -c "
from interface.qt.app import QtBatchFileSenderApp
from core.constants import CURRENT_DATABASE_VERSION
app = QtBatchFileSenderApp(appname='Batch File Sender', version='(Git Branch: Master)', database_version=CURRENT_DATABASE_VERSION)
app.initialize()
app._args = type('Args', (), {'automatic': True, 'graphical_automatic': False})()
app._automatic_process_directories(app._database.folders_table)
app.shutdown()
"

# Verify output
md5sum test_edi/202001.001 outdir/202001.001
head -2 outdir/202001.001
```

### Check Tweak Settings

```python
folders = list(app._database.folders_table.find(id=<folder_id>))
if folders:
    folder = folders[0]
    print('tweak_edi:', folder.get('tweak_edi'))
    print('pad_a_records:', folder.get('pad_a_records'))
    print('calculate_upc_check_digit:', folder.get('calculate_upc_check_digit'))
    print('override_upc_bool:', folder.get('override_upc_bool'))
    print('override_upc_level:', folder.get('override_upc_level'))
    print('upc_target_length:', folder.get('upc_target_length'))
    print('upc_padding_pattern:', repr(folder.get('upc_padding_pattern')))
```

---

## What Each Converter Needs

### 1. **Sample EDI Input Files**
```
✓ Basic valid EDI (A, B, C records)
✓ Multi-invoice EDI
✓ Edge cases (negative amounts, long descriptions)
✓ Malformed/invalid records
```

### 2. **Parameter Testing**
```
✓ Each converter has unique parameters
✓ Test enabled/disabled for boolean flags
✓ Test different values for config parameters
✓ Parameter matrix combinations
```

### 3. **Output Validation**
```
✓ File creation
✓ Format correctness (CSV, TXT, XML)
✓ Encoding (UTF-8, ASCII, binary)
✓ Line terminators (CRLF, LF)
✓ Field delimiters and quoting
```

### 4. **Data Accuracy**
```
✓ Record type preservation
✓ Field mapping correctness
✓ Data transformations (dates, prices)
✓ UPC lookups and check digits
✓ Truncation/padding rules
```

### 5. **Error Handling**
```
✓ Empty files
✓ Malformed records
✓ Missing fields
✓ Invalid data types
✓ Character encoding issues
```

---

## Effort Breakdown

| Phase | Scope | Time | Difficulty |
|-------|-------|------|-----------|
| **Phase 1: Setup** | Infrastructure & fixtures | 4 hours | Easy |
| **Phase 2: Smoke Tests** | Basic validation for all 10 | 8 hours | Easy |
| **Phase 3: Core Tests** | Top 3 converters, deep tests | 12 hours | Medium |
| **Phase 4: Complete** | All 10 backends, comprehensive | 16 hours | Medium |
| **TOTAL** | Full coverage | **40 hours** | Medium |

---

## Quick Win Approach (Start Small)

### Minimum Viable Testing (8 hours)
✅ Can be done immediately
```
1. Create sample EDI fixtures (1 hour)
2. Write smoke test for each converter (3 hours)
3. Write 1-2 format tests per converter (4 hours)

Result: 30-40 basic tests covering all 10 backends
```

### Recommended Starting Point (24 hours)
✅ Good balance of coverage vs effort
```
1. Infrastructure & fixtures (4 hours)
2. Smoke tests for all 10 (6 hours)
3. Deep tests for top 3 most-used backends (14 hours)

Result: 60-80 tests with solid coverage where it matters most
```

### Full Production Coverage (40+ hours)
✅ For critical reliability
```
1. All phases complete
2. Parameter matrix testing
3. Edge case coverage
4. Performance benchmarks

Result: 70+ tests per backend, comprehensive coverage
```

---

## Key Testing Patterns

### Test Structure
```python
@pytest.mark.convert_backend
@pytest.mark.unit
class TestConvertToCSV:
    def test_basic_conversion(self, temp_dir, sample_edi_file, parameters_dict):
        # Test basic conversion works
        
    def test_output_format(self, temp_dir, sample_edi_file):
        # Test output file format is correct
        
    @pytest.mark.parametrize("param_value", [True, False, "special"])
    def test_parameters(self, temp_dir, sample_edi_file, param_value):
        # Test parameter variations
```

### Fixtures Needed
```python
@pytest.fixture
def sample_edi_file(temp_dir):
    """Create a valid sample EDI file"""
    
@pytest.fixture
def parameters_dict():
    """Return default parameters for converter"""
    
@pytest.fixture
def settings_dict():
    """Return backend settings (DB connection, etc.)"""
    
@pytest.fixture
def upc_lookup():
    """Return mock UPC database"""
```

---

## Implementation Command

Ready to implement Phase 1 + 2 (basic infrastructure and smoke tests)?

```bash
pytest tests/convert_backends/ -v -m convert_backend
```

This would give you baseline tests for all 10 converters to catch regressions.

---

## Current Status

| Item | Status |
|------|--------|
| 10 Converters Identified | ✅ |
| Testing Strategy Defined | ✅ |
| Sample EDI Fixtures | ⏳ (needed) |
| Test Infrastructure | ⏳ (needed) |
| Smoke Tests | ⏳ (needed) |
| Parameter Tests | ⏳ (needed) |
| Full Coverage | ⏳ (Phase 4) |

---

See [CONVERT_TO_TESTING_PLAN.md](CONVERT_TO_TESTING_PLAN.md) for detailed analysis.
