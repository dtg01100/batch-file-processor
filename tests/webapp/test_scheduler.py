"""Tests for the webapp scheduler."""

from __future__ import annotations

import datetime
import time

import pytest

from webapp.config import Settings
from webapp.database import open_database
from webapp.scheduler import (
    DEFAULT_INTERVAL_SECONDS,
    MIN_INTERVAL_SECONDS,
    Scheduler,
    get_schedule_summary,
    read_schedule_state,
    write_last_run,
    write_schedule_state,
)

pytestmark = [pytest.mark.integration]


@pytest.fixture
def settings(tmp_path):
    s = Settings(base_dir=tmp_path / "data", data_dir=tmp_path / "data" / "config")
    s.ensure_dirs()
    # Seed a folders row so the scheduler's "try a run" path has
    # something to chew on without crashing.
    db = open_database(s)
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
    return s


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def test_read_returns_disabled_when_nothing_persisted(settings):
    enabled, interval = read_schedule_state(settings)
    assert enabled is False
    assert interval == DEFAULT_INTERVAL_SECONDS


def test_write_then_read_round_trips(settings):
    write_schedule_state(settings, enabled=True, interval=300)
    enabled, interval = read_schedule_state(settings)
    assert enabled is True
    assert interval == 300


def test_write_clamps_interval_to_minimum(settings):
    write_schedule_state(settings, enabled=True, interval=1)
    _enabled, interval = read_schedule_state(settings)
    assert interval == MIN_INTERVAL_SECONDS


def test_write_clamps_interval_to_maximum(settings):
    write_schedule_state(settings, enabled=True, interval=10**9)
    _enabled, interval = read_schedule_state(settings)
    # 1 day ceiling
    assert interval == 24 * 60 * 60


def test_get_schedule_summary_includes_next_run(settings):
    write_schedule_state(settings, enabled=True, interval=60)
    write_last_run(settings)
    summary = get_schedule_summary(settings)
    assert summary["enabled"] is True
    assert summary["interval_seconds"] == 60
    assert summary["last_run_at"] != ""
    assert summary["next_run_at"] != ""


def test_get_schedule_summary_tolerates_missing_db(settings):
    """Even before a database is imported, the summary endpoint works."""
    settings.database_path.unlink(missing_ok=True)
    summary = get_schedule_summary(settings)
    assert summary["enabled"] is False


def test_read_returns_disabled_when_db_corrupt(settings, tmp_path):
    """A corrupt settings row should not raise; just default to disabled."""
    # Force open_database to migrate first, then we'll corrupt the
    # kv_settings table.
    db = open_database(settings)
    db.close()
    # Drop and recreate the kv_settings table to make the read fail.
    import sqlite3
    con = sqlite3.connect(str(settings.database_path))
    con.execute("DROP TABLE kv_settings")
    con.commit()
    con.close()
    enabled, _interval = read_schedule_state(settings)
    assert enabled is False


# ---------------------------------------------------------------------------
# Scheduler thread
# ---------------------------------------------------------------------------


def test_scheduler_starts_and_stops(settings):
    sched = Scheduler()
    sched.attach_run_store(_FakeRunStore())
    sched.start()
    assert sched._thread is not None
    assert sched._thread.is_alive()
    sched.stop()
    # Wait briefly for the thread to exit.
    for _ in range(20):
        if not sched._thread.is_alive():
            break
        time.sleep(0.05)
    assert not sched._thread.is_alive()


def test_scheduler_start_is_idempotent(settings):
    sched = Scheduler()
    sched.attach_run_store(_FakeRunStore())
    sched.start()
    first_thread = sched._thread
    sched.start()
    # Same thread, not a second one.
    assert sched._thread is first_thread
    sched.stop()


def test_scheduler_skips_run_when_disabled(settings):
    """With the schedule disabled, no run is started."""
    sched = Scheduler()
    store = _FakeRunStore()
    sched.attach_run_store(store)
    # Schedule is disabled by default.
    result = sched._maybe_run()
    assert result == DEFAULT_INTERVAL_SECONDS
    assert store.start_count == 0


def test_scheduler_starts_run_when_enabled(settings):
    write_schedule_state(settings, enabled=True, interval=60)
    sched = Scheduler()
    store = _FakeRunStore()
    sched.attach_run_store(store)
    Scheduler.configure_settings(settings)
    try:
        sched._maybe_run()
        assert store.start_count == 1
    finally:
        Scheduler.configure_settings(None)


def test_scheduler_does_not_start_a_second_concurrent_run(settings):
    write_schedule_state(settings, enabled=True, interval=60)
    sched = Scheduler()
    store = _FakeRunStore(raise_on_start=RuntimeError("already in progress"))
    sched.attach_run_store(store)
    Scheduler.configure_settings(settings)
    try:
        # Should not propagate the RuntimeError.
        sched._maybe_run()
        assert store.start_count == 1  # only the first attempt counted
    finally:
        Scheduler.configure_settings(None)


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class _FakeRunStore:
    def __init__(self, *, raise_on_start: Exception | None = None):
        self._raise = raise_on_start
        self.start_count = 0

    @property
    def active_count(self) -> int:
        return 0

    def start(self, settings):
        self.start_count += 1
        if self._raise is not None:
            raise self._raise
        return "fake-run-id"
