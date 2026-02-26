# Test Fixtures

This directory contains real database files used for integration testing.

## Files

- `legacy_v32_folders.db` - A real production database from a legacy Windows installation at version 32. Contains 530 folder configurations and 227,501 processed file records. Used to test the complete database upgrade path from v32 → v42.

## Database Contents

The `legacy_v32_folders.db` fixture contains:

- 530 folder configurations in `folders` table
- 227,501 processed file records in `processed_files` table
- Settings record (SMTP, ODBC configuration)
- Administrative record (log paths, defaults)
- Schema version: 32, platform: Windows

## Known Reference Records

Tests rely on the following specific records from the fixture database:

| Table          | Key    | Fields                                              | Notes                    |
|----------------|--------|-----------------------------------------------------|--------------------------|
| folders        | id=21  | alias="012258", convert_to_format="csv"             | Active production folder |
| folders        | id=29  | alias="PIERCES"                                     | Second reference folder  |
| settings       | id=1   | smtp_port=587, email_smtp_server="smtp.example.com" |                          |
| administrative | id=1   | logs_directory="C:/ProgramData/BatchFileSender/Logs" |                          |

## Shared Fixtures

The following pytest fixtures are defined in `tests/conftest.py`:

| Fixture              | Type       | Description                                |
|----------------------|------------|--------------------------------------------|
| `legacy_v32_db`      | path (str) | Isolated copy of the v32 database          |
| `migrated_v42_db`    | connection | Fully migrated v42 dataset connection      |
| `real_folder_row`    | dict       | Single folder row (id=21)                  |
| `real_folder_rows`   | list[dict] | 5 diverse folder rows                      |
| `real_settings_row`  | dict       | Settings row                               |
| `real_admin_row`     | dict       | Administrative row                         |

## Usage Examples

Use the shared fixtures directly as pytest function arguments:

```python
def test_folder_alias_is_populated(real_folder_row):
    assert real_folder_row["alias"] == "012258"
    assert real_folder_row["convert_to_format"] == "csv"
```
