"""Qt reimplementation of the Batch File Sender main application window.

Provides :class:`QtBatchFileSenderApp`, which mirrors the public API of
:class:`~interface.app.BatchFileSenderApp` (``initialize``, ``run``,
``shutdown``) while using PyQt5 for all UI rendering.
"""

from __future__ import annotations

import argparse
import datetime
import logging
import multiprocessing
import os
import platform
import sys
from typing import Any

import appdirs
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QWidget

import core.utils as utils
import scripts.backup_increment as backup_increment
import scripts.batch_log_sender as batch_log_sender
import scripts.print_run_log as print_run_log
from adapters.sqlite.repositories import (
    SqliteFolderRepository,
    SqliteProcessedFilesRepository,
    SqliteSettingsRepository,
)
from backend.database.database_obj import DatabaseObj
from core.constants import APP_VERSION, CURRENT_DATABASE_VERSION, UPC_PADDING_PATTERN
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
        version: str = APP_VERSION,
        database_version: str = CURRENT_DATABASE_VERSION,
        database_obj: DatabaseObj | None = None,
        folder_manager: FolderManager | None = None,
        ui_service: UIServiceProtocol | None = None,
        progress_service: ProgressServiceProtocol | None = None,
    ) -> None:
        self._appname = appname
        self._version = version
        self._database_version = database_version

        self._database: DatabaseObj | None = database_obj
        self._ui_service: UIServiceProtocol | None = ui_service
        self._progress_service: ProgressServiceProtocol | None = progress_service

        self._running_platform = platform.system()
        self._appdirs_module = appdirs
        self._sys_module = sys
        self._os_module = os
        self._utils_module = utils
        self._backup_increment_module = backup_increment

        self._config_folder: str | None = None
        self._database_path: str | None = None

        self._folder_manager: FolderManager | None = folder_manager
        self._folder_repo: Any | None = None
        self._settings_repo: Any | None = None
        self._processed_files_repo: Any | None = None
        self._reporting_service: ReportingService | None = None

        self._app: QApplication | None = None
        self._window: QMainWindow | None = None

        self._folder_filter = ""

        self._folder_list_widget: Any | None = None
        self._search_widget: Any | None = None
        self._right_panel_widget: QWidget | None = None

        self._process_folder_button: QPushButton | None = None
        self._processed_files_button: QPushButton | None = None
        self._allow_resend_button: QPushButton | None = None

        self._args: argparse.Namespace | None = None

        self._logs_directory: dict | None = None
        self._errors_directory: dict | None = None

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

    def initialize(self, args: list[str] | None = None) -> None:
        multiprocessing.freeze_support()

        self._configure_qt_platform()

        logger.info("%s Version %s", self._appname, self._version)
        logger.info("Running on %s", self._running_platform)

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
                    logger.warning(
                        "Failed to dispose progress service during shutdown",
                        exc_info=True,
                    )

        if self._window is not None:
            try:
                self._window.close()
                self._window.deleteLater()
            except Exception:
                logger.warning(
                    "Failed to close and delete main window during shutdown",
                    exc_info=True,
                )
            self._window = None

        QT_EVENT_PROCESSING_ITERATIONS = 10

        try:
            if QApplication.instance() is not None:
                for _ in range(QT_EVENT_PROCESSING_ITERATIONS):
                    QApplication.processEvents()
        except Exception:
            logger.warning(
                "Failed to process pending Qt events during shutdown", exc_info=True
            )

        self._ui_service = None
        self._progress_service = None

        if self._database is not None:
            self._database.close()

    def _configure_qt_platform(self) -> None:
        self._bootstrap.configure_qt_platform()

    def _parse_arguments(self, args: list[str] | None = None) -> None:
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

    def _set_main_button_states(self) -> None:
        self._window_controller.set_main_button_states()

    def _select_folder(self) -> None:
        if not self._preselect_select_folder_checks():
            return

        prior_folder = self._database.get_oversight_or_default()
        initial_directory = prior_folder.get("single_add_folder_prior", "")
        if not initial_directory or not os.path.exists(initial_directory):
            initial_directory = os.path.expanduser("~")

        selected_folder = self._ui_service.ask_directory(
            title="Select Directory",
            initial_dir=initial_directory,
        )
        if not selected_folder or not os.path.exists(selected_folder):
            return

        if self._database.oversight_and_defaults:
            self._database.oversight_and_defaults.update(
                {"id": 1, "single_add_folder_prior": selected_folder},
                ["id"],
            )
        existing_folders = self._folder_manager.check_folder_exists(selected_folder)

        if existing_folders["truefalse"]:
            if self._handle_existing_folder_choice(existing_folders):
                return

        if self._progress_service:
            self._progress_service.show("Adding Folder...")
        self._folder_manager.add_folder(selected_folder)
        # Only ask about marking processed if folder is new (no existing configs)
        if not existing_folders["truefalse"]:
            self._maybe_mark_as_processed(selected_folder)
        if self._progress_service:
            self._progress_service.hide()
        self._refresh_users_list()

    def _maybe_mark_as_processed(self, selected_folder: str) -> None:
        """Ask user whether to mark files as processed and perform marking if agreed."""
        if self._ui_service.ask_yes_no(
            "Mark Processed", "Do you want to mark files in folder as processed?"
        ):
            if self._database and self._database.folders_table:
                folder_dict = self._database.folders_table.find_one(
                    folder_name=selected_folder
                )
                if folder_dict:
                    self._mark_active_as_processed_wrapper(folder_dict["id"])

    def _preselect_select_folder_checks(self) -> bool:
        """Checks prerequisites for selecting a folder."""
        if (
            self._database is None
            or self._ui_service is None
            or self._folder_manager is None
        ):
            return False
        return True

    def _handle_existing_folder_choice(self, existing_folders: dict) -> bool:
        """Handle user choice when folder already exists.

        Returns True if dialog action handled and caller should return.
        """
        # Folder already exists - give user three choices
        existing_count = len(existing_folders["all_matched_folders"])
        msg = f"This folder has {existing_count} existing configuration(s)."
        choice = self._ui_service.ask_three_choices(
            "Folder Already Exists",
            msg,
            "Add Another",  # 0
            "Edit Original",  # 1
            "Cancel",  # 2
        )
        if choice == 2:  # Cancel
            return True
        if choice == 1:  # Edit original
            self._open_edit_folders_dialog(existing_folders["matched_folder"])
            return True
        return False

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
        added = 0
        for folder in folders_to_add:
            if self._progress_service:
                self._progress_service.update_message(
                    f"Adding folders... ({added + 1}/{len(folders_to_add)})"
                )
            self._folder_manager.add_folder(folder)
            added += 1

        logger.info("done adding %s folders", added)
        if self._progress_service:
            self._progress_service.hide()
        self._ui_service.show_info(
            "Batch Add Complete",
            f"{added} folders added.",
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
        except Exception:
            # Cleanup failure is non-fatal; continue with main operation
            pass

        try:
            if self._database.session_database:
                self._database.session_database.query(
                "CREATE TABLE IF NOT EXISTS "
                "single_table AS SELECT * FROM folders WHERE 0"
                )
                self._database.session_database.query(
                    "ALTER TABLE single_table ADD COLUMN old_id INTEGER"
                )
                single_table = self._database.session_database["single_table"]
                if self._database.folders_table:
                    table_dict = self._database.folders_table.find_one(id=folder_id)
                    if table_dict:
                        table_dict["old_id"] = table_dict.pop("id")
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

                if self._database.session_database:
                    self._graphical_process_directories(single_table)
                    single_table.drop()
        finally:
            self._progress_service.hide()

    def _disable_folder(self, folder_id: int) -> None:
        if self._folder_manager is None:
            return
        self._folder_manager.disable_folder(folder_id)
        self._refresh_users_list()

    def _toggle_folder(self, folder_id: int) -> None:
        if self._folder_manager is None or self._ui_service is None:
            return
        folder = self._folder_manager.get_folder_by_id(folder_id)
        if not folder:
            return

        is_active = folder.get("folder_is_active", False)

        if is_active:
            self._folder_manager.disable_folder(folder_id)
        else:
            has_backend = (
                folder.get("process_backend_email")
                or folder.get("process_backend_ftp")
                or folder.get("process_backend_copy")
            )
            if not has_backend:
                self._ui_service.show_error(
                    "Cannot Enable Folder",
                f"Folder '{folder.get('alias', 'Unknown')}' "
                f"has no backends configured.\n\n"
                    "Please edit the folder and enable at least one backend:\n"
                    "• Email\n"
                    "• FTP\n"
                    "• Copy to Directory",
                )
                return
            self._folder_manager.enable_folder(folder_id)

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
            if self._database:
                settings = dict(self._database.get_settings_or_default())
                if self._database.folders_table:
                    settings["folders"] = self._database.folders_table.find()
                return settings
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
        defaults = dict(self._database.get_oversight_or_default())
        default_values = {
            "copy_to_directory": "",
            "logs_directory": os.path.join(
                os.path.expanduser("~"), "BatchFileSenderLogs"
            ),
            "enable_reporting": False,
            "report_email_destination": "",
            "report_edi_errors": False,
            "folder_name": "template",
            "folder_is_active": True,
            "alias": "",
            "process_backend_copy": False,
            "process_backend_ftp": False,
            "process_backend_email": False,
            "ftp_server": "",
            "ftp_port": 21,
            "ftp_folder": "",
            "ftp_username": "",
            "ftp_password": "",
            "email_to": "",
            "email_subject_line": "",
            "process_edi": False,
            "convert_to_format": "csv",
            "calculate_upc_check_digit": False,
            "include_a_records": False,
            "include_c_records": False,
            "include_headers": False,
            "filter_ampersand": False,
            "split_edi": False,
            "split_edi_include_invoices": False,
            "split_edi_include_credits": False,
            "prepend_date_files": False,
            "split_edi_filter_categories": "ALL",
            "split_edi_filter_mode": "include",
            "rename_file": "",
            "pad_a_records": False,
            "a_record_padding": "",
            "a_record_padding_length": 6,
            "append_a_records": False,
            "a_record_append_text": "",
            "force_txt_file_ext": False,
            "invoice_date_offset": 0,
            "invoice_date_custom_format": False,
            "invoice_date_custom_format_string": "%Y%m%d",
            "retail_uom": False,
            "force_edi_validation": False,
            "override_upc_bool": False,
            "override_upc_level": 1,
            "override_upc_category_filter": "",
            "upc_target_length": 11,
            "upc_padding_pattern": UPC_PADDING_PATTERN,
            "include_item_numbers": False,
            "include_item_description": False,
            "simple_csv_sort_order": "",
            "split_prepaid_sales_tax_crec": False,
            "estore_store_number": "",
            "estore_Vendor_OId": "",
            "estore_vendor_NameVendorOID": "",
            "estore_c_record_OID": "",
            "fintech_division_id": "",
        }
        for key, value in default_values.items():
            defaults.setdefault(key, value)
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
                logger.debug("Database import failed: %s", e)
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
        self, selected_folder: int | None = None
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
            logger.debug("Logs directory check failed: %s", log_directory_error)
            return False

    def _log_critical_error(self, error) -> None:
        logger.critical(
            "Critical error: %s",
            error,
            exc_info=error if isinstance(error, Exception) else None,
        )
        try:
            log_dir = (
                os.path.dirname(self._database_path) if self._database_path else "."
            )
            log_path = os.path.join(log_dir, "critical_error.log")
            with open(log_path, "a", encoding="utf-8") as critical_log:
                critical_log.write(f"Program version: {self._version}\n")
                critical_log.write(f"Timestamp: {datetime.datetime.now()}\n")
                if isinstance(error, Exception):
                    critical_log.write(f"Error: {error!r}\n")
                else:
                    critical_log.write(f"Error: {error}\n")
                critical_log.write("-" * 50 + "\n")
        except Exception as log_error:
            logger.error("Failed to write critical error log: %s", log_error)
        raise SystemExit(1) from (error if isinstance(error, Exception) else None)
