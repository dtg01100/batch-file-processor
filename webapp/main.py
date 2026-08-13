"""FastAPI application for the Batch File Sender webapp.

Run with::

    BFS_BASE_DIR=./data python -m webapp.main
    # or
    uvicorn webapp.main:app --host 0.0.0.0 --port 8000

Endpoints
---------
- ``GET  /``                      browser UI (static files)
- ``GET  /api/health``            liveness + data dirs
- ``GET  /api/config``            base-dir / data-dir / platform
- ``POST /api/import``            multipart: file (legacy folders.db),
                                  base_dir (optional), platform (optional)
- ``POST /api/preview/edi``       classify an EDI upload (parse-only preview)
- ``GET  /api/folders``           configured folders (relative + resolved)
- ``GET  /api/folders/{id}``      one folder (full edit schema)
- ``PUT  /api/folders/{id}``      save one folder
- ``POST /api/run``               start a background run
- ``POST /api/resend``            start a background resend run
- ``POST /api/folders/{id}/run``  run one folder
- ``GET  /api/runs``              recent runs
- ``GET  /api/runs/{run_id}``     one run (poll this while running)
- ``GET  /api/runs/{run_id}/log`` SSE stream of the run's per-folder logs
- ``GET  /api/processed-files``   recently processed files
- ``GET  /api/processed-files/flagged``  same, with resend_flag info
- ``POST /api/processed-files/{id}/resend``  flag a row for resend
- ``POST /api/processed-files/resend-batch``  flag many rows
- ``POST /api/processed-files/clear-flags``   clear every resend flag
- ``POST /api/maintenance/clear-processed``   bulk-delete processed rows
- ``POST /api/maintenance/mark-processed``    record a single file as processed
- ``POST /api/maintenance/export-processed``  write CSV report
- ``GET  /api/maintenance/download``          download a previously-written report
- ``GET  /api/schedule``           current schedule state
- ``POST /api/schedule``           enable/disable the scheduler + set interval
- ``GET  /api/watched``            watched folders + live watcher health
- ``POST /api/watcher/refresh``    force the watcher supervisor to re-read
- ``GET  /api/errors``             error-ledger rows + per-folder counts
- ``GET  /api/errors/file``        download a raw error-text artifact
- ``GET  /api/errors/folder-file`` download one folder's full error text
- ``POST /api/errors/clear``       delete error-ledger rows
- ``GET  /api/backups``            list timestamped backup files
- ``POST /api/backup/create``      snapshot the active DB
- ``POST /api/backup/restore``     restore a named backup as the active DB
- ``GET  /api/backup/download``    download a backup file
"""

from __future__ import annotations

import contextlib
import platform as _platform
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from core.domain.models.folder import FolderConfiguration
from core.structured_logging import get_logger
from webapp.backup import (
    list_backups,
    make_backup,
    restore_backup,
)
from webapp.config import Settings
from webapp.database import get_base_directory, get_source_platform, lock, open_database
from webapp.errors import (
    clear_errors,
    error_counts,
    folder_error_text,
    list_errors,
)
from webapp.folder_schema import (
    FolderEditSchema,
    folder_row_to_schema,
    schema_to_folder_row,
)
from webapp.history import RunHistory
from webapp.importer import ImportResult, import_database
from webapp.maintenance import (
    clear_processed_files,
    export_processed_report,
    mark_file_processed,
)
from webapp.paths import resolve
from webapp.preview import preview_edi
from webapp.resend import (
    clear_resend_flags,
    list_processed_files,
    set_resend_flag,
    set_resend_flag_batch,
)
from webapp.runner import RunReport, RunStore
from webapp.scheduler import (
    Scheduler,
    get_schedule_summary,
    write_schedule_state,
)
from webapp.watcher import WatcherSupervisor, list_watched

STATIC_DIR = Path(__file__).parent / "static"

logger = get_logger(__name__)

_run_store = RunStore()
_history: RunHistory | None = None
_scheduler = Scheduler()
_watcher_supervisor: WatcherSupervisor | None = None


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    """Start/stop the background scheduler + folder watcher."""
    global _history, _watcher_supervisor
    settings = _app.state.settings
    _history = RunHistory(settings)
    _run_store.attach_history(_history)
    _scheduler.attach_run_store(_run_store)
    _scheduler.start()
    _watcher_supervisor = WatcherSupervisor(settings, _run_store)
    _watcher_supervisor.start()
    try:
        yield
    finally:
        _scheduler.stop()
        if _watcher_supervisor is not None:
            _watcher_supervisor.stop()


def _folder_summary(row: dict, base_dir: str) -> dict:
    """Build the API representation of a folder row."""
    relative = str(row.get("folder_name") or "")
    resolved = resolve(base_dir, relative)
    backends = [
        name
        for name, key in (
            ("copy", "process_backend_copy"),
            ("ftp", "process_backend_ftp"),
            ("email", "process_backend_email"),
            ("http", "process_backend_http"),
        )
        if str(row.get(key, "")).lower() in ("1", "true")
    ]
    return {
        "id": row.get("id"),
        "folder_name": relative,
        "resolved_path": resolved,
        "path_exists": bool(resolved) and Path(resolved).is_dir(),
        "alias": row.get("alias") or "",
        "is_active": str(row.get("folder_is_active", "")).lower() in ("1", "true"),
        "backends": backends,
    }


def _config_payload(settings: Settings) -> dict:
    """Build the /api/config payload, tolerating a missing/corrupt DB."""
    source_platform = ""
    stored_base = ""
    folders_count = 0
    active_count = 0
    try:
        with lock():
            db = open_database(settings)
            with contextlib.suppress(Exception):
                source_platform = get_source_platform(db)
                stored_base = get_base_directory(db, settings)
                rows = list(db.folders_table.all()) if db.folders_table else []
                folders_count = len(rows)
                active_count = sum(
                    1
                    for r in rows
                    if str(r.get("folder_is_active", "")).lower() in ("1", "true")
                )
            with contextlib.suppress(Exception):
                db.close()
    except Exception:
        # A missing/corrupt database should not take down /api/config;
        # the payload already reports database_exists=False. Log for
        # operators instead of failing the endpoint.
        logger.debug("api/config tolerated an unreadable database", exc_info=True)
    return {
        "base_dir": str(settings.base_dir),
        "data_dir": str(settings.data_dir),
        "database_exists": settings.database_path.is_file(),
        "imported_base_dir": stored_base,
        "source_platform": source_platform,
        "folders_count": folders_count,
        "active_count": active_count,
    }


def _run_summary(report: RunReport, *, include_log: bool = False) -> dict:
    """Serialize a RunReport for the API (folder detail + optional log)."""
    data = {
        "run_id": report.run_id,
        "status": report.status,
        "started_at": report.started_at,
        "finished_at": report.finished_at,
        "total_processed": report.total_processed,
        "total_failed": report.total_failed,
        "error": report.error,
        # Phase 5.3: computed at completion (0.0 on the running placeholder).
        "duration_seconds": report.duration_seconds,
        "files_per_second": report.files_per_second,
        "folders": [
            {
                "alias": f.alias,
                "relative_path": f.relative_path,
                "resolved_path": f.resolved_path,
                "files_processed": f.files_processed,
                "files_failed": f.files_failed,
                "success": f.success,
                "errors": f.errors,
            }
            for f in report.folders
        ],
    }
    if include_log:
        data["run_log"] = "\n".join(f.run_log for f in report.folders)
    return data


def dataclass_to_dict(result: ImportResult) -> dict:
    return {
        "folders_imported": result.folders_imported,
        "active_folders": result.active_folders,
        "rebased_paths": result.rebased_paths,
        "source_platform": result.source_platform,
        "database_path": result.database_path,
        "base_directory": result.base_directory,
    }


def create_app(  # noqa: C901 - flat endpoint registry, linear on purpose
    settings: Settings | None = None,
) -> FastAPI:
    """Build the FastAPI app. ``settings`` is injectable for tests."""
    app = FastAPI(title="Batch File Sender", version="0.1.0", lifespan=_lifespan)
    app.state.settings = settings or Settings.from_env()
    app.state.run_store = _run_store

    @app.get("/api/health")
    def health() -> dict:
        settings = app.state.settings
        settings.ensure_dirs()
        return {
            "status": "ok",
            "base_dir": str(settings.base_dir),
            "data_dir": str(settings.data_dir),
            "database_exists": settings.database_path.is_file(),
            "platform": _platform.system(),
        }

    @app.get("/api/config")
    def config() -> dict:
        return _config_payload(app.state.settings)

    @app.post("/api/import")
    async def api_import(
        file: Annotated[UploadFile, File()],
        base_dir: Annotated[str | None, Form()] = None,
        platform: Annotated[str | None, Form()] = None,
    ) -> dict:
        settings = app.state.settings
        suffix = Path(file.filename or "folders.db").suffix or ".db"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
        try:
            result: ImportResult = import_database(
                tmp_path,
                settings,
                base_dir=base_dir or None,
                platform=platform or None,
            )
            return dataclass_to_dict(result)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=500, detail=f"Import failed: {exc}"
            ) from exc
        finally:
            with contextlib.suppress(Exception):
                Path(tmp_path).unlink(missing_ok=True)

    @app.post("/api/preview/edi")
    async def api_preview_edi(file: Annotated[UploadFile, File()]) -> dict:
        """Classify an EDI upload and return per-line structure.

        This is a parse-only preview; the full conversion pipeline
        (which writes its output to disk and needs UPC + DB2) is
        not run here.
        """
        suffix = Path(file.filename or "sample.edi").suffix or ".edi"
        with tempfile.NamedTemporaryFile(
            suffix=suffix, delete=False, mode="w+b"
        ) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
        try:
            return preview_edi(tmp_path)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="File not found") from exc
        finally:
            with contextlib.suppress(Exception):
                Path(tmp_path).unlink(missing_ok=True)

    @app.get("/api/folders")
    def api_folders() -> list[dict]:
        settings = app.state.settings
        try:
            with lock():
                db = open_database(settings)
                with contextlib.suppress(Exception):
                    rows = list(db.folders_table.all()) if db.folders_table else []
                with contextlib.suppress(Exception):
                    db.close()
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return [_folder_summary(r, str(settings.base_dir)) for r in rows]

    @app.get("/api/folders/{folder_id}", response_model=FolderEditSchema)
    def api_get_folder(folder_id: int) -> FolderEditSchema:
        """Return the full edit representation of one folder.

        Raises:
            HTTPException: 404 if no folder with this id exists, 503 if
                the database is not yet imported.
        """
        settings = app.state.settings
        if not settings.database_path.is_file():
            raise HTTPException(status_code=503, detail="No database imported yet")
        settings.ensure_dirs()
        with lock():
            db = open_database(settings)
            try:
                row = db.folders_table.find_one(id=folder_id)
            finally:
                db.close()
        if row is None:
            raise HTTPException(status_code=404, detail=f"Folder {folder_id} not found")
        return folder_row_to_schema(row)

    @app.put("/api/folders/{folder_id}", response_model=FolderEditSchema)
    def api_put_folder(folder_id: int, schema: FolderEditSchema) -> FolderEditSchema:
        """Replace one folder's editable fields with the request body.

        The dataclass ``FolderConfiguration.validate_with_pydantic``
        remains the source of truth for cross-field invariants; we
        round-trip through it to surface any error as a 400 with the
        message a human can act on.

        Raises:
            HTTPException: 404 if no folder with this id exists, 400 on
                validation failure, 503 if no database imported yet.
        """
        settings = app.state.settings
        if not settings.database_path.is_file():
            raise HTTPException(status_code=503, detail="No database imported yet")
        if schema.id != folder_id:
            # Don't silently rewrite another folder's id.
            raise HTTPException(
                status_code=400,
                detail=f"URL id {folder_id} does not match body id {schema.id}",
            )
        settings.ensure_dirs()
        row = schema_to_folder_row(schema)
        try:
            # Round-trip through FolderConfiguration so the cross-field
            # invariants (e.g. prepend_date_files requires split_edi)
            # are checked the same way the desktop app checks them.
            FolderConfiguration.from_dict(row)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        with lock():
            db = open_database(settings)
            try:
                existing = db.folders_table.find_one(id=folder_id)
                if existing is None:
                    raise HTTPException(
                        status_code=404, detail=f"Folder {folder_id} not found"
                    )
                db.folders_table.update(row, ["id"])
                refreshed = db.folders_table.find_one(id=folder_id)
            finally:
                db.close()
        if refreshed is None:
            # Defensive: the row was visible above so it should still be
            # visible right after the update. If it isn't, something has
            # gone badly wrong (e.g. a hook deleted it).
            raise HTTPException(
                status_code=500,
                detail=f"Folder {folder_id} disappeared during update",
            )
        return folder_row_to_schema(refreshed)

    @app.post("/api/run")
    def api_run() -> dict:
        settings = app.state.settings
        if not settings.database_path.is_file():
            raise HTTPException(status_code=400, detail="No database imported yet")
        try:
            run_id = app.state.run_store.start(settings)
        except RuntimeError as exc:
            # Guardrail: refuse to start a second concurrent run.
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"run_id": run_id}

    @app.post("/api/resend")
    def api_resend() -> dict:
        """Run the dispatcher against every flagged processed-files row."""
        settings = app.state.settings
        if not settings.database_path.is_file():
            raise HTTPException(status_code=400, detail="No database imported yet")
        try:
            run_id = app.state.run_store.start_resend(settings)
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"run_id": run_id}

    @app.post("/api/folders/{folder_id}/run")
    def api_run_folder(folder_id: int) -> dict:
        """Run the dispatcher against a single folder."""
        settings = app.state.settings
        if not settings.database_path.is_file():
            raise HTTPException(status_code=400, detail="No database imported yet")
        # Validate the folder exists up-front so a bad id returns
        # 404 immediately rather than spawning a worker that just
        # reports a failure.
        try:
            with lock():
                db = open_database(settings)
                try:
                    existing = db.folders_table.find_one(id=folder_id)
                finally:
                    db.close()
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        if existing is None:
            raise HTTPException(status_code=404, detail=f"Folder {folder_id} not found")
        try:
            run_id = app.state.run_store.start_folder(settings, folder_id)
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"run_id": run_id}

    @app.get("/api/schedule")
    def api_get_schedule() -> dict:
        """Return the persisted schedule state + last/next run timestamps."""
        return get_schedule_summary(app.state.settings)

    @app.post("/api/schedule")
    def api_set_schedule(
        enabled: bool,  # noqa: FBT001
        interval_seconds: int | None = None,
    ) -> dict:
        """Persist the schedule and re-read it for the response."""
        settings = app.state.settings
        if not settings.database_path.is_file():
            raise HTTPException(status_code=503, detail="No database imported yet")
        interval = interval_seconds if interval_seconds is not None else 60
        write_schedule_state(settings, enabled=enabled, interval=interval)
        return get_schedule_summary(settings)

    @app.get("/api/watched")
    def api_list_watched() -> dict:
        """Return the folders whose watcher is enabled."""
        return {"folders": list_watched(app.state.settings)}

    @app.post("/api/watcher/refresh")
    def api_refresh_watcher() -> dict:
        """Force the watcher supervisor to re-read the watch list.

        The supervisor refreshes every 30 seconds automatically; this
        endpoint is for operators who just toggled watch_enabled via
        the folder editor and don't want to wait.
        """
        if _watcher_supervisor is not None:
            _watcher_supervisor._refresh()
        return {"refreshed": True}

    @app.get("/api/errors")
    def api_list_errors(folder_id: int | None = None, limit: int = 200) -> dict:
        """Return error-ledger rows, newest first, optionally per folder.

        ``folder_id`` filters by the folder whose relative path the
        pipeline recorded; ``limit`` caps the page (bounded to 10000 so
        an accidental huge request can't return the whole table).
        ``folder_counts`` (open question #3) maps every folder id to its
        total ledger-row count so the Errors card can show per-folder
        totals regardless of the active filter.
        """
        settings = app.state.settings
        if not settings.database_path.is_file():
            raise HTTPException(status_code=503, detail="No database imported yet")
        settings.ensure_dirs()
        with lock():
            db = open_database(settings)
            try:
                rows = list_errors(db, folder_id=folder_id, limit=limit)
                counts = error_counts(db)
            finally:
                db.close()
        return {"count": len(rows), "errors": rows, "folder_counts": counts}

    @app.get("/api/errors/file")
    def api_error_file(path: str):
        """Stream a raw error-text artifact back to the browser.

        ``path`` must live under the data dir's ``errors/`` folder — the
        same traversal guard as ``/api/maintenance/download`` — so an
        operator-supplied path can't read arbitrary files.
        """
        settings = app.state.settings
        resolved = Path(path).resolve()
        allowed_root = settings.errors_dir.resolve()
        try:
            resolved.relative_to(allowed_root)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Path not allowed") from exc
        if not resolved.is_file():
            raise HTTPException(status_code=404, detail="Error file not found")
        return FileResponse(
            path=str(resolved),
            filename=resolved.name,
            media_type="text/plain",
        )

    @app.get("/api/errors/folder-file")
    def api_error_folder_file(folder_id: int):
        """Download one folder's full raw error text.

        Concatenates every ledger row's raw artifact (falling back to a
        synthesized block when a row has no linked file), so an operator
        can grab the whole folder's error text at once instead of
        scrolling the ledger.
        """
        settings = app.state.settings
        if not settings.database_path.is_file():
            raise HTTPException(status_code=503, detail="No database imported yet")
        settings.ensure_dirs()
        with lock():
            db = open_database(settings)
            try:
                folder = db.folders_table.find_one(id=folder_id)
                if folder is None:
                    raise HTTPException(
                        status_code=404, detail=f"Folder {folder_id} not found"
                    )
                text = folder_error_text(
                    db,
                    folder_id=folder_id,
                    errors_dir=str(settings.errors_dir),
                )
            finally:
                db.close()
        alias = str(folder.get("alias") or folder.get("folder_name") or folder_id)
        safe = "".join(c for c in alias if c.isalnum() or c in " _-") or "folder"
        return Response(
            content=text or f"No errors recorded for {alias}.\n",
            media_type="text/plain",
            headers={
                "Content-Disposition": f'attachment; filename="{safe} errors.txt"'
            },
        )

    @app.post("/api/errors/clear")
    def api_clear_errors(folder_id: int | None = None) -> dict:
        """Delete error-ledger rows, optionally for one folder."""
        settings = app.state.settings
        if not settings.database_path.is_file():
            raise HTTPException(status_code=503, detail="No database imported yet")
        settings.ensure_dirs()
        with lock():
            db = open_database(settings)
            try:
                cleared = clear_errors(db, folder_id=folder_id)
            finally:
                db.close()
        return {"cleared": cleared}

    @app.get("/api/processed-files/flagged")
    def api_processed_files_flagged(folder_id: int | None = None) -> dict:
        """List every processed-files row, optionally filtered by folder."""
        settings = app.state.settings
        if not settings.database_path.is_file():
            raise HTTPException(status_code=503, detail="No database imported yet")
        settings.ensure_dirs()
        with lock():
            db = open_database(settings)
            try:
                rows = list_processed_files(db, folder_id=folder_id, limit=500)
            finally:
                db.close()
        return {"count": len(rows), "files": rows}

    @app.post("/api/processed-files/{file_id}/resend")
    def api_flag_for_resend(file_id: int, resend: bool = True) -> dict:  # noqa: FBT001,FBT002
        """Set or clear the resend flag on one processed-files row."""
        settings = app.state.settings
        if not settings.database_path.is_file():
            raise HTTPException(status_code=503, detail="No database imported yet")
        settings.ensure_dirs()
        with lock():
            db = open_database(settings)
            try:
                ok = set_resend_flag(db, file_id, resend=resend)
            finally:
                db.close()
        if not ok:
            raise HTTPException(status_code=404, detail=f"Row {file_id} not found")
        return {"id": file_id, "resend_flag": resend}

    @app.post("/api/processed-files/resend-batch")
    def api_flag_batch(file_ids: list[int], resend: bool = True) -> dict:  # noqa: FBT001,FBT002
        """Set/clear the resend flag on many rows in one call."""
        settings = app.state.settings
        if not settings.database_path.is_file():
            raise HTTPException(status_code=503, detail="No database imported yet")
        settings.ensure_dirs()
        with lock():
            db = open_database(settings)
            try:
                updated = set_resend_flag_batch(db, file_ids, resend=resend)
            finally:
                db.close()
        return {"updated": updated}

    @app.post("/api/processed-files/clear-flags")
    def api_clear_flags() -> dict:
        """Clear every resend_flag in the database."""
        settings = app.state.settings
        if not settings.database_path.is_file():
            raise HTTPException(status_code=503, detail="No database imported yet")
        settings.ensure_dirs()
        with lock():
            db = open_database(settings)
            try:
                rows = list_processed_files(db, limit=10000)
                ids = [r["id"] for r in rows if r.get("resend_flag")]
                cleared = clear_resend_flags(db, ids)
            finally:
                db.close()
        return {"cleared": cleared}

    @app.get("/api/runs")
    def api_runs() -> list[dict]:
        """Return recent runs, newest first.

        The in-memory store hands out runs in insertion order (oldest
        first) while ``RunHistory.recent`` is newest first, so the
        in-memory slice is reversed here to keep one consistent ordering
        contract for the UI (which reverses again for display). Without
        this, the Recent-runs list would reorder after a restart.
        """
        in_memory = {r.run_id: r for r in app.state.run_store.list()}
        persisted = []
        if _history is not None:
            persisted = _history.recent(limit=50)
        seen: set[str] = set()
        out: list[dict] = []
        for r in reversed(list(in_memory.values())):
            out.append(_run_summary(r))
            seen.add(r.run_id)
        for r in persisted:
            if r.run_id not in seen:
                out.append(_run_summary(r))
                seen.add(r.run_id)
        return out

    @app.get("/api/runs/{run_id}")
    def api_run_detail(run_id: str) -> dict:
        report = app.state.run_store.get(run_id)
        if report is None and _history is not None:
            report = _history.get(run_id)
        if report is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return _run_summary(report, include_log=True)

    @app.get("/api/runs/{run_id}/log")
    def api_run_log(run_id: str):
        """Server-Sent Events stream of the run's per-folder logs.

        For finished runs we replay the persisted run_log. For
        in-flight runs we poll the in-memory report every second and
        emit any new lines since the last tick. The connection closes
        when the run finishes (``event: done``).
        """
        store = app.state.run_store
        report = store.get(run_id)
        if report is None and _history is not None:
            report = _history.get(run_id)
        if report is None:
            raise HTTPException(status_code=404, detail="Run not found")

        def _events():
            last_seen = 0
            yielded = False
            while True:
                # Re-fetch on every tick so we see new lines as the
                # worker writes them.
                cur = store.get(run_id)
                if cur is None and _history is not None:
                    cur = _history.get(run_id)
                if cur is None:
                    yield "event: done\ndata: missing\n\n"
                    return
                log = "\n".join(f.run_log for f in cur.folders)
                if len(log) > last_seen:
                    chunk = log[last_seen:]
                    yield "event: log\ndata: " + chunk.replace("\n", "\\n") + "\n\n"
                    last_seen = len(log)
                    yielded = True
                if cur.status != "running":
                    if not yielded:
                        # Stream the full log once before closing.
                        yield "event: log\ndata: " + log.replace("\n", "\\n") + "\n\n"
                    yield f"event: done\ndata: {cur.status}\n\n"
                    return
                import time
                time.sleep(1.0)

        return StreamingResponse(
            _events(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/api/processed-files")
    def api_processed_files() -> dict:
        settings = app.state.settings
        with lock():
            db = open_database(settings)
            try:
                raw = db.database_connection.query(
                    "SELECT file_name, folder_alias, processed_at, status, "
                    "sent_to, invoice_numbers FROM processed_files "
                    "ORDER BY id DESC LIMIT 200"
                )
                rows = [dict(r) for r in raw] if raw else []
            finally:
                db.close()
        return {"count": len(rows), "files": rows}

    @app.post("/api/maintenance/clear-processed")
    def api_clear_processed(folder_id: int | None = None) -> dict:
        """Bulk-delete ``processed_files`` rows.

        Args (form/query params):
            folder_id: optional — restrict to one folder.
        """
        settings = app.state.settings
        if not settings.database_path.is_file():
            raise HTTPException(status_code=503, detail="No database imported yet")
        settings.ensure_dirs()
        with lock():
            db = open_database(settings)
            try:
                deleted = clear_processed_files(db, folder_id=folder_id)
            finally:
                db.close()
        return {"deleted": deleted}

    @app.post("/api/maintenance/mark-processed")
    def api_mark_processed(
        file_path: str,
        folder_id: int,
        folder_alias: str = "",
        invoice_numbers: str = "",
        sent_to: str = "",
        status: str = "processed",
    ) -> dict:
        """Record a single file as already processed."""
        settings = app.state.settings
        if not settings.database_path.is_file():
            raise HTTPException(status_code=503, detail="No database imported yet")
        settings.ensure_dirs()
        with lock():
            db = open_database(settings)
            try:
                # 404 if the folder doesn't exist.
                folder = db.folders_table.find_one(id=folder_id)
                if folder is None:
                    raise HTTPException(
                        status_code=404, detail=f"Folder {folder_id} not found"
                    )
                row_id = mark_file_processed(
                    db,
                    file_path=file_path,
                    folder_id=folder_id,
                    folder_alias=folder_alias or folder.get("alias", ""),
                    invoice_numbers=invoice_numbers,
                    status=status,
                    sent_to=sent_to,
                )
            finally:
                db.close()
        return {"id": row_id}

    @app.post("/api/maintenance/export-processed")
    def api_export_processed(folder_id: int) -> dict:
        """Write a CSV report for one folder. Returns the file path."""
        settings = app.state.settings
        if not settings.database_path.is_file():
            raise HTTPException(status_code=503, detail="No database imported yet")
        settings.ensure_dirs()
        with lock():
            db = open_database(settings)
            try:
                try:
                    path = export_processed_report(
                        db, folder_id=folder_id, output_dir=str(settings.logs_dir)
                    )
                except ValueError as exc:
                    # The maintenance helper raises ValueError when the
                    # folder doesn't exist; surface that as 404 rather
                    # than letting it bubble to a 500.
                    raise HTTPException(status_code=404, detail=str(exc)) from exc
            finally:
                db.close()
        return {"path": path}

    @app.get("/api/maintenance/download")
    def api_download_report(path: str):
        """Stream a previously-exported report back to the browser."""
        settings = app.state.settings
        # Only allow downloading files that live under the data dir —
        # an operator-supplied path elsewhere would be a path-traversal
        # vector.
        resolved = Path(path).resolve()
        allowed_root = settings.data_dir.resolve()
        try:
            resolved.relative_to(allowed_root)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Path not allowed") from exc
        if not resolved.is_file():
            raise HTTPException(status_code=404, detail="Report not found")
        return FileResponse(
            path=str(resolved),
            filename=resolved.name,
            media_type="text/csv",
        )

    @app.get("/api/backup/download")
    def api_download_backup(path: str):
        """Stream a backup file back to the browser."""
        settings = app.state.settings
        resolved = Path(path).resolve()
        allowed_root = settings.data_dir.resolve()
        try:
            resolved.relative_to(allowed_root)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Path not allowed") from exc
        if not resolved.is_file():
            raise HTTPException(status_code=404, detail="Backup not found")
        return FileResponse(
            path=str(resolved),
            filename=resolved.name,
            media_type="application/octet-stream",
        )

    @app.get("/api/backups")
    def api_list_backups() -> dict:
        """Return the list of timestamped backup files."""
        return {"backups": list_backups(app.state.settings.data_dir)}

    @app.post("/api/backup/create")
    def api_create_backup() -> dict:
        """Snapshot the active DB to a new ``folders.db.bak-<ts>`` file."""
        settings = app.state.settings
        if not settings.database_path.is_file():
            raise HTTPException(status_code=503, detail="No database imported yet")
        path = make_backup(settings)
        if not path:
            raise HTTPException(status_code=500, detail="Backup failed")
        return {"path": path}

    @app.post("/api/backup/restore")
    def api_restore_backup(path: str) -> dict:
        """Restore the named backup as the active DB.

        Args (form):
            path: absolute path of the backup file (must live under
                the data directory).
        """
        settings = app.state.settings
        try:
            pre_restore = restore_backup(settings, path)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"restored_from": path, "pre_restore_backup": pre_restore}

    # Static UI (served last so /api/* routes win).
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
    return app


app = create_app()


def main() -> None:
    """Run the webapp with uvicorn (``python -m webapp.main``)."""
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    main()
