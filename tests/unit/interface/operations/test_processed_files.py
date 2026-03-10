"""Focused tests for processed files report export behavior."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from interface.operations.processed_files import export_processed_report


@dataclass
class _FoldersTable:
    folder: dict[str, Any] | None

    def find_one(self, **kwargs):
        _ = kwargs
        return self.folder


@dataclass
class _ProcessedFilesTable:
    rows: list[dict[str, Any]]

    def find(self, **kwargs):
        _ = kwargs
        return list(self.rows)


@dataclass
class _Database:
    folders_table: _FoldersTable
    processed_files: _ProcessedFilesTable


def test_export_processed_report_raises_value_error_when_folder_missing(tmp_path: Path):
    db = _Database(folders_table=_FoldersTable(folder=None), processed_files=_ProcessedFilesTable(rows=[]))

    with pytest.raises(ValueError, match="Folder with id 99 not found"):
        export_processed_report(folder_id=99, output_folder=str(tmp_path), database_obj=db)


def test_export_processed_report_writes_header_and_formatted_row(tmp_path: Path):
    db = _Database(
        folders_table=_FoldersTable(folder={"id": 1, "alias": "Invoices"}),
        processed_files=_ProcessedFilesTable(
            rows=[
                {
                    "file_name": "invoice-001.pdf",
                    "sent_date_time": datetime(2026, 3, 10, 12, 34, 56),
                    "copy_destination": "Archive",
                    "ftp_destination": "ftp://example",
                    "email_destination": "ops@example.com",
                }
            ]
        ),
    )

    export_processed_report(folder_id=1, output_folder=str(tmp_path), database_obj=db)

    report_path = tmp_path / "Invoices processed report.csv"
    assert report_path.exists()
    lines = report_path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "File,Date,Copy Destination,FTP Destination,Email Destination"
    assert (
        lines[1]
        == "invoice-001.pdf,2026-03-10 12:34:56,Archive,ftp://example,ops@example.com"
    )


def test_export_processed_report_writes_header_only_when_no_rows(tmp_path: Path):
    db = _Database(
        folders_table=_FoldersTable(folder={"id": 2, "alias": "Empty"}),
        processed_files=_ProcessedFilesTable(rows=[]),
    )

    export_processed_report(folder_id=2, output_folder=str(tmp_path), database_obj=db)

    report_path = tmp_path / "Empty processed report.csv"
    assert report_path.exists()
    assert (
        report_path.read_text(encoding="utf-8")
        == "File,Date,Copy Destination,FTP Destination,Email Destination\n"
    )


def test_export_processed_report_uses_incrementing_suffix_on_name_collision(tmp_path: Path):
    db = _Database(
        folders_table=_FoldersTable(folder={"id": 3, "alias": "Archive"}),
        processed_files=_ProcessedFilesTable(rows=[]),
    )

    base = tmp_path / "Archive processed report.csv"
    first_collision = tmp_path / "Archive processed report (1).csv"
    base.write_text("existing", encoding="utf-8")
    first_collision.write_text("existing-1", encoding="utf-8")

    export_processed_report(folder_id=3, output_folder=str(tmp_path), database_obj=db)

    second_collision = tmp_path / "Archive processed report (2).csv"
    assert second_collision.exists()
    assert base.read_text(encoding="utf-8") == "existing"
    assert first_collision.read_text(encoding="utf-8") == "existing-1"
