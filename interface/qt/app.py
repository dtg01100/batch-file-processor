"""Qt reimplementation of the Batch File Sender main application window.

Provides :class:`QtBatchFileSenderApp`, which mirrors the public API of
:class:`~interface.app.BatchFileSenderApp` (``initialize``, ``run``,
``shutdown``) while using PyQt6 for all UI rendering.
"""

from __future__ import annotations

import argparse
import datetime
import logging
import multiprocessing
import os
import platform
import sys
from typing import Any, Optional

import appdirs
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QWidget

import scripts.backup_increment as backup_increment
import scripts.batch_log_sender as batch_log_sender
import scripts.print_run_log as print_run_log
import core.utils
from adapters.sqlite.repositories import (
    SqliteFolderRepository,
    SqliteProcessedFilesRepository,
    SqliteSettingsRepository,
)
from backend.database.database_obj import DatabaseObj
from core.constants import CURRENT_DATABASE_VERSION
from interface.operations.folder_manager import FolderManager
from interface.ports import ProgressServiceProtocol, UIServiceProtocol
from interface.qt.bootstrap import QtAppBootstrapService
from interface.qt.diagnostics import QtDiagnosticsService
from interface.qt.run_coordinator import QtRunCoordinator
from interface.qt.window_controller import QtMainWindowController
from interface.services.reporting_service import ReportingService

logger = logging.getLogger(__name__)


class QtBatchFileSenderApp:
    """Qt-based main application window for Batch File Sender."""

    def __init__(
        self,
        appname: str = "Batch File Sender",
        version: str = "(Git Branch: Master)",
        database_version: str = CURRENT_DATABASE_VERSION,
        database_obj: Optional[DatabaseObj] = None,
        folder_manager: Optional[FolderManager] = None,
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
        self._appdirs_module = appdirs
        self._sys_module = sys
        self._os_module = os
        self._utils_module = utils
        self._backup_increment_module = backup_increment

        self._config_folder: Optional[str] = None
        self._database_path: Optional[str] = None

        self._folder_manager: Optional[FolderManager] = folder_manager
        self._folder_repo: Optional[Any] = None
        self._settings_repo: Optional[Any] = None
        self._processed_files_repo: Optional[Any] = None
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

        self._bootstrap = QtAppBootstrapService(self)
        self._window_controller = QtMainWindowController(self)
        self._run_coordinator = QtRunCoordinator(self)
        self._diagnostics = QtDiagnosticsService(self)

    @property
    def database(self) -> DatabaseObj:
        if self._database is None:
            raise RuntimeError("Database not initialized - call initialize() first")
        return self._database

    @property
    def folder_manager(self) -> FolderManager:
        if self._folder_manager is None:
            raise RuntimeError(
                "Folder manager not initialized - call initialize() first"
            )
        return self._folder_manager

    @property
    def args(self) -> argparse.Namespace:
        if self._args is None:
            raise RuntimeError("Arguments not parsed - call initialize() first")
        return self._args

    def _run_self_test(self) -> int:
        return self._diagnostics.run_self_test()

    def _get_qapplication_cls(self):
        return QApplication

    def _get_qmainwindow_cls(self):
        return QMainWindow

    def _run_gui_self_test(self) -> int:
        return self._diagnostics.run_gui_self_test()

    def initialize(self, args: Optional[list[str]] = None) -> None:
        multiprocessing.freeze_support()

        self._configure_qt_platform()

        print(f"{self._appname} Version {self._version}")
        print(f"Running on {self._running_platform}")

        self._parse_arguments(args)

        if self._args and self._args.self_test:
            exit_code = self._run_self_test()
            sys.exit(exit_code)

        if self._args and self._args.gui_test:
            exit_code = self._run_gui_self_test()
            sys.exit(exit_code)

        self._setup_config_directories()

        if self._database is None:
            if self._database_path is None or self._config_folder is None:
                raise RuntimeError("Configuration directories not initialized")
            self._database = DatabaseObj(
                self._database_path,
                self._database_version,
                self._config_folder,
                self._running_platform,
            )

        self._folder_repo = SqliteFolderRepository(self._database)
        self._settings_repo = SqliteSettingsRepository(self._database)
        self._processed_files_repo = SqliteProcessedFilesRepository(self._database)

        if self._folder_manager is None:
            self._folder_manager = FolderManager(
                database=self._database,
                folder_repo=self._folder_repo,
                settings_repo=self._settings_repo,
            )
        self._reporting_service = ReportingService(
            database=self._database,
            batch_log_sender_module=batch_log_sender,
            print_run_log_module=print_run_log,
            utils_module=utils,
        )

        oversight = self._database.get_oversight_or_default()
        self._logs_directory = oversight
        self._errors_directory = oversight

        if self._args and self._args.automatic:
            # Automatic mode: skip GUI setup entirely; run() will process.
            return

        self._bootstrap.build_ui_runtime()
        self._build_main_window()
        self._set_main_button_states()
        self._configure_window()

    def run(self) -> int:
        if self._args is not None and self._args.automatic:
            self._automatic_process_directories(self._database.folders_table)
            return 0
        if self._window is None:
            raise RuntimeError("Application not initialized - call initialize() first")
        self._window.show()
        if self._args is not None and getattr(self._args, "graphical_automatic", False):
            QTimer.singleShot(
                500,
                lambda: self._graphical_process_directories(
                    self._database.folders_table
                ),
            )
        QApplication.exec()

    def shutdown(self) -> None:
        if self._progress_service is not None:
            disposer = getattr(self._progress_service, "dispose", None)
            if callable(disposer):
                try:
                    disposer()
                except Exception:
                    logger.debug(
                        "Failed to dispose progress service during shutdown",
                        exc_info=True,
                    )

        if self._window is not None:
            try:
                self._window.close()
                self._window.deleteLater()
            except Exception:
                logger.debug(
                    "Failed to close and delete main window during shutdown",
                    exc_info=True,
                )
            self._window = None

        try:
            if QApplication.instance() is not None:
                # Process events multiple times to fully drain pending events
                # (signals, deleteLater calls, timers) left by widget teardown
                for _ in range(10):
                    QApplication.processEvents()
        except Exception:
            logger.debug(
                "Failed to process pending Qt events during shutdown", exc_info=True
            )

        self._ui_service = None
        self._progress_service = None

        if self._database is not None:
            self._database.close()

    def _configure_qt_platform(self) -> None:
        self._bootstrap.configure_qt_platform()

    def _parse_arguments(self, args: Optional[list[str]] = None) -> None:
        self._args = self._bootstrap.parse_arguments(args)

    def _setup_config_directories(self) -> None:
        self._config_folder, self._database_path = (
            self._bootstrap.setup_config_directories()
        )

    def _configure_window(self) -> None:
        self._window_controller.configure_window()

    def _build_main_window(self) -> None:
        self._window_controller.build_main_window()

    def _build_folder_list(self, parent_layout) -> None:
        self._window_controller.build_folder_list(parent_layout)

    def _refresh_users_list(self) -> None:
        self._window_controller.refresh_users_list()

    def _update_filter_count_label(self, filtered_count: int, total_count: int) -> None:
        pass

    def _set_main_button_states(self) -> None:
        self._window_controller.set_main_button_states()

    def _select_folder(self) -> None:
        if (
            self._database is None
            or self._ui_service is None
            or self._folder_manager is None
        ):
            return
        prior_folder = self._database.get_oversight_or_default()
        initial_directory = prior_folder.get("single_add_folder_prior", "")
        if not initial_directory or not os.path.exists(initial_directory):
            initial_directory = os.path.expanduser("~")

        selected_folder = self._ui_service.ask_directory(
            title="Select Directory", initial_dir=initial_directory
        )
        if not selected_folder or not os.path.exists(selected_folder):
            return

        if self._database.oversight_and_defaults:
            self._database.oversight_and_defaults.update(
                {"id": 1, "single_add_folder_prior": selected_folder}, ["id"]
            )
        proposed_folder = self._folder_manager.check_folder_exists(selected_folder)

        if proposed_folder["truefalse"] is False:
            if self._progress_service:
                self._progress_service.show("Adding Folder...")
            self._folder_manager.add_folder(selected_folder)
            if self._ui_service.ask_yes_no(
                "Mark Processed",
                "Do you want to mark files in folder as processed?",
            ):
                if self._database.folders_table:
                    folder_dict = self._database.folders_table.find_one(
                        folder_name=selected_folder
                    )
                    if folder_dict:
                        self._mark_active_as_processed_wrapper(folder_dict["id"])
            if self._progress_service:
                self._progress_service.hide()
            self._refresh_users_list()
        else:
            proposed_folder_dict = proposed_folder["matched_folder"]
            if self._ui_service.ask_ok_cancel(
                "Query:", "Folder already known, would you like to edit?"
            ):
                self._open_edit_folders_dialog(proposed_folder_dict)

    def _batch_add_folders(self) -> None:
        if (
            self._database is None
            or self._ui_service is None
            or self._folder_manager is None
        ):
            return
        prior_folder = self._database.get_oversight_or_default()
        starting_directory = os.getcwd()
        initial = prior_folder.get("batch_add_folder_prior") or os.path.expanduser("~")

        selection = self._ui_service.ask_directory(
            title="Select Parent Directory", initial_dir=initial
        )
        if not selection:
            return

        if self._database.oversight_and_defaults:
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

        if self._progress_service:
            self._progress_service.show("Adding folders...")
        added, skipped = 0, 0
        for folder in folders_to_add:
            if self._progress_service:
                self._progress_service.update_message(
                    f"Adding folders... ({added + skipped + 1}/{len(folders_to_add)})"
                )
            if self._folder_manager.check_folder_exists(folder)["truefalse"]:
                skipped += 1
            else:
                self._folder_manager.add_folder(folder)
                added += 1

        print(f"done adding {added} folders")
        if self._progress_service:
            self._progress_service.hide()
        self._ui_service.show_info(
            "Batch Add Complete",
            f"{added} folders added, {skipped} folders skipped.",
        )
        self._refresh_users_list()
        os.chdir(starting_directory)

    def _edit_folder_selector(self, folder_to_be_edited: int) -> None:
        if self._database is None or self._ui_service is None:
            return
        edit_folder = (
            self._database.folders_table.find_one(id=folder_to_be_edited)
            if self._database.folders_table
            else None
        )
        if edit_folder:
            self._open_edit_folders_dialog(edit_folder)
        else:
            self._ui_service.show_error(
                "Error", f"Folder with id {folder_to_be_edited} not found."
            )

    def _send_single(self, folder_id: int) -> None:
        if (
            self._database is None
            or self._ui_service is None
            or self._progress_service is None
        ):
            return
        self._progress_service.show("Working...")
        try:
            if self._database.session_database:
                single_table = self._database.session_database["single_table"]
                single_table.drop()
        finally:
            if self._database.session_database:
                self._database.session_database.query(
                    "CREATE TABLE IF NOT EXISTS single_table AS SELECT * FROM folders WHERE 0"
                )
                self._database.session_database.query(
                    "ALTER TABLE single_table ADD COLUMN old_id INTEGER"
                )
                single_table = self._database.session_database["single_table"]
                if self._database.folders_table:
                    table_dict = self._database.folders_table.find_one(id=folder_id)
                    if table_dict:
                        table_dict["old_id"] = table_dict.pop("id")
                        # Filter to columns that exist in single_table to handle
                        # schema differences between main and session databases
                        valid_cols = {
                            row["name"]
                            for row in self._database.session_database.query(
                                "PRAGMA table_info(single_table)"
                            )
                        }
                        table_dict = {
                            k: v for k, v in table_dict.items() if k in valid_cols
                        }
                        single_table.insert(table_dict)
                    else:
                        self._ui_service.show_error(
                            "Error", f"Folder with id {folder_id} not found."
                        )
                        return
                self._progress_service.hide()
                if self._database.session_database:
                    self._graphical_process_directories(single_table)
                    single_table.drop()

    def _disable_folder(self, folder_id: int) -> None:
        if self._folder_manager is None:
            return
        self._folder_manager.disable_folder(folder_id)
        self._refresh_users_list()

    def _toggle_folder(self, folder_id: int) -> None:
        if self._folder_manager is None or self._ui_service is None:
            return
        folder = self._folder_manager.get_folder_by_id(folder_id)
        if folder:
            if not folder.get("folder_is_active", False):
                has_backend = (
                    folder.get("process_backend_email")
                    or folder.get("process_backend_ftp")
                    or folder.get("process_backend_copy")
                )
                if not has_backend:
                    self._ui_service.show_error(
                        "Cannot Enable Folder",
                        f"Folder '{folder.get('alias', 'Unknown')}' has no backends configured.\n\n"
                        "Please edit the folder and enable at least one backend:\n"
                        "• Email\n"
                        "• FTP\n"
                        "• Copy to Directory",
                    )
                    return
            if folder.get("folder_is_active", False):
                self._folder_manager.disable_folder(folder_id)
            else:
                self._folder_manager.enable_folder(folder_id)

            # Update only the affected row instead of rebuilding the whole list
            if (
                self._folder_list_widget is not None
                and self._folder_list_widget.update_folder_row(folder_id)
            ):
                self._set_main_button_states()
            else:
                self._refresh_users_list()
                self._set_main_button_states()

    def _set_folders_filter(self, filter_field_contents: str) -> None:
        self._folder_filter = filter_field_contents
        if self._folder_list_widget is not None:
            self._folder_list_widget.apply_filter(filter_field_contents)
        else:
            self._refresh_users_list()

    def _delete_folder_entry_wrapper(
        self, folder_to_be_removed: int, alias: str
    ) -> None:
        if self._ui_service is None or self._folder_manager is None:
            return
        if self._ui_service.ask_yes_no(
            "Confirm Delete",
            f"Are you sure you want to remove the folder {alias}?",
        ):
            self._folder_manager.delete_folder_with_related(folder_to_be_removed)
            self._refresh_users_list()
            self._set_main_button_states()

    def _graphical_process_directories(self, folders_table_process) -> None:
        self._run_coordinator.graphical_process_directories(folders_table_process)

    def _process_directories(self, folders_table_process) -> None:
        self._run_coordinator.process_directories(folders_table_process)

    def _automatic_process_directories(self, automatic_process_folders_table) -> None:
        self._run_coordinator.automatic_process_directories(
            automatic_process_folders_table
        )

    def _open_edit_folders_dialog(self, folder_config: dict) -> None:
        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog

        def _get_aliases() -> list:
            if self._database and self._database.folders_table:
                return [
                    row["alias"]
                    for row in self._database.folders_table.find()
                    if row.get("alias")
                ]
            return []

        def _get_settings() -> dict:
            if self._database and self._database.folders_table:
                return {"folders": self._database.folders_table.find()}
            return {}

        dlg = EditFoldersDialog(
            self._window,
            folder_config,
            on_apply_success=self._on_folder_edit_applied,
            alias_provider=_get_aliases,
            settings_provider=_get_settings,
        )
        if dlg.exec():
            folder_id = folder_config.get("id")
            if (
                folder_id is not None
                and self._folder_list_widget is not None
                and self._folder_list_widget.update_folder_row(folder_id)
            ):
                self._set_main_button_states()
            else:
                self._refresh_users_list()
                self._set_main_button_states()

    def _on_folder_edit_applied(self, folder_config: dict) -> None:
        if self._database is None or self._database.folders_table is None:
            return
        self._database.folders_table.update(folder_config, ["id"])

    def _set_defaults_popup(self) -> None:
        if self._database is None:
            return
        defaults = self._database.get_oversight_or_default()
        defaults = dict(defaults)
        defaults.setdefault("copy_to_directory", "")
        defaults.setdefault(
            "logs_directory",
            os.path.join(os.path.expanduser("~"), "BatchFileSenderLogs"),
        )
        defaults.setdefault("enable_reporting", False)
        defaults.setdefault("report_email_destination", "")
        defaults.setdefault("report_edi_errors", False)
        defaults.setdefault("folder_name", "template")
        defaults.setdefault("folder_is_active", True)
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
        defaults.setdefault("process_edi", False)
        defaults.setdefault("convert_to_format", "csv")
        defaults.setdefault("calculate_upc_check_digit", False)
        defaults.setdefault("include_a_records", False)
        defaults.setdefault("include_c_records", False)
        defaults.setdefault("include_headers", False)
        defaults.setdefault("filter_ampersand", False)
        defaults.setdefault("tweak_edi", False)
        defaults.setdefault("split_edi", False)
        defaults.setdefault("split_edi_include_invoices", False)
        defaults.setdefault("split_edi_include_credits", False)
        defaults.setdefault("prepend_date_files", False)
        defaults.setdefault("split_edi_filter_categories", "ALL")
        defaults.setdefault("split_edi_filter_mode", "include")
        defaults.setdefault("rename_file", "")
        defaults.setdefault("pad_a_records", False)
        defaults.setdefault("a_record_padding", "")
        defaults.setdefault("a_record_padding_length", 6)
        defaults.setdefault("append_a_records", False)
        defaults.setdefault("a_record_append_text", "")
        defaults.setdefault("force_txt_file_ext", False)
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
        if self._database is None:
            return
        from interface.qt.dialogs.edit_settings_dialog import EditSettingsDialog

        EditSettingsDialog(
            self._window,
            self._database.get_oversight_or_default(),
            settings_provider=lambda: (
                self._database.get_settings_or_default() if self._database else {}
            ),
            oversight_provider=lambda: (
                self._database.get_oversight_or_default() if self._database else {}
            ),
            update_settings=lambda s: (
                self._database.settings.update(s, ["id"])
                if self._database and self._database.settings
                else None
            ),
            update_oversight=lambda o: (
                self._database.oversight_and_defaults.update(o, ["id"])
                if self._database and self._database.oversight_and_defaults
                else None
            ),
            on_apply=self._update_reporting,
            refresh_callback=self._refresh_users_list,
            count_email_backends=lambda: (
                self._database.folders_table.count(process_backend_email=True)
                if self._database and self._database.folders_table
                else 0
            ),
            count_disabled_folders=lambda: (
                self._database.folders_table.count(
                    process_backend_email=True,
                    process_backend_ftp=False,
                    process_backend_copy=False,
                    folder_is_active=True,
                )
                if self._database and self._database.folders_table
                else 0
            ),
            disable_email_backends=self._disable_all_email_backends,
            disable_folders_without_backends=self._disable_folders_without_backends,
        ).exec()

    def _show_maintenance_dialog_wrapper(self) -> None:
        from interface.operations.maintenance_functions import MaintenanceFunctions
        from interface.qt.dialogs.database_import_dialog import (
            show_database_import_dialog,
        )
        from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog

        backup_increment.do_backup(self._database_path)

        def database_import_callback(selected_import_db_path: str) -> bool:
            if self._window is None or self._database_path is None:
                return False
            try:
                show_database_import_dialog(
                    parent=self._window,
                    original_database_path=self._database_path,
                    running_platform=self._running_platform,
                    backup_path=selected_import_db_path,
                    current_db_version=self._database_version,
                    preselected_database_path=selected_import_db_path,
                )
                return True
            except Exception as e:
                print(f"Database import failed: {e}")
                return False

        maintenance = MaintenanceFunctions(
            database_obj=self._database,
            refresh_callback=self._refresh_users_list,
            set_button_states_callback=self._set_main_button_states,
            delete_folder_callback=(
                self._folder_manager.delete_folder_with_related
                if self._folder_manager
                else None
            ),
            database_path=self._database_path,
            running_platform=self._running_platform,
            database_version=self._database_version,
            progress_callback=self._progress_service,
            confirm_callback=lambda msg: (
                self._ui_service.ask_ok_cancel("Confirm", msg)
                if self._ui_service
                else False
            ),
            database_import_callback=database_import_callback,
            folder_repo=self._folder_repo,
            settings_repo=self._settings_repo,
            processed_files_repo=self._processed_files_repo,
        )

        MaintenanceDialog.open_dialog(
            parent=self._window,
            maintenance_functions=maintenance,
            ui_service=self._ui_service,
        )

    def _show_processed_files_dialog_wrapper(self) -> None:
        if self._database is None or self._ui_service is None:
            return
        from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog

        dlg = ProcessedFilesDialog(
            parent=self._window,
            database_obj=self._database,
            ui_service=self._ui_service,
        )
        dlg.exec()

    def _show_resend_dialog(self) -> None:
        if self._database is None:
            return
        from interface.qt.dialogs.resend_dialog import ResendDialog

        dlg = ResendDialog(
            parent=self._window,
            database_connection=self._database.database_connection,
        )
        if dlg._should_show:
            dlg.exec()

    def _disable_all_email_backends(self) -> None:
        if self._database is None or self._database.folders_table is None:
            return
        for row in self._database.folders_table.find(process_backend_email=True):
            row["process_backend_email"] = False
            self._database.folders_table.update(row, ["id"])

    def _disable_folders_without_backends(self) -> None:
        if self._database is None or self._database.folders_table is None:
            return
        for row in self._database.folders_table.find(
            process_backend_email=False,
            process_backend_ftp=False,
            process_backend_copy=False,
            folder_is_active=True,
        ):
            row["folder_is_active"] = False
            self._database.folders_table.update(row, ["id"])

    def _update_reporting(self, changes: dict) -> None:
        if self._database is None or self._database.oversight_and_defaults is None:
            return
        self._database.oversight_and_defaults.update(changes, ["id"])

    def _mark_active_as_processed_wrapper(
        self, selected_folder: Optional[int] = None
    ) -> None:
        if self._folder_manager is None:
            return
        from interface.operations.maintenance_functions import MaintenanceFunctions

        maintenance = MaintenanceFunctions(
            database_obj=self._database,
            refresh_callback=self._refresh_users_list,
            set_button_states_callback=self._set_main_button_states,
            delete_folder_callback=self._folder_manager.delete_folder_with_related,
            database_path=self._database_path,
            running_platform=self._running_platform,
            database_version=self._database_version,
            progress_callback=self._progress_service,
            folder_repo=self._folder_repo,
            settings_repo=self._settings_repo,
            processed_files_repo=self._processed_files_repo,
        )
        maintenance.mark_active_as_processed(selected_folder=selected_folder)

    def _check_logs_directory(self) -> bool:
        if self._logs_directory is None:
            return False
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
            raise SystemExit from (
                error if isinstance(error, Exception) else SystemExit(str(error))
            )
        except SystemExit:
            raise
        except Exception as big_error:
            print("error writing critical error log...")
            raise SystemExit from big_error


def main() -> None:
    app = QtBatchFileSenderApp(
        appname="Batch File Sender",
        version="(Git Branch: Master)",
        database_version=CURRENT_DATABASE_VERSION,
    )
    app.initialize()
    app.run()
    app.shutdown()


if __name__ == "__main__":
    main()
