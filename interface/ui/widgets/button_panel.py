"""
Button panel widget module for PyQt6 interface.

This module contains the ButtonPanel class for the main application
button controls.
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
    """Panel containing main application buttons.

    This panel provides buttons for:
    - Process Directories
    - Add Folder
    - Batch Add Folders
    - Edit Settings
    - Maintenance
    - Processed Files Report
    - Exit
    """

    # Signals
    process_clicked = Signal()
    add_folder_clicked = Signal()
    batch_add_clicked = Signal()
    edit_settings_clicked = Signal()
    maintenance_clicked = Signal()
    processed_files_clicked = Signal()
    exit_clicked = Signal()

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
        self._add_folder_btn.setMinimumWidth(150)
        self._add_folder_btn.clicked.connect(self.add_folder_clicked.emit)

        # Batch Add Folders button
        self._batch_add_btn = QPushButton("Batch Add Directories...")
        self._batch_add_btn.setMinimumWidth(150)
        self._batch_add_btn.clicked.connect(self.batch_add_clicked.emit)

        # Edit Settings button
        self._settings_btn = QPushButton("Edit Settings...")
        self._settings_btn.setMinimumWidth(150)
        self._settings_btn.clicked.connect(self.edit_settings_clicked.emit)

        # Separator
        self._separator1 = QFrame()
        self._separator1.setFrameShape(QFrame.Shape.HLine)
        self._separator1.setFrameShadow(QFrame.Shadow.Sunken)

        # Processed Files button
        self._processed_files_btn = QPushButton("Processed Files Report...")
        self._processed_files_btn.setMinimumWidth(150)
        self._processed_files_btn.clicked.connect(self.processed_files_clicked.emit)

        # Separator 2
        self._separator2 = QFrame()
        self._separator2.setFrameShape(QFrame.Shape.HLine)
        self._separator2.setFrameShadow(QFrame.Shadow.Sunken)

        # Maintenance button
        self._maintenance_btn = QPushButton("Maintenance...")
        self._maintenance_btn.setMinimumWidth(150)
        self._maintenance_btn.clicked.connect(self.maintenance_clicked.emit)

        # Vertical spacer
        self._spacer = QSpacerItem(
            0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )

        # Separator 3
        self._separator3 = QFrame()
        self._separator3.setFrameShape(QFrame.Shape.HLine)
        self._separator3.setFrameShadow(QFrame.Shadow.Sunken)

        # Process button (at bottom)
        self._process_btn = QPushButton("Process All Folders")
        self._process_btn.setMinimumWidth(150)
        self._process_btn.clicked.connect(self.process_clicked.emit)

        # Exit button
        self._exit_btn = QPushButton("Exit")
        self._exit_btn.setMinimumWidth(150)
        self._exit_btn.clicked.connect(self.exit_clicked.emit)

    def _setup_layout(self) -> None:
        """Setup button layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        # Add buttons at top
        layout.addWidget(self._add_folder_btn)
        layout.addWidget(self._batch_add_btn)
        layout.addWidget(self._settings_btn)

        # Add separator
        layout.addWidget(self._separator1)

        # Add processed files button
        layout.addWidget(self._processed_files_btn)

        # Add separator
        layout.addWidget(self._separator2)

        # Add maintenance button
        layout.addWidget(self._maintenance_btn)

        # Add vertical spacer
        layout.addItem(self._spacer)

        # Add separator
        layout.addWidget(self._separator3)

        # Add process button at bottom
        layout.addWidget(self._process_btn)

        # Add exit button
        layout.addWidget(self._exit_btn)

    def set_button_enabled(self, button_name: str, enabled: bool) -> None:
        """
        Set the enabled state of a button.

        Args:
            button_name: Name of the button ('add_folder', 'batch_add',
                        'process', 'processed_files', 'maintenance',
                        'settings', 'exit').
            enabled: Whether to enable the button.
        """
        button_map = {
            "add_folder": self._add_folder_btn,
            "batch_add": self._batch_add_btn,
            "process": self._process_btn,
            "processed_files": self._processed_files_btn,
            "maintenance": self._maintenance_btn,
            "settings": self._settings_btn,
            "exit": self._exit_btn,
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
