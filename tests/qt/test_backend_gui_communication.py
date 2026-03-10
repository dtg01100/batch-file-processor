"""Focused tests for backend <-> GUI communication boundaries in Qt app.

These tests target concrete communication points where GUI actions trigger
backend behavior (and vice versa), rather than only asserting method
existence.
"""

from __future__ import annotations

import argparse
from unittest.mock import MagicMock

import pytest

from interface.qt.app import QtBatchFileSenderApp


pytestmark = [pytest.mark.qt, pytest.mark.gui]


class TestToggleFolderCommunication:
    """Verify folder-toggle communication from GUI controls to backend manager."""

    def _make_app(self) -> QtBatchFileSenderApp:
        app = QtBatchFileSenderApp()
        app._folder_manager = MagicMock()
        app._ui_service = MagicMock()
        app._refresh_users_list = MagicMock()
        app._set_main_button_states = MagicMock()
        return app

    def test_toggle_active_folder_disables_it(self) -> None:
        app = self._make_app()
        app._folder_manager.get_folder_by_id.return_value = {
            "id": 10,
            "alias": "Folder A",
            "folder_is_active": "True",
            "process_backend_email": False,
            "process_backend_ftp": False,
            "process_backend_copy": False,
        }

        app._toggle_folder(10)

        app._folder_manager.disable_folder.assert_called_once_with(10)
        app._folder_manager.enable_folder.assert_not_called()
        app._refresh_users_list.assert_called_once()
        app._set_main_button_states.assert_called_once()

    def test_toggle_inactive_folder_without_backends_shows_error(self) -> None:
        app = self._make_app()
        app._folder_manager.get_folder_by_id.return_value = {
            "id": 11,
            "alias": "Folder B",
            "folder_is_active": "False",
            "process_backend_email": False,
            "process_backend_ftp": False,
            "process_backend_copy": False,
        }

        app._toggle_folder(11)

        app._ui_service.show_error.assert_called_once()
        app._folder_manager.enable_folder.assert_not_called()
        app._refresh_users_list.assert_not_called()
        app._set_main_button_states.assert_not_called()

    def test_toggle_inactive_folder_with_backend_enables_it(self) -> None:
        app = self._make_app()
        app._folder_manager.get_folder_by_id.return_value = {
            "id": 12,
            "alias": "Folder C",
            "folder_is_active": "False",
            "process_backend_email": True,
            "process_backend_ftp": False,
            "process_backend_copy": False,
        }

        app._toggle_folder(12)

        app._folder_manager.enable_folder.assert_called_once_with(12)
        app._refresh_users_list.assert_called_once()
        app._set_main_button_states.assert_called_once()


class TestRunTimerCommunication:
    """Verify graphical automatic mode wiring between GUI and processing call."""

    def test_run_graphical_automatic_schedules_and_triggers_processing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        app = QtBatchFileSenderApp()
        app._window = MagicMock()
        app._database = MagicMock()
        app._database.folders_table = object()
        app._graphical_process_directories = MagicMock()
        app._args = argparse.Namespace(automatic=False, graphical_automatic=True)

        scheduled = {"delay": None}

        def fake_single_shot(delay, callback):
            scheduled["delay"] = delay
            callback()

        exec_called = []

        monkeypatch.setattr("interface.qt.app.QTimer.singleShot", fake_single_shot)
        monkeypatch.setattr(
            "interface.qt.app.QApplication.exec", lambda: exec_called.append(True)
        )

        app.run()

        assert scheduled["delay"] == 500
        app._window.show.assert_called_once()
        app._graphical_process_directories.assert_called_once_with(
            app._database.folders_table
        )
        assert exec_called == [True]


class TestProcessingCallbackCommunication:
    """Verify processing callback plumbing between GUI and backend dispatch/reporting."""

    def test_process_directories_passes_progress_callback_to_dispatch_and_reporting(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        db = MagicMock()
        db.database_connection = MagicMock()
        db.get_settings_or_default.return_value = {
            "id": 1,
            "enable_interval_backups": False,
            "backup_counter": 0,
            "backup_counter_maximum": 100,
        }
        db.get_oversight_or_default.return_value = {
            "logs_directory": str(tmp_path / "logs"),
            "enable_reporting": True,
        }
        db.settings = MagicMock()
        db.emails_table = MagicMock()
        db.processed_files = MagicMock()

        app = QtBatchFileSenderApp(database_obj=db)
        app._database_path = str(tmp_path / "folders.db")
        app._logs_directory = {"logs_directory": str(tmp_path / "logs")}
        app._errors_directory = {"errors_directory": str(tmp_path / "errors")}
        app._version = "test-version"
        app._progress_service = MagicMock()
        app._reporting_service = MagicMock()
        app._args = argparse.Namespace(automatic=False)
        app._check_logs_directory = MagicMock(return_value=True)
        (tmp_path / "logs").mkdir(parents=True, exist_ok=True)

        folders_table = MagicMock()
        folders_table.find.return_value = []

        captured_dispatch_kwargs: dict = {}

        def fake_dispatch(*args, **kwargs):
            captured_dispatch_kwargs.update(kwargs)
            return False, "ok"

        monkeypatch.setattr("interface.qt.app.os.getcwd", lambda: str(tmp_path))
        monkeypatch.setattr("interface.qt.app.os.chdir", lambda _: None)
        monkeypatch.setattr("interface.qt.app.os.path.isdir", lambda _: True)
        monkeypatch.setattr("interface.qt.app.utils.do_clear_old_files", lambda *_: None)
        monkeypatch.setattr("dispatch.process", fake_dispatch)

        app._process_directories(folders_table)

        assert captured_dispatch_kwargs["progress_callback"] is app._progress_service

        app._reporting_service.send_report_emails.assert_called_once()
        reporting_kwargs = app._reporting_service.send_report_emails.call_args.kwargs
        assert reporting_kwargs["progress_callback"] is app._progress_service
