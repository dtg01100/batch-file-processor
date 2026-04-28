# Proposal: Achieve Backward Compatibility with Pre-Refactoring Version

## Why

The codebase has undergone extensive refactoring (PyQt5 migration, module reorganization, service extraction). While a previous compatibility verification (March 2026) confirmed API stability for the recent changes, a gap exists: **the current architecture requires imports from refactored package paths** (e.g., `dispatch.orchestrator`, `dispatch.services.file_processor`) rather than the **original module paths** (e.g., `dispatch.py`, `dispatch.file_processor`, `utils.py`).

External scripts, integrations, and documentation may reference these legacy paths, making the current version incompatible as a drop-in replacement.

## What Changes

1. **Audit legacy import usage** - Find all code using old import paths
2. **Migrate internal code to modern imports** - Update dispatch/, backend/, interface/, tests/
3. **Migrate EDI tweaks to conversion target** - "tweaks" becomes a first-class format like "scannerware" or "csv"
4. **Delete legacy root modules** - Remove `dispatch.py`, `utils.py`, etc. where no external users
5. **Update documentation** - Fix import examples to show modern paths
6. **Simplify compatibility layer** - Keep only utility functions in `dispatch/compatibility.py`

## Capabilities

### New Capabilities

- **Tweaks as Conversion Target**: EDI tweaks become a first-class conversion format selectable in the UI (format: "tweaks")
- **Migration Audit**: Complete inventory of legacy import paths and their usage
- **Modern Import Convention**: Single code path using `dispatch.orchestrator`, `dispatch.edi_validator`, etc.

### Modified Capabilities

- **Module Import Compatibility**: Legacy imports are migrated, not preserved with deprecation warnings
- **dispatch/__init__.py**: Ensures all needed symbols are exported for modern imports
- **EDI Tweaks**: Transitioned from standalone `edi_tweaks.py` to `convert_to_tweaks.py` in the converter plugin system

### Constraints

- **Python 3.11 maximum**: Target system only supports Python 3.11 - no newer versions
- **Qt5 maximum**: Target system only supports Qt5 - no Qt6 or newer
- **PyInstaller via Docker**: Windows executable built using `batonogov/pyinstaller-windows` Docker container

## Build Configuration

### Docker Build

Windows executable is built using the `batonogov/pyinstaller-windows:v4.0.1` Docker container:

```bash
docker build -f Dockerfile.windows.build -t batch-file-processor .
```

### Build Artifacts

| File | Purpose |
|------|---------|
| `Dockerfile.windows.build` | Multi-stage Docker build targeting Python 3.11 |
| `main_interface.spec` | PyInstaller spec with all hidden imports |
| `Dockerfile` | Linux development environment (Python 3.11) |

### Spec File Requirements

The `main_interface.spec` must explicitly list hidden imports because PyInstaller cannot detect them from:
- Dynamic imports (e.g., `importlib.import_module()`)
- Module-level string operations
- Qt signal/slot connections

Required hidden imports include:
- All PyQt5 modules (QtCore, QtGui, QtWidgets, QtNetwork, etc.)
- All backend modules (database, FTP, SMTP, copy)
- All converters in `dispatch.converters.*`
- Archive modules for legacy compatibility

## Impact

### Affected Code
- `dispatch/` (internal imports - migrate to package-relative)
- `backend/` (internal imports - migrate)
- `interface/` (internal imports - migrate)
- `tests/` (test imports - migrate)
- `docs/` (documentation examples - update)

### Removed Files
- Potentially: `dispatch.py`, `utils.py`, `edi_tweaks.py`, `edi_validator.py`, `schema.py`, `create_database.py`

### Systems
- Module import resolution (simplified - one path per symbol)
- Test suite (updated imports)
- Documentation (updated examples)