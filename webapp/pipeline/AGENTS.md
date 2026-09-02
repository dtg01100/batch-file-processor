# WEBAPP/PIPELINE MODULE (Core Processing)

Refactored file-processing pipeline — owned by the webapp since
Phase 9.1 (2026-09-02). Replaces the pre-pivot `dispatch/`
package.

## STRUCTURE

```
webapp/pipeline/
├── orchestrator.py          # DispatchOrchestrator (main orchestration)
├── pipeline/
│   ├── factory.py           # create_standard_pipeline (wires the 5 steps)
│   └── interfaces.py        # PipelineStep protocol, adapters
├── services/
│   ├── file_processor.py    # FileProcessor (per-file processing)
│   ├── folder_processor.py  # FolderPipelineExecutor (per-folder)
│   ├── folder_discovery.py  # FolderDiscoveryService
│   ├── progress_reporter.py # ProgressReporter Protocol + CLI/Null/Logging
│   ├── progress_reporting.py# ProgressReportingService (the SSE/CLI bridge)
│   ├── upc_service.py       # UPCLookupService
│   └── customer_lookup_service.py, uom_lookup_service.py
├── converters/              # 12 format converters (registry-discovered)
│   ├── convert_base.py      # BaseEDIConverter + EDIRecord
│   ├── csv_utils.py         # shared CSV helpers
│   ├── mixins.py            # DB-enabled converter mixins (Phase 12: rewrite)
│   └── registry.py          # CONVERTER_METADATA discovery (pkgutil)
├── send_manager.py          # SendManager + BackendFactory
├── error_handler.py         # ErrorHandler (Phase 9.5: routed to webapp/errors)
└── edi_validator.py         # EDIValidator + ValidationResult
```

The rename from `dispatch/` to `webapp/pipeline/` happened in
Phase 9.1. Subsequent phases simplified the layout:

- 9.2 — deleted Qt-era `UIProgressReporter` class
- 9.3 — consolidated background runs into a single
  `ThreadPoolExecutor` (FastAPI endpoints are sync `def`, not
  `async def`)
- 9.4 — converter spec API is registry-driven (adding a converter
  is a one-file change)
- 9.5 — pipeline errors route through `webapp.errors.insert_error`
  (the canonical ledger); deleted dead helpers
- 9.6 — documented watcher → `RunStore` → orchestrator path
- 9.7 — added `make_folder_row()` factory in `tests/conftest.py`
- Phase 11 (next) — typed records + per-converter config
  dataclasses (`_config.py` siblings)

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Main orchestration | `orchestrator.py` | `DispatchOrchestrator.process()` — full flow |
| Pipeline configuration | `pipeline/factory.py` | `create_standard_pipeline` |
| Pipeline interfaces | `pipeline/interfaces.py` | `PipelineStep` protocol, adapters |
| Per-folder processing | `services/folder_processor.py` | `FolderPipelineExecutor` |
| Per-file processing | `services/file_processor.py` | `FileProcessor.process_file()` |
| File discovery/hashing | `services/file_processor.py` | `FileDiscoverer`, `HashGenerator` |
| EDI validation | `edi_validator.py` | `ValidationResult` with errors list |
| Send to backends | `send_manager.py` | `SendManager.send_file()`, `BackendFactory` |
| Error recording | `error_handler.py` | Routes to `webapp.errors.insert_error` |
| Converter discovery | `converters/registry.py` | `get_all_converters()` |

## KEY CLASSES

**DispatchOrchestrator** — Main orchestration
- Delegates to `FolderPipelineExecutor` for per-folder processing
- Uses `FileProcessor` for per-file processing
- Maintains high-level coordination and progress reporting

**create_standard_pipeline** — Pipeline factory
- `create_standard_pipeline(settings=..., error_handler=..., backends=..., upc_dict=...)`
- Wires the validator → splitter → converter → tweaker → sender steps

**FolderPipelineExecutor** — Per-folder processing
- File discovery + filtering (skip already-processed via checksum)
- Per-file processing through `FileProcessor`
- Aggregates results and errors

**FileProcessor** — Per-file processing
- Hash generation → validation → splitting → conversion → tweaks → send
- Pipeline-step pattern for extensibility

**PipelineStep Protocol** — Standardized pipeline interface
- `execute(input_path, context) -> (success, output_path, errors)`
- `wrap_as_pipeline_step()` for adapter support

**ErrorHandler** — Pipeline error capture
- Records errors to in-memory buffer + file log + `webapp/errors` ledger
- Phase 9.5: routes via `webapp.errors.insert_error(dedupe=True)`
- Phase 11.x: legacy `_persist_to_database` path will be removed

## CONVENTIONS

**Processing flow:**
1. `DispatchOrchestrator.process()` receives folder config
2. `FolderPipelineExecutor` handles per-folder ops:
   - File discovery (list input directory)
   - Filtering (skip already-processed via checksum)
3. `FileProcessor` handles per-file ops:
   - Hash generation
   - EDI validation
   - Splitting (if enabled)
   - Conversion (to target format via `converters/registry.py`)
   - Tweak application (if enabled)
   - Send (via `SendManager` to backends)
4. Results aggregated and returned

**Plugin invocation:**
- Converters: `module.edi_convert(edi_process, output_filename, settings_dict, parameters_dict, upc_lookup)`
- Backends: `module.do(process_parameters, settings_dict, filename)`

**Pipeline step interface:**
```python
class PipelineStep(Protocol):
    def execute(self, input_path: str, context: dict) -> tuple[bool, str, list[str]]:
        ...
```

**Converter registration (Phase 9.4):**
```python
# In webapp/pipeline/converters/convert_to_myformat.py
CONVERTER_METADATA = {
    "format_name": "myformat",
    "display_name": "My Format",
    "module_name": "webapp.pipeline.converters.convert_to_myformat",
}

class MyFormatConverter(BaseEDIConverter):
    ...

edi_convert = make_edi_convert(MyFormatConverter)
```

The registry auto-discovers; no manual list update needed.

## CONFIGURATION

```python
from webapp.pipeline.orchestrator import DispatchOrchestrator
from webapp.pipeline.pipeline.factory import create_standard_pipeline

config = create_standard_pipeline(
    settings=settings_dict,
    version="webapp",
    error_handler=error_handler,
    backends={"copy": copy_backend},
    upc_dict={},
)
orchestrator = DispatchOrchestrator(config)
```

## ANTI-PATTERNS

**DO NOT:**
- Add UI logic to the orchestrator (use progress reporter only)
- Hardcode converter/backend names (use `converters/registry.py` and
  `BackendFactory`)
- Skip error recording (always go through `ErrorHandler` — it routes
  to the ledger)
- Import from `webapp.pipeline.services.progress_reporter` directly
  in new code (use `services.progress_reporting.ProgressReportingService`)
- Add new converter modules without `CONVERTER_METADATA` (the
  registry won't pick them up)

## FUTURE PHASES

- **Phase 11** — typed records (`ARecord`/`BRecord`/`CRecord` instead
  of `dict`) + per-converter config dataclasses. The `ARecord` etc.
  dataclasses already exist in `core/edi/edi_parser.py`; Phase 11
  wires them through.
- **Phase 12** — rewrite `converters/mixins.py` (4 mixin classes) as
  composition (a converter that holds a `DatabaseHandle` field) instead
  of multiple inheritance.
- **Phase 10 checkpoint** — re-evaluate Candidate C (full async
  pipeline + JSON config column). Trigger: schema migrations more
  frequent than 1/quarter.
