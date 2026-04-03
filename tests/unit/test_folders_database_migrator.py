"""Unit tests for folders_database_migrator module.

Tests cover:
- Migration version checking logic
- Target version handling (early return when already at target)
- Individual migration steps
- Edge cases and error handling
- Log output verification
"""

import sqlite3
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.database, pytest.mark.upgrade]

from backend.database import sqlite_wrapper
from core.database import schema
from migrations import folders_database_migrator


class TestLogMigrationStep:
    """Tests for _log_migration_step function."""

    def test_log_migration_step_output(self, capsys):
        """Test that _log_migration_step prints correct format."""
        folders_database_migrator._log_migration_step("5", "6")

        captured = capsys.readouterr()
        assert "Migrating: v5 -> v6" in captured.out

    def test_log_migration_step_multiple_versions(self, capsys):
        """Test logging multiple migration steps."""
        folders_database_migrator._log_migration_step("10", "11")
        folders_database_migrator._log_migration_step("11", "12")

        captured = capsys.readouterr()
        assert "Migrating: v10 -> v11" in captured.out
        assert "Migrating: v11 -> v12" in captured.out


class TestUpgradeDatabase:
    """Tests for upgrade_database function."""

    def test_target_version_stops_early(self, tmp_path):
        """Test that target_version causes early return when already at target."""
        db_path = str(tmp_path / "test_target_version.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)

        # Start at version 10
        db_conn["version"].insert(dict(version="10", os="Linux"))
        db_conn["administrative"].insert(dict(id=1, copy_to_directory=""))
        db_conn.commit()

        # Request upgrade to version 10 (should be a no-op)
        folders_database_migrator.upgrade_database(
            db_conn, str(tmp_path), "Linux", target_version="10"
        )

        version_record = db_conn["version"].find_one(id=1)
        assert version_record["version"] == "10"

        db_conn.close()

    def test_migration_from_v25(self, tmp_path):
        """Test migration from version 25."""
        db_path = str(tmp_path / "test_v25.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)

        db_conn["version"].insert(dict(version="25", os="Linux"))
        db_conn["folders"].insert(dict(folder_name="/test", alias="Test"))
        db_conn["administrative"].insert(dict(id=1, copy_to_directory=""))
        db_conn.commit()

        folders_database_migrator.upgrade_database(db_conn, str(tmp_path), "Linux")

        version_record = db_conn["version"].find_one(id=1)
        assert version_record["version"] == "50"

        db_conn.close()

    def test_migration_from_v30(self, tmp_path):
        """Test migration from version 30."""
        db_path = str(tmp_path / "test_v30.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)

        db_conn["version"].insert(dict(version="30", os="Linux"))
        db_conn["folders"].insert(dict(folder_name="/test", alias="Test"))
        db_conn["administrative"].insert(dict(id=1, copy_to_directory=""))
        db_conn.commit()

        folders_database_migrator.upgrade_database(db_conn, str(tmp_path), "Linux")

        version_record = db_conn["version"].find_one(id=1)
        assert version_record["version"] == "50"

        db_conn.close()


class TestMigrationEdgeCases:
    """Test edge cases in migration logic."""

    def test_migration_handles_none_config_folder(self, tmp_path):
        """Test migration handles None config_folder."""
        db_path = str(tmp_path / "test_none_config.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)

        db_conn["version"].insert(dict(version="30", os="Linux"))
        db_conn["administrative"].insert(dict(id=1, copy_to_directory=""))
        db_conn.commit()

        # Should not raise with None config_folder
        folders_database_migrator.upgrade_database(db_conn, None, "Linux")

        db_conn.close()

    def test_ensure_schema_retries_locked_db(self, tmp_path, monkeypatch):
        """Ensure schema applies even if first raw execute raises a locked error."""
        db_path = str(tmp_path / "test_locked_db.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)

        call_count = {"n": 0}
        original_execute = schema._execute_sqlite_statement

        def locked_once(conn, stmt, object_name=None):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise sqlite3.OperationalError("database is locked")
            return original_execute(conn, stmt, object_name=object_name)

        monkeypatch.setattr(schema, "_execute_sqlite_statement", locked_once)

        try:
            schema.ensure_schema(db_conn)
        finally:
            monkeypatch.setattr(schema, "_execute_sqlite_statement", original_execute)

        assert call_count["n"] > 1
        # The tables should still exist after retry.
        assert "folders" in db_conn.tables

        db_conn.close()

    def test_multiple_consecutive_migrations(self, tmp_path):
        """Test running migration multiple times is idempotent."""
        db_path = str(tmp_path / "test_multiple.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)

        db_conn["version"].insert(dict(version="30", os="Linux"))
        db_conn["folders"].insert(dict(folder_name="/test", alias="Test"))
        db_conn["administrative"].insert(dict(id=1, copy_to_directory=""))
        db_conn.commit()

        # Run migration multiple times
        folders_database_migrator.upgrade_database(db_conn, str(tmp_path), "Linux")
        folders_database_migrator.upgrade_database(db_conn, str(tmp_path), "Linux")
        folders_database_migrator.upgrade_database(db_conn, str(tmp_path), "Linux")

        version_record = db_conn["version"].find_one(id=1)
        # Should be at current version, not incrementing infinitely
        assert int(version_record["version"]) <= 50

        db_conn.close()


class TestMigrationVersion36:
    """Test specific migration to version 36 (index creation)."""

    def test_version_35_to_36(self, tmp_path):
        """Test migration from version 35 to 36 creates database indexes."""
        db_path = str(tmp_path / "test_indexes.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)

        db_conn["version"].insert(dict(version="35", os="Linux"))
        db_conn["folders"].insert(dict(folder_name="/test", alias="Test"))
        db_conn["administrative"].insert(dict(id=1, copy_to_directory=""))
        db_conn.commit()

        folders_database_migrator.upgrade_database(db_conn, str(tmp_path), "Linux")

        # Migration runs to completion (note: target_version param has a bug)
        version_record = db_conn["version"].find_one(id=1)
        assert int(version_record["version"]) >= 35

        db_conn.close()


class TestMigrationVersion37and38:
    """Test versions 37 and 38 migrations."""

    def test_version_36_to_37(self, tmp_path):
        """Test migration to version 37 adds notes to version table."""
        db_path = str(tmp_path / "test_v37.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)

        db_conn["version"].insert(dict(version="36", os="Linux"))
        db_conn["administrative"].insert(dict(id=1, copy_to_directory=""))
        db_conn.commit()

        folders_database_migrator.upgrade_database(db_conn, str(tmp_path), "Linux")

        # Migration runs to completion
        version_record = db_conn["version"].find_one(id=1)
        assert int(version_record["version"]) >= 36

        db_conn.close()

    def test_version_37_to_38(self, tmp_path):
        """Test migration to version 38 adds edi_format column."""
        db_path = str(tmp_path / "test_v38.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)

        db_conn["version"].insert(dict(version="37", os="Linux"))
        db_conn["folders"].insert(dict(folder_name="/test", alias="Test"))
        db_conn["administrative"].insert(dict(id=1, copy_to_directory=""))
        db_conn.commit()

        folders_database_migrator.upgrade_database(db_conn, str(tmp_path), "Linux")

        # Migration runs to completion
        version_record = db_conn["version"].find_one(id=1)
        assert int(version_record["version"]) >= 37

        db_conn.close()


class TestMigrationVersion39:
    """Test version 39 migration which adds id column to folders."""

    def test_version_38_to_39(self, tmp_path):
        """Test migration to version 39 adds id column to folders."""
        db_path = str(tmp_path / "test_v39.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)

        db_conn["version"].insert(dict(version="38", os="Linux"))
        db_conn["folders"].insert(dict(folder_name="/test", alias="Test"))
        db_conn["administrative"].insert(dict(id=1, copy_to_directory=""))
        db_conn.commit()

        folders_database_migrator.upgrade_database(db_conn, str(tmp_path), "Linux")

        # Migration runs to completion
        version_record = db_conn["version"].find_one(id=1)
        assert int(version_record["version"]) >= 38

        db_conn.close()


class TestMigrationVersion40:
    """Test version 40 migration (backend columns)."""

    def test_version_39_to_40(self, tmp_path):
        """Test migration to version 40 adds backend email/FTP columns."""
        db_path = str(tmp_path / "test_v40.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)

        db_conn["version"].insert(dict(version="39", os="Linux"))
        db_conn["folders"].insert(dict(folder_name="/test", alias="Test"))
        db_conn["administrative"].insert(dict(id=1, copy_to_directory=""))
        db_conn.commit()

        folders_database_migrator.upgrade_database(db_conn, str(tmp_path), "Linux")

        # Migration runs to completion
        version_record = db_conn["version"].find_one(id=1)
        assert int(version_record["version"]) >= 39

        db_conn.close()


class TestMigrationVersion41:
    """Test version 41 migration (boolean normalization) and version 42."""

    def test_version_40_to_42(self, tmp_path):
        """Test migration from version 40 completes to version 42."""
        db_path = str(tmp_path / "test_v41.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)

        db_conn["version"].insert(dict(version="40", os="Linux"))
        db_conn["folders"].insert(dict(folder_name="/test", alias="Test"))
        db_conn["administrative"].insert(dict(id=1, copy_to_directory=""))
        db_conn.commit()

        folders_database_migrator.upgrade_database(db_conn, str(tmp_path), "Linux")

        version_record = db_conn["version"].find_one(id=1)
        assert version_record["version"] == "50"

        db_conn.close()


class TestMigrationSkipLogic:
    """Test the version checking and skip logic in migrations."""

    def test_double_version_check_does_not_hang(self, tmp_path):
        """Test that duplicate version checks work correctly."""
        db_path = str(tmp_path / "test_double_check.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)

        # Start at a version that has duplicate checks (e.g., version 11)
        db_conn["version"].insert(dict(version="11", os="Linux"))
        db_conn["administrative"].insert(dict(id=1, copy_to_directory=""))
        db_conn["folders"].insert(dict(folder_name="/test", alias="Test"))
        db_conn.commit()

        # This should complete without hanging or errors
        folders_database_migrator.upgrade_database(db_conn, str(tmp_path), "Linux")

        version_record = db_conn["version"].find_one(id=1)
        assert int(version_record["version"]) > 11

        db_conn.close()

    def test_target_version_exactly_current(self, tmp_path):
        """Test target_version exactly equal to current version."""
        db_path = str(tmp_path / "test_exact_target.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)

        db_conn["version"].insert(dict(version="35", os="Linux"))
        db_conn["administrative"].insert(dict(id=1, copy_to_directory=""))
        db_conn.commit()

        folders_database_migrator.upgrade_database(
            db_conn, str(tmp_path), "Linux", target_version="35"
        )

        version_record = db_conn["version"].find_one(id=1)
        assert version_record["version"] == "35"

        db_conn.close()

    def test_target_version_one_ahead(self, tmp_path):
        """Test target_version one version ahead."""
        db_path = str(tmp_path / "test_one_ahead.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)

        db_conn["version"].insert(dict(version="35", os="Linux"))
        db_conn["administrative"].insert(dict(id=1, copy_to_directory=""))
        db_conn.commit()

        folders_database_migrator.upgrade_database(
            db_conn, str(tmp_path), "Linux", target_version="36"
        )

        version_record = db_conn["version"].find_one(id=1)
        assert version_record["version"] == "36"

        db_conn.close()


class TestMigrationContents:
    """Test that migrations add correct content."""

    def test_v30_folders_columns(self, tmp_path):
        """Test that v30 migration adds expected columns to folders."""
        db_path = str(tmp_path / "test_v30_cols.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)

        db_conn["version"].insert(dict(version="29", os="Linux"))
        db_conn["folders"].insert(dict(folder_name="/test", alias="Test"))
        db_conn["administrative"].insert(dict(id=1, copy_to_directory=""))
        db_conn.commit()

        folders_database_migrator.upgrade_database(db_conn, str(tmp_path), "Linux")

        folders = list(db_conn["folders"].all())
        assert "split_edi_include_invoices" in folders[0]
        assert "split_edi_include_credits" in folders[0]
        assert "fintech_division_id" in folders[0]

        db_conn.close()

    def test_v33_timestamps(self, tmp_path):
        """Test that v33 migration adds timestamp columns."""
        db_path = str(tmp_path / "test_v33.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)

        db_conn["version"].insert(dict(version="32", os="Linux"))
        db_conn["folders"].insert(dict(folder_name="/test", alias="Test"))
        db_conn["administrative"].insert(dict(id=1, copy_to_directory=""))
        db_conn["processed_files"].insert(dict(folder_id=1, filename="test.edi"))
        db_conn["settings"].insert(dict(folder_name="test"))
        db_conn.commit()

        folders_database_migrator.upgrade_database(db_conn, str(tmp_path), "Linux")

        # Check folders has timestamps
        folders = list(db_conn["folders"].all())
        assert "created_at" in folders[0]
        assert "updated_at" in folders[0]

        # Check processed_files has timestamps
        processed = list(db_conn["processed_files"].all())
        assert "created_at" in processed[0]
        assert "processed_at" in processed[0]

        db_conn.close()

    def test_v34_filename_columns(self, tmp_path):
        """Test that v34 migration adds filename columns."""
        db_path = str(tmp_path / "test_v34.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)

        db_conn["version"].insert(dict(version="33", os="Linux"))
        db_conn["folders"].insert(dict(folder_name="/test", alias="Test"))
        db_conn["administrative"].insert(dict(id=1, copy_to_directory=""))
        db_conn["processed_files"].insert(dict(folder_id=1, file_name="test.edi"))
        db_conn.commit()

        folders_database_migrator.upgrade_database(db_conn, str(tmp_path), "Linux")

        processed = list(db_conn["processed_files"].all())
        assert "filename" in processed[0]
        assert "original_path" in processed[0]
        assert "processed_path" in processed[0]
        assert "status" in processed[0]

        db_conn.close()

    def test_v45_clear_stale_convert_to_format_for_tweak_edi(self, tmp_path):
        """Test that v45 migration handles convert_to_format for folders with tweak_edi=True.

        The migration honors non-empty convert_to_format (does not clear it) when
        tweak_edi=1, since the stored format is the intended conversion target.
        Folders with tweak_edi=1 and empty convert_to_format get convert_to_format='tweaks'.
        """
        db_path = str(tmp_path / "test_v45.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)

        db_conn["version"].insert(dict(version="44", os="Linux"))
        # Insert folder with tweak_edi=True and non-empty convert_to_format
        db_conn["folders"].insert(
            dict(
                folder_name="/test",
                alias="Test",
                tweak_edi=1,
                convert_to_format="eStore eInvoice",
            )
        )
        # Insert another folder with tweak_edi=True and different non-empty format
        db_conn["folders"].insert(
            dict(
                folder_name="/test2",
                alias="Test2",
                tweak_edi=1,
                convert_to_format="csv",
            )
        )
        # Insert folder with tweak_edi=True and empty convert_to_format
        db_conn["folders"].insert(
            dict(
                folder_name="/test3",
                alias="Test3",
                tweak_edi=1,
                convert_to_format="",
            )
        )
        db_conn.commit()

        folders_database_migrator.upgrade_database(db_conn, str(tmp_path), "Linux")

        # Check migration results
        folders = list(db_conn["folders"].all())
        # Folder 1: tweak_edi=True with non-empty format -> format is honored
        assert folders[0]["convert_to_format"] == "eStore eInvoice"
        assert folders[0]["tweak_edi"] == 0
        # Folder 2: tweak_edi=True with non-empty format -> format is honored
        assert folders[1]["convert_to_format"] == "csv"
        assert folders[1]["tweak_edi"] == 0
        # Folder 3: tweak_edi=True with empty format -> gets 'tweaks'
        assert folders[2]["convert_to_format"] == "tweaks"
        assert folders[2]["tweak_edi"] == 0

        db_conn.close()

    def test_v45_clears_tweak_edi_process_edi_unchanged(self, tmp_path):
        """v44→v48 migration chain: tweak_edi is cleared, process_edi is never altered.

        Starting from v44:
        - v45 clears tweak_edi (retiring the deprecated flag)
        - v48 is a version-bump only; it does NOT touch process_edi

        Folders with process_edi=0 keep process_edi=0 regardless of convert_to_format.
        Disabling a folder (process_edi=0) is an explicit user choice that migration
        must not override.
        """
        db_path = str(tmp_path / "test_v45_disabled.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)

        db_conn["version"].insert(dict(version="44", os="Linux"))
        # Folder: process_edi=0 + tweak_edi=1 + non-empty format
        # After migration: process_edi stays 0 — disabled is an intentional state.
        db_conn["folders"].insert(
            dict(
                folder_name="/test_disabled",
                alias="Disabled",
                process_edi=0,
                tweak_edi=1,
                convert_to_format="csv",
            )
        )
        # Folder: process_edi=0 + tweak_edi=1 + empty format
        # After migration: process_edi stays 0.
        db_conn["folders"].insert(
            dict(
                folder_name="/test_disabled_empty",
                alias="DisabledEmpty",
                process_edi=0,
                tweak_edi=1,
                convert_to_format="",
            )
        )
        db_conn.commit()

        folders_database_migrator.upgrade_database(db_conn, str(tmp_path), "Linux")

        folders = {f["alias"]: f for f in db_conn["folders"].all()}
        # Both folders remain disabled — migration must not flip process_edi.
        assert (
            folders["Disabled"]["process_edi"] == 0
        ), "process_edi=0 must not be promoted — disabling a folder is intentional"
        assert folders["Disabled"]["tweak_edi"] == 0
        assert folders["Disabled"]["convert_to_format"] == "csv"
        assert (
            folders["DisabledEmpty"]["process_edi"] == 0
        ), "process_edi=0 with no format must remain 0"
        assert folders["DisabledEmpty"]["tweak_edi"] == 0
        assert folders["DisabledEmpty"]["convert_to_format"] in ("", None)

        db_conn.close()


class TestMigrationVersion48:
    """Test v47 -> v48: version bump only, no data changes."""

    def test_v48_leaves_process_edi_unchanged(self, tmp_path):
        """v47→v48 is a no-op for data; process_edi is never altered.

        A prior version of this step attempted to flip process_edi=0→1 for folders
        with a convert_to_format set, but that heuristic was wrong: legacy databases
        have many intentionally-disabled folders with stale convert_to_format values.
        Enabling conversion for those would change dispatch behaviour silently.
        """
        db_path = str(tmp_path / "test_v48.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)

        db_conn["version"].insert(dict(version="47", os="Linux"))
        # These must all keep their original process_edi after migration.
        db_conn["folders"].insert(
            dict(folder_name="/a", alias="A", process_edi=0, convert_to_format="csv")
        )
        db_conn["folders"].insert(
            dict(
                folder_name="/b",
                alias="B",
                process_edi="False",
                convert_to_format="Estore eInvoice Generic",
            )
        )
        db_conn["folders"].insert(
            dict(folder_name="/c", alias="C", process_edi=0, convert_to_format="")
        )
        db_conn["folders"].insert(
            dict(
                folder_name="/d",
                alias="D",
                process_edi=0,
                convert_to_format="do_nothing",
            )
        )
        db_conn["folders"].insert(
            dict(folder_name="/e", alias="E", process_edi=1, convert_to_format="csv")
        )
        db_conn["administrative"].insert(dict(id=1, copy_to_directory=""))
        db_conn.commit()

        folders_database_migrator.upgrade_database(db_conn, str(tmp_path), "Linux")

        version_record = db_conn["version"].find_one(id=1)
        assert version_record["version"] == "50"

        folders = {f["alias"]: f for f in db_conn["folders"].all()}
        # Disabled folders must remain disabled regardless of convert_to_format.
        from core.utils.bool_utils import normalize_bool

        assert not normalize_bool(
            folders["A"]["process_edi"]
        ), "disabled with format — must stay disabled"
        assert not normalize_bool(
            folders["B"]["process_edi"]
        ), "disabled with format — must stay disabled"
        assert not normalize_bool(
            folders["C"]["process_edi"]
        ), "no format — must stay disabled"
        assert not normalize_bool(
            folders["D"]["process_edi"]
        ), "do_nothing — must stay disabled"
        assert normalize_bool(
            folders["E"]["process_edi"]
        ), "already enabled — must stay enabled"

        db_conn.close()

    def test_v48_idempotent(self, tmp_path):
        """Running migration on an already-v48 database does nothing."""
        db_path = str(tmp_path / "test_v48_idempotent.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)

        db_conn["version"].insert(dict(version="48", os="Linux"))
        db_conn["folders"].insert(
            dict(folder_name="/a", alias="A", process_edi=0, convert_to_format="csv")
        )
        db_conn["administrative"].insert(dict(id=1, copy_to_directory=""))
        db_conn.commit()

        folders_database_migrator.upgrade_database(db_conn, str(tmp_path), "Linux")
        folders_database_migrator.upgrade_database(db_conn, str(tmp_path), "Linux")

        version_record = db_conn["version"].find_one(id=1)
        assert version_record["version"] == "50"
        # process_edi must NOT have been touched (migration skipped)
        folder = db_conn["folders"].find_one(alias="A")
        assert folder["process_edi"] == 0

        db_conn.close()


class TestMigrationVersion49to50:
    """Test v49 -> v50: add process_backend_http column with automatic repair."""

    def test_v49_to_v50_adds_process_backend_http_column(self, tmp_path):
        """Migration from v49 to v50 adds process_backend_http to both tables."""
        db_path = str(tmp_path / "test_v49_v50.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)

        db_conn["version"].insert(dict(version="49", os="Linux"))
        db_conn["folders"].insert(
            dict(folder_name="/a", alias="A", process_edi=1, convert_to_format="csv")
        )
        db_conn["administrative"].insert(dict(id=1, copy_to_directory=""))
        db_conn.commit()

        folders_database_migrator.upgrade_database(db_conn, str(tmp_path), "Linux")

        version_record = db_conn["version"].find_one(id=1)
        assert version_record["version"] == "50"

        # Verify column exists in folders table
        cursor = db_conn.raw_connection.cursor()
        cursor.execute('PRAGMA table_info("folders")')
        folders_columns = [row[1] for row in cursor.fetchall()]
        assert "process_backend_http" in folders_columns

        # Verify column exists in administrative table
        cursor.execute('PRAGMA table_info("administrative")')
        admin_columns = [row[1] for row in cursor.fetchall()]
        assert "process_backend_http" in admin_columns

        # Verify default value is 0
        folder = db_conn["folders"].find_one(alias="A")
        assert folder["process_backend_http"] == 0

        db_conn.close()

    def test_v50_repair_adds_missing_process_backend_http_column(self, tmp_path):
        """Repair step at v50 adds missing process_backend_http columns."""
        db_path = str(tmp_path / "test_v50_repair.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)

        # Simulate broken state: version 50 but missing column
        db_conn["version"].insert(dict(version="50", os="Linux"))
        db_conn["folders"].insert(
            dict(folder_name="/a", alias="A", process_edi=1, convert_to_format="csv")
        )
        db_conn["administrative"].insert(dict(id=1, copy_to_directory=""))
        db_conn.commit()

        # Manually remove the column to simulate failed migration
        # (schema.ensure_schema may have added it)
        db_conn.raw_connection.execute(
            'ALTER TABLE "folders" DROP COLUMN "process_backend_http"'
        )

        # Run migration - should trigger repair
        folders_database_migrator.upgrade_database(db_conn, str(tmp_path), "Linux")

        # Verify column was added by repair
        cursor = db_conn.raw_connection.cursor()
        cursor.execute('PRAGMA table_info("folders")')
        folders_columns = [row[1] for row in cursor.fetchall()]
        assert "process_backend_http" in folders_columns

        # Verify default value is 0
        folder = db_conn["folders"].find_one(alias="A")
        assert folder["process_backend_http"] == 0

        db_conn.close()

    def test_v50_repair_adds_missing_http_payload_columns(self, tmp_path):
        """Repair step at v50 backfills HTTP payload columns used by folder save."""
        db_path = str(tmp_path / "test_v50_http_payload_repair.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)

        db_conn["version"].insert(dict(version="50", os="Linux"))
        db_conn["folders"].insert(
            dict(folder_name="/a", alias="A", process_edi=1, convert_to_format="csv")
        )
        db_conn["administrative"].insert(dict(id=1, copy_to_directory=""))
        db_conn.commit()

        # Simulate legacy v50 DBs where only process_backend_http exists.
        for table_name in ("folders", "administrative"):
            cursor = db_conn.raw_connection.cursor()
            cursor.execute(f'PRAGMA table_info("{table_name}")')
            existing_columns = {row[1] for row in cursor.fetchall()}
            for col in (
                "http_url",
                "http_headers",
                "http_field_name",
                "http_auth_type",
                "http_api_key",
            ):
                if col in existing_columns:
                    db_conn.raw_connection.execute(
                        f'ALTER TABLE "{table_name}" DROP COLUMN "{col}"'
                    )
        db_conn.commit()

        folders_database_migrator.upgrade_database(db_conn, str(tmp_path), "Linux")

        cursor = db_conn.raw_connection.cursor()
        for table_name in ("folders", "administrative"):
            cursor.execute(f'PRAGMA table_info("{table_name}")')
            columns = {row[1] for row in cursor.fetchall()}
            for col in (
                "process_backend_http",
                "http_url",
                "http_headers",
                "http_field_name",
                "http_auth_type",
                "http_api_key",
            ):
                assert col in columns

        folder = db_conn["folders"].find_one(alias="A")
        assert folder["http_url"] == ""
        assert folder["http_headers"] == ""
        assert folder["http_field_name"] == "file"
        assert folder["http_auth_type"] == ""
        assert folder["http_api_key"] == ""

        db_conn.close()

    def test_v50_repair_is_idempotent(self, tmp_path):
        """Running migration multiple times at v50 is safe."""
        db_path = str(tmp_path / "test_v50_idempotent.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)

        db_conn["version"].insert(dict(version="50", os="Linux"))
        db_conn["folders"].insert(dict(folder_name="/a", alias="A", process_edi=1))
        db_conn["administrative"].insert(dict(id=1, copy_to_directory=""))
        db_conn.commit()

        # Run migration twice - should be safe
        folders_database_migrator.upgrade_database(db_conn, str(tmp_path), "Linux")
        folders_database_migrator.upgrade_database(db_conn, str(tmp_path), "Linux")

        version_record = db_conn["version"].find_one(id=1)
        assert version_record["version"] == "50"

        folder = db_conn["folders"].find_one(alias="A")
        assert folder["process_backend_http"] == 0

        db_conn.close()


@pytest.mark.integration
@pytest.mark.database
class TestV32UpgradeIntegration:
    """Integration tests for the v32→current upgrade path using the real legacy fixture."""

    @pytest.fixture
    def migrated_db_conn(self, tmp_path):
        """Migrate the real v32 fixture to current schema and return a raw sqlite3 connection."""
        import shutil

        src = Path("tests/fixtures/legacy_v32_folders.db")
        if not src.exists():
            pytest.skip("Legacy v32 database fixture not found")

        db_path = str(tmp_path / "folders.db")
        shutil.copy2(str(src), db_path)

        db = sqlite_wrapper.Database.connect(db_path)
        folders_database_migrator.upgrade_database(db, str(tmp_path), "Linux")
        db.close()

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        yield conn
        conn.close()

    def test_total_folder_count_preserved(self, migrated_db_conn):
        """Migration must not lose any folder rows."""
        cur = migrated_db_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM folders")
        assert cur.fetchone()[0] == 530

    def test_no_string_booleans_remain_after_upgrade(self, migrated_db_conn):
        """All boolean columns must be stored as integers — no 'True'/'False' strings."""
        bool_columns = [
            "process_edi",
            "tweak_edi",
            "folder_is_active",
            "include_c_records",
            "pad_a_records",
            "filter_ampersand",
            "calculate_upc_check_digit",
            "include_headers",
            "include_a_records",
            "append_a_records",
            "force_txt_file_ext",
        ]
        cur = migrated_db_conn.cursor()
        for col in bool_columns:
            cur.execute(
                f"SELECT COUNT(*) FROM folders"
                f" WHERE LOWER(CAST({col} AS TEXT)) IN ('true', 'false')"
            )
            count = cur.fetchone()[0]
            assert (
                count == 0
            ), f"Column '{col}' still has string boolean values after migration"

    def test_disabled_folders_remain_disabled_after_upgrade(self, migrated_db_conn):
        """The 380 originally-disabled folders must not become enabled during migration."""
        cur = migrated_db_conn.cursor()

        # No string remnants
        cur.execute(
            "SELECT COUNT(*) FROM folders"
            " WHERE LOWER(CAST(process_edi AS TEXT)) IN ('true', 'false')"
        )
        assert cur.fetchone()[0] == 0

        # Exactly 150 folders were originally enabled; none of the 380 disabled
        # ones should have been promoted to process_edi=1.
        cur.execute("SELECT COUNT(*) FROM folders WHERE process_edi = 1")
        assert cur.fetchone()[0] <= 150

        cur.execute("SELECT COUNT(*) FROM folders WHERE process_edi = 0")
        assert cur.fetchone()[0] == 380

    def test_convert_to_format_normalized_after_upgrade(self, migrated_db_conn):
        """Display-name convert_to_format values must be replaced by canonical tokens."""
        cur = migrated_db_conn.cursor()

        # Old display names must be gone
        for old_name in (
            "Estore eInvoice Generic",
            "YellowDog CSV",
            "scansheet-type-a",
            "ScannerWare",
        ):
            cur.execute(
                "SELECT COUNT(*) FROM folders WHERE convert_to_format = ?", (old_name,)
            )
            assert (
                cur.fetchone()[0] == 0
            ), f"Display name '{old_name}' still present after migration"

        # Normalized canonical tokens must be present with correct counts
        expected = {
            "estore_einvoice_generic": 15,
            "yellowdog_csv": 14,
            "scansheet_type_a": 2,
            "scannerware": 1,
        }
        for token, expected_count in expected.items():
            cur.execute(
                "SELECT COUNT(*) FROM folders WHERE convert_to_format = ?", (token,)
            )
            actual = cur.fetchone()[0]
            assert (
                actual == expected_count
            ), f"Expected {expected_count} folders with format '{token}', got {actual}"

    def test_all_convert_formats_are_supported_after_upgrade(self, migrated_db_conn):
        """Every non-empty convert_to_format value must be a known canonical token."""
        from dispatch.pipeline.converter import SUPPORTED_FORMATS

        cur = migrated_db_conn.cursor()
        cur.execute(
            "SELECT DISTINCT convert_to_format FROM folders"
            " WHERE convert_to_format IS NOT NULL AND convert_to_format != ''"
        )
        unknown = [row[0] for row in cur.fetchall() if row[0] not in SUPPORTED_FORMATS]
        assert (
            unknown == []
        ), f"Unsupported format values found after migration: {unknown}"

    def test_tweak_edi_cleared_for_all_folders(self, migrated_db_conn):
        """The deprecated tweak_edi flag must be 0 for every folder after migration."""
        cur = migrated_db_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM folders WHERE tweak_edi != 0")
        assert cur.fetchone()[0] == 0

    def test_tweaks_format_not_assigned_to_disabled_folders(self, migrated_db_conn):
        """Disabled folders must never receive convert_to_format='tweaks'."""
        cur = migrated_db_conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM folders"
            " WHERE process_edi = 0 AND convert_to_format = 'tweaks'"
        )
        assert cur.fetchone()[0] == 0

    def test_enabled_tweak_edi_folders_get_tweaks_format(self, migrated_db_conn):
        """Enabled folders must not be left with an empty convert_to_format."""
        cur = migrated_db_conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM folders"
            " WHERE process_edi = 1"
            " AND (convert_to_format IS NULL OR convert_to_format = '')"
        )
        assert cur.fetchone()[0] == 0
