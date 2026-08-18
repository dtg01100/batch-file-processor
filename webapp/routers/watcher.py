"""Folder-watcher endpoints.

Endpoints
---------
- ``GET  /api/watched``         folders with ``watch_enabled``
- ``POST /api/watcher/refresh`` force the watcher supervisor to re-read

The refresh endpoint reaches into a private method
(``_WatcherSupervisor._refresh``) on the singleton supervisor started
by the lifespan. The supervisor refreshes every 30 seconds
automatically; this endpoint is for operators who just toggled
``watch_enabled`` via the folder editor and don't want to wait.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from webapp.config import Settings
from webapp.routers._deps import (
    get_settings,
    get_watcher_supervisor,
)
from webapp.watcher import list_watched

router = APIRouter()


@router.get("/api/watched")
def api_list_watched(settings: Settings = Depends(get_settings)) -> dict:
    """Return the folders whose watcher is enabled."""
    return {"folders": list_watched(settings)}


@router.post("/api/watcher/refresh")
def api_refresh_watcher(
    supervisor=Depends(get_watcher_supervisor),
) -> dict:
    """Force the watcher supervisor to re-read the watch list.

    The supervisor refreshes every 30 seconds automatically; this
    endpoint is for operators who just toggled ``watch_enabled`` via
    the folder editor and don't want to wait.
    """
    if supervisor is not None:
        supervisor._refresh()
    return {"refreshed": True}
