# Data Flow Design Document

**Version:** 1.1  
**Date:** 2026-05-18  
**Status:** CORRECTED

---

## 1. Overview

This document describes how data moves through the Batch File Processor system, from input file discovery through processing to output delivery. **Updated to reflect actual codebase structure with adapter layer and lookup services.**

## 2. High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER (PyQt5 GUI)                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DispatchOrchestrator                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │ FolderProcessor │  │  FileProcessor   │  │      SendManager            │  │
│  │  (per-folder)   │  │   (per-file)    │  │      (backends)             │  │
│  └────────┬────────┘  └────────┬────────┘  └──────────────┬──────────────┘  │
│           │                    │                          │                 │
│           ▼                    ▼                          ▼                 │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      Pipeline Steps                                  │  │
│  │  Validator → Splitter → Converter                                  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
              ┌──────────┐    ┌──────────────┐   ┌──────────┐
              │  Email   │    │     FTP      │   │   Copy   │
              │ (SMTP)   │    │  (backend/)  │   │  Backend │
              └──────────┘    └──────────────┘   └──────────┘
```

## 3. Repository and Adapter Layer

The system uses an **Adapter Pattern** with repository interfaces for clean separation:

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

### 3.1 Repository Interface Usage

```python
# Application code uses repository interfaces
from core.ports.repositories import IFolderRepository

def process_folders(repo: IFolderRepository):
    folders = repo.find_all(active_only=True)
    for folder in folders:
        # Process folder
```

### 3.2 Adapter Implementation

```python
# adapters/sqlite/repositories/sqlite_folder_repo.py
class SqliteFolderRepository(IFolderRepository):
    def __init__(self, database_obj: DatabaseObj):
        self._db = database_obj
    
    def find_all(self, active_only: bool = False) -> list[dict]:
        if active_only:
            return list(self._db.folders_table.find(folder_is_active=True))
        return list(self._db.folders_table.all())
```

## 4. Processing Stages

### 4.1 File Discovery

**Source:** Configured folders in `folders` table  
**Mechanism:** `FileSystemInterface` via `FolderDiscoveryService`

```python
# dispatch/services/folder_discovery.py
class FolderDiscoveryService:
    def discover_files(self, folder_path: str) -> List[str]:
        """Return all files in folder, excluding already-processed."""
        all_files = os.listdir(folder_path)
        return self._filter_processed(all_files)
    
    def _filter_processed(self, files: List[str]) -> List[str]:
        """Filter out already-processed files using hash."""
        tracker = ProcessedFilesTracker()
        processed_hashes = tracker.get_hashes_for_folder(self.folder_id)
        return [f for f in files if compute_hash(f) not in processed_hashes]
```

### 4.2 Hash-Based Deduplication

**Purpose:** Skip files already processed (using MD5 hash)

```python
# dispatch/hash_utils.py
def compute_file_hash(file_path: str) -> str:
    """Compute MD5 hash of file contents."""
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            hasher.update(chunk)
    return hasher.hexdigest()
```

### 4.3 EDI Validation

**Purpose:** Verify file is valid EDI format  
**Module:** `dispatch/pipeline/validator.py`

```python
# dispatch/pipeline/validator.py
class ValidatorStep:
    def __init__(self, validator: EDIValidator, error_handler: ErrorHandler = None):
        self._validator = validator
        self._error_handler = error_handler
    
    def execute(self, input_path: str, context: dict) -> tuple[bool, str, list]:
        """Validate EDI format."""
        is_valid, errors = self._validator.validate_file(input_path)
        if not is_valid:
            self._record_error(input_path, errors)
            return (False, input_path, errors)
        return (True, input_path, [])
```

### 4.4 EDI Splitting

**Purpose:** Split multi-transaction EDI files into individual transactions  
**Module:** `dispatch/pipeline/splitter.py` / `core/edi/edi_splitter.py`

```python
# dispatch/pipeline/splitter.py
class SplitterStep:
    def execute(self, input_path: str, context: dict) -> tuple[bool, str, list]:
        """Split EDI file into transactions."""
        folder_config = context.get('folder', {})
        
        if not folder_config.get('split_edi'):
            return (True, input_path, [])
        
        transactions = split_edi_file(input_path)
        output_paths = write_transactions(transactions, context.get('temp_dir'))
        return (True, output_paths[0] if output_paths else input_path, [])
```

### 4.5 EDI Tweaking

**Purpose:** Apply field-level modifications to EDI data  
**Module:** `core/edi/edi_tweaker.py`

```python
# core/edi/edi_tweaker.py
def apply_tweaks(edi_content: str, tweak_config: dict, settings: dict) -> str:
    """Apply configured field tweaks and return modified EDI."""
    # Read tweak rules from plugin_config or flat columns
    # Apply NTE, REF, PER segment modifications
    # Return modified content
```

### 4.6 Format Conversion

**Purpose:** Convert EDI to target output format  
**Module:** `dispatch/pipeline/converter.py`

```python
# dispatch/pipeline/converter.py
class ConverterStep:
    def __init__(self, converter_registry: ConverterRegistry):
        self._registry = converter_registry
    
    def execute(self, input_path: str, context: dict) -> tuple[bool, str, list]:
        """Convert EDI to target format."""
        format_name = context.get('format', 'csv')
        converter = self._registry.get(format_name)
        
        edi_process = context.get('edi_process', {})
        output_path = context.get('output_path')
        
        success, output_path, errors = converter.convert(
            edi_process, output_path, 
            context.get('settings', {}),
            context.get('parameters', {}),
            context.get('upc_lookup')
        )
        return (success, output_path, errors)
```

### 4.7 Backend Dispatch

**Purpose:** Send converted files to configured destinations  
**Module:** `dispatch/send_manager.py`

```python
# dispatch/send_manager.py
class SendManager:
    DEFAULT_BACKENDS = {
        "copy": {"module": "backend.copy_backend", ...},
        "ftp": {"module": "backend.ftp_backend", ...},
        "email": {"module": "backend.email_backend", ...},
        "http": {"module": "backend.http_backend", ...},
    }
    
    def send_all(self, enabled_backends, file_path, params, settings) -> dict:
        """Send file via all enabled backends."""
        results = {}
        for backend_name in enabled_backends:
            backend = self._get_backend(backend_name)
            results[backend_name] = backend.do(params, settings, file_path)
        return results
```

## 5. Lookup Services Flow

```
Processing Context
       │
       ▼
┌────────────────────────────────┐
│      UPC Lookup Service         │
│  dispatch/services/upc_service.py│
│                                │
│  - Lookup UPC in database       │
│  - Validate check digit         │
│  - Pad/normalize UPC            │
│  - Handle override rules        │
└────────────────────────────────┘
       │
       ▼ (optional, via converter)
┌────────────────────────────────┐
│  Customer Lookup Service        │
│  dispatch/services/customer_lookup_service.py │
│                                │
│  - Lookup customer by ID        │
│  - Get billing/shipping info   │
│  - Return customer details     │
└────────────────────────────────┘
       │
       ▼ (optional)
┌────────────────────────────────┐
│     UOM Lookup Service          │
│  dispatch/services/uom_lookup_service.py │
│                                │
│  - Lookup unit of measure      │
│  - Normalize UOM codes         │
└────────────────────────────────┘
```

### 5.1 UPC Service

```python
# dispatch/services/upc_service.py
class UPCService:
    def __init__(self, db: DatabaseInterface, settings: dict):
        self._db = db
        self._settings = settings
    
    def lookup_upc(self, upc: str, folder: dict) -> dict:
        """Lookup and normalize UPC."""
        # Check for override rules
        # Validate check digit
        # Pad to target length
        # Return lookup result
```

### 5.2 Customer Service

```python
# dispatch/services/customer_lookup_service.py
class CustomerLookupService:
    def get_customer(self, customer_id: str) -> dict:
        """Get customer information."""
        # Query customer database
        # Return billing/shipping info
```

## 6. Backend Delivery Flow

### 6.1 Copy Backend

```python
# backend/copy_backend.py
def do(process_parameters, settings_dict, filename, disable_retry=False) -> bool:
    """Copy file to local destination."""
    dest_dir = process_parameters.get('copy_to_directory') or settings_dict.get('copy_to_directory')
    dest_path = os.path.join(dest_dir, os.path.basename(filename))
    shutil.copy2(filename, dest_path)
```

### 6.2 FTP Backend

```python
# backend/ftp_backend.py
def do(process_parameters, settings_dict, filename, disable_retry=False) -> bool:
    """Upload file via FTP/FTPS."""
    ftp_settings = {
        'server': process_parameters.get('ftp_server'),
        'port': process_parameters.get('ftp_port', 21),
        'username': process_parameters.get('ftp_username'),
        'password': process_parameters.get('ftp_password'),
        'folder': process_parameters.get('ftp_folder'),
    }
    with FTPClient(ftp_settings) as ftp:
        ftp.upload(filename)
```

### 6.3 Email Backend

```python
# backend/email_backend.py
def do(process_parameters, settings_dict, filename, disable_retry=False) -> bool:
    """Send file as email attachment."""
    with SMTPClient(settings_dict) as server:
        msg = create_email_message(
            to=process_parameters.get('email_to'),
            subject=process_parameters.get('email_subject_line'),
            attachment=filename
        )
        server.send(msg)
```

### 6.4 HTTP Backend

```python
# backend/http_backend.py
def do(process_parameters, settings_dict, filename, disable_retry=False) -> bool:
    """Upload file via HTTP POST."""
    url = process_parameters.get('http_url')
    auth = get_http_auth(process_parameters)
    headers = parse_headers(process_parameters.get('http_headers'))
    
    with open(filename, 'rb') as f:
        response = requests.post(
            url,
            files={process_parameters.get('http_field_name', 'file'): f},
            headers=headers,
            auth=auth
        )
```

## 7. State Management

### 7.1 Database Tables

| Table | Purpose |
|-------|---------|
| `folders` | Folder configurations with converter/backend settings (60+ columns) |
| `processed_files` | Track processed files with hashes and timestamps |
| `settings` | Global application settings |
| `email_queue` | Queued email items for retry |

### 7.2 Processing State Flow

```
1. Start Processing
   ↓
2. Load folder config via SqliteFolderRepository
   ↓
3. Discover new files via FolderDiscoveryService
   ↓
4. Filter by hash via FileFilter (skip already processed)
   ↓
5. Process each file through pipeline:
   - ValidatorStep
   - SplitterStep (if enabled)
   - ConverterStep (applies EDI tweaks when convert_to_format = "tweaks")
   ↓
6. Send via SendManager to backends
   ↓
7. Record in ProcessedFilesTracker
   ↓
8. Update processed_files table via SqliteProcessedFilesRepository
```

## 8. Error Handling Flow

```
Processing Error
      │
      ▼
ErrorHandler.record_error()
      │
      ├──► Log to file (scripts/record_error.do)
      ├──► Update error buffer
      ├──► Send error email (if configured)
      └──► Record to database (optional)

Continue processing remaining files
```

## 9. Related Documents

- [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md) - Architecture principles
- [PROCESSING_PIPELINE.md](PROCESSING_PIPELINE.md) - Pipeline details
- [BACKEND_ARCHITECTURE.md](BACKEND_ARCHITECTURE.md) - Backend implementations
- [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) - Database design with repository pattern
- [DESIGN_CORRECTIONS.md](DESIGN_CORRECTIONS.md) - Correction history
