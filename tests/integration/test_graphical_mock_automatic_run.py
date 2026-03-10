"""Integration tests for graphical mocked automatic run harness."""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from scripts.graphical_mock_automatic_run import (
    _mock_dispatch_process,
    run_graphical_mock_automatic,
)


pytestmark = [pytest.mark.integration, pytest.mark.workflow, pytest.mark.qt, pytest.mark.gui]


def test_mock_dispatch_process_updates_progress_and_writes_log() -> None:
    run_log = MagicMock()
    progress = MagicMock()

    has_error, summary = _mock_dispatch_process(
        _database_connection=MagicMock(),
        _folders_table_process=MagicMock(),
        run_log=run_log,
        _emails_table=MagicMock(),
        _logs_directory="/tmp/logs",
        _reporting={},
        _processed_files=MagicMock(),
        version="v-test",
        _errors_directory={},
        _settings_dict={},
        progress_callback=progress,
    )

    assert has_error is False
    assert "Mock graphical dispatch completed successfully" in summary
    progress.show.assert_called_once()
    progress.update_progress.assert_called_once_with(100)
    progress.update_message.assert_called_once()
    progress.hide.assert_called_once()
    assert run_log.write.call_count >= 2


def test_run_graphical_mock_automatic_creates_expected_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_initialize(self, args=None):
        # Simulate initialization required for _graphical_process_directories path,
        # without creating a real GUI event loop.
        self._args = argparse.Namespace(automatic=False, graphical_automatic=True)
        self._progress_service = MagicMock()
        self._ui_service = MagicMock()
        self._reporting_service = MagicMock()
        self._logs_directory = self._database.get_oversight_or_default()
        self._errors_directory = self._logs_directory
        self._refresh_users_list = MagicMock()
        self._set_main_button_states = MagicMock()

    def fake_run(self):
        self._graphical_process_directories(self._database.folders_table)

    monkeypatch.setattr(
        "scripts.graphical_mock_automatic_run.QtBatchFileSenderApp.initialize",
        fake_initialize,
    )
    monkeypatch.setattr(
        "scripts.graphical_mock_automatic_run.QtBatchFileSenderApp.run",
        fake_run,
    )

    result = run_graphical_mock_automatic(tmp_path, keep_open=False)

    assert result.exit_code == 0
    assert result.config_dir.exists()
    assert result.database_path.exists()
    assert result.input_dir.exists()
    assert result.logs_dir.exists()
    assert len(result.run_log_files) >= 1

    run_log_text = result.run_log_files[0].read_text(encoding="utf-8")
    assert "[MOCK] graphical dispatch.process called" in run_log_text
