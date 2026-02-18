"""PyQt6 implementations of UIServiceProtocol and ProgressServiceProtocol.

Provides :class:`QtUIService` and :class:`QtProgressService` as the Qt
equivalents of ``TkinterUIService`` and ``TkinterProgressCallback``.  All
dependencies (parent widgets, application instance) are injectable to
support testing and headless environments.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QEvent, QObject, Qt
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)


class QtUIService:
    """Adapter that satisfies :class:`UIServiceProtocol` using PyQt6.

    Uses :class:`QMessageBox` for informational and question dialogs,
    :class:`QFileDialog` for file/directory selection, and
    :meth:`QApplication.processEvents` for event-loop pumping.

    Args:
        parent: Optional parent widget for all dialogs.  When ``None``,
            dialogs are shown as top-level windows.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        self._parent = parent

    # -- informational dialogs ------------------------------------------------

    def show_info(self, title: str, message: str) -> None:
        """Display an informational message via :class:`QMessageBox`."""
        QMessageBox.information(self._parent, title, message)

    def show_error(self, title: str, message: str) -> None:
        """Display an error message via :class:`QMessageBox`."""
        QMessageBox.critical(self._parent, title, message)

    def show_warning(self, title: str, message: str) -> None:
        """Display a warning message via :class:`QMessageBox`."""
        QMessageBox.warning(self._parent, title, message)

    # -- question dialogs -----------------------------------------------------

    def ask_yes_no(self, title: str, message: str) -> bool:
        """Prompt the user with a Yes / No question.

        Returns:
            ``True`` if the user selected *Yes*, ``False`` otherwise.
        """
        result = QMessageBox.question(
            self._parent,
            title,
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return result == QMessageBox.StandardButton.Yes

    def ask_ok_cancel(self, title: str, message: str) -> bool:
        """Prompt the user with an OK / Cancel question.

        Returns:
            ``True`` if the user selected *OK*, ``False`` otherwise.
        """
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
        """Convert Tkinter-style filetypes to a Qt filter string.

        Tkinter format: ``[("Description", "*.ext"), ...]``
        Qt format:      ``"Description (*.ext);;..."``

        Args:
            filetypes: Tkinter-style filetypes list, or ``None``.

        Returns:
            A ``;;``-separated Qt filter string, or an empty string when
            *filetypes* is ``None`` or empty.
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
        """Show a directory-selection dialog via :class:`QFileDialog`.

        Returns:
            The selected directory path, or an empty string if cancelled.
        """
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
        """Show a file-open dialog via :class:`QFileDialog`.

        Returns:
            The selected file path, or an empty string if cancelled.
        """
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
        """Show a file-save dialog via :class:`QFileDialog`.

        If *default_ext* is provided and the chosen path does not already
        carry an extension, *default_ext* is appended automatically.

        Returns:
            The selected file path, or an empty string if cancelled.
        """
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
        """Process pending Qt events via :meth:`QApplication.processEvents`."""
        QApplication.processEvents()


class QtProgressService(QObject):
    """Semi-transparent overlay that satisfies :class:`ProgressServiceProtocol`.

    Creates a :class:`QFrame` overlay covering the *parent* widget.  The
    overlay auto-resizes when the parent is resized by installing an event
    filter on the parent.

    Args:
        parent: The widget to overlay.  The overlay is parented to this
            widget and resizes to match it.
    """

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._parent = parent
        self._overlay = self._build_overlay(parent)
        self._label = self._build_label(self._overlay)
        self._setup_layout()
        self._overlay.hide()
        parent.installEventFilter(self)

    # -- construction helpers -------------------------------------------------

    @staticmethod
    def _build_overlay(parent: QWidget) -> QFrame:
        """Create the semi-transparent overlay frame."""
        overlay = QFrame(parent)
        overlay.setObjectName("qt_progress_overlay")
        overlay.setAutoFillBackground(True)

        palette = overlay.palette()
        color = QColor(0, 0, 0, 160)
        palette.setColor(QPalette.ColorRole.Window, color)
        overlay.setPalette(palette)

        overlay.setFrameShape(QFrame.Shape.NoFrame)
        return overlay

    @staticmethod
    def _build_label(parent: QWidget) -> QLabel:
        """Create the centred message label."""
        label = QLabel(parent)
        label.setAlignment(
            Qt.AlignmentFlag.AlignCenter,
        )
        label.setStyleSheet("color: white; font-size: 14pt;")
        label.setWordWrap(True)
        return label

    def _setup_layout(self) -> None:
        """Arrange the label inside the overlay with a centred layout."""
        layout = QVBoxLayout(self._overlay)
        layout.addStretch()
        layout.addWidget(self._label)
        layout.addStretch()
        self._overlay.setLayout(layout)

    # -- ProgressServiceProtocol implementation --------------------------------

    def show(self, message: str = "") -> None:
        """Show the overlay with an optional message.

        Resizes to cover the parent, sets the text, and raises the overlay
        above sibling widgets.
        """
        self._label.setText(message)
        self._sync_geometry()
        self._overlay.setVisible(True)
        self._overlay.raise_()

    def hide(self) -> None:
        """Hide the overlay."""
        self._overlay.setVisible(False)

    def update_message(self, message: str) -> None:
        """Update the label text.

        If the overlay is not currently visible it is shown automatically.
        """
        self._label.setText(message)
        if not self._overlay.isVisible():
            self.show(message)

    def is_visible(self) -> bool:
        """Return whether the overlay is currently visible."""
        return self._overlay.isVisible()

    # -- geometry management --------------------------------------------------

    def _sync_geometry(self) -> None:
        """Resize the overlay to match the parent widget."""
        self._overlay.setGeometry(self._parent.rect())

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        """Resize overlay when the parent widget is resized."""
        if obj is self._parent and event.type() == QEvent.Type.Resize:
            self._sync_geometry()
        return super().eventFilter(obj, event)
