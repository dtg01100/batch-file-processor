"""Error-ledger endpoints.

Endpoints
---------
- ``GET  /api/errors``              ledger rows + per-folder counts
- ``GET  /api/errors/file``         download a raw error-text artifact
- ``GET  /api/errors/folder-file``  download one folder's full error text
- ``POST /api/errors/clear``        delete ledger rows (optionally per folder)

The two download endpoints both enforce a path-traversal guard: the
operator-supplied path must live under ``settings.data_dir`` (for the
folder file) or ``settings.errors_dir`` (for individual artifacts), so
the URLs can't be abused to read arbitrary files on disk.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response

from webapp.config import Settings
from webapp.database import lock, open_database
from webapp.errors import (
    clear_errors,
    error_counts,
    folder_error_text,
    list_errors,
)
from webapp.routers._deps import get_settings

router = APIRouter()


@router.get("/api/errors")
def api_list_errors(
    folder_id: int | None = None,
    limit: int = 200,
    settings: Settings = Depends(get_settings),
) -> dict:
    """Return error-ledger rows, newest first, optionally per folder.

    ``folder_id`` filters by the folder whose relative path the
    pipeline recorded; ``limit`` caps the page (bounded to 10000 so
    an accidental huge request can't return the whole table).
    ``folder_counts`` (open question #3) maps every folder id to its
    total ledger-row count so the Errors card can show per-folder
    totals regardless of the active filter.
    """
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


@router.get("/api/errors/file")
def api_error_file(
    path: str,
    settings: Settings = Depends(get_settings),
):
    """Stream a raw error-text artifact back to the browser.

    ``path`` must live under the data dir's ``errors/`` folder — the
    same traversal guard as ``/api/maintenance/download`` — so an
    operator-supplied path can't read arbitrary files.
    """
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


@router.get("/api/errors/folder-file")
def api_error_folder_file(
    folder_id: int,
    settings: Settings = Depends(get_settings),
):
    """Download one folder's full raw error text.

    Concatenates every ledger row's raw artifact (falling back to a
    synthesized block when a row has no linked file), so an operator
    can grab the whole folder's error text at once instead of
    scrolling the ledger.
    """
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
        headers={"Content-Disposition": f'attachment; filename="{safe} errors.txt"'},
    )


@router.post("/api/errors/clear")
def api_clear_errors(
    folder_id: int | None = None,
    settings: Settings = Depends(get_settings),
) -> dict:
    """Delete error-ledger rows, optionally for one folder."""
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
