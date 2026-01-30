"""
Maintenance dialog module for PyQt6 interface.

This module contains the MaintenanceDialog implementation.
A dialog providing maintenance functions for the application.
"""

from typing import TYPE_CHECKING, Dict, Any, Optional
import os

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QLabel,
    QPushButton,
    QMessageBox,
    QFrame,
)
from PyQt6.QtCore import Qt

if TYPE_CHECKING:
    from interface.database.database_manager import DatabaseManager


class MaintenanceDialog(QDialog):
    """Dialog for maintenance functions."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        db_manager: Optional["DatabaseManager"] = None,
        running_platform: str = "Linux",
    ):
        """
        Initialize the maintenance dialog.

        Args:
            parent: Parent window.
            db_manager: Database manager instance.
            running_platform: Current operating system platform.
        """
        super().__init__(parent)

        self.db_manager = db_manager
        self.running_platform = running_platform

        self.setWindowTitle("Maintenance Functions")
        self.setModal(True)
        self.resize(400, 500)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)

        # Warning label
        warning = QLabel("WARNING:\\nFOR\\nADVANCED\\nUSERS\\nONLY!")
        warning.setStyleSheet("color: red; font-weight: bold;")
        warning.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(warning)

        # Button frame
        button_frame = QWidget()
        button_layout = QVBoxLayout(button_frame)
        layout.addWidget(button_frame)

        # Create buttons
        self._create_buttons(button_layout)

    def _create_buttons(self, layout: QVBoxLayout) -> None:
        """Create maintenance operation buttons."""
        # Set all active button
        set_all_active_btn = QPushButton(
            "Move all to active (Skips Settings Validation)"
        )
        set_all_active_btn.clicked.connect(self._on_set_all_active)
        layout.addWidget(set_all_active_btn)

        # Set all inactive button
        set_all_inactive_btn = QPushButton("Move all to inactive")
        set_all_inactive_btn.clicked.connect(self._on_set_all_inactive)
        layout.addWidget(set_all_inactive_btn)

        # Clear resend flags button
        clear_resend_btn = QPushButton("Clear all resend flags")
        clear_resend_btn.clicked.connect(self._on_clear_resend_flags)
        layout.addWidget(clear_resend_btn)

        # Clear emails queue button
        clear_emails_btn = QPushButton("Clear queued emails")
        clear_emails_btn.clicked.connect(self._on_clear_emails_queue)
        layout.addWidget(clear_emails_btn)

        # Mark active as processed button
        mark_processed_btn = QPushButton("Mark all in active as processed")
        mark_processed_btn.clicked.connect(self._on_mark_active_as_processed)
        layout.addWidget(mark_processed_btn)

        # Remove inactive button
        remove_inactive_btn = QPushButton("Remove all inactive configurations")
        remove_inactive_btn.clicked.connect(self._on_remove_inactive)
        layout.addWidget(remove_inactive_btn)

        # Clear processed files button
        clear_files_btn = QPushButton("Clear sent file records")
        clear_files_btn.clicked.connect(self._on_clear_processed_files)
        layout.addWidget(clear_files_btn)

        # Import button
        import_btn = QPushButton("Import old configurations...")
        import_btn.clicked.connect(self._on_import_configurations)
        layout.addWidget(import_btn)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _on_set_all_active(self) -> None:
        """Set all folders to active state."""
        if self.db_manager is None or self.db_manager.database_connection is None:
            return

        reply = QMessageBox.question(
            self,
            "Confirm",
            "Are you sure you want to set all folders to active?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db_manager.database_connection.query(
                    'UPDATE folders SET folder_is_active="True" WHERE folder_is_active="False"'
                )
                QMessageBox.information(self, "Success", "All folders set to active.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error: {str(e)}")

    def _on_set_all_inactive(self) -> None:
        """Set all folders to inactive state."""
        if self.db_manager is None or self.db_manager.database_connection is None:
            return

        reply = QMessageBox.question(
            self,
            "Confirm",
            "Are you sure you want to set all folders to inactive?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db_manager.database_connection.query(
                    'UPDATE folders SET folder_is_active="False" WHERE folder_is_active="True"'
                )
                QMessageBox.information(self, "Success", "All folders set to inactive.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error: {str(e)}")

    def _on_clear_resend_flags(self) -> None:
        """Clear all resend flags."""
        if self.db_manager is None or self.db_manager.database_connection is None:
            return

        reply = QMessageBox.question(
            self,
            "Confirm",
            "Are you sure you want to clear all resend flags?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db_manager.database_connection.query(
                    "UPDATE processed_files SET resend_flag=0 WHERE resend_flag=1"
                )
                QMessageBox.information(self, "Success", "Resend flags cleared.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error: {str(e)}")

    def _on_clear_emails_queue(self) -> None:
        """Clear the emails queue."""
        if self.db_manager is None or self.db_manager.emails_table is None:
            return

        reply = QMessageBox.question(
            self,
            "Confirm",
            "Are you sure you want to clear the emails queue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db_manager.emails_table.delete()
                QMessageBox.information(self, "Success", "Emails queue cleared.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error: {str(e)}")

    def _on_mark_active_as_processed(self) -> None:
        """Mark all active folders as processed."""
        if self.db_manager is None:
            return

        reply = QMessageBox.question(
            self,
            "Confirm",
            "Are you sure you want to mark all active folders as processed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                from interface.operations.maintenance import MaintenanceOperations

                ops = MaintenanceOperations(self.db_manager)
                ops.mark_all_as_processed()
                QMessageBox.information(
                    self, "Success", "Active folders marked as processed."
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error: {str(e)}")

    def _on_remove_inactive(self) -> None:
        """Remove all inactive folder configurations."""
        if (
            self.db_manager is None
            or self.db_manager.folders_table is None
            or self.db_manager.processed_files is None
            or self.db_manager.emails_table is None
        ):
            return

        reply = QMessageBox.question(
            self,
            "Confirm",
            "Are you sure you want to remove all inactive folder configurations?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                count = 0
                for folder in self.db_manager.folders_table.find(
                    folder_is_active="False"
                ):
                    self.db_manager.folders_table.delete(id=folder["id"])
                    self.db_manager.processed_files.delete(folder_id=folder["id"])
                    self.db_manager.emails_table.delete(folder_id=folder["id"])
                    count += 1

                QMessageBox.information(
                    self, "Success", f"Removed {count} inactive folder configurations."
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error: {str(e)}")

    def _on_clear_processed_files(self) -> None:
        """Clear all processed file records."""
        if self.db_manager is None or self.db_manager.processed_files is None:
            return

        reply = QMessageBox.question(
            self,
            "Confirm",
            "This will clear all records of sent files.\\nAre you sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db_manager.processed_files.delete()
                QMessageBox.information(
                    self, "Success", "Processed file records cleared."
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error: {str(e)}")

    def _on_import_configurations(self) -> None:
        """Import old configurations from backup."""
        if self.db_manager is None:
            return

        from PyQt6.QtWidgets import QFileDialog
        from interface.main import DATABASE_VERSION
        import os

        backup_file, _ = QFileDialog.getOpenFileName(
            self,
            "Select Backup File",
            os.path.expanduser("~"),
            "SQLite DB (*.db);;All Files (*.*)",
        )

        if backup_file:
            try:
                import database_import

                db_path = getattr(self.db_manager, "_database_path", "")
                if database_import.import_interface(
                    self,
                    db_path,
                    self.running_platform,
                    backup_file,
                    DATABASE_VERSION,
                ):
                    if hasattr(self.db_manager, "reload"):
                        self.db_manager.reload()
                    QMessageBox.information(
                        self, "Success", "Configurations imported successfully."
                    )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Import error: {str(e)}")
