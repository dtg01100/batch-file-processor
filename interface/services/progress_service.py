"""Toolkit-agnostic progress reporting service."""
from __future__ import annotations
from typing import Protocol, runtime_checkable, Optional


@runtime_checkable
class ProgressCallback(Protocol):
    """Protocol for progress reporting - no Tkinter dependency."""

    def show(self, message: str = "") -> None:
        """Show the progress indicator with optional message."""
        ...

    def hide(self) -> None:
        """Hide the progress indicator."""
        ...

    def update_message(self, message: str) -> None:
        """Update the progress message."""
        ...

    def is_visible(self) -> bool:
        """Check if the progress indicator is currently visible."""
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


class NullProgressCallback:
    """No-op implementation for headless/testing use."""

    def show(self, message: str = "") -> None:
        pass

    def hide(self) -> None:
        pass

    def update_message(self, message: str) -> None:
        pass

    def is_visible(self) -> bool:
        return False

    def update_progress(self, progress: int) -> None:
        pass

    def set_indeterminate(self) -> None:
        pass


class CLIProgressCallback:
    """CLI implementation that prints to stdout."""

    def __init__(self) -> None:
        self._visible = False

    def show(self, message: str = "") -> None:
        self._visible = True
        if message:
            print(f"[PROGRESS] {message}")

    def hide(self) -> None:
        self._visible = False
        print("[PROGRESS] Done")

    def update_message(self, message: str) -> None:
        if self._visible:
            print(f"[PROGRESS] {message}")

    def is_visible(self) -> bool:
        return self._visible

    def update_progress(self, progress: int) -> None:
        if self._visible:
            print(f"[PROGRESS] {progress}%")

    def set_indeterminate(self) -> None:
        if self._visible:
            print("[PROGRESS] Processing...")
