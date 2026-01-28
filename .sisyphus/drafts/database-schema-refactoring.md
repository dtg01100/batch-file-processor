# Draft: Database Schema Refactoring Plan

## Requirements (confirmed)

### User's Stated Goals
- Improve database schema maintainability
- Fix MASSIVE column duplication (folders vs administrative tables)
- Normalize 88+ flat columns into proper structure
- Fix schema-model mismatch (interface/models/* don't match schema)
- Standardize boolean types (TEXT "True"/"False" vs INTEGER 0/1)
- Add foreign key constraints where missing
- Add indexes for common query patterns

### Constraints (confirmed)
- **MUST FOLLOW**:
  - Sequential migration strategy (v32 -> v33 -> v34...)
  - Maintain backwards compatibility
  - Update BOTH create_database.py AND folders_database_migrator.py
  - Keep 90 migration tests passing
  - Never delete columns (SQLite limitation)
  
- **MUST NOT BREAK**:
  - Existing folder configurations
  - Processed file tracking
  - Settings persistence
  - Email queue functionality

- **SAFE TO CHANGE**:
  - Add new columns
  - Add new tables
  - Migrate data between columns
  - Add indexes
  - Add constraints (with caution)

## Technical Decisions

### Approach: Staged, Incremental Refactoring
- Each step = single migration version
- Each step independently testable
- Each step deployable on its own
- Prioritize high-impact, low-risk first

### JSON Migration In Progress
- `plugin_config` column already exists
- Old columns still present
- Migration logic in `migrations/add_plugin_config_column.py`
- Need to complete this transition safely

## Research Findings (COMPLETE)

### Schema Analysis (from create_database.py)

**Tables Created:**
1. `version` - id, version, os
2. `administrative` - 60+ columns (same as folders)
3. `folders` - 60+ columns (same structure)
4. `settings` - 13 columns (email, AS400 config)
5. `processed_files` - 7 columns (id, file_name, file_checksum, copy_destination, ftp_destination, email_destination, resend_flag, folder_id)
6. `emails_to_send` - id, log
7. `working_batch_emails_to_send` - id, log
8. `sent_emails_removal_queue` - id, log

**Column Count in initial_db_dict (folders/administrative):** 60 columns in create_database.py
**Additional columns added via migrations v5→v32:** ~28 more columns

**Boolean Type Mix Identified:**
- TEXT "True"/"False": `folder_is_active`, `process_edi`, `calculate_upc_check_digit`, `include_a_records`, etc.
- INTEGER (0/1 or True/False): `tweak_edi`, `invoice_date_custom_format`, `process_backend_copy`, etc.

**No Foreign Keys:** `processed_files.folder_id` has no FK constraint

### Migration System Analysis (from folders_database_migrator.py)

**Pattern Mix:**
- v5→v12: ORM-style using `table.create_column()`, `table.update()`, `table.find()`
- v14+: Raw SQL using `database_connection.query("ALTER TABLE...")`

**Structure:**
- 27 sequential version checks (v5→v32)
- Each adds columns to BOTH `folders` AND `administrative` tables
- Heavy duplication (same column added to both tables)

**JSON Migration State (migrations/add_plugin_config_column.py):**
- **EXISTS**: Adds `plugin_config TEXT` column to `folders` table
- **STATUS**: Migration logic written but NOT integrated into main migrator
- **DATA**: Converts plugin columns to JSON structure
- **OLD COLUMNS**: Still present (SQLite can't delete columns)

### Model-Schema Mismatch (CRITICAL)

| Model Field | Expected Type | Actual Schema | Status |
|-------------|---------------|---------------|--------|
| **ProcessedFile** |
| `filename` | str | `file_name` | WRONG NAME |
| `status` | str | (none) | MISSING |
| `error_message` | str | (none) | MISSING |
| `original_path` | str | (none) | MISSING |
| `processed_path` | str | (none) | MISSING |
| `convert_format` | str | (none) | MISSING |
| `sent_to` | str | (none) | MISSING |
| `created_at` | datetime | (none) | MISSING |
| `processed_at` | datetime | (none) | MISSING |
| **Settings** |
| `key` | str | (none) | WRONG STRUCTURE |
| `category` | str | (none) | MISSING |
| `description` | str | (none) | MISSING |
| `created_at` | datetime | (none) | MISSING |
| `updated_at` | datetime | (none) | MISSING |
| **Folder** |
| `path` | str | `folder_name` | DIFFERENT NAME |
| `active` | bool | `folder_is_active` TEXT | DIFFERENT NAME+TYPE |
| `processed` | bool | (none) | MISSING |
| `ftp_host` | str | `ftp_server` | DIFFERENT NAME |
| `ftp_remote_path` | str | `ftp_folder` | DIFFERENT NAME |
| `email_subject_prefix` | str | `email_subject_line` | DIFFERENT NAME |
| `edi_format` | str | (none) | MISSING |
| `edi_convert_options` | dict | (none) | MISSING (plugin_config covers this) |
| `created_at` | datetime | (none) | MISSING |
| `updated_at` | datetime | (none) | MISSING |

**Note:** Settings model expects key-value structure; current schema has flat columns.

### Test Infrastructure

- **Test File**: `tests/integration/test_database_migrations.py` (246 lines)
- **Helper File**: `tests/integration/database_schema_versions.py` (generates DBs at any version)
- **Test Count**: 90+ tests covering:
  - Migration from every version to current (parametrized)
  - Data preservation during migration
  - Structure validation at each version
  - Idempotency (running migration on current is no-op)
  - Individual step testing (vN to vN+1)
- **Pattern**: Uses `DatabaseConnectionManager` context manager, temporary files

## User Decisions (Confirmed)

### 1. Administrative Table → SPLIT RESPONSIBILITIES (CONFIRMED)
- User confirmed after discovering true purpose
- **SPLIT PLAN**:
  - Default folder template → Mark row in `folders` as `is_template=1` (special row id=0 or separate flag)
  - App settings (prior paths, reporting) → Move to `settings` table with appropriate keys
  - UI state → `settings` table with category='ui_state'
- Will require updating code that references `oversight_and_defaults`

### 2. Interface Models → NOT IN USE YET
- Models in `interface/models/` are new/planned code
- Schema should be MIGRATED to match the models (not vice versa)
- This means models define the target state

### 3. Boolean Format → INTEGER (0/1)
- Standardize all booleans to INTEGER (0/1) format
- This is SQLite standard, cleaner queries, better tooling

### 4. JSON Migration Status → NOT DEPLOYED YET
- `migrations/add_plugin_config_column.py` exists but not integrated
- No production databases have the `plugin_config` column
- We can incorporate this cleanly into the plan

### 5. Step Size → SMALLER STEPS (SAFER)
- User prefers 6-10 granular migrations
- Each step lower risk
- More version numbers but safer rollback

## Open Questions (Remaining)

None - all critical questions resolved.

## Scope Boundaries

### IN SCOPE
- All 8 issues listed (Critical, High, Medium priority)
- Staged migration plan with exact SQL
- Test verification strategy
- Rollback strategies
- Commit checkpoints

### OUT OF SCOPE (unless user says otherwise)
- Changing PyQt6 QSqlDatabase to different ORM
- Major architectural changes beyond schema
- Changing test framework
- UI/interface changes
