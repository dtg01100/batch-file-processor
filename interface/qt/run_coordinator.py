"""Processing execution and run/report coordination for Qt app."""

from __future__ import annotations

import datetime
import logging
import time
from typing import Any

from core.structured_logging import (
    generate_correlation_id,
    get_correlation_id,
    get_logger,
    log_with_context,
    set_correlation_id,
)
from dispatch.error_handler import ErrorHandler
from dispatch.preflight_validator import PreflightValidator

logger = get_logger(__name__)


class QtRunCoordinator:
    """Coordinates directory processing and report flow."""

    def __init__(self, app: Any) -> None:
        self._app = app

    def graphical_process_directories(self, folders_table_process) -> None:
        correlation_id = generate_correlation_id()
        set_correlation_id(correlation_id)
        logger.info(
            "Starting graphical directory processing",
            extra={
                "correlation_id": correlation_id,
                "operation": "graphical_process_directories",
                "component": "qt_run_coordinator",
            },
        )
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
            # Preflight validation — catch config issues before the run.
            active_folders = list(folders_table_process.find(folder_is_active=True))
            settings = self._app._database.get_settings_or_default()
            preflight = PreflightValidator(os_module=self._app._os_module)
            preflight_result = preflight.validate_folders(active_folders, settings)
            if not preflight_result.is_valid:
                proceed = self._app._ui_service.ask_ok_cancel(
                    "Preflight Warning",
                    preflight_result.format_message() + "\n\nContinue anyway?",
                )
                if not proceed:
                    return
            elif preflight_result.warnings:
                self._app._ui_service.show_warning(
                    "Preflight Warning",
                    preflight_result.format_message(),
                )

            self._app._progress_service.show("Preparing run...")
            self._app._process_directories(folders_table_process)
            self._app._refresh_users_list()
            self._app._set_main_button_states()
            self._app._progress_service.hide()
        else:
            self._app._ui_service.show_error("Error", "No Active Folders")

    def process_directories(self, folders_table_process) -> None:
        correlation_id = get_correlation_id() or generate_correlation_id()
        set_correlation_id(correlation_id)
        log_with_context(
            logger,
            logging.DEBUG,
            "Starting process_directories run",
            correlation_id=correlation_id,
            component="qt_run_coordinator",
            operation="process_directories",
            context={
                "folder_count": folders_table_process.count(
                    folder_is_active=True
                )
            },
        )

        original_folder = self._app._os_module.getcwd()
        settings_dict = self._app._database.get_settings_or_default()

        # Prepare run (backups, log directory checks)
        start_time, reporting, run_log_path, run_log_full_path = self._prepare_run(
            settings_dict
        )

        run_summary_string = ""

        # Main run body
        try:
            with open(run_log_full_path, "wb") as run_log:
                self._write_run_header(run_log, run_log_path)
                if self._app._utils_module.normalize_bool(
                    reporting["enable_reporting"]
                ):
                    self._app._database.emails_table.insert(
                        {
                            "log": run_log_full_path,
                            "folder_alias": self._app._os_module.path.basename(
                                run_log_full_path
                            ),
                        }
                    )

                run_summary_string = self._execute_dispatch(
                    folders_table_process, settings_dict, run_log
                )
        finally:
            # Ensure we always return to original cwd
            try:
                self._app._os_module.chdir(original_folder)
            except Exception:
                pass

        # Send reports if configured
        if self._app._utils_module.normalize_bool(reporting["enable_reporting"]):
            self._app._reporting_service.send_report_emails(
                settings_dict=settings_dict,
                reporting_config=reporting,
                run_log_path=run_log_path,
                start_time=start_time,
                run_summary=run_summary_string,
                progress_callback=self._app._progress_service,
            )

    def _prepare_run(self, settings_dict: dict[str, Any]):
        """Prepare run: handle backups, ensure log directory exists
        and return run paths.
        """
        if (
            settings_dict["enable_interval_backups"]
            and settings_dict[
                "backup_counter"
            ]
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
            "Run Log " + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".txt"
        )

        if not self._app._os_module.path.isdir(
            self._app._logs_directory["logs_directory"]
        ):
            try:
                self._app._os_module.mkdir(self._app._logs_directory["logs_directory"])
            except IOError as mkdir_error:
                log_with_context(
                    logger,
                    40,
                    f"Failed to create log directory: {mkdir_error}",
                    correlation_id=get_correlation_id(),
                    component="qt_run_coordinator",
                    operation="process_directories",
                    context={
                        "log_directory": self._app._logs_directory["logs_directory"],
                        "error_type": type(mkdir_error).__name__,
                    },
                    exc_info=True,
                )
                log_folder_creation_error = True

        if not self._app._check_logs_directory() or log_folder_creation_error:
            if not self._app._args.automatic:
                while not self._app._check_logs_directory():
                    if self._app._ui_service.ask_ok_cancel(
                        "Error",
                        "Can't write to log directory,\r\n "
                        "would you like to change reporting settings?",
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
        return start_time, reporting, run_log_path, run_log_full_path

    def _write_run_header(self, run_log, run_log_path: str) -> None:
        logger.debug("Run log: %s", run_log_path)
        self._app._utils_module.do_clear_old_files(run_log_path, 1000)
        run_log.write((f"Batch File Sender Version {self._app._version}\r\n").encode())
        run_log.write((f"starting run at {time.ctime()}\r\n").encode())

    def _execute_dispatch(
        self, folders_table_process, settings_dict: dict[str, Any], run_log
    ) -> str:
        """Execute dispatch pipeline and return run summary string."""
        # Decompose into smaller helpers to reduce complexity
        config = self._build_dispatch_config(folders_table_process, settings_dict)
        orchestrator, folders = self._init_orchestrator_and_folders(
            config, folders_table_process
        )
        run_error_bool = self._process_folders(orchestrator, folders, run_log)
        run_summary_string = orchestrator.get_summary()
        self._handle_validation_report(
            orchestrator, run_log, settings_dict, run_summary_string
        )
        if run_error_bool and not self._app._args.automatic:
            self._app._ui_service.show_info("Run Status", "Run completed with errors.")
        log_with_context(
            logger,
            20,
            "Dispatch completed",
            correlation_id=get_correlation_id(),
            component="qt_run_coordinator",
            operation="process_directories",
            context={
                "run_error": run_error_bool,
                "summary": run_summary_string,
                "folders_processed": len(folders),
            },
        )
        return run_summary_string

    def _build_dispatch_config(self, folders_table_process, settings_dict):
        from dispatch.pipeline import create_standard_pipeline

        return create_standard_pipeline(
            database=folders_table_process,
            settings=settings_dict,
            version=self._app._version,
            progress_reporter=self._app._progress_service,
        )

    def _init_orchestrator_and_folders(self, config, folders_table_process):
        from dispatch import DispatchOrchestrator

        orchestrator = DispatchOrchestrator(config)
        folders = list(
            folders_table_process.find(folder_is_active=True, order_by="alias")
        )
        if (
            self._app._progress_service
            and hasattr(self._app._progress_service, "start_sending")
        ):
            self._app._progress_service.start_sending(
                total_files=0, total_folders=len(folders)
            )
        return orchestrator, folders

    def _process_folders(self, orchestrator, folders, run_log):
        run_error_bool = False
        for folder_index, folder in enumerate(folders, start=1):
            if (
                self._app._progress_service
                and hasattr(self._app._progress_service, "set_folder_context")
            ):
                self._app._progress_service.set_folder_context(
                    folder_num=folder_index,
                    folder_total=len(folders),
                    folder_name=folder.get("alias", folder.get("folder_name", "")),
                    file_total=0,
                )
            try:
                result = orchestrator.discover_and_process_folder(
                    folder,
                    run_log,
                    self._app._database.processed_files,
                    folder_num=folder_index,
                    folder_total=len(folders),
                )
                if not result.success:
                    run_error_bool = True
            except Exception as folder_error:
                run_error_bool = True
                run_log.write(
                    f"ERROR processing folder {folder.get('alias', 'unknown')}: "
                    f"{folder_error}\r\n".encode()
                )
        return run_error_bool

    def _handle_validation_report(
        self, orchestrator, run_log, settings_dict, run_summary_string
    ):
        validator_log_output = ""
        validator_step = orchestrator.config.validator_step
        if validator_step and hasattr(validator_step, "get_error_log"):
            validator_log_output = validator_step.get_error_log()

        report_edi_errors_enabled = self._app._utils_module.normalize_bool(
            settings_dict.get("report_edi_errors", False)
        )
        if report_edi_errors_enabled and validator_log_output.strip():
            try:
                validator_report_path = ErrorHandler(
                    run_log_directory=self._app._logs_directory.get(
                        "logs_directory", ""
                    )
                ).write_validation_report(validator_log_output)
                if self._app._utils_module.normalize_bool(
                    settings_dict.get("enable_reporting", False)
                ):
                    self._app._database.emails_table.insert(
                        {"log": validator_report_path}
                    )
                run_summary_string += ", has EDI validator errors"
            except Exception as validation_report_error:
                run_log.write(
                    (
                        f"Failed to write validation report: "
                        f"{validation_report_error}\r\n"
                    ).encode()
                )

    def automatic_process_directories(self, automatic_process_folders_table) -> None:
        correlation_id = generate_correlation_id()
        set_correlation_id(correlation_id)
        active_count = automatic_process_folders_table.count(folder_is_active=True)
        if active_count > 0:
            log_with_context(
                logger,
                20,  # INFO
                "Batch processing configured directories",
                correlation_id=correlation_id,
                component="qt_run_coordinator",
                operation="automatic_process_directories",
                context={"active_folders": active_count},
            )
            # Preflight validation — log only, never block automatic runs.
            try:
                active_folders = list(
                    automatic_process_folders_table.find(folder_is_active=True)
                )
                settings = self._app._database.get_settings_or_default()
                preflight = PreflightValidator(os_module=self._app._os_module)
                preflight_result = preflight.validate_folders(active_folders, settings)
                if preflight_result.issues:
                    log_with_context(
                        logger,
                        30,  # WARNING
                        "Preflight validation issues (automatic mode, "
                        "proceeding anyway): " + preflight_result.format_message(),
                        correlation_id=correlation_id,
                        component="qt_run_coordinator",
                        operation="automatic_process_directories",
                    )
            except Exception as preflight_error:
                log_with_context(
                    logger,
                    30,  # WARNING
                    f"Preflight validation failed: {preflight_error}",
                    correlation_id=correlation_id,
                    component="qt_run_coordinator",
                    operation="automatic_process_directories",
                )
            try:
                self._app._process_directories(automatic_process_folders_table)
            except Exception as automatic_process_error:
                log_with_context(
                    logger,
                    50,  # CRITICAL
                    f"Automatic processing failed: {automatic_process_error}",
                    correlation_id=get_correlation_id(),
                    component="qt_run_coordinator",
                    operation="automatic_process_directories",
                    context={"error_type": type(automatic_process_error).__name__},
                    exc_info=True,
                )
                self._app._log_critical_error(automatic_process_error)
        else:
            log_with_context(
                logger,
                30,  # WARNING
                "No active folders configured",
                correlation_id=get_correlation_id(),
                component="qt_run_coordinator",
                operation="automatic_process_directories",
            )
