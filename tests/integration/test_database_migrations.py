"""
Database migration integration tests.

Tests that ALL database schema versions can successfully migrate to the current version.
This ensures backwards compatibility and data integrity during upgrades.

IMPORTANT: When adding a new migration (version N+1):
1. Update DATABASE_VERSION in interface/main.py
2. Add migration logic to folders_database_migrator.py
3. Update ALL_VERSIONS in database_schema_versions.py (it will auto-increment)
4. Run these tests - they will automatically test the new version
"""

import os
import sys
import tempfile
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.integration.database_schema_versions import (
    generate_database_at_version,
    get_database_version,
    verify_database_structure,
    ALL_VERSIONS,
    CURRENT_VERSION,
    DatabaseConnectionManager,
)
import folders_database_migrator


class TestDatabaseMigrations:
    """Test database schema migrations from all historical versions to current."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database file path."""
        fd, path = tempfile.mkstemp(suffix=".db", prefix="test_migration_")
        os.close(fd)
        os.unlink(path)
        yield path
        if os.path.exists(path):
            try:
                os.unlink(path)
            except Exception:
                pass

    @pytest.mark.parametrize("start_version", ALL_VERSIONS)
    def test_migrate_from_version_to_current(self, start_version, temp_db_path):
        """Test migration from EVERY supported version to current.

        This runs once for each version 5-39, ensuring complete coverage.
        """
        if start_version == int(CURRENT_VERSION):
            pytest.skip(f"Version {start_version} is already current")

        db_path = generate_database_at_version(start_version, temp_db_path)

        assert get_database_version(db_path) == str(start_version), (
            f"Generated database should be at version {start_version}"
        )

        with DatabaseConnectionManager(
            db_path, f"test_mig_v{start_version}"
        ) as db_conn:
            folders_database_migrator.upgrade_database(db_conn, None, "Linux")

        final_version = get_database_version(db_path)
        assert final_version == CURRENT_VERSION, (
            f"Migration from v{start_version} should reach v{CURRENT_VERSION}, got v{final_version}"
        )

    @pytest.mark.parametrize("version", ALL_VERSIONS)
    def test_database_structure_at_each_version(self, version, temp_db_path):
        """Verify database structure is valid at each version."""
        db_path = generate_database_at_version(version, temp_db_path)

        structure = verify_database_structure(db_path)

        assert structure["version"] == str(version)
        assert "version" in structure["tables"]
        assert "folders" in structure["tables"]
        assert "administrative" in structure["tables"]
        assert "processed_files" in structure["tables"]

        assert "version" in structure["columns"]["version"]
        assert "os" in structure["columns"]["version"]

    def test_data_preservation_during_full_migration(self, temp_db_path):
        """Test that data survives migration from oldest to newest version."""
        db_path = generate_database_at_version(5, temp_db_path)

        with DatabaseConnectionManager(db_path, "insert_data") as db_conn:
            db_conn["folders"].insert(
                {
                    "folder_is_active": "True",
                    "folder_name": "/test/migration/folder",
                    "alias": "MigrationTest",
                    "process_edi": "False",
                }
            )

        with DatabaseConnectionManager(db_path, "migrate_full") as db_conn:
            folders_database_migrator.upgrade_database(db_conn, None, "Linux")

        with DatabaseConnectionManager(db_path, "verify_data") as db_conn:
            folder = db_conn["folders"].find_one(alias="MigrationTest")
            assert folder is not None, "Test data lost during migration"
            assert folder["folder_name"] == "/test/migration/folder"
            assert folder["alias"] == "MigrationTest"

    def test_all_versions_increment_sequentially(self):
        """Verify ALL_VERSIONS contains all numbers from 5 to current with no gaps."""
        expected = list(range(5, int(CURRENT_VERSION) + 1))
        assert ALL_VERSIONS == expected, (
            f"ALL_VERSIONS should be {expected}, got {ALL_VERSIONS}. "
            "Check database_schema_versions.py"
        )

    def test_migration_is_idempotent(self, temp_db_path):
        """Running migration on current version should be safe (no-op)."""
        db_path = generate_database_at_version(int(CURRENT_VERSION), temp_db_path)

        version_before = get_database_version(db_path)
        assert version_before == CURRENT_VERSION

        with DatabaseConnectionManager(db_path, "idempotent_test") as db_conn:
            folders_database_migrator.upgrade_database(db_conn, None, "Linux")

        version_after = get_database_version(db_path)
        assert version_after == CURRENT_VERSION

    def test_intermediate_migrations_work(self, temp_db_path):
        """Test migrating through intermediate versions (not just oldest->newest)."""
        db_path = generate_database_at_version(10, temp_db_path)
        assert get_database_version(db_path) == "10"

        with DatabaseConnectionManager(db_path, "intermediate_mig") as db_conn:
            folders_database_migrator.upgrade_database(db_conn, None, "Linux")

        assert get_database_version(db_path) == CURRENT_VERSION


class TestMigrationMaintenance:
    """Tests to ensure migration system remains maintainable going forward."""

    def test_current_version_matches_interface_main(self):
        """Verify CURRENT_VERSION matches DATABASE_VERSION in interface/main.py."""
        main_file = Path(__file__).parent.parent.parent / "interface" / "main.py"
        content = main_file.read_text()

        for line in content.splitlines():
            if line.startswith("DATABASE_VERSION"):
                assert f'"{CURRENT_VERSION}"' in line, (
                    f"DATABASE_VERSION in interface/main.py ({line.strip()}) "
                    f"should match CURRENT_VERSION ({CURRENT_VERSION})"
                )
                break
        else:
            pytest.fail("DATABASE_VERSION not found in interface/main.py")

    def test_all_versions_list_is_complete(self):
        """Verify ALL_VERSIONS goes from 5 to CURRENT_VERSION with no gaps."""
        assert ALL_VERSIONS[0] == 5, "ALL_VERSIONS should start at 5"
        assert ALL_VERSIONS[-1] == int(CURRENT_VERSION), (
            f"ALL_VERSIONS should end at {CURRENT_VERSION}"
        )

        for i in range(len(ALL_VERSIONS) - 1):
            assert ALL_VERSIONS[i + 1] == ALL_VERSIONS[i] + 1, (
                f"Gap in ALL_VERSIONS between {ALL_VERSIONS[i]} and {ALL_VERSIONS[i + 1]}"
            )

    def test_schema_generator_supports_all_versions(self):
        """Verify we can generate databases at every version."""
        for version in ALL_VERSIONS:
            try:
                fd, path = tempfile.mkstemp(suffix=".db")
                os.close(fd)
                os.unlink(path)

                db_path = generate_database_at_version(version, path)
                actual_version = get_database_version(db_path)

                assert actual_version == str(version), (
                    f"Generated v{version} but got v{actual_version}"
                )

                os.unlink(db_path)
            except Exception as e:
                pytest.fail(f"Failed to generate database at version {version}: {e}")


class TestMigrationPathCoverage:
    """Ensure every single migration step is tested."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database file path."""
        fd, path = tempfile.mkstemp(suffix=".db", prefix="test_migration_")
        os.close(fd)
        os.unlink(path)
        yield path
        if os.path.exists(path):
            try:
                os.unlink(path)
            except Exception:
                pass

    @pytest.mark.parametrize("version", list(range(5, int(CURRENT_VERSION))))
    def test_each_individual_migration_step(self, version, temp_db_path):
        """Test migration from version N to N+1 for ALL steps.

        This ensures every individual migration in folders_database_migrator.py
        is executed and tested.
        """
        db_path = generate_database_at_version(version, temp_db_path)
        assert get_database_version(db_path) == str(version)

        with DatabaseConnectionManager(
            db_path, f"step_v{version}_to_{version + 1}"
        ) as db_conn:
            folders_database_migrator.upgrade_database(db_conn, None, "Linux")

        final_version = int(get_database_version(db_path))
        assert final_version > version, f"Migration from v{version} didn't progress"
