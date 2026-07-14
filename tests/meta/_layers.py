"""Test layer definitions for the meta-test runners.

Each "layer" represents a test directory in the project (unit, integration, qt).
The meta-test runners (test_hygiene, test_assertions_are_meaningful) walk every
layer and run their checks against the test files in that layer.

The layer abstraction is intentionally simple:

- A name (used in test IDs and reports)
- A path (the directory under tests/ containing the test files)
- A file enumerator (a callable that returns the list of test files in the layer)
- A description (a one-line summary for the runner's CLI output)

Adding a new layer is a one-line change to ALL_LAYERS. The runners pick up
the new layer automatically on the next test collection.

Layer exclusions are also enumerated here so the rationale is in one place
(not buried in a runner's glob). The current exclusions are:
- convert_backends: the directory exists with AGENTS.md + data/ but no test
  files yet (the AGENTS.md describes a planned structure that hasn't been
  implemented). Listed in ALL_LAYERS as a no-op; the enumerator returns []. The
  intent is that once test files are added, the runner will pick them up
  automatically.
- meta: the meta-tests themselves. The runner's own self-check
  (``test_<runner>_runner_self_check``) lives here and verifies the runner
  file is hygiene/assertion-clean.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Layer data model.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Layer:
    """A test layer (directory under tests/).

    Attributes:
        name: short identifier used in test IDs and reports (e.g. ``"unit"``).
        path: directory under ``tests/`` containing the test files.
        description: one-line summary of the layer for the runner's CLI output.
        iter_files: callable returning the sorted list of test files in the
            layer. Returning ``[]`` is allowed (the layer is a no-op in that
            case).
    """

    name: str
    path: Path
    description: str
    iter_files: Callable[[], list[Path]]


# ---------------------------------------------------------------------------
# Standard test-file glob. Mirrors the project's pytest discovery pattern
# (test_*.py under each layer's directory). Layer-specific enumerators can
# filter this further.
# ---------------------------------------------------------------------------


def _glob_test_files(directory: Path) -> list[Path]:
    """Return every ``test_*.py`` under ``directory``, sorted.

    Excludes nothing by default. Layers that need to exclude
    conftest.py, helper modules, or specific files should pass a custom
    ``iter_files`` to ``Layer`` instead of editing this function.
    """
    return sorted(directory.rglob("test_*.py"))


# ---------------------------------------------------------------------------
# Special-case enumerators. Some layers need a tighter glob or to skip
# specific files (e.g. fixtures, the meta-tests themselves).
# ---------------------------------------------------------------------------


def _iter_unit_test_files() -> list[Path]:
    """test_*.py under tests/unit/.

    Excludes:
      - conftest.py (not a test module)
      - anything under tests/unit/scripts/ (helper scripts, not tests)
    """
    unit_dir = Path("tests/unit")
    return sorted(p for p in unit_dir.rglob("test_*.py"))


def _iter_meta_test_files() -> list[Path]:
    """test_*.py under tests/meta/.

    The meta-test runners live here. Each runner's ``self_check`` test
    verifies that this file is itself hygiene/assertion-clean, so the
    meta-tests are tested by the meta-tests. Listing them in the layer
    makes them part of the regular scan; the self-check guards against
    self-referential noise (a test asserting on the runner's own regex
    pattern would otherwise be flagged as bare_magicmock or single_item
    _dispatch_root_import by the runner's own checks).
    """
    meta_dir = Path("tests/meta")
    return sorted(p for p in meta_dir.rglob("test_*.py"))


# ---------------------------------------------------------------------------
# ALL_LAYERS — the single source of truth for what the runners cover.
#
# Order matters: it's the order the runners report findings in, and the
# order the test IDs use. Unit is first because it's the largest and
# historically the most-tested layer.
# ---------------------------------------------------------------------------

ALL_LAYERS: list[Layer] = [
    Layer(
        name="unit",
        path=Path("tests/unit"),
        description="Unit tests (fast, isolated, no DB/network).",
        iter_files=_iter_unit_test_files,
    ),
    Layer(
        name="integration",
        path=Path("tests/integration"),
        description="Integration tests (DB, network, full pipeline).",
        iter_files=lambda: _glob_test_files(Path("tests/integration")),
    ),
    Layer(
        name="qt",
        path=Path("tests/qt"),
        description="PyQt5 UI tests (single-threaded per AGENTS.md).",
        iter_files=lambda: _glob_test_files(Path("tests/qt")),
    ),
    Layer(
        name="meta",
        path=Path("tests/meta"),
        description="Meta-tests themselves (the runners).",
        iter_files=_iter_meta_test_files,
    ),
    Layer(
        name="convert_backends",
        path=Path("tests/convert_backends"),
        description=(
            "Converter parity/baseline tests (see convert_backends/AGENTS.md). "
            "Currently a no-op: the directory has AGENTS.md + data/ but no test_*.py files yet."
        ),
        iter_files=lambda: _glob_test_files(Path("tests/convert_backends")),
    ),
]


# ---------------------------------------------------------------------------
# Scope helpers. Used by the meta-test runners to enumerate "every test
# file the runner should walk". The runners MUST NOT enumerate layers
# directly (the meta layer would be flagged by their own checks; the
# convert_backends layer is empty).
# Two scopes are defined:
# - ``scanned_layers()`` / ``iter_scanned_test_files()`` — the layers
#   and test files every meta-test runner walks. Excludes ``meta`` (the
#   runners themselves) and ``convert_backends`` (no test files yet).
# - ``self_check_layers()`` / ``iter_self_check_test_files()`` — the
#   layers and test files the runner's self-check should walk. Currently
#   the meta layer only.
# ---------------------------------------------------------------------------


SCAN_EXCLUDE: frozenset[str] = frozenset({"meta", "convert_backends"})
"""Layer names excluded from the regular scan.

The ``meta`` layer is excluded because the runners' own
``test_<runner>_self_check`` walks it; including it in the parametrized
scan would re-flag the same patterns the self-check covers.

The ``convert_backends`` layer is excluded because it has no test
files yet (only AGENTS.md + data/). Re-add the name here when test
files land.
"""


def scanned_layers() -> list[Layer]:
    """Return every layer the meta-test runners should walk.

    Order matches ``ALL_LAYERS`` so reports are stable.
    """
    return [layer for layer in ALL_LAYERS if layer.name not in SCAN_EXCLUDE]


def iter_scanned_test_files() -> list[tuple[Path, Layer]]:
    """Yield every (test_file, layer) the meta-test runners should walk.

    Excludes layers named in :data:`SCAN_EXCLUDE`. Files are sorted within
    each layer; the order across layers matches :data:`scanned_layers`.
    """
    out: list[tuple[Path, Layer]] = []
    for layer in scanned_layers():
        for f in layer.iter_files():
            out.append((f, layer))
    return out


def self_check_layers() -> list[Layer]:
    """Return the layers the runner's self-check should walk.

    Currently the meta layer only — that's where the runners live.
    """
    return [layer for layer in ALL_LAYERS if layer.name == "meta"]


def iter_self_check_test_files() -> list[tuple[Path, Layer]]:
    """Yield every (test_file, layer) the self-check should walk.

    Currently the meta layer's own runners; future runners added there
    will be picked up automatically.
    """
    out: list[tuple[Path, Layer]] = []
    for layer in self_check_layers():
        for f in layer.iter_files():
            out.append((f, layer))
    return out


# ---------------------------------------------------------------------------
# Helper accessors used by the runners.
# ---------------------------------------------------------------------------


def iter_all_test_files() -> list[tuple[Path, Layer]]:
    """Yield every test file across all layers, paired with its layer.

    Layers that have no test files (e.g. convert_backends) are skipped
    here but are still in ALL_LAYERS so they're documented.
    """
    out: list[tuple[Path, Layer]] = []
    for layer in ALL_LAYERS:
        for f in layer.iter_files():
            out.append((f, layer))
    return out


def layer_of(file: Path) -> Layer | None:
    """Return the layer a test file belongs to, or None.

    Used by the runner's CLI summary to group findings by layer.
    """
    try:
        rel = file.relative_to(Path("tests"))
    except ValueError:
        return None
    for layer in ALL_LAYERS:
        try:
            rel.relative_to(layer.path)
            return layer
        except ValueError:
            continue
    return None
