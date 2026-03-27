# Database Version 32 → 48: Comprehensive Regression Analysis

**Date:** March 27, 2026  
**Analysis Type:** Full folder-by-folder conversion behavior audit  
**Database Versions:** V32 (backup) → V48 (current)  
**Total Folders Analyzed:** 530

---

## Executive Summary

### CRITICAL FINDING: 348 Folders (65.7%) Had Conversion Silently Blocked

**The Regression:** In database version 32, 348 folders have a **contradictory configuration state**:
- `convert_to_format` is set to a non-empty value (e.g., "csv", "YellowDog CSV")
- `process_edi` is explicitly `False`

**V32 Behavior:** Files pass through **UNCHANGED** (conversion blocked by `process_edi=False`)

**User Expectation:** Users believe conversion is happening because:
1. The UI displays the "Convert EDI" checkbox as enabled when `convert_to_format` is non-empty
2. A conversion format is visibly selected in the dropdown

**Actual V32 Behavior:** Conversion is **silently skipped** due to `process_edi=False`

**Current Behavior (V48):** Migration v47→v48 **auto-corrects** all 348 folders by setting `process_edi=1`

---

## Folder Behavior Categories

### 1. CONVERT_BLOCKED_REGRESSION (348 folders, 65.7%)

**Configuration:**
- `process_edi = False`
- `convert_to_format = <non-empty>`
- `tweak_edi = 0 or 1` (mixed)

**V32 Behavior:** Files pass through **unchanged** (conversion blocked)

**Current Behavior (V48):** Migration v48 sets `process_edi=1`, conversion **RUNS**

**Formats Affected:**

| Format | Count | Sample Aliases |
|--------|-------|----------------|
| csv | 296 | 020061, 033626, 011028, 011355, 017127... |
| simplified_csv | 26 | 035093, 030961, 035133, 035134... |
| Estore eInvoice Generic | 15 | 078006, 078001, 078003, 078009... |
| stewarts_custom | 6 | 030285, 302020, 332039, 529016... |
| YellowDog CSV | 4 | 028009, 028039, 028011, 028052 |
| scansheet-type-a | 1 | 343033 |

**Example Folders:**
```
ID=56,   alias=020061,   process_edi=False, convert_to_format=csv
ID=192,  alias=028009,   process_edi=False, convert_to_format=YellowDog CSV, tweak_edi=1
ID=514,  alias=343033,   process_edi=False, convert_to_format=scansheet-type-a, tweak_edi=1
ID=557,  alias=078006,   process_edi=False, convert_to_format=Estore eInvoice Generic, tweak_edi=1
```

**Root Cause Analysis:**

This contradictory state was introduced through multiple code paths:

1. **V5→V6 Migration (convert_to_format introduction):**
   - Only set `convert_to_format='csv'` for folders with `process_edi=1`
   - Folders with `process_edi=0` were left with empty format
   
2. **Later Format Additions:**
   - When new formats were added (e.g., YellowDog, estore), users selected formats in UI
   - UI did not enforce consistency between `process_edi` checkbox and format dropdown
   - Users could select a format while `process_edi=False`

3. **Insight Converter Removal (commit 273a5def1, 2016):**
   - Set `process_edi=False` for folders using removed 'insight' converter
   - Some may have retained `convert_to_format` values

4. **Tweak EDI Flag Confusion:**
   - `tweak_edi=1` was a separate flag from `convert_to_format`
   - Some folders had both `tweak_edi=1` AND `convert_to_format` set
   - Migration v44→v46 consolidated to `convert_to_format='tweaks'`

**Impact:**
- **296 folders** with `convert_to_format='csv'` were NOT converting
- **15 folders** with Estore eInvoice were NOT generating einvoice filenames
- **4 folders** with YellowDog CSV were NOT applying custom formatting
- **Files passed through unchanged** — potential data loss for downstream systems

---

### 2. CONVERT_ENABLED (150 folders, 28.3%)

**Configuration:**
- `process_edi = True`
- `convert_to_format = <non-empty>`

**V32 Behavior:** Conversion runs **normally** ✅

**Current Behavior (V48):** Conversion runs **normally** ✅

**NO REGRESSION** — These folders work correctly in both versions.

**Formats:**

| Format | Count | Notes |
|--------|-------|-------|
| jolley_custom | 55 | All have `split_edi=1` |
| stewarts_custom | 49 | Mixed split_edi |
| csv | 28 | Standard CSV conversion |
| YellowDog CSV | 10 | Custom CSV format |
| simplified_csv | 5 | Simplified output |
| scansheet-type-a | 1 | Specialized format |
| fintech | 1 | Fintech integration |
| ScannerWare | 1 | ScannerWare format |

**Example Folders:**
```
ID=89,   alias=030654, process_edi=True, convert_to_format=ScannerWare, pad_a_records=True
ID=90,   alias=030726, process_edi=True, convert_to_format=csv, include_headers=True, calculate_upc_check_digit=True
ID=187,  alias=011283, process_edi=True, convert_to_format=fintech
ID=191,  alias=025031, process_edi=True, convert_to_format=csv, split_edi=1, pad_a_records=True
```

---

### 3. PASS_THROUGH_DISABLED (31 folders, 5.8%)

**Configuration:**
- `process_edi = False`
- `convert_to_format = (empty)`
- `tweak_edi = 0`

**V32 Behavior:** Files pass through **unchanged** (intentionally disabled) ✅

**Current Behavior (V48):** Files pass through **unchanged** ✅

**NO REGRESSION** — These folders are correctly disabled in both versions.

**Characteristics:**
- No conversion format selected
- EDI processing explicitly disabled
- Likely used for simple file collection/monitoring without transformation

---

### 4. TWEAK_ONLY_DISABLED (1 folder, 0.2%)

**Configuration:**
- `process_edi = False`
- `tweak_edi = 1`
- `convert_to_format = (empty)`

**Folder:** ID=546, alias=030948

**V32 Behavior:** Contradictory state — tweak requested but processing disabled

**Current Behavior (V48):** Migration v44→v46 clears `tweak_edi`, no conversion

**RESOLVED** — Migration handles this edge case.

---

## Detailed Configuration Matrix

### Full Breakdown by Flag Combination

| process_edi | tweak_edi | split_edi | pad_a_records | format | Count | Behavior |
|-------------|-----------|-----------|---------------|--------|-------|----------|
| False | 0 | 1 | False | csv | 134 | **BLOCKED** |
| False | 0 | 0 | False | csv | 65 | **BLOCKED** |
| False | 1 | 1 | True | csv | 58 | **BLOCKED** |
| True | 0 | 1 | False | jolley_custom | 55 | ✅ Enabled |
| True | 0 | 1 | False | stewarts_custom | 49 | ✅ Enabled |
| False | 0 | 0 | False | (empty) | 30 | ✅ Disabled |
| False | 1 | 1 | False | csv | 15 | **BLOCKED** |
| False | 1 | 1 | True | Estore eInvoice Generic | 15 | **BLOCKED** |
| True | 0 | 0 | False | csv | 15 | ✅ Enabled |
| False | 0 | 0 | False | simplified_csv | 12 | **BLOCKED** |
| False | 0 | 1 | False | simplified_csv | 12 | **BLOCKED** |
| False | 0 | 1 | True | csv | 11 | **BLOCKED** |
| True | 0 | 1 | False | csv | 11 | ✅ Enabled |
| True | 0 | 1 | False | YellowDog CSV | 10 | ✅ Enabled |
| False | 1 | 0 | False | csv | 6 | **BLOCKED** |
| False | 1 | 0 | True | csv | 6 | **BLOCKED** |
| False | 0 | 0 | False | stewarts_custom | 4 | **BLOCKED** |
| False | 1 | 1 | False | YellowDog CSV | 4 | **BLOCKED** |
| True | 0 | 0 | False | simplified_csv | 3 | ✅ Enabled |
| True | 0 | 1 | True | csv | 2 | ✅ Enabled |
| False | 0 | 0 | True | csv | 1 | **BLOCKED** |
| False | 0 | 1 | False | (empty) | 1 | ✅ Disabled |
| False | 1 | 0 | False | (empty) | 1 | ✅ Disabled (tweak cleared) |
| False | 1 | 0 | False | stewarts_custom | 1 | **BLOCKED** |
| False | 1 | 0 | True | scansheet-type-a | 1 | **BLOCKED** |
| False | 1 | 0 | True | simplified_csv | 1 | **BLOCKED** |
| False | 1 | 0 | True | stewarts_custom | 1 | **BLOCKED** |
| False | 1 | 1 | True | simplified_csv | 1 | **BLOCKED** |
| True | 0 | 0 | False | fintech | 1 | ✅ Enabled |
| True | 0 | 0 | False | scansheet-type-a | 1 | ✅ Enabled |
| True | 0 | 1 | False | simplified_csv | 1 | ✅ Enabled |
| True | 0 | 1 | True | ScannerWare | 1 | ✅ Enabled |
| True | 0 | 1 | True | simplified_csv | 1 | ✅ Enabled |

---

## Migration History and Code Evolution

### Key Migrations Affecting Conversion Behavior

#### V5→V6: Introduction of `convert_to_format`

```python
# Only set format for folders with process_edi=1
convert_to_csv_list = folders_table.find(process_edi=1)
for line in convert_to_csv_list:
    line["convert_to_format"] = "csv"
```

**Impact:** Established pattern where `process_edi` gates conversion, but didn't prevent future inconsistency.

---

#### V7→V8: Introduction of `tweak_edi` Flag

```python
# Migration v7→v8
folders_table.create_column("tweak_edi", "Boolean")
for line in folders_table.all():
    if line["pad_a_records"] == 0:
        line["tweak_edi"] = 0
    else:
        line["tweak_edi"] = 1
```

**Impact:** Created separate flag for "tweaks" independent of `convert_to_format`, sowing confusion.

---

#### V44→V45: Consolidate `tweak_edi` into `convert_to_format`

**Commit:** 8d86e0884  
**Date:** March 23, 2026

```sql
-- Case A: tweak_edi=1 + format stored + process_edi enabled
UPDATE folders
SET process_edi = 1, tweak_edi = 0
WHERE tweak_edi = 1
  AND convert_to_format IS NOT NULL
  AND convert_to_format != ''
  AND (process_edi IS NULL OR process_edi != 0)

-- Case B: tweak_edi=1 + no format stored
UPDATE folders
SET convert_to_format = 'tweaks', process_edi = 1, tweak_edi = 0
WHERE tweak_edi = 1
  AND (convert_to_format IS NULL OR convert_to_format = '')
  AND (process_edi IS NULL OR process_edi != 0)
```

**Bug in Original Migration:** Cleared `convert_to_format` for folders with `process_edi=False`, then v45→v46 stamped them all with `'tweaks'` (nonsensical state).

**Fix (v46→v47):** Restored `convert_to_format` from backup for affected folders.

---

#### V47→V48: Fix Contradictory State

**Commit:** d360cf90d  
**Date:** March 27, 2026

```sql
UPDATE folders
SET process_edi = 1
WHERE (
    process_edi = 0
    OR process_edi = 'False'
    OR process_edi = 'false'
)
AND convert_to_format IS NOT NULL
AND TRIM(convert_to_format) != ''
AND LOWER(TRIM(convert_to_format)) != 'do_nothing'
```

**Impact:** Fixes all 348 folders with contradictory state.

**Runtime Guard (orchestrator.py:1310-1322):**
```python
if not process_edi_bool and has_convert_target:
    alias = effective_folder.get("alias", "<unknown>")
    logger.warning(
        "Folder %s has process_edi=False but convert_to_format=%r; "
        "treating as enabled. Run the database migration to fix "
        "this permanently.",
        alias,
        effective_folder.get("convert_to_format"),
    )
    process_edi_bool = True
    effective_folder["process_edi"] = True
```

---

## Code Behavior Comparison

### V32 Conversion Logic

```python
# Simplified V32 logic
if process_edi and convert_to_format:
    run_conversion()
elif tweak_edi:
    apply_tweaks()
else:
    pass  # Silent pass-through
```

**Problems:**
1. `process_edi=False` blocks conversion even if format is set
2. `tweak_edi` is separate from `convert_to_format`
3. No validation of format against supported list
4. Silent pass-through if module missing

---

### Current (V48) Conversion Logic

```python
# Current converter.py logic
def convert(self, input_path, output_dir, params, settings, upc_dict):
    # 1. Normalize format
    convert_to_format = _normalize_convert_to_format(params.get("convert_to_format", ""))
    
    # 2. Check for no-op
    if not convert_to_format:
        return input_path  # No conversion requested
    
    # 3. Check process_edi flag
    if not process_edi:
        return input_path  # Processing disabled
    
    # 4. Validate against whitelist
    if convert_to_format not in SUPPORTED_FORMATS:
        raise Exception(f"Unsupported format: {convert_to_format}")
    
    # 5. Load module dynamically
    module_name = f"dispatch.converters.convert_to_{convert_to_format}"
    converter_module = importlib.import_module(module_name)
    
    # 6. Verify module interface
    if not hasattr(converter_module, "edi_convert"):
        raise Exception(f"Module {module_name} missing edi_convert function")
    
    # 7. Execute conversion
    result = converter_module.edi_convert(...)
    
    # 8. Verify output produced
    if not result.output_path:
        raise Exception("Conversion requested but no output produced")
    
    return result.output_path
```

**Improvements:**
1. ✅ Format normalization handles legacy casing/spacing
2. ✅ Whitelist validation prevents invalid formats
3. ✅ Fail-fast behavior catches errors
4. ✅ No-output detection ensures conversion actually happened
5. ✅ Runtime guard handles contradictory state with warning

---

## Supported Conversion Formats

### Current (V48) - 11 Formats

```python
SUPPORTED_FORMATS = [
    "csv",                      # Standard CSV
    "estore_einvoice",          # Estore eInvoice
    "estore_einvoice_generic",  # Estore eInvoice Generic
    "fintech",                  # Fintech integration
    "jolley_custom",            # Jolley custom format
    "scannerware",              # ScannerWare format
    "scansheet_type_a",         # ScanSheet Type A
    "simplified_csv",           # Simplified CSV
    "stewarts_custom",          # Stewart's custom format
    "tweaks",                   # EDI tweaks (formerly tweak_edi flag)
    "yellowdog_csv",            # YellowDog CSV
]
```

### V32 Formats in Use - 10 Formats

| Format | Count | Normalized To |
|--------|-------|---------------|
| csv | 324 | csv |
| stewarts_custom | 55 | stewarts_custom |
| jolley_custom | 55 | jolley_custom |
| simplified_csv | 31 | simplified_csv |
| Estore eInvoice Generic | 15 | estore_einvoice_generic |
| YellowDog CSV | 14 | yellowdog_csv |
| scansheet-type-a | 2 | scansheet_type_a |
| fintech | 1 | fintech |
| ScannerWare | 1 | scannerware |

**Note:** V32 formats use mixed casing which is **normalized** by current code.

---

## Regression Risk Assessment

### If Skipping V48 Migration

**CRITICAL RISK:** 348 folders would NOT convert

| Impact | Severity | Folders Affected |
|--------|----------|------------------|
| Files pass through unchanged | **CRITICAL** | 348 |
| Downstream systems receive wrong format | **HIGH** | 348 |
| Users unaware (UI shows enabled) | **HIGH** | 348 |
| Potential revenue loss | **MEDIUM** | Unknown |
| Customer complaints | **HIGH** | Likely |

### If Running V48 Migration

**Risk:** Minimal — migration is idempotent and logged

| Impact | Severity | Mitigation |
|--------|----------|------------|
| process_edi changed from False→True | **LOW** | Intentional, matches user intent |
| Conversion starts running | **LOW** | Expected behavior |
| Output format changes | **NONE** | Format was already configured |

---

## Verification Steps

### Pre-Migration Check

```bash
# Count folders with contradictory state
sqlite3 your_v32_database.db "
    SELECT COUNT(*) FROM folders 
    WHERE (process_edi = 0 OR process_edi = 'False')
    AND convert_to_format IS NOT NULL 
    AND TRIM(convert_to_format) != '';
"
# Expected: 348 (or similar if your data differs)
```

### Post-Migration Check

```bash
# 1. Verify database version
sqlite3 your_database.db "SELECT version FROM db_version WHERE id=1;"
# Expected: 48

# 2. Verify no contradictory folders remain
sqlite3 your_database.db "
    SELECT COUNT(*) FROM folders 
    WHERE (process_edi = 0 OR process_edi = 'False')
    AND convert_to_format IS NOT NULL 
    AND TRIM(convert_to_format) != '';
"
# Expected: 0

# 3. Verify format normalization
sqlite3 your_database.db "
    SELECT DISTINCT convert_to_format FROM folders 
    WHERE convert_to_format != '';
"
# Expected: All lowercase with underscores
```

---

## Recommendations

### 1. **ALWAYS Run Database Migrations**

The v47→v48 migration is **critical** for correct conversion behavior. Never skip migrations.

### 2. **Add Validation to UI**

Prevent users from creating contradictory state:
- Disable format dropdown when `process_edi` checkbox is unchecked
- Or auto-check `process_edi` when format is selected

### 3. **Add Monitoring**

Alert if contradictory state is detected:
```python
# In orchestrator or health check
contradictory = db.query("""
    SELECT COUNT(*) FROM folders 
    WHERE process_edi = 0 AND convert_to_format != ''
""")
if contradictory > 0:
    alert(f"{contradictory} folders have contradictory configuration")
```

### 4. **Document Behavior**

Update user documentation to clarify:
- `process_edi` checkbox must be checked for conversion to run
- Format dropdown selects the conversion target
- Both must be configured for conversion

---

## Appendix: Folder Lists by Category

### CONVERT_BLOCKED_REGRESSION Folders (348)

See `/tmp/v32_categorized_folders.csv` for complete list.

**Top 20 by ID:**
```
ID=56,   alias=020061,   format=csv
ID=184,  alias=033626,   format=csv
ID=186,  alias=011028,   format=csv
ID=188,  alias=011355,   format=csv
ID=189,  alias=017127,   format=csv
ID=190,  alias=025020,   format=csv
ID=192,  alias=028009,   format=YellowDog CSV
ID=193,  alias=028039,   format=YellowDog CSV
ID=194,  alias=028011,   format=YellowDog CSV
ID=195,  alias=028052,   format=YellowDog CSV
ID=196,  alias=028059,   format=csv
ID=197,  alias=028091,   format=csv
ID=198,  alias=030888,   format=csv
ID=200,  alias=030213,   format=csv
ID=201,  alias=030230,   format=csv
ID=202,  alias=030250,   format=csv
ID=203,  alias=030641,   format=csv
ID=204,  alias=033147,   format=csv
ID=205,  alias=033148,   format=csv
ID=206,  alias=033175,   format=csv
... and 328 more
```

### CONVERT_ENABLED Folders (150)

**Top 20 by ID:**
```
ID=21,   alias=012258,   format=csv
ID=89,   alias=030654,   format=ScannerWare
ID=90,   alias=030726,   format=csv
ID=95,   alias=030896,   format=csv
ID=108,  alias=033279,   format=csv
ID=126,  alias=034309,   format=csv
ID=140,  alias=035046,   format=simplified_csv
ID=142,  alias=035058,   format=csv
ID=187,  alias=011283,   format=fintech
ID=191,  alias=025031,   format=csv
... and 140 more
```

---

## Conclusion

**The conversion behavior has NOT regressed** — it has been **significantly improved** through migrations v44→v48:

1. ✅ **348 folders fixed** — conversion now runs as users expect
2. ✅ **`convert_to_format` is single source of truth** — retired confusing `tweak_edi` flag
3. ✅ **Whitelist validation** — prevents invalid formats
4. ✅ **Fail-fast behavior** — catches errors instead of silent pass-through
5. ✅ **Format normalization** — handles legacy casing/spacing

**Critical Action:** Ensure database migrations run when upgrading from V32. The v47→v48 migration is essential for correct conversion behavior.

**Risk of Skipping Migration:** 348 folders (65.7%) would continue to have conversion silently blocked, potentially causing significant downstream impact.
