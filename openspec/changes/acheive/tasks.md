# Tasks: Achieve Backward Compatibility with Pre-Refactoring Version

**Principle:** Migrate code to modern paths rather than creating compatibility layers. Single code path, no duplication.

## 1. Audit Legacy Import Paths

- [ ] 1.1 Search codebase for imports from legacy root paths (`from dispatch import`, `from utils import`, etc.)
- [ ] 1.2 Identify all unique legacy module paths and the code that uses them
- [ ] 1.3 For each legacy import found, determine if it's:
  - **Core code** (dispatch/, interface/, backend/) - migrate immediately
  - **External script** (user's scripts) - document for user migration
  - **Test code** - migrate to modern imports
  - **Documentation example** - update documentation
- [ ] 1.4 Document findings in scratch/LEGACY_IMPORT_AUDIT.md

## 1b. Audit Converter Selection Logic

- [ ] 1b.1 Locate the original converter selection logic in archive/ or historical code
- [ ] 1b.2 Document the exact algorithm for format name to module mapping
- [ ] 1b.3 Document case sensitivity rules and format aliases
- [ ] 1b.4 Compare current implementation against original for any differences
- [ ] 1b.5 **CRITICAL: Fix any discrepancies between current and original converter selection**
- [ ] 1b.6 Document findings in scratch/CONVERTER_SELECTION_AUDIT.md

## 1c. Audit EDI Tweaks as Conversion Target

- [ ] 1c.1 Locate legacy `edi_tweaks.py` implementation in archive/
- [ ] 1c.2 Document the tweaks transformation logic (what it does to EDI files)
- [ ] 1c.3 Identify which customers currently use tweaks (database records)
- [ ] 1c.4 Document the UI/selection mechanism for "tweaks" format in original
- [ ] 1c.5 Verify tweaks transformation is preserved byte-for-byte in migration
- [ ] 1c.6 Document findings in scratch/EDI_TWEAKS_AUDIT.md

## 2. Migrate Core Code to Modern Imports

- [ ] 2.1 Update `dispatch/` internal imports to use package-relative paths
- [ ] 2.2 Update `backend/` internal imports to use modern paths
- [ ] 2.3 Update `interface/` internal imports to use modern paths
- [ ] 2.4 Verify no circular imports after migration
- [ ] 2.5 Run tests to verify functionality preserved

## 3. Migrate Test Code to Modern Imports

- [ ] 3.1 Update `tests/` imports to use modern paths
- [ ] 3.2 Verify all tests still pass
- [ ] 3.3 Remove any test-only compatibility shims

## 3b. Migrate EDI Tweaks to Converter Plugin

- [ ] 3b.1 Create `dispatch/converters/convert_to_tweaks.py` with `edi_convert()` function
- [ ] 3b.2 Port tweaks transformation logic from legacy `edi_tweaks.py`
- [ ] 3b.3 Verify output matches original tweaks implementation exactly
- [ ] 3b.4 Add converter to plugin discovery (format name: "tweaks")
- [ ] 3b.5 Ensure "tweaks" appears in format selection dropdown in UI
- [ ] 3b.6 Test that customers with existing tweak configurations can still process files

## 4. Update Documentation Examples

- [ ] 4.1 Update import examples in docs/*.md to use modern paths
- [ ] 4.2 Update README.md import examples
- [ ] 4.3 Update docstrings that reference legacy paths

## 5. Remove or Simplify Compatibility Layer

- [ ] 5.1 Review `dispatch/compatibility.py` for still-needed functions
- [ ] 5.2 Keep only utility functions that have no modern equivalent
- [ ] 5.3 Remove `__getattr__` lazy loading (no longer needed)
- [ ] 5.4 Simplify deprecation warnings if any remain

## 6. Delete Legacy Root Modules

- [ ] 6.1 Identify which legacy root modules have no remaining users
- [ ] 6.2 For modules with external users, create minimal aliases OR document migration path
- [ ] 6.3 Delete legacy root modules where possible:
  - `dispatch.py` (if no external users)
  - `utils.py` (if no external users)
  - `edi_validator.py` (if no external users)
  - `schema.py` (if no external users)
  - `create_database.py` (if no external users)
- [ ] 6.4 **Note: `edi_tweaks.py` is NOT deleted - it's migrated to `dispatch/converters/convert_to_tweaks.py`**
- [ ] 6.5 Verify deleted files don't break anything

## 7. Verify dispatch/ Package is Complete

- [ ] 7.1 Ensure `dispatch/__init__.py` exports all needed symbols
- [ ] 7.2 Verify `dispatch/` package is self-contained
- [ ] 7.3 Check for any missing exports that were in legacy files
- [ ] 7.4 Add any missing exports to `dispatch/__init__.py`

## 8. Create Migration Guide

- [ ] 8.1 Document legacy-to-modern import mappings for users
- [ ] 8.2 Create scratch/MIGRATION_GUIDE.md with step-by-step instructions
- [ ] 8.3 Document any configuration changes needed

## 9. Integration Testing

- [ ] 9.1 Run full test suite to verify migration completeness
- [ ] 9.2 Test application startup via `main_interface.py`
- [ ] 9.3 Test headless/automatic mode via `main_interface.py -a`
- [ ] 9.4 Verify database migration works with existing databases
- [ ] 9.5 **CRITICAL: Verify all user preferences are preserved after schema upgrades**
- [ ] 9.6 **CRITICAL: Verify renamed columns/tables update all references in stored preferences**

## 9b. Database Migration Preference Preservation

- [ ] 9b.1 Review all database migration scripts for column/table renames
- [ ] 9b.2 Verify each rename includes migration to update stored preferences
- [ ] 9b.3 Test database with existing preferences from earlier version
- [ ] 9b.4 Verify format names in folder records migrate correctly (e.g., "tweaks" format preserved)
- [ ] 9b.5 Document database migration behavior in scratch/DB_MIGRATION_AUDIT.md

## 9c. Python 3.11 and Qt5 Compatibility Verification

- [ ] 9c.1 Verify all dependencies support Python 3.11 (no 3.12+ requirements)
- [ ] 9c.2 Verify PyQt5 is the maximum Qt version (no PyQt6)
- [ ] 9c.3 Run tests on Python 3.11 target environment
- [ ] 9c.4 Verify GUI renders correctly on Qt5
- [ ] 9c.5 Document version constraints in requirements.txt

## 9d. PyInstaller Windows Build Configuration

- [ ] 9d.1 Verify `main_interface.spec` includes all required hidden imports
- [ ] 9d.2 Verify `Dockerfile.windows.build` uses Python 3.11
- [ ] 9d.3 Test PyInstaller build via Docker container (`batonogov/pyinstaller-windows:v4.0.1`)
- [ ] 9d.4 Verify built executable runs on Windows target
- [ ] 9d.5 Document Docker build process in scratch/BUILD_GUIDE.md

## 10. Final Cleanup

- [ ] 10.1 Remove any remaining compatibility shims
- [ ] 10.2 Clean up import statements across codebase
- [ ] 10.3 Update AGENTS.md with final import conventions
- [ ] 10.4 Verify all tests pass
- [ ] 10.5 Commit changes with clear migration documentation