# Folder Defaults/Template Functionality - Implementation Summary

## Overview
Restored the complete folder defaults/template functionality that was incomplete after the PyQt6 migration.

## Problem
The "Set Defaults" button was removed during PyQt6 migration with the intention of merging its functionality into "Edit Settings." However, only **5 out of 63** template fields were actually added to the Edit Settings dialog, leaving users unable to configure defaults for:
- Backend settings (Copy, FTP, Email)
- EDI processing options
- Conversion format settings  
- File formatting options
- Plugin/conversion-specific settings

## Solution
Added a comprehensive "Folder Defaults" tab to the Edit Settings dialog that exposes all template fields.

## Changes Made

### 1. Edit Settings Dialog (`interface/ui/dialogs/edit_settings_dialog.py`)
- Added new "Folder Defaults" tab (placed first for visibility)
- Created `_build_folder_defaults_tab()` method with scrollable content
- Organized fields into logical groups:
  - **Backend Settings**: Copy destination, FTP server/port/credentials, Email recipient/subject
  - **EDI Processing**: Enable processing, convert format, tweak EDI, UPC check digit, include records
  - **Advanced Options**: Force validation, split EDI, prepend date, rename pattern

- Added `_select_default_copy_destination()` helper for directory selection
- Updated `_validate()` to check that backends have required configuration
- Updated `_apply()` to save all folder default fields to database

### 2. Database Manager (`interface/database/database_manager.py`)
- Added `get_template()` method to reliably get the template from administrative table
- Handles cases where `id` column doesn't exist in administrative table

### 3. Folder Operations (`interface/operations/folder_operations.py`)
- Updated `_get_template_settings()` to use new `get_template()` method
- More robust error handling when template not found

### 4. Updated All Template References
Used AST-grep to update all occurrences of `oversight_and_defaults.find_one(id=1)` to use the new `get_template()` method:
- `interface/application_controller.py` (3 locations)
- `interface/operations/processing.py` (3 locations)
- `interface/ui/dialogs/processed_files_dialog.py` (2 locations)

## Testing
Created and ran comprehensive test script (`test_folder_defaults.py`) that verified:
1. ✅ Template settings can be read from administrative table
2. ✅ New folders inherit all template settings correctly
3. ✅ Only skip-list fields (folder_name, alias, id, etc.) are excluded
4. ✅ Template inheritance works for all 63 configuration fields

## User Impact

**Before:**
- Users could only set 5 template fields (logs directory, reporting options)
- Had to manually configure every new folder with same settings
- No way to set default backends, FTP settings, EDI options, etc.

**After:**
- ✅ Complete template configuration available in "Edit Settings" → "Folder Defaults" tab
- ✅ All 58 missing fields now exposed and editable
- ✅ New folders automatically inherit all configured defaults
- ✅ Validation ensures backends are properly configured before enabling
- ✅ Scrollable interface for easy navigation of all settings

## Architecture
The template system works as follows:
1. **Storage**: Template stored as row in `administrative` table (also called `oversight_and_defaults`)
2. **Retrieval**: `DatabaseManager.get_template()` gets the first/only row from administrative table
3. **Inheritance**: `FolderOperations.add_folder()` copies all template fields except skip-list to new folder
4. **Editing**: "Edit Settings" → "Folder Defaults" tab allows full template customization

## Files Modified
- `interface/ui/dialogs/edit_settings_dialog.py` - Added Folder Defaults tab
- `interface/database/database_manager.py` - Added get_template() method
- `interface/operations/folder_operations.py` - Updated to use get_template()
- `interface/application_controller.py` - Updated template references
- `interface/operations/processing.py` - Updated template references  
- `interface/ui/dialogs/processed_files_dialog.py` - Updated template references

## Validation
- Copy backend requires copy destination
- FTP backend requires FTP server
- Email backend requires valid email recipient
- All validation errors shown to user before saving

## Notes
- The Folder Defaults tab is placed first in the tab order for discoverability
- Fields are organized logically to match the Edit Folder dialog structure
- Scrollable interface accommodates all fields without overwhelming the UI
- Maintains consistency with existing Edit Settings dialog patterns
