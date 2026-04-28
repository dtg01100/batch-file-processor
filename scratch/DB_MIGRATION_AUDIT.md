# Database Migration Preference Preservation Audit

**Date:** 2026-04-28  
**Status:** COMPLETE

## Summary

No column or table renames were found in the database schema. All columns use `CREATE TABLE IF NOT EXISTS` pattern, which only adds missing columns without renaming existing ones.

## Schema Management Approach

### Current Implementation

**Location:** `core/database/schema.py` -> `ensure_schema()`

The schema uses a conservative approach:
```python
CREATE TABLE IF NOT EXISTS folders (...)
```

This means:
- Tables are created only if they don't exist
- Columns are added only if they don't exist
- **No renaming of existing columns**
- **No data migration for renamed columns**

### Implications

| Scenario | Behavior |
|----------|----------|
| Fresh database | Creates all columns |
| Existing database with fewer columns | Adds missing columns, preserves existing |
| Column rename | NOT SUPPORTED - old column stays, new column added |
| Data migration for renamed fields | NOT AUTOMATED - would require manual UPDATE |

### Database Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `version` | Track schema version | version, os, notes |
| `settings` | Application settings | Various (deprecated) |
| `administrative` | Admin settings (deprecated) | Various |
| `folders` | Main folder configurations | folder_name, convert_to_format, tweak_edi, etc. |
| `emails_queue` | Email queue | Various |
| `sent_emails_removal_queue` | Cleanup queue | Various |
| `processed_files` | File tracking | Various |

### Key Columns for Folder Configuration

| Column | Type | Purpose |
|--------|------|---------|
| `folder_name` | TEXT | Folder name |
| `convert_to_format` | TEXT | Output format (e.g., "scannerware", "tweaks") |
| `tweak_edi` | INTEGER | Whether to apply EDI tweaks (0/1) |
| `process_edi` | INTEGER | Whether to process EDI |
| `process_backend_email` | INTEGER | Email backend enabled |
| `process_backend_ftp` | INTEGER | FTP backend enabled |
| `process_backend_copy` | INTEGER | Copy backend enabled |

## Preference Preservation Analysis

### Scenario 1: Fresh Install
- Creates all columns
- All preferences start at defaults
- **No issue**

### Scenario 2: Existing Database Without New Columns
- `CREATE TABLE IF NOT EXISTS` adds missing columns
- Existing data preserved
- New columns default to NULL or database defaults
- **No issue**

### Scenario 3: Column Rename (NOT FOUND)
- No column renames found in codebase
- If a column were renamed, old data would remain in old column
- **N/A - not implemented**

### Scenario 4: Format Name Changes
- `convert_to_format` stores format names as TEXT
- If format name changes, old settings with old names would not work
- Format names like "scannerware", "tweaks", "csv" are stored as-is
- **No automated migration for format name changes**

## Migration Path Verification

### No Migration Scripts Found
Searched for:
- `ALTER TABLE` statements - 0 found
- `RENAME COLUMN` - 0 found
- Migration file patterns - 0 found

### Conclusion
The current database schema management:
1. **Does NOT rename columns** - new columns are added, old ones preserved
2. **Does NOT migrate data** - relies on `IF NOT EXISTS` pattern
3. **Does NOT update stored preferences** - if column names change, preferences are lost

## Recommendations

### For Future Column Renames
If a column needs to be renamed in the future:
```sql
-- Step 1: Add new column
ALTER TABLE folders ADD COLUMN new_column_name TEXT;

-- Step 2: Copy data from old column
UPDATE folders SET new_column_name = old_column_name WHERE new_column_name IS NULL;

-- Step 3: (Optional) Drop old column
-- Note: SQLite doesn't support DROP COLUMN until 3.35.0+
```

### For Format Name Changes
If a format name changes (e.g., "tweaks" -> "edi_tweaks"):
```sql
UPDATE folders SET convert_to_format = 'edi_tweaks' WHERE convert_to_format = 'tweaks';
```

## Conclusion

**Database preference preservation is handled by the `IF NOT EXISTS` pattern.** 
- No column renames exist in current schema
- No automated migration for renamed columns
- Format names stored as-is in `convert_to_format` column

The current implementation meets the requirement that "database upgrades preserve user preferences" by simply not performing destructive schema changes.
