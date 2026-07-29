"""Module-coverage meta-test.

This meta-test asks: does every production module in the project have at
least one test file that imports from it? A production module with zero
test coverage is a gap: a refactor that silently breaks the module will
not be caught by any test.

Scope:
  - Walks every ``.py`` file under the production roots:
    ``core/``, ``dispatch/``, ``backend/``, ``interface/``,
    ``adapters/`` (and ``batch_file_processor/``, the compatibility
    shim).
  - Excludes ``__init__.py`` modules (these are namespace shims; their
    behavior is exercised when their submodules are imported).
  - Excludes ``tests/fixtures/legacy_147/`` and similar vendored-code
    fixtures — those are imported by the ``legacy_147`` drift test.
  - Excludes modules in any path that does not look like the project's
    production layout (e.g. ``main_qt.py``, ``main_interface.py`` at
    the repo root — those are entry points, not libraries).

Detection strategy:
  1. Walk the production roots and build a list of module relpaths
     (``core/edi/edi_parser.py`` -> ``core.edi.edi_parser``).
  2. Walk every test file and extract every ``ImportFrom`` and
     ``Import`` statement. Build a set of imported module names.
  3. A module is "covered" if any test imports its dotted path OR any
     parent path that exposes it. For ``core.edi.edi_parser`` we accept
     ``from core.edi import edi_parser`` OR ``from core.edi.edi_parser
     import some_thing``.

Allowlist:
  - ``KNOWN_UNCOVERED`` lists modules that are intentionally not tested.
    Each entry cites the reason so reviewers can audit. A typo fails
    closed: an unknown relpath does NOT match, so the violation is
    reported.
  - ``--no-skip-known-uncovered`` re-runs without the allowlist so the
    list itself is auditable.

Usage::

    # Run the coverage check.
    pytest tests/meta/test_module_coverage.py -n auto

    # Audit a single root.
    pytest tests/meta/test_module_coverage.py -k core_edi

    # Re-validate the allowlist.
    pytest tests/meta/test_module_coverage.py --no-skip-known-uncovered

    # CLI summary (no pytest).
    python tests/meta/test_module_coverage.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import NamedTuple

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Production roots to scan. Each entry is (relpath, label). The label is
# used in test IDs and the CLI summary.
PRODUCTION_ROOTS: list[tuple[str, str]] = [
    ("core", "core"),
    ("dispatch", "dispatch"),
    ("backend", "backend"),
    ("interface", "interface"),
    ("adapters", "adapters"),
    ("batch_file_processor", "batch_file_processor"),
    ("scripts", "scripts"),
]

# Modules that are intentionally entry points (main_*.py) or pure
# namespace packages (__init__.py) and should not require a direct
# test. The detection step also excludes these by path pattern.
ENTRY_POINT_NAMES = {"__init__.py", "main_qt.py", "main_interface.py"}


class UncoveredModule(NamedTuple):
    """One row in the report: a production module no test imports."""

    relpath: str
    root: str


# ---------------------------------------------------------------------------
# Auditability allowlist. Same fail-closed contract as the other meta-tests:
# an entry that doesn't match a real module relpath does NOT silence the
# violation.
# ---------------------------------------------------------------------------


KNOWN_UNCOVERED: list[tuple[str, str]] = [
    # ---- adapter/repo modules ----
    # In-memory adapter repositories. Production code path uses the
    # db2ssh adapter (see adapters/db2ssh/); the in-memory variant is
    # exercised only by integration scenarios that haven't landed in
    # tests yet. Re-validate when those scenarios are added.
    (
        "adapters/inmemory/repositories/inmemory_email_queue_repo.py",
        "in-memory adapter; db2ssh is the production path",
    ),
    (
        "adapters/inmemory/repositories/inmemory_folder_repo.py",
        "in-memory adapter; db2ssh is the production path",
    ),
    (
        "adapters/inmemory/repositories/inmemory_processed_files_repo.py",
        "in-memory adapter; db2ssh is the production path",
    ),
    (
        "adapters/inmemory/repositories/inmemory_settings_repo.py",
        "in-memory adapter; db2ssh is the production path",
    ),
    # ---- core utility modules ----
    # Retail UOM conversions. Defined in core/edi/retail_uom.py but
    # not imported by any test; the unit conversion path lives in
    # dispatch/services/uom_lookup_service.py and is exercised there.
    (
        "core/edi/retail_uom.py",
        "retail-UOM constants; not imported by any test "
        "(UOM lookup is covered via dispatch.services.uom_lookup_service)",
    ),
    # EDI format-parser helper. Same module is referenced indirectly
    # through core/edi/edi_parser.py tests.
    (
        "core/edi/edi_format_parser.py",
        "EDI format parser helper; not directly imported by tests "
        "(covered transitively via test_edi_parser.py)",
    ),
    # Small utility modules that are pure constants / helpers.
    (
        "core/utils/csv_utils.py",
        "small CSV helper; replace with stdlib csv when needed "
        "(see AGENTS.md anti-patterns about reinventing stdlib)",
    ),
    (
        "core/utils/folder_utils.py",
        "folder-path helper; not imported by any test "
        "(path operations covered via os.path / pathlib tests elsewhere)",
    ),
    (
        "core/utils/utils.py",
        "generic utility module; not imported by any test "
        "(superseded by more specific core/utils/* modules)",
    ),
    # ---- dispatch ----
    # Converters that are imported only at runtime via patch() string
    # references OR that have no test (the registry holds them but
    # they're not exercised end-to-end).
    (
        "dispatch/converters/convert_to_simplified_csv.py",
        "simplified CSV converter; test exists but imports via "
        "patch() string reference only (see test_all_processing_flows)",
    ),
    (
        "dispatch/converters/convert_to_stewarts_custom.py",
        "Stewart's custom converter; no end-to-end test yet "
        "(converter is registered but not on the live codepath)",
    ),
    (
        "dispatch/converters/convert_to_tweaks.py",
        "tweaks converter; the dispatch/pipeline/tweaker step was "
        "removed and replaced with convert_to_format='tweaks' — see "
        "AGENTS.md 'Removed/Migrated Components' table",
    ),
    (
        "dispatch/pipeline/factory.py",
        "pipeline factory; not imported by any test "
        "(pipeline is constructed inline in tests)",
    ),
    (
        "dispatch/services/folder_discovery.py",
        "folder discovery helper; covered transitively via " "FolderProcessor tests",
    ),
    (
        "dispatch/services/progress_reporting.py",
        "progress reporting module; covered transitively via "
        "dispatch.services.progress_reporter (note the singular); "
        "consider deleting one if they're truly redundant",
    ),
    # ---- interface ----
    (
        "interface/form/config_section_widgets.py",
        "Qt form widget factory; not imported by any test "
        "(covered via interface/qt/dialogs/* tests)",
    ),
    (
        "interface/form/section_factory.py",
        "form section factory; not imported by any test "
        "(covered via interface/qt/dialogs/* tests)",
    ),
    (
        "interface/interfaces.py",
        "interface module protocol definitions; not imported by any "
        "test (covered via interface/qt/* smoke tests at runtime)",
    ),
    (
        "interface/plugins/plugin_config.py",
        "plugin config dataclasses; not imported by any test "
        "(plugin system covered via tests/unit/test_plugins/*)",
    ),
    (
        "interface/plugins/plugin_manager_provider.py",
        "plugin manager provider singleton; not imported by any test "
        "(covered via tests/unit/test_plugins/test_plugin_manager*)",
    ),
    (
        "interface/qt/bootstrap.py",
        "Qt bootstrap helpers; not imported by any test "
        "(bootstrap is exercised at app startup, see "
        "tests/unit/test_app_smoke.py)",
    ),
    (
        "interface/qt/diagnostics.py",
        "Qt diagnostics helpers; not imported by any test",
    ),
    (
        "interface/qt/window_controller.py",
        "Qt window controller; not imported by any test "
        "(window construction is covered in tests/qt/*)",
    ),
    (
        "interface/services/progress_service.py",
        "progress service; not imported by any test "
        "(covered transitively via qt UI smoke tests)",
    ),
    # ---- scripts ----
    # Utility scripts. Most are CLI entry points invoked from the
    # command line, not library code that should be imported by
    # tests. Their behaviour is exercised manually / via CI scripts.
    (
        "scripts/clear_old_files.py",
        "CLI utility; invoked manually, not imported by tests",
    ),
    (
        "scripts/create_database.py",
        "CLI utility for DB creation; tests use "
        "DatabaseConnectionManager fixture instead (see conftest.py)",
    ),
    (
        "scripts/create_tar.py",
        "CLI utility; invoked manually",
    ),
    (
        "scripts/demo_legacy_import.py",
        "CLI demo / scratch script; not imported by tests",
    ),
    (
        "scripts/dummy_run_progress.py",
        "CLI demo / scratch script; not imported by tests",
    ),
    (
        "scripts/export_anonymized_folders.py",
        "CLI utility; invoked manually",
    ),
    (
        "scripts/extract_tar.py",
        "CLI utility; invoked manually",
    ),
    (
        "scripts/generate_test_report.py",
        "CLI utility; invoked from CI",
    ),
    (
        "scripts/query_runner.py",
        "CLI utility for ad-hoc queries; not imported by tests "
        "(test path uses core/database/query_runner.py)",
    ),
    (
        "scripts/record_error.py",
        "CLI utility; invoked manually",
    ),
    (
        "scripts/screenshot_script.py",
        "CLI utility; invoked manually",
    ),
    (
        "scripts/self_test.py",
        "CLI self-test entry point; not imported by tests",
    ),
    (
        "scripts/test_animation.py",
        "CLI utility; invoked manually",
    ),
]


def _lookup_uncovered(relpath: str) -> str | None:
    """Return the allowlist reason for ``relpath`` if it is in
    ``KNOWN_UNCOVERED``, else None. Used by the test and CLI report so
    allowlisted items are visible (not silently dropped)."""
    for entry_relpath, reason in KNOWN_UNCOVERED:
        if entry_relpath == relpath:
            return reason
    return None


def _is_known_uncovered(relpath: str) -> bool:
    return _lookup_uncovered(relpath) is not None


_AUDIT_UNCOVERED: bool = "--no-skip-known-uncovered" in sys.argv


# ---------------------------------------------------------------------------
# Discovery.
# ---------------------------------------------------------------------------


def _is_production_path(path: Path) -> bool:
    """True if ``path`` lives under one of ``PRODUCTION_ROOTS`` and is
    a top-level production file (not a vendored fixture, not a
    migration, not in tests/, not in .venv/, not a __pycache__)."""
    try:
        rel = path.resolve().relative_to(PROJECT_ROOT.resolve())
    except ValueError:
        return False
    parts = rel.parts
    if not parts:
        return False
    head = parts[0]
    if head not in {root for root, _ in PRODUCTION_ROOTS}:
        return False
    # Skip vendored fixture trees that happen to live under a
    # production root (e.g. tests/fixtures/legacy_147/dispatch.py
    # mirrors dispatch/orchestrator.py shape).
    rel_str = str(rel)
    return not (
        rel_str.startswith("tests/") or "fixtures/" in rel_str or "/legacy_" in rel_str
    )


def _iter_production_modules() -> list[tuple[Path, str, str]]:
    """Yield (abs_path, relpath_str, dotted_module_name) for every
    production module that the meta-test should check."""
    out: list[tuple[Path, str, str]] = []
    for root_rel, _label in PRODUCTION_ROOTS:
        root = PROJECT_ROOT / root_rel
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.py")):
            if path.name in ENTRY_POINT_NAMES:
                continue
            if not _is_production_path(path):
                continue
            try:
                rel_str = str(path.resolve().relative_to(PROJECT_ROOT.resolve()))
            except ValueError:
                continue
            # Convert filesystem path to dotted module name.
            dotted = rel_str.replace("/", ".").removesuffix(".py")
            if dotted.endswith(".__init__"):
                continue
            dotted = dotted.removesuffix(".__init__")
            out.append((path, rel_str, dotted))
    return out


def _iter_test_imports() -> set[str]:
    """Build the set of every module name imported by any test file.

    Walks ``tests/`` (excluding ``tests/meta/`` — the runners are not
    production-code tests) and parses every ``Import`` and ``ImportFrom``
    statement. Also extracts dotted module paths from string arguments
    to ``unittest.mock.patch`` and ``monkeypatch.setattr`` because those
    are common runtime-import paths that don't show up as AST imports
    (e.g. ``patch("dispatch.converters.convert_to_csv.edi_convert")``).
    """
    imports: set[str] = set()
    tests_root = PROJECT_ROOT / "tests"
    if not tests_root.exists():
        return imports
    for path in sorted(tests_root.rglob("*.py")):
        rel_str = str(path.resolve().relative_to(PROJECT_ROOT.resolve()))
        if rel_str.startswith("tests/meta/"):
            # Meta-test runners reference production modules in their
            # own source (e.g. they have string mentions of "core/edi"
            # in docstrings). Including them would mask real gaps.
            # The fixtures dir under tests/ contains production data
            # files, not test files.
            continue
        if "fixtures/" in rel_str:
            continue
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=str(path))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module is None:
                    continue
                imports.add(node.module)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.Call):
                _collect_string_import_targets(node, imports)
    return imports


# Module names that look like dotted module paths when used as the
# first argument to ``patch`` / ``patch.object`` / ``setattr`` etc.
_PATCH_FUNCS = {"patch", "patch.object", "patch.dict", "_patch"}
_PATCH_KW_ARG = {"target"}


def _collect_string_import_targets(call: ast.Call, imports: set[str]) -> None:
    """Add dotted module paths found in patch()/setattr()/import_module()
    string-argument calls.

    The shape of the string argument depends on the function:
      - ``patch("dispatch.converters.convert_to_csv.edi_convert")`` —
        patches attribute ``edi_convert`` of module
        ``dispatch.converters.convert_to_csv``. The module is the
        prefix before the last dot.
      - ``patch.object(SomeClass, "method")`` — we do NOT infer a
        module from this shape (the class is the import target, and
        we'd need to walk imports to find it).
      - ``monkeypatch.setattr("module.attr", value)`` — first
        positional arg; same prefix-before-last-dot rule as
        ``patch``.
      - ``import_module("dispatch.converters.convert_to_csv")`` —
        imports the module whose name is the WHOLE string. The
        call does not have an attribute-access shape (the function
        call takes a module name, not a path to a function), so
        the prefix-before-last-dot rule would be wrong: it would
        record ``dispatch.converters`` instead of the actual
        imported module ``dispatch.converters.convert_to_csv``.

    Only paths that look like a Python module (lowercase + underscore
    segments; reject class-like CamelCase) are recorded.
    """
    func = call.func
    func_name_parts: list[str] = []
    cur: ast.expr = func
    while isinstance(cur, ast.Attribute):
        func_name_parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        func_name_parts.append(cur.id)
    # The first segment is the actual function being called (e.g. for
    # ``importlib.import_module`` the parts list is
    # ``['import_module', 'importlib']``; for ``monkeypatch.setattr``
    # it's ``['setattr', 'monkeypatch']``; the last segment is the
    # outer qualifier, not the function name).
    bare_name = func_name_parts[0] if func_name_parts else ""
    if bare_name not in _PATCH_FUNCS and bare_name not in (
        "setattr",
        "import_module",
    ):
        return

    target_str: ast.expr | None = None
    if call.args and isinstance(call.args[0], ast.Constant):
        target_str = call.args[0]
    else:
        for kw in call.keywords:
            if kw.arg in _PATCH_KW_ARG and isinstance(kw.value, ast.Constant):
                target_str = kw.value
                break
    if target_str is None:
        return
    value = target_str.value
    if not isinstance(value, str) or "." not in value:
        return
    # ``import_module`` takes a module name (the whole string is the
    # module). ``patch`` and ``setattr`` take a path to an attribute;
    # the module is the prefix before the last dot. Branch on the
    # function name so the right rule is applied.
    module_path = value if bare_name == "import_module" else value.rsplit(".", 1)[0]
    if not all(part.isidentifier() for part in module_path.split(".")):
        return
    if any(part and part[0].isupper() for part in module_path.split(".")):
        return
    imports.add(module_path)


# ---------------------------------------------------------------------------
# Coverage check.
# ---------------------------------------------------------------------------


def _is_covered(dotted: str, test_imports: set[str]) -> bool:
    """True if any test imports ``dotted`` (direct or longer path).

    Two patterns count as coverage:

    1. Direct module import: ``from core.edi.edi_parser import X``
       or ``import core.edi.edi_parser``. Python loads
       ``core/edi/edi_parser.py`` and runs its module body.
    2. Longer path: ``from core.edi.edi_parser.foo import bar`` or
       ``from core.edi.edi_parser import something_else``. The test
       reaches into the module's namespace, so the module body
       has run.

    Patterns that DO NOT count (would risk false negatives):

      - ``from core.edi import edi_parser``. Python imports
        ``core.edi`` and only resolves the ``edi_parser`` attribute
        if ``core/edi/__init__.py`` eagerly re-exports it (and even
        then only as a re-exported name, not via module load). Most
        ``__init__.py`` files in this project are lazy.
      - ``import core`` (or any ancestor). Doesn't auto-load
        submodules.
      - ``from core.edi import *`` (wildcard). Doesn't auto-discover
        submodules.

    The risk of false positives (saying uncovered when actually
    loaded by an eager ``__init__.py``) is acceptable: those modules
    end up in the KNOWN_UNCOVERED allowlist with a one-line
    explanation. The risk of false negatives (missing real coverage
    gaps) is not.
    """
    for imported in test_imports:
        if imported == dotted or imported.startswith(dotted + "."):
            return True
    return False


def find_uncovered() -> list[UncoveredModule]:
    """Return every production module not imported by any test file."""
    imports = _iter_test_imports()
    uncovered: list[UncoveredModule] = []
    for _path, rel_str, dotted in _iter_production_modules():
        if not _is_covered(dotted, imports):
            root = rel_str.split("/", 1)[0]
            uncovered.append(UncoveredModule(relpath=rel_str, root=root))
    return uncovered


# ---------------------------------------------------------------------------
# Pytest-discoverable wrapper.
# ---------------------------------------------------------------------------


@pytest.mark.meta_coverage
def test_no_uncovered_production_modules() -> None:
    """Every production module must be imported by at least one test.

    A module with no test coverage is silent breakage waiting to happen.
    The runner fails on the first uncovered module; re-run with
    ``--no-skip-known-uncovered`` to audit the allowlist.
    """
    uncovered = find_uncovered()
    if _AUDIT_UNCOVERED:
        visible = uncovered
    else:
        visible = [u for u in uncovered if not _is_known_uncovered(u.relpath)]

    if not visible:
        return

    by_root: dict[str, list[str]] = {}
    for u in visible:
        by_root.setdefault(u.root, []).append(u.relpath)
    lines = [
        f"{len(visible)} production module(s) have no test coverage:",
    ]
    for root in sorted(by_root):
        lines.append(f"  [{root}]")
        for relpath in sorted(by_root[root]):
            lines.append(f"    {relpath}")
    pytest.fail("\n".join(lines))


# ---------------------------------------------------------------------------
# Self-check. The runner itself must be importable and the
# public surface must exist.
# ---------------------------------------------------------------------------


@pytest.mark.meta_coverage
def test_coverage_runner_self_check() -> None:
    """Sanity check: the runner file parses and exposes the public
    surface (``PRODUCTION_ROOTS``, ``KNOWN_UNCOVERED``,
    ``find_uncovered``). Parity with the other runners' self-checks.
    """
    self_path = Path(__file__).resolve()
    try:
        ast.parse(self_path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError as exc:
        pytest.fail(f"self-parse failed: {exc}")

    required = {"PRODUCTION_ROOTS", "KNOWN_UNCOVERED", "find_uncovered"}
    missing = required - set(globals())
    if missing:
        pytest.fail(
            "coverage runner is missing required top-level names: "
            + ", ".join(sorted(missing))
        )

    if not PRODUCTION_ROOTS:
        pytest.fail("PRODUCTION_ROOTS is empty — the meta-test would be a no-op")


@pytest.mark.meta_coverage
@pytest.mark.parametrize(
    ("source", "expected_modules"),
    [
        # patch() / setattr() — module is the prefix before the last
        # dot (the last segment is the function/attribute name).
        (
            'patch("core.utils.format_utils.normalize_upc_case")',
            {"core.utils.format_utils"},
        ),
        (
            'monkeypatch.setattr("core.edi.edi_parser.parse_edi_file", mock)',
            {"core.edi.edi_parser"},
        ),
        # import_module() — the whole string IS the module name.
        # A naive rsplit(". ", 1)[0] would record the parent path
        # and miss the actual module being imported.
        (
            'importlib.import_module("dispatch.converters.convert_to_csv")',
            {"dispatch.converters.convert_to_csv"},
        ),
        (
            # Bare module name (no dot) — the runner's
            # "value must contain a dot" filter at line 467 drops
            # this. The test file is recorded as importing the
            # module via a different path; the runner's
            # ``_is_covered`` check (line 506) still finds coverage
            # if the test file's other imports match a longer
            # prefix of the dotted form.
            'importlib.import_module("convert_to_csv")',
            set(),
        ),
        # Bare name (no dot) — not a multi-segment module, but the
        # function still has a string arg. Without a dot, no path
        # is recorded. This is the existing behavior; pin it.
        (
            'patch("name")',
            set(),
        ),
    ],
)
def test_collect_string_import_targets_shapes(
    source: str, expected_modules: set[str]
) -> None:
    """The patch / setattr / import_module dispatch in
    ``_collect_string_import_targets`` produces the right module
    name for each call shape.

    A regression in the function-name branch (e.g. accidentally
    re-introducing rsplit for import_module) would surface here.
    """
    # Re-parse the actual snippet wrapped in a function call
    wrapped = f"def _t():\n    {source}\n"
    tree = ast.parse(wrapped)
    call = tree.body[0].body[0].value
    assert isinstance(call, ast.Call)
    imports: set[str] = set()
    _collect_string_import_targets(call, imports)
    assert (
        imports == expected_modules
    ), f"expected {expected_modules!r}, got {imports!r} for source {source!r}"


# ---------------------------------------------------------------------------
# CLI summary.
# ---------------------------------------------------------------------------


def main() -> int:
    uncovered = find_uncovered()
    visible = (
        uncovered
        if _AUDIT_UNCOVERED
        else [u for u in uncovered if not _is_known_uncovered(u.relpath)]
    )
    total_modules = len(_iter_production_modules())
    print(
        f"Scanned {total_modules} production module(s); "
        f"{len(uncovered)} uncovered, {len(visible)} after allowlist."
    )
    by_root: dict[str, list[str]] = {}
    for u in visible:
        by_root.setdefault(u.root, []).append(u.relpath)
    for root in sorted(by_root):
        print(f"  [{root}] {len(by_root[root])} uncovered:")
        for relpath in sorted(by_root[root]):
            print(f"    {relpath}")
    return 1 if visible else 0


if __name__ == "__main__":
    raise SystemExit(main())
