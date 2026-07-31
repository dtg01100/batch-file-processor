# Batch File Processor — Technical Reference

**Version:** 1.2 | **Last Updated:** 2026-05-18
**Purpose:** Development guide for contributors and maintainers

> **Development Philosophy:** There is no time limit. It is more important to do things correctly than to do them quickly. Take the time to understand the codebase, follow patterns, and ensure changes are robust and maintainable.

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
│                              USER (Qt GUI)                                  │
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
| **interface/** | Qt GUI layer (PySide6 binding; PyQt5 is legacy) | `qt/app.py`, `qt/main_window.py`, `application_controller.py` |
| **interface/qt/** | Qt widgets and dialogs | `dialogs/`, `widgets/`, `theme.py`, `run_coordinator.py` |
| **interface/models/** | Data models (dataclasses) | `folder_configuration.py` |
| **interface/operations/** | Business logic | `folder_operations.py`, `processing.py`, `maintenance.py` |
| **interface/database/** | Database access | `database_manager.py`, `Table` wrapper |
| **dispatch/** | Core file processing | `orchestrator.py`, `send_manager.py`, `edi_validator.py`, `results.py` |
| **dispatch/services/** | Processing services | `file_processor.py`, `folder_processor.py` |
| **dispatch/pipeline/** | Pipeline steps | `validator.py`, `splitter.py`, `converter.py` |
| **dispatch/converters/** | 17 format converters | `convert_to_csv.py`, `convert_to_scannerware.py`, etc. |
| **backend/** | Output backends | `email_backend.py`, `ftp_backend.py`, `copy_backend.py`, `http_backend.py` |
| **core/** | Shared utilities | `structured_logging.py`, `constants.py`, `exceptions.py` |
| **core/edi/** | EDI parsing | `edi_parser.py`, `edi_splitter.py`, `edi_tweaker.py` |
| **core/database/** | Database layer | SQLite adapter and repositories |
| **adapters/** | Database adapters | `adapters/sqlite/` (current), `adapters/db2ssh/` (production) |
| **tests/** | Test suite | `unit/`, `integration/`, `qt/`, `convert_backends/` |

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

**Always include `exc_info=True`** when logging exceptions, even in "non-fatal" handlers:

```python
except Exception:
    # Errors in error recording are silently ignored to avoid cascading failures.
    # The original error is already logged or will be recorded via other paths.
    logger.debug(
        "Failed to dispatch error alert (non-fatal)",
        exc_info=True,
        extra={"folder_alias": (context or {}).get("folder_alias", "")},
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

### Removed/Migrated Components

The following components have been removed or migrated. References to them in old code should be updated:

| Former File/Component | Replacement | Migration Notes |
|----------------------|-------------|-----------------|
| `dispatch.pipeline.tweaker.EDITweakerStep` | Use `convert_to_format='tweaks'` in converter | Tweak logic moved to `dispatch/converters/convert_to_tweaks.py` |
| Legacy `dispatch_process.py` | `dispatch.orchestrator.DispatchOrchestrator` | Use instance-based API |
| Legacy `mtc_edi_validator.py` | `dispatch.edi_validator.EDIValidator` | Use class-based validator |

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
| `qt` | Qt UI tests (PySide6) | `pytest -m qt -n0` (single-threaded) |
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

⚠️ **Qt tests MUST run single-threaded (`-n0`)** due to PySide6 + pytest-xdist segfaults from worker thread cleanup.

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
| Import from `dispatch` root (single item) | Unclear source, breaks encapsulation | Import from `dispatch.module` explicitly; multiple items is OK |
| Business logic in UI widgets | Couples UI to logic, hard to test | Put logic in `interface/operations/` |
| Direct DB queries from widgets | Breaks MVC, tight coupling | Use controller → operations → DB manager |
| Qt tests with `-n auto` | Segfaults with pytest-xdist | Use `-n0` for Qt tests |
| Bare `# noqa` | Unjustified suppression | Always add justification comment |
| Hardcoded converter names | Reduces flexibility | Use dynamic import patterns |
| Silent `except: pass` | Hides errors from debugging | Use `logger.debug(..., exc_info=True)` |
| Tuple-return lambda trick `(expr, None)[1]` | Obfuscatory | Use named helper function |
| Nested try/except pyramid (3+ levels) | Hard to follow | Use `stage` variable with single try/except |
| Bare `MagicMock()` without spec | Auto-creates any attribute, hides typos | Use `MagicMock(spec=ProtocolOrClass)` |
| getattr for private `_conn` without hasattr check | MagicMock returns new MagicMock for any attr | Use `hasattr(type(obj), "attr")` pattern |
| Magic padding `"00" + x` | Locale-dependent, unreadable | Use `x.zfill(2)` or `f"{x:02d}"` |

---

## Bug-Hunting Checklist

When auditing code, check for:

1. **Silent exception swallowing** — `except Exception: pass` without logging
2. **File handle leaks** — Files opened without context manager or try/finally
3. **DB recording failures** — Processing succeeds but DB write fails silently (causes reprocessing)
4. **Magic padding in string formatting** — `"00" + x` instead of `x.zfill(2)` or `f"{x:02d}"`
5. **getattr on unknown objects** — Without hasattr check, MagicMock auto-creates attrs
6. **Dead code in mocks** — spec= catches methods that don't exist on real objects
7. **Lambda returning None implicitly** — Use explicit `return None` or named function
8. **Awkward workarounds** — Tuple tricks, monkeypatching stdlib, etc.
9. **Bare MagicMock()** — Use spec= to catch typos and undefined attributes at test time

---

## Version Constraints

- **Python:** 3.11+ (pyproject.toml requires-python = ">=3.11"; black/ruff target = py313)
- **Qt:** PySide6 >= 6.5.0, < 6.12 (PyQt5 is legacy; see `scripts/mover.py` for the one remaining PyQt5 user)

---

*For project methodology and workflow, see `.clio/instructions.md`*
*For test suite details, see `tests/AGENTS.md`*
*For interface module details, see `interface/AGENTS.md`*
*For dispatch module details, see `dispatch/AGENTS.md`*