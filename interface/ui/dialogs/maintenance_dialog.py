"""MaintenanceDialog for advanced maintenance functions.

This module provides maintenance functions for the Batch File Sender application,
extracted from main_interface.py for better testability.
"""

import os
import datetime
import hashlib
import tkinter
import tkinter.ttk
from typing import Any, Callable, Dict, Optional

from tkinter.messagebox import askokcancel

import backup_increment
import database_import
import doingstuffoverlay


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
        """
        self._database_obj = database_obj
        self._refresh_callback = refresh_callback
        self._set_button_states_callback = set_button_states_callback
        self._delete_folder_callback = delete_folder_callback
        self._database_path = database_path
        self._running_platform = running_platform
        self._database_version = database_version
        self._maintenance_popup: Optional[tkinter.Toplevel] = None

    def set_maintenance_popup(self, popup: tkinter.Toplevel) -> None:
        """Set the maintenance popup window reference."""
        self._maintenance_popup = popup

    def set_all_inactive(self) -> None:
        """Set all folders to inactive status."""
        if self._maintenance_popup:
            self._maintenance_popup.unbind("<Escape>")
        doingstuffoverlay.make_overlay(
            self._maintenance_popup if self._maintenance_popup else None, 
            "Working..."
        )
        if self._maintenance_popup:
            self._maintenance_popup.update()
        self._database_obj.database_connection.query(
            'update folders set folder_is_active="False" where folder_is_active="True"'
        )
        if self._refresh_callback:
            self._refresh_callback()
        doingstuffoverlay.destroy_overlay()
        if self._maintenance_popup:
            self._maintenance_popup.update()
            self._maintenance_popup.bind("<Escape>", self._destroy_maintenance_popup)

    def set_all_active(self) -> None:
        """Set all folders to active status."""
        if self._maintenance_popup:
            self._maintenance_popup.unbind("<Escape>")
        doingstuffoverlay.make_overlay(
            self._maintenance_popup if self._maintenance_popup else None, 
            "Working..."
        )
        if self._maintenance_popup:
            self._maintenance_popup.update()
        self._database_obj.database_connection.query(
            'update folders set folder_is_active="True" where folder_is_active="False"'
        )
        if self._refresh_callback:
            self._refresh_callback()
        doingstuffoverlay.destroy_overlay()
        if self._maintenance_popup:
            self._maintenance_popup.update()
            self._maintenance_popup.bind("<Escape>", self._destroy_maintenance_popup)

    def clear_resend_flags(self) -> None:
        """Clear all resend flags in processed files."""
        if self._maintenance_popup:
            self._maintenance_popup.unbind("<Escape>")
        doingstuffoverlay.make_overlay(
            self._maintenance_popup if self._maintenance_popup else None, 
            "Working..."
        )
        if self._maintenance_popup:
            self._maintenance_popup.update()
        self._database_obj.database_connection.query(
            "update processed_files set resend_flag=0 where resend_flag=1"
        )
        doingstuffoverlay.destroy_overlay()
        if self._maintenance_popup:
            self._maintenance_popup.update()
            self._maintenance_popup.bind("<Escape>", self._destroy_maintenance_popup)

    def clear_processed_files_log(self) -> None:
        """Clear all processed files records."""
        if askokcancel(
            message="This will clear all records of sent files.\nAre you sure?"
        ):
            if self._maintenance_popup:
                self._maintenance_popup.unbind("<Escape>")
            self._database_obj.processed_files.delete()
            if self._set_button_states_callback:
                self._set_button_states_callback()
            if self._maintenance_popup:
                self._maintenance_popup.bind("<Escape>", self._destroy_maintenance_popup)

    def remove_inactive_folders(self) -> None:
        """Remove all folders marked as inactive."""
        if self._maintenance_popup:
            self._maintenance_popup.unbind("<Escape>")
        users_refresh = False
        if self._database_obj.folders_table.count(folder_is_active="False") > 0:
            users_refresh = True
        folders_total = self._database_obj.folders_table.count(
            folder_is_active="False"
        )
        folders_count = 0
        doingstuffoverlay.make_overlay(
            self._maintenance_popup if self._maintenance_popup else None,
            "removing " + str(folders_count) + " of " + str(folders_total),
        )
        for folder_to_be_removed in self._database_obj.folders_table.find(
            folder_is_active="False"
        ):
            folders_count += 1
            doingstuffoverlay.update_overlay(
                self._maintenance_popup if self._maintenance_popup else None,
                "removing " + str(folders_count) + " of " + str(folders_total),
            )
            if self._delete_folder_callback:
                self._delete_folder_callback(folder_to_be_removed["id"])
        doingstuffoverlay.destroy_overlay()
        if users_refresh and self._refresh_callback:
            self._refresh_callback()
        if self._maintenance_popup:
            self._maintenance_popup.bind("<Escape>", self._destroy_maintenance_popup)

    def mark_active_as_processed(
        self, 
        master: Optional[tkinter.Toplevel] = None, 
        selected_folder: Optional[int] = None
    ) -> None:
        """Mark all files in active folders as processed.

        Args:
            master: Parent window for overlay display
            selected_folder: Optional specific folder ID, or None for all active folders
        """
        popup = master or self._maintenance_popup
        if selected_folder is None and popup:
            popup.unbind("<Escape>")
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
        if selected_folder is None and popup:
            doingstuffoverlay.make_overlay(popup, "adding files to processed list...")
        for parameters_dict in (
            self._database_obj.folders_table_list
        ):  # create list of active directories
            file_total = 0
            file_count = 0
            folder_count += 1
            doingstuffoverlay.update_overlay(
                parent=popup if popup else None,
                overlay_text="adding files to processed list...\n\n"
                + " folder "
                + str(folder_count)
                + " of "
                + str(folder_total)
                + " file "
                + str(file_count)
                + " of "
                + str(file_total),
            )
            os.chdir(os.path.abspath(parameters_dict["folder_name"]))
            files = [f for f in os.listdir(".") if os.path.isfile(f)]
            # create list of all files in directory
            file_total = len(files)
            filtered_files = []
            for f in files:
                file_count += 1
                doingstuffoverlay.update_overlay(
                    parent=popup if popup else None,
                    overlay_text="checking files for already processed\n\n"
                    + str(folder_count)
                    + " of "
                    + str(folder_total)
                    + " file "
                    + str(file_count)
                    + " of "
                    + str(file_total),
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
                doingstuffoverlay.update_overlay(
                    parent=popup if popup else None,
                    overlay_text="adding files to processed list...\n\n"
                    + " folder "
                    + str(folder_count)
                    + " of "
                    + str(folder_total)
                    + " file "
                    + str(file_count)
                    + " of "
                    + str(file_total),
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
        doingstuffoverlay.destroy_overlay()
        os.chdir(starting_folder)
        if self._set_button_states_callback:
            self._set_button_states_callback()
        if selected_folder is None and popup:
            popup.bind("<Escape>", self._destroy_maintenance_popup)

    def database_import_wrapper(self, backup_path: str) -> None:
        """Import database from a backup.

        Args:
            backup_path: Path to the backup file
        """
        if self._maintenance_popup and self._database_path and self._running_platform:
            if database_import.import_interface(
                self._maintenance_popup,
                self._database_path,
                self._running_platform,
                backup_path,
                self._database_version,
            ):
                self._maintenance_popup.unbind("<Escape>")
                doingstuffoverlay.make_overlay(self._maintenance_popup, "Working...")
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
                        process_backend_email=False,
                        process_backend_ftp=False,
                        process_backend_copy=False,
                        folder_is_active="True",
                    ):
                        folder_to_disable["folder_is_active"] = "False"
                        self._database_obj.folders_table.update(
                            folder_to_disable, ["id"]
                        )
                if self._refresh_callback:
                    self._refresh_callback()
                doingstuffoverlay.destroy_overlay()
            self._maintenance_popup.bind("<Escape>", self._destroy_maintenance_popup)
            self._maintenance_popup.grab_set()
            self._maintenance_popup.focus_set()

    def _destroy_maintenance_popup(self, _=None) -> None:
        """Destroy the maintenance popup window."""
        if self._maintenance_popup:
            self._maintenance_popup.destroy()


def show_maintenance_dialog(
    root: tkinter.Tk,
    database_obj: Any,
    database_path: str,
    running_platform: str,
    database_version: str,
    refresh_callback: Callable[[], None],
    set_button_states_callback: Callable[[], None],
    delete_folder_callback: Callable[[int], None],
) -> Optional[tkinter.Toplevel]:
    """Show the maintenance functions popup dialog.

    Args:
        root: Parent window
        database_obj: Database object for data access
        database_path: Path to the database file
        running_platform: Platform identifier
        database_version: Database version string
        refresh_callback: Callback to refresh the UI
        set_button_states_callback: Callback to update button states
        delete_folder_callback: Callback to delete a folder by ID

    Returns:
        The maintenance popup window, or None if cancelled
    """
    # Warn the user about the dangers of this dialog
    if not askokcancel(
        message="Maintenance window is for advanced users only, potential for data loss if incorrectly used."
        " Are you sure you want to continue?"
    ):
        return None

    # Create backup before opening maintenance dialog
    backup_path = backup_increment.do_backup(database_path)

    # Create maintenance functions instance
    maintenance = MaintenanceFunctions(
        database_obj=database_obj,
        refresh_callback=refresh_callback,
        set_button_states_callback=set_button_states_callback,
        delete_folder_callback=delete_folder_callback,
        database_path=database_path,
        running_platform=running_platform,
        database_version=database_version,
    )

    # Create popup window
    maintenance_popup = tkinter.Toplevel()
    maintenance_popup.title("Maintenance Functions")
    maintenance_popup.transient(root)
    # center dialog on main window
    maintenance_popup.geometry(
        "+%d+%d" % (root.winfo_rootx() + 50, root.winfo_rooty() + 50)
    )
    maintenance_popup.grab_set()
    maintenance_popup.focus_set()
    maintenance_popup.resizable(width=tkinter.FALSE, height=tkinter.FALSE)

    # Set the popup reference in maintenance functions
    maintenance.set_maintenance_popup(maintenance_popup)

    maintenance_popup_button_frame = tkinter.ttk.Frame(maintenance_popup)
    # a persistent warning that this dialog can break things...
    maintenance_popup_warning_label = tkinter.ttk.Label(
        maintenance_popup, text="WARNING:\nFOR\nADVANCED\nUSERS\nONLY!"
    )
    set_all_active_button = tkinter.ttk.Button(
        maintenance_popup_button_frame,
        text="Move all to active (Skips Settings Validation)",
        command=maintenance.set_all_active,
    )
    set_all_inactive_button = tkinter.ttk.Button(
        maintenance_popup_button_frame,
        text="Move all to inactive",
        command=maintenance.set_all_inactive,
    )
    clear_resend_flags_button = tkinter.ttk.Button(
        maintenance_popup_button_frame,
        text="Clear all resend flags",
        command=maintenance.clear_resend_flags,
    )
    clear_emails_queue = tkinter.ttk.Button(
        maintenance_popup_button_frame,
        text="Clear queued emails",
        command=database_obj.emails_table.delete,
    )
    move_active_to_obe_button = tkinter.ttk.Button(
        maintenance_popup_button_frame,
        text="Mark all in active as processed",
        command=lambda: maintenance.mark_active_as_processed(maintenance_popup),
    )
    remove_all_inactive = tkinter.ttk.Button(
        maintenance_popup_button_frame,
        text="Remove all inactive configurations",
        command=maintenance.remove_inactive_folders,
    )
    clear_processed_files_log_button = tkinter.ttk.Button(
        maintenance_popup_button_frame,
        text="Clear sent file records",
        command=maintenance.clear_processed_files_log,
    )
    database_import_button = tkinter.ttk.Button(
        maintenance_popup_button_frame,
        text="Import old configurations...",
        command=lambda: maintenance.database_import_wrapper(backup_path),
    )

    # pack widgets into dialog
    set_all_active_button.pack(side=tkinter.TOP, fill=tkinter.X, padx=2, pady=2)
    set_all_inactive_button.pack(
        side=tkinter.TOP, fill=tkinter.X, padx=2, pady=2
    )
    clear_resend_flags_button.pack(
        side=tkinter.TOP, fill=tkinter.X, padx=2, pady=2
    )
    clear_emails_queue.pack(side=tkinter.TOP, fill=tkinter.X, padx=2, pady=2)
    move_active_to_obe_button.pack(
        side=tkinter.TOP, fill=tkinter.X, padx=2, pady=2
    )
    remove_all_inactive.pack(side=tkinter.TOP, fill=tkinter.X, padx=2, pady=2)
    clear_processed_files_log_button.pack(
        side=tkinter.TOP, fill=tkinter.X, padx=2, pady=2
    )
    database_import_button.pack(
        side=tkinter.TOP, fill=tkinter.X, padx=2, pady=2
    )
    maintenance_popup_button_frame.pack(side=tkinter.LEFT)
    maintenance_popup_warning_label.pack(side=tkinter.RIGHT, padx=20)
    maintenance_popup.bind("<Escape>", maintenance._destroy_maintenance_popup)

    return maintenance_popup
