"""Integration tests for batch workflow orchestration.

Tests the DispatchOrchestrator end-to-end with MockBackend, covering:
- Single/multi-file folder processing
- Multi-folder processing
- Checksum-based deduplication
- Error recording
- No-backends edge case
- process_file() single-file mode
"""

import hashlib
import os
from io import BytesIO
from typing import Any, Dict, List, Optional

import pytest

from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator
from dispatch.send_manager import MockBackend

pytestmark = [pytest.mark.integration, pytest.mark.dispatch]

# ---------------------------------------------------------------------------
# In-memory processed-files database
# ---------------------------------------------------------------------------


class InMemoryProcessedFiles:
    """Simple in-memory implementation of the DatabaseInterface for processed files.

    Stores records as plain dicts and supports the find/find_one/insert/update
    operations required by DispatchOrchestrator._filter_processed_files() and
    DispatchOrchestrator._record_processed_file().
    """

    def __init__(self):
        self.records: List[Dict[str, Any]] = []

    def find(self, folder_id: Optional[int] = None, **kwargs) -> List[Dict[str, Any]]:
        """Return records matching *folder_id* (and any extra kwargs)."""
        result = self.records
        if folder_id is not None:
            result = [r for r in result if r.get("folder_id") == folder_id]
        for key, value in kwargs.items():
            result = [r for r in result if r.get(key) == value]
        return result

    def find_one(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Return the first record where all kwargs match, or None."""
        for r in self.records:
            if all(r.get(k) == v for k, v in kwargs.items()):
                return r
        return None

    def insert(self, record: Dict[str, Any]) -> None:
        """Insert a new record, assigning an auto-increment id."""
        record = dict(record)
        record["id"] = len(self.records) + 1
        self.records.append(record)

    def insert_many(self, records: List[Dict[str, Any]]) -> None:
        """Insert a batch of records."""
        for r in records:
            self.insert(r)

    def update(self, record: Dict[str, Any], keys: List[str]) -> None:
        """Update the first record whose key fields match *record*."""
        for r in self.records:
            if all(r.get(k) == record.get(k) for k in keys):
                r.update(record)
                return

    def count(self, **kwargs) -> int:
        return len(self.find(**kwargs))

    def query(self, sql: str) -> Any:
        return []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_file(folder: str, name: str, content: bytes) -> str:
    """Write *content* to *folder/name* and return the absolute path."""
    path = os.path.join(folder, name)
    with open(path, "wb") as fh:
        fh.write(content)
    return path


def _md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def _build_orchestrator(
    mock_backend: Optional[MockBackend] = None,
    fail_backend: bool = False,
    no_backends: bool = False,
) -> tuple:
    """
    Build a (DispatchOrchestrator, MockBackend) pair.

    Args:
        mock_backend: Pre-built MockBackend to reuse (creates a new one if None).
        fail_backend: If True, injects a backend that always raises on send().
        no_backends: If True, creates an orchestrator with no backends injected.

    Returns:
        (orchestrator, backend) -- backend is the MockBackend or None.
    """
    if no_backends:
        config = DispatchConfig(settings={})
        return DispatchOrchestrator(config), None

    if fail_backend:

        class _FailingBackend:
            def send(self, params, settings, filename):
                raise RuntimeError("Simulated send failure")

            def validate(self, params):
                return []

            def get_name(self):
                return "FailBackend"

        config = DispatchConfig(settings={}, backends={"fail": _FailingBackend()})
        return DispatchOrchestrator(config), None

    backend = mock_backend or MockBackend(should_succeed=True)
    config = DispatchConfig(settings={}, backends={"mock": backend})
    return DispatchOrchestrator(config), backend


def _folder_cfg(path: str, folder_id: int = 1, alias: str = "test_folder") -> dict:
    return {"folder_name": path, "alias": alias, "id": folder_id}


# ---------------------------------------------------------------------------
# Batch workflow tests
# ---------------------------------------------------------------------------


class TestSingleFolderWorkflows:
    """Tests for processing a single folder with the DispatchOrchestrator."""

    def test_single_folder_single_file_workflow(self, tmp_path):
        """Process one folder containing one file; verify exactly 1 backend send call."""
        orch, backend = _build_orchestrator()
        folder = str(tmp_path / "inbox")
        os.makedirs(folder)
        _make_file(folder, "invoice.txt", b"Invoice data")

        result = orch.process_folder(_folder_cfg(folder), BytesIO())

        assert result.success is True
        assert result.files_processed == 1
        assert result.files_failed == 0
        assert result.errors == []
        assert len(backend.send_calls) == 1

    def test_single_folder_multi_file_workflow(self, tmp_path):
        """Process one folder with 5 files; verify 5 send calls on the backend."""
        orch, backend = _build_orchestrator()
        folder = str(tmp_path / "batch")
        os.makedirs(folder)
        for i in range(5):
            _make_file(folder, f"file_{i}.txt", f"content {i}".encode())

        result = orch.process_folder(_folder_cfg(folder), BytesIO())

        assert result.success is True
        assert result.files_processed == 5
        assert len(backend.send_calls) == 5

    def test_empty_folder_workflow(self, tmp_path):
        """Process an empty folder; verify 0 send calls and success=True."""
        orch, backend = _build_orchestrator()
        folder = str(tmp_path / "empty")
        os.makedirs(folder)

        result = orch.process_folder(_folder_cfg(folder), BytesIO())

        assert result.success is True
        assert result.files_processed == 0
        assert result.files_failed == 0
        assert len(backend.send_calls) == 0

    def test_folder_not_found_workflow(self, tmp_path):
        """Process a non-existent folder; verify FolderResult.success=False and error recorded."""
        orch, backend = _build_orchestrator()
        nonexistent = str(tmp_path / "does_not_exist")

        result = orch.process_folder(_folder_cfg(nonexistent), BytesIO())

        assert result.success is False
        assert any("not found" in e.lower() or "Folder" in e for e in result.errors)

    def test_backend_failure_recorded_in_result(self, tmp_path):
        """When the backend raises, FolderResult.errors must be non-empty and success=False."""
        orch, _ = _build_orchestrator(fail_backend=True)
        folder = str(tmp_path / "fail_folder")
        os.makedirs(folder)
        _make_file(folder, "data.txt", b"will fail")

        result = orch.process_folder(_folder_cfg(folder), BytesIO())

        assert result.success is False
        assert result.files_failed >= 1
        assert len(result.errors) > 0

    def test_no_backends_enabled(self, tmp_path):
        """Folder config with no backends should produce errors containing 'No backends enabled'."""
        # Use an orchestrator with no backends and explicitly disable all default backends
        config = DispatchConfig(settings={})
        orch = DispatchOrchestrator(config)
        folder = str(tmp_path / "no_backends")
        os.makedirs(folder)
        _make_file(folder, "x.txt", b"data")

        folder_cfg = {
            "folder_name": folder,
            "alias": "no_backends",
            "id": 1,
            "process_backend_ftp": False,
            "process_backend_email": False,
            "process_backend_copy": False,
        }

        result = orch.process_folder(folder_cfg, BytesIO())

        assert result.success is False
        assert any("No backends enabled" in e for e in result.errors)


class TestMultiFolderWorkflows:
    """Tests for processing multiple folders in sequence."""

    def test_multi_folder_workflow(self, tmp_path):
        """Process 3 folders with 2 files each; verify 6 total backend send calls."""
        orch, backend = _build_orchestrator()
        total_sends = 0
        for folder_idx in range(3):
            folder = str(tmp_path / f"folder_{folder_idx}")
            os.makedirs(folder)
            for file_idx in range(2):
                _make_file(
                    folder,
                    f"f{file_idx}.txt",
                    f"folder{folder_idx}_file{file_idx}".encode(),
                )

            result = orch.process_folder(
                _folder_cfg(folder, folder_id=folder_idx + 1), BytesIO()
            )
            assert result.success is True
            assert result.files_processed == 2
            total_sends += result.files_processed

        assert total_sends == 6
        assert len(backend.send_calls) == 6

    def test_automatic_mode_multiple_folders(self, tmp_path):
        """Simulate automatic dispatch over multiple active folders; each sends independently."""
        backend = MockBackend(should_succeed=True)
        config = DispatchConfig(settings={}, backends={"mock": backend})
        orch = DispatchOrchestrator(config)

        run_log = BytesIO()
        folder_results = []
        for i in range(4):
            folder_path = str(tmp_path / f"auto_folder_{i}")
            os.makedirs(folder_path)
            for j in range(3):
                _make_file(
                    folder_path, f"doc_{j}.txt", f"auto content {i}-{j}".encode()
                )

            folder_cfg = {"folder_name": folder_path, "alias": f"auto_{i}", "id": i + 1}
            folder_results.append(orch.process_folder(folder_cfg, run_log))

        assert all(r.success for r in folder_results)
        assert sum(r.files_processed for r in folder_results) == 12
        assert len(backend.send_calls) == 12

    def test_multi_folder_with_mixed_results(self, tmp_path):
        """One folder with files, one empty, one non-existent -- verify each result individually."""
        backend = MockBackend(should_succeed=True)
        config = DispatchConfig(settings={}, backends={"mock": backend})
        orch = DispatchOrchestrator(config)

        # Folder 1: 2 files
        folder1 = str(tmp_path / "f1")
        os.makedirs(folder1)
        _make_file(folder1, "a.txt", b"aaa")
        _make_file(folder1, "b.txt", b"bbb")

        # Folder 2: empty
        folder2 = str(tmp_path / "f2_empty")
        os.makedirs(folder2)

        # Folder 3: non-existent
        folder3 = str(tmp_path / "f3_missing")

        r1 = orch.process_folder(_folder_cfg(folder1, 1, "f1"), BytesIO())
        r2 = orch.process_folder(_folder_cfg(folder2, 2, "f2"), BytesIO())
        r3 = orch.process_folder(_folder_cfg(folder3, 3, "f3"), BytesIO())

        assert r1.success is True
        assert r1.files_processed == 2
        assert r2.success is True
        assert r2.files_processed == 0
        assert r3.success is False
        assert len(backend.send_calls) == 2


class TestDeduplication:
    """Tests for checksum-based deduplication via InMemoryProcessedFiles."""

    def test_already_processed_file_skipped(self, tmp_path):
        """A file whose checksum is already in the DB must not be sent again."""
        backend = MockBackend(should_succeed=True)
        config = DispatchConfig(settings={}, backends={"mock": backend})
        orch = DispatchOrchestrator(config)

        folder = str(tmp_path / "dedup")
        os.makedirs(folder)
        filepath = _make_file(folder, "report.txt", b"static content")

        db = InMemoryProcessedFiles()
        folder_cfg = {"folder_name": folder, "alias": "dedup", "id": 1}

        # First run -- should send
        result1 = orch.process_folder(folder_cfg, BytesIO(), processed_files=db)
        assert result1.files_processed == 1
        assert len(backend.send_calls) == 1

        # Second run with same DB -- should skip
        orch2 = DispatchOrchestrator(config)
        result2 = orch2.process_folder(folder_cfg, BytesIO(), processed_files=db)
        assert result2.files_processed == 0
        assert len(backend.send_calls) == 1  # no new calls

    def test_new_file_after_previous_processed(self, tmp_path):
        """Adding a new file after the first run means only the new file is sent."""
        backend = MockBackend(should_succeed=True)
        config = DispatchConfig(settings={}, backends={"mock": backend})

        folder = str(tmp_path / "incremental")
        os.makedirs(folder)
        _make_file(folder, "old.txt", b"existing file content")

        db = InMemoryProcessedFiles()
        folder_cfg = {"folder_name": folder, "alias": "incremental", "id": 1}

        # Run 1 -- processes the old file
        orch1 = DispatchOrchestrator(config)
        result1 = orch1.process_folder(folder_cfg, BytesIO(), processed_files=db)
        assert result1.files_processed == 1

        # Add a new file
        _make_file(folder, "new.txt", b"brand new content")

        # Run 2 -- only the new file should be processed
        orch2 = DispatchOrchestrator(config)
        result2 = orch2.process_folder(folder_cfg, BytesIO(), processed_files=db)
        assert result2.files_processed == 1

        # Total across both runs
        assert len(backend.send_calls) == 2
        # Last send is the new file
        _, _, last_fn = backend.send_calls[-1]
        assert "new.txt" in os.path.basename(last_fn)

    def test_duplicate_content_different_names_both_sent_then_deduplicated(
        self, tmp_path
    ):
        """Two files with identical content in same folder are both sent on first run; on re-run both are skipped."""
        backend = MockBackend(should_succeed=True)
        config = DispatchConfig(settings={}, backends={"mock": backend})

        folder = str(tmp_path / "twin")
        os.makedirs(folder)
        identical_content = b"exactly the same bytes"
        _make_file(folder, "twin_a.txt", identical_content)
        _make_file(folder, "twin_b.txt", identical_content)

        db = InMemoryProcessedFiles()
        folder_cfg = {"folder_name": folder, "alias": "twin", "id": 1}

        # Run 1 -- first file records checksum, second is filtered
        orch1 = DispatchOrchestrator(config)
        result1 = orch1.process_folder(folder_cfg, BytesIO(), processed_files=db)
        # At least one should be sent; the second may be skipped after the first
        # records its checksum mid-run (implementation detail), so just check ≥1
        assert result1.files_processed >= 1

        # Run 2 -- nothing new
        orch2 = DispatchOrchestrator(config)
        result2 = orch2.process_folder(folder_cfg, BytesIO(), processed_files=db)
        assert result2.files_processed == 0

    def test_modified_file_with_different_content_is_resent(self, tmp_path):
        """After overwriting a file with different bytes, the checksum changes and the file is sent again."""
        backend = MockBackend(should_succeed=True)
        config = DispatchConfig(settings={}, backends={"mock": backend})

        folder = str(tmp_path / "modified")
        os.makedirs(folder)
        filepath = _make_file(folder, "changing.txt", b"version 1")

        db = InMemoryProcessedFiles()
        folder_cfg = {"folder_name": folder, "alias": "modified", "id": 1}

        orch1 = DispatchOrchestrator(config)
        result1 = orch1.process_folder(folder_cfg, BytesIO(), processed_files=db)
        assert result1.files_processed == 1

        # Overwrite with new content (new checksum)
        with open(filepath, "wb") as fh:
            fh.write(b"version 2 - different content")

        orch2 = DispatchOrchestrator(config)
        result2 = orch2.process_folder(folder_cfg, BytesIO(), processed_files=db)
        assert result2.files_processed == 1

        assert len(backend.send_calls) == 2


class TestSingleFileMode:
    """Tests for process_file() -- direct single-file processing."""

    def test_single_mode_single_file(self, tmp_path):
        """process_file() on a specific file produces FileResult.sent=True and 1 send call."""
        orch, backend = _build_orchestrator()
        folder = str(tmp_path / "single_mode")
        os.makedirs(folder)
        filepath = _make_file(folder, "invoice.edi", b"EDI invoice content")
        folder_cfg = _folder_cfg(folder)

        file_result = orch.process_file(filepath, folder_cfg)

        assert file_result.sent is True
        assert file_result.checksum != ""
        assert file_result.errors == []
        assert len(backend.send_calls) == 1
        _, _, sent_fn = backend.send_calls[0]
        assert sent_fn == filepath

    def test_single_mode_records_checksum(self, tmp_path):
        """FileResult.checksum matches the MD5 of the file content."""
        orch, backend = _build_orchestrator()
        content = b"checksum verification data"
        folder = str(tmp_path / "checksum_test")
        os.makedirs(folder)
        filepath = _make_file(folder, "check.dat", content)

        file_result = orch.process_file(filepath, _folder_cfg(folder))

        assert file_result.checksum == _md5(content)

    def test_single_mode_binary_file(self, tmp_path):
        """process_file() handles binary files correctly."""
        orch, backend = _build_orchestrator()
        content = bytes(range(256)) * 2
        folder = str(tmp_path / "binary_single")
        os.makedirs(folder)
        filepath = _make_file(folder, "binary.bin", content)

        file_result = orch.process_file(filepath, _folder_cfg(folder))

        assert file_result.sent is True
        assert file_result.checksum == _md5(content)

    def test_single_mode_failure_recorded(self, tmp_path):
        """When the backend fails in process_file(), FileResult.sent=False and errors non-empty."""
        orch, _ = _build_orchestrator(fail_backend=True)
        folder = str(tmp_path / "fail_single")
        os.makedirs(folder)
        filepath = _make_file(folder, "fail.txt", b"should fail")

        file_result = orch.process_file(filepath, _folder_cfg(folder))

        assert file_result.sent is False
        assert len(file_result.errors) > 0

    def test_single_mode_no_backends(self, tmp_path):
        """process_file() with no enabled backends results in FileResult.sent=False."""
        config = DispatchConfig(settings={})
        orch = DispatchOrchestrator(config)
        folder = str(tmp_path / "no_backends_single")
        os.makedirs(folder)
        filepath = _make_file(folder, "x.txt", b"data")
        folder_cfg = {
            "folder_name": folder,
            "alias": "nb",
            "id": 1,
            "process_backend_ftp": False,
            "process_backend_email": False,
            "process_backend_copy": False,
        }

        file_result = orch.process_file(filepath, folder_cfg)

        assert file_result.sent is False
        assert any("No backends enabled" in e for e in file_result.errors)


class TestOrchestratorResultTracking:
    """Tests for cumulative result tracking across multiple folder/file runs."""

    def test_processed_count_accumulates(self, tmp_path):
        """orchestrator.processed_count increases with each successful send."""
        backend = MockBackend(should_succeed=True)
        config = DispatchConfig(settings={}, backends={"mock": backend})
        orch = DispatchOrchestrator(config)

        for i in range(3):
            folder = str(tmp_path / f"acc_{i}")
            os.makedirs(folder)
            _make_file(folder, "f.txt", f"data {i}".encode())
            orch.process_folder(_folder_cfg(folder, i + 1), BytesIO())

        assert orch.processed_count == 3

    def test_error_count_accumulates(self, tmp_path):
        """orchestrator.error_count increases with each failed send."""
        orch, _ = _build_orchestrator(fail_backend=True)

        for i in range(2):
            folder = str(tmp_path / f"err_{i}")
            os.makedirs(folder)
            _make_file(folder, "f.txt", f"data {i}".encode())
            orch.process_folder(_folder_cfg(folder, i + 1), BytesIO())

        assert orch.error_count == 2

    def test_get_summary_reflects_counts(self, tmp_path):
        """get_summary() returns a non-empty string with the processed/error counts."""
        backend = MockBackend(should_succeed=True)
        config = DispatchConfig(settings={}, backends={"mock": backend})
        orch = DispatchOrchestrator(config)

        folder = str(tmp_path / "summary")
        os.makedirs(folder)
        _make_file(folder, "s.txt", b"summary test")
        orch.process_folder(_folder_cfg(folder), BytesIO())

        summary = orch.get_summary()
        assert isinstance(summary, str)
        assert len(summary) > 0
        # Should contain numeric info
        assert any(c.isdigit() for c in summary)

    def test_reset_clears_counters(self, tmp_path):
        """After reset(), processed_count and error_count return to 0."""
        backend = MockBackend(should_succeed=True)
        config = DispatchConfig(settings={}, backends={"mock": backend})
        orch = DispatchOrchestrator(config)

        folder = str(tmp_path / "reset_test")
        os.makedirs(folder)
        _make_file(folder, "r.txt", b"reset test data")
        orch.process_folder(_folder_cfg(folder), BytesIO())
        assert orch.processed_count == 1

        orch.reset()
        assert orch.processed_count == 0
        assert orch.error_count == 0

    def test_folder_result_alias_preserved(self, tmp_path):
        """FolderResult.alias matches the folder configuration alias."""
        orch, _ = _build_orchestrator()
        folder = str(tmp_path / "alias_test")
        os.makedirs(folder)
        _make_file(folder, "a.txt", b"alias content")
        folder_cfg = {"folder_name": folder, "alias": "My Special Alias", "id": 1}

        result = orch.process_folder(folder_cfg, BytesIO())

        assert result.alias == "My Special Alias"

    def test_folder_result_folder_name_preserved(self, tmp_path):
        """FolderResult.folder_name matches the folder configuration folder_name."""
        orch, _ = _build_orchestrator()
        folder = str(tmp_path / "name_test")
        os.makedirs(folder)
        _make_file(folder, "n.txt", b"name content")

        result = orch.process_folder(_folder_cfg(folder), BytesIO())

        assert result.folder_name == folder


class TestRunLogIntegration:
    """Tests verifying the run log receives messages during processing."""

    def test_run_log_receives_messages(self, tmp_path):
        """Run log BytesIO buffer is written to during folder processing."""
        orch, _ = _build_orchestrator()
        folder = str(tmp_path / "log_test")
        os.makedirs(folder)
        _make_file(folder, "log_file.txt", b"log content")

        run_log = BytesIO()
        orch.process_folder(_folder_cfg(folder), run_log)

        log_contents = run_log.getvalue()
        assert len(log_contents) > 0

    def test_run_log_records_success(self, tmp_path):
        """Run log includes the word 'Success' after a successful file send."""
        orch, _ = _build_orchestrator()
        folder = str(tmp_path / "success_log")
        os.makedirs(folder)
        _make_file(folder, "ok.txt", b"ok content")

        run_log = BytesIO()
        orch.process_folder(_folder_cfg(folder), run_log)

        log_text = run_log.getvalue().decode("utf-8", errors="replace")
        assert (
            "Success" in log_text
            or "success" in log_text.lower()
            or "ok.txt" in log_text
        )

    def test_run_log_records_folder_not_found(self, tmp_path):
        """Run log contains an error message when the folder is not found."""
        orch, _ = _build_orchestrator()
        missing_folder = str(tmp_path / "missing_xyz")

        run_log = BytesIO()
        orch.process_folder(_folder_cfg(missing_folder), run_log)

        log_text = run_log.getvalue().decode("utf-8", errors="replace")
        assert "ERROR" in log_text or "not found" in log_text.lower()
