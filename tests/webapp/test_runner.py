"""Integration tests for webapp.runner (end-to-end dispatch via the webapp)."""

import contextlib
from pathlib import Path

import pytest

from webapp.config import Settings
from webapp.database import open_database
from webapp.runner import _folder_warning, run_folders

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


def _insert_folder(
    db,
    folder_name: str,
    *,
    copy_to_directory: str | None = None,
    max_duration_seconds: str | None = None,
    max_failure_rate_percent: str | None = None,
):
    row = {
        "folder_name": folder_name,
        "folder_is_active": "True",
        "alias": "inbox",
        "process_backend_copy": bool(copy_to_directory),
        "copy_to_directory": copy_to_directory or "",
        "process_backend_ftp": False,
        "process_backend_email": False,
    }
    if max_duration_seconds is not None:
        row["max_duration_seconds"] = max_duration_seconds
    if max_failure_rate_percent is not None:
        row["max_failure_rate_percent"] = max_failure_rate_percent
    db.folders_table.insert(row)


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
    # Per-folder timing is recorded too; no thresholds configured → no warning.
    assert report.folders[0].duration_seconds > 0
    assert report.folders[0].warning == ""


# ---------------------------------------------------------------------------
# Phase 5.3 follow-up: per-folder run-warning thresholds
# ---------------------------------------------------------------------------


def test_folder_warning_flags_exceeded_thresholds():
    row = {"max_duration_seconds": "60", "max_failure_rate_percent": "10"}
    # Duration over, rate under.
    assert (
        _folder_warning(row, duration_seconds=95, files_processed=10, files_failed=1)
        == "took 95.0s (limit 60s)"
    )
    # Rate over.
    out = _folder_warning(row, duration_seconds=30, files_processed=8, files_failed=2)
    assert out == "failure rate 20.0% (limit 10%)"
    # Both over — joined.
    out = _folder_warning(row, duration_seconds=95, files_processed=8, files_failed=2)
    assert out == "took 95.0s (limit 60s); failure rate 20.0% (limit 10%)"
    # Within limits — no warning.
    assert (
        _folder_warning(row, duration_seconds=30, files_processed=10, files_failed=0)
        == ""
    )
    # Rate exactly at the limit is not a warning.
    assert (
        _folder_warning(
            {"max_failure_rate_percent": "50"},
            duration_seconds=1,
            files_processed=1,
            files_failed=1,
        )
        == ""
    )


def test_folder_warning_no_thresholds_or_bad_values():
    # No thresholds configured → nothing to compare against.
    assert (
        _folder_warning({}, duration_seconds=9999, files_processed=0, files_failed=5)
        == ""
    )
    # Invalid / negative threshold values are treated as unset.
    bad = {"max_duration_seconds": "abc", "max_failure_rate_percent": "-5"}
    assert (
        _folder_warning(bad, duration_seconds=1, files_processed=0, files_failed=1)
        == ""
    )
    # No files at all → failure rate is 0, never warns.
    assert (
        _folder_warning(
            {"max_failure_rate_percent": "0.0001"},
            duration_seconds=1,
            files_processed=0,
            files_failed=0,
        )
        == ""
    )


def test_run_warns_when_folder_exceeds_failure_rate_threshold(workspace):
    """A missing folder fails every file — 100% failure rate > 10% limit."""
    settings = workspace
    db = open_database(settings)
    try:
        _insert_folder(db, "does-not-exist", max_failure_rate_percent="10")
    finally:
        with contextlib.suppress(Exception):
            db.close()

    report = run_folders(settings)
    folder = report.folders[0]
    assert folder.files_failed == 1
    assert folder.duration_seconds > 0
    assert folder.warning == "failure rate 100.0% (limit 10%)"


def test_run_uses_real_upc_lookup_when_as400_configured(workspace, monkeypatch):
    """AS400 credentials in the settings table reach the UPC lookup.

    Regression for the webapp gap: the runner used to pass a non-empty
    ``upc_dict={"_mock": []}`` that short-circuited the orchestrator's
    UPC lookup entirely, so converters silently degraded (no UPC data)
    even when real AS400 credentials were configured. With an empty
    dict, the orchestrator's ``UPCLookupService`` actually runs; when
    the AS400 settings are set it fetches the dictionary.
    """
    import webapp.pipeline.services.upc_service as upc_service_module

    calls: list[dict] = []

    def fake_get_dictionary(self, *args, **kwargs):
        # Record the settings the lookup sees (real AS400 creds from
        # the settings table) and return a canned dictionary.
        calls.append(dict(self.settings))
        return {int("001002003004"): ["Product A"]}

    monkeypatch.setattr(
        upc_service_module.UPCLookupService, "get_dictionary", fake_get_dictionary
    )

    settings = workspace
    db = open_database(settings)
    try:
        _insert_folder(db, "input", copy_to_directory="output")
        # Configure AS400 credentials the way the Settings card does.
        db.settings.update(
            {
                "id": 1,
                "as400_address": "10.0.0.7",
                "as400_username": "edi_user",
                "as400_password": "pw",
                "ssh_key_filename": "",
            },
            ["id"],
        )
    finally:
        with contextlib.suppress(Exception):
            db.close()

    report = run_folders(settings)

    assert report.status == "completed"
    assert report.total_processed == 2
    # The lookup actually ran (was not short-circuited by a mock dict).
    assert len(calls) == 1
    assert calls[0]["as400_address"] == "10.0.0.7"
    assert calls[0]["as400_username"] == "edi_user"


def test_run_without_as400_creds_still_succeeds(workspace, monkeypatch):
    """No AS400 credentials → empty UPC dict, run still completes.

    The orchestrator's lookup fails fast on missing credentials
    (non-strict mode) and returns ``{}``; files must still process.
    """
    import webapp.pipeline.services.upc_service as upc_service_module

    def fake_get_dictionary(self, *args, **kwargs):
        # Mirrors the real service: missing creds -> no query -> {}.
        assert not self.settings.get("as400_address")
        return {}

    monkeypatch.setattr(
        upc_service_module.UPCLookupService, "get_dictionary", fake_get_dictionary
    )

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
    assert report.total_failed == 0


def test_run_merges_plugin_config_into_converter(workspace):
    """Per-format plugin_configurations reach the converter at run time.

    Regression for the webapp gap: plugin_configurations was schema-only
    (no UI, nothing consumed it). The runner now merges the config for
    the folder's convert_to_format into the folder dict, so e.g. the
    tweaks converter's force_txt_file_ext setting takes effect and the
    output is written with a .txt extension.
    """
    settings = workspace
    inbox = settings.base_dir / "input"  # created by the workspace fixture
    # Drop the fixture's non-EDI samples so only conv.edi runs.
    for stale in inbox.glob("sample_*.txt"):
        stale.unlink()
    b_record = (
        "B"
        + "ABCDEFGHIJK"
        + ("Test Item Description    1234560001000100000100010991001000000")
    )
    b_record = b_record.ljust(76)
    (inbox / "conv.edi").write_text(
        "AVENDOR00000000010101250000100000\n"
        f"{b_record}\n"
        "CTABSales Tax                 000010000\n",
        encoding="utf-8",
    )

    db = open_database(settings)
    try:
        db.folders_table.insert(
            {
                "folder_name": "input",
                "folder_is_active": "True",
                "alias": "conv",
                "process_edi": True,
                "convert_to_format": "tweaks",
                "process_backend_copy": True,
                "copy_to_directory": "out",
                "process_backend_ftp": False,
                "process_backend_email": False,
                "plugin_configurations": {"tweaks": {"force_txt_file_ext": True}},
            }
        )
    finally:
        with contextlib.suppress(Exception):
            db.close()

    report = run_folders(settings)
    assert report.status == "completed"
    assert report.total_processed == 1, report
    assert report.total_failed == 0
    out = settings.base_dir / "out"
    # force_txt_file_ext merged from plugin_configurations → .txt output.
    assert list(out.glob("*.txt")), f"expected .txt output in {out}"


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

    # The worker runs run_folders() which does SQLite I/O on a
    # tmp_path database; under xdist with other tests writing their
    # own tmp_path DBs, this can exceed 5 seconds. Use a 30-second
    # deadline via the production helper (rather than a hardcoded
    # polling loop in the test) so the lifecycle contract is
    # exercised regardless of I/O contention.
    assert store.wait_until_idle(timeout=30.0)
