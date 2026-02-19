"""Qt reimplementation of the Batch File Sender main application window.

Provides :class:`QtBatchFileSenderApp`, which mirrors the public API of
:class:`~interface.app.BatchFileSenderApp` (``initialize``, ``run``,
``shutdown``) while using PyQt6 for all UI rendering.
"""

from __future__ import annotations

import argparse
import datetime
import multiprocessing
import os
import platform
import sys
import time
import traceback
from typing import Any, Optional

import appdirs
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QSpacerItem,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from interface.database.database_obj import DatabaseObj
from interface.operations.folder_manager import FolderManager
from interface.ports import ProgressServiceProtocol, UIServiceProtocol
from interface.services.reporting_service import ReportingService

import batch_log_sender
import print_run_log
import utils
import backup_increment


class QtBatchFileSenderApp:
    """Qt-based main application window for Batch File Sender.

    Drop-in replacement for :class:`~interface.app.BatchFileSenderApp` using
    PyQt6 instead of Tkinter.  The constructor accepts the same DI-friendly
    parameters and the class exposes the same ``initialize`` / ``run`` /
    ``shutdown`` lifecycle methods.
    """

    def __init__(
        self,
        appname: str = "Batch File Sender",
        version: str = "(Git Branch: Master)",
        database_version: str = "33",
        database_obj: Optional[DatabaseObj] = None,
        ui_service: Optional[UIServiceProtocol] = None,
        progress_service: Optional[ProgressServiceProtocol] = None,
    ) -> None:
        self._appname = appname
        self._version = version
        self._database_version = database_version

        self._database: Optional[DatabaseObj] = database_obj
        self._ui_service: Optional[UIServiceProtocol] = ui_service
        self._progress_service: Optional[ProgressServiceProtocol] = progress_service

        self._running_platform = platform.system()

        self._config_folder: Optional[str] = None
        self._database_path: Optional[str] = None

        self._folder_manager: Optional[FolderManager] = None
        self._reporting_service: Optional[ReportingService] = None

        self._app: Optional[QApplication] = None
        self._window: Optional[QMainWindow] = None

        self._folder_filter = ""

        self._folder_list_widget: Optional[Any] = None
        self._search_widget: Optional[Any] = None
        self._right_panel_widget: Optional[QWidget] = None

        self._process_folder_button: Optional[QPushButton] = None
        self._processed_files_button: Optional[QPushButton] = None
        self._allow_resend_button: Optional[QPushButton] = None

        self._args: Optional[argparse.Namespace] = None

        self._logs_directory: Optional[dict] = None
        self._errors_directory: Optional[dict] = None

    @property
    def database(self) -> DatabaseObj:
        if self._database is None:
            raise RuntimeError("Database not initialized - call initialize() first")
        return self._database

    @property
    def folder_manager(self) -> FolderManager:
        if self._folder_manager is None:
            raise RuntimeError("Folder manager not initialized - call initialize() first")
        return self._folder_manager

    @property
    def args(self) -> argparse.Namespace:
        if self._args is None:
            raise RuntimeError("Arguments not parsed - call initialize() first")
        return self._args

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        multiprocessing.freeze_support()
        print(f"{self._appname} Version {self._version}")
        print(f"Running on {self._running_platform}")

        self._parse_arguments()
        self._setup_config_directories()

        if self._database is None:
            self._database = DatabaseObj(
                self._database_path,
                self._database_version,
                self._config_folder,
                self._running_platform,
            )

        self._folder_manager = FolderManager(self._database)
        self._reporting_service = ReportingService(
            database=self._database,
            batch_log_sender_module=batch_log_sender,
            print_run_log_module=print_run_log,
            utils_module=utils,
        )

        self._logs_directory = self._database.oversight_and_defaults.find_one(id=1)
        self._errors_directory = self._database.oversight_and_defaults.find_one(id=1)

        if self._args.automatic:
            self._automatic_process_directories(self._database.folders_table)
            return

        self._app = QApplication.instance() or QApplication(sys.argv)
        self._window = QMainWindow()
        self._window.setWindowTitle(f"{self._appname} {self._version}")

        if self._ui_service is None:
            from interface.qt.services.qt_services import QtUIService
            self._ui_service = QtUIService(self._window)

        if self._progress_service is None:
            from interface.qt.services.qt_services import QtProgressService
            self._progress_service = QtProgressService(self._window)

        self._build_main_window()
        self._set_main_button_states()
        self._configure_window()

    def run(self) -> None:
        if self._args is not None and self._args.automatic:
            return
        if self._window is None:
            raise RuntimeError("Application not initialized - call initialize() first")
        self._window.show()
        QApplication.exec()

    def shutdown(self) -> None:
        if self._database is not None:
            self._database.close()

    # ------------------------------------------------------------------
    # Argument parsing / config
    # ------------------------------------------------------------------

    def _parse_arguments(self) -> None:
        launch_options = argparse.ArgumentParser()
        launch_options.add_argument("-a", "--automatic", action="store_true")
        self._args = launch_options.parse_args()

    def _setup_config_directories(self) -> None:
        self._config_folder = appdirs.user_data_dir(self._appname)
        self._database_path = os.path.join(self._config_folder, "folders.db")
        try:
            os.makedirs(self._config_folder)
        except FileExistsError:
            pass

    # ------------------------------------------------------------------
    # Window construction
    # ------------------------------------------------------------------

    def _configure_window(self) -> None:
        self._window.adjustSize()
        self._window.setMinimumSize(self._window.size())
        self._window.setFixedWidth(self._window.size().width())

    def _build_main_window(self) -> None:
        central = QWidget()
        self._window.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        options_widget = QWidget()
        options_widget.setFixedWidth(200)
        options_layout = QVBoxLayout(options_widget)
        options_layout.setContentsMargins(4, 4, 4, 4)
        options_layout.setSpacing(2)

        add_dir_btn = QPushButton("Add Directory...")
        add_dir_btn.clicked.connect(self._select_folder)
        options_layout.addWidget(add_dir_btn)

        batch_add_btn = QPushButton("Batch Add Directories...")
        batch_add_btn.clicked.connect(self._batch_add_folders)
        options_layout.addWidget(batch_add_btn)

        defaults_btn = QPushButton("Set Defaults...")
        defaults_btn.clicked.connect(self._set_defaults_popup)
        options_layout.addWidget(defaults_btn)

        edit_settings_btn = QPushButton("Edit Settings...")
        edit_settings_btn.clicked.connect(self._show_edit_settings_dialog)
        options_layout.addWidget(edit_settings_btn)

        maintenance_btn = QPushButton("Maintenance...")
        maintenance_btn.clicked.connect(self._show_maintenance_dialog_wrapper)
        options_layout.addWidget(maintenance_btn)

        self._processed_files_button = QPushButton("Processed Files Report...")
        self._processed_files_button.clicked.connect(self._show_processed_files_dialog_wrapper)
        options_layout.addWidget(self._processed_files_button)

        options_layout.addItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )

        self._allow_resend_button = QPushButton("Enable Resend...")
        self._allow_resend_button.clicked.connect(self._show_resend_dialog)
        options_layout.addWidget(self._allow_resend_button)

        sep_h = QFrame()
        sep_h.setFrameShape(QFrame.Shape.HLine)
        sep_h.setFrameShadow(QFrame.Shadow.Sunken)
        options_layout.addWidget(sep_h)

        self._process_folder_button = QPushButton("Process All Folders")
        self._process_folder_button.clicked.connect(
            lambda: self._graphical_process_directories(self._database.folders_table)
        )
        options_layout.addWidget(self._process_folder_button)

        main_layout.addWidget(options_widget)

        sep_v = QFrame()
        sep_v.setFrameShape(QFrame.Shape.VLine)
        sep_v.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(sep_v)

        self._right_panel_widget = QWidget()
        right_layout = QVBoxLayout(self._right_panel_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self._build_folder_list(right_layout)

        main_layout.addWidget(self._right_panel_widget, stretch=1)

    def _build_folder_list(self, parent_layout: QVBoxLayout) -> None:
        from interface.qt.widgets.folder_list_widget import FolderListWidget
        from interface.qt.widgets.search_widget import SearchWidget

        self._folder_list_widget = FolderListWidget(
            parent=self._right_panel_widget,
            folders_table=self._database.folders_table,
            on_send=self._send_single,
            on_edit=self._edit_folder_selector,
            on_disable=self._disable_folder,
            on_delete=self._delete_folder_entry_wrapper,
            filter_value=self._folder_filter,
            total_count_callback=self._update_filter_count_label,
        )

        self._search_widget = SearchWidget(
            parent=self._right_panel_widget,
            initial_value=self._folder_filter,
            on_filter_change=self._set_folders_filter,
        )

        if self._database.folders_table.count() == 0:
            self._search_widget.set_enabled(False)

        parent_layout.addWidget(self._folder_list_widget, stretch=1)
        parent_layout.addWidget(self._search_widget)

    # ------------------------------------------------------------------
    # Refresh helpers
    # ------------------------------------------------------------------

    def _refresh_users_list(self) -> None:
        if self._right_panel_widget is None:
            return

        layout = self._right_panel_widget.layout()

        if self._folder_list_widget is not None:
            layout.removeWidget(self._folder_list_widget)
            self._folder_list_widget.setParent(None)
            self._folder_list_widget.deleteLater()
            self._folder_list_widget = None

        if self._search_widget is not None:
            layout.removeWidget(self._search_widget)
            self._search_widget.setParent(None)
            self._search_widget.deleteLater()
            self._search_widget = None

        self._build_folder_list(layout)
        self._set_main_button_states()

    def _update_filter_count_label(self, filtered_count: int, total_count: int) -> None:
        pass

    def _set_main_button_states(self) -> None:
        folder_count = self._database.folders_table.count()
        active_count = self._database.folders_table.count(folder_is_active="True")
        processed_count = self._database.processed_files.count()

        if folder_count == 0 or active_count == 0:
            self._process_folder_button.setEnabled(False)
        else:
            self._process_folder_button.setEnabled(True)

        has_processed = processed_count > 0
        self._processed_files_button.setEnabled(has_processed)
        self._allow_resend_button.setEnabled(has_processed)

    # ------------------------------------------------------------------
    # Folder operations
    # ------------------------------------------------------------------

    def _select_folder(self) -> None:
        prior_folder = self._database.oversight_and_defaults.find_one(id=1)
        initial_directory = prior_folder.get("single_add_folder_prior", "")
        if not initial_directory or not os.path.exists(initial_directory):
            initial_directory = os.path.expanduser("~")

        selected_folder = self._ui_service.ask_directory(
            title="Select Directory", initial_dir=initial_directory
        )
        if not selected_folder or not os.path.exists(selected_folder):
            return

        self._database.oversight_and_defaults.update(
            {"id": 1, "single_add_folder_prior": selected_folder}, ["id"]
        )
        proposed_folder = self._folder_manager.check_folder_exists(selected_folder)

        if proposed_folder["truefalse"] is False:
            self._progress_service.show("Adding Folder...")
            self._folder_manager.add_folder(selected_folder)
            if self._ui_service.ask_yes_no(
                "Mark Processed",
                "Do you want to mark files in folder as processed?",
            ):
                folder_dict = self._database.folders_table.find_one(
                    folder_name=selected_folder
                )
                self._mark_active_as_processed_wrapper(folder_dict["id"])
            self._progress_service.hide()
            self._refresh_users_list()
        else:
            proposed_folder_dict = proposed_folder["matched_folder"]
            if self._ui_service.ask_ok_cancel(
                "Query:", "Folder already known, would you like to edit?"
            ):
                self._open_edit_folders_dialog(proposed_folder_dict)

    def _batch_add_folders(self) -> None:
        prior_folder = self._database.oversight_and_defaults.find_one(id=1)
        starting_directory = os.getcwd()
        initial = prior_folder.get("batch_add_folder_prior") or os.path.expanduser("~")

        selection = self._ui_service.ask_directory(
            title="Select Parent Directory", initial_dir=initial
        )
        if not selection:
            return

        self._database.oversight_and_defaults.update(
            {"id": 1, "batch_add_folder_prior": selection}, ["id"]
        )

        folders_to_add = [
            os.path.join(selection, f)
            for f in os.listdir(selection)
            if os.path.isdir(os.path.join(selection, f))
        ]
        if not self._ui_service.ask_ok_cancel(
            "Confirm",
            f"This will add {len(folders_to_add)} directories, are you sure?",
        ):
            return

        self._progress_service.show("Adding folders...")
        added, skipped = 0, 0
        for folder in folders_to_add:
            self._progress_service.update_message(
                f"Adding folders... ({added + skipped + 1}/{len(folders_to_add)})"
            )
            if self._folder_manager.check_folder_exists(folder)["truefalse"]:
                skipped += 1
            else:
                self._folder_manager.add_folder(folder)
                added += 1

        print(f"done adding {added} folders")
        self._progress_service.hide()
        self._ui_service.show_info(
            "Batch Add Complete",
            f"{added} folders added, {skipped} folders skipped.",
        )
        self._refresh_users_list()
        os.chdir(starting_directory)

    def _edit_folder_selector(self, folder_to_be_edited: int) -> None:
        edit_folder = self._database.folders_table.find_one(id=[folder_to_be_edited])
        self._open_edit_folders_dialog(edit_folder)

    def _send_single(self, folder_id: int) -> None:
        self._progress_service.show("Working...")
        try:
            single_table = self._database.session_database["single_table"]
            single_table.drop()
        finally:
            single_table = self._database.session_database["single_table"]
            table_dict = self._database.folders_table.find_one(id=folder_id)
            table_dict["old_id"] = table_dict.pop("id")
            single_table.insert(table_dict)
            self._progress_service.hide()
            self._graphical_process_directories(single_table)
            single_table.drop()

    def _disable_folder(self, folder_id: int) -> None:
        self._folder_manager.disable_folder(folder_id)
        self._refresh_users_list()

    def _set_folders_filter(self, filter_field_contents: str) -> None:
        self._folder_filter = filter_field_contents
        self._refresh_users_list()

    def _delete_folder_entry_wrapper(self, folder_to_be_removed: int, alias: str) -> None:
        if self._ui_service.ask_yes_no(
            "Confirm Delete",
            f"Are you sure you want to remove the folder {alias}?",
        ):
            self._folder_manager.delete_folder_with_related(folder_to_be_removed)
            self._refresh_users_list()
            self._set_main_button_states()

    # ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------

    def _graphical_process_directories(self, folders_table_process) -> None:
        missing_folder = False
        for folder_test in folders_table_process.find(folder_is_active="True"):
            if not os.path.exists(folder_test["folder_name"]):
                missing_folder = True

        if missing_folder:
            self._ui_service.show_error(
                "Error", "One or more expected folders are missing."
            )
        elif folders_table_process.count(folder_is_active="True") > 0:
            self._progress_service.show("processing folders...")
            self._process_directories(folders_table_process)
            self._refresh_users_list()
            self._set_main_button_states()
            self._progress_service.hide()
        else:
            self._ui_service.show_error("Error", "No Active Folders")

    def _process_directories(self, folders_table_process) -> None:
        original_folder = os.getcwd()
        settings_dict = self._database.settings.find_one(id=1)

        if (
            settings_dict["enable_interval_backups"]
            and settings_dict["backup_counter"] >= settings_dict["backup_counter_maximum"]
        ):
            backup_increment.do_backup(self._database_path)
            settings_dict["backup_counter"] = 0
        settings_dict["backup_counter"] += 1
        self._database.settings.update(settings_dict, ["id"])

        log_folder_creation_error = False
        start_time = str(datetime.datetime.now())
        reporting = self._database.oversight_and_defaults.find_one(id=1)
        run_log_name_constructor = "Run Log " + str(time.ctime()).replace(":", "-") + ".txt"

        if not os.path.isdir(self._logs_directory["logs_directory"]):
            try:
                os.mkdir(self._logs_directory["logs_directory"])
            except IOError:
                log_folder_creation_error = True

        if not self._check_logs_directory() or log_folder_creation_error:
            if not self._args.automatic:
                while not self._check_logs_directory():
                    if self._ui_service.ask_ok_cancel(
                        "Error",
                        "Can't write to log directory,\r\n"
                        " would you like to change reporting settings?",
                    ):
                        self._show_edit_settings_dialog()
                    else:
                        self._ui_service.show_error(
                            "Error", "Can't write to log directory, exiting"
                        )
                        raise SystemExit
            else:
                self._log_critical_error(
                    "can't write into logs directory. in automatic mode, so no prompt",
                )

        run_log_path = str(reporting["logs_directory"])
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
                import dispatch

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
                    progress_callback=self._progress_service,
                )
                if run_error_bool and not self._args.automatic:
                    self._ui_service.show_info(
                        "Run Status", "Run completed with errors."
                    )
                os.chdir(original_folder)
            except Exception as dispatch_error:
                os.chdir(original_folder)
                print(
                    f"Run failed, check your configuration \r\n"
                    f"Error from dispatch module is: \r\n{dispatch_error}\r\n"
                )
                traceback.print_exc()
                run_log.write(
                    (
                        f"Run failed, check your configuration \r\n"
                        f"Error from dispatch module is: \r\n{dispatch_error}\r\n"
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
                progress_callback=self._progress_service,
            )

    def _automatic_process_directories(self, automatic_process_folders_table) -> None:
        if automatic_process_folders_table.count(folder_is_active="True") > 0:
            print("batch processing configured directories")
            try:
                self._process_directories(automatic_process_folders_table)
            except Exception as automatic_process_error:
                self._log_critical_error(automatic_process_error)
        else:
            print("Error, No Active Folders")
        self._database.close()
        sys.exit()

    # ------------------------------------------------------------------
    # Dialogs
    # ------------------------------------------------------------------

    def _open_edit_folders_dialog(self, folder_config: dict) -> None:
        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog

        dlg = EditFoldersDialog(
            self._window,
            folder_config,
            on_apply_success=self._on_folder_edit_applied,
        )
        if dlg.exec():
            self._refresh_users_list()
            self._set_main_button_states()

    def _on_folder_edit_applied(self, folder_config: dict) -> None:
        """Persist folder configuration changes after dialog apply."""
        self._database.folders_table.update(folder_config, ["id"])

    def _set_defaults_popup(self) -> None:
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
        self._open_edit_folders_dialog(defaults)

    def _show_edit_settings_dialog(self) -> None:
        from interface.qt.dialogs.edit_settings_dialog import EditSettingsDialog

        EditSettingsDialog(
            self._window,
            self._database.oversight_and_defaults.find_one(id=1),
            settings_provider=lambda: self._database.settings.find_one(id=1),
            oversight_provider=lambda: self._database.oversight_and_defaults.find_one(id=1),
            update_settings=lambda s: self._database.settings.update(s, ["id"]),
            update_oversight=lambda o: self._database.oversight_and_defaults.update(o, ["id"]),
            on_apply=self._update_reporting,
            refresh_callback=self._refresh_users_list,
            count_email_backends=lambda: self._database.folders_table.count(
                process_backend_email=True
            ),
            count_disabled_folders=lambda: self._database.folders_table.count(
                process_backend_email=True,
                process_backend_ftp=False,
                process_backend_copy=False,
                folder_is_active="True",
            ),
            disable_email_backends=self._disable_all_email_backends,
            disable_folders_without_backends=self._disable_folders_without_backends,
        ).exec()

    def _show_maintenance_dialog_wrapper(self) -> None:
        from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog
        from interface.qt.dialogs.database_import_dialog import show_database_import_dialog
        from interface.ui.dialogs.maintenance_dialog import MaintenanceFunctions

        backup_increment.do_backup(self._database_path)

        def database_import_callback(backup_path: str) -> bool:
            """Callback to show database import dialog."""
            try:
                show_database_import_dialog(
                    parent=self._window,
                    original_database_path=self._database_path,
                    running_platform=self._running_platform,
                    backup_path=backup_path,
                    current_db_version=self._database_version,
                )
                return True
            except Exception as e:
                print(f"Database import failed: {e}")
                return False

        maintenance = MaintenanceFunctions(
            database_obj=self._database,
            refresh_callback=self._refresh_users_list,
            set_button_states_callback=self._set_main_button_states,
            delete_folder_callback=self._folder_manager.delete_folder_with_related,
            database_path=self._database_path,
            running_platform=self._running_platform,
            database_version=self._database_version,
            progress_callback=self._progress_service,
            confirm_callback=lambda msg: self._ui_service.ask_ok_cancel("Confirm", msg),
            database_import_callback=database_import_callback,
        )

        MaintenanceDialog.open_dialog(
            parent=self._window,
            maintenance_functions=maintenance,
            ui_service=self._ui_service,
        )

    def _show_processed_files_dialog_wrapper(self) -> None:
        from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog

        dlg = ProcessedFilesDialog(
            parent=self._window,
            database_obj=self._database,
            ui_service=self._ui_service,
        )
        dlg.exec()

    def _show_resend_dialog(self) -> None:
        from interface.qt.dialogs.resend_dialog import ResendDialog
        from interface.services.resend_service import ResendService

        resend_service = ResendService(self._database.database_connection)
        dlg = ResendDialog(parent=self._window, resend_service=resend_service)
        dlg.exec()

    # ------------------------------------------------------------------
    # Settings helpers
    # ------------------------------------------------------------------

    def _disable_all_email_backends(self) -> None:
        for row in self._database.folders_table.find(process_backend_email=True):
            row["process_backend_email"] = False
            self._database.folders_table.update(row, ["id"])

    def _disable_folders_without_backends(self) -> None:
        for row in self._database.folders_table.find(
            process_backend_email=False,
            process_backend_ftp=False,
            process_backend_copy=False,
            folder_is_active="True",
        ):
            row["folder_is_active"] = "False"
            self._database.folders_table.update(row, ["id"])

    def _update_reporting(self, changes: dict) -> None:
        self._database.oversight_and_defaults.update(changes, ["id"])

    # ------------------------------------------------------------------
    # Mark-as-processed helper
    # ------------------------------------------------------------------

    def _mark_active_as_processed_wrapper(self, selected_folder: Optional[int] = None) -> None:
        from interface.ui.dialogs.maintenance_dialog import MaintenanceFunctions

        maintenance = MaintenanceFunctions(
            database_obj=self._database,
            refresh_callback=self._refresh_users_list,
            set_button_states_callback=self._set_main_button_states,
            delete_folder_callback=self._folder_manager.delete_folder_with_related,
            database_path=self._database_path,
            running_platform=self._running_platform,
            database_version=self._database_version,
            progress_callback=self._progress_service,
        )
        maintenance.mark_active_as_processed(selected_folder=selected_folder)

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def _check_logs_directory(self) -> bool:
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

    def _log_critical_error(self, error) -> None:
        try:
            print(str(error))
            with open("critical_error.log", "a", encoding="utf-8") as critical_log:
                critical_log.write(f"program version is {self._version}")
                critical_log.write(f"{datetime.datetime.now()}{error}\r\n")
            raise SystemExit from error if isinstance(error, Exception) else SystemExit(str(error))
        except SystemExit:
            raise
        except Exception as big_error:
            print("error writing critical error log...")
            raise SystemExit from big_error


def main() -> None:
    app = QtBatchFileSenderApp(
        appname="Batch File Sender",
        version="(Git Branch: Master)",
        database_version="33",
    )
    app.initialize()
    app.run()
    app.shutdown()


if __name__ == "__main__":
    main()
