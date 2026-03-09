#!/usr/bin/env python3
"""Debug script to find where the hang occurs."""

import sys

print("Starting debug script", flush=True)
print("Step 1: Basic import", flush=True)

try:
    print("Step 2: Importing PyQt6", flush=True)
    from PyQt6.QtWidgets import QApplication
    print("Step 3: PyQt6 imported successfully", flush=True)
    
    print("Step 4: Creating application", flush=True)
    app = QApplication([])
    print("Step 5: Application created", flush=True)
    
    print("Step 6: Importing unittest.mock", flush=True)
    from unittest.mock import patch, MagicMock
    print("Step 7: unittest.mock imported", flush=True)
    
    print("Step 8: Setting up patch context", flush=True)
    with patch('interface.qt.dialogs.edit_folders_dialog.PluginManager') as mock_pm:
        print("Step 9: Inside patch context", flush=True)
        mock_manager = MagicMock()
        mock_manager.get_configuration_plugins.return_value = []
        mock_pm.return_value = mock_manager
        print("Step 10: Mock setup complete", flush=True)
        
        print("Step 11: Importing EditFoldersDialog", flush=True)
        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog
        print("Step 12: EditFoldersDialog imported", flush=True)
        
        print("Step 13: Creating dialog", flush=True)
        dialog = EditFoldersDialog(None, {})
        print("Step 14: Dialog created successfully!", flush=True)
    
    print("SUCCESS: All steps completed!", flush=True)
    
except Exception as e:
    print(f"ERROR: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)
