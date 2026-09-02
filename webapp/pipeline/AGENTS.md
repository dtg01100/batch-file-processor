# WEBAPP/PIPELINE MODULE (Core Processing)

Refactored file-processing pipeline — owned by the webapp since
Phase 9.1. Replaces the pre-pivot `dispatch/` package.

## STRUCTURE

```
webapp/pipeline/
├── orchestrator.py          # DispatchOrchestrator (main orchestration)
├── config_builder.py        # DispatchConfigBuilder (fluent config)
├── pipeline/
│   └── interfaces.py        # PipelineStep protocol, adapters
├── services/
│   ├── file_processor.py    # FileProcessor (per-file processing)
│   └── folder_processor.py  # FolderPipelineExecutor (per-folder processing)
├── converters/              # 11 format converters (CSV, ScannerWare, x810, …)
├── send_manager.py          # SendManager, BackendFactory
├── error_handler.py         # ErrorHandler, ErrorLogger (Phase 9.5: delete)
└── edi_validator.py         # EDIValidator, ValidationResult
```

> The rename from `dispatch/` to `webapp/pipeline/` happened in
> Phase 9.1 (2026-09-02). Subsequent phases simplify this layout:
> 9.2 collapses the two progress reporters, 9.3 changes the
> async boundary, 9.4 adds registry-driven converter discovery,
> 9.5 deletes `error_handler.py` in favor of direct calls to
> `webapp/errors.insert_error`.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Main orchestration | `orchestrator.py` | DispatchOrchestrator.process() — full flow |
| Pipeline configuration | `config_builder.py` | DispatchConfigBuilder for fluent setup |
| Pipeline interfaces | `pipeline/interfaces.py` | PipelineStep protocol, adapters |
| Per-folder processing | `services/folder_processor.py` | FolderPipelineExecutor |
| Per-file processing | `services/file_processor.py` | FileProcessor.process_file() |
| File discovery/hashing | `services/file_processor.py` | FileDiscoverer, HashGenerator |
| EDI validation | `edi_validator.py` | ValidationResult with errors list |
| Send to backends | `send_manager.py` | SendManager.send_file(), BackendFactory |
| Error recording | `error_handler.py` | ErrorLogger, ReportGenerator |

## KEY CLASSES

**DispatchOrchestrator** — Main orchestration
- Delegates to FolderPipelineExecutor for per-folder processing
- Uses FileProcessor for per-file processing
- Maintains high-level coordination and progress reporting

**DispatchConfigBuilder** — Fluent configuration
- `DispatchConfigBuilder().with_validator(v).with_backends(b).build()`
- Simplifies pipeline step composition

**FolderPipelineExecutor** — Per-folder processing
- Handles file discovery and filtering
- Processes files through FileProcessor pipeline
- Aggregates results and errors

**FileProcessor** — Per-file processing
- Coordinates validation, splitting, conversion, tweaks, sending
- Uses pipeline step pattern for extensibility

**PipelineStep Protocol** — Standardized pipeline interface
- `execute(input_path, context) -> (success, output_path, errors)`
- `wrap_as_pipeline_step()` for adapter support

## CONVENTIONS

**Processing flow**:
1. DispatchOrchestrator.process_folder() receives folder config
2. FolderPipelineExecutor handles per-folder operations:
   - File discovery (list files in directory)
   - Filtering (skip already-processed via checksum)
3. FileProcessor handles per-file operations:
   - Hash generation
   - EDI validation
   - Splitting (if enabled)
   - Conversion (to target format)
   - Apply tweaks (if enabled)
   - Send (via SendManager to backends)
4. Results aggregated and returned

**Plugin invocation**:
- Converters: `module.edi_convert(edi_process, output_filename, settings_dict, parameters_dict, upc_lookup)`
- Backends: `module.do(process_parameters, settings_dict, filename)`

**Pipeline step interface**:
```python
class PipelineStep(Protocol):
    def execute(self, input_path: str, context: dict) -> tuple[bool, str, list[str]]:
        ...
```

## CONFIGURATION

```python
from dispatch.edi_validator import EDIValidator

config = {
    "validator": EDIValidator(),
    "settings": {"email_host": "smtp.example.com"},
    "backends": {"email": email_backend},
}

orchestrator = DispatchOrchestrator(config)
```

## ANTI-PATTERNS

**DO NOT**:
- Import from root `dispatch.py` for new code (use `dispatch/` package)
- Add UI logic to orchestrator (use callbacks/overlay updates only)
- Hardcode converter/backend names (use dynamic import patterns)
- Skip error recording (always use ErrorHandler)
