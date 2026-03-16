"""Tests for database state management, schema verification, and orchestrator DB integration.

Tests cover:
- DB snapshot / restore patterns
- fresh_db isolation between tests
- Schema verification
- Folder and processed_files CRUD
- Resend flag lifecycle
- Concurrent reads
- Orchestrator DB integration
"""

import concurrent.futures
import hashlib
import os
import shutil
import sqlite3
import sys
import threading
import time
from io import StringIO
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from interface.database import sqlite_wrapper
from interface.database.database_obj import DatabaseObj
from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator
from dispatch.send_manager import MockBackend


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def open_db(db_path: Path) -> sqlite_wrapper.Database:
    """Connect to the SQLite database at db_path."""
    return sqlite_wrapper.Database.connect(str(db_path))


def minimal_folder_row(
    folder_name: str = "/tmp/test_folder",
    alias: str = "TestAlias",
    active: bool = True,
) -> dict:
    return {
        "folder_name": folder_name,
        "alias": alias,
        "folder_is_active": active,
        "process_backend_copy": False,
        "process_backend_ftp": False,
        "process_backend_email": False,
        "process_edi": False,
        "split_edi": False,
        "tweak_edi": False,
        "force_edi_validation": False,
        "ftp_port": 21,
        "ftp_server": "",
        "ftp_username": "",
        "ftp_password": "",
        "ftp_folder": "",
        "email_to": "",
        "email_subject_line": "",
        "copy_to_directory": "",
    }


def minimal_processed_file_row(
    file_name: str = "/tmp/test/data.txt",
    folder_id: int = 1,
    checksum: str = "abc123",
    resend_flag: int = 0,
    status: str = "processed",
) -> dict:
    return {
        "file_name": file_name,
        "folder_id": folder_id,
        "folder_alias": "TestAlias",
        "file_checksum": checksum,
        "resend_flag": resend_flag,
        "status": status,
        "processed_at": "2026-03-01T10:00:00",
        "sent_to": "N/A",
        "invoice_numbers": "",
    }


# ---------------------------------------------------------------------------
# Snapshot / restore tests
# ---------------------------------------------------------------------------


class TestDBSnapshotRestore:
    """DB file snapshot and restore patterns."""

    def test_db_snapshot_and_restore(self, fresh_db, tmp_path):
        """Copy DB, modify it, restore from snapshot, verify original state."""
        snapshot = tmp_path / "snapshot.db"
        shutil.copy2(str(fresh_db), str(snapshot))

        db = open_db(fresh_db)
        db["folders"].insert(minimal_folder_row(alias="ModifiedAlias"))
        db.close()

        # Verify modification is visible
        db2 = open_db(fresh_db)
        assert db2["folders"].count(alias="ModifiedAlias") == 1
        db2.close()

        # Restore from snapshot
        shutil.copy2(str(snapshot), str(fresh_db))

        # Verify modification is gone
        db3 = open_db(fresh_db)
        assert db3["folders"].count(alias="ModifiedAlias") == 0
        db3.close()

    def test_db_state_isolated_between_tests(self, fresh_db, tmp_path):
        """Two separate fresh_db paths should not share state."""
        # This test verifies that fresh_db is per-test isolated.
        # We insert a unique marker and verify the path is not shared
        # with another tmp_path copy.
        second_db_path = tmp_path / "second.db"
        shutil.copy2(str(fresh_db), str(second_db_path))

        db1 = open_db(fresh_db)
        db2 = open_db(second_db_path)

        db1["folders"].insert(minimal_folder_row(alias="Only_In_DB1"))

        count_in_db1 = db1["folders"].count(alias="Only_In_DB1")
        count_in_db2 = db2["folders"].count(alias="Only_In_DB1")

        db1.close()
        db2.close()

        assert count_in_db1 == 1
        assert count_in_db2 == 0

    def test_db_cleanup_between_runs(self, fresh_db, tmp_path):
        """Demonstrate snapshot/restore for test isolation."""
        snapshot = tmp_path / "clean_snapshot.db"
        shutil.copy2(str(fresh_db), str(snapshot))

        # Simulate run 1: insert records
        db = open_db(fresh_db)
        for i in range(5):
            db["folders"].insert(
                minimal_folder_row(
                    folder_name=f"/run1/folder{i}",
                    alias=f"Run1Folder{i}",
                )
            )
        db.close()

        # Restore snapshot (simulating cleanup between runs)
        shutil.copy2(str(snapshot), str(fresh_db))

        # Run 2: DB should be clean
        db2 = open_db(fresh_db)
        count = db2["folders"].count()
        db2.close()

        assert count == 0


# ---------------------------------------------------------------------------
# Schema verification tests
# ---------------------------------------------------------------------------


class TestDBSchema:
    """Verify that fresh_db has the correct schema."""

    def test_fresh_db_has_correct_schema(self, fresh_db):
        """fresh_db must have folders, settings, and processed_files tables."""
        db = open_db(fresh_db)
        tables = db.tables
        db.close()

        assert "folders" in tables
        assert "settings" in tables
        assert "processed_files" in tables

    def test_fresh_db_has_version_table(self, fresh_db):
        """fresh_db must have a version record."""
        db = open_db(fresh_db)
        version = db["version"].find_one(id=1)
        db.close()

        assert version is not None
        assert "version" in version

    def test_fresh_db_has_all_expected_tables(self, fresh_db):
        """All application tables should be present after schema initialisation."""
        expected_tables = {
            "folders",
            "settings",
            "processed_files",
            "emails_to_send",
            "working_batch_emails_to_send",
            "sent_emails_removal_queue",
            "administrative",
            "version",
        }
        db = open_db(fresh_db)
        tables = set(db.tables)
        db.close()

        missing = expected_tables - tables
        assert missing == set(), f"Missing tables: {missing}"

    def test_processed_files_has_resend_flag_column(self, fresh_db):
        """processed_files table must have a resend_flag column."""
        conn = sqlite3.connect(str(fresh_db))
        cursor = conn.execute("PRAGMA table_info(processed_files)")
        cols = {row[1] for row in cursor.fetchall()}
        conn.close()

        assert "resend_flag" in cols

    def test_folders_table_has_required_columns(self, fresh_db):
        """folders table must have backend-related boolean columns."""
        conn = sqlite3.connect(str(fresh_db))
        cursor = conn.execute("PRAGMA table_info(folders)")
        cols = {row[1] for row in cursor.fetchall()}
        conn.close()

        required = {
            "folder_name",
            "alias",
            "folder_is_active",
            "process_backend_ftp",
            "process_backend_email",
            "process_backend_copy",
        }
        missing = required - cols
        assert missing == set(), f"Missing columns in folders: {missing}"


# ---------------------------------------------------------------------------
# CRUD tests
# ---------------------------------------------------------------------------


class TestFolderCRUD:
    """Create, read, update, delete operations on folder records."""

    def test_folder_crud_operations(self, fresh_db):
        """Full CRUD cycle for a folder record."""
        db = open_db(fresh_db)
        tbl = db["folders"]

        # Create
        row_id = tbl.insert(minimal_folder_row(alias="MyCRUDFolder"))
        assert row_id > 0

        # Read
        found = tbl.find_one(alias="MyCRUDFolder")
        assert found is not None
        assert found["alias"] == "MyCRUDFolder"

        # Update
        tbl.update({"id": found["id"], "alias": "UpdatedAlias"}, ["id"])
        updated = tbl.find_one(id=found["id"])
        assert updated["alias"] == "UpdatedAlias"

        # Delete
        tbl.delete(id=found["id"])
        deleted = tbl.find_one(id=found["id"])
        assert deleted is None

        db.close()

    def test_folder_active_filter(self, fresh_db):
        """find(folder_is_active=True) must return only active folders."""
        db = open_db(fresh_db)
        tbl = db["folders"]

        tbl.insert(minimal_folder_row(alias="Active1", active=True))
        tbl.insert(minimal_folder_row(alias="Active2", active=True))
        tbl.insert(minimal_folder_row(alias="Inactive1", active=False))

        active = tbl.find(folder_is_active=True)
        inactive = tbl.find(folder_is_active=False)
        db.close()

        active_aliases = {r["alias"] for r in active}
        inactive_aliases = {r["alias"] for r in inactive}

        assert "Active1" in active_aliases
        assert "Active2" in active_aliases
        assert "Inactive1" not in active_aliases
        assert "Inactive1" in inactive_aliases

    def test_folder_insert_multiple_and_count(self, fresh_db):
        """Inserting multiple folders should be reflected in count()."""
        db = open_db(fresh_db)
        tbl = db["folders"]

        for i in range(7):
            tbl.insert(minimal_folder_row(alias=f"Folder{i}"))

        total = tbl.count()
        db.close()

        assert total == 7

    def test_folder_find_by_alias(self, fresh_db):
        """find_one with alias should return the correct record."""
        db = open_db(fresh_db)
        tbl = db["folders"]
        tbl.insert(minimal_folder_row(alias="SpecificAlias"))
        tbl.insert(minimal_folder_row(alias="OtherAlias"))

        found = tbl.find_one(alias="SpecificAlias")
        db.close()

        assert found is not None
        assert found["alias"] == "SpecificAlias"


# ---------------------------------------------------------------------------
# Processed files tests
# ---------------------------------------------------------------------------


class TestProcessedFilesCRUD:
    """Tests for the processed_files table."""

    def test_processed_files_insert_and_query(self, fresh_db):
        """Insert a processed_file record, then query by folder_id."""
        db = open_db(fresh_db)
        folders = db["folders"]
        folder_id = folders.insert(minimal_folder_row(alias="FolderForPF"))

        pf = db["processed_files"]
        pf.insert(
            minimal_processed_file_row(
                file_name="/test/myfile.txt",
                folder_id=folder_id,
                checksum="deadbeef",
            )
        )

        results = pf.find(folder_id=folder_id)
        db.close()

        assert len(results) == 1
        assert results[0]["file_name"] == "/test/myfile.txt"
        assert results[0]["file_checksum"] == "deadbeef"

    def test_processed_files_checksum_uniqueness(self, fresh_db):
        """Same checksum can exist under different folder_ids."""
        db = open_db(fresh_db)
        folders = db["folders"]
        id1 = folders.insert(minimal_folder_row(alias="Folder_A"))
        id2 = folders.insert(minimal_folder_row(alias="Folder_B"))

        pf = db["processed_files"]
        pf.insert(minimal_processed_file_row(folder_id=id1, checksum="shared_checksum"))
        pf.insert(minimal_processed_file_row(folder_id=id2, checksum="shared_checksum"))

        results = pf.find(file_checksum="shared_checksum")
        db.close()

        assert len(results) == 2
        folder_ids = {r["folder_id"] for r in results}
        assert id1 in folder_ids
        assert id2 in folder_ids

    def test_db_resend_flag_lifecycle(self, fresh_db):
        """Insert with resend_flag=0, set to 1, verify query, set to 0, verify cleared."""
        db = open_db(fresh_db)
        folders = db["folders"]
        folder_id = folders.insert(minimal_folder_row(alias="ResendFolder"))

        pf = db["processed_files"]
        rec_id = pf.insert(
            minimal_processed_file_row(folder_id=folder_id, resend_flag=0)
        )

        # Verify initially not in resend set
        resend_records = pf.find(resend_flag=1)
        assert len(resend_records) == 0

        # Set resend_flag=1
        pf.update({"id": rec_id, "resend_flag": 1}, ["id"])
        resend_records = pf.find(resend_flag=1)
        assert len(resend_records) == 1

        # Clear resend_flag
        pf.update({"id": rec_id, "resend_flag": 0}, ["id"])
        resend_records = pf.find(resend_flag=1)
        assert len(resend_records) == 0

        db.close()

    def test_processed_files_update_status(self, fresh_db):
        """Update status field from 'pending' to 'processed'."""
        db = open_db(fresh_db)
        folders = db["folders"]
        folder_id = folders.insert(minimal_folder_row())

        pf = db["processed_files"]
        rec_id = pf.insert(
            minimal_processed_file_row(folder_id=folder_id, status="pending")
        )

        pf.update({"id": rec_id, "status": "processed"}, ["id"])
        record = pf.find_one(id=rec_id)
        db.close()

        assert record["status"] == "processed"

    def test_processed_files_sent_to_field(self, fresh_db):
        """The sent_to field should be stored and retrieved correctly."""
        db = open_db(fresh_db)
        folders = db["folders"]
        folder_id = folders.insert(minimal_folder_row())

        pf = db["processed_files"]
        pf.insert(
            {
                **minimal_processed_file_row(folder_id=folder_id),
                "sent_to": "FTP: ftp.example.com, Email: ops@example.com",
            }
        )

        record = pf.find_one(folder_id=folder_id)
        db.close()

        assert "FTP: ftp.example.com" in record["sent_to"]

    def test_processed_files_count_by_folder(self, fresh_db):
        """count() with folder_id filters correctly."""
        db = open_db(fresh_db)
        folders = db["folders"]
        id_a = folders.insert(minimal_folder_row(alias="A"))
        id_b = folders.insert(minimal_folder_row(alias="B"))

        pf = db["processed_files"]
        for i in range(3):
            pf.insert(
                minimal_processed_file_row(
                    file_name=f"/a/file{i}.txt", folder_id=id_a, checksum=f"ca{i}"
                )
            )
        for i in range(5):
            pf.insert(
                minimal_processed_file_row(
                    file_name=f"/b/file{i}.txt", folder_id=id_b, checksum=f"cb{i}"
                )
            )

        count_a = pf.count(folder_id=id_a)
        count_b = pf.count(folder_id=id_b)
        db.close()

        assert count_a == 3
        assert count_b == 5


# ---------------------------------------------------------------------------
# Concurrent reads test
# ---------------------------------------------------------------------------


class TestDBConcurrentAccess:
    """Verify that concurrent read access does not cause corruption."""

    def test_db_concurrent_reads(self, fresh_db):
        """Spawn 5 threads reading from the DB simultaneously; no corruption."""
        db_setup = open_db(fresh_db)
        folders = db_setup["folders"]
        for i in range(20):
            folders.insert(minimal_folder_row(alias=f"ConcFolder{i}"))
        db_setup.close()

        errors = []

        def read_worker(worker_id):
            try:
                db = open_db(fresh_db)
                records = db["folders"].find()
                count = len(records)
                db.close()
                if count != 20:
                    errors.append(f"Worker {worker_id} got unexpected count: {count}")
            except Exception as exc:
                errors.append(f"Worker {worker_id} raised: {exc}")

        threads = [threading.Thread(target=read_worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert errors == [], f"Concurrent read errors: {errors}"

    def test_db_concurrent_reads_threadpool(self, fresh_db):
        """ThreadPoolExecutor with 5 workers reading simultaneously."""
        db_setup = open_db(fresh_db)
        pf = db_setup["processed_files"]
        for i in range(10):
            pf.insert(
                minimal_processed_file_row(
                    file_name=f"/conc/file{i}.txt",
                    folder_id=1,
                    checksum=f"c{i:04d}",
                )
            )
        db_setup.close()

        errors = []

        def reader(worker_id):
            try:
                db = open_db(fresh_db)
                rows = db["processed_files"].find(folder_id=1)
                db.close()
                return len(rows)
            except Exception as exc:
                errors.append(str(exc))
                return -1

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(reader, i) for i in range(5)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert errors == [], f"Concurrent errors: {errors}"
        for count in results:
            assert count == 10


# ---------------------------------------------------------------------------
# Orchestrator DB integration tests
# ---------------------------------------------------------------------------


class TestOrchestratorDBIntegration:
    """Verify that the orchestrator correctly persists state to the DB."""

    @pytest.fixture
    def folder_dir(self, tmp_path):
        d = tmp_path / "orch_inbox"
        d.mkdir()
        (d / "invoice.txt").write_bytes(b"invoice data 001")
        return d

    @pytest.fixture
    def db_processed_files(self, fresh_db):
        """Return a live processed_files Table from a fresh_db."""
        db = open_db(fresh_db)
        yield db["processed_files"]
        db.close()

    def _make_folder(self, folder_path, folder_id=1):
        return {
            "id": folder_id,
            "folder_name": str(folder_path),
            "alias": f"OrcFolder_{folder_id}",
            "folder_is_active": True,
            "process_backend_copy": False,
            "process_backend_ftp": False,
            "process_backend_email": False,
            "process_edi": False,
            "split_edi": False,
            "tweak_edi": False,
            "force_edi_validation": False,
            "convert_edi": False,
        }

    def test_orchestrator_records_processed_files(self, folder_dir, db_processed_files):
        """After a successful run, the file appears in processed_files."""
        mock_be = MockBackend(should_succeed=True)
        config = DispatchConfig(backends={"mock": mock_be})
        orc = DispatchOrchestrator(config)
        folder = self._make_folder(folder_dir)

        orc.process_folder(folder, [], processed_files=db_processed_files)

        file_path = str(folder_dir / "invoice.txt")
        record = db_processed_files.find_one(folder_id=1)
        assert record is not None

    def test_orchestrator_does_not_duplicate_records(self, folder_dir, fresh_db):
        """Running orchestrator twice on the same file should produce only one record."""
        db = open_db(fresh_db)
        pf = db["processed_files"]

        mock_be = MockBackend(should_succeed=True)
        config = DispatchConfig(backends={"mock": mock_be})
        folder = self._make_folder(folder_dir)

        # First run
        orc = DispatchOrchestrator(config)
        orc.process_folder(folder, [], processed_files=pf)

        # Second run (same file, same folder)
        mock_be2 = MockBackend(should_succeed=True)
        config2 = DispatchConfig(backends={"mock": mock_be2})
        orc2 = DispatchOrchestrator(config2)
        orc2.process_folder(folder, [], processed_files=pf)

        count = pf.count(folder_id=1)
        db.close()

        # File should not be processed a second time → only 1 record
        assert count == 1
        # And the second orchestrator's backend was not called
        assert len(mock_be2.send_calls) == 0

    def test_orchestrator_sent_to_field_populated_with_ftp(self, folder_dir, fresh_db):
        """When FTP backend is enabled, sent_to should contain 'FTP:'."""
        db = open_db(fresh_db)
        pf = db["processed_files"]

        mock_be = MockBackend(should_succeed=True)
        config = DispatchConfig(backends={"ftp": mock_be})
        folder = {
            **self._make_folder(folder_dir),
            "process_backend_ftp": True,
            "ftp_server": "ftp.example.com",
        }

        orc = DispatchOrchestrator(config)
        orc.process_folder(folder, [], processed_files=pf)

        record = pf.find_one(folder_id=1)
        db.close()

        assert record is not None
        assert "FTP" in record.get("sent_to", "")

    def test_orchestrator_resend_flag_cleared_in_real_db(self, folder_dir, fresh_db):
        """resend_flag should be cleared to 0 in the real SQLite DB after resend."""
        db = open_db(fresh_db)
        pf = db["processed_files"]

        file_path = str(folder_dir / "invoice.txt")
        with open(file_path, "rb") as fh:
            checksum = hashlib.md5(fh.read()).hexdigest()

        pf.insert(
            {
                "file_name": file_path,
                "folder_id": 1,
                "folder_alias": "OrcFolder_1",
                "file_checksum": checksum,
                "resend_flag": 1,
                "status": "processed",
                "processed_at": "2026-01-01T00:00:00",
                "sent_to": "N/A",
                "invoice_numbers": "",
            }
        )

        mock_be = MockBackend(should_succeed=True)
        config = DispatchConfig(backends={"mock": mock_be})
        folder = self._make_folder(folder_dir)

        orc = DispatchOrchestrator(config)
        orc.process_folder(folder, [], processed_files=pf)

        record = pf.find_one(folder_id=1)
        db.close()

        assert record["resend_flag"] == 0 or record["resend_flag"] is False

    def test_orchestrator_nonexistent_folder_no_db_writes(self, tmp_path, fresh_db):
        """If the folder does not exist, nothing should be written to the DB."""
        db = open_db(fresh_db)
        pf = db["processed_files"]

        mock_be = MockBackend(should_succeed=True)
        config = DispatchConfig(backends={"mock": mock_be})
        folder = self._make_folder(tmp_path / "does_not_exist")

        orc = DispatchOrchestrator(config)
        orc.process_folder(folder, [], processed_files=pf)

        count = pf.count()
        db.close()

        assert count == 0

    def test_orchestrator_email_backend_flag_in_sent_to(self, folder_dir, fresh_db):
        """When email backend is enabled, sent_to should contain 'Email:'."""
        db = open_db(fresh_db)
        pf = db["processed_files"]

        mock_be = MockBackend(should_succeed=True)
        config = DispatchConfig(backends={"email": mock_be})
        folder = {
            **self._make_folder(folder_dir),
            "process_backend_email": True,
            "email_to": "recipient@example.com",
        }

        orc = DispatchOrchestrator(config)
        orc.process_folder(folder, [], processed_files=pf)

        record = pf.find_one(folder_id=1)
        db.close()

        assert record is not None
        assert "Email" in record.get("sent_to", "")

    def test_processed_files_table_isolation_across_folders(self, tmp_path, fresh_db):
        """Files from different folders should be independently tracked."""
        db = open_db(fresh_db)
        pf = db["processed_files"]

        dir_a = tmp_path / "folder_a"
        dir_b = tmp_path / "folder_b"
        dir_a.mkdir()
        dir_b.mkdir()
        (dir_a / "file_a.txt").write_bytes(b"data_a")
        (dir_b / "file_b.txt").write_bytes(b"data_b")

        mock_be = MockBackend(should_succeed=True)
        config = DispatchConfig(backends={"mock": mock_be})

        folder_a = self._make_folder(dir_a, folder_id=10)
        folder_b = self._make_folder(dir_b, folder_id=20)

        orc = DispatchOrchestrator(config)
        orc.process_folder(folder_a, [], processed_files=pf)

        mock_be2 = MockBackend(should_succeed=True)
        config2 = DispatchConfig(backends={"mock": mock_be2})
        orc2 = DispatchOrchestrator(config2)
        orc2.process_folder(folder_b, [], processed_files=pf)

        records_a = pf.find(folder_id=10)
        records_b = pf.find(folder_id=20)
        db.close()

        assert len(records_a) == 1
        assert len(records_b) == 1
        # Verify the correct files are recorded for each folder
        assert any("file_a.txt" in r.get("file_name", "") for r in records_a)
        assert any("file_b.txt" in r.get("file_name", "") for r in records_b)
