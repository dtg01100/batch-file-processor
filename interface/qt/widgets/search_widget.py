"""Qt implementation of the search/filter widget."""

from typing import Optional, Callable
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLineEdit
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QShortcut, QKeySequence

from interface.qt.theme import Theme


class SearchWidget(QWidget):
    """Search/filter widget with real-time text filtering.

    Emits filter_changed signal as the user types.
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

    def _build_ui(self) -> None:
        self.setStyleSheet(
            f"""
            SearchWidget {{
                background-color: transparent;
                border-radius: {Theme.RADIUS_LG};
                padding: {Theme.SPACING_SM};
            }}
        """
        )

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Theme.SPACING_SM_INT)

        self._entry = QLineEdit()
        self._entry.setPlaceholderText("\U0001F50D Search folders...")
        self._entry.setToolTip("Type folder name text to filter folders as you type")
        self._entry.setAccessibleName("Folder search")
        self._entry.setAccessibleDescription("Search folders by alias text (filters automatically as you type)")
        self._entry.setStyleSheet(Theme.get_input_stylesheet())
        self._entry.textChanged.connect(self._on_text_changed)

        layout.addWidget(self._entry, stretch=1)
        self.setLayout(layout)

    def _setup_shortcuts(self) -> None:
        self._escape_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self._escape_shortcut.setEnabled(False)
        self._escape_shortcut.activated.connect(self._on_escape_pressed)

    def _on_text_changed(self, text: str) -> None:
        self._on_filter_applied(text.strip())

    def _on_escape_pressed(self) -> None:
        self.clear()

    def _on_filter_applied(self, filter_text: str) -> None:
        if self._filter_value == filter_text:
            return

        self._filter_value = filter_text
        self._escape_shortcut.setEnabled(bool(filter_text))
        self.filter_changed.emit(filter_text)
