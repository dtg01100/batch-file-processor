"""Backup / restore endpoints.

Endpoints
---------
- ``GET  /api/backups``           list timestamped backup files
- ``POST /api/backup/create``     snapshot the active DB
- ``POST /api/backup/restore``    restore a named backup as the active DB
- ``GET  /api/backup/download``   download a backup file

Restore writes a pre-restore backup first, so an operator can recover
from a botched restore. The download endpoint enforces the same path
traversal guard as ``/api/maintenance/download`` and
``/api/errors/file``: the path must resolve under ``settings.data_dir``.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from webapp.backup import list_backups, make_backup, restore_backup
from webapp.config import Settings
from webapp.routers._deps import get_settings

router = APIRouter()


@router.get("/api/backups")
def api_list_backups(settings: Settings = Depends(get_settings)) -> dict:
    """Return the list of timestamped backup files."""
    return {"backups": list_backups(settings.data_dir)}


@router.post("/api/backup/create")
def api_create_backup(settings: Settings = Depends(get_settings)) -> dict:
    """Snapshot the active DB to a new ``folders.db.bak-<ts>`` file."""
    if not settings.database_path.is_file():
        raise HTTPException(status_code=503, detail="No database imported yet")
    path = make_backup(settings)
    if not path:
        raise HTTPException(status_code=500, detail="Backup failed")
    return {"path": path}


@router.post("/api/backup/restore")
def api_restore_backup(
    path: str,
    settings: Settings = Depends(get_settings),
) -> dict:
    """Restore the named backup as the active DB.

    Args (form):
        path: absolute path of the backup file (must live under the
            data directory).
    """
    try:
        pre_restore = restore_backup(settings, path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"restored_from": path, "pre_restore_backup": pre_restore}


@router.get("/api/backup/download")
def api_download_backup(
    path: str,
    settings: Settings = Depends(get_settings),
):
    """Stream a backup file back to the browser."""
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
