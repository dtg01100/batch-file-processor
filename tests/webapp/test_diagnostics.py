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
    # The fixture seeds ``process_backend_copy=True`` with a
    # ``copy_to_directory`` that doesn't exist on disk — Phase 6.3
    # surfaces that as a warning so the operator notices. The other
    # sections (modules, runs, watcher) stay clean.
    copy_warnings = [w for w in body["warnings"] if "Copy destination" in w]
    assert len(copy_warnings) == 1
    assert "TEST" in copy_warnings[0]


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


# ---------------------------------------------------------------------------
# Phase 6.3 — backend health probe tests
# ---------------------------------------------------------------------------


def test_diagnostics_includes_backends_health(client):
    """The diagnostics payload gains a ``backends_health`` key with
    the three documented sections: ``smtp``, ``ftp``, ``copy``.

    Even without a configured SMTP server the shape is stable — the
    ``not configured`` sentinel is the documented contract for
    "operator hasn't pointed the webapp at an SMTP server yet".
    """
    test_client, _ = client
    r = test_client.get("/api/diagnostics")
    assert r.status_code == 200
    body = r.json()
    assert "backends_health" in body
    bh = body["backends_health"]
    assert set(bh.keys()) == {"smtp", "ftp", "copy"}
    # SMTP is "not configured" because the fixture doesn't seed an
    # ``email_smtp_server`` row.
    assert bh["smtp"]["ok"] is False
    assert "not configured" in bh["smtp"]["error"].lower()
    # FTP likewise — no folder has ``process_backend_ftp`` enabled.
    assert bh["ftp"]["ok"] is False
    # Copy: the fixture seeded one folder with ``process_backend_copy``
    # enabled and ``copy_to_directory = archive/test`` (which doesn't
    # exist on disk). The probe reports ``ok: False`` with the
    # missing-path error.
    assert isinstance(bh["copy"], list)
    assert len(bh["copy"]) == 1
    row = bh["copy"][0]
    assert row["folder_id"] == 1
    assert row["alias"] == "TEST"
    assert row["ok"] is False
    assert "missing" in row["error"].lower()


def test_probe_smtp_reports_unreachable_host(tmp_path):
    """A TCP probe to an unroutable host returns ``{ok: False, error}``
    within the documented timeout — never raises."""
    from webapp.diagnostics import _probe_smtp

    # 198.51.100.0/24 is reserved for documentation (RFC 5737); packets
    # to it are guaranteed to be dropped by the upstream router, so
    # the probe times out cleanly without hitting a real server.
    result = _probe_smtp("198.51.100.7", 25, timeout=0.3)
    assert result["ok"] is False
    assert result["error"] is not None
    assert result["latency_ms"] is not None
    # The latency_ms is the wall-clock spent before the error; assert
    # it's at least approximately the timeout we set.
    assert result["latency_ms"] >= 200


def test_probe_ftp_reports_unreachable_host(tmp_path):
    """Same contract as :func:`_probe_smtp` — unreachable → False +
    error, never raises."""
    from webapp.diagnostics import _probe_ftp

    result = _probe_ftp("198.51.100.8", 21, timeout=0.3)
    assert result["ok"] is False
    assert result["error"] is not None
    assert result["latency_ms"] is not None


def test_probe_copy_missing_path():
    """A missing path is reported as ``ok: False`` with a clear
    error."""
    from webapp.diagnostics import _probe_copy

    # /this/path/definitely/does/not/exist/anywhere
    result = _probe_copy("/nonexistent/path/for/test")
    assert result["ok"] is False
    assert "missing" in result["error"].lower()


def test_probe_copy_existing_path(tmp_path):
    """An existing directory is reported as ``ok: True``."""
    from webapp.diagnostics import _probe_copy

    result = _probe_copy(str(tmp_path))
    assert result["ok"] is True
    assert result["error"] is None


def test_probe_copy_empty_path():
    """An empty path is reported as ``ok: False`` with the
    documented "no copy destination configured" message."""
    from webapp.diagnostics import _probe_copy

    result = _probe_copy("")
    assert result["ok"] is False
    assert "no copy destination" in result["error"].lower()


def test_probe_smtp_reports_reachable(tmp_path):
    """A local TCP server is reported as reachable.

    The probe binds a real socket on localhost, then probes it from
    the production code path. ``socket.create_connection`` accepts
    any listening socket — we don't need a real SMTP server, only
    a TCP listener. This validates the happy path of the probe.
    """
    import socket
    import threading

    from webapp.diagnostics import _probe_smtp

    ready = threading.Event()
    stop = threading.Event()

    def _serve():
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        srv.settimeout(5.0)
        ready.set()
        try:
            conn, _ = srv.accept()
            conn.settimeout(2.0)
            # Send a minimal SMTP banner so the probe's banner-read
            # path runs.
            conn.sendall(b"220 test\r\n")
            conn.close()
        except Exception:
            pass
        finally:
            srv.close()
            stop.set()

    t = threading.Thread(target=_serve, daemon=True)
    t.start()
    try:
        ready.wait(timeout=2.0)
        port = t.name and 0  # placeholder; we need the actual bound port
    except Exception:
        pass
    # Re-bind to get the actual port: simpler approach — start a
    # thread that returns the port via a list.
    port_holder = [0]
    ready2 = threading.Event()

    def _serve2():
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("127.0.0.1", 0))
        port_holder[0] = srv.getsockname()[1]
        srv.listen(1)
        srv.settimeout(5.0)
        ready2.set()
        try:
            conn, _ = srv.accept()
            conn.settimeout(2.0)
            conn.sendall(b"220 test\r\n")
            conn.close()
        except Exception:
            pass
        finally:
            srv.close()

    t2 = threading.Thread(target=_serve2, daemon=True)
    t2.start()
    ready2.wait(timeout=2.0)
    port = port_holder[0]
    result = _probe_smtp("127.0.0.1", port, timeout=2.0)
    t2.join(timeout=3.0)
    assert result["ok"] is True
    assert result["latency_ms"] is not None
    assert result["error"] is None


def test_probe_ftp_reports_reachable(tmp_path):
    """A local TCP listener is reported as reachable by the FTP
    probe (same rationale as :func:`test_probe_smtp_reports_reachable`)."""
    import socket
    import threading

    from webapp.diagnostics import _probe_ftp

    port_holder = [0]
    ready = threading.Event()

    def _serve():
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("127.0.0.1", 0))
        port_holder[0] = srv.getsockname()[1]
        srv.listen(1)
        srv.settimeout(5.0)
        ready.set()
        try:
            conn, _ = srv.accept()
            conn.settimeout(2.0)
            conn.sendall(b"220 test FTP\r\n")
            conn.close()
        except Exception:
            pass
        finally:
            srv.close()

    t = threading.Thread(target=_serve, daemon=True)
    t.start()
    ready.wait(timeout=2.0)
    port = port_holder[0]
    result = _probe_ftp("127.0.0.1", port, timeout=2.0)
    t.join(timeout=3.0)
    assert result["ok"] is True
    assert result["latency_ms"] is not None


def test_collect_diagnostics_warns_on_unreachable_smtp(tmp_path):
    """A configured but unreachable SMTP server surfaces as a
    warning so the diagnostics banner lights up amber."""
    from webapp.diagnostics import PROBE_TIMEOUT_SECONDS, collect_diagnostics

    settings = Settings(
        base_dir=tmp_path / "data", data_dir=tmp_path / "data" / "config"
    )
    settings.ensure_dirs()
    db = open_database(settings)
    try:
        # Seed the global settings row (id=1) with an SMTP server
        # that's guaranteed to be unroutable. ``database_obj``'s
        # ``get_settings_or_default`` helper reads this row.
        settings_row = db.database_connection.raw_connection.execute(
            "SELECT * FROM settings WHERE id = 1"
        ).fetchone()
        if settings_row is None:
            db.database_connection.raw_connection.execute(
                "INSERT INTO settings (id, email_smtp_server, smtp_port) "
                "VALUES (1, ?, ?)",
                ("198.51.100.10", 25),
            )
        else:
            db.database_connection.raw_connection.execute(
                "UPDATE settings SET email_smtp_server = ?, smtp_port = ? WHERE id = 1",
                ("198.51.100.10", 25),
            )
        db.database_connection.raw_connection.commit()
    finally:
        db.close()

    payload = collect_diagnostics(
        settings=settings,
        run_store=None,
        history=None,
        schedule_summary=None,
        watched_folders=[],
        backups_count=0,
    )
    bh = payload["backends_health"]
    assert bh["smtp"]["ok"] is False
    # The warning surfaces to the dashboard's banner.
    assert any("SMTP backend unreachable" in w for w in payload["warnings"])


def test_collect_diagnostics_does_not_raise_with_no_db(tmp_path):
    """The diagnostics endpoint never raises even when every probe
    is up against a missing database — the contract for the
    pre-import path is "show zeros + not-configured, not 500"."""
    from webapp.diagnostics import collect_diagnostics

    settings = Settings(
        base_dir=tmp_path / "data", data_dir=tmp_path / "data" / "config"
    )
    settings.ensure_dirs()
    payload = collect_diagnostics(
        settings=settings,
        run_store=None,
        history=None,
        schedule_summary=None,
        watched_folders=[],
        backups_count=0,
    )
    bh = payload["backends_health"]
    assert bh["smtp"]["ok"] is False
    assert bh["ftp"]["ok"] is False
    assert bh["copy"] == []
