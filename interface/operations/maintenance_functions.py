"""MaintenanceFunctions for batch file processing operations.

This module provides maintenance functions for the Batch File Sender application,
extracted from main_interface.py for better testability.
"""

import datetime
import hashlib
import os
from typing import Any, Callable

from core.ports.repositories import (
    IFolderRepository,
    IProcessedFilesRepository,
    ISettingsRepository,
)
from core.structured_logging import get_logger
from interface.services.progress_service import NullProgressCallback, ProgressCallback

logger = get_logger(__name__)


class MaintenanceFunctions:
    """Maintenance functions for the Batch File Sender application.

    This class encapsulates maintenance operations with dependency injection
    for testability. It provides functions for:
    - Setting all folders active/inactive
    - Clearing resend flags
    - Removing inactive folders
    - Marking files as processed
    - Clearing processed files log
    - Database import

    Dependencies are injected for testability:
    - database_obj: Database object for data access
    - refresh_callback: Callback to refresh the UI
    - set_button_states_callback: Callback to update button states
    - delete_folder_callback: Callback to delete a folder
    """

    def __init__(
        self,
        database_obj: Any,
        refresh_callback: Callable[[], None] | None = None,
        set_button_states_callback: Callable[[], None] | None = None,
        delete_folder_callback: Callable[[int], None] | None = None,
        database_path: str | None = None,
        running_platform: str | None = None,
        database_version: str | None = None,
        progress_callback: ProgressCallback | None = None,
        on_operation_start: Callable[[], None] | None = None,
        on_operation_end: Callable[[], None] | None = None,
        confirm_callback: Callable[[str], bool] | None = None,
        database_import_callback: Callable[[str], bool] | None = None,
        folder_repo: IFolderRepository | None = None,
        settings_repo: ISettingsRepository | None = None,
        processed_files_repo: IProcessedFilesRepository | None = None,
    ) -> None:
        """Initialize MaintenanceFunctions with dependencies.

        Args:
            database_obj: Database object for data access
            refresh_callback: Callback to refresh the UI
            set_button_states_callback: Callback to update button states
            delete_folder_callback: Callback to delete a folder by ID
            database_path: Path to the database file
            running_platform: Platform identifier (e.g., 'Windows', 'Linux')
            database_version: Database version string
            progress_callback: Progress reporting callback
            on_operation_start: Called at the start of each operation
            on_operation_end: Called at the end of each operation
            confirm_callback: Callback for user confirmation prompts
            database_import_callback: Callback for database import
            folder_repo: Optional folder repository for data access
            settings_repo: Optional settings repository for data access
            processed_files_repo: Optional processed files repository for data access

        """
        self._database_obj = database_obj
        self._refresh_callback = refresh_callback
        self._set_button_states_callback = set_button_states_callback
        self._delete_folder_callback = delete_folder_callback
        self._database_path = database_path
        self._running_platform = running_platform
        self._database_version = database_version
        self._progress = progress_callback or NullProgressCallback()
        self._on_operation_start = on_operation_start
        self._on_operation_end = on_operation_end
        self._confirm = confirm_callback or (lambda msg: True)
        self._database_import_callback = database_import_callback
        self._folder_repo = folder_repo
        self._settings_repo = settings_repo
        self._processed_files_repo = processed_files_repo

    def set_operation_callbacks(
        self,
        on_start: Callable[[], None] | None,
        on_end: Callable[[], None] | None,
    ) -> None:
        """Set callbacks invoked at the start and end of each operation.

        Args:
            on_start: Called before each maintenance operation begins.
            on_end: Called after each maintenance operation completes.

        """
        self._on_operation_start = on_start
        self._on_operation_end = on_end

    def get_database(self) -> Any:
        """Return the underlying database object.

        Returns:
            The database object passed at construction time.

        """
        return self._database_obj

    def set_all_inactive(self) -> None:
        """Set all folders to inactive status."""
        if self._on_operation_start:
            self._on_operation_start()
        self._progress.show("Working...")
        if self._folder_repo is not None:
            for row in self._folder_repo.find_all(active_only=True):
                row["folder_is_active"] = False
                self._folder_repo.update(row)
        else:
            for row in self._database_obj.folders_table.find(folder_is_active=True):
                row["folder_is_active"] = False
                self._database_obj.folders_table.update(row, ["id"])
        if self._refresh_callback:
            self._refresh_callback()
        self._progress.hide()
        if self._on_operation_end:
            self._on_operation_end()

    def set_all_active(self) -> None:
        """Set all folders to active status."""
        if self._on_operation_start:
            self._on_operation_start()
        self._progress.show("Working...")
        if self._folder_repo is not None:
            for row in self._folder_repo.find_all(active_only=False):
                if not row.get("folder_is_active", True):
                    row["folder_is_active"] = True
                    self._folder_repo.update(row)
        else:
            for row in self._database_obj.folders_table.find(folder_is_active=False):
                row["folder_is_active"] = True
                self._database_obj.folders_table.update(row, ["id"])
        if self._refresh_callback:
            self._refresh_callback()
        self._progress.hide()
        if self._on_operation_end:
            self._on_operation_end()

    def clear_resend_flags(self) -> None:
        """Clear all resend flags in processed files."""
        if self._on_operation_start:
            self._on_operation_start()
        self._progress.show("Working...")
        self._database_obj.database_connection.query(
            "update processed_files set resend_flag=0 where resend_flag=1"
        )
        self._progress.hide()
        if self._on_operation_end:
            self._on_operation_end()

    def clear_processed_files_log(self) -> None:
        """Clear all processed files records."""
        if self._confirm("This will clear all records of sent files.\nAre you sure?"):
            if self._on_operation_start:
                self._on_operation_start()
            if self._processed_files_repo is not None:
                self._processed_files_repo.clear_all()
            else:
                self._database_obj.processed_files.delete()
            if self._set_button_states_callback:
                self._set_button_states_callback()
            if self._on_operation_end:
                self._on_operation_end()

    def remove_inactive_folders(self) -> None:
        """Remove all folders marked as inactive."""
        if self._on_operation_start:
            self._on_operation_start()
        users_refresh = False

        def _remove_folders_iter(folders_iter, *, active_only: bool) -> None:
            nonlocal users_refresh
            count = len(folders_iter) if hasattr(folders_iter, "__len__") else 0
            if count > 0:
                users_refresh = True
            folders_total = count
            folders_count = 0
            self._progress.show(
                "removing " + str(folders_count) + " of " + str(folders_total)
            )
            for folder_to_be_removed in folders_iter:
                folders_count += 1
                self._progress.update_message(
                    "removing " + str(folders_count) + " of " + str(folders_total)
                )
                if self._delete_folder_callback:
                    self._delete_folder_callback(folder_to_be_removed["id"])

        if self._folder_repo is not None:
            folders = list(self._folder_repo.find_all(active_only=True))
            _remove_folders_iter(folders, active_only=True)
        else:
            folders = list(
                self._database_obj.folders_table.find(folder_is_active=False)
            )
            _remove_folders_iter(folders, active_only=False)

        self._progress.hide()
        if users_refresh and self._refresh_callback:
            self._refresh_callback()
        if self._on_operation_end:
            self._on_operation_end()

    def mark_active_as_processed(
        self,
        selected_folder: int | None = None,
    ) -> None:
        """Mark all files in active folders as processed.

        Args:
            selected_folder: Optional specific folder ID, or None for all active folders

        """
        # Start operation
        if selected_folder is None and self._on_operation_start:
            self._on_operation_start()

        starting_folder = os.getcwd()
        try:
            folders = self._get_folders_to_process(selected_folder)
            folder_total = len(folders)
            if selected_folder is None:
                self._progress.show("adding files to processed list...")

            folder_count = 0
            for parameters_dict in folders:
                folder_count += 1
                self._process_single_folder(
                    parameters_dict=parameters_dict,
                    folder_count=folder_count,
                    folder_total=folder_total,
                )

        finally:
            self._progress.hide()
            os.chdir(starting_folder)
            if self._set_button_states_callback:
                self._set_button_states_callback()
            if selected_folder is None and self._on_operation_end:
                self._on_operation_end()

    def _get_folders_to_process(self, selected_folder: int | None) -> list:
        """Return a list of folder parameter dicts to process."""
        if selected_folder is None:
            return list(self._database_obj.folders_table.find(folder_is_active=True))

        folder_dict = self._database_obj.folders_table.find_one(id=selected_folder)
        if folder_dict:
            return [folder_dict]

        logger.debug("Warning: Folder with id %s not found", selected_folder)
        return []

    def _checksum_of_file(self, path: str) -> str:
        """Compute MD5 checksum for given file path."""
        with open(path, "rb") as fh:
            return hashlib.md5(fh.read()).hexdigest()

    def _progress_message(
        self,
        prefix: str,
        folder_count: int,
        folder_total: int,
        file_count: int,
        file_total: int,
    ) -> str:
        return (
            prefix
            + "\n\n folder "
            + str(folder_count)
            + " of "
            + str(folder_total)
            + " file "
            + str(file_count)
            + " of "
            + str(file_total)
        )

    def _process_single_folder(
        self, parameters_dict: dict, folder_count: int, folder_total: int
    ) -> None:
        """Process a single folder: find unprocessed files and insert records."""
        # Change into folder
        self._progress.update_message(
            self._progress_message(
                "adding files to processed list...",
                folder_count,
                folder_total,
                0,
                0,
            )
        )
        os.chdir(os.path.abspath(parameters_dict["folder_name"]))

        # List files and filter those not already processed
        files = [f for f in os.listdir(".") if os.path.isfile(f)]
        file_total = len(files)
        filtered_files: list[str] = []
        file_count = 0
        for f in files:
            file_count += 1
            self._progress.update_message(
                self._progress_message(
                    "checking files for already processed",
                    folder_count,
                    folder_total,
                    file_count,
                    file_total,
                )
            )
            checksum = self._checksum_of_file(f)
            if self._database_obj.processed_files.find_one(
                file_name=os.path.join(os.getcwd(), f), file_checksum=checksum
            ) is None:
                filtered_files.append(f)

        file_total = len(filtered_files)
        file_count = 0
        for filename in filtered_files:
            logger.debug("Processing file: %s", filename)
            file_count += 1
            self._progress.update_message(
                self._progress_message(
                    "adding files to processed list...",
                    folder_count,
                    folder_total,
                    file_count,
                    file_total,
                )
            )
            checksum = self._checksum_of_file(filename)
            self._database_obj.processed_files.insert(
                {
                    "file_name": str(os.path.abspath(filename)),
                    "file_checksum": checksum,
                    "folder_id": parameters_dict["id"],
                    "folder_alias": parameters_dict["alias"],
                    "copy_destination": "N/A",
                    "ftp_destination": "N/A",
                    "email_destination": "N/A",
                    "sent_date_time": datetime.datetime.now(),
                    "resend_flag": False,
                }
            )

    def database_import_wrapper(self, backup_path: str) -> None:
        """Import database from a backup.

        Args:
            backup_path: Path to the backup file

        """
        if self._database_import_callback is None:
            logger.debug("Database import callback not configured")
            return

        if self._database_import_callback(backup_path):
            if self._on_operation_start:
                self._on_operation_start()
            self._progress.show("Working...")
            self._database_obj.reload()
            settings_dict = self._database_obj.get_settings_or_default()
            logger.debug("Email enabled in settings: %s", settings_dict["enable_email"])
            if not settings_dict["enable_email"]:
                for email_backend_to_disable in self._database_obj.folders_table.find(
                    process_backend_email=True
                ):
                    email_backend_to_disable["process_backend_email"] = False
                    self._database_obj.folders_table.update(
                        email_backend_to_disable, ["id"]
                    )
                for folder_to_disable in self._database_obj.folders_table.find(
                    process_backend_ftp=False,
                    process_backend_copy=False,
                    process_backend_email=False,
                    folder_is_active=True,
                ):
                    folder_to_disable["folder_is_active"] = False
                    self._database_obj.folders_table.update(folder_to_disable, ["id"])
            if self._refresh_callback:
                self._refresh_callback()
            self._progress.hide()
        if self._on_operation_end:
            self._on_operation_end()
