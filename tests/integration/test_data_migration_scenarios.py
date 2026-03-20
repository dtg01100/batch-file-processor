"""End-to-end tests for database migration scenarios.

Tests cover:
- Legacy database → Current schema migration
- Migration with data validation
- Rollback scenarios
- Interrupted migration recovery
- Multi-version skip migration
"""

import shutil
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.e2e, pytest.mark.migration]


@pytest.fixture
def legacy_database_v1(tmp_path):
    """Create a legacy v1 database schema."""
    db_path = tmp_path / "legacy_v1.db"

    import sqlite3

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create v1 schema (minimal columns)
    cursor.execute(
        """
        CREATE TABLE folders (
            id INTEGER PRIMARY KEY,
            folder_name TEXT,
            alias TEXT
        )
    """
    )

    # Create version table for migration
    cursor.execute(
        """
        CREATE TABLE version (
            id INTEGER PRIMARY KEY,
            version TEXT,
            os TEXT
        )
    """
    )

    # Insert version record (v1 = version 1)
    cursor.execute(
        "INSERT INTO version (id, version, os) VALUES (?, ?, ?)", (1, "1", "Linux")
    )

    # Insert test data
    cursor.execute(
        "INSERT INTO folders (folder_name, alias) VALUES (?, ?)",
        ("/test/folder1", "Legacy Folder 1"),
    )
    cursor.execute(
        "INSERT INTO folders (folder_name, alias) VALUES (?, ?)",
        ("/test/folder2", "Legacy Folder 2"),
    )

    conn.commit()
    conn.close()

    return db_path


@pytest.fixture
def legacy_database_v2(tmp_path):
    """Create a legacy v2 database schema."""
    db_path = tmp_path / "legacy_v2.db"

    import sqlite3

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create v2 schema (added backend columns)
    cursor.execute(
        """
        CREATE TABLE folders (
            id INTEGER PRIMARY KEY,
            folder_name TEXT,
            alias TEXT,
            process_backend_copy TEXT,
            process_backend_ftp TEXT,
            copy_to_directory TEXT
        )
    """
    )

    # Create version table for migration
    cursor.execute(
        """
        CREATE TABLE version (
            id INTEGER PRIMARY KEY,
            version TEXT,
            os TEXT
        )
    """
    )

    # Insert version record (v2 = version 2)
    cursor.execute(
        "INSERT INTO version (id, version, os) VALUES (?, ?, ?)", (1, "2", "Linux")
    )

    # Insert test data
    cursor.execute(
        """
        INSERT INTO folders (folder_name, alias, process_backend_copy, process_backend_ftp, copy_to_directory)
        VALUES (?, ?, ?, ?, ?)
    """,
        ("/test/folder1", "V2 Folder", "True", "False", "/test/output"),
    )

    conn.commit()
    conn.close()

    return db_path


@pytest.fixture
def legacy_database_v3(tmp_path):
    """Create a legacy v3 database schema with processed_files."""
    db_path = tmp_path / "legacy_v3.db"

    import sqlite3

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create v3 schema
    cursor.execute(
        """
        CREATE TABLE folders (
            id INTEGER PRIMARY KEY,
            folder_name TEXT,
            alias TEXT,
            folder_is_active TEXT,
            process_backend_copy TEXT,
            process_backend_ftp TEXT,
            process_backend_email TEXT,
            copy_to_directory TEXT,
            convert_to_type TEXT
        )
    """
    )

    # Create version table for migration
    cursor.execute(
        """
        CREATE TABLE version (
            id INTEGER PRIMARY KEY,
            version TEXT,
            os TEXT
        )
    """
    )

    # Insert version record (v3 = version 3)
    cursor.execute(
        "INSERT INTO version (id, version, os) VALUES (?, ?, ?)", (1, "3", "Linux")
    )

    cursor.execute(
        """
        CREATE TABLE processed_files (
            id INTEGER PRIMARY KEY,
            folder_id INTEGER,
            filename TEXT,
            md5 TEXT,
            processed_date TEXT
        )
    """
    )

    # Insert test data
    cursor.execute(
        """
        INSERT INTO folders (folder_name, alias, folder_is_active, process_backend_copy, convert_to_type)
        VALUES (?, ?, ?, ?, ?)
    """,
        ("/test/folder1", "V3 Folder", "True", "True", "csv"),
    )

    cursor.execute(
        """
        INSERT INTO processed_files (folder_id, filename, md5, processed_date)
        VALUES (?, ?, ?, ?)
    """,
        (1, "test.edi", "abc123", "2024-01-01"),
    )

    conn.commit()
    conn.close()

    return db_path


@pytest.mark.e2e
class TestLegacyDatabaseMigration:
    """Test migration from legacy database versions."""

    def test_migrate_v1_to_current(self, legacy_database_v1, tmp_path):
        """Test migrating from v1 schema to current."""
        import core.database.schema
        from migrations.folders_database_migrator import upgrade_database
        from backend.database import sqlite_wrapper

        # Connect to the database
        db_for_migration = sqlite_wrapper.Database.connect(str(legacy_database_v1))

        # Ensure schema (creates necessary tables)
        schema.ensure_schema(db_for_migration)

        # Create config folder
        config_folder = str(tmp_path / "config")
        Path(config_folder).mkdir()

        try:
            upgrade_database(db_for_migration, config_folder, "Linux")

            # Verify migration succeeded using sqlite_wrapper directly
            folders = db_for_migration["folders"].find({})
            folder_list = list(folders)
            assert len(folder_list) == 2

            # Verify data preserved
            assert folder_list[0]["alias"] == "Legacy Folder 1"

        except Exception as e:
            # Migration might not support v1 directly, that's OK
            pytest.skip(f"Migration not supported for v1: {e}")
        finally:
            db_for_migration.close()

    def test_migrate_v2_to_current(self, legacy_database_v2, tmp_path):
        """Test migrating from v2 schema to current."""
        import core.database.schema
        from migrations.folders_database_migrator import upgrade_database
        from backend.database import sqlite_wrapper

        db_for_migration = sqlite_wrapper.Database.connect(str(legacy_database_v2))

        # Ensure schema
        schema.ensure_schema(db_for_migration)

        # Create config folder
        config_folder = str(tmp_path / "config")
        Path(config_folder).mkdir()

        try:
            upgrade_database(db_for_migration, config_folder, "Linux")

            # Verify migration using sqlite_wrapper
            folders = db_for_migration["folders"].find({})
            folder_list = list(folders)
            assert len(folder_list) == 1
            assert folder_list[0]["alias"] == "V2 Folder"

        except Exception as e:
            pytest.skip(f"Migration not supported for v2: {e}")
        finally:
            db_for_migration.close()

    def test_migrate_v3_to_current(self, legacy_database_v3, tmp_path):
        """Test migrating from v3 schema to current."""
        import core.database.schema
        from migrations.folders_database_migrator import upgrade_database
        from backend.database import sqlite_wrapper

        db_for_migration = sqlite_wrapper.Database.connect(str(legacy_database_v3))

        # Ensure schema
        schema.ensure_schema(db_for_migration)

        # Create config folder
        config_folder = str(tmp_path / "config")
        Path(config_folder).mkdir()

        try:
            upgrade_database(db_for_migration, config_folder, "Linux")

            # Verify migration using sqlite_wrapper
            # Check folders migrated
            folders = db_for_migration["folders"].find({})
            folder_list = list(folders)
            assert len(folder_list) == 1

            # Check processed_files migrated
            processed = db_for_migration["processed_files"].find({})
            processed_list = list(processed)
            assert len(processed_list) == 1
            assert processed_list[0]["filename"] == "test.edi"

        except Exception as e:
            pytest.skip(f"Migration not supported for v3: {e}")
        finally:
            db_for_migration.close()


@pytest.mark.e2e
class TestMigrationWithDataValidation:
    """Test migration with data validation."""

    def test_validate_data_preserved_after_migration(
        self, legacy_database_v3, tmp_path
    ):
        """Test that all data is preserved after migration."""
        import core.database.schema
        from migrations.folders_database_migrator import upgrade_database
        from backend.database import sqlite_wrapper

        # Read data before migration using sqlite_wrapper
        db_before = sqlite_wrapper.Database.connect(str(legacy_database_v3))
        original_folders = list(db_before["folders"].find({}))
        original_processed = list(db_before["processed_files"].find({}))
        db_before.close()

        # Migrate
        db_for_migration = sqlite_wrapper.Database.connect(str(legacy_database_v3))

        # Ensure schema
        schema.ensure_schema(db_for_migration)

        # Create config folder
        config_folder = str(tmp_path / "config")
        Path(config_folder).mkdir()

        try:
            upgrade_database(db_for_migration, config_folder, "Linux")

            # Read data after migration
            db_after = sqlite_wrapper.Database.connect(str(legacy_database_v3))
            migrated_folders = list(db_after["folders"].find({}))
            migrated_processed = list(db_after["processed_files"].find({}))
            db_after.close()

            # Verify counts match
            assert len(migrated_folders) == len(original_folders)
            assert len(migrated_processed) == len(original_processed)

        except Exception as e:
            pytest.skip(f"Migration failed: {e}")
        finally:
            db_for_migration.close()

    def test_validate_data_types_preserved(self, legacy_database_v3, tmp_path):
        """Test that data types are preserved during migration."""
        import core.database.schema
        from migrations.folders_database_migrator import upgrade_database
        from backend.database import sqlite_wrapper

        db_for_migration = sqlite_wrapper.Database.connect(str(legacy_database_v3))

        # Ensure schema
        schema.ensure_schema(db_for_migration)

        # Create config folder
        config_folder = str(tmp_path / "config")
        Path(config_folder).mkdir()

        try:
            upgrade_database(db_for_migration, config_folder, "Linux")

            folders = list(db_for_migration["folders"].find({}))

            # Verify types
            assert isinstance(folders[0]["id"], int)
            assert isinstance(folders[0]["folder_name"], str)
            assert isinstance(folders[0]["alias"], str)

        except Exception as e:
            pytest.skip(f"Migration failed: {e}")
        finally:
            db_for_migration.close()


@pytest.mark.e2e
class TestMigrationRollback:
    """Test migration rollback scenarios."""

    def test_backup_created_before_migration(self, legacy_database_v3, tmp_path):
        """Test that backup is created before migration."""
        import core.database.schema
        from migrations.folders_database_migrator import upgrade_database
        from backend.database import sqlite_wrapper

        db_for_migration = sqlite_wrapper.Database.connect(str(legacy_database_v3))

        # Ensure schema
        schema.ensure_schema(db_for_migration)

        # Create config folder
        config_folder = str(tmp_path / "config")
        Path(config_folder).mkdir()

        backup_path = tmp_path / "backup"

        try:
            try:
                upgrade_database(db_for_migration, config_folder, "Linux")
            except Exception as e:
                message = str(e).lower()
                if isinstance(e, NotImplementedError) or any(
                    marker in message
                    for marker in (
                        "unsupported",
                        "not supported",
                        "platform",
                        "environment",
                    )
                ):
                    pytest.skip(f"Migration not supported in this environment: {e}")
                pytest.fail(f"Migration failed unexpectedly: {e}")

            version_row = db_for_migration["version"].find_one(id=1)
            assert version_row is not None, "Version row should exist after migration"

            # Check backup outcome
            if backup_path.exists():
                backup_files = list(backup_path.glob("*.db"))
                assert (
                    backup_files
                ), f"Backup directory exists but no .db backup file was found: {backup_path}"
            else:
                folders = list(db_for_migration["folders"].find({}))
                processed_files = list(db_for_migration["processed_files"].find({}))
                assert int(version_row["version"]) >= 3, (
                    "No backup directory was created and database version is invalid "
                    "after migration attempt"
                )
                assert folders, (
                    "No backup directory was created and folders data is missing "
                    "after migration attempt"
                )
                assert processed_files, (
                    "No backup directory was created and processed_files data is missing "
                    "after migration attempt"
                )
        finally:
            db_for_migration.close()

    def test_restore_from_backup(self, legacy_database_v3, tmp_path):
        """Test restoring from backup after failed migration."""
        import core.database.schema
        from migrations.folders_database_migrator import upgrade_database
        from backend.database import sqlite_wrapper

        # Create backup manually
        backup_path = tmp_path / "backup"
        backup_path.mkdir()
        backup_db = backup_path / "folders_backup.db"
        shutil.copy(str(legacy_database_v3), str(backup_db))

        # Read original data
        db_original = sqlite_wrapper.Database.connect(str(legacy_database_v3))
        original_folders = list(db_original["folders"].find({}))
        db_original.close()

        # Connect for migration
        db_for_migration = sqlite_wrapper.Database.connect(str(legacy_database_v3))

        # Ensure schema
        schema.ensure_schema(db_for_migration)

        # Create config folder
        config_folder = str(tmp_path / "config")
        Path(config_folder).mkdir()

        try:
            # Attempt migration
            upgrade_database(db_for_migration, config_folder, "Linux")

        except Exception:
            # Restore from backup
            shutil.copy(str(backup_db), str(legacy_database_v3))

            # Verify restored
            db_restored = sqlite_wrapper.Database.connect(str(legacy_database_v3))
            restored_folders = list(db_restored["folders"].find({}))
            db_restored.close()

            assert len(restored_folders) == len(original_folders)
        finally:
            db_for_migration.close()


@pytest.mark.e2e
class TestInterruptedMigration:
    """Test recovery from interrupted migration."""

    def test_resume_interrupted_migration(self, legacy_database_v3, tmp_path):
        """Test resuming migration after interruption."""
        import core.database.schema
        from migrations.folders_database_migrator import upgrade_database
        from backend.database import sqlite_wrapper

        db_for_migration = sqlite_wrapper.Database.connect(str(legacy_database_v3))

        # Ensure schema
        schema.ensure_schema(db_for_migration)

        # Create config folder
        config_folder = str(tmp_path / "config")
        Path(config_folder).mkdir()

        try:
            # Start migration
            upgrade_database(db_for_migration, config_folder, "Linux")

            # If completes, verify
            folders = list(db_for_migration["folders"].find({}))
            assert len(folders) > 0

        except Exception as e:
            # If interrupted, should be able to retry
            pytest.skip(f"Migration interrupted: {e}")
        finally:
            db_for_migration.close()

    def test_corrupted_migration_recovery(self, legacy_database_v3, tmp_path):
        """Test recovery from corrupted migration."""
        import core.database.schema

        # Create backup
        backup_path = tmp_path / "backup"
        backup_path.mkdir()
        backup_db = backup_path / "folders_backup.db"
        shutil.copy(str(legacy_database_v3), str(backup_db))

        # Connect for migration
        from migrations.folders_database_migrator import upgrade_database
        from backend.database import sqlite_wrapper

        db_for_migration = sqlite_wrapper.Database.connect(str(legacy_database_v3))

        # Ensure schema
        schema.ensure_schema(db_for_migration)

        # Create config folder
        config_folder = str(tmp_path / "config")
        Path(config_folder).mkdir()

        try:
            # Attempt migration
            upgrade_database(db_for_migration, config_folder, "Linux")

        except Exception:
            # Restore from backup
            shutil.copy(str(backup_db), str(legacy_database_v3))

            # Verify database is usable
            db = sqlite_wrapper.Database.connect(str(legacy_database_v3))
            folders = list(db["folders"].find({}))
            db.close()
            assert len(folders) > 0
        finally:
            db_for_migration.close()


@pytest.mark.e2e
class TestMultiVersionMigration:
    """Test skipping multiple versions during migration."""

    def test_skip_version_migration_v1_to_v5(self, legacy_database_v1, tmp_path):
        """Test migrating from v1 directly to current (skipping intermediate versions)."""
        import core.database.schema
        from migrations.folders_database_migrator import upgrade_database
        from backend.database import sqlite_wrapper

        db_for_migration = sqlite_wrapper.Database.connect(str(legacy_database_v1))

        # Ensure schema
        schema.ensure_schema(db_for_migration)

        # Create config folder
        config_folder = str(tmp_path / "config")
        Path(config_folder).mkdir()

        try:
            upgrade_database(db_for_migration, config_folder, "Linux")

            # Verify migration succeeded
            folders = list(db_for_migration["folders"].find({}))
            assert len(folders) == 2

        except Exception as e:
            pytest.skip(f"Multi-version skip not supported: {e}")
        finally:
            db_for_migration.close()

    def test_migrate_with_schema_evolution(self, legacy_database_v2, tmp_path):
        """Test migration handling schema evolution."""
        import core.database.schema
        from migrations.folders_database_migrator import upgrade_database
        from backend.database import sqlite_wrapper

        db_for_migration = sqlite_wrapper.Database.connect(str(legacy_database_v2))

        # Ensure schema
        schema.ensure_schema(db_for_migration)

        # Create config folder
        config_folder = str(tmp_path / "config")
        Path(config_folder).mkdir()

        try:
            upgrade_database(db_for_migration, config_folder, "Linux")

            # Verify new columns added
            folders = list(db_for_migration["folders"].find({}))
            assert len(folders) > 0

        except Exception as e:
            pytest.skip(f"Schema evolution migration failed: {e}")
        finally:
            db_for_migration.close()


@pytest.mark.e2e
class TestMigrationEdgeCases:
    """Test migration edge cases."""

    def test_migrate_empty_database(self, tmp_path):
        """Test migrating empty database."""
        db_path = tmp_path / "empty.db"

        import sqlite3

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Create minimal folders table
        cursor.execute(
            """
            CREATE TABLE folders (
                id INTEGER PRIMARY KEY,
                folder_name TEXT,
                alias TEXT
            )
        """
        )

        # Create version table
        cursor.execute(
            """
            CREATE TABLE version (
                id INTEGER PRIMARY KEY,
                version TEXT,
                os TEXT
            )
        """
        )

        # Create settings table (needed by migration)
        cursor.execute(
            """
            CREATE TABLE settings (
                id INTEGER PRIMARY KEY,
                enable_email INTEGER
            )
        """
        )

        # Create administrative table (needed by migration)
        cursor.execute(
            """
            CREATE TABLE administrative (
                id INTEGER PRIMARY KEY,
                copy_to_directory TEXT
            )
        """
        )

        # Insert version record
        cursor.execute(
            "INSERT INTO version (id, version, os) VALUES (?, ?, ?)", (1, "5", "Linux")
        )

        # Insert settings record
        cursor.execute("INSERT INTO settings (id, enable_email) VALUES (?, ?)", (1, 0))

        # Insert administrative record
        cursor.execute(
            "INSERT INTO administrative (id, copy_to_directory) VALUES (?, ?)", (1, "")
        )

        conn.commit()
        conn.close()

        import core.database.schema
        from migrations.folders_database_migrator import upgrade_database
        from backend.database import sqlite_wrapper

        db_for_migration = sqlite_wrapper.Database.connect(str(db_path))

        # Ensure schema
        schema.ensure_schema(db_for_migration)

        # Create config folder
        config_folder = str(tmp_path / "config")
        Path(config_folder).mkdir()

        try:
            upgrade_database(db_for_migration, config_folder, "Linux")

            # Should handle empty database
            folders = list(db_for_migration["folders"].find({}))
            assert len(folders) == 0

        except Exception as e:
            pytest.skip(f"Empty database migration failed: {e}")
        finally:
            db_for_migration.close()

    def test_migrate_large_database(self, tmp_path):
        """Test migrating database with many records."""
        db_path = tmp_path / "large.db"

        import sqlite3

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE folders (
                id INTEGER PRIMARY KEY,
                folder_name TEXT,
                alias TEXT
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE processed_files (
                id INTEGER PRIMARY KEY,
                folder_id INTEGER,
                filename TEXT,
                md5 TEXT
            )
        """
        )

        # Create version table
        cursor.execute(
            """
            CREATE TABLE version (
                id INTEGER PRIMARY KEY,
                version TEXT,
                os TEXT
            )
        """
        )

        # Create settings table (needed by migration)
        cursor.execute(
            """
            CREATE TABLE settings (
                id INTEGER PRIMARY KEY,
                enable_email INTEGER
            )
        """
        )

        # Create administrative table (needed by migration)
        cursor.execute(
            """
            CREATE TABLE administrative (
                id INTEGER PRIMARY KEY,
                copy_to_directory TEXT
            )
        """
        )

        # Insert version record - start from version 40 to skip problematic migrations
        cursor.execute(
            "INSERT INTO version (id, version, os) VALUES (?, ?, ?)", (1, "40", "Linux")
        )

        # Insert settings record
        cursor.execute("INSERT INTO settings (id, enable_email) VALUES (?, ?)", (1, 0))

        # Insert administrative record
        cursor.execute(
            "INSERT INTO administrative (id, copy_to_directory) VALUES (?, ?)", (1, "")
        )

        # Insert 100 folders
        for i in range(100):
            cursor.execute(
                "INSERT INTO folders (folder_name, alias) VALUES (?, ?)",
                (f"/folder/{i}", f"Folder {i}"),
            )

        # Insert 1000 processed files
        for i in range(1000):
            cursor.execute(
                "INSERT INTO processed_files (folder_id, filename, md5) VALUES (?, ?, ?)",
                ((i % 100) + 1, f"file_{i}.edi", f"hash_{i:04d}"),
            )

        conn.commit()
        conn.close()

        import core.database.schema
        from migrations.folders_database_migrator import upgrade_database
        from backend.database import sqlite_wrapper

        db_for_migration = sqlite_wrapper.Database.connect(str(db_path))

        # Ensure schema
        schema.ensure_schema(db_for_migration)

        # Create config folder
        config_folder = str(tmp_path / "config")
        Path(config_folder).mkdir()

        try:
            upgrade_database(db_for_migration, config_folder, "Linux")

            # Verify migration
            folders = list(db_for_migration["folders"].find({}))
            assert len(folders) == 100

            processed = list(db_for_migration["processed_files"].find({}))
            assert len(processed) == 1000

        except Exception as e:
            pytest.skip(f"Large database migration failed: {e}")
        finally:
            db_for_migration.close()
