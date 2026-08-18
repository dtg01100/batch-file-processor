"""Editable application settings (email / AS400 / backups / reporting).

Endpoints
---------
- ``GET /api/settings``  return the editable settings payload
- ``PUT /api/settings``  replace the editable settings

These don't share the folder-domain router because the desktop app's
``settings`` and ``oversight_and_defaults`` tables are app-wide, not
per-folder. The runner reads the same singleton records via
``get_settings_or_default``, so editing here takes effect on the next
run without a restart.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from webapp.config import Settings
from webapp.database import lock, open_database
from webapp.routers._deps import get_settings
from webapp.settings_api import (
    SettingsSchema,
    payload_to_oversight_row,
    payload_to_settings_row,
    settings_row_to_payload,
)

router = APIRouter()


@router.get("/api/settings", response_model=SettingsSchema)
def api_get_settings(settings: Settings = Depends(get_settings)) -> SettingsSchema:
    """Return the editable application settings (email/AS400/backup).

    Reads the two singleton records (``settings`` + ``administrative``)
    the desktop app used. The runner already feeds the ``settings``
    record into the backends via ``get_settings_or_default``, so
    editing here takes effect on the next run.

    Raises:
        HTTPException: 503 if no database imported yet.
    """
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


@router.put("/api/settings", response_model=SettingsSchema)
def api_put_settings(
    schema: SettingsSchema,
    settings: Settings = Depends(get_settings),
) -> SettingsSchema:
    """Replace the editable settings with the request body.

    Full replace of the editable subset (matching the folder PUT
    semantics); bookkeeping fields like ``backup_counter`` are left
    untouched. The ``administrative`` record is only written when it
    exists, so a minimal legacy DB without it still works.

    Raises:
        HTTPException: 503 if no database imported yet.
    """
    if not settings.database_path.is_file():
        raise HTTPException(status_code=503, detail="No database imported yet")
    settings.ensure_dirs()
    with lock():
        db = open_database(settings)
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
