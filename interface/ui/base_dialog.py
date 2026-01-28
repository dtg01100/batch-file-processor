"""
Base dialog module for PyQt6 interface.

This module contains the base dialog class for all interface dialogs.
"""

from typing import Any, Dict, Optional

from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, pyqtSignal as Signal


class BaseDialog(QDialog):
    """Base dialog class for all interface dialogs.
    
    This class provides common patterns for modal dialogs including:
    - OK/Cancel button handling
    - validate()/apply() pattern
    - Modal dialog behavior
    - Common dialog setup
    """
    
    # Signals
    accepted_data = Signal(dict)  # Emitted when dialog is accepted with data
    
    def __init__(
        self,
        parent: QWidget = None,
        title: str = "Dialog",
        data: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the base dialog.
        
        Args:
            parent: Parent window.
            title: Dialog title.
            data: Optional data to initialize the dialog with.
        """
        super().__init__(parent)
        
        self.setWindowTitle(title)
        self.setModal(True)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowSystemMenuHint)
        
        # Store initial data
        self._data = data if data else {}
        
        # Result of the dialog
        self._result: Optional[Dict[str, Any]] = None
        
        # Create layout
        self._layout = QVBoxLayout(self)
        
        # Create body frame
        self._body_frame = QWidget()
        self._layout.addWidget(self._body_frame)
        
        # Create button box
        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        self._button_box.accepted.connect(self._on_ok)
        self._button_box.rejected.connect(self.reject)
        self._layout.addWidget(self._button_box)
        
        # Create widgets
        self._create_widgets()
        
        # Setup layout
        self._setup_layout()
        
        # Set initial focus
        self._set_initial_focus()
    
    def _create_widgets(self) -> None:
        """Create dialog widgets. Override in subclasses."""
        pass
    
    def _setup_layout(self) -> None:
        """Setup dialog layout. Override in subclasses."""
        pass
    
    def _set_initial_focus(self) -> None:
        """Set initial focus widget. Override in subclasses."""
        pass
    
    def _on_ok(self) -> None:
        """Handle OK button press."""
        if not self.validate():
            return
        
        result = self.apply()
        self._result = result
        self.accepted_data.emit(result)
        self.accept()
    
    def validate(self) -> bool:
        """Validate the dialog input.
        
        This method should be overridden in subclasses to perform
        validation of the dialog's input.
        
        Returns:
            True if input is valid, False otherwise.
        """
        return True
    
    def apply(self) -> Dict[str, Any]:
        """Apply the dialog changes.
        
        This method should be overridden in subclasses to apply
        the dialog's changes to the data.
        
        Returns:
            Dictionary containing the applied changes.
        """
        return self._data.copy()
    
    @property
    def data(self) -> Dict[str, Any]:
        """Get the dialog data."""
        return self._data
    
    @data.setter
    def data(self, value: Dict[str, Any]) -> None:
        """Set the dialog data."""
        self._data = value
    
    def get_result(self) -> Optional[Dict[str, Any]]:
        """Get the dialog result.
        
        Returns:
            The dialog result, or None if cancelled.
        """
        return self._result
    
    def show(self) -> Optional[Dict[str, Any]]:
        """Show the dialog and wait for result.
        
        Returns:
            The dialog result, or None if cancelled.
        """
        if self.exec() == QDialog.DialogCode.Accepted:
            return self._result
        return None


class OkCancelDialog(BaseDialog):
    """Base dialog with OK and Cancel buttons."""
    
    def __init__(
        self,
        parent: QWidget = None,
        title: str = "Dialog",
        data: Optional[Dict[str, Any]] = None
    ):
        super().__init__(parent, title, data)
