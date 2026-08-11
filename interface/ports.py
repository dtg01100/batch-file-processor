"""UI abstraction ports for toolkit-agnostic application design.

This module defines the complete set of ports (abstractions) the application
needs from ANY UI toolkit. It provides Protocol definitions for all UI
interactions (message boxes, file dialogs, progress overlays, event loop
pumping) plus a null implementation for headless/testing use.

By programming against these protocols, the application logic is fully
decoupled from any specific UI framework.

Note: the former Qt adapter (:class:`QtUIService`) was removed with the
Qt UI layer in the webapp pivot. The protocols and :class:`NullUIService`
remain for headless/testing use.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


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

    def ask_three_choices(
        self,
        title: str,
        message: str,
        choice1: str,
        choice2: str,
        choice3: str,
    ) -> int:
        """Prompt the user with a three-choice question.

        Args:
            title: Dialog title.
            message: Question or informational text.
            choice1: Label for first button.
            choice2: Label for second button.
            choice3: Label for third button (cancel-like).

        Returns:
            0 if user selected choice1, 1 if choice2, 2 if choice3.

        """
        ...

    # -- file / directory dialogs ---------------------------------------------

    def ask_directory(
        self,
        title: str = "Select Directory",
        initial_dir: str | None = None,
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
        initial_dir: str | None = None,
        filetypes: list[tuple[str, str]] | None = None,
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
        initial_dir: str | None = None,
        default_ext: str = "",
        filetypes: list[tuple[str, str]] | None = None,
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

    def update_detailed_progress(
        self,
        folder_num: int,
        folder_total: int,
        file_num: int,
        file_total: int,
        footer: str = "",
    ) -> None:
        """Update the detailed progress information.

        Args:
            folder_num: Current folder index (1-based)
            folder_total: Total number of folders to process
            file_num: Current file index (1-based)
            file_total: Total number of files to process
            footer: Optional footer text

        """
        ...

    def is_visible(self) -> bool:
        """Return whether the progress indicator is currently visible.

        Returns:
            ``True`` if the indicator is shown, ``False`` otherwise.

        """
        ...

    def update_progress(self, progress: int) -> None:
        """Update the progress with a percentage value (0-100).

        Shows a progress bar with the given percentage and hides the throbber.

        Args:
            progress: Progress percentage from 0 to 100

        """
        ...

    def set_indeterminate(self) -> None:
        """Switch to indeterminate mode (show throbber, hide progress bar)."""
        ...


# ---------------------------------------------------------------------------
# Null (no-op) implementation -- for headless / testing use
# ---------------------------------------------------------------------------


class NullUIService:
    """No-op :class:`UIServiceProtocol` implementation.

    Every dialog method returns a sensible default so that application logic
    can run without any real UI toolkit present (e.g. in unit tests, CI
    pipelines, or headless server environments).

    Default return values:
        - show_* methods: No-op (silently ignored)
        - ask_yes_no: False (conservative/safe default)
        - ask_ok_cancel: False (conservative/safe default)
        - ask_three_choices: -1 (cancel/default indicator)
        - ask_* file/dir methods: "" (empty string = no selection)
        - pump_events: No-op

    Example:
        >>> ui = NullUIService()
        >>> ui.ask_yes_no("Confirm", "Delete all files?")
        False

    """

    def show_info(self, title: str, message: str) -> None:
        """No-op -- silently ignores the info message."""

    def show_error(self, title: str, message: str) -> None:
        """No-op -- silently ignores the error message."""

    def show_warning(self, title: str, message: str) -> None:
        """No-op -- silently ignores the warning message."""

    def ask_yes_no(self, _title: str, _message: str) -> bool:
        """Returns ``False`` (the safe/conservative default)."""
        return False

    def ask_ok_cancel(self, _title: str, _message: str) -> bool:
        """Returns ``False`` (the safe/conservative default)."""
        return False

    def ask_three_choices(
        self,
        _title: str,
        _message: str,
        _choice1: str,
        _choice2: str,
        _choice3: str,
    ) -> int:
        """Returns -1 (cancel/default indicator).

        Note:
            The Protocol specifies return values 0, 1, or 2 for the three
            choices. This implementation returns -1 to indicate that no
            choice was made (equivalent to cancel).

        """
        return -1

    def ask_directory(
        self,
        _title: str = "Select Directory",
        _initial_dir: str | None = None,
    ) -> str:
        """Returns an empty string (no selection)."""
        return ""

    def ask_open_filename(
        self,
        _title: str = "Open File",
        _initial_dir: str | None = None,
        _filetypes: list[tuple[str, str]] | None = None,
    ) -> str:
        """Returns an empty string (no selection)."""
        return ""

    def ask_save_filename(
        self,
        _title: str = "Save File",
        _initial_dir: str | None = None,
        _default_ext: str = "",
        _filetypes: list[tuple[str, str]] | None = None,
    ) -> str:
        """Returns an empty string (no selection)."""
        return ""

    def pump_events(self) -> None:
        """No-op -- nothing to pump."""



__all__ = [
    "NullUIService",
    "ProgressServiceProtocol",
    "UIServiceProtocol",
]
