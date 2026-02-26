"""MaintenanceFunctions for batch file processing operations.

This module provides maintenance functions for the Batch File Sender application,
extracted from main_interface.py for better testability.
"""

import os
import datetime
import hashlib
from typing import Any, Callable, Optional

from interface.services.progress_service import ProgressCallback, NullProgressCallback


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
        refresh_callback: Optional[Callable[[], None]] = None,
        set_button_states_callback: Optional[Callable[[], None]] = None,
        delete_folder_callback: Optional[Callable[[int], None]] = None,
        database_path: Optional[str] = None,
        running_platform: Optional[str] = None,
        database_version: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None,
        on_operation_start: Optional[Callable[[], None]] = None,
        on_operation_end: Optional[Callable[[], None]] = None,
        confirm_callback: Optional[Callable[[str], bool]] = None,
        database_import_callback: Optional[Callable[[str], bool]] = None,
    ):
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
            database_import_callback: Callback for database import (receives backup_path, returns success)
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

    def set_all_inactive(self) -> None:
        """Set all folders to inactive status."""
        if self._on_operation_start:
            self._on_operation_start()
        self._progress.show("Working...")
        self._database_obj.database_connection.query(
            'update folders set folder_is_active="False" where folder_is_active="True"'
        )
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
        self._database_obj.database_connection.query(
            'update folders set folder_is_active="True" where folder_is_active="False"'
        )
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
        if self._database_obj.folders_table.count(folder_is_active="False") > 0:
            users_refresh = True
        folders_total = self._database_obj.folders_table.count(
            folder_is_active="False"
        )
        folders_count = 0
        self._progress.show(
            "removing " + str(folders_count) + " of " + str(folders_total)
        )
        for folder_to_be_removed in self._database_obj.folders_table.find(
            folder_is_active="False"
        ):
            folders_count += 1
            self._progress.update_message(
                "removing " + str(folders_count) + " of " + str(folders_total)
            )
            if self._delete_folder_callback:
                self._delete_folder_callback(folder_to_be_removed["id"])
        self._progress.hide()
        if users_refresh and self._refresh_callback:
            self._refresh_callback()
        if self._on_operation_end:
            self._on_operation_end()

    def mark_active_as_processed(
        self,
        selected_folder: Optional[int] = None,
    ) -> None:
        """Mark all files in active folders as processed.

        Args:
            selected_folder: Optional specific folder ID, or None for all active folders
        """
        if selected_folder is None:
            if self._on_operation_start:
                self._on_operation_start()
        starting_folder = os.getcwd()
        folder_count = 0
        self._database_obj.folders_table_list = []
        if selected_folder is None:
            for row in self._database_obj.folders_table.find(
                folder_is_active="True"
            ):
                self._database_obj.folders_table_list.append(row)
        else:
            self._database_obj.folders_table_list = [
                self._database_obj.folders_table.find_one(id=selected_folder)
            ]
        folder_total = len(self._database_obj.folders_table_list)
        if selected_folder is None:
            self._progress.show("adding files to processed list...")
        for parameters_dict in (
            self._database_obj.folders_table_list
        ):  # create list of active directories
            file_total = 0
            file_count = 0
            folder_count += 1
            self._progress.update_message(
                "adding files to processed list...\n\n"
                + " folder "
                + str(folder_count)
                + " of "
                + str(folder_total)
                + " file "
                + str(file_count)
                + " of "
                + str(file_total)
            )
            os.chdir(os.path.abspath(parameters_dict["folder_name"]))
            files = [f for f in os.listdir(".") if os.path.isfile(f)]
            file_total = len(files)
            filtered_files = []
            for f in files:
                file_count += 1
                self._progress.update_message(
                    "checking files for already processed\n\n"
                    + str(folder_count)
                    + " of "
                    + str(folder_total)
                    + " file "
                    + str(file_count)
                    + " of "
                    + str(file_total)
                )
                with open(f, "rb") as file_handle:
                    file_checksum = hashlib.md5(file_handle.read()).hexdigest()
                if (
                    self._database_obj.processed_files.find_one(
                        file_name=os.path.join(os.getcwd(), f),
                        file_checksum=file_checksum,
                    )
                    is None
                ):
                    filtered_files.append(f)
            file_total = len(filtered_files)
            file_count = 0
            for filename in filtered_files:
                print(filename)
                file_count += 1
                self._progress.update_message(
                    "adding files to processed list...\n\n"
                    + " folder "
                    + str(folder_count)
                    + " of "
                    + str(folder_total)
                    + " file "
                    + str(file_count)
                    + " of "
                    + str(file_total)
                )
                with open(filename, "rb") as file_handle:
                    file_checksum = hashlib.md5(file_handle.read()).hexdigest()
                self._database_obj.processed_files.insert(
                    {
                        "file_name": str(os.path.abspath(filename)),
                        "file_checksum": file_checksum,
                        "folder_id": parameters_dict["id"],
                        "folder_alias": parameters_dict["alias"],
                        "copy_destination": "N/A",
                        "ftp_destination": "N/A",
                        "email_destination": "N/A",
                        "sent_date_time": datetime.datetime.now(),
                        "resend_flag": False,
                    }
                )
        self._progress.hide()
        os.chdir(starting_folder)
        if self._set_button_states_callback:
            self._set_button_states_callback()
        if selected_folder is None:
            if self._on_operation_end:
                self._on_operation_end()

    def database_import_wrapper(self, backup_path: str) -> None:
        """Import database from a backup.

        Args:
            backup_path: Path to the backup file
        """
        if self._database_import_callback is None:
            print("Database import callback not configured")
            return

        if self._database_import_callback(backup_path):
            if self._on_operation_start:
                self._on_operation_start()
            self._progress.show("Working...")
            self._database_obj.reload()
            settings_dict = self._database_obj.settings.find_one(id=1)
            print(settings_dict["enable_email"])
            if not settings_dict["enable_email"]:
                for (
                    email_backend_to_disable
                ) in self._database_obj.folders_table.find(
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
                    folder_is_active="True",
                ):
                    folder_to_disable["folder_is_active"] = "False"
                    self._database_obj.folders_table.update(
                        folder_to_disable, ["id"]
                    )
            if self._refresh_callback:
                self._refresh_callback()
            self._progress.hide()
        if self._on_operation_end:
            self._on_operation_end()
