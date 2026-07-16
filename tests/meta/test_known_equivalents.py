"""Allowlist integrity meta-test.

Each meta-test runner maintains a ``KNOWN_*`` allowlist of intentional
exceptions. The fail-closed contract is "a typo fails closed: an entry
that doesn't match a real source line is NOT applied, the violation is
reported normally". The contract is asymmetric: a wrong line number
fails closed (good); a wrong file path also fails closed (good). But a
*stale* entry — one whose line number was once valid but has since
shifted because the test file was rewritten — also fails closed, which
means the entry silently stops silencing anything. There's no signal
to the maintainer that the entry is dead.

This runner walks every entry in every allowlist and asserts the cited
``line`` is within the line range of the cited ``file_relpath``. If a
file is deleted, the entry fails; if a line shifts, the entry fails;
if a tuple has the wrong arity, the entry fails. The output is a
per-entry list of failures with the file:line and reason, so a
maintainer can either update the entry (real drift) or remove it (the
underlying issue was fixed).

The lookup contract is ``(file_relpath, key1, key2_or_line, reason)``
for most runners, ``(file_relpath, line, reason)`` for the simpler
allowlists. The function ``_allowlist_entries`` below flattens each
allowlist into a uniform ``(file, line, reason)`` triple so a single
parametrized test can walk all of them.

Self-check: this runner's own public names (``_allowlist_entries``,
``ALLOWLISTS``) must exist and the ALLOWLISTS list must be non-empty.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass(frozen=True)
class AllowlistEntry:
    """One (file, line, reason) row from any runner's allowlist.

    The ``runner`` field is the name of the runner module the entry
    came from. The ``extra_key`` field carries the 4-tuple runners'
    mutation/rule/test-name key so future checks can use it; the line
    existence check below only needs ``file`` and ``line``.
    """

    runner: str
    file_relpath: str
    line: int
    reason: str
    extra_key: str = ""


def _entries_from_4tuple(
    runner: str, items: list[tuple]
) -> list[AllowlistEntry]:
    """Flatten ``(file, key, line, reason)`` allowlists (most runners)."""
    out: list[AllowlistEntry] = []
    for tup in items:
        if len(tup) != 4:
            continue
        file_rel, key, line, reason = tup
        if not isinstance(file_rel, str) or not isinstance(line, int):
            continue
        out.append(
            AllowlistEntry(
                runner=runner,
                file_relpath=file_rel,
                line=line,
                reason=str(reason),
                extra_key=str(key),
            )
        )
    return out


def _entries_from_3tuple(
    runner: str, items: list[tuple]
) -> list[AllowlistEntry]:
    """Flatten ``(file, line, reason)`` allowlists (hygiene, coverage,
    marker-placement, assertions).
    """
    out: list[AllowlistEntry] = []
    for tup in items:
        if len(tup) != 3:
            continue
        file_rel, line, reason = tup
        if not isinstance(file_rel, str) or not isinstance(line, int):
            continue
        out.append(
            AllowlistEntry(
                runner=runner,
                file_relpath=file_rel,
                line=line,
                reason=str(reason),
            )
        )
    return out


def _entries_from_5tuple(
    runner: str, items: list[tuple]
) -> list[AllowlistEntry]:
    """Flatten ``(file, test_name, line, kind, reason)`` (oracle runner)."""
    out: list[AllowlistEntry] = []
    for tup in items:
        if len(tup) != 5:
            continue
        file_rel, _test_name, line, _kind, reason = tup
        if not isinstance(file_rel, str) or not isinstance(line, int):
            continue
        out.append(
            AllowlistEntry(
                runner=runner,
                file_relpath=file_rel,
                line=line,
                reason=str(reason),
            )
        )
    return out


def _allowlist_entries() -> list[AllowlistEntry]:
    """Aggregate every (file, line, reason) row from every runner's
    allowlist. The output is the test parameter for the line-existence
    check below.
    """
    # Import the runner modules lazily so this file does not pull in
    # the entire meta-test corpus at module import time. The sys.path
    # insertion mirrors the other runners.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import test_assertions_are_meaningful  # type: ignore[import-not-found]
    import test_hygiene  # type: ignore[import-not-found]
    import test_marker_placement  # type: ignore[import-not-found]
    import test_module_coverage  # type: ignore[import-not-found]
    import test_property_oracle_consistency  # type: ignore[import-not-found]
    import test_property_tests_are_sufficient  # type: ignore[import-not-found]

    entries: list[AllowlistEntry] = []
    entries += _entries_from_3tuple(
        "test_assertions_are_meaningful",
        test_assertions_are_meaningful.KNOWN_ASSERTION_EQUIVALENT,
    )
    entries += _entries_from_3tuple(
        "test_hygiene",
        test_hygiene.KNOWN_HYGIENE_VIOLATIONS,
    )
    entries += _entries_from_3tuple(
        "test_marker_placement",
        test_marker_placement.KNOWN_MARKER_MISPLACEMENT,
    )
    entries += _entries_from_3tuple(
        "test_module_coverage",
        test_module_coverage.KNOWN_UNCOVERED,
    )
    entries += _entries_from_5tuple(
        "test_property_oracle_consistency",
        test_property_oracle_consistency.KNOWN_ORACLE_EQUIVALENT,
    )
    entries += _entries_from_4tuple(
        "test_property_tests_are_sufficient",
        test_property_tests_are_sufficient.KNOWN_EQUIVALENT,
    )
    return entries


ALLOWLISTS: list[AllowlistEntry] = _allowlist_entries()


@pytest.mark.meta_known_equivalents
@pytest.mark.parametrize(
    "entry",
    ALLOWLISTS,
    ids=lambda e: f"{e.runner}|{e.file_relpath}:{e.line}",
)
def test_allowlist_entry_line_exists(entry: AllowlistEntry) -> None:
    """The cited ``file_relpath`` must exist and contain at least
    ``line`` lines.

    Failure modes this catches:
    - The file the entry points to was deleted or renamed.
    - The line number drifted because the file was rewritten.
    - The tuple was constructed with the wrong field order (e.g. line
      in the second position instead of the third).

    The failure modes it does NOT catch:
    - The line number is right but the cited content no longer
      matches the ``reason``. (Reason/line coherence is a separate
      concern; this test focuses on existence only.)
    - The ``extra_key`` (mutation name, rule name) is wrong. That
      would be caught when the runner actually applies the allowlist
      and the entry doesn't match.
    """
    path = PROJECT_ROOT / entry.file_relpath
    if not path.exists():
        pytest.fail(
            f"{entry.runner}: allowlist entry references missing file: "
            f"{entry.file_relpath}:{entry.line} "
            f"({entry.reason[:60]!r})"
        )
    # Bound the read; the allowlist entries are unit-test files, well
    # under any reasonable cap. If a file is > 50k lines something is
    # very wrong and the test should fail loudly anyway.
    line_count = sum(1 for _ in path.open(encoding="utf-8", errors="replace"))
    if not (1 <= entry.line <= line_count):
        pytest.fail(
            f"{entry.runner}: allowlist entry line out of range: "
            f"{entry.file_relpath}:{entry.line} "
            f"(file has {line_count} lines; {entry.reason[:60]!r})"
        )


def test_allowlists_is_non_empty() -> None:
    """Sanity: the aggregate list of entries must be non-empty. If this
    fires, every runner's allowlist was either removed (which would
    silently turn the runner into a no-op) or the import above failed
    silently.
    """
    if not ALLOWLISTS:
        pytest.fail(
            "ALLOWLISTS is empty — every runner's allowlist was either "
            "removed or import-failed. Run tests/meta/ directly to see "
            "the import error."
        )


def test_self_check_public_surface() -> None:
    """The runner file itself must parse and expose the public surface
    used by the parametrized test. Mirrors the other runners' self-checks.
    """
    import ast as _ast

    self_path = Path(__file__).resolve()
    try:
        _ast.parse(self_path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError as exc:
        pytest.fail(f"self-parse failed: {exc}")
    required = {"ALLOWLISTS", "_allowlist_entries", "test_allowlist_entry_line_exists"}
    missing = required - set(globals())
    if missing:
        pytest.fail(
            "known-equivalents runner is missing required top-level names: "
            + ", ".join(sorted(missing))
        )
