"""Tests for the webapp error ledger (phase 5.1).

Covers:

- ``webapp.errors.LedgerDatabase``: the adapter that lets the dispatch
  ``ErrorHandler`` write into ``dispatch_errors`` through the webapp's
  ``DatabaseObj``.
- ``list_errors`` / ``clear_errors``: the SQL helpers behind
  ``GET /api/errors`` and ``POST /api/errors/clear``, including the
  folder filter (which must match both the stored relative name and the
  absolute path the pipeline records).
- The API endpoints, including the 503-no-database guard.
- One true end-to-end test: a real folder run that fails inside the
  pipeline and lands a row in the ledger.
"""

from __future__ import annotations

import datetime
import time

import pytest
from fastapi.testclient import TestClient

from dispatch.error_handler import ErrorHandler
from webapp.config import Settings
from webapp.database import open_database
from webapp.errors import LedgerDatabase, clear_errors, insert_error, list_errors
from webapp.main import create_app

pytestmark = [pytest.mark.integration]


@pytest.fixture
def settings(tmp_path):
    s = Settings(base_dir=tmp_path / "data", data_dir=tmp_path / "data" / "config")
    s.ensure_dirs()
    return s


def _insert_folder(
    settings,
    *,
    folder_name: str = "inbox/test",
    alias: str = "TEST",
    **extra,
) -> int:
    """Insert a folder row and return its id."""
    db = open_database(settings)
    row = {
        "folder_name": folder_name,
        "folder_is_active": True,
        "alias": alias,
        "process_backend_copy": True,
        "copy_to_directory": "archive/test",
        "process_backend_ftp": False,
        "process_backend_email": False,
        "process_backend_http": False,
        "created_at": datetime.datetime.now().isoformat(),
    }
    row.update(extra)
    try:
        return db.folders_table.insert(row)
    finally:
        db.close()


def _record(settings, *, folder_name: str, filename: str, message: str = "boom"):
    """Persist one ledger row the way the pipeline does (ErrorHandler +
    LedgerDatabase adapter)."""
    db = open_database(settings)
    try:
        handler = ErrorHandler(database=LedgerDatabase(db))
        handler.record_error(
            folder=folder_name,
            filename=filename,
            error=ValueError(message),
        )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# LedgerDatabase adapter
# ---------------------------------------------------------------------------


def test_adapter_exposes_raw_connection(settings):
    db = open_database(settings)
    try:
        adapter = LedgerDatabase(db)
        assert adapter.raw_connection is db.database_connection.raw_connection
    finally:
        db.close()


def test_adapter_insert_fallback_without_raw_connection():
    """When ``raw_connection`` is unavailable, ErrorHandler falls back to
    ``db.insert`` — the adapter must route that to the table wrapper."""

    class _FakeTable:
        def __init__(self):
            self.rows = []

        def insert(self, record):
            self.rows.append(record)

    class _FakeConn:
        def __init__(self):
            self.table = _FakeTable()

        def __getitem__(self, key):
            return self.table

    class _FakeDb:
        def __init__(self):
            self.database_connection = _FakeConn()

    fake = _FakeDb()
    adapter = LedgerDatabase(fake)
    adapter.insert({"folder": "inbox/test", "error_message": "x"})

    assert fake.database_connection.table.rows == [
        {"folder": "inbox/test", "error_message": "x"}
    ]


def test_error_handler_persists_through_adapter(settings):
    db = open_database(settings)
    try:
        handler = ErrorHandler(database=LedgerDatabase(db))
        handler.record_error(
            folder="inbox/test",
            filename="/data/inbox/test/bad.edi",
            error=ValueError("boom"),
            error_source="Validator",
        )
        rows = list_errors(db)
    finally:
        db.close()

    assert len(rows) == 1
    row = rows[0]
    assert row["folder"] == "inbox/test"
    assert row["filename"] == "/data/inbox/test/bad.edi"
    assert row["error_message"] == "boom"
    assert row["error_type"] == "ValueError"
    assert row["error_source"] == "Validator"
    assert row["timestamp"]


# ---------------------------------------------------------------------------
# list_errors
# ---------------------------------------------------------------------------


def test_list_errors_newest_first(settings):
    _record(settings, folder_name="inbox/test", filename="a.edi", message="first")
    _record(settings, folder_name="inbox/test", filename="b.edi", message="second")

    db = open_database(settings)
    try:
        rows = list_errors(db)
    finally:
        db.close()

    assert [r["filename"] for r in rows] == ["b.edi", "a.edi"]


def test_list_errors_filters_by_folder_id(settings):
    fid = _insert_folder(settings, folder_name="inbox/test", alias="TEST")
    _insert_folder(settings, folder_name="inbox/other", alias="OTHER")
    _record(settings, folder_name="inbox/test", filename="a.edi")
    _record(settings, folder_name="inbox/other", filename="b.edi")

    db = open_database(settings)
    try:
        rows = list_errors(db, folder_id=fid)
    finally:
        db.close()

    assert [r["filename"] for r in rows] == ["a.edi"]


def test_list_errors_matches_absolute_folder_paths(settings):
    """The pipeline records the *resolved* folder_name (absolute path);
    the folder filter must still match the stored relative name."""
    fid = _insert_folder(settings, folder_name="inbox/test")
    resolved = str(settings.base_dir / "inbox/test")
    _record(settings, folder_name=resolved, filename="a.edi")

    db = open_database(settings)
    try:
        rows = list_errors(db, folder_id=fid)
    finally:
        db.close()

    assert len(rows) == 1
    assert rows[0]["folder"] == resolved


def test_list_errors_unknown_folder_id_returns_empty(settings):
    _record(settings, folder_name="inbox/test", filename="a.edi")

    db = open_database(settings)
    try:
        rows = list_errors(db, folder_id=9999)
    finally:
        db.close()

    assert rows == []


def test_list_errors_respects_limit(settings):
    for i in range(5):
        _record(settings, folder_name="inbox/test", filename=f"f{i}.edi")

    db = open_database(settings)
    try:
        rows = list_errors(db, limit=2)
    finally:
        db.close()

    assert len(rows) == 2
    assert rows[0]["filename"] == "f4.edi"


# ---------------------------------------------------------------------------
# clear_errors
# ---------------------------------------------------------------------------


def test_clear_errors_clears_all(settings):
    _record(settings, folder_name="inbox/test", filename="a.edi")
    _record(settings, folder_name="inbox/other", filename="b.edi")

    db = open_database(settings)
    try:
        cleared = clear_errors(db)
        rows = list_errors(db)
    finally:
        db.close()

    assert cleared == 2
    assert rows == []


def test_clear_errors_filters_by_folder_id(settings):
    fid = _insert_folder(settings, folder_name="inbox/test")
    _record(settings, folder_name="inbox/test", filename="a.edi")
    _record(settings, folder_name="inbox/other", filename="b.edi")

    db = open_database(settings)
    try:
        cleared = clear_errors(db, folder_id=fid)
        rows = list_errors(db)
    finally:
        db.close()

    assert cleared == 1
    assert [r["filename"] for r in rows] == ["b.edi"]


# ---------------------------------------------------------------------------
# insert_error: dedupe + MAX_ERROR_ROWS trim
# ---------------------------------------------------------------------------


def test_insert_error_records_a_row(settings):
    db = open_database(settings)
    try:
        inserted = insert_error(
            db, folder="/data/inbox/test", error_message="folder missing"
        )
        rows = list_errors(db, limit=100)
    finally:
        db.close()
    assert inserted is True
    assert len(rows) == 1
    assert rows[0]["error_message"] == "folder missing"


def test_insert_error_dedupes_consecutive_identical(settings):
    """The same failure twice in a row records only one row (the watcher
    ticks every few seconds; a permanent failure must not spam the
    ledger)."""
    db = open_database(settings)
    try:
        first = insert_error(
            db, folder="/data/inbox/test", error_message="folder missing", dedupe=True
        )
        second = insert_error(
            db, folder="/data/inbox/test", error_message="folder missing", dedupe=True
        )
        rows = list_errors(db, limit=100)
    finally:
        db.close()
    assert first is True
    assert second is False
    assert len(rows) == 1


def test_insert_error_records_when_message_changes(settings):
    """A *different* failure is a new episode and gets its own row."""
    db = open_database(settings)
    try:
        insert_error(
            db, folder="/data/inbox/test", error_message="folder missing", dedupe=True
        )
        insert_error(
            db,
            folder="/data/inbox/test",
            error_message="permission denied",
            dedupe=True,
        )
        rows = list_errors(db, limit=100)
    finally:
        db.close()
    assert len(rows) == 2
    assert [r["error_message"] for r in rows] == [
        "permission denied",
        "folder missing",
    ]


def test_insert_error_dedupe_is_per_folder(settings):
    """Identical messages for different folders are separate rows."""
    db = open_database(settings)
    try:
        insert_error(
            db, folder="/data/inbox/acme", error_message="folder missing", dedupe=True
        )
        insert_error(
            db, folder="/data/inbox/gamma", error_message="folder missing", dedupe=True
        )
        rows = list_errors(db, limit=100)
    finally:
        db.close()
    assert len(rows) == 2


def test_insert_error_records_again_after_clear(settings):
    """Dedupe compares against the ledger, so clearing resets the episode."""
    db = open_database(settings)
    try:
        insert_error(
            db, folder="/data/inbox/test", error_message="folder missing", dedupe=True
        )
        clear_errors(db)
        again = insert_error(
            db,
            folder="/data/inbox/test",
            error_message="folder missing",
            dedupe=True,
        )
        rows = list_errors(db, limit=100)
    finally:
        db.close()
    assert again is True
    assert len(rows) == 1


def test_insert_error_trims_oldest_rows_beyond_cap(settings, monkeypatch):
    """The ledger is bounded by MAX_ERROR_ROWS (mirroring history.py's
    trim-on-write); the newest rows survive."""
    monkeypatch.setattr("webapp.errors.MAX_ERROR_ROWS", 5)
    db = open_database(settings)
    try:
        for i in range(7):
            insert_error(
                db, folder=f"/data/inbox/f{i}", error_message=f"error {i}"
            )
        rows = list_errors(db, limit=100)
    finally:
        db.close()
    assert len(rows) == 5
    # Newest five survive, in newest-first order.
    assert [r["error_message"] for r in rows] == [
        "error 6",
        "error 5",
        "error 4",
        "error 3",
        "error 2",
    ]


def test_clear_errors_unknown_folder_id_returns_zero(settings):
    _record(settings, folder_name="inbox/test", filename="a.edi")

    db = open_database(settings)
    try:
        cleared = clear_errors(db, folder_id=9999)
    finally:
        db.close()

    assert cleared == 0


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------


@pytest.fixture
def client_with_db(settings):
    app = create_app(settings=settings)
    return TestClient(app)


def test_api_errors_requires_database(tmp_path):
    settings = Settings(base_dir=tmp_path / "data", data_dir=tmp_path / "data" / "config")
    settings.ensure_dirs()
    client = TestClient(create_app(settings=settings))

    resp = client.get("/api/errors")
    assert resp.status_code == 503

    resp = client.post("/api/errors/clear")
    assert resp.status_code == 503


def test_api_errors_empty(client_with_db, settings):
    _insert_folder(settings)

    resp = client_with_db.get("/api/errors")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 0
    assert body["errors"] == []


def test_api_errors_returns_rows(client_with_db, settings):
    _insert_folder(settings, folder_name="inbox/test")
    _record(settings, folder_name="inbox/test", filename="bad.edi", message="boom")

    resp = client_with_db.get("/api/errors")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1
    assert body["errors"][0]["filename"] == "bad.edi"
    assert body["errors"][0]["error_message"] == "boom"
    assert body["errors"][0]["error_type"] == "ValueError"


def test_api_errors_filter_by_folder_id(client_with_db, settings):
    fid = _insert_folder(settings, folder_name="inbox/test")
    _insert_folder(settings, folder_name="inbox/other")
    _record(settings, folder_name="inbox/test", filename="a.edi")
    _record(settings, folder_name="inbox/other", filename="b.edi")

    resp = client_with_db.get(f"/api/errors?folder_id={fid}")
    assert resp.status_code == 200
    body = resp.json()
    assert [e["filename"] for e in body["errors"]] == ["a.edi"]


def test_api_errors_clear(client_with_db, settings):
    _record(settings, folder_name="inbox/test", filename="a.edi")
    _record(settings, folder_name="inbox/test", filename="b.edi")

    resp = client_with_db.post("/api/errors/clear")
    assert resp.status_code == 200
    assert resp.json() == {"cleared": 2}

    body = client_with_db.get("/api/errors").json()
    assert body["count"] == 0


# ---------------------------------------------------------------------------
# End-to-end: a real failing run lands a ledger row
# ---------------------------------------------------------------------------


def test_failing_run_records_error_in_ledger(settings):
    """Real path: folder run → pipeline raises inside ``_send_file``
    (invalid rename template) → ``record_error`` → ``dispatch_errors``
    row → visible via GET /api/errors, filterable by folder id."""
    # ``rename_file=".."`` survives the sanitizer (dots are legal) and
    # trips ``apply_file_rename``'s traversal guard — but only for a file
    # with no extension, since a ``.edi`` suffix would be appended to the
    # template before validation and make it legal.
    fid = _insert_folder(
        settings,
        folder_name="inbox/test",
        alias="TEST",
        rename_file="..",
    )
    inbox = settings.base_dir / "inbox" / "test"
    inbox.mkdir(parents=True)
    (inbox / "failfile").write_bytes(b"HEADER line\nDETAIL line\n")

    client = TestClient(create_app(settings=settings))
    resp = client.post(f"/api/folders/{fid}/run")
    assert resp.status_code == 200, resp.text
    run_id = resp.json()["run_id"]

    detail = {}
    for _ in range(50):  # up to ~5s
        time.sleep(0.1)
        detail = client.get(f"/api/runs/{run_id}").json()
        if detail["status"] != "running":
            break
    assert detail["status"] == "completed"
    assert detail["total_failed"] >= 1

    body = client.get("/api/errors").json()
    assert body["count"] == 1
    row = body["errors"][0]
    assert row["error_type"] == "ValueError"
    assert "pattern" in row["error_message"].lower()
    assert (row["filename"] or "").endswith("failfile")

    # The folder filter must match even though the pipeline stored the
    # resolved (absolute) folder path.
    filtered = client.get(f"/api/errors?folder_id={fid}").json()
    assert filtered["count"] == 1
