"""Run the dispatch pipeline over the webapp's active folders.

This is the Qt-free counterpart of the desktop app's "process directories"
flow: load active folder rows from the database, resolve their relative
paths against the base-dir, build a ``DispatchConfig`` with the standard
pipeline and the module-based send backends, and run every folder through
``DispatchOrchestrator``. Results are collected per folder, including the
run log, and returned (or stored for background polling).
"""

from __future__ import annotations

import contextlib
import dataclasses
import datetime
import io
import threading
import uuid
from typing import Any

from dispatch.error_handler import ErrorHandler
from dispatch.orchestrator import DispatchOrchestrator
from dispatch.pipeline.factory import create_standard_pipeline
from webapp.config import Settings
from webapp.database import lock, open_database
from webapp.paths import resolve_row


@dataclasses.dataclass
class FolderRunReport:
    """Result of processing one folder."""

    alias: str
    relative_path: str
    resolved_path: str
    files_processed: int = 0
    files_failed: int = 0
    success: bool = True
    errors: list[str] = dataclasses.field(default_factory=list)
    run_log: str = ""


@dataclasses.dataclass
class RunReport:
    """Aggregate result of a run across all active folders."""

    run_id: str
    status: str = "running"  # running | completed | failed
    started_at: str = ""
    finished_at: str = ""
    folders: list[FolderRunReport] = dataclasses.field(default_factory=list)
    total_processed: int = 0
    total_failed: int = 0
    error: str = ""


def _is_active(row: dict[str, Any]) -> bool:
    return str(row.get("folder_is_active", "")).lower() in ("1", "true", "yes")


def _folder_relative_path(row: dict[str, Any]) -> str:
    return str(row.get("folder_name", "") or "")


def _snapshot(report: RunReport) -> RunReport:
    """Copy a run report so readers never see a half-mutated run.

    ``RunStore`` hands out reports to the API while the worker thread is
    still appending folder results. A shallow copy is enough here: the
    per-folder reports are created once and then only read; only the
    aggregate counters/status/folders list change during the run.
    """
    snap = dataclasses.replace(report)
    snap.folders = list(report.folders)
    return snap


def run_folders(settings: Settings, db=None) -> RunReport:
    """Process every active folder synchronously.

    Args:
        settings: Webapp settings (base-dir, data-dir).
        db: Optional already-open ``DatabaseObj`` to use. When None, one
            is opened inside this call.

    Returns:
        A completed ``RunReport``.

    """
    report = RunReport(
        run_id=uuid.uuid4().hex[:12],
        status="running",
        started_at=datetime.datetime.now().isoformat(),
    )
    owns_db = db is None
    if owns_db:
        db = open_database(settings)

    try:
        with lock():
            settings.ensure_dirs()

            rows = list(db.folders_table.all()) if db.folders_table else []
            active = [r for r in rows if _is_active(r)]
            # Keep the original (relative) row for the report; hand the
            # dispatcher the resolved (absolute) copy.
            active_pairs = [(r, resolve_row(r, settings.base_dir)) for r in active]

            settings_dict = db.get_settings_or_default() or {}

            error_handler = ErrorHandler(
                errors_folder=str(settings.errors_dir),
                run_log_directory=str(settings.logs_dir),
            )
            config = create_standard_pipeline(
                settings=settings_dict,
                version="webapp",
                error_handler=error_handler,
                backends={},
                # Non-empty dict prevents the UPC lookup from trying to reach
                # the AS400 (the webapp runs without DB2/SSH access).
                upc_dict={"_mock": []},
            )
            orchestrator = DispatchOrchestrator(config)

            folder_total = len(active_pairs)
            for folder_num, (original_row, folder) in enumerate(active_pairs, start=1):
                run_log = io.StringIO()
                folder_report = FolderRunReport(
                    alias=str(
                        original_row.get("alias") or _folder_relative_path(original_row)
                    ),
                    relative_path=_folder_relative_path(original_row),
                    resolved_path=str(folder.get("folder_name", "")),
                )
                try:
                    result = orchestrator.process_folder(
                        folder,
                        run_log,
                        processed_files=db.processed_files,
                        folder_num=folder_num,
                        folder_total=folder_total,
                    )
                    folder_report.files_processed = result.files_processed
                    folder_report.files_failed = result.files_failed
                    folder_report.success = result.success
                    folder_report.errors = list(result.errors)
                except Exception as exc:
                    folder_report.success = False
                    folder_report.files_failed = 1
                    folder_report.errors.append(f"{type(exc).__name__}: {exc}")
                folder_report.run_log = run_log.getvalue()
                report.folders.append(folder_report)
                report.total_processed += folder_report.files_processed
                report.total_failed += folder_report.files_failed

            report.status = "completed"
    except Exception as exc:
        report.status = "failed"
        report.error = f"{type(exc).__name__}: {exc}"
    finally:
        if owns_db:
            with contextlib.suppress(Exception):
                db.close()
        report.finished_at = datetime.datetime.now().isoformat()

    return report


def run_resend(settings: Settings, db=None) -> RunReport:
    """Re-process every row whose resend_flag is set, scoped per folder.

    Behaviour:
    1. Collect every flagged row.
    2. Group by folder_id.
    3. For each folder: delete the flagged rows (so the dispatcher
       doesn't see them as already-processed), then call the
       orchestrator with ``pre_discovered_files`` set to the
       row's stored file paths. The dispatcher will then validate,
       convert, and re-send them like a fresh run.
    4. The deleted rows are replaced by new processed-files rows
       written by the dispatcher (with fresh resend_flag=False).

    Args:
        settings: Webapp settings.
        db: Optional already-open ``DatabaseObj``.

    Returns:
        A ``RunReport`` with one FolderRunReport per folder that
        had at least one flagged row.

    """
    from webapp.resend import delete_processed_rows, list_processed_files

    report = RunReport(
        run_id=uuid.uuid4().hex[:12],
        status="running",
        started_at=datetime.datetime.now().isoformat(),
    )
    owns_db = db is None
    if owns_db:
        db = open_database(settings)

    try:
        with lock():
            settings.ensure_dirs()
            flagged = list_processed_files(
                db, only_resend_flagged=True, limit=10000
            )
            if not flagged:
                report.status = "completed"
                report.finished_at = datetime.datetime.now().isoformat()
                return report

            # Group by folder_id.
            by_folder: dict[int, list[dict]] = {}
            for row in flagged:
                by_folder.setdefault(row["folder_id"], []).append(row)

            folders_by_id = {
                r["id"]: r for r in (db.folders_table.all() or [])
            }
            settings_dict = db.get_settings_or_default() or {}

            error_handler = ErrorHandler(
                errors_folder=str(settings.errors_dir),
                run_log_directory=str(settings.logs_dir),
            )
            config = create_standard_pipeline(
                settings=settings_dict,
                version="webapp",
                error_handler=error_handler,
                backends={},
                upc_dict={"_mock": []},
            )
            orchestrator = DispatchOrchestrator(config)

            folder_total = len(by_folder)
            for folder_num, (folder_id, rows) in enumerate(by_folder.items(), start=1):
                original_row = folders_by_id.get(folder_id)
                if original_row is None:
                    # Folder deleted but rows remain — drop them.
                    delete_processed_rows(db, [r["id"] for r in rows])
                    continue
                resolved = resolve_row(original_row, settings.base_dir)
                run_log = io.StringIO()
                folder_report = FolderRunReport(
                    alias=str(
                        original_row.get("alias") or _folder_relative_path(original_row)
                    ),
                    relative_path=_folder_relative_path(original_row),
                    resolved_path=str(resolved.get("folder_name", "")),
                )
                # Free the flagged rows so the dispatcher's checksum
                # dedup doesn't skip them.
                row_ids = [r["id"] for r in rows]
                delete_processed_rows(db, row_ids)
                file_paths = [
                    r["file_name"] for r in rows if r.get("file_name")
                ]
                try:
                    result = orchestrator.process_folder(
                        resolved,
                        run_log,
                        processed_files=db.processed_files,
                        pre_discovered_files=file_paths,
                        folder_num=folder_num,
                        folder_total=folder_total,
                    )
                    folder_report.files_processed = result.files_processed
                    folder_report.files_failed = result.files_failed
                    folder_report.success = result.success
                    folder_report.errors = list(result.errors)
                except Exception as exc:
                    folder_report.success = False
                    folder_report.files_failed = 1
                    folder_report.errors.append(f"{type(exc).__name__}: {exc}")
                folder_report.run_log = run_log.getvalue()
                report.folders.append(folder_report)
                report.total_processed += folder_report.files_processed
                report.total_failed += folder_report.files_failed

            report.status = "completed"
    except Exception as exc:
        report.status = "failed"
        report.error = f"{type(exc).__name__}: {exc}"
    finally:
        if owns_db:
            with contextlib.suppress(Exception):
                db.close()
        report.finished_at = datetime.datetime.now().isoformat()

    return report


def run_folder(settings: Settings, folder_id: int, db=None) -> RunReport:
    """Process a single folder by id (background worker; same shape as run_folders).

    The folder is loaded fresh from the DB on every call so a stale
    in-memory copy doesn't bypass a recent PUT /api/folders/{id} save.

    Args:
        settings: Webapp settings.
        folder_id: Primary key in the folders table.
        db: Optional already-open ``DatabaseObj``.

    Returns:
        A ``RunReport`` with exactly one ``FolderRunReport``.

    """
    report = RunReport(
        run_id=uuid.uuid4().hex[:12],
        status="running",
        started_at=datetime.datetime.now().isoformat(),
    )
    owns_db = db is None
    if owns_db:
        db = open_database(settings)
    try:
        with lock():
            settings.ensure_dirs()
            row = db.folders_table.find_one(id=folder_id)
            if row is None:
                raise ValueError(f"Folder {folder_id} not found")
            resolved = resolve_row(row, settings.base_dir)
            settings_dict = db.get_settings_or_default() or {}
            error_handler = ErrorHandler(
                errors_folder=str(settings.errors_dir),
                run_log_directory=str(settings.logs_dir),
            )
            config = create_standard_pipeline(
                settings=settings_dict,
                version="webapp",
                error_handler=error_handler,
                backends={},
                upc_dict={"_mock": []},
            )
            orchestrator = DispatchOrchestrator(config)
            run_log = io.StringIO()
            folder_report = FolderRunReport(
                alias=str(row.get("alias") or _folder_relative_path(row)),
                relative_path=_folder_relative_path(row),
                resolved_path=str(resolved.get("folder_name", "")),
            )
            try:
                result = orchestrator.process_folder(
                    resolved,
                    run_log,
                    processed_files=db.processed_files,
                )
                folder_report.files_processed = result.files_processed
                folder_report.files_failed = result.files_failed
                folder_report.success = result.success
                folder_report.errors = list(result.errors)
            except Exception as exc:
                folder_report.success = False
                folder_report.files_failed = 1
                folder_report.errors.append(f"{type(exc).__name__}: {exc}")
            folder_report.run_log = run_log.getvalue()
            report.folders.append(folder_report)
            report.total_processed = folder_report.files_processed
            report.total_failed = folder_report.files_failed
            report.status = "completed"
    except ValueError as exc:
        report.status = "failed"
        report.error = str(exc)
    except Exception as exc:
        report.status = "failed"
        report.error = f"{type(exc).__name__}: {exc}"
    finally:
        if owns_db:
            with contextlib.suppress(Exception):
                db.close()
        report.finished_at = datetime.datetime.now().isoformat()
    return report


class RunStore:
    """In-memory store of background runs (single-user local webapp).

    A single-user internal tool doesn't need a queue, but it does need a
    guardrail: a fat-fingered double-click on "Process all folders" (or a
    stale 8-second poll loop firing POST /api/run twice) would otherwise
    spawn two simultaneous worker threads hammering the same SQLite
    database. The active-run counter refuses a second ``start()`` while a
    previous run is still in flight; the UI surfaces the rejection via the
    standard FastAPI 400 path.

    In-memory state is for the live view (a worker thread mutates a
    ``RunReport`` while the browser polls). On completion, each run is
    appended to the persistent ``RunHistory`` so /api/runs still shows
    recent runs after a container restart.
    """

    def __init__(self) -> None:
        self._runs: dict[str, RunReport] = {}
        self._lock = threading.Lock()
        self._active: int = 0
        self._history = None  # injected via attach_history

    def attach_history(self, history) -> None:
        """Inject the persistent RunHistory (called from main.py)."""
        self._history = history

    def _persist(self, report: RunReport, *, kind: str) -> None:
        if self._history is None:
            return
        with contextlib.suppress(Exception):
            self._history.append(report, kind=kind)

    @property
    def active_count(self) -> int:
        """Return the number of runs currently in flight."""
        with self._lock:
            return self._active

    def start(self, settings: Settings) -> str:
        """Start a background run and return its id immediately.

        Raises:
            RuntimeError: If a previous run is still in flight.
                (The caller maps that to HTTP 400.)
        """
        with self._lock:
            if self._active > 0:
                raise RuntimeError("A run is already in progress")
            self._active += 1
        run_id = uuid.uuid4().hex[:12]
        placeholder = RunReport(run_id=run_id, status="running")
        with self._lock:
            self._runs[run_id] = placeholder

        def _work() -> None:
            try:
                report = run_folders(settings)
                report.run_id = run_id
                with self._lock:
                    self._runs[run_id] = report
                self._persist(report, kind="normal")
            finally:
                with self._lock:
                    self._active -= 1

        threading.Thread(target=_work, name=f"webapp-run-{run_id}", daemon=True).start()
        return run_id

    def start_resend(self, settings: Settings) -> str:
        """Start a background resend run and return its id immediately.

        Same active-run guard as ``start()`` so a normal run and a
        resend can't be in flight at the same time.

        Raises:
            RuntimeError: If a previous run is still in flight.
        """
        with self._lock:
            if self._active > 0:
                raise RuntimeError("A run is already in progress")
            self._active += 1
        run_id = uuid.uuid4().hex[:12]
        placeholder = RunReport(run_id=run_id, status="running")
        with self._lock:
            self._runs[run_id] = placeholder

        def _work() -> None:
            try:
                report = run_resend(settings)
                report.run_id = run_id
                with self._lock:
                    self._runs[run_id] = report
                self._persist(report, kind="resend")
            finally:
                with self._lock:
                    self._active -= 1

        threading.Thread(
            target=_work, name=f"webapp-resend-{run_id}", daemon=True
        ).start()
        return run_id

    def start_folder(self, settings: Settings, folder_id: int) -> str:
        """Start a background single-folder run.

        Raises:
            RuntimeError: If a previous run is still in flight.
            ValueError: If the folder id doesn't exist.
        """
        with self._lock:
            if self._active > 0:
                raise RuntimeError("A run is already in progress")
            self._active += 1
        run_id = uuid.uuid4().hex[:12]
        placeholder = RunReport(run_id=run_id, status="running")
        with self._lock:
            self._runs[run_id] = placeholder

        def _work() -> None:
            try:
                report = run_folder(settings, folder_id)
                report.run_id = run_id
                with self._lock:
                    self._runs[run_id] = report
                self._persist(report, kind="folder")
            finally:
                with self._lock:
                    self._active -= 1

        threading.Thread(
            target=_work, name=f"webapp-folder-{run_id}", daemon=True
        ).start()
        return run_id

    def get(self, run_id: str) -> RunReport | None:
        """Return a snapshot of one run (safe to read while it runs)."""
        with self._lock:
            report = self._runs.get(run_id)
            return _snapshot(report) if report is not None else None

    def list(self) -> list[RunReport]:
        """Return snapshots of all runs (safe to read while they run)."""
        with self._lock:
            return [_snapshot(r) for r in self._runs.values()]
