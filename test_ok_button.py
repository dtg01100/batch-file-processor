#!/usr/bin/env python3
"""Minimal test to identify the exact crash location when clicking OK."""

from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication

# Mock the plugin manager before importing dialog
with patch('interface.qt.dialogs.edit_folders_dialog.PluginManager') as mock_pm_class:
    mock_manager = MagicMock()
    mock_manager.get_configuration_plugins.return_value = []
    mock_pm_class.return_value = mock_manager

    from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog

app = QApplication([])

print("=" * 60)
print("TEST: EditFoldersDialog OK Button Crash")
print("=" * 60)

try:
    print("\n1. Creating dialog...")
    dialog = EditFoldersDialog(
        None,
        {"folder_name": "/test/folder"},
        ftp_service=MagicMock(),
        validator=MagicMock(),
    )
    print("   ✓ Dialog created successfully")

    print("\n2. Getting active checkbox...")
    active_btn = dialog._fields.get("active_checkbutton")
    print(f"   ✓ active_checkbutton: {type(active_btn).__name__}")

    print("\n3. Disabling folder...")
    active_btn.setChecked(False)
    print("   ✓ Folder disabled")

    print("\n4. Calling validate()...")
    result = dialog.validate()
    print(f"   ✓ validate() returned: {result}")

    print("\n5. Calling apply()...")
    dialog.apply()
    print("   ✓ apply() completed successfully")

    print("\n6. Mocking accept() to prevent dialog close...")
    dialog.accept = MagicMock()

    print("\n7. Calling _on_ok()...")
    dialog._on_ok()
    print("   ✓ _on_ok() completed successfully")

    print("\n" + "=" * 60)
    print("SUCCESS: All OK button operations completed without crash!")
    print("=" * 60)

except AttributeError as e:
    print(f"\n❌ AttributeError: {e}")
    import traceback
    traceback.print_exc()

except Exception as e:
    print(f"\n❌ Exception: {e}")
    import traceback
    traceback.print_exc()
