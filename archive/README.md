# Archived Legacy Files

This directory contains legacy files that have been deprecated and archived as part of the codebase cleanup initiative.

## Archive Date
March 3, 2026

## Files Archived

### 1. _dispatch_legacy.py (33,601 characters)
- **Status**: Backup of even older dispatch code
- **Superseded By**: `dispatch/orchestrator.py` (which has better error handling and dependency injection)
- **Reason for Archiving**: Redundant legacy code that was no longer actively used

### 2. dispatch_process.py (34,193 characters)
- **Status**: Active legacy but superseded by dispatch/ module
- **Superseded By**: `dispatch/orchestrator.py`
- **Key Functions**: The `process()` function was previously imported by `dispatch/__init__.py`
- **Migration**: The `process()` function import was removed from `dispatch/__init__.py`. Use `DispatchOrchestrator` instead.
- **Reason for Archiving**: Procedural implementation replaced by class-based orchestrator with dependency injection

### 3. mtc_edi_validator.py (5,465 characters)
- **Status**: Procedural implementation
- **Superseded By**: `dispatch/edi_validator.py` (class-based with dependency injection)
- **Key Functions**: `check()` and `report_edi_issues()`
- **Reason for Archiving**: Replaced by more testable, class-based EDI validator

### 4. edi_tweaks.py (12,482 characters)
- **Status**: Procedural EDI tweaks
- **Superseded By**: `dispatch/pipeline/tweaker.py` and `core/edi/` package
- **Key Functions**: `edi_tweak()` was used by `dispatch/pipeline/tweaker.py`
- **Migration**: The pipeline tweaker now has the functionality integrated or uses `core/edi/` modules
- **Reason for Archiving**: Procedural implementation replaced by class-based pipeline step

## Total Code Removed
**85,741+ characters** of dead code eliminated

## Associated Test Files Removed
- `tests/unit/test_edi_tweaks.py`
- `tests/unit/test_mtc_edi_validator.py`

## Migration Guide

### For dispatch_process.process()
Replace:
```python
from dispatch import process
# or
from dispatch_process import process
```

With:
```python
from dispatch.orchestrator import DispatchOrchestrator, DispatchConfig

config = DispatchConfig(...)
orchestrator = DispatchOrchestrator(config)
orchestrator.process_all(folders_data, processed_files)
```

### For edi_tweaks.edi_tweak()
Replace:
```python
from edi_tweaks import edi_tweak
result = edi_tweak(edi_process, output_filename, settings_dict, parameters_dict, upc_dict)
```

With:
```python
from dispatch.pipeline.tweaker import EDITweakerStep

tweaker = EDITweakerStep()
result = tweaker.tweak(input_path, output_dir, params, settings, upc_dict)
```

### For mtc_edi_validator.check()
Replace:
```python
from mtc_edi_validator import check, report_edi_issues
is_valid = check(file_path)
```

With:
```python
from dispatch.edi_validator import EDIValidator

validator = EDIValidator()
is_valid = validator.validate(file_path)
```

## Verification

After archiving, run the full test suite to verify no broken imports:
```bash
python -m pytest tests/ -v --tb=short
```

## Restoration

If any of these files need to be restored, simply move them back from this archive directory to the project root. However, note that you may need to update imports in dependent files as they have been migrated to use the new refactored modules.
