# UI COMPONENTS (PyQt6 Windows/Dialogs/Widgets)

PyQt6 UI layer — Application, MainWindow, dialogs, custom widgets, plugin UI generator.

## STRUCTURE

```
ui/
├── app.py                 # Application, ApplicationSignals, create_application
├── main_window.py         # MainWindow, create_main_window
├── base_dialog.py         # BaseDialog, OkCancelDialog (validate/apply pattern)
├── plugin_ui_generator.py # Dynamic UI from ConfigField descriptors
├── dialogs/               # EditFolderDialog, EditSettingsDialog, MaintenanceDialog, etc.
└── widgets/               # ButtonPanel, FolderListWidget
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| App entry/signals | `app.py` | Application.signals (global events) |
| Main window composition | `main_window.py` | Composes ButtonPanel + FolderListWidget |
| Dialog base | `base_dialog.py` | validate()/apply() pattern |
| Folder edit dialog | `dialogs/edit_folder_dialog.py` | Large tabbed dialog (730 lines) |
| Settings dialog | `dialogs/edit_settings_dialog.py` | Global settings |
| Maintenance actions | `dialogs/maintenance_dialog.py` | Bulk operations |
| Button panel | `widgets/button_panel.py` | Top-level action buttons |
| Folder list | `widgets/folder_list.py` | Active/inactive lists, per-item actions |
| Plugin config UI | `plugin_ui_generator.py` | Builds widgets from ConfigField |

## SIGNAL PROPAGATION (Three-Layer)

**1. Widget-level** (local signals):
- `ButtonPanel.process_clicked`, `ButtonPanel.add_folder_clicked`
- `FolderListWidget.folder_edit_requested(int)`, `folder_delete_requested(int)`

**2. Window-level** (re-emission):
- MainWindow connects widget signals to own signals via `.connect(signal.emit)`
- Example: `self._button_panel.add_folder_clicked.connect(self.add_folder_requested.emit)`

**3. Controller** (business logic):
- ApplicationController connects to MainWindow signals
- Shows dialogs, calls operations, updates UI

**Pattern**: Re-emit via `widget_signal.connect(outer_signal.emit)` — keeps MainWindow simple forwarding layer

## CONVENTIONS

**Initialization pattern**:
- `__init__` → `_setup_ui()` → `_connect_signals()` → other init
- Dialogs use `_build_*` methods for tab construction

**Factories**:
- `create_application(argv)` — QApplication + ApplicationSignals
- `create_main_window(db_manager, app)` — MainWindow + controller wiring

**BaseDialog pattern**:
- Override `_create_widgets()`, `_setup_layout()`, `_set_initial_focus()`
- Implement `validate()` → `apply()` → `accept()` or `reject()`
- QDialogButtonBox wired to `_on_ok` / `_on_cancel`

**FolderListWidget lambdas**:
- Per-item buttons use `lambda checked, fid=folder_id: self._on_edit(fid)`
- Default argument (`fid=folder_id`) captures ID (avoids late-binding issue)

**PluginUIGenerator**:
- Dynamically builds widgets from `ConfigField` descriptors
- Used by EditFolderDialog to generate plugin config tabs

## ANTI-PATTERNS

**DO NOT**:
- Add business logic to widgets (emit signals, let controller handle)
- Create nested signal chains (widget → intermediate → window — keep flat)
- Directly call operations from dialogs (return data, controller calls operations)
- Use direct database access from UI (controller → operations → database)
