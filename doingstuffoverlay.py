"""Loading overlay for Tkinter applications.

Provides both a class-based API (DoingStuffOverlay) for new code
and backward-compatible module-level functions for existing callers.
"""
import tkinter
import tkinter.ttk


class DoingStuffOverlay:
    """Encapsulated loading overlay widget.

    Each instance manages its own overlay frame independently,
    allowing multiple overlays to coexist without global state conflicts.
    """

    def __init__(self):
        self.doing_stuff_frame = None
        self._doing_stuff_label = None
        self._header_label = None
        self._footer_label = None
        self._label_var = None
        self._header_var = None
        self._footer_var = None

    def make_overlay(self, parent, overlay_text, header="", footer="", overlay_height=100):
        """Create and show the overlay on the parent widget."""
        if self.doing_stuff_frame is not None:
            try:
                self.doing_stuff_frame.grab_release()
            except tkinter.TclError:
                pass
            self.doing_stuff_frame.destroy()

        self._label_var = tkinter.StringVar()
        self._label_var.set(overlay_text)
        self._header_var = tkinter.StringVar()
        self._header_var.set(header)
        self._footer_var = tkinter.StringVar()
        self._footer_var.set(footer)

        self.doing_stuff_frame = tkinter.ttk.Frame(parent, relief=tkinter.RIDGE)
        self.doing_stuff_frame.grab_set()
        self._doing_stuff_label = tkinter.ttk.Label(self.doing_stuff_frame, text=self._label_var.get())
        self._doing_stuff_label.place(relx=.5, rely=.5, anchor=tkinter.CENTER)
        self._header_label = tkinter.ttk.Label(self.doing_stuff_frame, text=self._header_var.get())
        self._header_label.place(relx=.05, rely=.15, anchor=tkinter.W)
        self._footer_label = tkinter.ttk.Label(self.doing_stuff_frame, text=self._footer_var.get())
        self._footer_label.place(relx=.05, rely=.85, anchor=tkinter.W)
        self.doing_stuff_frame.place(relx=.5, rely=.5, height=overlay_height, relwidth=1, anchor=tkinter.CENTER)
        parent.update()

    def update_overlay(self, parent, overlay_text, header="", footer="", overlay_height=None):
        """Update the overlay text."""
        if (
            self._doing_stuff_label is None
            or self.doing_stuff_frame is None
            or self._header_label is None
            or self._footer_label is None
        ):
            return
        self._doing_stuff_label.configure(text=overlay_text)
        self._header_label.configure(text=header)
        self._footer_label.configure(text=footer)
        if overlay_height is not None and overlay_height != self.doing_stuff_frame.winfo_height():
            self.doing_stuff_frame.place(height=overlay_height)
        parent.update()

    def destroy_overlay(self):
        """Destroy the overlay."""
        if self.doing_stuff_frame is not None:
            try:
                self.doing_stuff_frame.grab_release()
            except tkinter.TclError:
                pass
            self.doing_stuff_frame.destroy()
            self.doing_stuff_frame = None


# -------------------------------------------------------------------------
# Module-level singleton + backward-compatible functions
# -------------------------------------------------------------------------

_default_overlay = DoingStuffOverlay()

# Expose the frame reference for backward compatibility (read-only access pattern)
# Code that checks `doingstuffoverlay.doing_stuff_frame is not None` still works
doing_stuff_frame = None


def make_overlay(parent, overlay_text, header="", footer="", overlay_height=100):
    """Backward-compatible module-level make_overlay."""
    global doing_stuff_frame
    _default_overlay.make_overlay(parent, overlay_text, header, footer, overlay_height)
    doing_stuff_frame = _default_overlay.doing_stuff_frame


def update_overlay(parent, overlay_text, header="", footer="", overlay_height=None):
    """Backward-compatible module-level update_overlay."""
    _default_overlay.update_overlay(parent, overlay_text, header, footer, overlay_height)


def destroy_overlay():
    """Backward-compatible module-level destroy_overlay."""
    global doing_stuff_frame
    _default_overlay.destroy_overlay()
    doing_stuff_frame = None
