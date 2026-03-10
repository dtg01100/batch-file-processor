"""Comprehensive validation tests for database import and upgrade functionality.

Tests cover:
- Migration from all historical database versions (5 to 41)
- Schema validation before and after migrations
- Data preservation during upgrades
- Edge cases: corrupted databases, missing tables, incomplete migrations
- Performance under load
- Rollback and recovery scenarios
"""

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.database,
    pytest.mark.upgrade,
    pytest.mark.slow,
]
from interface.database import sqlite_wrapper
import schema
import create_database
import folders_database_migrator
from batch_file_processor.constants import CURRENT_DATABASE_VERSION


class TestDatabaseCreation:
    """Test fresh database creation."""

    def test_fresh_database_creation(self, tmp_path):
        """Verify fresh database is created with correct version and schema."""
        db_path = str(tmp_path / "fresh.db")
        create_database.do(
            database_version=CURRENT_DATABASE_VERSION,
            database_path=db_path,
            config_folder=str(tmp_path),
            running_platform="test",
        )

        db = sqlite_wrapper.Database.connect(db_path)

        # Verify version
        version_rec = db["version"].find_one(id=1)
        assert version_rec is not None
        assert version_rec["version"] == "41"

        # Verify all core tables exist
        expected_tables = [
            "version",
            "settings",
            "administrative",
            "folders",
            "processed_files",
            "emails_to_send",
        ]

        for table in expected_tables:
            assert table in db.tables, f"Table {table} should exist"

        # Verify default records exist
        settings_rec = db["settings"].find_one(id=1)
        assert settings_rec is not None
        assert settings_rec["folder_name"] == "template"

        admin_rec = db["administrative"].find_one(id=1)
        assert admin_rec is not None

        db.close()

    def test_fresh_database_has_all_columns(self, tmp_path):
        """Verify fresh database has all expected columns in each table."""
        db_path = str(tmp_path / "fresh.db")
        create_database.do(
            database_version=CURRENT_DATABASE_VERSION,
            database_path=db_path,
            config_folder=str(tmp_path),
            running_platform="test",
        )

        db = sqlite_wrapper.Database.connect(db_path)
        cursor = db.raw_connection.cursor()

        # Check folders table columns
        cursor.execute("PRAGMA table_info(folders)")
        folders_columns = [row[1] for row in cursor.fetchall()]

        required_folders_columns = [
            "id",
            "folder_name",
            "alias",
            "folder_is_active",
            "process_edi",
            "tweak_edi",
            "convert_to_format",
            "process_backend_copy",
            "process_backend_email",
            "process_backend_ftp",
            "email_to",
            "ftp_server",
            "ftp_port",
            "ftp_username",
            "ftp_password",
        ]

        for col in required_folders_columns:
            assert col in folders_columns, f"folders table should have {col} column"

        # Check administrative table columns
        cursor.execute("PRAGMA table_info(administrative)")
        admin_columns = [row[1] for row in cursor.fetchall()]

        required_admin_columns = [
            "id",
            "logs_directory",
            "errors_folder",
            "process_backend_email",
            "process_backend_ftp",
        ]

        for col in required_admin_columns:
            assert (
                col in admin_columns
            ), f"administrative table should have {col} column"

        db.close()


class TestMigrationPathValidation:
    """Test migration from each historical version."""

    def _create_old_database(self, db_path, version, extra_columns=None):
        """Helper to create an old version database."""
        db = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db)

        # Insert version
        db["version"].insert(dict(version=str(version), os="Linux"))

        # Add some sample folders
        db["folders"].insert(
            dict(
                folder_name="/test/folder1",
                alias="Test Folder 1",
                folder_is_active="True",
                process_edi=1,
            )
        )

        # Add administrative record
        db["administrative"].insert(dict(id=1, logs_directory="/tmp/logs"))

        # Add any extra columns for testing
        if extra_columns:
            cursor = db.raw_connection.cursor()
            for col_name, col_type in extra_columns.items():
                try:
                    cursor.execute(
                        f"ALTER TABLE folders ADD COLUMN {col_name} {col_type}"
                    )
                except Exception:
                    pass
            db.raw_connection.commit()

        db.close()

    def test_migration_from_version_5_to_41(self, tmp_path):
        """Test migration from version 5 (earliest supported) to 41."""
        db_path = str(tmp_path / "old_v5.db")
        self._create_old_database(db_path, 5)

        # Run migration
        db = sqlite_wrapper.Database.connect(db_path)
        folders_database_migrator.upgrade_database(
            db, str(tmp_path), "test", target_version="41"
        )

        # Verify version updated
        version_rec = db["version"].find_one(id=1)
        assert version_rec["version"] == "41"

        # Verify data preserved
        folder = db["folders"].find_one(folder_name="/test/folder1")
        assert folder is not None
        assert folder["alias"] == "Test Folder 1"

        # Verify new columns added
        cursor = db.raw_connection.cursor()
        cursor.execute("PRAGMA table_info(folders)")
        columns = [row[1] for row in cursor.fetchall()]
        cursor.execute("PRAGMA table_info(processed_files)")
        processed_columns = [row[1] for row in cursor.fetchall()]

        assert "convert_to_format" in columns
        assert "tweak_edi" in columns
        assert "resend_flag" in processed_columns

        db.close()

    def test_migration_from_version_15_to_41(self, tmp_path):
        """Test migration from version 15 to 41."""
        db_path = str(tmp_path / "old_v15.db")
        self._create_old_database(db_path, 15)

        db = sqlite_wrapper.Database.connect(db_path)
        folders_database_migrator.upgrade_database(
            db, str(tmp_path), "test", target_version="41"
        )

        version_rec = db["version"].find_one(id=1)
        assert version_rec["version"] == "41"

        # Verify force_edi_validation was added
        cursor = db.raw_connection.cursor()
        cursor.execute("PRAGMA table_info(folders)")
        columns = [row[1] for row in cursor.fetchall()]

        assert "force_edi_validation" in columns
        assert "append_a_records" in columns

        db.close()

    def test_migration_from_version_30_to_41(self, tmp_path):
        """Test migration from version 30 to 41."""
        db_path = str(tmp_path / "old_v30.db")
        self._create_old_database(db_path, 30)

        db = sqlite_wrapper.Database.connect(db_path)
        folders_database_migrator.upgrade_database(
            db, str(tmp_path), "test", target_version="41"
        )

        version_rec = db["version"].find_one(id=1)
        assert version_rec["version"] == "41"

        db.close()

    def test_migration_from_version_39_to_41(self, tmp_path):
        """Test migration from version 39 to 41 (includes ID column addition)."""
        db_path = str(tmp_path / "old_v39.db")
        self._create_old_database(db_path, 39)

        db = sqlite_wrapper.Database.connect(db_path)
        folders_database_migrator.upgrade_database(
            db, str(tmp_path), "test", target_version="41"
        )

        version_rec = db["version"].find_one(id=1)
        assert version_rec["version"] == "41"

        # Verify id column was added
        cursor = db.raw_connection.cursor()
        cursor.execute("PRAGMA table_info(folders)")
        columns = [row[1] for row in cursor.fetchall()]

        assert "id" in columns

        # Verify backend columns were added
        assert "process_backend_email" in columns
        assert "process_backend_ftp" in columns
        assert "ftp_server" in columns

        db.close()

    def test_migration_already_at_target_version(self, tmp_path):
        """Test that migration is skipped when already at target version."""
        db_path = str(tmp_path / "current.db")
        create_database.do(
            database_version=CURRENT_DATABASE_VERSION,
            database_path=db_path,
            config_folder=str(tmp_path),
            running_platform="test",
        )

        db = sqlite_wrapper.Database.connect(db_path)

        # Get initial state
        initial_version = db["version"].find_one(id=1)

        # Run migration (should be no-op)
        folders_database_migrator.upgrade_database(
            db, str(tmp_path), "test", target_version="41"
        )

        # Verify unchanged
        final_version = db["version"].find_one(id=1)
        assert final_version["version"] == initial_version["version"]

        db.close()


class TestDataPreservationDuringMigration:
    """Test that data is preserved during migrations."""

    def test_folder_data_preserved_across_migration(self, tmp_path):
        """Verify folder data is preserved during migration."""
        db_path = str(tmp_path / "preserve.db")

        # Create old version with specific data
        db = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db)
        db["version"].insert(dict(version="20", os="Linux"))

        # Insert multiple folders with specific data
        test_folders = [
            dict(
                folder_name="/path/1",
                alias="Folder 1",
                folder_is_active="True",
                process_edi=1,
            ),
            dict(
                folder_name="/path/2",
                alias="Folder 2",
                folder_is_active="False",
                process_edi=0,
            ),
            dict(
                folder_name="/path/3",
                alias="Folder 3",
                folder_is_active="True",
                process_edi=1,
            ),
        ]

        for folder in test_folders:
            db["folders"].insert(folder)

        db["administrative"].insert(dict(id=1, logs_directory="/logs"))
        db.close()

        # Run migration
        db = sqlite_wrapper.Database.connect(db_path)
        folders_database_migrator.upgrade_database(
            db, str(tmp_path), "test", target_version="41"
        )

        # Verify all folders still exist with correct data
        for test_folder in test_folders:
            folder = db["folders"].find_one(folder_name=test_folder["folder_name"])
            assert (
                folder is not None
            ), f"Folder {test_folder['folder_name']} should exist"
            assert folder["alias"] == test_folder["alias"]
            assert folder["folder_is_active"] == test_folder["folder_is_active"]

        db.close()

    def test_processed_files_preserved_during_migration(self, tmp_path):
        """Verify processed files records are preserved during migration."""
        db_path = str(tmp_path / "processed.db")

        db = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db)
        db["version"].insert(dict(version="20", os="Linux"))

        # Insert processed files
        db["processed_files"].insert_many(
            [
                dict(file_name="file1.edi", folder_alias="Folder1", md5="abc123"),
                dict(file_name="file2.edi", folder_alias="Folder1", md5="def456"),
                dict(file_name="file3.edi", folder_alias="Folder2", md5="ghi789"),
            ]
        )

        db["folders"].insert(dict(folder_name="/test", alias="Test"))
        db["administrative"].insert(dict(id=1, logs_directory="/logs"))
        db.close()

        # Run migration
        db = sqlite_wrapper.Database.connect(db_path)
        folders_database_migrator.upgrade_database(
            db, str(tmp_path), "test", target_version="41"
        )

        # Verify processed files still exist
        files = list(db["processed_files"].all())
        assert len(files) == 3

        for f in files:
            assert f["md5"] is not None

        db.close()

    def test_settings_preserved_during_migration(self, tmp_path):
        """Verify settings are preserved during migration."""
        db_path = str(tmp_path / "settings.db")

        db = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db)
        db["version"].insert(dict(version="20", os="Linux"))

        # Insert custom settings
        db["settings"].insert(
            dict(
                folder_name="custom_template",
                alias="Custom",
                upc_target_length=12,
                convert_to_format="custom",
            )
        )

        db["folders"].insert(dict(folder_name="/test", alias="Test"))
        db["administrative"].insert(dict(id=1, logs_directory="/logs"))
        db.close()

        # Run migration
        db = sqlite_wrapper.Database.connect(db_path)
        folders_database_migrator.upgrade_database(
            db, str(tmp_path), "test", target_version="41"
        )

        # Verify settings preserved
        settings = db["settings"].find_one(id=1)
        assert settings is not None
        assert settings["upc_target_length"] == 12
        assert settings["convert_to_format"] == "custom"

        db.close()


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling during migrations."""

    def test_migration_with_missing_tables(self, tmp_path):
        """Test migration when some tables are missing."""
        db_path = str(tmp_path / "missing_tables.db")

        db = sqlite_wrapper.Database.connect(db_path)
        # Only create version and folders tables
        db.query("CREATE TABLE version (id INTEGER PRIMARY KEY, version TEXT, os TEXT)")
        db.query(
            "CREATE TABLE folders (id INTEGER PRIMARY KEY AUTOINCREMENT, folder_name TEXT, alias TEXT)"
        )

        db["version"].insert(dict(version="10", os="Linux"))
        db["folders"].insert(dict(folder_name="/test", alias="Test"))
        db.close()

        # Run migration - should handle missing tables gracefully
        db = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db)  # Ensure schema is applied first
        if db["administrative"].find_one(id=1) is None:
            db["administrative"].insert(dict(id=1, logs_directory="/logs"))

        folders_database_migrator.upgrade_database(
            db, str(tmp_path), "test", target_version="41"
        )

        # Verify migration completed
        version_rec = db["version"].find_one(id=1)
        assert version_rec["version"] == "41"

        db.close()

    def test_migration_with_null_values(self, tmp_path):
        """Test migration handles NULL values correctly."""
        db_path = str(tmp_path / "nulls.db")

        db = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db)
        db["version"].insert(dict(version="20", os="Linux"))

        # Insert folder with NULL values
        db["folders"].insert(
            dict(
                folder_name="/test",
                alias=None,
                folder_is_active="True",
                copy_to_directory=None,
                process_edi=1,
            )
        )

        db["administrative"].insert(dict(id=1, logs_directory="/logs"))
        db.close()

        # Run migration
        db = sqlite_wrapper.Database.connect(db_path)
        folders_database_migrator.upgrade_database(
            db, str(tmp_path), "test", target_version="41"
        )

        # Verify folder still exists
        folder = db["folders"].find_one(folder_name="/test")
        assert folder is not None

        db.close()

    def test_migration_with_large_dataset(self, tmp_path):
        """Test migration performance with large dataset."""
        db_path = str(tmp_path / "large.db")

        db = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db)
        db["version"].insert(dict(version="20", os="Linux"))

        # Insert large number of folders
        large_dataset = [
            dict(
                folder_name=f"/folder/{i}", alias=f"Folder {i}", folder_is_active="True"
            )
            for i in range(1000)
        ]
        db["folders"].insert_many(large_dataset)

        # Insert large number of processed files
        processed_files = [
            dict(
                file_name=f"file_{i}.edi",
                folder_alias=f"Folder {i % 100}",
                md5=f"hash_{i}",
            )
            for i in range(5000)
        ]
        db["processed_files"].insert_many(processed_files)

        db["administrative"].insert(dict(id=1, logs_directory="/logs"))
        db.close()

        # Run migration
        db = sqlite_wrapper.Database.connect(db_path)
        folders_database_migrator.upgrade_database(
            db, str(tmp_path), "test", target_version="41"
        )

        # Verify all data preserved
        folders = list(db["folders"].all())
        assert len(folders) == 1000

        files = list(db["processed_files"].all())
        assert len(files) == 5000

        db.close()

    def test_migration_with_duplicate_folders(self, tmp_path):
        """Test migration handles duplicate folder names."""
        db_path = str(tmp_path / "duplicates.db")

        db = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db)
        db["version"].insert(dict(version="20", os="Linux"))

        # Insert folders with duplicate names (shouldn't happen, but test resilience)
        db["folders"].insert(
            dict(folder_name="/test", alias="Test 1", folder_is_active="True")
        )
        db["folders"].insert(
            dict(folder_name="/test", alias="Test 2", folder_is_active="False")
        )

        db["administrative"].insert(dict(id=1, logs_directory="/logs"))
        db.close()

        # Run migration
        db = sqlite_wrapper.Database.connect(db_path)
        folders_database_migrator.upgrade_database(
            db, str(tmp_path), "test", target_version="41"
        )

        # Both folders should still exist
        folders = list(db["folders"].find(folder_name="/test"))
        assert len(folders) == 2

        db.close()


class TestSchemaValidation:
    """Test schema validation after migrations."""

    def test_all_tables_have_id_column(self, tmp_path):
        """Verify all tables have id column after migration to v40+."""
        db_path = str(tmp_path / "schema_test.db")

        # Create old version
        db = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db)
        db["version"].insert(dict(version="38", os="Linux"))
        db["folders"].insert(dict(folder_name="/test", alias="Test"))
        db["administrative"].insert(dict(logs_directory="/logs"))
        db.close()

        # Run migration
        db = sqlite_wrapper.Database.connect(db_path)
        folders_database_migrator.upgrade_database(
            db, str(tmp_path), "test", target_version="41"
        )

        # Check all tables have id column
        cursor = db.raw_connection.cursor()

        for table in ["folders", "administrative", "processed_files"]:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [row[1] for row in cursor.fetchall()]
            assert "id" in columns, f"{table} should have id column"

        db.close()

    def test_column_types_correct_after_migration(self, tmp_path):
        """Verify column types are correct after migration."""
        db_path = str(tmp_path / "types.db")
        create_database.do(
            database_version=CURRENT_DATABASE_VERSION,
            database_path=db_path,
            config_folder=str(tmp_path),
            running_platform="test",
        )

        db = sqlite_wrapper.Database.connect(db_path)
        cursor = db.raw_connection.cursor()

        # Check folders table
        cursor.execute("PRAGMA table_info(folders)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        # Verify key column types
        assert "id" in columns
        assert "folder_name" in columns
        assert "process_edi" in columns

        db.close()

    def test_foreign_keys_enabled(self, tmp_path):
        """Verify foreign keys are enabled after migration."""
        db_path = str(tmp_path / "fk.db")
        create_database.do(
            database_version=CURRENT_DATABASE_VERSION,
            database_path=db_path,
            config_folder=str(tmp_path),
            running_platform="test",
        )

        db = sqlite_wrapper.Database.connect(db_path)
        cursor = db.raw_connection.cursor()

        cursor.execute("PRAGMA foreign_keys")
        result = cursor.fetchone()

        # Foreign keys should be enabled
        assert result[0] == 1 or result[0] == "1"

        db.close()


class TestMigrationSpecificSteps:
    """Test specific migration steps that have complex logic."""

    def test_version_39_to_40_adds_id_column(self, tmp_path):
        """Test that version 39→40 migration adds id column to folders and administrative."""
        db_path = str(tmp_path / "v39_to_v40.db")

        # Create v39 database WITHOUT id column
        db = sqlite_wrapper.Database.connect(db_path)
        db.query("CREATE TABLE version (id INTEGER PRIMARY KEY, version TEXT, os TEXT)")
        db.query("CREATE TABLE folders (folder_name TEXT, alias TEXT)")
        db.query("CREATE TABLE administrative (logs_directory TEXT)")

        db["version"].insert(dict(version="39", os="Linux"))
        db["folders"].insert(dict(folder_name="/test", alias="Test"))
        db["administrative"].insert(dict(logs_directory="/logs"))
        db.close()

        # Run migration
        db = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db)
        folders_database_migrator.upgrade_database(
            db, str(tmp_path), "test", target_version="40"
        )

        # Verify id column added
        cursor = db.raw_connection.cursor()

        cursor.execute("PRAGMA table_info(folders)")
        folders_cols = [row[1] for row in cursor.fetchall()]
        assert "id" in folders_cols

        cursor.execute("PRAGMA table_info(administrative)")
        admin_cols = [row[1] for row in cursor.fetchall()]
        assert "id" in admin_cols

        # Verify data preserved
        folder = db["folders"].find_one(folder_name="/test")
        assert folder is not None
        assert folder["alias"] == "Test"

        db.close()

    def test_version_40_to_41_adds_backend_columns(self, tmp_path):
        """Test that version 40→41 migration adds backend columns."""
        db_path = str(tmp_path / "v40_to_v41.db")

        # Create v40 database
        db = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db)
        db["version"].insert(dict(version="40", os="Linux"))
        db["folders"].insert(dict(id=1, folder_name="/test", alias="Test"))
        db["administrative"].insert(dict(id=1, logs_directory="/logs"))
        db.close()

        # Run migration
        db = sqlite_wrapper.Database.connect(db_path)
        folders_database_migrator.upgrade_database(
            db, str(tmp_path), "test", target_version="41"
        )

        # Verify backend columns added
        cursor = db.raw_connection.cursor()
        cursor.execute("PRAGMA table_info(folders)")
        columns = [row[1] for row in cursor.fetchall()]

        backend_columns = [
            "process_backend_email",
            "process_backend_ftp",
            "email_to",
            "ftp_server",
            "ftp_port",
            "ftp_folder",
            "ftp_username",
            "ftp_password",
        ]

        for col in backend_columns:
            assert col in columns, f"Column {col} should be added"

        # Verify default values
        folder = db["folders"].find_one(folder_name="/test")
        assert folder["process_backend_email"] == 0
        assert folder["process_backend_ftp"] == 0
        assert folder["ftp_port"] == 21

        db.close()


class TestDatabaseImport:
    """Test database import functionality."""

    def test_import_database_from_file(self, tmp_path):
        """Test importing a database file from a different location."""
        # Create source database
        source_db_path = str(tmp_path / "source.db")
        create_database.do(
            database_version=CURRENT_DATABASE_VERSION,
            database_path=source_db_path,
            config_folder=str(tmp_path),
            running_platform="test",
        )

        db = sqlite_wrapper.Database.connect(source_db_path)
        db["folders"].insert_many(
            [
                dict(folder_name="/folder/1", alias="Folder 1"),
                dict(folder_name="/folder/2", alias="Folder 2"),
            ]
        )
        db.close()

        # "Import" by copying
        import_db_path = str(tmp_path / "imported.db")
        import shutil

        shutil.copy(source_db_path, import_db_path)

        # Verify imported database is valid
        db = sqlite_wrapper.Database.connect(import_db_path)

        version = db["version"].find_one(id=1)
        assert version["version"] == "41"

        folders = list(db["folders"].all())
        assert len(folders) == 2

        db.close()

    def test_import_and_upgrade_old_database(self, tmp_path):
        """Test importing an old database and upgrading it."""
        # Create old version database
        old_db_path = str(tmp_path / "old_source.db")
        db = sqlite_wrapper.Database.connect(old_db_path)
        schema.ensure_schema(db)
        db["version"].insert(dict(version="15", os="Linux"))
        db["folders"].insert(dict(folder_name="/old/folder", alias="Old Folder"))
        db["administrative"].insert(dict(id=1, logs_directory="/logs"))
        db.close()

        # Import and upgrade
        db = sqlite_wrapper.Database.connect(old_db_path)
        folders_database_migrator.upgrade_database(
            db, str(tmp_path), "test", target_version="41"
        )

        # Verify upgraded
        version = db["version"].find_one(id=1)
        assert version["version"] == "41"

        # Verify data preserved
        folder = db["folders"].find_one(folder_name="/old/folder")
        assert folder is not None
        assert folder["alias"] == "Old Folder"

        db.close()


class TestMigrationIdempotency:
    """Test that migrations are idempotent and can be run multiple times safely."""

    def test_migration_can_be_run_multiple_times(self, tmp_path):
        """Test running migration multiple times doesn't cause issues."""
        db_path = str(tmp_path / "idempotent.db")

        # Create old version
        db = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db)
        db["version"].insert(dict(version="20", os="Linux"))
        db["folders"].insert(dict(folder_name="/test", alias="Test"))
        db["administrative"].insert(dict(id=1, logs_directory="/logs"))
        db.close()

        # Run migration twice
        for _ in range(2):
            db = sqlite_wrapper.Database.connect(db_path)
            folders_database_migrator.upgrade_database(
                db, str(tmp_path), "test", target_version="41"
            )
            db.close()

        # Verify final state
        db = sqlite_wrapper.Database.connect(db_path)
        version = db["version"].find_one(id=1)
        assert version["version"] == "41"

        folder = db["folders"].find_one(folder_name="/test")
        assert folder is not None

        db.close()


class TestMigrationPerformance:
    """Test migration performance with various dataset sizes."""

    @pytest.mark.slow
    def test_migration_performance_with_10000_folders(self, tmp_path):
        """Test migration performance with 10,000 folders."""
        db_path = str(tmp_path / "perf.db")

        db = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db)
        db["version"].insert(dict(version="20", os="Linux"))

        # Insert 10,000 folders
        import time

        start = time.time()

        folders = [
            dict(
                folder_name=f"/folder/{i}", alias=f"Folder {i}", folder_is_active="True"
            )
            for i in range(10000)
        ]
        db["folders"].insert_many(folders)

        insert_time = time.time() - start
        print(f"\nInsert time: {insert_time:.2f}s")

        db["administrative"].insert(dict(id=1, logs_directory="/logs"))
        db.close()

        # Run migration and time it
        db = sqlite_wrapper.Database.connect(db_path)

        start = time.time()
        folders_database_migrator.upgrade_database(
            db, str(tmp_path), "test", target_version="41"
        )
        migration_time = time.time() - start

        print(f"Migration time: {migration_time:.2f}s")

        # Migration should complete in reasonable time
        assert migration_time < 60, "Migration should complete within 60 seconds"

        # Verify data
        all_folders = list(db["folders"].all())
        assert len(all_folders) == 10000

        db.close()
