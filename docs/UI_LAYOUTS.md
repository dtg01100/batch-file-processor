# UI Layout Documentation

This document provides ASCII art diagrams showing the layout structure of all windows, dialogs, and widgets in the Batch File Processor application.

---

## Table of Contents

1. [MainWindow](#mainwindow)
2. [ButtonPanel Widget](#buttonpanel-widget)
3. [FolderListWidget](#folderlistwidget)
4. [BaseDialog](#basedialog)
5. [EditFolderDialog](#editfolderdialog)
6. [EditSettingsDialog](#editsettingsdialog)
7. [MaintenanceDialog](#maintenancedialog)
8. [ProcessedFilesDialog](#processedfilesdialog)

---

## MainWindow

**File:** `interface/ui/main_window.py`

```
+==================================================================================+
| Window Title: "Batch File Processor"                                             |
| Minimum Size: 900x600                                                           |
+==================================================================================+
| +------------------------------------------------------------------------------+ |
| | QHBoxLayout (Central Widget)                                                  | |
| | ContentsMargins: 5,5,5,5 | Spacing: 5                                       | |
| +------------------------------------------------------------------------------+ |
| |                                                                              | |
| | +--------------------------+  +-------+  +--------------------------------+ | |
| | | QFrame (Sidebar)         |  | QFrame|  | QWidget (Content Area)        | | |
| | | SizePolicy: Fixed        |  |(Line) |  | VBoxLayout                    | | |
| | | MinWidth: 160, MaxWidth: |  | VLine |  | ContentsMargins: 5,5,5,5     | | |
| | |           180            |  |       |  | Spacing: 5                    | | |
| | +--------------------------+  +-------+  +--------------------------------+ | |
| | | QVBoxLayout              |          |  |                              | | |
| | | ContentsMargins: 5,5,5,5|          |  | QSplitter (Horizontal)       | | |
| | | Spacing: 3               |          |  | +--------------------------+  | | |
| | +--------------------------+          |  | | FolderListWidget         |  | | |
| | | [ButtonPanel]            |          |  | | (Active/Inactive Split)  |  | | |
| | | +----------------------+ |          |  | +--------------------------+  | | |
| | | | QVBoxLayout           | |          |  |                              | | |
| | | | [Add Directory...]   | |          |  +------------------------------+ | |
| | | | [Batch Add...]       | |          |                                  | |
| | | | -------------------  | |          |                                  | |
| | | | [Set Defaults...]    | |          |                                  | |
| | | | -------------------  | |          |                                  | |
| | | | [Process All Folders]| |          |                                  | |
| | | | -------------------  | |          |                                  | |
| | | | [Processed Files...]  | |          |                                  | |
| | | | -------------------  | |          |                                  | |
| | | | [Maintenance...]     | |          |                                  | |
| | | | -------------------  | |          |                                  | |
| | | | [Edit Settings...]    | |          |                                  | |
| | | | <spacer>              | |          |                                  | |
| | | | -------------------  | |          |                                  | |
| | | | [Enable Resend]       | |          |                                  | |
| | | +----------------------+ |          |                                  | |
| | +--------------------------+          |                                  | |
| |                                      |                                  | |
| +--------------------------------------+----------------------------------+ |
|                                                                              | |
+------------------------------------------------------------------------------+
```

**Signal Flow:**
- `process_directories_requested` - Process all directories
- `add_folder_requested` - Add new folder
- `batch_add_folders_requested` - Batch add folders
- `set_defaults_requested` - Set defaults
- `edit_settings_requested` - Edit settings
- `maintenance_requested` - Open maintenance
- `processed_files_requested` - View processed files
- `enable_resend_requested` - Enable resend
- `edit_folder_requested(int)` - Edit folder (folder_id)
- `toggle_active_requested(int)` - Toggle active (folder_id)
- `delete_folder_requested(int)` - Delete folder (folder_id)
- `send_folder_requested(int)` - Send folder (folder_id)

---

## ButtonPanel Widget

**File:** `interface/ui/widgets/button_panel.py`

```
+----------------------------------------------------------------------+
| ButtonPanel (QWidget)                                                |
+----------------------------------------------------------------------+
| QVBoxLayout                                                          |
| ContentsMargins: 5,5,5,5 | Spacing: 3                               |
+----------------------------------------------------------------------+
| [QPushButton: "Add Directory..."] (min-width: 140)                   |
| [QPushButton: "Batch Add Directories..."] (min-width: 140)          |
| -------------------------------------------------------------------- |
| QFrame (HLine, Sunken)                                               |
| -------------------------------------------------------------------- |
| [QPushButton: "Set Defaults..."] (min-width: 140)                    |
| -------------------------------------------------------------------- |
| QFrame (HLine, Sunken)                                               |
| -------------------------------------------------------------------- |
| [QPushButton: "Process All Folders"] (min-width: 140)               |
| -------------------------------------------------------------------- |
| QFrame (HLine, Sunken)                                               |
| -------------------------------------------------------------------- |
| [QPushButton: "Processed Files Report..."] (min-width: 140)        |
| -------------------------------------------------------------------- |
| QFrame (HLine, Sunken)                                               |
| -------------------------------------------------------------------- |
| [QPushButton: "Maintenance..."] (min-width: 140)                    |
| -------------------------------------------------------------------- |
| QFrame (HLine, Sunken)                                               |
| -------------------------------------------------------------------- |
| [QPushButton: "Edit Settings..."] (min-width: 140)                  |
| <QSpacer (Expanding)>                                                |
| -------------------------------------------------------------------- |
| QFrame (HLine, Sunken)                                               |
| -------------------------------------------------------------------- |
| [QPushButton: "Enable Resend"] (min-width: 140)                      |
+----------------------------------------------------------------------+

**Signals:**
- `process_clicked` - Process button clicked
- `add_folder_clicked` - Add folder clicked
- `batch_add_clicked` - Batch add clicked
- `set_defaults_clicked` - Set defaults clicked
- `edit_settings_clicked` - Edit settings clicked
- `maintenance_clicked` - Maintenance clicked
- `processed_files_clicked` - Processed files clicked
- `enable_resend_clicked` - Enable resend clicked
```

---

## FolderListWidget

**File:** `interface/ui/widgets/folder_list.py`

```
+----------------------------------------------------------------------+
| FolderListWidget (QWidget)                                           |
+----------------------------------------------------------------------+
| QVBoxLayout                                                          |
| ContentsMargins: 0,0,0,0 | Spacing: 5                               |
+----------------------------------------------------------------------+
| QHBoxLayout (Search Bar)                                             |
| +----------------------------------------------+ +-----------------+ |
| | QLabel: "Filter:"                            | | QLineEdit       | |
| |                                              | | (Placeholder:   | |
| |                                              | |  "Type to       | |
| |                                              | |  filter...")   | |
| +----------------------------------------------+ +-----+-----------+ |
|                                              +---+ [Update Filter]  |
+----------------------------------------------------------------------+
| QLabel: "[count] folders" (AlignRight)                                |
+----------------------------------------------------------------------+
| QSplitter (Horizontal)                                               |
| +----------------------------------+ +------------------------------+ |
| | QFrame (Inactive Folders)         | | QFrame (Active Folders)     | |
| | Style: StyledPanel | Sunken       | | Style: StyledPanel | Sunken | |
| +----------------------------------+ +------------------------------+ |
| | QVBoxLayout                       | | QVBoxLayout                  | |
| | ContentsMargins: 5,5,5,5          | | ContentsMargins: 5,5,5,5    | |
| +----------------------------------+ +------------------------------+ |
| | QLabel: "Inactive Folders"        | | QLabel: "Active Folders"    | |
| | (Style: font-weight: bold)        | | (Style: font-weight: bold)  | |
| +----------------------------------+ +------------------------------+ |
| | QListWidget                       | | QListWidget                  | |
| | - SelectionMode: NoSelection      | | - SelectionMode: NoSelection| |
| | - HScrollBarPolicy: AlwaysOff     | | - HScrollBarPolicy: AlwaysOff|
| | - Each item is a QFrame widget    | | - Each item is a QFrame     | |
| |   with VBoxLayout:                | |   with VBoxLayout:          | |
| |   +---------------------------+   | | +-------------------------+  | |
| |   | QLabel: "<alias>"         |   | | | QLabel: "<alias>"      |  | |
| |   +---------------------------+   | | +-------------------------+  | |
| |   | QHBoxLayout (Buttons)     |   | | | QHBoxLayout (Buttons)  |  | |
| |   | +--------+ +----+ +-----+ |   | | | +----+ +---+ +------+  |  | |
| |   | | [Edit..]| |Delete|      |   | | | |[Send]| |<-| [Edit..]| |  | |
| |   | +--------+ +----+         |   | | | +----+ +---+ +------+  |  | |
| |   +---------------------------+   | | +-------------------------+  | |
| +----------------------------------+ +------------------------------+ |
+----------------------------------------------------------------------+

**Folder Item Layout (per item in list):**
```
+--------------------------+
| QFrame (Card Widget)     |
| Border: 1px solid #888   |
| BorderRadius: 4px        |
+--------------------------+
| QVBoxLayout              |
| ContentsMargins: 4,2,4,2  |
| Spacing: 2               |
+--------------------------+
| QLabel: "<folder_alias>"  |
| AlignLeft | AlignVCenter |
+--------------------------+
| QHBoxLayout (Buttons)   |
| Spacing: 2               |
| +--------+ +----+ +----+|
| |[Edit...]|[Delete]     || <- Inactive folder
| +--------+ +----+        |
|                        OR
| +----+ +---+ +--------+ |
| |Send|<-- | [Edit...] | | <- Active folder
| +----+ +---+ +--------+ |
+--------------------------+
```

**Signals:**
- `folder_edit_requested(int)` - Edit folder (folder_id)
- `folder_toggle_active(int)` - Toggle active (folder_id)
- `folder_delete_requested(int)` - Delete folder (folder_id)
- `folder_send_requested(int)` - Send folder (folder_id)
```

---

## BaseDialog

**File:** `interface/ui/base_dialog.py`

```
+----------------------------------------------------------------------+
| BaseDialog (QDialog)                                                |
| Window Title: "Dialog" | Modal: True | SystemMenuHint              |
+----------------------------------------------------------------------+
| QVBoxLayout                                                          |
+----------------------------------------------------------------------+
| QWidget (_body_frame) - Content area for subclasses                 |
| (To be filled by subclasses)                                         |
+----------------------------------------------------------------------+
| QDialogButtonBox                                                     |
| +-------------------------------------------+                       |
| | [ Cancel ]                          [ OK ] |                       |
| +-------------------------------------------+                       |
+----------------------------------------------------------------------+

**Pattern:**
- Subclasses override `_create_widgets()` and `_setup_layout()`
- OK/Cancel buttons: `accepted_data` signal emits dict on accept
- `validate()` - Override for validation
- `apply()` - Override to collect data
- `show_modal()` - Returns result dict or None
```

---

## EditFolderDialog

**File:** `interface/ui/dialogs/edit_folder_dialog.py`

```
+==================================================================================================+
| EditFolderDialog (QDialog)                                                                        |
| Window Title: "Edit Folder" or "Add Folder" | Modal: True | Size: 700x500                      |
+==================================================================================================+
| QVBoxLayout                                                                                      |
+--------------------------------------------------------------------------------------------------+
| QTabWidget                                                                                       |
| +------------------------------------------------------------------------------------------------+
| | [ General ] [ FTP Settings ] [ Email Settings ] [ Copy Settings ] [ EDI Processing ] [Conversion] |
| +------------------------------------------------------------------------------------------------+
| |                                                                                                |
| | TAB 1: General                                                                                |
| | +--------------------------------------------------------------------------------------------+ |
| | | QVBoxLayout                                                                                | |
| | | +----------------------------------------------------------------------------------------+ | |
| | | | QCheckBox: "Active"                                                                    | | |
| | | +----------------------------------------------------------------------------------------+ | |
| | |                                                                                            | |
| | | QGroupBox: "Folder Alias"                                                                 | |
| | | +----------------------------------------------------------------------------------------+ | |
| | | | QVBoxLayout                                                                            | | |
| | | | [QLineEdit: folder_alias_input] (Placeholder: "Enter folder alias...")                  | | |
| | | | [QPushButton: "Show Folder Path"]                                                      | | |
| | | +----------------------------------------------------------------------------------------+ | |
| | |                                                                                            | |
| | | QGroupBox: "Backends"                                                                     | |
| | | +----------------------------------------------------------------------------------------+ | |
| | | | QVBoxLayout (Dynamic - one checkbox per send backend plugin)                             | | |
| | | | +--------------------------------------------------------------------------------------+| | |
| | | | | [ ] Copy Backend                                                                     | | |
| | | | +--------------------------------------------------------------------------------------+| | |
| | | | +--------------------------------------------------------------------------------------+| | |
| | | | | [ ] FTP Backend                                                                      | | |
| | | | +--------------------------------------------------------------------------------------+| | |
| | | | +--------------------------------------------------------------------------------------+| | |
| | | | | [ ] Email Backend                                                                    | | |
| | | | +--------------------------------------------------------------------------------------+| | |
| | | +----------------------------------------------------------------------------------------+ | |
| | | <Stretch>                                                                                | |
| | +--------------------------------------------------------------------------------------------+ |
| |                                                                                                |
| | TAB 2-N: Backend Settings (one tab per enabled send plugin)                                   |
| | +--------------------------------------------------------------------------------------------+ |
| | | PluginUIGenerator.create_plugin_config_widget() - Dynamic UI from ConfigField specs       | |
| | +--------------------------------------------------------------------------------------------+ |
| |                                                                                                |
| | TAB: EDI Processing                                                                           |
| | +--------------------------------------------------------------------------------------------+ |
| | | QVBoxLayout                                                                                | |
| | | [ ] Force EDI Validation                                                                   | |
| | | [ ] Split EDI Documents                                                                    | |
| | | [ ] Include Invoices in Split                                                              | |
| | | [ ] Include Credits in Split                                                               | |
| | | [ ] Prepend Dates to Files                                                                 | |
| | | QHBoxLayout: [Label: "Rename File:"] [QLineEdit: rename_field]                           | |
| | | QHBoxLayout: [Label: "EDI Options:"] [QComboBox: {"Do Nothing", "Convert EDI", "Tweak EDI"}] | |
| | +--------------------------------------------------------------------------------------------+ |
| |                                                                                                |
| | TAB: Conversion Format                                                                         |
| | +--------------------------------------------------------------------------------------------+ |
| | | QVBoxLayout                                                                                | |
| | | [ ] Process EDI                                                                           | |
| | | QHBoxLayout: [Label: "EDI Format:"] [QComboBox: available formats]                        | |
| | | QHBoxLayout: [Label: "Convert To:"] [QComboBox: {csv, ScannerWare, scansheet-type-a,       | |
| | |                                              jolley_custom, stewarts_custom,              | |
| | |                                              simplified_csv, Estore eInvoice,              | |
| | |                                              Estore eInvoice Generic,                    | |
| | |                                              YellowDog CSV, fintech}]                     | |
| | |                                                                                            | |
| | | QStackedWidget (Format-specific options - switches based on format selection)             | |
| | | +--------------------------------------------------------------------------------------+   | |
| | | | CSV Options: [ ] Calculate UPC Check Digit, [ ] Include A Records, [ ] Include C...,   | | |
| | | +--------------------------------------------------------------------------------------+   | |
| | | +--------------------------------------------------------------------------------------+   | |
| | | | ScannerWare Options: [ ] Pad "A" Records                                               | | |
| | | +--------------------------------------------------------------------------------------+   | |
| | | +--------------------------------------------------------------------------------------+   | |
| | | | Simplified CSV Options: [ ] Include Item Numbers, [ ] Include Item Description       | | |
| | | +--------------------------------------------------------------------------------------+   | |
| | | +--------------------------------------------------------------------------------------+   | |
| | | | Estore eInvoice: QGridLayout [Label: "Store Number:"] [QLineEdit],                    | | |
| | | |                    [Label: "Vendor OId:"] [QLineEdit]                                | | |
| | | +--------------------------------------------------------------------------------------+   | |
| | | +--------------------------------------------------------------------------------------+   | |
| | | | Estore eInvoice Generic: QGridLayout [Label: "Store Number:"] [QLineEdit],            | | |
| | | |                            [Label: "Vendor OId:"] [QLineEdit],                       | | |
| | | |                            [Label: "C Record OId:"] [QLineEdit]                      | | |
| | | +--------------------------------------------------------------------------------------+   | |
| | | +--------------------------------------------------------------------------------------+   | |
| | | | Fintech Options: QHBoxLayout [Label: "Division ID:"] [QLineEdit]                     | | |
| | | +--------------------------------------------------------------------------------------+   | |
| | | +--------------------------------------------------------------------------------------+   | |
| | | | Default/Others: QLabel: "No format-specific options"                                  | | |
| | | +--------------------------------------------------------------------------------------+   | |
| | |                                                                                            | |
| | | [ ] Apply EDI Tweaks                                                                     | |
| | +--------------------------------------------------------------------------------------------+ |
| +------------------------------------------------------------------------------------------------+
|                                                                                                  |
| QDialogButtonBox                                                                                 |
| +-------------------------------------------------------------------------------------------+     |
| | [ Cancel ]                                                                             [ OK ]|     |
| +-------------------------------------------------------------------------------------------+     |
+--------------------------------------------------------------------------------------------------+
```

---

## EditSettingsDialog

**File:** `interface/ui/dialogs/edit_settings_dialog.py`

```
+==================================================================================+
| EditSettingsDialog (QDialog)                                                      |
| Window Title: "Edit Settings" | Modal: True | Size: 600x400                     |
+==================================================================================+
| QVBoxLayout                                                                      |
+----------------------------------------------------------------------------------+
| QTabWidget                                                                       |
| +------------------------------------------------------------------------------+ |
| | [ AS400 Connection ] [ Email Settings ] [ Backup Settings ] [ Reporting ]   | |
| +------------------------------------------------------------------------------+ |
| |                                                                              | |
| | TAB 1: AS400 Connection                                                     | |
| | +----------------------------------------------------------------------+    | |
| | | QGridLayout                                                           |    | |
| | | Row 0: [Label: "ODBC Driver:"] [QComboBox: available_drivers]        |    | |
| | | Row 1: [Label: "AS400 Address:"] [QLineEdit: as400_address]         |    | |
| | | Row 2: [Label: "AS400 Username:"] [QLineEdit: as400_username]       |    | |
| | | Row 3: [Label: "AS400 Password:"] [QLineEdit: (EchoMode=Password)]  |    | |
| | +----------------------------------------------------------------------+    | |
| |                                                                              | |
| | TAB 2: Email Settings                                                        | |
| | +----------------------------------------------------------------------+    | |
| | | QGridLayout                                                           |    | |
| | | Row 0: [QCheckBox: "Enable Email"] (spans 2 cols)                    |    | |
| | | Row 1: [Label: "Email Address:"] [QLineEdit: (validator=EMAIL)]     |    | |
| | | Row 2: [Label: "Email Username:"] [QLineEdit: email_username]       |    | |
| | | Row 3: [Label: "Email Password:"] [QLineEdit: (EchoMode=Password)]  |    | |
| | | Row 4: [Label: "SMTP Server:"] [QLineEdit: smtp_server]             |    | |
| | | Row 5: [Label: "SMTP Port:"] [QSpinBox: (1-65535, default=25)]      |    | |
| | +----------------------------------------------------------------------+    | |
| |                                                                              | |
| | TAB 3: Backup Settings                                                       | |
| | +----------------------------------------------------------------------+    | |
| | | QGridLayout                                                           |    | |
| | | Row 0: [QCheckBox: "Enable Interval Backup"] (spans 2 cols)          |    | |
| | | Row 1: [Label: "Backup Interval:"] [QSpinBox: (1-5000, default=100)]|    | |
| | | Row 2: [Label: "Logs Directory:"] [QLineEdit: logs_directory]        |    | |
| | | Row 3:                        [QPushButton: "Select..."]             |    | |
| | +----------------------------------------------------------------------+    | |
| |                                                                              | |
| | TAB 4: Reporting Options                                                     | |
| | +----------------------------------------------------------------------+    | |
| | | QGridLayout                                                           |    | |
| | | Row 0: [QCheckBox: "Enable Report Sending"] (spans 2 cols)           |    | |
| | | Row 1: [QCheckBox: "Report EDI Validator Warnings"] (spans 2 cols)  |    | |
| | | Row 2: [Label: "Report Email:"] [QLineEdit: (validator=EMAIL)]       |    | |
| | | Row 3: [QCheckBox: "Enable Report Printing Fallback"] (spans 2 cols)|    | |
| | +----------------------------------------------------------------------+    | |
| |                                                                              | |
| +------------------------------------------------------------------------------+ |
|                                                                                  |
| QDialogButtonBox                                                               |
| +--------------------------------------------------------------------------+    |
| | [ Cancel ]                                                          [ OK ] |    |
| +--------------------------------------------------------------------------+    |
+----------------------------------------------------------------------------------+
```

---

## MaintenanceDialog

**File:** `interface/ui/dialogs/maintenance_dialog.py`

```
+==================================================================================+
| MaintenanceDialog (QDialog)                                                     |
| Window Title: "Maintenance Functions" | Modal: True | Size: 400x500            |
+==================================================================================+
| QVBoxLayout                                                                      |
+----------------------------------------------------------------------------------+
| QLabel: "WARNING:\nFOR\nADVANCED\nUSERS\nONLY!"                                |
| Style: color: red; font-weight: bold; | AlignCenter                             |
+----------------------------------------------------------------------------------+
| QWidget (Button Frame)                                                          |
| +----------------------------------------------------------------------+        |
| | QVBoxLayout                                                          |        |
| | +--------------------------------------------------------------------+ |        |
| | | [QPushButton: "Move all to active (Skips Settings Validation)"]   | |        |
| | +--------------------------------------------------------------------+ |        |
| | +--------------------------------------------------------------------+ |        |
| | | [QPushButton: "Move all to inactive"]                              | |        |
| | +--------------------------------------------------------------------+ |        |
| | +--------------------------------------------------------------------+ |        |
| | | [QPushButton: "Clear all resend flags"]                            | |        |
| | +--------------------------------------------------------------------+ |        |
| | +--------------------------------------------------------------------+ |        |
| | | [QPushButton: "Clear queued emails"]                               | |        |
| | +--------------------------------------------------------------------+ |        |
| | +--------------------------------------------------------------------+ |        |
| | | [QPushButton: "Mark all in active as processed"]                   | |        |
| | +--------------------------------------------------------------------+ |        |
| | +--------------------------------------------------------------------+ |        |
| | | [QPushButton: "Remove all inactive configurations"]                | |        |
| | +--------------------------------------------------------------------+ |        |
| | +--------------------------------------------------------------------+ |        |
| | | [QPushButton: "Clear sent file records"]                           | |        |
| | +--------------------------------------------------------------------+ |        |
| | +--------------------------------------------------------------------+ |        |
| | | [QPushButton: "Import old configurations..."]                       | |        |
| | +--------------------------------------------------------------------+ |        |
| | --------------------------------------------------------------------  |        |
| | | QFrame (HLine, Sunken)                                             | |        |
| | --------------------------------------------------------------------  |        |
| | +--------------------------------------------------------------------+ |        |
| | | [QPushButton: "Close"]                                             | |        |
| | +--------------------------------------------------------------------+ |        |
| +----------------------------------------------------------------------+        |
+----------------------------------------------------------------------------------+
```

---

## ProcessedFilesDialog

**File:** `interface/ui/dialogs/processed_files_dialog.py`

```
+==================================================================================+
| ProcessedFilesDialog (QDialog)                                                  |
| Window Title: "Processed Files Report" | Modal: True | Size: 500x400            |
+==================================================================================+
| QHBoxLayout                                                                      |
+----------------------------------------------------------------------------------+
| QGroupBox: "Select a Folder" (stretch=1)                                        |
| +----------------------------------------------------------------------+        |
| | QVBoxLayout                                                          |        |
| | +--------------------------------------------------------------------+ |        |
| | | QListWidget (folder_list)                                          | |        |
| | | - Shows folders with processed files                               | |        |
| | | - Each item has UserRole data with folder_id                       | |        |
| | | - Items sorted alphabetically by alias                             | |        |
| | | - Special item if no processed files: "No Folders With..."        | |        |
| | +--------------------------------------------------------------------+ |        |
| +----------------------------------------------------------------------+        |
|                                                                                  |
| QGroupBox: "Actions" (stretch=1)                                                |
| +----------------------------------------------------------------------+        |
| | QVBoxLayout                                                          |        |
| | +--------------------------------------------------------------------+ |        |
| | | [QPushButton: "Export Processed Report"] (enabled=False initially) | |        |
| | +--------------------------------------------------------------------+ |        |
| | +--------------------------------------------------------------------+ |        |
| | | QLabel: "Loading..." (hidden after load)                            | |        |
| | +--------------------------------------------------------------------+ |        |
| +----------------------------------------------------------------------+        |
+----------------------------------------------------------------------------------+
```

---

## Summary

| Component | Type | Layout | Key Features |
|-----------|------|--------|--------------|
| MainWindow | QMainWindow | HBox: Sidebar + Content + Splitter | Left sidebar for buttons, right for folder list |
| ButtonPanel | QWidget | VBox | 8 buttons with separators |
| FolderListWidget | QWidget | VBox + Splitter | Split view: Inactive (left) / Active (right) folders |
| BaseDialog | QDialog | VBox | Base pattern for all dialogs |
| EditFolderDialog | QDialog | VBox + Tabs | 6+ tabs: General, Backends, EDI, Conversion |
| EditSettingsDialog | QDialog | VBox + Tabs | 4 tabs: AS400, Email, Backup, Reporting |
| MaintenanceDialog | QDialog | VBox | 9 action buttons for maintenance tasks |
| ProcessedFilesDialog | QDialog | HBox | Left: folder list, Right: export actions |
