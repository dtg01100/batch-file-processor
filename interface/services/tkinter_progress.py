"""Tkinter-specific progress callback implementation."""
from __future__ import annotations
from typing import Optional
from interface.services.progress_service import ProgressCallback


class TkinterProgressCallback:
    """Wraps the existing doingstuffoverlay for Tkinter UI.

    The doingstuffoverlay module provides three functions:
      - make_overlay(parent, overlay_text, header="", footer="", overlay_height=100)
      - update_overlay(parent, overlay_text, header="", footer="", overlay_height=None)
      - destroy_overlay()

    This class maps the ProgressCallback protocol onto those functions.
    """

    def __init__(self, root_window) -> None:
        """
        Args:
            root_window: The Tkinter root window (or any widget).
        """
        self._root = root_window
        self._visible = False
        # Import here to keep Tkinter dependency isolated to this file
        import doingstuffoverlay
        self._overlay = doingstuffoverlay

    def show(self, message: str = "") -> None:
        """Show the progress overlay using make_overlay."""
        self._overlay.make_overlay(self._root, message)
        self._visible = True

    def hide(self) -> None:
        """Destroy the progress overlay."""
        self._overlay.destroy_overlay()
        self._visible = False

    def update_message(self, message: str) -> None:
        """Update the overlay text using update_overlay.

        If the overlay is not currently visible, shows it first.
        """
        if self._visible:
            self._overlay.update_overlay(self._root, message)
        else:
            self.show(message)

    def is_visible(self) -> bool:
        """Return whether the overlay is currently visible."""
        return self._visible
