"""Qt implementation of the search/filter widget."""

from typing import Optional, Callable
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QShortcut, QKeySequence


class SearchWidget(QWidget):
    """Search/filter widget with text entry and apply button.

    Emits filter_changed signal when the filter text is applied.
    Supports Escape key to clear the filter when active.

    Args:
        parent: Parent widget
        initial_value: Initial filter text
        on_filter_change: Optional callback for filter changes
    """

    filter_changed = pyqtSignal(str)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        initial_value: str = "",
        on_filter_change: Optional[Callable[[str], None]] = None,
    ):
        super().__init__(parent)
        self._filter_value = initial_value
        self._on_filter_change = on_filter_change

        if on_filter_change:
            self.filter_changed.connect(on_filter_change)

        self._build_ui()
        self._setup_shortcuts()

        if initial_value:
            self._entry.setText(initial_value)
            self._escape_shortcut.setEnabled(True)

    @property
    def entry(self) -> QLineEdit:
        """Get the search entry field."""
        return self._entry

    @property
    def button(self) -> QPushButton:
        """Get the filter button."""
        return self._button

    @property
    def value(self) -> str:
        """Get the current filter text."""
        return self._entry.text()

    def clear(self) -> None:
        """Clear the search field and fire filter change."""
        self._entry.clear()
        self._on_filter_applied("")

    def set_value(self, value: str) -> None:
        """Set the search field text without firing the signal.

        Args:
            value: The new text value
        """
        self._entry.setText(value)

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the widget.

        Args:
            enabled: True to enable, False to disable
        """
        self._entry.setEnabled(enabled)
        self._button.setEnabled(enabled)

    def _build_ui(self) -> None:
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self._entry = QLineEdit()
        self._entry.setPlaceholderText("Filter...")
        self._entry.returnPressed.connect(self._on_return_pressed)

        self._button = QPushButton("Update Filter")
        self._button.clicked.connect(self._on_button_clicked)

        layout.addWidget(self._entry, stretch=1)
        layout.addWidget(self._button)
        self.setLayout(layout)

    def _setup_shortcuts(self) -> None:
        self._escape_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self._escape_shortcut.setEnabled(False)
        self._escape_shortcut.activated.connect(self._on_escape_pressed)

    def _on_button_clicked(self) -> None:
        self._on_filter_applied(self._entry.text())

    def _on_return_pressed(self) -> None:
        self._on_filter_applied(self._entry.text())

    def _on_escape_pressed(self) -> None:
        self.clear()

    def _on_filter_applied(self, filter_text: str) -> None:
        if self._filter_value == filter_text:
            return

        self._filter_value = filter_text
        self._escape_shortcut.setEnabled(bool(filter_text))
        self.filter_changed.emit(filter_text)
