# Database Migration Testing System

## Overview

The project now has comprehensive migration testing that verifies **EVERY single version** (5-32) can successfully upgrade to the current version.

## What Was Created

### 1. Schema Version Generator (`tests/integration/database_schema_versions.py`)

**Key Features:**
- Generates database files at any version from 5-32
- Uses actual migration code (not fake schemas)
- Proper connection management via context managers
- Version verification utilities

```python
# Generate a database at version 10
db_path = generate_database_at_version(10)

# Verify its version
assert get_database_version(db_path) == "10"

# Check structure
structure = verify_database_structure(db_path)
print(structure["tables"])  # ['version', 'folders', ...]
```

### 2. Comprehensive Test Suite (`tests/integration/test_database_migrations.py`)

**Test Coverage:**
- ✅ **28 parametrized tests**: One for each version 5-31 → 32
- ✅ **28 structure tests**: Verifies schema validity at each version
- ✅ **27 individual step tests**: Tests each N→N+1 migration
- ✅ Data preservation during full migration
- ✅ Idempotency (migrating current version is safe)
- ✅ Intermediate migrations (e.g., v10→v32)
- ✅ Version constant synchronization

**Total: ~85 migration tests covering all scenarios**

###3. Updated Documentation (`DATABASE_MIGRATION_GUIDE.md`)

Step-by-step guide for adding new migrations with testing checklist.

## How It Works

### Automatic Version Testing

The system automatically tests ALL versions thanks to this pattern:

```python
# In database_schema_versions.py
ALL_VERSIONS = list(range(5, 33))  # Auto-generates [5, 6, 7, ..., 32]
CURRENT_VERSION = "32"

# In test file
@pytest.mark.parametrize("start_version", ALL_VERSIONS)
def test_migrate_from_version_to_current(self, start_version):
    # This runs 28 times automatically!
    ...
```

When you add version 33:
1. Update `ALL_VERSIONS = list(range(5, 34))`  ← Adds 33 automatically
2. Update `CURRENT_VERSION = "33"`
3. Run tests → **Automatically tests v33**

No need to manually add v33 to test parameters!

### Schema Generation Strategy

Instead of maintaining 28 different schema creation functions, the system:
1. Creates a baseline v5 database
2. Applies real migrations to reach target version
3. This ensures we're testing **actual migration code**, not mock schemas

```python
def generate_database_at_version(version):
    create_baseline_v5_schema(db_path)  # Start at v5
    migrate_to_version(db_path, version)  # Use real migrator
    return db_path
```

## Running the Tests

```bash
# Run all migration tests
pytest tests/integration/test_database_migrations.py -v

# Run just one version
pytest tests/integration/test_database_migrations.py::TestDatabaseMigrations::test_migrate_from_version_to_current[10] -v

# Run maintenance checks
pytest tests/integration/test_database_migrations.py::TestMigrationMaintenance -v

# Run individual step tests
pytest tests/integration/test_database_migrations.py::TestMigrationPathCoverage -v
```

## Adding a New Migration (Version 33)

### Step 1: Update Version Constants

```python
# interface/main.py
DATABASE_VERSION = "33"

# tests/integration/database_schema_versions.py  
ALL_VERSIONS = list(range(5, 34))  # Was range(5, 33)
CURRENT_VERSION = "33"
```

### Step 2: Add Migration Logic

```python
# folders_database_migrator.py
def upgrade_database(database_connection, config_folder, running_platform):
    # ... existing migrations ...
    
    db_version_dict = db_version.find_one(id=1)
    
    if db_version_dict["version"] == "32":
        # Your new migration here
        folders_table = database_connection["folders"]
        folders_table.create_column("new_feature_flag", "Boolean")
        
        for line in folders_table.all():
            line["new_feature_flag"] = False
            folders_table.update(line, ["id"])
        
        administrative_section = database_connection["administrative"]
        administrative_section.create_column("new_feature_flag", "Boolean")
        # ... set defaults ...
        
        update_version = dict(id=1, version="33", os=running_platform)
        db_version.update(update_version, ["id"])
```

### Step 3: Update Initial Schema

```python
# create_database.py - add to initial_db_dict
initial_db_dict = {
    # ... existing fields ...
    "new_feature_flag": False,  # Add here
}
```

### Step 4: Run Tests

```bash
pytest tests/integration/test_database_migrations.py -v
```

The test suite will automatically:
- Test migration from v32→v33
- Test all previous versions still migrate to v33
- Verify v33 schema structure
- Check data preservation

## Test Structure

```
tests/integration/test_database_migrations.py
├── TestDatabaseMigrations
│   ├── test_migrate_from_version_to_current[5-32]  ← 28 tests
│   ├── test_database_structure_at_each_version[5-32]  ← 28 tests  
│   ├── test_data_preservation_during_full_migration
│   ├── test_all_versions_increment_sequentially
│   ├── test_migration_is_idempotent
│   └── test_intermediate_migrations_work
│
├── TestMigrationMaintenance
│   ├── test_current_version_matches_interface_main
│   ├── test_all_versions_list_is_complete
│   └── test_schema_generator_supports_all_versions
│
└── TestMigrationPathCoverage
    └── test_each_individual_migration_step[5-31]  ← 27 tests
```

## Benefits

### Complete Coverage
- Every version 5-32 is tested
- Every migration step is verified
- No gaps in test coverage

### Automatic Expansion
- Adding v33 only requires changing 2 numbers
- Tests automatically expand to cover new version
- No manual test case additions needed

### Real Migration Testing
- Uses actual migration code
- Not mocked or simplified
- Catches real-world issues

### Data Integrity
- Verifies data survives migrations
- Tests column additions
- Validates default values

## Known Limitations

- Test execution requires proper Qt SQL environment
- Some test environments may experience connection issues
- Manual verification may be needed in certain scenarios

## Maintenance

The system is designed to be **zero-maintenance** for new versions:
1. Change 2 numbers in version constants
2. Write migration logic
3. Run tests
4. Done!

No need to update test parameters, add new test cases, or maintain separate schema generators for each version.

---

**Summary**: This testing system ensures that every database migration is thoroughly tested, data integrity is preserved, and adding new migrations is trivial going forward.
