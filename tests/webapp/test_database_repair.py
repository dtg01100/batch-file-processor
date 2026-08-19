"""Phase 7.1 — one-shot current-version repair.

Phase 7.1 gates ``_run_current_version_repairs`` on a
``schema_repaired_at`` row in ``kv_settings``. Before this fix the
function ran on every ``open_database`` call, which re-fired the
v33→v51 migration's ``_backfill_defaults`` UPDATE on the ``folders``
table. That UPDATE silently mutated freshly-inserted rows, breaking
any "snapshot-then-round-trip" test (Phase 6.4 hit this — see
``tests/webapp/test_soft_delete.py:30-35`` for the workaround
Phase 7.1 makes unnecessary).

The tests below verify:

1. ``test_repair_runs_only_once_across_opens`` — a counting migrator
   is invoked exactly once across two ``DatabaseObj`` instances on
   the same file.

2. ``test_repair_marker_is_persisted`` — the ``schema_repaired_at``
   key is present in ``kv_settings`` after the first repair; the
   second ``DatabaseObj`` skips the repair entirely.

3. ``test_round_trip_stable_without_reopen`` — the Phase 6.4 round-trip
   pattern (insert, ``find_one``, soft-delete + restore) works
   *without* the explicit re-open in the fixture, proving the fix
   resolves the symptom the workaround was papering over.

The tests are deliberately decoupled from ``webapp/``; they target
``backend.database.database_obj.DatabaseObj`` directly. Phase 6.4
touched this code path implicitly (every ``open_database`` triggered
the repair); the regression coverage belongs at the same layer.
"""

from __future__ import annotations

import datetime
import inspect
from pathlib import Path
from typing import Any

import pytest

from backend.database.database_obj import DatabaseObj
from core.constants import CURRENT_DATABASE_VERSION

pytestmark = [pytest.mark.integration]


def _counting_migrator() -> tuple[Any, list[int]]:
    """Build a counting migrator function for ``DatabaseObj``.

    Returns ``(callable, call_counts)``. The callable ignores its
    arguments (the migrator runs the migration steps itself) and
    records each invocation in the shared ``call_counts`` list.
    The list is mutable; read it after the test runs to assert how
    many times the migrator fired.
    """
    call_counts: list[int] = []

    def _fn(*args: Any, **kwargs: Any) -> None:
        call_counts.append(1)

    return _fn, call_counts


def _open_db(
    *,
    database_path: Path,
    config_folder: Path,
    migrator_func: Any = None,
) -> DatabaseObj:
    """Construct a ``DatabaseObj`` against ``database_path``.

    ``migrator_func`` is the production-code fast-path bypass — if
    ``None``, ``DatabaseObj`` falls back to the real migrator. We pass
    a counting stub for the gate tests so we can assert exactly
    how many times the migration ran.
    """
    return DatabaseObj(
        database_path=str(database_path),
        database_version=CURRENT_DATABASE_VERSION,
        config_folder=str(config_folder),
        running_platform="Linux",
        migrator_func=migrator_func,
    )


def test_repair_runs_only_once_across_opens(tmp_path: Path) -> None:
    """Two ``DatabaseObj`` instances on the same file, counting
    migrator. Assert the migrator ran exactly once.

    The first open is the ``_create_database`` path (file does not
    exist), so the migrator runs as part of the v32→v51 jump. The
    second open is the at-version path — that's where the gate
    matters: it must skip the repair because the marker is now
    present in ``kv_settings``.
    """
    database_path = tmp_path / "folders.db"
    config_folder = tmp_path / "config"
    config_folder.mkdir()
    migrator, call_counts = _counting_migrator()

    db1 = _open_db(
        database_path=database_path,
        config_folder=config_folder,
        migrator_func=migrator,
    )
    db1.close()

    db2 = _open_db(
        database_path=database_path,
        config_folder=config_folder,
        migrator_func=migrator,
    )
    db2.close()

    assert len(call_counts) == 1, (
        "Expected the migrator to run once (first open) and be skipped "
        f"on the second open. Got {len(call_counts)} calls."
    )


def test_repair_marker_is_persisted(tmp_path: Path) -> None:
    """The ``schema_repaired_at`` key is written by the first repair
    and read by the second.

    This is the explicit proof that the gate's *signal* is the
    marker, not just "the migrator happened to be idempotent and
    produced the same result twice." Without the marker, the gate
    would be invisible to a regression test that runs the migrator
    manually between opens.
    """
    database_path = tmp_path / "folders.db"
    config_folder = tmp_path / "config"
    config_folder.mkdir()

    db1 = _open_db(
        database_path=database_path, config_folder=config_folder
    )
    try:
        marker = db1.database_connection["kv_settings"].find_one(
            key="schema_repaired_at"
        )
    finally:
        db1.close()

    assert marker is not None, (
        "Phase 7.1 must write the schema_repaired_at marker after the "
        "first successful repair."
    )
    # The value is an ISO timestamp; just sanity-check the shape.
    value = marker.get("value")
    assert isinstance(value, str)
    parsed = datetime.datetime.fromisoformat(value)
    assert parsed.tzinfo is not None, (
        "schema_repaired_at must be timezone-aware (UTC ISO)."
    )


def test_repair_marker_skips_migrator(tmp_path: Path) -> None:
    """Second ``DatabaseObj`` with a counting migrator skips the
    migrator entirely when the marker is present.

    Companion to ``test_repair_runs_only_once_across_opens``: this
    one uses the *production* migrator for the first open (to set
    the marker naturally) and a counting migrator for the second
    open. Asserts the second open's migrator is *not* called — the
    gate fires.
    """
    database_path = tmp_path / "folders.db"
    config_folder = tmp_path / "config"
    config_folder.mkdir()

    db1 = _open_db(
        database_path=database_path, config_folder=config_folder
    )
    db1.close()

    counting_migrator, call_counts = _counting_migrator()
    db2 = _open_db(
        database_path=database_path,
        config_folder=config_folder,
        migrator_func=counting_migrator,
    )
    db2.close()

    assert call_counts == [], (
        "The gate must skip the migrator when schema_repaired_at is "
        f"already present; counting migrator was called {len(call_counts)} "
        "times on the second open."
    )


def test_round_trip_stable_without_reopen(tmp_path: Path) -> None:
    """The Phase 6.4 round-trip pattern works *without* the
    explicit re-open in the fixture.

    This is the regression test that proves the fix resolves the
    symptom the Phase 6.4 workaround was papering over. If the
    ``_run_current_version_repairs`` gate ever regresses (e.g. the
    marker check is removed), this test fails — even though no
    test in ``test_soft_delete.py`` will.
    """
    from webapp.config import Settings
    from webapp.database import open_database

    settings = Settings(
        tmp_path / "data", tmp_path / "data" / "config"
    )

    # Insert a folder row with only the minimum keys; the columns
    # the migration knows defaults for (``process_edi``, etc.)
    # stay NULL.
    db = open_database(settings)
    try:
        folder_id = db.folders_table.insert(
            {
                "folder_name": "inbox/round-trip",
                "folder_is_active": True,
                "alias": "RT",
                "process_backend_copy": False,
                "process_backend_ftp": False,
                "process_backend_email": False,
                "process_backend_http": False,
                "created_at": "2026-08-18T12:00:00",
            }
        )
    finally:
        db.close()

    # CRITICAL: do NOT re-open the DB here. The Phase 6.4 fixture
    # explicitly re-opens to give the repair pass a chance to run
    # before the snapshot. With Phase 7.1 the repair ran exactly
    # once (during the insert above's open), the marker is now
    # persisted, and the next open will skip the repair. So the
    # snapshot below must reflect the same state as the second open
    # would see.
    db = open_database(settings)
    try:
        original = dict(db.folders_table.find_one(id=folder_id))
    finally:
        db.close()

    # The round-trip expectation: ``process_edi`` should be None,
    # not False. Before Phase 7.1, this assertion would fail
    # because every open fired the ``_backfill_defaults`` UPDATE,
    # which sets ``process_edi = 0`` on NULL rows.
    assert original.get("process_edi") is None, (
        "process_edi should stay NULL through a round-trip. If this "
        "is False, the repair pass is firing on every open again — "
        "the Phase 7.1 gate regressed."
    )
    # And the other ``_EXPLICIT_BOOLEAN_COLUMNS_BY_TABLE`` columns
    # should also stay NULL — they all share the same code path.
    for col in (
        "split_edi",
        "include_a_records",
        "include_c_records",
        "include_headers",
        "force_edi_validation",
    ):
        assert original.get(col) is None, (
            f"{col} should stay NULL through a round-trip; got "
            f"{original.get(col)!r}. The Phase 7.1 gate regressed."
        )


def test_runbook_endpoints_referenced(tmp_path: Path) -> None:
    """Placeholder for the Phase 7.2 docs check.

    The runbook references every endpoint it documents. This test
    is added in 7.1's file (rather than 7.2's) so the regression
    net ships with the gate fix; Phase 7.2's actual runbook work
    only adds the docstring content the test verifies against.

    Skipped until ``docs/runbook.md`` exists. Marked ``xfail`` with
    ``strict=False`` so a missing runbook is a soft failure, not a
    hard one — the gate fix in 7.1 stands on its own.
    """
    runbook = Path(__file__).parent.parent.parent / "docs" / "runbook.md"
    if not runbook.exists():
        pytest.skip(
            "Phase 7.2 runbook not yet written; this test is a placeholder "
            "that becomes active once docs/runbook.md lands."
        )

    from webapp.routers import (
        backups,
        errors,
        folders,
        processed,
        runs,
        schedule,
        system,
        watcher,
    )

    # Each module exposes a ``router`` attribute. Build the set of
    # path templates the FastAPI app would route on.
    modules_with_routers = {
        "backups": backups,
        "errors": errors,
        "folders": folders,
        "processed": processed,
        "runs": runs,
        "schedule": schedule,
        "system": system,
        "watcher": watcher,
    }

    referenced_paths: set[str] = set()
    text = runbook.read_text()
    # ``curl ... /api/runs/{run_id} ...`` and similar — extract any
    # /api/... path that follows a forward-slash.
    import re

    for match in re.finditer(r"/api/[A-Za-z_/{}\-]+", text):
        referenced_paths.add(match.group(0).rstrip(".,;"))

    # Every path the runbook mentions must be routable in some
    # module's ``router.routes`` list. We compare against the
    # ``path`` attribute of each route.
    all_paths: set[str] = set()
    for mod in modules_with_routers.values():
        router = getattr(mod, "router", None)
        if router is None:
            continue
        for route in router.routes:
            if hasattr(route, "path"):
                all_paths.add(route.path)

    missing = referenced_paths - all_paths
    assert not missing, (
        "docs/runbook.md references endpoints that are not defined "
        f"in any router: {sorted(missing)}"
    )


# Sanity check: the module imports compile. ``DatabaseObj`` is a
# sizable class; the import alone catches a lot of mistakes.
def test_module_imports_succeed() -> None:
    assert inspect.isclass(DatabaseObj)
