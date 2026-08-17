"""API tests for the webapp (FastAPI TestClient)."""

import contextlib
import shutil
import time

import pytest
from fastapi.testclient import TestClient

from webapp.config import Settings
from webapp.database import open_database
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
    # Phase 6 (gap 1.6): the response now includes the wall-clock
    # duration so the dashboard's import notice can render "Imported
    # N folders in 28.4s". The number is non-negative and small for
    # the tiny test fixture.
    assert isinstance(body["duration_seconds"], (int, float))
    assert body["duration_seconds"] >= 0
    assert body["duration_seconds"] < 60

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


def test_import_rejects_non_sqlite_upload(client):
    """A malformed database upload is a 400 (client error), not a 500."""
    resp = client.post(
        "/api/import",
        files={
            "file": (
                "garbage.db",
                b"this is not a database",
                "application/octet-stream",
            )
        },
    )
    assert resp.status_code == 400, resp.text
    assert "not a SQLite database" in resp.json()["detail"]


def test_run_endpoint_requires_database(client):
    resp = client.post("/api/run")
    assert resp.status_code == 400


def test_processed_files_empty_before_import(client):
    body = client.get("/api/processed-files").json()
    assert body["count"] == 0


def test_unknown_run_404(client):
    resp = client.get("/api/runs/does-not-exist")
    assert resp.status_code == 404


def test_run_report_duration(client):
    """Phase 5.3: a completed run's API payload carries duration + throughput."""
    settings = client.app.state.settings
    input_dir = settings.base_dir / "input"
    input_dir.mkdir(parents=True)
    (input_dir / "sample_001.txt").write_text("hello 001\n", encoding="utf-8")
    (input_dir / "sample_002.txt").write_text("hello 002\n", encoding="utf-8")

    db = open_database(settings)
    try:
        db.folders_table.insert(
            {
                "folder_name": "input",
                "folder_is_active": "True",
                "alias": "inbox",
                "process_backend_copy": True,
                "copy_to_directory": "output",
                "process_backend_ftp": False,
                "process_backend_email": False,
            }
        )
    finally:
        with contextlib.suppress(Exception):
            db.close()

    resp = client.post("/api/run")
    assert resp.status_code == 200, resp.text
    run_id = resp.json()["run_id"]

    # The run executes in a background thread; poll until it completes.
    report = {}
    for _ in range(200):
        report = client.get(f"/api/runs/{run_id}").json()
        if report["status"] != "running":
            break
        time.sleep(0.05)
    assert report["status"] == "completed"
    assert report["total_processed"] == 2
    assert report["duration_seconds"] >= 0
    assert report["files_per_second"] > 0


def test_run_report_warning_surfaces_failure_rate(client):
    """Phase 5.3 follow-up: a folder over its failure-rate threshold warns."""
    settings = client.app.state.settings

    db = open_database(settings)
    try:
        db.folders_table.insert(
            {
                "folder_name": "inbox/missing",
                "folder_is_active": "True",
                "alias": "MISSING",
                "process_backend_copy": True,
                "copy_to_directory": "output",
                "process_backend_ftp": False,
                "process_backend_email": False,
                "max_failure_rate_percent": "10",
            }
        )
    finally:
        with contextlib.suppress(Exception):
            db.close()

    resp = client.post("/api/run")
    assert resp.status_code == 200, resp.text
    run_id = resp.json()["run_id"]

    report = {}
    for _ in range(200):
        report = client.get(f"/api/runs/{run_id}").json()
        if report["status"] != "running":
            break
        time.sleep(0.05)
    assert report["status"] == "completed"
    folder = report["folders"][0]
    assert folder["files_failed"] == 1
    assert folder["warning"] == "failure rate 100.0% (limit 10%)"
    assert folder["duration_seconds"] >= 0

    # The list endpoint keeps one ordering contract (newest first)
    # regardless of whether runs come from memory or persisted history.
    # Ordering itself is asserted in test_api_runs_orders_by_start_time_desc;
    # here we only need the completed run to be listed.
    runs = client.get("/api/runs").json()
    ids = [r["run_id"] for r in runs]
    assert run_id in ids


def test_api_runs_orders_by_start_time_desc(client):
    """Phase 5.3: /api/runs is uniformly newest-first across sources.

    The in-memory store hands out runs in insertion order (oldest
    first) while persisted history is newest first. The endpoint must
    normalise both so the Recent-runs list does not reorder after a
    restart (see the api_runs docstring).
    """
    from webapp.runner import RunReport, RunStore

    # Replace the app's store contents with two reports whose ids sort
    # the same way their start times do, so the assertion below
    # distinguishes insertion order from time order: "older" was
    # inserted first but started later.
    older = RunReport(
        run_id="older",
        status="completed",
        started_at="2026-08-13T09:00:00.000000",
        finished_at="2026-08-13T09:00:10.000000",
        total_processed=1,
    )
    newer = RunReport(
        run_id="newer",
        status="completed",
        started_at="2026-08-13T10:00:00.000000",
        finished_at="2026-08-13T10:00:10.000000",
        total_processed=2,
    )
    # ``_runs`` is keyed by run_id; the dict keeps insertion order, so
    # this simulates the store handing the older run back first.
    store = RunStore()
    store._runs = {"older": older, "newer": newer}
    old_store = client.app.state.run_store
    try:
        client.app.state.run_store = store
        runs = client.get("/api/runs").json()
        ids = [r["run_id"] for r in runs]
        assert ids[0] == "newer", f"newest first, got {ids}"
        assert ids[1] == "older"
    finally:
        client.app.state.run_store = old_store


def test_settings_requires_database(client):
    resp = client.get("/api/settings")
    assert resp.status_code == 503
    assert "No database imported" in resp.json()["detail"]
    resp = client.put("/api/settings", json={})
    assert resp.status_code == 503


def test_settings_defaults_after_import(client, legacy_db):
    """After import the editable settings mirror the legacy DB records."""
    with open(legacy_db, "rb") as fh:
        resp = client.post(
            "/api/import",
            files={"file": ("folders.db", fh, "application/octet-stream")},
            data={"platform": "Windows", "base_dir": "/data"},
        )
    assert resp.status_code == 200, resp.text

    body = client.get("/api/settings").json()
    assert body["email"]["smtp_port"] == 587
    assert isinstance(body["email"]["enable_email"], bool)
    assert body["as400"]["as400_address"] == "" or isinstance(
        body["as400"]["as400_address"], str
    )
    assert isinstance(body["backup"]["enable_interval_backups"], bool)
    assert body["backup"]["backup_counter_maximum"] >= 1
    assert isinstance(body["reporting"]["enable_reporting"], bool)


def test_settings_put_round_trips_and_reaches_runner(client, legacy_db):
    """PUT persists into both singleton records; the runner reads them."""
    with open(legacy_db, "rb") as fh:
        resp = client.post(
            "/api/import",
            files={"file": ("folders.db", fh, "application/octet-stream")},
            data={"platform": "Windows", "base_dir": "/data"},
        )
    assert resp.status_code == 200, resp.text

    payload = {
        "email": {
            "enable_email": True,
            "email_address": "ops@example.com",
            "email_username": "sender",
            "email_password": "s3cret",
            "email_smtp_server": "smtp.example.com",
            "smtp_port": 2525,
        },
        "as400": {
            "as400_address": "10.0.0.7",
            "as400_username": "edi_user",
            "as400_password": "pw",
            "ssh_key_filename": "/keys/edi.pem",
        },
        "backup": {
            "enable_interval_backups": True,
            "backup_counter_maximum": 50,
        },
        "reporting": {
            "enable_reporting": True,
            "report_email_destination": "reports@example.com",
            "report_edi_errors": True,
            "report_printing_fallback": False,
            "logs_directory": "/var/log/bfs",
            "copy_to_directory": "/data/out",
        },
    }
    resp = client.put("/api/settings", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["email"]["smtp_port"] == 2525
    assert body["email"]["enable_email"] is True
    assert body["as400"]["as400_address"] == "10.0.0.7"
    assert body["backup"]["enable_interval_backups"] is True
    assert body["backup"]["backup_counter_maximum"] == 50
    assert body["reporting"]["report_email_destination"] == "reports@example.com"

    # The GET returns the same payload.
    assert client.get("/api/settings").json() == body

    # The runner's settings_dict reads the same record, so AS400 creds
    # flow into converters on the next run.
    settings = client.app.state.settings
    db = open_database(settings)
    try:
        settings_dict = db.get_settings_or_default()
        assert settings_dict["as400_address"] == "10.0.0.7"
        assert settings_dict["email_smtp_server"] == "smtp.example.com"
        assert settings_dict["enable_email"] is True
    finally:
        with contextlib.suppress(Exception):
            db.close()


def test_settings_put_rejects_unknown_fields(client, legacy_db):
    with open(legacy_db, "rb") as fh:
        resp = client.post(
            "/api/import",
            files={"file": ("folders.db", fh, "application/octet-stream")},
            data={"platform": "Windows", "base_dir": "/data"},
        )
    assert resp.status_code == 200, resp.text

    resp = client.put(
        "/api/settings",
        json={"email": {"enable_email": True, "bogus": 1}},
    )
    assert resp.status_code == 422
