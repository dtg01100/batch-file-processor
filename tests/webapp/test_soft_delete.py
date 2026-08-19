"""Phase 6.4 soft-delete tests."""
from __future__ import annotations

import datetime
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from webapp.config import Settings
from webapp.database import open_database
from webapp.main import create_app
from webapp.routers.folders import SoftDeleteTrimSupervisor

pytestmark = [pytest.mark.integration]


@pytest.fixture
def setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("BFS_API_TOKEN", raising=False)
    settings = Settings(tmp_path / "data", tmp_path / "data" / "config")
    db = open_database(settings)
    try:
        folder_id = db.folders_table.insert({
            "folder_name": "inbox/soft-delete", "folder_is_active": True,
            "alias": "SOFT", "process_backend_copy": False,
            "process_backend_ftp": False, "process_backend_email": False,
            "process_backend_http": False, "created_at": "2026-08-18T12:00:00",
        })
        # Phase 7.1 made the re-open unnecessary — the
        # ``_run_current_version_repairs`` gate now runs the v33→v51
        # ``_backfill_defaults`` UPDATE exactly once per DB lifetime
        # (gated on a ``schema_repaired_at`` marker in
        # ``kv_settings``). The fixture can capture ``original``
        # immediately after the insert; the round-trip test in
        # ``tests/webapp/test_database_repair.py`` proves the
        # no-reopen path is stable.
        original = dict(db.folders_table.find_one(id=folder_id))
    finally:
        db.close()
    return TestClient(create_app(settings=settings)), settings, folder_id, original


def test_soft_delete_moves_row(setup):
    client, settings, folder_id, _ = setup
    response = client.delete(f"/api/folders/{folder_id}")
    assert response.status_code == 200
    listed = client.get("/api/folders/deleted").json()
    assert listed["count"] == 1
    assert listed["rows"][0]["folder_id"] == folder_id
    db = open_database(settings)
    try:
        assert db.folders_table.find_one(id=folder_id) is None
    finally:
        db.close()


def test_soft_delete_restore_round_trip(setup):
    client, settings, folder_id, original = setup
    assert client.delete(f"/api/folders/{folder_id}").status_code == 200
    response = client.post(f"/api/folders/{folder_id}/restore")
    assert response.status_code == 200
    db = open_database(settings)
    try:
        restored = dict(db.folders_table.find_one(id=folder_id))
    finally:
        db.close()
    assert restored == original


def test_restore_conflict_on_id_reuse(setup):
    client, settings, folder_id, original = setup
    client.delete(f"/api/folders/{folder_id}")
    db = open_database(settings)
    try:
        db.folders_table.insert(dict(original))
    finally:
        db.close()
    response = client.post(f"/api/folders/{folder_id}/restore")
    assert response.status_code == 409
    assert response.json()["detail"] == f"Folder id {folder_id} already exists; cannot restore"


def test_expired_rows_purged_by_trim(setup):
    _, settings, folder_id, original = setup
    db = open_database(settings)
    try:
        con = db.database_connection.raw_connection
        past = (datetime.datetime.utcnow() - datetime.timedelta(days=1)).isoformat()
        con.execute("INSERT INTO folders_deleted (folder_id, deleted_at, expires_at, original_row_json) VALUES (?, ?, ?, ?)", (folder_id, past, past, json.dumps(original)))
        con.commit()
    finally:
        db.close()
    SoftDeleteTrimSupervisor(settings, interval_seconds=0).start()
    db = open_database(settings)
    try:
        count = db.database_connection.raw_connection.execute("SELECT COUNT(*) FROM folders_deleted").fetchone()[0]
    finally:
        db.close()
    assert count == 0


@pytest.mark.parametrize(("raw", "expected"), [("999", 365), ("0", 1), ("-5", 1)])
def test_ttl_clamp(tmp_path, monkeypatch, raw, expected):
    monkeypatch.setenv("FOLDERS_DELETED_TTL_DAYS", raw)
    settings = Settings(tmp_path / "data", tmp_path / "data" / "config")
    assert settings.folders_deleted_ttl_days == expected
