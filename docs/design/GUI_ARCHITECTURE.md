# GUI Architecture

**Version:** 1.0  
**Date:** 2026-05-18  
**Status:** DRAFT

---

## 1. Overview

The GUI layer is built with PyQt5 and follows a layered architecture with clear separation between UI components, business logic, and data access.

## 2. Layer Structure

```
interface/qt/
├── app.py              # QApplication setup and window creation
├── bootstrap.py        # Service initialization
├── theme.py            # Application styling
├── window_controller.py # Window lifecycle management
├── run_coordinator.py  # Processing coordination
├── diagnostics.py      # Diagnostics utilities
│
├── dialogs/            # Dialog windows
│   ├── edit_folders/
│   │   ├── edit_folders_dialog.py
│   │   └── base_dialog.py
│   ├── database_import_dialog.py
│   ├── edit_settings_dialog.py
│   ├── maintenance_dialog.py
│   ├── processed_files_dialog.py
│   └── resend_dialog.py
│
├── widgets/            # Reusable widgets
│   ├── folder_list_widget.py
│   └── search_widget.py
│
└── services/           # Qt service layer
    └── qt_services.py
```

## 3. Entry Points

### 3.1 main_interface.py

```bash
# GUI mode
python main_interface.py

# Automatic/headless mode
python main_interface.py -a
```

### 3.2 main_qt.py

Desktop shortcut entry point (wraps main_interface).

## 4. Application Bootstrap

```python
# interface/qt/app.py
class QtBatchFileSenderApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self._setup_theme()
        self._init_services()
        self._create_main_window()
    
    def _setup_theme(self):
        """Apply application styling."""
        from interface.qt.theme import setup_theme
        setup_theme(self.app)
    
    def _init_services(self):
        """Initialize application services."""
        from interface.qt.bootstrap import init_services
        init_services(self)
```

## 5. Main Window

**Module:** `interface/qt/app.py`

```python
class MainWindow(QMainWindow):
    def __init__(self, database_manager, orchestrator):
        super().__init__()
        self.db = database_manager
        self.orchestrator = orchestrator
        self._setup_ui()
    
    def _setup_ui(self):
        """Initialize UI components."""
        # Central widget setup
        # Menu bar
        # Status bar
        # Toolbar
```

## 6. Dialog Architecture

### 6.1 Base Dialog

```python
# interface/qt/dialogs/base_dialog.py
class BaseDialog(QDialog):
    """Base class for all dialogs."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(True)
    
    def accept(self):
        """Override to add validation."""
        if self.validate():
            super().accept()
    
    def validate(self) -> bool:
        """Override to implement dialog-specific validation."""
        return True
```

### 6.2 Edit Folders Dialog

```python
# interface/qt/dialogs/edit_folders/edit_folders_dialog.py
class EditFoldersDialog(BaseDialog):
    def __init__(self, folder_manager, plugin_manager, parent=None):
        super().__init__(parent)
        self.folder_manager = folder_manager
        self.plugin_manager = plugin_manager
```

## 7. Form Generation

**Module:** `interface/form/form_generator.py`

Dynamic form generation for folder configuration:

```python
class FormGenerator:
    def generate_form(self, plugin: ConfigurationPlugin) -> List[QWidget]:
        """Generate form widgets from plugin configuration."""
        sections = plugin.get_sections()
        widgets = []
        for section in sections:
            for field in section.fields:
                widget = self._create_widget(field)
                widgets.append(widget)
        return widgets
```

## 8. Service Layer

**Module:** `interface/qt/services/qt_services.py`

Qt-specific services that bridge UI and operations:

```python
class QtServices:
    def __init__(self, db_manager, operations):
        self.progress = QtProgressService(operations.progress)
        self.reporting = QtReportingService(operations.reporting)
```

## 9. UI-Business Logic Decoupling

### 9.1 Decoupled Areas

| Component | Decoupled From | Via |
|-----------|----------------|-----|
| Dialogs | Database | FolderManager, Operations |
| Form Generator | Plugin Config | ConfigurationPlugin |
| Progress Display | Processing | ProgressService |
| Error Display | Dispatch | ErrorHandler |

### 9.2 Coupling Points (Historical — Resolved in v1.1 PyQt5 refactor)

The following areas were identified in the original Tkinter-era analysis.
**All have been resolved** by the v1.1 PyQt5 refactor:

| Issue | Resolution |
|-------|------------|
| Tkinter variables as state containers | ✅ Replaced by `QCheckBox.isChecked()`, `QLineEdit.text()`, Qt signals |
| Direct database access from dialog code | ✅ All DB access via `DatabaseObj` / repository pattern in operations layer |
| Network operations in validation methods | ✅ Moved to services layer (`interface/services/`) with injectable protocols |
| `tweak_edi` Tkinter variable name | ✅ Now a `QCheckBox` in PyQt5 dialogs |

## 10. Related Documents

- [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md) - Architecture principles
- [DIALOG_DESIGN.md](DIALOG_DESIGN.md) - Dialog interactions
- [CONFIGURATION_SYSTEM.md](CONFIGURATION_SYSTEM.md) - Configuration UI
