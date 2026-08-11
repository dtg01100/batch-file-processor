"""Folder watcher: poll a single folder's input dir and run it on demand.

The watcher is intentionally simple: a thread per folder that
sleeps for ``interval_seconds``, scans the input directory for new
files (anything not yet in ``processed_files``), and runs the
dispatcher against any new arrivals.

Scope trade-offs:

- We don't watch filesystems with inotify — the webapp's
  deployment is single-host, single-user, and polling every 30
  seconds is cheap.
- We don't try to be clever about partial writes; if a file is
  mid-write, the dispatcher's own checksum dedup will re-process
  it on the next tick.
- The watcher respects the same active-run guard as the rest of
  the run-store: if a manual run starts mid-tick, the watcher
  skips that tick.

Per-folder settings live in ``webapp.watcher_state`` (a JSON
column is overkill; we just use the folders table directly):
"""

from __future__ import annotations

import contextlib
import threading
from pathlib import Path
from typing import Any

from webapp.config import Settings
from webapp.database import lock, open_database
from webapp.runner import RunStore

# Default poll interval when a folder doesn't override it.
DEFAULT_INTERVAL_SECONDS = 30
# How many files per tick to process. A burst arrival shouldn't
# make one watcher tick hold the dispatcher for an hour.
MAX_FILES_PER_TICK = 200
# Don't bother processing files smaller than this — they're
# almost certainly being written.
MIN_FILE_BYTES = 1


def list_watched(settings: Settings) -> list[dict[str, Any]]:
    """Return the list of folders with ``watch_enabled = 1``.

    The result is suitable for the API: each entry has the folder
    id, alias, resolved path, and the polling interval (in
    seconds)."""
    out: list[dict[str, Any]] = []
    with contextlib.suppress(Exception):
        settings.ensure_dirs()
        db = open_database(settings)
        try:
            for row in db.folders_table.all() or []:
                if str(row.get("watch_enabled", "")).lower() not in (
                    "1",
                    "true",
                    "yes",
                ):
                    continue
                try:
                    raw_interval = row.get("watch_interval_seconds")
                    interval = int(raw_interval or DEFAULT_INTERVAL_SECONDS)
                except (TypeError, ValueError):
                    interval = DEFAULT_INTERVAL_SECONDS
                out.append(
                    {
                        "id": row["id"],
                        "alias": row.get("alias", ""),
                        "watch_enabled": True,
                        "watch_interval_seconds": interval,
                        "watch_path": str(
                            (settings.base_dir / row.get("folder_name", "")).resolve()
                        )
                        if row.get("folder_name")
                        else "",
                    }
                )
        finally:
            with contextlib.suppress(Exception):
                db.close()
    return out


class FolderWatcher:
    """Per-folder watcher thread."""

    def __init__(
        self,
        settings: Settings,
        folder_id: int,
        run_store: RunStore,
        interval_seconds: int,
    ) -> None:
        self._settings = settings
        self._folder_id = folder_id
        self._run_store = run_store
        self._interval = max(5, int(interval_seconds))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop,
            name=f"webapp-watcher-folder-{self._folder_id}",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def _loop(self) -> None:
        while not self._stop.is_set():
            with contextlib.suppress(Exception):
                # Don't let an exception in the watcher kill the
                # thread; just try again on the next tick.
                self._maybe_run()
            if self._stop.wait(timeout=self._interval):
                return

    def _maybe_run(self) -> None:  # noqa: C901 - intentional complexity
        """Scan the folder and start a run if there are new files."""
        settings = self._settings
        try:
            settings.ensure_dirs()
            with lock():
                db = open_database(settings)
                try:
                    row = db.folders_table.find_one(id=self._folder_id)
                    if row is None:
                        return
                    # If the operator disabled watching since the
                    # thread was scheduled, exit.
                    if str(row.get("watch_enabled", "")).lower() not in (
                        "1",
                        "true",
                        "yes",
                    ):
                        return
                    rel = row.get("folder_name") or ""
                    if not rel:
                        return
                    folder_path = settings.base_dir / rel
                    if not folder_path.is_dir():
                        return
                    already = {
                        Path(r.get("file_name", "")).name
                        for r in db.processed_files.find(folder_id=self._folder_id)
                    }
                finally:
                    db.close()
        except Exception:
            return

        try:
            candidates = []
            for entry in folder_path.iterdir():
                if not entry.is_file():
                    continue
                if entry.stat().st_size < MIN_FILE_BYTES:
                    continue
                if entry.name in already:
                    continue
                candidates.append(entry)
        except OSError:
            return

        if not candidates:
            return
        # Truncate to MAX_FILES_PER_TICK so one tick can't get
        # stuck processing forever.
        if len(candidates) > MAX_FILES_PER_TICK:
            candidates = candidates[:MAX_FILES_PER_TICK]
        # Only start a run if no other run is in flight.
        with contextlib.suppress(RuntimeError):
            # Another run is in progress; try again on the next tick.
            self._run_store.start_folder(settings, self._folder_id)


class WatcherSupervisor:
    """Owns a watcher thread per folder with watch_enabled = 1.

    Started from the FastAPI lifespan; restarts each watcher when
    its folder is updated or every poll interval (whichever comes
    first).
    """

    def __init__(self, settings: Settings, run_store: RunStore) -> None:
        self._settings = settings
        self._run_store = run_store
        self._watchers: dict[int, FolderWatcher] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._stop.clear()
        self._refresh()
        self._thread = threading.Thread(
            target=self._supervisor_loop,
            name="webapp-watcher-supervisor",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        with self._lock:
            for w in list(self._watchers.values()):
                w.stop()
            self._watchers.clear()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def _refresh(self) -> None:
        """Re-read the watch list and start/stop watchers as needed."""
        wanted = {f["id"]: f for f in list_watched(self._settings)}
        with self._lock:
            current = set(self._watchers)
            wanted_ids = set(wanted)
            # Stop watchers for folders no longer watched.
            for fid in current - wanted_ids:
                self._watchers[fid].stop()
                del self._watchers[fid]
            # Start new watchers.
            for fid, info in wanted.items():
                if (
                    fid in self._watchers
                    and self._watchers[fid]._interval == info["watch_interval_seconds"]
                ):
                    continue
                if fid in self._watchers:
                    self._watchers[fid].stop()
                    del self._watchers[fid]
                self._watchers[fid] = FolderWatcher(
                    self._settings,
                    fid,
                    self._run_store,
                    info["watch_interval_seconds"],
                )
                self._watchers[fid].start()

    def _supervisor_loop(self) -> None:
        while not self._stop.is_set():
            # Refresh every 30s so toggles pick up quickly.
            self._refresh()
            if self._stop.wait(timeout=30):
                return


__all__ = [
    "DEFAULT_INTERVAL_SECONDS",
    "MAX_FILES_PER_TICK",
    "FolderWatcher",
    "WatcherSupervisor",
    "list_watched",
]
