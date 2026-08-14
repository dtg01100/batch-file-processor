"""Tests for the folder-edit HTTP endpoints + schema translation."""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from webapp.config import Settings
from webapp.database import open_database
from webapp.folder_schema import (
    FolderEditSchema,
    folder_row_to_schema,
    schema_to_folder_row,
)
from webapp.main import create_app

pytestmark = [pytest.mark.integration]


@pytest.fixture
def client(tmp_path: Path):
    """A TestClient backed by a fresh folder database with one row seeded."""
    settings = Settings(base_dir=tmp_path / "data", data_dir=tmp_path / "data" / "config")
    settings.ensure_dirs()
    db = open_database(settings)
    db.folders_table.insert(
        {
            "folder_name": "inbox/test",
            "folder_is_active": True,
            "alias": "TEST",
            "process_backend_copy": True,
            "copy_to_directory": "archive/test",
            "process_backend_ftp": True,
            "ftp_server": "a.example.com",
            "ftp_port": 21,
            "ftp_username": "u",
            "ftp_password": "p",
            "ftp_folder": "/uploads/",
            "process_backend_email": False,
            "process_backend_http": False,
            "created_at": datetime.datetime.now().isoformat(),
        }
    )
    db.close()
    app = create_app(settings=settings)
    return TestClient(app)


# ---------------------------------------------------------------------------
# Schema round-trip
# ---------------------------------------------------------------------------


def test_schema_roundtrip_preserves_every_field():
    """Every column set by ``schema_to_folder_row`` round-trips back."""
    row = {
        "id": 1,
        "folder_name": "x",
        "folder_is_active": True,
        "alias": "ALIAS",
        "process_backend_copy": True,
        "process_backend_ftp": True,
        "process_backend_email": False,
        "process_backend_http": False,
        "alert_on_failure": True,
        "max_duration_seconds": 90,
        "max_failure_rate_percent": 5,
        "ftp_server": "ftp.example.com",
        "ftp_port": 2121,
        "ftp_username": "user",
        "ftp_password": "pw",
        "ftp_folder": "/out/",
        "email_to": "ops@example.com",
        "email_subject_line": "Daily",
        "copy_to_directory": "out/x",
        "convert_to_format": "csv",
        "process_edi": True,
        "split_edi": True,
        "split_edi_include_invoices": True,
        "split_edi_include_credits": False,
        "prepend_date_files": False,
        "tweak_edi": True,
        "force_edi_validation": False,
        "rename_file": "",
        "split_edi_filter_categories": "ALL",
        "split_edi_filter_mode": "include",
        "override_upc_bool": True,
        "override_upc_level": 2,
        "override_upc_category_filter": "1,2,3",
        "upc_target_length": 12,
        "upc_padding_pattern": "0",
        "pad_a_records": False,
        "a_record_padding": "",
        "a_record_padding_length": 6,
        "a_record_append_text": "",
        "append_a_records": False,
        "force_txt_file_ext": False,
        "invoice_date_offset": 1,
        "invoice_date_custom_format": True,
        "invoice_date_custom_format_string": "%Y-%m-%d",
        "retail_uom": False,
        "each_uom_categories": "1,2",
        "each_uom_mode": "exclude",
        "estore_store_number": "1234",
        "estore_Vendor_OId": "v1",
        "estore_vendor_NameVendorOID": "n1",
        "estore_c_record_OID": "c1",
        "fintech_division_id": "F-1",
        "include_headers": True,
        "filter_ampersand": False,
        "include_item_numbers": True,
        "include_item_description": False,
        "simple_csv_sort_order": "asc",
        "split_prepaid_sales_tax_crec": False,
        "plugin_configurations": {},
    }
    schema = folder_row_to_schema(row)
    flat = schema_to_folder_row(schema)
    # Every populated input column survives the round-trip.
    for key, value in row.items():
        if value in (None, "") and key != "id":
            continue
        assert flat.get(key) == value, f"{key}: {flat.get(key)!r} != {value!r}"


def test_schema_coerces_legacy_integer_backend_specific_cells():
    """Legacy DBs store backend-specific ids as ints; the schema needs str.

    Without coercion, ``GET /api/folders/{id}`` raised a Pydantic
    ``ValidationError`` → HTTP 500 for every imported legacy folder
    (``estore_c_record_OID`` etc. are integers in the v32 desktop DB).
    """
    row = {
        "id": 7,
        "folder_name": "x",
        "estore_store_number": 338,
        "estore_Vendor_OId": 338,
        "estore_vendor_NameVendorOID": "n1",
        "estore_c_record_OID": 10025,
        "fintech_division_id": 445,
    }
    schema = folder_row_to_schema(row)
    assert schema.backend_specific is not None
    assert schema.backend_specific.estore_store_number == "338"
    assert schema.backend_specific.estore_vendor_oid == "338"
    assert schema.backend_specific.estore_vendor_namevendoroid == "n1"
    assert schema.backend_specific.estore_c_record_oid == "10025"
    assert schema.backend_specific.fintech_division_id == "445"
    # The schema validates cleanly (this is what used to 500).
    schema.model_dump()


def test_schema_coerces_null_backend_specific_cells():
    """NULL backend-specific cells become empty strings, not 'None'."""
    schema = folder_row_to_schema({"id": 1, "folder_name": "x"})
    assert schema.backend_specific is not None
    assert schema.backend_specific.estore_store_number == ""
    assert schema.backend_specific.estore_c_record_oid == ""
    assert schema.backend_specific.fintech_division_id == ""


def test_get_folder_with_legacy_integer_backend_specific(client):
    """End-to-end: a folder with integer backend-specific cells loads (200)."""
    settings = client.app.state.settings
    db = open_database(settings)
    db.folders_table.insert(
        {
            "folder_name": "legacy/int",
            "folder_is_active": True,
            "alias": "LEGACY",
            "process_backend_copy": True,
            "copy_to_directory": "out",
            "process_backend_ftp": False,
            "process_backend_email": False,
            "process_backend_http": False,
            "estore_store_number": 338,
            "estore_Vendor_OId": 338,
            "estore_c_record_OID": 10025,
            "fintech_division_id": 445,
        }
    )
    db.close()
    r = client.get("/api/folders/2")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["backend_specific"]["estore_c_record_oid"] == "10025"
    assert body["backend_specific"]["estore_store_number"] == "338"


def test_schema_to_row_omits_unconfigured_backends():
    """Backend columns are only emitted when the nested config is non-None."""
    schema = FolderEditSchema(
        id=1,
        folder_name="x",
        ftp=None,
        email=None,
        copy_backend=None,
        http=None,
    )
    row = schema_to_folder_row(schema)
    for backend_col in (
        "ftp_server",
        "ftp_port",
        "email_to",
        "copy_to_directory",
        "http_url",
    ):
        assert backend_col not in row, f"{backend_col} should be omitted"


# ---------------------------------------------------------------------------
# GET /api/folders/{id}
# ---------------------------------------------------------------------------


def test_get_folder_returns_full_schema(client):
    r = client.get("/api/folders/1")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == 1
    assert body["alias"] == "TEST"
    assert body["folder_name"] == "inbox/test"
    assert body["ftp"] is not None
    assert body["ftp"]["server"] == "a.example.com"
    assert body["ftp"]["port"] == 21


def test_get_folder_404_when_id_unknown(client):
    r = client.get("/api/folders/999")
    assert r.status_code == 404


def test_get_folder_503_when_no_database(tmp_path):
    settings = Settings(base_dir=tmp_path / "data", data_dir=tmp_path / "data" / "config")
    settings.ensure_dirs()
    # Don't seed anything; database file doesn't exist yet.
    app = create_app(settings=settings)
    no_db_client = TestClient(app)
    r = no_db_client.get("/api/folders/1")
    assert r.status_code == 503


# ---------------------------------------------------------------------------
# PUT /api/folders/{id}
# ---------------------------------------------------------------------------


def test_put_folder_persists_changes(client):
    r = client.get("/api/folders/1")
    body = r.json()
    body["alias"] = "TEST-RENAMED"
    body["ftp"]["server"] = "ftp.changed.example.com"

    r = client.put("/api/folders/1", json=body)
    assert r.status_code == 200
    assert r.json()["alias"] == "TEST-RENAMED"
    assert r.json()["ftp"]["server"] == "ftp.changed.example.com"

    # Verify persistence directly in the DB so a future regression that
    # returns the response without writing the row is caught here.
    db = open_database(Settings(base_dir=client.app.state.settings.base_dir,
                                data_dir=client.app.state.settings.data_dir))
    row = db.folders_table.find_one(id=1)
    db.close()
    assert row["alias"] == "TEST-RENAMED"
    assert row["ftp_server"] == "ftp.changed.example.com"


def test_put_folder_persists_alert_thresholds(client):
    """Phase 5.3 follow-up: duration + failure-rate thresholds round-trip."""
    r = client.get("/api/folders/1")
    body = r.json()
    body["max_duration_seconds"] = 90
    body["max_failure_rate_percent"] = 5

    r = client.put("/api/folders/1", json=body)
    assert r.status_code == 200
    assert r.json()["max_duration_seconds"] == 90
    assert r.json()["max_failure_rate_percent"] == 5

    # Persisted in the DB (TEXT-affinity columns, so compare as strings).
    db = open_database(Settings(base_dir=client.app.state.settings.base_dir,
                                data_dir=client.app.state.settings.data_dir))
    row = db.folders_table.find_one(id=1)
    db.close()
    assert str(row["max_duration_seconds"]) == "90"
    assert str(row["max_failure_rate_percent"]) == "5"

    # GET re-reads them as ints (the editor's wire type).
    fetch = client.get("/api/folders/1")
    assert fetch.json()["max_duration_seconds"] == 90
    assert fetch.json()["max_failure_rate_percent"] == 5


def test_put_folder_rejects_invalid_thresholds(client):
    """Negative duration / out-of-range percent are rejected at the boundary."""
    r = client.get("/api/folders/1")
    body = r.json()
    body["max_duration_seconds"] = -1
    r = client.put("/api/folders/1", json=body)
    assert r.status_code == 422

    r = client.get("/api/folders/1")
    body = r.json()
    body["max_failure_rate_percent"] = 101
    r = client.put("/api/folders/1", json=body)
    assert r.status_code == 422


def test_put_folder_rejects_cross_field_violation(client):
    """``prepend_date_files`` requires ``split_edi`` — dataclass invariant."""
    r = client.get("/api/folders/1")
    body = r.json()
    body["edi"] = {
        "process_edi": True,
        "split_edi": False,
        "prepend_date_files": True,
        "split_edi_include_invoices": False,
        "split_edi_include_credits": False,
        "tweak_edi": False,
        "convert_to_format": "",
        "force_edi_validation": False,
        "rename_file": "",
        "split_edi_filter_categories": "ALL",
        "split_edi_filter_mode": "include",
    }
    r = client.put("/api/folders/1", json=body)
    assert r.status_code == 400
    assert "prepend_date_files" in r.json()["detail"]


def test_put_folder_rejects_id_mismatch(client):
    r = client.get("/api/folders/1")
    body = r.json()
    body["id"] = 999  # URL says 1, body says 999.
    r = client.put("/api/folders/1", json=body)
    assert r.status_code == 400
    assert "URL id" in r.json()["detail"]


def test_put_folder_rejects_unknown_fields(client):
    """``extra='forbid'`` on every Pydantic model catches typos."""
    r = client.get("/api/folders/1")
    body = r.json()
    body["bogus_field"] = "x"
    r = client.put("/api/folders/1", json=body)
    assert r.status_code == 422  # FastAPI's standard validation error.


def test_put_folder_404_when_id_unknown(client):
    """Even with a valid body shape, a non-existent id returns 404."""
    settings = client.app.state.settings
    db = open_database(settings)
    # Fetch a real schema body, then change its id to one that doesn't exist.
    schema = folder_row_to_schema(db.folders_table.find_one(id=1))
    db.close()
    schema.id = 999
    r = client.put("/api/folders/999", json=schema.model_dump())
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/folders (create) + DELETE /api/folders/{id}
# ---------------------------------------------------------------------------


def test_create_folder_inserts_and_returns_schema(client):
    """POST /api/folders creates a fresh row (db-assigned id) and returns
    the full edit schema so the UI can keep editing it."""
    r = client.post(
        "/api/folders",
        json={
            "folder_name": "inbox/new",
            "alias": "NEW",
            "folder_is_active": True,
            "process_backend_copy": True,
            "copy_backend": {"destination_directory": "archive/new"},
            "process_backend_ftp": False,
            "process_backend_email": False,
            "process_backend_http": False,
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["id"] not in (None, 1)  # a brand-new row, not the seeded one
    assert body["alias"] == "NEW"
    assert body["copy_backend"]["destination_directory"] == "archive/new"

    # Persisted, and loadable back through the edit endpoint.
    fetch = client.get(f"/api/folders/{body['id']}")
    assert fetch.status_code == 200
    assert fetch.json()["alias"] == "NEW"


def test_create_folder_ignores_caller_supplied_id(client):
    """A body id must not be honored — the DB owns the new row's id."""
    r = client.post(
        "/api/folders",
        json={"id": 999, "folder_name": "inbox/x", "alias": "X"},
    )
    assert r.status_code == 201
    assert r.json()["id"] != 999


def test_create_folder_rejects_cross_field_violation(client):
    """Create goes through the same FolderConfiguration invariants as PUT."""
    r = client.post(
        "/api/folders",
        json={
            "folder_name": "inbox/x",
            "alias": "X",
            "edi": {"process_edi": True, "split_edi": False, "prepend_date_files": True},
        },
    )
    assert r.status_code == 400
    assert "prepend_date_files" in r.json()["detail"]


def test_create_folder_503_when_no_database(tmp_path):
    settings = Settings(base_dir=tmp_path / "data", data_dir=tmp_path / "data" / "config")
    settings.ensure_dirs()
    app = create_app(settings=settings)
    no_db_client = TestClient(app)
    r = no_db_client.post("/api/folders", json={"folder_name": "x", "alias": "X"})
    assert r.status_code == 503


def test_delete_folder_removes_row_and_processed_history(client):
    """DELETE removes the folder row and its processed-files rows."""
    settings = client.app.state.settings
    r = client.post(
        "/api/folders",
        json={
            "folder_name": "inbox/tmp",
            "alias": "TMP",
            "process_backend_copy": True,
            "copy_backend": {"destination_directory": "archive/tmp"},
        },
    )
    new_id = r.json()["id"]

    db = open_database(settings)
    db.database_connection["processed_files"].insert(
        {
            "file_name": "inbox/tmp/a.edi",
            "folder_alias": "TMP",
            "folder_id": new_id,
            "processed_at": datetime.datetime.now().isoformat(),
            "status": "processed",
            "sent_to": "copy",
        }
    )
    db.close()

    resp = client.delete(f"/api/folders/{new_id}")
    assert resp.status_code == 200
    assert resp.json() == {"deleted": new_id}

    assert client.get(f"/api/folders/{new_id}").status_code == 404
    db = open_database(settings)
    try:
        row = db.database_connection.raw_connection.execute(
            "SELECT COUNT(*) AS n FROM processed_files WHERE folder_id = ?",
            (new_id,),
        ).fetchone()
        assert row[0] == 0
    finally:
        db.close()


def test_delete_folder_404_when_id_unknown(client):
    resp = client.delete("/api/folders/999")
    assert resp.status_code == 404


def test_delete_folder_503_when_no_database(tmp_path):
    settings = Settings(base_dir=tmp_path / "data", data_dir=tmp_path / "data" / "config")
    settings.ensure_dirs()
    app = create_app(settings=settings)
    no_db_client = TestClient(app)
    r = no_db_client.delete("/api/folders/1")
    assert r.status_code == 503
