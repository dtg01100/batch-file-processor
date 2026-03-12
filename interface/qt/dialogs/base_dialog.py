"""Base dialog class for Qt-based dialogs.

Provides a common base class for all Qt dialogs, replacing the tkinter Dialog class.
"""

from __future__ import annotations

from typing import Literal, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from interface.qt.theme import Theme


class BaseDialog(QDialog):
    """Base dialog class providing common functionality.

    This is the Qt equivalent of the tkinter Dialog class.
    Subclasses should override body() to create dialog content,
    and optionally override validate() and apply().

    Attributes:
        result: Store dialog result data

    Example:
        class MyDialog(BaseDialog):
            def body(self, parent):
                label = QLabel("Enter name:")
                parent.layout().addWidget(label)
                return None  # No initial focus widget

            def validate(self):
                return True  # Always valid

            def apply(self):
                print("Applying changes")
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: Optional[str] = None,
        action_mode: Literal["ok_cancel", "close_only", "none"] = "ok_cancel",
    ) -> None:
        super().__init__(parent)
        self._action_mode = action_mode

        if title:
            self.setWindowTitle(title)

        # Set modal behavior
        self.setWindowModality(Qt.WindowModality.WindowModal)

        # Create main layout
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(
            Theme.SPACING_SM_INT,
            Theme.SPACING_SM_INT,
            Theme.SPACING_SM_INT,
            Theme.SPACING_SM_INT,
        )

        # Create body container
        self._body_widget = QWidget()
        self._body_layout = QVBoxLayout(self._body_widget)
        self._body_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.addWidget(self._body_widget)

        # Build body
        self.initial_focus = self.body(self._body_widget)

        # Add button box
        self._button_box = self._create_button_box()
        if self._button_box is not None:
            self._main_layout.addWidget(self._button_box)

        # Set initial focus
        if self.initial_focus:
            self.initial_focus.setFocus()
        else:
            self.setFocus()

        # Set reasonable default minimum size
        self.setMinimumSize(500, 400)

    def body(self, parent: QWidget) -> Optional[QWidget]:
        """Create dialog body.

        Override this method to add widgets to the dialog.
        The parent widget's layout should be used to add child widgets.

        Args:
            parent: Parent widget for the body content

        Returns:
            Widget that should have initial focus, or None
        """

    def _create_button_box(self) -> Optional[QDialogButtonBox]:
        """Create dialog action buttons according to configured mode."""
        if self._action_mode == "none":
            return None

        if self._action_mode == "close_only":
            button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
            button_box.rejected.connect(self.reject)
            return button_box

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_ok)
        button_box.rejected.connect(self.reject)
        return button_box

    def _on_ok(self) -> None:
        """Handle OK button click."""
        if self.validate():
            self.apply()
            self.accept()

    def validate(self) -> bool:
        """Validate dialog data.

        Override this method to add validation logic.

        Returns:
            True if validation passes, False otherwise
        """
        return True

    def apply(self) -> None:
        """Apply dialog changes.

        Override this method to process dialog data.
        Called after validation succeeds.
        """

    def show_info(self, title: str, message: str) -> None:
        """Show an informational message box."""
        QMessageBox.information(self, title, message)

    def show_error(self, title: str, message: str) -> None:
        """Show an error message box."""
        QMessageBox.critical(self, title, message)

    def show_warning(self, title: str, message: str) -> None:
        """Show a warning message box."""
        QMessageBox.warning(self, title, message)

    def confirm_yes_no(self, title: str, message: str) -> bool:
        """Ask a Yes/No question and return True when Yes is selected."""
        reply = QMessageBox.question(
            self,
            title,
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    def confirm_ok_cancel(self, title: str, message: str) -> bool:
        """Ask an OK/Cancel question and return True when OK is selected."""
        reply = QMessageBox.question(
            self,
            title,
            message,
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        return reply == QMessageBox.StandardButton.Ok
