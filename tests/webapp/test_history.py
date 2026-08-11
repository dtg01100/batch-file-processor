"""Tests for the webapp run-history persistence."""

from __future__ import annotations

import datetime

import pytest

from webapp.config import Settings
from webapp.history import MAX_HISTORY_ROWS, RunHistory
from webapp.runner import FolderRunReport, RunReport

pytestmark = [pytest.mark.integration]


@pytest.fixture
def history(tmp_path):
    s = Settings(base_dir=tmp_path / "data", data_dir=tmp_path / "data" / "config")
    s.ensure_dirs()
    return RunHistory(s)


def _make_report(run_id: str, *, status: str = "completed") -> RunReport:
    return RunReport(
        run_id=run_id,
        status=status,
        started_at=datetime.datetime.now().isoformat(),
        finished_at=datetime.datetime.now().isoformat(),
        total_processed=5,
        total_failed=1,
        folders=[
            FolderRunReport(
                alias="test",
                relative_path="inbox/test",
                resolved_path="/data/inbox/test",
                files_processed=5,
                files_failed=1,
                success=(status != "failed"),
                run_log="line one\nline two\n",
            )
        ],
    )


def test_append_creates_table_and_persists_run(history):
    history.append(_make_report("abc"), kind="normal")
    found = history.get("abc")
    assert found is not None
    assert found.run_id == "abc"
    assert found.total_processed == 5
    assert len(found.folders) == 1


def test_recent_returns_newest_first(history):
    history.append(_make_report("aaa"), kind="normal")
    history.append(_make_report("bbb"), kind="normal")
    history.append(_make_report("ccc"), kind="normal")
    recent = history.recent(limit=10)
    assert [r.run_id for r in recent] == ["ccc", "bbb", "aaa"]


def test_recent_respects_limit(history):
    for i in range(5):
        history.append(_make_report(f"r{i}"), kind="normal")
    recent = history.recent(limit=2)
    assert len(recent) == 2


def test_get_returns_none_for_unknown(history):
    assert history.get("nope") is None


def test_append_trims_to_max_history_rows(history):
    for i in range(MAX_HISTORY_ROWS + 5):
        history.append(_make_report(f"r{i:03d}"), kind="normal")
    recent = history.recent(limit=MAX_HISTORY_ROWS + 10)
    # Exactly MAX_HISTORY_ROWS kept; the oldest five got pruned.
    assert len(recent) == MAX_HISTORY_ROWS
    # The most recent runs are the ones we kept.
    ids = [r.run_id for r in recent]
    assert ids[0] == f"r{MAX_HISTORY_ROWS + 4:03d}"


def test_append_overwrites_existing_run_id(history):
    """Re-running the same run-id should update, not duplicate."""
    report = _make_report("dup")
    history.append(report, kind="normal")
    report.total_processed = 99
    history.append(report, kind="normal")
    found = history.get("dup")
    assert found is not None
    assert found.total_processed == 99
    assert len(history.recent(limit=10)) == 1


def test_history_tolerates_a_failing_open_database(tmp_path, monkeypatch):
    """When ``open_database`` itself raises, ``append`` swallows it."""
    from webapp import history as history_module

    def boom(_settings):
        raise RuntimeError("db unavailable")

    monkeypatch.setattr(history_module, "open_database", boom)
    s = Settings(base_dir=tmp_path / "data", data_dir=tmp_path / "data" / "config")
    s.ensure_dirs()
    hist = RunHistory(s)
    # Must not propagate.
    hist.append(_make_report("x"), kind="normal")


def test_history_survives_a_fresh_object_against_the_same_db(tmp_path):
    """Restart-safety: a second RunHistory sees the first's rows."""
    s = Settings(base_dir=tmp_path / "data", data_dir=tmp_path / "data" / "config")
    s.ensure_dirs()
    h1 = RunHistory(s)
    h1.append(_make_report("first"), kind="normal")
    h2 = RunHistory(s)
    assert h2.get("first") is not None
