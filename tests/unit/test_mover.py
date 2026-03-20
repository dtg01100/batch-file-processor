"""Unit tests for mover module (database migration).

Tests:
- DbMigrationThing class initialization
- do_migrate: progress callback is invoked
- do_migrate: new active folders from new_db are inserted into original_db
- do_migrate: inactive folders are skipped
- do_migrate: FTP settings merged for matching folders
- do_migrate: copy settings merged for matching folders
- do_migrate: original_database_path override is respected
- Error handling: os.path.samefile raises OSError on missing paths
"""

import os

import pytest

import scripts.mover as mover
import core.database.schema as schema
from backend.database import sqlite_wrapper

pytestmark = [pytest.mark.unit, pytest.mark.database, pytest.mark.upgrade]


def _make_db(path, version="42"):
    """Create a minimal test database at *path* with schema and a version row."""
    conn = sqlite_wrapper.Database.connect(str(path))
    schema.ensure_schema(conn)
    conn["version"].insert(dict(version=version, os="Linux"))
    conn.commit()
    return conn


class TestDbMigrationThingInit:
    """Test suite for DbMigrationThing initialization."""

    def test_module_import(self):
        """Test that mover module can be imported."""
        assert mover is not None

    def test_initialization(self):
        """Constructor stores paths and zeros counters."""
        migrator = mover.DbMigrationThing(
            original_folder_path="/path/to/original.db",
            new_folder_path="/path/to/new.db",
        )

        assert migrator.original_folder_path == "/path/to/original.db"
        assert migrator.new_folder_path == "/path/to/new.db"
        assert migrator.number_of_folders == 0
        assert migrator.progress_of_folders == 0


class TestDoMigrate:
    """Integration tests for DbMigrationThing.do_migrate()."""

    def test_do_migrate_calls_progress_callback(self, tmp_path):
        """do_migrate must invoke progress_callback at least once."""
        orig_db = tmp_path / "original.db"
        new_db = tmp_path / "new.db"
        for path in (orig_db, new_db):
            _make_db(path).close()

        migrator = mover.DbMigrationThing(str(orig_db), str(new_db))
        calls = []
        migrator.do_migrate(progress_callback=lambda c, m: calls.append((c, m)))

        assert len(calls) > 0

    def test_do_migrate_inserts_new_folder_into_original(self, tmp_path):
        """Active folders in new_db absent from original_db get inserted."""
        orig_db = tmp_path / "original.db"
        new_db = tmp_path / "new.db"
        for path in (orig_db, new_db):
            _make_db(path).close()

        new_conn = sqlite_wrapper.Database.connect(str(new_db))
        new_conn["folders"].insert(
            dict(folder_name="/imported/folder", folder_is_active=1, alias="")
        )
        new_conn.commit()
        new_conn.close()

        migrator = mover.DbMigrationThing(str(orig_db), str(new_db))
        migrator.do_migrate()

        orig_conn = sqlite_wrapper.Database.connect(str(orig_db))
        folders = list(orig_conn["folders"].find(folder_name="/imported/folder"))
        orig_conn.close()

        assert len(folders) == 1

    def test_do_migrate_skips_inactive_folders(self, tmp_path):
        """Inactive folders (folder_is_active=0) in new_db must not be imported."""
        orig_db = tmp_path / "original.db"
        new_db = tmp_path / "new.db"
        for path in (orig_db, new_db):
            _make_db(path).close()

        new_conn = sqlite_wrapper.Database.connect(str(new_db))
        new_conn["folders"].insert(
            dict(folder_name="/inactive/folder", folder_is_active=0, alias="")
        )
        new_conn.commit()
        new_conn.close()

        migrator = mover.DbMigrationThing(str(orig_db), str(new_db))
        migrator.do_migrate()

        orig_conn = sqlite_wrapper.Database.connect(str(orig_db))
        folders = list(orig_conn["folders"].find(folder_name="/inactive/folder"))
        orig_conn.close()

        assert len(folders) == 0

    def test_do_migrate_merges_ftp_settings_for_matching_folder(self, tmp_path):
        """FTP settings from new_db overwrite those in original_db for matching folders."""
        orig_db = tmp_path / "original.db"
        new_db = tmp_path / "new.db"
        for path in (orig_db, new_db):
            _make_db(path).close()

        orig_conn = sqlite_wrapper.Database.connect(str(orig_db))
        orig_conn["folders"].insert(
            dict(
                folder_name="/shared/folder",
                folder_is_active=1,
                alias="",
                process_backend_ftp=True,
                ftp_server="old.ftp.com",
                ftp_port=21,
                ftp_folder="/",
                ftp_username="olduser",
                ftp_password="oldpass",
            )
        )
        orig_conn.commit()
        orig_conn.close()

        new_conn = sqlite_wrapper.Database.connect(str(new_db))
        new_conn["folders"].insert(
            dict(
                folder_name="/shared/folder",
                folder_is_active=1,
                alias="",
                process_backend_ftp=True,
                ftp_server="new.ftp.com",
                ftp_port=2121,
                ftp_folder="/uploads",
                ftp_username="newuser",
                ftp_password="newpass",
            )
        )
        new_conn.commit()
        new_conn.close()

        migrator = mover.DbMigrationThing(str(orig_db), str(new_db))
        migrator.do_migrate()

        orig_conn = sqlite_wrapper.Database.connect(str(orig_db))
        folder = orig_conn["folders"].find_one(folder_name="/shared/folder")
        orig_conn.close()

        assert folder["ftp_server"] == "new.ftp.com"
        assert folder["ftp_port"] == 2121

    def test_do_migrate_merges_copy_settings_for_matching_folder(self, tmp_path):
        """Copy settings from new_db overwrite those in original_db for matching folders."""
        orig_db = tmp_path / "original.db"
        new_db = tmp_path / "new.db"
        for path in (orig_db, new_db):
            _make_db(path).close()

        orig_conn = sqlite_wrapper.Database.connect(str(orig_db))
        orig_conn["folders"].insert(
            dict(
                folder_name="/shared/folder",
                folder_is_active=1,
                alias="",
                process_backend_copy=True,
                copy_to_directory="/old/backup",
            )
        )
        orig_conn.commit()
        orig_conn.close()

        new_conn = sqlite_wrapper.Database.connect(str(new_db))
        new_conn["folders"].insert(
            dict(
                folder_name="/shared/folder",
                folder_is_active=1,
                alias="",
                process_backend_copy=True,
                copy_to_directory="/new/backup",
            )
        )
        new_conn.commit()
        new_conn.close()

        migrator = mover.DbMigrationThing(str(orig_db), str(new_db))
        migrator.do_migrate()

        orig_conn = sqlite_wrapper.Database.connect(str(orig_db))
        folder = orig_conn["folders"].find_one(folder_name="/shared/folder")
        orig_conn.close()

        assert folder["copy_to_directory"] == "/new/backup"

    def test_do_migrate_accepts_override_original_path(self, tmp_path):
        """original_database_path kwarg overrides self.original_folder_path."""
        orig_db_1 = tmp_path / "original1.db"
        orig_db_2 = tmp_path / "original2.db"
        new_db = tmp_path / "new.db"
        for path in (orig_db_1, orig_db_2, new_db):
            _make_db(path).close()

        new_conn = sqlite_wrapper.Database.connect(str(new_db))
        new_conn["folders"].insert(
            dict(folder_name="/test/folder", folder_is_active=1, alias="")
        )
        new_conn.commit()
        new_conn.close()

        # Provide orig_db_2 as override -- the folder should land there, not orig_db_1
        migrator = mover.DbMigrationThing(str(orig_db_1), str(new_db))
        migrator.do_migrate(original_database_path=str(orig_db_2))

        conn2 = sqlite_wrapper.Database.connect(str(orig_db_2))
        folders_in_2 = list(conn2["folders"].find(folder_name="/test/folder"))
        conn2.close()

        conn1 = sqlite_wrapper.Database.connect(str(orig_db_1))
        folders_in_1 = list(conn1["folders"].find(folder_name="/test/folder"))
        conn1.close()

        assert len(folders_in_2) == 1
        assert len(folders_in_1) == 0


class TestErrorHandling:
    """Test suite for error handling during migration."""

    def test_oserror_for_missing_path(self):
        """os.path.samefile raises OSError on non-existent paths (mover relies on this)."""
        with pytest.raises(OSError):
            os.path.samefile("/nonexistent/path1", "/nonexistent/path2")
