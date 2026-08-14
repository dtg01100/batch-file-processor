"""Tests for the per-format converter configuration (converters API + merge)."""

from __future__ import annotations

import contextlib

import pytest
from fastapi.testclient import TestClient

from webapp.config import Settings
from webapp.converters_api import (
    CONVERTER_FORMATS,
    all_converter_specs,
    merge_plugin_config,
)
from webapp.database import open_database
from webapp.main import create_app

pytestmark = [pytest.mark.integration]


def test_registry_covers_eleven_formats():
    """The registry matches the 11 converter modules + desktop plugin UIs."""
    assert set(CONVERTER_FORMATS) == {
        "csv",
        "scannerware",
        "simplified_csv",
        "estore_einvoice",
        "estore_einvoice_generic",
        "fintech",
        "tweaks",
        "jolley_custom",
        "stewarts_custom",
        "scansheet_type_a",
        "yellowdog_csv",
    }
    # Formats with declared fields carry typed specs.
    csv_spec = CONVERTER_FORMATS["csv"]
    assert csv_spec["display_name"] == "CSV"
    keys = {f["key"] for f in csv_spec["fields"]}
    assert "include_headers" in keys and "filter_ampersand" in keys
    assert all(
        f["type"] in ("string", "boolean", "integer", "select")
        for f in csv_spec["fields"]
    )


def test_converters_endpoint_returns_specs(tmp_path):
    settings = Settings(
        base_dir=tmp_path / "data", data_dir=tmp_path / "data" / "config"
    )
    app = create_app(settings=settings)
    c = TestClient(app)
    body = c.get("/api/converters").json()
    assert len(body) == 11
    by_format = {spec["format"]: spec for spec in body}
    assert by_format["scannerware"]["display_name"] == "ScannerWare"
    field_keys = {f["key"] for f in by_format["scannerware"]["fields"]}
    assert "a_record_padding" in field_keys and "retail_uom" in field_keys
    tweaks = by_format["tweaks"]["fields"]
    arec_len = next(f for f in tweaks if f["key"] == "a_record_padding_length")
    assert arec_len["type"] == "select"
    assert arec_len["options"] == [6, 30]


def test_all_converter_specs_normalizes_format_keys():
    for spec in all_converter_specs():
        assert spec["format"] == spec["format"].lower()
        assert "display_name" in spec and "fields" in spec


def test_merge_plugin_config_applies_matching_format():
    folder = {
        "folder_name": "inbox/x",
        "convert_to_format": "ScannerWare",
        "force_txt_file_ext": False,
        "plugin_configurations": {
            "scannerware": {"force_txt_file_ext": True, "retail_uom": True}
        },
    }
    merged = merge_plugin_config(folder)
    assert merged["force_txt_file_ext"] is True
    assert merged["retail_uom"] is True
    # Unrelated keys survive; the original is untouched.
    assert merged["folder_name"] == "inbox/x"
    assert folder["force_txt_file_ext"] is False


def test_merge_plugin_config_case_insensitive_format():
    folder = {
        "convert_to_format": "simplified_csv",
        "plugin_configurations": {"SIMPLIFIED_CSV": {"include_headers": True}},
    }
    merged = merge_plugin_config(folder)
    assert merged["include_headers"] is True


def test_merge_plugin_config_noop_without_config():
    folder = {"folder_name": "inbox/x", "convert_to_format": "csv"}
    merged = merge_plugin_config(folder)
    assert merged == folder
    folder2 = {
        "folder_name": "inbox/x",
        "convert_to_format": "csv",
        "plugin_configurations": {"csv": {}},
    }
    assert merge_plugin_config(folder2) == folder2


def test_merge_plugin_config_ignores_unknown_format():
    folder = {
        "convert_to_format": "bogus_format",
        "plugin_configurations": {"bogus_format": {"x": 1}},
    }
    merged = merge_plugin_config(folder)
    assert "x" not in merged


def test_plugin_configurations_round_trips_through_api(tmp_path, legacy_db):
    """Saving a folder persists plugin_configurations; GET returns them."""
    settings = Settings(
        base_dir=tmp_path / "data", data_dir=tmp_path / "data" / "config"
    )
    from webapp.importer import import_database

    import_database(legacy_db, settings, platform="Windows")
    c = TestClient(create_app(settings=settings))

    folders = c.get("/api/folders").json()
    fid = folders[0]["id"]

    schema = c.get(f"/api/folders/{fid}").json()
    schema.setdefault("edi", {})["convert_to_format"] = "ScannerWare"
    schema["plugin_configurations"] = {
        "scannerware": {"force_txt_file_ext": True, "retail_uom": True}
    }
    r = c.put(f"/api/folders/{fid}", json=schema)
    assert r.status_code == 200, r.text
    assert (
        r.json()["plugin_configurations"]["scannerware"]["force_txt_file_ext"] is True
    )

    # The DB row stores it as JSON; a fresh GET sees it.
    assert (
        c.get(f"/api/folders/{fid}").json()["plugin_configurations"]["scannerware"][
            "force_txt_file_ext"
        ]
        is True
    )

    # The list payload carries the config too (read-only audit view).
    summary = c.get("/api/folders").json()
    audited = next(f for f in summary if f["id"] == fid)
    assert audited["convert_to_format"] == "scannerware"
    assert audited["plugin_configurations"]["scannerware"]["retail_uom"] is True

    # And the runner merges it into the folder handed to the dispatcher.
    db = open_database(settings)
    try:
        row = db.folders_table.find_one(id=fid)
        merged = merge_plugin_config(row)
        assert merged["force_txt_file_ext"] is True
    finally:
        with contextlib.suppress(Exception):
            db.close()


@pytest.fixture
def legacy_db(tmp_path):
    import shutil

    src = __import__("tests.conftest", fromlist=["LEGACY_DB_PATH"]).LEGACY_DB_PATH
    if not src.exists():
        pytest.skip("Legacy v32 database fixture not found")
    dst = tmp_path / "source_folders.db"
    shutil.copy2(src, dst)
    return dst
