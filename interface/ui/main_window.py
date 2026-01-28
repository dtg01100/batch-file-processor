"""
Main window module for PyQt6 interface.

This module contains the main application window setup.
"""

from typing import TYPE_CHECKING, Optional, Dict, Any

from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QSplitter, QFrame, QLabel
from PyQt6.QtCore import pyqtSignal as Signal, Qt

if TYPE_CHECKING:
    from interface.database.database_manager import DatabaseManager
    from interface.ui.app import Application


class MainWindow(QMainWindow):
    """Main application window for Batch File Processor."""

    # Signals for communication with application
    process_directories_requested = Signal()
    add_folder_requested = Signal()
    batch_add_folders_requested = Signal()
    edit_settings_requested = Signal()
    maintenance_requested = Signal()
    processed_files_requested = Signal()
    exit_requested = Signal()
    edit_folder_requested = Signal(int)  # folder_id
    toggle_active_requested = Signal(int)  # folder_id
    delete_folder_requested = Signal(int)  # folder_id
    send_folder_requested = Signal(int)  # folder_id

    def __init__(
        self,
        db_manager: "DatabaseManager",
        app: "Application" = None,
        parent: QWidget = None,
    ):
        """
        Initialize the main window.

        Args:
            db_manager: Database manager instance.
            app: Application instance.
            parent: Parent widget.
        """
        super().__init__(parent)

        self._db_manager = db_manager
        self._app = app
        self._version = "1.0.0"

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Setup the main window UI components."""
        try:
            self.setWindowTitle("Batch File Processor")
            self.setMinimumSize(900, 600)

            # Central widget with vertical layout
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            layout = QVBoxLayout(central_widget)
            layout.setContentsMargins(5, 5, 5, 5)
            layout.setSpacing(5)

            # Button panel at top
            from interface.ui.widgets.button_panel import ButtonPanel

            self._button_panel = ButtonPanel()
            layout.addWidget(self._button_panel)

            # Add separator
            separator = QFrame()
            separator.setFrameShape(QFrame.Shape.HLine)
            separator.setFrameShadow(QFrame.Shadow.Sunken)
            layout.addWidget(separator)

            # Splitter for folder lists (active/inactive split view)
            self._folder_splitter = QSplitter(Qt.Orientation.Horizontal)
            layout.addWidget(self._folder_splitter, stretch=1)

            # Folder list widget
            from interface.ui.widgets.folder_list import FolderListWidget

            self._folder_list = FolderListWidget(
                db_manager=self._db_manager, parent=self
            )
            self._folder_splitter.addWidget(self._folder_list)

            # Set initial splitter sizes
            self._folder_splitter.setSizes([400, 400])
        except Exception as e:
            print(f"Error setting up main window UI: {str(e)}")
            # Create a basic UI to allow the app to continue running
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            layout = QVBoxLayout(central_widget)
            error_label = QLabel("Error initializing UI components")
            layout.addWidget(error_label)

    def _connect_signals(self) -> None:
        """Connect signals to slots."""
        # Connect button panel signals
        self._button_panel.process_clicked.connect(
            self.process_directories_requested.emit
        )
        self._button_panel.add_folder_clicked.connect(self.add_folder_requested.emit)
        self._button_panel.batch_add_clicked.connect(
            self.batch_add_folders_requested.emit
        )
        self._button_panel.edit_settings_clicked.connect(
            self.edit_settings_requested.emit
        )
        self._button_panel.maintenance_clicked.connect(self.maintenance_requested.emit)
        self._button_panel.processed_files_clicked.connect(
            self.processed_files_requested.emit
        )
        self._button_panel.exit_clicked.connect(self.exit_requested.emit)

        # Connect folder list signals
        self._folder_list.folder_edit_requested.connect(self.edit_folder_requested.emit)
        self._folder_list.folder_toggle_active.connect(
            self.toggle_active_requested.emit
        )
        self._folder_list.folder_delete_requested.connect(
            self.delete_folder_requested.emit
        )
        self._folder_list.folder_send_requested.connect(self.send_folder_requested.emit)

    def refresh_folder_list(self) -> None:
        """Refresh the folder list."""
        self._folder_list.refresh()

    @property
    def db_manager(self) -> "DatabaseManager":
        """Get the database manager instance."""
        return self._db_manager

    @property
    def app(self) -> "Application":
        """Get the application instance."""
        return self._app

    @property
    def version(self) -> str:
        """Get the application version."""
        return self._version


def create_main_window(
    db_manager: "DatabaseManager", app: "Application" = None, parent: QWidget = None
) -> MainWindow:
    """
    Create the main window.

    Args:
        db_manager: Database manager instance.
        app: Application instance.
        parent: Parent widget.

    Returns:
        Main window instance.
    """
    window = MainWindow(db_manager=db_manager, app=app, parent=parent)
    return window
