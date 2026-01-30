"""
Application Controller for PyQt6 interface.

This module wires together the UI components with the business logic operations,
matching the functionality of the original tkinter interface.
"""

import os
from typing import TYPE_CHECKING, Optional

from PyQt6.QtWidgets import QFileDialog, QMessageBox, QProgressDialog
from PyQt6.QtCore import Qt

if TYPE_CHECKING:
    from interface.database.database_manager import DatabaseManager
    from interface.ui.main_window import MainWindow
    from interface.ui.app import Application

from interface.operations.folder_operations import FolderOperations
from interface.operations.maintenance import MaintenanceOperations
from interface.operations.processing import ProcessingOrchestrator


class ApplicationController:
    """
    Application controller that wires UI to business logic.

    This class connects the MainWindow signals to the appropriate operations,
    matching the behavior of the original tkinter interface.
    """

    def __init__(
        self,
        main_window: "MainWindow",
        db_manager: "DatabaseManager",
        app: "Application",
        database_path: str,
        args,
        version: str,
    ):
        """
        Initialize the application controller.

        Args:
            main_window: The main window instance
            db_manager: Database manager instance
            app: Application instance
            database_path: Path to database file
            args: Command-line arguments
            version: Application version string
        """
        self._main_window = main_window
        self._db_manager = db_manager
        self._app = app
        self._database_path = database_path
        self._args = args
        self._version = version

        # Initialize operation handlers
        self._folder_ops = FolderOperations(db_manager)
        self._maintenance_ops = MaintenanceOperations(db_manager)
        self._processing_orchestrator = ProcessingOrchestrator(
            db_manager, database_path, args, version
        )

        # Connect signals
        self._connect_signals()

        # Update button states
        self._update_button_states()

    def _connect_signals(self) -> None:
        """Connect main window signals to handlers."""
        # Button panel signals
        self._main_window.process_directories_requested.connect(
            self._handle_process_directories
        )
        self._main_window.add_folder_requested.connect(self._handle_add_folder)
        self._main_window.batch_add_folders_requested.connect(
            self._handle_batch_add_folders
        )
        self._main_window.edit_settings_requested.connect(self._handle_edit_settings)
        self._main_window.maintenance_requested.connect(self._handle_maintenance)
        self._main_window.processed_files_requested.connect(
            self._handle_processed_files
        )
        self._main_window.exit_requested.connect(self._handle_exit)

        # Folder operation signals
        self._main_window.edit_folder_requested.connect(self._handle_edit_folder)
        self._main_window.toggle_active_requested.connect(self._handle_toggle_active)
        self._main_window.delete_folder_requested.connect(self._handle_delete_folder)
        self._main_window.send_folder_requested.connect(self._handle_send_single)

    def _update_button_states(self) -> None:
        """Update button enabled states based on database state."""
        # Enable/disable process button based on active folders
        has_folders = self._folder_ops.get_folder_count() > 0
        has_active = self._folder_ops.get_folder_count(active_only=True) > 0

        # Update process button state
        if hasattr(self._main_window, "_button_panel"):
            self._main_window._button_panel.set_process_enabled(
                enabled=has_folders, has_active_folders=has_active
            )

    def _handle_add_folder(self) -> None:
        """Handle add folder request."""
        # Get prior folder from settings
        if self._db_manager.oversight_and_defaults is None:
            initial_dir = os.path.expanduser("~")
        else:
            prior_folder = self._db_manager.oversight_and_defaults.find_one(id=1)
            initial_dir = (
                prior_folder.get("single_add_folder_prior", os.path.expanduser("~"))
                if prior_folder
                else os.path.expanduser("~")
            )

        if not os.path.exists(initial_dir):
            initial_dir = os.path.expanduser("~")

        # Show folder selection dialog
        folder_path = QFileDialog.getExistingDirectory(
            self._main_window, "Select Folder", initial_dir
        )

        if not folder_path:
            return

        # Update prior folder setting
        if self._db_manager.oversight_and_defaults is not None:
            self._db_manager.oversight_and_defaults.update(
                {"id": 1, "single_add_folder_prior": folder_path}, ["id"]
            )

        # Check if folder already exists
        existing = self._folder_ops.check_folder_exists(folder_path)

        if existing["truefalse"]:
            # Offer to edit existing folder
            reply = QMessageBox.question(
                self._main_window,
                "Folder Exists",
                "Folder already known, would you like to edit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                folder_id = existing["matched_folder"]["id"]
                self._handle_edit_folder(folder_id)
        else:
            # Add new folder
            folder_id = self._folder_ops.add_folder(folder_path)

            # Ask if user wants to mark files as processed
            reply = QMessageBox.question(
                self._main_window,
                "Mark Files",
                "Do you want to mark files in folder as processed?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes and folder_id:
                self._maintenance_ops.mark_all_as_processed(folder_id)

            # Refresh folder list
            self._main_window.refresh_folder_list()
            self._update_button_states()

    def _handle_batch_add_folders(self) -> None:
        """Handle batch add folders request."""
        # Get prior folder from settings
        if self._db_manager.oversight_and_defaults is None:
            initial_dir = os.path.expanduser("~")
        else:
            prior_folder = self._db_manager.oversight_and_defaults.find_one(id=1)
            initial_dir = (
                prior_folder.get("batch_add_folder_prior", os.path.expanduser("~"))
                if prior_folder
                else os.path.expanduser("~")
            )

        if not os.path.exists(initial_dir):
            initial_dir = os.path.expanduser("~")

        # Show folder selection dialog
        parent_folder = QFileDialog.getExistingDirectory(
            self._main_window, "Select Parent Folder", initial_dir
        )

        if not parent_folder:
            return

        # Update prior folder setting
        if self._db_manager.oversight_and_defaults is not None:
            self._db_manager.oversight_and_defaults.update(
                {"id": 1, "batch_add_folder_prior": parent_folder}, ["id"]
            )

        # Get subdirectories
        folders_to_add = [
            os.path.join(parent_folder, folder)
            for folder in os.listdir(parent_folder)
            if os.path.isdir(os.path.join(parent_folder, folder))
        ]

        if not folders_to_add:
            QMessageBox.information(
                self._main_window,
                "No Folders",
                "No subdirectories found in selected folder.",
            )
            return

        # Confirm batch add
        reply = QMessageBox.question(
            self._main_window,
            "Confirm Batch Add",
            f"This will add {len(folders_to_add)} directories. Are you sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Add folders with progress dialog
        progress = QProgressDialog(
            "Adding folders...", "Cancel", 0, len(folders_to_add), self._main_window
        )
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setWindowTitle("Batch Add Folders")

        added_ids, added_count, skipped_count = self._folder_ops.batch_add_folders(
            folders_to_add
        )

        progress.close()

        # Show results
        QMessageBox.information(
            self._main_window,
            "Batch Add Complete",
            f"{added_count} folders added, {skipped_count} folders skipped.",
        )

        # Refresh folder list
        self._main_window.refresh_folder_list()
        self._update_button_states()

    def _handle_edit_folder(self, folder_id: int) -> None:
        """Handle edit folder request."""
        from interface.ui.dialogs.edit_folder_dialog import EditFolderDialog

        folder = self._folder_ops.get_folder(folder_id)
        if not folder:
            QMessageBox.warning(self._main_window, "Error", "Folder not found.")
            return

        dialog = EditFolderDialog(
            parent=self._main_window, folder_data=folder, db_manager=self._db_manager
        )
        if dialog.exec():
            # Refresh folder list
            self._main_window.refresh_folder_list()
            self._update_button_states()

    def _handle_edit_settings(self) -> None:
        """Handle edit settings request."""
        from interface.ui.dialogs.edit_settings_dialog import EditSettingsDialog

        settings = None
        if self._db_manager.oversight_and_defaults is not None:
            settings = self._db_manager.oversight_and_defaults.find_one(id=1)
        dialog = EditSettingsDialog(
            parent=self._main_window, oversight=settings, db_manager=self._db_manager
        )

        if dialog.exec():
            # Settings were updated
            pass

    def _handle_toggle_active(self, folder_id: int) -> None:
        """Handle toggle folder active state."""
        folder = self._folder_ops.get_folder(folder_id)
        if not folder:
            return

        # Toggle active state
        current_state = folder.get("folder_is_active", "False")
        new_state = "False" if current_state == "True" else "True"

        folder["folder_is_active"] = new_state
        self._folder_ops.update_folder(folder_id, folder)

        # Refresh folder list
        self._main_window.refresh_folder_list()
        self._update_button_states()

    def _handle_delete_folder(self, folder_id: int) -> None:
        """Handle delete folder request."""
        self._folder_ops.delete_folder(folder_id)

        # Refresh folder list
        self._main_window.refresh_folder_list()
        self._update_button_states()

    def _handle_send_single(self, folder_id: int) -> None:
        """Handle send single folder request."""
        if self._db_manager.session_database is None:
            return

        # Create temporary session database with single folder
        try:
            single_table = self._db_manager.session_database["single_table"]
            single_table.drop()
        except:
            pass

        single_table = self._db_manager.session_database["single_table"]
        folder_dict = self._folder_ops.get_folder(folder_id)
        if not folder_dict:
            return

        folder_dict["old_id"] = folder_dict.pop("id")
        single_table.insert(folder_dict)

        # Process this single folder
        self._process_folders_with_progress(single_table)

        single_table.drop()

    def _handle_process_directories(self) -> None:
        """Handle process all directories request."""
        # Check if folders are missing
        missing_folder = False
        for folder in self._folder_ops.get_active_folders():
            if not os.path.exists(folder["folder_name"]):
                missing_folder = True
                break

        if missing_folder:
            QMessageBox.critical(
                self._main_window, "Error", "One or more expected folders are missing."
            )
            return

        active_count = self._folder_ops.get_folder_count(active_only=True)
        if active_count == 0:
            QMessageBox.critical(self._main_window, "Error", "No Active Folders")
            return

        # Process all active folders
        self._process_folders_with_progress(self._db_manager.folders_table)

    def _process_folders_with_progress(self, folders_table) -> None:
        """Process folders with progress dialog."""
        progress = QProgressDialog(
            "Processing folders...", None, 0, 0, self._main_window
        )
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setWindowTitle("Processing")
        progress.setCancelButton(None)
        progress.show()

        # Process directories
        result = self._processing_orchestrator.process_all(auto_mode=False)

        progress.close()

        if not result.success:
            QMessageBox.critical(
                self._main_window,
                "Processing Error",
                f"Processing failed: {result.error}",
            )
        elif result.error:
            QMessageBox.information(
                self._main_window, "Run Status", "Run completed with errors."
            )

        # Refresh folder list
        self._main_window.refresh_folder_list()
        self._update_button_states()

    def _handle_maintenance(self) -> None:
        """Handle maintenance request."""
        from interface.ui.dialogs.maintenance_dialog import MaintenanceDialog

        # Warn user
        reply = QMessageBox.question(
            self._main_window,
            "Warning",
            "Maintenance window is for advanced users only, potential for data loss if "
            "incorrectly used. Are you sure you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Create backup
        import backup_increment

        backup_increment.do_backup(self._database_path)

        # Show maintenance dialog
        dialog = MaintenanceDialog(
            parent=self._main_window,
            db_manager=self._db_manager,
            running_platform="Linux",  # Could get from args
        )

        if dialog.exec():
            # Refresh folder list if changes were made
            self._main_window.refresh_folder_list()
            self._update_button_states()

    def _handle_processed_files(self) -> None:
        """Handle processed files report request."""
        from interface.ui.dialogs.processed_files_dialog import ProcessedFilesDialog

        dialog = ProcessedFilesDialog(
            parent=self._main_window, db_manager=self._db_manager
        )
        dialog.exec()

    def _handle_exit(self) -> None:
        """Handle exit request."""
        self._main_window.close()
