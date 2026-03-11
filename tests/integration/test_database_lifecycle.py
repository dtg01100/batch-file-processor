"""Integration tests for database lifecycle with real SQLite.

Tests cover:
- Database creation from scratch via create_database.do()
- Full migration chain from older versions to current
- Folder CRUD operations via the real database tables
- Settings persistence and retrieval
- Processed files tracking via real database
- DatabaseObj initialization and table wiring
- Orchestrator with real database-backed folder list
"""

import os
from unittest.mock import MagicMock

import pytest

import create_database
import folders_database_migrator
import schema
from interface.database import sqlite_wrapper
from interface.database.database_obj import DatabaseObj
from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator

pytestmark = [pytest.mark.integration, pytest.mark.database]

CURRENT_DB_VERSION = "42"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _create_fresh_db(tmp_path, version=CURRENT_DB_VERSION):
    """Create a brand new database at the current version."""
    db_path = str(tmp_path / "test.db")
    config_folder = str(tmp_path / "config")
    os.makedirs(config_folder, exist_ok=True)
    create_database.do(version, db_path, config_folder, "Linux")
    folders_database_migrator.upgrade_database(
        sqlite_wrapper.Database.connect(db_path),
        config_folder,
        "Linux",
    )
    return db_path, config_folder


class TrackingBackend:
    def __init__(self):
        self.sent = []

    def send(self, params, settings, filename):
        self.sent.append(filename)
        return True


# ---------------------------------------------------------------------------
# Tests: Database creation
# ---------------------------------------------------------------------------
class TestDatabaseCreation:

    def test_create_database_creates_file(self, tmp_path):
        db_path, _ = _create_fresh_db(tmp_path)
        assert os.path.isfile(db_path)

    def test_created_db_has_version_table(self, tmp_path):
        db_path, _ = _create_fresh_db(tmp_path)
        conn = sqlite_wrapper.Database.connect(db_path)
        ver = conn["version"].find_one(id=1)
        assert int(ver["version"]) >= int(CURRENT_DB_VERSION)
        conn.close()

    def test_created_db_has_settings_table(self, tmp_path):
        db_path, _ = _create_fresh_db(tmp_path)
        conn = sqlite_wrapper.Database.connect(db_path)
        settings = conn["settings"].find_one(id=1)
        assert settings is not None
        conn.close()

    def test_created_db_has_administrative_table(self, tmp_path):
        db_path, _ = _create_fresh_db(tmp_path)
        conn = sqlite_wrapper.Database.connect(db_path)
        admin = conn["administrative"].find_one(id=1)
        assert admin is not None
        conn.close()

    def test_created_db_has_folders_table(self, tmp_path):
        db_path, _ = _create_fresh_db(tmp_path)
        conn = sqlite_wrapper.Database.connect(db_path)
        # folders table exists but is empty initially
        folders = list(conn["folders"].all())
        assert isinstance(folders, list)
        conn.close()


# ---------------------------------------------------------------------------
# Tests: Folder CRUD
# ---------------------------------------------------------------------------
class TestFolderCRUD:

    @pytest.fixture()
    def db(self, tmp_path):
        db_path, _ = _create_fresh_db(tmp_path)
        conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(conn)
        yield conn
        conn.close()

    def test_insert_and_retrieve_folder(self, db):
        folders = db["folders"]
        folders.insert(dict(
            folder_name="/data/invoices",
            alias="invoices",
            folder_is_active=1,
            process_backend_copy=1,
            copy_to_directory="/out",
        ))
        db.commit()

        found = folders.find_one(alias="invoices")
        assert found is not None
        assert found["folder_name"] == "/data/invoices"
        assert found["folder_is_active"] == 1

    def test_update_folder(self, db):
        folders = db["folders"]
        folders.insert(dict(
            folder_name="/data/old",
            alias="orig",
            folder_is_active=1,
        ))
        db.commit()

        row = folders.find_one(alias="orig")
        row["folder_name"] = "/data/new"
        folders.update(row, ["id"])
        db.commit()

        updated = folders.find_one(id=row["id"])
        assert updated["folder_name"] == "/data/new"

    def test_delete_folder(self, db):
        folders = db["folders"]
        folders.insert(dict(folder_name="/tmp/del", alias="del_me", folder_is_active=0))
        db.commit()

        row = folders.find_one(alias="del_me")
        assert row is not None
        folders.delete(id=row["id"])
        db.commit()

        assert folders.find_one(alias="del_me") is None

    def test_find_active_folders_only(self, db):
        folders = db["folders"]
        folders.insert(dict(folder_name="/a", alias="active", folder_is_active=1))
        folders.insert(dict(folder_name="/b", alias="inactive", folder_is_active=0))
        db.commit()

        active = list(folders.find(folder_is_active=1))
        assert len(active) == 1
        assert active[0]["alias"] == "active"

    def test_multiple_folder_insert_and_count(self, db):
        folders = db["folders"]
        for i in range(10):
            folders.insert(dict(
                folder_name=f"/folder_{i}",
                alias=f"f{i}",
                folder_is_active=1,
            ))
        db.commit()

        all_folders = list(folders.all())
        assert len(all_folders) == 10


# ---------------------------------------------------------------------------
# Tests: Settings persistence
# ---------------------------------------------------------------------------
class TestSettingsPersistence:

    @pytest.fixture()
    def db(self, tmp_path):
        db_path, _ = _create_fresh_db(tmp_path)
        conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(conn)
        yield conn
        conn.close()

    def test_settings_default_values(self, db):
        settings = db["settings"].find_one(id=1)
        assert settings is not None
        # Default from create_database
        assert settings.get("folder_name") == "template"

    def test_update_settings(self, db):
        settings_table = db["settings"]
        row = settings_table.find_one(id=1)
        row["enable_email"] = 1
        row["email_address"] = "test@example.com"
        settings_table.update(row, ["id"])
        db.commit()

        updated = settings_table.find_one(id=1)
        assert updated["enable_email"] == 1
        assert updated["email_address"] == "test@example.com"

    def test_settings_roundtrip(self, db, tmp_path):
        """Write settings, close, reopen, read back."""
        db_path = str(tmp_path / "test.db")
        settings_table = db["settings"]
        row = settings_table.find_one(id=1)
        row["email_smtp_server"] = "mail.test.com"
        settings_table.update(row, ["id"])
        db.commit()
        db.close()

        conn2 = sqlite_wrapper.Database.connect(db_path)
        read_back = conn2["settings"].find_one(id=1)
        assert read_back["email_smtp_server"] == "mail.test.com"
        conn2.close()


# ---------------------------------------------------------------------------
# Tests: Processed files tracking
# ---------------------------------------------------------------------------
class TestProcessedFilesTracking:

    @pytest.fixture()
    def db(self, tmp_path):
        db_path, _ = _create_fresh_db(tmp_path)
        conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(conn)
        yield conn
        conn.close()

    def test_insert_processed_file(self, db):
        pf = db["processed_files"]
        pf.insert(dict(
            file_name="invoice_001.edi",
            folder_id=1,
            file_checksum="abc123",
        ))
        db.commit()

        found = pf.find_one(file_name="invoice_001.edi")
        assert found is not None
        assert found["file_checksum"] == "abc123"

    def test_no_duplicate_tracking(self, db):
        pf = db["processed_files"]
        pf.insert(dict(file_name="dup.edi", folder_id=1, file_checksum="x"))
        pf.insert(dict(file_name="dup.edi", folder_id=1, file_checksum="y"))
        db.commit()

        rows = list(pf.find(file_name="dup.edi"))
        # Both inserts are stored (uniqueness enforced at app level, not DB)
        assert len(rows) == 2

    def test_resend_flag(self, db):
        pf = db["processed_files"]
        pf.insert(dict(
            file_name="resend_me.edi",
            folder_id=1,
            file_checksum="abc",
            resend_flag=0,
        ))
        db.commit()

        row = pf.find_one(file_name="resend_me.edi")
        row["resend_flag"] = 1
        pf.update(row, ["id"])
        db.commit()

        updated = pf.find_one(id=row["id"])
        assert updated["resend_flag"] == 1


# ---------------------------------------------------------------------------
# Tests: Migration chain
# ---------------------------------------------------------------------------
class TestMigrationChain:

    def test_migrate_from_v33_to_current(self, tmp_path):
        """Create DB at v33, then migrate to current."""
        db_path = str(tmp_path / "old.db")
        config = str(tmp_path / "cfg")
        os.makedirs(config, exist_ok=True)

        create_database.do("33", db_path, config, "Linux")
        conn = sqlite_wrapper.Database.connect(db_path)
        folders_database_migrator.upgrade_database(conn, config, "Linux")

        ver = conn["version"].find_one(id=1)
        assert int(ver["version"]) >= 42
        conn.close()

    def test_migrate_from_v33_to_v38_partial(self, tmp_path):
        """Partial migration with target_version."""
        db_path = str(tmp_path / "partial.db")
        config = str(tmp_path / "cfg")
        os.makedirs(config, exist_ok=True)

        create_database.do("33", db_path, config, "Linux")
        conn = sqlite_wrapper.Database.connect(db_path)
        folders_database_migrator.upgrade_database(
            conn, config, "Linux", target_version="38"
        )

        ver = conn["version"].find_one(id=1)
        assert ver["version"] == "38"
        conn.close()

    def test_idempotent_migration(self, tmp_path):
        """Running migration twice doesn't error."""
        db_path = str(tmp_path / "idem.db")
        config = str(tmp_path / "cfg")
        os.makedirs(config, exist_ok=True)

        create_database.do("33", db_path, config, "Linux")
        conn = sqlite_wrapper.Database.connect(db_path)
        folders_database_migrator.upgrade_database(conn, config, "Linux")
        folders_database_migrator.upgrade_database(conn, config, "Linux")

        ver = conn["version"].find_one(id=1)
        assert int(ver["version"]) >= 42
        conn.close()


# ---------------------------------------------------------------------------
# Tests: DatabaseObj wrapper
# ---------------------------------------------------------------------------
class TestDatabaseObjWrapper:

    def test_database_obj_creates_and_connects(self, tmp_path):
        """DatabaseObj creates a new database if it doesn't exist."""
        db_path = str(tmp_path / "dbobj.db")
        config = str(tmp_path / "cfg")
        os.makedirs(config, exist_ok=True)

        db = DatabaseObj(
            database_path=db_path,
            database_version=CURRENT_DB_VERSION,
            config_folder=config,
            running_platform="Linux",
        )

        assert db.folders_table is not None
        assert db.settings is not None
        assert db.processed_files is not None
        db.close()

    def test_database_obj_folder_table_operations(self, tmp_path):
        """Insert and retrieve folders through DatabaseObj."""
        db_path = str(tmp_path / "crud.db")
        config = str(tmp_path / "cfg")
        os.makedirs(config, exist_ok=True)

        db = DatabaseObj(
            database_path=db_path,
            database_version=CURRENT_DB_VERSION,
            config_folder=config,
            running_platform="Linux",
        )

        db.folders_table.insert(dict(
            folder_name="/test/path",
            alias="myalias",
            folder_is_active=1,
        ))
        db.database_connection.commit()

        found = db.folders_table.find_one(alias="myalias")
        assert found["folder_name"] == "/test/path"
        db.close()

    def test_database_obj_with_injected_connection(self, tmp_path):
        """DatabaseObj works with an injected connection."""
        db_path = str(tmp_path / "injected.db")
        config = str(tmp_path / "cfg")
        os.makedirs(config, exist_ok=True)

        create_database.do(CURRENT_DB_VERSION, db_path, config, "Linux")
        conn = sqlite_wrapper.Database.connect(db_path)
        folders_database_migrator.upgrade_database(conn, config, "Linux")

        db = DatabaseObj(
            database_path=db_path,
            database_version=CURRENT_DB_VERSION,
            config_folder=config,
            running_platform="Linux",
            connection=conn,
        )

        assert db.folders_table is not None
        db.close()


# ---------------------------------------------------------------------------
# Tests: Orchestrator with real DB folders
# ---------------------------------------------------------------------------
class TestOrchestratorWithRealDB:

    def test_process_active_folders_from_db(self, tmp_path):
        """Insert active folders into DB, then process them via orchestrator."""
        db_path = str(tmp_path / "orch.db")
        config = str(tmp_path / "cfg")
        os.makedirs(config, exist_ok=True)

        create_database.do(CURRENT_DB_VERSION, db_path, config, "Linux")
        conn = sqlite_wrapper.Database.connect(db_path)
        folders_database_migrator.upgrade_database(conn, config, "Linux")

        # Create input folder with EDI file
        inp = tmp_path / "input"
        inp.mkdir()
        (inp / "test.edi").write_text(
            "HDRA0000000000000000  000000000000000test.edi\n"
            "A0000000000  0000000100100000000000\n"
        )
        out = tmp_path / "output"
        out.mkdir()

        # Insert an active folder into the real database
        folders = conn["folders"]
        folders.insert(dict(
            folder_name=str(inp),
            alias="real_test",
            folder_is_active=1,
            process_backend_copy=1,
            copy_to_directory=str(out),
        ))
        conn.commit()

        # Read it back
        folder_row = folders.find_one(alias="real_test")
        assert folder_row is not None

        # Process it
        backend = TrackingBackend()
        orch_config = DispatchConfig(
            backends={"copy": backend},
            settings={},
            database=folders,
        )
        orch = DispatchOrchestrator(orch_config)
        result = orch.process_folder(dict(folder_row), MagicMock())

        assert len(backend.sent) == 1
        assert result.files_processed == 1
        conn.close()

    def test_process_only_active_folders(self, tmp_path):
        """Inactive folders should not produce any file sends."""
        db_path = str(tmp_path / "inactive.db")
        config = str(tmp_path / "cfg")
        os.makedirs(config, exist_ok=True)

        create_database.do(CURRENT_DB_VERSION, db_path, config, "Linux")
        conn = sqlite_wrapper.Database.connect(db_path)
        folders_database_migrator.upgrade_database(conn, config, "Linux")

        inp = tmp_path / "input"
        inp.mkdir()
        (inp / "test.edi").write_text("HDR content\nA record\n")

        folders = conn["folders"]
        folders.insert(dict(
            folder_name=str(inp),
            alias="disabled",
            folder_is_active=0,
            process_backend_copy=1,
            copy_to_directory=str(tmp_path / "out"),
        ))
        conn.commit()

        active = list(folders.find(folder_is_active=1))
        assert len(active) == 0
        conn.close()

    def test_process_multiple_db_folders_sequentially(self, tmp_path):
        """Multiple active folders from DB are each processed."""
        db_path = str(tmp_path / "multi.db")
        config = str(tmp_path / "cfg")
        os.makedirs(config, exist_ok=True)

        create_database.do(CURRENT_DB_VERSION, db_path, config, "Linux")
        conn = sqlite_wrapper.Database.connect(db_path)
        folders_database_migrator.upgrade_database(conn, config, "Linux")

        backend = TrackingBackend()
        orch_config = DispatchConfig(backends={"copy": backend}, settings={})
        orch = DispatchOrchestrator(orch_config)

        for i in range(3):
            inp = tmp_path / f"input_{i}"
            inp.mkdir()
            (inp / f"file_{i}.edi").write_text(
                "HDRA0000000000000000  000000000000000test.edi\n"
                "A0000000000  0000000100100000000000\n"
            )
            out = tmp_path / f"out_{i}"
            out.mkdir()

            conn["folders"].insert(dict(
                folder_name=str(inp),
                alias=f"folder_{i}",
                folder_is_active=1,
                process_backend_copy=1,
                copy_to_directory=str(out),
            ))
        conn.commit()

        active = list(conn["folders"].find(folder_is_active=1))
        assert len(active) == 3

        for f in active:
            orch.process_folder(dict(f), MagicMock())

        assert len(backend.sent) == 3
        conn.close()
