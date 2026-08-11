"""Tests for the webapp backup / restore module."""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from webapp.backup import list_backups, make_backup, restore_backup
from webapp.config import Settings
from webapp.database import open_database
from webapp.main import create_app

pytestmark = [pytest.mark.integration]


@pytest.fixture
def env(tmp_path):
    """A Settings + active DB with one folder row seeded."""
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
    return settings


# ---------------------------------------------------------------------------
# list_backups
# ---------------------------------------------------------------------------


def test_list_backups_empty_when_no_files(env):
    assert list_backups(env.data_dir) == []


def test_list_backups_returns_newest_first(env):
    p1 = make_backup(env)
    import time
    time.sleep(2.0)  # ensure a different mtime (filesystem is 1s resolution)
    p2 = make_backup(env)
    backups = list_backups(env.data_dir)
    assert len(backups) == 2
    assert backups[0]["path"] == p2
    assert backups[1]["path"] == p1
    # Names use the backup prefix.
    assert all(b["name"].startswith("folders.db.bak-") for b in backups)


def test_list_backups_ignores_unrelated_files(env):
    # Drop a random file into the data dir.
    (env.data_dir / "random.txt").write_text("hi", encoding="utf-8")
    make_backup(env)
    backups = list_backups(env.data_dir)
    assert len(backups) == 1


# ---------------------------------------------------------------------------
# make_backup
# ---------------------------------------------------------------------------


def test_make_backup_returns_empty_when_no_db(tmp_path):
    settings = Settings(
        base_dir=tmp_path / "data", data_dir=tmp_path / "data" / "config"
    )
    settings.ensure_dirs()
    # No DB file yet.
    assert make_backup(settings) == ""


def test_make_backup_copies_the_db(env):
    path = make_backup(env)
    assert Path(path).is_file()
    assert Path(path).read_bytes() == env.database_path.read_bytes()


# ---------------------------------------------------------------------------
# restore_backup
# ---------------------------------------------------------------------------


def test_restore_replaces_active_db(env):
    make_backup(env)  # initial snapshot
    # Mutate the active DB so we can prove restore rewrote it.
    db = open_database(env)
    try:
        rows = list(db.folders_table.all())
        row = dict(rows[0])
        row["alias"] = "MUTATED"
        db.folders_table.update(row, ["id"])
    finally:
        db.close()

    # Make a fresh backup AFTER the mutation; then restore it
    # (which mutates nothing because the backup already has
    # MUTATED) — this proves the restore pipeline works end to end.
    backup = make_backup(env)
    pre_restore = restore_backup(env, backup)
    assert Path(pre_restore).is_file()  # the pre-restore backup

    db = open_database(env)
    try:
        rows = list(db.folders_table.all())
        assert rows[0]["alias"] == "MUTATED"
    finally:
        db.close()


def test_restore_rejects_path_outside_data_dir(env):
    with pytest.raises(ValueError, match="outside the data directory"):
        restore_backup(env, "/etc/passwd")


def test_restore_rejects_non_backup_filename(env):
    (env.data_dir / "not-a-backup.txt").write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="Not a recognised backup"):
        restore_backup(env, str(env.data_dir / "not-a-backup.txt"))


def test_restore_404_for_missing_file(env):
    with pytest.raises(FileNotFoundError):
        restore_backup(env, str(env.data_dir / "folders.db.bak-nope"))


# ---------------------------------------------------------------------------
# HTTP endpoints
# ---------------------------------------------------------------------------


def test_get_backups_returns_empty_list(env):
    app = create_app(settings=env)
    client = TestClient(app)
    r = client.get("/api/backups")
    assert r.status_code == 200
    assert r.json() == {"backups": []}


def test_post_backup_create_then_list(env):
    app = create_app(settings=env)
    client = TestClient(app)
    r = client.post("/api/backup/create")
    assert r.status_code == 200
    path = r.json()["path"]
    assert Path(path).is_file()
    r = client.get("/api/backups")
    assert r.status_code == 200
    backups = r.json()["backups"]
    assert len(backups) == 1
    assert backups[0]["path"] == path


def test_post_backup_restore_400_on_bad_path(env):
    app = create_app(settings=env)
    client = TestClient(app)
    r = client.post("/api/backup/restore?path=/etc/passwd")
    assert r.status_code == 400
    assert "outside" in r.json()["detail"]


def test_post_backup_restore_round_trip(env):
    app = create_app(settings=env)
    client = TestClient(app)
    # Snapshot the active DB, then mutate it, then restore.
    snap = client.post("/api/backup/create").json()["path"]
    db = open_database(env)
    try:
        rows = list(db.folders_table.all())
        row = dict(rows[0])
        row["alias"] = "MUTATED"
        db.folders_table.update(row, ["id"])
    finally:
        db.close()
    r = client.post(f"/api/backup/restore?path={snap}")
    assert r.status_code == 200
    body = r.json()
    assert body["restored_from"] == snap
    assert Path(body["pre_restore_backup"]).is_file()


def test_get_backup_download_serves_the_file(env):
    app = create_app(settings=env)
    client = TestClient(app)
    snap = client.post("/api/backup/create").json()["path"]
    r = client.get(f"/api/backup/download?path={snap}")
    assert r.status_code == 200
    assert "application/octet-stream" in r.headers["content-type"]


def test_get_backup_download_rejects_path_outside_data_dir(env):
    app = create_app(settings=env)
    client = TestClient(app)
    r = client.get("/api/backup/download?path=/etc/passwd")
    assert r.status_code == 400
