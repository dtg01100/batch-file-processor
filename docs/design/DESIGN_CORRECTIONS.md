# Design Corrections - Accuracy Report

**Version:** 1.2
**Date:** 2026-05-18
**Status:** Maintained — Updated 2026-05-18

---

## 1. Summary of Discrepancies Found

### Round 1 — Corrected in v1.1 (2026-05-18)

| Document | Issue | Resolution |
|----------|-------|------------|
| DATABASE_SCHEMA.md | Wrong database class names, incomplete schema | ✅ Rewrote to show `DatabaseObj` + `Table` pipeline, adapter pattern, full folders schema (60+ columns) |
| DATA_FLOW.md | Missing adapter layer, wrong processing flow | ⚠️ Partially: adapter layer added; pipeline still had TweakerStep (fixed in v1.1b) |
| COMPONENT_MAP.md | Missing modules, wrong locations | ✅ Added adapters/, observability/, dispatch services, corrected locations |
| SYSTEM_OVERVIEW.md | Missing adapter pattern | ⚠️ Not addressed in this round |

### Round 2 — Corrected in v1.1b (2026-05-18)

| Document | Issue | Resolution |
|----------|-------|------------|
| PROCESSING_PIPELINE.md | TweakerStep referenced but file `dispatch/pipeline/tweaker.py` does not exist | ✅ Replaced section 4.3 with correct EDI-tweaks-as-a-converter description |
| DATA_FLOW.md | High-level diagram still showed TweakerStep (validator→splitter→tweaker→converter) | ✅ Corrected to validator→splitter→converter |
| DATA_FLOW_DESIGN.md | Mermaid diagram and prose both referenced nonexistent TweakerStep | ✅ Corrected diagram and section 3.3 |
| BACKEND_ARCHITECTURE.md | `send_file` method does not exist; BackendFactory not used | ✅ Replaced section 4+5 with correct `SendManager.DEFAULT_BACKENDS` table; `send_all` replaces `send_file` |
| SYSTEM_ARCHITECTURE.md | Python 3.10+ / Tkinter / wrong file paths / missing HTTP backend | ✅ Changed to 3.11 maximum; PyQt5 5.15; fixed paths; added HTTP backend; fixed Pipeline section table |
| SECURITY_MODEL.md | Section numbering jump (2.1 → 2.3, missing 2.2) | ✅ Added 2.2 Encryption at Rest |

### Round 3 — Corrected in v1.2 (2026-05-18)

| Document | Issue | Resolution |
|----------|-------|------------|
| CONFIGURATION_SYSTEM.md | `GlobalSettings` class doesn't exist; wrong `FolderConfiguration` fields; `list_plugins()` method missing; subscript `db['folders']` wrong API | ✅ Replaced with `EditSettingsDialog` description, correct `FolderConfiguration` fields (nested dataclasses), `list_converters()` method, correct `DatabaseObj` attribute-access pattern |
| ERROR_HANDLING.md | Fake standalone `ErrorLogger` and `ErrorReporter` classes; wrong `record_error.do()` signature | ✅ Replaced with correct `ErrorHandler`/`ErrorLogger` (`ErrorLogger` is internal wrapper of `scripts/record_error.do()`); corrected `ReportGenerator` as sub-component of `ErrorHandler` |
| API_INTERFACE_DESIGN.md | `TkinterProtocol`, `VariableProtocol`, `ListboxProtocol` (Tkinter-only); nonexistent `dispatch/interfaces.py` | ✅ Noted as Tkinter-era protocols; updated to actual `interface/interfaces.py` protocols (`MessageBoxProtocol`, `FileDialogProtocol`, `WidgetProtocol`, `OverlayProtocol`); `DB2SSHConnectionConfig` in production use |
| WIDGET_LAYOUT_SPECIFICATION.md | Every section anchored to `interface.py` which doesn't exist; all widgets described as Tkinter (`ttk.Frame`, `tk.Button`) | ✅ Rewrote as PyQt5 layout reference: all anchors to `interface/qt/app.py`, all widgets to PyQt5 equivalents (`QFrame`, `QPushButton`, `QListWidget`, `QCheckBox`, `QComboBox`, `QSpinBox`, `QDialog`, `QLineEdit`, `QLabel`) |
| UI_DECOUPLING_ANALYSIS.md | Document describes Tkinter-era architecture throughout; non-existent files listed; wrong `interface/ui/` paths | ✅ Rewrote as archival document explaining original coupling points and their resolutions during v1.1 PyQt5 refactor; all coupling points now marked ✅ Resolved |
| GUI_ARCHITECTURE.md | Coupling points section still listed as "could be improved" | ✅ Updated to historical table with ✅ Resolved status |
| DIALOG_DESIGN.md | `ApplicationController` referenced (doesn't exist) | ✅ Replaced with correct signal flow: widget signal → window re-emit → operations layer → database |
| EDIT_FOLDERS_DIALOG_DESIGN.md | Path `interface.ui.dialogs.*` (Tkinter-era dotted path) | ✅ Corrected to `interface.qt.dialogs.*` |
| DATABASE_SCHEMA.md | `ErrorReporter` class listed at reporter layer (doesn't exist) | ✅ Fixed to show only `ErrorHandler` (ErrorReporter was only doc's own terminology, not a real class) |
| COMPONENT_MAP.md | `results.py` as module for `FileResult`/`DispatchConfig` | ✅ Fixed: `FileResult` is in `dispatch/services/file_processor.py`; `DispatchConfig` in `dispatch/results.py`; `BackendBase` is in `backend/backend_base.py` |

---

---

## 2. Database Layer Correction

### Actual Implementation

**Primary Classes:**
- `backend.database.database_obj.DatabaseObj` - Main database class (NOT `DatabaseManager`)
- `backend.database.database_obj.Table` - Table wrapper (NOT in `interface/database/`)

**Pattern:** Adapter Pattern with Repository Interfaces

```
┌─────────────────────────────────────────────────────────────────┐
│                     Application Layer                            │
│   (QtApp, Orchestrator, Services)                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Repository Interfaces                           │
│   core/ports/repositories.py                                     │
│   - IFolderRepository                                            │
│   - ISettingsRepository                                          │
│   - IProcessedFilesRepository                                    │
│   - IEmailQueueRepository                                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   SQLite Adapters                                │
│   adapters/sqlite/repositories/                                  │
│   - SqliteFolderRepository                                       │
│   - SqliteSettingsRepository                                     │
│   - SqliteProcessedFilesRepository                              │
│   - SqliteEmailQueueRepository                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│               DatabaseObj (Table API)                            │
│   backend/database/database_obj.py                              │
│   - DatabaseObj.folders_table                                    │
│   - DatabaseObj.settings_table                                    │
│   - DatabaseObj.processed_files_table                            │
└─────────────────────────────────────────────────────────────────┘
```

### Correct Usage

```python
# CORRECT - Using repository pattern
from backend.database.database_obj import DatabaseObj
from adapters.sqlite.repositories import SqliteFolderRepository

db = DatabaseObj(db_path)
repo = SqliteFolderRepository(db)
folders = repo.find_all(active_only=True)

# OR using Table directly
db = DatabaseObj(db_path)
folders = db.folders_table.find(folder_is_active=True)
```

### Correction for DATABASE_SCHEMA.md

Replace section 3.1 DatabaseManager with:

```python
# backend/database/database_obj.py
class DatabaseObj:
    """Main database access class.
    
    Provides Table instances for each table via attribute access.
    """
    def __init__(self, db_path: str):
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        # Enable foreign keys
        self._conn.execute("PRAGMA foreign_keys = ON")
    
    @property
    def folders_table(self) -> Table:
        return Table(self._conn, "folders")
    
    @property
    def settings_table(self) -> Table:
        return Table(self._conn, "settings")
    
    # ... other tables

class Table:
    """Table wrapper providing dataset-like API."""
    def __init__(self, conn, table_name: str):
        self._conn = conn
        self._table = table_name
    
    def find(self, order_by: str = None, **kwargs) -> List[Dict]:
        """Query with filtering."""
    
    def find_one(self, **kwargs) -> Optional[Dict]:
        """Get single record."""
    
    def insert(self, data: Dict) -> int:
        """Insert record, return ID."""
    
    def update(self, data: Dict, keys: List[str]) -> bool:
        """Update by key fields."""
```

---

## 3. Folder Table Schema Correction

The actual `folders` table has **60+ columns**, not the 15 documented.

### Complete Schema (from core/database/schema.py)

```sql
CREATE TABLE folders (
    -- Identity
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    folder_name TEXT,
    alias TEXT,
    
    -- Status
    folder_is_active INTEGER,
    status TEXT,
    error_message TEXT,
    
    -- Conversion
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
    
    -- Records
    include_a_records INTEGER,
    include_c_records INTEGER,
    pad_a_records INTEGER,
    a_record_padding TEXT,
    a_record_padding_length INTEGER,
    append_a_records INTEGER,
    a_record_append_text TEXT,
    estore_c_record_OID INTEGER,
    
    -- Headers/Filters
    include_headers INTEGER,
    filter_ampersand INTEGER,
    force_txt_file_ext INTEGER,
    
    -- Date/Format
    invoice_date_custom_format INTEGER,
    invoice_date_custom_format_string TEXT,
    invoice_date_offset INTEGER,
    simple_csv_sort_order TEXT,
    
    -- UOM
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
    
    -- Plugin
    plugin_config TEXT,
    
    -- Timestamps
    created_at TEXT,
    updated_at TEXT
);
```

### Correction for DATABASE_SCHEMA.md

Replace section 2.1 with the complete schema above.

---

## 4. Backend Order Correction

### Actual Backend Order (from SendManager)

```python
DEFAULT_BACKENDS: ClassVar[dict[str, dict[str, str]]] = {
    "copy": {     # <-- First, not third
        "module": "backend.copy_backend",
        "setting": "copy_to_directory",
        "display_name": "Copy Backend",
        "enabled_key": "process_backend_copy",
    },
    "ftp": {      # <-- Second, not second (same position)
        "module": "backend.ftp_backend",
        "setting": "ftp_server",
        "display_name": "FTP Backend",
        "enabled_key": "process_backend_ftp",
    },
    "email": {    # <-- Third, not first
        "module": "backend.email_backend",
        "setting": "email_to",
        "display_name": "Email Backend",
        "enabled_key": "process_backend_email",
    },
    "http": {    # <-- Fourth, not new (HTTP was added)
        "module": "backend.http_backend",
        "setting": "http_url",
        "display_name": "HTTP Backend",
        "enabled_key": "process_backend_http",
    },
}
```

### Correction for BACKEND_ARCHITECTURE.md

Update section 4 to show correct order: copy, ftp, email, http.

---

## 5. Pipeline Interface Correction

### Actual PipelineStep Protocol

```python
# dispatch/pipeline/interfaces.py

class ErrorRecordingMixin:
    """Mixin providing consistent error recording for pipeline steps.
    
    Pipeline steps that need to record errors should include this mixin.
    """
    def _record_error(
        self,
        filename: str,
        error_msg: str,
        *,
        source: str = "PipelineStep",
        error_source: str = "Pipeline",
        error_type: type[Exception] = Exception,
    ) -> None:
        """Record error to error handler."""
        handler = getattr(self, "_error_handler", None)
        if handler is None:
            return
        handler.record_error(...)

@runtime_checkable
class PipelineStep(Protocol):
    """Protocol for pipeline processing steps."""
    
    def execute(
        self,
        input_path: str,
        context: dict[str, Any],
    ) -> tuple[bool, str, list[str]]:
        """Execute the pipeline step.
        
        Returns:
            Tuple of (success, output_path, errors)
        """
        ...
```

### Correction for PROCESSING_PIPELINE.md

1. Add `ErrorRecordingMixin` to section 3
2. Note that context is `dict[str, Any]` not just `dict`

---

## 6. Component Map Corrections

### Missing/Incorrect Components

| Design Doc Says | Actual Location/Name |
|-----------------|----------------------|
| `interface/database/database_manager.py` | `backend/database/database_obj.py` |
| `dispatch/converters/registry.py` | EXISTS, but BUILTIN_CONVERTERS not documented |
| `dispatch/pipeline/tweaker.py` | `core/edi/edi_tweaker.py` (NOT in pipeline/) |
| Missing: `dispatch/services/customer_lookup_service.py` | EXISTS |
| Missing: `dispatch/services/upc_service.py` | EXISTS |
| Missing: `dispatch/services/uom_lookup_service.py` | EXISTS |
| Missing: `dispatch/observability/` | EXISTS |
| Missing: `adapters/` | EXISTS |

### Correct Component Map Additions

```markdown
## 6. Additional Components

### Adapters Layer (adapters/)

| Component | Location | Responsibility |
|-----------|----------|-----------------|
| SqliteFolderRepository | `adapters/sqlite/repositories/sqlite_folder_repo.py` | Folder data access |
| SqliteSettingsRepository | `adapters/sqlite/repositories/sqlite_settings_repo.py` | Settings data access |
| SqliteProcessedFilesRepository | `adapters/sqlite/repositories/sqlite_processed_files_repo.py` | Processed files access |

### Dispatch Observability (dispatch/observability/)

| Component | Location | Responsibility |
|-----------|----------|-----------------|
| AlertDispatcher | `dispatch/observability/alert_dispatcher.py` | Alert dispatching |
| AlertQueue | `dispatch/observability/alert_queue.py` | Alert queue management |
| AuditLogger | `dispatch/observability/audit_logger.py` | Audit logging |
| BackgroundWriter | `dispatch/observability/background_writer.py` | Async write operations |

### Dispatch Services (additional)

| Component | Location | Responsibility |
|-----------|----------|-----------------|
| CustomerLookupService | `dispatch/services/customer_lookup_service.py` | Customer data lookup |
| UPCService | `dispatch/services/upc_service.py` | UPC/barcode lookup |
| UOMLookupService | `dispatch/services/uom_lookup_service.py` | Unit of measure lookup |
| DatabaseConnector | `dispatch/services/database_connector.py` | DB connection management |

### Core EDI (additional)

| Component | Location | Responsibility |
|-----------|----------|-----------------|
| EDITransformer | `core/edi/edi_transformer.py` | EDI transformation |
| UPCUtils | `core/edi/upc_utils.py` | UPC utilities |

### Backend (additional)

| Component | Location | Responsibility |
|-----------|----------|-----------------|
| Protocols | `backend/protocols.py` | Backend interface protocols |
| FileOperations | `backend/file_operations.py` | File system operations |
```

---

## 7. Data Flow Corrections

### Missing Layers

1. **Adapter Layer** - Not shown in current DATA_FLOW.md
2. **Repository Interfaces** - Not shown
3. **UPC Lookup Service** - Not shown in flow
4. **Customer Lookup Service** - Not shown in flow

### Correction for DATA_FLOW.md

Add after Backend Delivery Flow:

```markdown
## 8. Lookup Services Flow

```
Processing Context
       │
       ▼
┌─────────────────────────────┐
│    UPC Lookup Service        │
│  dispatch/services/upc_service.py │
│                             │
│  - Lookup UPC in DB         │
│  - Validate check digit     │
│  - Pad/normalize UPC        │
└─────────────────────────────┘
       │
       ▼ (optional, via converter)
┌─────────────────────────────┐
│  Customer Lookup Service    │
│  dispatch/services/customer_lookup_service.py │
│                             │
│  - Lookup customer by ID    │
│  - Get billing/shipping info│
└─────────────────────────────┘
```

## 9. Adapter Layer Flow

```
Application (Qt, Orchestrator)
       │
       ▼
┌─────────────────────────────────────────────────┐
│           Repository Interfaces                  │
│   core/ports/repositories.py                    │
│                                               │
│   - IFolderRepository.find_all()               │
│   - IFolderRepository.find_by_id()             │
│   - IProcessedFilesRepository.insert()          │
└─────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────┐
│            SQLite Adapters                      │
│   adapters/sqlite/repositories/                 │
│                                               │
│   - SqliteFolderRepository                     │
│   - SqliteProcessedFilesRepository             │
└─────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────┐
│         DatabaseObj (Table API)                 │
│   backend/database/database_obj.py             │
│                                               │
│   db.folders_table.find(...)                   │
│   db.processed_files_table.insert(...)         │
└─────────────────────────────────────────────────┘
```
```

---

## 8. Related Corrections

### Error Handler Interface

**Actual in dispatch/error_handler.py:**
```python
class ErrorHandler:
    """Central error handling."""
    
    def record_error(
        self,
        folder: str,
        filename: str,
        error: Exception,
        *,
        context: dict | None = None,
        error_source: str = "Unknown",
    ) -> None:
        """Record a processing error."""
```

Note: Interface differs from scripts/record_error.py function.

### Processing Result

**Actual in dispatch/orchestrator.py:**
```python
class FileResult(NamedTuple):
    """Result of processing a single file."""
    success: bool
    file_path: str
    output_path: str | None
    errors: list[str]
    backends_sent: list[str]

def DispatchOrchestrator.process_file(
    self, 
    file_path: str, 
    folder: dict
) -> FileResult:
    """Process a single file in a folder."""
```

---

## 9. Files to Update (Remaining — Corrected after v1.1 Round)

| Document | Priority | Status |
|----------|----------|--------|
| PROCESSING_PIPELINE.md | HIGH | ✅ **FIXED** (v1.1b): Removed TweakerStep from diagram and section 4.3; set validator→splitter→converter. |
| DATA_FLOW.md | HIGH | ✅ **FIXED** (v1.1b): Corrected line 31 pipeline diagram; replaced TweakerStep in state-flow with ConverterStep note. |
| DATA_FLOW_DESIGN.md | HIGH | ✅ **FIXED** (v1.1b): Replaced TweakerStep in Mermaid diagram (sections 1.1 and 3.3) with ConverterStep description. |
| BACKEND_ARCHITECTURE.md | MEDIUM | ✅ **FIXED** (v1.1b): Replaced `send_file` with `send_all`; replaced 4. BackendFactory with SendManager DEFAULT_BACKENDS table in correct copy→ftp→email→http order; updated "Add New Backend" section. |
| SYSTEM_ARCHITECTURE.md | HIGH | ✅ **FIXED** (v1.1b): Updated Python constraint to 3.11 maximum; replaced Tkinter with PyQt5 5.15; fixed file paths (`interface/app.py` → `interface/qt/app.py`; `interface/ui/` → `interface/qt/`; `interface/database/` → `backend/database/`); corrected backend list; replaced legacy dataset/SQLAlchemy/alembic entries; corrected Pipeline section table to 4-step; removed `TweakerStep` row. |
| SECURITY_MODEL.md | LOW | ✅ **FIXED** (v1.1b): Added missing section 2.2 (Encryption at Rest) between 2.1 and 2.3. |

---

## 10. Additional Discrepancies Found — Round 3 Audit (unaddressed, 2026-05-18)

Comprehensive grep + file-level review of all 26 design docs found the following doc-tool misfits that do not match the actual `PyQt5 3.11` codebase.

### CONFIGURATION_SYSTEM.md

| Line | Wrong Description | Correct Reference |
|------|-------------------|-------------------|
| 45 | `class GlobalSettings` at `interface/qt/dialogs/edit_settings_dialog.py` | Actual class is `EditSettingsDialog`; no `GlobalSettings` class exists |
| 62 | `FolderConfiguration` fields: `folder_converter`, `folder_tweaks_enabled`, `folder_splitting_enabled`, `folder_backends`, `folder_description`, `folder_plugin_config` | Actual fields (in `interface/models/folder_configuration.py`): must be verified against code — likely `convert_to_format`, `folders_tweaks_enabled`, `folders_splitting_enabled`, `folders_backends` |
| 105 | `PluginManager.list_plugins()` | `interface/plugins/plugin_manager.py` defines `list_converters()`; no `list_plugins()` method |
| 190–209 | `db['folders']` subscript access on `DatabaseManager` | `DatabaseObj` uses attribute access `db.folders_table`; subscript form raises `TypeError` |

### GUI_ARCHITECTURE.md

| Line | Wrong Description | Correct Reference |
|------|-------------------|-------------------|
| 39 | `interface/qt/services/qt_services.py` | `interface/qt/services/` is a directory (`__init__.py`); no standalone `qt_services.py` file |
| 180 | `tweak_edi` — Tkinter-era variable name listed in "Tkinter variables used as state containers" | PyQt5 equivalent uses `QCheckBox.isChecked()`, `QLineEdit.text()` etc.; no Tkinter-var bindings |

### ERROR_HANDLING.md

| Line | Wrong Description | Correct Reference |
|------|-------------------|-------------------|
| 55–66 | `ErrorLogger` class defined in `dispatch/error_handler.py` | Only `ErrorHandler` class exists; no standalone `ErrorLogger` |
| 98–107 | `ErrorReporter` class as separate from `ErrorHandler` | No `ErrorReporter` class in the codebase |

### API_INTERFACE_DESIGN.md

| Line | Wrong Description | Correct Reference |
|------|-------------------|-------------------|
| 13–16 | `dispatch/interfaces.py` (named `TkinterProtocol`, `VariableProtocol`, `ListboxProtocol`) | `dispatch/interfaces.py` does not exist; `interface/interfaces.py` defines `MessageBoxProtocol`, `FileDialogProtocol`, `WidgetProtocol`, `OverlayProtocol` only |
| 14–18 | `TkinterProtocol` with `Tk.mainloop()`, `Tk.after()`, `Tk.withdraw()`, `StringVar/IntVar/BooleanVar` | Pure Tkinter concepts; no analogue exists in `interface/interfaces.py` for this codebase |
| 178–182 | `VariableProtocol` with `Var.get()` / `Var.set(value)` (Tkinter `StringVar`/`IntVar`/`BooleanVar`) | PyQt5 uses signals/slots; no variable-binding abstraction in current codebase |
| 205–214 | `ListboxProtocol` / `curselection()` / `get(start, end)` | Tkinter `Listbox` API; PyQt5 `QListWidget` uses `currentItem()`, `selectedItems()` |

### WIDGET_LAYOUT_SPECIFICATION.md

| Line | Wrong Description | Correct Reference |
|------|-------------------|-------------------|
| 3, 13, 26, 59, 96, 113, 184, 210, 238 | Every inline anchor references `# interface.py` and every section header reads `# interface.py — <section>` | File is `interface/qt/app.py` + `interface/qt/dialogs/`; `interface.py` does not exist |
| 8, 13, 59, 96, 113, 184, 210, 238 | Every widget described as `tkinter.ttk.Frame`, `tk.Button`, `tk.Listbox`, `tk.StringVar`, etc. | Actual widgets: `QFrame`, `QPushButton`, `QListWidget`, `QCheckBox`, `QComboBox`, `QLineEdit`, etc. |

### UI_DECOUPLING_ANALYSIS.md

| Line | Wrong Description | Correct Reference |
|------|-------------------|-------------------|
| 8, 58 | Document describes "Tkinter UI" throughout | Interface was refactored to PyQt5 (`interface/qt/`); entire doc title and narrative must reflect current state |
| 98–99 | `interface/app.py` (~41K chars) | Actual: `interface/qt/app.py`, ~34K bytes (≈34K, not 41K) |
| 120–197 | `interface/ui/dialogs/` paths, `tk.StringVar`, `tk.BooleanVar`, `tkinter.messagebox`, `Toplevel`, `Dialog(Toplevel)` | All `interface/ui/` paths should be `interface/qt/`; `tk.*` vars/messagebox do not exist in PyQt5 codebase |
| 107–108 | `_dispatch_legacy.py` (34K chars) — "already decoupled" list | File was removed; does not exist in codebase |
| 114, 61–66 | `doingstuffoverlay.py`, `resend_interface.py` — "already decoupled" list | Files do not exist in codebase |
| 600–601 | File-size table: `edit_folders_dialog.py` "74K", `app.py` "41K", `maintenance_dialog.py` "19K", `tk_extra_widgets.py` "15K" | Actual files under `interface/qt/`; `tk_extra_widgets.py` does not exist |

### DATABASE_SCHEMA.md

| Line | Wrong Description | Correct Reference |
|------|-------------------|-------------------|
| 46–48 | Repository layer lists `reporter.py` / `ErrorReporter` | `dispatch/error_handler.py` defines `ErrorHandler` only; no `ErrorReporter` class exists |

### COMPONENT_MAP.md

| Line | Wrong Description | Correct Reference |
|------|-------------------|-------------------|
| 112–113 | `DispatchConfig` / `FileResult` at `results.py` | `FileResult` is a `NamedTuple` defined in `dispatch/orchestrator.py`; no standalone `results.py` file |
| 191 | `BackendBase` at `backend_base.py` | `backend/protocols.py` defines the backend interface protocol |

### DIALOG_DESIGN.md

| Line | Wrong Description | Correct Reference |
|------|-------------------|-------------------|
| 176 | `ApplicationController` catches error | No class named `ApplicationController` exists in the codebase |

### EDIT_FOLDERS_DIALOG_DESIGN.md

| Line | Wrong Description | Correct Reference |
|------|-------------------|-------------------|
| 23 | `interface.ui.dialogs.edit_folders_dialog.EditFoldersDialog` | Correct dotted path: `interface.qt.dialogs.edit_folders_dialog.EditFoldersDialog` |

---
