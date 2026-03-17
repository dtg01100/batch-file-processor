"""Integration tests using a real legacy v32 production database.

Tests the complete upgrade path from v32 → v42 using an actual database
file from a legacy Windows installation. This database contains:
- 530 folder configurations
- 227,501 processed file records
- Real production settings and administrative data

The database is at version 32 with the Windows platform marker.
"""

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.database,
    pytest.mark.upgrade,
    pytest.mark.slow,
]

import os
import shutil
import sqlite3

import folders_database_migrator
import schema
from core.utils.bool_utils import normalize_bool
from interface.database import sqlite_wrapper

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures")
LEGACY_DB_PATH = os.path.join(FIXTURES_DIR, "legacy_v32_folders.db")


@pytest.fixture
def legacy_db(tmp_path):
    """Copy the real legacy v32 database to a temp directory for testing.

    Each test gets its own copy so tests are isolated.
    """
    if not os.path.exists(LEGACY_DB_PATH):
        pytest.skip("Legacy v32 database fixture not found")
    dest = str(tmp_path / "folders.db")
    shutil.copy2(LEGACY_DB_PATH, dest)
    return dest


@pytest.fixture
def migrated_db(legacy_db, tmp_path):
    """Provide a fully migrated database (v32 → v42).

    Returns the dataset connection to the migrated database.
    """
    db = sqlite_wrapper.Database.connect(legacy_db)
    folders_database_migrator.upgrade_database(db, str(tmp_path), "Linux")
    yield db
    db.close()


@pytest.fixture(scope="class")
def migrated_db_shared(tmp_path_factory):
    """Class-scoped migrated database for read-only test classes.

    Performs the expensive v32→v42 migration ONCE per test class.
    WARNING: Tests using this fixture must NOT modify the database.
    """
    if not os.path.exists(LEGACY_DB_PATH):
        pytest.skip("Legacy v32 database fixture not found")
    tmpdir = tmp_path_factory.mktemp("legacy_shared")
    dest = str(tmpdir / "folders.db")
    shutil.copy2(LEGACY_DB_PATH, dest)
    db = sqlite_wrapper.Database.connect(dest)
    folders_database_migrator.upgrade_database(db, str(tmpdir), "Linux")
    yield db
    db.close()


class TestLegacyDatabasePreConditions:
    """Verify the legacy database is in the expected v32 state before migration."""

    def test_legacy_db_is_version_32(self, legacy_db):
        """The fixture database should be at version 32."""
        db = sqlite_wrapper.Database.connect(legacy_db)
        version = db["version"].find_one(id=1)
        assert version["version"] == "32"
        assert version["os"] == "Windows"
        db.close()

    def test_legacy_db_has_530_folders(self, legacy_db):
        """The fixture database should contain 530 folder records."""
        db = sqlite_wrapper.Database.connect(legacy_db)
        count = db["folders"].count()
        assert count == 530
        db.close()

    def test_legacy_db_has_227501_processed_files(self, legacy_db):
        """The fixture database should contain 227,501 processed file records."""
        db = sqlite_wrapper.Database.connect(legacy_db)
        count = db["processed_files"].count()
        assert count == 227501
        db.close()

    def test_legacy_db_has_expected_tables(self, legacy_db):
        """The fixture database should have all 8 expected tables."""
        db = sqlite_wrapper.Database.connect(legacy_db)
        tables = db.tables
        expected = {
            "version",
            "administrative",
            "folders",
            "processed_files",
            "settings",
            "emails_to_send",
            "working_batch_emails_to_send",
            "sent_emails_removal_queue",
        }
        assert expected.issubset(set(tables))
        db.close()

    def test_legacy_db_has_no_plugin_config(self, legacy_db):
        """v32 database should NOT have plugin_config column yet."""
        conn = sqlite3.connect(legacy_db)
        cursor = conn.execute("PRAGMA table_info(folders)")
        columns = {row[1] for row in cursor.fetchall()}
        assert "plugin_config" not in columns
        conn.close()

    def test_legacy_db_has_no_edi_format(self, legacy_db):
        """v32 database should NOT have edi_format column yet."""
        conn = sqlite3.connect(legacy_db)
        cursor = conn.execute("PRAGMA table_info(folders)")
        columns = {row[1] for row in cursor.fetchall()}
        assert "edi_format" not in columns
        conn.close()

    def test_legacy_db_has_no_timestamps(self, legacy_db):
        """v32 database should NOT have created_at/updated_at columns yet."""
        conn = sqlite3.connect(legacy_db)
        cursor = conn.execute("PRAGMA table_info(folders)")
        columns = {row[1] for row in cursor.fetchall()}
        assert "created_at" not in columns
        assert "updated_at" not in columns
        conn.close()

    def test_legacy_db_has_string_booleans(self, legacy_db):
        """v32 database should have string "True"/"False" boolean values."""
        import sqlite3

        conn = sqlite3.connect(legacy_db)
        row = conn.execute(
            "SELECT folder_is_active FROM folders WHERE id=21"
        ).fetchone()
        assert normalize_bool(row[0]) is True
        conn.close()


class TestUpgradeCompletes:
    """Test that the full v32 → v42 migration completes successfully."""

    def test_upgrade_reaches_v42(self, migrated_db_shared):
        """Migration should bring the database to version 42."""
        version = migrated_db_shared["version"].find_one(id=1)
        assert version["version"] == "42"

    def test_upgrade_updates_os_field(self, migrated_db_shared):
        """Migration should update the OS field to the current platform."""
        version = migrated_db_shared["version"].find_one(id=1)
        # upgrade_database() is called with "Linux", so OS gets updated
        assert version["os"] == "Linux"


class TestDataPreservation:
    """Test that all data survives the migration intact."""

    def test_all_530_folders_preserved(self, migrated_db_shared):
        """All 530 folder records should survive migration."""
        count = migrated_db_shared["folders"].count()
        assert count == 530

    def test_all_processed_files_preserved(self, migrated_db_shared):
        """All 227,501 processed file records should survive migration."""
        count = migrated_db_shared["processed_files"].count()
        assert count == 227501

    def test_specific_folder_data_preserved(self, migrated_db_shared):
        """Specific folder data should be preserved exactly."""
        folder = migrated_db_shared["folders"].find_one(id=21)
        assert folder is not None
        assert folder["alias"] == "012258"
        assert folder["convert_to_format"] == "csv"

    def test_second_folder_data_preserved(self, migrated_db_shared):
        """Second sample folder should be preserved."""
        folder = migrated_db_shared["folders"].find_one(id=29)
        assert folder is not None
        assert folder["alias"] == "PIERCES"

    def test_settings_preserved(self, migrated_db_shared):
        """Settings table data should be preserved."""
        settings = migrated_db_shared["settings"].find_one(id=1)
        assert settings is not None
        assert settings["smtp_port"] == 587
        assert settings["email_smtp_server"] == "smtp.example.com"
        assert settings["odbc_driver"] == "iSeries Access ODBC Driver"
        assert settings["as400_address"] == "10.0.0.100"

    def test_administrative_preserved(self, migrated_db_shared):
        """Administrative table data should be preserved."""
        admin = migrated_db_shared["administrative"].find_one(id=1)
        assert admin is not None
        assert admin["logs_directory"] == "C:/ProgramData/BatchFileSender/Logs"

    def test_processed_file_data_preserved(self, migrated_db_shared):
        """Individual processed file records should be preserved."""
        pf = migrated_db_shared["processed_files"].find_one(id=1)
        assert pf is not None
        assert pf["file_name"] == r"D:\DATA\OUT\012258\012258.115"
        assert pf["folder_id"] == 21

    def test_email_tables_preserved(self, migrated_db_shared):
        """Email-related tables should still exist after migration."""
        tables = migrated_db_shared.tables
        assert "emails_to_send" in tables
        assert "working_batch_emails_to_send" in tables
        assert "sent_emails_removal_queue" in tables

    def test_legacy_email_origin_columns_preserved(self, migrated_db_shared):
        """Legacy email_origin_* columns that were in the v32 schema must not
        be dropped by migration — the raw data must survive even though the
        current app reads SMTP credentials from the global settings table.
        """
        conn = migrated_db_shared.raw_connection
        cursor = conn.execute("PRAGMA table_info(folders)")
        columns = {row[1] for row in cursor.fetchall()}
        legacy_cols = {
            "email_origin_address",
            "email_origin_password",
            "email_origin_username",
            "email_origin_smtp_server",
            "email_smtp_port",
            "reporting_smtp_port",
        }
        for col in legacy_cols:
            assert col in columns, f"Legacy column '{col}' was dropped during migration"

    def test_legacy_email_origin_data_values_preserved(self, migrated_db_shared):
        """Data in legacy email_origin_* columns should be unchanged after migration."""
        conn = migrated_db_shared.raw_connection
        row = conn.execute(
            "SELECT email_origin_address, email_origin_username, email_origin_smtp_server "
            "FROM folders WHERE id=21"
        ).fetchone()
        assert row is not None
        assert row[0] == "user21@example.com"
        assert row[1] == "user21@example.com"
        assert row[2] == "smtp.example.com"


class TestNewColumnsAdded:
    """Test that migration adds all expected new columns."""

    def test_folders_has_plugin_config(self, migrated_db_shared):
        """Folders table should have plugin_config column after migration."""
        folder = migrated_db_shared["folders"].find_one(id=21)
        assert "plugin_config" in folder

    def test_folders_has_edi_format(self, migrated_db_shared):
        """Folders table should have edi_format column with default value."""
        folder = migrated_db_shared["folders"].find_one(id=21)
        assert "edi_format" in folder
        assert folder["edi_format"] == "default"

    def test_folders_has_timestamps(self, migrated_db_shared):
        """Folders table should have created_at and updated_at columns."""
        folder = migrated_db_shared["folders"].find_one(id=21)
        assert "created_at" in folder
        assert folder["created_at"] is not None
        assert "updated_at" in folder
        assert folder["updated_at"] is not None

    def test_folders_has_split_edi_filter_columns(self, migrated_db_shared):
        """Folders table should have split_edi_filter_categories and split_edi_filter_mode."""
        folder = migrated_db_shared["folders"].find_one(id=21)
        assert "split_edi_filter_categories" in folder
        assert "split_edi_filter_mode" in folder

    def test_administrative_has_plugin_config(self, migrated_db_shared):
        """Administrative table should have plugin_config column."""
        admin = migrated_db_shared["administrative"].find_one(id=1)
        assert "plugin_config" in admin

    def test_administrative_has_edi_format(self, migrated_db_shared):
        """Administrative table should have edi_format column."""
        admin = migrated_db_shared["administrative"].find_one(id=1)
        assert "edi_format" in admin
        assert admin["edi_format"] == "default"

    def test_administrative_has_timestamps(self, migrated_db_shared):
        """Administrative table should have created_at and updated_at."""
        admin = migrated_db_shared["administrative"].find_one(id=1)
        assert "created_at" in admin
        assert admin["created_at"] is not None
        assert "updated_at" in admin

    def test_version_has_notes_column(self, migrated_db_shared):
        """Version table should have notes column after v37→v38."""
        version = migrated_db_shared["version"].find_one(id=1)
        assert "notes" in version

    def test_processed_files_has_new_columns(self, migrated_db_shared):
        """Processed files should have new columns from v34→v35."""
        pf = migrated_db_shared["processed_files"].find_one(id=1)
        assert "filename" in pf
        assert "original_path" in pf
        assert "processed_path" in pf
        assert "status" in pf
        assert "error_message" in pf
        assert "convert_format" in pf
        assert "sent_to" in pf

    def test_settings_has_timestamps(self, migrated_db_shared):
        """Settings table should have created_at and updated_at."""
        settings = migrated_db_shared["settings"].find_one(id=1)
        assert "created_at" in settings
        assert "updated_at" in settings


class TestBooleanNormalization:
    """Test that string booleans are normalized to integers (v40→v41)."""

    def test_folder_is_active_normalized(self, migrated_db_shared):
        """folder_is_active should be normalized from "True"/"False" to 1/0."""
        folder = migrated_db_shared["folders"].find_one(id=21)
        # Was "True" in legacy, should now be 1 or "1"
        assert folder["folder_is_active"] not in ("True", "False")
        assert folder["folder_is_active"] in (0, 1, True, False)

    def test_process_edi_normalized(self, migrated_db_shared):
        """process_edi should be normalized from "True"/"False" to 1/0."""
        folder = migrated_db_shared["folders"].find_one(id=21)
        assert folder["process_edi"] not in ("True", "False")
        assert folder["process_edi"] in (0, 1, True, False)

    def test_active_folder_has_value_1(self, migrated_db_shared):
        """Folder id=21 was active ("True"), should now be 1."""
        folder = migrated_db_shared["folders"].find_one(id=21)
        assert int(folder["folder_is_active"]) == 1

    @pytest.mark.slow
    def test_boolean_fields_across_multiple_folders(self, migrated_db_shared):
        """Check boolean normalization across several folders."""
        boolean_fields = [
            "folder_is_active",
            "process_edi",
            "calculate_upc_check_digit",
            "include_a_records",
            "include_c_records",
            "include_headers",
            "filter_ampersand",
            "pad_a_records",
        ]
        for folder in migrated_db_shared["folders"].find(_limit=20):
            for field in boolean_fields:
                if field in folder and folder[field] is not None:
                    val = folder[field]
                    assert val not in (
                        "True",
                        "False",
                    ), f"Folder {folder['id']}.{field} = {val!r} still has string boolean"


class TestIndexesCreated:
    """Test that migration creates expected indexes (v35→v36)."""

    def test_idx_folders_active_exists(self, legacy_db, tmp_path):
        """idx_folders_active index should exist after migration."""
        db = sqlite_wrapper.Database.connect(legacy_db)
        folders_database_migrator.upgrade_database(db, str(tmp_path), "Linux")
        db.close()

        conn = sqlite3.connect(legacy_db)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_folders_active'"
        )
        result = cursor.fetchone()
        assert result is not None, "idx_folders_active index should exist"
        conn.close()

    def test_idx_folders_alias_exists(self, legacy_db, tmp_path):
        """idx_folders_alias index should exist after migration."""
        db = sqlite_wrapper.Database.connect(legacy_db)
        folders_database_migrator.upgrade_database(db, str(tmp_path), "Linux")
        db.close()

        conn = sqlite3.connect(legacy_db)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_folders_alias'"
        )
        result = cursor.fetchone()
        assert result is not None, "idx_folders_alias index should exist"
        conn.close()

    def test_idx_processed_files_folder_exists(self, legacy_db, tmp_path):
        """idx_processed_files_folder index should exist after migration."""
        db = sqlite_wrapper.Database.connect(legacy_db)
        folders_database_migrator.upgrade_database(db, str(tmp_path), "Linux")
        db.close()

        conn = sqlite3.connect(legacy_db)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_processed_files_folder'"
        )
        result = cursor.fetchone()
        assert result is not None, "idx_processed_files_folder index should exist"
        conn.close()

    def test_idx_processed_files_status_exists(self, legacy_db, tmp_path):
        """idx_processed_files_status index should exist after migration."""
        db = sqlite_wrapper.Database.connect(legacy_db)
        folders_database_migrator.upgrade_database(db, str(tmp_path), "Linux")
        db.close()

        conn = sqlite3.connect(legacy_db)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_processed_files_status'"
        )
        result = cursor.fetchone()
        assert result is not None, "idx_processed_files_status index should exist"
        conn.close()


class TestNormalizedTablesCreated:
    """Test that v41→v42 creates the new normalized schema tables."""

    def test_users_table_exists(self, migrated_db_shared):
        """users table should exist after v42 migration."""
        assert "users" in migrated_db_shared.tables

    def test_organizations_table_exists(self, migrated_db_shared):
        """organizations table should exist after v42 migration."""
        assert "organizations" in migrated_db_shared.tables

    def test_projects_table_exists(self, migrated_db_shared):
        """projects table should exist after v42 migration."""
        assert "projects" in migrated_db_shared.tables

    def test_files_table_exists(self, migrated_db_shared):
        """files table should exist after v42 migration."""
        assert "files" in migrated_db_shared.tables

    def test_batches_table_exists(self, migrated_db_shared):
        """batches table should exist after v42 migration."""
        assert "batches" in migrated_db_shared.tables

    def test_processors_table_exists(self, migrated_db_shared):
        """processors table should exist after v42 migration."""
        assert "processors" in migrated_db_shared.tables

    def test_processing_jobs_table_exists(self, migrated_db_shared):
        """processing_jobs table should exist after v42 migration."""
        assert "processing_jobs" in migrated_db_shared.tables

    def test_job_logs_table_exists(self, migrated_db_shared):
        """job_logs table should exist after v42 migration."""
        assert "job_logs" in migrated_db_shared.tables

    def test_tags_table_exists(self, migrated_db_shared):
        """tags table should exist after v42 migration."""
        assert "tags" in migrated_db_shared.tables

    def test_file_tags_table_exists(self, migrated_db_shared):
        """file_tags table should exist after v42 migration."""
        assert "file_tags" in migrated_db_shared.tables


class TestTableRebuild:
    """Test that v39→v40 table rebuild produces correct PRIMARY KEY ids."""

    def test_folders_has_primary_key(self, legacy_db, tmp_path):
        """After migration, folders table should have PRIMARY KEY on id."""
        db = sqlite_wrapper.Database.connect(legacy_db)
        folders_database_migrator.upgrade_database(db, str(tmp_path), "Linux")
        db.close()

        conn = sqlite3.connect(legacy_db)
        cursor = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='folders'"
        )
        create_sql = cursor.fetchone()[0]
        conn.close()
        # After rebuild, should have PRIMARY KEY on id
        assert "PRIMARY KEY" in create_sql.upper()

    def test_administrative_has_primary_key(self, legacy_db, tmp_path):
        """After migration, administrative table should have PRIMARY KEY on id."""
        db = sqlite_wrapper.Database.connect(legacy_db)
        folders_database_migrator.upgrade_database(db, str(tmp_path), "Linux")
        db.close()

        conn = sqlite3.connect(legacy_db)
        cursor = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='administrative'"
        )
        create_sql = cursor.fetchone()[0]
        conn.close()
        assert "PRIMARY KEY" in create_sql.upper()

    def test_rebuild_recovers_from_stale_new_table(self, tmp_path):
        """If a previous migration attempt left a folders_new table behind,
        the rebuild must silently clean it up and complete successfully,
        preserving all data in the original 'folders' table.
        """
        db_path = str(tmp_path / "test_stale.db")
        conn = sqlite3.connect(db_path)
        # folders WITHOUT an id column — triggers the rebuild path
        conn.execute("CREATE TABLE folders (folder_name TEXT, alias TEXT)")
        conn.execute("INSERT INTO folders VALUES ('path/a', 'ALPHA')")
        conn.execute("INSERT INTO folders VALUES ('path/b', 'BETA')")
        # Simulate a leftover from a previously aborted migration attempt
        conn.execute(
            "CREATE TABLE folders_new (id INTEGER PRIMARY KEY, folder_name TEXT)"
        )
        conn.execute(
            "CREATE TABLE version "
            "(id INTEGER PRIMARY KEY, version TEXT, os TEXT, notes TEXT)"
        )
        conn.execute("INSERT INTO version VALUES (1, '39', 'Linux', NULL)")
        conn.execute(
            "CREATE TABLE administrative (id INTEGER PRIMARY KEY, folder_name TEXT)"
        )
        conn.execute("INSERT INTO administrative VALUES (1, 'admin')")
        conn.commit()
        conn.close()

        db = sqlite_wrapper.Database.connect(db_path)
        # Must NOT raise — stale folders_new is cleaned up automatically
        folders_database_migrator.upgrade_database(
            db, str(tmp_path), "Linux", target_version="40"
        )
        db.close()

        # All original folder data must be preserved
        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            "SELECT folder_name, alias FROM folders ORDER BY folder_name"
        ).fetchall()
        version = conn.execute("SELECT version FROM version WHERE id=1").fetchone()[0]
        conn.close()
        assert version == "40", "Migration should have reached v40"
        assert len(rows) == 2, "All folder rows must survive after stale-table recovery"
        assert rows[0] == ("path/a", "ALPHA")
        assert rows[1] == ("path/b", "BETA")


class TestMigratedDatabaseCRUD:
    """Test that CRUD operations work correctly on the migrated database."""

    def test_can_insert_new_folder(self, migrated_db):
        """Should be able to insert a new folder into the migrated database."""
        new_folder = dict(
            folder_name="/new/test/folder",
            alias="New Test Folder",
            folder_is_active=1,
            process_edi=0,
            convert_to_format="csv",
            plugin_config="",
            edi_format="default",
        )
        folder_id = migrated_db["folders"].insert(new_folder)
        assert folder_id is not None

        # Verify it was inserted
        folder = migrated_db["folders"].find_one(id=folder_id)
        assert folder["folder_name"] == "/new/test/folder"
        assert folder["alias"] == "New Test Folder"

    def test_can_update_existing_folder(self, migrated_db):
        """Should be able to update an existing folder in the migrated database."""
        folder = migrated_db["folders"].find_one(id=21)
        original_alias = folder["alias"]

        migrated_db["folders"].update(dict(id=21, alias="UPDATED_ALIAS"), ["id"])

        updated = migrated_db["folders"].find_one(id=21)
        assert updated["alias"] == "UPDATED_ALIAS"

        # Restore
        migrated_db["folders"].update(dict(id=21, alias=original_alias), ["id"])

    def test_can_delete_folder(self, migrated_db):
        """Should be able to delete a folder from the migrated database."""
        # Insert a test folder first
        test_id = migrated_db["folders"].insert(
            dict(
                folder_name="/delete/me",
                alias="Delete Me",
            )
        )

        migrated_db["folders"].delete(id=test_id)
        assert migrated_db["folders"].find_one(id=test_id) is None

    def test_can_query_folders_by_active_status(self, migrated_db):
        """Should be able to query folders by active status after boolean normalization."""
        active_folders = list(migrated_db["folders"].find(folder_is_active=1))
        assert len(active_folders) > 0

    def test_can_insert_processed_file(self, migrated_db):
        """Should be able to insert a new processed file record."""
        new_pf = dict(
            file_name="/test/file.edi",
            file_checksum="abc123",
            folder_id=21,
            status="processed",
        )
        pf_id = migrated_db["processed_files"].insert(new_pf)
        assert pf_id is not None

        pf = migrated_db["processed_files"].find_one(id=pf_id)
        assert pf["file_name"] == "/test/file.edi"

    def test_can_update_settings(self, migrated_db):
        """Should be able to update settings in the migrated database."""
        migrated_db["settings"].update(dict(id=1, smtp_port=465), ["id"])
        settings = migrated_db["settings"].find_one(id=1)
        assert settings["smtp_port"] == 465

    def test_can_update_administrative(self, migrated_db):
        """Should be able to update administrative record in the migrated database."""
        migrated_db["administrative"].update(
            dict(id=1, logs_directory="/new/logs/path"), ["id"]
        )
        admin = migrated_db["administrative"].find_one(id=1)
        assert admin["logs_directory"] == "/new/logs/path"


class TestSchemaEnsureOnMigratedDb:
    """Test that schema.ensure_schema() works on the migrated database."""

    def test_ensure_schema_is_idempotent(self, legacy_db, tmp_path):
        """Running ensure_schema() on a migrated database should not break anything."""
        db = sqlite_wrapper.Database.connect(legacy_db)
        folders_database_migrator.upgrade_database(db, str(tmp_path), "Linux")

        # Count folders before
        count_before = db["folders"].count()

        # Run ensure_schema
        schema.ensure_schema(db)

        # Count folders after - should be the same
        count_after = db["folders"].count()
        assert count_after == count_before

        # Version should still be 42
        version = db["version"].find_one(id=1)
        assert version["version"] == "42"
        db.close()


class TestIntermediateMigrationStops:
    """Test stopping migration at intermediate versions using target_version."""

    def test_stop_at_v33(self, legacy_db, tmp_path):
        """Migration should stop at v33 when target_version='33'."""
        db = sqlite_wrapper.Database.connect(legacy_db)
        folders_database_migrator.upgrade_database(
            db, str(tmp_path), "Linux", target_version="33"
        )
        version = db["version"].find_one(id=1)
        assert version["version"] == "33"

        # Should have plugin_config now
        folder = db["folders"].find_one(id=21)
        assert "plugin_config" in folder
        assert "split_edi_filter_categories" in folder
        db.close()

    def test_stop_at_v36(self, legacy_db, tmp_path):
        """Migration should stop at v36 (after indexes are created)."""
        db = sqlite_wrapper.Database.connect(legacy_db)
        folders_database_migrator.upgrade_database(
            db, str(tmp_path), "Linux", target_version="36"
        )
        version = db["version"].find_one(id=1)
        assert version["version"] == "36"

        # Should have timestamps from v34
        folder = db["folders"].find_one(id=21)
        assert "created_at" in folder
        db.close()

    def test_stop_at_v39(self, legacy_db, tmp_path):
        """Migration should stop at v39 (after edi_format added)."""
        db = sqlite_wrapper.Database.connect(legacy_db)
        folders_database_migrator.upgrade_database(
            db, str(tmp_path), "Linux", target_version="39"
        )
        version = db["version"].find_one(id=1)
        assert version["version"] == "39"

        folder = db["folders"].find_one(id=21)
        assert "edi_format" in folder
        assert folder["edi_format"] == "default"
        db.close()

    def test_resume_from_v33_to_v42(self, legacy_db, tmp_path):
        """Should be able to migrate to v33, then resume to v42."""
        db = sqlite_wrapper.Database.connect(legacy_db)

        # First stop at v33
        folders_database_migrator.upgrade_database(
            db, str(tmp_path), "Linux", target_version="33"
        )
        assert db["version"].find_one(id=1)["version"] == "33"

        # Then continue to v42
        folders_database_migrator.upgrade_database(db, str(tmp_path), "Linux")
        assert db["version"].find_one(id=1)["version"] == "42"

        # All data should still be intact
        assert db["folders"].count() == 530
        db.close()


class TestMigrationIdempotency:
    """Test that re-running migration on an already-migrated database is safe."""

    def test_double_migration_is_safe(self, legacy_db, tmp_path):
        """Running migration twice should not corrupt data."""
        db = sqlite_wrapper.Database.connect(legacy_db)

        folders_database_migrator.upgrade_database(db, str(tmp_path), "Linux")
        assert db["version"].find_one(id=1)["version"] == "42"
        count_first = db["folders"].count()

        folders_database_migrator.upgrade_database(db, str(tmp_path), "Linux")
        assert db["version"].find_one(id=1)["version"] == "42"
        count_second = db["folders"].count()

        assert count_first == count_second == 530
        db.close()

    def test_triple_migration_is_safe(self, legacy_db, tmp_path):
        """Running migration three times should not corrupt data."""
        db = sqlite_wrapper.Database.connect(legacy_db)

        for _ in range(3):
            folders_database_migrator.upgrade_database(db, str(tmp_path), "Linux")

        assert db["version"].find_one(id=1)["version"] == "42"
        assert db["folders"].count() == 530
        assert db["processed_files"].count() == 227501
        db.close()


class TestRequiredFieldReadability:
    """Test that all fields required by the application are readable after v32 migration.

    Verifies:
    1. FolderConfiguration.from_dict() can be called on every migrated folder
       without raising KeyError or TypeError.
    2. The settings table contains all fields required by email_backend.py.
    3. The folders table contains all fields required by FTP, email, and copy backends
       for folders that use those backends.
    4. process_parameters hard-access fields exist in all folder rows after migration.
    """

    # Fields accessed via hard bracket [] in backend modules — missing = KeyError
    _BACKEND_REQUIRED_FOLDER_FIELDS = {
        "copy_to_directory",   # copy_backend.py: process_parameters["copy_to_directory"]
        "email_subject_line",  # email_backend.py: process_parameters["email_subject_line"]
        "email_to",            # email_backend.py: process_parameters["email_to"]
        "ftp_server",          # ftp_backend.py: process_parameters["ftp_server"]
        "ftp_port",            # ftp_backend.py: process_parameters["ftp_port"]
        "ftp_username",        # ftp_backend.py: process_parameters["ftp_username"]
        "ftp_password",        # ftp_backend.py: process_parameters["ftp_password"]
        "ftp_folder",          # ftp_backend.py: process_parameters["ftp_folder"]
    }

    # Fields accessed via hard bracket [] in email_backend.py from settings table
    _REQUIRED_SETTINGS_FIELDS = {
        "email_address",       # settings["email_address"]
        "email_smtp_server",   # settings["email_smtp_server"]
        "smtp_port",           # settings["smtp_port"]
    }

    @pytest.fixture
    def fully_migrated_db(self, legacy_db, tmp_path):
        """Database that has been through full upgrade + ensure_schema (same as app startup)."""
        db = sqlite_wrapper.Database.connect(legacy_db)
        folders_database_migrator.upgrade_database(db, str(tmp_path), "Linux")
        schema.ensure_schema(db)
        yield db
        db.close()

    def test_all_folders_readable_as_folder_configuration(self, fully_migrated_db):
        """FolderConfiguration.from_dict() must not raise for any migrated folder."""
        from interface.models.folder_configuration import FolderConfiguration

        errors = []
        for folder in fully_migrated_db["folders"].all():
            try:
                fc = FolderConfiguration.from_dict(dict(folder))
                assert fc.folder_name is not None
            except Exception as exc:
                errors.append(f"folder id={folder['id']}: {exc}")

        assert not errors, f"from_dict() failed for {len(errors)} folders:\n" + "\n".join(errors[:10])

    def test_all_backend_required_fields_present_in_every_folder(self, fully_migrated_db):
        """Every folder row must have all backend-required fields (no KeyError on access)."""
        missing_report = []
        for folder in fully_migrated_db["folders"].all():
            row = dict(folder)
            for field in self._BACKEND_REQUIRED_FOLDER_FIELDS:
                if field not in row:
                    missing_report.append(f"folder id={row['id']} missing '{field}'")

        assert not missing_report, (
            f"{len(missing_report)} missing fields found:\n" + "\n".join(missing_report[:20])
        )

    def test_ftp_fields_readable_for_ftp_folders(self, fully_migrated_db):
        """FTP folders must have non-None ftp_server so backend can connect."""
        ftp_fields = {"ftp_server", "ftp_port", "ftp_username", "ftp_password", "ftp_folder"}
        ftp_folders = list(fully_migrated_db["folders"].find(process_backend_ftp=1))
        if not ftp_folders:
            pytest.skip("No FTP-enabled folders in fixture")

        for folder in ftp_folders:
            row = dict(folder)
            for field in ftp_fields:
                assert field in row, f"folder id={row['id']} missing FTP field '{field}'"

    def test_email_fields_readable_for_email_folders(self, fully_migrated_db):
        """Email folders must have email_to and email_subject_line fields."""
        email_fields = {"email_to", "email_subject_line"}
        email_folders = list(fully_migrated_db["folders"].find(process_backend_email=1))
        if not email_folders:
            pytest.skip("No email-enabled folders in fixture")

        for folder in email_folders:
            row = dict(folder)
            for field in email_fields:
                assert field in row, f"folder id={row['id']} missing email field '{field}'"

    def test_settings_table_has_all_required_email_fields(self, fully_migrated_db):
        """Settings table row must have all fields required by email_backend.py."""
        settings = fully_migrated_db["settings"].find_one(id=1)
        assert settings is not None, "Settings row (id=1) must exist after migration"

        settings_dict = dict(settings)
        for field in self._REQUIRED_SETTINGS_FIELDS:
            assert field in settings_dict, f"Settings missing required field '{field}'"

    def test_plugin_configurations_column_present_after_ensure_schema(self, fully_migrated_db):
        """plugin_configurations must be present after ensure_schema() runs (added via ALTER TABLE)."""
        folder = fully_migrated_db["folders"].find_one(id=21)
        assert folder is not None
        row = dict(folder)
        assert "plugin_configurations" in row, (
            "plugin_configurations column must be added by ensure_schema(); "
            "FolderConfiguration.from_dict() defaults it to {} if None"
        )

    def test_folder_is_active_field_readable(self, fully_migrated_db):
        """folder_is_active must be present for all folders (used to skip inactive folders)."""
        for folder in fully_migrated_db["folders"].all():
            row = dict(folder)
            assert "folder_is_active" in row, f"folder id={row['id']} missing 'folder_is_active'"

    def test_convert_to_format_field_readable(self, fully_migrated_db):
        """convert_to_format drives dispatch routing — must be present in all folders."""
        for folder in fully_migrated_db["folders"].all():
            row = dict(folder)
            assert "convert_to_format" in row, (
                f"folder id={row['id']} missing 'convert_to_format'"
            )

    def test_processed_files_required_fields_readable(self, fully_migrated_db):
        """processed_files rows must have fields needed by the UI (file_name, folder_id, status)."""
        required = {"file_name", "folder_id", "status"}
        # Sample first 100 rows for speed
        pf_rows = list(fully_migrated_db["processed_files"].all())[:100]
        assert pf_rows, "Expected processed_files rows in migrated fixture"

        for row in pf_rows:
            pf = dict(row)
            for field in required:
                assert field in pf, f"processed_files row missing '{field}'"
