"""
Legacy database import module - now a stub.

This module previously provided tkinter-based database import functionality.
Since the application has migrated to PyQt6, this is now a stub.

TODO: Reimplement using PyQt6 dialogs if this feature is needed.
"""


def import_interface(
    master_window,
    original_database_path,
    running_platform,
    backup_path,
    current_db_version,
):
    """
    Legacy database import interface - not implemented in PyQt6 version.

    Returns:
        False to indicate the operation was not completed.
    """
    print("ERROR: Database import feature is not yet implemented in PyQt6 version.")
    print("This feature requires migration from tkinter to PyQt6.")
    return False


run_has_happened = False
new_database_path = ""
