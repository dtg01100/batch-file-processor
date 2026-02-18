"""UI abstraction ports for toolkit-agnostic application design.

This module defines the complete set of ports (abstractions) the application
needs from ANY UI toolkit. It provides Protocol definitions for all UI
interactions (message boxes, file dialogs, progress overlays, event loop
pumping) plus a null implementation for headless/testing use and a concrete
Tkinter adapter.

By programming against these protocols, the application logic is fully
decoupled from any specific UI framework.
"""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from interface.services.progress_service import ProgressCallback


@runtime_checkable
class UIServiceProtocol(Protocol):
    """Comprehensive protocol for all non-progress UI interactions.

    This single facade covers message dialogs, file/directory choosers, and
    event-loop integration.  Any UI toolkit adapter must satisfy this protocol
    so the rest of the application never imports toolkit-specific modules.
    """

    # -- informational dialogs ------------------------------------------------

    def show_info(self, title: str, message: str) -> None:
        """Display an informational message to the user.

        Args:
            title: Dialog title.
            message: Body text to display.
        """
        ...

    def show_error(self, title: str, message: str) -> None:
        """Display an error message to the user.

        Args:
            title: Dialog title.
            message: Body text describing the error.
        """
        ...

    def show_warning(self, title: str, message: str) -> None:
        """Display a warning message to the user.

        Args:
            title: Dialog title.
            message: Body text describing the warning.
        """
        ...

    # -- question dialogs -----------------------------------------------------

    def ask_yes_no(self, title: str, message: str) -> bool:
        """Prompt the user with a Yes / No question.

        Args:
            title: Dialog title.
            message: Question to ask.

        Returns:
            ``True`` if the user selected *Yes*, ``False`` otherwise.
        """
        ...

    def ask_ok_cancel(self, title: str, message: str) -> bool:
        """Prompt the user with an OK / Cancel question.

        Args:
            title: Dialog title.
            message: Question or informational text.

        Returns:
            ``True`` if the user selected *OK*, ``False`` otherwise.
        """
        ...

    # -- file / directory dialogs ---------------------------------------------

    def ask_directory(
        self,
        title: str = "Select Directory",
        initial_dir: Optional[str] = None,
    ) -> str:
        """Show a directory-selection dialog.

        Args:
            title: Dialog title.
            initial_dir: Directory to display initially.

        Returns:
            The selected directory path, or an empty string if cancelled.
        """
        ...

    def ask_open_filename(
        self,
        title: str = "Open File",
        initial_dir: Optional[str] = None,
        filetypes: Optional[list[tuple[str, str]]] = None,
    ) -> str:
        """Show a file-open dialog.

        Args:
            title: Dialog title.
            initial_dir: Directory to display initially.
            filetypes: Acceptable file types as ``(description, pattern)``
                tuples, e.g. ``[("Text files", "*.txt")]``.

        Returns:
            The selected file path, or an empty string if cancelled.
        """
        ...

    def ask_save_filename(
        self,
        title: str = "Save File",
        initial_dir: Optional[str] = None,
        default_ext: str = "",
        filetypes: Optional[list[tuple[str, str]]] = None,
    ) -> str:
        """Show a file-save dialog.

        Args:
            title: Dialog title.
            initial_dir: Directory to display initially.
            default_ext: Default file extension (e.g. ``".txt"``).
            filetypes: Acceptable file types as ``(description, pattern)``
                tuples.

        Returns:
            The selected file path, or an empty string if cancelled.
        """
        ...

    # -- event loop -----------------------------------------------------------

    def pump_events(self) -> None:
        """Process any pending UI events.

        This replaces direct calls to ``root.update()`` and allows
        long-running operations to keep the UI responsive without blocking.
        """
        ...


@runtime_checkable
class ProgressServiceProtocol(Protocol):
    """Protocol for progress / loading-overlay operations.

    Semantically identical to
    :class:`interface.services.progress_service.ProgressCallback` but
    re-exported here so that consumers only need to import from ``ports``.
    """

    def show(self, message: str = "") -> None:
        """Show the progress indicator with an optional message.

        Args:
            message: Text to display alongside the indicator.
        """
        ...

    def hide(self) -> None:
        """Hide the progress indicator."""
        ...

    def update_message(self, message: str) -> None:
        """Update the text shown on the progress indicator.

        Args:
            message: New text to display.
        """
        ...

    def is_visible(self) -> bool:
        """Return whether the progress indicator is currently visible.

        Returns:
            ``True`` if the indicator is shown, ``False`` otherwise.
        """
        ...


# ---------------------------------------------------------------------------
# Null (no-op) implementation — for headless / testing use
# ---------------------------------------------------------------------------


class NullUIService:
    """No-op :class:`UIServiceProtocol` implementation.

    Every dialog method returns a sensible default so that application logic
    can run without any real UI toolkit present (e.g. in unit tests, CI
    pipelines, or headless server environments).
    """

    def show_info(self, title: str, message: str) -> None:
        """No-op — silently ignores the info message."""

    def show_error(self, title: str, message: str) -> None:
        """No-op — silently ignores the error message."""

    def show_warning(self, title: str, message: str) -> None:
        """No-op — silently ignores the warning message."""

    def ask_yes_no(self, title: str, message: str) -> bool:
        """Returns ``False`` (the safe/conservative default)."""
        return False

    def ask_ok_cancel(self, title: str, message: str) -> bool:
        """Returns ``False`` (the safe/conservative default)."""
        return False

    def ask_directory(
        self,
        title: str = "Select Directory",
        initial_dir: Optional[str] = None,
    ) -> str:
        """Returns an empty string (no selection)."""
        return ""

    def ask_open_filename(
        self,
        title: str = "Open File",
        initial_dir: Optional[str] = None,
        filetypes: Optional[list[tuple[str, str]]] = None,
    ) -> str:
        """Returns an empty string (no selection)."""
        return ""

    def ask_save_filename(
        self,
        title: str = "Save File",
        initial_dir: Optional[str] = None,
        default_ext: str = "",
        filetypes: Optional[list[tuple[str, str]]] = None,
    ) -> str:
        """Returns an empty string (no selection)."""
        return ""

    def pump_events(self) -> None:
        """No-op — nothing to pump."""


# ---------------------------------------------------------------------------
# Tkinter adapter
# ---------------------------------------------------------------------------


class TkinterUIService:
    """Adapter that satisfies :class:`UIServiceProtocol` using Tkinter.

    Tkinter modules (``tkinter.messagebox``, ``tkinter.filedialog``) are
    imported lazily inside ``__init__`` so that the mere *definition* of this
    class never triggers a Tkinter import — only instantiation does.

    Args:
        root: The ``tkinter.Tk`` root window instance used for
            ``pump_events()`` and as the implicit parent for dialogs.
    """

    def __init__(self, root) -> None:  # root: tkinter.Tk
        import tkinter.filedialog as _fd
        import tkinter.messagebox as _mb

        self._root = root
        self._messagebox = _mb
        self._filedialog = _fd

    # -- informational dialogs ------------------------------------------------

    def show_info(self, title: str, message: str) -> None:
        """Delegates to ``tkinter.messagebox.showinfo``."""
        self._messagebox.showinfo(title, message)

    def show_error(self, title: str, message: str) -> None:
        """Delegates to ``tkinter.messagebox.showerror``."""
        self._messagebox.showerror(title, message)

    def show_warning(self, title: str, message: str) -> None:
        """Delegates to ``tkinter.messagebox.showwarning``."""
        self._messagebox.showwarning(title, message)

    # -- question dialogs -----------------------------------------------------

    def ask_yes_no(self, title: str, message: str) -> bool:
        """Delegates to ``tkinter.messagebox.askyesno``."""
        return self._messagebox.askyesno(title, message)

    def ask_ok_cancel(self, title: str, message: str) -> bool:
        """Delegates to ``tkinter.messagebox.askokcancel``."""
        return self._messagebox.askokcancel(title, message)

    # -- file / directory dialogs ---------------------------------------------

    def ask_directory(
        self,
        title: str = "Select Directory",
        initial_dir: Optional[str] = None,
    ) -> str:
        """Delegates to ``tkinter.filedialog.askdirectory``."""
        kwargs: dict[str, object] = {"title": title}
        if initial_dir is not None:
            kwargs["initialdir"] = initial_dir
        result = self._filedialog.askdirectory(**kwargs)
        return result if isinstance(result, str) else ""

    def ask_open_filename(
        self,
        title: str = "Open File",
        initial_dir: Optional[str] = None,
        filetypes: Optional[list[tuple[str, str]]] = None,
    ) -> str:
        """Delegates to ``tkinter.filedialog.askopenfilename``."""
        kwargs: dict[str, object] = {"title": title}
        if initial_dir is not None:
            kwargs["initialdir"] = initial_dir
        if filetypes is not None:
            kwargs["filetypes"] = filetypes
        result = self._filedialog.askopenfilename(**kwargs)
        return result if isinstance(result, str) else ""

    def ask_save_filename(
        self,
        title: str = "Save File",
        initial_dir: Optional[str] = None,
        default_ext: str = "",
        filetypes: Optional[list[tuple[str, str]]] = None,
    ) -> str:
        """Delegates to ``tkinter.filedialog.asksaveasfilename``."""
        kwargs: dict[str, object] = {
            "title": title,
            "defaultextension": default_ext,
        }
        if initial_dir is not None:
            kwargs["initialdir"] = initial_dir
        if filetypes is not None:
            kwargs["filetypes"] = filetypes
        result = self._filedialog.asksaveasfilename(**kwargs)
        return result if isinstance(result, str) else ""

    # -- event loop -----------------------------------------------------------

    def pump_events(self) -> None:
        """Delegates to ``root.update()`` to process pending Tk events."""
        self._root.update()
