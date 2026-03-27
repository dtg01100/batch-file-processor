# Migration Audit Report: `process_backend_http` Column

**Date:** March 27, 2026  
**Audit Scope:** Database migrations from v5 to v50 (current)  
**Trigger:** `sqlite3.OperationalError: no such column: process_backend_http`

---

## Executive Summary

### Root Cause

The error occurs when a database is at **version 49** but is **missing the `process_backend_http` column** in the `folders` and/or `administrative` tables. This column was supposed to be added during the v49→v50 migration, but the migration either:

1. **Failed partway through** (added column to one table but not both)
2. **Was never executed** (database stuck at v49)
3. **Ran on a corrupted/locked database** (ALTER TABLE failed silently)

### Current State

- **Schema definition** (`core/database/schema.py`): ✅ Defines `process_backend_http` column
- **Migration script** (`migrations/folders_database_migrator.py`): ✅ Has v49→v50 migration
- **Application code**: ✅ References `process_backend_http` in 13 locations
- **Database on user's system**: ❌ Missing the column despite being at version 49

---

## Detailed Findings

### 1. Migration Chain Analysis

#### Version History (Recent)

| Version | Key Changes | Status |
|---------|-------------|--------|
| v40 | Add PRIMARY KEY to folders/administrative | ✅ Tested |
| v41 | Add backend email/FTP columns | ✅ Tested |
| v42 | Normalize boolean values (True→1, False→0) | ✅ Tested |
| v43 | Normalize folder paths (backslash→forward slash) | ✅ Tested |
| v44 | Add UPC columns (`upc_target_length`, `upc_padding_pattern`) | ✅ Tested |
| v45 | Fix `convert_to_format` for `tweak_edi` folders | ✅ Tested |
| v46 | Repair corrupted `convert_to_format` from backups | ✅ Tested |
| v47 | Fix `process_edi=False` with conversion target | ✅ Tested |
| v48 | **No schema changes** (version bump only) | ⚠️ No-op migration |
| v49 | **Add `process_backend_http` column** | ❌ **FAILING** |
| v50 | Current version | - |

#### Critical Observation: v48 is a No-Op

The v48→v49 migration block (lines 1420-1428 in `folders_database_migrator.py`) only increments the version number:

```python
if str(db_version_dict["version"]) == "48":
    update_version = dict(id=1, version="49", os=running_platform)
    db_version.update(update_version, ["id"])
    _log_migration_step("48", "49")
```

**No columns are added in this step.** This is problematic because:

1. If the migration fails between v48→v49, the version is incremented but no work is done
2. The actual column addition happens in v49→v50, but users may think they're "caught up" at v49

### 2. The v49→v50 Migration Block

**Location:** `migrations/folders_database_migrator.py` lines 1430-1445

```python
db_version_dict = db_version.find_one(id=1)

if str(db_version_dict["version"]) == "49":
    for table_name in ("folders", "administrative"):
        _ensure_column(table_name, "process_backend_http", "INTEGER", "0")

    update_version = dict(id=1, version="50", os=running_platform)
    db_version.update(update_version, ["id"])
    _log_migration_step("49", "50")
```

#### The `_ensure_column` Function

**Location:** Lines 1408-1426

```python
def _ensure_column(table_name, column_name, sql_type, default_sql) -> None:
    if column_name in _existing_columns(table_name):
        return
    quoted_table = _quote_identifier(table_name)
    quoted_column = _quote_identifier(column_name)
    conn = database_connection.raw_connection
    try:
        conn.execute(
            f"ALTER TABLE {quoted_table} ADD COLUMN {quoted_column} {sql_type}"
        )
    except Exception as e:
        raise RuntimeError(
            f"Failed to add column {quoted_column} to table {quoted_table}: {e}"
        ) from e
    try:
        conn.execute(f"UPDATE {quoted_table} SET {quoted_column} = {default_sql}")
    except Exception as e:
        raise RuntimeError(
            f"Failed to set default value for column {quoted_column} in table {quoted_table}: {e}"
        ) from e
```

**Key Issue:** This function **raises `RuntimeError`** on failure, which should stop the migration. However, if:

1. The first table (`folders`) succeeds
2. The second table (`administrative`) fails
3. The exception is raised, but the version was already incremented to 50

Then the database is left in an **inconsistent state**: version 50 but missing a column.

### 3. Existing Remediation: `fix_missing_columns.py`

**Location:** `migrations/fix_missing_columns.py`

This standalone script was created to handle exactly this scenario. It:

1. Checks if `process_backend_http` exists in both tables
2. If version is 49 and column is missing, reverts to version 48
3. Adds the missing column(s)
4. Updates version to 49

**Problem:** This script must be run **manually** by the user. It's not automatically invoked when the error occurs.

### 4. Schema Definition vs. Migration Reality

**Schema file:** `core/database/schema.py` line 161

```python
process_backend_http INTEGER,
```

The schema definition includes the column, and `ensure_schema()` is called during database initialization. However:

- `ensure_schema()` uses `CREATE TABLE IF NOT EXISTS` - it **does not ALTER existing tables**
- Existing databases (upgraded from older versions) rely on migrations to add new columns
- **Gap:** `ensure_schema()` should call `_ensure_column()` for new columns, but it doesn't

---

## Impact Analysis

### Affected Components

| Component | File | Usage |
|-----------|------|-------|
| Send Manager | `dispatch/send_manager.py:56` | Backend selection |
| Folder Config Model | `interface/models/folder_configuration.py:272,503,526` | Serialization |
| Data Extractor | `interface/operations/folder_data_extractor.py:27,140` | Data extraction |
| Edit Folders Dialog | `interface/qt/dialogs/edit_folders_dialog.py:128,239,358,707` | UI field |
| Column Builders | `interface/qt/dialogs/edit_folders/column_builders.py:181` | Field mapping |

### User Impact

When this error occurs:

1. **User cannot save folder configuration** - any edit to a folder triggers the UPDATE
2. **Error is not user-friendly** - raw SQLite error exposed to end user
3. **No automatic recovery** - requires manual intervention

---

## Testing Coverage

### Existing Tests

| Test File | Coverage |
|-----------|----------|
| `tests/unit/test_folders_database_migrator.py` | ✅ Tests v40-v48 migrations |
| `tests/integration/test_real_legacy_db_upgrade.py` | ✅ Full v32→current migration |
| `tests/integration/test_data_migration_scenarios.py` | ✅ Edge cases, rollback |
| `tests/unit/migrations/test_add_plugin_config_column.py` | ✅ Plugin config migration |

### Missing Tests

❌ **No test for v49→v50 migration specifically**  
❌ **No test for partial migration failure (one table succeeds, one fails)**  
❌ **No test for `fix_missing_columns.py` script**

---

## Recommendations

### Immediate Fix (User-Facing)

**Option 1: Auto-invoke fix script on error**

Modify `backend/database/database_obj.py` to catch this specific error:

```python
try:
    folders_database_migrator.upgrade_database(...)
except sqlite3.OperationalError as e:
    if "process_backend_http" in str(e):
        # Auto-run fix script
        from migrations import fix_missing_columns
        fix_script_path = os.path.join(
            os.path.dirname(__file__), "..", "migrations", "fix_missing_columns.py"
        )
        # ... invoke fix ...
    raise
```

**Option 2: Make ensure_schema() idempotent**

Add column-checking to `core/database/schema.py`:

```python
# After CREATE TABLE statements
for table in ("folders", "administrative"):
    _ensure_column(database_connection, table, "process_backend_http", "INTEGER", "0")
```

### Long-Term Fixes

1. **Add v49→v50 migration test**
   - Test both tables get the column
   - Test partial failure scenario
   - Test idempotency

2. **Improve error handling in `_ensure_column`**
   - Log which table failed
   - Don't increment version if any table fails
   - Consider using a transaction

3. **Integrate `fix_missing_columns.py` into migration flow**
   - Run as a "repair step" before version check
   - Or: convert to a function and call from `upgrade_database()`

4. **Add migration health check**
   - Before allowing folder edits, verify all expected columns exist
   - Show user-friendly error if migration is incomplete

5. **Review v48→v49 no-op migration**
   - Either add actual work to v48→v49, or
   - Combine v49→v50 into a single atomic migration

---

## Verification Steps

To verify a database is healthy:

```sql
-- Check version
SELECT version FROM version WHERE id = 1;
-- Should return: 50

-- Check folders table has column
PRAGMA table_info(folders);
-- Should include: process_backend_http INTEGER

-- Check administrative table has column
PRAGMA table_info(administrative);
-- Should include: process_backend_http INTEGER
```

To fix a broken database:

```bash
# Option 1: Use the fix script
python -m migrations.fix_missing_columns /path/to/folders.db

# Option 2: Manual SQL (if comfortable)
sqlite3 /path/to/folders.db
ALTER TABLE folders ADD COLUMN process_backend_http INTEGER DEFAULT 0;
ALTER TABLE administrative ADD COLUMN process_backend_http INTEGER DEFAULT 0;
UPDATE version SET version = '50' WHERE id = 1;
```

---

## Conclusion

The `process_backend_http` column error is caused by an **incomplete or failed migration** from v49→v50. The migration infrastructure exists but has gaps:

1. **No automatic recovery** when migration fails partway
2. **No test coverage** for this specific migration
3. **Schema definition doesn't backfill** existing tables

A fix script exists (`fix_missing_columns.py`) but requires manual invocation. The recommended approach is to:

1. **Immediate:** Auto-detect and fix on application startup
2. **Short-term:** Add comprehensive tests for v49→v50
3. **Long-term:** Improve migration atomicity and error recovery

---

## Appendix: File Locations

| File | Purpose |
|------|---------|
| `migrations/folders_database_migrator.py` | Main migration script |
| `migrations/fix_missing_columns.py` | Standalone repair script |
| `core/database/schema.py` | Schema definition |
| `backend/database/database_obj.py` | Migration invocation |
| `dispatch/send_manager.py` | HTTP backend send manager |

---

**Audit Completed:** March 27, 2026  
**Auditor:** Batch File Processor Development Team
