"""Integration tests for webapp.runner (end-to-end dispatch via the webapp)."""

import contextlib
from pathlib import Path

import pytest

from webapp.config import Settings
from webapp.database import open_database
from webapp.runner import run_folders

pytestmark = [pytest.mark.integration]


@pytest.fixture
def workspace(tmp_path):
    """A base-dir with an input folder of sample files and a config dir."""
    base = tmp_path / "data"
    input_dir = base / "input"
    input_dir.mkdir(parents=True)
    (input_dir / "sample_001.txt").write_text("hello 001\n", encoding="utf-8")
    (input_dir / "sample_002.txt").write_text("hello 002\n", encoding="utf-8")
    settings = Settings(base_dir=base, data_dir=base / "config")
    return settings


def _insert_folder(db, folder_name: str, *, copy_to_directory: str | None = None):
    db.folders_table.insert(
        {
            "folder_name": folder_name,
            "folder_is_active": "True",
            "alias": "inbox",
            "process_backend_copy": bool(copy_to_directory),
            "copy_to_directory": copy_to_directory or "",
            "process_backend_ftp": False,
            "process_backend_email": False,
        }
    )


def test_run_processes_files_and_records_processed(workspace):
    settings = workspace
    db = open_database(settings)
    try:
        _insert_folder(
            db,
            "input",  # relative to the base-dir
            copy_to_directory="output",
        )
    finally:
        with contextlib.suppress(Exception):
            db.close()

    report = run_folders(settings)

    assert report.status == "completed"
    assert report.total_processed == 2
    assert report.total_failed == 0
    assert len(report.folders) == 1
    folder = report.folders[0]
    assert folder.alias == "inbox"
    assert folder.relative_path == "input"
    assert folder.resolved_path == str(settings.base_dir / "input")
    assert folder.success

    # Copy backend ran: outputs exist under the base-dir.
    output_dir = settings.base_dir / "output"
    assert (output_dir / "sample_001.txt").is_file()
    assert (output_dir / "sample_002.txt").is_file()

    # Processed files were recorded in the database. The pipeline records
    # the (resolved, absolute) file path — same behaviour as the desktop
    # app; dedup is checksum-based.
    db = open_database(settings)
    try:
        rows = list(db.processed_files.all())
        assert len(rows) == 2
        names = {Path(r.get("file_name")).name for r in rows}
        assert names == {"sample_001.txt", "sample_002.txt"}
    finally:
        with contextlib.suppress(Exception):
            db.close()


def test_run_skips_inactive_folders(workspace):
    settings = workspace
    db = open_database(settings)
    try:
        db.folders_table.insert(
            {
                "folder_name": "input",
                "folder_is_active": "False",
                "alias": "disabled",
            }
        )
    finally:
        with contextlib.suppress(Exception):
            db.close()

    report = run_folders(settings)
    assert report.status == "completed"
    assert report.folders == []
    assert report.total_processed == 0


def test_run_reports_missing_folder_as_failure(workspace):
    settings = workspace
    db = open_database(settings)
    try:
        _insert_folder(db, "does-not-exist")
    finally:
        with contextlib.suppress(Exception):
            db.close()

    report = run_folders(settings)
    assert report.status == "completed"
    assert len(report.folders) == 1
    folder = report.folders[0]
    assert not folder.success
    assert folder.files_failed == 1
    # Phase 5.3: even a failed run gets a duration stamp (0 throughput).
    assert report.duration_seconds >= 0
    assert report.files_per_second == 0


def test_run_report_duration_metrics(workspace):
    """Phase 5.3: completed runs carry duration + throughput."""
    settings = workspace
    db = open_database(settings)
    try:
        _insert_folder(db, "input", copy_to_directory="output")
    finally:
        with contextlib.suppress(Exception):
            db.close()

    report = run_folders(settings)

    assert report.status == "completed"
    assert report.total_processed == 2
    assert report.started_at
    assert report.finished_at >= report.started_at
    # Two files through a real pipeline take well over a microsecond.
    assert report.duration_seconds > 0
    assert report.duration_seconds < 60  # sanity bound
    assert report.files_per_second == pytest.approx(
        report.total_processed / report.duration_seconds
    )
    assert report.files_per_second > 0


def test_run_store_refuses_second_concurrent_run(workspace):
    """A second ``start()`` while a previous run is in flight raises."""
    from webapp.runner import RunStore

    store = RunStore()

    # First start succeeds and increments the active counter.
    store.start(workspace)
    assert store.active_count == 1

    # Second start is rejected; counter is unchanged.
    with pytest.raises(RuntimeError, match="already in progress"):
        store.start(workspace)
    assert store.active_count == 1


def test_run_store_active_count_drops_after_run_completes(workspace):
    """A successful run leaves the active counter at zero."""
    from webapp.runner import RunStore

    store = RunStore()
    store.start(workspace)

    # Wait for the worker to finish; 5s is generous for an empty folder.
    import time

    deadline = time.monotonic() + 5.0
    while store.active_count > 0 and time.monotonic() < deadline:
        time.sleep(0.05)
    assert store.active_count == 0
