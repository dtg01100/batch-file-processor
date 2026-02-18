"""Loading overlay for Qt applications.

Provides a Qt-based loading overlay to replace the tkinter DoingStuffOverlay.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class QtDoingStuffOverlay:
    """Encapsulated loading overlay widget for Qt.

    Each instance manages its own overlay frame independently,
    allowing multiple overlays to coexist without global state conflicts.

    Example:
        overlay = QtDoingStuffOverlay()
        overlay.make_overlay(parent_widget, "Processing...", "Header", "Footer")
        # ... do work ...
        overlay.update_overlay(parent_widget, "Still working...", "Header", "Updated footer")
        overlay.destroy_overlay()
    """

    def __init__(self) -> None:
        self._overlay: Optional[QFrame] = None
        self._message_label: Optional[QLabel] = None
        self._header_label: Optional[QLabel] = None
        self._footer_label: Optional[QLabel] = None

    def make_overlay(
        self,
        parent: QWidget,
        overlay_text: str = "",
        header: str = "",
        footer: str = "",
        overlay_height: int = 100,
    ) -> None:
        """Create and show the overlay on the parent widget.

        Args:
            parent: Parent widget to overlay
            overlay_text: Main message text
            header: Header text (top-left)
            footer: Footer text (bottom-left)
            overlay_height: Fixed height for overlay (not used in Qt version)
        """
        # Destroy any existing overlay
        self.destroy_overlay()

        # Create overlay frame
        self._overlay = QFrame(parent)
        self._overlay.setObjectName("qt_loading_overlay")
        self._overlay.setAutoFillBackground(True)

        # Set semi-transparent background
        palette = self._overlay.palette()
        color = QColor(0, 0, 0, 160)
        palette.setColor(QPalette.ColorRole.Window, color)
        self._overlay.setPalette(palette)

        self._overlay.setFrameShape(QFrame.Shape.NoFrame)
        self._overlay.setGeometry(parent.rect())

        # Create layout
        layout = QVBoxLayout(self._overlay)
        layout.setContentsMargins(20, 20, 20, 20)

        # Create header label
        self._header_label = QLabel(header)
        self._header_label.setStyleSheet("color: white; font-size: 12pt;")
        self._header_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self._header_label)

        # Create main message label
        self._message_label = QLabel(overlay_text)
        self._message_label.setStyleSheet("color: white; font-size: 14pt; font-weight: bold;")
        self._message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        layout.addWidget(self._message_label)
        layout.addStretch()

        # Create footer label
        self._footer_label = QLabel(footer)
        self._footer_label.setStyleSheet("color: white; font-size: 12pt;")
        self._footer_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
        layout.addWidget(self._footer_label)

        self._overlay.setLayout(layout)
        self._overlay.raise_()
        self._overlay.show()

        # Process events to ensure overlay is displayed
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()

    def update_overlay(
        self,
        parent: QWidget,
        overlay_text: str = "",
        header: str = "",
        footer: str = "",
        overlay_height: Optional[int] = None,
    ) -> None:
        """Update the overlay text.

        Args:
            parent: Parent widget (not used in Qt version)
            overlay_text: New main message text
            header: New header text
            footer: New footer text
            overlay_height: New height (not used in Qt version)
        """
        if self._message_label is None or self._overlay is None:
            return

        self._message_label.setText(overlay_text)
        if self._header_label is not None:
            self._header_label.setText(header)
        if self._footer_label is not None:
            self._footer_label.setText(footer)

        # Process events to ensure update is displayed
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()

    def destroy_overlay(self) -> None:
        """Destroy the overlay."""
        if self._overlay is not None:
            self._overlay.close()
            self._overlay.deleteLater()
            self._overlay = None
            self._message_label = None
            self._header_label = None
            self._footer_label = None


# Module-level singleton for backward compatibility
_default_overlay = QtDoingStuffOverlay()


def make_overlay(
    parent: QWidget,
    overlay_text: str = "",
    header: str = "",
    footer: str = "",
    overlay_height: int = 100,
) -> None:
    """Backward-compatible module-level make_overlay."""
    _default_overlay.make_overlay(parent, overlay_text, header, footer, overlay_height)


def update_overlay(
    parent: QWidget,
    overlay_text: str = "",
    header: str = "",
    footer: str = "",
    overlay_height: Optional[int] = None,
) -> None:
    """Backward-compatible module-level update_overlay."""
    _default_overlay.update_overlay(parent, overlay_text, header, footer, overlay_height)


def destroy_overlay() -> None:
    """Backward-compatible module-level destroy_overlay."""
    _default_overlay.destroy_overlay()
