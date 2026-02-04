"""
Base dialog module for PyQt6 interface.

This module contains the base dialog class for all interface dialogs.
Provides a unified lifecycle and API for all dialog subclasses.
"""

from copy import deepcopy
from typing import Any, Dict, Optional, Tuple

from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout, QWidget, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal as Signal


class BaseDialog(QDialog):
    """Base dialog class for all interface dialogs.

    Provides unified lifecycle and patterns for all modal dialogs:
    
    **Lifecycle:**
    1. __init__(parent, title, data) — initialize and setup UI
    2. _setup_ui() — build widget hierarchy (override)
    3. _set_dialog_values() — populate UI from self.data (override)
    4. User interacts with widgets
    5. OK clicked → validate() → apply() → accept dialog
    6. Cancel clicked → discard changes, close dialog
    
    **Implementation Guide:**
    - Override _setup_ui() to build widgets (don't call super)
    - Override _set_dialog_values() to load data into UI
    - Override validate() to return (is_valid, error_message) tuple
    - Override apply() to write UI values back to self.data
    - Keep self.data synchronized with UI state when done

    **Signals:**
    - accepted_data: emitted with data dict when OK is pressed and validation passes
    """

    # Signals
    accepted_data = Signal(dict)  # Emitted when dialog is accepted with data

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: str = "Dialog",
        data: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the base dialog.

        Args:
            parent: Parent window.
            title: Dialog title.
            data: Optional data dict to initialize dialog with.
        """
        super().__init__(parent)

        self.setWindowTitle(title)
        self.setModal(True)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowSystemMenuHint)

        # Store data; keep original for potential reset
        self._data = data if data else {}
        self._original_data = deepcopy(self._data)

        # Result of the dialog (set when accepted)
        self._result: Optional[Dict[str, Any]] = None

        # Create main layout
        self._layout = QVBoxLayout(self)

        # Setup dialog UI and initial values
        self._setup_ui()
        self._set_dialog_values()
        self._setup_buttons()

    def _setup_ui(self) -> None:
        """Setup dialog UI widgets.
        
        Override in subclasses to build widget hierarchy.
        Do NOT call super() in override (this method is a hook).
        Do NOT add widgets to self._layout here; add to self._body_layout.
        
        Example:
            def _setup_ui(self):
                self._body_layout = QVBoxLayout()
                self._name_input = QLineEdit()
                self._body_layout.addWidget(QLabel("Name:"))
                self._body_layout.addWidget(self._name_input)
                self._layout.addLayout(self._body_layout)
        """
        # Default: create empty body layout
        # Subclasses can override to add custom widgets
        if not hasattr(self, '_body_layout'):
            self._body_layout = QVBoxLayout()
            self._layout.addLayout(self._body_layout)

    def _set_dialog_values(self) -> None:
        """Load initial data into UI widgets.
        
        Override in subclasses to populate UI from self.data.
        Called after _setup_ui() in __init__.
        
        Example:
            def _set_dialog_values(self):
                self._name_input.setText(self.data.get("name", ""))
        """
        pass

    def _setup_buttons(self) -> None:
        """Setup OK/Cancel buttons (internal; do not override)."""
        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._button_box.accepted.connect(self._on_ok_clicked)
        self._button_box.rejected.connect(self.reject)
        self._layout.addWidget(self._button_box)

    def _on_ok_clicked(self) -> None:
        """Handle OK button press (internal)."""
        is_valid, error_msg = self.validate()
        if not is_valid:
            QMessageBox.warning(self, "Validation Error", error_msg)
            return
        
        self.apply()
        self._result = deepcopy(self.data)
        self.accepted_data.emit(self._result)
        self.accept()

    def validate(self) -> Tuple[bool, str]:
        """Validate dialog data before accepting.
        
        Override in subclasses to implement validation logic.
        
        Returns:
            Tuple of (is_valid, error_message).
            is_valid=True and error_message="" means valid.
            is_valid=False with non-empty error_message shows warning dialog.
        
        Example:
            def validate(self):
                name = self._name_input.text().strip()
                if not name:
                    return (False, "Name cannot be empty")
                if len(name) < 3:
                    return (False, "Name must be at least 3 characters")
                return (True, "")
        """
        return (True, "")

    def apply(self) -> None:
        """Write UI state back to self.data.
        
        Override in subclasses to sync UI values to self.data.
        Called after validate() succeeds and before dialog closes.
        
        Example:
            def apply(self):
                self.data["name"] = self._name_input.text()
                self.data["active"] = self._active_checkbox.isChecked()
        """
        pass

    @property
    def data(self) -> Dict[str, Any]:
        """Get the dialog data dict."""
        return self._data

    @data.setter
    def data(self, value: Dict[str, Any]) -> None:
        """Set the dialog data dict."""
        self._data = value

    def get_result(self) -> Optional[Dict[str, Any]]:
        """Get the dialog result.

        Returns:
            The dialog result (data dict if OK pressed), or None if cancelled.
        """
        return self._result

    def show_modal(self) -> Optional[Dict[str, Any]]:
        """Show the dialog modally and wait for result.

        Returns:
            The dialog result (data dict if OK pressed), or None if cancelled.
        """
        if self.exec() == QDialog.DialogCode.Accepted:
            return self._result
        return None


class OkCancelDialog(BaseDialog):
    """Base dialog with OK and Cancel buttons."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: str = "Dialog",
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(parent, title, data)
