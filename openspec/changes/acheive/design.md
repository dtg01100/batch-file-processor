# Design: Achieve Backward Compatibility with Pre-Refactoring Version

## Context

### Background

The batch-file-processor codebase underwent significant refactoring:
1. **Tkinter → PyQt5 migration**: GUI layer rewritten
2. **Module reorganization**: Single files split into packages (`dispatch/`, `backend/`, `interface/`)
3. **Service extraction**: Mixins converted to composition (CustomerLookupService, UOMLookupService, etc.)
4. **Pipeline architecture**: Procedural processing replaced with step-based pipeline

### Current State

- Modern modules at `dispatch/*.py`, `backend/*.py` paths
- `dispatch/` package has `__init__.py` with all public exports
- `dispatch/compatibility.py` exists with some legacy mappings
- No legacy root modules (`dispatch.py`, `utils.py`, etc.) exist
- Archive contains legacy implementations (dispatch_process.py, edi_tweaks.py)

### Constraints

- Cannot break existing `dispatch/` package imports (already refactored code)
- Must not introduce circular import dependencies
- Database must remain usable across schema versions
- **Converter selection MUST match the original implementation exactly - no exceptions**
- **Plugin parameter passing MUST match the original implementation exactly - no exceptions**
- **Python 3.11 and Qt5 are the maximum supported versions on target system - no newer versions**

## Goals

1. **Zero-breaking-change migration**: Existing code using old import paths continues to work
2. **Clear deprecation path**: Warnings guide users to modern import paths
3. **Minimal maintenance burden**: Re-export modules are thin wrappers, not duplicated logic
4. **Full test coverage**: Verification that all legacy paths work

## Non-Goals

1. **No preservation of implementation**: Use modern code paths, just re-export
2. **No permanent compatibility layer**: Deprecation warnings indicate these will be removed
3. **No Tkinter restoration**: GUI remains PyQt5 only
4. **No runtime behavior changes**: Only import paths change
5. **No Python 3.12+ or Qt 6.x support**: Target system is limited to Python 3.11 and Qt5

## CRITICAL CONSTRAINTS

### Converter Selection

**Converter selection MUST match the original implementation byte-for-byte.**

Any changes to how converters are selected will break existing workflows:

- **Format name to module mapping** SHALL be identical to original (e.g., "scannerware" → `convert_to_scannerware.py`)
- **Case sensitivity** SHALL be preserved exactly (e.g., "Scannerware" → `convert_to_Scannerware.py`)
- **Format alias resolution** SHALL work identically (e.g., "edi" → "810")
- **Error messages** for unrecognized formats SHALL be identical to original

### Plugin Parameter Passing

**Plugin parameter order, types, and default values SHALL match the original exactly.**

- `edi_convert(edi_process, output_filename, settings_dict, parameters_dict, upc_lookup)`
- `do(process_parameters, settings_dict, filename)`

### EDI Tweaks as Conversion Target

**"tweaks" MUST be a first-class conversion format selectable by users.**

- Customers who have applied EDI tweaks historically SHALL continue to do so
- The tweaks transformation MUST be selectable as format "tweaks" in the UI (like "scannerware", "csv")
- The converter plugin pattern SHALL be used: `convert_to_tweaks.py` with `edi_convert()` function
- The legacy `edi_tweaks.py` SHALL be migrated to the converter plugin architecture

### Database Migration Preserves Preferences

**Database upgrades MUST preserve all user preferences and settings.**

- **If something is renamed in the schema, the database migration MUST follow** and update stored values accordingly
- Column renames: migration updates all preferences referencing old column
- Table renames: migration updates all references and foreign keys
- Format name changes: migration updates all folder records with old format name
- All preference values SHALL be preserved exactly; only structural changes are applied
- Cascading updates for entities with dependencies (foreign keys, references)

### PyInstaller Windows Build

**The project is packaged for Windows using PyInstaller via the `batonogov/pyinstaller-windows` Docker container.**

- Build configuration: `Dockerfile.windows.build` with Python 3.11
- Spec file: `main_interface.spec` with all required hidden imports
- All dynamic imports (plugin discovery) MUST be explicitly listed in hiddenimports

**Critical hidden imports required:**
- All PyQt5 modules (QtCore, QtGui, QtWidgets, QtNetwork, QtSvg, QtXml, QtPrintSupport, sip)
- All backend modules (database_obj, ftp_client, smtp_client, copy_backend, email_backend, ftp_backend)
- All converter plugins in `dispatch.converters.*`
- Archive modules for legacy compatibility

## Decisions

### Decision 1: Migrate legacy paths to modern code, not re-export

**Choice:** When a legacy import path is needed, update the code at that path to use modern modules directly.

**Rationale:**
- Single source of truth: logic lives in one place
- No duplicate code, no wrapper maintenance
- Clear migration path - code moves, doesn't copy
- Consistent with the refactoring that already happened

**Example:**
Instead of:
```python
# dispatch.py (re-export wrapper with deprecation)
from dispatch.orchestrator import DispatchOrchestrator
```

Do this:
```python
# dispatch.py (deleted - file no longer exists)
# OR: dispatch.py becomes identical to dispatch/__init__.py via import
```

Or better yet, update external scripts to use the modern path directly.

### Decision 2: Remove legacy files where possible

**Choice:** Where legacy import paths are not used by core code, remove the legacy files entirely.

**Rationale:**
- No dead code to maintain
- Forces all code to use modern paths
- Easier to understand codebase

**Exception:** Files that exist and are used by external scripts or documented in user guides.

### Decision 3: Migration rather than compatibility layer

**Choice:** Instead of adding `__getattr__` to emit deprecation warnings, migrate the actual imports to modern paths.

**Rationale:**
- Deprecated code paths are removed, not maintained
- Developers always use modern paths
- Cleaner codebase
- No confusion about "which path should I use?"

### Decision 4: Consolidate to dispatch/ package

**Choice:** All dispatch logic lives in the `dispatch/` package. Legacy files at project root either:
- Import from `dispatch/` and re-export (temporary)
- Are deleted (preferred)

**Rationale:**
- `dispatch/` is the canonical location post-refactoring
- Archive contains historical snapshots for reference
- No split between "new" and "old" dispatch code

## Architecture

### After Migration

```
Project Root
├── main_interface.py    # Entry point (exists, no change)
├── main_qt.py           # Alias to main_interface (exists, no change)
├── dispatch.py          # DELETED - imports now use dispatch/ package
├── utils.py             # DELETED - imports now use dispatch/ or core/ packages
├── edi_tweaks.py        # DELETED - migrated to dispatch/converters/convert_to_tweaks.py
├── edi_validator.py     # DELETED - imports now use dispatch.edi_validator
├── schema.py            # DELETED - imports now use core.database.schema
├── create_database.py   # DELETED - imports now use core.database.manager
│
├── dispatch/            # Modern package (canonical location)
│   ├── __init__.py      # Public API exports
│   ├── orchestrator.py  # Core orchestration
│   ├── compatibility.py # Config format conversion utilities
│   ├── converters/     # Conversion targets (scannerware, csv, tweaks, etc.)
│   │   ├── convert_to_scannerware.py
│   │   ├── convert_to_csv.py
│   │   └── convert_to_tweaks.py  # <-- EDI tweaks as first-class format
│   └── ...
│
└── archive/             # Historical snapshots (reference only, not used)
```

### Migration Pattern

For each legacy import path found:

1. **Find the code** using the legacy path
2. **Identify the modern equivalent** in `dispatch/` package
3. **Update the code** to import from the modern path
4. **Remove the legacy file** if no other code uses it

### Example Migration

Before:
```python
# Old script.py
from dispatch import DispatchOrchestrator
orch = DispatchOrchestrator()
```

After (Option A - Update script):
```python
# script.py (updated)
from dispatch.orchestrator import DispatchOrchestrator
orch = DispatchOrchestrator()
```

After (Option B - Keep dispatch.py as alias):
```python
# dispatch.py (minimal alias to dispatch package)
"""Dispatch package - re-exports dispatch/ for import compatibility."""
from dispatch import *  # noqa: F401, F403
```

But Option B is discouraged - prefer Option A to have single code path.

## Risks and Trade-offs

### Risk: Breaking existing code

**Description:** Migrating to modern imports may break external scripts that rely on legacy paths.

**Mitigation:**
- Audit all usage before making changes
- Provide migration guide for external users
- Only delete files with no external users
- Update documentation to show modern paths

### Trade-off: One-time migration effort

**Description:** All code using legacy imports needs to be updated.

**Mitigation:**
- Task list breaks into manageable phases
- Can be done incrementally
- Single code path is cleaner long-term

### Risk: Missing some usages during audit

**Description:** Audit might miss some code using legacy paths.

**Mitigation:**
- Run tests after each change to catch breakage
- Grep for import patterns across entire codebase
- Check documentation examples

### Risk: Converter selection mismatch

**Description:** Current converter selection logic might differ from original implementation.

**Mitigation:**
- Compare against archive/history to verify exact algorithm
- Run existing converter tests to verify behavior
- If discrepancies found, restore original algorithm (no changes allowed)

### Non-issue: No deprecation warnings

**Rationale:** We are not keeping legacy paths with deprecation warnings - we are migrating code to modern paths. This eliminates the warning noise concern entirely.

## Implementation Approach

### Phase 1: Audit (understand what exists)

1. Search for all imports from legacy root paths
2. Categorize by usage: core code, tests, external scripts, documentation
3. Document findings

### Phase 2: Migrate (update code to modern imports)

1. Update internal imports in dispatch/, backend/, interface/
2. Update test imports
3. Update documentation examples

### Phase 3: Remove (delete legacy files)

1. Delete legacy root modules where possible
2. Verify no breaking changes

### Phase 4: Verify (ensure everything works)

1. Run full test suite
2. Verify application starts
3. Document any remaining compatibility needs

## Testing Strategy

1. **Import tests**: Verify modern paths work correctly (no legacy paths to test)
2. **Functional tests**: Verify imported objects work correctly after migration
3. **Database tests**: Verify migration from old schema versions still works
4. **Integration tests**: Verify full processing pipeline works with modern imports
5. **Application startup tests**: Verify `main_interface.py` starts correctly