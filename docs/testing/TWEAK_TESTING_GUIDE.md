# EDI Tweaks and Conversion Testing Guide

## Overview

This guide covers testing the EDI tweak and conversion pipeline with real data and backends. Unlike unit tests which use mocks, this approach validates actual output against known-good configurations.

## Prerequisites

1. **Database location**: `~/.local/share/Batch File Sender/folders.db`
2. **Test EDI files**: Located in `test_edi/` directory
3. **Output directory**: `outdir/` (configurable copy destination)
4. **Settings configured**: AS400 credentials, UPC dictionary loaded from AS400

## Quick Test Run

### 1. Clear Processed Files

Before each test run, clear the processed files table to ensure all files are treated as new:

```bash
sqlite3 ~/.local/share/"Batch File Sender"/folders.db "DELETE FROM processed_files;"
```

### 2. Clear Output Directory

```bash
rm -rf outdir/*
```

### 3. Run Automatic Processing

```python
from interface.qt.app import QtBatchFileSenderApp
from core.constants import CURRENT_DATABASE_VERSION

app = QtBatchFileSenderApp(
    appname='Batch File Sender',
    version='(Git Branch: Master)',
    database_version=CURRENT_DATABASE_VERSION,
)
app.initialize()
app._args = type('Args', (), {'automatic': True, 'graphical_automatic': False})()
app._automatic_process_directories(app._database.folders_table)
app.shutdown()
```

Or from command line with debug logging:

```bash
DEBUG=1 python -c "
from interface.qt.app import QtBatchFileSenderApp
from core.constants import CURRENT_DATABASE_VERSION
app = QtBatchFileSenderApp(appname='Batch File Sender', version='(Git Branch: Master)', database_version=CURRENT_DATABASE_VERSION)
app.initialize()
app._args = type('Args', (), {'automatic': True, 'graphical_automatic': False})()
app._automatic_process_directories(app._database.folders_table)
app.shutdown()
"
```

## Verifying Output

### Compare Checksums

```bash
# Original vs output
md5sum test_edi/202001.001 outdir/202001.001

# If different, tweaks were applied
```

### View Raw Output

```bash
head -5 outdir/202001.001
```

### Check Database Records

```bash
sqlite3 ~/.local/share/"Batch File Sender"/folders.db \
  "SELECT file_name, file_checksum, status FROM processed_files LIMIT 5;"
```

## Key Tweak Settings

### Folder Configuration Check

```python
folders = list(app._database.folders_table.find(id=<folder_id>))
if folders:
    folder = folders[0]
    print('tweak_edi:', folder.get('tweak_edi'))
    print('pad_a_records:', folder.get('pad_a_records'))
    print('calculate_upc_check_digit:', folder.get('calculate_upc_check_digit'))
    print('override_upc_bool:', folder.get('override_upc_bool'))
    print('override_upc_level:', folder.get('override_upc_level'))
    print('override_upc_category_filter:', repr(folder.get('override_upc_category_filter')))
    print('upc_target_length:', folder.get('upc_target_length'))
    print('upc_padding_pattern:', repr(folder.get('upc_padding_pattern')))
```

### Setting Descriptions

| Setting | Purpose |
|---------|---------|
| `tweak_edi` | Enable EDI tweaks (A record padding, UPC override, check digit calc) |
| `pad_a_records` | Pad A record cust_vendor field to configured width |
| `calculate_upc_check_digit` | Add check digit to 11-char UPCs |
| `override_upc_bool` | Replace UPC with value from AS400 UPC lookup |
| `override_upc_level` | Which column in UPC lookup result to use (0-indexed) |
| `override_upc_category_filter` | Filter override by category (empty or "ALL" = no filter) |
| `upc_target_length` | Target UPC length (11, 12, or 13) |
| `upc_padding_pattern` | Character to pad UPCs with (default: space) |

## UPC Length Handling

The tweak pipeline handles UPCs of different lengths:

| Input Length | Target | Action |
|--------------|--------|--------|
| 11 chars | 12 or 13 | Add check digit first, then pad if needed |
| 12 chars | 13 | Pad with `upc_padding_pattern[0]` |
| 12 chars | 12 | Valid as-is |
| 13 chars | 13 | Valid as-is |
| 8 chars (UPC-E) | Any | Convert to UPCA first, then process |

### Example UPC Transformations

```
Original: 01230000007 (11 chars)
  ↓ calc_upc=True → 012300000073 (12 chars, check digit added)
  ↓ target_length=13, padding=' ' → " 012300000073" (13 chars, space-padded)

Override: 012300107136 (12 chars from AS400)
  ↓ target_length=13, padding='0' → "0012300107136" (13 chars, zero-padded)
```

## Debugging Tips

### Enable Verbose Logging

```python
import os
os.environ['DISPATCH_DEBUG_MODE'] = '1'
from core.logging_config import setup_logging, get_logger
import logging

setup_logging()
logger = get_logger('dispatch')
logger.setLevel(logging.DEBUG)
```

### Check UPC Dictionary

```python
from dispatch import DispatchConfig, DispatchOrchestrator
from dispatch.pipeline.converter import EDIConverterStep

config = DispatchConfig(
    database=app._database.folders_table,
    settings=settings_dict,
    version=app._version,
    converter_step=EDIConverterStep(),
)
orch = DispatchOrchestrator(config)
upc_dict = orch._get_upc_dictionary(settings_dict)

print(f'UPC dictionary loaded: {len(upc_dict)} entries')
print(f'Sample lookup for vendor 5790: {upc_dict.get(5790)}')
```

### Trace Tweak Application

The tweak function logs at DEBUG level:
- `Enabled tweaks: [...]` - which tweaks are active
- `override_upc` applied - UPC override was applied
- `UPC override not found for vendor item: X` - lookup failed

## Common Issues

### UPC Override Not Applied

**Symptoms**: Output UPC matches original, not overridden value

**Causes**:
1. `override_upc_category_filter` is empty but not "ALL" - fix by setting to "ALL"
2. UPC dictionary not loaded - check AS400 credentials in settings
3. Vendor item number not in UPC dictionary

**Fix in `archive/edi_tweaks.py`**:
```python
# Line ~371 - empty filter should default to ALL behavior
category_filter = override_upc_category_filter.strip()
if category_filter == "" or category_filter == "ALL":
    # Apply override to all items
```

### Check Digit Not Added

**Symptoms**: 11-char UPC remains 11 chars instead of becoming 12

**Cause**: `calc_upc=True` but target length is 13 and override provided 12-char UPC

**Note**: 12 and 13 char UPCs are considered valid and skip check digit addition. Only 11-char UPCs get check digits added.

### A Record Padding Wrong

**Symptoms**: Padded A record has incorrect width or content

**Cause**: `a_record_padding` or `a_record_padding_length` settings incorrect

## Testing Checklist

- [ ] Clear processed_files before run
- [ ] Clear output directory before run
- [ ] Verify input file checksum
- [ ] Run automatic processing
- [ ] Check output file created
- [ ] Compare input vs output checksums
- [ ] Verify specific fields were tweaked (UPC, A record, etc.)
- [ ] Check database records
- [ ] Review debug logs if issues encountered

## Related Documentation

- [EDI Format Guide](../user-guide/edi-format-guide.md)
- [Conversion Testing Quick Reference](CONVERT_TESTING_QUICK_REFERENCE.md)
- [Corpus Testing Guide](CORPUS_TESTING_GUIDE.md)
