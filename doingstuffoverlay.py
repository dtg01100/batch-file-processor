"""
Legacy overlay module - now a no-op stub.

This module previously provided tkinter progress overlays.
Since the application has migrated to PyQt6, this is now a stub
that does nothing, allowing legacy code that imports it to continue working.
"""


class DoingStuffOverlay:
    """Legacy class - no-op stub."""

    def __init__(self, parent):
        self.parent = parent


def make_overlay(parent, overlay_text, header="", footer="", overlay_height=100):
    """No-op: Previously created a tkinter progress overlay."""
    pass


def update_overlay(parent, overlay_text, header="", footer="", overlay_height=None):
    """No-op: Previously updated a tkinter progress overlay."""
    pass


def destroy_overlay():
    """No-op: Previously destroyed a tkinter progress overlay."""
    pass
