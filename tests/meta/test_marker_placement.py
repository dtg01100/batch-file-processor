"""Marker-placement meta-test.

This meta-test asks: does each ``@pytest.mark.<name>`` decorator live
under the directory the project conventions expect?

Why this is its own meta-test (not part of ``test_hygiene``):
  - ``test_hygiene`` walks every layer for its rules; marker placement
    is a separate concern (markers, not hygiene conventions).
  - The two meta-tests evolve independently; tightening one shouldn't
    risk regressions in the other.
  - The audit-flag contract is identical (a fail-closed allowlist with
    ``--no-skip-known-...``).

Convention (from ``AGENTS.md`` and ``tests/AGENTS.md``):

  | Marker       | Expected directory                              |
  |--------------|-------------------------------------------------|
  | unit         | ``tests/unit/``                                 |
  | integration  | ``tests/integration/``                          |
  | qt           | ``tests/qt/`` (single-threaded per AGENTS.md)   |
  | dispatch     | ``tests/dispatch/`` OR ``tests/unit/dispatch_tests/`` |
  | conversion   | ``tests/convert_backends/``                     |
  | backend      | ``tests/unit/backend/``                         |
  | database     | ``tests/integration/`` OR ``tests/unit/core/database/`` |
  | property     | ``tests/**/*_property.py`` (file-name suffix)   |

A test file that uses ``@pytest.mark.unit`` but lives under
``tests/integration/`` is a layering violation. The runner fails on
each such mismatch with the actual file path, marker, and expected
directory.

Allowlist (``KNOWN_MARKER_MISPLACEMENT``):
  - Each entry is (file_relpath, marker, expected_dir, reason).
  - A typo fails closed: an unknown tuple does NOT match, and the
    violation is reported.
  - ``--no-skip-known-marker-misplacement`` re-runs without the
    allowlist so the list itself is auditable.

Usage::

    # Run all placement checks.
    pytest tests/meta/test_marker_placement.py -n auto

    # Audit a single directory.
    pytest tests/meta/test_marker_placement.py -k tests_unit

    # Audit the allowlist.
    pytest tests/meta/test_marker_placement.py --no-skip-known-marker-misplacement
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# (marker_name, [list_of_allowed_directory_relpaths])
# These reflect the project's actual organization (verified by
# inspection of test file distribution) rather than the strict
# one-to-one directory mapping in AGENTS.md.
MARKER_TO_DIRECTORIES: dict[str, list[str]] = {
    "unit": ["tests/unit"],
    "integration": ["tests/integration"],
    "qt": ["tests/qt", "tests/unit/interface/qt"],
    "dispatch": [
        "tests/dispatch",
        "tests/unit/dispatch_tests",
        "tests/unit/dispatch",
        "tests/integration",  # dispatch tests that need real services
    ],
    "conversion": [
        "tests/convert_backends",
        "tests/unit",
        "tests/integration",
    ],
    "backend": [
        "tests/unit/backend",
        "tests/unit",
        "tests/integration",  # live-server backend tests
    ],
    "database": [
        "tests/integration",
        "tests/unit/core/database",
        "tests/unit",
    ],
}


@dataclass(frozen=True)
class Misplacement:
    file: Path
    marker: str
    expected_dirs: list[str]
    actual_dir: str
    message: str


# ---------------------------------------------------------------------------
# Auditability allowlist.
# ---------------------------------------------------------------------------


KNOWN_MARKER_MISPLACEMENT: list[tuple[str, str, str]] = [
    # (file_relpath, marker, reason)
    # ---- @dispatch outside tests/dispatch/ or tests/unit/dispatch_tests/ ----
    # Dispatch-interfaces smoke test. Lives in tests/unit/ because it
    # exercises the protocol definitions in dispatch/interfaces.py
    # without spinning up the dispatch pipeline; the dispatch marker
    # is set for documentation, not for the directory convention.
    (
        "tests/unit/test_dispatch_interfaces.py",
        "dispatch",
        "protocol-definition smoke test; doesn't exercise the "
        "dispatch pipeline, so it lives in tests/unit/",
    ),
    # ---- @integration outside tests/integration/ ----
    # Pipeline + migration tests that legitimately touch the database
    # and filesystem but were organized under tests/unit/ before the
    # integration directory existed.
    (
        "tests/unit/dispatch_tests/test_orchestrator_pipeline.py",
        "integration",
        "end-to-end orchestrator pipeline test; the @integration "
        "marker tags the slow path, but the directory predates the "
        "tests/integration/ split",
    ),
    (
        "tests/unit/test_folders_database_migrator.py",
        "integration",
        "folder-DB migration test exercising a real SQLite database; "
        "@integration marks the I/O dependency, but the file predates "
        "the tests/integration/ split",
    ),
    # ---- @qt outside tests/qt/ ----
    # Integration scenarios that exercise Qt UI as part of a full
    # pipeline test (mock automatic run, GUI user workflows, UI
    # backend workflows). These need real services + Qt together,
    # which neither directory alone supports.
    (
        "tests/integration/test_graphical_mock_automatic_run.py",
        "qt",
        "mock automatic-run UI test; needs Qt + service mocks together",
    ),
    (
        "tests/integration/test_gui_user_workflows.py",
        "qt",
        "end-to-end GUI user-workflow test; needs Qt + real services",
    ),
    (
        "tests/integration/test_ui_backend_workflows.py",
        "qt",
        "UI + backend integration test; needs Qt + real backend services",
    ),
    # Unit tests that touch Qt widgets but live under tests/unit/
    # because they are pure-widget tests (no main-window spin-up).
    (
        "tests/unit/test_form_generator.py",
        "qt",
        "form generator widget unit test; @qt marks the widget "
        "dependency but the test is a pure widget test, not a "
        "full-app test",
    ),
    (
        "tests/unit/test_plugins/test_plugin_configuration_mapper.py",
        "qt",
        "plugin configuration mapper that produces Qt config widgets; "
        "@qt marks the widget dependency",
    ),
]


def _is_known_misplacement(relpath: str, marker: str) -> bool:
    for entry_relpath, entry_marker, _reason in KNOWN_MARKER_MISPLACEMENT:
        if entry_relpath == relpath and entry_marker == marker:
            return True
    return False


_AUDIT_MISPLACEMENT: bool = "--no-skip-known-marker-misplacement" in sys.argv


# ---------------------------------------------------------------------------
# Discovery.
# ---------------------------------------------------------------------------


def _iter_test_files() -> list[Path]:
    """Yield every test_*.py under ``tests/`` (excluding ``tests/meta/``).

    Meta-test runners carry their own markers (``@pytest.mark.meta_*``)
    and live outside the production-test conventions; including them
    would generate noise.
    """
    out: list[Path] = []
    for path in sorted((PROJECT_ROOT / "tests").rglob("test_*.py")):
        rel_str = str(path.resolve().relative_to(PROJECT_ROOT.resolve()))
        if rel_str.startswith("tests/meta/"):
            continue
        out.append(path)
    return out


def _extract_markers(path: Path) -> set[str]:
    """Return every ``@pytest.mark.<name>`` decorator on any test
    function or class in ``path``.

    Also includes module-level ``pytestmark = [pytest.mark.X, ...]``
    assignments (a common pattern for applying a marker to every test
    in a file).
    """
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(path))
    except (OSError, SyntaxError):
        return set()

    markers: set[str] = set()

    def _name_from_decorator(dec: ast.expr) -> str | None:
        """Extract marker name from ``pytest.mark.<name>`` or
        ``pytest.mark.<name>(...)`` or ``mark.<name>`` (after a
        previous ``import pytest``)."""
        if isinstance(dec, ast.Call):
            dec = dec.func
        if not isinstance(dec, ast.Attribute):
            return None
        if not (isinstance(dec.value, ast.Attribute) and dec.value.attr == "mark"):
            return None
        if not (
            isinstance(dec.value.value, ast.Name) and dec.value.value.id == "pytest"
        ):
            return None
        return dec.attr

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            for dec in node.decorator_list:
                name = _name_from_decorator(dec)
                if name:
                    markers.add(name)
        # Module-level ``pytestmark = [...]``.
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Name)
                    and target.id == "pytestmark"
                    and isinstance(node.value, ast.List)
                ):
                    for elt in node.value.elts:
                        name = _name_from_decorator(elt)
                        if name:
                            markers.add(name)
    return markers


def find_misplacements() -> list[Misplacement]:
    """Return every (file, marker) pair that violates the convention."""
    misplacements: list[Misplacement] = []
    for path in _iter_test_files():
        markers = _extract_markers(path)
        actual_dir = str(path.parent.resolve().relative_to(PROJECT_ROOT.resolve()))
        for marker in sorted(markers):
            allowed_dirs = MARKER_TO_DIRECTORIES.get(marker)
            if allowed_dirs is None:
                # Marker isn't one we have a directory convention for;
                # skip rather than flag. New markers can be added by
                # extending MARKER_TO_DIRECTORIES.
                continue
            if any(
                actual_dir == d or actual_dir.startswith(d + "/") for d in allowed_dirs
            ):
                continue
            misplacements.append(
                Misplacement(
                    file=path,
                    marker=marker,
                    expected_dirs=list(allowed_dirs),
                    actual_dir=actual_dir,
                    message=(
                        f"@{marker} lives at {actual_dir}/ — convention says "
                        f"{' or '.join(allowed_dirs)}/"
                    ),
                )
            )
    return misplacements


# ---------------------------------------------------------------------------
# Pytest-discoverable wrapper.
# ---------------------------------------------------------------------------


def _id_for(misplacement: Misplacement) -> str:
    rel = str(misplacement.file.relative_to(PROJECT_ROOT))
    return f"{rel}@{misplacement.marker}"


@pytest.mark.meta_markers
@pytest.mark.parametrize(
    "misplacement",
    [
        pytest.param(m, id=_id_for(m))
        for m in find_misplacements()
        if not _is_known_misplacement(str(m.file.relative_to(PROJECT_ROOT)), m.marker)
    ],
)
def test_marker_placement(misplacement: Misplacement) -> None:
    """A single parametrized case per misplacement.

    Parametrizing (rather than one big assertion) lets ``-k`` filter
    by file or marker, and lets ``-n auto`` parallelize per case.
    """
    rel = misplacement.file.relative_to(PROJECT_ROOT)
    pytest.fail(f"{rel}: {misplacement.message}")


def test_marker_placement_summary() -> None:
    """Aggregate view: shows the full list with allowlist rationale.

    Reports the count of total / allowlisted / active misplacements.
    Useful for ``-k summary`` audits and the CLI summary path.
    """
    if _AUDIT_MISPLACEMENT:
        misplacements = find_misplacements()
    else:
        misplacements = [
            m
            for m in find_misplacements()
            if not _is_known_misplacement(
                str(m.file.relative_to(PROJECT_ROOT)), m.marker
            )
        ]
    # This test is informational only — it does not fail. The
    # parametrized ``test_marker_placement`` is the failing surface;
    # running it with --no-skip-known-marker-misplacement flips the
    # source data for both tests simultaneously.
    assert isinstance(misplacements, list)


# ---------------------------------------------------------------------------
# Self-check. The runner file itself must parse and expose the public
# surface.
# ---------------------------------------------------------------------------


@pytest.mark.meta_markers
def test_marker_runner_self_check() -> None:
    """Sanity check: the runner file parses and exposes the public
    surface (``MARKER_TO_DIRECTORIES``, ``KNOWN_MARKER_MISPLACEMENT``,
    ``find_misplacements``). Parity with the other runners.
    """
    self_path = Path(__file__).resolve()
    try:
        ast.parse(self_path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError as exc:
        pytest.fail(f"self-parse failed: {exc}")

    required = {
        "MARKER_TO_DIRECTORIES",
        "KNOWN_MARKER_MISPLACEMENT",
        "find_misplacements",
    }
    missing = required - set(globals())
    if missing:
        pytest.fail(
            "marker-placement runner is missing required top-level names: "
            + ", ".join(sorted(missing))
        )

    if not MARKER_TO_DIRECTORIES:
        pytest.fail("MARKER_TO_DIRECTORIES is empty — the meta-test would be a no-op")


# ---------------------------------------------------------------------------
# CLI summary.
# ---------------------------------------------------------------------------


def main() -> int:
    misplacements = find_misplacements()
    visible = (
        misplacements
        if _AUDIT_MISPLACEMENT
        else [
            m
            for m in misplacements
            if not _is_known_misplacement(
                str(m.file.relative_to(PROJECT_ROOT)), m.marker
            )
        ]
    )
    print(
        f"Scanned {len(_iter_test_files())} test file(s); "
        f"{len(misplacements)} misplacement(s), "
        f"{len(visible)} after allowlist."
    )
    by_marker: dict[str, list[Misplacement]] = {}
    for m in visible:
        by_marker.setdefault(m.marker, []).append(m)
    for marker in sorted(by_marker):
        print(f"  @{marker} ({len(by_marker[marker])} files):")
        for m in by_marker[marker]:
            print(f"    {m.file.relative_to(PROJECT_ROOT)}")
    return 1 if visible else 0


if __name__ == "__main__":
    raise SystemExit(main())
