"""Processing execution and run/report coordination for Qt app."""

from __future__ import annotations

import datetime
import logging
import time
import traceback
from typing import Any

logger = logging.getLogger(__name__)


class QtRunCoordinator:
    """Coordinates directory processing and report flow."""

    def __init__(self, app: Any) -> None:
        self._app = app

    def graphical_process_directories(self, folders_table_process) -> None:
        missing_folder = False
        missing_folder_name = None
        for folder_test in folders_table_process.find(folder_is_active=True):
            if not self._app._os_module.path.exists(folder_test["folder_name"]):
                missing_folder = True
                missing_folder_name = (
                    folder_test.get("alias") or folder_test["folder_name"]
                )

        if missing_folder:
            self._app._ui_service.show_error(
                "Error",
                "One or more expected folders are missing"
                + (f" (e.g. '{missing_folder_name}')." if missing_folder_name else "."),
            )
        elif folders_table_process.count(folder_is_active=True) > 0:
            self._app._progress_service.show("processing folders...")
            self._app._process_directories(folders_table_process)
            self._app._refresh_users_list()
            self._app._set_main_button_states()
            self._app._progress_service.hide()
        else:
            self._app._ui_service.show_error("Error", "No Active Folders")

    def process_directories(self, folders_table_process) -> None:
        logger.debug("Starting process_directories run")
        original_folder = self._app._os_module.getcwd()
        settings_dict = self._app._database.get_settings_or_default()

        if (
            settings_dict["enable_interval_backups"]
            and settings_dict["backup_counter"]
            >= settings_dict["backup_counter_maximum"]
        ):
            self._app._backup_increment_module.do_backup(self._app._database_path)
            settings_dict["backup_counter"] = 0
        settings_dict["backup_counter"] += 1
        self._app._database.settings.update(settings_dict, ["id"])

        log_folder_creation_error = False
        start_time = str(datetime.datetime.now())
        reporting = self._app._database.get_oversight_or_default()
        run_log_name_constructor = (
            "Run Log " + str(time.ctime()).replace(":", "-") + ".txt"
        )

        if not self._app._os_module.path.isdir(
            self._app._logs_directory["logs_directory"]
        ):
            try:
                self._app._os_module.mkdir(self._app._logs_directory["logs_directory"])
            except IOError as mkdir_error:
                logger.error(
                    "Failed to create log directory '%s': %s",
                    self._app._logs_directory["logs_directory"],
                    mkdir_error,
                )
                log_folder_creation_error = True

        if not self._app._check_logs_directory() or log_folder_creation_error:
            if not self._app._args.automatic:
                while not self._app._check_logs_directory():
                    if self._app._ui_service.ask_ok_cancel(
                        "Error",
                        "Can't write to log directory,\r\n"
                        " would you like to change reporting settings?",
                    ):
                        self._app._show_edit_settings_dialog()
                    else:
                        self._app._ui_service.show_error(
                            "Error", "Can't write to log directory, exiting"
                        )
                        raise SystemExit
            else:
                self._app._log_critical_error(
                    "can't write into logs directory. in automatic mode, so no prompt"
                )

        run_log_path = str(reporting["logs_directory"])
        run_log_full_path = self._app._os_module.path.join(
            run_log_path, run_log_name_constructor
        )
        run_summary_string = ""

        with open(run_log_full_path, "wb") as run_log:
            logger.debug("Run log: %s", run_log_full_path)
            self._app._utils_module.do_clear_old_files(run_log_path, 1000)
            run_log.write(
                (f"Batch File Sender Version {self._app._version}\r\n").encode()
            )
            run_log.write((f"starting run at {time.ctime()}\r\n").encode())

            if self._app._utils_module.normalize_bool(reporting["enable_reporting"]):
                self._app._database.emails_table.insert(
                    {"log": run_log_full_path, "folder_alias": run_log_name_constructor}
                )

            try:
                from dispatch import process

                run_error_bool = False
                run_error_bool, run_summary_string = process(
                    self._app._database.database_connection,
                    folders_table_process,
                    run_log,
                    self._app._database.emails_table,
                    reporting["logs_directory"],
                    reporting,
                    self._app._database.processed_files,
                    self._app._version,
                    self._app._errors_directory,
                    settings_dict,
                    progress_callback=self._app._progress_service,
                )
                if run_error_bool and not self._app._args.automatic:
                    self._app._ui_service.show_info(
                        "Run Status", "Run completed with errors."
                    )
                logger.info(
                    "Dispatch completed (errors=%s, summary=%s)",
                    run_error_bool,
                    run_summary_string,
                )
            except Exception as dispatch_error:
                logger.exception("Run failed: %s", dispatch_error)
                run_log.write(
                    (
                        "Run failed, check your configuration \r\n"
                        f"Error from dispatch module is: \r\n{dispatch_error}\r\n"
                    ).encode()
                )
                run_log.write(traceback.format_exc().encode())
            finally:
                self._app._os_module.chdir(original_folder)

        if self._app._utils_module.normalize_bool(reporting["enable_reporting"]):
            self._app._reporting_service.send_report_emails(
                settings_dict=settings_dict,
                reporting_config=reporting,
                run_log_path=run_log_path,
                start_time=start_time,
                run_summary=run_summary_string,
                progress_callback=self._app._progress_service,
            )

    def automatic_process_directories(self, automatic_process_folders_table) -> None:
        if automatic_process_folders_table.count(folder_is_active=True) > 0:
            logger.info("Batch processing configured directories")
            try:
                self._app._process_directories(automatic_process_folders_table)
            except Exception as automatic_process_error:
                self._app._log_critical_error(automatic_process_error)
        else:
            logger.warning("No active folders configured")
        self._app._database.close()
        self._app._sys_module.exit()
