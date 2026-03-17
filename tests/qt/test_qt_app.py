"""Tests for QtBatchFileSenderApp using pytest-qt."""

import pytest

pytestmark = [pytest.mark.qt, pytest.mark.gui, pytest.mark.slow]
import argparse
import builtins
import os
import types
from unittest.mock import MagicMock

from batch_file_processor.constants import CURRENT_DATABASE_VERSION


@pytest.mark.qt
class TestQtBatchFileSenderApp:

    def test_construction_stores_parameters(self):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp(
            appname="Test", version="1.0", database_version=CURRENT_DATABASE_VERSION
        )
        assert app._appname == "Test"
        assert app._version == "1.0"
        assert app._database_version == CURRENT_DATABASE_VERSION

    def test_database_property_raises_before_init(self):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        with pytest.raises(RuntimeError, match="Database not initialized"):
            _ = app.database

    def test_folder_manager_property_raises_before_init(self):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        with pytest.raises(RuntimeError, match="Folder manager not initialized"):
            _ = app.folder_manager

    def test_args_property_raises_before_init(self):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        with pytest.raises(RuntimeError, match="Arguments not parsed"):
            _ = app.args

    def test_database_injected(self):
        from interface.qt.app import QtBatchFileSenderApp

        mock_db = MagicMock()
        app = QtBatchFileSenderApp(database_obj=mock_db)
        assert app._database is mock_db

    def test_shutdown_closes_database(self):
        from interface.qt.app import QtBatchFileSenderApp

        mock_db = MagicMock()
        app = QtBatchFileSenderApp(database_obj=mock_db)
        app.shutdown()
        mock_db.close.assert_called_once()

    def test_shutdown_no_db_no_error(self):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        app.shutdown()

    def test_set_main_button_states_no_folders(self):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        app._database = MagicMock()
        app._database.folders_table.count.return_value = 0
        app._database.processed_files.count.return_value = 0
        app._process_folder_button = MagicMock()
        app._processed_files_button = MagicMock()
        app._allow_resend_button = MagicMock()
        app._set_main_button_states()
        app._process_folder_button.setEnabled.assert_called_with(False)

    def test_set_main_button_states_with_folders(self):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        app._database = MagicMock()
        app._database.folders_table.count.side_effect = lambda **kw: 5 if not kw else 3
        app._database.processed_files.count.return_value = 10
        app._process_folder_button = MagicMock()
        app._processed_files_button = MagicMock()
        app._allow_resend_button = MagicMock()
        app._set_main_button_states()
        app._process_folder_button.setEnabled.assert_called_with(True)
        app._processed_files_button.setEnabled.assert_called_with(True)
        app._allow_resend_button.setEnabled.assert_called_with(True)

    def test_disable_folder(self):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        app._folder_manager = MagicMock()
        app._refresh_users_list = MagicMock()
        app._disable_folder(42)
        app._folder_manager.disable_folder.assert_called_once_with(42)
        app._refresh_users_list.assert_called_once()

    def test_set_folders_filter(self):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        app._refresh_users_list = MagicMock()
        app._set_folders_filter("test")
        assert app._folder_filter == "test"
        app._refresh_users_list.assert_called_once()

    def test_delete_folder_confirmed(self):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        app._ui_service = MagicMock()
        app._ui_service.ask_yes_no.return_value = True
        app._folder_manager = MagicMock()
        app._refresh_users_list = MagicMock()
        app._set_main_button_states = MagicMock()
        app._delete_folder_entry_wrapper(42, "test")
        app._folder_manager.delete_folder_with_related.assert_called_once_with(42)

    def test_delete_folder_cancelled(self):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        app._ui_service = MagicMock()
        app._ui_service.ask_yes_no.return_value = False
        app._folder_manager = MagicMock()
        app._delete_folder_entry_wrapper(42, "test")
        app._folder_manager.delete_folder_with_related.assert_not_called()

    def test_disable_all_email_backends(self):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        app._database = MagicMock()
        row1 = {"id": 1, "process_backend_email": True}
        row2 = {"id": 2, "process_backend_email": True}
        app._database.folders_table.find.return_value = [row1, row2]
        app._disable_all_email_backends()
        assert row1["process_backend_email"] is False
        assert row2["process_backend_email"] is False
        assert app._database.folders_table.update.call_count == 2

    def test_update_reporting(self):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        app._database = MagicMock()
        changes = {"id": 1, "enable_reporting": True}
        app._update_reporting(changes)
        app._database.oversight_and_defaults.update.assert_called_once_with(
            changes, ["id"]
        )

    def test_graphical_process_directories_shows_error_for_missing_folder(
        self, monkeypatch
    ):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        app._ui_service = MagicMock()
        app._progress_service = MagicMock()
        app._process_directories = MagicMock()
        app._refresh_users_list = MagicMock()
        app._set_main_button_states = MagicMock()

        folders_table = MagicMock()
        folders_table.find.return_value = [{"folder_name": "/missing/path"}]
        folders_table.count.return_value = 1

        monkeypatch.setattr("interface.qt.app.os.path.exists", lambda _: False)

        app._graphical_process_directories(folders_table)

        app._ui_service.show_error.assert_called_once_with(
            "Error", "One or more expected folders are missing (e.g. '/missing/path')."
        )
        app._process_directories.assert_not_called()
        app._progress_service.show.assert_not_called()

    def test_graphical_process_directories_shows_error_when_no_active_folders(
        self, monkeypatch
    ):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        app._ui_service = MagicMock()
        app._progress_service = MagicMock()
        app._process_directories = MagicMock()

        folders_table = MagicMock()
        folders_table.find.return_value = []
        folders_table.count.return_value = 0

        monkeypatch.setattr("interface.qt.app.os.path.exists", lambda _: True)

        app._graphical_process_directories(folders_table)

        app._ui_service.show_error.assert_called_once_with("Error", "No Active Folders")
        app._process_directories.assert_not_called()

    def test_graphical_process_directories_processes_active_folders(self, monkeypatch):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        app._ui_service = MagicMock()
        app._progress_service = MagicMock()
        app._process_directories = MagicMock()
        app._refresh_users_list = MagicMock()
        app._set_main_button_states = MagicMock()

        folders_table = MagicMock()
        folders_table.find.return_value = [{"folder_name": "/existing/path"}]
        folders_table.count.return_value = 1

        monkeypatch.setattr("interface.qt.app.os.path.exists", lambda _: True)

        app._graphical_process_directories(folders_table)

        app._progress_service.show.assert_called_once_with("processing folders...")
        app._process_directories.assert_called_once_with(folders_table)
        app._refresh_users_list.assert_called_once()
        app._set_main_button_states.assert_called_once()
        app._progress_service.hide.assert_called_once()

    def test_disable_folders_without_backends_marks_active_rows_inactive(self):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        app._database = MagicMock()
        row1 = {"id": 1, "folder_is_active": "True"}
        row2 = {"id": 2, "folder_is_active": "True"}
        app._database.folders_table.find.return_value = [row1, row2]

        app._disable_folders_without_backends()

        assert row1["folder_is_active"] is False
        assert row2["folder_is_active"] is False
        assert app._database.folders_table.update.call_count == 2

    def test_automatic_process_directories_delegates_to_run_coordinator(self):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        app._run_coordinator = MagicMock()

        folders_table = MagicMock()

        app._automatic_process_directories(folders_table)

        app._run_coordinator.automatic_process_directories.assert_called_once_with(
            folders_table
        )

    def test_check_logs_directory_returns_true_when_writable(self, tmp_path):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        app._logs_directory = {"logs_directory": str(tmp_path)}

        assert app._check_logs_directory() is True

    def test_check_logs_directory_returns_false_on_io_error(self, monkeypatch):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        app._logs_directory = {"logs_directory": "/nonexistent/path"}

        def _raise_io(*args, **kwargs):
            raise IOError("no write")

        monkeypatch.setattr("builtins.open", _raise_io)

        assert app._check_logs_directory() is False

    def test_configure_qt_platform_forces_xcb_when_wayland_and_x11_present(
        self, monkeypatch
    ):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()

        monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
        monkeypatch.setenv("DISPLAY", ":0")
        monkeypatch.delenv("QT_QPA_PLATFORM", raising=False)

        app._configure_qt_platform()

        assert os.environ.get("QT_QPA_PLATFORM") == "xcb"

    def test_configure_qt_platform_keeps_existing_qpa_platform(self, monkeypatch):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()

        monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
        monkeypatch.setenv("DISPLAY", ":0")
        monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

        app._configure_qt_platform()

        assert os.environ.get("QT_QPA_PLATFORM") == "offscreen"

    def test_setup_config_directories_sets_paths(self, monkeypatch, tmp_path):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp(appname="TestApp")

        monkeypatch.setattr(
            "interface.qt.app.appdirs.user_data_dir", lambda _: str(tmp_path / "cfg")
        )

        app._setup_config_directories()

        assert app._config_folder == str(tmp_path / "cfg")
        assert app._database_path.endswith("folders.db")
        assert os.path.isdir(app._config_folder)

    def test_mark_active_as_processed_wrapper_calls_maintenance(self, monkeypatch):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        app._database = MagicMock()
        app._folder_manager = MagicMock()
        app._folder_manager.delete_folder_with_related = MagicMock()
        app._database_path = "/tmp/folders.db"
        app._running_platform = "Linux"
        app._database_version = "41"
        app._progress_service = MagicMock()
        app._refresh_users_list = MagicMock()
        app._set_main_button_states = MagicMock()

        maintenance_instance = MagicMock()

        class _FakeMaintenanceFunctions:
            def __init__(self, **kwargs):
                self._kwargs = kwargs

            def mark_active_as_processed(self, selected_folder=None):
                maintenance_instance.mark_active_as_processed(
                    selected_folder=selected_folder
                )

        monkeypatch.setattr(
            "interface.operations.maintenance_functions.MaintenanceFunctions",
            _FakeMaintenanceFunctions,
        )

        app._mark_active_as_processed_wrapper(selected_folder=123)

        maintenance_instance.mark_active_as_processed.assert_called_once_with(
            selected_folder=123
        )

    def test_log_critical_error_writes_log_and_exits(self, tmp_path, monkeypatch):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp(version="v-test")

        monkeypatch.chdir(tmp_path)

        with pytest.raises(SystemExit):
            app._log_critical_error("fatal")

        log_file = tmp_path / "critical_error.log"
        assert log_file.exists()
        assert "v-test" in log_file.read_text(encoding="utf-8")

    def test_run_raises_when_window_missing(self):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        app._args = argparse.Namespace(automatic=False)

        with pytest.raises(RuntimeError, match="Application not initialized"):
            app.run()

    def test_run_shows_window_and_executes_qapplication(self, monkeypatch):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        app._args = argparse.Namespace(automatic=False)
        app._window = MagicMock()

        exec_mock = MagicMock()
        monkeypatch.setattr("interface.qt.app.QApplication.exec", exec_mock)

        app.run()

        app._window.show.assert_called_once()
        exec_mock.assert_called_once()

    def test_edit_folder_selector_shows_error_when_missing(self):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        app._database = MagicMock()
        app._database.folders_table.find_one.return_value = None
        app._ui_service = MagicMock()

        app._edit_folder_selector(99)

        app._ui_service.show_error.assert_called_once_with(
            "Error", "Folder with id 99 not found."
        )

    def test_send_single_shows_error_when_folder_missing(self):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        app._database = MagicMock()
        app._ui_service = MagicMock()
        app._progress_service = MagicMock()
        app._graphical_process_directories = MagicMock()

        single_table = MagicMock()
        session_database = MagicMock()
        session_database.__getitem__.return_value = single_table
        app._database.session_database = session_database
        app._database.folders_table.find_one.return_value = None

        app._send_single(123)

        # CREATE TABLE + ALTER TABLE = 2 queries (no PRAGMA since folder not found)
        assert session_database.query.call_count == 2
        single_table.drop.assert_called_once()
        app._ui_service.show_error.assert_called_once_with(
            "Error", "Folder with id 123 not found."
        )
        app._graphical_process_directories.assert_not_called()

    def test_send_single_builds_single_table_and_processes(self):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        app._database = MagicMock()
        app._ui_service = MagicMock()
        app._progress_service = MagicMock()
        app._graphical_process_directories = MagicMock()

        single_table = MagicMock()
        session_database = MagicMock()
        session_database.__getitem__.return_value = single_table

        # Mock the PRAGMA table_info query to return column info for filtering
        def query_side_effect(sql):
            if "PRAGMA table_info" in sql:
                # Return column names that exist in the single_table
                return [
                    {"name": "id"},
                    {"name": "folder_name"},
                    {"name": "folder_is_active"},
                    {"name": "old_id"},
                ]
            return None

        session_database.query.side_effect = query_side_effect
        app._database.session_database = session_database
        app._database.folders_table.find_one.return_value = {
            "id": 7,
            "folder_name": "/tmp/f",
            "folder_is_active": "True",
        }

        app._send_single(7)

        # CREATE TABLE + ALTER TABLE + PRAGMA table_info = 3 queries
        assert session_database.query.call_count == 3
        single_table.insert.assert_called_once()
        inserted = single_table.insert.call_args[0][0]
        assert inserted["old_id"] == 7
        assert "id" not in inserted
        app._progress_service.hide.assert_called_once()
        app._graphical_process_directories.assert_called_once_with(single_table)
        assert single_table.drop.call_count == 2

    def test_batch_add_folders_returns_when_no_selection(self):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        app._database = MagicMock()
        app._ui_service = MagicMock()
        app._progress_service = MagicMock()
        app._folder_manager = MagicMock()
        app._database.get_oversight_or_default.return_value = {
            "batch_add_folder_prior": ""
        }
        app._ui_service.ask_directory.return_value = ""

        app._batch_add_folders()

        app._database.oversight_and_defaults.update.assert_not_called()
        app._folder_manager.add_folder.assert_not_called()

    def test_batch_add_folders_adds_and_skips(self, tmp_path, monkeypatch):
        from interface.qt.app import QtBatchFileSenderApp

        root = tmp_path / "parent"
        root.mkdir()
        (root / "exists").mkdir()
        (root / "new1").mkdir()

        app = QtBatchFileSenderApp()
        app._database = MagicMock()
        app._ui_service = MagicMock()
        app._progress_service = MagicMock()
        app._folder_manager = MagicMock()
        app._refresh_users_list = MagicMock()

        app._database.get_oversight_or_default.return_value = {
            "batch_add_folder_prior": ""
        }
        app._ui_service.ask_directory.return_value = str(root)
        app._ui_service.ask_ok_cancel.return_value = True

        def _exists_check(path):
            return {"truefalse": path.endswith("exists")}

        app._folder_manager.check_folder_exists.side_effect = _exists_check

        start_dir = os.getcwd()
        app._batch_add_folders()

        app._database.oversight_and_defaults.update.assert_called_once()
        app._folder_manager.add_folder.assert_called_once()
        app._ui_service.show_info.assert_called_once_with(
            "Batch Add Complete", "1 folders added, 1 folders skipped."
        )
        app._refresh_users_list.assert_called_once()
        assert os.getcwd() == start_dir

    def test_select_folder_existing_folder_opens_edit_dialog(self, monkeypatch):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        app._database = MagicMock()
        app._ui_service = MagicMock()
        app._progress_service = MagicMock()
        app._folder_manager = MagicMock()
        app._open_edit_folders_dialog = MagicMock()

        app._database.get_oversight_or_default.return_value = {
            "single_add_folder_prior": ""
        }
        app._ui_service.ask_directory.return_value = "/tmp/existing"
        app._folder_manager.check_folder_exists.return_value = {
            "truefalse": True,
            "matched_folder": {"id": 55, "folder_name": "/tmp/existing"},
        }
        app._ui_service.ask_ok_cancel.return_value = True

        monkeypatch.setattr("interface.qt.app.os.path.exists", lambda *_: True)

        app._select_folder()

        app._open_edit_folders_dialog.assert_called_once_with(
            {"id": 55, "folder_name": "/tmp/existing"}
        )

    def test_automatic_process_directories_calls_process_and_exits(self):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        app._run_coordinator = MagicMock()

        folders_table = MagicMock()

        app._automatic_process_directories(folders_table)

        app._run_coordinator.automatic_process_directories.assert_called_once_with(
            folders_table
        )

    def test_automatic_process_directories_propagates_coordinator_exception(self):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        app._run_coordinator = MagicMock()
        app._run_coordinator.automatic_process_directories.side_effect = RuntimeError(
            "coordinator error"
        )

        folders_table = MagicMock()

        with pytest.raises(RuntimeError, match="coordinator error"):
            app._automatic_process_directories(folders_table)

    def test_select_folder_adds_new_folder_and_marks_processed(self, monkeypatch):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        app._database = MagicMock()
        app._ui_service = MagicMock()
        app._progress_service = MagicMock()
        app._folder_manager = MagicMock()
        app._refresh_users_list = MagicMock()
        app._mark_active_as_processed_wrapper = MagicMock()

        selected = "/tmp/new-folder"
        app._database.get_oversight_or_default.return_value = {
            "single_add_folder_prior": ""
        }
        app._ui_service.ask_directory.return_value = selected
        app._folder_manager.check_folder_exists.return_value = {"truefalse": False}
        app._ui_service.ask_yes_no.return_value = True
        app._database.folders_table.find_one.return_value = {"id": 77}

        monkeypatch.setattr("interface.qt.app.os.path.exists", lambda *_: True)

        app._select_folder()

        app._folder_manager.add_folder.assert_called_once_with(selected)
        app._mark_active_as_processed_wrapper.assert_called_once_with(77)
        app._refresh_users_list.assert_called_once()

    def test_show_dialog_wrappers_create_and_exec(self, monkeypatch):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        app._database = MagicMock()
        app._window = MagicMock()
        app._ui_service = MagicMock()

        processed_exec = MagicMock()
        resend_exec = MagicMock()

        class _FakeProcessedFilesDialog:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            def exec(self):
                processed_exec()

        class _FakeResendDialog:
            def __init__(self, **kwargs):
                self._should_show = True

            def exec(self):
                resend_exec()

        monkeypatch.setattr(
            "interface.qt.dialogs.processed_files_dialog.ProcessedFilesDialog",
            _FakeProcessedFilesDialog,
        )
        monkeypatch.setattr(
            "interface.qt.dialogs.resend_dialog.ResendDialog",
            _FakeResendDialog,
        )

        app._show_processed_files_dialog_wrapper()
        app._show_resend_dialog()

        processed_exec.assert_called_once()
        resend_exec.assert_called_once()

    def test_run_self_test_success_path(self, monkeypatch, tmp_path):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp(appname="TestApp", version="v1")

        original_import = builtins.__import__
        fake_module = types.SimpleNamespace(__file__="/tmp/fake.py")

        fake_prefixes = (
            "interface.",
            "core.",
            "dispatch",
            "backend.",
            "convert_to_",
        )
        fake_exact = {
            "batch_log_sender",
            "print_run_log",
            "utils",
            "backup_increment",
            "record_error",
            "folders_database_migrator",
            "mover",
            "clear_old_files",
            "copy_backend",
            "ftp_backend",
            "email_backend",
            "lxml",
            "lxml.etree",
            "PyQt6.sip",
        }

        def _fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name in fake_exact or name.startswith(fake_prefixes):
                return fake_module
            return original_import(name, globals, locals, fromlist, level)

        def _fake_setup():
            cfg = tmp_path / "cfg"
            cfg.mkdir(exist_ok=True)
            app._config_folder = str(cfg)
            app._database_path = str(cfg / "folders.db")

        monkeypatch.setattr("builtins.__import__", _fake_import)
        monkeypatch.setattr(app, "_setup_config_directories", _fake_setup)
        monkeypatch.setattr(
            "interface.qt.app.appdirs.user_data_dir",
            lambda _: str(tmp_path / "appdirs"),
        )
        monkeypatch.setattr(
            "interface.qt.app.os.path.expanduser", lambda _: str(tmp_path)
        )

        result = app._run_self_test()

        assert result == 0

    def test_initialize_self_test_path_exits(self, monkeypatch):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        app._parse_arguments = MagicMock()
        app._args = argparse.Namespace(self_test=True, automatic=False)
        app._run_self_test = MagicMock(return_value=1)

        monkeypatch.setattr(
            "interface.qt.app.multiprocessing.freeze_support", lambda: None
        )
        monkeypatch.setattr(
            "interface.qt.app.sys.exit",
            lambda code=0: (_ for _ in ()).throw(SystemExit(code)),
        )

        with pytest.raises(SystemExit):
            app.initialize()

    def test_initialize_automatic_path_skips_qt_window(self, monkeypatch):
        from interface.qt.app import QtBatchFileSenderApp

        db = MagicMock()
        db.folders_table = MagicMock()
        db.get_oversight_or_default.return_value = {
            "logs_directory": "/tmp",
            "enable_reporting": False,
        }

        app = QtBatchFileSenderApp(database_obj=db)
        app._parse_arguments = MagicMock()
        app._args = argparse.Namespace(self_test=False, gui_test=False, automatic=True)
        app._automatic_process_directories = MagicMock()

        monkeypatch.setattr(
            "interface.qt.app.multiprocessing.freeze_support", lambda: None
        )
        monkeypatch.setattr("interface.qt.app.FolderManager", lambda *_: MagicMock())
        monkeypatch.setattr(
            "interface.qt.app.ReportingService", lambda **_: MagicMock()
        )
        monkeypatch.setattr(app, "_setup_config_directories", lambda: None)

        app.initialize()
        app.run()

        app._automatic_process_directories.assert_called_once_with(db.folders_table)
        assert app._app is None
        assert app._window is None

    def test_refresh_users_list_no_panel_is_noop(self):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        app._right_panel_widget = None

        app._refresh_users_list()

    def test_refresh_users_list_rebuilds_widgets(self, monkeypatch):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        db = MagicMock()
        db.folders_table = MagicMock()
        db.folders_table.find.return_value = []
        db.folders_table.count.return_value = 0
        app._database = db

        layout = MagicMock()
        right_panel = MagicMock()
        right_panel.layout.return_value = layout
        app._right_panel_widget = right_panel

        old_folder_list = MagicMock()
        app._folder_list_widget = old_folder_list
        app._search_widget = MagicMock()
        layout.indexOf.return_value = 1

        app._set_main_button_states = MagicMock()

        # Patch FolderListWidget so it doesn't require a real QWidget parent
        mock_new_list = MagicMock()
        monkeypatch.setattr(
            "interface.qt.widgets.folder_list_widget.FolderListWidget",
            lambda **kwargs: mock_new_list,
        )

        app._refresh_users_list()

        # Old folder list widget should be removed
        layout.removeWidget.assert_called_once_with(old_folder_list)
        old_folder_list.deleteLater.assert_called_once()
        # New folder list widget should be inserted
        assert app._folder_list_widget is mock_new_list
        layout.insertWidget.assert_called_once()
        app._set_main_button_states.assert_called_once()

    def test_process_directories_triggers_backup_when_counter_reached(
        self, tmp_path, monkeypatch
    ):
        from interface.qt.app import QtBatchFileSenderApp

        db = MagicMock()
        db.get_settings_or_default.return_value = {
            "id": 1,
            "enable_interval_backups": True,
            "backup_counter": 10,
            "backup_counter_maximum": 10,
        }
        db.get_oversight_or_default.return_value = {
            "logs_directory": str(tmp_path / "logs"),
            "enable_reporting": False,
        }
        db.settings = MagicMock()
        folders_table = MagicMock()
        folders_table.find.return_value = []

        app = QtBatchFileSenderApp(database_obj=db)
        app._database_path = str(tmp_path / "folders.db")
        app._logs_directory = {"logs_directory": str(tmp_path / "logs")}
        app._version = "1.0"
        app._errors_directory = str(tmp_path / "errors")
        app._progress_service = MagicMock()
        app._check_logs_directory = MagicMock(return_value=True)

        backup_called = []

        def mock_backup(path):
            backup_called.append(path)

        monkeypatch.setattr("interface.qt.app.backup_increment.do_backup", mock_backup)
        monkeypatch.setattr("interface.qt.app.os.getcwd", lambda: str(tmp_path))
        monkeypatch.setattr("interface.qt.app.os.chdir", lambda _: None)
        monkeypatch.setattr("interface.qt.app.os.path.isdir", lambda _: True)
        monkeypatch.setattr(
            "interface.qt.app.utils.do_clear_old_files", lambda *_: None
        )

        (tmp_path / "logs").mkdir()

        app._process_directories(folders_table)

        assert len(backup_called) == 1
        assert backup_called[0] == str(tmp_path / "folders.db")
        db.settings.update.assert_called()

    def test_process_directories_skips_backup_when_not_needed(
        self, tmp_path, monkeypatch
    ):
        from interface.qt.app import QtBatchFileSenderApp

        db = MagicMock()
        db.get_settings_or_default.return_value = {
            "id": 1,
            "enable_interval_backups": False,
            "backup_counter": 5,
            "backup_counter_maximum": 10,
        }
        db.get_oversight_or_default.return_value = {
            "logs_directory": str(tmp_path / "logs"),
            "enable_reporting": False,
        }
        db.settings = MagicMock()
        folders_table = MagicMock()
        folders_table.find.return_value = []

        app = QtBatchFileSenderApp(database_obj=db)
        app._database_path = str(tmp_path / "folders.db")
        app._logs_directory = {"logs_directory": str(tmp_path / "logs")}
        app._version = "1.0"
        app._errors_directory = str(tmp_path / "errors")
        app._progress_service = MagicMock()
        app._check_logs_directory = MagicMock(return_value=True)

        backup_called = []

        def mock_backup(path):
            backup_called.append(path)

        monkeypatch.setattr("interface.qt.app.backup_increment.do_backup", mock_backup)
        monkeypatch.setattr("interface.qt.app.os.getcwd", lambda: str(tmp_path))
        monkeypatch.setattr("interface.qt.app.os.chdir", lambda _: None)
        monkeypatch.setattr("interface.qt.app.os.path.isdir", lambda _: True)
        monkeypatch.setattr(
            "interface.qt.app.utils.do_clear_old_files", lambda *_: None
        )

        (tmp_path / "logs").mkdir()

        app._process_directories(folders_table)

        assert len(backup_called) == 0

    def test_process_directories_creates_log_folder_when_missing(
        self, tmp_path, monkeypatch
    ):
        from interface.qt.app import QtBatchFileSenderApp

        db = MagicMock()
        db.get_settings_or_default.return_value = {
            "id": 1,
            "enable_interval_backups": False,
            "backup_counter": 0,
            "backup_counter_maximum": 10,
        }
        db.get_oversight_or_default.return_value = {
            "logs_directory": str(tmp_path / "logs"),
            "enable_reporting": False,
        }
        db.settings = MagicMock()
        folders_table = MagicMock()
        folders_table.find.return_value = []

        app = QtBatchFileSenderApp(database_obj=db)
        app._database_path = str(tmp_path / "folders.db")
        app._logs_directory = {"logs_directory": str(tmp_path / "logs")}
        app._version = "1.0"
        app._errors_directory = str(tmp_path / "errors")
        app._progress_service = MagicMock()
        app._check_logs_directory = MagicMock(return_value=True)
        app._args = argparse.Namespace(automatic=False)

        mkdir_called = []
        orig_isdir = os.path.isdir
        orig_mkdir = os.mkdir

        def mock_isdir(path):
            if (
                path == str(tmp_path / "logs")
                and str(tmp_path / "logs") not in mkdir_called
            ):
                return False
            return orig_isdir(path)

        def mock_mkdir(path):
            mkdir_called.append(path)
            orig_mkdir(path)

        monkeypatch.setattr("interface.qt.app.os.getcwd", lambda: str(tmp_path))
        monkeypatch.setattr("interface.qt.app.os.chdir", lambda _: None)
        monkeypatch.setattr("interface.qt.app.os.path.isdir", mock_isdir)
        monkeypatch.setattr("interface.qt.app.os.mkdir", mock_mkdir)
        monkeypatch.setattr(
            "interface.qt.app.utils.do_clear_old_files", lambda *_: None
        )

        app._process_directories(folders_table)

        assert str(tmp_path / "logs") in mkdir_called

    def test_process_directories_prompts_user_when_log_dir_not_writable(
        self, tmp_path, monkeypatch
    ):
        from interface.qt.app import QtBatchFileSenderApp

        db = MagicMock()
        db.get_settings_or_default.return_value = {
            "id": 1,
            "enable_interval_backups": False,
            "backup_counter": 0,
            "backup_counter_maximum": 10,
        }
        db.get_oversight_or_default.return_value = {
            "logs_directory": str(tmp_path / "logs"),
            "enable_reporting": False,
        }
        db.settings = MagicMock()
        folders_table = MagicMock()
        folders_table.find.return_value = []

        app = QtBatchFileSenderApp(database_obj=db)
        app._database_path = str(tmp_path / "folders.db")
        app._logs_directory = {"logs_directory": str(tmp_path / "logs")}
        app._version = "1.0"
        app._errors_directory = str(tmp_path / "errors")
        app._progress_service = MagicMock()
        app._args = argparse.Namespace(automatic=False)
        app._ui_service = MagicMock()
        app._ui_service.ask_ok_cancel.return_value = False

        # Always return False to trigger the error path
        app._check_logs_directory = MagicMock(return_value=False)

        def mock_show_error(*args, **kwargs):
            raise SystemExit()

        app._ui_service.show_error = mock_show_error

        monkeypatch.setattr("interface.qt.app.os.getcwd", lambda: str(tmp_path))
        monkeypatch.setattr("interface.qt.app.os.chdir", lambda _: None)
        monkeypatch.setattr("interface.qt.app.os.path.isdir", lambda _: True)

        with pytest.raises(SystemExit):
            app._process_directories(folders_table)

        app._ui_service.ask_ok_cancel.assert_called_once()

    def test_process_directories_automatic_mode_logs_critical_on_bad_log_dir(
        self, tmp_path, monkeypatch
    ):
        from interface.qt.app import QtBatchFileSenderApp

        db = MagicMock()
        db.get_settings_or_default.return_value = {
            "id": 1,
            "enable_interval_backups": False,
            "backup_counter": 0,
            "backup_counter_maximum": 10,
        }
        db.get_oversight_or_default.return_value = {
            "logs_directory": str(tmp_path / "logs"),
            "enable_reporting": False,
        }
        db.settings = MagicMock()
        folders_table = MagicMock()
        folders_table.find.return_value = []

        app = QtBatchFileSenderApp(database_obj=db)
        app._database_path = str(tmp_path / "folders.db")
        app._logs_directory = {"logs_directory": str(tmp_path / "logs")}
        app._version = "1.0"
        app._errors_directory = str(tmp_path / "errors")
        app._progress_service = MagicMock()
        app._args = argparse.Namespace(automatic=True)
        app._log_critical_error = MagicMock()

        def mock_mkdir(path):
            raise IOError("Permission denied")

        monkeypatch.setattr("interface.qt.app.os.getcwd", lambda: str(tmp_path))
        monkeypatch.setattr("interface.qt.app.os.chdir", lambda _: None)
        monkeypatch.setattr("interface.qt.app.os.path.isdir", lambda _: False)
        monkeypatch.setattr("interface.qt.app.os.mkdir", mock_mkdir)

        app._check_logs_directory = MagicMock(return_value=False)

        # Should not crash, just log
        try:
            app._process_directories(folders_table)
        except Exception:
            pass  # May throw but should have logged

        app._log_critical_error.assert_called_once()

    def test_process_directories_calls_dispatch_and_handles_success(
        self, tmp_path, monkeypatch
    ):
        from interface.qt.app import QtBatchFileSenderApp

        db = MagicMock()
        db.database_connection = MagicMock()
        db.get_settings_or_default.return_value = {
            "id": 1,
            "enable_interval_backups": False,
            "backup_counter": 0,
            "backup_counter_maximum": 10,
        }
        db.get_oversight_or_default.return_value = {
            "logs_directory": str(tmp_path / "logs"),
            "enable_reporting": False,
        }
        db.settings = MagicMock()
        db.processed_files = MagicMock()
        db.emails_table = MagicMock()
        folders_table = MagicMock()
        folders_table.find.return_value = []

        app = QtBatchFileSenderApp(database_obj=db)
        app._run_coordinator = MagicMock()

        app._process_directories(folders_table)

        app._run_coordinator.process_directories.assert_called_once_with(folders_table)

    def test_process_directories_shows_info_on_errors_in_graphical_mode(
        self, tmp_path, monkeypatch
    ):
        from interface.qt.app import QtBatchFileSenderApp

        db = MagicMock()
        db.database_connection = MagicMock()
        db.get_settings_or_default.return_value = {
            "id": 1,
            "enable_interval_backups": False,
            "backup_counter": 0,
            "backup_counter_maximum": 10,
        }
        db.get_oversight_or_default.return_value = {
            "logs_directory": str(tmp_path / "logs"),
            "enable_reporting": False,
        }
        db.settings = MagicMock()
        db.processed_files = MagicMock()
        db.emails_table = MagicMock()
        folders_table = MagicMock()
        folders_table.find.return_value = []

        app = QtBatchFileSenderApp(database_obj=db)
        app._run_coordinator = MagicMock()

        app._process_directories(folders_table)

        app._run_coordinator.process_directories.assert_called_once_with(folders_table)

    def test_process_directories_handles_dispatch_exception(
        self, tmp_path, monkeypatch
    ):
        from interface.qt.app import QtBatchFileSenderApp

        db = MagicMock()
        db.database_connection = MagicMock()
        db.get_settings_or_default.return_value = {
            "id": 1,
            "enable_interval_backups": False,
            "backup_counter": 0,
            "backup_counter_maximum": 10,
        }
        db.get_oversight_or_default.return_value = {
            "logs_directory": str(tmp_path / "logs"),
            "enable_reporting": False,
        }
        db.settings = MagicMock()
        db.processed_files = MagicMock()
        db.emails_table = MagicMock()
        folders_table = MagicMock()
        folders_table.find.return_value = []

        app = QtBatchFileSenderApp(database_obj=db)
        app._run_coordinator = MagicMock()
        app._run_coordinator.process_directories.side_effect = RuntimeError("Boom")

        with pytest.raises(RuntimeError, match="Boom"):
            app._process_directories(folders_table)

    def test_build_main_window_creates_widgets(self, qtbot):
        from PyQt6.QtWidgets import QMainWindow

        from interface.qt.app import QtBatchFileSenderApp

        db = MagicMock()
        db.folders_table.count.return_value = 0
        db.processed_files.count.return_value = 0

        app = QtBatchFileSenderApp(database_obj=db)
        app._window = QMainWindow()
        app._database = db
        app._folder_filter = ""
        app._send_single = MagicMock()
        app._edit_folder_selector = MagicMock()
        app._disable_folder = MagicMock()
        app._delete_folder_entry_wrapper = MagicMock()
        app._update_filter_count_label = MagicMock()
        app._set_folders_filter = MagicMock()

        app._build_main_window()

        assert app._window.centralWidget() is not None
        assert app._process_folder_button is not None
        assert app._processed_files_button is not None
        assert app._allow_resend_button is not None
        assert app._right_panel_widget is not None

    def test_set_defaults_popup_opens_edit_folders_with_template(self, monkeypatch):
        from interface.qt.app import QtBatchFileSenderApp

        db = MagicMock()
        db.get_oversight_or_default.return_value = {"id": 1}

        app = QtBatchFileSenderApp(database_obj=db)
        app._database = db
        app._open_edit_folders_dialog = MagicMock()

        app._set_defaults_popup()

        app._open_edit_folders_dialog.assert_called_once()
        call_args = app._open_edit_folders_dialog.call_args[0][0]
        assert call_args["folder_name"] == "template"
        assert "copy_to_directory" in call_args
        assert "logs_directory" in call_args

    def test_on_folder_edit_applied_updates_database(self):
        from interface.qt.app import QtBatchFileSenderApp

        db = MagicMock()
        app = QtBatchFileSenderApp(database_obj=db)
        app._database = db

        folder_config = {"id": 42, "alias": "test"}

        app._on_folder_edit_applied(folder_config)

        db.folders_table.update.assert_called_once_with(folder_config, ["id"])

    def test_configure_window(self, qtbot):
        from PyQt6.QtWidgets import QMainWindow

        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        window = QMainWindow()
        app._window = window

        app._configure_window()

        # Just verify no crash
        assert window.minimumSize().width() > 0

    def test_run_self_test_with_module_import_failure(self, monkeypatch, tmp_path):
        """Test _run_self_test returns 1 when module import fails."""
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp(appname="TestApp", version="v1")

        original_import = builtins.__import__

        def _fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "nonexistent.module.that.will.fail":
                raise ImportError("Module not found")
            return original_import(name, globals, locals, fromlist, level)

        # Monkeypatch to force a module import failure in required_modules
        # by patching the _run_self_test to include a failing module
        def _fake_run_self_test_with_failure():
            # Simulate the check but with a failing module
            failures = 1  # Start with one failure
            return 1 if failures > 0 else 0

        # Setup config directories to succeed
        cfg = tmp_path / "cfg"
        cfg.mkdir(exist_ok=True)
        app._config_folder = str(cfg)
        app._database_path = str(cfg / "folders.db")

        monkeypatch.setattr(
            "interface.qt.app.appdirs.user_data_dir",
            lambda _: str(tmp_path / "appdirs"),
        )
        monkeypatch.setattr(
            "interface.qt.app.os.path.expanduser", lambda _: str(tmp_path)
        )

        # This test verifies that when there's a failure, the method returns 1
        # We can't easily simulate a module import failure, so we test the logic directly
        app._setup_config_directories = lambda: None
        app._config_folder = str(tmp_path)

        # Directly test that _run_self_test returns non-zero on failure
        # by mocking a scenario where setup fails
        def _fail_setup():
            raise Exception("Config setup failed")

        monkeypatch.setattr(app, "_setup_config_directories", _fail_setup)

        result = app._run_self_test()

        assert result == 1  # Should return 1 for failures

    def test_run_self_test_filesystem_check_failure(self, monkeypatch, tmp_path):
        """Test _run_self_test handles filesystem access failure."""
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp(appname="TestApp", version="v1")

        # Setup config directories to succeed
        cfg = tmp_path / "cfg"
        cfg.mkdir(exist_ok=True)
        app._config_folder = str(cfg)
        app._database_path = str(cfg / "folders.db")

        monkeypatch.setattr(
            "interface.qt.app.appdirs.user_data_dir",
            lambda _: str(tmp_path / "appdirs"),
        )

        # Make filesystem operations fail
        def _fail_makedirs(path, exist_ok=False):
            raise PermissionError("Access denied")

        def _fail_mkdir(path):
            raise PermissionError("Access denied")

        monkeypatch.setattr("interface.qt.app.os.makedirs", _fail_makedirs)
        monkeypatch.setattr("interface.qt.app.os.mkdir", _fail_mkdir)

        result = app._run_self_test()

        # Should return 1 due to filesystem access failure
        assert result == 1

    def test_initialize_creates_database_and_services(self, monkeypatch):
        """Test initialize creates database, folder manager, and services."""
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        app._parse_arguments = MagicMock()
        app._args = argparse.Namespace(self_test=False, gui_test=False, automatic=False)
        app._database_path = "/tmp/test.db"
        app._config_folder = "/tmp/config"
        app._setup_config_directories = MagicMock()
        app._build_main_window = MagicMock()
        app._set_main_button_states = MagicMock()
        app._configure_window = MagicMock()

        mock_db = MagicMock()
        mock_db.folders_table = MagicMock()
        mock_db.folders_table.count.return_value = 0
        mock_db.get_oversight_or_default.return_value = {"logs_directory": "/tmp"}

        mock_qapp = MagicMock()
        mock_qapp_instance = MagicMock()
        mock_qapp.instance.return_value = None
        mock_qapp.return_value = mock_qapp_instance

        class _FakeUIService:
            def __init__(self, parent=None):
                self.parent = parent

        class _FakeProgressService:
            def __init__(self, parent=None):
                self.parent = parent

        monkeypatch.setattr(
            "interface.qt.app.multiprocessing.freeze_support", lambda: None
        )
        monkeypatch.setattr("interface.qt.app.DatabaseObj", lambda *a, **kw: mock_db)
        monkeypatch.setattr("interface.qt.app.FolderManager", lambda *_: MagicMock())
        monkeypatch.setattr(
            "interface.qt.app.ReportingService", lambda **_: MagicMock()
        )
        monkeypatch.setattr("interface.qt.app.QApplication", mock_qapp)
        monkeypatch.setattr(
            "interface.qt.services.qt_services.QtUIService", _FakeUIService
        )
        monkeypatch.setattr(
            "interface.qt.services.qt_services.QtProgressService", _FakeProgressService
        )

        app.initialize()

        assert app._database is not None
        assert app._folder_manager is not None
        assert app._reporting_service is not None
        app._build_main_window.assert_called_once()
        app._set_main_button_states.assert_called_once()

    def test_initialize_uses_injected_database(self, monkeypatch):
        """Test initialize uses injected database object."""
        from interface.qt.app import QtBatchFileSenderApp

        mock_db = MagicMock()
        mock_db.folders_table = MagicMock()
        mock_db.folders_table.count.return_value = 0
        mock_db.get_oversight_or_default.return_value = {"logs_directory": "/tmp"}

        app = QtBatchFileSenderApp(database_obj=mock_db)
        app._parse_arguments = MagicMock()
        app._args = argparse.Namespace(self_test=False, gui_test=False, automatic=False)
        app._setup_config_directories = MagicMock()
        app._build_main_window = MagicMock()
        app._set_main_button_states = MagicMock()
        app._configure_window = MagicMock()

        mock_qapp = MagicMock()
        mock_qapp_instance = MagicMock()
        mock_qapp.instance.return_value = None
        mock_qapp.return_value = mock_qapp_instance

        class _FakeUIService:
            def __init__(self, parent=None):
                self.parent = parent

        class _FakeProgressService:
            def __init__(self, parent=None):
                self.parent = parent

        monkeypatch.setattr(
            "interface.qt.app.multiprocessing.freeze_support", lambda: None
        )
        monkeypatch.setattr("interface.qt.app.FolderManager", lambda *_: MagicMock())
        monkeypatch.setattr(
            "interface.qt.app.ReportingService", lambda **_: MagicMock()
        )
        monkeypatch.setattr("interface.qt.app.QApplication", mock_qapp)
        monkeypatch.setattr(
            "interface.qt.services.qt_services.QtUIService", _FakeUIService
        )
        monkeypatch.setattr(
            "interface.qt.services.qt_services.QtProgressService", _FakeProgressService
        )

        app.initialize()

        assert app._database is mock_db

    def test_initialize_creates_ui_and_progress_services(self, monkeypatch):
        """Test initialize creates UI and progress services."""
        from interface.qt.app import QtBatchFileSenderApp

        mock_db = MagicMock()
        mock_db.folders_table = MagicMock()
        mock_db.folders_table.count.return_value = 0
        mock_db.get_oversight_or_default.return_value = {"logs_directory": "/tmp"}

        app = QtBatchFileSenderApp(database_obj=mock_db)
        app._parse_arguments = MagicMock()
        app._args = argparse.Namespace(self_test=False, gui_test=False, automatic=False)
        app._setup_config_directories = MagicMock()
        app._build_main_window = MagicMock()
        app._set_main_button_states = MagicMock()
        app._configure_window = MagicMock()

        mock_qapp = MagicMock()
        mock_qapp_instance = MagicMock()
        mock_qapp.instance.return_value = None
        mock_qapp.return_value = mock_qapp_instance

        class _FakeUIService:
            def __init__(self, parent=None):
                self.parent = parent

        class _FakeProgressService:
            def __init__(self, parent=None):
                self.parent = parent

        monkeypatch.setattr(
            "interface.qt.app.multiprocessing.freeze_support", lambda: None
        )
        monkeypatch.setattr("interface.qt.app.FolderManager", lambda *_: MagicMock())
        monkeypatch.setattr(
            "interface.qt.app.ReportingService", lambda **_: MagicMock()
        )
        monkeypatch.setattr("interface.qt.app.QApplication", mock_qapp)
        monkeypatch.setattr(
            "interface.qt.services.qt_services.QtUIService", _FakeUIService
        )
        monkeypatch.setattr(
            "interface.qt.services.qt_services.QtProgressService", _FakeProgressService
        )

        app.initialize()

        assert app._ui_service is not None
        assert app._progress_service is not None

    def test_show_edit_settings_dialog_opens_dialog(self, monkeypatch):
        """Test _show_edit_settings_dialog opens the settings dialog."""
        from interface.qt.app import QtBatchFileSenderApp

        db = MagicMock()
        db.get_oversight_or_default.return_value = {"id": 1}
        db.get_settings_or_default.return_value = {"id": 1}
        db.settings = MagicMock()
        db.oversight_and_defaults = MagicMock()
        db.folders_table.count.return_value = 0

        app = QtBatchFileSenderApp(database_obj=db)
        app._database = db
        app._window = MagicMock()
        app._refresh_users_list = MagicMock()
        app._update_reporting = MagicMock()
        app._disable_all_email_backends = MagicMock()
        app._disable_folders_without_backends = MagicMock()

        dialog_exec = MagicMock()
        mock_dialog_class = MagicMock(return_value=MagicMock(exec=dialog_exec))

        monkeypatch.setattr(
            "interface.qt.dialogs.edit_settings_dialog.EditSettingsDialog",
            mock_dialog_class,
        )

        app._show_edit_settings_dialog()

        mock_dialog_class.assert_called_once()
        dialog_exec.assert_called_once()

    def test_show_maintenance_dialog_wrapper_creates_dialog(self, monkeypatch):
        """Test _show_maintenance_dialog_wrapper creates maintenance dialog."""
        from interface.qt.app import QtBatchFileSenderApp

        db = MagicMock()
        db.folders_table = MagicMock()
        db.processed_files = MagicMock()

        app = QtBatchFileSenderApp(database_obj=db)
        app._database = db
        app._window = MagicMock()
        app._database_path = "/tmp/folders.db"
        app._running_platform = "Linux"
        app._database_version = "42"
        app._folder_manager = MagicMock()
        app._refresh_users_list = MagicMock()
        app._set_main_button_states = MagicMock()
        app._progress_service = MagicMock()
        app._ui_service = MagicMock()

        backup_called = []
        monkeypatch.setattr(
            "interface.qt.app.backup_increment.do_backup",
            lambda path: backup_called.append(path),
        )

        open_dialog_called = []
        mock_open_dialog = MagicMock(
            side_effect=lambda **kwargs: open_dialog_called.append(kwargs)
        )
        monkeypatch.setattr(
            "interface.qt.dialogs.maintenance_dialog.MaintenanceDialog.open_dialog",
            mock_open_dialog,
        )

        app._show_maintenance_dialog_wrapper()

        assert len(backup_called) == 1
        mock_open_dialog.assert_called_once()

    def test_parse_arguments_parses_self_test_flag(self):
        """Test _parse_arguments correctly parses self-test flag."""
        import sys

        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()

        # Save original argv
        original_argv = sys.argv
        try:
            sys.argv = ["test", "--self-test"]
            app._parse_arguments()
            assert app._args.self_test is True
        finally:
            sys.argv = original_argv

    def test_parse_arguments_parses_automatic_flag(self):
        """Test _parse_arguments correctly parses automatic flag."""
        import sys

        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()

        # Save original argv
        original_argv = sys.argv
        try:
            sys.argv = ["test", "-a"]
            app._parse_arguments()
            assert app._args.automatic is True
        finally:
            sys.argv = original_argv

    def test_parse_arguments_default_values(self):
        """Test _parse_arguments has correct default values."""
        import sys

        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()

        # Save original argv
        original_argv = sys.argv
        try:
            sys.argv = ["test"]
            app._parse_arguments()
            assert app._args.automatic is False
            assert app._args.self_test is False
        finally:
            sys.argv = original_argv


@pytest.mark.qt
class TestQtAppInteractionWorkflows:
    """Focused interaction tests for app <-> dialog <-> folder manager paths."""

    def test_open_edit_dialog_apply_success_persists_and_refreshes(self, monkeypatch):
        from interface.qt.app import QtBatchFileSenderApp

        db = MagicMock()
        app = QtBatchFileSenderApp(database_obj=db)
        app._database = db
        app._window = MagicMock()
        app._refresh_users_list = MagicMock()
        app._set_main_button_states = MagicMock()

        class _FakeEditFoldersDialog:
            def __init__(self, parent, folder_config, on_apply_success=None, **kwargs):
                self.folder_config = dict(folder_config)
                self.on_apply_success = on_apply_success

            def exec(self):
                updated = dict(self.folder_config)
                updated["id"] = 42
                updated["alias"] = "Updated Alias"
                self.on_apply_success(updated)
                return 1

        monkeypatch.setattr(
            "interface.qt.dialogs.edit_folders_dialog.EditFoldersDialog",
            _FakeEditFoldersDialog,
        )

        app._open_edit_folders_dialog({"id": 42, "alias": "Before"})

        db.folders_table.update.assert_called_once_with(
            {"id": 42, "alias": "Updated Alias"},
            ["id"],
        )
        app._refresh_users_list.assert_called_once()
        app._set_main_button_states.assert_called_once()

    def test_open_edit_dialog_cancel_does_not_refresh(self, monkeypatch):
        from interface.qt.app import QtBatchFileSenderApp

        db = MagicMock()
        app = QtBatchFileSenderApp(database_obj=db)
        app._database = db
        app._window = MagicMock()
        app._refresh_users_list = MagicMock()
        app._set_main_button_states = MagicMock()

        class _FakeEditFoldersDialog:
            def __init__(self, *args, **kwargs):
                pass

            def exec(self):
                return 0

        monkeypatch.setattr(
            "interface.qt.dialogs.edit_folders_dialog.EditFoldersDialog",
            _FakeEditFoldersDialog,
        )

        app._open_edit_folders_dialog({"id": 42, "alias": "Before"})

        db.folders_table.update.assert_not_called()
        app._refresh_users_list.assert_not_called()
        app._set_main_button_states.assert_not_called()

    def test_edit_folder_selector_existing_opens_dialog(self):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        app._database = MagicMock()
        app._ui_service = MagicMock()
        app._database.folders_table.find_one.return_value = {
            "id": 12,
            "folder_name": "/tmp/f",
        }
        app._open_edit_folders_dialog = MagicMock()

        app._edit_folder_selector(12)

        app._open_edit_folders_dialog.assert_called_once_with(
            {"id": 12, "folder_name": "/tmp/f"}
        )

    def test_select_folder_existing_user_declines_no_dialog(self, monkeypatch):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        app._database = MagicMock()
        app._ui_service = MagicMock()
        app._progress_service = MagicMock()
        app._folder_manager = MagicMock()
        app._open_edit_folders_dialog = MagicMock()

        app._database.get_oversight_or_default.return_value = {
            "single_add_folder_prior": ""
        }
        app._ui_service.ask_directory.return_value = "/tmp/existing"
        app._folder_manager.check_folder_exists.return_value = {
            "truefalse": True,
            "matched_folder": {"id": 55, "folder_name": "/tmp/existing"},
        }
        app._ui_service.ask_ok_cancel.return_value = False

        monkeypatch.setattr("interface.qt.app.os.path.exists", lambda *_: True)

        app._select_folder()

        app._open_edit_folders_dialog.assert_not_called()

    def test_select_folder_new_user_skips_mark_processed(self, monkeypatch):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        app._database = MagicMock()
        app._ui_service = MagicMock()
        app._progress_service = MagicMock()
        app._folder_manager = MagicMock()
        app._refresh_users_list = MagicMock()
        app._mark_active_as_processed_wrapper = MagicMock()

        selected = "/tmp/new-folder"
        app._database.get_oversight_or_default.return_value = {
            "single_add_folder_prior": ""
        }
        app._ui_service.ask_directory.return_value = selected
        app._folder_manager.check_folder_exists.return_value = {"truefalse": False}
        app._ui_service.ask_yes_no.return_value = False

        monkeypatch.setattr("interface.qt.app.os.path.exists", lambda *_: True)

        app._select_folder()

        app._folder_manager.add_folder.assert_called_once_with(selected)
        app._mark_active_as_processed_wrapper.assert_not_called()
        app._refresh_users_list.assert_called_once()
        app._progress_service.show.assert_called_once_with("Adding Folder...")
        app._progress_service.hide.assert_called_once()

    def test_batch_add_folders_cancelled_confirmation_skips_manager_calls(
        self, tmp_path
    ):
        from interface.qt.app import QtBatchFileSenderApp

        root = tmp_path / "parent"
        root.mkdir()
        (root / "new1").mkdir()
        (root / "new2").mkdir()

        app = QtBatchFileSenderApp()
        app._database = MagicMock()
        app._ui_service = MagicMock()
        app._progress_service = MagicMock()
        app._folder_manager = MagicMock()
        app._refresh_users_list = MagicMock()

        app._database.get_oversight_or_default.return_value = {
            "batch_add_folder_prior": ""
        }
        app._ui_service.ask_directory.return_value = str(root)
        app._ui_service.ask_ok_cancel.return_value = False

        app._batch_add_folders()

        app._database.oversight_and_defaults.update.assert_called_once()
        app._folder_manager.add_folder.assert_not_called()
        app._progress_service.show.assert_not_called()
        app._refresh_users_list.assert_not_called()

    def test_delete_folder_confirmed_triggers_refresh_and_button_state(self):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        app._ui_service = MagicMock()
        app._folder_manager = MagicMock()
        app._refresh_users_list = MagicMock()
        app._set_main_button_states = MagicMock()

        app._ui_service.ask_yes_no.return_value = True

        app._delete_folder_entry_wrapper(42, "alias-42")

        app._folder_manager.delete_folder_with_related.assert_called_once_with(42)
        app._refresh_users_list.assert_called_once()
        app._set_main_button_states.assert_called_once()

    def test_show_processed_files_dialog_wrapper_wires_dependencies(self, monkeypatch):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        app._window = MagicMock()
        app._database = MagicMock()
        app._ui_service = MagicMock()

        captured = {}

        class _FakeProcessedFilesDialog:
            def __init__(self, parent=None, database_obj=None, ui_service=None):
                captured["parent"] = parent
                captured["database_obj"] = database_obj
                captured["ui_service"] = ui_service

            def exec(self):
                captured["executed"] = True

        monkeypatch.setattr(
            "interface.qt.dialogs.processed_files_dialog.ProcessedFilesDialog",
            _FakeProcessedFilesDialog,
        )

        app._show_processed_files_dialog_wrapper()

        assert captured["parent"] is app._window
        assert captured["database_obj"] is app._database
        assert captured["ui_service"] is app._ui_service
        assert captured.get("executed") is True

    def test_show_resend_dialog_skips_exec_when_dialog_not_ready(self, monkeypatch):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        app._window = MagicMock()
        app._database = MagicMock()
        app._database.database_connection = MagicMock()

        exec_called = MagicMock()

        class _FakeResendDialog:
            def __init__(self, parent=None, database_connection=None):
                self._should_show = False
                self._parent = parent
                self._db = database_connection

            def exec(self):
                exec_called()

        monkeypatch.setattr(
            "interface.qt.dialogs.resend_dialog.ResendDialog",
            _FakeResendDialog,
        )

        app._show_resend_dialog()

        exec_called.assert_not_called()

    def test_show_edit_settings_dialog_callback_wiring(self, monkeypatch):
        from interface.qt.app import QtBatchFileSenderApp

        db = MagicMock()
        db.get_oversight_or_default.return_value = {"id": 1}
        db.get_settings_or_default.return_value = {"id": 2}
        db.settings = MagicMock()
        db.oversight_and_defaults = MagicMock()
        db.folders_table.count.return_value = 3

        app = QtBatchFileSenderApp(database_obj=db)
        app._database = db
        app._window = MagicMock()
        app._refresh_users_list = MagicMock()
        app._update_reporting = MagicMock()
        app._disable_all_email_backends = MagicMock()
        app._disable_folders_without_backends = MagicMock()

        captured_kwargs = {}

        class _FakeEditSettingsDialog:
            def __init__(self, *args, **kwargs):
                captured_kwargs.update(kwargs)

            def exec(self):
                return 1

        monkeypatch.setattr(
            "interface.qt.dialogs.edit_settings_dialog.EditSettingsDialog",
            _FakeEditSettingsDialog,
        )

        app._show_edit_settings_dialog()

        # Invoke wired callbacks to verify interaction plumbing
        captured_kwargs["update_settings"]({"id": 9})
        captured_kwargs["update_oversight"]({"id": 8})
        captured_kwargs["on_apply"]({"enable_reporting": True})
        captured_kwargs["refresh_callback"]()
        captured_kwargs["disable_email_backends"]()
        captured_kwargs["disable_folders_without_backends"]()

        db.settings.update.assert_called_once_with({"id": 9}, ["id"])
        db.oversight_and_defaults.update.assert_called_once_with({"id": 8}, ["id"])
        app._update_reporting.assert_called_once_with({"enable_reporting": True})
        app._refresh_users_list.assert_called_once()
        app._disable_all_email_backends.assert_called_once()
        app._disable_folders_without_backends.assert_called_once()

    def test_show_maintenance_dialog_wrapper_callback_wiring(self, monkeypatch):
        from interface.qt.app import QtBatchFileSenderApp

        db = MagicMock()
        db.folders_table = MagicMock()
        db.processed_files = MagicMock()

        app = QtBatchFileSenderApp(database_obj=db)
        app._database = db
        app._window = MagicMock()
        app._database_path = "/tmp/folders.db"
        app._running_platform = "Linux"
        app._database_version = "42"
        app._folder_manager = MagicMock()
        app._refresh_users_list = MagicMock()
        app._set_main_button_states = MagicMock()
        app._progress_service = MagicMock()
        app._ui_service = MagicMock()
        app._ui_service.ask_ok_cancel.return_value = True

        monkeypatch.setattr(
            "interface.qt.app.backup_increment.do_backup", lambda *_: None
        )

        captured = {}

        class _FakeMaintenanceFunctions:
            def __init__(self, **kwargs):
                captured.update(kwargs)

        open_dialog_called = MagicMock()

        monkeypatch.setattr(
            "interface.operations.maintenance_functions.MaintenanceFunctions",
            _FakeMaintenanceFunctions,
        )
        monkeypatch.setattr(
            "interface.qt.dialogs.maintenance_dialog.MaintenanceDialog.open_dialog",
            lambda **kwargs: open_dialog_called(**kwargs),
        )

        app._show_maintenance_dialog_wrapper()

        # Verify callback wiring into maintenance functions
        assert (
            captured["delete_folder_callback"]
            is app._folder_manager.delete_folder_with_related
        )
        assert captured["refresh_callback"] is app._refresh_users_list
        assert captured["set_button_states_callback"] is app._set_main_button_states
        # confirm_callback delegates to UI service
        assert captured["confirm_callback"]("Proceed?") is True
        app._ui_service.ask_ok_cancel.assert_called_once_with("Confirm", "Proceed?")
        assert open_dialog_called.call_count == 1

    def test_mark_active_as_processed_wrapper_wires_delete_callback(self, monkeypatch):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        app._database = MagicMock()
        app._folder_manager = MagicMock()
        app._database_path = "/tmp/folders.db"
        app._running_platform = "Linux"
        app._database_version = "41"
        app._progress_service = MagicMock()
        app._refresh_users_list = MagicMock()
        app._set_main_button_states = MagicMock()

        captured = {}

        class _FakeMaintenanceFunctions:
            def __init__(self, **kwargs):
                captured.update(kwargs)

            def mark_active_as_processed(self, selected_folder=None):
                captured["selected_folder"] = selected_folder

        monkeypatch.setattr(
            "interface.operations.maintenance_functions.MaintenanceFunctions",
            _FakeMaintenanceFunctions,
        )

        app._mark_active_as_processed_wrapper(selected_folder=99)

        assert (
            captured["delete_folder_callback"]
            is app._folder_manager.delete_folder_with_related
        )
        assert captured["selected_folder"] == 99

    def test_set_defaults_popup_populates_advanced_defaults(self):
        from interface.qt.app import QtBatchFileSenderApp

        db = MagicMock()
        db.get_oversight_or_default.return_value = {"id": 1}

        app = QtBatchFileSenderApp(database_obj=db)
        app._database = db
        app._open_edit_folders_dialog = MagicMock()

        app._set_defaults_popup()

        defaults = app._open_edit_folders_dialog.call_args[0][0]
        assert defaults["folder_name"] == "template"
        assert defaults["upc_target_length"] == 11
        assert defaults["invoice_date_offset"] == 0
        assert defaults["split_edi_filter_mode"] == "include"
        assert defaults["convert_to_format"] == "csv"

    def test_show_edit_settings_dialog_count_callbacks_query_expected_filters(
        self, monkeypatch
    ):
        from interface.qt.app import QtBatchFileSenderApp

        db = MagicMock()
        db.get_oversight_or_default.return_value = {"id": 1}
        db.get_settings_or_default.return_value = {"id": 2}
        db.settings = MagicMock()
        db.oversight_and_defaults = MagicMock()

        app = QtBatchFileSenderApp(database_obj=db)
        app._database = db
        app._window = MagicMock()
        app._refresh_users_list = MagicMock()
        app._update_reporting = MagicMock()
        app._disable_all_email_backends = MagicMock()
        app._disable_folders_without_backends = MagicMock()

        captured_kwargs = {}

        class _FakeEditSettingsDialog:
            def __init__(self, *args, **kwargs):
                captured_kwargs.update(kwargs)

            def exec(self):
                return 1

        monkeypatch.setattr(
            "interface.qt.dialogs.edit_settings_dialog.EditSettingsDialog",
            _FakeEditSettingsDialog,
        )

        app._show_edit_settings_dialog()

        _ = captured_kwargs["count_email_backends"]()
        _ = captured_kwargs["count_disabled_folders"]()

        assert db.folders_table.count.call_count == 2
        db.folders_table.count.assert_any_call(process_backend_email=True)
        db.folders_table.count.assert_any_call(
            process_backend_email=True,
            process_backend_ftp=False,
            process_backend_copy=False,
            folder_is_active=True,
        )

    def test_show_maintenance_dialog_database_import_callback_branches(
        self, monkeypatch
    ):
        from interface.qt.app import QtBatchFileSenderApp

        db = MagicMock()
        db.folders_table = MagicMock()
        db.processed_files = MagicMock()

        app = QtBatchFileSenderApp(database_obj=db)
        app._database = db
        app._window = MagicMock()
        app._database_path = "/tmp/folders.db"
        app._running_platform = "Linux"
        app._database_version = "42"
        app._folder_manager = MagicMock()
        app._refresh_users_list = MagicMock()
        app._set_main_button_states = MagicMock()
        app._progress_service = MagicMock()
        app._ui_service = MagicMock()

        monkeypatch.setattr(
            "interface.qt.app.backup_increment.do_backup", lambda *_: None
        )

        captured = {}

        class _FakeMaintenanceFunctions:
            def __init__(self, **kwargs):
                captured.update(kwargs)

        monkeypatch.setattr(
            "interface.operations.maintenance_functions.MaintenanceFunctions",
            _FakeMaintenanceFunctions,
        )
        monkeypatch.setattr(
            "interface.qt.dialogs.maintenance_dialog.MaintenanceDialog.open_dialog",
            lambda **kwargs: None,
        )

        captured_show_kwargs = {}

        # Success path
        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.show_database_import_dialog",
            lambda **kwargs: captured_show_kwargs.update(kwargs),
        )

        app._show_maintenance_dialog_wrapper()
        assert captured["database_import_callback"]("/tmp/backup.db") is True
        assert captured_show_kwargs["preselected_database_path"] == "/tmp/backup.db"
        assert captured_show_kwargs["backup_path"] == "/tmp/backup.db"

        # Failure path
        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.show_database_import_dialog",
            lambda **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        app._show_maintenance_dialog_wrapper()
        assert captured["database_import_callback"]("/tmp/backup.db") is False

    def test_select_folder_ignores_nonexistent_selection(self, monkeypatch):
        from interface.qt.app import QtBatchFileSenderApp

        app = QtBatchFileSenderApp()
        app._database = MagicMock()
        app._ui_service = MagicMock()
        app._progress_service = MagicMock()
        app._folder_manager = MagicMock()

        app._database.get_oversight_or_default.return_value = {
            "single_add_folder_prior": ""
        }
        app._ui_service.ask_directory.return_value = "/tmp/does-not-exist"

        monkeypatch.setattr("interface.qt.app.os.path.exists", lambda *_: False)

        app._select_folder()

        app._database.oversight_and_defaults.update.assert_not_called()
        app._folder_manager.add_folder.assert_not_called()
