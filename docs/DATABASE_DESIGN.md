# Database Design Document

**Generated:** 2026-01-30  
**Commit:** c2898be44  
**Branch:** cleanup-refactoring

## 1. Overview

The database layer uses SQLite for local data persistence with a framework-agnostic design that supports both GUI and headless operations.

## 2. Database Technology

| Aspect | Technology |
|--------|------------|
| Engine | SQLite |
| Driver | sqlite3 (Python stdlib) |
| Qt Integration | QtSql (legacy) → sqlite3 (current) |
| Wrapper | Custom Table/DatabaseConnection classes |

## 3. Architecture

```mermaid
flowchart TB
    subgraph GUI Layer
        DBM[DatabaseManager]
    end
    
    subgraph Core Layer
        Conn[DatabaseConnection]
        Table[Table]
        Schema[Schema Creation]
        Migrate[Migrations]
    end
    
    subgraph SQLite
        SQLite[(folders.db)]
    end
    
    DBM --> Conn
    Conn --> Table
    Schema --> SQLite
    Migrate --> SQLite
```

## 4. Key Components

### 4.1 Table Class

Dataset-like API wrapper over sqlite3.

```python
# core/database/connection.py
class Table:
    def __init__(self, connection: sqlite3.Connection, table_name: str):
        self._connection = connection
        self._table_name = table_name
    
    def find(self, order_by: Optional[str] = None, **kwargs) -> List[Dict]:
        """Query records with optional filtering."""
        pass
    
    def find_one(self, **kwargs) -> Optional[Dict]:
        """Get single record."""
        pass
    
    def insert(self, data: Dict[str, Any]) -> None:
        """Insert new record."""
        pass
    
    def update(self, data: Dict[str, Any], keys: List[str]) -> None:
        """Update record by key(s)."""
        pass
    
    def delete(self, **kwargs) -> None:
        """Delete records."""
        pass
    
    def count(self, **kwargs) -> int:
        """Count records."""
        pass
```

### 4.2 DatabaseConnection Class

Connection manager with table access.

```python
# core/database/connection.py
class DatabaseConnection:
    def __init__(self, connection: sqlite3.Connection):
        self._connection = connection
    
    def __getitem__(self, table_name: str) -> Table:
        """Get table by name."""
        return Table(self._connection, table_name)
    
    def query(self, sql: str) -> None:
        """Execute raw SQL."""
        pass
    
    def close(self) -> None:
        """Close connection."""
        pass
```

### 4.3 DatabaseManager Class

Full database manager with migrations.

```python
# core/database/manager.py
class DatabaseManager:
    def __init__(self, database_path: str, config_folder: str,
                 platform: str, app_version: str, database_version: str):
        self._initialize_database()
    
    def _initialize_database(self) -> None:
        """Create or connect to database."""
        pass
    
    def _check_version_and_migrate(self) -> None:
        """Check version and apply migrations."""
        pass
    
    def reload(self) -> None:
        """Reload database connection."""
        pass
    
    def close(self) -> None:
        """Close all connections."""
        pass
```

## 5. Schema

### 5.1 Version Table

Stores database schema version.

```sql
CREATE TABLE version (
    id INTEGER PRIMARY KEY,
    version TEXT,
    os TEXT
)
```

### 5.2 Folders Table

Stores folder configurations.

```sql
CREATE TABLE folders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    folder_is_active TEXT,
    copy_to_directory TEXT,
    process_edi TEXT,
    convert_to_format TEXT,
    calculate_upc_check_digit TEXT,
    include_a_records TEXT,
    include_c_records TEXT,
    include_headers TEXT,
    filter_ampersand TEXT,
    tweak_edi INTEGER,
    pad_a_records TEXT,
    a_record_padding TEXT,
    a_record_padding_length INTEGER,
    invoice_date_custom_format_string TEXT,
    invoice_date_custom_format INTEGER,
    reporting_email TEXT,
    folder_name TEXT,
    alias TEXT,
    report_email_destination TEXT,
    process_backend_copy INTEGER,
    process_backend_ftp INTEGER,
    process_backend_email INTEGER,
    ftp_server TEXT,
    ftp_folder TEXT,
    ftp_username TEXT,
    ftp_password TEXT,
    email_to TEXT,
    logs_directory TEXT,
    errors_folder TEXT,
    enable_reporting TEXT,
    report_printing_fallback TEXT,
    ftp_port INTEGER,
    email_subject_line TEXT,
    single_add_folder_prior TEXT,
    batch_add_folder_prior TEXT,
    export_processed_folder_prior TEXT,
    report_edi_errors INTEGER,
    split_edi INTEGER,
    split_edi_include_invoices INTEGER,
    split_edi_include_credits INTEGER,
    force_edi_validation INTEGER,
    append_a_records TEXT,
    a_record_append_text TEXT,
    force_txt_file_ext TEXT,
    invoice_date_offset INTEGER,
    retail_uom INTEGER,
    include_item_numbers INTEGER,
    include_item_description INTEGER,
    simple_csv_sort_order TEXT,
    split_prepaid_sales_tax_crec INTEGER,
    estore_store_number INTEGER,
    estore_Vendor_OId INTEGER,
    estore_vendor_NameVendorOID TEXT,
    estore_c_record_OID TEXT,
    prepend_date_files INTEGER,
    rename_file TEXT,
    override_upc_bool INTEGER,
    override_upc_level INTEGER,
    override_upc_category_filter TEXT,
    fintech_division_id INTEGER,
    plugin_config TEXT,
    edi_format TEXT,
    created_at TEXT,
    updated_at TEXT
)
```

### 5.3 Settings Table

Stores global application settings.

```sql
CREATE TABLE settings (
    enable_email INTEGER,
    email_address TEXT,
    email_username TEXT,
    email_password TEXT,
    email_smtp_server TEXT,
    smtp_port INTEGER,
    backup_counter INTEGER,
    backup_counter_maximum INTEGER,
    enable_interval_backups INTEGER,
    odbc_driver TEXT,
    as400_address TEXT,
    as400_username TEXT,
    as400_password TEXT,
    created_at TEXT,
    updated_at TEXT
)
```

### 5.4 Processed Files Table

Tracks processed files.

```sql
CREATE TABLE processed_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    folder_id INTEGER,
    filename TEXT,
    original_path TEXT,
    processed_path TEXT,
    status TEXT,
    error_message TEXT,
    convert_format TEXT,
    sent_to TEXT,
    created_at TEXT,
    processed_at TEXT,
    file_name TEXT,
    file_checksum TEXT,
    copy_destination TEXT,
    ftp_destination TEXT,
    email_destination TEXT,
    resend_flag INTEGER
)
```

### 5.5 Supporting Tables

```sql
CREATE TABLE administrative (...);  -- Oversight and defaults
CREATE TABLE emails_to_send (id INTEGER PRIMARY KEY AUTOINCREMENT, log TEXT);
CREATE TABLE working_batch_emails_to_send (id INTEGER PRIMARY KEY AUTOINCREMENT, log TEXT);
CREATE TABLE sent_emails_removal_queue (id INTEGER PRIMARY KEY AUTOINCREMENT, log TEXT);
```

### 5.6 Indexes

```sql
CREATE INDEX IF NOT EXISTS idx_folders_active ON folders(folder_is_active);
CREATE INDEX IF NOT EXISTS idx_folders_alias ON folders(alias);
CREATE INDEX IF NOT EXISTS idx_processed_files_folder ON processed_files(folder_id);
CREATE INDEX IF NOT EXISTS idx_processed_files_status ON processed_files(status);
CREATE INDEX IF NOT EXISTS idx_processed_files_created ON processed_files(created_at);
```

## 6. Database Migrations

### 6.1 Migration System

Sequential migrations from v5 to v40 in `folders_database_migrator.py`.

```python
# folders_database_migrator.py
def upgrade_database(connection, config_folder, platform, target_version):
    current_version = get_current_version(connection)
    
    for version in range(current_version, target_version):
        apply_migration(connection, version, version + 1)
```

### 6.2 Migration Pattern

```python
if db_version_dict["version"] == "38":
    # Add new column
    connection.execute('ALTER TABLE folders ADD COLUMN new_column TEXT')
    # Update version
    db_version.update(dict(id=1, version="39", os=running_platform), ["id"])
    _log_migration_step("38", "39")
```

### 6.3 Migration Rules

- Never delete columns (SQLite limitation)
- Never skip version numbers
- Never modify existing migrations
- Always create backup before migration
- Validate OS compatibility

## 7. Connection Functions

### 7.1 Connect to Database

```python
# core/database/connection.py
def connect(database_path: str) -> DatabaseConnection:
    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA foreign_keys = ON")
    return DatabaseConnection(connection)
```

### 7.2 In-Memory Database

```python
def connect_memory() -> DatabaseConnection:
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    return DatabaseConnection(connection)
```

## 8. Access Patterns

### 8.1 Dict-Style Table Access

```python
# Get all active folders
folders = db["folders"].find(active=True)

# Get single record
settings = db["settings"].find_one()

# Insert record
db["folders"].insert({"alias": "Test", "folder_name": "/path"})

# Update record
db["folders"].update({"id": 1, "alias": "Updated"}, ["id"])

# Delete records
db["processed_files"].delete(folder_id=5)
```

### 8.2 Raw SQL Query

```python
db.query("DELETE FROM processed_files WHERE created_at < '2024-01-01'")
```

## 9. Testing

### 9.1 Test Coverage

- `tests/unit/test_create_database.py` - Schema creation
- `tests/unit/test_interface_db_manager.py` - Database manager
- `tests/integration/test_database_migrations.py` - Migration tests
- `tests/integration/test_automatic_migrations.py` - Automatic migrations

### 9.2 Test Fixtures

```python
@pytest.fixture
def mock_db_manager():
    """Create mock database manager for testing."""
    pass
```

## 10. Current Version

| Property | Value |
|----------|-------|
| Current Schema Version | 40 |
| Supported Range | v5-v40 |
| Last Migration | v40 |
