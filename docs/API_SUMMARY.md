# API Reference Summary

**Generated:** 2026-01-30  
**Commit:** c2898be44  
**Branch:** cleanup-refactoring

## 1. Overview

This document summarizes the key public APIs, classes, and interfaces in the batch file processor system.

## 2. GUI Layer APIs

### 2.1 Application (`interface/ui/app.py`)

```python
class Application(QApplication):
    signals: ApplicationSignals
    
    @property
    def database_manager(self) -> Optional[DatabaseManager]
    
    @database_manager.setter
    def database_manager(self, manager: DatabaseManager) -> None
```

### 2.2 ApplicationSignals

```python
class ApplicationSignals(QObject):
    # Database signals
    database_changed = Signal()
    
    # Folder signals
    folder_added = Signal(int)        # folder_id
    folder_updated = Signal(int)      # folder_id
    folder_deleted = Signal(int)      # folder_id
    folder_toggled = Signal(int, bool)  # folder_id, is_active
    
    # Processing signals
    processing_started = Signal()
    processing_finished = Signal()
    processing_error = Signal(str)    # error_message
    processing_progress = Signal(int, int)  # current, total
```

### 2.3 MainWindow (`interface/ui/main_window.py`)

```python
class MainWindow(QMainWindow):
    # Signals
    process_directories_requested = Signal()
    add_folder_requested = Signal()
    batch_add_folders_requested = Signal()
    edit_settings_requested = Signal()
    maintenance_requested = Signal()
    processed_files_requested = Signal()
    exit_requested = Signal()
    edit_folder_requested = Signal(int)      # folder_id
    toggle_active_requested = Signal(int)    # folder_id
    delete_folder_requested = Signal(int)    # folder_id
    send_folder_requested = Signal(int)      # folder_id
    
    # Properties
    @property
    def db_manager(self) -> DatabaseManager
    
    @property
    def app(self) -> Optional[Application]
    
    # Methods
    def refresh_folder_list(self) -> None
```

### 2.4 BaseDialog (`interface/ui/base_dialog.py`)

```python
class BaseDialog(QDialog):
    def validate(self) -> bool:
        """Validate inputs. Returns True if valid."""
        pass
    
    def apply(self) -> None:
        """Apply changes. Called only if validate() returns True."""
        pass
```

## 3. Database Layer APIs

### 3.1 Table (`core/database/connection.py`)

```python
class Table:
    def __init__(self, connection: sqlite3.Connection, table_name: str)
    
    def find(self, order_by: Optional[str] = None, **kwargs) -> List[Dict[str, Any]]
    def find_one(self, **kwargs) -> Optional[Dict[str, Any]]
    def all(self) -> List[Dict[str, Any]]
    def insert(self, data: Dict[str, Any]) -> None
    def insert_many(self, records: List[Dict[str, Any]]) -> None
    def update(self, data: Dict[str, Any], keys: List[str]) -> None
    def delete(self, **kwargs) -> None
    def count(self, **kwargs) -> int
    def distinct(self, column: str) -> List[Any]
```

### 3.2 DatabaseConnection (`core/database/connection.py`)

```python
class DatabaseConnection:
    def __init__(self, connection: sqlite3.Connection)
    def __getitem__(self, table_name: str) -> Table
    def query(self, sql: str) -> None
    def close(self) -> None
    @property
    def raw_connection(self) -> sqlite3.Connection
```

### 3.3 DatabaseManager (`core/database/manager.py`)

```python
class DatabaseManager:
    def __init__(self, database_path: str, config_folder: str,
                 platform: str, app_version: str, database_version: str)
    
    def reload(self) -> None
    def close(self) -> None
    
    # Table references
    @property
    def folders_table(self) -> Table
    @property
    def settings(self) -> Table
    @property
    def processed_files(self) -> Table
    @property
    def emails_table(self) -> Table
```

## 4. Processing Layer APIs

### 4.1 DispatchCoordinator (`dispatch/coordinator.py`)

```python
class DispatchCoordinator:
    def __init__(self, database_connection, folders_database, run_log,
                 emails_table, run_log_directory, reporting, processed_files,
                 root, args, version, errors_folder, settings, simple_output=None)
    
    def process(self) -> Tuple[bool, str]:
        """Main processing function. Returns (has_errors, run_summary_string)."""
        pass
```

### 4.2 SendManager (`dispatch/send_manager.py`)

```python
class SendManager:
    BACKEND_CONFIG = {
        'copy': ('copy_backend', 'copy_to_directory', 'Copy Backend'),
        'ftp': ('ftp_backend', 'ftp_server', 'FTP Backend'),
        'email': ('email_backend', 'email_to', 'Email Backend')
    }
    
    def send_file(self, file_path: str, parameters_dict: dict, 
                  settings: dict) -> List[SendResult]
```

### 4.3 SendResult (`dispatch/send_manager.py`)

```python
class SendResult:
    def __init__(self, success: bool, backend_name: str, destination: str,
                 error_message: str = "", details: Dict[str, Any] = None)
```

## 5. Plugin APIs

### 5.1 BaseConverter (`convert_base.py`)

```python
class BaseConverter:
    PLUGIN_ID: str = "base"
    PLUGIN_NAME: str = "Base Converter"
    PLUGIN_DESCRIPTION: str = ""
    CONFIG_FIELDS: List[dict] = []
    
    def __init__(self, edi_process: str, output_filename: str,
                 settings_dict: dict, parameters_dict: dict, upc_lookup: dict)
    
    def initialize_output(self) -> None
    def process_record_a(self, record: dict) -> None
    def process_record_b(self, record: dict) -> None
    def process_record_c(self, record: dict) -> None
    def finalize_output(self) -> None
    def process(self, input_file: str) -> str
```

### 5.2 BaseSendBackend (`send_base.py`)

```python
class BaseSendBackend:
    PLUGIN_ID: str = "base"
    PLUGIN_NAME: str = "Base Backend"
    PLUGIN_DESCRIPTION: str = ""
    CONFIG_FIELDS: List[dict] = []
    
    def __init__(self, process_parameters: dict, settings_dict: dict, filename: str)
    
    def get_config_value(self, key: str, default=None) -> Any
    def _send(self) -> None:
        """Override in subclass."""
        raise NotImplementedError
```

## 6. Entry Points

### 6.1 GUI Entry

```python
# interface/main.py
def main() -> int:
    app = create_application(sys.argv)
    db_manager = DatabaseManager(...)
    window = create_main_window(db_manager=db_manager)
    window.show()
    return app.exec()
```

### 6.2 Processing Entry

```python
# dispatch/coordinator.py
def process(database_connection, folders_database, run_log, emails_table,
            run_log_directory, reporting, processed_files, root, args,
            version, errors_folder, settings, simple_output=None) -> Tuple[bool, str]:
```

## 7. Return Types

### 7.1 Processing Result

```python
Tuple[bool, str]  # (has_errors, run_summary_string)
```

### 7.2 Send Result

```python
List[SendResult]  # One result per backend
```

## 8. File Locations Reference

| File | Purpose |
|------|---------|
| `interface/main.py` | GUI entry point |
| `interface/ui/app.py` | Application class |
| `interface/ui/main_window.py` | Main window |
| `core/database/connection.py` | Database wrappers |
| `core/database/manager.py` | Database manager |
| `dispatch/coordinator.py` | Processing coordinator |
| `dispatch/send_manager.py` | Send manager |
| `dispatch/edi_processor.py` | EDI components |
| `convert_base.py` | Converter base |
| `send_base.py` | Backend base |
