"""PyQt5 implementations of UIServiceProtocol and ProgressServiceProtocol.

Provides :class:`QtUIService` and :class:`QtProgressService` as the Qt
equivalents of ``TkinterUIService`` and ``TkinterProgressCallback``.  All
dependencies (parent widgets, application instance) are injectable to
support testing and headless environments.
"""

from __future__ import annotations

import logging
import os

from PyQt5.QtCore import QEvent, QObject, Qt
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QLabel,
    QMessageBox,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from interface.qt.theme import Theme

logger = logging.getLogger(__name__)


class QtUIService:
    """Adapter that satisfies :class:`UIServiceProtocol` using PyQt5.

    Uses :class:`QMessageBox` for informational and question dialogs,
    :class:`QFileDialog` for file/directory selection, and
    :meth:`QApplication.processEvents` for event-loop pumping.

    Args:
        parent: Optional parent widget for all dialogs.  When ``None``,
            dialogs are shown as top-level windows.

    """

    def __init__(self, parent: QWidget | None = None) -> None:
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
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,  # type: ignore[arg-type] - PyQt5 stubs incorrect, flags work at runtime
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
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,  # type: ignore[arg-type] - PyQt5 stubs incorrect, flags work at runtime
            QMessageBox.StandardButton.Cancel,
        )
        return result == QMessageBox.StandardButton.Ok

    def ask_three_choices(
        self,
        title: str,
        message: str,
        choice1: str,
        choice2: str,
        choice3: str,
    ) -> int:
        """Prompt the user with a three-choice question.

        Returns:
            0 if user selected choice1, 1 if choice2, 2 if choice3.

        """
        msg_box = QMessageBox(self._parent)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        btn1 = msg_box.addButton(choice1, QMessageBox.ButtonRole.AcceptRole)
        btn2 = msg_box.addButton(choice2, QMessageBox.ButtonRole.AcceptRole)
        btn3 = msg_box.addButton(choice3, QMessageBox.ButtonRole.RejectRole)
        msg_box.setDefaultButton(btn1)
        msg_box.exec()

        clicked = msg_box.clickedButton()
        if clicked == btn1:
            return 0
        elif clicked == btn2:
            return 1
        elif clicked == btn3:
            return 2
        return -1

    # -- file / directory dialogs ---------------------------------------------

    @staticmethod
    def _convert_filetypes(
        filetypes: list[tuple[str, str]] | None,
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
        initial_dir: str | None = None,
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
        initial_dir: str | None = None,
        filetypes: list[tuple[str, str]] | None = None,
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
        initial_dir: str | None = None,
        default_ext: str = "",
        filetypes: list[tuple[str, str]] | None = None,
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
        if path and default_ext and "." not in os.path.basename(path):
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
        self._title_label = self._build_title_label(self._overlay)
        self._throbber = self._build_throbber(self._overlay)
        self._discovery_progress_label = self._build_phase_label(
            self._overlay,
            "Finding files to send",
        )
        self._discovery_progress_bar = self._build_progress_bar(self._overlay)
        self._send_progress_label = self._build_phase_label(
            self._overlay,
            "Sending files",
        )
        self._progress_bar = self._build_progress_bar(self._overlay)
        self._folder_label = self._build_detail_label(self._overlay)
        self._file_label = self._build_detail_label(self._overlay)
        self._footer_label = self._build_footer_label(self._overlay)
        self._total = 0  # Initialize total progress value
        self._current_folder_name = ""
        self._current_folder_num = 1
        self._current_folder_total = 1
        self._current_file_index = 0
        self._current_file_total = 0
        self._overall_file_total = 0
        self._completed_files_before_current = 0
        self._setup_layout()
        self._overlay.hide()
        parent.installEventFilter(self)
        self.set_indeterminate()  # Default to indeterminate mode

    # -- property access for tests and external usage -------------------------

    @property
    def progress_dialog(self) -> QFrame:
        """Get the progress overlay frame.

        This property provides access to the underlying overlay widget for testing
        and external code that needs to interact with it directly.

        Returns:
            The :class:`QFrame` overlay instance.

        """
        return self._overlay

    # -- construction helpers -------------------------------------------------

    @staticmethod
    def _build_overlay(parent: QWidget) -> QFrame:
        """Create the semi-transparent overlay frame."""
        overlay = QFrame(parent)
        overlay.setObjectName("qt_progress_overlay")
        overlay.setAutoFillBackground(True)
        # Ensure stylesheet background gets painted even with global QFrame styles.
        overlay.setAttribute(
            Qt.WidgetAttribute.WA_StyledBackground,
            True,  # noqa: FBT003 - Qt attribute requires boolean argument for WA_StyledBackground
        )
        overlay.setStyleSheet(
            f"QFrame#qt_progress_overlay "
            f"{{ background-color: {Theme.OVERLAY_BACKGROUND}; }}"
        )

        palette = overlay.palette()
        color = QColor(0, 0, 0, 230)  # Semi-transparent black
        palette.setColor(QPalette.ColorRole.Window, color)
        overlay.setPalette(palette)

        overlay.setFrameShape(QFrame.Shape.NoFrame)
        return overlay

    @staticmethod
    def _build_title_label(parent: QWidget) -> QLabel:
        """Create the centred title label (main message)."""
        label = QLabel(parent)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(
            f"color: {Theme.TEXT_ON_OVERLAY}; font-size: 16pt; font-weight: bold;"
        )
        label.setWordWrap(True)
        return label

    @staticmethod
    def _build_detail_label(parent: QWidget) -> QLabel:
        """Create a label for detailed progress information."""
        label = QLabel(parent)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(
            f"color: {Theme.TEXT_ON_OVERLAY_SECONDARY}; font-size: 12pt;"
        )
        label.setWordWrap(True)
        return label

    @staticmethod
    def _build_footer_label(parent: QWidget) -> QLabel:
        """Create the footer label for additional context."""
        label = QLabel(parent)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(
            f"color: {Theme.TEXT_ON_OVERLAY_TERTIARY}; "
            f"font-size: 11pt; font-style: italic;"
        )
        label.setWordWrap(True)
        return label

    @staticmethod
    def _build_phase_label(parent: QWidget, text: str) -> QLabel:
        """Create a label for a progress phase bar."""
        label = QLabel(text, parent)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(
            f"color: {Theme.TEXT_ON_OVERLAY_SECONDARY}; "
            f"font-size: 11pt; font-weight: 600;"
        )
        return label

    @staticmethod
    def _build_throbber(parent: QWidget) -> QLabel:
        """Create an animated throbber indicator with pulsing effect."""
        throbber = QLabel("◐", parent)
        throbber.setAlignment(Qt.AlignmentFlag.AlignCenter)
        throbber.setStyleSheet(
            f"color: {Theme.TEXT_ON_OVERLAY}; font-size: 36pt; font-weight: bold;"
        )

        # Create pulsing animation for opacity (ping-pong effect)
        # Use QGraphicsOpacityEffect for proper opacity animation support
        from PyQt5.QtCore import QEasingCurve, QPropertyAnimation
        from PyQt5.QtWidgets import QGraphicsOpacityEffect

        opacity_effect = QGraphicsOpacityEffect(throbber)
        throbber.setGraphicsEffect(opacity_effect)

        animation = QPropertyAnimation(opacity_effect, b"opacity")
        animation.setDuration(1000)
        animation.setStartValue(0.3)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

        # Ping-pong effect: reverse direction when animation finishes
        def on_animation_finished() -> None:
            current_dir = animation.direction()
            new_dir = (
                QPropertyAnimation.Direction.Backward
                if current_dir == QPropertyAnimation.Direction.Forward
                else QPropertyAnimation.Direction.Forward
            )
            animation.setDirection(new_dir)
            animation.start()

        animation.finished.connect(on_animation_finished)
        animation.start()
        # Store animation and effect as attributes to prevent garbage collection
        setattr(throbber, "_animation", animation)
        setattr(throbber, "_opacity_effect", opacity_effect)
        return throbber

    @staticmethod
    def _build_progress_bar(parent: QWidget) -> "QProgressBar":
        """Create a QProgressBar for percentage-based progress."""
        from PyQt5.QtWidgets import QProgressBar

        progress_bar = QProgressBar(parent)
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(100)
        progress_bar.setValue(0)
        progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid {Theme.PROGRESS_BAR_BORDER};
                border-radius: 5px;
                text-align: center;
                color: {Theme.TEXT_ON_OVERLAY};
                font-size: 12pt;
            }}
            QProgressBar::chunk {{
                background-color: {Theme.PROGRESS_BAR_CHUNK};
                border-radius: 3px;
            }}
        """)
        return progress_bar

    def _setup_layout(self) -> None:
        """Arrange the widgets inside the overlay with a centred layout."""
        layout = QVBoxLayout(self._overlay)
        layout.addStretch()
        layout.addWidget(self._throbber)
        layout.addWidget(self._discovery_progress_label)
        layout.addWidget(self._discovery_progress_bar)
        layout.addSpacing(Theme.SPACING_MD_INT)
        layout.addWidget(self._send_progress_label)
        layout.addWidget(self._progress_bar)
        layout.addSpacing(Theme.SPACING_LG_INT)
        layout.addWidget(self._title_label)
        layout.addSpacing(Theme.SPACING_MD_INT)
        layout.addWidget(self._folder_label)
        layout.addWidget(self._file_label)
        layout.addSpacing(Theme.SPACING_LG_INT)
        layout.addWidget(self._footer_label)
        layout.addStretch()
        self._overlay.setLayout(layout)

    # -- ProgressServiceProtocol implementation --------------------------------

    def show(self, message: str = "") -> None:
        """Show the overlay with an optional message.

        Resizes to cover the parent, sets the text, and raises the overlay
        above sibling widgets.
        """
        self._title_label.setText(message)
        # Ensure parent widget has proper geometry
        if self._parent.width() == 0 or self._parent.height() == 0:
            self._parent.resize(640, 480)  # Default size if parent is hidden
        if not self._parent.isVisible():
            self._parent.show()  # Show parent to ensure proper rendering
        self._sync_geometry()
        self._overlay.setVisible(True)
        self._overlay.raise_()
        # Process events to ensure visibility updates
        QApplication.processEvents()

    def show_progress(self) -> None:
        """Show the progress overlay with default message.

        Alias for :meth:`show` for backward compatibility with tests.
        """
        self.show()

    def hide(self) -> None:
        """Hide the overlay."""
        self._overlay.setVisible(False)

    def hide_progress(self) -> None:
        """Hide the progress overlay.

        Alias for :meth:`hide` for backward compatibility with tests.
        """
        self.hide()

    def dispose(self) -> None:
        """Release Qt resources associated with the overlay.

        Stops any running throbber animation, removes the parent event filter,
        and schedules overlay deletion. This helps avoid resource leakage in
        repeated create/destroy test cycles.
        """
        animation = getattr(self._throbber, "_animation", None)
        if animation is not None:
            try:
                animation.stop()
            except RuntimeError:
                logger.debug(
                    "Failed to stop throbber animation during dispose", exc_info=True
                )

        if self._parent is not None:
            try:
                self._parent.removeEventFilter(self)
            except (RuntimeError, AttributeError):
                logger.debug(
                    "Failed to remove event filter during dispose", exc_info=True
                )

        if self._overlay is not None:
            try:
                self._overlay.hide()
                self._overlay.deleteLater()
            except RuntimeError:
                logger.debug(
                    "Failed to hide and delete overlay during dispose", exc_info=True
                )

    def set_message(self, message: str) -> None:
        """Set the progress message.

        Updates the main title label with the given message.

        Args:
            message: The message to display

        """
        self.update_message(message)

    def set_total(self, total: int) -> None:
        """Set the total progress value.

        This is a helper method for progress tracking. Currently stores
        the total but doesn't affect the display directly.

        Args:
            total: The total progress value

        """
        # Store total for reference if needed
        self._total = total

    def set_current(self, current: int) -> None:
        """Set the current progress value.

        Updates the progress bar if total is known, otherwise shows
        indeterminate progress.

        Args:
            current: The current progress value

        """
        if hasattr(self, "_total") and self._total > 0:
            percentage = min(100, int((current / self._total) * 100))
            self.update_progress(percentage)
        else:
            self.set_indeterminate()

    def update_message(self, message: str) -> None:
        """Update the label text.

        If the overlay is not currently visible it is shown automatically.
        """
        self._title_label.setText(message)
        if not self._overlay.isVisible():
            self.show(message)

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
        if folder_total > 0:
            self._folder_label.setText(f"Folder {folder_num} of {folder_total}")
            self._folder_label.show()
        else:
            self._folder_label.hide()

        if file_total > 0:
            self._file_label.setText(f"File {file_num} of {file_total}")
            self._file_label.show()
        else:
            self._file_label.hide()

        if footer:
            self._footer_label.setText(footer)
            self._footer_label.show()
        else:
            self._footer_label.hide()

    def is_visible(self) -> bool:
        """Return whether the overlay is currently visible."""
        return self._overlay.isVisible()

    def update_progress(self, progress: int) -> None:
        """Update the progress with a percentage value (0-100).

        Shows a progress bar with the given percentage and hides the throbber.

        Args:
            progress: Progress percentage from 0 to 100

        """
        # Ensure progress is within valid range
        progress = max(0, min(100, progress))
        self._progress_bar.setValue(progress)
        self._throbber.hide()
        self._send_progress_label.show()
        self._progress_bar.show()

    def update_discovery_progress(
        self,
        folder_num: int,
        folder_total: int,
        folder_name: str,
        pending_for_folder: int,
        pending_total: int,
    ) -> None:
        """Update phase-1 (file discovery) progress.

        Args:
            folder_num: Current folder index (1-based)
            folder_total: Total folders being scanned
            folder_name: Current folder display name
            pending_for_folder: Pending files found in current folder
            pending_total: Accumulated pending files found so far

        """
        if folder_total <= 0:
            self._discovery_progress_bar.setValue(0)
        else:
            discovery_pct = int((folder_num / folder_total) * 100)
            self._discovery_progress_bar.setValue(max(0, min(100, discovery_pct)))

        self._discovery_progress_label.setText(
            f"Finding files to send ({folder_num}/{folder_total})"
        )
        self._title_label.setText("Finding files to send...")
        self._folder_label.setText(f"Folder: {folder_name}")
        self._folder_label.show()
        self._file_label.setText(
            f"Pending in folder: {pending_for_folder} | Pending total: {pending_total}"
        )
        self._file_label.show()
        self._footer_label.hide()
        self._throbber.hide()
        self._discovery_progress_label.show()
        self._discovery_progress_bar.show()
        self._send_progress_label.show()
        self._progress_bar.show()

    def start_discovery(self, folder_total: int) -> None:
        """Begin phase-1 (file discovery) tracking."""
        self.show("Finding files to send...")
        self._discovery_progress_bar.setValue(0)
        self._progress_bar.setValue(0)
        self._discovery_progress_label.setText(
            f"Finding files to send (0/{folder_total})"
        )
        self._send_progress_label.setText("Sending files")
        self._throbber.hide()
        self._discovery_progress_label.show()
        self._discovery_progress_bar.show()
        self._send_progress_label.show()
        self._progress_bar.show()

    def finish_discovery(self, total_pending: int) -> None:
        """Complete phase-1 discovery tracking."""
        self._discovery_progress_bar.setValue(100)
        self._footer_label.setText(f"Found {total_pending} file(s) ready to send")
        self._footer_label.show()

    def update_discovery_file(
        self,
        folder_num: int,
        folder_total: int,
        file_num: int,
        file_total: int,
        filename: str,
    ) -> None:
        """Update per-file progress during discovery phase.

        Called during checksum calculation to show which file is being scanned.

        Args:
            folder_num: Current folder index (1-based)
            folder_total: Total folders being scanned
            file_num: Current file index within folder (1-based)
            file_total: Total files in current folder
            filename: Name of the file being scanned

        """
        # Show scanning status in the file label
        self._file_label.setText(f"Scanning: {filename} ({file_num}/{file_total})")
        self._file_label.show()
        # Process events to keep UI responsive
        QApplication.processEvents()

    def start_sending(self, total_files: int, total_folders: int) -> None:
        """Begin phase-2 (sending) tracking."""
        self._overall_file_total = max(0, total_files)
        self._completed_files_before_current = 0
        self._current_folder_num = 1
        self._current_folder_total = max(1, total_folders)
        self._progress_bar.setValue(0)
        self._send_progress_label.setText(
            f"Sending files (0/{self._overall_file_total})"
        )
        self._title_label.setText("Sending files...")
        self._throbber.hide()
        self._discovery_progress_label.show()
        self._discovery_progress_bar.show()
        self._send_progress_label.show()
        self._progress_bar.show()

    def set_folder_context(
        self,
        folder_num: int,
        folder_total: int,
        folder_name: str,
        file_total: int,
    ) -> None:
        """Set active folder metadata for phase-2 sending progress."""
        self._current_folder_num = max(1, folder_num)
        self._current_folder_total = max(1, folder_total)
        self._current_folder_name = folder_name
        self._current_file_total = max(0, file_total)
        self._current_file_index = 0

        self.update_detailed_progress(
            folder_num=self._current_folder_num,
            folder_total=self._current_folder_total,
            file_num=0,
            file_total=self._current_file_total,
            footer="",
        )

    def set_indeterminate(self) -> None:
        """Switch to indeterminate mode (show throbber, hide progress bar)."""
        self._throbber.show()
        self._send_progress_label.hide()
        self._progress_bar.hide()
        self._progress_bar.setValue(0)

    # -- dispatch compatibility methods --------------------------------------

    def start_folder(
        self,
        folder_name: str,
        total_files: int,
        folder_num: int | None = None,
        folder_total: int | None = None,
    ) -> None:
        """Start progress reporting for a folder.

        This compatibility method is used by the dispatch orchestrator.

        Args:
            folder_name: Display name of the folder being processed.
            total_files: Number of files to process in this folder.

        """
        self._current_folder_name = folder_name
        if folder_num is not None:
            self._current_folder_num = max(1, folder_num)
        if folder_total is not None:
            self._current_folder_total = max(1, folder_total)
        self._current_file_index = 0
        self._current_file_total = max(0, total_files)

        self.update_message(f"Processing folder: {folder_name}")
        self.update_detailed_progress(
            folder_num=self._current_folder_num,
            folder_total=self._current_folder_total,
            file_num=0,
            file_total=self._current_file_total,
            footer="",
        )
        if self._overall_file_total <= 0:
            self.set_indeterminate()

    def update_file(self, current_file: int, total_files: int) -> None:
        """Update file-level progress for the current folder.

        Args:
            current_file: 1-based current file index.
            total_files: Total files in current folder.

        """
        self._current_file_index = max(0, current_file)
        self._current_file_total = max(0, total_files)

        if self._overall_file_total > 0:
            absolute_progress = self._completed_files_before_current + min(
                self._current_file_index, self._current_file_total
            )
            percentage = int((absolute_progress / self._overall_file_total) * 100)
            self._send_progress_label.setText(
                f"Sending files ({absolute_progress}/{self._overall_file_total})"
            )
            self.update_progress(percentage)
        elif self._current_file_total > 0:
            percentage = int(
                (self._current_file_index / self._current_file_total) * 100
            )
            self.update_progress(percentage)
        else:
            self.set_indeterminate()

        self.update_detailed_progress(
            folder_num=self._current_folder_num,
            folder_total=self._current_folder_total,
            file_num=self._current_file_index,
            file_total=self._current_file_total,
            footer="",
        )

    def complete_folder(self, *, success: bool) -> None:
        """Complete progress reporting for the current folder.

        Args:
            success: Whether folder processing succeeded.

        """
        status_text = "Completed" if success else "Completed with errors"
        folder_name = self._current_folder_name or "folder"
        self.update_message(f"{status_text}: {folder_name}")

        if self._overall_file_total > 0:
            self._completed_files_before_current = min(
                self._overall_file_total,
                self._completed_files_before_current + self._current_file_total,
            )
            self._send_progress_label.setText(
                "Sending files "
                f"({self._completed_files_before_current}/{self._overall_file_total})"
            )

        self.update_detailed_progress(
            folder_num=self._current_folder_num,
            folder_total=self._current_folder_total,
            file_num=self._current_file_total,
            file_total=self._current_file_total,
            footer="",
        )
        if self._overall_file_total > 0:
            overall_percentage = int(
                (self._completed_files_before_current / self._overall_file_total) * 100
            )
            self.update_progress(overall_percentage)
        else:
            self.update_progress(100)

    # -- geometry management --------------------------------------------------

    def _sync_geometry(self) -> None:
        """Resize the overlay to match the parent widget."""
        self._overlay.setGeometry(self._parent.rect())

    def eventFilter(self, a0: QObject | None, a1: QEvent | None) -> bool:  # noqa: N802 - Qt override, 'a0'/'a1' are conventional Qt names
        """Resize overlay when the parent widget is resized."""
        parent = getattr(self, "_parent", None)
        if a0 is parent and a1 and a1.type() == QEvent.Type.Resize:
            self._sync_geometry()
        return super().eventFilter(a0, a1)
