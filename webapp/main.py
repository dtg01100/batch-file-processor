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
- ``POST /api/run``               start a background run
- ``GET  /api/runs``              recent runs
- ``GET  /api/runs/{run_id}``     one run (poll this while running)
- ``GET  /api/processed-files``   recently processed files
"""

from __future__ import annotations

import contextlib
import platform as _platform
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles

from core.structured_logging import get_logger
from webapp.config import Settings
from webapp.database import get_base_directory, get_source_platform, lock, open_database
from webapp.importer import ImportResult, import_database
from webapp.paths import resolve
from webapp.runner import RunReport, RunStore

STATIC_DIR = Path(__file__).parent / "static"

logger = get_logger(__name__)

_run_store = RunStore()


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
    app = FastAPI(title="Batch File Sender", version="0.1.0")
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
        try:
            with lock():
                db = open_database(settings)
                with contextlib.suppress(Exception):
                    raw = db.database_connection.query(
                        "SELECT file_name, folder_alias, processed_at, status, "
                        "sent_to, invoice_numbers FROM processed_files "
                        "ORDER BY id DESC LIMIT 200"
                    )
                    rows = [dict(r) for r in raw] if raw else []
                with contextlib.suppress(Exception):
                    db.close()
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return {"count": len(rows), "files": rows}

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
