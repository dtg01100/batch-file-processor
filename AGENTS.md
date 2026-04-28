# AGENTS.md

**Version:** 1.0
**Date:** 2026-04-28
**Purpose:** Technical reference for batch-file-processor development

---

## Project Overview

**batch-file-processor** is a Python/PyQt5 GUI application for processing EDI/batch files with email, FTP, and copy backends.

- **Language:** Python 3.11+ (tested with 3.13)
- **GUI Framework:** PyQt5 5.15
- **Architecture:** MVC with service layer, pipeline-based processing
- **Testing:** pytest with 1300+ tests

---

## Quick Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run GUI application
./.venv/bin/python interface/qt/app.py

# Run in automatic/headless mode
./.venv/bin/python interface/qt/app.py -a

# Run tests
./.venv/bin/pytest tests/

# Run tests excluding Qt tests (faster)
./.venv/bin/pytest -m "not qt" -n auto
```

## Version Constraints

**CRITICAL: This project targets Python 3.11 and Qt5.**

- **Python 3.11** is the maximum supported version (target system does not support 3.12+)
- **Qt5/PyQt5** is the maximum supported version (target system does not support Qt6)
- Do NOT update to Python 3.12, 3.13, or newer
- Do NOT update to PyQt6 or Qt6

## PyInstaller Windows Build

This project is packaged for Windows using PyInstaller via the `batonogov/pyinstaller-windows` Docker container.

### Build Files

| File | Purpose |
|------|---------|
| `Dockerfile.windows.build` | Docker build file for Windows executable |
| `main_interface.spec` | PyInstaller spec file for Windows build |
| `Dockerfile` | Linux dev environment (Python 3.11) |

### Build Process

```bash
# Build Windows executable via Docker
docker build -f Dockerfile.windows.build -t batch-file-processor .

# Output: dist/Batch File Sender.exe
```

### Spec File Details

The `main_interface.spec` file includes:
- All PyQt5 modules (QtCore, QtGui, QtWidgets, QtNetwork, etc.)
- All backend modules (email, FTP, copy)
- All dispatch converters (scannerware, csv, tweaks, etc.)
- All interface modules (Qt dialogs, operations, services)

### Hidden Imports

PyInstaller cannot detect these imports automatically, so they are explicitly listed:
- PyQt5.sip and all Qt modules
- All backend modules (database, FTP, SMTP, copy)
- All converters in `dispatch.converters.*`
- Archive modules for legacy support

---

## Architecture

```
User Input (PyQt5 GUI)
    |
    v
interface/qt/app.py (Main Application)
    |
    v
dispatch/orchestrator.py (DispatchOrchestrator)
    |
    +-- dispatch/services/file_processor.py (FileProcessor)
    |       |
    |       +-- dispatch/edi_validator.py (EDI Validation)
    |       +-- dispatch/converters/* (Format Conversion)
    |       +-- backend/* (Email, FTP, Copy, HTTP)
    |
    v
Results → interface/models → PyQt5 UI Updates
```

---

## Directory Structure

| Path | Purpose |
|------|---------|
| `interface/` | PyQt5 GUI application layer |
| `interface/qt/` | Qt widgets, dialogs, main app |
| `interface/models/` | Data models (Folder, ProcessedFile, Settings) |
| `interface/operations/` | Business logic operations |
| `interface/plugins/` | Plugin system for extensions |
| `dispatch/` | Core file processing orchestration |
| `dispatch/pipeline/` | Pipeline step interfaces and adapters |
| `dispatch/services/` | File and folder processing services |
| `dispatch/converters/` | 10+ format converters |
| `backend/` | Output backends (email, FTP, copy, HTTP) |
| `core/` | Shared utilities, constants, structured logging |
| `core/edi/` | EDI parsing and validation |
| `core/database/` | Database layer |
| `tests/` | Test suite (see `tests/AGENTS.md`) |

---

## Code Style

### Python Conventions

- **Line length:** 88 characters (Black formatter)
- **Indentation:** 4 spaces (no tabs)
- **Type hints:** Required for function signatures
- **Docstrings:** Google style for public APIs

### noqa Comments — Always Justify

When adding `# noqa` suppressions, always include a justification comment explaining **why** the suppression is needed. Never leave a bare `# noqa`.

**Good:**
```python
context: dict[str, Any],  # noqa: ARG001 - required by PipelineStep protocol but unused by adapter
```

**Bad:**
```python
context: dict[str, Any],  # noqa: ARG001
```

### Justification Requirements by Error Type

| Error Code | Meaning | When Appropriate |
|------------|---------|-----------------|
| `ARG001` | Unused argument | Required by protocol/interface but not used in implementation |
| `FBT001/FBT003` | Qt boolean-to-int conversion | Qt signal handlers that require specific signatures |
| `N802` | Qt method override naming | Qt method overrides using Qt conventional parameter names |
| `E402` | Module import at module level | Backward compatibility re-exports |
| `F401` | Unused import | Re-exports for backward compatibility |
| `BLE001` | Bare except clause | Intentional exception fallthrough in logging |
| `type: ignore[arg-type]` | PyQt5 stub incompatibilities | PyQt5 type stubs are incorrect, code works at runtime |

### Resolution Before Suppression

Always try to fix the underlying issue first. Suppressions should be a last resort when:
- The code is correct but linter/type checker is wrong
- External API requires specific signatures
- Type stubs are incorrect (document which)

---

## Module Naming Conventions

| Prefix | Purpose | Examples |
|--------|---------|----------|
| `interface/qt/` | Qt widgets and dialogs | `app.py`, `main_window.py`, `run_coordinator.py` |
| `interface/models/` | Data models | `folder.py`, `processed_file.py` |
| `interface/operations/` | Business logic | `folder_operations.py`, `processed_files.py` |
| `dispatch/` | Core processing | `orchestrator.py`, `send_manager.py` |
| `dispatch/services/` | Processing services | `file_processor.py`, `folder_processor.py` |
| `dispatch/converters/` | Format converters | `convert_to_csv.py`, `convert_to_scannerware.py` |
| `backend/` | Output backends | `email_backend.py`, `ftp_backend.py`, `copy_backend.py` |
| `core/` | Shared utilities | `structured_logging.py`, `constants.py` |

---

## Testing

### Before Committing

```bash
# Run all tests (excluding Qt)
make test-parallel

# Run unit tests only
make test-unit

# Run fast unit tests
make test-unit-fast

# Run Qt tests (single-threaded required)
make test-qt

# Run specific test file
make test-file FILE=tests/unit/test_utils.py

# Run tests with fail-fast
make test-failfast
```

### Qt Tests

Qt tests **MUST** be run with `-n0` (single-threaded) because PyQt5 widgets with background threads cause segfaults with pytest-xdist parallel execution.

```bash
# Correct
./.venv/bin/pytest tests/unit/interface/qt/ -n0

# Wrong (may cause segfaults)
./.venv/bin/pytest tests/unit/interface/qt/ -n auto
```

### Test Markers

| Marker | Purpose |
|--------|---------|
| `unit` | Unit tests (fast, isolated) |
| `integration` | Integration tests |
| `qt` | Qt UI tests (single-threaded) |
| `conversion` | File conversion tests |
| `backend` | Backend tests (FTP, Email, Copy) |
| `dispatch` | Dispatch/orchestration tests |
| `fast` | Fast tests (<5 seconds) |
| `slow` | Slow tests (>30 seconds) |

---

## Commit Format

```
type(scope): brief description

Problem: What was broken/incomplete
Solution: How you fixed it
Testing: How you verified the fix
```

**Types:** `feat`, `fix`, `refactor`, `docs`, `test`, `chore`

**Example:**

```bash
git add -A
git commit -m "fix(dispatch): resolve retry logic in FTP backend

Problem: time.sleep was being patched on wrong module
Solution: Patched backend_base.time.sleep instead
Testing: All retry tests pass, integration verified"
```

---

## Development Tools

### Common Commands

```bash
# Run GUI
./.venv/bin/python interface/qt/app.py

# Run headless
./.venv/bin/python interface/qt/app.py -a

# Install package
./.venv/bin/pip install -e .

# Run linter
ruff check .

# Format code
black .

# Type check
mypy .
```

---

## Common Patterns

### Pipeline Step Pattern

```python
class PipelineStep(Protocol):
    def execute(self, input_path: str, context: dict) -> tuple[bool, str, list[str]]:
        """Execute the pipeline step.
        
        Args:
            input_path: Path to input file
            context: Processing context with settings
            
        Returns:
            Tuple of (success, output_path, errors)
        """
        ...

# Adapter for existing functions
def wrap_as_pipeline_step(func):
    def execute(self, input_path: str, context: dict):
        return func(input_path, context), input_path, []
    return execute
```

### Backend Pattern

```python
def do(
    process_parameters: dict,
    settings_dict: dict,
    filename: str,
    disable_retry: bool = False,
) -> bool:
    """Send a file via backend.
    
    Args:
        process_parameters: Backend-specific parameters
        settings_dict: Global settings
        filename: File to send
        disable_retry: Skip retry logic (for testing)
        
    Returns:
        True if successful
    """
    backend = MyBackend(disable_retry=disable_retry)
    return backend.send(process_parameters, settings_dict, filename)
```

---

## Documentation

### Module Documentation

Each module should have:
- Module docstring explaining purpose
- Class docstrings with Attributes section
- Method docstrings with Args, Returns sections

### What Needs Documentation

| Change Type | Required Documentation |
|-------------|----------------------|
| New module | Docstring + AGENTS.md update |
| API change | Update docstrings + changelog |
| New feature | Update relevant AGENTS.md section |
| Backend change | Update `backend/` section in AGENTS.md |

### Documentation Files

| File | Purpose |
|------|---------|
| `AGENTS.md` | This file - technical reference |
| `interface/AGENTS.md` | Interface module details |
| `dispatch/AGENTS.md` | Dispatch module details |
| `tests/AGENTS.md` | Test suite details |

---

## Anti-Patterns (What NOT To Do)

| Anti-Pattern | Why It's Wrong | What To Do |
|--------------|----------------|------------|
| Use `python` instead of `.venv/bin/python` | Wrong Python environment | Always use `.venv/bin/python` |
| Run Qt tests with `-n auto` | Causes segfaults | Use `-n0` for Qt tests |
| Skip pytest markers | Loses test categorization | Use `-m` markers appropriately |
| Use bare `# noqa` | Unclear why linting is suppressed | Always justify noqa comments |
| Import from `dispatch` root | Old pattern, breaks encapsulation | Import from `dispatch.module` |
| Hardcode converter/backend names | Reduces flexibility | Use dynamic import patterns |

---

## PyInstaller Windows Build

The project is packaged for Windows using PyInstaller via the `batonogov/pyinstaller-windows:v4.0.1` Docker container.

### Build Files

| File | Purpose |
|------|---------|
| `Dockerfile.windows.build` | Docker build file targeting Python 3.11 |
| `main_interface.spec` | PyInstaller spec with all hidden imports |
| `Dockerfile` | Linux development environment |

### Build Process

```bash
# Build Windows executable via Docker
docker build -f Dockerfile.windows.build -t batch-file-processor .

# Output: dist/Batch File Sender.exe
```

### Spec File Requirements

The `main_interface.spec` explicitly lists hidden imports because PyInstaller cannot detect them from:
- Dynamic imports (`importlib.import_module()`)
- Plugin discovery patterns
- Qt signal/slot connections

**Required hidden imports:**
- PyQt5 modules: QtCore, QtGui, QtWidgets, QtNetwork, QtSvg, QtXml, QtPrintSupport, sip
- Backend modules: database_obj, ftp_client, smtp_client, copy_backend, email_backend, ftp_backend
- Converters: All modules in `dispatch.converters.*`
- Archive: Legacy modules for backward compatibility

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `./.venv/bin/python interface/qt/app.py` | Run GUI |
| `./.venv/bin/python interface/qt/app.py -a` | Run headless |
| `./.venv/bin/pytest tests/ -m "not qt"` | Run tests (no Qt) |
| `./.venv/bin/pytest tests/unit/interface/qt/ -n0` | Run Qt tests |
| `make test-unit` | Unit tests |
| `make test-qt` | Qt tests (single-threaded) |
| `ruff check .` | Lint code |
| `black .` | Format code |

---

*For project methodology and workflow, see .clio/instructions.md*
