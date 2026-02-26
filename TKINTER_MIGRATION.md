# Migration from Tkinter to Qt

**Date:** February 26, 2026

## Overview

This project has completed a hard migration from **Tkinter** to **Qt (PyQt5)** for its graphical user interface. All legacy Tkinter code has been removed.

## Removed Files

### Deprecated Modules (4 files deleted)

| File | Description |
|------|-------------|
| `doingstuffoverlay.py` | Tkinter loading overlay component |
| `dialog.py` | Tkinter dialog base class |
| `database_import.py` | Tkinter database import UI |
| `resend_interface.py` | Tkinter resend dialog |

### Legacy Test Files (2 files deleted)

| File | Description |
|------|-------------|
| `tests/ui/test_edit_folders_dialog.py` | Tkinter-based dialog tests |
| `tests/ui/test_processed_files_dialog.py` | Tkinter-based dialog tests |

## New Qt-Based Architecture

The application now uses Qt exclusively:

### UI Layer
- `interface/qt/` - Qt-based UI components
- `interface/plugins/ui_abstraction.py` - Widget factory system supporting Qt

### Qt Tests
- `tests/qt/` - All UI tests are now Qt-based:
  - `test_qt_app.py`
  - `test_qt_dialogs.py`
  - `test_qt_widgets.py`
  - `test_qt_services.py`
  - `test_edit_folders_dialog.py` (Qt version)

### Backend Services
- `interface/services/` - Business logic services (framework-agnostic)

## Benefits of Qt Over Tkinter

1. **Professional UI** - Native look and feel on all platforms
2. **Rich Widgets** - Advanced widgets (tables, trees, menus)
3. **Better Layout** - Modern layout system (layouts, splitters, docks)
4. **Event Handling** - Robust signal/slot mechanism
5. **Accessibility** - Better screen reader support
6. **Active Development** - Qt is actively maintained

## Running the Application

The Qt-based application can be started with:

```bash
python main_qt.py
```

Or via the module:

```bash
python -m interface.qt.main
```

## Tests

Run Qt-based tests:

```bash
pytest tests/qt/ -v
```

## Notes

- The `tests/ui/` directory has been deprecated in favor of `tests/qt/`
- All new UI development should use Qt (PyQt5)
- The widget factory in `interface/plugins/ui_abstraction.py` supports easy swapping of UI frameworks if needed in the future
