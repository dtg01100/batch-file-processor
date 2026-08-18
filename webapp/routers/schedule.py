"""Scheduler state endpoints.

Endpoints
---------
- ``GET  /api/schedule``  current schedule state + last/next run timestamps
- ``POST /api/schedule``  enable/disable the scheduler + set interval

The interval defaults to 60s on POST when the caller omits it; this
mirrors the desktop's Settings dialog default and keeps the dashboard
working after a "just enable it" click.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from webapp.config import Settings
from webapp.routers._deps import get_settings
from webapp.scheduler import get_schedule_summary, write_schedule_state

router = APIRouter()


@router.get("/api/schedule")
def api_get_schedule(settings: Settings = Depends(get_settings)) -> dict:
    """Return the persisted schedule state + last/next run timestamps."""
    return get_schedule_summary(settings)


@router.post("/api/schedule")
def api_set_schedule(
    enabled: bool,  # noqa: FBT001
    interval_seconds: int | None = None,
    settings: Settings = Depends(get_settings),
) -> dict:
    """Persist the schedule and re-read it for the response."""
    if not settings.database_path.is_file():
        raise HTTPException(status_code=503, detail="No database imported yet")
    interval = interval_seconds if interval_seconds is not None else 60
    write_schedule_state(settings, enabled=enabled, interval=interval)
    return get_schedule_summary(settings)
