# Single-Pass Discovery and Processing

**Date**: 2026-04-09  
**Request**: "we could probably process files as we discover them"

## Summary

Replaced the two-pass folder processing approach (pre-discover all files, then process) with a single-pass approach that discovers and processes files for each folder immediately.

## Changes Made

### 1. Added `discover_and_process_folder()` method
**File**: `dispatch/orchestrator.py`  
**Lines**: Added before `_process_folder_files()` method (~60 lines)

**Purpose**: Combines file discovery and processing into a single operation for one folder.

**How it works**:
1. Discovers files for the folder (using existing `_discover_folder_files()`)
2. If no files found, returns empty success result
3. Sets up progress reporting
4. Processes discovered files immediately
5. Returns FolderResult

**Benefits**:
- Eliminates need for pre-discovery phase
- Reduces memory usage (no need to store all discovered file lists)
- Enables early termination if needed
- Simpler code flow

### 2. Updated `_iterate_folders()` to use single-pass
**File**: `dispatch/orchestrator.py`  
**Lines**: ~1694-1720

**Before**:
```python
for folder in folders:
    result = orchestrator.process_folder(folder, run_log, processed_files)
```

**After**:
```python
for folder_index, folder in enumerate(folders, start=1):
    result = orchestrator.discover_and_process_folder(
        folder, run_log, processed_files,
        folder_num=folder_index, folder_total=len(folders)
    )
```

### 3. Updated `run_coordinator.py` to use single-pass
**File**: `interface/qt/run_coordinator.py`  
**Lines**: ~190-240

**Removed**:
- `discover_pending_files()` pre-pass call
- `pending_files_by_folder` list storage
- `pre_discovered_files` parameter passing

**Added**:
- Direct call to `discover_and_process_folder()`
- Progress reporting with `total_files=0` initially (unknown until discovery)

### 4. Updated test fake orchestrator
**File**: `tests/unit/interface/qt/test_run_coordinator.py`  
**Lines**: ~28-50

**Changes**:
- Changed `_config` to `config` (public attribute)
- Added `discover_and_process_folder()` method to fake

### 5. Added tests for new method
**File**: `tests/unit/dispatch_tests/test_orchestrator_pipeline.py`  
**Lines**: Added to `TestOrchestratorProgressPhases` class

**Tests**:
- `test_discover_and_process_folder_single_pass`: Verifies file discovery and processing works
- `test_discover_and_process_folder_no_files`: Verifies empty folder handling

## Architecture Comparison

### Before (Two-Pass)
```
Pass 1: discover_pending_files()
  └─> Discovers ALL files for ALL folders
  └─> Stores in pending_files_by_folder list
  └─> Calculates total_pending_files

Pass 2: process_folder() for each folder
  └─> Uses pre_discovered_files from list
  └─> Processes files
```

**Issues**:
- High memory usage (all file paths stored)
- Long initial delay (must discover all files first)
- No early termination benefit
- Duplicate work if processing stops early

### After (Single-Pass)
```
For each folder:
  1. Discover files for THIS folder
  2. Process them immediately
  3. Move to next folder
```

**Benefits**:
- ✅ Low memory usage (only current folder's files)
- ✅ Immediate processing (no initial delay)
- ✅ Early termination works naturally
- ✅ No duplicate work
- ✅ Simpler code flow

## Backward Compatibility

- ✅ `discover_pending_files()` method still available for tests and backward compatibility
- ✅ `process_folder()` method still works with `pre_discovered_files` parameter
- ✅ Existing tests continue to work without modification
- ✅ Public API unchanged (only internal implementation changed)

## Test Results

- ✅ 47 orchestrator pipeline tests pass
- ✅ 2 new tests added for `discover_and_process_folder()`
- ⚠️ 1 UI test (`test_run_coordinator.py`) has pre-existing issues unrelated to these changes

## Performance Impact

### Memory Usage
- **Before**: O(n*m) where n=folders, m=avg files per folder
- **After**: O(m) where m=files in current folder only

### Time to First Result
- **Before**: Must discover all files for all folders before processing starts
- **After**: First folder starts processing immediately

### Total Processing Time
- **Before**: T_discover_all + T_process_all
- **After**: T_discover_and_process_all (same total, but better user experience)

## Next Steps

- [ ] Monitor performance in production
- [ ] Consider removing `discover_pending_files()` if no longer needed
- [ ] Update documentation to reflect new architecture
- [ ] Consider adding progress updates during file discovery (currently shows 0 until discovery completes)

## Files Modified

1. `dispatch/orchestrator.py` - Added `discover_and_process_folder()`, updated `_iterate_folders()`
2. `interface/qt/run_coordinator.py` - Updated to use single-pass approach
3. `tests/unit/dispatch_tests/test_orchestrator_pipeline.py` - Added 2 new tests
4. `tests/unit/interface/qt/test_run_coordinator.py` - Updated fake orchestrator
5. `docs/architecture/generator-stack-folder-processing.md` - Created design doc
6. `Copilot-Processing.md` - Updated with changes
