"""Batch File Sender Application class.

This module contains the main application class that encapsulates
the Tkinter application state, initialization, and lifecycle management.

The BatchFileSenderApp class provides:
- Application initialization and configuration
- UI setup and management
- Event coordination
- Lifecycle methods (setup, run, cleanup)
- Dependency injection for testability
"""

import argparse
import datetime
import multiprocessing
import os
import platform
import time
import tkinter
import tkinter.ttk
import traceback
from typing import Any, Callable, Optional

import appdirs
from tkinter.filedialog import askdirectory
from tkinter.messagebox import askokcancel, askyesno, showerror, showinfo

# Import application modules
import batch_log_sender
import create_database
import database_import
import dialog
import dispatch
import doingstuffoverlay
import folders_database_migrator
import print_run_log
import resend_interface
import utils
import tk_extra_widgets
import backup_increment

# Import refactored components
from interface.database.database_obj import DatabaseObj
from interface.operations.folder_manager import FolderManager
from interface.services.reporting_service import ReportingService
from interface.ui.dialogs.edit_folders_dialog import EditFoldersDialog
from interface.ui.dialogs.edit_settings_dialog import EditSettingsDialog
from interface.ui.dialogs.maintenance_dialog import show_maintenance_dialog, MaintenanceFunctions
from interface.ui.dialogs.processed_files_dialog import (
    export_processed_report,
    show_processed_files_dialog,
)
from interface.ui.widgets.folder_list_widget import FolderListWidget
from interface.ui.widgets.search_widget import SearchWidget
from tk_extra_widgets import columnSorterWidget

from .interfaces import TkinterProtocol


class BatchFileSenderApp:
    """Main application class for Batch File Sender.
    
    This class encapsulates all application state and logic, providing
    a clean interface for initialization, running, and shutdown.
    
    Attributes:
        appname: Application name
        version: Version string
        database_version: Database schema version
        
    Example:
        >>> app = BatchFileSenderApp(
        ...     appname="Batch File Sender",
        ...     version="(Git Branch: Master)",
        ...     database_version="33"
        ... )
        >>> app.initialize()
        >>> app.run()
    """
    
    def __init__(
        self,
        appname: str = "Batch File Sender",
        version: str = "(Git Branch: Master)",
        database_version: str = "33",
        root: Optional[tkinter.Tk] = None,
        database_obj: Optional[DatabaseObj] = None,
    ):
        """Initialize the application.
        
        Args:
            appname: Application name displayed in title bar
            version: Version string displayed in title bar
            database_version: Database schema version
            root: Optional pre-created Tkinter root (for testing)
            database_obj: Optional pre-configured database (for testing)
        """
        self._appname = appname
        self._version = version
        self._database_version = database_version
        
        # Core components
        self._root: Optional[tkinter.Tk] = root
        self._database: Optional[DatabaseObj] = database_obj
        self._folder_manager: Optional[FolderManager] = None
        self._reporting_service: Optional[ReportingService] = None
        
        # Platform info
        self._running_platform = platform.system()
        
        # Configuration paths
        self._config_folder: Optional[str] = None
        self._database_path: Optional[str] = None
        
        # UI state
        self._folder_filter = ""
        self._users_list_frame: Optional[tkinter.ttk.Frame] = None
        self._options_frame: Optional[tkinter.ttk.Frame] = None
        self._feedback_text: Optional[tkinter.ttk.Label] = None
        self._search_field: Optional[tkinter.ttk.Entry] = None
        
        # Extracted widgets
        self._search_widget: Optional[SearchWidget] = None
        self._folder_list_widget: Optional[FolderListWidget] = None
        
        # UI buttons (stored for state management)
        self._process_folder_button: Optional[tkinter.ttk.Button] = None
        self._processed_files_button: Optional[tkinter.ttk.Button] = None
        self._allow_resend_button: Optional[tkinter.ttk.Button] = None
        
        # Command line arguments
        self._args: Optional[argparse.Namespace] = None
        
        # Cached database queries
        self._logs_directory: Optional[dict] = None
        self._errors_directory: Optional[dict] = None
    
    @property
    def root(self) -> tkinter.Tk:
        """Get the Tkinter root window.
        
        Returns:
            The Tkinter root window instance
            
        Raises:
            RuntimeError: If root has not been initialized
        """
        if self._root is None:
            raise RuntimeError("Application not initialized - call initialize() first")
        return self._root
    
    @property
    def database(self) -> DatabaseObj:
        """Get the database instance.
        
        Returns:
            The DatabaseObj instance
            
        Raises:
            RuntimeError: If database has not been initialized
        """
        if self._database is None:
            raise RuntimeError("Database not initialized - call initialize() first")
        return self._database
    
    @property
    def folder_manager(self) -> FolderManager:
        """Get the folder manager instance.
        
        Returns:
            The FolderManager instance
            
        Raises:
            RuntimeError: If folder manager has not been initialized
        """
        if self._folder_manager is None:
            raise RuntimeError("Folder manager not initialized - call initialize() first")
        return self._folder_manager
    
    @property
    def args(self) -> argparse.Namespace:
        """Get the parsed command line arguments.
        
        Returns:
            The parsed arguments namespace
        """
        if self._args is None:
            raise RuntimeError("Arguments not parsed - call initialize() first")
        return self._args
    
    def initialize(self) -> None:
        """Initialize all application components.
        
        This method sets up the application in the correct order:
        1. Parse command line arguments
        2. Create/verify Tkinter root window
        3. Set up configuration directories
        4. Initialize database
        5. Initialize service classes
        6. Build UI
        7. Check for automatic mode
        
        Raises:
            RuntimeError: If initialization fails
        """
        multiprocessing.freeze_support()
        print(f"{self._appname} Version {self._version}")
        print(f"Running on {self._running_platform}")
        
        # Parse command line arguments
        self._parse_arguments()
        
        # Create or use existing root window
        if self._root is None:
            self._root = tkinter.Tk()
        self._root.title(f"{self._appname} {self._version}")
        
        # Create initial UI elements
        self._options_frame = tkinter.ttk.Frame(self._root)
        self._feedback_text = tkinter.ttk.Label(self._root, text="Loading...")
        self._feedback_text.pack(side=tkinter.BOTTOM)
        self._root.update()
        
        # Set up configuration directories
        self._setup_config_directories()
        
        # Initialize database if not provided
        if self._database is None:
            self._database = DatabaseObj(
                self._database_path,
                self._database_version,
                self._config_folder,
                self._running_platform
            )
        
        # Initialize service classes
        self._folder_manager = FolderManager(self._database)
        self._reporting_service = ReportingService(
            database=self._database,
            batch_log_sender_module=batch_log_sender,
            print_run_log_module=print_run_log,
            utils_module=utils,
        )
        
        # Cache database queries
        self._logs_directory = self._database.oversight_and_defaults.find_one(id=1)
        self._errors_directory = self._database.oversight_and_defaults.find_one(id=1)
        
        # Check for automatic mode
        if self._args.automatic:
            self._automatic_process_directories(self._database.folders_table)
            return
        
        # Build the main UI
        self._make_users_list()
        self._build_main_window()
        self._set_main_button_states()
        
        # Configure window
        self._configure_window()
    
    def _parse_arguments(self) -> None:
        """Parse command line arguments."""
        launch_options = argparse.ArgumentParser()
        launch_options.add_argument("-a", "--automatic", action="store_true")
        self._args = launch_options.parse_args()
    
    def _setup_config_directories(self) -> None:
        """Set up configuration directories."""
        self._config_folder = appdirs.user_data_dir(self._appname)
        self._database_path = os.path.join(self._config_folder, "folders.db")
        
        try:
            os.makedirs(self._config_folder)
        except FileExistsError:
            pass
    
    def _configure_window(self) -> None:
        """Configure the main window properties."""
        self._root.update()
        self._root.minsize(self._root.winfo_width(), self._root.winfo_height())
        self._root.resizable(width=tkinter.FALSE, height=tkinter.TRUE)
    
    def run(self) -> None:
        """Start the application main loop.
        
        This method blocks until the application window is closed.
        """
        if self._root is None:
            raise RuntimeError("Application not initialized - call initialize() first")
        self._root.mainloop()
    
    def shutdown(self) -> None:
        """Clean up and close the application.
        
        This method should be called before exiting to ensure
        proper cleanup of resources.
        """
        if self._database is not None:
            self._database.close()
    
    # -------------------------------------------------------------------------
    # UI Construction Methods
    # -------------------------------------------------------------------------
    
    def _build_main_window(self) -> None:
        """Build the main window widgets."""
        if self._options_frame is None:
            self._options_frame = tkinter.ttk.Frame(self._root)
        
        # Create buttons
        open_folder_button = tkinter.ttk.Button(
            self._options_frame, text="Add Directory...", command=self._select_folder
        )
        open_multiple_folder_button = tkinter.ttk.Button(
            self._options_frame, text="Batch Add Directories...", command=self._batch_add_folders
        )
        default_settings = tkinter.ttk.Button(
            self._options_frame, text="Set Defaults...", command=self._set_defaults_popup
        )
        edit_reporting = tkinter.ttk.Button(
            self._options_frame,
            text="Edit Settings...",
            command=self._show_edit_settings_dialog,
        )
        self._process_folder_button = tkinter.ttk.Button(
            self._options_frame,
            text="Process All Folders",
            command=lambda: self._graphical_process_directories(
                self._database.folders_table
            ),
        )
        
        self._allow_resend_button = tkinter.ttk.Button(
            self._options_frame,
            text="Enable Resend...",
            command=lambda: resend_interface.do(
                self._database.database_connection, self._root
            ),
        )
        
        maintenance_button = tkinter.ttk.Button(
            self._options_frame, text="Maintenance...", command=self._show_maintenance_dialog_wrapper
        )
        self._processed_files_button = tkinter.ttk.Button(
            self._options_frame, text="Processed Files Report...", command=self._show_processed_files_dialog_wrapper
        )
        options_frame_divider = tkinter.ttk.Separator(self._root, orient=tkinter.VERTICAL)
        
        # Pack buttons
        open_folder_button.pack(side=tkinter.TOP, fill=tkinter.X, pady=2, padx=2)
        open_multiple_folder_button.pack(side=tkinter.TOP, fill=tkinter.X, pady=2, padx=2)
        default_settings.pack(side=tkinter.TOP, fill=tkinter.X, pady=2, padx=2)
        edit_reporting.pack(side=tkinter.TOP, fill=tkinter.X, pady=2, padx=2)
        self._process_folder_button.pack(side=tkinter.BOTTOM, fill=tkinter.X, pady=2, padx=2)
        tkinter.ttk.Separator(self._options_frame, orient=tkinter.HORIZONTAL).pack(
            fill="x", side=tkinter.BOTTOM
        )
        maintenance_button.pack(side=tkinter.TOP, fill=tkinter.X, pady=2, padx=2)
        self._allow_resend_button.pack(side=tkinter.BOTTOM, fill=tkinter.X, pady=2, padx=2)
        tkinter.ttk.Separator(self._options_frame, orient=tkinter.HORIZONTAL).pack(
            fill="x", side=tkinter.BOTTOM
        )
        self._processed_files_button.pack(side=tkinter.TOP, fill=tkinter.X, pady=2, padx=2)
        
        # Remove loading text
        if self._feedback_text is not None:
            self._feedback_text.destroy()
        
        # Pack main frames
        self._options_frame.pack(side=tkinter.LEFT, anchor="n", fill=tkinter.Y)
        options_frame_divider.pack(side=tkinter.LEFT, fill=tkinter.Y)
    
    def _make_users_list(self) -> None:
        """Create the users/folders list UI using extracted widgets."""
        self._users_list_frame = tkinter.ttk.Frame(self._root)
        
        # Create search widget
        self._search_widget = SearchWidget(
            parent=self._users_list_frame,
            initial_value=self._folder_filter,
            on_filter_change=self._set_folders_filter,
            on_escape_clear=True,
            attach_right_click_menu=True,
        )
        
        # Create folder list widget
        self._folder_list_widget = FolderListWidget(
            parent=self._root,
            folders_table=self._database.folders_table,
            on_send=self._send_single,
            on_edit=self._edit_folder_selector,
            on_disable=self._disable_folder,
            on_delete=self._delete_folder_entry_wrapper,
            filter_value=self._folder_filter,
            total_count_callback=self._update_filter_count_label,
        )
        
        # Disable search if no folders exist
        if self._database.folders_table.count() == 0:
            self._search_widget.disable()
        
        # Pack search widget at bottom
        self._search_widget.pack(side=tkinter.BOTTOM, ipady=5)
        
        # Pack folder list widget
        self._folder_list_widget.pack(
            side=tkinter.RIGHT, fill=tkinter.BOTH, expand=tkinter.TRUE
        )
        
        # Store reference to search field for backward compatibility
        self._search_field = self._search_widget.entry
    
    def _update_filter_count_label(self, filtered_count: int, total_count: int) -> None:
        """Update the filter count label if filtering is active.
        
        Args:
            filtered_count: Number of folders shown after filtering
            total_count: Total number of folders in database
        """
        # This callback is provided for future enhancement
        # Currently the count is shown in the folder list widget itself
        pass
    
    def _set_main_button_states(self) -> None:
        """Update the state of main window buttons based on current state."""
        if self._database.folders_table.count() == 0:
            self._process_folder_button.configure(state=tkinter.DISABLED)
        else:
            if self._database.folders_table.count(folder_is_active="True") > 0:
                self._process_folder_button.configure(state=tkinter.NORMAL)
            else:
                self._process_folder_button.configure(state=tkinter.DISABLED)
        
        if self._database.processed_files.count() > 0:
            self._processed_files_button.configure(state=tkinter.NORMAL)
            self._allow_resend_button.configure(state=tkinter.NORMAL)
        else:
            self._processed_files_button.configure(state=tkinter.DISABLED)
            self._allow_resend_button.configure(state=tkinter.DISABLED)
    
    # -------------------------------------------------------------------------
    # Folder Operations
    # -------------------------------------------------------------------------
    
    def _select_folder(self) -> None:
        """Open folder selection dialog and add selected folder."""
        prior_folder = self._database.oversight_and_defaults.find_one(id=1)
        if os.path.exists(prior_folder["single_add_folder_prior"]):
            initial_directory = prior_folder["single_add_folder_prior"]
        else:
            initial_directory = os.path.expanduser("~")
        selected_folder = askdirectory(initialdir=initial_directory)
        if os.path.exists(selected_folder):
            update_last_folder = {"id": 1, "single_add_folder_prior": selected_folder}
            self._database.oversight_and_defaults.update(
                update_last_folder, ["id"]
            )
            proposed_folder = self._folder_manager.check_folder_exists(selected_folder)
            
            if proposed_folder["truefalse"] is False:
                doingstuffoverlay.make_overlay(self._root, "Adding Folder...")
                self._folder_manager.add_folder(selected_folder)
                if askyesno(
                    message="Do you want to mark files in folder as processed?"
                ):
                    folder_dict = self._database.folders_table.find_one(
                        folder_name=selected_folder
                    )
                    self._mark_active_as_processed_wrapper(self._root, folder_dict["id"])
                doingstuffoverlay.destroy_overlay()
                self._refresh_users_list()
            else:
                proposed_folder_dict = proposed_folder["matched_folder"]
                if askokcancel(
                    "Query:", "Folder already known, would you like to edit?"
                ):
                    EditFoldersDialog(self._root, proposed_folder_dict)
    
    def _batch_add_folders(self) -> None:
        """Batch add multiple folders from a selected parent directory."""
        prior_folder = self._database.oversight_and_defaults.find_one(id=1)
        starting_directory = os.getcwd()
        selection = askdirectory(
            initialdir=prior_folder["batch_add_folder_prior"] or os.path.expanduser("~")
        )
        if selection:
            folders_to_add = [
                os.path.join(selection, folder)
                for folder in os.listdir(selection)
                if os.path.isdir(os.path.join(selection, folder))
            ]
            if not askokcancel(
                message=f"This will add {len(folders_to_add)} directories, are you sure?"
            ):
                return
            doingstuffoverlay.make_overlay(
                parent=self._root, overlay_text="Adding folders..."
            )
            added, skipped = 0, 0
            for folder in folders_to_add:
                doingstuffoverlay.update_overlay(
                    parent=self._root,
                    overlay_text=f"Adding folders... ({added + skipped + 1}/{len(folders_to_add)})",
                )
                if self._folder_manager.check_folder_exists(folder)["truefalse"]:
                    skipped += 1
                else:
                    self._folder_manager.add_folder(folder)
                    added += 1
            print(f"done adding {added} folders")
            doingstuffoverlay.destroy_overlay()
            showinfo(
                parent=self._root,
                message=f"{added} folders added, {skipped} folders skipped.",
            )
            self._refresh_users_list()
        os.chdir(starting_directory)
    
    def _edit_folder_selector(self, folder_to_be_edited: int) -> None:
        """Open edit dialog for a specific folder.
        
        Args:
            folder_to_be_edited: The ID of the folder to edit
        """
        edit_folder = self._database.folders_table.find_one(
            id=[folder_to_be_edited]
        )
        EditFoldersDialog(self._root, edit_folder)
    
    def _send_single(self, folder_id: int) -> None:
        """Process a single folder.
        
        Args:
            folder_id: The ID of the folder to process
        """
        doingstuffoverlay.make_overlay(self._root, "Working...")
        try:
            single_table = self._database.session_database["single_table"]
            single_table.drop()
        finally:
            single_table = self._database.session_database["single_table"]
            table_dict = self._database.folders_table.find_one(id=folder_id)
            table_dict["old_id"] = table_dict.pop("id")
            single_table.insert(table_dict)
            doingstuffoverlay.destroy_overlay()
            self._graphical_process_directories(single_table)
            single_table.drop()
    
    def _disable_folder(self, folder_id: int) -> None:
        """Disable a folder.
        
        Args:
            folder_id: The ID of the folder to disable
        """
        self._folder_manager.disable_folder(folder_id)
        self._refresh_users_list()
    
    def _set_folders_filter(self, filter_field_contents: str) -> None:
        """Set the folder filter and refresh the list.
        
        Args:
            filter_field_contents: The filter string to apply
        """
        self._folder_filter = filter_field_contents
        self._refresh_users_list()
    
    def _refresh_users_list(self) -> None:
        """Refresh the users/folders list display."""
        # Destroy existing widgets if they exist
        if hasattr(self, '_folder_list_widget') and self._folder_list_widget is not None:
            self._folder_list_widget.destroy()
        if self._users_list_frame is not None:
            self._users_list_frame.destroy()
        
        # Recreate the widgets
        self._make_users_list()
        self._users_list_frame.pack(
            side=tkinter.RIGHT, fill=tkinter.BOTH, expand=1
        )
        self._set_main_button_states()
    
    def _delete_folder_entry_wrapper(self, folder_to_be_removed: int, alias: str) -> None:
        """Delete a folder entry with confirmation.
        
        Args:
            folder_to_be_removed: The ID of the folder to remove
            alias: The alias of the folder for the confirmation message
        """
        if askyesno(
            message=f"Are you sure you want to remove the folder {alias}?"
        ):
            self._folder_manager.delete_folder_with_related(folder_to_be_removed)
            self._refresh_users_list()
            self._set_main_button_states()
    
    # -------------------------------------------------------------------------
    # Processing Methods
    # -------------------------------------------------------------------------
    
    def _graphical_process_directories(
        self,
        folders_table_process,
    ) -> None:
        """Process folders while showing progress overlay.
        
        Args:
            folders_table_process: The table of folders to process
        """
        missing_folder = False
        for folder_test in folders_table_process.find(folder_is_active="True"):
            if not os.path.exists(folder_test["folder_name"]):
                missing_folder = True
        if missing_folder:
            showerror(
                parent=self._root,
                title="Error",
                text="One or more expected folders are missing.",
            )
        else:
            if folders_table_process.count(folder_is_active="True") > 0:
                doingstuffoverlay.make_overlay(
                    parent=self._root, overlay_text="processing folders..."
                )
                self._process_directories(folders_table_process)
                self._refresh_users_list()
                self._set_main_button_states()
                doingstuffoverlay.destroy_overlay()
            else:
                showerror(parent=self._root, title="Error", text="No Active Folders")
    
    def _process_directories(self, folders_table_process) -> None:
        """Process all active folders.
        
        Args:
            folders_table_process: The table of folders to process
        """
        original_folder = os.getcwd()
        settings_dict = self._database.settings.find_one(id=1)
        if (
            settings_dict["enable_interval_backups"]
            and settings_dict["backup_counter"]
            >= settings_dict["backup_counter_maximum"]
        ):
            backup_increment.do_backup(self._database_path)
            settings_dict["backup_counter"] = 0
        settings_dict["backup_counter"] += 1
        self._database.settings.update(settings_dict, ["id"])
        
        log_folder_creation_error = False
        start_time = str(datetime.datetime.now())
        reporting = self._database.oversight_and_defaults.find_one(id=1)
        run_log_name_constructor = (
            "Run Log " + str(time.ctime()).replace(":", "-") + ".txt"
        )
        
        # Check for configured logs directory
        if not os.path.isdir(self._logs_directory["logs_directory"]):
            try:
                os.mkdir(self._logs_directory["logs_directory"])
            except IOError:
                log_folder_creation_error = True
        
        if not self._check_logs_directory() or log_folder_creation_error:
            if not self._args.automatic:
                while not self._check_logs_directory():
                    if askokcancel(
                        "Error",
                        "Can't write to log directory,\r\n"
                        " would you like to change reporting settings?",
                    ):
                        self._show_edit_settings_dialog()
                    else:
                        showerror(
                            parent=self._root, message="Can't write to log directory, exiting"
                        )
                        raise SystemExit
            else:
                self._log_critical_error(
                    "can't write into logs directory. in automatic mode, so no prompt",
                )
        
        run_log_path = reporting["logs_directory"]
        run_log_path = str(run_log_path)
        run_log_full_path = os.path.join(run_log_path, run_log_name_constructor)
        
        run_summary_string = ""
        
        with open(run_log_full_path, "wb") as run_log:
            utils.do_clear_old_files(run_log_path, 1000)
            run_log.write((f"Batch File Sender Version {self._version}\r\n").encode())
            run_log.write((f"starting run at {time.ctime()}\r\n").encode())
            
            if utils.normalize_bool(reporting["enable_reporting"]):
                self._database.emails_table.insert(
                    {"log": run_log_full_path, "folder_alias": run_log_name_constructor}
                )
            
            try:
                run_error_bool, run_summary_string = dispatch.process(
                    self._database.database_connection,
                    folders_table_process,
                    run_log,
                    self._database.emails_table,
                    reporting["logs_directory"],
                    reporting,
                    self._database.processed_files,
                    self._version,
                    self._errors_directory,
                    settings_dict,
                    progress_callback=self._build_progress_callback(),
                )
                if run_error_bool and not self._args.automatic:
                    showinfo(
                        parent=self._root,
                        title="Run Status",
                        message="Run completed with errors.",
                    )
                os.chdir(original_folder)
            except Exception as dispatch_error:
                os.chdir(original_folder)
                print(
                    f"Run failed, check your configuration \r\nError from dispatch module is: \r\n"
                    f"{dispatch_error}\r\n"
                )
                traceback.print_exc()
                run_log.write(
                    (
                        f"Run failed, check your configuration \r\nError from dispatch module is: \r\n"
                        f"{dispatch_error}\r\n"
                    ).encode()
                )
                run_log.write(traceback.format_exc().encode())
        
        if utils.normalize_bool(reporting["enable_reporting"]):
            self._reporting_service.send_report_emails(
                settings_dict=settings_dict,
                reporting_config=reporting,
                run_log_path=run_log_path,
                start_time=start_time,
                run_summary=run_summary_string,
                progress_callback=self._build_progress_callback(),
            )
    
    def _automatic_process_directories(self, automatic_process_folders_table) -> None:
        """Process directories in automatic mode without UI.
        
        Args:
            automatic_process_folders_table: The table of folders to process
        """
        if automatic_process_folders_table.count(folder_is_active="True") > 0:
            print("batch processing configured directories")
            try:
                tkinter.ttk.Label(self._root, text="Running In Automatic Mode...").pack(
                    side=tkinter.TOP
                )
                self._root.minsize(400, self._root.winfo_height())
                self._root.update()
                self._process_directories(automatic_process_folders_table)
            except Exception as automatic_process_error:
                self._log_critical_error(automatic_process_error)
        else:
            print("Error, No Active Folders")
        self._database.close()
        raise SystemExit
    
    # -------------------------------------------------------------------------
    # Dialog Methods
    # -------------------------------------------------------------------------
    
    def _show_edit_settings_dialog(self) -> None:
        """Show the EditSettingsDialog with proper dependency injection."""
        EditSettingsDialog(
            self._root,
            self._database.oversight_and_defaults.find_one(id=1),
            settings_provider=lambda: self._database.settings.find_one(id=1),
            oversight_provider=lambda: self._database.oversight_and_defaults.find_one(id=1),
            update_settings=lambda s: self._database.settings.update(s, ["id"]),
            update_oversight=lambda o: self._database.oversight_and_defaults.update(o, ["id"]),
            on_apply=self._update_reporting,
            refresh_callback=self._refresh_users_list,
            count_email_backends=lambda: self._database.folders_table.count(process_backend_email=True),
            count_disabled_folders=lambda: self._database.folders_table.count(
                process_backend_email=True,
                process_backend_ftp=False,
                process_backend_copy=False,
                folder_is_active="True",
            ),
            disable_email_backends=self._disable_all_email_backends,
            disable_folders_without_backends=self._disable_folders_without_backends,
            root=self._root,
        )
    
    def _disable_all_email_backends(self) -> None:
        """Disable email backend for all folders."""
        for email_backend_to_disable in self._database.folders_table.find(
            process_backend_email=True
        ):
            email_backend_to_disable["process_backend_email"] = False
            self._database.folders_table.update(email_backend_to_disable, ["id"])
    
    def _disable_folders_without_backends(self) -> None:
        """Disable folders that have no active backends."""
        for folder_to_disable in self._database.folders_table.find(
            process_backend_email=False,
            process_backend_ftp=False,
            process_backend_copy=False,
            folder_is_active="True",
        ):
            folder_to_disable["folder_is_active"] = "False"
            self._database.folders_table.update(folder_to_disable, ["id"])
    
    def _update_reporting(self, changes: dict) -> None:
        """Update reporting settings.
        
        Args:
            changes: The settings changes to apply
        """
        self._database.oversight_and_defaults.update(changes, ["id"])
    
    def _set_defaults_popup(self) -> None:
        """Show the defaults popup dialog."""
        defaults = self._database.oversight_and_defaults.find_one(id=1)
        if defaults is None:
            defaults = {}
        defaults.setdefault("copy_to_directory", "")
        defaults.setdefault(
            "logs_directory",
            os.path.join(os.path.expanduser("~"), "BatchFileSenderLogs"),
        )
        defaults.setdefault("enable_reporting", False)
        defaults.setdefault("report_email_destination", "")
        defaults.setdefault("report_edi_errors", False)
        defaults.setdefault("folder_name", "template")
        defaults.setdefault("folder_is_active", "True")
        defaults.setdefault("alias", "")
        defaults.setdefault("process_backend_copy", False)
        defaults.setdefault("process_backend_ftp", False)
        defaults.setdefault("process_backend_email", False)
        defaults.setdefault("ftp_server", "")
        defaults.setdefault("ftp_port", 21)
        defaults.setdefault("ftp_folder", "")
        defaults.setdefault("ftp_username", "")
        defaults.setdefault("ftp_password", "")
        defaults.setdefault("email_to", "")
        defaults.setdefault("email_subject_line", "")
        defaults.setdefault("process_edi", "False")
        defaults.setdefault("convert_to_format", "csv")
        defaults.setdefault("calculate_upc_check_digit", "False")
        defaults.setdefault("include_a_records", "False")
        defaults.setdefault("include_c_records", "False")
        defaults.setdefault("include_headers", "False")
        defaults.setdefault("filter_ampersand", "False")
        defaults.setdefault("tweak_edi", False)
        defaults.setdefault("split_edi", False)
        defaults.setdefault("split_edi_include_invoices", False)
        defaults.setdefault("split_edi_include_credits", False)
        defaults.setdefault("prepend_date_files", False)
        defaults.setdefault("split_edi_filter_categories", "ALL")
        defaults.setdefault("split_edi_filter_mode", "include")
        defaults.setdefault("rename_file", "")
        defaults.setdefault("pad_a_records", "False")
        defaults.setdefault("a_record_padding", "")
        defaults.setdefault("a_record_padding_length", 6)
        defaults.setdefault("append_a_records", "False")
        defaults.setdefault("a_record_append_text", "")
        defaults.setdefault("force_txt_file_ext", "False")
        defaults.setdefault("invoice_date_offset", 0)
        defaults.setdefault("invoice_date_custom_format", False)
        defaults.setdefault("invoice_date_custom_format_string", "%Y%m%d")
        defaults.setdefault("retail_uom", False)
        defaults.setdefault("force_edi_validation", False)
        defaults.setdefault("override_upc_bool", False)
        defaults.setdefault("override_upc_level", 1)
        defaults.setdefault("override_upc_category_filter", "")
        defaults.setdefault("upc_target_length", 11)
        defaults.setdefault("upc_padding_pattern", "           ")
        defaults.setdefault("include_item_numbers", False)
        defaults.setdefault("include_item_description", False)
        defaults.setdefault("simple_csv_sort_order", "")
        defaults.setdefault("split_prepaid_sales_tax_crec", False)
        defaults.setdefault("estore_store_number", "")
        defaults.setdefault("estore_Vendor_OId", "")
        defaults.setdefault("estore_vendor_NameVendorOID", "")
        defaults.setdefault("estore_c_record_OID", "")
        defaults.setdefault("fintech_division_id", "")
        EditFoldersDialog(self._root, defaults)
    
    def _show_maintenance_dialog_wrapper(self) -> None:
        """Show the maintenance dialog using the extracted module."""
        show_maintenance_dialog(
            root=self._root,
            database_obj=self._database,
            database_path=self._database_path,
            running_platform=self._running_platform,
            database_version=self._database_version,
            refresh_callback=self._refresh_users_list,
            set_button_states_callback=self._set_main_button_states,
            delete_folder_callback=self._folder_manager.delete_folder_with_related,
        )
    
    def _show_processed_files_dialog_wrapper(self) -> None:
        """Show the processed files dialog using the extracted module."""
        show_processed_files_dialog(
            root=self._root,
            database_obj=self._database,
        )
    
    def _mark_active_as_processed_wrapper(
        self, master: tkinter.Tk, selected_folder: Optional[int] = None
    ) -> None:
        """Mark files as processed using the MaintenanceFunctions class.
        
        Args:
            master: The parent window
            selected_folder: Optional folder ID to mark
        """
        import doingstuffoverlay as _overlay
        from interface.services.progress_service import ProgressCallback

        class _TkProgressCb:
            def show(self, message: str = "") -> None:
                _overlay.make_overlay(master, message)

            def hide(self) -> None:
                _overlay.destroy_overlay()
                master.update()

            def update_message(self, message: str) -> None:
                _overlay.update_overlay(parent=master, overlay_text=message)

            def is_visible(self) -> bool:
                return _overlay.doing_stuff_frame is not None

        maintenance = MaintenanceFunctions(
            database_obj=self._database,
            refresh_callback=self._refresh_users_list,
            set_button_states_callback=self._set_main_button_states,
            delete_folder_callback=self._folder_manager.delete_folder_with_related,
            database_path=self._database_path,
            running_platform=self._running_platform,
            database_version=self._database_version,
            progress_callback=_TkProgressCb(),
        )
        maintenance.mark_active_as_processed(selected_folder=selected_folder)
    
    def _build_progress_callback(self):
        import doingstuffoverlay as _overlay
        from interface.services.progress_service import NullProgressCallback

        if self._args is not None and self._args.automatic:
            class _AutoProgressCb:
                def __init__(self, feedback_text):
                    self._feedback_text = feedback_text

                def show(self, message: str = "") -> None:
                    if self._feedback_text is not None:
                        self._feedback_text.configure(text=message)

                def hide(self) -> None:
                    pass

                def update_message(self, message: str) -> None:
                    if self._feedback_text is not None:
                        self._feedback_text.configure(text=message)

                def is_visible(self) -> bool:
                    return True

            return _AutoProgressCb(self._feedback_text)

        root = self._root

        class _TkProgressCb:
            def show(self, message: str = "") -> None:
                _overlay.destroy_overlay()
                _overlay.make_overlay(root, message)

            def hide(self) -> None:
                _overlay.destroy_overlay()

            def update_message(self, message: str) -> None:
                _overlay.update_overlay(parent=root, overlay_text=message)
                root.update()

            def is_visible(self) -> bool:
                return _overlay.doing_stuff_frame is not None

        return _TkProgressCb()
    
    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------
    
    def _check_logs_directory(self) -> bool:
        """Check if the logs directory is writable.
        
        Returns:
            True if the directory is writable, False otherwise
        """
        try:
            test_file_path = os.path.join(
                self._logs_directory["logs_directory"], "test_log_file"
            )
            with open(test_file_path, "w", encoding="utf-8") as test_log_file:
                test_log_file.write("teststring")
            os.remove(test_file_path)
            return True
        except IOError as log_directory_error:
            print(str(log_directory_error))
            return False
    
    def _log_critical_error(self, error: Exception) -> None:
        """Log a critical error to the critical_error.log file and exit.
        
        Args:
            error: The error to log
            
        Raises:
            SystemExit: Always exits after logging
        """
        try:
            print(str(error))
            with open("critical_error.log", "a", encoding="utf-8") as critical_log:
                critical_log.write(f"program version is {self._version}")
                critical_log.write(f"{datetime.datetime.now()}{error}\r\n")
            raise SystemExit from error
        except Exception as big_error:
            print("error writing critical error log...")
            raise SystemExit from big_error
    
    @staticmethod
    def _attach_right_click_menu(entry_widget: tkinter.ttk.Entry) -> None:
        """Attach a right-click context menu to an entry widget.
        
        Args:
            entry_widget: A tkinter Entry widget to attach the menu to
        """
        rclick_menu = tk_extra_widgets.RightClickMenu(entry_widget)
        entry_widget.bind("<3>", rclick_menu)


def main():
    """Main entry point for the application."""
    app = BatchFileSenderApp(
        appname="Batch File Sender",
        version="(Git Branch: Master)",
        database_version="33"
    )
    app.initialize()
    app.run()
    app.shutdown()


if __name__ == "__main__":
    main()