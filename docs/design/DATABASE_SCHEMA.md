# Database Schema Design Document

**Version:** 1.1  
**Date:** 2026-05-18  
**Status:** CORRECTED

---

## 1. Overview

The database uses SQLite for local persistence. The application uses an **Adapter Pattern** with repository interfaces for clean separation of concerns.

## 2. Architecture

### 2.1 Layer Structure

```
┌─────────────────────────────────────────────────────┐
│              Application Layer                       │
│         (Qt App, Orchestrator, Services)             │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│            Repository Interfaces                      │
│       core/ports/repositories.py                     │
│   - IFolderRepository                               │
│   - ISettingsRepository                             │
│   - IProcessedFilesRepository                       │
│   - IEmailQueueRepository                           │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│              SQLite Adapters                         │
│      adapters/sqlite/repositories/                  │
│   - SqliteFolderRepository                          │
│   - SqliteSettingsRepository                        │
│   - SqliteProcessedFilesRepository                  │
│   - SqliteEmailQueueRepository                      │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│            DatabaseObj (Table API)                   │
│      backend/database/database_obj.py               │
└─────────────────────────────────────────────────────┘
```

### 2.2 DatabaseObj Class

**Location:** `backend/database/database_obj.py`

```python
# Main database access class
class DatabaseObj:
    """Provides Table instances for each table via attribute access."""
    
    def __init__(self, db_path: str):
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
    
    @property
    def folders_table(self) -> Table:
        """Access folders table."""
        return Table(self._conn, "folders")
    
    @property
    def settings_table(self) -> Table:
        """Access settings table."""
        return Table(self._conn, "settings")
    
    @property
    def processed_files_table(self) -> Table:
        """Access processed_files table."""
        return Table(self._conn, "processed_files")
    
    @property
    def email_queue_table(self) -> Table:
        """Access email_queue table."""
        return Table(self._conn, "email_queue")
    
    def query(self, sql: str) -> list[dict]:
        """Execute raw SQL and return results."""
    
    def close(self) -> None:
        """Close database connection."""
```

### 2.3 Table Wrapper

```python
class Table:
    """Table wrapper providing dataset-like API."""
    
    def __init__(self, conn: sqlite3.Connection, table_name: str):
        self._conn = conn
        self._table = table_name
    
    def find_one(self, **kwargs) -> dict | None:
        """Get single record matching criteria."""
    
    def find(self, order_by: str = None, **kwargs) -> list[dict]:
        """Get all records matching criteria."""
    
    def all(self) -> list[dict]:
        """Get all records."""
    
    def insert(self, record: dict) -> int:
        """Insert record, return row ID."""
    
    def update(self, record: dict, keys: list[str]) -> None:
        """Update record by key fields."""
    
    def delete(self, **kwargs) -> int:
        """Delete records matching criteria."""
    
    def count(self, **kwargs) -> int:
        """Count records matching criteria."""
```

### 2.4 Repository Pattern Usage

```python
# Using repositories (recommended for new code)
from backend.database.database_obj import DatabaseObj
from adapters.sqlite.repositories import SqliteFolderRepository

db = DatabaseObj(db_path)
repo = SqliteFolderRepository(db)
folders = repo.find_all(active_only=True)

# Using Table directly (existing pattern)
from backend.database.database_obj import DatabaseObj

db = DatabaseObj(db_path)
folders = db.folders_table.find(folder_is_active=True)
```

## 3. Database Tables

### 3.1 folders

**Purpose:** Main folder configuration table with 60+ columns.

```sql
CREATE TABLE folders (
    -- Identity
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    folder_name TEXT,
    alias TEXT,
    
    -- Status
    folder_is_active INTEGER DEFAULT 1,
    status TEXT,
    error_message TEXT,
    
    -- Conversion Settings
    convert_to_format TEXT,
    convert_format TEXT,
    calculate_upc_check_digit INTEGER,
    upc_target_length INTEGER,
    upc_padding_pattern TEXT,
    override_upc_bool INTEGER,
    override_upc_level INTEGER,
    override_upc_category_filter TEXT,
    
    -- EDI Processing
    process_edi INTEGER,
    split_edi INTEGER,
    split_edi_include_invoices INTEGER,
    split_edi_include_credits INTEGER,
    split_edi_filter_categories TEXT,
    split_edi_filter_mode TEXT,
    force_edi_validation INTEGER,
    
    -- Record Types
    include_a_records INTEGER,
    include_c_records INTEGER,
    pad_a_records INTEGER,
    a_record_padding TEXT,
    a_record_padding_length INTEGER,
    append_a_records INTEGER,
    a_record_append_text TEXT,
    estore_c_record_OID INTEGER,
    
    -- Headers and Filters
    include_headers INTEGER,
    filter_ampersand INTEGER,
    force_txt_file_ext INTEGER,
    
    -- Date and Format
    invoice_date_custom_format INTEGER,
    invoice_date_custom_format_string TEXT,
    invoice_date_offset INTEGER,
    simple_csv_sort_order TEXT,
    
    -- Unit of Measure
    retail_uom INTEGER,
    force_each_upc INTEGER,
    
    -- Item Fields
    include_item_numbers INTEGER,
    include_item_description INTEGER,
    
    -- Tax Splitting
    split_prepaid_sales_tax_crec INTEGER,
    
    -- Store/Vendor (eStore)
    estore_store_number INTEGER,
    estore_Vendor_OId INTEGER,
    estore_vendor_NameVendorOID TEXT,
    
    -- FinTech
    fintech_division_id INTEGER,
    
    -- File Naming
    prepend_date_files INTEGER,
    rename_file TEXT,
    
    -- Backend: Copy
    process_backend_copy INTEGER,
    copy_to_directory TEXT,
    backend_copy_destination TEXT,
    
    -- Backend: Email
    process_backend_email INTEGER,
    email_to TEXT,
    email_subject_line TEXT,
    
    -- Backend: FTP
    process_backend_ftp INTEGER,
    ftp_server TEXT,
    ftp_port INTEGER,
    ftp_folder TEXT,
    ftp_username TEXT,
    ftp_password TEXT,
    
    -- Backend: HTTP
    process_backend_http INTEGER,
    http_url TEXT,
    http_headers TEXT,
    http_field_name TEXT,
    http_auth_type TEXT,
    http_api_key TEXT,
    
    -- Reporting
    report_email_destination TEXT,
    reporting_email TEXT,
    
    -- EDI Output
    process_edi_output INTEGER,
    edi_output_folder TEXT,
    
    -- Audit Trail
    filename TEXT,
    original_path TEXT,
    processed_path TEXT,
    sent_to TEXT,
    edi_format TEXT,
    alert_on_failure INTEGER,
    
    -- Plugin Configuration
    plugin_config TEXT,
    
    -- Timestamps
    created_at TEXT,
    updated_at TEXT
);
```

### 3.2 settings

**Purpose:** Global application settings.

```sql
CREATE TABLE settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Email Configuration
    enable_email INTEGER,
    email_address TEXT,
    email_username TEXT,
    email_password TEXT,
    email_smtp_server TEXT,
    smtp_port INTEGER,
    
    -- AS/400 Configuration
    ssh_key_filename TEXT,
    as400_address TEXT,
    as400_username TEXT,
    as400_password TEXT,
    
    -- Backup Settings
    backup_counter INTEGER,
    backup_counter_maximum INTEGER,
    enable_interval_backups INTEGER,
    
    -- Default Folder Settings
    folder_is_active INTEGER,
    copy_to_directory TEXT,
    convert_to_format TEXT,
    process_edi INTEGER,
    calculate_upc_check_digit INTEGER,
    upc_target_length INTEGER,
    upc_padding_pattern TEXT,
    include_a_records INTEGER,
    include_c_records INTEGER,
    include_headers INTEGER,
    filter_ampersand INTEGER,
    tweak_edi INTEGER,
    pad_a_records INTEGER,
    a_record_padding TEXT,
    a_record_padding_length INTEGER,
    invoice_date_custom_format_string TEXT,
    invoice_date_custom_format INTEGER,
    reporting_email TEXT,
    folder_name TEXT,
    alias TEXT,
    report_email_destination TEXT,
    process_backend_copy INTEGER,
    backend_copy_destination TEXT,
    process_edi_output INTEGER,
    edi_output_folder TEXT,
    
    -- Timestamps
    created_at TEXT,
    updated_at TEXT
);
```

### 3.3 processed_files

**Purpose:** Track processed files for deduplication.

```sql
CREATE TABLE processed_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name TEXT,
    folder_alias TEXT,
    md5 TEXT,
    file_checksum TEXT,
    resend_flag INTEGER,
    folder_id INTEGER REFERENCES folders(id),
    created_at TEXT,
    processed_at TEXT,
    filename TEXT,
    original_path TEXT,
    processed_path TEXT,
    status TEXT,
    error_message TEXT,
    convert_format TEXT,
    sent_to TEXT
);
```

### 3.4 email_queue

**Purpose:** Email retry queue.

```sql
CREATE TABLE email_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipient TEXT,
    subject TEXT,
    body TEXT,
    attachment_path TEXT,
    status TEXT DEFAULT 'pending',
    created_at TEXT,
    last_attempt TEXT,
    attempt_count INTEGER DEFAULT 0
);
```

## 4. Migrations

**Location:** `migrations/`

| Migration | Purpose |
|-----------|---------|
| `add_plugin_config_column.py` | Add plugin_config column |
| `fix_missing_columns.py` | Fix missing columns in legacy DB |
| `folders_database_migrator.py` | Main folder schema migration |
| `legacy_migrations.py` | Legacy database migration |
| `modern_migrations.py` | Modern schema updates |

### Migration Pattern

```python
def migrate(db_conn: sqlite3.Connection) -> None:
    """Apply migration to database connection."""
    cursor = db_conn.cursor()
    cursor.execute("ALTER TABLE folders ADD COLUMN new_column TEXT")
    db_conn.commit()
```

## 5. Foreign Key Support

Foreign keys are enabled on connection:

```python
# backend/database/database_obj.py
def _connect_to_database(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
```

## 6. Related Documents

- [DATA_FLOW.md](DATA_FLOW.md) - Data flow with repository pattern
- [CONFIGURATION_SYSTEM.md](CONFIGURATION_SYSTEM.md) - Configuration storage
- [DESIGN_CORRECTIONS.md](DESIGN_CORRECTIONS.md) - Correction history
