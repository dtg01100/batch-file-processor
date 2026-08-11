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
- ``GET  /api/folders``           configured folders (relative + resolved)
- ``GET  /api/folders/{id}``      one folder (full edit schema)
- ``PUT  /api/folders/{id}``      save one folder
- ``POST /api/run``               start a background run
- ``POST /api/resend``            start a background resend run
- ``GET  /api/runs``              recent runs
- ``GET  /api/runs/{run_id}``     one run (poll this while running)
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
"""

from __future__ import annotations

import contextlib
import platform as _platform
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from core.domain.models.folder import FolderConfiguration
from core.structured_logging import get_logger
from webapp.config import Settings
from webapp.database import get_base_directory, get_source_platform, lock, open_database
from webapp.folder_schema import (
    FolderEditSchema,
    folder_row_to_schema,
    schema_to_folder_row,
)
from webapp.importer import ImportResult, import_database
from webapp.maintenance import (
    clear_processed_files,
    export_processed_report,
    mark_file_processed,
)
from webapp.paths import resolve
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

STATIC_DIR = Path(__file__).parent / "static"

logger = get_logger(__name__)

_run_store = RunStore()
_scheduler = Scheduler()


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    """Start/stop the background scheduler alongside the app."""
    _scheduler.attach_run_store(_run_store)
    _scheduler.start()
    try:
        yield
    finally:
        _scheduler.stop()


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
        return [_run_summary(r) for r in app.state.run_store.list()]

    @app.get("/api/runs/{run_id}")
    def api_run_detail(run_id: str) -> dict:
        report = app.state.run_store.get(run_id)
        if report is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return _run_summary(report, include_log=True)

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
