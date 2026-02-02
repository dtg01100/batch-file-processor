"""
Button panel widget module for PyQt6 interface.

This module contains the ButtonPanel class for the main application
button controls arranged in a vertical sidebar layout.
"""

from typing import Optional

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QFrame,
    QSpacerItem,
    QSizePolicy,
)
from PyQt6.QtCore import pyqtSignal as Signal


class ButtonPanel(QWidget):
    """Vertical sidebar panel containing main application buttons.

    This panel provides buttons for:
    - Add Folder
    - Batch Add Folders
    - Set Defaults
    - Process All Folders
    - Processed Files Report
    - Maintenance
    - Edit Settings
    - Enable Resend
    """

    # Signals
    process_clicked = Signal()
    add_folder_clicked = Signal()
    batch_add_clicked = Signal()
    set_defaults_clicked = Signal()
    edit_settings_clicked = Signal()
    maintenance_clicked = Signal()
    processed_files_clicked = Signal()
    enable_resend_clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initialize the button panel.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._create_widgets()
        self._setup_layout()

    def _create_widgets(self) -> None:
        """Create button widgets."""
        # Add Folder button
        self._add_folder_btn = QPushButton("Add Directory...")
        self._add_folder_btn.setMinimumWidth(140)
        self._add_folder_btn.clicked.connect(self.add_folder_clicked.emit)

        # Batch Add Folders button
        self._batch_add_btn = QPushButton("Batch Add Directories...")
        self._batch_add_btn.setMinimumWidth(140)
        self._batch_add_btn.clicked.connect(self.batch_add_clicked.emit)

        # Separator 1
        self._separator1 = QFrame()
        self._separator1.setFrameShape(QFrame.Shape.HLine)
        self._separator1.setFrameShadow(QFrame.Shadow.Sunken)

        # Set Defaults button
        self._set_defaults_btn = QPushButton("Set Defaults...")
        self._set_defaults_btn.setMinimumWidth(140)
        self._set_defaults_btn.clicked.connect(self.set_defaults_clicked.emit)

        # Separator 2
        self._separator2 = QFrame()
        self._separator2.setFrameShape(QFrame.Shape.HLine)
        self._separator2.setFrameShadow(QFrame.Shadow.Sunken)

        # Process button
        self._process_btn = QPushButton("Process All Folders")
        self._process_btn.setMinimumWidth(140)
        self._process_btn.clicked.connect(self.process_clicked.emit)

        # Separator 3
        self._separator3 = QFrame()
        self._separator3.setFrameShape(QFrame.Shape.HLine)
        self._separator3.setFrameShadow(QFrame.Shadow.Sunken)

        # Processed Files button
        self._processed_files_btn = QPushButton("Processed Files Report...")
        self._processed_files_btn.setMinimumWidth(140)
        self._processed_files_btn.clicked.connect(self.processed_files_clicked.emit)

        # Separator 4
        self._separator4 = QFrame()
        self._separator4.setFrameShape(QFrame.Shape.HLine)
        self._separator4.setFrameShadow(QFrame.Shadow.Sunken)

        # Maintenance button
        self._maintenance_btn = QPushButton("Maintenance...")
        self._maintenance_btn.setMinimumWidth(140)
        self._maintenance_btn.clicked.connect(self.maintenance_clicked.emit)

        # Separator 5
        self._separator5 = QFrame()
        self._separator5.setFrameShape(QFrame.Shape.HLine)
        self._separator5.setFrameShadow(QFrame.Shadow.Sunken)

        # Edit Settings button
        self._settings_btn = QPushButton("Edit Settings...")
        self._settings_btn.setMinimumWidth(140)
        self._settings_btn.clicked.connect(self.edit_settings_clicked.emit)

        # Vertical spacer
        self._spacer = QSpacerItem(
            0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )

        # Separator 6
        self._separator6 = QFrame()
        self._separator6.setFrameShape(QFrame.Shape.HLine)
        self._separator6.setFrameShadow(QFrame.Shadow.Sunken)

        # Enable Resend button
        self._enable_resend_btn = QPushButton("Enable Resend")
        self._enable_resend_btn.setMinimumWidth(140)
        self._enable_resend_btn.clicked.connect(self.enable_resend_clicked.emit)

    def _setup_layout(self) -> None:
        """Setup vertical sidebar button layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)

        # Add folder buttons at top
        layout.addWidget(self._add_folder_btn)
        layout.addWidget(self._batch_add_btn)

        # Add separator
        layout.addWidget(self._separator1)

        # Add Set Defaults button
        layout.addWidget(self._set_defaults_btn)

        # Add separator
        layout.addWidget(self._separator2)

        # Add Process button
        layout.addWidget(self._process_btn)

        # Add separator
        layout.addWidget(self._separator3)

        # Add Processed Files button
        layout.addWidget(self._processed_files_btn)

        # Add separator
        layout.addWidget(self._separator4)

        # Add Maintenance button
        layout.addWidget(self._maintenance_btn)

        # Add separator
        layout.addWidget(self._separator5)

        # Add Edit Settings button
        layout.addWidget(self._settings_btn)

        # Add vertical spacer
        layout.addItem(self._spacer)

        # Add separator
        layout.addWidget(self._separator6)

        # Add Enable Resend button at bottom
        layout.addWidget(self._enable_resend_btn)

    def set_button_enabled(self, button_name: str, enabled: bool) -> None:
        """
        Set the enabled state of a button.

        Args:
            button_name: Name of the button ('add_folder', 'batch_add',
                        'set_defaults', 'process', 'processed_files',
                        'maintenance', 'settings', 'enable_resend').
            enabled: Whether to enable the button.
        """
        button_map = {
            "add_folder": self._add_folder_btn,
            "batch_add": self._batch_add_btn,
            "set_defaults": self._set_defaults_btn,
            "process": self._process_btn,
            "processed_files": self._processed_files_btn,
            "maintenance": self._maintenance_btn,
            "settings": self._settings_btn,
            "enable_resend": self._enable_resend_btn,
        }

        button = button_map.get(button_name)
        if button:
            button.setEnabled(enabled)

    def set_process_enabled(
        self, enabled: bool, has_active_folders: bool = False
    ) -> None:
        """Enable or disable the process button.

        Args:
            enabled: Whether to enable the button.
            has_active_folders: Whether there are active folders.
        """
        if enabled and has_active_folders:
            self._process_btn.setEnabled(True)
        else:
            self._process_btn.setEnabled(False)
