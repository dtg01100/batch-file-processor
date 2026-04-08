"""Unit tests for Qt run coordinator report handling."""

from __future__ import annotations

import argparse
import os
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from interface.qt.run_coordinator import QtRunCoordinator


class _FakeValidationStep:
    def __init__(self):
        self._log = "\r\nErrors for bad.edi:\r\nCritical validation error\r\n"

    def get_error_log(self) -> str:
        return self._log


class _FakeSplitterStep:
    pass


class _FakeConverterStep:
    pass


class _FakeOrchestrator:
    def __init__(self, config):
        self._config = config

    def discover_pending_files(self, folders, processed_files, progress_reporter=None):
        return ([[] for _ in folders], 0)

    def process_folder(
        self,
        folder,
        run_log,
        processed_files,
        pre_discovered_files=None,
        folder_num=None,
        folder_total=None,
    ):
        return SimpleNamespace(success=True)

    def get_summary(self) -> str:
        return "0 processed, 0 errors"


@pytest.mark.unit
def test_process_directories_writes_validation_report_when_enabled(
    tmp_path, monkeypatch
):
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    app = MagicMock()
    app._os_module = os
    app._database_path = str(tmp_path / "folders.db")
    app._version = "1.0"
    app._logs_directory = {"logs_directory": str(logs_dir)}
    app._args = argparse.Namespace(automatic=False)
    app._backup_increment_module = MagicMock()
    app._check_logs_directory = MagicMock(return_value=True)
    app._progress_service = MagicMock()
    app._ui_service = MagicMock()
    app._reporting_service = MagicMock()

    app._utils_module = SimpleNamespace(
        do_clear_old_files=lambda *_: None,
        normalize_bool=lambda v: (
            bool(v)
            if isinstance(v, bool)
            else str(v).strip().lower() in {"true", "1", "yes", "on"}
        ),
    )

    app._database = MagicMock()
    app._database.settings = MagicMock()
    app._database.processed_files = MagicMock()
    app._database.emails_table = MagicMock()
    app._database.get_settings_or_default.return_value = {
        "id": 1,
        "enable_interval_backups": False,
        "backup_counter": 0,
        "backup_counter_maximum": 10,
    }
    app._database.get_oversight_or_default.return_value = {
        "logs_directory": str(logs_dir),
        "enable_reporting": True,
        "report_edi_errors": True,
    }

    folders_table = MagicMock()
    folders_table.count.return_value = 1
    folders_table.find.return_value = [
        {"id": 1, "alias": "A", "folder_name": str(tmp_path)}
    ]

    monkeypatch.setattr("dispatch.DispatchOrchestrator", _FakeOrchestrator)
    monkeypatch.setattr(
        "dispatch.pipeline.validator.EDIValidationStep", _FakeValidationStep
    )
    monkeypatch.setattr("dispatch.pipeline.splitter.EDISplitterStep", _FakeSplitterStep)
    monkeypatch.setattr(
        "dispatch.pipeline.converter.EDIConverterStep", _FakeConverterStep
    )

    coordinator = QtRunCoordinator(app)
    coordinator.process_directories(folders_table)

    validator_logs = list(logs_dir.glob("Validator Log *.txt"))
    assert len(validator_logs) == 1

    validator_text = validator_logs[0].read_text(encoding="utf-8")
    assert "EDI Validation Report" in validator_text
    assert "Critical validation error" in validator_text

    inserted_logs = [
        c.args[0]["log"] for c in app._database.emails_table.insert.call_args_list
    ]
    assert any("Validator Log" in log_path for log_path in inserted_logs)
