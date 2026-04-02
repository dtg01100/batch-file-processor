"""Integration tests for database lifecycle with real SQLite.

Tests cover:
- Database creation from scratch via create_database.do()
- Full migration chain from older versions to current
- Folder CRUD operations via the real database tables
- Settings persistence and retrieval
- Processed files tracking via real database
- DatabaseObj initialization and table wiring
- Orchestrator with real database-backed folder list
- App-upgrade scenario: open old DB via DatabaseObj, auto-migrate
"""

import os
import shutil
from unittest.mock import MagicMock

import pytest

from backend.database import sqlite_wrapper
from backend.database.database_obj import DatabaseObj
from core.constants import CURRENT_DATABASE_VERSION as CURRENT_DB_VERSION
from core.database import schema
from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator
from migrations import folders_database_migrator
from scripts import create_database

pytestmark = [pytest.mark.integration, pytest.mark.database]


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
    def test_fresh_database_structure(self, tmp_path):
        """Verify fresh database has correct file, tables, columns, and settings."""
        # Create database once
        db_path, _ = _create_fresh_db(tmp_path)

        # Verify file exists
        assert os.path.isfile(db_path)

        conn = sqlite_wrapper.Database.connect(db_path)
        cursor = conn.raw_connection.cursor()

        # Verify version table exists with correct version
        ver = conn["version"].find_one(id=1)
        assert int(ver["version"]) >= int(CURRENT_DB_VERSION)

        # Verify settings table exists
        settings = conn["settings"].find_one(id=1)
        assert settings is not None

        # Verify administrative table exists
        admin = conn["administrative"].find_one(id=1)
        assert admin is not None

        # Verify folders table exists (can be queried)
        folders = list(conn["folders"].all())
        assert isinstance(folders, list)

        # Verify all required columns in folders table
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

        # Verify all required columns in administrative table
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

        # Verify foreign keys are enabled
        cursor.execute("PRAGMA foreign_keys")
        result = cursor.fetchone()
        assert result[0] == 1 or result[0] == "1"

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
        folders.insert(
            dict(
                folder_name="/data/invoices",
                alias="invoices",
                folder_is_active=1,
                process_backend_copy=1,
                copy_to_directory="/out",
            )
        )
        db.commit()

        found = folders.find_one(alias="invoices")
        assert found is not None
        assert found["folder_name"] == "/data/invoices"
        assert found["folder_is_active"] == 1

    def test_update_folder(self, db):
        folders = db["folders"]
        folders.insert(
            dict(
                folder_name="/data/old",
                alias="orig",
                folder_is_active=1,
            )
        )
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
            folders.insert(
                dict(
                    folder_name=f"/folder_{i}",
                    alias=f"f{i}",
                    folder_is_active=1,
                )
            )
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
        pf.insert(
            dict(
                file_name="invoice_001.edi",
                folder_id=1,
                file_checksum="abc123",
            )
        )
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
        pf.insert(
            dict(
                file_name="resend_me.edi",
                folder_id=1,
                file_checksum="abc",
                resend_flag=0,
            )
        )
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
@pytest.mark.slow
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

    def test_migration_with_missing_tables(self, tmp_path):
        """Test migration when some tables are missing."""
        db_path = str(tmp_path / "missing_tables.db")
        config = str(tmp_path / "cfg")
        os.makedirs(config, exist_ok=True)

        conn = sqlite_wrapper.Database.connect(db_path)
        # Only create version and folders tables
        conn.query(
            "CREATE TABLE version (id INTEGER PRIMARY KEY, version TEXT, os TEXT)"
        )
        conn.query(
            "CREATE TABLE folders "
            "(id INTEGER PRIMARY KEY AUTOINCREMENT, folder_name TEXT, alias TEXT)"
        )

        conn["version"].insert(dict(version="10", os="Linux"))
        conn["folders"].insert(dict(folder_name="/test", alias="Test"))
        conn.close()

        # Run migration - should handle missing tables gracefully
        conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(conn)
        if conn["administrative"].find_one(id=1) is None:
            conn["administrative"].insert(dict(id=1, logs_directory="/logs"))

        folders_database_migrator.upgrade_database(conn, config, "Linux")

        # Verify migration completed
        version_rec = conn["version"].find_one(id=1)
        assert int(version_rec["version"]) >= int(CURRENT_DB_VERSION)

        conn.close()

    def test_migration_with_null_values(self, tmp_path):
        """Test migration handles NULL values correctly."""
        db_path = str(tmp_path / "nulls.db")
        config = str(tmp_path / "cfg")
        os.makedirs(config, exist_ok=True)

        conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(conn)
        conn["version"].insert(dict(version="20", os="Linux"))

        # Insert folder with NULL values
        conn["folders"].insert(
            dict(
                folder_name="/test",
                alias=None,
                folder_is_active="True",
                copy_to_directory=None,
                process_edi=1,
            )
        )

        conn["administrative"].insert(dict(id=1, logs_directory="/logs"))
        conn.close()

        # Run migration
        conn = sqlite_wrapper.Database.connect(db_path)
        folders_database_migrator.upgrade_database(
            conn, config, "Linux", target_version="41"
        )

        # Verify folder still exists
        folder = conn["folders"].find_one(folder_name="/test")
        assert folder is not None

        conn.close()

    def test_migration_with_duplicate_folders(self, tmp_path):
        """Test migration handles duplicate folder names."""
        db_path = str(tmp_path / "duplicates.db")
        config = str(tmp_path / "cfg")
        os.makedirs(config, exist_ok=True)

        conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(conn)
        conn["version"].insert(dict(version="20", os="Linux"))

        # Insert folders with duplicate names (shouldn't happen, but test resilience)
        conn["folders"].insert(
            dict(folder_name="/test", alias="Test 1", folder_is_active="True")
        )
        conn["folders"].insert(
            dict(folder_name="/test", alias="Test 2", folder_is_active="False")
        )

        conn["administrative"].insert(dict(id=1, logs_directory="/logs"))
        conn.close()

        # Run migration
        conn = sqlite_wrapper.Database.connect(db_path)
        folders_database_migrator.upgrade_database(
            conn, config, "Linux", target_version="41"
        )

        # Both folders should still exist
        folders = list(conn["folders"].find(folder_name="/test"))
        assert len(folders) == 2

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

        db.folders_table.insert(
            dict(
                folder_name="/test/path",
                alias="myalias",
                folder_is_active=1,
            )
        )
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

    def test_import_database_from_file(self, tmp_path):
        """Test importing a database file from a different location."""
        # Create source database
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        source_path, _ = _create_fresh_db(source_dir)
        conn = sqlite_wrapper.Database.connect(source_path)
        conn["folders"].insert_many(
            [
                dict(folder_name="/folder/1", alias="Folder 1"),
                dict(folder_name="/folder/2", alias="Folder 2"),
            ]
        )
        conn.close()

        # "Import" by copying
        import_db_path = str(tmp_path / "imported.db")
        shutil.copy(source_path, import_db_path)

        # Verify imported database is valid
        conn = sqlite_wrapper.Database.connect(import_db_path)

        version = conn["version"].find_one(id=1)
        assert int(version["version"]) >= int(CURRENT_DB_VERSION)

        folders = list(conn["folders"].all())
        assert len(folders) == 2

        conn.close()


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
        folders.insert(
            dict(
                folder_name=str(inp),
                alias="real_test",
                folder_is_active=1,
                process_backend_copy=1,
                copy_to_directory=str(out),
            )
        )
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
        folders.insert(
            dict(
                folder_name=str(inp),
                alias="disabled",
                folder_is_active=0,
                process_backend_copy=1,
                copy_to_directory=str(tmp_path / "out"),
            )
        )
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

            conn["folders"].insert(
                dict(
                    folder_name=str(inp),
                    alias=f"folder_{i}",
                    folder_is_active=1,
                    process_backend_copy=1,
                    copy_to_directory=str(out),
                )
            )
        conn.commit()

        active = list(conn["folders"].find(folder_is_active=1))
        assert len(active) == 3

        for f in active:
            orch.process_folder(dict(f), MagicMock())

        assert len(backend.sent) == 3
        conn.close()


# ---------------------------------------------------------------------------
# Helpers for app-upgrade tests
# ---------------------------------------------------------------------------
LEGACY_DB_PATH = os.path.join(
    os.path.dirname(__file__), "..", "fixtures", "legacy_v32_folders.db"
)


def _create_old_version_db(db_path: str, config_folder: str, version: str) -> None:
    """Create a database at *version* with sample data, ready for upgrade.

    Uses raw SQL to create tables at a schema level that pre-dates the
    migrations from *version* onward, so the real migration path is exercised
    when DatabaseObj opens the file.
    """
    import sqlite3

    raw = sqlite3.connect(db_path)
    c = raw.cursor()

    # -- Base tables at roughly v33 level (no columns added by v33+ migrations)
    c.execute("""
        CREATE TABLE version (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version TEXT,
            os TEXT
        )
    """)
    c.execute(
        "INSERT INTO version (id, version, os) VALUES (1, ?, 'Linux')", (version,)
    )

    c.execute("""
        CREATE TABLE folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folder_name TEXT,
            alias TEXT,
            folder_is_active INTEGER DEFAULT 0,
            copy_to_directory TEXT,
            process_edi INTEGER DEFAULT 0,
            convert_to_format TEXT DEFAULT 'csv',
            calculate_upc_check_digit INTEGER DEFAULT 0,
            upc_target_length INTEGER DEFAULT 11,
            upc_padding_pattern TEXT DEFAULT '',
            include_a_records INTEGER DEFAULT 0,
            include_c_records INTEGER DEFAULT 0,
            include_headers INTEGER DEFAULT 0,
            filter_ampersand INTEGER DEFAULT 0,
            tweak_edi INTEGER DEFAULT 0,
            pad_a_records INTEGER DEFAULT 0,
            a_record_padding TEXT DEFAULT '',
            a_record_padding_length INTEGER DEFAULT 6,
            invoice_date_custom_format_string TEXT DEFAULT '%Y%%m%%d',
            invoice_date_custom_format INTEGER DEFAULT 0,
            reporting_email TEXT DEFAULT '',
            report_email_destination TEXT DEFAULT '',
            process_backend_copy INTEGER DEFAULT 0,
            backend_copy_destination TEXT,
            process_edi_output INTEGER DEFAULT 0,
            edi_output_folder TEXT,
            split_edi INTEGER DEFAULT 0,
            force_edi_validation INTEGER DEFAULT 0,
            append_a_records INTEGER DEFAULT 0,
            force_txt_file_ext INTEGER DEFAULT 0,
            prepend_date_files INTEGER DEFAULT 0,
            override_upc_bool INTEGER DEFAULT 0,
            split_edi_include_invoices INTEGER DEFAULT 0,
            split_edi_include_credits INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE processed_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT,
            folder_id INTEGER,
            file_checksum TEXT,
            resend_flag INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            enable_email INTEGER DEFAULT 0,
            email_address TEXT DEFAULT '',
            email_username TEXT DEFAULT '',
            email_password TEXT DEFAULT '',
            email_smtp_server TEXT DEFAULT '',
            smtp_port INTEGER DEFAULT 587,
            as400_address TEXT DEFAULT '',
            as400_username TEXT DEFAULT '',
            as400_password TEXT DEFAULT '',
            backup_counter INTEGER DEFAULT 0,
            backup_counter_maximum INTEGER DEFAULT 100,
            enable_interval_backups INTEGER DEFAULT 0,
            folder_is_active INTEGER DEFAULT 0,
            copy_to_directory TEXT,
            convert_to_format TEXT DEFAULT 'csv',
            process_edi INTEGER DEFAULT 0,
            calculate_upc_check_digit INTEGER DEFAULT 0,
            upc_target_length INTEGER DEFAULT 11,
            upc_padding_pattern TEXT DEFAULT '',
            include_a_records INTEGER DEFAULT 0,
            include_c_records INTEGER DEFAULT 0,
            include_headers INTEGER DEFAULT 0,
            filter_ampersand INTEGER DEFAULT 0,
            tweak_edi INTEGER DEFAULT 0,
            pad_a_records INTEGER DEFAULT 0,
            a_record_padding TEXT DEFAULT '',
            a_record_padding_length INTEGER DEFAULT 6,
            invoice_date_custom_format_string TEXT DEFAULT '%Y%%m%%d',
            invoice_date_custom_format INTEGER DEFAULT 0,
            reporting_email TEXT DEFAULT '',
            folder_name TEXT DEFAULT 'template',
            alias TEXT DEFAULT '',
            report_email_destination TEXT DEFAULT '',
            process_backend_copy INTEGER DEFAULT 0,
            backend_copy_destination TEXT,
            process_edi_output INTEGER DEFAULT 0,
            edi_output_folder TEXT,
            split_edi INTEGER DEFAULT 0,
            force_edi_validation INTEGER DEFAULT 0,
            append_a_records INTEGER DEFAULT 0,
            force_txt_file_ext INTEGER DEFAULT 0,
            prepend_date_files INTEGER DEFAULT 0,
            override_upc_bool INTEGER DEFAULT 0,
            split_edi_include_invoices INTEGER DEFAULT 0,
            split_edi_include_credits INTEGER DEFAULT 0
        )
    """)
    c.execute("INSERT INTO settings (id) VALUES (1)")

    c.execute("""
        CREATE TABLE administrative (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            copy_to_directory TEXT DEFAULT '',
            logs_directory TEXT,
            enable_reporting INTEGER DEFAULT 0,
            report_email_destination TEXT DEFAULT '',
            report_edi_errors INTEGER DEFAULT 0,
            convert_to_format TEXT DEFAULT 'csv',
            tweak_edi INTEGER DEFAULT 0,
            split_edi INTEGER DEFAULT 0,
            single_add_folder_prior TEXT,
            batch_add_folder_prior TEXT,
            export_processed_folder_prior TEXT
        )
    """)
    c.execute(
        "INSERT INTO administrative (id, logs_directory) VALUES (1, ?)",
        (os.path.join(config_folder, "logs"),),
    )

    # -- Test data: two folders and one processed file
    c.execute(
        "INSERT INTO folders (folder_name, alias, folder_is_active, process_backend_copy, copy_to_directory)"
        " VALUES (?, ?, 1, 1, ?)",
        ("/data/invoices", "invoices", "/out/invoices"),
    )
    c.execute(
        "INSERT INTO folders (folder_name, alias, folder_is_active, process_backend_copy)"
        " VALUES (?, ?, 0, 0)",
        ("/data/orders", "orders"),
    )
    c.execute(
        "INSERT INTO processed_files (file_name, folder_id, file_checksum)"
        " VALUES (?, 1, ?)",
        ("old_invoice.edi", "legacy_checksum_abc"),
    )

    raw.commit()
    raw.close()

    # If the caller wants a version higher than 33, migrate up to it so
    # the schema matches that version exactly.
    if int(version) > 33:
        conn = sqlite_wrapper.Database.connect(db_path)
        folders_database_migrator.upgrade_database(
            conn, config_folder, "Linux", target_version=version
        )
        conn.commit()
        conn.close()


# ---------------------------------------------------------------------------
# Tests: App upgrade via DatabaseObj (simulates real app opening old DB)
# ---------------------------------------------------------------------------
class TestAppUpgradeViaDatabaseObj:
    """Open an old-version DB through DatabaseObj and verify auto-upgrade.

    This mirrors the real app-upgrade scenario: user installs a new version
    of the application, launches it, and DatabaseObj detects the older schema,
    creates a backup, and migrates in-place.
    """

    @pytest.mark.slow
    @pytest.mark.parametrize("old_version", ["33", "35", "38", "40"])
    def test_upgrade_from_old_version_reaches_current(self, tmp_path, old_version):
        """DatabaseObj auto-migrates an old DB to CURRENT_DB_VERSION."""
        db_path = str(tmp_path / "folders.db")
        config = str(tmp_path / "config")
        os.makedirs(config, exist_ok=True)

        _create_old_version_db(db_path, config, old_version)

        db = DatabaseObj(
            database_path=db_path,
            database_version=CURRENT_DB_VERSION,
            config_folder=config,
            running_platform="Linux",
        )

        ver = db.database_connection["version"].find_one(id=1)
        assert int(ver["version"]) == int(CURRENT_DB_VERSION)
        db.close()

    @pytest.mark.slow
    @pytest.mark.parametrize("old_version", ["33", "35", "38", "40"])
    def test_backup_created_before_upgrade(self, tmp_path, old_version):
        """A backup file is produced during the upgrade."""
        db_path = str(tmp_path / "folders.db")
        config = str(tmp_path / "config")
        os.makedirs(config, exist_ok=True)

        _create_old_version_db(db_path, config, old_version)

        db = DatabaseObj(
            database_path=db_path,
            database_version=CURRENT_DB_VERSION,
            config_folder=config,
            running_platform="Linux",
        )

        # backup_increment.do_backup creates files in a "backups" sub-folder
        backups_dir = tmp_path / "backups"
        assert backups_dir.is_dir(), "No backups directory created during upgrade"
        backup_files = list(backups_dir.iterdir())
        assert len(backup_files) >= 1, "No backup file created during upgrade"
        db.close()

    @pytest.mark.slow
    @pytest.mark.parametrize("old_version", ["33", "38"])
    def test_folder_data_preserved_after_upgrade(self, tmp_path, old_version):
        """Folder rows inserted before upgrade survive the migration."""
        db_path = str(tmp_path / "folders.db")
        config = str(tmp_path / "config")
        os.makedirs(config, exist_ok=True)

        _create_old_version_db(db_path, config, old_version)

        db = DatabaseObj(
            database_path=db_path,
            database_version=CURRENT_DB_VERSION,
            config_folder=config,
            running_platform="Linux",
        )

        invoices = db.folders_table.find_one(alias="invoices")
        assert invoices is not None
        assert invoices["folder_name"] == "/data/invoices"

        orders = db.folders_table.find_one(alias="orders")
        assert orders is not None
        assert orders["folder_name"] == "/data/orders"

        db.close()

    @pytest.mark.slow
    @pytest.mark.parametrize("old_version", ["33", "38"])
    def test_processed_files_preserved_after_upgrade(self, tmp_path, old_version):
        """Processed file records survive the upgrade."""
        db_path = str(tmp_path / "folders.db")
        config = str(tmp_path / "config")
        os.makedirs(config, exist_ok=True)

        _create_old_version_db(db_path, config, old_version)

        db = DatabaseObj(
            database_path=db_path,
            database_version=CURRENT_DB_VERSION,
            config_folder=config,
            running_platform="Linux",
        )

        pf = db.processed_files.find_one(file_name="old_invoice.edi")
        assert pf is not None
        assert pf["file_checksum"] == "legacy_checksum_abc"
        db.close()

    def test_tables_all_wired_after_upgrade(self, tmp_path):
        """All DatabaseObj table references are non-None after upgrading."""
        db_path = str(tmp_path / "folders.db")
        config = str(tmp_path / "config")
        os.makedirs(config, exist_ok=True)

        _create_old_version_db(db_path, config, "33")

        db = DatabaseObj(
            database_path=db_path,
            database_version=CURRENT_DB_VERSION,
            config_folder=config,
            running_platform="Linux",
        )

        assert db.folders_table is not None
        assert db.settings is not None
        assert db.processed_files is not None
        assert db.oversight_and_defaults is not None
        assert db.emails_table is not None
        assert db.session_database is not None
        db.close()

    @pytest.mark.slow
    def test_upgraded_db_is_fully_functional(self, tmp_path):
        """After upgrade, new folder inserts and queries work normally."""
        db_path = str(tmp_path / "folders.db")
        config = str(tmp_path / "config")
        os.makedirs(config, exist_ok=True)

        _create_old_version_db(db_path, config, "33")

        db = DatabaseObj(
            database_path=db_path,
            database_version=CURRENT_DB_VERSION,
            config_folder=config,
            running_platform="Linux",
        )

        # Insert a new folder post-upgrade
        db.folders_table.insert(
            dict(
                folder_name="/new/path",
                alias="new_folder",
                folder_is_active=1,
                process_backend_copy=1,
                copy_to_directory="/new/out",
            )
        )
        db.database_connection.commit()

        found = db.folders_table.find_one(alias="new_folder")
        assert found is not None
        assert found["folder_name"] == "/new/path"

        # Old data still there
        assert db.folders_table.find_one(alias="invoices") is not None

        # Settings accessible
        settings = db.settings.find_one(id=1)
        assert settings is not None
        db.close()

    @pytest.mark.slow
    def test_upgraded_db_can_process_files(self, tmp_path):
        """After upgrade, the orchestrator can process folders from the DB."""
        db_path = str(tmp_path / "folders.db")
        config = str(tmp_path / "config")
        os.makedirs(config, exist_ok=True)

        _create_old_version_db(db_path, config, "33")

        db = DatabaseObj(
            database_path=db_path,
            database_version=CURRENT_DB_VERSION,
            config_folder=config,
            running_platform="Linux",
        )

        # Create real input folder with a file
        inp = tmp_path / "input"
        inp.mkdir()
        (inp / "test.edi").write_text(
            "HDRA0000000000000000  000000000000000test.edi\n"
            "A0000000000  0000000100100000000000\n"
        )
        out = tmp_path / "output"
        out.mkdir()

        # Update the "invoices" folder to point at real paths
        row = db.folders_table.find_one(alias="invoices")
        row["folder_name"] = str(inp)
        row["copy_to_directory"] = str(out)
        db.folders_table.update(row, ["id"])
        db.database_connection.commit()

        folder = dict(db.folders_table.find_one(alias="invoices"))

        backend = TrackingBackend()
        orch_config = DispatchConfig(backends={"copy": backend}, settings={})
        orch = DispatchOrchestrator(orch_config)
        result = orch.process_folder(folder, MagicMock())

        assert len(backend.sent) == 1
        assert result.files_processed == 1
        db.close()

    def test_version_too_new_raises_system_exit(self, tmp_path):
        """Opening a DB newer than the app version raises SystemExit."""
        db_path = str(tmp_path / "folders.db")
        config = str(tmp_path / "config")
        os.makedirs(config, exist_ok=True)

        # Create DB at current version
        _create_old_version_db(db_path, config, CURRENT_DB_VERSION)

        # Try to open it as if the app is at an older version
        with pytest.raises(SystemExit, match="Database version too new"):
            DatabaseObj(
                database_path=db_path,
                database_version="33",
                config_folder=config,
                running_platform="Linux",
            )

    @pytest.mark.slow
    def test_double_open_after_upgrade_is_noop(self, tmp_path):
        """Opening an already-upgraded DB a second time doesn't re-migrate."""
        db_path = str(tmp_path / "folders.db")
        config = str(tmp_path / "config")
        os.makedirs(config, exist_ok=True)

        _create_old_version_db(db_path, config, "33")

        # First open: triggers upgrade
        db1 = DatabaseObj(
            database_path=db_path,
            database_version=CURRENT_DB_VERSION,
            config_folder=config,
            running_platform="Linux",
        )
        db1.close()

        # Second open: should be a no-op (already at current version)
        db2 = DatabaseObj(
            database_path=db_path,
            database_version=CURRENT_DB_VERSION,
            config_folder=config,
            running_platform="Linux",
        )
        ver = db2.database_connection["version"].find_one(id=1)
        assert int(ver["version"]) == int(CURRENT_DB_VERSION)

        # Data still intact
        assert db2.folders_table.find_one(alias="invoices") is not None
        db2.close()
