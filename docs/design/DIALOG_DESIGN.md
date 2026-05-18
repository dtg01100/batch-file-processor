# Dialog Design Document

**Version:** 1.0  
**Date:** 2026-05-18  
**Status:** DRAFT

---

## 1. Overview

Dialog components handle user interactions for folder management, settings configuration, and maintenance operations.

## 2. Dialog Hierarchy

```
BaseDialog (QDialog)
├── EditFoldersDialog
│   └── FolderListWidget
├── EditSettingsDialog
├── DatabaseImportDialog
├── MaintenanceDialog
├── ProcessedFilesDialog
└── ResendDialog
```

## 3. BaseDialog

**Module:** `interface/qt/dialogs/base_dialog.py`

```python
class BaseDialog(QDialog):
    """Base class for all dialogs."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(True)
    
    def validate(self) -> bool:
        """Override for dialog-specific validation."""
        return True
    
    def on_accept(self):
        """Called when OK/Accept is clicked."""
        pass
```

## 4. Edit Folders Dialog

**Module:** `interface/qt/dialogs/edit_folders/edit_folders_dialog.py`

### 4.1 Purpose

- Add/edit/delete folder configurations
- Configure converter and backend settings per folder
- Manage tweaks and splitting options

### 4.2 Key Components

```python
class EditFoldersDialog(BaseDialog):
    def __init__(self, folder_manager, plugin_manager, parent=None):
        # Initialize folder list
        # Setup form generator
        # Connect signals
    
    def add_folder(self):
        """Add new folder configuration."""
    
    def edit_folder(self, folder_id: int):
        """Edit existing folder."""
    
    def delete_folder(self, folder_id: int):
        """Remove folder configuration."""
```

### 4.3 Form Structure

```
EditFoldersDialog
├── FolderListWidget (left panel)
│   └── [Folder entries with icons]
├── FormPanel (right panel)
│   ├── GeneralSection
│   │   ├── folder_name
│   │   ├── folder_path
│   │   └── folder_description
│   ├── ConverterSection
│   │   └── [Dynamic from plugin]
│   ├── BackendSection
│   │   ├── email_enabled
│   │   ├── ftp_enabled
│   │   └── copy_enabled
│   └── TweaksSection
│       └── [Tweak rules]
└── ButtonPanel
    ├── OK
    ├── Cancel
    └── Apply
```

## 5. Edit Settings Dialog

**Module:** `interface/qt/dialogs/edit_settings_dialog.py`

### 5.1 Purpose

- Configure global email settings
- Configure default backend settings
- Application preferences

### 5.2 Form Structure

```
EditSettingsDialog
├── EmailSection
│   ├── enable_email (checkbox)
│   ├── email_address
│   ├── email_username
│   └── email_password
├── SMTPSection
│   ├── smtp_server
│   └── smtp_port
└── ButtonPanel
```

## 6. Maintenance Dialog

**Module:** `interface/qt/dialogs/maintenance_dialog.py`

### 6.1 Purpose

- Clear processed files log
- Reset folder statistics
- Database maintenance

### 6.2 Actions

| Action | Description |
|--------|-------------|
| Clear Processed | Clear processed_files table |
| Reset Statistics | Reset folder statistics |
| Optimize Database | Run VACUUM |

## 7. Resend Dialog

**Module:** `interface/qt/dialogs/resend_dialog.py`

### 7.1 Purpose

- Resend previously processed files
- Filter by date range or folder
- Retry failed sends

### 7.2 Structure

```
ResendDialog
├── FilterPanel
│   ├── folder_select
│   ├── date_from
│   └── date_to
├── FileList
│   └── [Files to resend]
└── ActionPanel
    ├── Resend Selected
    └── Cancel
```

## 8. Signal Flow

```
User clicks action
       ↓
Dialog emit signal
       ↓
MainWindow / window_controller re-emits
       ↓
Operations layer (folder_operations / processing / maintenance)
       ↓
Database updated (DatabaseObj)
       ↓
Completion signal emitted
       ↓
Dialog updates or closes
```

## 9. Validation Integration

Dialogs use `interface/validation/` validators:

```python
class EditFoldersDialog(BaseDialog):
    def validate(self) -> bool:
        """Validate folder settings."""
        validator = FolderSettingsValidator()
        errors = validator.validate(self.get_form_values())
        self.show_errors(errors)
        return len(errors) == 0
```

## 10. Related Documents

- [GUI_ARCHITECTURE.md](GUI_ARCHITECTURE.md) - GUI design
- [CONFIGURATION_SYSTEM.md](CONFIGURATION_SYSTEM.md) - Configuration
