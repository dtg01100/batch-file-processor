"""Tests for the webapp folder watcher (phase 4.3).

Covers the three public pieces of ``webapp.watcher``:

- ``list_watched``: the API-facing list of folders with watching enabled.
- ``FolderWatcher``: the per-folder polling thread and its tick logic
  (``_maybe_run``).
- ``WatcherSupervisor``: ownership of one watcher thread per watched
  folder, including start/stop/restart on config changes.

The dispatch pipeline itself is not exercised here — ``RunStore`` is
replaced with a fake that records ``start_folder`` calls, matching the
pattern used by ``tests/webapp/test_scheduler.py``.
"""

from __future__ import annotations

import datetime
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from webapp.config import Settings
from webapp.database import open_database
from webapp.errors import list_errors
from webapp.main import create_app
from webapp.watcher import (
    DEFAULT_INTERVAL_SECONDS,
    MIN_INTERVAL_SECONDS,
    FolderWatcher,
    WatcherSupervisor,
    list_watched,
)

pytestmark = [pytest.mark.integration]


@pytest.fixture
def settings(tmp_path):
    s = Settings(base_dir=tmp_path / "data", data_dir=tmp_path / "data" / "config")
    s.ensure_dirs()
    return s


def _insert_folder(
    settings,
    *,
    folder_name: str = "inbox/test",
    alias: str = "TEST",
    watch_enabled: bool = False,
    watch_interval_seconds: int = 30,
    **extra,
) -> int:
    """Insert a folder row and return its id."""
    db = open_database(settings)
    row = {
        "folder_name": folder_name,
        "folder_is_active": True,
        "alias": alias,
        "process_backend_copy": False,
        "copy_to_directory": "archive/test",
        "process_backend_ftp": False,
        "process_backend_email": False,
        "process_backend_http": False,
        "watch_enabled": watch_enabled,
        "watch_interval_seconds": watch_interval_seconds,
        "created_at": datetime.datetime.now().isoformat(),
    }
    row.update(extra)
    try:
        fid = db.folders_table.insert(row)
    finally:
        db.close()
    return fid


class _FakeRunStore:
    """Records ``start_folder`` calls so tests can assert on them."""

    def __init__(self, *, raise_on_start_folder: Exception | None = None):
        self._raise = raise_on_start_folder
        self.started: list[tuple] = []

    def start_folder(self, settings, folder_id: int) -> str:
        self.started.append((settings, folder_id))
        if self._raise is not None:
            raise self._raise
        return "fake-run-id"


def _make_file(folder_path, name: str, content: bytes = b"x") -> None:
    (folder_path / name).write_bytes(content)


# ---------------------------------------------------------------------------
# list_watched
# ---------------------------------------------------------------------------


def test_list_watched_returns_only_enabled_folders(settings):
    watched = _insert_folder(settings, watch_enabled=True)
    _insert_folder(settings, folder_name="inbox/other", alias="OFF", watch_enabled=False)

    result = list_watched(settings)

    assert len(result) == 1
    assert result[0]["id"] == watched
    assert result[0]["alias"] == "TEST"
    assert result[0]["watch_enabled"] is True


def test_list_watched_uses_per_folder_interval(settings):
    fid = _insert_folder(settings, watch_enabled=True, watch_interval_seconds=120)

    result = list_watched(settings)

    assert result[0]["id"] == fid
    assert result[0]["watch_interval_seconds"] == 120


def test_list_watched_defaults_interval_when_missing_or_garbage(settings):
    # Missing interval → default.
    missing = _insert_folder(settings, watch_enabled=True, watch_interval_seconds=None)
    # Non-numeric interval → default.
    garbage = _insert_folder(
        settings,
        folder_name="inbox/garbage",
        alias="GARBAGE",
        watch_enabled=True,
        watch_interval_seconds="abc",
    )

    by_id = {f["id"]: f for f in list_watched(settings)}

    assert by_id[missing]["watch_interval_seconds"] == DEFAULT_INTERVAL_SECONDS
    assert by_id[garbage]["watch_interval_seconds"] == DEFAULT_INTERVAL_SECONDS


def test_list_watched_clamps_sub_minimum_interval(settings):
    """Intervals below the floor are clamped so the supervisor's restart
    comparison (clamped watcher vs. reported interval) stays consistent."""
    fid = _insert_folder(settings, watch_enabled=True, watch_interval_seconds=2)

    result = list_watched(settings)

    assert result[0]["id"] == fid
    assert result[0]["watch_interval_seconds"] == MIN_INTERVAL_SECONDS


def test_list_watched_resolves_watch_path(settings):
    _insert_folder(settings, watch_enabled=True)

    result = list_watched(settings)

    assert result[0]["watch_path"] == str((settings.base_dir / "inbox/test").resolve())


def test_list_watched_tolerates_missing_database(settings):
    settings.database_path.unlink(missing_ok=True)
    assert list_watched(settings) == []


# ---------------------------------------------------------------------------
# FolderWatcher._maybe_run
# ---------------------------------------------------------------------------


def test_maybe_run_starts_run_when_new_files_arrive(settings):
    fid = _insert_folder(settings, watch_enabled=True)
    folder_path = settings.base_dir / "inbox/test"
    folder_path.mkdir(parents=True)
    _make_file(folder_path, "new.edi")

    store = _FakeRunStore()
    watcher = FolderWatcher(settings, fid, store, interval_seconds=5)
    watcher._maybe_run()

    assert store.started == [(settings, fid)]


def test_maybe_run_is_a_noop_when_no_files(settings):
    fid = _insert_folder(settings, watch_enabled=True)
    folder_path = settings.base_dir / "inbox/test"
    folder_path.mkdir(parents=True)

    store = _FakeRunStore()
    watcher = FolderWatcher(settings, fid, store, interval_seconds=5)
    watcher._maybe_run()

    assert store.started == []


def test_maybe_run_skips_files_already_processed(settings):
    fid = _insert_folder(settings, watch_enabled=True)
    folder_path = settings.base_dir / "inbox/test"
    folder_path.mkdir(parents=True)
    _make_file(folder_path, "done.edi")
    # Seed a processed-files row whose file_name is a *full path*; the
    # watcher must compare basenames, not raw strings.
    db = open_database(settings)
    db.processed_files.insert(
        {
            "file_name": str(folder_path / "done.edi"),
            "folder_alias": "TEST",
            "folder_id": fid,
            "status": "processed",
        }
    )
    db.close()

    store = _FakeRunStore()
    watcher = FolderWatcher(settings, fid, store, interval_seconds=5)
    watcher._maybe_run()

    assert store.started == []


def test_maybe_run_starts_run_when_only_new_file_is_unprocessed(settings):
    """A mix of processed + new files still triggers a run."""
    fid = _insert_folder(settings, watch_enabled=True)
    folder_path = settings.base_dir / "inbox/test"
    folder_path.mkdir(parents=True)
    _make_file(folder_path, "done.edi")
    _make_file(folder_path, "fresh.edi")
    db = open_database(settings)
    db.processed_files.insert(
        {"file_name": "done.edi", "folder_alias": "TEST", "folder_id": fid}
    )
    db.close()

    store = _FakeRunStore()
    watcher = FolderWatcher(settings, fid, store, interval_seconds=5)
    watcher._maybe_run()

    assert store.started == [(settings, fid)]


def test_maybe_run_is_a_noop_when_watching_disabled_mid_flight(settings):
    fid = _insert_folder(settings, watch_enabled=True)
    folder_path = settings.base_dir / "inbox/test"
    folder_path.mkdir(parents=True)
    _make_file(folder_path, "new.edi")

    # Operator turns watching off after the thread was created.
    db = open_database(settings)
    db.folders_table.update({"id": fid, "watch_enabled": False}, ["id"])
    db.close()

    store = _FakeRunStore()
    watcher = FolderWatcher(settings, fid, store, interval_seconds=5)
    watcher._maybe_run()

    assert store.started == []


def test_maybe_run_is_a_noop_when_folder_dir_missing(settings):
    fid = _insert_folder(settings, watch_enabled=True)
    # The configured directory is never created.

    store = _FakeRunStore()
    watcher = FolderWatcher(settings, fid, store, interval_seconds=5)
    watcher._maybe_run()

    assert store.started == []


def test_maybe_run_is_a_noop_when_folder_row_deleted(settings):
    fid = _insert_folder(settings, watch_enabled=True)
    folder_path = settings.base_dir / "inbox/test"
    folder_path.mkdir(parents=True)
    _make_file(folder_path, "new.edi")
    db = open_database(settings)
    db.folders_table.delete(id=fid)
    db.close()

    store = _FakeRunStore()
    watcher = FolderWatcher(settings, fid, store, interval_seconds=5)
    watcher._maybe_run()

    assert store.started == []


def test_maybe_run_skips_empty_files(settings):
    fid = _insert_folder(settings, watch_enabled=True)
    folder_path = settings.base_dir / "inbox/test"
    folder_path.mkdir(parents=True)
    # Zero-byte files are almost certainly mid-write; skip them.
    _make_file(folder_path, "partial.edi", content=b"")

    store = _FakeRunStore()
    watcher = FolderWatcher(settings, fid, store, interval_seconds=5)
    watcher._maybe_run()

    assert store.started == []

    # Once the file has content, the next tick picks it up.
    _make_file(folder_path, "partial.edi", content=b"content")
    watcher._maybe_run()
    assert store.started == [(settings, fid)]


def test_maybe_run_truncates_burst_to_max_files_per_tick(settings, monkeypatch):
    """A burst arrival still triggers exactly one run; the tick is capped
    (the cap bounds the dispatcher's work, which the fake store can't see,
    but the run must still start and must not be started twice)."""
    monkeypatch.setattr("webapp.watcher.MAX_FILES_PER_TICK", 2)
    fid = _insert_folder(settings, watch_enabled=True)
    folder_path = settings.base_dir / "inbox/test"
    folder_path.mkdir(parents=True)
    for i in range(10):
        _make_file(folder_path, f"burst-{i}.edi")

    store = _FakeRunStore()
    watcher = FolderWatcher(settings, fid, store, interval_seconds=5)
    watcher._maybe_run()

    assert store.started == [(settings, fid)]


def test_maybe_run_suppresses_concurrent_run_error(settings):
    """If another run is in flight, start_folder raises RuntimeError; the
    watcher must swallow it and try again on the next tick."""
    fid = _insert_folder(settings, watch_enabled=True)
    folder_path = settings.base_dir / "inbox/test"
    folder_path.mkdir(parents=True)
    _make_file(folder_path, "new.edi")

    store = _FakeRunStore(raise_on_start_folder=RuntimeError("run in progress"))
    watcher = FolderWatcher(settings, fid, store, interval_seconds=5)
    watcher._maybe_run()  # must not raise

    assert len(store.started) == 1


def test_maybe_run_handles_corrupt_database(settings):
    """A broken DB row read must not take down the tick; just skip."""
    fid = _insert_folder(settings, watch_enabled=True)
    folder_path = settings.base_dir / "inbox/test"
    folder_path.mkdir(parents=True)
    _make_file(folder_path, "new.edi")

    # Break the database so open_database/find_one fails.
    import sqlite3

    db = open_database(settings)
    db.close()
    con = sqlite3.connect(str(settings.database_path))
    con.execute("DROP TABLE folders")
    con.commit()
    con.close()

    store = _FakeRunStore()
    watcher = FolderWatcher(settings, fid, store, interval_seconds=5)
    watcher._maybe_run()  # must not raise

    assert store.started == []


# ---------------------------------------------------------------------------
# Phase 5.2 watcher health (last_tick_at / last_run_id / last_error)
# ---------------------------------------------------------------------------


def _read_health(settings, fid) -> dict:
    """Read the watcher-health columns straight off the folders row."""
    db = open_database(settings)
    try:
        row = db.folders_table.find_one(id=fid)
        return {
            "last_tick_at": row.get("last_tick_at", ""),
            "last_run_id": row.get("last_run_id", ""),
            "last_error": row.get("last_error", ""),
        }
    finally:
        db.close()


def test_list_watched_includes_health_fields(settings):
    fid = _insert_folder(
        settings,
        watch_enabled=True,
        last_tick_at="2026-08-12T14:00:00.000000",
        last_run_id="run-abc123",
        last_error="",
    )

    result = list_watched(settings)[0]

    assert result["id"] == fid
    assert result["last_tick_at"] == "2026-08-12T14:00:00.000000"
    assert result["last_run_id"] == "run-abc123"
    assert result["last_error"] == ""


def test_list_watched_health_fields_default_to_empty(settings):
    """Pre-5.2 rows (columns absent or NULL) report empty strings."""
    fid = _insert_folder(settings, watch_enabled=True)
    # Columns added by _ensure_columns default to ''.
    result = list_watched(settings)[0]

    assert result["id"] == fid
    assert result["last_tick_at"] == ""
    assert result["last_run_id"] == ""
    assert result["last_error"] == ""


def test_maybe_run_persists_health_on_healthy_tick(settings):
    """A tick that starts a run records the tick time + run id, no error."""
    fid = _insert_folder(settings, watch_enabled=True)
    folder_path = settings.base_dir / "inbox/test"
    folder_path.mkdir(parents=True)
    _make_file(folder_path, "new.edi")

    store = _FakeRunStore()
    watcher = FolderWatcher(settings, fid, store, interval_seconds=5)
    watcher._maybe_run()

    health = _read_health(settings, fid)
    assert health["last_tick_at"]
    assert health["last_run_id"] == "fake-run-id"
    assert health["last_error"] == ""


def test_maybe_run_keeps_last_run_id_across_noop_ticks(settings):
    """The run id survives later ticks that don't trigger a run, so the
    card keeps showing the most recent run the watcher started."""
    fid = _insert_folder(settings, watch_enabled=True)
    folder_path = settings.base_dir / "inbox/test"
    folder_path.mkdir(parents=True)
    _make_file(folder_path, "new.edi")

    store = _FakeRunStore()
    watcher = FolderWatcher(settings, fid, store, interval_seconds=5)
    watcher._maybe_run()
    assert _read_health(settings, fid)["last_run_id"] == "fake-run-id"

    # File is now processed (fake store records the run), so the next
    # tick is a no-op — but last_run_id must be preserved.
    watcher._maybe_run()
    health = _read_health(settings, fid)
    assert health["last_run_id"] == "fake-run-id"
    assert health["last_tick_at"]


def test_maybe_run_records_missing_folder_error(settings):
    """A watched folder whose directory vanished records last_error and a
    ledger row (phase 5.2) instead of failing silently."""
    fid = _insert_folder(settings, watch_enabled=True)
    # The configured directory is never created.

    store = _FakeRunStore()
    watcher = FolderWatcher(settings, fid, store, interval_seconds=5)
    watcher._maybe_run()

    assert store.started == []
    health = _read_health(settings, fid)
    assert health["last_tick_at"]
    assert "missing" in health["last_error"]

    # The failure lands in the error ledger, filterable by folder.
    db = open_database(settings)
    try:
        rows = list_errors(db, folder_id=fid)
    finally:
        db.close()
    assert len(rows) == 1
    assert rows[0]["error_type"] == "WatcherScanError"
    assert rows[0]["error_source"] == "FolderWatcher"
    assert "missing" in rows[0]["error_message"]
    assert rows[0]["folder"].endswith("inbox/test")

    # The row links a raw error-text artifact the watcher wrote
    # (open question #2), named like the dispatch ones.
    artifact = rows[0]["error_file"]
    assert artifact, "scan-failure row should link its raw artifact"
    artifact_path = Path(artifact)
    assert artifact_path.is_file()
    assert artifact_path.parent == settings.errors_dir / "test"
    assert "TEST errors." in artifact_path.name
    raw = artifact_path.read_text(encoding="utf-8")
    assert "Error Message is:" in raw
    assert "missing" in raw


def test_maybe_run_writes_one_artifact_per_scan_error_episode(settings):
    """A repeating failure keeps one ledger row AND one artifact file —
    the second tick sees a dedupe match and must not orphan a new file."""
    fid = _insert_folder(settings, watch_enabled=True)
    store = _FakeRunStore()
    watcher = FolderWatcher(settings, fid, store, interval_seconds=5)

    watcher._maybe_run()
    watcher._maybe_run()  # same missing-folder error again

    db = open_database(settings)
    try:
        rows = list_errors(db, folder_id=fid)
    finally:
        db.close()
    assert len(rows) == 1
    assert rows[0]["error_file"], "first tick linked its artifact"
    assert Path(rows[0]["error_file"]).is_file()
    artifacts = list((settings.errors_dir / "test").glob("TEST errors.*.txt"))
    assert len(artifacts) == 1, "repeating failures must not write extra files"


def test_maybe_run_dedupes_repeated_scan_errors(settings):
    """A permanent failure keeps updating last_tick_at but writes only one
    ledger row instead of one per tick (phase 5.2 spam guard)."""
    fid = _insert_folder(settings, watch_enabled=True)
    # The configured directory is never created → same error every tick.

    store = _FakeRunStore()
    watcher = FolderWatcher(settings, fid, store, interval_seconds=5)
    watcher._maybe_run()
    first_tick = _read_health(settings, fid)["last_tick_at"]
    watcher._maybe_run()
    watcher._maybe_run()

    health = _read_health(settings, fid)
    assert health["last_tick_at"] >= first_tick  # still ticking
    assert "missing" in health["last_error"]
    db = open_database(settings)
    try:
        rows = list_errors(db, folder_id=fid)
    finally:
        db.close()
    assert len(rows) == 1


def test_maybe_run_records_scan_oserror(settings, monkeypatch):
    """An OSError while scanning the directory records the failure."""
    fid = _insert_folder(settings, watch_enabled=True)
    folder_path = settings.base_dir / "inbox/test"
    folder_path.mkdir(parents=True)
    _make_file(folder_path, "new.edi")

    def _deny(self):
        raise PermissionError("permission denied")

    monkeypatch.setattr("webapp.watcher.Path.iterdir", _deny)

    store = _FakeRunStore()
    watcher = FolderWatcher(settings, fid, store, interval_seconds=5)
    watcher._maybe_run()  # must not raise

    assert store.started == []
    health = _read_health(settings, fid)
    assert "permission denied" in health["last_error"]


def test_maybe_run_clears_last_error_on_recovery(settings):
    """A healthy tick after a failure clears last_error and re-enables runs."""
    fid = _insert_folder(settings, watch_enabled=True)
    folder_path = settings.base_dir / "inbox/test"
    # First tick: folder missing → error recorded.
    store = _FakeRunStore()
    watcher = FolderWatcher(settings, fid, store, interval_seconds=5)
    watcher._maybe_run()
    assert _read_health(settings, fid)["last_error"]

    # Operator recreates the directory with a file → healthy tick.
    folder_path.mkdir(parents=True)
    _make_file(folder_path, "new.edi")
    watcher._maybe_run()

    health = _read_health(settings, fid)
    assert health["last_error"] == ""
    assert health["last_run_id"] == "fake-run-id"
    assert store.started == [(settings, fid)]


# ---------------------------------------------------------------------------
# FolderWatcher lifecycle
# ---------------------------------------------------------------------------


def test_watcher_start_stop_lifecycle(settings):
    fid = _insert_folder(settings, watch_enabled=True)
    store = _FakeRunStore()
    watcher = FolderWatcher(settings, fid, store, interval_seconds=5)

    watcher.start()
    assert watcher._thread is not None
    assert watcher._thread.is_alive()

    # start() is idempotent — same thread, no duplicate.
    first = watcher._thread
    watcher.start()
    assert watcher._thread is first

    watcher.stop()
    assert not watcher._thread.is_alive()


def test_watcher_clamps_interval_to_minimum(settings):
    store = _FakeRunStore()
    watcher = FolderWatcher(settings, 1, store, interval_seconds=2)
    assert watcher._interval == MIN_INTERVAL_SECONDS


# ---------------------------------------------------------------------------
# WatcherSupervisor
# ---------------------------------------------------------------------------


def test_supervisor_starts_watchers_for_watched_folders(settings):
    fid = _insert_folder(settings, watch_enabled=True)
    sup = WatcherSupervisor(settings, _FakeRunStore())

    sup._refresh()

    assert fid in sup._watchers
    assert sup._watchers[fid]._thread is not None
    assert sup._watchers[fid]._thread.is_alive()
    sup.stop()


def test_supervisor_ignores_unwatched_folders(settings):
    _insert_folder(settings, watch_enabled=False)
    sup = WatcherSupervisor(settings, _FakeRunStore())

    sup._refresh()

    assert sup._watchers == {}
    sup.stop()


def test_supervisor_stops_watchers_when_watching_disabled(settings):
    fid = _insert_folder(settings, watch_enabled=True)
    sup = WatcherSupervisor(settings, _FakeRunStore())
    sup._refresh()
    assert fid in sup._watchers

    db = open_database(settings)
    db.folders_table.update({"id": fid, "watch_enabled": False}, ["id"])
    db.close()

    sup._refresh()
    assert fid not in sup._watchers
    sup.stop()


def test_supervisor_restarts_watcher_when_interval_changes(settings):
    fid = _insert_folder(settings, watch_enabled=True, watch_interval_seconds=30)
    sup = WatcherSupervisor(settings, _FakeRunStore())
    sup._refresh()
    first = sup._watchers[fid]

    db = open_database(settings)
    db.folders_table.update({"id": fid, "watch_interval_seconds": 120}, ["id"])
    db.close()

    sup._refresh()
    second = sup._watchers[fid]
    assert second is not first
    assert second._interval == 120
    sup.stop()


def test_supervisor_refresh_is_idempotent(settings):
    fid = _insert_folder(settings, watch_enabled=True, watch_interval_seconds=30)
    sup = WatcherSupervisor(settings, _FakeRunStore())

    sup._refresh()
    first = sup._watchers[fid]
    sup._refresh()

    assert sup._watchers[fid] is first
    sup.stop()


def test_supervisor_does_not_churn_on_sub_minimum_interval(settings):
    """A clamped interval must compare equal on the next refresh, so the
    supervisor doesn't stop/restart the watcher every cycle."""
    fid = _insert_folder(settings, watch_enabled=True, watch_interval_seconds=1)
    sup = WatcherSupervisor(settings, _FakeRunStore())

    sup._refresh()
    first = sup._watchers[fid]
    assert first._interval == MIN_INTERVAL_SECONDS

    sup._refresh()
    assert sup._watchers[fid] is first
    sup.stop()


def test_supervisor_stop_cleans_up_watchers(settings):
    _insert_folder(settings, watch_enabled=True)
    sup = WatcherSupervisor(settings, _FakeRunStore())
    sup._refresh()
    assert sup._watchers

    sup.stop()

    assert sup._watchers == {}


# ---------------------------------------------------------------------------
# End-to-end: supervisor → watcher thread → RunStore → dispatcher
# ---------------------------------------------------------------------------


def test_watcher_picks_up_new_file_end_to_end(tmp_path):
    """Real path: TestClient lifespan starts the supervisor, the watcher
    thread spots a new file and starts a real run, and the dispatcher
    records the file in processed_files and delivers it via the copy
    backend."""
    settings = Settings(
        base_dir=tmp_path / "data", data_dir=tmp_path / "data" / "config"
    )
    settings.ensure_dirs()
    inbox = settings.base_dir / "inbox" / "test"
    archive = settings.base_dir / "archive" / "test"
    inbox.mkdir(parents=True)
    archive.mkdir(parents=True)

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
            "watch_enabled": True,
            "watch_interval_seconds": 5,
            "created_at": datetime.datetime.now().isoformat(),
        }
    )
    db.close()

    app = create_app(settings=settings)
    with TestClient(app) as client:
        # Drop the file, then kick the supervisor so the change is
        # picked up without waiting for its 30s refresh loop.
        (inbox / "arrival.edi").write_bytes(b"HEADER line\nDETAIL line\n")
        client.post("/api/watcher/refresh")

        found = False
        for _ in range(50):  # up to ~10s: first tick is immediate, else +5s
            time.sleep(0.2)
            body = client.get("/api/processed-files").json()
            if any(
                (f.get("file_name") or "").endswith("arrival.edi")
                for f in body.get("files", [])
            ):
                found = True
                break
        assert found, "watcher never picked up the new file"
        # The copy backend delivered the file to the resolved destination.
        assert (archive / "arrival.edi").is_file()
