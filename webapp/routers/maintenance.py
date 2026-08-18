"""App-wide maintenance endpoints.

Endpoints
---------
- ``POST /api/maintenance/clear-processed``       bulk-delete processed rows
- ``POST /api/maintenance/mark-processed``        record a single file as processed
- ``POST /api/maintenance/set-all-active``        bulk activate every folder
- ``POST /api/maintenance/set-all-inactive``      bulk deactivate every folder
- ``POST /api/maintenance/clear-queued-emails``   drop queued report emails
- ``POST /api/maintenance/remove-inactive``       delete inactive folders + history
- ``POST /api/maintenance/mark-all-processed``    record every active folder's files
- ``POST /api/maintenance/export-processed``      write a CSV report for one folder
- ``GET  /api/maintenance/download``              download a previously-written report

These mirror the desktop Maintenance dialog's destructive actions.
The card UI surfaces every one with a confirm-and-go button so the
operator can run them without leaving the browser.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from webapp.config import Settings
from webapp.database import lock, open_database
from webapp.maintenance import (
    clear_processed_files,
    clear_queued_emails,
    export_processed_report,
    mark_active_as_processed,
    mark_file_processed,
    remove_inactive_folders,
    set_all_folders_active,
)
from webapp.routers._deps import get_settings

router = APIRouter()


@router.post("/api/maintenance/clear-processed")
def api_clear_processed(
    folder_id: int | None = None,
    settings: Settings = Depends(get_settings),
) -> dict:
    """Bulk-delete ``processed_files`` rows.

    Args (form/query params):
        folder_id: optional — restrict to one folder.
    """
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


@router.post("/api/maintenance/mark-processed")
def api_mark_processed(
    file_path: str,
    folder_id: int,
    folder_alias: str = "",
    invoice_numbers: str = "",
    sent_to: str = "",
    status: str = "processed",
    settings: Settings = Depends(get_settings),
) -> dict:
    """Record a single file as already processed."""
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


@router.post("/api/maintenance/set-all-active")
def api_set_all_active(settings: Settings = Depends(get_settings)) -> dict:
    """Activate every inactive folder (desktop's "Move all to active")."""
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


@router.post("/api/maintenance/set-all-inactive")
def api_set_all_inactive(settings: Settings = Depends(get_settings)) -> dict:
    """Deactivate every active folder (desktop's "Move all to inactive")."""
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


@router.post("/api/maintenance/clear-queued-emails")
def api_clear_queued_emails(settings: Settings = Depends(get_settings)) -> dict:
    """Drop every queued report-email row (desktop's "Clear queued emails")."""
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


@router.post("/api/maintenance/remove-inactive")
def api_remove_inactive(settings: Settings = Depends(get_settings)) -> dict:
    """Delete every inactive folder + its processed rows (desktop's
    "Remove all inactive configurations").
    """
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


@router.post("/api/maintenance/mark-all-processed")
def api_mark_all_processed(settings: Settings = Depends(get_settings)) -> dict:
    """Record every file in the active folders as processed.

    Mirrors the desktop's "Mark all in active as processed": scans
    each active folder's directory, dedupes by checksum against
    ``processed_files``, and inserts a row per remaining file so the
    next run skips them.

    Raises:
        HTTPException: 503 if no database imported yet.
    """
    if not settings.database_path.is_file():
        raise HTTPException(status_code=503, detail="No database imported yet")
    settings.ensure_dirs()
    with lock():
        db = open_database(settings)
        try:
            result = mark_active_as_processed(db, base_dir=str(settings.base_dir))
        finally:
            db.close()
    return result


@router.post("/api/maintenance/export-processed")
def api_export_processed(
    folder_id: int,
    settings: Settings = Depends(get_settings),
) -> dict:
    """Write a CSV report for one folder. Returns the file path."""
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


@router.get("/api/maintenance/download")
def api_download_report(
    path: str,
    settings: Settings = Depends(get_settings),
):
    """Stream a previously-exported report back to the browser."""
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
