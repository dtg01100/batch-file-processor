"""
Legacy dialog module - now a stub.

This module previously provided tkinter-based dialog base classes.
Since the application has migrated to PyQt6, this is now a stub.

TODO: Remove if no longer needed, or implement PyQt6 equivalent.
"""


class Dialog:
    """Legacy tkinter Dialog base class - stub implementation."""

    def __init__(self, parent, foldersnameinput, title=None):
        """Initialize stub dialog."""
        print(
            "Warning: Using legacy Dialog stub - this should be replaced with PyQt6 QDialog"
        )
        self.parent = parent
        self.foldersnameinput = foldersnameinput
        self.result = None

    def body(self, master):
        """Stub body method."""
        pass

    def buttonbox(self):
        """Stub buttonbox method."""
        pass

    def ok(self, event=None):
        """Stub ok method."""
        pass

    def cancel(self, event=None):
        """Stub cancel method."""
        pass

    def validate(self):
        """Stub validate method."""
        return 1

    def apply(self, foldersnameapply):
        """Stub apply method."""
        pass
