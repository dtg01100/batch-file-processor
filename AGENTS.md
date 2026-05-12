# Batch File Processor — Technical Reference

**Version:** 1.0 | **Last Updated:** 2026-05-11
**Purpose:** Development guide for contributors and maintainers

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Directory Structure](#directory-structure)
3. [Key Entry Points](#key-entry-points)
4. [Import Conventions](#import-conventions)
5. [Core Patterns](#core-patterns)
6. [Legacy & Compatibility](#legacy--compatibility)
7. [Testing](#testing)
8. [Common Tasks](#common-tasks)
9. [Anti-Patterns](#anti-patterns)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER (PyQt5 GUI)                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         interface/qt/app.py                                  │
│                           Main Application                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     DispatchOrchestrator (dispatch/)                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │ FolderProcessor │  │  FileProcessor  │  │      SendManager           │  │
│  │  (per-folder)   │  │   (per-file)    │  │      (backends)             │  │
│  └────────┬────────┘  └────────┬────────┘  └──────────────┬──────────────┘  │
│           │                    │                          │                 │
│           ▼                    ▼                          ▼                 │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      Pipeline Steps                                  │  │
│  │  Validator → Splitter → Converter → Tweaker → Sender                │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
              ┌──────────┐    ┌──────────────┐   ┌──────────┐
              │  Email   │    │     FTP      │   │   Copy   │
              │ (SMTP)   │    │  (backend/)  │   │  Backend │
              └──────────┘    └──────────────┘   └──────────┘
```

### Data Flow

1. **User triggers processing** via Qt UI or automatic mode
2. **DispatchOrchestrator** coordinates per-folder processing
3. **FolderProcessor** discovers files, skips already-processed (checksum)
4. **FileProcessor** runs each file through the pipeline:
   - EDI validation
   - Splitting (if enabled)
   - Format conversion
   - Tweaks (if enabled)
5. **SendManager** delivers output via configured backends

---

## Directory Structure

| Path | Purpose | Key Files |
|------|---------|-----------|
| **interface/** | PyQt5 GUI layer | `qt/app.py`, `qt/main_window.py`, `application_controller.py` |
| **interface/qt/** | Qt widgets and dialogs | `dialogs/`, `widgets/`, `theme.py`, `run_coordinator.py` |
| **interface/models/** | Data models (dataclasses) | `folder_configuration.py` |
| **interface/operations/** | Business logic | `folder_operations.py`, `processing.py`, `maintenance.py` |
| **interface/database/** | Database access | `database_manager.py`, `Table` wrapper |
| **dispatch/** | Core file processing | `orchestrator.py`, `send_manager.py`, `edi_validator.py` |
| **dispatch/services/** | Processing services | `file_processor.py`, `folder_processor.py` |
| **dispatch/pipeline/** | Pipeline steps | `validator.py`, `splitter.py`, `converter.py` |
| **dispatch/converters/** | 12 format converters | `convert_to_csv.py`, `convert_to_scannerware.py`, etc. |
| **backend/** | Output backends | `email_backend.py`, `ftp_backend.py`, `copy_backend.py`, `http_backend.py` |
| **core/** | Shared utilities | `structured_logging.py`, `constants.py`, `exceptions.py` |
| **core/edi/** | EDI parsing | `edi_parser.py`, `edi_splitter.py`, `edi_tweaker.py` |
| **core/database/** | Database layer | SQLite adapter and repositories |
| **adapters/** | Database adapters | `adapters/sqlite/` (current), `adapters/db2ssh/` (future) |
| **tests/** | Test suite (~4757 tests) | `unit/`, `integration/`, `qt/`, `convert_backends/` |
| **archive/** | Deprecated code | Legacy `dispatch_process.py`, `edi_tweaks.py` (read-only) |

---

## Key Entry Points

| File | Purpose |
|------|---------|
| `main_qt.py` | Desktop shortcut entry point (delegates to `main_interface`) |
| `main_interface.py` | Application bootstrap — arg parsing, DB path, window creation |
| `interface/qt/app.py` | QApplication setup, theme, window instantiation |
| `interface/qt/bootstrap.py` | Service initialization (DB, config, window factory) |

### Running the Application

```bash
# GUI mode
.venv/bin/python interface/qt/app.py

# Automatic/headless mode
.venv/bin/python interface/qt/app.py -a

# Legacy entry point (wraps main_interface)
.venv/bin/python main_qt.py
```

---

## Import Conventions

### Recommended Import Patterns

**For new code, prefer explicit imports:**

```python
# ✓ Recommended - explicit and searchable
from dispatch.orchestrator import DispatchOrchestrator
from dispatch.edi_validator import EDIValidator
from backend.email_backend import do as email_do

# ✓ Recommended - import from module root when using multiple items
from dispatch import EDIValidator, SendManager
```

### Module Aliases Used in Codebase

```python
dispatch        # → dispatch/ package
backend         # → backend/ package
core            # → core/ package
interface       # → interface/ package
```

### Anti-pattern to Avoid

```python
# ✗ Avoid - unclear where DispatchOrchestrator comes from
from dispatch import DispatchOrchestrator

# ✓ Better - explicit import from actual location
from dispatch.orchestrator import DispatchOrchestrator
```

**Exception:** Importing multiple items from `dispatch` root is acceptable when using multiple classes from the same package:

```python
# ✓ Acceptable - multiple items from same package
from dispatch import EDIValidator, SendManager

# ✗ Avoid - single item import from root
from dispatch import EDIValidator
```

---

## Core Patterns

### 1. Pipeline Step Pattern

Standard interface for processing steps:

```python
from dispatch.pipeline.interfaces import PipelineStep

class MyStep(PipelineStep):
    def execute(self, input_path: str, context: dict) -> tuple[bool, str, list[str]]:
        """Execute the pipeline step.
        
        Returns:
            Tuple of (success, output_path, errors)
        """
        ...
```

### 2. Backend Pattern

All backends implement the same interface:

```python
def do(
    process_parameters: dict,  # Backend-specific config
    settings_dict: dict,      # Global settings
    filename: str,            # File to send
    disable_retry: bool = False,
) -> bool:
    """Send a file via backend.
    
    Returns:
        True if successful
    """
```

### 3. Converter Pattern

Converters receive a structured EDI process dict:

```python
def edi_convert(
    edi_process: dict,        # EDI processing context
    output_filename: str,      # Target output path
    settings_dict: dict,       # Global settings
    parameters_dict: dict,     # Converter-specific params
    upc_lookup: dict = None,   # UPC lookup table
) -> tuple[bool, str, list[str]]:
    """Convert EDI file to target format.
    
    Returns:
        Tuple of (success, output_path, errors)
    """
```

### 4. Error Handling Pattern

```python
from dispatch.error_handler import ErrorHandler

handler = ErrorHandler(errors_folder=errors_path)
handler.record_error(
    folder_id=folder.id,
    file_path=file_path,
    error_type="ValidationError",
    error_message="Invalid EDI format",
    stack_trace=traceback.format_exc(),
)
```

### 5. Logging Pattern

```python
from core.structured_logging import get_logger

logger = get_logger(__name__)

logger.info("Processing started", extra={"folder": folder.alias})
logger.debug("File discovered", extra={"path": file_path, "size": size})
logger.error("Backend failed", extra={"backend": "ftp", "retry": 2})
```

---

## Legacy & Compatibility

### Archive Directory (`archive/`)

Contains deprecated code kept for reference and potential rollback. **Do not import from here for new development.**

| Archived File | Superseded By | Migration Notes |
|--------------|--------------|-----------------|
| `dispatch_process.py` | `dispatch.orchestrator.DispatchOrchestrator` | Use instance-based API |
| `mtc_edi_validator.py` | `dispatch.edi_validator.EDIValidator` | Use class-based validator |
| `edi_tweaks.py` | `dispatch.pipeline.tweaker.EDITweakerStep` | Use pipeline step |
| `_dispatch_legacy.py` | `dispatch/orchestrator.py` | Refactored with DI |

### Compatibility Layer (`dispatch/compatibility.py`)

Provides backward-compatible imports with deprecation warnings for legacy code. **New code should import directly from dispatch package modules.**

```python
# Legacy (with deprecation warning)
from dispatch.compatibility import DispatchOrchestrator

# Modern (recommended)
from dispatch import DispatchOrchestrator
```

### Feature Flags (`dispatch/feature_flags.py`)

Runtime configuration via environment variables:

```python
from dispatch.feature_flags import get_feature_flags, set_feature_flag

flags = get_feature_flags()
if flags.get("DISPATCH_DEBUG_MODE"):
    logger.setLevel(logging.DEBUG)
```

---

## Testing

### Test Markers

| Marker | Purpose | Execution |
|--------|---------|-----------|
| `unit` | Fast unit tests | `pytest -m unit -n auto` |
| `integration` | Database/integration tests | `pytest -m integration -n auto` |
| `qt` | PyQt5 UI tests | `pytest -m qt -n0` (single-threaded) |
| `conversion` | Converter parity tests | `pytest -m conversion -n auto` |
| `backend` | Backend tests | `pytest -m backend -n auto` |
| `fast` | Tests <5 seconds | `pytest -m "unit and fast" -n auto` |

### Running Tests

```bash
# All tests (excludes Qt, parallel)
make test-parallel

# Qt tests only (single-threaded - required!)
make test-qt

# Unit tests
make test-unit

# Specific file
make test-file FILE=tests/unit/dispatch/test_orchestrator.py

# Fail-fast
make test-failfast
```

### Qt Test Rules

⚠️ **Qt tests MUST run single-threaded (`-n0`)** due to PyQt5 + pytest-xdist segfaults from worker thread cleanup.

```bash
# ✓ Correct
pytest tests/unit/interface/qt/ -n0

# ✗ Wrong (may segfault)
pytest tests/unit/interface/qt/ -n auto
```

---

## Common Tasks

### Where to look for common tasks:

| Task | Location | Notes |
|------|----------|-------|
| Add new UI dialog | `interface/qt/dialogs/` | Follow existing dialog patterns |
| Add new backend | `backend/` | Implement `do()` function, add to `BackendFactory` |
| Add new converter | `dispatch/converters/` | Implement `edi_convert()` function |
| Add pipeline step | `dispatch/pipeline/` | Implement `PipelineStep` protocol |
| Add folder operation | `interface/operations/folder_operations.py` | Use `DatabaseManager` for DB access |
| Modify EDI validation | `dispatch/edi_validator.py` | `EDIValidator` class |
| Modify file splitting | `core/edi/edi_splitter.py` | `split_edi_file()` function |
| Add database migration | `migrations/` | Follow versioned migration pattern |

### Adding a New Backend

1. Create `backend/my_backend.py` with `do()` function
2. Add to `send_manager.py` `BackendFactory` class
3. Register in `DispatchConfig` backend list
4. Add tests in `tests/unit/backend/`

### Adding a New Converter

1. Create `dispatch/converters/convert_to_format.py`
2. Implement `edi_convert()` function
3. Register in `dispatch/converters/__init__.py`
4. Add converter tests in `tests/convert_backends/`

---

## Anti-Patterns

| Pattern | Why Wrong | Correct Approach |
|---------|-----------|------------------|
| Import from `dispatch` root | Unclear source, breaks encapsulation | Import from `dispatch.module` explicitly |
| Business logic in UI widgets | Couples UI to logic, hard to test | Put logic in `interface/operations/` |
| Direct DB queries from widgets | Breaks MVC, tight coupling | Use controller → operations → DB manager |
| Qt tests with `-n auto` | Segfaults with pytest-xdist | Use `-n0` for Qt tests |
| Bare `# noqa` | Unjustified suppression | Always add justification comment |
| Hardcoded converter names | Reduces flexibility | Use dynamic import patterns |

---

## Version Constraints

- **Python:** 3.11 maximum (target system limitation)
- **Qt:** PyQt5 5.15 / Qt5 maximum (target system limitation)
- **Do NOT update** to Python 3.12+ or PyQt6/Qt6

---

*For project methodology and workflow, see `.clio/instructions.md`*
*For test suite details, see `tests/AGENTS.md`*
*For interface module details, see `interface/AGENTS.md`*
*For dispatch module details, see `dispatch/AGENTS.md`*