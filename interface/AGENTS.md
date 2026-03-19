# INTERFACE MODULE (PyQt6 GUI)

PyQt6 GUI application layer — models, operations, database access, UI components, validation.

## STRUCTURE

```
interface/
├── ui/                # Windows, dialogs, widgets (see ui/AGENTS.md)
├── operations/        # Processing, folder ops, maintenance
├── database/          # DatabaseManager, Table wrapper (dataset-like API)
├── models/            # Folder, ProcessedFile, Settings models
├── utils/             # Validators, validation feedback
├── application_controller.py  # Wires UI signals to business logic
└── main.py            # Entry point, arg parsing, DB path setup
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Wire new UI action | `application_controller.py` | Connects MainWindow signals to operations |
| Add folder operation | `operations/folder_operations.py` | add/remove/toggle/update folder |
| Add maintenance op | `operations/maintenance.py` | clear_processed, mark_processed |
| Processing orchestration | `operations/processing.py` | backup, dispatch, email reports |
| Database access | `database/database_manager.py` | DatabaseManager + Table wrapper |
| Data models | `models/folder.py`, `models/processed_file.py` | Dataclasses for DB records |
| Input validation | `utils/validation.py` | Pure validation functions |
| Qt validators | `utils/qt_validators.py` | EMAIL_VALIDATOR, PORT_VALIDATOR |
| Visual feedback | `utils/validation_feedback.py` | add_validation_to_fields |

## SIGNAL FLOW (Three-Layer Pattern)

1. **Widget-level**: `ButtonPanel.process_clicked`, `FolderListWidget.folder_edit_requested`
2. **Window-level**: `MainWindow` re-emits widget signals via `.connect(signal.emit)`
3. **Controller**: `ApplicationController` connects to MainWindow signals, calls operations

## DATABASE ACCESS

**Wrapper**: `DatabaseManager` + `Table` (dataset-like)
- `db["folders"].find(active=True)` — query with kwargs
- `db["folders"].insert({...})` — insert dict
- `db["folders"].update({...}, ["id"])` — update with key list
- `db.query("SELECT...")` — raw SQL fallback

**Connection**: `DatabaseManager._connect_to_database` enables `PRAGMA foreign_keys = ON`

## CONVENTIONS

**Operations pattern**: operations/processing.py uses ProcessingOrchestrator
- backup → dispatch → email reports → cleanup
- Long operations wrapped in QProgressDialog by controller

**Validation pattern**: dialogs use `interface.utils` validators
- `setup_validation_feedback()` wires validators to visual styling
- `add_validation_to_fields()` applies per-field feedback

**Model pattern**: dataclasses in models/ (NOT QObject properties)
- Simple Python dataclasses, no signals/reactive behavior
- DB interaction via DatabaseManager, not ORM

## ANTI-PATTERNS

**DO NOT**:
- Add business logic to UI widgets (put in operations/)
- Query database directly from widgets (use controller → operations)
- Create modal dialogs from within operations (operations return results, controller shows dialogs)
- Convert models to QObject unless reactive UI/QML required (design decision: keep simple)
