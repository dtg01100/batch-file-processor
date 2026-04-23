"""Qt implementation of the search/filter widget."""

from typing import Callable

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QHBoxLayout, QLineEdit, QShortcut, QStyle, QWidget

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
        parent: QWidget | None = None,
        initial_value: str = "",
        on_filter_change: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._filter_value = initial_value
        self._on_filter_change = on_filter_change
        self._pending_filter = initial_value

        if on_filter_change:
            self.filter_changed.connect(on_filter_change)

        self._build_ui()
        self._setup_shortcuts()

        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(150)
        self._debounce_timer.timeout.connect(self._emit_filter)

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
        had_content = (
            bool(self._entry.text())
            or bool(self._filter_value)
            or bool(self._pending_filter)
        )
        self._debounce_timer.stop()
        self._entry.blockSignals(True)  # noqa: FBT003 - prevent signal during programmatic clear
        self._entry.clear()
        self._entry.blockSignals(False)  # noqa: FBT003 - re-enable signals after programmatic clear
        self._pending_filter = ""
        self._filter_value = ""
        self._escape_shortcut.setEnabled(False)
        if had_content:
            self.filter_changed.emit("")

    def set_value(self, value: str) -> None:
        """Set the search field text without firing the signal.

        Args:
            value: The new text value

        """
        self._entry.setText(value)

    def set_enabled(self, *, enabled: bool) -> None:
        """Enable or disable the widget.

        Args:
            enabled: True to enable, False to disable

        """
        self._entry.setEnabled(enabled)

    def _build_ui(self) -> None:
        self.setStyleSheet(f"""
            SearchWidget {{
                background-color: transparent;
                border-radius: {Theme.RADIUS_LG};
                padding: {Theme.SPACING_SM};
            }}
        """)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Theme.SPACING_SM_INT)

        self._entry = QLineEdit()
        self._entry.setPlaceholderText("Search folders...")
        search_icon = self.style().standardIcon(
            QStyle.StandardPixmap.SP_FileDialogContentsView
        )
        self._entry.addAction(search_icon, QLineEdit.ActionPosition.LeadingPosition)
        self._entry.setToolTip("Type folder name text to filter folders as you type")
        self._entry.setAccessibleName("Folder search")
        self._entry.setAccessibleDescription(
            "Search folders by alias text (filters automatically as you type)"
        )
        self._entry.setStyleSheet(Theme.get_input_stylesheet())
        self._entry.textChanged.connect(self._on_text_changed)

        layout.addWidget(self._entry, stretch=1)
        self.setLayout(layout)

    def _setup_shortcuts(self) -> None:
        self._escape_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self._escape_shortcut.setEnabled(False)
        self._escape_shortcut.activated.connect(self._on_escape_pressed)

    def _on_text_changed(self, text: str) -> None:
        self._pending_filter = text.strip()
        self._debounce_timer.start()

    def _emit_filter(self) -> None:
        self._on_filter_applied(self._pending_filter)

    def _on_escape_pressed(self) -> None:
        self.clear()

    def _on_filter_applied(self, filter_text: str) -> None:
        if self._filter_value == filter_text:
            return

        self._filter_value = filter_text
        self._escape_shortcut.setEnabled(bool(filter_text))
        self.filter_changed.emit(filter_text)
