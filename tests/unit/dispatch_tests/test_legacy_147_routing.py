"""1.47 routing-harness tests (per-row end-to-end).

Drives the *vendored* 1.47 ``dispatch.process()`` with anonymized folder rows
and records, for each row:

* which converter module was loaded (if any)
* which backend was invoked, with what output filename
* whether ``process_edi`` gating routed to conversion or pass-through
* whether ``record_error.do`` captured any errors

The test is the behavioural oracle: it tells us what 1.47 *would have done*
for a real customer configuration. The accompanying
``test_master_routing_matches_147.py`` then asserts the master pipeline picks
the same converter for the same rows.

Folder rows come from ``tests/fixtures/anonymized_folders/folders/*.json``.
The test fails loudly when no fixtures are committed — see
``test_anonymized_fixtures_present`` — so the suite cannot pass vacuously.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.unit.dispatch_tests.routing_parity_helpers import (
    drive_legacy_147_for_row,
)

ANON_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "anonymized_folders" / "folders"


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
# Coverage sentinel: fail loudly when no fixtures are present.
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
# Per-row routing test body
# ---------------------------------------------------------------------------


def _missing_third_party_deps(fmt: str) -> list[str]:
    """Return the names of third-party modules this format needs that the
    test environment doesn't have. Centralised so adding more formats is a
    one-liner.
    """
    missing: list[str] = []
    if "scansheet" in fmt:
        for mod in ("barcode", "openpyxl"):
            try:
                __import__(mod)
            except ImportError:
                missing.append(mod)
    if fmt in ("jolley_custom", "stewarts_custom"):
        try:
            __import__("dateutil")
        except ImportError:
            missing.append("dateutil")
    return missing


@pytest.mark.parametrize(
    "row",
    ANONYMIZED_ROWS,
    ids=[f"{int(r.get('id', i))}-{(str(r.get('alias', '')) or 'row')}"
         for i, r in enumerate(ANONYMIZED_ROWS)],
)
def test_legacy_147_routing_per_row(
    row,
    tmp_path,
    legacy_147_dispatch,
    legacy_147_registry,
    monkeypatch,
):
    """One test per anonymized folder row.

    For rows whose format requires a third-party module missing from the test
    environment (``barcode``, ``openpyxl``, ``dateutil``), we ``pytest.skip``
    with a TODO. The remaining rows run end-to-end through vendored dispatch.

    The per-row oracle result is also stashed into the session-scoped
    ``legacy_147_registry`` so the suite-wide parity dashboard test can
    correlate. The master-parity test does NOT depend on this registry —
    it runs its own 1.47 drive so the two files are truly independent.
    """
    fmt = (row.get("convert_to_format") or "").strip().lower().replace(" ", "_").replace("-", "_")
    format_module = f"convert_to_{fmt}" if fmt else ""

    missing = _missing_third_party_deps(fmt)
    legacy_result, converter_calls, backend_calls = drive_legacy_147_for_row(
        row, tmp_path, monkeypatch, legacy_147_dispatch
    )
    if missing:
        legacy_result.skipped_reason = f"missing deps: {missing}"
        legacy_147_registry.record(legacy_result)
        pytest.skip(
            f"format {fmt!r} requires vendored third-party libs missing "
            f"from test env: {missing}. TODO: install or stub. "
            f"See plan §'Py2 -> Py3 shims'."
        )

    legacy_147_registry.record(legacy_result)

    # Per-row invariants on the oracle.
    if row.get("process_edi") == "True":
        assert legacy_result.legacy_process_edi_enabled is True
    if fmt:
        assert legacy_result.format_module_requested == format_module

    # Capture for introspection via pytest -s.
    test_legacy_147_routing_per_row.legacy_result = legacy_result  # type: ignore[attr-defined]
    test_legacy_147_routing_per_row.backend_calls = backend_calls  # type: ignore[attr-defined]
    test_legacy_147_routing_per_row.converter_calls = converter_calls  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Coverage stats test (non-asserting on purpose; prints format coverage).
# ---------------------------------------------------------------------------


def test_format_coverage_in_anonymized_db():
    """Surface every format value seen in real customer rows.

    Fails only if no fixtures are committed. Otherwise prints a coverage
    report so a human reading the log knows what's in the DB.
    """
    if not ANONYMIZED_ROWS:
        pytest.fail(
            "No anonymized folder fixtures committed; see "
            "test_anonymized_fixtures_present."
        )
    from collections import Counter

    formats = Counter((r.get("convert_to_format") or "").strip() for r in ANONYMIZED_ROWS)
    print("\nformat coverage:")
    for fmt, count in sorted(formats.items(), key=lambda x: (-x[1], x[0])):
        print(f"  {count:5d}  {fmt!r}")
    if not any(formats):
        pytest.skip(
            "All anonymized rows have empty convert_to_format; "
            "no converter routing to exercise."
        )


# ---------------------------------------------------------------------------
# process_edi promotion drift detection (customer-safety assertion).
# ---------------------------------------------------------------------------
#
# This is the single highest-value assertion in the harness. 1.47 dispatch
# uses a string-equality check ``parameters_dict['process_edi'] == "True"``
# at lines 314, 369, 390. Master uses ``normalize_bool`` which accepts any
# truthy form (Python True, int 1, "true"/"True"/"yes"/"on", etc.). Any
# anonymized row whose ``process_edi`` value is *not* exactly the string
# ``"True"`` is treated as "no conversion" by 1.47 but "do conversion" by
# master — a silent promotion that changes how the customer's files are
# routed. We classify every row's value and surface the deltas.


def _normalize_truthy(value):
    """A reduced normalize_bool that mirrors master/utils.bool_utils.

    Accepts: True, False, 1, 0, "True", "False", "true", "yes", "on",
    "1", "0", "", None, and anything else.
    """
    if value is True or value is False:
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ("true", "yes", "on", "1")
    return False


def _classify_process_edi(value):
    """Return "both_enabled" / "both_disabled" / "master_promotes" / "1.47_promotes".

    The four-way classification answers: would 1.47 invoke the converter
    for this value, and would master?
    """
    legacy_match = value == "True"
    master_match = bool(_normalize_truthy(value))
    if legacy_match and master_match:
        return "both_enabled"
    if not legacy_match and not master_match:
        return "both_disabled"
    if not legacy_match and master_match:
        return "master_promotes"  # 1.47 disabled -> master enabled
    return "1.47_promotes"  # 1.47 enabled -> master disabled (rare)


def test_process_edi_normalization_drift():
    """Classify every row's ``process_edi`` value and report promotions.

    Fails loudly when any row would be silently promoted from "no
    conversion" (1.47) to "conversion" (master). The failure message
    lists every affected customer row so they can be data-migrated before
    the master upgrade is rolled out.
    """
    if not ANONYMIZED_ROWS:
        pytest.fail(
            "No anonymized folder fixtures committed; see "
            "test_anonymized_fixtures_present."
        )

    promotions: list[dict] = []
    counts: dict[str, int] = {}
    for row in ANONYMIZED_ROWS:
        cls = _classify_process_edi(row.get("process_edi"))
        counts[cls] = counts.get(cls, 0) + 1
        if cls == "master_promotes":
            promotions.append(
                {
                    "id": row.get("id"),
                    "alias": row.get("alias"),
                    "value_repr": repr(row.get("process_edi")),
                    "convert_to_format": row.get("convert_to_format"),
                }
            )

    msg = "\nprocess_edi classification of {n} rows:\n{rep}".format(
        n=len(ANONYMIZED_ROWS),
        rep="\n".join(
            f"  {cls:18s}: {cnt}" for cls, cnt in sorted(counts.items())
        ),
    )
    if promotions:
        msg += "\n\nDRIFT: these rows will be PROMOTED from 'no conversion' to 'conversion':\n"
        for p in promotions[:50]:  # cap at 50 in the assert message
            msg += f"  id={p['id']} alias={p['alias']!r} value={p['value_repr']} convert_to_format={p['convert_to_format']!r}\n"
        if len(promotions) > 50:
            msg += f"  ... and {len(promotions) - 50} more (see captured promotions list)\n"
        test_process_edi_normalization_drift.promotions = promotions  # type: ignore[attr-defined]
        pytest.fail(
            msg
            + "\nAction required: data-migrate or suppress-promote these rows "
            "before master rollout. See plan §'process_edi promotion risk'."
        )


# ---------------------------------------------------------------------------
# Smoke for the variance of process_backend_* (no assertion, just a report).
# ---------------------------------------------------------------------------


def test_process_backend_representation_drift():
    """Report which rows store ``process_backend_*`` as ints vs strings.

    Same kind of drift as ``process_edi``: 1.47 uses ``is True`` and
    master coerces.  This test does not fail — it just records the
    counts so a human can decide if data migration is warranted.
    """
    if not ANONYMIZED_ROWS:
        pytest.fail(
            "No anonymized folder fixtures committed; see "
            "test_anonymized_fixtures_present."
        )
    from collections import Counter

    kinds: dict[str, Counter] = {k: Counter() for k in (
        "process_edi", "process_backend_copy", "process_backend_ftp",
        "process_backend_email", "tweak_edi",
    )}
    for row in ANONYMIZED_ROWS:
        for k in kinds:
            v = row.get(k)
            kinds[k][type(v).__name__] += 1
    print("\nbackend/edi boolean field type coverage:")
    for k, c in kinds.items():
        print(f"  {k}: " + ", ".join(f"{t}={n}" for t, n in c.items()))
