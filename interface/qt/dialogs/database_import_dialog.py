"""Qt-based database import dialog.

Replaces the tkinter-based database_import.py with a Qt implementation.
"""

from __future__ import annotations

import os
import threading
from typing import Any, Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
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

import dataset

import backup_increment
import folders_database_migrator


class DatabaseImportDialog(QDialog):
    """Dialog for importing folders from another database."""

    def __init__(
        self,
        parent: QWidget,
        original_database_path: str,
        running_platform: str,
        backup_path: str,
        current_db_version: str,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("folders.db merging utility")
        self.setModal(True)
        self.setWindowModality(Qt.WindowModality.WindowModal)

        self._original_database_path = original_database_path
        self._running_platform = running_platform
        self._backup_path = backup_path
        self._current_db_version = current_db_version
        self._new_database_path: Optional[str] = None
        self._database_migrate_job: Optional[DbMigrationJob] = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Database file selection frame
        db_file_frame = QFrame()
        db_file_layout = QVBoxLayout(db_file_frame)
        db_file_layout.setContentsMargins(0, 0, 0, 0)

        self._select_button = QPushButton("Select New Database File")
        self._select_button.clicked.connect(self._select_database)
        db_file_layout.addWidget(self._select_button)

        self._db_label = QLabel("No File Selected")
        self._db_label.setFrameShape(QFrame.Shape.Box)
        self._db_label.setFrameShadow(QFrame.Shadow.Sunken)
        db_file_layout.addWidget(self._db_label)

        main_layout.addWidget(db_file_frame)

        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        main_layout.addWidget(self._progress_bar)

        # Button frame
        button_frame = QFrame()
        button_layout = QHBoxLayout(button_frame)
        button_layout.setContentsMargins(0, 0, 0, 0)

        self._import_button = QPushButton("Import Active Folders")
        self._import_button.setEnabled(False)
        self._import_button.clicked.connect(self._start_import)
        button_layout.addWidget(self._import_button)

        button_layout.addStretch()

        self._close_button = QPushButton("Close")
        self._close_button.clicked.connect(self.accept)
        button_layout.addWidget(self._close_button)

        main_layout.addWidget(button_frame)

        # Set minimum size
        self.setMinimumSize(600, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def _select_database(self) -> None:
        """Handle database file selection."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Database File",
            os.path.expanduser('~'),
            "Database Files (*.db);;All Files (*)"
        )

        if file_path and os.path.exists(file_path):
            self._new_database_path = file_path
            self._db_label.setText(file_path)
            self._import_button.setEnabled(True)
            self._database_migrate_job = DbMigrationJob(self._original_database_path, file_path)

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
            self._backup_path
        )
        self._import_thread.progress.connect(self._on_progress)
        self._import_thread.finished.connect(self._on_finished)
        self._import_thread.error.connect(self._on_error)
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
            QMessageBox.information(self, "Import Complete", message)
        else:
            QMessageBox.critical(self, "Import Failed", message)

        # Re-enable buttons
        self._import_button.setEnabled(True)
        self._select_button.setEnabled(True)

    def _on_error(self, error_message: str) -> None:
        """Handle import error."""
        QMessageBox.critical(self, "Import Error", error_message)
        self._import_button.setEnabled(True)
        self._select_button.setEnabled(True)


class ImportThread(QThread):
    """Background thread for database import."""

    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(bool, str)
    error = pyqtSignal(str)

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

    def run(self) -> None:
        """Run the import process."""
        try:
            # Validate database version
            new_db_connection = dataset.connect('sqlite:///' + self._new_db_path)
            new_db_version_table = new_db_connection['version']
            new_db_version_dict = new_db_version_table.find_one(id=1)
            new_db_version = new_db_version_dict['version']

            # Check version compatibility
            if int(new_db_version) < 14:
                reply = QMessageBox.question(
                    None,
                    "Version Warning",
                    "Database versions below 14 do not contain operating system "
                    "information.\nFolder paths are not portable between operating "
                    "systems.\nThere is no guarantee that the imported folders will "
                    "work. Continue?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    self.finished.emit(False, "Import cancelled by user")
                    return

            elif int(new_db_version) > int(self._db_version):
                reply = QMessageBox.question(
                    None,
                    "Version Warning",
                    "The proposed database version is newer than the version "
                    "supported by this program.\nContinue?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    self.finished.emit(False, "Import cancelled by user")
                    return

                reply = QMessageBox.question(
                    None,
                    "Compatibility Warning",
                    "THIS WILL RESULT IN UNDEFINED BEHAVIOR, ARE YOU SURE YOU WANT "
                    "TO CONTINUE?\nBackup is stored at: " + self._backup_path,
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    self.finished.emit(False, "Import cancelled by user")
                    return

            elif new_db_version_dict.get('os') != self._platform:
                reply = QMessageBox.question(
                    None,
                    "Platform Warning",
                    "The operating system specified in the configuration does "
                    "not match the currently running operating system.\n"
                    "There is no guarantee that the imported folders will work. "
                    "Continue?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    self.finished.emit(False, "Import cancelled by user")
                    return

            # Run the migration
            self._migrate_job.do_migrate(
                self,
                self._new_db_path,
                self._original_db_path
            )

            self.finished.emit(True, "Import completed successfully")

        except Exception as e:
            self.error.emit(f"Import failed: {e}")


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
        original_db = dataset.connect('sqlite:///' + original_database_path)
        backup_increment.do_backup(self.original_folder_path)
        modified_new_path = backup_increment.do_backup(self.new_folder_path)

        original_db_version = original_db['version']
        original_db_version_dict = original_db_version.find_one(id=1)

        new_db = dataset.connect('sqlite:///' + modified_new_path)
        new_db_version = new_db['version']
        new_db_version_dict = new_db_version.find_one(id=1)

        if int(new_db_version_dict['version']) < int(original_db_version_dict['version']):
            folders_database_migrator.upgrade_database(new_db, None, "Null")

        # Get active folders
        new_folders = new_db['folders']
        old_folders = original_db['folders']

        # Count folders for progress
        active_new_folders = list(new_folders.find(folder_is_active="True"))
        active_new_folders.extend(list(new_folders.find(folder_is_active=1)))
        # Deduplicate
        seen_ids = set()
        unique_folders = []
        for folder in active_new_folders:
            if folder['id'] not in seen_ids:
                seen_ids.add(folder['id'])
                unique_folders.append(folder)

        total_folders = len(unique_folders)
        thread.progress.emit(0, total_folders, "Migrating folders...")

        # Migrate folders
        for i, folder in enumerate(unique_folders):
            self._migrate_folder(folder, old_folders, new_db)
            thread.progress.emit(i + 1, total_folders, f"Migrated {i + 1}/{total_folders} folders")

    def _migrate_folder(
        self,
        folder: dict,
        old_folders: Any,
        new_db: Any,
    ) -> None:
        """Migrate a single folder's settings."""
        # Find matching folder in old database
        match = None
        for old_folder in old_folders.find(folder_is_active="True"):
            try:
                if os.path.samefile(
                    old_folder['folder_name'],
                    folder['folder_name']
                ):
                    match = old_folder
                    break
            except (OSError, TypeError, ValueError):
                if old_folder['folder_name'] == folder['folder_name']:
                    match = old_folder
                    break

        if match:
            update_data = {'id': folder['id']}

            # Merge backend settings
            if match.get('process_backend_copy') in (True, 1, "True"):
                update_data.update({
                    'process_backend_copy': match['process_backend_copy'],
                    'copy_to_directory': match['copy_to_directory'],
                })

            if match.get('process_backend_ftp') in (True, 1, "True"):
                update_data.update({
                    'ftp_server': match['ftp_server'],
                    'ftp_folder': match['ftp_folder'],
                    'ftp_username': match['ftp_username'],
                    'ftp_password': match['ftp_password'],
                })

            if match.get('process_backend_email') in (True, 1, "True"):
                update_data.update({
                    'process_backend_email': match['process_backend_email'],
                    'email_recipients': match['email_recipients'],
                    'email_subject': match['email_subject'],
                    'email_from': match['email_from'],
                    'smtp_server': match['smtp_server'],
                    'smtp_port': match['smtp_port'],
                    'smtp_username': match['smtp_username'],
                    'smtp_password': match['smtp_password'],
                    'smtp_use_tls': match['smtp_use_tls'],
                })

            if update_data:
                new_db['folders'].update(update_data)


def show_database_import_dialog(
    parent: QWidget,
    original_database_path: str,
    running_platform: str,
    backup_path: str,
    current_db_version: str,
) -> None:
    """Show the database import dialog.

    Args:
        parent: Parent widget
        original_database_path: Path to the original database
        running_platform: Current operating system platform
        backup_path: Path for backup files
        current_db_version: Current database version
    """
    dialog = DatabaseImportDialog(
        parent,
        original_database_path,
        running_platform,
        backup_path,
        current_db_version,
    )
    dialog.exec()
