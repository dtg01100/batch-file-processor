# Widget Layout Specification

> **Note:** This document describes the current PyQt5 UI layout as of the
> 2026-05-18 codebase. The layout structure follows `interface/qt/`.
> Historical Tkinter-era layout differences are documented in
> `DESIGN_CORRECTIONS.md` §10.

This document provides a comprehensive specification of the widget layout for
the Batch File Sender application. It details the visual hierarchy, layout
management, and widget configuration for all major dialogs and windows.

---

## 1. Main Application Window (`interface/qt/app.py`)

The main application window is created by `QtBatchFileSenderApp`, a
`QWidget`-based app that delegates to `interface/qt/dialogs/` for all
user-facing popups.

### 1.1 Primary Dialogs

| Dialog | Location | Purpose |
|--------|----------|---------|
| `EditFoldersDialog` | `qt/dialogs/edit_folders_dialog.py` | Edit folder settings (also lives as sub-package) |
| `EditSettingsDialog` | `qt/dialogs/edit_settings_dialog.py` | Global settings |
| `MaintenanceDialog` | `qt/dialogs/maintenance_dialog.py` | Advanced maintenance operations |
| `ResendDialog` | `qt/dialogs/resend_dialog.py` | Resend failed files |
| `ProcessedFilesDialog` | `qt/dialogs/processed_files_dialog.py` | View/export processed file reports |
| `DatabaseImportDialog` | `qt/dialogs/database_import_dialog.py` | Import database from legacy format |

### 1.2 Primary Widgets

| Widget | Location | Purpose |
|--------|----------|---------|
| `FolderListWidget` | `qt/widgets/folder_list_widget.py` | Scrolled list of folder rows with edit/send/delete actions |
| `SearchWidget` | `qt/widgets/search_widget.py` | Filter/search the folder list |
| `ButtonPanel` | `qt/widgets/folder_list_widget.py` | Row action buttons (edit, send, delete) |

### 1.3 Architecture

The main window follows a **three-layer signal pattern** documented in
`interface/AGENTS.md`:

```
Widget-level (ButtonPanel, FolderListWidget)
       │  emit signals  │
       ▼
Window-level (MainWindow: re-emits via .connect(signal.emit))
       │
       ▼
Controller (ApplicationController: connects signals to operations)
```

---

## 2. Folder List Widget (`interface/qt/widgets/folder_list_widget.py`)

Displays the active/inactive folder rows with per-row action buttons.

### 2.1 Visual Hierarchy

*   **FolderListWidget** (`QWidget`/`QListWidget`)
    *   **Inactive Section**
        *   `QLabel`: "Inactive Folders"
        *   **Container** (`QWidget`/`QVBoxLayout`)
            *   Per-folder row with **ButtonPanel**
    *   **Active Section**
        *   `QLabel`: "Active Folders"
        *   **Container** (`QWidget`/`QVBoxLayout`)
            *   Per-folder row with **ButtonPanel**

### 2.2 Layout

Both sections use `QVBoxLayout` inside `QWidget` containers. The outer
`FolderListWidget` uses a `QVBoxLayout` to stack the inactive and active
sections.

---

## 3. Search Widget (`interface/qt/widgets/search_widget.py`)

A reusable widget for filtering the folder list.

### 3.1 Visual Hierarchy

*   **SearchWidget** (`QWidget`)
    *   `QLineEdit` — search input
    *   `QPushButton` — "Filter" / "Clear Filter"

### 3.2 Layout

Uses `QHBoxLayout`. `QLineEdit` expands (stretch 1), `QPushButton` is fixed
width on the right.

---

## 4. Edit Settings Dialog (`interface/qt/dialogs/edit_settings_dialog.py`)

A modal dialog for configuring application-wide settings.

### 4.1 Visual Hierarchy

*   **EditSettingsDialog** (`QDialog`)
    *   **Email Options Group** (`QGroupBox`)
        *   `QCheckBox`: "Enable Email"
        *   `QLineEdit`: Email address
        *   `QLineEdit`: Username
        *   `QLineEdit`: Password
        *   `QLineEdit`: SMTP server
        *   `QSpinBox`: SMTP port
    *   **Interval Backups Group** (`QGroupBox`)
        *   `QCheckBox`: "Enable interval backup"
        *   `QSpinBox`: Backup interval
    *   **Report Options Group** (`QGroupBox`)
        *   `QLineEdit`: Report email destination
        *   `QCheckBox`: "Enable Report Sending"
        *   `QCheckBox`: "Report EDI Validator Warnings"
        *   `QCheckBox`: "Enable Report Printing Fallback"
    *   **Buttons**
        *   `QPushButton`: "Select Log Folder…"
        *   `QDialogButtonBox`: OK / Cancel

### 4.2 Layout

Uses `QFormLayout` for field groups; `QVBoxLayout` at the dialog level.  
Form fields use `addRow(QLabel, QWidget)` pairs.

---

## 5. Maintenance Dialog (`interface/qt/dialogs/maintenance_dialog.py`)

A dialog for advanced maintenance operations.

### 5.1 Visual Hierarchy

*   **MaintenanceDialog** (`QDialog`)
    *   **Button Layout** (`QVBoxLayout`)
        *   `QPushButton`: "Move all to active (Skips Settings Validation)"
        *   `QPushButton`: "Move all to inactive"
        *   `QPushButton`: "Clear all resend flags"
        *   `QPushButton`: "Clear queued emails"
        *   `QPushButton`: "Mark all in active as processed"
        *   `QPushButton`: "Remove all inactive configurations"
        *   `QPushButton`: "Clear sent file records"
        *   `QPushButton`: "Import old configurations…"
    *   **Warning Label** (`QLabel`)

### 5.2 Layout

Uses `QVBoxLayout`. Buttons are stacked vertically; warning label is at the
bottom.

---

## 6. Processed Files Dialog (`interface/qt/dialogs/processed_files_dialog.py`)

A dialog for viewing and exporting processed file reports.

### 6.1 Visual Hierarchy

*   **ProcessedFilesDialog** (`QDialog`)
    *   **Browser List** (`QListWidget`)
        *   Folder alias items (selectable)
    *   **Action Panel**
        *   `QLabel`: "Select a Folder."
        *   `QPushButton`: "Choose Output Folder" (dynamic, enabled on selection)
        *   `QPushButton`: "Export Processed Report"
    *   **Close Button**

### 6.2 Layout

Uses `QHBoxLayout` for the list + action panel split; `QVBoxLayout` for
the action panel buttons.

---

## 7. Edit Folders Dialog (`interface/qt/dialogs/edit_folders_dialog.py`)

A complex dialog for editing individual folder settings.  
Highly dynamic — options change based on the selected "Convert To" format.

### 7.1 Visual Hierarchy

*   **EditFoldersDialog** (`QDialog`)
    *   **Header** (`QWidget`)
        *   `QCheckBox`: "Active"
    *   **Other Configs** (`QGroupBox`)
        *   `QListWidget`: List of other folders (for copying config)
        *   `QPushButton`: "Copy Config"
    *   **Folder Settings** (`QGroupBox`)
        *   Path, Alias, Backend selection checkboxes
    *   **Backend Settings** (`QGroupBox`)
        *   Copy, FTP, and Email backend configuration
    *   **EDI Settings** (`QGroupBox`)
        *   `QCheckBox`: "Process EDI"
        *   `QCheckBox`: "Split EDI"
        *   `tweak_edi` (`QCheckBox`): "Enable EDI Tweaks"
        *   Convert-to format selector
        *   **Convert Options** — dynamically shown/hidden based on format
    *   **Buttons**
        *   `QPushButton`: "Save"
        *   `QPushButton`: "Cancel"

### 7.2 Layout

Uses `QVBoxLayout` at the dialog level; `QFormLayout` within `QGroupBox`
containers. Dynamic plugin panels are stacked below the format selector and
shown/hidden with `setVisible()` based on the selected converter format.

---

## 8. Resend Dialog (`interface/qt/dialogs/resend_dialog.py`)

A dialog for resending previously-failed files.

*   **ResendDialog** (`QDialog`)
    *   **File browser** (`QListWidget`) showing failed file records
    *   **Action buttons** (`QPushButton`): "Resend Selected", "Resend All"
    *   **Close button**

---

## PyQt5 Widget Mapping (v1.1 — replaces Tkinter-era layout)

| Tkinter (legacy) | PyQt5 (current) | Notes |
|---|---|---|
| `tkinter.Tk` | `QApplication` + `QWidget` | Top-level app object |
| `tkinter.ttk.Frame` | `QWidget` / `QFrame` | Container widget |
| `tkinter.Button` | `QPushButton` | Push button |
| `tkinter.ttk.Button` | `QPushButton` | Push button |
| `tkinter.Label` | `QLabel` | Text label |
| `tkinter.ttk.Label` | `QLabel` | Text label |
| `tkinter.Entry` | `QLineEdit` | Single-line text input |
| `tkinter.BooleanVar` | `QCheckBox.isChecked()` | Boolean state |
| `tkinter.StringVar` | `QLineEdit.text()` | String state |
| `tkinter.ttk.Combobox` | `QComboBox` | Dropdown selector |
| `tkinter.ttk.Checkbutton` | `QCheckBox` | Checkbox |
| `tkinter.ttk.Spinbox` | `QSpinBox` | Numeric spinners |
| `tkinter.Toplevel` | `QDialog` | Modal popup |
| `tkinter.ScrolledText` | `QTextEdit` (read-only) | Text display |
| `tkinter.Listbox` | `QListWidget` | Scrollable item list |
| tkinter `pack()` / `grid()` | `QVBoxLayout`, `QHBoxLayout`, `QFormLayout`, `QGridLayout` | Qt layout managers |

---

## 9. Backend Codes (Error Dialog — UI Decoupling Design Reference)

*See `interface/qt/actions/error_home_action.py` and
`interface/qt/dialogs/edit_settings.py` — the backend systems (`email_backend`,
`COPY_DESTINATION`, `ftp_backend`) are handled at the `SendManager` layer
(`dispatch/send_manager.py`) and are NOT referenced directly from the dialog
widgets themselves.*

---







