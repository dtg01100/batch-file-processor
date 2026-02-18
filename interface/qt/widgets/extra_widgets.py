"""Qt equivalents of extra widgets from tk_extra_widgets.py.

Provides Qt-based implementations of:
- RightClickMenu: Context menu for QLineEdit widgets
- VerticalScrolledFrame: Scrollable frame widget
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QFrame,
    QMenu,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class RightClickMenu:
    """Context menu for QLineEdit widgets.

    Provides standard edit operations (Cut, Copy, Paste, Delete, Select All)
    via right-click context menu and keyboard shortcuts.

    Usage:
        entry = QLineEdit()
        rclick_menu = RightClickMenu(entry)
        # Context menu is automatically enabled

    Attributes:
        parent: The QLineEdit widget this menu is attached to
    """

    def __init__(self, parent: QWidget) -> None:
        self.parent = parent

        # Install event filter to intercept right-click
        self.parent.installEventFilter(self)

        # Set up keyboard shortcuts
        self._setup_shortcuts()

    def _setup_shortcuts(self) -> None:
        """Set up keyboard shortcuts for edit operations."""
        # Ctrl+A for Select All
        select_all_shortcut = QShortcut(QKeySequence.StandardKey.SelectAll, self.parent)
        select_all_shortcut.activated.connect(self._select_all)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        """Filter events to handle right-click context menu."""
        from PyQt6.QtCore import QEvent
        from PyQt6.QtGui import QContextMenuEvent

        if event.type() == QEvent.Type.ContextMenu:
            ce = QContextMenuEvent(event)
            self._show_menu(ce.globalPos())
            return True

        return False

    def _show_menu(self, pos) -> None:
        """Show the context menu at the specified position."""
        # Check if widget is disabled
        if not self.parent.isEnabled():
            return

        menu = QMenu(self.parent)

        # Check for selected text
        has_selection = self.parent.hasSelectedText()

        # Cut
        cut_action = menu.addAction("Cut")
        cut_action.setEnabled(has_selection)
        cut_action.triggered.connect(lambda: self.parent.cut())

        # Copy
        copy_action = menu.addAction("Copy")
        copy_action.setEnabled(has_selection)
        copy_action.triggered.connect(lambda: self.parent.copy())

        menu.addSeparator()

        # Paste
        paste_action = menu.addAction("Paste")
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        paste_action.setEnabled(bool(clipboard.text()))
        paste_action.triggered.connect(lambda: self.parent.paste())

        menu.addSeparator()

        # Delete
        delete_action = menu.addAction("Delete")
        delete_action.setEnabled(has_selection)
        delete_action.triggered.connect(lambda: self.parent.del_())

        menu.addSeparator()

        # Select All
        select_all_action = menu.addAction("Select All")
        select_all_action.triggered.connect(self._select_all)

        menu.exec(pos)

    def _select_all(self) -> None:
        """Select all text in the widget."""
        self.parent.selectAll()


class VerticalScrolledFrame(QScrollArea):
    """A Qt scrollable frame that works like Tkinter's VerticalScrolledFrame.

    * Use the :attr:`interior` attribute to place widgets inside the scrollable frame
    * Construct and use like a normal Qt widget
    * Only allows vertical scrolling

    Example:
        scrolled_frame = VerticalScrolledFrame(parent)
        scrolled_frame.pack(fill=BOTH, expand=True)

        # Add widgets to the interior
        label = QLabel("Content")
        scrolled_frame.interior.layout().addWidget(label)
    """

    def __init__(self, parent: Optional[QWidget] = None, *args, **kwargs) -> None:
        super().__init__(parent, *args, **kwargs)

        # Configure scroll area
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Create interior frame
        self._interior = QWidget()
        self._interior_layout = QVBoxLayout(self._interior)
        self._interior_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Set the interior widget
        self.setWidget(self._interior)

    @property
    def interior(self) -> QWidget:
        """Get the interior widget for adding child widgets."""
        return self._interior

    @property
    def interior_layout(self) -> QVBoxLayout:
        """Get the layout of the interior widget."""
        return self._interior_layout

    def pack(self, fill=None, expand=False, **kwargs) -> None:
        """Compatibility method for Tkinter-style packing.

        In Qt, this is a no-op as layout is managed by the parent.
        """
        pass
