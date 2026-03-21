"""Diagnostics and self-test helpers for the Qt application."""

from __future__ import annotations

import os
import sys
from typing import Any

import appdirs
from PyQt5.QtWidgets import QApplication, QMainWindow

from backend.database.database_obj import DatabaseObj
from interface.operations.folder_manager import FolderManager


class QtDiagnosticsService:
    """Runs non-GUI and GUI self-tests for ``QtBatchFileSenderApp``."""

    def __init__(self, app: Any) -> None:
        self._app = app

    def run_self_test(self) -> int:
        print(
            f"Running self-test for {self._app._appname} Version {self._app._version}"
        )
        print(f"Platform: {self._app._running_platform}")
        print("=" * 50)

        failures = 0
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
            "PyQt5.QtCore",
            "PyQt5.QtWidgets",
            "PyQt5.QtGui",
            "PyQt5.QtPrintSupport",
            "PyQt5.QtSvg",
            "PyQt5.QtXml",
            "PyQt5.QtNetwork",
            "PyQt5.sip",
            "backend.database.database_obj",
            "interface.operations.folder_manager",
            "interface.ports",
            "interface.services.reporting_service",
            "interface.qt.app",
            "interface.qt.dialogs.edit_folders_dialog",
            "interface.qt.dialogs.edit_folders.data_extractor",
            "core.edi.edi_parser",
            "core.edi.edi_splitter",
            "core.edi.inv_fetcher",
            "core.edi.po_fetcher",
            "dispatch",
            "dispatch.orchestrator",
            "dispatch.send_manager",
            "dispatch.converters.convert_to_csv",
            "dispatch.converters.convert_to_fintech",
            "dispatch.converters.convert_to_simplified_csv",
            "dispatch.converters.convert_to_stewarts_custom",
            "dispatch.converters.convert_to_yellowdog_csv",
            "dispatch.converters.convert_to_estore_einvoice",
            "dispatch.converters.convert_to_estore_einvoice_generic",
            "dispatch.converters.convert_to_scannerware",
            "dispatch.converters.convert_to_scansheet_type_a",
            "dispatch.converters.convert_to_jolley_custom",
            "backend.ftp_client",
            "backend.smtp_client",
            "backend.copy_backend",
            "backend.ftp_backend",
            "backend.email_backend",
            "archive",
            "archive.edi_tweaks",
            "lxml",
            "lxml.etree",
        ]

        optional_modules = []
        if sys.platform != "win32":
            optional_modules = ["pyodbc", "PIL"]
        else:
            required_modules.extend(["pyodbc", "PIL"])

        print("\n1. Checking module imports...")
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

        print("\n2. Checking configuration directories...")
        try:
            self._app._setup_config_directories()
            if self._app._config_folder and os.path.exists(self._app._config_folder):
                print(f"  [OK] Config directory: {self._app._config_folder}")
            else:
                print(
                    f"  [FAIL] Config directory not created: {self._app._config_folder}"
                )
                failures += 1
        except Exception as e:
            print(f"  [FAIL] Failed to setup config directories: {e}")
            failures += 1

        print("\n3. Checking appdirs functionality...")
        try:
            test_config = appdirs.user_data_dir("TestApp")
            print(f"  [OK] appdirs module working: {test_config}")
        except Exception as e:
            print(f"  [FAIL] appdirs module error: {e}")
            failures += 1

        print("\n4. Checking file system access...")
        try:
            temp_dir = os.path.join(os.path.expanduser("~"), "BatchFileSenderTest")
            os.makedirs(temp_dir, exist_ok=True)
            temp_file = os.path.join(temp_dir, "test.tmp")
            with open(temp_file, "w") as f:
                f.write("test")
            os.remove(temp_file)
            os.rmdir(temp_dir)
            print("  [OK] File system access working")
        except Exception as e:
            print(f"  [FAIL] File system access error: {e}")
            failures += 1

        print("\n" + "=" * 50)
        if failures == 0:
            print(
                f"[PASS] Self-test passed - all {len(required_modules)} checks successful"
            )
            return 0

        print(
            f"[FAIL] Self-test failed - {failures} out of {len(required_modules)} checks failed"
        )
        return 1

    def run_gui_self_test(self) -> int:
        from PyQt5.QtCore import QTimer

        print(f"\n{'=' * 50}")
        print("GUI Self-Test")
        print("=" * 50)

        failures = 0

        print("\n1. Creating QApplication...")
        try:
            self._app._app = QApplication.instance() or QApplication(sys.argv)
            print("  [OK] QApplication created")
        except Exception as e:
            print(f"  [FAIL] QApplication creation failed: {e}")
            return 1

        print("\n2. Creating main window...")
        try:
            self._app._window = QMainWindow()
            self._app._window.setWindowTitle(
                f"{self._app._appname} {self._app._version} (GUI Test)"
            )
            print("  [OK] QMainWindow created")
        except Exception as e:
            print(f"  [FAIL] QMainWindow creation failed: {e}")
            return 1

        print("\n3. Initializing database and services...")
        try:
            self._app._setup_config_directories()
            if self._app._database is None:
                self._app._database = DatabaseObj(
                    self._app._database_path,
                    self._app._database_version,
                    self._app._config_folder,
                    self._app._running_platform,
                )
            print("  [OK] Database initialized")
        except Exception as e:
            print(f"  [FAIL] Database initialization failed: {e}")
            failures += 1

        try:
            self._app._folder_manager = FolderManager(self._app._database)
            print("  [OK] FolderManager initialized")
        except Exception as e:
            print(f"  [FAIL] FolderManager initialization failed: {e}")
            failures += 1

        print("\n4. Building UI components...")
        try:
            self._app._build_main_window()
            print("  [OK] Main window built")
        except Exception as e:
            print(f"  [FAIL] Main window build failed: {e}")
            failures += 1

        print("\n5. Verifying widgets...")
        widgets_to_check = [
            ("Folder list widget", self._app._folder_list_widget),
            ("Search widget", self._app._search_widget),
            ("Right panel widget", self._app._right_panel_widget),
            ("Process folder button", self._app._process_folder_button),
            ("Processed files button", self._app._processed_files_button),
            ("Allow resend button", self._app._allow_resend_button),
        ]

        for widget_name, widget in widgets_to_check:
            if widget is not None:
                print(f"  [OK] {widget_name}")
            else:
                print(f"  [FAIL] {widget_name} is None")
                failures += 1

        print("\n6. Displaying window (will auto-close in 2 seconds)...")
        try:
            self._app._window.show()
            print("  [OK] Window displayed")
        except Exception as e:
            print(f"  [FAIL] Window display failed: {e}")
            failures += 1

        def close_and_quit() -> None:
            print("\n7. Closing window...")
            self._app._window.close()
            self._app._app.quit()
            print("  [OK] Window closed")
            print(f"\n{'=' * 50}")
            if failures == 0:
                print("[PASS] GUI self-test passed")
            else:
                print(f"[FAIL] GUI self-test failed with {failures} errors")
            print("=" * 50)

        QTimer.singleShot(2000, close_and_quit)
        return self._app._app.exec()
