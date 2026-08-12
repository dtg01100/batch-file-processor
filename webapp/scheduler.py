"""Background scheduler for the webapp.

Single-user, single-host; the scheduler is a daemon thread that wakes
up at a fixed interval, checks the persisted schedule in the
``kv_settings`` table, and runs the dispatcher if the schedule is
enabled. The interval is itself a setting so an operator can drop it
from the default of 60s to "every 5 minutes" without restarting the
container.

Settings persisted in kv_settings:

- ``webapp.schedule_enabled`` ("true"/"false"): master switch.
- ``webapp.schedule_interval_seconds`` ("60"): how often the scheduler
  considers running.
- ``webapp.schedule_last_run_at`` (ISO timestamp): when the scheduler
  last triggered a run. Used to compute "next run at" in the UI.
- ``webapp.schedule_runs_triggered`` (integer string): monotonic
  counter of scheduler-fired runs (phase 5.2).

The scheduler is intentionally simple:

- It does NOT keep its own state — restart-safety is handled by the
  in-flight check in ``RunStore`` (a second scheduler thread that
  fires while a run is in flight is a no-op).
- It does NOT retry on failure — the run's RunReport already shows
  the error.
- It does NOT schedule cron expressions — keep it simple, the
  interval is enough.

The scheduler thread is started from ``create_app`` lifespan hooks.
"""

from __future__ import annotations

import contextlib
import datetime
import threading
from typing import Any

from webapp.config import Settings
from webapp.database import open_database
from webapp.runner import RunStore

SCHEDULE_ENABLED_KEY = "webapp.schedule_enabled"
SCHEDULE_INTERVAL_KEY = "webapp.schedule_interval_seconds"
SCHEDULE_LAST_RUN_KEY = "webapp.schedule_last_run_at"
SCHEDULE_RUNS_KEY = "webapp.schedule_runs_triggered"

DEFAULT_INTERVAL_SECONDS = 60
MIN_INTERVAL_SECONDS = 5
MAX_INTERVAL_SECONDS = 24 * 60 * 60  # one day, hard ceiling


class Scheduler:
    """Background thread that triggers ``RunStore.start`` periodically.

    The thread is started exactly once per process. ``start()`` is
    idempotent — calling it twice from the FastAPI lifespan hooks is
    safe. ``stop()`` is called on shutdown to drain the thread.
    """

    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.Lock()

    def start(self) -> None:
        """Start the scheduler thread if not already running."""
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = threading.Thread(
                target=self._run_loop,
                name="webapp-scheduler",
                daemon=True,
            )
            self._thread.start()

    def stop(self) -> None:
        """Signal the thread to exit and wait briefly for it."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def _run_loop(self) -> None:
        """Sleep, then check whether a run is due. Repeat forever."""
        while not self._stop.is_set():
            try:
                interval = self._maybe_run()
            except Exception:
                # Don't let an exception in the scheduler take down the
                # thread. Log and continue with the default interval.
                interval = DEFAULT_INTERVAL_SECONDS
            # ``stop.wait`` returns True if the event was set during the
            # sleep, so shutdown is prompt.
            if self._stop.wait(timeout=interval):
                return

    def _maybe_run(self) -> int:
        """Run the dispatcher if the schedule is enabled.

        Returns:
            The number of seconds the scheduler should sleep before
            considering the next run.

        """
        settings = self._current_settings()
        if settings is None:
            return DEFAULT_INTERVAL_SECONDS
        enabled, interval = read_schedule_state(settings)
        if not enabled:
            return interval
        # Try to start a run. RunStore.start refuses if a run is
        # already in flight; we treat that as a no-op and retry on
        # the next interval.
        try:
            run_store = self._run_store
            if run_store is None or not run_store.active_count:
                run_store.start(settings)
                write_last_run(settings)
                # Phase 5.2: the monotonic counter tracks how many runs
                # the scheduler has fired since the database was
                # imported (kv_settings, so it survives restarts).
                increment_runs_triggered(settings)
        except RuntimeError:
            # Another run is in flight; try again later.
            pass
        return interval

    # The RunStore is injected by ``attach_run_store`` once the app
    # has built it. Until then the scheduler is a no-op.
    _run_store: RunStore | None = None

    def attach_run_store(self, store: RunStore) -> None:
        self._run_store = store

    @staticmethod
    def _current_settings() -> Settings | None:
        """Return the scheduler's configured settings, or build from env.

        Tests pass settings via ``configure_settings``; in production
        the scheduler reads from the env. The fallback covers the
        case where the test didn't configure settings.
        """
        if Scheduler._injected_settings is not None:
            return Scheduler._injected_settings
        try:
            return Settings.from_env()
        except Exception:
            return None

    _injected_settings: Settings | None = None

    @classmethod
    def configure_settings(cls, settings: Settings | None) -> None:
        """Inject settings for tests (call with None to clear)."""
        cls._injected_settings = settings


# ---------------------------------------------------------------------------
# Helpers (also called from the HTTP endpoints below)
# ---------------------------------------------------------------------------


def read_schedule_state(settings: Settings) -> tuple[bool, int]:
    """Return ``(enabled, interval_seconds)`` from the database.

    Falls back to (False, default) when the DB isn't migrated yet or
    the keys aren't present — this lets the scheduler thread start
    before a database has been imported.
    """
    try:
        settings.ensure_dirs()
        db = open_database(settings)
    except Exception:
        return False, DEFAULT_INTERVAL_SECONDS
    try:
        try:
            enabled_raw = db.get_setting(SCHEDULE_ENABLED_KEY) or ""
            interval_raw = db.get_setting(SCHEDULE_INTERVAL_KEY) or ""
        except Exception:
            return False, DEFAULT_INTERVAL_SECONDS
    finally:
        with contextlib.suppress(Exception):
            db.close()
    enabled = enabled_raw.lower() in ("1", "true", "yes")
    try:
        interval = int(interval_raw)
    except (TypeError, ValueError):
        interval = DEFAULT_INTERVAL_SECONDS
    interval = max(MIN_INTERVAL_SECONDS, min(MAX_INTERVAL_SECONDS, interval))
    return enabled, interval


def write_schedule_state(settings: Settings, *, enabled: bool, interval: int) -> None:
    """Persist ``enabled`` and ``interval`` in kv_settings."""
    settings.ensure_dirs()
    db = open_database(settings)
    try:
        kv = db.kv_settings
        kv.upsert(
            {"key": SCHEDULE_ENABLED_KEY, "value": ("true" if enabled else "false")},
            ["key"],
        )
        bounded = max(
            MIN_INTERVAL_SECONDS, min(MAX_INTERVAL_SECONDS, int(interval))
        )
        kv.upsert(
            {"key": SCHEDULE_INTERVAL_KEY, "value": str(bounded)},
            ["key"],
        )
    finally:
        db.close()


def write_last_run(settings: Settings) -> None:
    """Stamp the scheduler's last-fired time."""
    settings.ensure_dirs()
    db = open_database(settings)
    try:
        kv = db.kv_settings
        now_iso = datetime.datetime.now().isoformat()
        kv.upsert(
            {"key": SCHEDULE_LAST_RUN_KEY, "value": now_iso},
            ["key"],
        )
    finally:
        db.close()


def increment_runs_triggered(settings: Settings) -> None:
    """Bump the scheduler's monotonic run counter (kv_settings).

    Phase 5.2: the Schedule card shows how many runs the scheduler has
    fired. The counter is persisted in ``kv_settings`` so it survives
    scheduler-thread restarts; a missing or corrupt value counts as 0.
    """
    settings.ensure_dirs()
    db = open_database(settings)
    try:
        kv = db.kv_settings
        current = db.get_setting(SCHEDULE_RUNS_KEY) or "0"
        try:
            count = int(current)
        except (TypeError, ValueError):
            count = 0
        kv.upsert(
            {"key": SCHEDULE_RUNS_KEY, "value": str(count + 1)},
            ["key"],
        )
    finally:
        db.close()


def get_schedule_summary(settings: Settings) -> dict[str, Any]:
    """Read everything needed to render the schedule UI section."""
    enabled, interval = read_schedule_state(settings)
    last_run = ""
    runs_triggered = 0
    if settings.database_path.is_file():
        try:
            db = open_database(settings)
            try:
                last_run = db.get_setting(SCHEDULE_LAST_RUN_KEY) or ""
                raw_runs = db.get_setting(SCHEDULE_RUNS_KEY) or "0"
                try:
                    runs_triggered = int(raw_runs)
                except (TypeError, ValueError):
                    runs_triggered = 0
            finally:
                db.close()
        except Exception:
            pass
    next_run = ""
    if last_run:
        try:
            ts = datetime.datetime.fromisoformat(last_run)
            next_run = (ts + datetime.timedelta(seconds=interval)).isoformat()
        except ValueError:
            next_run = ""
    return {
        "enabled": enabled,
        "interval_seconds": interval,
        "last_run_at": last_run,
        "next_run_at": next_run,
        "runs_triggered": runs_triggered,
    }


__all__ = [
    "DEFAULT_INTERVAL_SECONDS",
    "MAX_INTERVAL_SECONDS",
    "MIN_INTERVAL_SECONDS",
    "Scheduler",
    "get_schedule_summary",
    "increment_runs_triggered",
    "read_schedule_state",
    "write_last_run",
    "write_schedule_state",
]
