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

from batch_file_processor.constants import CURRENT_DATABASE_VERSION
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
from interface.qt.theme import Theme
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
        database_version: str = CURRENT_DATABASE_VERSION,
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
            raise RuntimeError(
                "Folder manager not initialized - call initialize() first"
            )
        return self._folder_manager

    @property
    def args(self) -> argparse.Namespace:
        if self._args is None:
            raise RuntimeError("Arguments not parsed - call initialize() first")
        return self._args

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _run_self_test(self) -> int:
        """Run self-test checks and return exit code (0 for success, 1 for failures)."""
        print(f"Running self-test for {self._appname} Version {self._version}")
        print(f"Platform: {self._running_platform}")
        print("=" * 50)

        failures = 0

        # Check 1: Verify required modules can be imported
        print("\n1. Checking module imports...")
        required_modules = [
            "argparse",
            "datetime",
            "multiprocessing",
            "os",
            "platform",
            "sys",
            "time",
            "traceback",
            "appdirs",
            "PyQt6.QtCore",
            "PyQt6.QtWidgets",
            "PyQt6.QtGui",
            "PyQt6.QtPrintSupport",
            "PyQt6.QtSvg",
            "PyQt6.QtXml",
            "PyQt6.QtNetwork",
            "interface.database.database_obj",
            "interface.operations.folder_manager",
            "interface.ports",
            "interface.services.reporting_service",
            "interface.qt.app",
            "interface.qt.dialogs.edit_folders_dialog",
            "interface.qt.dialogs.edit_folders.data_extractor",
            "batch_log_sender",
            "print_run_log",
            "utils",
            "backup_increment",
            # Core business logic modules
            "core.edi.edi_parser",
            "core.edi.edi_splitter",
            "core.edi.inv_fetcher",
            "core.edi.po_fetcher",
            "dispatch",
            "dispatch.orchestrator",
            "dispatch.send_manager",
            "backend.ftp_client",
            "backend.smtp_client",
            "record_error",
            "folders_database_migrator",
            "mover",
            "clear_old_files",
            "rclick_menu",
            # Convert backends
            "convert_to_csv",
            "convert_to_fintech",
            "convert_to_simplified_csv",
            "convert_to_stewarts_custom",
            "convert_to_yellowdog_csv",
            "convert_to_estore_einvoice",
            "convert_to_estore_einvoice_generic",
            "convert_to_scannerware",
            "convert_to_scansheet_type_a",
            "convert_to_jolley_custom",
            # Backend modules
            "copy_backend",
            "ftp_backend",
            "email_backend",
            # Third-party dependencies
            "lxml",
            "lxml.etree",
        ]

        # pyodbc is only bundled on Windows builds (excluded from Linux native builds)
        optional_modules = []
        if sys.platform != "win32":
            optional_modules = ["pyodbc", "PIL"]
        else:
            required_modules.extend(["pyodbc", "PIL"])

        for module in required_modules:
            try:
                __import__(module)
                print(f"  [OK] {module}")
            except ImportError as e:
                print(f"  [FAIL] {module}: {e}")
                failures += 1

        for module in optional_modules:
            try:
                __import__(module)
                print(f"  [OK] {module} (optional)")
            except ImportError as e:
                print(f"  [?] {module} (optional, not bundled on this platform): {e}")

        # Check for sip which is required by PyQt6 but imported differently
        try:
            print(f"  [OK] PyQt6.sip")
        except ImportError as e:
            print(f"  [FAIL] PyQt6.sip: {e}")
            failures += 1

        # Check 2: Validate configuration directory setup
        print("\n2. Checking configuration directories...")
        try:
            self._setup_config_directories()
            if self._config_folder and os.path.exists(self._config_folder):
                print(f"  [OK] Config directory: {self._config_folder}")
            else:
                print(f"  [FAIL] Config directory not created: {self._config_folder}")
                failures += 1
        except Exception as e:
            print(f"  [FAIL] Failed to setup config directories: {e}")
            failures += 1

        # Check 3: Test appdirs module functionality
        print("\n3. Checking appdirs functionality...")
        try:
            test_config = appdirs.user_data_dir("TestApp")
            print(f"  [OK] appdirs module working: {test_config}")
        except Exception as e:
            print(f"  [FAIL] appdirs module error: {e}")
            failures += 1

        # Check 4: Verify file system access
        print("\n4. Checking file system access...")
        try:
            temp_dir = os.path.join(os.path.expanduser("~"), "BatchFileSenderTest")
            os.makedirs(temp_dir, exist_ok=True)
            temp_file = os.path.join(temp_dir, "test.tmp")
            with open(temp_file, "w") as f:
                f.write("test")
            os.remove(temp_file)
            os.rmdir(temp_dir)
            print(f"  [OK] File system access working")
        except Exception as e:
            print(f"  [FAIL] File system access error: {e}")
            failures += 1

        # Check 5: Validate essential local modules
        print("\n5. Checking local module availability...")
        local_modules = [
            ("batch_log_sender", "batch_log_sender"),
            ("print_run_log", "print_run_log"),
            ("utils", "utils"),
            ("backup_increment", "backup_increment"),
        ]

        for module_name, import_name in local_modules:
            try:
                module = __import__(import_name)
                if hasattr(module, "__file__"):
                    print(f"  [OK] {module_name}")
                else:
                    print(
                        f"  [FAIL] {module_name}: Module imported but no __file__ attribute"
                    )
                    failures += 1
            except Exception as e:
                print(f"  [FAIL] {module_name}: {e}")
                failures += 1

        print("\n" + "=" * 50)
        if failures == 0:
            print(
                f"[PASS] Self-test passed - all {len(required_modules) + len(local_modules) + 3} checks successful"
            )
            return 0
        else:
            print(
                f"[FAIL] Self-test failed - {failures} out of {len(required_modules) + len(local_modules) + 3} checks failed"
            )
            return 1

    def _run_gui_self_test(self) -> int:
        """Run GUI self-test: verify Qt widgets can be created and displayed.

        This test creates the main window, verifies all widgets are properly
        initialized, shows the window briefly, then closes it.

        Returns:
            0 for success, 1 for failures
        """
        from PyQt6.QtCore import QTimer

        print(f"\n{'=' * 50}")
        print("GUI Self-Test")
        print("=" * 50)

        failures = 0

        # Step 1: Create QApplication
        print("\n1. Creating QApplication...")
        try:
            self._app = QApplication.instance() or QApplication(sys.argv)
            print("  [OK] QApplication created")
        except Exception as e:
            print(f"  [FAIL] QApplication creation failed: {e}")
            return 1

        # Step 2: Create main window
        print("\n2. Creating main window...")
        try:
            self._window = QMainWindow()
            self._window.setWindowTitle(f"{self._appname} {self._version} (GUI Test)")
            print("  [OK] QMainWindow created")
        except Exception as e:
            print(f"  [FAIL] QMainWindow creation failed: {e}")
            return 1

        # Step 3: Initialize database and services
        print("\n3. Initializing database and services...")
        try:
            self._setup_config_directories()
            if self._database is None:
                self._database = DatabaseObj(
                    self._database_path,
                    self._database_version,
                    self._config_folder,
                    self._running_platform,
                )
            print("  [OK] Database initialized")
        except Exception as e:
            print(f"  [FAIL] Database initialization failed: {e}")
            failures += 1

        try:
            self._folder_manager = FolderManager(self._database)
            print("  [OK] FolderManager initialized")
        except Exception as e:
            print(f"  [FAIL] FolderManager initialization failed: {e}")
            failures += 1

        # Step 4: Build UI
        print("\n4. Building UI components...")
        try:
            self._build_main_window()
            print("  [OK] Main window built")
        except Exception as e:
            print(f"  [FAIL] Main window build failed: {e}")
            failures += 1

        # Step 5: Verify widgets exist
        print("\n5. Verifying widgets...")
        widgets_to_check = [
            ("Folder list widget", self._folder_list_widget),
            ("Search widget", self._search_widget),
            ("Right panel widget", self._right_panel_widget),
            ("Process folder button", self._process_folder_button),
            ("Processed files button", self._processed_files_button),
            ("Allow resend button", self._allow_resend_button),
        ]

        for widget_name, widget in widgets_to_check:
            if widget is not None:
                print(f"  [OK] {widget_name}")
            else:
                print(f"  [FAIL] {widget_name} is None")
                failures += 1

        # Step 6: Show window and schedule close
        print("\n6. Displaying window (will auto-close in 2 seconds)...")
        try:
            self._window.show()
            print("  [OK] Window displayed")
        except Exception as e:
            print(f"  [FAIL] Window display failed: {e}")
            failures += 1

        # Schedule window close and app quit
        def close_and_quit():
            print("\n7. Closing window...")
            self._window.close()
            self._app.quit()
            print("  [OK] Window closed")
            print(f"\n{'=' * 50}")
            if failures == 0:
                print("[PASS] GUI self-test passed")
            else:
                print(f"[FAIL] GUI self-test failed with {failures} errors")
            print("=" * 50)

        QTimer.singleShot(2000, close_and_quit)

        # Run the event loop
        return self._app.exec()

    def initialize(self, args: Optional[list[str]] = None) -> None:
        multiprocessing.freeze_support()

        # Fix Qt platform plugin issues: force X11 when Wayland is misconfigured
        self._configure_qt_platform()

        print(f"{self._appname} Version {self._version}")
        print(f"Running on {self._running_platform}")

        self._parse_arguments(args)

        # Run self-test if requested
        if self._args.self_test:
            exit_code = self._run_self_test()
            sys.exit(exit_code)

        # Run GUI self-test if requested
        if self._args.gui_test:
            exit_code = self._run_gui_self_test()
            sys.exit(exit_code)

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

        # Use safe accessor to ensure these singleton records exist
        oversight = self._database.get_oversight_or_default()
        self._logs_directory = oversight
        self._errors_directory = oversight

        if self._args.automatic:
            self._automatic_process_directories(self._database.folders_table)
            return

        self._app = QApplication.instance() or QApplication(sys.argv)
        self._app.setStyleSheet(Theme.get_stylesheet())
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
    # Platform Configuration
    # ------------------------------------------------------------------

    def _configure_qt_platform(self) -> None:
        """Configure Qt platform plugin to avoid Wayland issues.

        When both WAYLAND_DISPLAY and DISPLAY are set, Qt may try to use
        Wayland but fail to connect. This forces Qt to use X11 (xcb) in
        such cases.

        Note: Windows builds running under Wine should use the 'windows'
        platform plugin, not xcb.
        """
        import os

        # Don't override platform for Windows builds (even under Wine)
        if sys.platform == "win32":
            return

        wayland_display = os.environ.get("WAYLAND_DISPLAY")
        x11_display = os.environ.get("DISPLAY")
        qpa_platform = os.environ.get("QT_QPA_PLATFORM")

        # If Wayland is set but QT_QPA_PLATFORM is not explicitly set,
        # and we have X11 available, force X11 to avoid Wayland connection issues
        if wayland_display and x11_display and not qpa_platform:
            os.environ["QT_QPA_PLATFORM"] = "xcb"
            print(f"Qt platform: Forcing XCB (X11) due to Wayland/X11 coexistence")

    # ------------------------------------------------------------------
    # Argument parsing / config
    # ------------------------------------------------------------------

    def _parse_arguments(self, args: Optional[list[str]] = None) -> None:
        launch_options = argparse.ArgumentParser()
        launch_options.add_argument("-a", "--automatic", action="store_true")
        launch_options.add_argument(
            "-s", "--self-test", action="store_true", help="Run self-test and exit"
        )
        launch_options.add_argument(
            "-g",
            "--gui-test",
            action="store_true",
            help="Run GUI self-test (opens and closes main window)",
        )
        self._args = launch_options.parse_args(args)

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
        # Set a reasonable minimum size but allow full resizing
        self._window.setMinimumSize(800, 600)

    def _build_main_window(self) -> None:
        from PyQt6.QtWidgets import QLabel

        central = QWidget()
        self._window.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar with modern styling
        options_widget = QWidget()
        options_widget.setFixedWidth(260)
        options_widget.setObjectName("sidebar")
        options_layout = QVBoxLayout(options_widget)
        options_layout.setContentsMargins(
            Theme.SPACING_LG_INT,
            Theme.SPACING_XL_INT,
            Theme.SPACING_LG_INT,
            Theme.SPACING_XL_INT,
        )
        options_layout.setSpacing(Theme.SPACING_SM_INT)

        # Modern header with enhanced typography
        header_label = QLabel("Batch File Sender")
        header_label.setObjectName("sidebar")
        header_label.setStyleSheet(
            f"""
            font-size: {Theme.FONT_SIZE_XL};
            font-weight: 700;
            color: {Theme.TEXT_ON_SIDEBAR};
            padding-bottom: {Theme.SPACING_LG};
            letter-spacing: 0.5px;
        """
        )
        options_layout.addWidget(header_label)

        # Navigation buttons with improved spacing
        add_dir_btn = QPushButton("Add Directory...")
        add_dir_btn.setObjectName("sidebar")
        add_dir_btn.setProperty("class", "sidebar")
        add_dir_btn.clicked.connect(self._select_folder)
        options_layout.addWidget(add_dir_btn)

        batch_add_btn = QPushButton("Batch Add Directories...")
        batch_add_btn.setObjectName("sidebar")
        batch_add_btn.setProperty("class", "sidebar")
        batch_add_btn.clicked.connect(self._batch_add_folders)
        options_layout.addWidget(batch_add_btn)

        defaults_btn = QPushButton("Set Defaults...")
        defaults_btn.setObjectName("sidebar")
        defaults_btn.setProperty("class", "sidebar")
        defaults_btn.clicked.connect(self._set_defaults_popup)
        options_layout.addWidget(defaults_btn)

        edit_settings_btn = QPushButton("Edit Settings...")
        edit_settings_btn.setObjectName("sidebar")
        edit_settings_btn.setProperty("class", "sidebar")
        edit_settings_btn.clicked.connect(self._show_edit_settings_dialog)
        options_layout.addWidget(edit_settings_btn)

        maintenance_btn = QPushButton("Maintenance...")
        maintenance_btn.setObjectName("sidebar")
        maintenance_btn.setProperty("class", "sidebar")
        maintenance_btn.clicked.connect(self._show_maintenance_dialog_wrapper)
        options_layout.addWidget(maintenance_btn)

        self._processed_files_button = QPushButton("Processed Files Report...")
        self._processed_files_button.setObjectName("sidebar")
        self._processed_files_button.setProperty("class", "sidebar")
        self._processed_files_button.clicked.connect(
            self._show_processed_files_dialog_wrapper
        )
        options_layout.addWidget(self._processed_files_button)

        # Flexible spacer
        options_layout.addItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )

        # Bottom action buttons
        self._allow_resend_button = QPushButton("Enable Resend...")
        self._allow_resend_button.setObjectName("sidebar")
        self._allow_resend_button.setProperty("class", "sidebar")
        self._allow_resend_button.clicked.connect(self._show_resend_dialog)
        options_layout.addWidget(self._allow_resend_button)

        # Modern separator with improved styling
        separator = QFrame()
        separator.setFixedHeight(1)
        separator.setObjectName("sidebar_separator")
        separator.setStyleSheet(
            f"""
            QFrame#sidebar_separator {{
                background-color: {Theme.SIDEBAR_OUTLINE};
                margin: {Theme.SPACING_MD} 0;
            }}
        """
        )
        options_layout.addWidget(separator)

        # Primary action button with enhanced prominence
        self._process_folder_button = QPushButton("Process All Folders")
        self._process_folder_button.setProperty("class", "primary")
        self._process_folder_button.clicked.connect(
            lambda: self._graphical_process_directories(self._database.folders_table)
        )
        options_layout.addWidget(self._process_folder_button)

        # Modern sidebar styling
        options_widget.setStyleSheet(
            f"""
            QWidget#sidebar {{
                background-color: {Theme.SIDEBAR_BACKGROUND};
                border-right: 1px solid {Theme.SIDEBAR_OUTLINE};
            }}
        """
        )

        main_layout.addWidget(options_widget)

        # Right panel with modern card-like appearance
        self._right_panel_widget = QWidget()
        self._right_panel_widget.setStyleSheet(
            f"""
            QWidget {{
                background-color: {Theme.BACKGROUND};
            }}
        """
        )
        right_layout = QVBoxLayout(self._right_panel_widget)
        right_layout.setContentsMargins(
            Theme.SPACING_XXL_INT,
            Theme.SPACING_XL_INT,
            Theme.SPACING_XXL_INT,
            Theme.SPACING_XL_INT,
        )
        right_layout.setSpacing(Theme.SPACING_LG_INT)

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
            on_toggle=self._toggle_folder,
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
        prior_folder = self._database.get_oversight_or_default()
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
                if folder_dict:
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
        prior_folder = self._database.get_oversight_or_default()
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
        edit_folder = self._database.folders_table.find_one(id=folder_to_be_edited)
        if edit_folder:
            self._open_edit_folders_dialog(edit_folder)
        else:
            self._ui_service.show_error(
                "Error", f"Folder with id {folder_to_be_edited} not found."
            )

    def _send_single(self, folder_id: int) -> None:
        self._progress_service.show("Working...")
        try:
            single_table = self._database.session_database["single_table"]
            single_table.drop()
        finally:
            single_table = self._database.session_database["single_table"]
            table_dict = self._database.folders_table.find_one(id=folder_id)
            if table_dict:
                table_dict["old_id"] = table_dict.pop("id")
                single_table.insert(table_dict)
            else:
                self._ui_service.show_error(
                    "Error", f"Folder with id {folder_id} not found."
                )
                return
            self._progress_service.hide()
            self._graphical_process_directories(single_table)
            single_table.drop()

    def _disable_folder(self, folder_id: int) -> None:
        self._folder_manager.disable_folder(folder_id)
        self._refresh_users_list()

    def _toggle_folder(self, folder_id: int) -> None:
        """Toggle a folder between active and inactive states."""
        folder = self._folder_manager.get_folder_by_id(folder_id)
        if folder:
            if folder["folder_is_active"] == "True":
                # Disable folder (no validation needed)
                self._folder_manager.disable_folder(folder_id)
            else:
                # Enable folder - validate that at least one backend is configured
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
                self._folder_manager.enable_folder(folder_id)
            self._refresh_users_list()
            self._set_main_button_states()

    def _set_folders_filter(self, filter_field_contents: str) -> None:
        self._folder_filter = filter_field_contents
        self._refresh_users_list()

    def _delete_folder_entry_wrapper(
        self, folder_to_be_removed: int, alias: str
    ) -> None:
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
        settings_dict = self._database.get_settings_or_default()

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
        reporting = self._database.get_oversight_or_default()
        run_log_name_constructor = (
            "Run Log " + str(time.ctime()).replace(":", "-") + ".txt"
        )

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
                from dispatch import process

                run_error_bool, run_summary_string = process(
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
        # Use safe accessor which guarantees non-None return
        defaults = self._database.get_oversight_or_default()
        # Create a copy to avoid modifying the persistent record
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
            self._database.get_oversight_or_default(),
            settings_provider=lambda: self._database.get_settings_or_default(),
            oversight_provider=lambda: self._database.get_oversight_or_default(),
            update_settings=lambda s: self._database.settings.update(s, ["id"]),
            update_oversight=lambda o: self._database.oversight_and_defaults.update(
                o, ["id"]
            ),
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
        from interface.qt.dialogs.database_import_dialog import (
            show_database_import_dialog,
        )
        from interface.operations.maintenance_functions import MaintenanceFunctions

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

        dlg = ResendDialog(
            parent=self._window, database_connection=self._database.database_connection
        )
        # Only show if data loaded successfully
        if dlg._should_show:
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

    def _mark_active_as_processed_wrapper(
        self, selected_folder: Optional[int] = None
    ) -> None:
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
