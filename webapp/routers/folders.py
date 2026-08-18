"""Folder CRUD + per-format converter metadata.

Endpoints
---------
- ``GET    /api/folders``                list folders (relative + resolved paths)
- ``POST   /api/folders``                create a new folder
- ``GET    /api/folders/{folder_id}``    one folder (full edit schema)
- ``PUT    /api/folders/{folder_id}``    save one folder
- ``DELETE /api/folders/{folder_id}``    soft-delete a folder (Phase 6.4)
- ``GET    /api/folders/deleted``        list soft-deleted folders (Phase 6.4)
- ``POST   /api/folders/{folder_id}/restore`` restore a soft-deleted folder
                                          (Phase 6.4)
- ``GET    /api/converters``             list the 11 convert formats with their
                                         per-format config fields

The soft-delete flow moves the folder row to a ``folders_deleted``
tombstone table (``_ensure_columns`` adds it idempotently). A
:func:`SoftDeleteTrimSupervisor` background thread purges rows whose
``expires_at`` has passed (default TTL = 30 days, configurable via
``FOLDERS_DELETED_TTL_DAYS``). The restore endpoint re-inserts the
original row JSON into ``folders`` with the same id, so downstream
references in ``processed_files`` stay attached.
"""

from __future__ import annotations

import contextlib
import datetime
import json
import threading

from fastapi import APIRouter, Depends, HTTPException

from core.domain.models.folder import FolderConfiguration
from core.structured_logging import get_logger
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

logger = get_logger(__name__)

router = APIRouter()


def _utcnow_iso() -> str:
    """UTC timestamp in the same ``isoformat()`` shape the rest of the
    webapp uses for ``created_at`` / ``deleted_at``."""
    return datetime.datetime.now(datetime.UTC).isoformat()


# Boolean columns on the ``folders`` table — mirror of
# ``backend.database.sqlite_wrapper.Table._EXPLICIT_BOOLEAN_COLUMNS_BY_TABLE``.
# Used by ``api_restore_folder`` to decide which ``None`` values can
# be safely dropped before re-inserting (see the comment in that
# endpoint for the rationale). Duplicated here rather than imported
# so the webapp layer doesn't reach into the dataset internals.
_FOLDERS_BOOLEAN_COLUMNS = frozenset(
    {
        "folder_is_active",
        "process_backend_copy",
        "process_backend_ftp",
        "process_backend_email",
        "process_edi",
        "calculate_upc_check_digit",
        "include_a_records",
        "include_c_records",
        "include_headers",
        "filter_ampersand",
        "tweak_edi",
        "split_edi",
        "force_edi_validation",
        "append_a_records",
        "force_txt_file_ext",
        "invoice_date_custom_format",
        "retail_uom",
        "override_upc_bool",
        "split_edi_include_invoices",
        "split_edi_include_credits",
        "prepend_date_files",
        "include_item_numbers",
        "include_item_description",
        "split_prepaid_sales_tax_crec",
        "pad_a_records",
    }
)


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


@router.get("/api/folders/deleted")
def api_list_deleted(
    settings: Settings = Depends(get_settings),
) -> dict:
    """List non-expired soft-deleted folders.

    Sorted by ``expires_at`` ascending so the UI can surface the
    rows that are about to disappear at the top. ``alias`` is read
    from the JSON-serialized original row so the dashboard can show
    the operator what they're about to lose.

    Returns ``{"count": N, "rows": [...]}``. Returns ``{"count": 0,
    "rows": []}`` when the database is not yet imported (the empty
    list is a normal "nothing here yet" answer, not an error).

    Note: this route is registered *before* the path-parameterized
    ``/api/folders/{folder_id}`` routes below so Starlette's
    first-match routing picks this literal path instead of binding
    ``folder_id="deleted"`` and 422-ing.
    """
    if not settings.database_path.is_file():
        return {"count": 0, "rows": []}
    now = _utcnow_iso()
    with lock():
        db = open_database(settings)
        try:
            con = db.database_connection.raw_connection
            rows = con.execute(
                "SELECT folder_id, deleted_at, expires_at, original_row_json "
                "FROM folders_deleted WHERE expires_at > ? "
                "ORDER BY expires_at ASC",
                (now,),
            ).fetchall()
        finally:
            db.close()
    out = []
    for fid, deleted_at, expires_at, raw_json in rows:
        alias = ""
        try:
            alias = (json.loads(raw_json) or {}).get("alias", "") or ""
        except (TypeError, ValueError):
            # A corrupted tombstone shouldn't take down the listing.
            alias = ""
        out.append(
            {
                "folder_id": fid,
                "deleted_at": deleted_at,
                "expires_at": expires_at,
                "alias": alias,
            }
        )
    return {"count": len(out), "rows": out}


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
    """Soft-delete a folder (Phase 6.4).

    Moves the folder row into the ``folders_deleted`` tombstone table
    (with the full original row JSON-serialized) and cascades the
    delete into ``processed_files``. The row is recoverable via
    ``POST /api/folders/{folder_id}/restore`` for the duration of the
    operator-configured TTL (``FOLDERS_DELETED_TTL_DAYS``, default 30
    days, clamped ``[1, 365]``).

    The original desktop Delete was permanent — that foot-gun is the
    reason this endpoint now soft-deletes. The error ledger rows are
    left alone (they remain queryable/filterable by the stored
    relative name; the folder filter renders orphaned rows as plain
    text).

    Raises:
        HTTPException: 404 if no folder with this id exists, 503 if
            no database imported yet.
    """
    if not settings.database_path.is_file():
        raise HTTPException(status_code=503, detail="No database imported yet")
    settings.ensure_dirs()
    deleted_at = _utcnow_iso()
    expires_at = (
        datetime.datetime.fromisoformat(deleted_at)
        + datetime.timedelta(days=settings.folders_deleted_ttl_days)
    ).isoformat()
    with lock():
        db = open_database(settings)
        try:
            existing = db.folders_table.find_one(id=folder_id)
            if existing is None:
                raise HTTPException(
                    status_code=404, detail=f"Folder {folder_id} not found"
                )
            # Snapshot the entire row so the restore endpoint can
            # rebuild it verbatim (id + every field, including
            # ones the FolderEditSchema doesn't expose).
            original = {k: v for k, v in existing.items()}
            con = db.database_connection.raw_connection
            con.execute(
                "INSERT INTO folders_deleted "
                "(folder_id, deleted_at, expires_at, original_row_json) "
                "VALUES (?, ?, ?, ?)",
                (
                    folder_id,
                    deleted_at,
                    expires_at,
                    json.dumps(original, default=str),
                ),
            )
            db.folders_table.delete(id=folder_id)
            con.execute(
                "DELETE FROM processed_files WHERE folder_id = ?",
                (folder_id,),
            )
            con.commit()
        finally:
            db.close()
    return {"deleted": folder_id, "expires_at": expires_at}


@router.post("/api/folders/{folder_id}/restore")
def api_restore_folder(
    folder_id: int,
    settings: Settings = Depends(get_settings),
) -> dict:
    """Restore a soft-deleted folder.

    Re-inserts the original row into ``folders`` with the original
    ``id`` so downstream references (``processed_files`` rows that
    were not touched by the soft-delete, watch state, etc.) stay
    attached. The matching ``folders_deleted`` tombstone is
    deleted in the same transaction.

    Edge cases:
    - 404 if no tombstone exists for ``folder_id``.
    - 410 Gone if the tombstone has already expired (operator is
      too late; the trim job will purge it shortly). We refuse
      rather than silently restore stale state.
    - 409 Conflict if the operator manually re-created the folder
      (the new row's id matches the tombstone's folder_id). We do
      not silently overwrite — the operator must rename or delete
      the new folder first.

    Raises:
        HTTPException: 404 / 409 / 410 as above; 503 if no database
            imported yet.
    """
    if not settings.database_path.is_file():
        raise HTTPException(status_code=503, detail="No database imported yet")
    settings.ensure_dirs()
    now = _utcnow_iso()
    with lock():
        db = open_database(settings)
        try:
            con = db.database_connection.raw_connection
            tomb = con.execute(
                "SELECT deleted_at, expires_at, original_row_json "
                "FROM folders_deleted WHERE folder_id = ?",
                (folder_id,),
            ).fetchone()
            if tomb is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"No soft-deleted folder with id {folder_id}",
                )
            _deleted_at, expires_at, raw_json = tomb
            if expires_at <= now:
                raise HTTPException(
                    status_code=410,
                    detail=(
                        f"Folder {folder_id} tombstone expired at "
                        f"{expires_at}; cannot restore"
                    ),
                )
            existing = db.folders_table.find_one(id=folder_id)
            if existing is not None:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Folder id {folder_id} already exists; "
                        "cannot restore"
                    ),
                )
            try:
                payload = json.loads(raw_json)
            except (TypeError, ValueError) as exc:
                raise HTTPException(
                    status_code=500,
                    detail=f"Corrupted folder tombstone: {exc}",
                ) from exc
            # Drop ``None`` values for boolean columns before
            # re-inserting. The dataset's ``Table.insert`` routes
            # any column listed in
            # ``_EXPLICIT_BOOLEAN_COLUMNS_BY_TABLE`` through
            # ``to_db_bool`` which converts ``None`` to ``0`` —
            # but on the *first* insert those columns were
            # omitted entirely, so the stored value is ``NULL``.
            # Without the drop, the round-trip flips ``None`` →
            # ``False`` for ``process_edi``,
            # ``split_prepaid_sales_tax_crec``, etc. SQLite's
            # per-column default (or NULL when no DEFAULT exists)
            # fires on omitted columns, restoring the original
            # behavior exactly. Non-boolean ``None`` values are
            # preserved so genuine NULL semantics survive the
            # round-trip.
            payload = {
                k: v
                for k, v in payload.items()
                if v is not None or k not in _FOLDERS_BOOLEAN_COLUMNS
            }
            # Re-insert verbatim with the original id. The
            # ``Dataset.insert`` API doesn't expose a way to force
            # the id, but it preserves any id already in the dict
            # for the primary key column.
            db.folders_table.insert(payload)
            con.execute(
                "DELETE FROM folders_deleted WHERE folder_id = ?",
                (folder_id,),
            )
            con.commit()
            alias = payload.get("alias", "") or ""
        finally:
            db.close()
    return {"restored": folder_id, "alias": alias}


@router.get("/api/converters")
def api_converters() -> list[dict]:
    """Return the 11 convert formats with their per-format config fields.

    Powers the folder panel's per-format plugin configuration section
    (the desktop's dynamic plugin UI). Each entry has the format key
    (matches ``convert_to_format``), the display name, and the config
    field specs the browser renders into a form.
    """
    return all_converter_specs()


class SoftDeleteTrimSupervisor:
    """Periodic trim job that purges expired ``folders_deleted`` rows.

    Started from the FastAPI lifespan (``webapp/main.py::_lifespan``)
    with the operator-configured interval
    (``FOLDERS_DELETED_TRIM_INTERVAL_SECONDS``, default 1h). The
    thread is daemonised so it doesn't block process exit; ``stop``
    is called from the lifespan teardown and waits up to 2s for
    the loop to acknowledge.

    The ``interval_seconds=0`` path is the synchronous-test
    override: ``start()`` runs **one** trim immediately on the
    calling thread and returns without spawning a background
    thread. ``test_soft_delete.py`` exercises this path to verify
    a 0-second interval purges expired rows without needing a
    long sleep.

    The trim body is wrapped in ``try / except`` with a
    ``logger.debug(..., exc_info=True)`` — mirrors the existing
    ``importer`` / ``restore`` patterns in ``AGENTS.md`` and
    prevents a transient DB error from killing the supervisor.
    """

    def __init__(self, settings: Settings, interval_seconds: int) -> None:
        self._settings = settings
        self._interval = max(0, int(interval_seconds))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._interval == 0:
            # Test path: run one trim on the calling thread and
            # return. No background thread is spawned.
            self._run_once()
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._supervisor_loop,
            name="webapp-soft-delete-trim",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        if self._thread is None:
            return
        self._stop.set()
        self._thread.join(timeout=2.0)
        self._thread = None

    def _supervisor_loop(self) -> None:
        # Run one tick on entry so a freshly-started supervisor
        # does something useful before the first sleep.
        self._run_once()
        while not self._stop.is_set():
            if self._stop.wait(timeout=self._interval):
                return
            self._run_once()

    def _run_once(self) -> None:
        try:
            self._settings.ensure_dirs()
            if not self._settings.database_path.is_file():
                # No DB yet (e.g. webapp launched before any import).
                # Nothing to trim; bail quietly.
                return
            with lock():
                db = open_database(self._settings)
                try:
                    con = db.database_connection.raw_connection
                    con.execute(
                        "DELETE FROM folders_deleted WHERE expires_at < ?",
                        (_utcnow_iso(),),
                    )
                    con.commit()
                finally:
                    db.close()
        except Exception:
            logger.debug(
                "Soft-delete trim tick failed (non-fatal)", exc_info=True
            )
