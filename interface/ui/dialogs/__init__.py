"""UI dialogs package for interface.py refactoring.

This package contains refactored dialog classes extracted from interface.py:
- EditFolderDialog: Tabbed dialog for editing folder configuration
- EditSettingsDialog: Tabbed dialog for editing global settings
- MaintenanceDialog: Dialog for maintenance functions
- ProcessedFilesDialog: Dialog for viewing and exporting processed files report
"""

from .edit_folder_dialog import EditFolderDialog
from .edit_settings_dialog import EditSettingsDialog
from .maintenance_dialog import MaintenanceDialog
from .processed_files_dialog import ProcessedFilesDialog

__all__ = [
    'EditFolderDialog',
    'EditSettingsDialog',
    'MaintenanceDialog',
    'ProcessedFilesDialog',
]
