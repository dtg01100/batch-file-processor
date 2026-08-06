"""Test-hygiene meta-test.

This meta-test asks: do the test files in the project conform to the
project's testing conventions documented in ``tests/AGENTS.md`` and the
broader project ``AGENTS.md``?

The runner walks every test layer except ``meta`` (the runners
themselves) and ``convert_backends`` (no test files yet) — see
``tests/meta/_layers.py`` for the source of truth.

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

Coverage scope (current):

- Walks every layer except ``meta`` and ``convert_backends`` (see
  ``tests/meta/_layers.py``). ``meta`` is excluded because each
  runner's own self-check covers it; ``convert_backends`` has no
  test files yet.
- Test marker enforcement is out of scope: the project relies on
  directory conventions (146 of 153 unit files have no marker), and
  marker drift is not a bug. A future check that validates directory
  placement is a separate concern.

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

# Layer registry. The single source of truth for which directories under
# ``tests/`` the meta-test runners walk. Defined in ``_layers.py`` so the
# runners, the report, and the layer-aware CLI summary all stay in sync.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _layers import (  # type: ignore[import-not-found]
    Layer,
    iter_scanned_test_files,
    scanned_layers,
)

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
        return f"{rel}:{self.line} [{self.rule}] {self.message}\n" f"    {self.source}"


# ---------------------------------------------------------------------------
# File enumeration.
# ---------------------------------------------------------------------------


def _iter_scanned_test_paths() -> list[Path]:
    """Return every absolute test file path the runner should walk.

    Walks every layer except ``meta`` (the runners themselves) and
    ``convert_backends`` (no test files yet). See ``_layers.py`` for
    the source of truth and the rationale for each exclusion. Paths
    are returned as absolute paths relative to ``PROJECT_ROOT`` so
    callers can ``relative_to(PROJECT_ROOT)`` for display.
    """
    return [(PROJECT_ROOT / rel).resolve() for rel, _layer in iter_scanned_test_files()]


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

# MagicMock assertion methods. This project's convention is to verify every
# ``MagicMock(spec=...)`` interaction with an explicit ``assert_called*``
# call (hermetic-real-shape tests skill, pitfall #9). These method names
# only exist on ``unittest.mock.Mock``, so matching on the attribute name
# is safe for any receiver expression — there is no realistic
# ``assert_called_once`` method on a non-mock object.
_MOCK_ASSERT_METHODS: frozenset[str] = frozenset(
    {
        "assert_called_with",
        "assert_called_once_with",
        "assert_called_once",
        "assert_not_called",
        "assert_any_call",
        "assert_has_calls",
    }
)

# unittest.TestCase assertion family. Require an explicit ``self.`` receiver
# so a hypothetical ``obj.assertSomething()`` helper (which does not exist
# in stdlib) is not mistaken for an assertion.
_UNITTEST_ASSERT_METHODS: frozenset[str] = frozenset(
    {
        "assertIsNotNone",
        "assertTrue",
        "assertFalse",
        "assertIs",
        "assertIsNot",
        "assertIsInstance",
        "assertNotIsInstance",
        "assertEqual",
        "assertNotEqual",
        "assertIn",
        "assertNotIn",
        "assertGreater",
        "assertGreaterEqual",
        "assertLess",
        "assertLessEqual",
        "assertRaises",
        "assertRaisesRegex",
        "assertWarns",
        "assertWarnsRegex",
        "assertAlmostEqual",
        "assertNotAlmostEqual",
        "assertDictEqual",
        "assertListEqual",
        "assertTupleEqual",
        "assertSetEqual",
        "assertMultiLineEqual",
        "assertSequenceEqual",
        "assertCountEqual",
        "assertRegex",
        "assertNotRegex",
        "assertLogs",
    }
)


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
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                if node.func.value.id == "pytest" and node.func.attr in {
                    "fail",
                    "raises",
                    "warns",
                    "skip",
                }:
                    self.found = True
            if node.func.attr in _MOCK_ASSERT_METHODS:
                self.found = True
            if node.func.attr in _UNITTEST_ASSERT_METHODS and (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id == "self"
            ):
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
                ) or ctx.func.attr.startswith(("assert", "wait")):
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

    # Walk every test_* function in the file — top-level OR nested in
    # a class body. The previous version filtered to top-level only
    # via ``tree.body``, which silently skipped methods inside
    # ``class TestX:`` blocks. ``ast.walk`` already recurses into
    # class bodies, so we just need to drop the filter and let it
    # find every test_* function. Fixtures are still excluded by
    # ``_is_fixture``.
    test_functions: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith("test_"):
            continue
        if node.name == "test_":  # bare `def test_(...):` is rare but skip
            continue
        if _is_fixture(node):
            continue
        test_functions.append(node)

    for node in test_functions:
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
            and isinstance(node.args[0], (ast.Constant, ast.JoinedStr))
            and (
                not isinstance(node.args[0], ast.Constant)
                or isinstance(node.args[0].value, str)
            )
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


def _is_bare_except(handler: ast.ExceptHandler) -> bool:
    """True for ``except:`` or ``except Exception:``-style handlers.

    Narrow handlers (``except ValueError:``,
    ``except (KeyError, TypeError):``) are NOT considered bare;
    they catch a specific exception class and the developer's
    intent is documented by the class name.
    """
    # No exception type at all: `except:`
    if handler.type is None:
        return True
    # Multiple names: `except (A, B):` — at least one must be the
    # generic ``Exception`` or ``BaseException`` for it to be bare.
    if isinstance(handler.type, ast.Tuple):
        for elt in handler.type.elts:
            if _is_generic_exception(elt):
                return True
        return False
    return _is_generic_exception(handler.type)


def _is_generic_exception(node: ast.expr) -> bool:
    """True if the node is ``Exception`` or ``BaseException``.

    Catches both ``Exception`` and ``BaseException`` as bare-style
    handlers. Anything else (``ValueError``, ``OSError``, etc.)
    is a narrow handler.
    """
    if isinstance(node, ast.Name) and node.id in {"Exception", "BaseException"}:
        return True
    if isinstance(node, ast.Attribute) and node.attr in {"Exception", "BaseException"}:
        return True
    return False


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
        # Skip narrow handlers — they're documented intent, not
        # silent error swallowing.
        if not _is_bare_except(node):
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
# Check:
NOQA_PATTERN = "# noqa"
NOQA_JUSTIFIED_RE = re.compile(r"#\s*noqa\s*:\s*[A-Z]+\d*\s*[—-]+\s*\S")


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
                message=NOQA_VIOLATION_MSG,
                source=line.strip(),
            )
        )
    return violations


NOQA_VIOLATION_MSG = (
    "# noqa without justification - append ': CODE - reason' "
    "(em-dash or hyphen separator) to make the suppression auditable"
)


# ---------------------------------------------------------------------------
# Check: assert X is True / assert X is False.
# ---------------------------------------------------------------------------
#
# The ``assert X is True`` pattern is an idiomatic smell: the explicit
# comparison against a bool literal provides no additional coverage over
# ``assert X``, and the comparator ``is`` (identity) is technically
# correct only if X is guaranteed to be exactly ``True`` or ``False``
# (not just truthy). When X is a numpy scalar, pandas value, or any
# custom truthy type, ``is True`` silently fails. The fix is one of:
#
#   assert X              # when only truthiness matters
#   assert X == expected  # when equality matters
#   assert X is True      # when X is guaranteed to be exactly True
#                         # (rare; cite the invariant)
#
# The runner does NOT flag every ``is True`` — it flags those that
# appear inside assert statements, where the smell combines with the
# assert's tautological nature (``assert truthy is True`` is a
# no-op for any truthy value).
# ---------------------------------------------------------------------------


def _check_assert_is_bool_comparison(file: Path) -> list[Violation]:
    try:
        source = file.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source)
    except SyntaxError:
        return []

    violations: list[Violation] = []
    source_lines = source.splitlines()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assert):
            continue
        test = node.test
        # Detect: assert <expr> is True / is False
        if not isinstance(test, ast.Compare):
            continue
        if len(test.ops) != 1:
            continue
        op = test.ops[0]
        if not isinstance(op, ast.Is):
            continue
        if len(test.comparators) != 1:
            continue
        rhs = test.comparators[0]
        # Narrow: only flag bare `assert <name> is True/False`. Attribute
        # access (``assert obj.flag is True``) and chained expressions
        # document which property is being tested, so dropping ``is True``
        # would lose signal. Bare ``Name`` is the pure tautology case
        # where ``assert x`` is strictly clearer than ``assert x is True``.
        if not isinstance(test.left, ast.Name):
            continue
        if not isinstance(rhs, ast.Constant) or (
            rhs.value is not True and rhs.value is not False
        ):
            continue
        if 1 <= node.lineno <= len(source_lines):
            src = source_lines[node.lineno - 1].strip()
        else:
            src = ""
        literal = "True" if rhs.value is True else "False"
        violations.append(
            Violation(
                file=file,
                line=node.lineno,
                rule="assert_is_bool_comparison",
                message=(
                    f"assert X is {literal} is redundant for truthy/falsy "
                    f"values; prefer 'assert X' or 'assert X == {literal}' "
                    f"if equality is the contract"
                ),
                source=src,
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
# Check: magic padding (e.g. "00" + x).
# ---------------------------------------------------------------------------
#
# AGENTS.md anti-patterns table:
#
#   Magic padding "00" + x  | Locale-dependent, unreadable
#                           | Use x.zfill(2) or f"{x:02d}"
#
# The smell is concatenating a string of zeros to a variable for
# zero-padding. The lint fires on ``Add`` where the left operand is a
# string literal matching ``^[0]+$`` and the right is a Name or
# Attribute (not another literal — those are normal concatenation).
# String-repetition ``"0" * 32`` is excluded (different operator: ``Mult``).
# ---------------------------------------------------------------------------


def _check_magic_padding(file: Path) -> list[Violation]:
    try:
        source = file.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source)
    except SyntaxError:
        return []

    violations: list[Violation] = []
    source_lines = source.splitlines()
    for node in ast.walk(tree):
        if not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.Add):
            continue
        if (
            not isinstance(node.left, ast.Constant)
            or not isinstance(node.left.value, str)
            or not re.fullmatch(r"0+", node.left.value)
            or not isinstance(node.right, (ast.Name, ast.Attribute))
        ):
            continue
        src = (
            source_lines[node.lineno - 1].strip()
            if 1 <= node.lineno <= len(source_lines)
            else ""
        )
        if src.startswith("#"):
            continue
        violations.append(
            Violation(
                file=file,
                line=node.lineno,
                rule="magic_padding",
                message=(
                    "'\"00\" + x' is locale-sensitive zero-padding; use "
                    'f"{x:02d}" for ints or x.zfill(N) for strings '
                    "(AGENTS.md anti-patterns)"
                ),
                source=src,
            )
        )
    return violations


# ---------------------------------------------------------------------------
# Check: tuple-return lambda trick ((expr, None)[1]).
# ---------------------------------------------------------------------------
#
# AGENTS.md anti-patterns table:
#
#   Tuple-return lambda trick (expr, None)[1] | Obfuscatory
#                                            | Use named helper function
#
# The smell is returning a value from a function by stuffing it into a
# tuple with a None sentinel and then indexing. Detected when a
# ``Subscript`` has a 2-element ``Tuple`` value containing exactly one
# ``None`` (literal or Name) and the other element is something else,
# with the slice being literal ``0`` or ``1``.
# ---------------------------------------------------------------------------


def _check_tuple_subscript_trick(file: Path) -> list[Violation]:
    try:
        source = file.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source)
    except SyntaxError:
        return []

    violations: list[Violation] = []
    source_lines = source.splitlines()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Subscript):
            continue
        if not isinstance(node.value, ast.Tuple) or len(node.value.elts) != 2:
            continue

        def _is_none(elt: ast.expr) -> bool:
            return (isinstance(elt, ast.Constant) and elt.value is None) or (
                isinstance(elt, ast.Name) and elt.id == "None"
            )

        none_count = sum(1 for e in node.value.elts if _is_none(e))
        if none_count != 1:
            continue

        index = node.slice
        if not isinstance(index, ast.Constant) or index.value not in (0, 1):
            continue

        src = (
            source_lines[node.lineno - 1].strip()
            if 1 <= node.lineno <= len(source_lines)
            else ""
        )
        violations.append(
            Violation(
                file=file,
                line=node.lineno,
                rule="tuple_subscript_trick",
                message=(
                    "(expr, None)[1] trick is obfuscatory; return the value "
                    "directly from a helper function (AGENTS.md anti-patterns)"
                ),
                source=src,
            )
        )
    return violations


# ---------------------------------------------------------------------------
# Check: nested try/except pyramid (3+ levels).
# ---------------------------------------------------------------------------
#
# AGENTS.md anti-patterns table:
#
#   Nested try/except pyramid (3+ levels) | Hard to follow
#                                       | Use 'stage' variable with single
#                                         try/except
#
# Detected by walking the AST and tracking a chain of enclosing
# ``ast.Try`` nodes. A node is added to the chain only if it has at
# least one ``except`` handler (a try/finally isn't nesting for this
# purpose). When the chain reaches length 3, the inner-most node is
# reported. Skip chains that contain a bare-except-pass anywhere — that
# is a different anti-pattern already covered by ``bare_except_pass``;
# the pyramid lint would just double-flag it.
# ---------------------------------------------------------------------------


def _check_nested_try_pyramid(file: Path) -> list[Violation]:
    try:
        source = file.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source)
    except SyntaxError:
        return []

    violations: list[Violation] = []
    source_lines = source.splitlines()

    def _has_bare_except_pass(try_node: ast.Try) -> bool:
        for handler in try_node.handlers:
            if handler.type is None:
                if len(handler.body) == 1 and isinstance(handler.body[0], ast.Pass):
                    return True
                continue
            type_node = handler.type
            if isinstance(type_node, ast.Name) and type_node.id == "Exception":
                if len(handler.body) == 1 and isinstance(handler.body[0], ast.Pass):
                    return True
        return False

    def visit(node: ast.AST, chain: list[ast.Try]) -> None:
        new_chain = chain
        if isinstance(node, ast.Try) and node.handlers:
            new_chain = [*chain, node]
            if len(new_chain) >= 3 and not any(
                _has_bare_except_pass(t) for t in new_chain
            ):
                src = (
                    source_lines[node.lineno - 1].strip()
                    if 1 <= node.lineno <= len(source_lines)
                    else ""
                )
                if not any(
                    v.rule == "nested_try_pyramid" and v.line == node.lineno
                    for v in violations
                ):
                    violations.append(
                        Violation(
                            file=file,
                            line=node.lineno,
                            rule="nested_try_pyramid",
                            message=(
                                "try/except nested 3+ levels deep; flatten "
                                "with a 'stage' variable (AGENTS.md "
                                "anti-patterns)"
                            ),
                            source=src,
                        )
                    )
        children: list[ast.AST] = list(ast.iter_child_nodes(node))
        for child in children:
            visit(child, new_chain)

    visit(tree, [])
    return violations


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
    "assert_is_bool_comparison": _check_assert_is_bool_comparison,
    "magic_padding": _check_magic_padding,
    "tuple_subscript_trick": _check_tuple_subscript_trick,
    "nested_try_pyramid": _check_nested_try_pyramid,
}


# ---------------------------------------------------------------------------
# Auditability allowlist. An entry is
# (relpath, rule, line, reason). It silences a violation that has been
# manually verified to be intentional. Each entry cites the source line
# as evidence. A typo fails closed: an unknown (file, rule, line) tuple
# does NOT match the lookup and the violation is reported normally.
# ---------------------------------------------------------------------------


KNOWN_HYGIENE_VIOLATIONS: list[tuple[str, str, int, str]] = [
    # Sentinel-class catch in a try/finally test. The test deliberately
    # raises an internal `_TestFailed` exception to verify that the
    # `finally` block in `context_timer()` runs. Catching it with `pass`
    # is the only way to inspect `timer.duration_ms` after the raise.
    # The flag (silent error swallowing) is the test's mechanism, not
    # a real bug.
    (
        "tests/unit/core/utils/test_timing_utils.py",
        "bare_except_pass",
        96,
        "sentinel catch of internal `_TestFailed` in try/finally test; "
        "the only way to assert the `finally` block ran",
    ),
    # Optional-dependency probe in build-configuration importability
    # test. `__import__(module)` may raise ImportError when an optional
    # dep is absent; we collect and report these as a separate list
    # (the test only fails if errors is non-empty at the end). The
    # `pass` is intentional: the goal is "can be imported", not
    # "imports cleanly".
    (
        "tests/unit/test_build_configuration.py",
        "bare_except_pass",
        193,
        "optional-dep ImportError probe in __import__(module); "
        "collected and reported as `errors` list, not silently lost",
    ),
    (
        "tests/unit/test_build_configuration.py",
        "bare_except_pass",
        195,
        "same try/except as L193 — broad Exception catch is the "
        "outer guard for the optional-dep import probe",
    ),
    # AST parse failure on `py_file` content. SyntaxError on a vendored
    # .py file is not a test failure; the test continues and the AST
    # walk skips the file. The `pass` is the documented behaviour.
    (
        "tests/unit/test_build_configuration.py",
        "bare_except_pass",
        298,
        "SyntaxError swallow in AST parse of vendored .py file; "
        "documented as 'not a test failure' in the loop comment",
    ),
    (
        "tests/unit/test_build_configuration.py",
        "bare_except_pass",
        300,
        "outer Exception catch in the same open()+ast.parse() block; "
        "guards against OSError on unreadable vendored files",
    ),
    # Optional PIL/Pillow + zxing dep probe. The test runs only if
    # pyzbar is available; if not, the helper returns None and the
    # caller asserts a skip. ImportError is the documented
    # opt-dep-missing case.
    (
        "tests/unit/test_convert_to_scansheet_type_a.py",
        "bare_except_pass",
        53,
        "optional PIL/zxing ImportError probe; helper returns None "
        "and the caller pytest.skip()s the test",
    ),
    # Optional yaml dep probe. The helper tries stdlib yaml first,
    # then invoke's vendored yaml. Both ImportError catches are
    # documented fallbacks; if both fail, the helper returns {}.
    (
        "tests/unit/test_golden_output.py",
        "bare_except_pass",
        315,
        "stdlib yaml ImportError probe; falls through to invoke's "
        "vendored yaml, then returns {} if both absent",
    ),
    (
        "tests/unit/test_golden_output.py",
        "bare_except_pass",
        324,
        "invoke.vendor.yaml ImportError probe; same fallback chain " "as L315",
    ),
    # Integration-layer sleep calls. All four are in explicit polling
    # helpers whose entire job is "wait for a real external thing to
    # become ready, with a deadline". The pattern is the same as the
    # unit test_timing_utils.SlowBackend test fixture: bounded by a
    # timeout, polling a real signal, fail-fast on deadline. The
    # ``time.sleep`` is the only way to do this without busy-waiting
    # the CPU; the helper docstring documents the contract.
    (
        "tests/integration/test_edi_sample_files.py",
        "sleep_call",
        95,
        "_wait_for_server: bounded poll for a real socket connect, "
        "raises RuntimeError on timeout; helper is the documented "
        "pattern for waiting on real servers",
    ),
    (
        "tests/integration/test_edi_sample_files.py",
        "sleep_call",
        108,
        "_wait_for_messages: bounded poll for handler.messages to "
        "reach count; same pattern as _wait_for_server",
    ),
    (
        "tests/integration/test_ftp_smtp_live_servers.py",
        "sleep_call",
        70,
        "_wait_for_server: bounded poll for a real socket connect; "
        "same pattern as test_edi_sample_files L95",
    ),
    (
        "tests/integration/test_ftp_smtp_live_servers.py",
        "sleep_call",
        83,
        "_wait_for_messages: bounded poll for handler.messages; "
        "same pattern as test_edi_sample_files L108",
    ),
    (
        "tests/integration/test_log_email_comprehensive.py",
        "sleep_call",
        110,
        "_wait_until: bounded poll with deadline; helper docstring "
        "states it replaces fixed time.sleep() with a deterministic "
        "deadline, so a faster handler doesn't slow the suite and a "
        "slower one fails fast",
    ),
    (
        "tests/integration/test_multi_folder_edge_cases.py",
        "sleep_call",
        93,
        "SlowBackend.send: explicit artificial-delay class for "
        "testing concurrency/race conditions; class name and "
        "docstring declare the intent",
    ),
    (
        "tests/integration/test_multi_folder_edge_cases.py",
        "sleep_call",
        420,
        "same SlowBackend.send pattern as L93",
    ),
    (
        "tests/integration/test_multi_folder_edge_cases.py",
        "sleep_call",
        430,
        "same SlowBackend.send pattern as L93",
    ),
    # UPC-A -> EAN-13 conversion. The literal "0" is not zero-padding
    # to a fixed width — it is a domain-specific prefix that converts
    # the 12-digit UPC-A into the 13-digit EAN-13 barcode format the
    # pyzbar decoder expects. ``"0" + upc`` is the canonical,
    # self-documenting way to express the conversion; ``upc.zfill(13)``
    # would silently zero-pad shorter UPCs and produce the wrong
    # barcode for a UPC-A that doesn't already start with "0". The
    # comment on each line states the conversion explicitly.
    (
        "tests/unit/test_convert_to_scansheet_type_a.py",
        "magic_padding",
        69,
        "UPC-A -> EAN-13 prefix conversion (not zero-padding to width); "
        "see test docstring 'UPC-A is encoded as EAN-13 (12 digits -> "
        "13 digits with leading zero)'",
    ),
    (
        "tests/unit/test_convert_to_scansheet_type_a.py",
        "magic_padding",
        91,
        "same UPC-A -> EAN-13 conversion as L69",
    ),
    (
        "tests/unit/test_convert_to_scansheet_type_a.py",
        "magic_padding",
        96,
        "same UPC-A -> EAN-13 conversion as L69 (list comprehension)",
    ),
    # ---- tests/integration/test_automatic_and_single_mode.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/integration/test_automatic_and_single_mode.py",
        "missing_assert",
        400,
        "class-body method; test_overlay_called_during_processing has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/integration/test_automatic_and_single_mode.py",
        "missing_assert",
        417,
        "class-body method; test_single_folder_overlay_text has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/integration/test_automatic_and_single_mode.py",
        "missing_assert",
        497,
        "class-body method; test_refresh_called_after_graphical_process has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/integration/test_automatic_and_single_mode.py",
        "missing_assert",
        512,
        "class-body method; test_refresh_users_list_destroys_and_recreates has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/integration/test_gui_user_workflows.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/integration/test_gui_user_workflows.py",
        "missing_assert",
        250,
        "class-body method; test_edit_email_settings_workflow has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/integration/test_gui_user_workflows.py",
        "missing_assert",
        277,
        "class-body method; test_edit_backup_settings_workflow has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/integration/test_gui_user_workflows.py",
        "missing_assert",
        292,
        "class-body method; test_process_single_folder_workflow has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/integration/test_gui_user_workflows.py",
        "missing_assert",
        309,
        "class-body method; test_process_all_folders_workflow has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/integration/test_gui_user_workflows.py",
        "missing_assert",
        333,
        "class-body method; test_maintenance_dialog_workflow has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/integration/test_gui_user_workflows.py",
        "missing_assert",
        345,
        "class-body method; test_database_import_workflow has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/integration/test_gui_user_workflows.py",
        "missing_assert",
        1232,
        "class-body method; test_view_processed_files_workflow has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/integration/test_gui_user_workflows.py",
        "missing_assert",
        1289,
        "class-body method; test_resend_dialog_workflow has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/integration/test_gui_user_workflows.py",
        "missing_assert",
        1509,
        "class-body method; test_folder_not_found_workflow has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/integration/test_gui_user_workflows.py",
        "missing_assert",
        1588,
        "class-body method; test_dialog_cleanup has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/integration/test_pipeline_logging_validation.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/integration/test_pipeline_logging_validation.py",
        "missing_assert",
        376,
        "class-body method; test_handler_with_none_run_log_discards_silently has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/interface/plugins/test_interfaces.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/interface/plugins/test_interfaces.py",
        "missing_assert",
        169,
        "class-body method; test_concrete_plugin_lifecycle_methods has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/qt/test_backend_gui_communication.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/qt/test_backend_gui_communication.py",
        "missing_assert",
        39,
        "class-body method; test_toggle_active_folder_disables_it has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_backend_gui_communication.py",
        "missing_assert",
        57,
        "class-body method; test_toggle_inactive_folder_without_backends_shows_error has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_backend_gui_communication.py",
        "missing_assert",
        75,
        "class-body method; test_toggle_inactive_folder_with_backend_enables_it has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/qt/test_comprehensive_ui.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/qt/test_comprehensive_ui.py",
        "missing_assert",
        625,
        "class-body method; test_ui_service_show_info has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_comprehensive_ui.py",
        "missing_assert",
        636,
        "class-body method; test_ui_service_show_warning has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_comprehensive_ui.py",
        "missing_assert",
        647,
        "class-body method; test_ui_service_show_error has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_comprehensive_ui.py",
        "missing_assert",
        801,
        "class-body method; test_app_refresh_folders has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/qt/test_database_import_dialog_extra.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/qt/test_database_import_dialog_extra.py",
        "missing_assert",
        271,
        "class-body method; test_on_error has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_database_import_dialog_extra.py",
        "missing_assert",
        404,
        "class-body method; test_import_thread_run_handles_exception has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_database_import_dialog_extra.py",
        "missing_assert",
        590,
        "class-body method; test_migration_job_migrate_folder_no_match_inserts has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/qt/test_edit_folders_dialog.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/qt/test_edit_folders_dialog.py",
        "missing_assert",
        530,
        "class-body method; test_select_copy_directory_uses_existing_as_initial has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_edit_folders_dialog.py",
        "missing_assert",
        559,
        "class-body method; test_copy_config_with_no_selection_does_nothing has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/qt/test_edit_folders_helpers.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/qt/test_edit_folders_helpers.py",
        "missing_assert",
        160,
        "class-body method; test_handle_convert_format_changed_dispatches_fallback_builders has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_edit_folders_helpers.py",
        "missing_assert",
        211,
        "class-body method; test_handle_convert_format_changed_uses_plugin_builder has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_edit_folders_helpers.py",
        "missing_assert",
        380,
        "class-body method; test_on_ok_calls_dialog_private_handler_when_present has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_edit_folders_helpers.py",
        "missing_assert",
        397,
        "class-body method; test_on_ok_success_calls_callback_and_accept has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_edit_folders_helpers.py",
        "missing_assert",
        451,
        "class-body method; test_noop_event_handler_methods_are_callable has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/qt/test_gui_stress_and_edge_cases.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/qt/test_gui_stress_and_edge_cases.py",
        "missing_assert",
        298,
        "class-body method; test_apply_with_none_callbacks has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_gui_stress_and_edge_cases.py",
        "missing_assert",
        1257,
        "class-body method; test_set_defaults_action_no_crash has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_gui_stress_and_edge_cases.py",
        "missing_assert",
        1269,
        "class-body method; test_add_directory_action_no_crash has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_gui_stress_and_edge_cases.py",
        "missing_assert",
        1290,
        "class-body method; test_maintenance_action_no_crash has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/qt/test_qt_app.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/qt/test_qt_app.py",
        "missing_assert",
        57,
        "class-body method; test_shutdown_closes_database has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_app.py",
        "missing_assert",
        65,
        "class-body method; test_shutdown_no_db_no_error has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_app.py",
        "missing_assert",
        71,
        "class-body method; test_set_main_button_states_no_folders has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_app.py",
        "missing_assert",
        84,
        "class-body method; test_set_main_button_states_with_folders has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_app.py",
        "missing_assert",
        99,
        "class-body method; test_disable_folder has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_app.py",
        "missing_assert",
        118,
        "class-body method; test_delete_folder_confirmed has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_app.py",
        "missing_assert",
        130,
        "class-body method; test_delete_folder_cancelled has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_app.py",
        "missing_assert",
        153,
        "class-body method; test_update_reporting has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_app.py",
        "missing_assert",
        164,
        "class-body method; test_graphical_process_directories_shows_error_for_missing_folder has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_app.py",
        "missing_assert",
        190,
        "class-body method; test_graphical_process_directories_shows_error_when_no_active_folders has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_app.py",
        "missing_assert",
        211,
        "class-body method; test_graphical_process_directories_processes_active_folders has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_app.py",
        "missing_assert",
        251,
        "class-body method; test_automatic_process_directories_delegates_to_run_coordinator has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_app.py",
        "missing_assert",
        329,
        "class-body method; test_mark_active_as_processed_wrapper_calls_maintenance has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_app.py",
        "missing_assert",
        388,
        "class-body method; test_run_shows_window_and_executes_qapplication has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_app.py",
        "missing_assert",
        403,
        "class-body method; test_edit_folder_selector_shows_error_when_missing has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_app.py",
        "missing_assert",
        487,
        "class-body method; test_batch_add_folders_returns_when_no_selection has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_app.py",
        "missing_assert",
        537,
        "class-body method; test_select_folder_existing_folder_opens_edit_dialog has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_app.py",
        "missing_assert",
        566,
        "class-body method; test_automatic_process_directories_calls_process_and_exits has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_app.py",
        "missing_assert",
        594,
        "class-body method; test_select_folder_adds_new_folder_and_marks_processed has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_app.py",
        "missing_assert",
        622,
        "class-body method; test_show_dialog_wrappers_create_and_exec has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_app.py",
        "missing_assert",
        772,
        "class-body method; test_refresh_users_list_no_panel_is_noop has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_app.py",
        "missing_assert",
        1060,
        "class-body method; test_process_directories_calls_dispatch_and_handles_success has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_app.py",
        "missing_assert",
        1090,
        "class-body method; test_process_directories_shows_info_on_errors_in_graphical_mode has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_app.py",
        "missing_assert",
        1194,
        "class-body method; test_on_folder_edit_applied_updates_database has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_app.py",
        "missing_assert",
        1407,
        "class-body method; test_show_edit_settings_dialog_opens_dialog has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_app.py",
        "missing_assert",
        1536,
        "class-body method; test_open_edit_dialog_apply_success_persists_and_refreshes has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_app.py",
        "missing_assert",
        1572,
        "class-body method; test_open_edit_dialog_cancel_does_not_refresh has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_app.py",
        "missing_assert",
        1600,
        "class-body method; test_edit_folder_selector_existing_opens_dialog has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_app.py",
        "missing_assert",
        1618,
        "class-body method; test_select_folder_existing_user_declines_no_dialog has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_app.py",
        "missing_assert",
        1645,
        "class-body method; test_select_folder_new_user_skips_mark_processed has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_app.py",
        "missing_assert",
        1674,
        "class-body method; test_batch_add_folders_cancelled_confirmation_skips_manager_calls has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_app.py",
        "missing_assert",
        1704,
        "class-body method; test_delete_folder_confirmed_triggers_refresh_and_button_state has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_app.py",
        "missing_assert",
        1752,
        "class-body method; test_show_resend_dialog_skips_exec_when_dialog_not_ready has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_app.py",
        "missing_assert",
        1780,
        "class-body method; test_show_edit_settings_dialog_callback_wiring has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_app.py",
        "missing_assert",
        2038,
        "class-body method; test_select_folder_ignores_nonexistent_selection has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/qt/test_qt_dialogs.py (class-body methods, surfaced 2026-07-16;
    #      line numbers updated 2026-08-05 after deleting test_apply_does_nothing) ----
    (
        "tests/qt/test_qt_dialogs.py",
        "missing_assert",
        417,
        "class-body method; test_construction has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_dialogs.py",
        "missing_assert",
        467,
        "class-body method; test_apply_calls_callback has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_dialogs.py",
        "missing_assert",
        539,
        "class-body method; test_construction has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_dialogs.py",
        "missing_assert",
        547,
        "class-body method; test_apply_calls_callbacks has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_dialogs.py",
        "missing_assert",
        580,
        "class-body method; test_apply_disables_email_backends_when_email_off has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_dialogs.py",
        "missing_assert",
        602,
        "class-body method; test_construction has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_dialogs.py",
        "missing_assert",
        690,
        "class-body method; test_construction has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_dialogs.py",
        "missing_assert",
        748,
        "class-body method; test_export_calls_shared_function has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_dialogs.py",
        "missing_assert",
        763,
        "class-body method; test_export_noop_when_no_folder_selected has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_dialogs.py",
        "missing_assert",
        780,
        "class-body method; test_export_noop_when_no_output_folder has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_dialogs.py",
        "missing_assert",
        1096,
        "class-body method; test_construction has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_dialogs.py",
        "missing_assert",
        1161,
        "class-body method; test_date_range_filter_applies_to_service_calls has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/qt/test_qt_dialogs.py",
        "missing_assert",
        1407,
        "class-body method; test_no_selection_initially has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/qt/test_qt_widgets.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/qt/test_qt_widgets.py",
        "missing_assert",
        217,
        "class-body method; test_empty_table has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/qt/test_resend_dialog_extra.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/qt/test_resend_dialog_extra.py",
        "missing_assert",
        286,
        "class-body method; test_apply_resend_flags has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/adapters/db2ssh/test_db2ssh_connection.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/adapters/db2ssh/test_db2ssh_connection.py",
        "missing_assert",
        196,
        "class-body method; test_execute_closes_cursor has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/adapters/sqlite/repositories/test_sqlite_folder_repo.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/adapters/sqlite/repositories/test_sqlite_folder_repo.py",
        "missing_assert",
        89,
        "class-body method; test_find_all_not_active_only_does_not_call_find has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/adapters/sqlite/repositories/test_sqlite_folder_repo.py",
        "missing_assert",
        245,
        "class-body method; test_delegates_to_table_delete has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/adapters/sqlite/repositories/test_sqlite_processed_files_repo.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/adapters/sqlite/repositories/test_sqlite_processed_files_repo.py",
        "missing_assert",
        49,
        "class-body method; test_inserts_processedfile has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/adapters/sqlite/repositories/test_sqlite_settings_repo.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/adapters/sqlite/repositories/test_sqlite_settings_repo.py",
        "missing_assert",
        36,
        "class-body method; test_delegates_to_update_default_settings has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/adapters/sqlite/repositories/test_sqlite_settings_repo.py",
        "missing_assert",
        68,
        "class-body method; test_delegates_to_db_set_setting has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/backend/test_file_operations.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/backend/test_file_operations.py",
        "missing_assert",
        75,
        "class-body method; test_makedirs_exist_ok has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/backend/test_ftp_client.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/backend/test_ftp_client.py",
        "missing_assert",
        53,
        "class-body method; test_connect_creates_ftps_connection_when_tls has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/backend/test_ftp_client.py",
        "missing_assert",
        63,
        "class-body method; test_connect_with_timeout has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/backend/test_ftp_client.py",
        "missing_assert",
        89,
        "class-body method; test_cwd_delegates_to_connection has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/backend/test_ftp_client.py",
        "missing_assert",
        103,
        "class-body method; test_storbinary_delegates_to_connection has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/backend/test_ftp_client.py",
        "missing_assert",
        151,
        "class-body method; test_set_pasv_delegates_to_connection has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/backend/test_smtp_client.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/backend/test_smtp_client.py",
        "missing_assert",
        49,
        "class-body method; test_starttls_delegates_to_connection has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/backend/test_smtp_client.py",
        "missing_assert",
        63,
        "class-body method; test_login_delegates_to_connection has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/backend/test_smtp_client.py",
        "missing_assert",
        99,
        "class-body method; test_send_message_delegates_to_connection has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/backend/test_smtp_client.py",
        "missing_assert",
        152,
        "class-body method; test_ehlo_delegates_to_connection has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/backend/test_smtp_client.py",
        "missing_assert",
        166,
        "class-body method; test_set_debuglevel_delegates_to_connection has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/backend/test_smtp_client.py",
        "missing_assert",
        203,
        "class-body method; test_from_config_without_auth has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/core/database/test_query_runner.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/core/database/test_query_runner.py",
        "missing_assert",
        56,
        "class-body method; test_close_does_nothing has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/core/database/test_query_runner.py",
        "missing_assert",
        99,
        "class-body method; test_close_delegates_to_connection has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/core/database/test_query_runner.py",
        "missing_assert",
        225,
        "class-body method; test_assert_read_only_accepts_select has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/core/database/test_query_runner.py",
        "missing_assert",
        229,
        "class-body method; test_assert_read_only_accepts_with has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/core/database/test_query_runner.py",
        "missing_assert",
        265,
        "class-body method; test_assert_read_only_accepts_multiple_select_statements has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/core/database/test_query_runner.py",
        "missing_assert",
        269,
        "class-body method; test_assert_read_only_rejects_semicolon_in_string_literal has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/core/database/test_query_runner.py",
        "missing_assert",
        285,
        "class-body method; test_assert_read_only_rejects_empty_statement_after_semicolon has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/core/edi/test_inv_fetcher.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/core/edi/test_inv_fetcher.py",
        "missing_assert",
        190,
        "class-body method; test_fetch_uom_desc_caches_uom_lut has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/dispatch/observability/test_alert_dispatcher.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/dispatch/observability/test_alert_dispatcher.py",
        "missing_assert",
        41,
        "class-body method; test_dispatch_never_raises has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/dispatch/pipeline/test_pipeline_interfaces.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/dispatch/pipeline/test_pipeline_interfaces.py",
        "missing_assert",
        41,
        "class-body method; test_record_error_no_handler_silently_returns has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/dispatch/services/test_folder_processor.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/dispatch/services/test_folder_processor.py",
        "missing_assert",
        348,
        "class-body method; test_record_processed_file_handles_error has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/dispatch/test_error_handler_alert_integration.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/dispatch/test_error_handler_alert_integration.py",
        "missing_assert",
        28,
        "class-body method; test_record_error_skips_alert_when_dispatcher_none has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/dispatch/test_error_handler_alert_integration.py",
        "missing_assert",
        51,
        "class-body method; test_record_error_skips_alert_when_alert_on_failure_false has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/dispatch_tests/test_interfaces.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/dispatch_tests/test_interfaces.py",
        "missing_assert",
        215,
        "class-body method; test_database_insert_many_method has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/dispatch_tests/test_interfaces.py",
        "missing_assert",
        221,
        "class-body method; test_database_update_method has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/dispatch_tests/test_interfaces.py",
        "missing_assert",
        284,
        "class-body method; test_filesystem_mkdir has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/dispatch_tests/test_interfaces.py",
        "missing_assert",
        290,
        "class-body method; test_filesystem_makedirs has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/dispatch_tests/test_interfaces.py",
        "missing_assert",
        296,
        "class-body method; test_filesystem_copy_file has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/dispatch_tests/test_interfaces.py",
        "missing_assert",
        302,
        "class-body method; test_filesystem_remove_file has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/dispatch_tests/test_interfaces.py",
        "missing_assert",
        451,
        "class-body method; test_log_close has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/dispatch_tests/test_interfaces.py",
        "missing_assert",
        496,
        "class-body method; test_incomplete_database_not_instance has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/dispatch_tests/test_log_sender.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/dispatch_tests/test_log_sender.py",
        "missing_assert",
        173,
        "class-body method; test_null_ui_does_nothing has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/dispatch_tests/test_log_sender.py",
        "missing_assert",
        226,
        "class-body method; test_send_log_with_mock_ui has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/dispatch_tests/test_orchestrator.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/dispatch_tests/test_orchestrator.py",
        "missing_assert",
        329,
        "class-body method; test_process_file_with_validation has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/dispatch_tests/test_send_manager.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/dispatch_tests/test_send_manager.py",
        "missing_assert",
        283,
        "class-body method; test_send_via_module_copy has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/dispatch_tests/test_send_manager.py",
        "missing_assert",
        300,
        "class-body method; test_send_via_module_ftp has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/dispatch_tests/test_send_manager.py",
        "missing_assert",
        316,
        "class-body method; test_send_via_module_email has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/dispatch_tests/test_services.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/dispatch_tests/test_services.py",
        "missing_assert",
        211,
        "class-body method; test_update_does_nothing has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/dispatch_tests/test_services.py",
        "missing_assert",
        219,
        "class-body method; test_update_with_empty_values has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/interface/database/test_database_obj.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/interface/database/test_database_obj.py",
        "missing_assert",
        124,
        "class-body method; test_set_setting has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/interface/database/test_database_obj.py",
        "missing_assert",
        149,
        "class-body method; test_update_default_settings has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/interface/database/test_database_obj.py",
        "missing_assert",
        160,
        "class-body method; test_close_calls_connection_close has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/interface/database/test_database_obj.py",
        "missing_assert",
        160,
        "class-body method; test_close_with_no_connection has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/interface/operations/test_folder_manager.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/interface/operations/test_folder_manager.py",
        "missing_assert",
        268,
        "class-body method; test_get_all_folders_with_order has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/interface/operations/test_folder_manager.py",
        "missing_assert",
        488,
        "class-body method; test_add_folder_uses_oversight_defaults_provider has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/interface/qt/test_database_import_dialog.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/interface/qt/test_database_import_dialog.py",
        "missing_assert",
        207,
        "class-body method; test_migrate_folder_no_match_skips_update has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/interface/qt/test_dialog_contracts_wave4.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/interface/qt/test_dialog_contracts_wave4.py",
        "missing_assert",
        303,
        "class-body method; test_resend_toggle_error_uses_show_error_helper has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/interface/qt/test_edit_settings_dialog.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/interface/qt/test_edit_settings_dialog.py",
        "missing_assert",
        644,
        "class-body method; test_test_connection_button_invokes_smtp_service has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/interface/qt/test_edit_settings_dialog.py",
        "missing_assert",
        990,
        "class-body method; test_apply_calls_on_apply_callback has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/interface/qt/test_edit_settings_dialog.py",
        "missing_assert",
        1011,
        "class-body method; test_apply_calls_refresh_callback has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/interface/qt/test_edit_settings_dialog.py",
        "missing_assert",
        1032,
        "class-body method; test_ok_button_validates_and_applies has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/interface/qt/test_edit_settings_dialog.py",
        "missing_assert",
        1055,
        "class-body method; test_ok_button_fails_validation has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/interface/qt/test_edit_settings_dialog.py",
        "missing_assert",
        1080,
        "class-body method; test_cancel_button_closes_dialog has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/interface/qt/test_edit_settings_dialog.py",
        "missing_assert",
        1103,
        "class-body method; test_disabling_email_disables_backends has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/interface/qt/test_qt_app.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/interface/qt/test_qt_app.py",
        "missing_assert",
        135,
        "class-body method; test_initialize_creates_window has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/interface/qt/test_qt_app.py",
        "missing_assert",
        696,
        "class-body method; test_shutdown_closes_database has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/interface/qt/test_qt_app.py",
        "missing_assert",
        716,
        "class-body method; test_shutdown_handles_no_database has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/interface/qt/test_resend_dialog.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/interface/qt/test_resend_dialog.py",
        "missing_assert",
        68,
        "class-body method; test_dialog_initializes_service has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/interface/test_ports.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/interface/test_ports.py",
        "missing_assert",
        61,
        "class-body method; test_show_info_is_noop has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/interface/test_ports.py",
        "missing_assert",
        67,
        "class-body method; test_show_error_is_noop has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/interface/test_ports.py",
        "missing_assert",
        73,
        "class-body method; test_show_warning_is_noop has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/interface/test_ports.py",
        "missing_assert",
        139,
        "class-body method; test_pump_events_is_noop has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/interface/test_ports.py",
        "missing_assert",
        164,
        "class-body method; test_show_info_delegates_to_qmessagebox has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/interface/test_ports.py",
        "missing_assert",
        173,
        "class-body method; test_show_error_delegates_to_qmessagebox has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/interface/test_ports.py",
        "missing_assert",
        182,
        "class-body method; test_show_warning_delegates_to_qmessagebox has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/interface/test_ports.py",
        "missing_assert",
        412,
        "class-body method; test_pump_events_delegates_to_process_events has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/interface/validation/test_email_validator.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/interface/validation/test_email_validator.py",
        "missing_assert",
        281,
        "class-body method; test_trailing_separator has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/test_batch_log_sender.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/test_batch_log_sender.py",
        "missing_assert",
        447,
        "class-body method; test_attachment_fallback_to_octet_stream has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_batch_log_sender.py",
        "missing_assert",
        493,
        "class-body method; test_attachment_with_encoding_not_none has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/test_convert_to_estore_einvoice_generic.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/test_convert_to_estore_einvoice_generic.py",
        "missing_assert",
        1134,
        "class-body method; test_qty_to_int_positive has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_convert_to_estore_einvoice_generic.py",
        "missing_assert",
        1140,
        "class-body method; test_qty_to_int_negative has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/test_converter_edge_cases.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/test_converter_edge_cases.py",
        "missing_assert",
        345,
        "class-body method; test_convert_to_yellowdog_csv_empty_file has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_converter_edge_cases.py",
        "missing_assert",
        631,
        "class-body method; test_convert_to_scansheet_type_a_empty_file has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_converter_edge_cases.py",
        "missing_assert",
        1194,
        "class-body method; test_convert_to_fintech_empty_upc_lut_raises_key_error has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/test_dispatch_interfaces.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/test_dispatch_interfaces.py",
        "missing_assert",
        40,
        "class-body method; test_database_runtime_checkable has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_dispatch_interfaces.py",
        "missing_assert",
        254,
        "class-body method; test_file_system_runtime_checkable has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_dispatch_interfaces.py",
        "missing_assert",
        627,
        "class-body method; test_backend_runtime_checkable has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_dispatch_interfaces.py",
        "missing_assert",
        753,
        "class-body method; test_validator_runtime_checkable has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_dispatch_interfaces.py",
        "missing_assert",
        870,
        "class-body method; test_error_handler_runtime_checkable has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_dispatch_interfaces.py",
        "missing_assert",
        1116,
        "class-body method; test_log_runtime_checkable has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/test_edit_dialog/test_edit_settings_dialog.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/test_edit_dialog/test_edit_settings_dialog.py",
        "missing_assert",
        109,
        "class-body method; test_dialog_calls_settings_provider_on_init has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_edit_dialog/test_edit_settings_dialog.py",
        "missing_assert",
        423,
        "class-body method; test_apply_calls_update_settings has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_edit_dialog/test_edit_settings_dialog.py",
        "missing_assert",
        432,
        "class-body method; test_apply_calls_update_oversight has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_edit_dialog/test_edit_settings_dialog.py",
        "missing_assert",
        441,
        "class-body method; test_apply_calls_on_apply has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_edit_dialog/test_edit_settings_dialog.py",
        "missing_assert",
        450,
        "class-body method; test_apply_calls_refresh_callback has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_edit_dialog/test_edit_settings_dialog.py",
        "missing_assert",
        459,
        "class-body method; test_apply_calls_all_callbacks has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_edit_dialog/test_edit_settings_dialog.py",
        "missing_assert",
        523,
        "class-body method; test_apply_disables_email_backends_when_email_off has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_edit_dialog/test_edit_settings_dialog.py",
        "missing_assert",
        539,
        "class-body method; test_apply_does_not_disable_backends_when_email_on has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/test_edit_dialog/test_field_coverage.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/test_edit_dialog/test_field_coverage.py",
        "missing_assert",
        494,
        "class-body method; test_all_config_fields_have_extractors has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_edit_dialog/test_field_coverage.py",
        "missing_assert",
        658,
        "class-body method; test_database_columns_match_config has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_edit_dialog/test_field_coverage.py",
        "missing_assert",
        721,
        "class-body method; test_no_orphan_config_fields has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/test_folder_db_roundtrip.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/test_folder_db_roundtrip.py",
        "missing_assert",
        45,
        "class-body method; test_insert_and_read_folder_with_plugin_configs has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_folder_db_roundtrip.py",
        "missing_assert",
        61,
        "class-body method; test_update_folder_plugin_configurations_via_mapper has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/test_folders_database_migrator.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/test_folders_database_migrator.py",
        "missing_assert",
        86,
        "class-body method; test_migration_handles_none_config_folder has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/test_form_generator.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/test_form_generator.py",
        "missing_assert",
        96,
        "class-body method; test_field_visibility has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/test_golden_output.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/test_golden_output.py",
        "missing_assert",
        842,
        "class-body method; test_nested_structure has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/test_http_backend.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/test_http_backend.py",
        "missing_assert",
        403,
        "class-body method; test_http_backend_class_cleanup has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/test_plugins/test_configuration_plugin.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/test_plugins/test_configuration_plugin.py",
        "missing_assert",
        25,
        "class-body method; test_interface_exists has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_configuration_plugin.py",
        "missing_assert",
        36,
        "class-body method; test_get_configuration_schema has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_configuration_plugin.py",
        "missing_assert",
        117,
        "class-body method; test_plugin_creation has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_configuration_plugin.py",
        "missing_assert",
        123,
        "class-body method; test_static_properties has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_configuration_plugin.py",
        "missing_assert",
        135,
        "class-body method; test_get_config_fields has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_configuration_plugin.py",
        "missing_assert",
        146,
        "class-body method; test_configuration_schema has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_configuration_plugin.py",
        "missing_assert",
        161,
        "class-body method; test_validate_config has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_configuration_plugin.py",
        "missing_assert",
        177,
        "class-body method; test_validate_invalid_config has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_configuration_plugin.py",
        "missing_assert",
        192,
        "class-body method; test_create_config has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_configuration_plugin.py",
        "missing_assert",
        222,
        "class-body method; test_create_config_with_defaults has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_configuration_plugin.py",
        "missing_assert",
        233,
        "class-body method; test_serialize_config has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_configuration_plugin.py",
        "missing_assert",
        263,
        "class-body method; test_deserialize_config has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_configuration_plugin.py",
        "missing_assert",
        293,
        "class-body method; test_plugin_lifecycle has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/test_plugins/test_form_generator_plugins.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/test_plugins/test_form_generator_plugins.py",
        "missing_assert",
        22,
        "class-body method; test_form_generator_with_csv_config_schema has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_form_generator_plugins.py",
        "missing_assert",
        31,
        "class-body method; test_csv_config_schema_completeness has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_form_generator_plugins.py",
        "missing_assert",
        54,
        "class-body method; test_csv_config_field_types has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_form_generator_plugins.py",
        "missing_assert",
        74,
        "class-body method; test_csv_config_default_values has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_form_generator_plugins.py",
        "missing_assert",
        90,
        "class-body method; test_get_default_configuration has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_form_generator_plugins.py",
        "missing_assert",
        106,
        "class-body method; test_schema_validation_for_csv_config has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_form_generator_plugins.py",
        "missing_assert",
        124,
        "class-body method; test_empty_config_validation has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_form_generator_plugins.py",
        "missing_assert",
        141,
        "class-body method; test_create_widget_method has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_form_generator_plugins.py",
        "missing_assert",
        158,
        "class-body method; test_create_widget_with_parent has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_form_generator_plugins.py",
        "missing_assert",
        181,
        "class-body method; test_create_widget_with_config has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_form_generator_plugins.py",
        "missing_assert",
        212,
        "class-body method; test_create_configuration_widget_from_manager has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/test_plugins/test_plugin_base.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/test_plugins/test_plugin_base.py",
        "missing_assert",
        88,
        "class-body method; test_plugin_creation has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_base.py",
        "missing_assert",
        93,
        "class-body method; test_plugin_static_properties has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_base.py",
        "missing_assert",
        102,
        "class-body method; test_plugin_lifecycle has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_base.py",
        "missing_assert",
        117,
        "class-body method; test_plugin_configuration has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_base.py",
        "missing_assert",
        143,
        "class-body method; test_invalid_configuration_update has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_base.py",
        "missing_assert",
        159,
        "class-body method; test_compatibility_check has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_base.py",
        "missing_assert",
        163,
        "class-body method; test_dependencies has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_base.py",
        "missing_assert",
        167,
        "class-body method; test_validate_configuration_without_schema_succeeds has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_base.py",
        "missing_assert",
        176,
        "class-body method; test_get_default_configuration_without_schema_returns_empty_dict has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_base.py",
        "missing_assert",
        184,
        "class-body method; test_update_configuration_invalid_does_not_call_initialize has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_base.py",
        "missing_assert",
        194,
        "class-body method; test_update_configuration_valid_calls_initialize_once has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/test_plugins/test_plugin_configuration_mapper.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/test_plugins/test_plugin_configuration_mapper.py",
        "missing_assert",
        33,
        "class-body method; test_initialize_state has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_configuration_mapper.py",
        "missing_assert",
        47,
        "class-body method; test_update_state has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_configuration_mapper.py",
        "missing_assert",
        64,
        "class-body method; test_update_state_no_change has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_configuration_mapper.py",
        "missing_assert",
        77,
        "class-body method; test_undo has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_configuration_mapper.py",
        "missing_assert",
        95,
        "class-body method; test_redo has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_configuration_mapper.py",
        "missing_assert",
        114,
        "class-body method; test_undo_empty_stack has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_configuration_mapper.py",
        "missing_assert",
        119,
        "class-body method; test_redo_empty_stack has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_configuration_mapper.py",
        "missing_assert",
        124,
        "class-body method; test_mark_saved has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_configuration_mapper.py",
        "missing_assert",
        139,
        "class-body method; test_reset_to_saved has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_configuration_mapper.py",
        "missing_assert",
        156,
        "class-body method; test_get_all_configs has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_configuration_mapper.py",
        "missing_assert",
        174,
        "class-body method; test_get_invalid_sections has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_configuration_mapper.py",
        "missing_assert",
        191,
        "class-body method; test_get_all_validation_errors has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_configuration_mapper.py",
        "missing_assert",
        213,
        "class-body method; test_can_undo_property has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_configuration_mapper.py",
        "missing_assert",
        226,
        "class-body method; test_can_redo_property has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_configuration_mapper.py",
        "missing_assert",
        240,
        "class-body method; test_clear has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_configuration_mapper.py",
        "missing_assert",
        262,
        "class-body method; test_init has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_configuration_mapper.py",
        "missing_assert",
        268,
        "class-body method; test_get_supported_plugin_formats has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_configuration_mapper.py",
        "missing_assert",
        274,
        "class-body method; test_get_plugin_configuration_fields has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_configuration_mapper.py",
        "missing_assert",
        280,
        "class-body method; test_serialize_plugin_config has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_configuration_mapper.py",
        "missing_assert",
        289,
        "class-body method; test_deserialize_plugin_config has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_configuration_mapper.py",
        "missing_assert",
        301,
        "class-body method; test_roundtrip_serialization has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_configuration_mapper.py",
        "missing_assert",
        311,
        "class-body method; test_validate_plugin_configurations_from_dict has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_configuration_mapper.py",
        "missing_assert",
        323,
        "class-body method; test_state_manager_integration has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_configuration_mapper.py",
        "missing_assert",
        345,
        "class-body method; test_get_state_manager has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_configuration_mapper.py",
        "missing_assert",
        363,
        "class-body method; test_populate_plugin_widgets_from_dict has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_configuration_mapper.py",
        "missing_assert",
        380,
        "class-body method; test_update_folder_configuration_from_dict has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_configuration_mapper.py",
        "missing_assert",
        403,
        "class-body method; test_creation has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_configuration_mapper.py",
        "missing_assert",
        415,
        "class-body method; test_default_validation_errors has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_configuration_mapper.py",
        "missing_assert",
        425,
        "class-body method; test_creation has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_configuration_mapper.py",
        "missing_assert",
        435,
        "class-body method; test_default_values has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/test_plugins/test_plugin_manager_configuration.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/test_plugins/test_plugin_manager_configuration.py",
        "missing_assert",
        23,
        "class-body method; test_initialization has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_manager_configuration.py",
        "missing_assert",
        36,
        "class-body method; test_discover_configuration_plugins has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_manager_configuration.py",
        "missing_assert",
        62,
        "class-body method; test_get_configuration_plugins has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_manager_configuration.py",
        "missing_assert",
        70,
        "class-body method; test_get_configuration_plugin_by_format has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_manager_configuration.py",
        "missing_assert",
        99,
        "class-body method; test_get_configuration_plugin_by_format_name has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_manager_configuration.py",
        "missing_assert",
        132,
        "class-body method; test_create_configuration_widget has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_manager_configuration.py",
        "missing_assert",
        146,
        "class-body method; test_validate_configuration has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_manager_configuration.py",
        "missing_assert",
        163,
        "class-body method; test_create_configuration has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_manager_configuration.py",
        "missing_assert",
        178,
        "class-body method; test_serialize_configuration has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_manager_configuration.py",
        "missing_assert",
        194,
        "class-body method; test_deserialize_configuration has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_manager_configuration.py",
        "missing_assert",
        211,
        "class-body method; test_get_configuration_fields has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_manager_configuration.py",
        "missing_assert",
        230,
        "class-body method; test_unsupported_format_handling has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_manager_configuration.py",
        "missing_assert",
        257,
        "class-body method; test_initialize_plugins_is_idempotent has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_manager_configuration.py",
        "missing_assert",
        304,
        "class-body method; test_initialize_order_is_initialize_then_activate_with_config has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/test_plugins/test_plugin_mapper_form_integration.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/test_plugins/test_plugin_mapper_form_integration.py",
        "missing_assert",
        18,
        "class-body method; test_form_generator_integration has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_mapper_form_integration.py",
        "missing_assert",
        59,
        "class-body method; test_state_manager_with_multiple_formats has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_mapper_form_integration.py",
        "missing_assert",
        78,
        "class-body method; test_undo_redo_with_multiple_formats has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_mapper_form_integration.py",
        "missing_assert",
        101,
        "class-body method; test_update_folder_with_multiple_plugins has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_mapper_form_integration.py",
        "missing_assert",
        128,
        "class-body method; test_serialize_deserialize_roundtrip has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_mapper_form_integration.py",
        "missing_assert",
        145,
        "class-body method; test_validation_state_tracking has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_mapper_form_integration.py",
        "missing_assert",
        168,
        "class-body method; test_empty_plugin_configurations has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_mapper_form_integration.py",
        "missing_assert",
        180,
        "class-body method; test_legacy_folder_config_dict has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_plugin_mapper_form_integration.py",
        "missing_assert",
        196,
        "class-body method; test_plugin_config_migration has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/test_plugins/test_section_registry.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/test_plugins/test_section_registry.py",
        "missing_assert",
        78,
        "class-body method; test_register_get_and_count has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_section_registry.py",
        "missing_assert",
        90,
        "class-body method; test_get_all_sections_sorted_by_priority has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_section_registry.py",
        "missing_assert",
        99,
        "class-body method; test_unregister_removes_section_and_renderer has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_section_registry.py",
        "missing_assert",
        109,
        "class-body method; test_register_plugin_section_and_filter_after_unregister has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_plugins/test_section_registry.py",
        "missing_assert",
        135,
        "class-body method; test_clear_resets_state has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/test_schema.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/test_schema.py",
        "missing_assert",
        513,
        "class-body method; test_handles_existing_plugin_configurations_column has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_schema.py",
        "missing_assert",
        541,
        "class-body method; test_handles_query_error_gracefully has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    (
        "tests/unit/test_schema.py",
        "missing_assert",
        564,
        "class-body method; test_handles_all_errors_silently has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- tests/unit/test_structured_logging.py (class-body methods, surfaced 2026-07-16) ----
    (
        "tests/unit/test_structured_logging.py",
        "missing_assert",
        364,
        "class-body method; test_func has no load-bearing assertion (was invisible to the runner pre-2026-07-16)",
    ),
    # ---- Smoke no-op allowlist (2026-08-05) ----
    # Post-26bfcb904 the missing_assert runner recognizes
    # mock.assert_called_* and unittest self.assertX, dropping its
    # false positives. These 9 are genuine smoke no-ops: the body
    # invokes a method and exits with no result observation.
    (
        "tests/unit/dispatch_tests/test_services.py",
        "missing_assert",
        219,
        "legitimate smoke - NullProgressReporter.update invoked, no result observation",
    ),
    (
        "tests/unit/dispatch_tests/test_services.py",
        "missing_assert",
        232,
        "legitimate smoke - NullProgressReporter.update empty values, no observation",
    ),
    (
        "tests/unit/interface/database/test_database_obj.py",
        "missing_assert",
        174,
        "legitimate smoke - close() on unset connection must not raise, no observation",
    ),
    (
        "tests/unit/test_structured_logging.py",
        "missing_assert",
        364,
        "nested helper named test_func inside @logged test; outer scope asserts result",
    ),
    (
        "tests/integration/test_gui_user_workflows.py",
        "missing_assert",
        333,
        "legitimate smoke - patched maintenance dialog opened, no result observation",
    ),
    (
        "tests/integration/test_gui_user_workflows.py",
        "missing_assert",
        345,
        "legitimate smoke - patched database import dialog opened, no result observation",
    ),
    (
        "tests/integration/test_gui_user_workflows.py",
        "missing_assert",
        1232,
        "legitimate smoke - patched processed-files dialog opened, no result observation",
    ),
    (
        "tests/integration/test_gui_user_workflows.py",
        "missing_assert",
        1588,
        "legitimate smoke - patched edit-settings dialog exec'd, no result observation",
    ),
    (
        "tests/qt/test_qt_app.py",
        "missing_assert",
        772,
        "legitimate smoke - _refresh_users_list no-op with no right panel, no observation",
    ),
]


def _is_known_hygiene_violation(file: Path, rule: str, line: int) -> bool:
    """Return True if (file, rule, line) is in the allowlist.

    ``file`` is matched by relative path string. The runner's caller
    passes the path the check function was invoked with; this helper
    resolves it the same way for the lookup.
    """
    try:
        rel = str(file.relative_to(PROJECT_ROOT))
    except ValueError:
        rel = str(file)
    for f, r, l, _reason in KNOWN_HYGIENE_VIOLATIONS:
        if f == rel and r == rule and l == line:
            return True
    return False


# Audit-mode flag. When True, KNOWN_HYGIENE_VIOLATIONS is NOT applied:
# every violation is reported, so the allowlist is re-validated
# end-to-end. Mirrors the ``--no-skip-known-equivalent`` flag on the
# mutation runner (``test_property_tests_are_sufficient.py``) and
# ``KNOWN_ASSERTION_EQUIVALENT`` on the assertion runner
# (``test_assertions_are_meaningful.py``).
_AUDIT_HYGIENE_VIOLATIONS: bool = "--no-skip-known-hygiene-violations" in sys.argv

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
        for f in _iter_scanned_test_paths()
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
    except Exception as exc:
        violations = [
            Violation(
                file=file,
                line=0,
                rule=check_name,
                message=f"check raised: {type(exc).__name__}: {exc}",
                source="",
            )
        ]

    # Filter allowlist. A violation matching an entry in
    # KNOWN_HYGIENE_VIOLATIONS is intentional and not reported as a
    # failure. The entry's reason is the audit trail; re-validate
    # periodically with --no-skip-known-hygiene-violations.
    if not _AUDIT_HYGIENE_VIOLATIONS:
        violations = [
            v
            for v in violations
            if not _is_known_hygiene_violation(v.file, v.rule, v.line)
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
        "magic_padding",
        "tuple_subscript_trick",
        "nested_try_pyramid",
    }
    self_violations: list[Violation] = []
    for check_name, check_fn in CHECKS.items():
        if check_name in SELF_CHECK_SKIP:
            continue
        self_violations.extend(check_fn(self_path))

    if not self_violations:
        return

    formatted = "\n".join(v.format() for v in self_violations)
    pytest.fail("tests/meta/test_hygiene.py violates its own checks:\n" + formatted)


# ---------------------------------------------------------------------------
# CLI summary entry point.
# ---------------------------------------------------------------------------


def main() -> int:
    """Run all checks and print a summary. Returns 0 on success, 1 on any
    violation. Useful for CI integration or local auditing without
    pytest overhead.
    """
    files = _iter_scanned_test_paths()
    # Build a (path -> layer) map for the per-file layer attribution in
    # the layer_summary line. Paths are absolute, so we use the layer's
    # path (also absolute) for the lookup.
    layer_by_path: dict[Path, Layer] = {}
    for layer in scanned_layers():
        for f in layer.iter_files():
            layer_by_path[(PROJECT_ROOT / f).resolve()] = layer
    all_violations: list[Violation] = []
    for file in files:
        for check_fn in CHECKS.values():
            all_violations.extend(check_fn(file))
    if not _AUDIT_HYGIENE_VIOLATIONS:
        # Drop allowlisted violations (intentional exceptions, cited in
        # KNOWN_HYGIENE_VIOLATIONS). Run with
        # ``--no-skip-known-hygiene-violations`` to re-validate.
        before = len(all_violations)
        all_violations = [
            v
            for v in all_violations
            if not _is_known_hygiene_violation(v.file, v.rule, v.line)
        ]
        suppressed = before - len(all_violations)
    else:
        suppressed = 0
    by_layer: dict[str, int] = {}
    for path in files:
        layer = layer_by_path.get(path)
        if layer is not None:
            by_layer[layer.name] = by_layer.get(layer.name, 0) + 1
    layer_summary = ", ".join(f"{name}={n}" for name, n in sorted(by_layer.items()))
    print(f"Scanned {len(files)} test file(s) across layers: {layer_summary}")
    if suppressed:
        print(
            f"Suppressed {suppressed} allowlisted violation(s) "
            f"(see KNOWN_HYGIENE_VIOLATIONS; re-validate with "
            f"--no-skip-known-hygiene-violations)."
        )
    print(
        f"Found {len(all_violations)} violation(s) across "
        f"{len({v.file for v in all_violations})} file(s)."
    )
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
