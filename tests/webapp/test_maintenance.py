"""Tests for the webapp maintenance endpoints."""

from __future__ import annotations

import csv
import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from webapp.config import Settings
from webapp.database import open_database
from webapp.main import create_app
from webapp.maintenance import (
    clear_processed_files,
    export_processed_report,
    mark_file_processed,
)

pytestmark = [pytest.mark.integration]


@pytest.fixture
def client(tmp_path):
    settings = Settings(base_dir=tmp_path / "data", data_dir=tmp_path / "data" / "config")
    settings.ensure_dirs()
    db = open_database(settings)
    db.folders_table.insert(
        {
            "folder_name": "inbox/test",
            "folder_is_active": True,
            "alias": "TEST",
            "process_backend_copy": True,
            "copy_to_directory": "archive/test",
            "process_backend_ftp": False,
            "process_backend_email": False,
            "process_backend_http": False,
            "created_at": datetime.datetime.now().isoformat(),
        }
    )
    db.folders_table.insert(
        {
            "folder_name": "inbox/other",
            "folder_is_active": True,
            "alias": "OTHER",
            "process_backend_copy": True,
            "copy_to_directory": "archive/other",
            "process_backend_ftp": False,
            "process_backend_email": False,
            "process_backend_http": False,
            "created_at": datetime.datetime.now().isoformat(),
        }
    )
    # Seed three processed-files rows: two for folder 1, one for folder 2.
    mark_file_processed(
        db,
        file_path="/incoming/test/sample.001",
        folder_id=1,
        folder_alias="TEST",
        invoice_numbers="0001",
        status="processed",
        sent_to="Email: ops@example.com",
    )
    mark_file_processed(
        db,
        file_path="/incoming/test/sample.002",
        folder_id=1,
        folder_alias="TEST",
        invoice_numbers="0002",
        status="processed",
    )
    mark_file_processed(
        db,
        file_path="/incoming/other/other.001",
        folder_id=2,
        folder_alias="OTHER",
        invoice_numbers="0003",
        status="failed",
    )
    db.close()
    app = create_app(settings=settings)
    return TestClient(app), settings


# ---------------------------------------------------------------------------
# clear_processed_files (function-level)
# ---------------------------------------------------------------------------


def test_clear_processed_all_removes_every_row(client):
    _test_client, settings = client
    db = open_database(settings)
    try:
        assert len(list(db.processed_files.all())) == 3
        deleted = clear_processed_files(db)
        assert deleted == 3
        assert len(list(db.processed_files.all())) == 0
    finally:
        db.close()


def test_clear_processed_by_folder_keeps_other_rows(client):
    _test_client, settings = client
    db = open_database(settings)
    try:
        deleted = clear_processed_files(db, folder_id=1)
        assert deleted == 2
        remaining = list(db.processed_files.all())
        assert len(remaining) == 1
        assert remaining[0]["folder_id"] == 2
    finally:
        db.close()


# ---------------------------------------------------------------------------
# HTTP: POST /api/maintenance/clear-processed
# ---------------------------------------------------------------------------


def test_post_clear_processed_returns_count(client):
    test_client, settings = client
    r = test_client.post("/api/maintenance/clear-processed?folder_id=1")
    assert r.status_code == 200
    assert r.json() == {"deleted": 2}
    db = open_database(settings)
    try:
        rows = list(db.processed_files.all())
        assert len(rows) == 1  # only folder 2 remains
    finally:
        db.close()


def test_post_clear_processed_503_when_no_database(tmp_path):
    settings = Settings(base_dir=tmp_path / "data", data_dir=tmp_path / "data" / "config")
    settings.ensure_dirs()
    app = create_app(settings=settings)
    c = TestClient(app)
    r = c.post("/api/maintenance/clear-processed")
    assert r.status_code == 503


# ---------------------------------------------------------------------------
# HTTP: POST /api/maintenance/mark-processed
# ---------------------------------------------------------------------------


def test_post_mark_processed_inserts_a_row(client):
    test_client, settings = client
    r = test_client.post(
        "/api/maintenance/mark-processed",
        params={
            "folder_id": 1,
            "file_path": "/incoming/test/sample.003",
            "invoice_numbers": "0003",
            "sent_to": "FTP: ftp.example.com",
        },
    )
    assert r.status_code == 200
    assert r.json()["id"] > 0
    db = open_database(settings)
    try:
        rows = list(db.processed_files.find(folder_id=1))
        assert len(rows) == 3  # the two original plus the new one
    finally:
        db.close()


def test_post_mark_processed_404_when_folder_unknown(client):
    test_client, _ = client
    r = test_client.post(
        "/api/maintenance/mark-processed",
        params={"folder_id": 999, "file_path": "/x"},
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# HTTP: POST /api/maintenance/export-processed
# ---------------------------------------------------------------------------


def test_post_export_processed_writes_csv(client):
    test_client, _ = client
    r = test_client.post("/api/maintenance/export-processed?folder_id=1")
    assert r.status_code == 200
    path = r.json()["path"]
    assert Path(path).is_file()
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    # Header + two data rows for folder 1.
    assert rows[0] == ["File", "Invoice Numbers", "Processed At", "Sent To", "Status"]
    assert len(rows) == 3
    invoice_col = [r[1] for r in rows[1:]]
    assert "0001" in invoice_col
    assert "0002" in invoice_col


def test_post_export_processed_404_when_folder_unknown(client):
    test_client, _ = client
    r = test_client.post("/api/maintenance/export-processed?folder_id=999")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# HTTP: GET /api/maintenance/download
# ---------------------------------------------------------------------------


def test_download_returns_csv_bytes(client):
    test_client, _ = client
    r = test_client.post("/api/maintenance/export-processed?folder_id=1")
    path = r.json()["path"]
    r = test_client.get(f"/api/maintenance/download?path={path}")
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert r.text.count("\n") >= 2  # at least header + 2 data rows


def test_download_rejects_path_outside_data_dir(client):
    test_client, _ = client
    r = test_client.get("/api/maintenance/download?path=/etc/passwd")
    assert r.status_code == 400


def test_download_404_for_missing_file(client):
    test_client, settings = client
    missing = settings.logs_dir / "nope.csv"
    r = test_client.get(f"/api/maintenance/download?path={missing}")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# export_processed_report (function-level)
# ---------------------------------------------------------------------------


def test_export_handles_duplicate_filename(client):
    """Two exports of the same folder get distinct filenames."""
    _test_client, settings = client
    db = open_database(settings)
    try:
        path_a = export_processed_report(db, folder_id=1, output_dir=str(settings.logs_dir))
        path_b = export_processed_report(db, folder_id=1, output_dir=str(settings.logs_dir))
    finally:
        db.close()
    assert path_a != path_b
    assert "(1)" in path_b
