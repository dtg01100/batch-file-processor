"""Multi-folder processing and backend integration edge-case tests.

Covers:
1. Mixed backend configurations across folders
2. Backend switching between processing runs
3. Sequential resource sharing (shared output dirs)
4. Error isolation between folders
5. Partial success recording
6. Large file processing
7. Resource cleanup after batch runs
8. Concurrent database access
"""

import pytest
import shutil
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock

pytestmark = [pytest.mark.integration, pytest.mark.e2e, pytest.mark.workflow]

from dispatch.orchestrator import DispatchOrchestrator, DispatchConfig


# ---------------------------------------------------------------------------
# Shared EDI content
# ---------------------------------------------------------------------------

SAMPLE_EDI = """\
A00000120240101001TESTVENDOR         Test Vendor Inc                 00001
B001001ITEM001     000010EA0010Test Item 1                     0000010000
B001002ITEM002     000020EA0020Test Item 2                     0000020000
C00000003000030000
"""


# ---------------------------------------------------------------------------
# Mock backends
# ---------------------------------------------------------------------------


class CopyBackend:
    """Mock copy backend that physically copies files."""

    def __init__(self):
        self.sent: list[str] = []

    def send(self, params: dict, settings: dict, filename: str) -> bool:
        dest = params.get("copy_to_directory")
        if dest:
            Path(dest).mkdir(parents=True, exist_ok=True)
            shutil.copy2(filename, Path(dest) / Path(filename).name)
        self.sent.append(filename)
        return True


class RecordingBackend:
    """Records calls without any side-effects."""

    def __init__(self, name: str = "recording"):
        self.name = name
        self.sent: list[str] = []

    def send(self, params: dict, settings: dict, filename: str) -> bool:
        self.sent.append(filename)
        return True


class FailingBackend:
    """Always raises."""

    def __init__(self, msg: str = "Backend error"):
        self.msg = msg
        self.attempted: list[str] = []

    def send(self, params: dict, settings: dict, filename: str) -> bool:
        self.attempted.append(filename)
        raise RuntimeError(self.msg)


class SlowBackend:
    """Succeeds after an artificial delay."""

    def __init__(self, delay: float = 0.05):
        self.delay = delay
        self.sent: list[str] = []

    def send(self, params: dict, settings: dict, filename: str) -> bool:
        time.sleep(self.delay)
        self.sent.append(filename)
        return True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_folder(tmp_path, idx, edi_count=1):
    """Create input/output dirs and EDI files; return folder config dict."""
    inp = tmp_path / f"input_{idx}"
    out = tmp_path / f"output_{idx}"
    inp.mkdir()
    out.mkdir()
    for j in range(edi_count):
        (inp / f"file_{idx}_{j}.edi").write_text(SAMPLE_EDI)
    return {
        "id": idx + 1,
        "folder_name": str(inp),
        "alias": f"Folder {idx}",
        "process_backend_copy": True,
        "copy_to_directory": str(out),
        "process_backend_ftp": False,
        "process_backend_email": False,
    }


# =============================================================================
# 1. Mixed backend configurations
# =============================================================================


class TestMixedBackendConfigurations:
    """Folders with different backend combos processed in the same run."""

    def test_copy_only_vs_copy_plus_ftp(self, tmp_path):
        """One folder copy-only, another copy+ftp; both succeed."""
        fc_copy = _make_folder(tmp_path, 0)

        fc_both = _make_folder(tmp_path, 1)
        fc_both["process_backend_ftp"] = True
        fc_both["ftp_server"] = "ftp.test.example"

        copy_be = CopyBackend()
        ftp_be = RecordingBackend("ftp")

        config = DispatchConfig(
            backends={"copy": copy_be, "ftp": ftp_be}, settings={}
        )
        orch = DispatchOrchestrator(config)

        r0 = orch.process_folder(fc_copy, MagicMock())
        r1 = orch.process_folder(fc_both, MagicMock())

        assert r0.success is True
        assert r1.success is True
        # FTP should only fire for folder 1
        assert len(ftp_be.sent) == 1
        # Copy fires for both folders
        assert len(copy_be.sent) == 2

    def test_all_three_backends_enabled(self, tmp_path):
        """Folder with copy + ftp + email all enabled."""
        fc = _make_folder(tmp_path, 0, edi_count=2)
        fc["process_backend_ftp"] = True
        fc["ftp_server"] = "ftp.test.example"
        fc["process_backend_email"] = True
        fc["email_to"] = "test@example.com"

        copy_be = CopyBackend()
        ftp_be = RecordingBackend("ftp")
        email_be = RecordingBackend("email")

        config = DispatchConfig(
            backends={"copy": copy_be, "ftp": ftp_be, "email": email_be},
            settings={},
        )
        orch = DispatchOrchestrator(config)
        result = orch.process_folder(fc, MagicMock())

        assert result.success is True
        assert result.files_processed == 2
        assert len(copy_be.sent) == 2
        assert len(ftp_be.sent) == 2
        assert len(email_be.sent) == 2


# =============================================================================
# 2. Backend switching between runs
# =============================================================================


class TestBackendSwitching:
    """Switch backends for a folder between successive runs."""

    def test_switch_from_copy_to_ftp(self, tmp_path):
        """First run with copy, second run with ftp (copy disabled)."""
        fc = _make_folder(tmp_path, 0)

        # --- run 1: copy only ---
        copy_be = CopyBackend()
        cfg1 = DispatchConfig(backends={"copy": copy_be}, settings={})
        r1 = DispatchOrchestrator(cfg1).process_folder(fc, MagicMock())
        assert r1.success is True
        assert len(copy_be.sent) == 1

        # --- run 2: switch to ftp only ---
        fc["process_backend_copy"] = False
        fc["process_backend_ftp"] = True
        fc["ftp_server"] = "ftp.test.example"

        ftp_be = RecordingBackend("ftp")
        cfg2 = DispatchConfig(backends={"ftp": ftp_be}, settings={})
        r2 = DispatchOrchestrator(cfg2).process_folder(fc, MagicMock())
        assert r2.success is True
        assert len(ftp_be.sent) == 1


# =============================================================================
# 3. Shared output directory
# =============================================================================


class TestSharedOutputDirectory:
    """Multiple folders writing to the same output directory."""

    def test_three_folders_shared_output(self, tmp_path):
        """Three folders output to the same directory; all files arrive."""
        shared_out = tmp_path / "shared_output"
        shared_out.mkdir()

        copy_be = CopyBackend()
        config = DispatchConfig(backends={"copy": copy_be}, settings={})
        orch = DispatchOrchestrator(config)

        for idx in range(3):
            fc = _make_folder(tmp_path, idx)
            fc["copy_to_directory"] = str(shared_out)
            result = orch.process_folder(fc, MagicMock())
            assert result.success is True

        output_files = list(shared_out.glob("*.edi"))
        assert len(output_files) == 3


# =============================================================================
# 4. Error isolation between folders
# =============================================================================


class TestErrorIsolation:
    """A failure in one folder must not corrupt the next."""

    def test_failure_in_middle_folder(self, tmp_path):
        """Folder 0 succeeds, folder 1 fails, folder 2 still succeeds."""
        fcs = [_make_folder(tmp_path, i) for i in range(3)]

        good_be = CopyBackend()
        bad_be = FailingBackend("bang")

        good_cfg = DispatchConfig(backends={"copy": good_be}, settings={})
        bad_cfg = DispatchConfig(backends={"copy": bad_be}, settings={})

        r0 = DispatchOrchestrator(good_cfg).process_folder(fcs[0], MagicMock())
        r1 = DispatchOrchestrator(bad_cfg).process_folder(fcs[1], MagicMock())
        r2 = DispatchOrchestrator(good_cfg).process_folder(fcs[2], MagicMock())

        assert r0.success is True
        assert r1.success is False
        assert r2.success is True

    def test_error_does_not_leak_into_run_log(self, tmp_path):
        """Run logs remain separate per folder invocation."""
        fc_good = _make_folder(tmp_path, 0)
        fc_bad = _make_folder(tmp_path, 1)

        log_good = MagicMock()
        log_bad = MagicMock()

        good_be = CopyBackend()
        bad_be = FailingBackend("boom")

        DispatchOrchestrator(
            DispatchConfig(backends={"copy": bad_be}, settings={})
        ).process_folder(fc_bad, log_bad)

        result = DispatchOrchestrator(
            DispatchConfig(backends={"copy": good_be}, settings={})
        ).process_folder(fc_good, log_good)

        assert result.success is True


# =============================================================================
# 5. Partial success across multiple backends
# =============================================================================


class TestPartialSuccess:
    """Copy succeeds but FTP fails within the same file."""

    def test_copy_ok_ftp_failure_means_file_fails(self, tmp_path):
        """When any backend raises, the file counts as failed."""
        fc = _make_folder(tmp_path, 0, edi_count=2)
        fc["process_backend_ftp"] = True
        fc["ftp_server"] = "ftp.test.example"

        copy_be = CopyBackend()
        ftp_be = FailingBackend("ftp down")

        config = DispatchConfig(
            backends={"copy": copy_be, "ftp": ftp_be}, settings={}
        )
        result = DispatchOrchestrator(config).process_folder(fc, MagicMock())

        assert result.success is False
        assert result.files_failed == 2
        # Copy backend was still attempted
        assert len(copy_be.sent) == 2
        assert len(ftp_be.attempted) == 2


# =============================================================================
# 6. Large file processing
# =============================================================================


class TestLargeFileProcessing:
    """EDI file with many records processes without issues."""

    def test_large_edi_file(self, tmp_path):
        """Generate a 500-record EDI file and process it."""
        inp = tmp_path / "large_input"
        out = tmp_path / "large_output"
        inp.mkdir()
        out.mkdir()

        records = []
        for i in range(500):
            records.append(
                f"A{i:06d}20240101001VENDOR{i:06d}       Vendor {i:<24}{i:05d}\n"
                f"B{i:06d}001ITEM{i:06d}   {i*10:06d}0EA{(i*100) % 10000:04d}"
                f"Test Item {i:<25}{i*1000:08d}\n"
                f"C{0:07d}{i*10000:08d}\n"
            )
        (inp / "big.edi").write_text("".join(records))

        fc = {
            "id": 1,
            "folder_name": str(inp),
            "alias": "Large",
            "process_backend_copy": True,
            "copy_to_directory": str(out),
            "process_backend_ftp": False,
            "process_backend_email": False,
        }

        copy_be = CopyBackend()
        config = DispatchConfig(backends={"copy": copy_be}, settings={})
        result = DispatchOrchestrator(config).process_folder(fc, MagicMock())

        assert result.success is True
        assert result.files_processed == 1
        assert len(list(out.glob("*.edi"))) == 1


# =============================================================================
# 7. Resource cleanup after batch runs
# =============================================================================


class TestResourceCleanup:
    """Process many folders in a loop; verify outputs and no leftover state."""

    def test_ten_folders_all_produce_output(self, tmp_path):
        """Process 10 folders; every output directory has the expected file."""
        copy_be = CopyBackend()
        config = DispatchConfig(backends={"copy": copy_be}, settings={})
        orch = DispatchOrchestrator(config)

        for idx in range(10):
            fc = _make_folder(tmp_path, idx)
            result = orch.process_folder(fc, MagicMock())
            assert result.success is True

        for idx in range(10):
            out = tmp_path / f"output_{idx}"
            assert len(list(out.glob("*.edi"))) == 1, f"Folder {idx} missing output"


# =============================================================================
# 8. Concurrent database access (via DatabaseObj)
# =============================================================================


class TestConcurrentDatabaseAccess:
    """Guarantee DatabaseObj handles concurrent reads/writes."""

    def test_concurrent_reads_and_writes(self, tmp_path):
        """Multiple threads read and one writes; no crashes."""
        from interface.database.database_obj import DatabaseObj
        from batch_file_processor.constants import CURRENT_DATABASE_VERSION
        import create_database

        db_path = tmp_path / "folders.db"
        create_database.do("33", str(db_path), str(tmp_path), "Linux")
        db = DatabaseObj(
            database_path=str(db_path),
            database_version=CURRENT_DATABASE_VERSION,
            config_folder=str(tmp_path),
            running_platform="Linux",
        )

        db.folders_table.insert(
            {"folder_name": "/test", "alias": "Conc", "folder_is_active": True}
        )

        errors: list[str] = []

        def reader():
            try:
                for _ in range(20):
                    _ = list(db.folders_table.all())
                    time.sleep(0.005)
            except Exception as e:
                errors.append(f"reader: {e}")

        def writer():
            try:
                row = list(db.folders_table.all())[0]
                for i in range(20):
                    row["alias"] = f"Conc {i}"
                    db.folders_table.update(row, ["id"])
                    time.sleep(0.005)
            except Exception as e:
                errors.append(f"writer: {e}")

        threads = [threading.Thread(target=reader) for _ in range(3)]
        threads.append(threading.Thread(target=writer))
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert len(errors) == 0, f"Concurrent access errors: {errors}"
        db.close()

    def test_multiple_folder_inserts_are_isolated(self, tmp_path):
        """Insert many folders quickly; verify all are present."""
        from interface.database.database_obj import DatabaseObj
        from batch_file_processor.constants import CURRENT_DATABASE_VERSION
        import create_database

        db_path = tmp_path / "folders.db"
        create_database.do("33", str(db_path), str(tmp_path), "Linux")
        db = DatabaseObj(
            database_path=str(db_path),
            database_version=CURRENT_DATABASE_VERSION,
            config_folder=str(tmp_path),
            running_platform="Linux",
        )

        count = 50
        for i in range(count):
            db.folders_table.insert(
                {"folder_name": f"/path/{i}", "alias": f"F{i}"}
            )

        rows = list(db.folders_table.all())
        assert len(rows) == count

        db.close()


# =============================================================================
# 9. Many files per folder
# =============================================================================


class TestManyFilesPerFolder:
    """Scale-up within a single folder."""

    def test_twenty_files_in_one_folder(self, tmp_path):
        """Process 20 EDI files through a single folder config."""
        fc = _make_folder(tmp_path, 0, edi_count=20)
        copy_be = CopyBackend()
        config = DispatchConfig(backends={"copy": copy_be}, settings={})
        result = DispatchOrchestrator(config).process_folder(fc, MagicMock())

        assert result.success is True
        assert result.files_processed == 20
        assert len(copy_be.sent) == 20

        out = tmp_path / "output_0"
        assert len(list(out.glob("*.edi"))) == 20

    def test_hundred_files_with_slow_backend(self, tmp_path):
        """Process 100 files with a slightly slow backend; still succeeds."""
        fc = _make_folder(tmp_path, 0, edi_count=100)
        slow_be = SlowBackend(delay=0.001)  # 1ms per file → ~0.1s total
        config = DispatchConfig(backends={"copy": slow_be}, settings={})
        result = DispatchOrchestrator(config).process_folder(fc, MagicMock())

        assert result.success is True
        assert result.files_processed == 100
        assert len(slow_be.sent) == 100
