"""Tests for the per-folder run endpoint."""

from __future__ import annotations

import datetime
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from webapp.config import Settings
from webapp.database import open_database
from webapp.main import create_app

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


def test_post_run_folder_starts_a_single_folder_run(client):
    test_client, _settings = client
    r = test_client.post("/api/folders/1/run")
    assert r.status_code == 200
    body = r.json()
    assert "run_id" in body
    # Wait for completion.
    for _ in range(20):
        time.sleep(0.1)
        detail = test_client.get(f"/api/runs/{body['run_id']}").json()
        if detail["status"] != "running":
            break
    assert detail["status"] == "completed"
    # Exactly one folder report.
    assert len(detail["folders"]) == 1
    assert detail["folders"][0]["alias"] == "TEST"


def test_post_run_folder_404_for_unknown_id(client):
    test_client, _ = client
    r = test_client.post("/api/folders/9999/run")
    assert r.status_code == 404
    assert "not found" in r.json()["detail"]


def test_post_run_folder_400_when_no_db(tmp_path):
    settings = Settings(base_dir=tmp_path / "data", data_dir=tmp_path / "data" / "config")
    settings.ensure_dirs()
    app = create_app(settings=settings)
    client = TestClient(app)
    r = client.post("/api/folders/1/run")
    assert r.status_code == 400


def test_post_run_folder_refuses_when_run_in_flight(client):
    """A second per-folder run cannot start while one is in flight."""
    from webapp.runner import RunStore

    test_client, settings = client
    store = RunStore()
    store.start(settings)
    test_client.app.state.run_store = store
    r = test_client.post("/api/folders/1/run")
    assert r.status_code == 400
    assert "already in progress" in r.json()["detail"]
