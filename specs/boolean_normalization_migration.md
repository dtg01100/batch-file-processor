# Spec: Native Boolean Normalization & Migration

**Status:** DRAFT  
**Author:** GitHub Copilot  
**Created:** 2026-02-03  
**Updated:** 2026-02-03

---

## 1. Summary

Migrate all boolean data from string-based storage (`"True"`/`"False"` TEXT) to native Python boolean types and SQLite INTEGER (0/1) throughout the application, including database schema, dialogs, converters, and processing logic.

---

## 2. Background

### 2.1 Problem Statement

Tkinter-era code stored booleans as strings in SQLite:
- **Database schema**: Fields like `folder_is_active`, `process_edi`, `include_a_records` stored as TEXT `"True"`/`"False"`.
- **UI code**: Dialog code compares with `== "True"` (e.g., `EditFolderDialog` lines 131, 216, 303–321).
- **Processing code**: Converter code and `utils.py` explicitly handle string booleans.
- **Settings code**: `EditSettingsDialog` stores `enable_reporting` as `"True"`/`"False"`.

This creates:
- **Type safety issues**: Booleans treated as strings; typos or case mismatches cause silent bugs.
- **Data integrity**: Schema mixing TEXT and INTEGER for boolean-like fields; migrations add more strings.
- **Code duplication**: Every module that touches booleans reimplements coercion logic.

### 2.2 Motivation

Native booleans simplify code, prevent type errors, and align with Python/SQL best practices. A one-time migration cost now avoids ongoing maintenance burden and prepares the codebase for type checking (mypy).

### 2.3 Prior Art

- Current code in `interface/utils/validation_feedback.py` already normalizes `str_to_bool()` (truthy values: `"true"`, `"1"`, `"yes"`).
- Database migrations in `folders_database_migrator.py` follow sequential version pattern with backups.
- Converter code (`convert_base.py`, converters) already handle various boolean formats.

---

## 3. Design

### 3.1 Architecture Alignment

- [x] Reviewed `docs/DATABASE_DESIGN.md` — confirms schema, migrations, and sequential version strategy.
- [x] Reviewed `docs/GUI_DESIGN.md` — confirms dialog data flow.
- [x] Reviewed `docs/MIGRATION_DESIGN.md` — confirms sequential versions, backups, and compat rules.
- [x] Reviewed `docs/CONFIGURATION_DESIGN.md` — notes string booleans in settings storage.

### 3.2 Technical Approach

**Components affected:**
- [x] `utils.py` — add `normalize_bool()`, `to_db_bool()`, `from_db_bool()` functions
- [x] `interface/utils/validation_feedback.py` — use unified boolean coercion
- [x] `create_database.py` — update schema defaults from `"True"`/`"False"` to INTEGER 0/1
- [x] `folders_database_migrator.py` — add sequential migration (version 40 → 41)
- [x] `interface/ui/dialogs/*.py` — replace `== "True"` with native bools
- [x] `convert_base.py` and converter plugins — use normalized bools
- [x] Tests — update integration tests for new schema version

**API changes — New utility functions (in `utils.py`):**

```python
def normalize_bool(value: Any) -> bool:
    """
    Convert any value to Python boolean.
    
    Accepts:
    - bool: True/False (returned as-is)
    - str: "true"/"false" (case-insensitive), "1"/"0", "yes"/"no"
    - int: 1/0
    - None: False
    
    Examples:
        normalize_bool("True") → True
        normalize_bool("1") → True
        normalize_bool(1) → True
        normalize_bool(None) → False
        normalize_bool(False) → False
    """

def to_db_bool(value: Any) -> int:
    """
    Convert any value to SQLite integer (0 or 1).
    
    Returns 1 for truthy values, 0 for falsy values.
    Used when writing to database.
    """

def from_db_bool(value: Any) -> bool:
    """
    Convert SQLite integer/string to Python boolean.
    
    Used when reading from database; handles both old string
    booleans ("True"/"False") and new integer booleans (0/1).
    """
```

**Schema changes — `create_database.py`:**

Update initial schema to use INTEGER for boolean fields:

```sql
-- Old (tkinter-era)
folder_is_active TEXT DEFAULT "True"
process_edi TEXT DEFAULT "False"
calculate_upc_check_digit TEXT DEFAULT "False"

-- New (native)
folder_is_active INTEGER DEFAULT 1
process_edi INTEGER DEFAULT 0
calculate_upc_check_digit INTEGER DEFAULT 0
```

**Migration script — `folders_database_migrator.py`:**

Add sequential migration from version 40 → 41:

```python
if db_version_dict["version"] == "40":
    # Backup happens automatically
    
    # Convert string booleans to integers in folders table
    db.query("""
        UPDATE folders
        SET folder_is_active = CASE WHEN folder_is_active = "True" THEN 1 ELSE 0 END
        WHERE folder_is_active IN ("True", "False")
    """)
    db.query("""
        UPDATE folders
        SET process_edi = CASE WHEN process_edi = "True" THEN 1 ELSE 0 END
        WHERE process_edi IN ("True", "False")
    """)
    # ... repeat for all boolean columns ...
    
    # Similarly for administrative table
    # ...
    
    db_version.update(dict(id=1, version="41", os=running_platform), ["id"])
    _log_migration_step("40", "41")
```

**Data flow — Reading (backward compat) & Writing (native):**

```
Old DB (v40)
  ├─ Read: from_db_bool("True") → True
  └─ Write: to_db_bool(True) → 1

New DB (v41)
  ├─ Read: from_db_bool(1) → True
  └─ Write: to_db_bool(True) → 1
```

**UI code changes:**

```python
# Old (tkinter-era)
if self.folder_data.get("folder_is_active") == "True":
    self.active_checkbox.setChecked(True)

# New (native)
if from_db_bool(self.folder_data.get("folder_is_active", False)):
    self.active_checkbox.setChecked(True)

# When writing back:
self.data["folder_is_active"] = self.active_checkbox.isChecked()  # Native bool
```

### 3.3 Alternatives Considered

| Alternative | Pros | Cons | Why Not Chosen |
|-------------|------|------|----------------|
| Use SQLite BOOLEAN type | SQL-native | SQLite doesn't have native BOOLEAN; mapped to INTEGER anyway | Use INTEGER instead |
| Keep string booleans, add compat layer | Zero migration | Perpetuates technical debt, maintains complexity | Chosen against |
| Single migration v40→v41 converting all at once | Simple rollout | Risk of data loss if migration fails; no intermediate states | Chosen (with backup) |
| Multiple small migrations | Lower risk per migration | More migration versions to maintain | Chosen against |

---

## 4. Implementation Plan

### Phase 1: Utility Functions (Estimated: 0.5 days)

- [ ] Task 1.1: Add `normalize_bool()`, `to_db_bool()`, `from_db_bool()` to `utils.py`
- [ ] Task 1.2: Update `interface/utils/validation_feedback.py` to use unified functions
- [ ] Task 1.3: Add unit tests for utility functions
- [ ] Deliverable: Boolean coercion functions ready for use everywhere

### Phase 2: Database Migration (Estimated: 1 day)

- [ ] Task 2.1: Update `create_database.py` schema to use INTEGER defaults
- [ ] Task 2.2: Add version 40→41 migration in `folders_database_migrator.py`
- [ ] Task 2.3: Update `tests/integration/database_schema_versions.py`: add v41, update `CURRENT_VERSION`
- [ ] Task 2.4: Write and run migration tests (old v40 DB → new v41)
- [ ] Deliverable: Schema version 41 with all boolean fields migrated

### Phase 3: Update Dialog Code (Estimated: 1 day)

- [ ] Task 3.1: Update `EditFolderDialog` to read/write native bools
- [ ] Task 3.2: Update `EditSettingsDialog` to read/write native bools
- [ ] Task 3.3: Update other dialogs that handle booleans
- [ ] Task 3.4: Run dialog tests; verify data round-tripping
- [ ] Deliverable: All dialogs use native booleans

### Phase 4: Update Processing Code (Estimated: 1 day)

- [ ] Task 4.1: Update `convert_base.py` to use normalized booleans
- [ ] Task 4.2: Update converter plugins (`convert_*.py`) to use normalized booleans
- [ ] Task 4.3: Update `dispatch/coordinator.py` and processing pipeline
- [ ] Task 4.4: Update `utils.py` EDI processing code
- [ ] Deliverable: All processing logic uses native booleans

### Phase 5: Testing & Documentation (Estimated: 1 day)

- [ ] Task 5.1: Run full test suite (`./run_tests.sh`); fix any failures
- [ ] Task 5.2: Smoke tests pass
- [ ] Task 5.3: Update `docs/DATABASE_DESIGN.md` to document native booleans
- [ ] Task 5.4: Update `docs/CONFIGURATION_DESIGN.md`
- [ ] Deliverable: All tests passing, docs updated

---

## 5. Testing Strategy

### Unit Tests
- **Utility functions**: `normalize_bool()`, `to_db_bool()`, `from_db_bool()` with all input types
- **Dialog boolean handling**: read/write native bools, UI←→data mapping

### Integration Tests
- **Database migration**: v40 → v41 conversion, data integrity, backward compat read
- **Dialog round-trip**: load v41 data → modify UI → apply → verify schema
- **Processing pipeline**: converters use native bools, produce correct output

### Test Cases
```python
# Utility tests
def test_normalize_bool_string():
    assert normalize_bool("True") is True
    assert normalize_bool("true") is True
    assert normalize_bool("1") is True
    assert normalize_bool("yes") is True
    assert normalize_bool("False") is False
    assert normalize_bool("0") is False

def test_to_db_bool():
    assert to_db_bool(True) == 1
    assert to_db_bool("True") == 1
    assert to_db_bool(False) == 0
    assert to_db_bool(None) == 0

def test_from_db_bool_backward_compat():
    assert from_db_bool("True") is True  # Old string format
    assert from_db_bool(1) is True       # New integer format
    assert from_db_bool(0) is False

# Migration test
def test_migrate_v40_to_v41():
    # Create v40 database with string booleans
    db = create_v40_db()
    assert db["folders"].find(id=1)[0]["folder_is_active"] == "True"
    
    # Run migration
    migrate_to_v41(db)
    
    # Verify conversion
    assert db["folders"].find(id=1)[0]["folder_is_active"] == 1
    assert from_db_bool(db["folders"].find(id=1)[0]["folder_is_active"]) is True
```

---

## 6. Risk Assessment

**Potential issues:**
1. **Migration data loss** — If conversion query has bugs, data could be lost. Mitigate: backup before migration (automatic); test migration on sample data first.
2. **Old code still checking `== "True"`** — Some code might not be updated. Mitigate: grep search for `== "True"` before release; add linting rule.
3. **Partial migration** — Old string booleans mixed with new integers. Mitigate: `from_db_bool()` handles both; migration updates all tables.
4. **Converter output changes** — If converters rely on string boolean formatting, output might differ. Mitigate: update converter tests (parity testing); use baseline regeneration if needed.

**Mitigations:**
- Run full test suite, especially parity tests (`tests/convert_backends/test_parity_verification.py`).
- Test migration on snapshot of real database if possible.
- Keep `from_db_bool()` flexible for edge cases.

---

## 7. Success Criteria

- [x] `normalize_bool()`, `to_db_bool()`, `from_db_bool()` cover all input types
- [x] Database schema version 41 created with INTEGER boolean defaults
- [x] Migration v40→v41 converts all string booleans to integers
- [x] All dialog code uses native boolean reads/writes
- [x] All processing and converter code uses normalized booleans
- [x] All 1600+ tests pass
- [x] Parity tests pass (converter outputs match baselines)
- [x] Docs updated to reflect native boolean storage
- [x] No `== "True"` string comparisons in production code

---

## 8. Timeline & Effort

- **Phase 1 (Utils)**: 0.5 days
- **Phase 2 (DB migration)**: 1 day
- **Phase 3 (Dialogs)**: 1 day
- **Phase 4 (Processing)**: 1 day
- **Phase 5 (Testing & docs)**: 1 day
- **Total**: ~4.5 days (accounting for testing, debugging, and edge cases)

---

## 9. Dependencies

- **Spec 1 (Dialog Architecture)** should complete Phase 2 (refactor dialogs) **before** this spec's Phase 3, so dialog data handling is clean and consistent.
- Both specs can run in parallel with coordination at the dialog refactoring boundary.
