"""Integration tests for graphical mocked automatic run harness."""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from scripts.graphical_mock_automatic_run import (
    _mock_orchestrator_process_folder,
    run_graphical_mock_automatic,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.workflow,
    pytest.mark.qt,
    pytest.mark.gui,
]


def test_mock_orchestrator_process_folder_writes_log_and_returns_success() -> None:
    run_log = MagicMock()

    result = _mock_orchestrator_process_folder(
        MagicMock(),
        {"folder_name": "/tmp/in", "alias": "Mock Alias"},
        run_log,
        MagicMock(),
    )

    assert result.success is True
    assert result.files_processed == 1
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
    assert "[MOCK] graphical DispatchOrchestrator.process_folder called" in run_log_text
