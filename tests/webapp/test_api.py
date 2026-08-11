"""API tests for the webapp (FastAPI TestClient)."""

import shutil

import pytest
from fastapi.testclient import TestClient

from webapp.config import Settings
from webapp.main import create_app

pytestmark = [pytest.mark.integration]


@pytest.fixture
def client(tmp_path):
    settings = Settings(
        base_dir=tmp_path / "data", data_dir=tmp_path / "data" / "config"
    )
    app = create_app(settings=settings)
    return TestClient(app)


@pytest.fixture
def legacy_db(tmp_path):
    src = __import__("tests.conftest", fromlist=["LEGACY_DB_PATH"]).LEGACY_DB_PATH
    if not src.exists():
        pytest.skip("Legacy v32 database fixture not found")
    dst = tmp_path / "source_folders.db"
    shutil.copy2(src, dst)
    return dst


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "base_dir" in body


def test_index_served(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Batch File Sender" in resp.text


def test_import_flow(client, legacy_db):
    # Empty before import.
    config = client.get("/api/config").json()
    assert config["folders_count"] == 0

    with open(legacy_db, "rb") as fh:
        resp = client.post(
            "/api/import",
            files={"file": ("folders.db", fh, "application/octet-stream")},
            data={"platform": "Windows", "base_dir": "/data"},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["folders_imported"] > 0
    assert body["source_platform"] == "Windows"
    assert body["base_directory"] == "/data"

    config = client.get("/api/config").json()
    assert config["folders_count"] == body["folders_imported"]
    assert config["source_platform"] == "Windows"
    assert config["imported_base_dir"] == "/data"

    folders = client.get("/api/folders").json()
    assert len(folders) == body["folders_imported"]
    for folder in folders:
        # Paths were rebased to be relative to the base-dir.
        assert not folder["folder_name"].startswith("/")
        assert ":" not in folder["folder_name"]


def test_run_endpoint_requires_database(client):
    resp = client.post("/api/run")
    assert resp.status_code == 400


def test_processed_files_empty_before_import(client):
    body = client.get("/api/processed-files").json()
    assert body["count"] == 0


def test_unknown_run_404(client):
    resp = client.get("/api/runs/does-not-exist")
    assert resp.status_code == 404
