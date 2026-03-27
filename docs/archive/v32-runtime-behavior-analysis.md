# Runtime Behavior Analysis: V32 vs V48

**Date:** March 27, 2026  
**Focus:** How the **program code** treats each folder configuration during file processing  
**Database Versions:** V32 (backup) → V48 (current)

---

## Methodology

This analysis traces through the **actual runtime code execution** for each folder type, showing:
1. **V32 behavior** - How the old code processed files
2. **V48 behavior** - How current code processes files
3. **Code path differences** - Exact decision points in the code

---

## File Processing Pipeline Overview

```
File Discovered
    ↓
_build_processing_context() - Line 1336
    ↓
_normalize_edi_flags() - Line 1295
    ↓
_execute_file_pipeline() - Line 810
    ↓
_apply_conversion_and_tweaks() - Line 835
    ↓
converter.convert() - converter.py:316
    ↓
_is_process_edi_disabled() - converter.py:476
    ↓
[Conversion or Pass-through]
```

---

## Category 1: CONVERT_BLOCKED_REGRESSION (348 folders)

### Configuration
```python
process_edi = False
convert_to_format = 'csv' (or other format)
tweak_edi = 0 or 1
```

### Example Folders
```
ID=56,   alias=020061,   process_edi=False, convert_to_format=csv
ID=192,  alias=028009,   process_edi=False, convert_to_format=YellowDog CSV, tweak_edi=1
ID=557,  alias=078006,   process_edi=False, convert_to_format=Estore eInvoice Generic, tweak_edi=1
```

---

### V32 Runtime Behavior (WITHOUT migration)

#### Step 1: Context Building (orchestrator.py:1336)
```python
def _build_processing_context(self, folder: dict, upc_dict: dict):
    effective_folder = folder.copy()
    
    # Apply defaults for NULL fields
    for key, default in self._FOLDER_DEFAULTS.items():
        if effective_folder.get(key) is None:
            effective_folder[key] = default
    
    # Normalize format (line 1354)
    effective_folder["convert_to_format"] = _normalize_convert_to_format(
        effective_folder.get("convert_to_format", "")  # Returns "csv"
    )
    
    has_convert_target = bool(effective_folder.get("convert_to_format"))  # True
    
    # Normalize EDI flags (line 1364)
    self._normalize_edi_flags(effective_folder, has_convert_target=has_convert_target)
```

#### Step 2: EDI Flag Normalization (orchestrator.py:1295)
```python
def _normalize_edi_flags(self, effective_folder, has_convert_target):
    process_edi_raw = effective_folder.get("process_edi")  # "False"
    
    if process_edi_raw is None:
        effective_folder["convert_edi"] = has_convert_target  # Would be True
    else:
        process_edi_bool = normalize_bool(process_edi_raw)  # False
        
        # ⚠️ RUNTIME GUARD (lines 1310-1322)
        if not process_edi_bool and has_convert_target:
            alias = effective_folder.get("alias", "<unknown>")
            logger.warning(
                "Folder %s has process_edi=False but convert_to_format=%r; "
                "treating as enabled. Run the database migration to fix "
                "this permanently.",
                alias,
                effective_folder.get("convert_to_format"),
            )
            process_edi_bool = True  # ← AUTO-CORRECT!
            effective_folder["process_edi"] = True  # ← AUTO-CORRECT!
        
        effective_folder["convert_edi"] = process_edi_bool  # True
```

**V32 WITHOUT Migration:**
- Runtime guard detects contradictory state
- Logs WARNING
- **Auto-corrects `process_edi` to True**
- Conversion **WILL RUN** (but with warning)

#### Step 3: Converter Execution (converter.py:316)
```python
def convert(self, input_path, output_dir, params, settings, upc_dict):
    start_time = time.perf_counter()
    correlation_id = get_or_create_correlation_id()
    
    # Get format (line 322-323)
    raw_convert_to_format = params.get("convert_to_format", "")  # "csv"
    convert_to_format = _normalize_convert_to_format(raw_convert_to_format)  # "csv"
    
    # Check for no-op conversion (line 446)
    is_noop, noop_result = self._is_noop_conversion(
        convert_to_format, input_path, input_basename, correlation_id, start_time
    )
    if is_noop:
        return noop_result  # Would return - format is set
    
    # Check process_edi flag (line 476)
    is_disabled, disabled_result = self._is_process_edi_disabled(
        process_edi=params.get("process_edi"),  # True (auto-corrected)
        convert_to_format=convert_to_format,
        input_path=input_path,
        input_basename=input_basename,
        correlation_id=correlation_id,
        start_time=start_time
    )
    
    # Line 493-511: _is_process_edi_disabled
    def _is_process_edi_disabled(self, *, process_edi, ...):
        if not process_edi:  # False (auto-corrected to True)
            # Log debug and return early
            return True, ConverterResult(...)  # ← NOT TAKEN
        return False, None  # ← This path taken
    
    if is_disabled:
        return disabled_result  # Not taken
    
    # Validate format (line 516)
    is_invalid, invalid_result = self._validate_conversion_format(
        convert_to_format, input_path, input_basename, correlation_id, start_time
    )
    # "csv" is in SUPPORTED_FORMATS, so validation passes
    
    # Load converter module (line 570)
    module_name = f"dispatch.converters.convert_to_{convert_to_format}"  # "convert_to_csv"
    converter_module = importlib.import_module(module_name)
    
    # Execute conversion (line 617)
    result = converter_module.edi_convert(...)
    
    # Verify output (orchestrator.py:1162)
    if converted_file:
        did_convert = True
    elif str(convert_format).strip():
        raise RuntimeError("Conversion requested but no output produced")
```

**V32 WITHOUT Migration - Result:**
```
✅ Conversion RUNS (due to runtime auto-correction)
⚠️ WARNING logged for each folder
⚠️ Each file processed triggers the warning
📝 Log output:
  "Folder 020061 has process_edi=False but convert_to_format='csv'; 
   treating as enabled. Run the database migration to fix this permanently."
```

---

### V48 Runtime Behavior (WITH migration)

#### Step 1: Database Migration (folders_database_migrator.py:1373)
```python
# Migration v47→v48 runs ONCE during upgrade
cursor.execute("""
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
""")
# Fixes 348 folders in database
```

#### Step 2: Context Building (orchestrator.py:1336)
```python
def _build_processing_context(self, folder: dict, upc_dict: dict):
    effective_folder = folder.copy()
    
    # process_edi is now 1 (True) from migration
    effective_folder["process_edi"] = 1
    
    # Normalize format
    effective_folder["convert_to_format"] = "csv"
    
    has_convert_target = True
    
    # Normalize EDI flags
    self._normalize_edi_flags(effective_folder, has_convert_target=has_convert_target)
    
    # Line 1301-1303: process_edi is True, so no warning
    process_edi_bool = normalize_bool(process_edi_raw)  # True
    if not process_edi_bool and has_convert_target:  # False - not taken
        # Warning NOT logged
        pass
    effective_folder["convert_edi"] = True
```

#### Step 3: Converter Execution
```python
def convert(self, input_path, output_dir, params, settings, upc_dict):
    # process_edi is True (from database)
    is_disabled, disabled_result = self._is_process_edi_disabled(
        process_edi=True,  # True from database
        ...
    )
    # Returns (False, None) - conversion proceeds
    
    # Conversion runs normally
    result = converter_module.edi_convert(...)
```

**V48 WITH Migration - Result:**
```
✅ Conversion RUNS (no auto-correction needed)
✅ NO warnings logged
✅ Clean execution
📝 No log messages about contradictory state
```

---

### Code Path Comparison

| Step | V32 (No Migration) | V48 (With Migration) |
|------|-------------------|---------------------|
| **Database state** | `process_edi=False` | `process_edi=True` (migrated) |
| **Context building** | Auto-corrects to `True` | Uses `True` from DB |
| **Warning logged** | ⚠️ YES (per folder, per run) | ✅ NO |
| **Conversion** | ✅ Runs | ✅ Runs |
| **Output** | ✅ Correct format | ✅ Correct format |
| **Performance** | ⚠️ Warning logging overhead | ✅ No overhead |

---

## Category 2: CONVERT_ENABLED (150 folders)

### Configuration
```python
process_edi = True
convert_to_format = 'csv' (or other format)
tweak_edi = 0
```

### Example Folders
```
ID=21,   alias=012258,   process_edi=True, convert_to_format=csv
ID=89,   alias=030654,   process_edi=True, convert_to_format=ScannerWare
ID=187,  alias=011283,   process_edi=True, convert_to_format=fintech
```

---

### V32 Runtime Behavior

#### Context Building
```python
effective_folder["process_edi"] = True  # From database
effective_folder["convert_to_format"] = "csv"  # Normalized
has_convert_target = True

# _normalize_edi_flags
process_edi_bool = normalize_bool(True)  # True
if not process_edi_bool and has_convert_target:  # False - not taken
    pass
effective_folder["convert_edi"] = True
```

#### Converter Execution
```python
def convert(self, input_path, output_dir, params, settings, upc_dict):
    # process_edi is True
    is_disabled, disabled_result = self._is_process_edi_disabled(
        process_edi=True,
        ...
    )
    # Returns (False, None)
    
    # Format validation passes
    # Module loads
    # Conversion runs
```

**V32 Result:**
```
✅ Conversion RUNS normally
✅ NO warnings
✅ Clean execution
```

---

### V48 Runtime Behavior

**Identical to V32** - No changes for this category.

**V48 Result:**
```
✅ Conversion RUNS normally
✅ NO warnings
✅ Clean execution
```

---

### Code Path Comparison

| Step | V32 | V48 |
|------|-----|-----|
| **Database state** | `process_edi=True` | `process_edi=True` |
| **Context building** | Uses `True` from DB | Uses `True` from DB |
| **Warning logged** | ✅ NO | ✅ NO |
| **Conversion** | ✅ Runs | ✅ Runs |
| **Output** | ✅ Correct format | ✅ Correct format |
| **Behavior change** | **NONE** | **NONE** |

---

## Category 3: PASS_THROUGH_DISABLED (31 folders)

### Configuration
```python
process_edi = False
convert_to_format = '' (empty)
tweak_edi = 0
```

### Example Folders
```
ID=29,   alias=PIERCES,  process_edi=False, convert_to_format=''
ID=38,   alias=011044,   process_edi=False, convert_to_format=''
```

---

### V32 Runtime Behavior

#### Context Building
```python
effective_folder["process_edi"] = False  # From database
effective_folder["convert_to_format"] = ""  # Empty
has_convert_target = False  # Empty format

# _normalize_edi_flags
process_edi_raw = effective_folder.get("process_edi")  # False
if process_edi_raw is None:  # False - not taken
    effective_folder["convert_edi"] = has_convert_target
else:
    process_edi_bool = normalize_bool(False)  # False
    if not process_edi_bool and has_convert_target:  # False - has_convert_target is False
        pass
    effective_folder["convert_edi"] = False
```

#### Converter Execution
```python
def convert(self, input_path, output_dir, params, settings, upc_dict):
    convert_to_format = ""  # Empty
    
    # Check for no-op conversion (line 446)
    is_noop, noop_result = self._is_noop_conversion(
        convert_to_format="",  # Empty!
        ...
    )
    
    # Line 459-471: _is_noop_conversion
    def _is_noop_conversion(self, convert_to_format, ...):
        if not convert_to_format:  # True - empty string!
            duration_ms = (time.perf_counter() - start_time) * 1000
            StructuredLogger.log_debug(
                logger, "convert", __name__,
                f"No convert_to_format set, skipping conversion",
                decision="no_format",
                ...
            )
            return True, ConverterResult(
                output_path=input_path,  # Return original file
                format_used="",
                success=True,
                errors=[]
            )
    
    if is_noop:
        return noop_result  # ← TAKEN - Early return!
```

**V32 Result:**
```
✅ Conversion SKIPPED (no format configured)
✅ File passes through unchanged
✅ Debug log: "No convert_to_format set, skipping conversion"
✅ Intentionally disabled - correct behavior
```

---

### V48 Runtime Behavior

**Identical to V32** - No changes for this category.

**V48 Result:**
```
✅ Conversion SKIPPED (no format configured)
✅ File passes through unchanged
✅ Debug log: "No convert_to_format set, skipping conversion"
✅ Intentionally disabled - correct behavior
```

---

### Code Path Comparison

| Step | V32 | V48 |
|------|-----|-----|
| **Database state** | `process_edi=False, format=''` | `process_edi=False, format=''` |
| **Context building** | `has_convert_target=False` | `has_convert_target=False` |
| **Converter check** | `_is_noop_conversion` returns True | `_is_noop_conversion` returns True |
| **Conversion** | ✅ Skipped | ✅ Skipped |
| **Output** | ✅ Original file | ✅ Original file |
| **Behavior change** | **NONE** | **NONE** |

---

## Category 4: TWEAK_ONLY_DISABLED (1 folder)

### Configuration
```python
process_edi = False
convert_to_format = '' (empty)
tweak_edi = 1
```

### Example Folder
```
ID=546,  alias=030948,   process_edi=False, tweak_edi=1, convert_to_format=''
```

---

### V32 Runtime Behavior (BEFORE v44→v46 migrations)

#### Context Building
```python
effective_folder["process_edi"] = False
effective_folder["tweak_edi"] = 1  # Deprecated flag
effective_folder["convert_to_format"] = ""  # Empty
has_convert_target = False

# _normalize_edi_flags
process_edi_bool = normalize_bool(False)  # False
effective_folder["convert_edi"] = False
```

#### Converter Execution
```python
def convert(self, input_path, output_dir, params, settings, upc_dict):
    convert_to_format = ""  # Empty
    
    # No-op check
    is_noop, noop_result = self._is_noop_conversion(
        convert_to_format="",  # Empty!
        ...
    )
    # Returns (True, noop_result) - early return
    
    if is_noop:
        return noop_result  # ← TAKEN
```

**V32 Result:**
```
✅ Conversion SKIPPED (no format)
⚠️ tweak_edi=1 is IGNORED (deprecated, not read at runtime)
✅ File passes through unchanged
```

---

### V48 Runtime Behavior (AFTER v44→v46 migrations)

#### Migration v44→v46 (folders_database_migrator.py:1148)
```python
# Migration clears tweak_edi for all folders
cursor.execute("UPDATE folders SET tweak_edi = 0")
cursor.execute("""
    UPDATE folders
    SET convert_to_format = 'tweaks'
    WHERE tweak_edi = 1 AND (convert_to_format IS NULL OR convert_to_format = '')
""")
# But folder 546 has process_edi=False, so it's left alone
# Only tweak_edi is cleared
```

#### Context Building (V48)
```python
effective_folder["process_edi"] = False
effective_folder["tweak_edi"] = 0  # Cleared by migration
effective_folder["convert_to_format"] = ""  # Still empty
has_convert_target = False
```

**V48 Result:**
```
✅ Conversion SKIPPED (no format)
✅ tweak_edi cleared by migration
✅ File passes through unchanged
✅ Same behavior as V32, but cleaner state
```

---

## Special Case: Folders with tweak_edi=1 AND format set

### Configuration (V32)
```python
process_edi = False
convert_to_format = 'csv'
tweak_edi = 1
```

### Example Folders
```
ID=196,  alias=028059,   process_edi=False, convert_to_format=csv, tweak_edi=1
ID=204,  alias=033147,   process_edi=False, convert_to_format=csv, tweak_edi=1
```

---

### V32 Runtime Behavior (BEFORE migrations)

```python
# Context building
effective_folder["process_edi"] = False
effective_folder["convert_to_format"] = "csv"
effective_folder["tweak_edi"] = 1  # Ignored at runtime
has_convert_target = True

# _normalize_edi_flags
process_edi_bool = normalize_bool(False)  # False
if not process_edi_bool and has_convert_target:  # True!
    logger.warning("Folder has process_edi=False but convert_to_format='csv'")
    process_edi_bool = True  # Auto-correct
    effective_folder["process_edi"] = True

# Converter runs with process_edi=True
```

**V32 Result:**
```
⚠️ WARNING logged
✅ Conversion RUNS (auto-corrected)
⚠️ tweak_edi=1 is IGNORED (deprecated)
```

---

### V48 Runtime Behavior (AFTER migrations)

#### Migration v44→v46
```python
# Case A: tweak_edi=1 + format stored + process_edi=False
# Migration clears tweak_edi, leaves process_edi=False, format='csv'
cursor.execute("""
    UPDATE folders
    SET tweak_edi = 0
    WHERE tweak_edi = 1
      AND convert_to_format IS NOT NULL
      AND convert_to_format != ''
      AND process_edi = 0
""")
```

#### Migration v47→v48
```python
# Now fix the contradictory state
cursor.execute("""
    UPDATE folders
    SET process_edi = 1
    WHERE process_edi = 'False'
      AND convert_to_format IS NOT NULL
""")
# Sets process_edi=1
```

#### Context Building (V48)
```python
effective_folder["process_edi"] = True  # Migrated
effective_folder["convert_to_format"] = "csv"  # Unchanged
effective_folder["tweak_edi"] = 0  # Cleared
has_convert_target = True

# _normalize_edi_flags
process_edi_bool = normalize_bool(True)  # True
if not process_edi_bool and has_convert_target:  # False - not taken
    pass
```

**V48 Result:**
```
✅ NO warnings
✅ Conversion RUNS normally
✅ tweak_edi cleared
✅ Clean state
```

---

## Summary: Runtime Behavior by Category

| Category | Count | V32 Behavior | V48 Behavior | Change |
|----------|-------|--------------|--------------|--------|
| **CONVERT_BLOCKED** | 348 | ⚠️ Runs with warning | ✅ Runs cleanly | Warning removed |
| **CONVERT_ENABLED** | 150 | ✅ Runs | ✅ Runs | None |
| **PASS_THROUGH** | 31 | ✅ Skipped | ✅ Skipped | None |
| **TWEAK_ONLY** | 1 | ✅ Skipped (tweak ignored) | ✅ Skipped | State cleaned |

---

## Key Findings

### 1. Runtime Auto-Correction Prevents Data Loss

**Critical:** The runtime guard in `_normalize_edi_flags()` (lines 1310-1322) **prevents data loss** even if migrations aren't run:

```python
if not process_edi_bool and has_convert_target:
    logger.warning("Folder %s has process_edi=False but convert_to_format=%r; "
                   "treating as enabled...", alias, format)
    process_edi_bool = True  # Auto-correct!
    effective_folder["process_edi"] = True
```

**Impact:** Files ARE converted even without migration, but with warning spam.

---

### 2. Migration v48 Eliminates Warning Spam

**Without migration:**
- Every folder run logs: `"Folder X has process_edi=False but convert_to_format='csv'"`
- For 348 folders, this could be thousands of warnings per day

**With migration:**
- Database state is corrected once
- No warnings logged
- Clean execution

---

### 3. No Functional Regression

**All folder categories either:**
- ✅ Work the same (CONVERT_ENABLED, PASS_THROUGH)
- ✅ Work better (CONVERT_BLOCKED - warning removed)
- ✅ Have cleaner state (TWEAK_ONLY)

**No folder has worse behavior in V48.**

---

### 4. Code Path Complexity

**V32 code paths:**
- Multiple checks for `process_edi`, `tweak_edi`, `convert_to_format`
- Inconsistent handling of contradictory states
- Deprecated `tweak_edi` flag still present

**V48 code paths:**
- `convert_to_format` is single source of truth
- Runtime guard handles edge cases
- Migrations clean up legacy state
- Simpler, more maintainable logic

---

## Verification Commands

### Test Runtime Behavior

```bash
# Run with a V32 database (before migration)
python -m dispatch.orchestrator --database /path/to/v32.db

# Check logs for warnings
grep "process_edi=False but convert_to_format" logs/application.log
# Expected: Many warnings (one per folder run)

# Run migrations
python -m migrations.folders_database_migrator --database /path/to/v32.db

# Run again (after migration)
python -m dispatch.orchestrator --database /path/to/v32.db

# Check logs
grep "process_edi=False but convert_to_format" logs/application.log
# Expected: No warnings
```

---

## Conclusion

**Runtime behavior analysis confirms:**

1. ✅ **No conversion is blocked** - Runtime guard auto-corrects contradictory state
2. ✅ **No data loss** - Files are converted even without migration
3. ✅ **Migration improves observability** - Removes warning spam
4. ✅ **Code is simpler** - Single source of truth for conversion
5. ✅ **No regression** - All folders work same or better

**The program treats folders correctly in both V32 and V48, but V48 is cleaner and more maintainable.**
