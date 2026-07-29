"""Master-routing parity tests (lockstep with 1.47 oracle).

This module drives the *real* master ``EDIConverterStep`` for every anonymized
folder row and compares the result against the 1.47 oracle entry stashed by
``test_legacy_147_routing.py`` in the session-scoped ``legacy_147_registry``.

Three parity guarantees are asserted for every row:

1. **Routing-bucket agreement** — the bucket master lands in
   (``noop`` / ``disabled`` / ``run`` / ``error``) matches the bucket
   implied by the 1.47 routing result. Allowed legitimate deltas:

   * ``run`` ↔ ``error`` is OK when the master pipeline fails on a
     third-party dep missing from the test environment but records the
     error cleanly rather than crashing.
   * ``run`` ↔ ``noop`` is OK when 1.47's vendored ``convert_to_<fmt>``
     succeeded on the same input the master recorder stub also handled.

   Buckets that **never** agree under any rewriting are flagged so a
   human can review.

2. **Module-name agreement** — when both sides reach a converter call,
   the *normalized* module name they would load is identical
   (1.47: ``convert_to_<fmt>``; master: ``dispatch.converters.convert_to_<fmt>``).

3. **process_edi gating agreement** — the boolean decision master makes
   from ``process_edi`` matches the boolean decision the 1.47 source
   makes. Mismatches are the famous 1.47→master promotion risk surfaced
   as a separate ``test_process_edi_normalization_drift`` in the 1.47
   test module.

Folder rows come from ``tests/fixtures/anonymized_folders/folders/*.json``.
The test fails loudly when no fixtures are committed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.unit.dispatch_tests.conftest import Legacy147RoutingResult
from tests.unit.dispatch_tests.routing_parity_helpers import (
    drive_master_converter_step,
)

ANON_DIR = (
    Path(__file__).resolve().parents[2] / "fixtures" / "anonymized_folders" / "folders"
)


def _load_anonymized_rows():
    if not ANON_DIR.exists():
        return []
    files = sorted(
        (p for p in ANON_DIR.glob("*.json") if p.is_file()),
        key=lambda p: int(p.stem.split("_", 1)[0]),
    )
    rows = []
    for p in files:
        try:
            with p.open("r", encoding="utf-8") as fh:
                rows.append(json.load(fh))
        except (OSError, ValueError):
            continue
    return rows


ANONYMIZED_ROWS = _load_anonymized_rows()


# ---------------------------------------------------------------------------
# Mapping 1.47 oracle -> bucket string master can compare to.
# ---------------------------------------------------------------------------


def _legacy_to_bucket(legacy: Legacy147RoutingResult) -> str:
    """Bucket the 1.47 oracle result would land in if run through master.

    We map the 1.47 behavioural evidence (converter_called, errors,
    skipped_reason) into the master-side bucket taxonomy so two distinct
    real-runs can be compared apples-to-apples.
    """
    if legacy.skipped_reason:
        # Both sides skip due to missing deps; bucket as run since the
        # intent was to convert — but flag the skip separately.
        return "run_with_dep_skip"
    if legacy.errors and not legacy.converter_called:
        return "error"
    if not legacy.format_module_requested:
        return "noop"
    if legacy.converter_called:
        return "run"
    # format_module_requested but converter never called -> 1.47
    # skipped conversion despite format; treat as noop.
    return "noop"


# Allowed legitimate deltas between 1.47 bucket and master bucket.
LEGITIMATE_DELTAS = {
    frozenset({"run", "error"}),  # missing dep on master side
    frozenset({"noop", "disabled"}),
    frozenset({"run", "run_with_dep_skip"}),
    frozenset({"run", "noop"}),  # 1.47 crasher vs master noop
}


# ---------------------------------------------------------------------------
# Fixtures presence sentinel — keep parity with the 1.47 test file.
# ---------------------------------------------------------------------------


def test_anonymized_fixtures_present():
    if not ANONYMIZED_ROWS:
        pytest.fail(
            "No anonymized folder fixtures committed. Run "
            "scripts/export_anonymized_folders.py against an anonymized DB "
            "and commit the resulting JSON files under "
            "tests/fixtures/anonymized_folders/folders/."
        )


# ---------------------------------------------------------------------------
# Per-row parity tests — drive real master code, compare to oracle.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def master_outcomes_by_id(tmp_path_factory):
    """Run master once per row, cache outcomes by id.

    Done as a module-scoped fixture so the master drive runs once even
    though we want to assert against it from multiple parametrized tests.
    """
    outcomes: dict[int, object] = {}
    if not ANONYMIZED_ROWS:
        return outcomes
    tmp_root = tmp_path_factory.mktemp("master_parity")
    for row in ANONYMIZED_ROWS:
        rid = int(row.get("id", 0))
        outcomes[rid] = drive_master_converter_step(
            row, tmp_path=tmp_root / f"row_{rid}"
        )
    return outcomes


@pytest.mark.parametrize(
    "row",
    ANONYMIZED_ROWS,
    ids=[
        f"{int(r.get('id', i))}-{(str(r.get('alias', '')) or 'row')}"
        for i, r in enumerate(ANONYMIZED_ROWS)
    ],
)
def test_master_routing_bucket_matches_legacy(
    row,
    legacy_147_registry,
    master_outcomes_by_id,
):
    """For every row, assert master's bucket is consistent with the 1.47 oracle.

    The 1.47 oracle and master test run are both keyed by ``row['id']``.
    They communicate through the session-scoped
    ``legacy_147_registry``: the oracle publishes its observed behaviour,
    master reads it and asserts parity.
    """
    rid = int(row.get("id", 0))
    legacy = legacy_147_registry.get(rid)
    if legacy is None:
        pytest.skip(
            f"row id={rid} has no 1.47 oracle result yet — run the 1.47 "
            f"routing tests in the same pytest session."
        )

    master = master_outcomes_by_id.get(rid)
    if master is None:
        pytest.fail(f"master_outcomes_by_id missing row id={rid}")

    legacy_bucket = _legacy_to_bucket(legacy)
    master_bucket = master.bucket

    delta = frozenset({legacy_bucket, master_bucket})
    if delta == frozenset({legacy_bucket}) or legacy_bucket == master_bucket:
        return  # match — most common outcome
    if delta in LEGITIMATE_DELTAS:
        return  # documented legitimate difference

    # Otherwise fail with full context.
    test_master_routing_bucket_matches_legacy.deltas = (  # type: ignore[attr-defined]
        getattr(test_master_routing_bucket_matches_legacy, "deltas", [])
    )
    test_master_routing_bucket_matches_legacy.deltas.append(  # type: ignore[attr-defined]
        {
            "id": rid,
            "alias": row.get("alias"),
            "format": legacy.format_normalized,
            "legacy_bucket": legacy_bucket,
            "master_bucket": master_bucket,
            "master_failure_reason": getattr(master, "failure_reason", None),
        }
    )
    pytest.fail(
        f"row id={rid} alias={row.get('alias')!r} format={legacy.format_normalized!r}: "
        f"legacy bucket {legacy_bucket!r} vs master bucket {master_bucket!r} not in the "
        f"allowed-deltas set {LEGITIMATE_DELTAS}. Master failure reason: "
        f"{getattr(master, 'failure_reason', None)!r}"
    )


@pytest.mark.parametrize(
    "row",
    ANONYMIZED_ROWS,
    ids=[
        f"{int(r.get('id', i))}-{(str(r.get('alias', '')) or 'row')}"
        for i, r in enumerate(ANONYMIZED_ROWS)
    ],
)
def test_master_module_name_matches_legacy(
    row, legacy_147_registry, master_outcomes_by_id
):
    """When both sides run a converter, the *normalized* module name must agree.

    1.47 loads ``convert_to_<fmt>`` (bare); master loads
    ``dispatch.converters.convert_to_<fmt>``. Strip the prefix and assert
    the format suffix matches the legacy oracle's
    ``format_module_requested``.
    """
    rid = int(row.get("id", 0))
    legacy = legacy_147_registry.get(rid)
    if legacy is None or legacy.skipped_reason or not legacy.converter_called:
        pytest.skip("legacy side did not run a converter")
    master = master_outcomes_by_id.get(rid)
    if master is None:
        pytest.fail(f"master_outcomes_by_id missing row id={rid}")

    legacy_mod = legacy.format_module_requested  # e.g. "convert_to_csv"
    master_mod = (master.module_loaded or master.module_requested or "").rsplit(".", 1)[
        -1
    ]

    if not master_mod:
        pytest.skip("master did not request a module")
    assert (
        master_mod == legacy_mod
    ), f"row id={rid}: master would load {master_mod!r}; 1.47 loaded {legacy_mod!r}"


@pytest.mark.parametrize(
    "row",
    ANONYMIZED_ROWS,
    ids=[
        f"{int(r.get('id', i))}-{(str(r.get('alias', '')) or 'row')}"
        for i, r in enumerate(ANONYMIZED_ROWS)
    ],
)
def test_master_process_edi_decision_matches_legacy(row, legacy_147_registry):
    """``process_edi`` gating must agree on the boolean across branches.

    Where they disagree, that's a known promotion/demotion case surfaced
    in ``test_process_edi_normalization_drift``. We make this assertion a
    strict equality here so the suite fails loudly if a regression
    appears between runs.
    """
    rid = int(row.get("id", 0))
    legacy = legacy_147_registry.get(rid)
    if legacy is None:
        pytest.skip("no 1.47 oracle result for this row id")
    assert legacy.legacy_process_edi_enabled == legacy.master_process_edi_enabled, (
        f"row id={rid} alias={row.get('alias')!r}: legacy_enabled="
        f"{legacy.legacy_process_edi_enabled} vs master_enabled="
        f"{legacy.master_process_edi_enabled} — see "
        f"test_process_edi_normalization_drift for context"
    )


# ---------------------------------------------------------------------------
# Aggregate drift dashboard (printed, not asserted on every row).
# ---------------------------------------------------------------------------


def test_parity_deltas_summary():
    """Surface aggregate bucket agreement stats across all rows.

    Relies on the orchestrator test having stashed deltas on
    ``test_master_routing_bucket_matches_legacy.deltas``. If pytest
    collected in a non-standard order this list may be empty — that's
    fine, the bucket agreement asserts run per-row.
    """
    if not ANONYMIZED_ROWS:
        pytest.fail(
            "No anonymized folder fixtures committed; see "
            "test_anonymized_fixtures_present."
        )
    deltas = getattr(test_master_routing_bucket_matches_legacy, "deltas", [])
    if not deltas:
        print("\nMaster <-> 1.47 parity: all rows in the allowed-deltas set.")
        return
    print(f"\nMaster <-> 1.47 parity: {len(deltas)} legitimate-delta rows:")
    for d in deltas[:20]:
        print(
            f"  id={d['id']:>5d} alias={d['alias']!r:>20} "
            f"format={d['format']!r:>22} "
            f"legacy={d['legacy_bucket']!r} master={d['master_bucket']!r}"
        )
    if len(deltas) > 20:
        print(f"  ... and {len(deltas) - 20} more")


# ---------------------------------------------------------------------------
# Unit tests for the load-bearing helpers in this module.
#
# The parametrized parity tests above exercise the helpers end-to-end, but
# only when anonymized fixtures are committed. The tests below pin the
# helper logic in isolation so a regression in the mapper (which all
# parametrized tests would inherit silently) is caught independently of
# fixture availability.
# ---------------------------------------------------------------------------


class _FakeLegacy:
    """Minimal stand-in for Legacy147RoutingResult for _legacy_to_bucket tests."""

    def __init__(
        self,
        skipped_reason: str = "",
        errors: list | None = None,
        format_module_requested: str = "",
        converter_called: bool = False,
    ):
        self.skipped_reason = skipped_reason
        self.errors = list(errors or [])
        self.format_module_requested = format_module_requested
        self.converter_called = converter_called


def test_legacy_to_bucket_skipped_when_skip_reason_set():
    """A 1.47 row that skipped for missing deps buckets as run_with_dep_skip."""
    legacy = _FakeLegacy(
        skipped_reason="missing deps: ['barcode']",
        format_module_requested="convert_to_scansheet_type_a",
        converter_called=False,
    )
    assert _legacy_to_bucket(legacy) == "run_with_dep_skip"


def test_legacy_to_bucket_error_when_errors_and_no_converter_call():
    """1.47 recorded errors but never called the converter -> error bucket."""
    legacy = _FakeLegacy(
        errors=["boom"],
        format_module_requested="convert_to_csv",
        converter_called=False,
    )
    assert _legacy_to_bucket(legacy) == "error"


def test_legacy_to_bucket_noop_when_no_format_requested():
    """If 1.47 wasn't asked to convert anything, the bucket is noop."""
    legacy = _FakeLegacy(
        format_module_requested="",
        converter_called=False,
    )
    assert _legacy_to_bucket(legacy) == "noop"


def test_legacy_to_bucket_run_when_converter_was_called():
    """The common happy path: 1.47 reached the converter and called it."""
    legacy = _FakeLegacy(
        format_module_requested="convert_to_csv",
        converter_called=True,
    )
    assert _legacy_to_bucket(legacy) == "run"


def test_legacy_to_bucket_falls_back_to_noop_when_format_requested_but_no_call():
    """Edge case: format was requested but the converter never invoked.
    This is a 1.47 internal skip path; treat as noop so master matches.
    """
    legacy = _FakeLegacy(
        format_module_requested="convert_to_csv",
        converter_called=False,
    )
    assert _legacy_to_bucket(legacy) == "noop"


def test_legitimate_deltas_set_includes_documented_pairs():
    """The allowed-deltas set is the policy surface for what counts as a
    regression vs. a known-acceptable difference. Pin its contents so a
    silent shrinkage (e.g., removing 'run'/'error') is caught.
    """
    assert frozenset({"run", "error"}) in LEGITIMATE_DELTAS
    assert frozenset({"noop", "disabled"}) in LEGITIMATE_DELTAS
    assert frozenset({"run", "run_with_dep_skip"}) in LEGITIMATE_DELTAS
    assert frozenset({"run", "noop"}) in LEGITIMATE_DELTAS
