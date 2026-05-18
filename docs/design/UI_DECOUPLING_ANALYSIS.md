# UI-Business Logic Decoupling Analysis

**Version:** 1.1
**Date:** 2026-05-18
**Status:** ARCHIVAL — Refactoring Complete
**Purpose:** Historical record of Tkinter→PyQt5 decoupling analysis. Current architecture is documented in `DESIGN_CORRECTIONS.md` §10.

---

> **⚠️ This document describes the Tkinter-era codebase that has since been
> refactored to PyQt5.** All coupling points listed here have been resolved.
> The current architecture uses a **three-layer signal pattern** documented
> in `interface/AGENTS.md` and `interface/qt/run_coordinator.py`.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current Architecture Overview](#2-current-architecture-overview)
3. [Coupling Points Inventory — Historical](#3-coupling-points-inventory--historical)
4. [Already Decoupled Areas — Historical](#4-already-decoupled-areas--historical)
5. [Severity Assessment — Historical](#5-severity-assessment--historical)
6. [Recommended Decoupling Strategy — Historical](#6-recommended-decoupling-strategy--historical)
7. [Risk Assessment — Historical](#7-risk-assessment--historical)
8. [Current State: PyQt5 Architecture](#8-current-state-pyqt5-architecture)

---

## 1. Executive Summary

**Original problem (pre-v1.1 refactor):** The Batch File Processor used Tkinter for
its UI, creating tight coupling between business logic and the UI toolkit.

**Current state:** The codebase was **fully refactored to PyQt5** (v1.1, 2026-05-18).
All coupling points identified in this document have been resolved. The UI now
follows a strict **three-layer signal pattern** with no business logic in widgets.

### Key Metrics — Before (Historical)

| Metric | Count |
|--------|-------|
| Files with Tkinter imports | ~15 |
| Tkinter variable instances (`StringVar`/`BooleanVar`/`IntVar`) | ~45 |
| Direct `tkinter.messagebox` calls from business logic | ~12 |
| Database operations inside UI classes | ~20 |
| Network operations inside UI validation | 2 (SMTP, FTP) |

---

## 2. Current Architecture Overview

### 2.1 Layer Diagram — PyQt5 (Current)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    INTERFACE LAYER (PyQt5 — Clean)                    │
│                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ qt/app.py    │  │ Dialogs      │  │ Widgets                   │  │
│  │ QtBatchFile  │  │ qt/dialogs/  │  │ qt/widgets/              │  │
│  │ SenderApp    │  │              │  │ folder_list_widget.py    │  │
│  │              │  │              │  │ search_widget.py         │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
│                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ Ports/       │  │ Operations   │  │ Models                   │  │
│  │ interfaces.py│  │ operations/  │  │ models/                 │  │
│  │ MessageBox   │  │ folder_ops   │  │ folder_configuration.py  │  │
│  │ FileDialog  │  │ processing   │  │                          │  │
│  │ Widget      │  │ maintenance  │  │                          │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│                    DISPATCH LAYER (Clean — no UI deps)                │
│         Orchestrator, Pipeline, Validators, SendManager, ErrorHandler │
├─────────────────────────────────────────────────────────────────────┤
│                    BACKEND LAYER (Clean — no UI deps)                  │
│        FTP, SMTP, File Copy, HTTP — protocol-based                    │
├─────────────────────────────────────────────────────────────────────┤
│                    CORE LAYER (Clean — no UI deps)                     │
│          Database, EDI Processing, Utilities, Structured Logging     │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Three-Layer Signal Pattern (Current — replaces Tkinter event binding)

The current UI uses a strict three-layer signal/slot pattern documented in
`interface/AGENTS.md`:

```
Layer 1 — Widget level (ButtonPanel, FolderListWidget)
  → emits Qt signals (folder_edit_requested, send_clicked, etc.)
       │
       ▼
Layer 2 — Window level (MainWindow via window_controller.py)
  → re-emits widget signals via .connect(signal.emit)
       │
       ▼
Layer 3 — Controller level
  → ApplicationController (or run_coordinator.py)
  → calls operations layer (folder_operations, processing, maintenance)
  → operations use DatabaseObj for database access
```

### 2.3 Key Entry Points

| File | Purpose |
|------|---------|
| `interface/qt/app.py` | `QtBatchFileSenderApp` — top-level QWidget, main window factory |
| `interface/qt/window_controller.py` | Window construction and UI state helpers |
| `interface/qt/dialogs/edit_folders_dialog.py` | Per-folder settings dialog |
| `interface/qt/dialogs/edit_settings_dialog.py` | Global settings dialog |
| `interface/qt/run_coordinator.py` | Processing run coordination with progress |
| `interface/qt/dialogs/maintenance_dialog.py` | Maintenance operations dialog |
| `interface/qt/dialogs/processed_files_dialog.py` | Processed files report dialog |
| `interface/qt/dialogs/resend_dialog.py` | Resend failed files dialog |
| `interface/qt/widgets/folder_list_widget.py` | Scrolled folder list with per-row action buttons |
| `interface/qt/widgets/search_widget.py` | Folder list filter/search widget |

---

## 3. Coupling Points Inventory — Historical

All items below are **resolved** as of the v1.1 PyQt5 refactor.

| # | Coupling Point | Resolution |
|---|---------------|------------|
| C1 | Tkinter `StringVar`/`BooleanVar`/`IntVar` as business state | **Resolved** — PyQt5 uses `QCheckBox.isChecked()`, `QLineEdit.text()`, Qt signals/slots |
| C2 | `_process_directories()` mixed concerns in `interface/app.py` | **Resolved** — Processing moved to `run_coordinator.py`; UI does not call dispatch directly |
| C3 | `_dispatch_legacy.process()` accepting Tkinter root | **Resolved** — `_dispatch_legacy.py` was removed during refactor |
| C4 | `doingstuffoverlay` global Tkinter module | **Resolved** — Replaced by `interface/qt/run_coordinator.py` with proper progress reporting |
| C5 | `dialog.py` base class inheriting from `tkinter.Toplevel` | **Resolved** — PyQt5 dialogs inherit from `QDialog` via `qt/dialogs/base_dialog.py` |
| C6 | SMTP test in `EditSettingsDialog.validate()` | **Resolved** — Email validation uses `interface/services/ftp_service.py`-patterned service |
| C7 | `mark_active_as_processed()` in maintenance dialog | **Resolved** — Business logic extracted to `interface/operations/maintenance.py` |
| C8 | `resend_interface.py` monolithic module | **Resolved** — Refactored to `qt/dialogs/resend_dialog.py` |
| C9 | `database_import.py` Tkinter + DB migration | **Resolved** — Refactored to `qt/dialogs/database_import_dialog.py` |
| C10 | Direct `messagebox` calls | **Resolved** — Dialogs use `QMessageBox` from PyQt5 |
| C11 | Direct `askdirectory` calls | **Resolved** — Dialogs use `QFileDialog` from PyQt5 |
| C12 | `interface/ui/` path references | **Resolved** — All UI code now at `interface/qt/` |
| C13 | `interface/database/database_obj.py` path | **Resolved** — Moved to `backend/database/database_obj.py` |
| C14 | `EditFoldersDialog` with `interface.ui.dialogs.*` path | **Resolved** — Now at `interface.qt.dialogs.edit_folders_dialog` |
| C15 | `ApplicationController` class | **Resolved** — Signal routing now handled via `window_controller.py` and direct signal connections |
| C16 | `FolderListWidget` referencing `folder_list_widget.py` path | **Resolved** — Now at `interface/qt/widgets/folder_list_widget.py` |

---

## 4. Already Decoupled Areas — Historical

| Component | Current Location | Description |
|-----------|-----------------|-------------|
| **Backend Layer** | `backend/` | FTP, SMTP, File Copy, HTTP — all protocol-based |
| **Dispatch Layer** | `dispatch/` | Orchestrator, Pipeline, Validators — protocol-based |
| **Core Layer** | `core/` | Database, EDI parsing — no UI dependencies |
| **FolderConfiguration** | `interface/models/folder_configuration.py` | Pure dataclass model with Pydantic validation |
| **FolderSettingsValidator** | `interface/validation/folder_settings_validator.py` | Pure validation logic |
| **EmailValidator** | `interface/validation/email_validator.py` | Pure regex validation |
| **FTPService** | `interface/services/ftp_service.py` | FTP connection testing via protocol |
| **DatabaseObj** | `backend/database/database_obj.py` | Database access; Table API via `sqlite_wrapper.py` |

---

## 5. Severity Assessment — Historical

All items were resolved in the v1.1 PyQt5 refactor. The table below is retained
for historical reference.

| # | Coupling Point | Severity (Historical) | Current Status |
|---|---------------|----------------------|----------------|
| C1 | Tkinter variables as business state | HIGH | ✅ Resolved |
| C2 | `_process_directories()` mixed concerns | HIGH | ✅ Resolved |
| C3 | `_dispatch_legacy.py` root parameter | HIGH | ✅ Resolved |
| C4 | `doingstuffoverlay` global module | HIGH | ✅ Resolved |
| C5 | `dialog.py` base class | HIGH | ✅ Resolved |
| C6 | SMTP test in validation | HIGH | ✅ Resolved |
| C7 | `mark_active_as_processed()` mixed concerns | HIGH | ✅ Resolved |
| C8 | `resend_interface.py` monolithic | MEDIUM | ✅ Resolved |
| C9 | `database_import.py` monolithic | MEDIUM | ✅ Resolved |
| C10 | Direct `messagebox` calls | MEDIUM | ✅ Resolved |
| C11 | Direct `askdirectory` calls | MEDIUM | ✅ Resolved |
| C12 | `_select_folder()` mixed concerns | MEDIUM | ✅ Resolved |
| C13 | `_batch_add_folders()` mixed concerns | MEDIUM | ✅ Resolved |
| C14 | `ReportingService` root/feedback params | MEDIUM | ✅ Resolved |
| C15 | `EditFoldersDialog` fallback DB access | MEDIUM | ✅ Resolved |
| C16 | `processed_files_dialog.py` mixed concerns | MEDIUM | ✅ Resolved |
| C17 | `tk_extra_widgets.py` custom widgets | LOW | ✅ Resolved (file removed) |
| C18 | `FolderListWidget` Tkinter construction | LOW | ✅ Resolved |
| C19 | `SearchWidget` Tkinter construction | LOW | ✅ Resolved |

---

## 6. Recommended Decoupling Strategy — Historical

All phases were completed in the v1.1 PyQt5 refactor:

- **Phase 1** (Cross-Layer Cleanup): ✅ Completed — `doingstuffoverlay` removed
- **Phase 2** (Abstract Dialog Infrastructure): ✅ Completed — `QDialog` base class
- **Phase 3** (Extract Business Logic from Dialogs): ✅ Completed — operations layer
- **Phase 4** (Replace Tkinter Variables): ✅ Completed — Qt signals/slots + `FolderConfiguration`
- **Phase 5** (Refactor Monolithic UI Modules): ✅ Completed — all dialogs refactored
- **Phase 6** (Create UI Abstraction Layer): ✅ Completed — PyQt5 is the toolkit

---

## 7. Risk Assessment — Historical

| Risk | Resolution |
|------|------------|
| Breaking `_dispatch_legacy.py` | File was removed during refactor |
| Breaking dialog validation | Tests in `tests/unit/interface/` ensure correctness |
| State synchronization bugs | PyQt5 signals provide deterministic binding |
| Overlay timing issues | `run_coordinator.py` manages progress with proper async pattern |

---

## 8. Current State: PyQt5 Architecture

### 8.1 Signal Flow (Authoritative)

```
User clicks action in widget (ButtonPanel / FolderListWidget)
       │  Qt signal emitted  │
       ▼
QtMainWindow / window_controller.py
       │  re-emits via .connect(signal.emit)  │
       ▼
Operations layer:
  - folder_operations.py (CRUD for folders)
  - processing.py (backup, dispatch, email reports)
  - maintenance.py (clear_processed, mark_processed)
       │  uses  │
       ▼
DatabaseObj (backend/database/database_obj.py)
       │  attribute access  │
       ▼
Table API (backend/database/sqlite_wrapper.py)
```

### 8.2 Key Files

| File | Role |
|------|------|
| `interface/qt/app.py` | `QtBatchFileSenderApp` — top-level app widget |
| `interface/qt/window_controller.py` | Window construction helpers, layout |
| `interface/qt/run_coordinator.py` | Progress dialog + async processing coordination |
| `interface/qt/dialogs/` | All modal dialogs (EditFolders, EditSettings, Maintenance, Resend, ProcessedFiles, DatabaseImport) |
| `interface/qt/widgets/folder_list_widget.py` | Folder list + row action buttons |
| `interface/qt/widgets/search_widget.py` | Filter/search widget |
| `interface/operations/folder_operations.py` | Folder CRUD operations |
| `interface/operations/processing.py` | Backup → dispatch → email reports pipeline |
| `interface/operations/maintenance.py` | Maintenance operations |
| `interface/models/folder_configuration.py` | Dataclass-based configuration model |
| `backend/database/database_obj.py` | DatabaseObj + Table API (replaces dataset shim) |
| `dispatch/orchestrator.py` | DispatchOrchestrator — file processing coordinator |
| `dispatch/send_manager.py` | SendManager — backend delivery (copy, ftp, email, http) |

### 8.3 What Was Removed

The following Tkinter-era files/modules were identified as coupling points and
**do not exist** in the current codebase:

| File (Historical) | Issue | Current Replacement |
|------------------|-------|--------------------|
| `interface/ui/` directory | Tkinter-era path | `interface/qt/` |
| `interface/ui/dialogs/` | Tkinter dialogs | `interface/qt/dialogs/` |
| `interface/app.py` | Monolithic Tkinter app | `interface/qt/app.py` |
| `interface/ui/widgets/` | Tkinter widgets | `interface/qt/widgets/` |
| `_dispatch_legacy.py` | Accepts Tkinter root param | Removed |
| `doingstuffoverlay.py` | Global Tkinter state | `interface/qt/run_coordinator.py` |
| `dialog.py` | `Toplevel` base class | `interface/qt/dialogs/base_dialog.py` (`QDialog`) |
| `tk_extra_widgets.py` | Custom Tkinter widgets | PyQt5 equivalents |
| `resend_interface.py` | Monolithic Tkinter+DB | `interface/qt/dialogs/resend_dialog.py` |
| `database_import.py` | Tkinter + DB migration | `interface/qt/dialogs/database_import_dialog.py` |
| `interface/database/database_obj.py` | Old path | `backend/database/database_obj.py` |
| `dispatch/interfaces.py` | Non-existent module | `dispatch/pipeline/interfaces.py` |
| `backend_base.py` (root) | Non-existent file | `backend/backend_base.py` |
| `results.py` (dispatch/) | Non-existent module | `dispatch/orchestrator.py` (`FileResult` NamedTuple) |

### 8.4 Related Documents

| Document | Purpose |
|----------|---------|
| `DESIGN_CORRECTIONS.md` | Master list of all doc-vs-code discrepancies and fixes |
| `SYSTEM_ARCHITECTURE.md` | PyQt5 stack, entry points, file paths |
| `PROCESSING_PIPELINE.md` | Validator → Splitter → Converter pipeline |
| `DATA_FLOW.md` / `DATA_FLOW_DESIGN.md` | Data flow diagrams (current: validator→splitter→converter) |
| `BACKEND_ARCHITECTURE.md` | SendManager + DEFAULT_BACKENDS (copy→ftp→email→http) |
| `interface/AGENTS.md` | Interface module conventions and signal pattern |
| `dispatch/AGENTS.md` | Dispatch module structure and orchestration flow |