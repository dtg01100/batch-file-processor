"""
UI Package for interface.py refactoring.

This package contains modular UI components:
- main_window: Main application window
- widgets: Reusable UI widgets (button_panel, folder_list)
- dialogs: Modal dialogs (edit_folder, edit_settings, maintenance, processed_files)
- base_dialog: Base dialog class
"""

from interface.ui.main_window import create_main_window
from interface.ui.widgets import ButtonPanel, FolderListWidget

__all__ = [
    "create_main_window",
    "ButtonPanel",
    "FolderListWidget",
]
