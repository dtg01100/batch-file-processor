"""Integration tests for webapp.importer using the real legacy fixture DB."""

import contextlib
import shutil
import sqlite3

import pytest

from webapp.config import Settings
from webapp.database import open_database
from webapp.importer import import_database

pytestmark = [pytest.mark.integration]


@pytest.fixture
def legacy_db(tmp_path):
    """Copy the real legacy v32 database fixture."""
    src = __import__("tests.conftest", fromlist=["LEGACY_DB_PATH"]).LEGACY_DB_PATH
    if not src.exists():
        pytest.skip("Legacy v32 database fixture not found")
    dst = tmp_path / "source_folders.db"
    shutil.copy2(src, dst)
    return dst


def test_import_rebases_paths_and_installs_active_db(tmp_path, legacy_db):
    settings = Settings(
        base_dir=tmp_path / "data", data_dir=tmp_path / "data" / "config"
    )
    result = import_database(legacy_db, settings, platform="Windows")

    assert result.folders_imported > 0
    assert result.rebased_paths > 0
    assert result.source_platform == "Windows"
    assert result.database_path == str(settings.database_path)
    assert settings.database_path.is_file()

    db = open_database(settings)
    try:
        # Every folder path must now be relative (no drive letter, no leading /).
        rows = list(db.folders_table.all())
        assert rows, "imported DB should have folder rows"
        for row in rows:
            folder_name = str(row.get("folder_name") or "")
            if folder_name:
                assert ":" not in folder_name.split("/")[0] or len(folder_name) < 2
                assert not folder_name.startswith("/"), folder_name

        # Provenance recorded.
        assert db.get_setting("webapp.source_platform") == "Windows"
        assert db.get_setting("webapp.base_directory") == str(settings.base_dir)
    finally:
        with contextlib.suppress(Exception):
            db.close()


def test_imported_db_has_webapp_write_columns(tmp_path, legacy_db):
    """Every column the webapp writes on folder edit exists post-import.

    Regression: the v32 desktop DB (and the v32→v51 migration) never
    had ``alert_on_failure``; the webapp's ``PUT /api/folders/{id}``
    writes it unconditionally, so folder editing 500'd with
    ``no such column: alert_on_failure`` after importing the real
    fixture. ``open_database`` backfills it via ``_ensure_columns``.
    """
    settings = Settings(
        base_dir=tmp_path / "data", data_dir=tmp_path / "data" / "config"
    )
    import_database(legacy_db, settings, platform="Windows")

    db = open_database(settings)
    try:
        conn = db.database_connection.raw_connection
        cols = {
            r[1]
            for r in conn.execute("PRAGMA table_info(folders)").fetchall()
        }
        assert "alert_on_failure" in cols
        # Existing rows default to enabled (1) so alerts aren't
        # silently disabled for imported folders.
        row = conn.execute(
            "SELECT alert_on_failure FROM folders LIMIT 1"
        ).fetchone()
        assert row is not None and row[0] == 1
    finally:
        with contextlib.suppress(Exception):
            db.close()


def test_imported_db_has_settings_columns(tmp_path, legacy_db):
    """The settings table carries every column the settings API writes.

    Regression: the v32 desktop DB (and its migration) never had
    ``ssh_key_filename``; ``PUT /api/settings`` writes it, so saving
    settings on an imported DB 500'd with ``no such column:
    ssh_key_filename``. ``open_database`` backfills it via
    ``_ensure_columns``.
    """
    settings = Settings(
        base_dir=tmp_path / "data", data_dir=tmp_path / "data" / "config"
    )
    import_database(legacy_db, settings, platform="Windows")

    db = open_database(settings)
    try:
        conn = db.database_connection.raw_connection
        cols = {
            r[1]
            for r in conn.execute("PRAGMA table_info(settings)").fetchall()
        }
        assert "ssh_key_filename" in cols
    finally:
        with contextlib.suppress(Exception):
            db.close()


def test_import_migrates_legacy_version(tmp_path, legacy_db):
    """The imported DB is migrated to the current schema (version table + kv_settings exist)."""
    settings = Settings(
        base_dir=tmp_path / "data", data_dir=tmp_path / "data" / "config"
    )
    import_database(legacy_db, settings, platform="Windows")

    conn = sqlite3.connect(settings.database_path)
    try:
        tables = {
            r[0]
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert "kv_settings" in tables
        assert "processed_files" in tables
        version = conn.execute("SELECT version FROM version WHERE id=1").fetchone()
        assert version is not None and int(version[0]) >= 1
    finally:
        conn.close()


def test_import_detects_platform_when_not_specified(tmp_path, legacy_db):
    settings = Settings(
        base_dir=tmp_path / "data", data_dir=tmp_path / "data" / "config"
    )
    result = import_database(legacy_db, settings)
    assert result.source_platform  # detected, non-empty


def test_import_missing_file_raises(tmp_path):
    settings = Settings(
        base_dir=tmp_path / "data", data_dir=tmp_path / "data" / "config"
    )
    with pytest.raises(ValueError, match="not found"):
        import_database(tmp_path / "nope.db", settings)


def test_import_non_sqlite_file_raises_value_error(tmp_path):
    """A malformed upload raises ValueError (→ 400), not sqlite3.DatabaseError (→ 500)."""
    settings = Settings(
        base_dir=tmp_path / "data", data_dir=tmp_path / "data" / "config"
    )
    bogus = tmp_path / "not_a_db.db"
    bogus.write_text("this is not a database\n", encoding="utf-8")
    with pytest.raises(ValueError, match="not a SQLite database"):
        import_database(bogus, settings)
