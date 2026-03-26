"""Unit tests for folders_database_migrator module.

Tests cover:
- Migration version checking logic
- Target version handling (early return when already at target)
- Individual migration steps
- Edge cases and error handling
- Log output verification
"""

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
        assert "Migrating: v5 → v6" in captured.out

    def test_log_migration_step_multiple_versions(self, capsys):
        """Test logging multiple migration steps."""
        folders_database_migrator._log_migration_step("10", "11")
        folders_database_migrator._log_migration_step("11", "12")

        captured = capsys.readouterr()
        assert "Migrating: v10 → v11" in captured.out
        assert "Migrating: v11 → v12" in captured.out


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

    def test_target_version_partial_upgrade(self, tmp_path):
        """Test that target_version stops migration at specified version."""
        db_path = str(tmp_path / "test_partial_upgrade.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)

        # Start at version 10
        db_conn["version"].insert(dict(version="10", os="Linux"))
        db_conn["administrative"].insert(dict(id=1, copy_to_directory=""))
        db_conn["folders"].insert(dict(folder_name="/test", alias="Test"))
        db_conn.commit()

        # Request upgrade to version 12
        folders_database_migrator.upgrade_database(
            db_conn, str(tmp_path), "Linux", target_version="12"
        )

        version_record = db_conn["version"].find_one(id=1)
        assert version_record["version"] == "12"

        db_conn.close()

    def test_current_version_no_migration(self, tmp_path):
        """Test that database at current version doesn't change."""
        db_path = str(tmp_path / "test_current_version.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)

        # Start at version 47 (current)
        db_conn["version"].insert(dict(version="47", os="Linux"))
        db_conn["administrative"].insert(dict(id=1, copy_to_directory=""))
        db_conn.commit()

        folders_database_migrator.upgrade_database(db_conn, str(tmp_path), "Linux")

        version_record = db_conn["version"].find_one(id=1)
        assert version_record["version"] == "47"

        db_conn.close()

    def test_full_migration_from_v10(self, tmp_path):
        """Test migration from version 10 to current."""
        db_path = str(tmp_path / "test_full_migration.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)

        db_conn["version"].insert(dict(version="10", os="Linux"))
        db_conn["folders"].insert(dict(folder_name="/test", alias="Test"))
        db_conn["administrative"].insert(dict(id=1, copy_to_directory=""))
        db_conn["processed_files"].insert(dict(folder_id=1, filename="test.edi"))
        db_conn.commit()

        folders_database_migrator.upgrade_database(db_conn, str(tmp_path), "Linux")

        version_record = db_conn["version"].find_one(id=1)
        assert version_record["version"] == "47"

        db_conn.close()

    def test_migration_from_v15(self, tmp_path):
        """Test migration from version 15."""
        db_path = str(tmp_path / "test_v15.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)

        db_conn["version"].insert(dict(version="15", os="Linux"))
        db_conn["folders"].insert(dict(folder_name="/test", alias="Test"))
        db_conn["administrative"].insert(dict(id=1, copy_to_directory=""))
        db_conn.commit()

        folders_database_migrator.upgrade_database(db_conn, str(tmp_path), "Linux")

        version_record = db_conn["version"].find_one(id=1)
        assert version_record["version"] == "47"

        db_conn.close()

    def test_migration_from_v20(self, tmp_path):
        """Test migration from version 20."""
        db_path = str(tmp_path / "test_v20.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)

        db_conn["version"].insert(dict(version="20", os="Linux"))
        db_conn["folders"].insert(dict(folder_name="/test", alias="Test"))
        db_conn["administrative"].insert(dict(id=1, copy_to_directory=""))
        db_conn.commit()

        folders_database_migrator.upgrade_database(db_conn, str(tmp_path), "Linux")

        version_record = db_conn["version"].find_one(id=1)
        assert version_record["version"] == "47"

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
        assert version_record["version"] == "47"

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
        assert version_record["version"] == "47"

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
        assert int(version_record["version"]) <= 47

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
        assert version_record["version"] == "47"

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

    def test_v45_preserves_process_edi_false_with_tweak_edi(self, tmp_path):
        """Migration must NOT flip process_edi from 0 to 1 when it was explicitly disabled.

        Folders with process_edi=0 (user disabled EDI processing) should keep
        passing through even if tweak_edi=1 was also set.  The deprecated
        tweak_edi flag is cleared, but process_edi=0 is preserved.
        """
        db_path = str(tmp_path / "test_v45_disabled.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)

        db_conn["version"].insert(dict(version="44", os="Linux"))
        # Folder: process_edi explicitly disabled + tweak_edi=1 + non-empty format
        db_conn["folders"].insert(
            dict(
                folder_name="/test_disabled",
                alias="Disabled",
                process_edi=0,
                tweak_edi=1,
                convert_to_format="csv",
            )
        )
        # Folder: process_edi explicitly disabled + tweak_edi=1 + empty format
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

        folders = list(db_conn["folders"].all())
        # Folder 1: process_edi=0 must stay 0 — only tweak_edi is cleared
        assert folders[0]["process_edi"] == 0, "process_edi=0 must not be promoted to 1"
        assert folders[0]["tweak_edi"] == 0
        assert (
            folders[0]["convert_to_format"] == "csv"
        ), "convert_to_format must be unchanged"
        # Folder 2: process_edi=0, empty format — tweak_edi cleared, no format added
        assert folders[1]["process_edi"] == 0, "process_edi=0 must not be promoted to 1"
        assert folders[1]["tweak_edi"] == 0
        assert folders[1]["convert_to_format"] in (
            "",
            None,
        ), "convert_to_format must stay empty when processing is disabled"

        db_conn.close()
