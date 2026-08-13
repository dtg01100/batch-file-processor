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
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dispatch.error_handler import ErrorHandler
from webapp.config import Settings
from webapp.database import open_database
from webapp.errors import (
    LedgerDatabase,
    clear_errors,
    dedupe_matches,
    error_counts,
    folder_error_text,
    insert_error,
    link_error_files,
    list_errors,
    max_error_id,
    write_error_artifact,
)
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


def test_insert_error_records_error_file(settings):
    """Open question #2: an insert can carry the raw artifact path."""
    db = open_database(settings)
    try:
        insert_error(
            db,
            folder="/data/inbox/test",
            error_message="boom",
            error_file="/tmp/errs/test errors.2026-08-12_14-00-00.txt",
        )
        rows = list_errors(db, limit=100)
    finally:
        db.close()
    assert rows[0]["error_file"] == "/tmp/errs/test errors.2026-08-12_14-00-00.txt"


def test_write_error_artifact_uses_legacy_naming(settings):
    """Watcher artifacts reuse the dispatch naming so the Errors card
    treats them identically: ``errors/<folder>/<alias> errors.<ts>.txt``."""
    path = write_error_artifact(
        str(settings.errors_dir),
        alias="GAMMA",
        folder_path="/data/inbox/gamma",
        timestamp="2026-08-12T14:05:00.000000",
        text="At: now\nError Message is:\nboom\n",
    )
    assert path == str(
        settings.errors_dir / "gamma" / "GAMMA errors.2026-08-12_14-05-00.txt"
    )
    assert Path(path).is_file()
    assert "boom" in Path(path).read_text(encoding="utf-8")


def test_dedupe_matches_tracks_latest_row(settings):
    """The watcher uses this to skip writing an artifact when the failure
    is a repeat of the latest row for the same folder."""
    db = open_database(settings)
    try:
        insert_error(
            db,
            folder="/d/inbox/test",
            error_message="folder missing",
            error_type="WatcherScanError",
            error_source="FolderWatcher",
        )
        assert dedupe_matches(
            db,
            folder="/d/inbox/test",
            error_message="folder missing",
            error_type="WatcherScanError",
            error_source="FolderWatcher",
        ) is True
        # A changed message / different folder is a new episode.
        assert dedupe_matches(
            db,
            folder="/d/inbox/test",
            error_message="permission denied",
            error_type="WatcherScanError",
            error_source="FolderWatcher",
        ) is False
        assert dedupe_matches(
            db,
            folder="/d/inbox/other",
            error_message="folder missing",
            error_type="WatcherScanError",
            error_source="FolderWatcher",
        ) is False
    finally:
        db.close()


def test_max_error_id_tracks_ledger_watermark(settings):
    """The runner snapshots MAX(id) before a folder run so it can link
    exactly that run's rows to the raw artifact afterwards."""
    db = open_database(settings)
    try:
        assert max_error_id(db) == 0  # empty ledger
        insert_error(db, folder="/d/x", error_message="a")
        first = max_error_id(db)
        assert first >= 1
        insert_error(db, folder="/d/x", error_message="b")
        assert max_error_id(db) == first + 1
    finally:
        db.close()


def test_link_error_files_updates_only_new_rows_for_folder(settings):
    """link_error_files points the rows a run produced (id > after_id,
    matching folder) at the raw file, leaving older/other rows alone."""
    db = open_database(settings)
    try:
        insert_error(db, folder="/d/inbox/test", error_message="old")
        before = max_error_id(db)
        insert_error(db, folder="/d/inbox/test", error_message="new1")
        insert_error(db, folder="/d/inbox/other", error_message="other")
        insert_error(db, folder="/d/inbox/test", error_message="new2")
        path = "/data/errors/test/ACME errors.2026-08-12_14-00-00.txt"

        linked = link_error_files(
            db, after_id=before, folder="/d/inbox/test", error_file=path
        )
        rows = list_errors(db, limit=100)
    finally:
        db.close()
    assert linked == 2  # new1 + new2, not the old row, not the other folder
    linked_rows = {r["error_message"] for r in rows if r["error_file"] == path}
    assert linked_rows == {"new1", "new2"}


def test_link_error_files_skips_already_linked_rows(settings):
    """Re-linking a row (e.g. an idempotent retry) must not clobber it."""
    db = open_database(settings)
    try:
        insert_error(db, folder="/d/x", error_message="a")
        before = max_error_id(db)
        insert_error(db, folder="/d/x", error_message="b")
        first_path = "/data/errors/x/one.txt"
        link_error_files(
            db, after_id=before, folder="/d/x", error_file=first_path
        )
        second = link_error_files(
            db, after_id=before, folder="/d/x", error_file="/data/errors/x/two.txt"
        )
        rows = list_errors(db, limit=100)
    finally:
        db.close()
    assert second == 0
    assert {r["error_file"] for r in rows if r["error_file"]} == {first_path}


def test_folder_error_text_concatenates_artifacts_and_falls_back(settings):
    """The folder-level download includes each row's raw artifact when
    linked, and synthesizes a block for rows without one."""
    fid = _insert_folder(settings, folder_name="inbox/test", alias="TEST")
    db = open_database(settings)
    try:
        artifact = write_error_artifact(
            str(settings.errors_dir),
            alias="TEST",
            folder_path=str(settings.base_dir / "inbox" / "test"),
            timestamp="2026-08-12T10:00:00.000000",
            text="At: t1\nError Message is:\nartifact boom\n",
        )
        insert_error(
            db,
            folder=str(settings.base_dir / "inbox" / "test"),
            error_message="artifact boom",
            error_file=artifact,
        )
        insert_error(
            db,
            folder=str(settings.base_dir / "inbox" / "test"),
            error_message="plain boom",
            error_type="ValueError",
        )
        text = folder_error_text(
            db, folder_id=fid, errors_dir=str(settings.errors_dir)
        )
    finally:
        db.close()
    # Both rows included, newest first (the plain row is newer).
    assert "artifact boom" in text
    assert "plain boom" in text
    assert text.index("plain boom") < text.index("artifact boom")
    # The row without a linked file still gets a synthesized block.
    assert "=== ValueError" in text
    assert "For object:" in text


def test_folder_error_text_skips_artifacts_outside_errors_dir(settings):
    """A tampered error_file must never be read — the folder download
    falls back to the synthesized block instead."""
    fid = _insert_folder(settings, folder_name="inbox/test", alias="TEST")
    db = open_database(settings)
    try:
        secret = settings.data_dir / "folders.db"
        insert_error(
            db,
            folder=str(settings.base_dir / "inbox" / "test"),
            error_message="boom",
            error_file=str(secret),
        )
        text = folder_error_text(
            db, folder_id=fid, errors_dir=str(settings.errors_dir)
        )
    finally:
        db.close()
    assert "boom" in text
    # Never any raw DB bytes leaking in.
    assert "SQLite format" not in text


def test_folder_error_text_returns_empty_for_no_rows(settings):
    fid = _insert_folder(settings, folder_name="inbox/test")
    db = open_database(settings)
    try:
        assert folder_error_text(db, folder_id=fid) == ""
    finally:
        db.close()


def test_error_counts_per_folder(settings):
    """Open question #3: total rows per folder id, counting rows recorded
    with the resolved absolute path against the stored relative name."""
    fid1 = _insert_folder(settings, folder_name="inbox/test", alias="TEST")
    fid2 = _insert_folder(settings, folder_name="inbox/other", alias="OTHER")
    _record(settings, folder_name="inbox/test", filename="a.edi")
    _record(settings, folder_name="inbox/test", filename="b.edi")
    _record(settings, folder_name=str(settings.base_dir / "inbox" / "test"), filename="c.edi")
    _record(settings, folder_name="inbox/other", filename="d.edi")

    db = open_database(settings)
    try:
        counts = error_counts(db)
    finally:
        db.close()
    assert counts == {fid1: 3, fid2: 1}


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


def test_api_errors_returns_folder_counts(client_with_db, settings):
    """The response carries per-folder totals for the dropdown labels."""
    fid = _insert_folder(settings, folder_name="inbox/test")
    _insert_folder(settings, folder_name="inbox/other")
    _record(settings, folder_name="inbox/test", filename="a.edi")
    _record(settings, folder_name="inbox/test", filename="b.edi")

    resp = client_with_db.get("/api/errors")
    assert resp.status_code == 200
    body = resp.json()
    # JSON serializes int dict keys to strings; the API contract is a
    # ``{folder_id: total}`` map.
    assert body["folder_counts"][str(fid)] == 2


def test_api_errors_file_download(client_with_db, settings):
    """GET /api/errors/file streams a raw artifact under errors_dir."""
    artifact = settings.errors_dir / "test" / "TEST errors.2026-08-12_14-00-00.txt"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("At: now\nError Message is: boom\n", encoding="utf-8")

    resp = client_with_db.get(
        "/api/errors/file", params={"path": str(artifact)}
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    assert "boom" in resp.text


def test_api_errors_folder_file_downloads_full_text(client_with_db, settings):
    """The banner's Download raw button hits this endpoint and gets the
    folder's whole error text as a text/plain attachment."""
    fid = _insert_folder(settings, folder_name="inbox/test", alias="TEST")
    _record(settings, folder_name="inbox/test", filename="bad.edi", message="boom")

    resp = client_with_db.get("/api/errors/folder-file", params={"folder_id": fid})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    assert "boom" in resp.text
    assert 'attachment; filename="TEST errors.txt"' in resp.headers[
        "content-disposition"
    ]


def test_api_errors_folder_file_unknown_folder(client_with_db, settings):
    _insert_folder(settings, folder_name="inbox/test")
    resp = client_with_db.get("/api/errors/folder-file", params={"folder_id": 9999})
    assert resp.status_code == 404


def test_api_errors_file_rejects_paths_outside_errors_dir(client_with_db, settings):
    """Path traversal guard: an operator-supplied path must stay under
    errors_dir, like the maintenance download endpoint."""
    secret = settings.data_dir / "folders.db"
    secret.touch()

    resp = client_with_db.get(
        "/api/errors/file", params={"path": str(secret)}
    )
    assert resp.status_code == 400

    resp = client_with_db.get(
        "/api/errors/file", params={"path": str(settings.errors_dir / "missing.txt")}
    )
    assert resp.status_code == 404


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

    # Open question #2: the runner wrote a raw error-text artifact for the
    # folder and linked the ledger row to it; the download endpoint serves
    # the exact text the pipeline recorded.
    assert row["error_file"], "row should link its raw artifact"
    artifact_path = Path(row["error_file"])
    assert artifact_path.is_file()
    raw = artifact_path.read_text(encoding="utf-8")
    assert "Error Message is:" in raw
    assert "pattern" in raw.lower()

    resp = client.get("/api/errors/file", params={"path": row["error_file"]})
    assert resp.status_code == 200
    assert "pattern" in resp.text.lower()


def _run_folder(client, fid) -> dict:
    """Start a single-folder run and wait for completion."""
    resp = client.post(f"/api/folders/{fid}/run")
    assert resp.status_code == 200, resp.text
    run_id = resp.json()["run_id"]
    detail = {}
    for _ in range(100):  # up to ~10s
        time.sleep(0.1)
        detail = client.get(f"/api/runs/{run_id}").json()
        if detail["status"] != "running":
            break
    assert detail["status"] == "completed"
    return detail


def test_edi_validation_major_problem_lands_ledger_row(settings):
    """Phase 5.5: a file that fails EDI format validation (major problem)
    records a ledger row with ``severity="major"``.

    Previously the validator step had no error handler wired, so EDI
    problems only appeared on the run card and never reached the errors
    ledger the watcher/pipeline exceptions used.
    """
    fid = _insert_folder(
        settings,
        folder_name="inbox/test",
        alias="TEST",
        process_edi=True,
        copy_to_directory="archive/test",
    )
    inbox = settings.base_dir / "inbox" / "test"
    inbox.mkdir(parents=True)
    # First char not 'A' → format check fails on line 1 (major problem).
    (inbox / "bad.edi").write_text("XNOTANEDI\n", encoding="utf-8")

    client = TestClient(create_app(settings=settings))
    detail = _run_folder(client, fid)
    assert detail["total_failed"] >= 1

    body = client.get("/api/errors").json()
    assert body["count"] >= 1
    row = next(
        (e for e in body["errors"] if (e["filename"] or "").endswith("bad.edi")),
        None,
    )
    assert row is not None
    assert row["error_type"] == "ValidationError"
    assert row["error_source"] == "EDIValidator"
    assert row["severity"] == "major"
    assert "EDI check failed" in row["error_message"]

    # The row carries the resolved folder path so folder filtering works.
    filtered = client.get(f"/api/errors?folder_id={fid}").json()
    assert filtered["count"] >= 1


def test_edi_validation_minor_problem_lands_ledger_row(settings):
    """Phase 5.5: a file that passes format checks but has a UPC warning
    (minor problem) records a ``severity="minor"`` row while still
    processing successfully.
    """
    fid = _insert_folder(
        settings,
        folder_name="inbox/test",
        alias="TEST",
        process_edi=True,
        # A no-op-ish converter that still produces output so the file
        # ships (validation must run, so process_edi=True is required;
        # with an empty convert_to_format the converter produces nothing
        # and the file fails with "No converted output was produced").
        convert_to_format="tweaks",
        copy_to_directory="archive/test",
    )
    inbox = settings.base_dir / "inbox" / "test"
    inbox.mkdir(parents=True)
    # A real convertible EDI (the estore sample shape) whose B-record UPC
    # is non-numeric → minor issue. The B record must be exactly 76 chars
    # (EDI_B_RECORD_STANDARD_LENGTH) to pass the format check. The file
    # must still process: minor problems don't block.
    b_record = "B" + "ABCDEFGHIJK" + (
        "Test Item Description    1234560001000100000100010991001000000"
    )
    b_record = b_record.ljust(76)
    assert len(b_record) == 76
    content = (
        "AVENDOR00000000010101250000100000\n"
        f"{b_record}\n"
        "CTABSales Tax                 000010000\n"
    )
    (inbox / "minor.edi").write_text(content, encoding="utf-8")

    client = TestClient(create_app(settings=settings))
    detail = _run_folder(client, fid)
    # Minor problems don't block: the file is converted and sent.
    assert detail["total_processed"] >= 1, detail
    assert detail["total_failed"] == 0, detail

    body = client.get("/api/errors").json()
    row = next(
        (e for e in body["errors"] if (e["filename"] or "").endswith("minor.edi")),
        None,
    )
    assert row is not None
    assert row["severity"] == "minor"
    assert "Non-numeric UPC" in row["error_message"]
