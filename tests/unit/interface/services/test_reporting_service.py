"""Communication-focused tests for ReportingService.

These tests verify orchestration between ReportingService and its collaborators:
- database queue tables
- batch log sender module
- optional progress callback
- printing fallback module
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from interface.services.reporting_service import ReportingService


@dataclass
class InMemoryTable:
    rows: list[dict[str, Any]] = field(default_factory=list)

    def find_one(self, **kwargs):
        for row in self.rows:
            if all(row.get(k) == v for k, v in kwargs.items()):
                return dict(row)
        return None

    def find(self, **kwargs):
        return [
            dict(r) for r in self.rows if all(r.get(k) == v for k, v in kwargs.items())
        ]

    def all(self):
        return [dict(r) for r in self.rows]

    def insert(self, record: dict):
        self.rows.append(dict(record))
        return len(self.rows)

    def update(self, record: dict, keys: list):
        for i, row in enumerate(self.rows):
            if all(row.get(k) == record.get(k) for k in keys):
                self.rows[i] = dict(record)
                return

    def delete(self, **kwargs):
        if not kwargs:
            self.rows = []
            return
        self.rows = [
            r for r in self.rows if not all(r.get(k) == v for k, v in kwargs.items())
        ]

    def count(self, **kwargs):
        if not kwargs:
            return len(self.rows)
        return len(
            [r for r in self.rows if all(r.get(k) == v for k, v in kwargs.items())]
        )


class InMemoryReportingDB:
    def __init__(self):
        self.emails_table = InMemoryTable()
        self.emails_table_batch = InMemoryTable()
        self.sent_emails_removal_queue = InMemoryTable()


class TestReportingServiceCommunication:
    def test_add_run_log_to_queue_when_enabled(self):
        db = InMemoryReportingDB()
        service = ReportingService(database=db)

        service.add_run_log_to_queue(
            run_log_path="/tmp/run.log",
            run_log_name="Run Log A",
            enable_reporting=True,
        )

        assert db.emails_table.count() == 1
        assert db.emails_table.all()[0]["log"] == "/tmp/run.log"

    def test_add_run_log_to_queue_when_disabled(self):
        db = InMemoryReportingDB()
        service = ReportingService(database=db)

        service.add_run_log_to_queue(
            run_log_path="/tmp/run.log",
            run_log_name="Run Log A",
            enable_reporting=False,
        )

        assert db.emails_table.count() == 0

    def test_send_report_emails_wires_progress_and_batch_sender(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        db = InMemoryReportingDB()

        log_file = tmp_path / "Run Log Test.txt"
        log_file.write_text("hello", encoding="utf-8")
        db.emails_table.insert({"log": str(log_file), "folder_alias": "Run Log Test"})

        batch_calls = []

        class BatchSender:
            @staticmethod
            def do(
                settings_dict,
                reporting_config,
                emails_table_batch,
                sent_emails_removal_queue,
                start_time,
                batch_number,
                emails_count,
                total_emails,
                run_summary,
                progress_callback,
            ):
                batch_calls.append(
                    {
                        "batch_count": emails_table_batch.count(),
                        "total_emails": total_emails,
                        "run_summary": run_summary,
                        "progress_callback": progress_callback,
                    }
                )

        class Utils:
            @staticmethod
            def normalize_bool(value):
                return bool(value)

        progress = object()
        service = ReportingService(
            database=db,
            batch_log_sender_module=BatchSender,
            utils_module=Utils,
        )

        fixed_time = datetime(2026, 3, 10, 12, 0, 0)
        monkeypatch.setattr(
            "interface.services.reporting_service.datetime",
            type(
                "MockDatetime",
                (),
                {
                    "now": lambda: fixed_time,
                    "datetime": datetime,
                },
            )(),
        )

        service.send_report_emails(
            settings_dict={"smtp_server": "example"},
            reporting_config={"enable_reporting": True},
            run_log_path=str(tmp_path),
            start_time="2026-03-10 12:00:00",
            run_summary="Run OK",
            progress_callback=progress,
        )

        assert len(batch_calls) >= 1
        assert batch_calls[0]["batch_count"] >= 1
        assert batch_calls[0]["progress_callback"] is progress

    def test_send_report_emails_handles_missing_files_with_error_log(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        db = InMemoryReportingDB()
        missing = tmp_path / "missing.log"
        db.emails_table.insert({"log": str(missing), "folder_alias": "missing"})

        class BatchSender:
            calls = 0

            @staticmethod
            def do(*args, **kwargs):
                BatchSender.calls += 1

        class Utils:
            @staticmethod
            def normalize_bool(value):
                return bool(value)

        service = ReportingService(
            database=db,
            batch_log_sender_module=BatchSender,
            utils_module=Utils,
        )

        monkeypatch.setattr(
            "interface.services.reporting_service.datetime",
            type(
                "MockDatetime",
                (),
                {
                    "now": lambda: datetime(2026, 3, 10, 12, 0, 0),
                    "datetime": datetime,
                },
            )(),
        )

        service.send_report_emails(
            settings_dict={},
            reporting_config={"enable_reporting": True},
            run_log_path=str(tmp_path),
            start_time="2026-03-10 12:00:00",
            run_summary="Run summary",
            progress_callback=None,
        )

        assert BatchSender.calls >= 1
        error_logs = list(tmp_path.glob("Email Errors Log *.txt"))
        assert len(error_logs) == 1

    def test_missing_files_error_log_filename_sanitizes_colons(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        db = InMemoryReportingDB()
        db.emails_table.insert(
            {"log": str(tmp_path / "missing-a.log"), "folder_alias": "missing-a"}
        )

        class BatchSender:
            @staticmethod
            def do(*args, **kwargs):
                return None

        class Utils:
            @staticmethod
            def normalize_bool(value):
                return bool(value)

        service = ReportingService(
            database=db,
            batch_log_sender_module=BatchSender,
            utils_module=Utils,
        )

        fixed_time = datetime(2026, 3, 10, 12, 0, 0)
        mock_datetime_instance = type(
            "MockDatetime",
            (),
            {
                "now": staticmethod(lambda: fixed_time),
            },
        )()
        mock_datetime = type(
            "MockDatetimeModule",
            (),
            {
                "datetime": mock_datetime_instance,
            },
        )()
        monkeypatch.setattr(
            "interface.services.reporting_service.datetime",
            mock_datetime,
        )

        service.send_report_emails(
            settings_dict={},
            reporting_config={"enable_reporting": True},
            run_log_path=str(tmp_path),
            start_time="2026-03-10 12:00:00",
            run_summary="Run summary",
        )

        error_logs = list(tmp_path.glob("Email Errors Log *.txt"))
        assert len(error_logs) == 1
        assert ":" not in error_logs[0].name
        assert "12-00-00" in error_logs[0].name

    def test_missing_files_error_log_contains_missing_path_lines(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        db = InMemoryReportingDB()
        missing_path = tmp_path / "missing-b.log"
        db.emails_table.insert({"log": str(missing_path), "folder_alias": "missing-b"})

        class BatchSender:
            @staticmethod
            def do(*args, **kwargs):
                return None

        class Utils:
            @staticmethod
            def normalize_bool(value):
                return bool(value)

        service = ReportingService(
            database=db,
            batch_log_sender_module=BatchSender,
            utils_module=Utils,
        )

        fixed_time = datetime(2026, 3, 10, 12, 0, 0)
        mock_datetime_instance = type(
            "MockDatetime",
            (),
            {
                "now": staticmethod(lambda: fixed_time),
            },
        )()
        mock_datetime = type(
            "MockDatetimeModule",
            (),
            {
                "datetime": mock_datetime_instance,
            },
        )()
        monkeypatch.setattr(
            "interface.services.reporting_service.datetime",
            mock_datetime,
        )

        service.send_report_emails(
            settings_dict={},
            reporting_config={"enable_reporting": True},
            run_log_path=str(tmp_path),
            start_time="2026-03-10 12:00:00",
            run_summary="Run summary",
        )

        error_log = next(tmp_path.glob("Email Errors Log *.txt"))
        content = error_log.read_text(encoding="utf-8")
        assert f"{missing_path} missing, skipping" in content
        assert (
            f"file was expected to be at {missing_path} on the sending computer"
            in content
        )
