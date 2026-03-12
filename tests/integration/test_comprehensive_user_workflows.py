"""Comprehensive user workflow integration tests.

These tests validate complete user journeys from start to finish using the
real DispatchOrchestrator, SendManager, ProcessedFilesTracker, and ErrorHandler
with mock backends and real file system operations.

Coverage:
1. Add Folder → Configure → Process → View Results
2. Edit Folder → Change Settings → Save → Verify Persistence
3. Process → Error → Retry → Success
4. Bulk Operations (select multiple folders → process/delete/edit)
5. Complete lifecycle management
6. Processed file tracking and resend workflows
"""

import shutil
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.e2e, pytest.mark.workflow]


from dispatch.error_handler import ErrorHandler
from dispatch.hash_utils import generate_file_hash
from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator
from dispatch.processed_files_tracker import (
    InMemoryDatabase,
    ProcessedFilesTracker,
)

# ---------------------------------------------------------------------------
# Shared helpers / fixtures
# ---------------------------------------------------------------------------

SAMPLE_EDI = """\
A00000120240101001TESTVENDOR         Test Vendor Inc                 00001
B001001ITEM001     000010EA0010Test Item 1                     0000010000
B001002ITEM002     000020EA0020Test Item 2                     0000020000
C00000003000030000
"""


class TrackingCopyBackend:
    """Backend that copies files and records each call."""

    def __init__(self):
        self.sent: list[str] = []

    def send(self, params: dict, settings: dict, filename: str) -> bool:
        dest_dir = params.get("copy_to_directory")
        if dest_dir:
            dest = Path(dest_dir)
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(filename, dest / Path(filename).name)
        self.sent.append(filename)
        return True


class FailOnceBackend:
    """Backend that fails on the first call, then succeeds."""

    def __init__(self):
        self.call_count = 0
        self.sent: list[str] = []

    def send(self, params: dict, settings: dict, filename: str) -> bool:
        self.call_count += 1
        if self.call_count == 1:
            raise ConnectionError("Transient failure")
        self.sent.append(filename)
        return True


class AlwaysFailBackend:
    """Backend that always raises."""

    def send(self, params: dict, settings: dict, filename: str) -> bool:
        raise RuntimeError("Permanent failure")


class NoopBackend:
    """Backend that succeeds silently."""

    def __init__(self):
        self.sent: list[str] = []

    def send(self, params: dict, settings: dict, filename: str) -> bool:
        self.sent.append(filename)
        return True


@pytest.fixture
def workspace(tmp_path):
    """Create a workspace with input, output, and error directories."""
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    error_dir = tmp_path / "errors"
    error_dir.mkdir()

    return {
        "root": tmp_path,
        "input": input_dir,
        "output": output_dir,
        "errors": error_dir,
    }


@pytest.fixture
def edi_files(workspace):
    """Write three sample EDI files into the workspace input directory."""
    paths = []
    for i in range(3):
        p = workspace["input"] / f"invoice_{i:03d}.edi"
        p.write_text(SAMPLE_EDI.replace("00001", f"{i + 1:05d}"))
        paths.append(p)
    return paths


@pytest.fixture
def folder_config(workspace):
    """Return a minimal folder-config dict ready for the orchestrator."""
    return {
        "id": 1,
        "folder_name": str(workspace["input"]),
        "alias": "Workflow Test Folder",
        "process_backend_copy": True,
        "copy_to_directory": str(workspace["output"]),
        "process_backend_ftp": False,
        "process_backend_email": False,
    }


# =============================================================================
# 1. Add Folder → Configure → Process → View Results
# =============================================================================


class TestAddConfigureProcessView:
    """Full user workflow: configure → process → verify results."""

    def test_single_folder_copy_backend(self, workspace, edi_files, folder_config):
        """Process a folder with copy backend and verify output files."""
        backend = TrackingCopyBackend()
        config = DispatchConfig(backends={"copy": backend}, settings={})
        orchestrator = DispatchOrchestrator(config)

        result = orchestrator.process_folder(folder_config, MagicMock())

        assert result.success is True
        assert result.files_processed == 3
        assert result.files_failed == 0

        output_files = list(workspace["output"].glob("*.edi"))
        assert len(output_files) == 3

    def test_single_folder_multiple_backends(self, workspace, edi_files, folder_config):
        """Process a folder with copy + ftp backends enabled."""
        folder_config["process_backend_ftp"] = True
        folder_config["ftp_server"] = "ftp.test.example"

        copy_be = TrackingCopyBackend()
        ftp_be = NoopBackend()

        config = DispatchConfig(backends={"copy": copy_be, "ftp": ftp_be}, settings={})
        orchestrator = DispatchOrchestrator(config)

        result = orchestrator.process_folder(folder_config, MagicMock())

        assert result.success is True
        assert result.files_processed == 3
        assert len(copy_be.sent) == 3
        assert len(ftp_be.sent) == 3

    def test_process_three_folders_sequentially(self, workspace):
        """Process three independent folders one after another."""
        copy_be = TrackingCopyBackend()
        config = DispatchConfig(backends={"copy": copy_be}, settings={})
        orchestrator = DispatchOrchestrator(config)

        results = []
        for idx in range(3):
            inp = workspace["root"] / f"inp_{idx}"
            out = workspace["root"] / f"out_{idx}"
            inp.mkdir()
            out.mkdir()
            (inp / f"file_{idx}.edi").write_text(SAMPLE_EDI)

            fc = {
                "id": idx + 1,
                "folder_name": str(inp),
                "alias": f"Folder {idx}",
                "process_backend_copy": True,
                "copy_to_directory": str(out),
                "process_backend_ftp": False,
                "process_backend_email": False,
            }
            results.append(orchestrator.process_folder(fc, MagicMock()))

        assert all(r.success for r in results)
        assert sum(r.files_processed for r in results) == 3
        assert len(copy_be.sent) == 3


# =============================================================================
# 2. Edit Folder → Change Settings → Save → Verify Persistence
# =============================================================================


class TestEditFolderPersistence:
    """Settings round-trip via DatabaseObj."""

    def test_folder_crud_roundtrip(self, tmp_path):
        """Insert, read, update, delete a folder in DatabaseObj."""
        import create_database
        from batch_file_processor.constants import CURRENT_DATABASE_VERSION
        from interface.database.database_obj import DatabaseObj

        db_path = tmp_path / "folders.db"
        create_database.do("33", str(db_path), str(tmp_path), "Linux")
        db = DatabaseObj(
            database_path=str(db_path),
            database_version=CURRENT_DATABASE_VERSION,
            config_folder=str(tmp_path),
            running_platform="Linux",
        )

        # --- INSERT ---
        db.folders_table.insert(
            {
                "folder_name": "/original/path",
                "alias": "Original",
                "process_backend_copy": True,
                "copy_to_directory": "/tmp/out",
            }
        )
        rows = list(db.folders_table.all())
        assert len(rows) == 1
        fid = rows[0]["id"]

        # --- READ ---
        row = db.folders_table.find_one(id=fid)
        assert row["alias"] == "Original"

        # --- UPDATE ---
        row["alias"] = "Renamed"
        row["process_backend_ftp"] = True
        db.folders_table.update(row, ["id"])
        row = db.folders_table.find_one(id=fid)
        assert row["alias"] == "Renamed"
        assert row["process_backend_ftp"] is True

        # --- DELETE ---
        db.folders_table.delete(id=fid)
        assert db.folders_table.find_one(id=fid) is None

        db.close()

    def test_toggle_folder_active_status(self, tmp_path):
        """Toggle folder active ↔ inactive and verify persistence."""
        import create_database
        from batch_file_processor.constants import CURRENT_DATABASE_VERSION
        from interface.database.database_obj import DatabaseObj

        db_path = tmp_path / "folders.db"
        create_database.do("33", str(db_path), str(tmp_path), "Linux")
        db = DatabaseObj(
            database_path=str(db_path),
            database_version=CURRENT_DATABASE_VERSION,
            config_folder=str(tmp_path),
            running_platform="Linux",
        )

        db.folders_table.insert(
            {"folder_name": "/test", "alias": "Toggle", "folder_is_active": True}
        )
        row = list(db.folders_table.all())[0]
        fid = row["id"]

        # Deactivate
        row["folder_is_active"] = False
        db.folders_table.update(row, ["id"])
        assert db.folders_table.find_one(id=fid)["folder_is_active"] is False

        # Reactivate
        row["folder_is_active"] = True
        db.folders_table.update(row, ["id"])
        assert db.folders_table.find_one(id=fid)["folder_is_active"] is True

        db.close()

    def test_settings_roundtrip(self, tmp_path):
        """Read and update global settings."""
        import create_database
        from batch_file_processor.constants import CURRENT_DATABASE_VERSION
        from interface.database.database_obj import DatabaseObj

        db_path = tmp_path / "folders.db"
        create_database.do("33", str(db_path), str(tmp_path), "Linux")
        db = DatabaseObj(
            database_path=str(db_path),
            database_version=CURRENT_DATABASE_VERSION,
            config_folder=str(tmp_path),
            running_platform="Linux",
        )

        settings = db.get_settings_or_default()
        assert settings.get("email_address") is None  # fresh db

        settings["email_address"] = "test@example.com"
        db.settings.update(settings, ["id"])

        updated = db.get_settings_or_default()
        assert updated.get("email_address") == "test@example.com"

        db.close()


# =============================================================================
# 3. Process → Error → Retry → Success
# =============================================================================


class TestErrorRetrySuccess:
    """Error-and-recovery workflow."""

    def test_backend_failure_then_retry_succeeds(
        self, workspace, edi_files, folder_config
    ):
        """First run fails (bad backend), second run with good backend succeeds."""
        # --- first run (fails) ---
        failing = AlwaysFailBackend()
        cfg1 = DispatchConfig(backends={"copy": failing}, settings={})
        orch1 = DispatchOrchestrator(cfg1)
        r1 = orch1.process_folder(folder_config, MagicMock())

        assert r1.success is False
        assert r1.files_failed == 3

        # --- second run (succeeds) ---
        good = TrackingCopyBackend()
        cfg2 = DispatchConfig(backends={"copy": good}, settings={})
        orch2 = DispatchOrchestrator(cfg2)
        r2 = orch2.process_folder(folder_config, MagicMock())

        assert r2.success is True
        assert r2.files_processed == 3
        assert len(list(workspace["output"].glob("*.edi"))) == 3

    def test_partial_backend_failure(self, workspace, edi_files, folder_config):
        """Copy backend succeeds but FTP fails – result reflects failure."""
        folder_config["process_backend_ftp"] = True
        folder_config["ftp_server"] = "ftp.test.example"

        copy_be = TrackingCopyBackend()
        ftp_be = AlwaysFailBackend()

        config = DispatchConfig(backends={"copy": copy_be, "ftp": ftp_be}, settings={})
        orchestrator = DispatchOrchestrator(config)
        result = orchestrator.process_folder(folder_config, MagicMock())

        # All files should fail because FTP raises on every file
        assert result.success is False
        assert result.files_failed == 3
        # But copy backend was called for every file
        assert len(copy_be.sent) == 3

    def test_error_handler_records_errors_in_memory(self, workspace):
        """ErrorHandler records errors to its in-memory list."""
        handler = ErrorHandler()

        handler.record_error(
            folder="/some/folder",
            filename="invoice.edi",
            error=RuntimeError("Test error"),
            context={"step": "send"},
        )

        assert len(handler.errors) == 1
        assert handler.errors[0]["filename"] == "invoice.edi"
        assert "Test error" in handler.errors[0]["error_message"]

    def test_error_does_not_propagate_between_files(
        self, workspace, edi_files, folder_config
    ):
        """A backend that raises once does not block subsequent files."""
        be = FailOnceBackend()
        config = DispatchConfig(backends={"copy": be}, settings={})
        orchestrator = DispatchOrchestrator(config)

        result = orchestrator.process_folder(folder_config, MagicMock())

        # The first file should fail; the remaining 2 should succeed
        assert result.files_failed == 1
        assert result.files_processed == 2
        assert len(be.sent) == 2


# =============================================================================
# 4. Bulk Operations
# =============================================================================


class TestBulkOperations:
    """Bulk folder operations."""

    def test_bulk_create_and_process(self, tmp_path):
        """Create N folders in DB, process all, verify all succeed."""
        import create_database
        from batch_file_processor.constants import CURRENT_DATABASE_VERSION
        from interface.database.database_obj import DatabaseObj

        db_path = tmp_path / "folders.db"
        create_database.do("33", str(db_path), str(tmp_path), "Linux")
        db = DatabaseObj(
            database_path=str(db_path),
            database_version=CURRENT_DATABASE_VERSION,
            config_folder=str(tmp_path),
            running_platform="Linux",
        )

        # Create 5 folder configs in DB
        for i in range(5):
            inp = tmp_path / f"inp_{i}"
            out = tmp_path / f"out_{i}"
            inp.mkdir()
            out.mkdir()
            (inp / f"file_{i}.edi").write_text(SAMPLE_EDI)

            db.folders_table.insert(
                {
                    "folder_name": str(inp),
                    "alias": f"Bulk {i}",
                    "process_backend_copy": True,
                    "copy_to_directory": str(out),
                }
            )

        all_folders = list(db.folders_table.all())
        assert len(all_folders) == 5

        copy_be = TrackingCopyBackend()
        config = DispatchConfig(backends={"copy": copy_be}, settings={})
        orchestrator = DispatchOrchestrator(config)

        results = [orchestrator.process_folder(f, MagicMock()) for f in all_folders]

        assert all(r.success for r in results)
        assert sum(r.files_processed for r in results) == 5

        db.close()

    def test_bulk_deactivate_and_delete(self, tmp_path):
        """Deactivate then delete multiple folder configs."""
        import create_database
        from batch_file_processor.constants import CURRENT_DATABASE_VERSION
        from interface.database.database_obj import DatabaseObj

        db_path = tmp_path / "folders.db"
        create_database.do("33", str(db_path), str(tmp_path), "Linux")
        db = DatabaseObj(
            database_path=str(db_path),
            database_version=CURRENT_DATABASE_VERSION,
            config_folder=str(tmp_path),
            running_platform="Linux",
        )

        for i in range(4):
            db.folders_table.insert({"folder_name": f"/path/{i}", "alias": f"Del {i}"})

        rows = list(db.folders_table.all())
        assert len(rows) == 4

        # Deactivate first two
        for row in rows[:2]:
            row["folder_is_active"] = False
            db.folders_table.update(row, ["id"])

        # Delete the deactivated ones
        for row in rows[:2]:
            db.folders_table.delete(id=row["id"])

        assert len(list(db.folders_table.all())) == 2

        db.close()


# =============================================================================
# 5. Complete Lifecycle
# =============================================================================


class TestCompleteLifecycle:
    """Create → Process → Edit → Deactivate → Delete."""

    def test_full_lifecycle(self, tmp_path):
        """Walk through the entire folder lifecycle."""
        import create_database
        from batch_file_processor.constants import CURRENT_DATABASE_VERSION
        from interface.database.database_obj import DatabaseObj

        db_path = tmp_path / "folders.db"
        create_database.do("33", str(db_path), str(tmp_path), "Linux")
        db = DatabaseObj(
            database_path=str(db_path),
            database_version=CURRENT_DATABASE_VERSION,
            config_folder=str(tmp_path),
            running_platform="Linux",
        )

        inp = tmp_path / "life_input"
        out = tmp_path / "life_output"
        inp.mkdir()
        out.mkdir()
        (inp / "a.edi").write_text(SAMPLE_EDI)

        # 1 – CREATE
        db.folders_table.insert(
            {
                "folder_name": str(inp),
                "alias": "Life",
                "process_backend_copy": True,
                "copy_to_directory": str(out),
            }
        )
        row = list(db.folders_table.all())[0]
        fid = row["id"]

        # 2 – PROCESS
        copy_be = TrackingCopyBackend()
        config = DispatchConfig(backends={"copy": copy_be}, settings={})
        orchestrator = DispatchOrchestrator(config)
        r = orchestrator.process_folder(row, MagicMock())
        assert r.success is True

        # 3 – EDIT
        row["alias"] = "Life - Renamed"
        db.folders_table.update(row, ["id"])
        assert db.folders_table.find_one(id=fid)["alias"] == "Life - Renamed"

        # 4 – DEACTIVATE
        row["folder_is_active"] = False
        db.folders_table.update(row, ["id"])
        assert db.folders_table.find_one(id=fid)["folder_is_active"] is False

        # 5 – DELETE
        db.folders_table.delete(id=fid)
        assert db.folders_table.find_one(id=fid) is None

        db.close()


# =============================================================================
# 6. Processed-file tracking & resend
# =============================================================================


class TestProcessedFilesTracking:
    """Workflow involving ProcessedFilesTracker."""

    def test_track_processed_files_and_mark_for_resend(self):
        """Record files, mark one for resend, verify list."""
        db = InMemoryDatabase()
        tracker = ProcessedFilesTracker(db)

        for i in range(3):
            tracker.record_sent_file_simple(
                file_name=f"file_{i}.edi",
                folder_id=1,
                file_checksum=f"hash_{i}",
            )

        assert tracker.count_files(folder_id=1) == 3

        # Mark one for resend
        assert tracker.mark_for_resend("file_1.edi", folder_id=1) is True

        resend = tracker.get_files_for_resend(folder_id=1)
        assert len(resend) == 1
        assert resend[0].file_name == "file_1.edi"

        # Clear resend flag
        tracker.clear_resend_flag("file_1.edi", folder_id=1)
        assert len(tracker.get_files_for_resend(folder_id=1)) == 0

    def test_duplicate_detection_via_checksum(self):
        """Same checksum + folder = file already sent."""
        db = InMemoryDatabase()
        tracker = ProcessedFilesTracker(db)

        tracker.record_sent_file_simple("a.edi", folder_id=1, file_checksum="abc")

        assert tracker.file_exists("a.edi", folder_id=1) is True
        assert tracker.file_exists("b.edi", folder_id=1) is False

    def test_processed_files_used_to_skip_reprocessing(
        self, workspace, edi_files, folder_config
    ):
        """Orchestrator can skip already-processed files via processed_files DB."""

        class SimpleProcessedDB:
            """Minimalist DatabaseInterface for the processed-files table."""

            def __init__(self):
                self._records: list[dict] = []

            def find(self, **kwargs) -> list[dict]:
                return [
                    r
                    for r in self._records
                    if all(r.get(k) == v for k, v in kwargs.items())
                ]

            def find_one(self, **kwargs):
                for r in self._records:
                    if all(r.get(k) == v for k, v in kwargs.items()):
                        return r
                return None

            def insert(self, record: dict) -> None:
                self._records.append(dict(record))

            def insert_many(self, records: list[dict]) -> None:
                for r in records:
                    self.insert(r)

            def update(self, record: dict, keys: list) -> None:
                for i, existing in enumerate(self._records):
                    if all(existing.get(k) == record.get(k) for k in keys):
                        self._records[i] = dict(record)
                        return

            def count(self, **kwargs) -> int:
                return len(self.find(**kwargs))

            def query(self, sql: str):
                return None

        db = SimpleProcessedDB()
        copy_be = TrackingCopyBackend()
        config = DispatchConfig(backends={"copy": copy_be}, settings={})
        orchestrator = DispatchOrchestrator(config)

        # First run – process everything
        r1 = orchestrator.process_folder(folder_config, MagicMock(), processed_files=db)
        assert r1.files_processed == 3

        # Second run – all should be skipped (already tracked)
        r2 = orchestrator.process_folder(folder_config, MagicMock(), processed_files=db)
        assert r2.files_processed == 0


# =============================================================================
# 7. Empty / missing folder edge cases
# =============================================================================


class TestEdgeCases:
    """Edge-case scenarios the user may hit."""

    def test_empty_folder(self, workspace, folder_config):
        """Processing an empty folder succeeds with 0 files."""
        config = DispatchConfig(backends={"copy": NoopBackend()}, settings={})
        orchestrator = DispatchOrchestrator(config)
        result = orchestrator.process_folder(folder_config, MagicMock())

        assert result.success is True
        assert result.files_processed == 0

    def test_missing_folder(self, workspace):
        """Processing a nonexistent folder returns failure."""
        fc = {
            "id": 99,
            "folder_name": str(workspace["root"] / "does_not_exist"),
            "alias": "Ghost",
            "process_backend_copy": True,
            "copy_to_directory": str(workspace["output"]),
        }
        config = DispatchConfig(backends={"copy": NoopBackend()}, settings={})
        orchestrator = DispatchOrchestrator(config)
        result = orchestrator.process_folder(fc, MagicMock())

        assert result.success is False
        assert len(result.errors) > 0

    def test_no_backends_enabled(self, workspace, edi_files, folder_config):
        """Processing with no backends enabled fails for each file."""
        folder_config["process_backend_copy"] = False
        config = DispatchConfig(backends={}, settings={})
        orchestrator = DispatchOrchestrator(config)
        result = orchestrator.process_folder(folder_config, MagicMock())

        # Each file fails because no backend is enabled
        assert result.success is False
        assert result.files_failed == 3

    def test_file_hashing_consistency(self, workspace, edi_files):
        """Same file → same hash, different file → different hash."""
        h1 = generate_file_hash(str(edi_files[0]))
        h2 = generate_file_hash(str(edi_files[0]))
        h3 = generate_file_hash(str(edi_files[1]))

        assert h1 == h2
        assert h1 != h3
        assert len(h1) == 32
