"""
PyQt6 Application module for Batch File Processor.

This module contains the PyQt6-based Application class.
"""

import sys
from typing import TYPE_CHECKING, Optional

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal as Signal

if TYPE_CHECKING:
    from interface.database.database_manager import DatabaseManager


class ApplicationSignals(QObject):
    """Application-wide signals for communication."""
    
    # Database signals
    database_changed = Signal()
    
    # Folder signals
    folder_added = Signal(int)           # folder_id
    folder_updated = Signal(int)         # folder_id
    folder_deleted = Signal(int)         # folder_id
    folder_toggled = Signal(int, bool)   # folder_id, is_active
    
    # Processing signals
    processing_started = Signal()
    processing_finished = Signal()
    processing_error = Signal(str)       # error_message
    processing_progress = Signal(int, int)  # current, total
    
    # Dialog signals
    dialog_opened = Signal(str)          # dialog_name
    dialog_closed = Signal(str, bool)    # dialog_name, accepted


class Application(QApplication):
    """Main application class for the batch file processor."""
    
    def __init__(self, argv: list):
        """
        Initialize the application.
        
        Args:
            argv: Command-line arguments.
        """
        super().__init__(argv)
        
        self.setApplicationName("Batch File Processor")
        self.setApplicationVersion("1.0.0")
        self.setOrganizationName("BatchFileProcessor")
        
        # Application-wide signals
        self.signals = ApplicationSignals()
        
        # Database manager reference
        self._database_manager: Optional["DatabaseManager"] = None
        
        # Load stylesheet
        self._load_stylesheet()
    
    def _load_stylesheet(self) -> None:
        """Load and apply the QSS stylesheet."""
        try:
            from interface.styles import load_stylesheet
            stylesheet = load_stylesheet()
            if stylesheet:
                self.setStyleSheet(stylesheet)
        except Exception as e:
            # Fallback to default styling if QSS file not found
            print(f"Warning: Could not load stylesheet: {str(e)}")
            pass
    
    @property
    def database_manager(self) -> Optional["DatabaseManager"]:
        """Get the database manager instance."""
        return self._database_manager
    
    @database_manager.setter
    def database_manager(self, manager: "DatabaseManager") -> None:
        """Set the database manager instance."""
        self._database_manager = manager
    
    def exec(self) -> int:
        """Override exec to return exit code."""
        return super().exec()


def create_application(argv: list) -> Application:
    """
    Create and configure the application instance.
    
    Args:
        argv: Command-line arguments.
        
    Returns:
        Configured Application instance.
    """
    app = Application(argv)
    return app
