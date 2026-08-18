"""FastAPI application factory for the Batch File Sender webapp.

Run with::

    BFS_BASE_DIR=./data python -m webapp.main
    # or
    uvicorn webapp.main:app --host 0.0.0.0 --port 8000

Phase 6.1 (2026-08-18): the default bind is now ``127.0.0.1:8000`` —
matches the spec's single-host local-first posture (§3.4 — "no
inbound network surface"). Operators who want remote access opt in
explicitly with ``BFS_HOST=0.0.0.0`` or ``uvicorn --host 0.0.0.0``.

This module owns only:

  * the ``Settings`` factory + ``RunStore`` / ``Scheduler`` singletons
  * the lifespan context manager that starts/stops the scheduler and
    the folder-watcher supervisor
  * ``create_app(settings=None)`` — the FastAPI app factory
  * the module-level ``app`` instance for ``uvicorn webapp.main:app``
  * the static-files mount for the browser UI

Endpoint logic lives in :mod:`webapp.routers` — one ``APIRouter`` per
domain. ``create_app`` calls ``app.include_router(router)`` for each.

Endpoints
---------
- ``GET    /``                              browser UI (static files)
- ``GET    /api/health``                    liveness + data dirs
- ``GET    /api/diagnostics``               self-test snapshot
- ``GET    /api/config``                    base-dir / data-dir + counts
- ``GET    /api/preflight``                 validate active folder configs
- ``POST   /api/import``                    upload a legacy folders.db
- ``POST   /api/preview/edi``               parse-only EDI preview
- ``GET    /api/folders``                   configured folders (list)
- ``POST   /api/folders``                   create a folder
- ``GET    /api/folders/{folder_id}``       one folder (full edit schema)
- ``PUT    /api/folders/{folder_id}``       save one folder
- ``DELETE /api/folders/{folder_id}``       delete a folder + history
- ``GET    /api/converters``                11 convert formats + config fields
- ``GET    /api/settings``                  editable app settings
- ``PUT    /api/settings``                  replace the editable settings
- ``POST   /api/run``                       start a background run
- ``POST   /api/resend``                    start a background resend run
- ``POST   /api/folders/{folder_id}/run``   run a single folder
- ``GET    /api/runs``                      recent runs
- ``GET    /api/runs/{run_id}``             one run (poll while running)
- ``GET    /api/runs/{run_id}/log``         SSE stream of run logs
- ``GET    /api/processed-files``           processed rows (filters, total, offset)
- ``GET    /api/processed-files/flagged``   same, with resend_flag info
- ``POST   /api/processed-files/{id}/resend``         flag a row for resend
- ``POST   /api/processed-files/resend-batch``        flag many rows
- ``POST   /api/processed-files/clear-flags``         clear every resend flag
- ``POST   /api/maintenance/clear-processed``         bulk-delete processed rows
- ``POST   /api/maintenance/mark-processed``          record a single file
- ``POST   /api/maintenance/set-all-active``          activate every folder
- ``POST   /api/maintenance/set-all-inactive``        deactivate every folder
- ``POST   /api/maintenance/clear-queued-emails``     drop queued report emails
- ``POST   /api/maintenance/remove-inactive``         delete inactive folders
- ``POST   /api/maintenance/mark-all-processed``      mark every active folder's files
- ``POST   /api/maintenance/export-processed``        write a CSV report
- ``GET    /api/maintenance/download``                download a report
- ``GET    /api/schedule``               current schedule state
- ``POST   /api/schedule``               enable/disable the scheduler
- ``GET    /api/watched``                watched folders + watcher health
- ``POST   /api/watcher/refresh``        force the supervisor to re-read
- ``GET    /api/errors``                 error-ledger rows + folder counts
- ``GET    /api/errors/file``            download a raw error-text artifact
- ``GET    /api/errors/folder-file``     download one folder's full error text
- ``POST   /api/errors/clear``           delete ledger rows (per folder or all)
- ``GET    /api/backups``                list timestamped backup files
- ``POST   /api/backup/create``          snapshot the active DB
- ``POST   /api/backup/restore``         restore a named backup
- ``GET    /api/backup/download``        download a backup file
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from webapp.config import Settings
from webapp.history import RunHistory
from webapp.routers import (
    backups,
    errors,
    folders,
    imports,
    maintenance,
    processed,
    runs,
    schedule,
    settings_api,
    system,
    watcher,
)
from webapp.runner import RunStore
from webapp.scheduler import Scheduler
from webapp.watcher import WatcherSupervisor

STATIC_DIR = Path(__file__).parent / "static"

# Module-level singletons shared across all app instances created via
# ``create_app``. Tests that call ``create_app(settings=...)`` share the
# same singletons; the run store is intentionally global so the
# background scheduler can find it from its own thread.
_run_store = RunStore()
_scheduler = Scheduler()


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Start/stop the background scheduler + folder watcher.

    ``history`` and ``watcher_supervisor`` are created here (not at
    import time) because both depend on the ``Settings`` that only
    exists once ``create_app`` has run. They are attached to
    ``app.state`` so router endpoints can reach them through the
    ``Depends()`` helpers in :mod:`webapp.routers._deps`.
    """
    settings = app.state.settings
    history = RunHistory(settings)
    _run_store.attach_history(history)
    _scheduler.attach_run_store(_run_store)
    _scheduler.start()
    supervisor = WatcherSupervisor(settings, _run_store)
    supervisor.start()
    app.state.history = history
    app.state.scheduler = _scheduler
    app.state.watcher_supervisor = supervisor
    try:
        yield
    finally:
        _scheduler.stop()
        if supervisor is not None:
            supervisor.stop()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI app. ``settings`` is injectable for tests."""
    app = FastAPI(title="Batch File Sender", version="0.1.0", lifespan=_lifespan)
    app.state.settings = settings or Settings.from_env()
    app.state.run_store = _run_store

    # Register one router per domain. Order is irrelevant — FastAPI
    # matches by path before method so the only thing that matters is
    # that each route appears at most once across all routers.
    for router in (
        system.router,
        imports.router,
        folders.router,
        settings_api.router,
        runs.router,
        schedule.router,
        watcher.router,
        errors.router,
        processed.router,
        maintenance.router,
        backups.router,
    ):
        app.include_router(router)

    # Static UI last so /api/* routes win.
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
    return app


app = create_app()


def main() -> None:
    """Run the webapp with uvicorn (``python -m webapp.main``).

    Phase 6.1: default bind is ``127.0.0.1:8000`` (local-first per
    ``PROJECT_SPEC.md`` §3.4). Operators who want remote access opt
    in via ``BFS_HOST=0.0.0.0`` or ``uvicorn --host 0.0.0.0``.
    """
    import uvicorn

    settings = Settings.from_env()
    uvicorn.run(app, host=settings.host, port=settings.port, log_level="info")


if __name__ == "__main__":
    main()
