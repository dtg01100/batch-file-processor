"""System-status endpoints.

Endpoints
---------
- ``GET /api/health``       liveness + data dirs
- ``GET /api/diagnostics``  self-test snapshot (platform, db, modules, runs)
- ``GET /api/config``       base-dir / data-dir / platform + folder counts
- ``GET /api/preflight``    validate active folder configs before a run
"""

from __future__ import annotations

import platform as _platform

from fastapi import APIRouter, Depends, HTTPException

from dispatch.preflight_validator import PreflightIssue, PreflightValidator
from webapp.backup import list_backups
from webapp.config import Settings
from webapp.database import lock, open_database
from webapp.diagnostics import collect_diagnostics
from webapp.paths import resolve_row
from webapp.routers._deps import get_history, get_run_store, get_settings
from webapp.routers._helpers import config_payload
from webapp.scheduler import get_schedule_summary

router = APIRouter()


@router.get("/api/health")
def health(settings: Settings = Depends(get_settings)) -> dict:
    """Liveness probe + the resolved data-dir paths.

    Cheap — no DB read. Used by Docker / load-balancer health checks.
    """
    settings.ensure_dirs()
    return {
        "status": "ok",
        "base_dir": str(settings.base_dir),
        "data_dir": str(settings.data_dir),
        "database_exists": settings.database_path.is_file(),
        "platform": _platform.system(),
    }


@router.get("/api/diagnostics")
def diagnostics(
    settings: Settings = Depends(get_settings),
    run_store=Depends(get_run_store),
    history=Depends(get_history),
) -> dict:
    """Self-test snapshot for the dashboard's Diagnostics card.

    Mirrors the desktop ``-t`` / ``--self-test`` CLI: platform / Python
    version, module-import checks, config + filesystem, plus the live
    snapshot of runs / scheduler / watcher the dashboard needs for
    support tickets. Never raises — every probe is wrapped so a missing
    table returns ``0`` instead of 500.
    """
    settings.ensure_dirs()
    # The schedule summary reads kv_settings, which the operator can
    # leave mid-write during an import — wrap it so the card always
    # renders.
    schedule_summary = None
    try:
        schedule_summary = get_schedule_summary(settings)
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
        run_store=run_store,
        history=history,
        schedule_summary=schedule_summary,
        watched_folders=watched_folders,
        backups_count=backups_count,
    )


@router.get("/api/config")
def config(settings: Settings = Depends(get_settings)) -> dict:
    """Return base-dir / data-dir / platform + folder counts.

    Tolerant of a missing DB — see :func:`webapp.routers._helpers.config_payload`.
    """
    return config_payload(settings)


@router.get("/api/preflight")
def api_preflight(
    folder_id: int | None = None,
    settings: Settings = Depends(get_settings),
) -> dict:
    """Validate active folder configurations before a run starts.

    Runs the shared ``PreflightValidator`` (the same checks the desktop
    surfaced as a dialog) over the active folders. Errors (missing
    backend config, email enabled without SMTP, no backends) will make
    the run fail per-file; warnings (missing copy destination) degrade
    gracefully. The caller decides whether to proceed — this endpoint
    never blocks an automatic/scheduled run.

    Args (query params):
        folder_id: optional — scope to one folder (per-folder runs).

    Raises:
        HTTPException: 503 if no database imported yet.
    """
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
