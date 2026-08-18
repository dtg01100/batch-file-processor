"""Tests for the webapp diagnostics endpoint + collector."""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from webapp.config import Settings
from webapp.database import open_database
from webapp.diagnostics import (
    EXPECTED_MODULES,
    collect_diagnostics,
)
from webapp.main import create_app
from webapp.maintenance import mark_file_processed

pytestmark = [pytest.mark.integration]


@pytest.fixture
def client(tmp_path: Path):
    settings = Settings(
        base_dir=tmp_path / "data", data_dir=tmp_path / "data" / "config"
    )
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
            "created_at": "2026-08-12T12:00:00",
        }
    )
    db.close()
    app = create_app(settings=settings)
    return TestClient(app), settings


def test_diagnostics_endpoint_returns_snapshot(client):
    """The endpoint surfaces a complete self-test snapshot."""
    test_client, _ = client
    r = test_client.get("/api/diagnostics")
    assert r.status_code == 200
    body = r.json()
    # Top-level keys mirror the audit-doc contract.
    assert set(body.keys()) >= {
        "platform",
        "app",
        "paths",
        "database",
        "runtime",
        "modules",
        "ok",
        "warnings",
        "collected_at",
    }
    # Platform: every required sub-key present.
    plat = body["platform"]
    assert {"system", "release", "machine", "python_version", "pid"}.issubset(
        plat.keys()
    )
    # The Python version is a real string the dashboard can render.
    assert "." in plat["python_version"]
    # Paths: base / data dirs are absolute, DB doesn't yet exist
    # because the seed fixture only inserts one folder row.
    paths = body["paths"]
    assert paths["base_dir"]
    assert paths["data_dir"]
    # The fixture creates folders.db via open_database() in the
    # ``client`` fixture, so database_exists is True.
    assert paths["database_exists"] is True
    # Database counts: one folder seeded; processed/errors/queued are 0.
    db = body["database"]
    assert db["folders_count"] == 1
    assert db["active_folders_count"] == 1
    assert db["processed_files_count"] == 0
    assert db["errors_count"] == 0
    assert db["queued_emails"] == 0
    # Runtime defaults: nothing scheduled, nothing running, no recent
    # failures, no watched folders.
    rt = body["runtime"]
    assert rt["active_runs"] == 0
    assert rt["recent_run_failures_24h"] == 0
    assert rt["watched_folders"] == 0
    # Modules: every expected module imports cleanly (the webapp
    # dependencies are pinned and present in the test venv).
    failed = [m for m in body["modules"] if not m["ok"]]
    assert failed == [], f"Modules failed to import: {failed}"
    # The "ok" flag agrees with the modules list.
    assert body["ok"] is True
    assert body["warnings"] == []


def test_diagnostics_endpoint_counts_processed_and_errors(client):
    """After seeding rows, the counts reflect them."""
    test_client, settings = client
    db = open_database(settings)
    try:
        mark_file_processed(
            db,
            file_path="/incoming/test/sample.001",
            folder_id=1,
            folder_alias="TEST",
        )
        # Two errors via the public errors API so we exercise the
        # normal insert path.
        from webapp.errors import insert_error

        insert_error(
            db,
            folder="/data/inbox/test",
            filename="/data/inbox/test/bad.edi",
            error_type="ValueError",
            error_message="bad data",
        )
    finally:
        db.close()

    r = test_client.get("/api/diagnostics")
    body = r.json()
    db_section = body["database"]
    assert db_section["processed_files_count"] == 1
    assert db_section["errors_count"] == 1


def test_collect_diagnostics_handles_missing_db(tmp_path):
    """When no database exists the collector returns zeros instead of
    raising. This is the path the dashboard hits immediately after
    starting the webapp — before any import has happened."""
    settings = Settings(
        base_dir=tmp_path / "data",
        data_dir=tmp_path / "data" / "config",
    )
    settings.ensure_dirs()
    # No open_database() call: the DB file doesn't exist.
    payload = collect_diagnostics(
        settings=settings,
        run_store=None,
        history=None,
        schedule_summary=None,
        watched_folders=[],
        backups_count=0,
    )
    assert payload["paths"]["database_exists"] is False
    assert payload["database"]["version"] is None
    assert payload["database"]["folders_count"] == 0
    # Recent runs is still a list (the empty case), not None.
    assert payload["runtime"]["recent_runs"] == []


def test_collect_diagnostics_records_warnings_on_recent_failures(tmp_path):
    """A failed run inside the 24h window surfaces as a warning so the
    card can light up amber instead of green."""
    settings = Settings(
        base_dir=tmp_path / "data",
        data_dir=tmp_path / "data" / "config",
    )
    settings.ensure_dirs()
    # No DB / no scheduler — we only care about the runs aggregation.
    #
    # Timestamps must be relative to "now" so the 24h window check in
    # ``_within_last_hours`` stays correct regardless of when the test
    # is run — a hard-coded 2026-08-17T10:00:00 silently dropped out
    # of the window on 2026-08-18 and broke CI.
    started_at = (
        datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=1)
    ).isoformat()
    finished_at = (
        datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=59)
    ).isoformat()
    fake_run = {
        "run_id": "run-bad",
        "status": "failed",
        "started_at": started_at,
        "finished_at": finished_at,
        "total_processed": 0,
        "total_failed": 3,
        "error": "backend down",
    }

    # The collector merges in-memory + history. Use a stub run store
    # exposing ``list`` + ``active_count``.
    class _FakeRun:
        # ``_recent_runs`` reads attributes (RunReport-like), so the
        # fake returns objects, not dicts.
        run_id = fake_run["run_id"]
        status = fake_run["status"]
        started_at = fake_run["started_at"]
        finished_at = fake_run["finished_at"]
        total_processed = fake_run["total_processed"]
        total_failed = fake_run["total_failed"]
        error = fake_run["error"]

    class _FakeRunStore:
        active_count = 0

        @staticmethod
        def list():
            return [_FakeRun()]

    payload = collect_diagnostics(
        settings=settings,
        run_store=_FakeRunStore(),
        history=None,
        schedule_summary={"enabled": False, "interval_seconds": 60},
        watched_folders=[{"last_error": "missing"}],
        backups_count=0,
    )
    # The recent_runs list reflects our fake.
    assert any(r["run_id"] == "run-bad" for r in payload["runtime"]["recent_runs"])
    assert payload["runtime"]["recent_run_failures_24h"] == 1
    # The warnings array surfaces both the recent failure and the
    # watcher error so the dashboard can light up amber.
    warnings = payload["warnings"]
    assert any("Recent run failures" in w for w in warnings)
    assert any("Watcher health" in w for w in warnings)
    # ``ok`` is false because we have warnings.
    assert payload["ok"] is False


def test_expected_modules_covers_core_imports():
    """The expected-modules list mirrors the desktop self-test minus
    the Qt-only entries. A future contributor adding a new module
    should add it here too — the diagnostics card is the regression
    net."""
    # Just a smoke check: the list is non-empty, every name parses
    # as a Python dotted path (top-level package or sub-module), and
    # nothing is obviously malformed.
    assert EXPECTED_MODULES
    for name in EXPECTED_MODULES:
        assert name and not name.endswith(".")
        parts = name.split(".")
        assert all(p.isidentifier() for p in parts), f"bad module name: {name}"
