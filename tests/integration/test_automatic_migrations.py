"""
Automatic migration integration tests.

Tests the real-world scenario: user has old database (v32), launches app with v38 code.
Database should automatically upgrade from v32 to v38 preserving all data.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.integration.database_schema_versions import (
    generate_database_at_version,
    get_database_version,
    DatabaseConnectionManager,
)
from interface.database.database_manager import DatabaseManager


class TestAutomaticMigration:
    """Test automatic migration when DatabaseManager detects old version."""

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database path."""
        fd, path = tempfile.mkstemp(suffix=".db", prefix="test_auto_migration_")
        os.close(fd)
        os.unlink(path)
        yield path
        if os.path.exists(path):
            try:
                os.unlink(path)
            except Exception:
                pass

    @pytest.fixture
    def temp_config_folder(self):
        """Create temporary config folder."""
        temp_dir = tempfile.mkdtemp(prefix="test_config_")
        yield temp_dir
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_automatic_migration_from_v32_to_v38(
        self, temp_db_path, temp_config_folder
    ):
        """Test that DatabaseManager automatically upgrades v32 database to v38."""
        db_path = generate_database_at_version(32, temp_db_path)

        assert get_database_version(db_path) == "32"

        with DatabaseConnectionManager(db_path, "insert_test_data") as db:
            db["folders"].insert(
                {
                    "folder_is_active": "True",
                    "folder_name": "/test/auto/migration",
                    "alias": "AutoMigrationTest",
                }
            )

        db_manager = DatabaseManager(
            database_path=db_path,
            config_folder=temp_config_folder,
            platform="Linux",
            app_version="1.0.0",
            database_version="38",
        )

        assert get_database_version(db_path) == "38"

        with DatabaseConnectionManager(db_path, "verify_migration") as db:
            result = db["folders"].find_one(alias="AutoMigrationTest")
            assert result is not None, "Test data lost during migration"
            assert result["folder_name"] == "/test/auto/migration"
            assert result["alias"] == "AutoMigrationTest"

        db_manager.close()

    def test_automatic_migration_creates_backup(self, temp_db_path, temp_config_folder):
        """Test that backup is created before migration."""
        db_path = generate_database_at_version(32, temp_db_path)

        backup_folder = os.path.join(os.path.dirname(db_path), "backups")
        existing_backups = (
            set(os.listdir(backup_folder)) if os.path.exists(backup_folder) else set()
        )

        db_manager = DatabaseManager(
            database_path=db_path,
            config_folder=temp_config_folder,
            platform="Linux",
            app_version="1.0.0",
            database_version="38",
        )

        current_backups = (
            set(os.listdir(backup_folder)) if os.path.exists(backup_folder) else set()
        )
        new_backups = current_backups - existing_backups

        backup_created = any(
            f.startswith(os.path.basename(db_path)) and ".bak" in f for f in new_backups
        )
        assert backup_created, (
            "Backup file should be created in backups/ subdirectory during migration"
        )

        db_manager.close()

    def test_automatic_migration_all_new_features_present(
        self, temp_db_path, temp_config_folder
    ):
        """Test that all v38 features are present after automatic migration."""
        db_path = generate_database_at_version(32, temp_db_path)

        db_manager = DatabaseManager(
            database_path=db_path,
            config_folder=temp_config_folder,
            platform="Linux",
            app_version="1.0.0",
            database_version="38",
        )

        with DatabaseConnectionManager(db_path, "verify_features") as db:
            conn = db.raw_connection

            # Check folders table columns
            cursor = conn.execute("PRAGMA table_info(folders)")
            columns = [row[1] for row in cursor.fetchall()]

            assert "plugin_config" in columns, "v33: plugin_config column missing"
            assert "created_at" in columns, "v34: created_at column missing"
            assert "updated_at" in columns, "v34: updated_at column missing"

            # Check processed_files table columns
            cursor = conn.execute("PRAGMA table_info(processed_files)")
            pf_columns = [row[1] for row in cursor.fetchall()]

            assert "filename" in pf_columns, "v35: filename column missing"
            assert "status" in pf_columns, "v35: status column missing"
            assert "original_path" in pf_columns, "v35: original_path column missing"
            assert "processed_at" in pf_columns, "v34: processed_at column missing"

            # Check indexes
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = [row[0] for row in cursor.fetchall()]

            assert "idx_folders_active" in indexes, "v36: idx_folders_active missing"
            assert "idx_folders_alias" in indexes, "v36: idx_folders_alias missing"
            assert "idx_processed_files_folder" in indexes, (
                "v36: idx_processed_files_folder missing"
            )

            # Check foreign keys enabled
            cursor = conn.execute("PRAGMA foreign_keys")
            fk_enabled = cursor.fetchone()[0]
            assert fk_enabled == 1, "v37: Foreign keys should be enabled"

            # Check version table columns
            cursor = conn.execute("PRAGMA table_info(version)")
            version_columns = [row[1] for row in cursor.fetchall()]

            assert "notes" in version_columns, (
                "v38: notes column missing from version table"
            )

        db_manager.close()

    def test_no_migration_when_versions_match(self, temp_db_path, temp_config_folder):
        """Test that no migration occurs when database is already at target version."""
        db_path = generate_database_at_version(38, temp_db_path)

        initial_mtime = os.path.getmtime(db_path)

        db_manager = DatabaseManager(
            database_path=db_path,
            config_folder=temp_config_folder,
            platform="Linux",
            app_version="1.0.0",
            database_version="38",
        )

        assert get_database_version(db_path) == "38"

        db_manager.close()

    def test_migration_preserves_complex_data(self, temp_db_path, temp_config_folder):
        """Test that complex data (multiple tables, relationships) is preserved."""
        db_path = generate_database_at_version(32, temp_db_path)

        with DatabaseConnectionManager(db_path, "insert_complex_data") as db:
            conn = db.raw_connection

            cursor = conn.execute(
                "INSERT INTO folders (folder_is_active, folder_name, alias) VALUES (?, ?, ?)",
                ("True", "/folder1", "Folder1"),
            )
            folder_id = cursor.lastrowid

            conn.execute(
                "INSERT INTO processed_files (file_name, file_checksum, folder_id) VALUES (?, ?, ?)",
                ("test_file.txt", "abc123", folder_id),
            )

            conn.execute(
                "INSERT INTO settings (enable_email, email_address) VALUES (?, ?)",
                (1, "test@example.com"),
            )
            conn.commit()

        db_manager = DatabaseManager(
            database_path=db_path,
            config_folder=temp_config_folder,
            platform="Linux",
            app_version="1.0.0",
            database_version="38",
        )

        with DatabaseConnectionManager(db_path, "verify_complex_data") as db:
            assert db["folders"].count(alias="Folder1") == 1, "Folder data lost"
            assert db["processed_files"].count(file_name="test_file.txt") == 1, (
                "Processed file data lost"
            )
            assert db["settings"].count(email_address="test@example.com") == 1, (
                "Settings data lost"
            )

        db_manager.close()

    def test_migration_from_multiple_starting_versions(
        self, temp_db_path, temp_config_folder
    ):
        """Test automatic migration works from various starting versions."""
        starting_versions = [25, 28, 30, 31, 32]

        for start_version in starting_versions:
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
                test_db_path = tmp.name

            try:
                db_path = generate_database_at_version(start_version, test_db_path)

                db_manager = DatabaseManager(
                    database_path=db_path,
                    config_folder=temp_config_folder,
                    platform="Linux",
                    app_version="1.0.0",
                    database_version="38",
                )

                assert get_database_version(db_path) == "38", (
                    f"Migration from v{start_version} to v38 failed"
                )

                db_manager.close()
            finally:
                if os.path.exists(test_db_path):
                    os.unlink(test_db_path)


class TestMigrationErrorHandling:
    """Test error handling in automatic migrations."""

    @pytest.fixture
    def temp_db_path(self):
        fd, path = tempfile.mkstemp(suffix=".db", prefix="test_error_migration_")
        os.close(fd)
        os.unlink(path)
        yield path
        if os.path.exists(path):
            try:
                os.unlink(path)
            except Exception:
                pass

    @pytest.fixture
    def temp_config_folder(self):
        temp_dir = tempfile.mkdtemp(prefix="test_error_config_")
        yield temp_dir
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_error_when_app_version_too_old(self, temp_db_path, temp_config_folder):
        """Test that error is raised when database is newer than app."""
        db_path = generate_database_at_version(38, temp_db_path)

        with pytest.raises(SystemExit):
            DatabaseManager(
                database_path=db_path,
                config_folder=temp_config_folder,
                platform="Linux",
                app_version="1.0.0",
                database_version="32",
            )

    def test_error_when_os_mismatch(self, temp_db_path, temp_config_folder):
        """Test that error is raised when OS doesn't match."""
        db_path = generate_database_at_version(32, temp_db_path)

        with DatabaseConnectionManager(db_path, "change_os") as db:
            db["version"].update({"id": 1, "os": "Windows"}, ["id"])

        with pytest.raises(SystemExit):
            DatabaseManager(
                database_path=db_path,
                config_folder=temp_config_folder,
                platform="Linux",
                app_version="1.0.0",
                database_version="38",
            )


class TestMigrationLogging:
    """Test that migration provides adequate logging/feedback."""

    @pytest.fixture
    def temp_db_path(self):
        fd, path = tempfile.mkstemp(suffix=".db", prefix="test_log_migration_")
        os.close(fd)
        os.unlink(path)
        yield path
        if os.path.exists(path):
            try:
                os.unlink(path)
            except Exception:
                pass

    @pytest.fixture
    def temp_config_folder(self):
        temp_dir = tempfile.mkdtemp(prefix="test_log_config_")
        yield temp_dir
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_migration_prints_progress(self, temp_db_path, temp_config_folder, capsys):
        """Test that migration progress is printed to stdout."""
        db_path = generate_database_at_version(32, temp_db_path)

        db_manager = DatabaseManager(
            database_path=db_path,
            config_folder=temp_config_folder,
            platform="Linux",
            app_version="1.0.0",
            database_version="38",
        )

        captured = capsys.readouterr()
        assert (
            "database schema update required" in captured.out.lower()
            or "creating backup before migration" in captured.out.lower()
        )
        assert "successfully upgraded" in captured.out.lower()

        db_manager.close()
