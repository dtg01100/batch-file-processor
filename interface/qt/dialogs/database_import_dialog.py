"""Qt-based database import dialog.

Replaces the tkinter-based database_import.py with a Qt implementation.
"""

from __future__ import annotations

import os
import threading
from typing import Any, Optional, cast

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from interface.qt.dialogs.base_dialog import BaseDialog
from interface.qt.theme import Theme

from interface.database import sqlite_wrapper
from core.utils.bool_utils import normalize_bool

import backup_increment
import folders_database_migrator


class DatabaseImportDialog(BaseDialog):
    """Dialog for importing folders from another database."""

    def __init__(
        self,
        parent: QWidget,
        original_database_path: str,
        running_platform: str,
        backup_path: str,
        current_db_version: str,
        preselected_database_path: Optional[str] = None,
    ) -> None:
        super().__init__(parent, "folders.db merging utility", action_mode="none")

        self._original_database_path = original_database_path
        self._running_platform = running_platform
        self._backup_path = backup_path
        self._current_db_version = current_db_version
        self._new_database_path: Optional[str] = None
        self._database_migrate_job: Optional[DbMigrationJob] = None

        self._setup_ui()
        if preselected_database_path:
            self._apply_selected_database_path(preselected_database_path)

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        main_layout = self._body_layout
        main_layout.setContentsMargins(
            Theme.SPACING_MD_INT,
            Theme.SPACING_MD_INT,
            Theme.SPACING_MD_INT,
            Theme.SPACING_MD_INT,
        )
        main_layout.setSpacing(Theme.SPACING_MD_INT)

        # Database file selection frame
        db_file_frame = QFrame()
        db_file_layout = QVBoxLayout(db_file_frame)
        db_file_layout.setContentsMargins(0, 0, 0, 0)

        self._select_button = QPushButton("Select &New Database File")
        self._select_button.clicked.connect(self._select_database)
        self._select_button.setAccessibleName("Select new database file")
        self._select_button.setAccessibleDescription(
            "Choose a database file to import active folder settings from"
        )
        db_file_layout.addWidget(self._select_button)

        self._db_label = QLabel("No File Selected")
        self._db_label.setFrameShape(QFrame.Shape.Box)
        self._db_label.setFrameShadow(QFrame.Shadow.Sunken)
        self._db_label.setAccessibleName("Selected database file")
        self._db_label.setAccessibleDescription(
            "Displays the currently selected database file path"
        )
        db_file_layout.addWidget(self._db_label)

        main_layout.addWidget(db_file_frame)

        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        self._progress_bar.setAccessibleName("Import progress")
        self._progress_bar.setAccessibleDescription(
            "Shows progress of active folders import"
        )
        main_layout.addWidget(self._progress_bar)

        # Button frame
        button_frame = QFrame()
        button_layout = QHBoxLayout(button_frame)
        button_layout.setContentsMargins(0, 0, 0, 0)

        self._import_button = QPushButton("&Import Active Folders")
        self._import_button.setEnabled(False)
        self._import_button.clicked.connect(self._start_import)
        self._import_button.setAccessibleName("Import active folders")
        self._import_button.setAccessibleDescription(
            "Start importing active folders from selected database"
        )
        button_layout.addWidget(self._import_button)

        button_layout.addStretch()

        self._close_button = QPushButton("&Close")
        self._close_button.clicked.connect(self.reject)
        self._close_button.setAccessibleName("Close database import dialog")
        self._close_button.setAccessibleDescription("Close this dialog")
        button_layout.addWidget(self._close_button)

        main_layout.addWidget(button_frame)

        # Set minimum size
        self.setMinimumSize(600, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

    def _select_database(self) -> None:
        """Handle database file selection."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Database File",
            os.path.expanduser("~"),
            "Database Files (*.db);;All Files (*)",
        )

        if file_path:
            self._apply_selected_database_path(file_path)

    def _apply_selected_database_path(self, file_path: str) -> None:
        """Apply a selected database path to dialog state and UI."""
        self._new_database_path = file_path
        self._db_label.setText(file_path)
        self._import_button.setEnabled(True)
        self._database_migrate_job = DbMigrationJob(
            self._original_database_path, file_path
        )

    def _start_import(self) -> None:
        """Start the import process."""
        if self._new_database_path is None or self._database_migrate_job is None:
            return

        # Disable buttons during import
        self._import_button.setEnabled(False)
        self._select_button.setEnabled(False)
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, 0)  # Indeterminate mode

        # Run import in background thread
        self._import_thread = ImportThread(
            self._database_migrate_job,
            self._new_database_path,
            self._original_database_path,
            self._running_platform,
            self._current_db_version,
            self._backup_path,
        )
        self._import_thread.progress.connect(self._on_progress)
        self._import_thread.finished.connect(self._on_finished)
        self._import_thread.error.connect(self._on_error)
        self._import_thread.confirm_required.connect(self._on_confirm_required)
        self._import_thread.start()

    def _on_progress(self, value: int, maximum: int, message: str) -> None:
        """Update progress bar."""
        self._progress_bar.setRange(0, maximum)
        self._progress_bar.setValue(value)

    def _on_finished(self, success: bool, message: str) -> None:
        """Handle import completion."""
        self._progress_bar.setRange(0, 1)
        self._progress_bar.setValue(1 if success else 0)

        if success:
            self._db_label.setText("Import Completed")
            self.show_info("Import Complete", message)
        else:
            self.show_error("Import Failed", message)

        # Re-enable buttons
        self._import_button.setEnabled(True)
        self._select_button.setEnabled(True)

    def _on_error(self, error_message: str) -> None:
        """Handle import error."""
        self._progress_bar.setRange(0, 1)
        self._progress_bar.setValue(0)
        self._db_label.setText("Import failed.")
        self.show_error("Import Error", error_message)
        self._import_button.setEnabled(True)
        self._select_button.setEnabled(True)

    def _on_confirm_required(
        self, title: str, message: str, result_event: threading.Event
    ) -> None:
        """Handle confirmation request from background thread."""
        # Store result in the thread's result container via the event's dict
        setattr(result_event, "result", self.confirm_yes_no(title, message))
        result_event.set()


class ImportThread(QThread):
    """Background thread for database import."""

    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(bool, str)
    error = pyqtSignal(str)
    confirm_required = pyqtSignal(str, str, object)  # title, message, result_event

    def __init__(
        self,
        migrate_job: DbMigrationJob,
        new_db_path: str,
        original_db_path: str,
        platform: str,
        db_version: str,
        backup_path: str,
    ) -> None:
        super().__init__()
        self._migrate_job = migrate_job
        self._new_db_path = new_db_path
        self._original_db_path = original_db_path
        self._platform = platform
        self._db_version = db_version
        self._backup_path = backup_path

    def _confirm(self, title: str, message: str) -> bool:
        """Request confirmation from main thread using signals/slots."""
        # Support direct run() calls in tests where this QThread is not started.
        if QThread.currentThread() == self.thread():
            reply = QMessageBox.question(
                None,
                title,
                message,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            return reply == QMessageBox.StandardButton.Yes

        result_event = threading.Event()
        setattr(result_event, "result", False)

        # Emit signal to main thread - handler will set result_event.result and call result_event.set()
        self.confirm_required.emit(title, message, result_event)

        # Wait for result
        if not result_event.wait(timeout=300):
            return False
        return bool(getattr(result_event, "result", False))

    def run(self) -> None:
        """Run the import process."""
        try:
            # Validate database version
            new_db_connection = sqlite_wrapper.Database.connect(self._new_db_path)
            new_db_version_table = new_db_connection["version"]
            new_db_version_dict = cast(Optional[dict[str, Any]], new_db_version_table.find_one(id=1))
            if new_db_version_dict is None:
                raise KeyError("version")
            new_db_version = new_db_version_dict["version"]

            # Check version compatibility
            if int(new_db_version) < 14:
                if not self._confirm(
                    "Version Warning",
                    "Database versions below 14 do not contain operating system "
                    "information.\nFolder paths are not portable between operating "
                    "systems.\nThere is no guarantee that the imported folders will "
                    "work. Continue?",
                ):
                    self.finished.emit(False, "Import cancelled by user")
                    return

            elif int(new_db_version) > int(self._db_version):
                if not self._confirm(
                    "Version Warning",
                    "The proposed database version is newer than the version "
                    "supported by this program.\nContinue?",
                ):
                    self.finished.emit(False, "Import cancelled by user")
                    return

                if not self._confirm(
                    "Compatibility Warning",
                    "THIS WILL RESULT IN UNDEFINED BEHAVIOR, ARE YOU SURE YOU WANT "
                    "TO CONTINUE?\nBackup is stored at: " + self._backup_path,
                ):
                    self.finished.emit(False, "Import cancelled by user")
                    return

            elif new_db_version_dict.get("os") != self._platform:
                if not self._confirm(
                    "Platform Warning",
                    "The operating system specified in the configuration does "
                    "not match the currently running operating system.\n"
                    "There is no guarantee that the imported folders will work. "
                    "Continue?",
                ):
                    self.finished.emit(False, "Import cancelled by user")
                    return

            # Run the migration
            self._migrate_job.do_migrate(
                self, self._new_db_path, self._original_db_path
            )

            self.finished.emit(True, "Import completed successfully")

        except FileNotFoundError as e:
            self.error.emit(f"Database file not found: {e}")
        except PermissionError as e:
            self.error.emit(f"Permission denied accessing database: {e}")
        except KeyError as e:
            self.error.emit(f"Database schema error (missing field): {e}")
        except ValueError as e:
            self.error.emit(f"Invalid data in database: {e}")
        except Exception as e:
            self.error.emit(f"Import failed: {type(e).__name__}: {e}")


class DbMigrationJob:
    """Database migration job."""

    def __init__(self, original_folder_path: str, new_folder_path: str) -> None:
        self.original_folder_path = original_folder_path
        self.new_folder_path = new_folder_path

    def do_migrate(
        self,
        thread: ImportThread,
        new_database_path: str,
        original_database_path: str,
    ) -> None:
        """Perform the database migration."""
        # Pre-import operations
        original_db = sqlite_wrapper.Database.connect(original_database_path)
        backup_increment.do_backup(self.original_folder_path)
        modified_new_path = backup_increment.do_backup(self.new_folder_path)

        original_db_version = original_db["version"]
        original_db_version_dict = cast(Optional[dict[str, Any]], original_db_version.find_one(id=1))
        if original_db_version_dict is None:
            raise KeyError("version")

        new_db = sqlite_wrapper.Database.connect(modified_new_path)
        new_db_version = new_db["version"]
        new_db_version_dict = cast(Optional[dict[str, Any]], new_db_version.find_one(id=1))
        if new_db_version_dict is None:
            raise KeyError("version")

        if int(new_db_version_dict["version"]) < int(
            original_db_version_dict["version"]
        ):
            folders_database_migrator.upgrade_database(new_db, None, "Null")

        # Get active folders
        new_folders = new_db["folders"]
        target_folders = original_db["folders"]

        # Count folders for progress
        active_new_folders = [
            folder
            for folder in new_folders.find()
            if normalize_bool(folder.get("folder_is_active"))
        ]

        total_folders = len(active_new_folders)
        thread.progress.emit(0, total_folders, "Migrating folders...")

        # Migrate folders
        for i, folder in enumerate(active_new_folders):
            if not isinstance(folder, dict):
                continue
            self._migrate_folder(folder, target_folders, original_db)
            thread.progress.emit(
                i + 1, total_folders, f"Migrated {i + 1}/{total_folders} folders"
            )

        # Preserve global settings from imported database where columns overlap.
        self._migrate_settings(new_db, original_db)

    def _migrate_settings(self, source_db: Any, target_db: Any) -> None:
        """Migrate settings row from source DB into target DB (column intersection)."""
        source_settings = source_db["settings"]
        target_settings = target_db["settings"]

        source_row = source_settings.find_one(id=1)
        target_row = target_settings.find_one(id=1)
        if not isinstance(source_row, dict) or not isinstance(target_row, dict):
            return

        cursor = target_db.raw_connection.cursor()
        cursor.execute("PRAGMA table_info(settings)")
        target_columns = {row[1] for row in cursor.fetchall()}

        payload = {
            key: value
            for key, value in source_row.items()
            if key in target_columns and key != "id"
        }
        if not payload:
            return

        payload["id"] = target_row["id"]
        target_settings.update(payload, ["id"])

    def _migrate_folder(
        self,
        imported_folder: dict,
        target_folders: Any,
        target_db: Any,
    ) -> None:
        """Migrate a single active folder into the live database.

        If a folder with the same path already exists in the target DB, update it.
        Otherwise, insert a new row.
        """
        # Find matching folder in target database (active or inactive)
        match = None
        for existing_folder in target_folders.find():
            try:
                if os.path.samefile(
                    existing_folder["folder_name"], imported_folder["folder_name"]
                ):
                    match = existing_folder
                    break
            except (OSError, TypeError, ValueError):
                if existing_folder["folder_name"] == imported_folder["folder_name"]:
                    match = existing_folder
                    break

        cursor = target_db.raw_connection.cursor()
        cursor.execute("PRAGMA table_info(folders)")
        target_columns = {row[1] for row in cursor.fetchall()}

        payload = {
            key: value
            for key, value in imported_folder.items()
            if key in target_columns and key != "id"
        }

        if match:
            payload["id"] = match["id"]
            target_folders.update(payload, ["id"])
            return

        if payload:
            target_folders.insert(payload)


def show_database_import_dialog(
    parent: QWidget,
    original_database_path: str,
    running_platform: str,
    backup_path: str,
    current_db_version: str,
    preselected_database_path: Optional[str] = None,
) -> None:
    """Show the database import dialog.

    Args:
        parent: Parent widget
        original_database_path: Path to the original database
        running_platform: Current operating system platform
        backup_path: Path for backup files
        current_db_version: Current database version
        preselected_database_path: Optional path to preselect and show in UI
    """
    dialog = DatabaseImportDialog(
        parent,
        original_database_path,
        running_platform,
        backup_path,
        current_db_version,
        preselected_database_path,
    )
    dialog.exec()
