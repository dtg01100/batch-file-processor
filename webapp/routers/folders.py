"""Folder CRUD + per-format converter metadata.

Endpoints
---------
- ``GET    /api/folders``             list folders (relative + resolved paths)
- ``POST   /api/folders``             create a new folder
- ``GET    /api/folders/{folder_id}`` one folder (full edit schema)
- ``PUT    /api/folders/{folder_id}`` save one folder
- ``DELETE /api/folders/{folder_id}`` delete a folder + its processed rows
- ``GET    /api/converters``          list the 11 convert formats with their
                                      per-format config fields
"""

from __future__ import annotations

import contextlib

from fastapi import APIRouter, Depends, HTTPException

from core.domain.models.folder import FolderConfiguration
from webapp.config import Settings
from webapp.converters_api import all_converter_specs
from webapp.database import lock, open_database
from webapp.folder_schema import (
    FolderCreateSchema,
    FolderEditSchema,
    folder_row_to_schema,
    schema_to_folder_row,
)
from webapp.routers._deps import get_settings
from webapp.routers._helpers import folder_summary

router = APIRouter()


@router.get("/api/folders")
def api_folders(settings: Settings = Depends(get_settings)) -> list[dict]:
    """Return the configured folders (relative + resolved paths).

    The original ``create_app`` body opened the DB, read every row, then
    closed the connection inside two separate ``contextlib.suppress``
    blocks. ``GET /api/folders`` is read-only — a 500 here is genuinely
    exceptional (an unreadable DB) so we surface it; the close() call
    still tolerates a follow-on failure to keep the previous contract.
    """
    try:
        with lock():
            db = open_database(settings)
            try:
                rows = list(db.folders_table.all()) if db.folders_table else []
            finally:
                with contextlib.suppress(Exception):
                    db.close()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return [folder_summary(r, str(settings.base_dir)) for r in rows]


@router.get("/api/folders/{folder_id}", response_model=FolderEditSchema)
def api_get_folder(
    folder_id: int,
    settings: Settings = Depends(get_settings),
) -> FolderEditSchema:
    """Return the full edit representation of one folder.

    Raises:
        HTTPException: 404 if no folder with this id exists, 503 if
            the database is not yet imported.
    """
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


@router.put("/api/folders/{folder_id}", response_model=FolderEditSchema)
def api_put_folder(
    folder_id: int,
    schema: FolderEditSchema,
    settings: Settings = Depends(get_settings),
) -> FolderEditSchema:
    """Replace one folder's editable fields with the request body.

    The dataclass ``FolderConfiguration.validate_with_pydantic`` remains
    the source of truth for cross-field invariants; we round-trip
    through it to surface any error as a 400 with the message a human
    can act on.

    Raises:
        HTTPException: 404 if no folder with this id exists, 400 on
            validation failure, 503 if no database imported yet.
    """
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


@router.post(
    "/api/folders",
    response_model=FolderEditSchema,
    status_code=201,
)
def api_create_folder(
    schema: FolderCreateSchema,
    settings: Settings = Depends(get_settings),
) -> FolderEditSchema:
    """Create a new folder row and return its full edit schema.

    Closes the desktop gap where new trading partners could only be
    onboarded via an imported legacy DB — the webapp previously had
    no way to add a folder through the UI or API.

    Raises:
        HTTPException: 400 on validation failure, 503 if no database
            imported yet.
    """
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


@router.delete("/api/folders/{folder_id}")
def api_delete_folder(
    folder_id: int,
    settings: Settings = Depends(get_settings),
) -> dict:
    """Delete a folder row and its processed-files history.

    The desktop's per-folder Delete removed the configuration row;
    its processed-files rows would otherwise linger as orphans the
    resend flagger could try to act on. The error ledger rows are
    kept (they remain queryable/filterable by the stored relative
    name — the folder filter already renders orphaned rows as plain
    text).

    Raises:
        HTTPException: 404 if no folder with this id exists, 503 if
            no database imported yet.
    """
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


@router.get("/api/converters")
def api_converters() -> list[dict]:
    """Return the 11 convert formats with their per-format config fields.

    Powers the folder panel's per-format plugin configuration section
    (the desktop's dynamic plugin UI). Each entry has the format key
    (matches ``convert_to_format``), the display name, and the config
    field specs the browser renders into a form.
    """
    return all_converter_specs()
