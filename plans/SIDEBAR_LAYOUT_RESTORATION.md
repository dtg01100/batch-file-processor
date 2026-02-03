# Left Sidebar Layout Restoration Plan

## Overview

Restore the intended left sidebar layout from git master in the current PyQt6 implementation.

## Current State

The current PyQt6 implementation has:
- ButtonPanel with horizontal layout at top
- Buttons: Add Folder, Batch Add, Process, Processed Files, Maintenance, Settings, Exit

The intended design (from git master Tkinter) has:
- Left sidebar with vertical buttons
- Buttons: Add Folder, Batch Add, Set Defaults, Process, Processed Files, Maintenance, Settings, Enable Resend

## Key Differences

| Current | Intended |
|---------|----------|
| Horizontal top bar | Vertical left sidebar |
| 7 buttons | 9 buttons |
| Exit button | No Exit button |
| No Set Defaults | Has Set Defaults |
| No Enable Resend | Has Enable Resend |

## Files to Modify

### 1. ButtonPanel (`interface/ui/widgets/button_panel.py`)

**Changes needed:**
- Add `_set_defaults_btn` button
- Add `_enable_resend_btn` button
- Remove `_exit_btn` button
- Change QHBoxLayout to QVBoxLayout
- Add signals: `set_defaults_clicked`, `enable_resend_clicked`
- Update `set_button_enabled` method with new button map

### 2. MainWindow (`interface/ui/main_window.py`)

**Changes needed:**
- Change main layout from QVBoxLayout to QHBoxLayout
- Create left sidebar frame containing ButtonPanel
- Create right content area containing FolderListWidget
- Re-emit new signals: `set_defaults_requested`, `enable_resend_requested`

### 3. ApplicationController (`interface/application_controller.py`)

**Changes needed:**
- Add `_handle_set_defaults` method
- Add `_handle_enable_resend` method
- Connect new signals from MainWindow

### 4. Tests

**Files to update:**
- `tests/ui/test_widgets.py`
- `tests/ui/test_interface_ui.py`
- `tests/ui/test_application_controller.py`

## Implementation Steps

1. **Create Sidebar Frame in MainWindow**
   - Add QFrame with QVBoxLayout for left sidebar
   - Move ButtonPanel into sidebar frame
   - Add right frame for FolderListWidget

2. **Restructure ButtonPanel**
   - Change layout to vertical
   - Add Set Defaults and Enable Resend buttons
   - Remove Exit button
   - Add new signals

3. **Update Signal Connections**
   - MainWindow re-emits new signals
   - ApplicationController connects to new signals

4. **Add Handler Methods**
   - `_handle_set_defaults`: Implement Set Defaults functionality
   - `_handle_enable_resend`: Toggle resend mode for processed files

5. **Update Tests**
   - Update layout assertions
   - Add tests for new signals and handlers

## Button Functionality

### Set Defaults
- Opens dialog to set default folder paths
- Saves to `oversight_and_defaults` table
- Provides sensible defaults for new folder configurations

### Enable Resend
- Toggles resend mode for processed files
- Sets `resend_flag = 1` on selected processed files
- Allows files to be reprocessed and resent
- Call `ResendFlagManager.mark_for_resend()` method

## Layout Structure

```
MainWindow
├── QHBoxLayout (main)
├── QFrame (left sidebar)
│   └── QVBoxLayout
│       └── ButtonPanel
│           ├── Add Folder
│           ├── Batch Add
│           ├── Set Defaults
│           ├── Process
│           ├── Processed Files
│           ├── Maintenance
│           ├── Settings
│           └── Enable Resend
└── QFrame (right content)
    └── FolderListWidget
```

## Testing Requirements

1. Smoke tests pass
2. UI tests for layout changes
3. Signal propagation tests
4. New button functionality tests

## Risk Assessment

- **Low Risk**: Layout changes are visual only
- **Medium Risk**: New functionality requires proper implementation
- **Low Risk**: No database schema changes required

## Estimated Files Changed

- 4 source files modified
- 3 test files updated
- 2 documentation files updated
