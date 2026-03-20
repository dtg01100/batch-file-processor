#!/usr/bin/env python3
"""Integration test: Verify OK button flow works end-to-end."""

if __name__ != "__main__":
    import pytest

    pytest.skip(
        "Manual root-level integration script; skip during pytest collection to avoid side effects.",
        allow_module_level=True,
    )

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Setup paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_ok_button_full_flow():
    """Test the complete OK button flow with database save."""
    from PyQt6.QtWidgets import QApplication

    QApplication([])

    # Mock the plugin manager before importing
    with patch(
        "interface.qt.dialogs.edit_folders_dialog.PluginManager"
    ) as mock_pm_class:
        mock_manager = MagicMock()
        mock_manager.get_configuration_plugins.return_value = []
        mock_pm_class.return_value = mock_manager

        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog

        print("\n" + "=" * 70)
        print("TEST: EditFoldersDialog OK Button Flow (Database Save)")
        print("=" * 70)

        try:
            print("\n1. Creating dialog...")
            dialog = EditFoldersDialog(
                None,
                {
                    "folder_name": "/test/folder",
                    "id": 1,
                    "folder_is_active": False,
                },
                ftp_service=MagicMock(),
                validator=MagicMock(),
            )
            print("   ✓ Dialog created")

            print("\n2. Getting active checkbox...")
            active_btn = dialog._fields.get("active_checkbutton")
            print(f"   ✓ Type: {type(active_btn).__name__}")

            print("\n3. Disabling folder...")
            active_btn.setChecked(False)
            print("   ✓ Set to disabled")

            print("\n4. Calling validate()...")
            is_valid = dialog.validate()
            print(f"   ✓ Validation result: {is_valid}")

            print("\n5. Capturing apply() data...")
            saved_data = {}

            def capture_save(config):
                saved_data.update(config)

            dialog._on_apply_success = capture_save

            print("\n6. Calling apply()...")
            dialog.apply()
            print("   ✓ Apply completed")

            print("\n7. Verifying saved data...")
            assert (
                "plugin_configurations" not in saved_data
            ), "❌ ERROR: plugin_configurations should not be in saved data"
            print("   ✓ plugin_configurations NOT in saved data (correct!)")

            assert (
                "folder_is_active" in saved_data
            ), "❌ ERROR: folder_is_active should be saved"
            print("   ✓ folder_is_active is in saved data")

            print("\n8. Mocking accept() to prevent dialog close...")
            dialog.accept = MagicMock()

            print("\n9. Calling _on_ok()...")
            dialog._on_ok()
            print("   ✓ _on_ok() completed")

            print("\n10. Verifying accept() was called...")
            dialog.accept.assert_called_once()
            print("   ✓ accept() was called")

            print("\n" + "=" * 70)
            print("✅ SUCCESS: All OK button operations completed!")
            print("=" * 70 + "\n")
            return True

        except Exception as e:
            print(f"\n❌ FAILED: {e}")
            import traceback

            traceback.print_exc()
            return False


if __name__ == "__main__":
    success = test_ok_button_full_flow()
    sys.exit(0 if success else 1)
