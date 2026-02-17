"""Dialog components for the Batch File Sender application.

This package contains dialog classes extracted from main_interface.py
for better testability and separation of concerns.

Available dialogs:
- EditFoldersDialog: Dialog for editing folder configurations
- EditSettingsDialog: Dialog for editing application settings
- MaintenanceDialog: Dialog for maintenance functions
- ProcessedFilesDialog: Dialog for viewing processed files reports
"""

from interface.ui.dialogs.edit_folders_dialog import EditFoldersDialog
from interface.ui.dialogs.edit_settings_dialog import EditSettingsDialog
from interface.ui.dialogs.maintenance_dialog import (
    MaintenanceFunctions,
    show_maintenance_dialog,
)
from interface.ui.dialogs.processed_files_dialog import (
    export_processed_report,
    show_processed_files_dialog,
)

__all__ = [
    "EditFoldersDialog",
    "EditSettingsDialog",
    "MaintenanceFunctions",
    "show_maintenance_dialog",
    "export_processed_report",
    "show_processed_files_dialog",
]
