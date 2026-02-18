"""UI abstraction ports for toolkit-agnostic application design.

This module defines the complete set of ports (abstractions) the application
needs from ANY UI toolkit. It provides Protocol definitions for all UI
interactions (message boxes, file dialogs, progress overlays, event loop
pumping) plus a null implementation for headless/testing use.

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
# Qt adapter
# ---------------------------------------------------------------------------


class QtUIService:
    """Adapter that satisfies :class:`UIServiceProtocol` using PyQt6.

    Uses QMessageBox for dialogs, QFileDialog for file/directory selection,
    and QApplication.processEvents() for event-loop pumping.

    Args:
        parent: Optional parent widget for dialogs.
    """

    def __init__(self, parent=None) -> None:
        from PyQt6.QtWidgets import QWidget
        self._parent: Optional[QWidget] = parent

    # -- informational dialogs ------------------------------------------------

    def show_info(self, title: str, message: str) -> None:
        """Delegates to QMessageBox.information."""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self._parent, title, message)

    def show_error(self, title: str, message: str) -> None:
        """Delegates to QMessageBox.critical."""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(self._parent, title, message)

    def show_warning(self, title: str, message: str) -> None:
        """Delegates to QMessageBox.warning."""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.warning(self._parent, title, message)

    # -- question dialogs -----------------------------------------------------

    def ask_yes_no(self, title: str, message: str) -> bool:
        """Delegates to QMessageBox.question."""
        from PyQt6.QtWidgets import QMessageBox
        result = QMessageBox.question(
            self._parent,
            title,
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return result == QMessageBox.StandardButton.Yes

    def ask_ok_cancel(self, title: str, message: str) -> bool:
        """Delegates to QMessageBox.question."""
        from PyQt6.QtWidgets import QMessageBox
        result = QMessageBox.question(
            self._parent,
            title,
            message,
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        return result == QMessageBox.StandardButton.Ok

    # -- file / directory dialogs ---------------------------------------------

    @staticmethod
    def _convert_filetypes(
        filetypes: Optional[list[tuple[str, str]]],
    ) -> str:
        """Convert filetypes to a Qt filter string.

        Tkinter format: ``[("Description", "*.ext"), ...]``
        Qt format:      ``"Description (*.ext);;..."``
        """
        if not filetypes:
            return ""
        parts: list[str] = []
        for description, pattern in filetypes:
            parts.append(f"{description} ({pattern})")
        return ";;".join(parts)

    def ask_directory(
        self,
        title: str = "Select Directory",
        initial_dir: Optional[str] = None,
    ) -> str:
        """Delegates to QFileDialog.getExistingDirectory."""
        from PyQt6.QtWidgets import QFileDialog
        result = QFileDialog.getExistingDirectory(
            self._parent,
            title,
            initial_dir or "",
        )
        return result or ""

    def ask_open_filename(
        self,
        title: str = "Open File",
        initial_dir: Optional[str] = None,
        filetypes: Optional[list[tuple[str, str]]] = None,
    ) -> str:
        """Delegates to QFileDialog.getOpenFileName."""
        from PyQt6.QtWidgets import QFileDialog
        filter_str = self._convert_filetypes(filetypes)
        path, _ = QFileDialog.getOpenFileName(
            self._parent,
            title,
            initial_dir or "",
            filter_str,
        )
        return path or ""

    def ask_save_filename(
        self,
        title: str = "Save File",
        initial_dir: Optional[str] = None,
        default_ext: str = "",
        filetypes: Optional[list[tuple[str, str]]] = None,
    ) -> str:
        """Delegates to QFileDialog.getSaveFileName."""
        from PyQt6.QtWidgets import QFileDialog
        filter_str = self._convert_filetypes(filetypes)
        path, _ = QFileDialog.getSaveFileName(
            self._parent,
            title,
            initial_dir or "",
            filter_str,
        )
        if path and default_ext and "." not in path.rsplit("/", 1)[-1]:
            path += default_ext
        return path or ""

    # -- event loop -----------------------------------------------------------

    def pump_events(self) -> None:
        """Delegates to QApplication.processEvents()."""
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
