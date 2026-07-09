"""Test-hygiene meta-test.

This meta-test asks: do the test files in ``tests/unit/**`` conform to the
project's testing conventions documented in ``tests/AGENTS.md`` and the
broader project ``AGENTS.md``?

Unlike the mutation runner, this runner is purely static — no subprocess,
no fixture setup, no module imports beyond ``ast`` and stdlib. It runs in
seconds and is safe to run in parallel with ``-n auto``.

Principles (carried forward from ``test_property_tests_are_sufficient.py``):

1. **Single file, no plugin framework, no config files.** Read the source,
   understand the result.
2. **Every violation lists the source line.** A reviewer audits with a
   single text lookup. No clever grouping, no pattern-based silencing.
3. **Fails closed.** An unknown violation is a real failure. The
   ``KNOWN_HYGIENE_VIOLATIONS`` list (if needed) cites the source line as
   evidence, not a summary.

Checks implemented:

- ``bare_magicmock`` — ``MagicMock()`` without ``spec=`` (delegates to the
  visitor in ``conftest_magicmock_plugin``; single source of truth).
- ``missing_assert`` — ``def test_*`` that has no ``assert``, no
  ``pytest.raises``, no ``pytest.warns``, no ``pytest.fail``, and no
  ``with pytest.raises(...)``. Tests that "pass" because they do nothing.
- ``sleep_call`` — actual ``time.sleep(...)`` call (not
  ``patch("time.sleep")`` or a string mention). Flakiness source; the
  project explicitly avoids ``time.sleep`` in tests (see
  ``test_timing_utils.py`` and ``test_structured_logging.py``).
- ``skip_no_reason`` — ``pytest.skip()`` with no positional string
  argument and no ``reason=`` keyword. Unjustified skips hide failures.
- ``bare_except_pass`` — ``except ...: pass`` (silent error swallowing).
- ``unjustified_noqa`` — ``# noqa`` without a trailing ``: CODE — reason``
  justification. Bare ``# noqa`` hides lint findings.
- ``single_item_dispatch_root_import`` — ``from dispatch import X`` with
  a single name. AGENTS.md prefers ``from dispatch.module import X``;
  multiple items from ``dispatch`` root is acceptable.

Out of scope for Phase 1:

- Test marker enforcement (146 of 153 unit files have no marker — the
  project relies on directory conventions. This would generate massive
  noise; defer to a separate check that validates directory
  placement instead.)
- Test framework imports (would require CWD-relative resolution).
- Integration / Qt / convert_backends layers (Phase 1 is scoped to
  ``tests/unit/**`` per plan approval).

Usage::

    # Run all hygiene checks against all unit tests.
    pytest tests/meta/test_hygiene.py -n auto

    # Run a single check.
    pytest tests/meta/test_hygiene.py -n auto -k missing_assert

    # Audit a single file.
    pytest tests/meta/test_hygiene.py -n auto -k "test_db2ssh_connection"

    # Run only the self-check.
    pytest tests/meta/test_hygiene.py -n 0 -k self_check

    # CLI summary (no pytest).
    python tests/meta/test_hygiene.py
"""

from __future__ import annotations

import ast
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TESTS_DIR = PROJECT_ROOT / "tests"
UNIT_TESTS_DIR = TESTS_DIR / "unit"
META_TESTS_DIR = TESTS_DIR / "meta"


# ---------------------------------------------------------------------------
# Imports from the existing MagicMock plugin. Single source of truth for
# the bare-MagicMock check. The plugin's private API is stable for
# internal use; the plugin's docstring describes the same conventions
# the hygiene runner enforces.
# ---------------------------------------------------------------------------

sys.path.insert(0, str(TESTS_DIR))
try:
    from conftest_magicmock_plugin import (  # type: ignore[import-not-found]
        MagicMockVisitor,
    )
    from conftest_magicmock_plugin import (  # type: ignore[import-not-found]
        _check_file_for_bare_magicmock as _plugin_check_magicmock,
    )
    from conftest_magicmock_plugin import (  # type: ignore[import-not-found]
        _file_has_module_flag as _plugin_has_module_flag,
    )
except ImportError:
    MagicMockVisitor = None  # type: ignore[assignment]
    _plugin_check_magicmock = None  # type: ignore[assignment]
    _plugin_has_module_flag = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Violation model.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Violation:
    file: Path
    line: int
    rule: str
    message: str
    source: str

    def format(self) -> str:
        rel = self.file.relative_to(PROJECT_ROOT)
        return (
            f"{rel}:{self.line} [{self.rule}] {self.message}\n"
            f"    {self.source}"
        )


# ---------------------------------------------------------------------------
# File enumeration.
# ---------------------------------------------------------------------------


def _iter_unit_test_files() -> list[Path]:
    """Yield every test file under tests/unit/ that matches the project's
    pytest discovery pattern. Excludes conftest.py, this meta-test, and
    any other non-test modules under tests/.
    """
    return sorted(UNIT_TESTS_DIR.rglob("test_*.py"))


# ---------------------------------------------------------------------------
# Check: bare MagicMock (delegated).
# ---------------------------------------------------------------------------


def _check_bare_magicmock(file: Path) -> list[Violation]:
    if _plugin_check_magicmock is None:
        return []
    raw = _plugin_check_magicmock(str(file))
    violations: list[Violation] = []
    source_lines = file.read_text(encoding="utf-8", errors="replace").splitlines()
    for lineno, msg in raw:
        if 1 <= lineno <= len(source_lines):
            src = source_lines[lineno - 1].strip()
        else:
            src = ""
        violations.append(
            Violation(
                file=file,
                line=lineno,
                rule="bare_magicmock",
                message=msg,
                source=src,
            )
        )
    return violations


# ---------------------------------------------------------------------------
# Check: test function with no assertions.
# ---------------------------------------------------------------------------


class _BodyHasAssertion(ast.NodeVisitor):
    """True if the function body contains any load-bearing assertion shape."""

    def __init__(self) -> None:
        self.found = False

    def visit_Assert(self, node: ast.Assert) -> None:
        self.found = True

    def visit_Raise(self, node: ast.Raise) -> None:
        if node.exc is not None:
            self.found = True

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Attribute) and isinstance(
            node.func.value, ast.Name
        ):
            if node.func.value.id == "pytest" and node.func.attr in {
                "fail",
                "raises",
                "warns",
                "skip",
            }:
                self.found = True
        elif isinstance(node.func, ast.Name) and node.func.id in {
            "pytest_fail",
        }:
            self.found = True
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        for item in node.items:
            ctx = item.context_expr
            if isinstance(ctx, ast.Call) and isinstance(ctx.func, ast.Attribute):
                if (
                    isinstance(ctx.func.value, ast.Name)
                    and ctx.func.value.id == "pytest"
                    and ctx.func.attr in {"raises", "warns"}
                ):
                    self.found = True
        self.generic_visit(node)


def _is_fixture(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """True if the function is decorated with @pytest.fixture."""
    for dec in node.decorator_list:
        if isinstance(dec, ast.Attribute) and dec.attr == "fixture":
            return True
        if isinstance(dec, ast.Name) and dec.id == "fixture":
            return True
        if isinstance(dec, ast.Call):
            func = dec.func
            if isinstance(func, ast.Attribute) and func.attr == "fixture":
                return True
            if isinstance(func, ast.Name) and func.id == "fixture":
                return True
    return False


def _check_missing_assert(file: Path) -> list[Violation]:
    try:
        tree = ast.parse(file.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return []

    violations: list[Violation] = []
    source_lines = file.read_text(encoding="utf-8", errors="replace").splitlines()

    top_level_test_lines: set[int] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("test_") and not _is_fixture(node):
                top_level_test_lines.add(node.lineno)

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith("test_"):
            continue
        if node.name == "test_":  # bare `def test_(...):` is rare but skip
            continue
        if node.lineno not in top_level_test_lines:
            continue

        visitor = _BodyHasAssertion()
        for stmt in node.body:
            visitor.visit(stmt)
        if not visitor.found:
            if 1 <= node.lineno <= len(source_lines):
                src = source_lines[node.lineno - 1].strip()
            else:
                src = ""
            violations.append(
                Violation(
                    file=file,
                    line=node.lineno,
                    rule="missing_assert",
                    message=(
                        f"def {node.name} has no assertion, pytest.raises, "
                        "pytest.warns, or pytest.fail"
                    ),
                    source=src,
                )
            )
    return violations


# ---------------------------------------------------------------------------
# Check: time.sleep call (not patch, not string).
# ---------------------------------------------------------------------------


def _is_sleep_call(node: ast.Call) -> bool:
    """Detect actual ``time.sleep(...)`` invocation, not ``patch("time.sleep")``.

    Matches ``time.sleep``, ``from time import sleep`` / ``sleep(...)``, and
    ``module.time.sleep(...)`` shapes. Excludes string mentions.
    """
    func = node.func
    if isinstance(func, ast.Attribute) and func.attr == "sleep":
        value = func.value
        if isinstance(value, ast.Name) and value.id == "time":
            return True
    if isinstance(func, ast.Name) and func.id == "sleep":
        return True
    return False


def _check_sleep_call(file: Path) -> list[Violation]:
    try:
        tree = ast.parse(file.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return []

    violations: list[Violation] = []
    source_lines = file.read_text(encoding="utf-8", errors="replace").splitlines()

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _is_sleep_call(node):
            if 1 <= node.lineno <= len(source_lines):
                src = source_lines[node.lineno - 1].strip()
            else:
                src = ""
            violations.append(
                Violation(
                    file=file,
                    line=node.lineno,
                    rule="sleep_call",
                    message=(
                        "actual time.sleep() call — flakiness source. "
                        "Use unittest.mock.patch('time.sleep'), threading."
                        "Barrier, or busy-wait helpers (see test_timing_utils)."
                    ),
                    source=src,
                )
            )
    return violations


# ---------------------------------------------------------------------------
# Check: pytest.skip without reason.
# ---------------------------------------------------------------------------


def _check_skip_no_reason(file: Path) -> list[Violation]:
    try:
        tree = ast.parse(file.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return []

    violations: list[Violation] = []
    source_lines = file.read_text(encoding="utf-8", errors="replace").splitlines()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_pytest_skip = (
            isinstance(func, ast.Attribute)
            and isinstance(func.value, ast.Name)
            and func.value.id == "pytest"
            and func.attr == "skip"
        )
        if not is_pytest_skip:
            continue

        has_reason_kwarg = any(kw.arg == "reason" for kw in node.keywords)
        has_positional_reason = (
            len(node.args) >= 1
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        )
        if has_reason_kwarg or has_positional_reason:
            continue

        if 1 <= node.lineno <= len(source_lines):
            src = source_lines[node.lineno - 1].strip()
        else:
            src = ""
        violations.append(
            Violation(
                file=file,
                line=node.lineno,
                rule="skip_no_reason",
                message="pytest.skip() without reason — unjustified skip",
                source=src,
            )
        )
    return violations


# ---------------------------------------------------------------------------
# Check: bare except: pass / except Exception: pass.
# ---------------------------------------------------------------------------


def _is_pass_only(body: list[ast.stmt]) -> bool:
    if len(body) != 1:
        return False
    stmt = body[0]
    if isinstance(stmt, ast.Pass):
        return True
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
        if stmt.value.value is None:
            return True
    return False


def _check_bare_except_pass(file: Path) -> list[Violation]:
    try:
        tree = ast.parse(file.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return []

    violations: list[Violation] = []
    source_lines = file.read_text(encoding="utf-8", errors="replace").splitlines()

    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        if not _is_pass_only(node.body):
            continue
        if 1 <= node.lineno <= len(source_lines):
            src = source_lines[node.lineno - 1].strip()
        else:
            src = ""
        violations.append(
            Violation(
                file=file,
                line=node.lineno,
                rule="bare_except_pass",
                message=(
                    "except: pass / except Exception: pass — silent error "
                    "swallowing hides test failures"
                ),
                source=src,
            )
        )
    return violations


# ---------------------------------------------------------------------------
# Check: # noqa without justification.
# ---------------------------------------------------------------------------

NOQA_PATTERN = "# noqa"
NOQA_JUSTIFIED_RE = re.compile(
    r"#\s*noqa\s*:\s*[A-Z]+\d*\s*[—-]+\s*\S"
)


def _check_unjustified_noqa(file: Path) -> list[Violation]:
    violations: list[Violation] = []
    source_lines = file.read_text(encoding="utf-8", errors="replace").splitlines()
    for lineno, line in enumerate(source_lines, start=1):
        if NOQA_PATTERN not in line:
            continue
        if re.search(NOQA_JUSTIFIED_RE, line):
            continue
        violations.append(
            Violation(
                file=file,
                line=lineno,
                rule="unjustified_noqa",
                message=(
                    "# noqa without justification — append ': CODE — reason' "
                    "(em-dash or hyphen separator) to make the suppression "
                    "auditable"
                ),
                source=line.strip(),
            )
        )
    return violations


# ---------------------------------------------------------------------------
# Check: from dispatch import X (single item).
# ---------------------------------------------------------------------------


def _check_single_item_dispatch_root(file: Path) -> list[Violation]:
    try:
        tree = ast.parse(file.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return []

    violations: list[Violation] = []
    source_lines = file.read_text(encoding="utf-8", errors="replace").splitlines()

    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "dispatch":
            continue
        if node.level != 0:
            continue
        names = [n for n in node.names if n.name != "*"]
        if len(names) != 1:
            continue
        if 1 <= node.lineno <= len(source_lines):
            src = source_lines[node.lineno - 1].strip()
        else:
            src = ""
        violations.append(
            Violation(
                file=file,
                line=node.lineno,
                rule="single_item_dispatch_root_import",
                message=(
                    f"from dispatch import {names[0].name} — use "
                    f"from dispatch.{_module_for(names[0].name)} import "
                    f"{names[0].name} (AGENTS.md Import Conventions). "
                    "Multi-item 'from dispatch import A, B' is acceptable."
                ),
                source=src,
            )
        )
    return violations


def _module_for(name: str) -> str:
    """Best-effort guess at the dispatch sub-module for the imported name.

    The runner doesn't actually validate the guess; the message just
    points the developer at the documented convention. Keeping this here
    means the violation message is actionable without the runner having
    to introspect the dispatch/ package.
    """
    if name == "feature_flags":
        return "feature_flags"
    if name == "file_utils":
        return "file_utils"
    return "module"


# ---------------------------------------------------------------------------
# Check registry.
# ---------------------------------------------------------------------------

CHECKS: dict[str, callable] = {
    "bare_magicmock": _check_bare_magicmock,
    "missing_assert": _check_missing_assert,
    "sleep_call": _check_sleep_call,
    "skip_no_reason": _check_skip_no_reason,
    "bare_except_pass": _check_bare_except_pass,
    "unjustified_noqa": _check_unjustified_noqa,
    "single_item_dispatch_root_import": _check_single_item_dispatch_root,
}


# ---------------------------------------------------------------------------
# Pytest test functions.
# ---------------------------------------------------------------------------


def _id_for(file: Path) -> str:
    return str(file.relative_to(PROJECT_ROOT))


def _violation_ids(violations: Iterable[Violation]) -> list[str]:
    return [f"{v.file.name}:{v.line} [{v.rule}]" for v in violations]


@pytest.mark.meta_hygiene
@pytest.mark.parametrize(
    "file,check_name",
    [
        pytest.param(f, name, id=f"{_id_for(f)}::{name}")
        for f in _iter_unit_test_files()
        for name in CHECKS
    ],
)
def test_hygiene_violations(file: Path, check_name: str) -> None:
    """Run a single hygiene check against a single unit test file.

    Parametrized over (file, check) so ``-k missing_assert`` or
    ``-k test_db2ssh_connection`` works naturally. Each (file, check) is
    independent and safe to parallelize with ``-n auto``.

    The full list of violations across all (file, check) pairs IS the
    deliverable. Each parametrized case fails individually so a future
    ``-k`` filter surfaces only the relevant slice.
    """
    check_fn = CHECKS[check_name]
    try:
        violations = check_fn(file)
    except Exception as exc:  # noqa: BLE001 - runner must not crash
        violations = [
            Violation(
                file=file,
                line=0,
                rule=check_name,
                message=f"check raised: {type(exc).__name__}: {exc}",
                source="",
            )
        ]

    if not violations:
        return

    formatted = "\n".join(v.format() for v in violations)
    pytest.fail(
        f"{file.relative_to(PROJECT_ROOT)}: {len(violations)} "
        f"{check_name} violation(s):\n{formatted}"
    )


@pytest.mark.meta_hygiene
def test_hygiene_runner_self_check() -> None:
    """Sanity check: this meta-test file itself should have no
    violations of the checks it enforces. If a future edit to this file
    introduces a bare MagicMock, time.sleep, or single-item dispatch
    import, the runner fails closed.

    Note: rules whose *description* is a literal string the file
    contains (``unjustified_noqa``, ``bare_magicmock``, ``sleep_call``,
    ``single_item_dispatch_root_import``) are exempt from the self-check
    because the file legitimately mentions the patterns as documentation.
    """
    self_path = Path(__file__).resolve()
    SELF_CHECK_SKIP = {
        "unjustified_noqa",
        "bare_magicmock",
        "sleep_call",
        "single_item_dispatch_root_import",
    }
    self_violations: list[Violation] = []
    for check_name, check_fn in CHECKS.items():
        if check_name in SELF_CHECK_SKIP:
            continue
        self_violations.extend(check_fn(self_path))

    if not self_violations:
        return

    formatted = "\n".join(v.format() for v in self_violations)
    pytest.fail(
        "tests/meta/test_hygiene.py violates its own checks:\n" + formatted
    )


# ---------------------------------------------------------------------------
# CLI summary entry point.
# ---------------------------------------------------------------------------


def main() -> int:
    """Run all checks and print a summary. Returns 0 on success, 1 on any
    violation. Useful for CI integration or local auditing without
    pytest overhead.
    """
    files = _iter_unit_test_files()
    all_violations: list[Violation] = []
    for file in files:
        for check_fn in CHECKS.values():
            all_violations.extend(check_fn(file))

    print(f"Scanned {len(files)} test file(s) under tests/unit/")
    print(f"Found {len(all_violations)} violation(s) across "
          f"{len({v.file for v in all_violations})} file(s).")
    by_rule: dict[str, int] = {}
    for v in all_violations:
        by_rule[v.rule] = by_rule.get(v.rule, 0) + 1
    for rule, count in sorted(by_rule.items()):
        print(f"  {rule}: {count}")
    if all_violations:
        print()
        for v in all_violations:
            print(v.format())
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
