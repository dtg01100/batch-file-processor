# Database Migration Testing Guide

## Overview

The database migration system ensures that databases from any historical schema version can safely upgrade to the current version while preserving data integrity.

## Current Status

- **Current Schema Version**: 32
- **Oldest Supported Version**: 5
- **Migration Path**: Sequential (5→6→7→...→32)

## Files Involved

| File | Purpose |
|------|---------|
| `interface/main.py` | Defines `DATABASE_VERSION` constant |
| `folders_database_migrator.py` | Contains all migration logic |
| `create_database.py` | Creates new databases at current version |
| `tests/integration/test_database_migrations.py` | Migration tests |

## When Adding a New Migration (Version N+1)

Follow these steps **in order**:

### 1. Update Version Constant
```python
# In interface/main.py
DATABASE_VERSION = "33"  # Increment from current
```

### 2. Add Migration Logic
```python
# In folders_database_migrator.py
def upgrade_database(database_connection, config_folder, running_platform):
    # ... existing migrations ...
    
    db_version_dict = db_version.find_one(id=1)
    
    if db_version_dict["version"] == "32":  # Previous version
        # Add your migration logic here
        folders_table = database_connection["folders"]
        folders_table.create_column("new_column_name", "String")  # or "Integer", "Boolean"
        
        # Set default values if needed
        for line in folders_table.all():
            line["new_column_name"] = "default_value"
            folders_table.update(line, ["id"])
        
        # Do the same for administrative table if needed
        administrative_section = database_connection["administrative"]
        administrative_section.create_column("new_column_name", "String")
        # ...
        
        # Update version
        update_version = dict(id=1, version="33", os=running_platform)
        db_version.update(update_version, ["id"])
```

### 3. Update create_database.py
Add the new column to the initial schema so new databases start with the current schema:

```python
# In create_database.py, in initial_db_dict:
initial_db_dict = {
    # ... existing fields ...
    "new_column_name": "default_value",  # Add here
    # ...
}
```

### 4. Update Test Constants
```python
# In tests/integration/test_database_migrations.py
CURRENT_VERSION = "33"  # Update to match interface/main.py
```

### 5. Test the Migration

```bash
# Run migration tests
pytest tests/integration/test_database_migrations.py -v

# Run full test suite
pytest tests/ -v
```

## Testing Checklist

When adding a new migration, verify:

- [ ] Old databases (v5, v10, v20, v31) can migrate to new version
- [ ] New databases are created at the new version
- [ ] Existing data is preserved during migration
- [ ] New columns have appropriate default values  
- [ ] All tests pass

## Migration Best Practices

### DO:
- ✅ Use descriptive column names
- ✅ Provide sensible default values
- ✅ Test with actual old database files if available
- ✅ Update both `folders` and `administrative` tables consistently
- ✅ Keep migrations sequential (never skip versions)

### DON'T:
- ❌ Delete existing columns (breaks backwards compatibility)
- ❌ Change column types (SQLite limitations)
- ❌ Skip version numbers
- ❌ Modify old migration code (append only)
- ❌ Forget to update version number after migration

## Manual Testing

To manually test a migration:

```bash
# 1. Create an old database
python3 << EOF
import sys
sys.path.insert(0, ".")
from tests.integration.test_database_migrations import TestDatabaseMigrations
test = TestDatabaseMigrations()
test.create_v5_database("test_v5.db")
EOF

# 2. Run migration
python3 << EOF
import sys
sys.path.insert(0, ".")
from PyQt6.QtSql import QSqlDatabase
from interface.database.database_manager import DatabaseConnection
import folders_database_migrator

db = QSqlDatabase.addDatabase("QSQLITE")
db.setDatabaseName("test_v5.db")
db.open()

db_conn = DatabaseConnection(db)
folders_database_migrator.upgrade_database(db_conn, None, "Linux")

db.close()
EOF

# 3. Verify version
sqlite3 test_v5.db "SELECT version FROM version"
```

## Troubleshooting

### "Version mismatch" error
- Check that `DATABASE_VERSION` in interface/main.py matches test constant
- Ensure migration logic increments through all intermediate versions

### Data loss during migration
- Verify migration doesn't delete or overwrite columns
- Check that default values are appropriate
- Review migration logic for each version step

### Tests failing after adding migration
- Run tests individually to isolate the issue
- Check that both forward migration (old→new) and fresh creation work
- Verify all required tables/columns exist

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 5 | Legacy | Baseline schema |
| 6 | Legacy | Added convert_to_format |
| 7 | Legacy | Added resend_flag |
| ... | ... | ... |
| 32 | Current | Latest features |

See `folders_database_migrator.py` for complete version history.
