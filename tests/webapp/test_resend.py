"""Tests for the webapp resend endpoints + runner."""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from webapp.config import Settings
from webapp.database import open_database
from webapp.main import create_app
from webapp.maintenance import mark_file_processed
from webapp.resend import (
    clear_resend_flags,
    delete_processed_rows,
    list_processed_files,
    set_resend_flag,
    set_resend_flag_batch,
)

pytestmark = [pytest.mark.integration]


@pytest.fixture
def client(tmp_path: Path):
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
    db.close()
    app = create_app(settings=settings)
    return TestClient(app), settings


@pytest.fixture
def seeded(client):
    """A client + a single seeded processed-files row."""
    test_client, settings = client
    db = open_database(settings)
    rid = mark_file_processed(
        db,
        file_path="/incoming/test/sample.001",
        folder_id=1,
        folder_alias="TEST",
        invoice_numbers="0001",
    )
    db.close()
    return test_client, settings, rid


# ---------------------------------------------------------------------------
# resend.py function-level tests
# ---------------------------------------------------------------------------


def test_list_processed_files_returns_recent_first(seeded):
    _, settings, _ = seeded
    db = open_database(settings)
    try:
        rows = list_processed_files(db, limit=10)
        assert len(rows) == 1
        assert rows[0]["file_name"] == "/incoming/test/sample.001"
        assert "resend_flag" in rows[0]
    finally:
        db.close()


def test_list_processed_files_only_resend_flagged(seeded):
    _test_client, settings, rid = seeded
    db = open_database(settings)
    try:
        # Initially nothing flagged.
        rows = list_processed_files(db, only_resend_flagged=True)
        assert rows == []
        # Flag the row.
        set_resend_flag(db, rid, resend=True)
        rows = list_processed_files(db, only_resend_flagged=True)
        assert len(rows) == 1
    finally:
        db.close()


def test_set_resend_flag_round_trip(seeded):
    _, settings, rid = seeded
    db = open_database(settings)
    try:
        assert set_resend_flag(db, rid, resend=True)
        rows = list(db.processed_files.find(id=rid))
        assert rows[0]["resend_flag"] is True or rows[0]["resend_flag"] == 1
        assert set_resend_flag(db, rid, resend=False)
        rows = list(db.processed_files.find(id=rid))
        assert not rows[0]["resend_flag"]
    finally:
        db.close()


def test_set_resend_flag_returns_false_for_missing(seeded):
    _, settings, _ = seeded
    db = open_database(settings)
    try:
        assert set_resend_flag(db, 99999, resend=True) is False
    finally:
        db.close()


def test_set_resend_flag_batch_updates_many(seeded):
    _test_client, settings, _ = seeded
    db = open_database(settings)
    try:
        mark_file_processed(
            db,
            file_path="/incoming/test/sample.002",
            folder_id=1,
            folder_alias="TEST",
        )
        mark_file_processed(
            db,
            file_path="/incoming/test/sample.003",
            folder_id=1,
            folder_alias="TEST",
        )
    finally:
        db.close()
    db = open_database(settings)
    try:
        rows = list(db.processed_files.find(folder_id=1))
        ids = [r["id"] for r in rows]
    finally:
        db.close()
    db = open_database(settings)
    try:
        updated = set_resend_flag_batch(db, ids, resend=True)
        assert updated == 3
        rows = list(db.processed_files.all())
        assert all(r["resend_flag"] for r in rows)
    finally:
        db.close()


def test_clear_resend_flags(seeded):
    _, settings, rid = seeded
    db = open_database(settings)
    try:
        set_resend_flag(db, rid, resend=True)
    finally:
        db.close()
    db = open_database(settings)
    try:
        cleared = clear_resend_flags(db, [rid])
        assert cleared == 1
        rows = list(db.processed_files.find(id=rid))
        assert not rows[0]["resend_flag"]
    finally:
        db.close()


def test_delete_processed_rows(seeded):
    _, settings, rid = seeded
    db = open_database(settings)
    try:
        removed = delete_processed_rows(db, [rid])
        assert removed == 1
        rows = list(db.processed_files.all())
        assert rows == []
    finally:
        db.close()


# ---------------------------------------------------------------------------
# HTTP endpoint tests
# ---------------------------------------------------------------------------


def test_get_flagged_returns_all_rows(seeded):
    test_client, _, _ = seeded
    r = test_client.get("/api/processed-files/flagged")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert body["files"][0]["resend_flag"] is False or body["files"][0]["resend_flag"] == 0


def test_flag_for_resend_single(seeded):
    test_client, _, rid = seeded
    r = test_client.post(f"/api/processed-files/{rid}/resend?resend=true")
    assert r.status_code == 200
    body = r.json()
    assert body == {"id": rid, "resend_flag": True}

    # Verify in DB.
    r = test_client.get("/api/processed-files/flagged")
    files = r.json()["files"]
    assert any(f["id"] == rid and f["resend_flag"] for f in files)


def test_flag_for_resend_404(seeded):
    test_client, _, _ = seeded
    r = test_client.post("/api/processed-files/99999/resend?resend=true")
    assert r.status_code == 404


def test_flag_batch(seeded):
    test_client, settings, _rid = seeded
    db = open_database(settings)
    try:
        mark_file_processed(
            db,
            file_path="/incoming/test/sample.002",
            folder_id=1,
            folder_alias="TEST",
        )
    finally:
        db.close()
    db = open_database(settings)
    try:
        ids = [r["id"] for r in db.processed_files.find(folder_id=1)]
    finally:
        db.close()
    r = test_client.post("/api/processed-files/resend-batch", json=[ids[0], ids[1]])
    assert r.status_code == 200
    assert r.json() == {"updated": 2}


def test_clear_all_flags(seeded):
    test_client, _, rid = seeded
    # Flag one row.
    test_client.post(f"/api/processed-files/{rid}/resend?resend=true")
    r = test_client.post("/api/processed-files/clear-flags")
    assert r.status_code == 200
    assert r.json() == {"cleared": 1}
    r = test_client.get("/api/processed-files/flagged")
    assert not any(f["resend_flag"] for f in r.json()["files"])


def test_resend_no_flagged_returns_immediately(seeded):
    """POST /api/resend with no flagged rows returns a run id but the
    report shows zero work."""
    test_client, _, _ = seeded
    r = test_client.post("/api/resend")
    assert r.status_code == 200
    run_id = r.json()["run_id"]
    # Wait for completion.
    import time
    for _ in range(20):
        time.sleep(0.1)
        report = test_client.get(f"/api/runs/{run_id}").json()
        if report["status"] != "running":
            break
    assert report["status"] == "completed"
    assert report["folders"] == []
    assert report["total_processed"] == 0


def test_resend_runs_through_dispatcher(seeded, tmp_path):
    """A flagged row whose source file exists triggers the dispatcher
    against that path. We make the file exist, flag the row, and
    expect the resend run to process it through the copy backend."""
    test_client, settings, rid = seeded
    base = settings.base_dir  # already a Path
    folder_path = base / "inbox" / "test"
    folder_path.mkdir(parents=True, exist_ok=True)
    src = folder_path / "sample.001"
    src.write_text("re-send me", encoding="utf-8")

    # Update the row's file_name to point at the actual file.
    db = open_database(settings)
    try:
        rows = list(db.processed_files.find(id=rid))
        row = dict(rows[0])
        row["file_name"] = str(src)
        db.processed_files.update(row, ["id"])
        set_resend_flag(db, rid, resend=True)
    finally:
        db.close()

    archive = base / "archive" / "test"
    archive.mkdir(parents=True, exist_ok=True)

    r = test_client.post("/api/resend")
    assert r.status_code == 200
    run_id = r.json()["run_id"]
    import time
    for _ in range(40):
        time.sleep(0.25)
        report = test_client.get(f"/api/runs/{run_id}").json()
        if report["status"] != "running":
            break
    assert report["status"] == "completed"
    # The copy backend should have written the file to the archive.
    assert (archive / "sample.001").is_file()
    # The flagged row should be replaced by a fresh processed-files row.
    db = open_database(settings)
    try:
        rows = list(db.processed_files.find(folder_id=1))
        # New row created; the old flagged one was deleted.
        assert len(rows) >= 1
        # The new row's resend_flag should be False (default).
        assert all(not r["resend_flag"] for r in rows)
    finally:
        db.close()


def test_resend_refuses_when_run_in_flight(seeded):
    """POST /api/resend cannot start while a normal run is active."""
    from webapp.runner import RunStore

    test_client, settings, _ = seeded
    # Fake-occupy the runner.
    store = RunStore()
    store.start(settings)  # starts a worker; will run on the empty DB quickly
    # Patch the app to use our test store.
    test_client.app.state.run_store = store
    # Now a second /api/resend should be refused because the in-flight
    # worker still owns the active slot.
    r = test_client.post("/api/resend")
    assert r.status_code == 400
    assert "already in progress" in r.json()["detail"]
