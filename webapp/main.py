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
- ``GET  /api/preflight``         validate active folder configs before a run
- ``POST /api/import``            multipart: file (legacy folders.db),
                                  base_dir (optional), platform (optional)
- ``POST /api/preview/edi``       classify an EDI upload (parse-only preview)
- ``GET  /api/folders``           configured folders (relative + resolved)
- ``POST /api/folders``           create a new folder
- ``GET  /api/folders/{id}``      one folder (full edit schema)
- ``PUT  /api/folders/{id}``      save one folder
- ``DELETE /api/folders/{id}``    delete a folder + its processed rows
- ``GET  /api/settings``          editable app settings (email/AS400/backup)
- ``PUT  /api/settings``          replace the editable app settings
- ``POST /api/run``               start a background run
- ``POST /api/resend``            start a background resend run
- ``POST /api/folders/{id}/run``  run one folder
- ``GET  /api/runs``              recent runs
- ``GET  /api/runs/{run_id}``     one run (poll this while running)
- ``GET  /api/runs/{run_id}/log`` SSE stream of the run's per-folder logs
- ``GET  /api/processed-files``   recently processed files (filters, ``total``, offset)
- ``GET  /api/processed-files/flagged``  same, with resend_flag info
- ``POST /api/processed-files/{id}/resend``  flag a row for resend
- ``POST /api/processed-files/resend-batch``  flag many rows
- ``POST /api/processed-files/clear-flags``   clear every resend flag
- ``POST /api/maintenance/clear-processed``   bulk-delete processed rows
- ``POST /api/maintenance/mark-processed``    record a single file as processed
- ``POST /api/maintenance/set-all-active``    activate every folder (bulk)
- ``POST /api/maintenance/set-all-inactive``  deactivate every folder (bulk)
- ``POST /api/maintenance/clear-queued-emails``  drop queued report emails
- ``POST /api/maintenance/remove-inactive``   delete inactive folders + history
- ``POST /api/maintenance/mark-all-processed``  record every active folder's files
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
import json
import platform as _platform
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter as _perf_counter
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from core.domain.models.folder import FolderConfiguration
from core.structured_logging import get_logger
from dispatch.preflight_validator import PreflightIssue, PreflightValidator
from webapp.backup import (
    list_backups,
    make_backup,
    restore_backup,
)
from webapp.config import Settings
from webapp.converters_api import all_converter_specs
from webapp.database import get_base_directory, get_source_platform, lock, open_database
from webapp.diagnostics import collect_diagnostics
from webapp.errors import (
    clear_errors,
    error_counts,
    folder_error_text,
    list_errors,
)
from webapp.folder_schema import (
    FolderCreateSchema,
    FolderEditSchema,
    folder_row_to_schema,
    schema_to_folder_row,
)
from webapp.history import RunHistory
from webapp.importer import ImportResult, import_database
from webapp.maintenance import (
    clear_processed_files,
    clear_queued_emails,
    export_processed_report,
    mark_active_as_processed,
    mark_file_processed,
    remove_inactive_folders,
    set_all_folders_active,
)
from webapp.paths import resolve, resolve_row
from webapp.preview import preview_edi
from webapp.resend import (
    clear_resend_flags,
    count_processed_files,
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
from webapp.settings_api import (
    SettingsSchema,
    payload_to_oversight_row,
    payload_to_settings_row,
    settings_row_to_payload,
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
    # Per-format plugin configuration (read-only audit view). Normalized
    # to a dict so the payload is JSON-safe even for legacy rows that
    # stored the column as JSON text.
    plugin_config = row.get("plugin_configurations") or {}
    if isinstance(plugin_config, str):
        with contextlib.suppress(json.JSONDecodeError, TypeError):
            plugin_config = json.loads(plugin_config)
    if not isinstance(plugin_config, dict):
        plugin_config = {}
    return {
        "id": row.get("id"),
        "folder_name": relative,
        "resolved_path": resolved,
        "path_exists": bool(resolved) and Path(resolved).is_dir(),
        "alias": row.get("alias") or "",
        "is_active": str(row.get("folder_is_active", "")).lower() in ("1", "true"),
        "backends": backends,
        # Normalized lowercase, matching merge_plugin_config's lookup.
        "convert_to_format": str(row.get("convert_to_format") or "").strip().lower(),
        "plugin_configurations": plugin_config,
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
                # Phase 5.3 follow-up: per-folder timing + threshold warning.
                "duration_seconds": f.duration_seconds,
                "warning": f.warning,
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

    @app.get("/api/diagnostics")
    def diagnostics() -> dict:
        """Self-test snapshot for the dashboard's Diagnostics card.

        Mirrors the desktop ``-t`` / ``--self-test`` CLI: platform /
        Python version, module-import checks, config + filesystem, plus
        the live snapshot of runs / scheduler / watcher the dashboard
        needs for support tickets. Never raises — every probe is
        wrapped so a missing table returns ``0`` instead of 500.
        """
        settings = app.state.settings
        settings.ensure_dirs()
        # The schedule summary reads kv_settings, which the operator
        # can leave mid-write during an import — wrap it so the card
        # always renders.
        schedule_summary = None
        try:
            from webapp.scheduler import get_schedule_summary as _gss

            schedule_summary = _gss(settings)
        except Exception:
            schedule_summary = {}
        watched_folders = []
        try:
            from webapp.watcher import list_watched as _lw

            watched_folders = _lw(settings)
        except Exception:
            watched_folders = []
        backups_count = 0
        try:
            backups_count = len(list_backups(settings.data_dir))
        except Exception:
            backups_count = 0
        return collect_diagnostics(
            settings=settings,
            run_store=app.state.run_store,
            history=_history,
            schedule_summary=schedule_summary,
            watched_folders=watched_folders,
            backups_count=backups_count,
        )

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
        # Phase 6 (gap 1.6): the desktop's "Cancel" button cancelled a
        # QThread; the webapp doesn't expose a Cancel endpoint (import
        # is a short-lived, one-time setup action and threading a
        # cancel through FastAPI's request lifecycle would add a lot
        # of code for little operator benefit). Instead, surface
        # timing so the dashboard's import notice can show how long
        # the import actually took — a 30-second import on 500 folders
        # used to be a mystery spinner; now it's a clear "Imported
        # 500 folders in 28.4s".
        started = _perf_counter()
        try:
            result: ImportResult = import_database(
                tmp_path,
                settings,
                base_dir=base_dir or None,
                platform=platform or None,
            )
            payload = dataclass_to_dict(result)
            payload["duration_seconds"] = round(_perf_counter() - started, 3)
            return payload
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

    @app.post("/api/folders", response_model=FolderEditSchema, status_code=201)
    def api_create_folder(schema: FolderCreateSchema) -> FolderEditSchema:
        """Create a new folder row and return its full edit schema.

        Closes the desktop gap where new trading partners could only be
        onboarded via an imported legacy DB — the webapp previously had
        no way to add a folder through the UI or API.

        Raises:
            HTTPException: 400 on validation failure, 503 if no database
                imported yet.
        """
        settings = app.state.settings
        if not settings.database_path.is_file():
            raise HTTPException(status_code=503, detail="No database imported yet")
        settings.ensure_dirs()
        row = schema_to_folder_row(schema)
        # ``id`` is database-assigned; never honor a caller-supplied one.
        row.pop("id", None)
        try:
            # Same cross-field invariant check the PUT path uses.
            FolderConfiguration.from_dict(row)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        with lock():
            db = open_database(settings)
            try:
                new_id = db.folders_table.insert(row)
                created = db.folders_table.find_one(id=new_id)
            finally:
                db.close()
        if created is None:
            raise HTTPException(
                status_code=500, detail="Folder insert did not return a row"
            )
        return folder_row_to_schema(created)

    @app.delete("/api/folders/{folder_id}")
    def api_delete_folder(folder_id: int) -> dict:
        """Delete a folder row and its processed-files history.

        The desktop's per-folder Delete removed the configuration row;
        its processed-files rows would otherwise linger as orphans the
        resend flagger could try to act on. The error ledger rows are
        kept (they remain queryable/filterable by the stored relative
        name — the folder filter already renders orphaned rows as
        plain text).

        Raises:
            HTTPException: 404 if no folder with this id exists, 503 if
                no database imported yet.
        """
        settings = app.state.settings
        if not settings.database_path.is_file():
            raise HTTPException(status_code=503, detail="No database imported yet")
        settings.ensure_dirs()
        with lock():
            db = open_database(settings)
            try:
                existing = db.folders_table.find_one(id=folder_id)
                if existing is None:
                    raise HTTPException(
                        status_code=404, detail=f"Folder {folder_id} not found"
                    )
                db.folders_table.delete(id=folder_id)
                con = db.database_connection.raw_connection
                con.execute(
                    "DELETE FROM processed_files WHERE folder_id = ?",
                    (folder_id,),
                )
                con.commit()
            finally:
                db.close()
        return {"deleted": folder_id}

    @app.get("/api/settings", response_model=SettingsSchema)
    def api_get_settings() -> SettingsSchema:
        """Return the editable application settings (email/AS400/backup).

        Reads the two singleton records (``settings`` + ``administrative``)
        the desktop app used. The runner already feeds the ``settings``
        record into the backends via ``get_settings_or_default``, so
        editing here takes effect on the next run.

        Raises:
            HTTPException: 503 if no database imported yet.
        """
        settings = app.state.settings
        if not settings.database_path.is_file():
            raise HTTPException(status_code=503, detail="No database imported yet")
        settings.ensure_dirs()
        with lock():
            db = open_database(settings)
            try:
                return settings_row_to_payload(
                    db.get_settings_or_default(), db.get_oversight_or_default()
                )
            finally:
                db.close()

    @app.put("/api/settings", response_model=SettingsSchema)
    def api_put_settings(schema: SettingsSchema) -> SettingsSchema:
        """Replace the editable settings with the request body.

        Full replace of the editable subset (matching the folder PUT
        semantics); bookkeeping fields like ``backup_counter`` are left
        untouched. The ``administrative`` record is only written when
        it exists, so a minimal legacy DB without it still works.

        Raises:
            HTTPException: 503 if no database imported yet.
        """
        app_settings = app.state.settings
        if not app_settings.database_path.is_file():
            raise HTTPException(status_code=503, detail="No database imported yet")
        app_settings.ensure_dirs()
        with lock():
            db = open_database(app_settings)
            try:
                db.settings.update(payload_to_settings_row(schema), ["id"])
                if db.oversight_and_defaults.find_one(id=1) is not None:
                    db.oversight_and_defaults.update(
                        payload_to_oversight_row(schema), ["id"]
                    )
                return settings_row_to_payload(
                    db.get_settings_or_default(), db.get_oversight_or_default()
                )
            finally:
                db.close()

    @app.get("/api/converters")
    def api_converters() -> list[dict]:
        """Return the 11 convert formats with their per-format config fields.

        Powers the folder panel's per-format plugin configuration section
        (the desktop's dynamic plugin UI). Each entry has the format key
        (matches ``convert_to_format``), the display name, and the config
        field specs the browser renders into a form.
        """
        return all_converter_specs()

    @app.get("/api/preflight")
    def api_preflight(folder_id: int | None = None) -> dict:
        """Validate active folder configurations before a run starts.

        Runs the shared ``PreflightValidator`` (the same checks the
        desktop surfaced as a dialog) over the active folders. Errors
        (missing backend config, email enabled without SMTP, no backends)
        will make the run fail per-file; warnings (missing copy
        destination) degrade gracefully. The caller decides whether to
        proceed — this endpoint never blocks an automatic/scheduled run.

        Args (query params):
            folder_id: optional — scope to one folder (per-folder runs).

        Raises:
            HTTPException: 503 if no database imported yet.
        """
        settings = app.state.settings
        if not settings.database_path.is_file():
            raise HTTPException(status_code=503, detail="No database imported yet")
        settings.ensure_dirs()
        with lock():
            db = open_database(settings)
            try:
                if folder_id is None:
                    rows = (
                        list(db.folders_table.find(folder_is_active=True))
                        if db.folders_table
                        else []
                    )
                else:
                    row = db.folders_table.find_one(id=folder_id)
                    rows = [row] if row is not None else []
                settings_dict = db.get_settings_or_default() or {}
            finally:
                db.close()
        # Resolve relative paths against the base-dir (like the runner
        # does) so the copy-destination existence check sees the real
        # absolute path.
        resolved = [resolve_row(r, settings.base_dir) for r in rows]
        result = PreflightValidator().validate_folders(resolved, settings_dict)

        def _issue(i: PreflightIssue) -> dict:
            return {
                "folder_alias": i.folder_alias,
                "message": i.message,
                "severity": i.severity,
                "field": i.field,
            }

        return {
            "is_valid": result.is_valid,
            "errors": [_issue(i) for i in result.errors],
            "warnings": [_issue(i) for i in result.warnings],
        }

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
    def api_processed_files(
        folder_id: int | None = None,
        search: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> dict:
        """List recent processed-files rows.

        Query params (all optional):
            folder_id: restrict to one folder.
            search: substring match against file_name / folder_alias /
                invoice_numbers (case-insensitive).
            date_from: ISO date lower bound on processed_at.
            date_to: ISO date upper bound (inclusive — the day
                itself is included).
            limit: maximum rows to return (default 200, capped at
                10000 to prevent expensive full-history dumps).
            offset: number of matching rows to skip (for "Load More"
                pagination). Must be non-negative; capped at 10000 to
                mirror the limit guard.

        The response includes ``total`` — the count of rows that match
        the filters ignoring ``limit`` / ``offset`` — so the dashboard
        knows whether more pages remain. ``count`` is the size of the
        current page.
        """
        if limit < 1:
            limit = 200
        if limit > 10000:
            limit = 10000
        if offset < 0:
            offset = 0
        if offset > 10000:
            offset = 10000
        settings = app.state.settings
        with lock():
            db = open_database(settings)
            try:
                total = count_processed_files(
                    db,
                    folder_id=folder_id,
                    search=search or None,
                    date_from=date_from or None,
                    date_to=date_to or None,
                )
                rows = list_processed_files(
                    db,
                    folder_id=folder_id,
                    search=search or None,
                    date_from=date_from or None,
                    date_to=date_to or None,
                    limit=limit,
                    offset=offset,
                )
            finally:
                db.close()
        return {
            "count": len(rows),
            "total": total,
            "limit": limit,
            "offset": offset,
            "files": rows,
        }

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

    @app.post("/api/maintenance/set-all-active")
    def api_set_all_active() -> dict:
        """Activate every inactive folder (desktop's "Move all to active")."""
        settings = app.state.settings
        if not settings.database_path.is_file():
            raise HTTPException(status_code=503, detail="No database imported yet")
        settings.ensure_dirs()
        with lock():
            db = open_database(settings)
            try:
                changed = set_all_folders_active(db, active=True)
            finally:
                db.close()
        return {"changed": changed}

    @app.post("/api/maintenance/set-all-inactive")
    def api_set_all_inactive() -> dict:
        """Deactivate every active folder (desktop's "Move all to inactive")."""
        settings = app.state.settings
        if not settings.database_path.is_file():
            raise HTTPException(status_code=503, detail="No database imported yet")
        settings.ensure_dirs()
        with lock():
            db = open_database(settings)
            try:
                changed = set_all_folders_active(db, active=False)
            finally:
                db.close()
        return {"changed": changed}

    @app.post("/api/maintenance/clear-queued-emails")
    def api_clear_queued_emails() -> dict:
        """Drop every queued report-email row (desktop's "Clear queued emails")."""
        settings = app.state.settings
        if not settings.database_path.is_file():
            raise HTTPException(status_code=503, detail="No database imported yet")
        settings.ensure_dirs()
        with lock():
            db = open_database(settings)
            try:
                cleared = clear_queued_emails(db)
            finally:
                db.close()
        return {"cleared": cleared}

    @app.post("/api/maintenance/remove-inactive")
    def api_remove_inactive() -> dict:
        """Delete every inactive folder + its processed rows (desktop's
        "Remove all inactive configurations").
        """
        settings = app.state.settings
        if not settings.database_path.is_file():
            raise HTTPException(status_code=503, detail="No database imported yet")
        settings.ensure_dirs()
        with lock():
            db = open_database(settings)
            try:
                removed = remove_inactive_folders(db)
            finally:
                db.close()
        return {"removed": removed}

    @app.post("/api/maintenance/mark-all-processed")
    def api_mark_all_processed() -> dict:
        """Record every file in the active folders as processed.

        Mirrors the desktop's "Mark all in active as processed": scans
        each active folder's directory, dedupes by checksum against
        ``processed_files``, and inserts a row per remaining file so the
        next run skips them.

        Raises:
            HTTPException: 503 if no database imported yet.
        """
        settings = app.state.settings
        if not settings.database_path.is_file():
            raise HTTPException(status_code=503, detail="No database imported yet")
        settings.ensure_dirs()
        with lock():
            db = open_database(settings)
            try:
                result = mark_active_as_processed(
                    db, base_dir=str(settings.base_dir)
                )
            finally:
                db.close()
        return result

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
