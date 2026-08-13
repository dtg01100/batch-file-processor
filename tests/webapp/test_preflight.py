"""Tests for the webapp preflight endpoint (GET /api/preflight)."""

from __future__ import annotations

import shutil

import pytest
from fastapi.testclient import TestClient

from webapp.config import Settings
from webapp.database import open_database
from webapp.main import create_app

pytestmark = [pytest.mark.integration]


def _make_app_with_folders(tmp_path, folders: list[dict]) -> tuple[TestClient, Settings]:
    """Build an app whose DB contains *folders* (raw rows)."""
    settings = Settings(base_dir=tmp_path / "data", data_dir=tmp_path / "data" / "config")
    settings.ensure_dirs()
    db = open_database(settings)
    try:
        for row in folders:
            db.folders_table.insert(row)
    finally:
        db.close()
    return TestClient(create_app(settings=settings)), settings


def _folder(**overrides) -> dict:
    """A minimal active copy-only folder row (mirrors the validator tests)."""
    base = {
        "folder_name": "inbox/x",
        "folder_is_active": True,
        "alias": "XFOLDER",
        "process_backend_copy": True,
        "copy_to_directory": "out/x",
        "process_backend_ftp": False,
        "process_backend_email": False,
        "process_backend_http": False,
    }
    base.update(overrides)
    return base


def test_preflight_503_when_no_database(tmp_path):
    settings = Settings(base_dir=tmp_path / "data", data_dir=tmp_path / "data" / "config")
    settings.ensure_dirs()
    c = TestClient(create_app(settings=settings))
    r = c.get("/api/preflight")
    assert r.status_code == 503


def test_preflight_valid_copy_folder(tmp_path):
    c, settings = _make_app_with_folders(tmp_path, [_folder()])
    # Create the copy destination so the existence check passes.
    (settings.base_dir / "out/x").mkdir(parents=True)
    r = c.get("/api/preflight")
    assert r.status_code == 200
    body = r.json()
    assert body["is_valid"] is True
    assert body["errors"] == []
    assert body["warnings"] == []


def test_preflight_no_backends_is_error(tmp_path):
    c, _ = _make_app_with_folders(
        tmp_path,
        [
            _folder(
                process_backend_copy=False,
                process_backend_ftp=False,
                process_backend_email=False,
                process_backend_http=False,
            )
        ],
    )
    body = c.get("/api/preflight").json()
    assert body["is_valid"] is False
    assert any("No send backends are enabled" in e["message"] for e in body["errors"])
    assert body["errors"][0]["folder_alias"] == "XFOLDER"


def test_preflight_missing_copy_destination_is_warning(tmp_path):
    # The relative copy destination resolves under the base-dir, which
    # does not exist, so the validator warns (not errors).
    c, _ = _make_app_with_folders(tmp_path, [_folder(copy_to_directory="out/nowhere")])
    body = c.get("/api/preflight").json()
    assert body["is_valid"] is True  # warnings don't invalidate
    assert any("does not exist" in w["message"] for w in body["warnings"])


def test_preflight_email_without_smtp_is_error(tmp_path):
    c, _ = _make_app_with_folders(tmp_path, [_folder(process_backend_email=True)])
    body = c.get("/api/preflight").json()
    assert body["is_valid"] is False
    assert any("email_smtp_server" in e["message"] for e in body["errors"])


def test_preflight_ftp_missing_fields_is_error(tmp_path):
    c, _ = _make_app_with_folders(
        tmp_path,
        [
            _folder(
                process_backend_copy=False,
                process_backend_ftp=True,
                ftp_server="",
                ftp_username="",
                ftp_password="",
                ftp_folder="",
            )
        ],
    )
    body = c.get("/api/preflight").json()
    assert body["is_valid"] is False
    msgs = " ".join(e["message"] for e in body["errors"])
    assert "FTP server" in msgs
    assert "FTP folder" in msgs


def test_preflight_scoped_to_folder_id(tmp_path):
    good = _folder(folder_name="inbox/good", alias="GOOD")
    bad = _folder(folder_name="inbox/bad", alias="BAD", process_backend_email=True)
    c, settings = _make_app_with_folders(tmp_path, [good, bad])
    db = open_database(settings)
    try:
        bad_id = db.folders_table.find_one(alias="BAD")["id"]
        good_id = db.folders_table.find_one(alias="GOOD")["id"]
    finally:
        db.close()
    # Scoped to the good folder: valid. Scoped to the bad one: invalid.
    assert c.get(f"/api/preflight?folder_id={good_id}").json()["is_valid"] is True
    body = c.get(f"/api/preflight?folder_id={bad_id}").json()
    assert body["is_valid"] is False
    assert all(e["folder_alias"] == "BAD" for e in body["errors"])


def test_preflight_inactive_folders_skipped(tmp_path):
    c, _ = _make_app_with_folders(
        tmp_path,
        [_folder(folder_is_active=False, process_backend_email=True)],
    )
    body = c.get("/api/preflight").json()
    assert body["is_valid"] is True  # inactive folders aren't run, so no issues


def test_preflight_on_imported_legacy_db(tmp_path, legacy_db):
    """Preflight runs across every imported active folder without 500s."""
    settings = Settings(base_dir=tmp_path / "data", data_dir=tmp_path / "data" / "config")
    from webapp.importer import import_database

    import_database(legacy_db, settings, platform="Windows")
    c = TestClient(create_app(settings=settings))
    body = c.get("/api/preflight").json()
    assert body["is_valid"] in (True, False)
    assert isinstance(body["errors"], list)
    assert isinstance(body["warnings"], list)
    # Every issue carries the expected shape.
    for issue in body["errors"] + body["warnings"]:
        assert set(issue) == {"folder_alias", "message", "severity", "field"}


@pytest.fixture
def legacy_db(tmp_path):
    src = __import__("tests.conftest", fromlist=["LEGACY_DB_PATH"]).LEGACY_DB_PATH
    if not src.exists():
        pytest.skip("Legacy v32 database fixture not found")
    dst = tmp_path / "source_folders.db"
    shutil.copy2(src, dst)
    return dst
