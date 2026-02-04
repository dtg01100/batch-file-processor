# DISPATCH MODULE (Core Processing)

Refactored dispatch package — file processing, EDI validation/splitting/conversion, sending, error handling.

## STRUCTURE

```
dispatch/
├── coordinator.py      # DispatchCoordinator (893 lines, main orchestration)
├── file_processor.py   # FileDiscoverer, HashGenerator, FileFilter
├── edi_validator.py    # EDIValidator, ValidationResult
├── edi_processor.py    # EDISplitter, EDIConverter, EDITweaker, FileNamer
├── send_manager.py     # SendManager, BackendFactory, SendResult
├── error_handler.py    # ErrorHandler, ErrorLogger, ReportGenerator
├── db_manager.py       # DBManager, ProcessedFilesTracker, ResendFlagManager
└── __init__.py         # Exports all public APIs
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Main orchestration | `coordinator.py` | DispatchCoordinator.process() — full flow |
| File discovery/hashing | `file_processor.py` | generate_match_lists, generate_file_hash |
| EDI validation | `edi_validator.py` | ValidationResult with errors list |
| EDI splitting | `edi_processor.py` | EDISplitter.split_edi() |
| Format conversion | `edi_processor.py` | EDIConverter imports convert_to_* plugins |
| Apply EDI tweaks | `edi_processor.py` | EDITweaker (calls convert_to_edi_tweaks.py) |
| Send to backends | `send_manager.py` | SendManager.send_file(), BackendFactory |
| Error recording | `error_handler.py` | ErrorLogger, ReportGenerator |
| Processed files tracking | `db_manager.py` | ProcessedFilesTracker (DB operations) |

## KEY CLASSES

**DispatchCoordinator** — Main orchestration (893 lines)
- `process(ProcessingContext)` — coordinates all steps
- Uses overlay updates for GUI progress (doingstuffoverlay.py)
- Calls file discovery → validate → split → convert → send → error handling

**EDIConverter** — Dynamic plugin loader
- Builds module name: `convert_to_<format>`
- `importlib.import_module()` then calls `module.edi_convert(...)`

**SendManager** — Send orchestration
- `BackendFactory.get_backend(backend_type)` imports `<backend>_backend.py`
- Calls `module.do(process_parameters, settings, file_path)`

## CONVENTIONS

**Processing flow** (coordinator.py):
1. File discovery (FileDiscoverer)
2. Hash generation (HashGenerator)
3. File filtering (FileFilter — check processed_files)
4. EDI validation (EDIValidator)
5. EDI splitting (EDISplitter)
6. EDI conversion (EDIConverter — imports converter)
7. Apply tweaks (EDITweaker if enabled)
8. Send (SendManager → backend)
9. Error handling (ErrorHandler if failures)

**Plugin invocation**:
- Converters: `module.edi_convert(edi_process, output_filename, settings_dict, parameters_dict, upc_lookup)`
- Backends: `module.do(process_parameters, settings_dict, filename)`

**Error handling**: record_error.py for logging, ErrorLogger aggregates errors, ReportGenerator creates reports

## COEXISTENCE WITH LEGACY

**dispatch.py** (root, 569 lines, deep nesting) — legacy monolithic dispatcher
- Both `dispatch.py` and `dispatch/` package exist
- Refactored code in `dispatch/` package is preferred
- Legacy `dispatch.py` still used by some code paths (being migrated)

## ANTI-PATTERNS

**DO NOT**:
- Import from root `dispatch.py` for new code (use `dispatch/` package)
- Add UI logic to coordinator (use ProcessingContext callbacks/overlay updates only)
- Hardcode converter/backend names (use dynamic import patterns)
- Skip error recording (always use record_error.py or ErrorLogger)
