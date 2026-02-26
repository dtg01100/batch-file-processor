"""Integration tests using a real legacy v32 production database.

Tests the complete upgrade path from v32 → v42 using an actual database
file from a legacy Windows installation. This database contains:
- 530 folder configurations
- 227,501 processed file records
- Real production settings and administrative data

The database is at version 32 with the Windows platform marker.
"""

import os
import shutil
import sqlite3

import dataset
import pytest

import folders_database_migrator
import schema


pytestmark = [pytest.mark.integration]

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), '..', 'fixtures')
LEGACY_DB_PATH = os.path.join(FIXTURES_DIR, 'legacy_v32_folders.db')


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
    db = dataset.connect('sqlite:///' + legacy_db)
    folders_database_migrator.upgrade_database(db, str(tmp_path), "Linux")
    yield db
    db.close()


class TestLegacyDatabasePreConditions:
    """Verify the legacy database is in the expected v32 state before migration."""

    def test_legacy_db_is_version_32(self, legacy_db):
        """The fixture database should be at version 32."""
        db = dataset.connect('sqlite:///' + legacy_db)
        version = db['version'].find_one(id=1)
        assert version['version'] == "32"
        assert version['os'] == "Windows"
        db.close()

    def test_legacy_db_has_530_folders(self, legacy_db):
        """The fixture database should contain 530 folder records."""
        db = dataset.connect('sqlite:///' + legacy_db)
        count = db['folders'].count()
        assert count == 530
        db.close()

    def test_legacy_db_has_227501_processed_files(self, legacy_db):
        """The fixture database should contain 227,501 processed file records."""
        db = dataset.connect('sqlite:///' + legacy_db)
        count = db['processed_files'].count()
        assert count == 227501
        db.close()

    def test_legacy_db_has_expected_tables(self, legacy_db):
        """The fixture database should have all 8 expected tables."""
        db = dataset.connect('sqlite:///' + legacy_db)
        tables = db.tables
        expected = {'version', 'administrative', 'folders', 'processed_files',
                    'settings', 'emails_to_send', 'working_batch_emails_to_send',
                    'sent_emails_removal_queue'}
        assert expected.issubset(set(tables))
        db.close()

    def test_legacy_db_has_no_plugin_config(self, legacy_db):
        """v32 database should NOT have plugin_config column yet."""
        conn = sqlite3.connect(legacy_db)
        cursor = conn.execute("PRAGMA table_info(folders)")
        columns = {row[1] for row in cursor.fetchall()}
        assert 'plugin_config' not in columns
        conn.close()

    def test_legacy_db_has_no_edi_format(self, legacy_db):
        """v32 database should NOT have edi_format column yet."""
        conn = sqlite3.connect(legacy_db)
        cursor = conn.execute("PRAGMA table_info(folders)")
        columns = {row[1] for row in cursor.fetchall()}
        assert 'edi_format' not in columns
        conn.close()

    def test_legacy_db_has_no_timestamps(self, legacy_db):
        """v32 database should NOT have created_at/updated_at columns yet."""
        conn = sqlite3.connect(legacy_db)
        cursor = conn.execute("PRAGMA table_info(folders)")
        columns = {row[1] for row in cursor.fetchall()}
        assert 'created_at' not in columns
        assert 'updated_at' not in columns
        conn.close()

    def test_legacy_db_has_string_booleans(self, legacy_db):
        """v32 database should have string "True"/"False" boolean values."""
        db = dataset.connect('sqlite:///' + legacy_db)
        # Folder id=21 has folder_is_active="True"
        folder = db['folders'].find_one(id=21)
        assert folder is not None
        assert folder['folder_is_active'] == "True"
        db.close()


class TestUpgradeCompletes:
    """Test that the full v32 → v42 migration completes successfully."""

    def test_upgrade_reaches_v42(self, migrated_db):
        """Migration should bring the database to version 42."""
        version = migrated_db['version'].find_one(id=1)
        assert version['version'] == "42"

    def test_upgrade_updates_os_field(self, migrated_db):
        """Migration should update the OS field to the current platform."""
        version = migrated_db['version'].find_one(id=1)
        # upgrade_database() is called with "Linux", so OS gets updated
        assert version['os'] == "Linux"


class TestDataPreservation:
    """Test that all data survives the migration intact."""

    def test_all_530_folders_preserved(self, migrated_db):
        """All 530 folder records should survive migration."""
        count = migrated_db['folders'].count()
        assert count == 530

    def test_all_processed_files_preserved(self, migrated_db):
        """All 227,501 processed file records should survive migration."""
        count = migrated_db['processed_files'].count()
        assert count == 227501

    def test_specific_folder_data_preserved(self, migrated_db):
        """Specific folder data should be preserved exactly."""
        folder = migrated_db['folders'].find_one(id=21)
        assert folder is not None
        assert folder['alias'] == "012258"
        assert folder['convert_to_format'] == "csv"

    def test_second_folder_data_preserved(self, migrated_db):
        """Second sample folder should be preserved."""
        folder = migrated_db['folders'].find_one(id=29)
        assert folder is not None
        assert folder['alias'] == "PIERCES"

    def test_settings_preserved(self, migrated_db):
        """Settings table data should be preserved."""
        settings = migrated_db['settings'].find_one(id=1)
        assert settings is not None
        assert settings['smtp_port'] == 587
        assert settings['email_smtp_server'] == "smtp.example.com"
        assert settings['odbc_driver'] == "iSeries Access ODBC Driver"
        assert settings['as400_address'] == "10.0.0.100"

    def test_administrative_preserved(self, migrated_db):
        """Administrative table data should be preserved."""
        admin = migrated_db['administrative'].find_one(id=1)
        assert admin is not None
        assert admin['logs_directory'] == "C:/ProgramData/BatchFileSender/Logs"

    def test_processed_file_data_preserved(self, migrated_db):
        """Individual processed file records should be preserved."""
        pf = migrated_db['processed_files'].find_one(id=1)
        assert pf is not None
        assert pf['file_name'] == r"D:\DATA\OUT\012258\012258.115"
        assert pf['folder_id'] == 21

    def test_email_tables_preserved(self, migrated_db):
        """Email-related tables should still exist after migration."""
        tables = migrated_db.tables
        assert 'emails_to_send' in tables
        assert 'working_batch_emails_to_send' in tables
        assert 'sent_emails_removal_queue' in tables


class TestNewColumnsAdded:
    """Test that migration adds all expected new columns."""

    def test_folders_has_plugin_config(self, migrated_db):
        """Folders table should have plugin_config column after migration."""
        folder = migrated_db['folders'].find_one(id=21)
        assert 'plugin_config' in folder

    def test_folders_has_edi_format(self, migrated_db):
        """Folders table should have edi_format column with default value."""
        folder = migrated_db['folders'].find_one(id=21)
        assert 'edi_format' in folder
        assert folder['edi_format'] == "default"

    def test_folders_has_timestamps(self, migrated_db):
        """Folders table should have created_at and updated_at columns."""
        folder = migrated_db['folders'].find_one(id=21)
        assert 'created_at' in folder
        assert folder['created_at'] is not None
        assert 'updated_at' in folder
        assert folder['updated_at'] is not None

    def test_folders_has_split_edi_filter_columns(self, migrated_db):
        """Folders table should have split_edi_filter_categories and split_edi_filter_mode."""
        folder = migrated_db['folders'].find_one(id=21)
        assert 'split_edi_filter_categories' in folder
        assert 'split_edi_filter_mode' in folder

    def test_administrative_has_plugin_config(self, migrated_db):
        """Administrative table should have plugin_config column."""
        admin = migrated_db['administrative'].find_one(id=1)
        assert 'plugin_config' in admin

    def test_administrative_has_edi_format(self, migrated_db):
        """Administrative table should have edi_format column."""
        admin = migrated_db['administrative'].find_one(id=1)
        assert 'edi_format' in admin
        assert admin['edi_format'] == "default"

    def test_administrative_has_timestamps(self, migrated_db):
        """Administrative table should have created_at and updated_at."""
        admin = migrated_db['administrative'].find_one(id=1)
        assert 'created_at' in admin
        assert admin['created_at'] is not None
        assert 'updated_at' in admin

    def test_version_has_notes_column(self, migrated_db):
        """Version table should have notes column after v37→v38."""
        version = migrated_db['version'].find_one(id=1)
        assert 'notes' in version

    def test_processed_files_has_new_columns(self, migrated_db):
        """Processed files should have new columns from v34→v35."""
        pf = migrated_db['processed_files'].find_one(id=1)
        assert 'filename' in pf
        assert 'original_path' in pf
        assert 'processed_path' in pf
        assert 'status' in pf
        assert 'error_message' in pf
        assert 'convert_format' in pf
        assert 'sent_to' in pf

    def test_settings_has_timestamps(self, migrated_db):
        """Settings table should have created_at and updated_at."""
        settings = migrated_db['settings'].find_one(id=1)
        assert 'created_at' in settings
        assert 'updated_at' in settings


class TestBooleanNormalization:
    """Test that string booleans are normalized to integers (v40→v41)."""

    def test_folder_is_active_normalized(self, migrated_db):
        """folder_is_active should be normalized from "True"/"False" to 1/0."""
        folder = migrated_db['folders'].find_one(id=21)
        # Was "True" in legacy, should now be 1 or "1"
        assert str(folder['folder_is_active']) in ('1', '0')
        assert str(folder['folder_is_active']) not in ('True', 'False')

    def test_process_edi_normalized(self, migrated_db):
        """process_edi should be normalized from "True"/"False" to 1/0."""
        folder = migrated_db['folders'].find_one(id=21)
        assert str(folder['process_edi']) in ('1', '0')
        assert str(folder['process_edi']) not in ('True', 'False')

    def test_active_folder_has_value_1(self, migrated_db):
        """Folder id=21 was active ("True"), should now be 1."""
        folder = migrated_db['folders'].find_one(id=21)
        assert int(folder['folder_is_active']) == 1

    @pytest.mark.slow
    def test_boolean_fields_across_multiple_folders(self, migrated_db):
        """Check boolean normalization across several folders."""
        boolean_fields = [
            'folder_is_active', 'process_edi', 'calculate_upc_check_digit',
            'include_a_records', 'include_c_records', 'include_headers',
            'filter_ampersand', 'pad_a_records'
        ]
        for folder in migrated_db['folders'].find(_limit=20):
            for field in boolean_fields:
                if field in folder and folder[field] is not None:
                    val = str(folder[field])
                    assert val not in ('True', 'False'), (
                        f"Folder {folder['id']}.{field} = {val!r} still has string boolean"
                    )


class TestIndexesCreated:
    """Test that migration creates expected indexes (v35→v36)."""

    def test_idx_folders_active_exists(self, legacy_db, tmp_path):
        """idx_folders_active index should exist after migration."""
        db = dataset.connect('sqlite:///' + legacy_db)
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
        db = dataset.connect('sqlite:///' + legacy_db)
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
        db = dataset.connect('sqlite:///' + legacy_db)
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
        db = dataset.connect('sqlite:///' + legacy_db)
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

    def test_users_table_exists(self, migrated_db):
        """users table should exist after v42 migration."""
        assert 'users' in migrated_db.tables

    def test_organizations_table_exists(self, migrated_db):
        """organizations table should exist after v42 migration."""
        assert 'organizations' in migrated_db.tables

    def test_projects_table_exists(self, migrated_db):
        """projects table should exist after v42 migration."""
        assert 'projects' in migrated_db.tables

    def test_files_table_exists(self, migrated_db):
        """files table should exist after v42 migration."""
        assert 'files' in migrated_db.tables

    def test_batches_table_exists(self, migrated_db):
        """batches table should exist after v42 migration."""
        assert 'batches' in migrated_db.tables

    def test_processors_table_exists(self, migrated_db):
        """processors table should exist after v42 migration."""
        assert 'processors' in migrated_db.tables

    def test_processing_jobs_table_exists(self, migrated_db):
        """processing_jobs table should exist after v42 migration."""
        assert 'processing_jobs' in migrated_db.tables

    def test_job_logs_table_exists(self, migrated_db):
        """job_logs table should exist after v42 migration."""
        assert 'job_logs' in migrated_db.tables

    def test_tags_table_exists(self, migrated_db):
        """tags table should exist after v42 migration."""
        assert 'tags' in migrated_db.tables

    def test_file_tags_table_exists(self, migrated_db):
        """file_tags table should exist after v42 migration."""
        assert 'file_tags' in migrated_db.tables


class TestTableRebuild:
    """Test that v39→v40 table rebuild produces correct PRIMARY KEY ids."""

    def test_folders_has_primary_key(self, legacy_db, tmp_path):
        """After migration, folders table should have PRIMARY KEY on id."""
        db = dataset.connect('sqlite:///' + legacy_db)
        folders_database_migrator.upgrade_database(db, str(tmp_path), "Linux")
        db.close()

        conn = sqlite3.connect(legacy_db)
        cursor = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='folders'"
        )
        create_sql = cursor.fetchone()[0]
        conn.close()
        # After rebuild, should have PRIMARY KEY on id
        assert 'PRIMARY KEY' in create_sql.upper()

    def test_administrative_has_primary_key(self, legacy_db, tmp_path):
        """After migration, administrative table should have PRIMARY KEY on id."""
        db = dataset.connect('sqlite:///' + legacy_db)
        folders_database_migrator.upgrade_database(db, str(tmp_path), "Linux")
        db.close()

        conn = sqlite3.connect(legacy_db)
        cursor = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='administrative'"
        )
        create_sql = cursor.fetchone()[0]
        conn.close()
        assert 'PRIMARY KEY' in create_sql.upper()


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
        folder_id = migrated_db['folders'].insert(new_folder)
        assert folder_id is not None

        # Verify it was inserted
        folder = migrated_db['folders'].find_one(id=folder_id)
        assert folder['folder_name'] == "/new/test/folder"
        assert folder['alias'] == "New Test Folder"

    def test_can_update_existing_folder(self, migrated_db):
        """Should be able to update an existing folder in the migrated database."""
        folder = migrated_db['folders'].find_one(id=21)
        original_alias = folder['alias']

        migrated_db['folders'].update(
            dict(id=21, alias="UPDATED_ALIAS"), ['id']
        )

        updated = migrated_db['folders'].find_one(id=21)
        assert updated['alias'] == "UPDATED_ALIAS"

        # Restore
        migrated_db['folders'].update(
            dict(id=21, alias=original_alias), ['id']
        )

    def test_can_delete_folder(self, migrated_db):
        """Should be able to delete a folder from the migrated database."""
        # Insert a test folder first
        test_id = migrated_db['folders'].insert(dict(
            folder_name="/delete/me",
            alias="Delete Me",
        ))

        migrated_db['folders'].delete(id=test_id)
        assert migrated_db['folders'].find_one(id=test_id) is None

    def test_can_query_folders_by_active_status(self, migrated_db):
        """Should be able to query folders by active status after boolean normalization."""
        active_folders = list(migrated_db['folders'].find(folder_is_active=1))
        assert len(active_folders) > 0

    def test_can_insert_processed_file(self, migrated_db):
        """Should be able to insert a new processed file record."""
        new_pf = dict(
            file_name="/test/file.edi",
            file_checksum="abc123",
            folder_id=21,
            status="processed",
        )
        pf_id = migrated_db['processed_files'].insert(new_pf)
        assert pf_id is not None

        pf = migrated_db['processed_files'].find_one(id=pf_id)
        assert pf['file_name'] == "/test/file.edi"

    def test_can_update_settings(self, migrated_db):
        """Should be able to update settings in the migrated database."""
        migrated_db['settings'].update(
            dict(id=1, smtp_port=465), ['id']
        )
        settings = migrated_db['settings'].find_one(id=1)
        assert settings['smtp_port'] == 465

    def test_can_update_administrative(self, migrated_db):
        """Should be able to update administrative record in the migrated database."""
        migrated_db['administrative'].update(
            dict(id=1, logs_directory="/new/logs/path"), ['id']
        )
        admin = migrated_db['administrative'].find_one(id=1)
        assert admin['logs_directory'] == "/new/logs/path"


class TestSchemaEnsureOnMigratedDb:
    """Test that schema.ensure_schema() works on the migrated database."""

    def test_ensure_schema_is_idempotent(self, legacy_db, tmp_path):
        """Running ensure_schema() on a migrated database should not break anything."""
        db = dataset.connect('sqlite:///' + legacy_db)
        folders_database_migrator.upgrade_database(db, str(tmp_path), "Linux")

        # Count folders before
        count_before = db['folders'].count()

        # Run ensure_schema
        schema.ensure_schema(db)

        # Count folders after - should be the same
        count_after = db['folders'].count()
        assert count_after == count_before

        # Version should still be 42
        version = db['version'].find_one(id=1)
        assert version['version'] == "42"
        db.close()


class TestIntermediateMigrationStops:
    """Test stopping migration at intermediate versions using target_version."""

    def test_stop_at_v33(self, legacy_db, tmp_path):
        """Migration should stop at v33 when target_version='33'."""
        db = dataset.connect('sqlite:///' + legacy_db)
        folders_database_migrator.upgrade_database(
            db, str(tmp_path), "Linux", target_version="33"
        )
        version = db['version'].find_one(id=1)
        assert version['version'] == "33"

        # Should have plugin_config now
        folder = db['folders'].find_one(id=21)
        assert 'plugin_config' in folder
        assert 'split_edi_filter_categories' in folder
        db.close()

    def test_stop_at_v36(self, legacy_db, tmp_path):
        """Migration should stop at v36 (after indexes are created)."""
        db = dataset.connect('sqlite:///' + legacy_db)
        folders_database_migrator.upgrade_database(
            db, str(tmp_path), "Linux", target_version="36"
        )
        version = db['version'].find_one(id=1)
        assert version['version'] == "36"

        # Should have timestamps from v34
        folder = db['folders'].find_one(id=21)
        assert 'created_at' in folder
        db.close()

    def test_stop_at_v39(self, legacy_db, tmp_path):
        """Migration should stop at v39 (after edi_format added)."""
        db = dataset.connect('sqlite:///' + legacy_db)
        folders_database_migrator.upgrade_database(
            db, str(tmp_path), "Linux", target_version="39"
        )
        version = db['version'].find_one(id=1)
        assert version['version'] == "39"

        folder = db['folders'].find_one(id=21)
        assert 'edi_format' in folder
        assert folder['edi_format'] == "default"
        db.close()

    def test_resume_from_v33_to_v42(self, legacy_db, tmp_path):
        """Should be able to migrate to v33, then resume to v42."""
        db = dataset.connect('sqlite:///' + legacy_db)

        # First stop at v33
        folders_database_migrator.upgrade_database(
            db, str(tmp_path), "Linux", target_version="33"
        )
        assert db['version'].find_one(id=1)['version'] == "33"

        # Then continue to v42
        folders_database_migrator.upgrade_database(
            db, str(tmp_path), "Linux"
        )
        assert db['version'].find_one(id=1)['version'] == "42"

        # All data should still be intact
        assert db['folders'].count() == 530
        db.close()


class TestMigrationIdempotency:
    """Test that re-running migration on an already-migrated database is safe."""

    def test_double_migration_is_safe(self, legacy_db, tmp_path):
        """Running migration twice should not corrupt data."""
        db = dataset.connect('sqlite:///' + legacy_db)

        folders_database_migrator.upgrade_database(db, str(tmp_path), "Linux")
        assert db['version'].find_one(id=1)['version'] == "42"
        count_first = db['folders'].count()

        folders_database_migrator.upgrade_database(db, str(tmp_path), "Linux")
        assert db['version'].find_one(id=1)['version'] == "42"
        count_second = db['folders'].count()

        assert count_first == count_second == 530
        db.close()

    def test_triple_migration_is_safe(self, legacy_db, tmp_path):
        """Running migration three times should not corrupt data."""
        db = dataset.connect('sqlite:///' + legacy_db)

        for _ in range(3):
            folders_database_migrator.upgrade_database(db, str(tmp_path), "Linux")

        assert db['version'].find_one(id=1)['version'] == "42"
        assert db['folders'].count() == 530
        assert db['processed_files'].count() == 227501
        db.close()
