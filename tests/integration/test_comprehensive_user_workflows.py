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

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.e2e, pytest.mark.workflow]


# -----------------------------------------------------------------------------
# Shared helpers / fixtures
# -----------------------------------------------------------------------------

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
