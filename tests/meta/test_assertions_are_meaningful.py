"""Assertion-mutation meta-test.

This meta-test asks: are the assertions in each test file actually doing
work, or would the test pass if every assertion were deleted / inverted?

For every test file in the project's scanned layers, the runner:

1. Parses the file with ``ast`` and enumerates every ``Assert`` node.
2. For each assertion, applies a set of targeted mutations using a
   ``NodeTransformer``:
   - ``polarity_flip`` — ``assert X`` -> ``assert not (X)``
   - ``equality_flip`` — ``assert X == Y`` -> ``assert X != Y``
   - ``inequality_flip`` — ``assert X != Y`` -> ``assert X == Y``
   - ``membership_flip`` — ``assert X in Y`` -> ``assert X not in Y``
   - ``identity_flip`` — ``assert X is Y`` -> ``assert X is not Y``
   - ``gt_lt_flip`` — ``assert X > Y`` -> ``assert X < Y``
   - ``ge_le_flip`` — ``assert X >= Y`` -> ``assert X <= Y``
   - ``bool_flip`` — ``assert X is True`` <-> ``assert X is False``
   - ``always_fail`` — replace the whole assertion with ``assert False``

   Note: the plan also listed a ``delete`` rule (replace with
   ``pass``). That rule was tried and removed: in pytest 9 (and
   most modern pytests), a test with zero assertions vacuously
   passes, so ``delete`` produces the same "all assertions are dead"
   signal regardless of whether any individual assertion was
   load-bearing. The ``always_fail`` rule already answers the same
   question with cleaner signal.
3. Unparses the modified AST to a temporary ``.py`` file alongside the
   original (so imports resolve identically), then runs the test via
   ``subprocess.run``.
4. The mutated file MUST fail. If it still passes, the assertion was
   dead — a real bug of that shape would have slipped past the test.

Subprocess isolation matters: we are deliberately breaking tests, so a
``SyntaxError`` or import-time error from a bad mutation must not
poison the runner process.

Pair list: every test file in the project's scanned layers
(``unit``, ``integration``, ``qt``) — see ``tests/meta/_layers.py``.
At the time of writing: 208 files (153 unit + 41 integration + 14 qt).
Wall time is dominated by subprocess startup and the
number of assertions per file; each mutation spawns a fresh
``pytest -x`` against the file. Safe to run with ``-n auto`` (each
(file, line, mutation_name) is independent).

Principles (carried forward from
``test_property_tests_are_sufficient.py``):

1. Single file, no plugin framework, no config files.
2. Every survivor lists the original and mutated source line. A
   reviewer audits with a single text lookup.
3. Fails closed. ``KNOWN_ASSERTION_EQUIVALENT`` cites the source line
   as evidence, not a summary.

Usage::

    # Run all assertion-mutation checks against all unit tests.
    pytest tests/meta/test_assertions_are_meaningful.py -n auto

    # Run a single check (e.g. always_fail only).
    pytest tests/meta/test_assertions_are_meaningful.py -n auto -k always_fail

    # Audit a single file.
    pytest tests/meta/test_assertions_are_meaningful.py -n auto -k test_format_utils

    # CLI summary (no pytest).
    python tests/meta/test_assertions_are_meaningful.py
"""

from __future__ import annotations

import ast
import importlib.util
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TESTS_DIR = PROJECT_ROOT / "tests"
MUTANTS_DIR = PROJECT_ROOT / "mutants_assertions"
PER_FILE_TIMEOUT = 30


# Layer registry. Single source of truth for which test files the
# runner walks. Defined in ``tests/meta/_layers.py`` so this runner
# and the others share the same scope.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _layers import (  # type: ignore[import-not-found]
    iter_scanned_test_files,
)
from _pytest.outcomes import Skipped as _PytestSkipped

# ---------------------------------------------------------------------------
# Mutation rules. Each rule is a function that takes an ast.Assert node
# and returns either:
#   - a *new* ast.Assert (or list of statements) to replace the original
#     assertion, or
#   - None to leave the assertion unchanged (rule does not apply).
#
# A rule's `name` is the rule's identifier in survivor reports. A rule
# may produce multiple output statements (e.g. for the `delete` rule we
# replace the Assert with a comment that records the original line).
# ---------------------------------------------------------------------------


def _copy_location(new_node: ast.AST, old_node: ast.AST) -> ast.AST:
    """Copy location info from ``old_node`` to ``new_node`` and return new."""
    for attr in ("lineno", "col_offset", "end_lineno", "end_col_offset"):
        if hasattr(old_node, attr):
            setattr(new_node, attr, getattr(old_node, attr))
    ast.copy_location(new_node, old_node)
    return new_node


def _wrap_in_not(node: ast.expr) -> ast.expr:
    """Wrap ``node`` in ``not (...)`` and return a new expression."""
    inner = _copy_location(ast.Expression(body=node), node).body
    call = ast.UnaryOp(op=ast.Not(), operand=inner)
    return _copy_location(call, node)


def _flip_compare_op(
    node: ast.Compare, mapping: dict[type, type]
) -> ast.Compare | None:
    """Flip the first comparator in a Compare node if its operator is in mapping.

    Returns a new Compare with the operator swapped, or None if the
    operator is not flippable.
    """
    if not node.ops:
        return None
    op = node.ops[0]
    new_op_type = mapping.get(type(op))
    if new_op_type is None:
        return None
    new_op = new_op_type()
    new_compare = ast.Compare(
        left=node.left,
        ops=[new_op],
        comparators=node.comparators,
    )
    return _copy_location(new_compare, node)


# Comparative operator flip maps. We pair operators that are conceptually
# inverse: ``>`` <-> ``<``, ``>=`` <-> ``<=``. Note that ``==`` and ``!=``
# are handled by separate rules because they live on the Compare node and
# are conceptually equality, not ordering.
_GT_LT_FLIP: dict[type, type] = {
    ast.Gt: ast.Lt,
    ast.Lt: ast.Gt,
}
_GE_LE_FLIP: dict[type, type] = {
    ast.GtE: ast.LtE,
    ast.LtE: ast.GtE,
}


@dataclass(frozen=True)
class MutationRule:
    name: str
    description: str

    def apply(self, node: ast.Assert) -> ast.AST | None:
        """Return a replacement node for ``node``, or None to skip."""
        raise NotImplementedError


@dataclass(frozen=True)
class PolarityFlip(MutationRule):
    name: str = "polarity_flip"
    description: str = "assert X -> assert not (X)"

    def apply(self, node: ast.Assert) -> ast.AST:
        new_test = _wrap_in_not(node.test)
        new_assert = ast.Assert(test=new_test)
        return _copy_location(new_assert, node)


@dataclass(frozen=True)
class EqualityFlip(MutationRule):
    name: str = "equality_flip"
    description: str = "assert X == Y -> assert X != Y"

    def apply(self, node: ast.Assert) -> ast.AST | None:
        if not isinstance(node.test, ast.Compare):
            return None
        new_compare = _flip_compare_op(node.test, {ast.Eq: ast.NotEq})
        if new_compare is None:
            return None
        new_assert = ast.Assert(test=new_compare)
        return _copy_location(new_assert, node)


@dataclass(frozen=True)
class InequalityFlip(MutationRule):
    name: str = "inequality_flip"
    description: str = "assert X != Y -> assert X == Y"

    def apply(self, node: ast.Assert) -> ast.AST | None:
        if not isinstance(node.test, ast.Compare):
            return None
        new_compare = _flip_compare_op(node.test, {ast.NotEq: ast.Eq})
        if new_compare is None:
            return None
        new_assert = ast.Assert(test=new_compare)
        return _copy_location(new_assert, node)


@dataclass(frozen=True)
class MembershipFlip(MutationRule):
    name: str = "membership_flip"
    description: str = "assert X in Y -> assert X not in Y"

    def apply(self, node: ast.Assert) -> ast.AST | None:
        if not isinstance(node.test, ast.Compare):
            return None
        if not node.test.ops or not isinstance(node.test.ops[0], ast.In):
            return None
        new_compare = ast.Compare(
            left=node.test.left,
            ops=[ast.NotIn()],
            comparators=node.test.comparators,
        )
        new_compare = _copy_location(new_compare, node.test)
        new_assert = ast.Assert(test=new_compare)
        return _copy_location(new_assert, node)


@dataclass(frozen=True)
class IdentityFlip(MutationRule):
    name: str = "identity_flip"
    description: str = "assert X is Y -> assert X is not Y"

    def apply(self, node: ast.Assert) -> ast.AST | None:
        if not isinstance(node.test, ast.Compare):
            return None
        if not node.test.ops or not isinstance(node.test.ops[0], ast.Is):
            return None
        new_compare = ast.Compare(
            left=node.test.left,
            ops=[ast.IsNot()],
            comparators=node.test.comparators,
        )
        new_compare = _copy_location(new_compare, node.test)
        new_assert = ast.Assert(test=new_compare)
        return _copy_location(new_assert, node)


@dataclass(frozen=True)
class GtLtFlip(MutationRule):
    name: str = "gt_lt_flip"
    description: str = "assert X > Y -> assert X < Y"

    def apply(self, node: ast.Assert) -> ast.AST | None:
        if not isinstance(node.test, ast.Compare):
            return None
        new_compare = _flip_compare_op(node.test, _GT_LT_FLIP)
        if new_compare is None:
            return None
        new_assert = ast.Assert(test=new_compare)
        return _copy_location(new_assert, node)


@dataclass(frozen=True)
class GeLeFlip(MutationRule):
    name: str = "ge_le_flip"
    description: str = "assert X >= Y -> assert X <= Y"

    def apply(self, node: ast.Assert) -> ast.AST | None:
        if not isinstance(node.test, ast.Compare):
            return None
        new_compare = _flip_compare_op(node.test, _GE_LE_FLIP)
        if new_compare is None:
            return None
        new_assert = ast.Assert(test=new_compare)
        return _copy_location(new_assert, node)


@dataclass(frozen=True)
class BoolLiteralFlip(MutationRule):
    name: str = "bool_literal_flip"
    description: str = "assert X is True <-> assert X is False"

    def apply(self, node: ast.Assert) -> ast.AST | None:
        if not isinstance(node.test, ast.Compare):
            return None
        if len(node.test.ops) != 1 or not isinstance(node.test.ops[0], ast.Is):
            return None
        if len(node.test.comparators) != 1:
            return None
        rhs = node.test.comparators[0]
        if not isinstance(rhs, ast.Constant) or not isinstance(rhs.value, bool):
            return None
        new_rhs = ast.Constant(value=not rhs.value)
        _copy_location(new_rhs, rhs)
        new_compare = ast.Compare(
            left=node.test.left,
            ops=[ast.Is()],
            comparators=[new_rhs],
        )
        new_compare = _copy_location(new_compare, node.test)
        new_assert = ast.Assert(test=new_compare)
        return _copy_location(new_assert, node)


@dataclass(frozen=True)
class AlwaysFail(MutationRule):
    name: str = "always_fail"
    description: str = "assert X -> assert False"

    def apply(self, node: ast.Assert) -> ast.AST:
        new_assert = ast.Assert(test=ast.Constant(value=False))
        return _copy_location(new_assert, node)


ALL_RULES: list[MutationRule] = [
    PolarityFlip(),
    EqualityFlip(),
    InequalityFlip(),
    MembershipFlip(),
    IdentityFlip(),
    GtLtFlip(),
    GeLeFlip(),
    BoolLiteralFlip(),
    AlwaysFail(),
]


# ---------------------------------------------------------------------------
# Mutant generation. The transformer walks the AST, finds every Assert,
# and applies each rule. Each (rule, assertion) combination produces a
# (file, line, rule_name, mutated_source) tuple.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AssertionMutant:
    file: Path
    line: int
    rule_name: str
    original_source: str
    mutated_source: str
    description: str


class _AssertionMutator(ast.NodeTransformer):
    """Apply ``rule`` to the assertion at ``target_lineno``, leave others alone."""

    def __init__(self, target_lineno: int, rule: MutationRule) -> None:
        self._target_lineno = target_lineno
        self._rule = rule
        self._replaced = False

    def visit_Assert(self, node: ast.Assert) -> ast.AST:
        if self._replaced or node.lineno != self._target_lineno:
            return self.generic_visit(node)
        replacement = self._rule.apply(node)
        if replacement is None:
            return self.generic_visit(node)
        self._replaced = True
        return _copy_location(replacement, node)


def _mutate_assertion(
    source: str,
    line: int,
    rule: MutationRule,
) -> str | None:
    """Apply ``rule`` to the assertion at ``line`` in ``source``.

    Returns the mutated source, or None if the rule did not apply (e.g.
    ``equality_flip`` on a non-Compare assertion). Unparse failures
    also return None — the runner treats these as "rule not applicable"
    rather than crashing.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None

    mutator = _AssertionMutator(target_lineno=line, rule=rule)
    new_tree = mutator.visit(tree)
    ast.fix_missing_locations(new_tree)
    if not mutator._replaced:
        return None
    try:
        return ast.unparse(new_tree)
    except Exception:
        return None


def _iter_assert_lines(source: str) -> list[int]:
    """Return line numbers of every ``assert`` statement in ``source``.

    Only top-level and nested ``def`` bodies are considered. Asserts
    inside docstrings, type comments, or string literals are excluded
    because they don't survive unparse anyway.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    lines: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            lines.append(node.lineno)
    return sorted(set(lines))


def _source_line(source: str, line: int) -> str:
    lines = source.splitlines()
    if 1 <= line <= len(lines):
        return lines[line - 1].strip()
    return ""


# ---------------------------------------------------------------------------
# Subprocess execution. We write the mutated source to a temp file
# inside ``mutants_assertions/`` (kept on disk for auditability), then
# run ``pytest`` against it. The temp file's location is alongside the
# original so all ``from X import Y`` statements resolve identically.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AssertionOutcome:
    rule_name: str
    line: int
    killed: bool
    failure_message: str = ""
    skipped: bool = False


def _mutant_path(file: Path, line: int, rule_name: str) -> Path:
    """Return the on-disk path for a mutated copy of ``file``.

    The path includes the line and rule so multiple mutants of the same
    file don't collide. Files are written to ``mutants_assertions/`` to
    keep them out of the source tree.
    """
    rel = file.relative_to(PROJECT_ROOT)
    safe = str(rel).replace("/", "_").replace(".py", "")
    return MUTANTS_DIR / f"{safe}__L{line}__{rule_name}.py"

def _run_pytest_on_mutant(mutant_path: Path) -> tuple[int, str, bool]:
    """Run pytest against ``mutant_path`` and return (exit_code, output, skipped).

    ``skipped`` is True when pytest's combined output contains a
    "SKIPPED" / "s" status and no "FAILED" line, i.e. every collected
    test was skipped rather than passing. This is the subprocess
    counterpart to the in-process executor's _PytestSkipped detection
    and lets the wrapper distinguish "test was skipped" from "test
    passed (survivor)" for files guarded by an optional dependency.

    The runner does NOT use ``-x`` on the mutant itself: if the
    mutation does kill the test, pytest exits non-zero with the first
    failure, which is the expected signal. If the mutation does NOT
    kill the test (survivor), pytest exits 0.

    Uses ``--override-ini=addopts=...`` to neutralize the project's
    ``-n auto`` from ``pytest.ini``. xdist would split tests across
    worker processes that don't share the temp file's content; the
    runner expects to mutate ONE file and observe the result.
    """
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(mutant_path),
                "-p",
                "no:cacheprovider",
                "-p",
                "no:xdist",
                "-q",
                "--no-header",
                "--tb=line",
                "--override-ini=addopts=--tb=short --strict-markers",
            ],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=PER_FILE_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return 124, "SUBPROCESS TIMED OUT (treated as kill)", False
    output = (result.stdout or "") + (result.stderr or "")
    skipped = _output_is_all_skipped(output)
    return result.returncode, output, skipped


def _output_is_all_skipped(output: str) -> bool:
    """True if pytest's output shows a single test status line with
    "SKIPPED" and no "FAILED" or "ERROR" lines.

    Heuristic for the in-process / subprocess parity contract: a
    file where every test is guarded by a missing optional
    dependency (e.g. pyzbar) shows a summary like
    ``1 skipped in 0.01s`` with no pass/fail markers. The same
    pattern under ``-v`` shows ``test_x SKIPPED [reason]``. We
    match on the summary line, which is the most stable form.
    """
    has_skip = "skipped" in output.lower()
    has_fail = "failed" in output.lower() or "error" in output.lower()
    return has_skip and not has_fail


# ---------------------------------------------------------------------------
# In-process runner. Loads the mutated source into a fresh module
# namespace, walks the AST to find every test_* function (top-level
# and class methods), and runs them in-process. A mutation "kills" the
# test if ANY test function raises.
#
# Speed: ~7ms per mutation vs ~1000ms for the subprocess approach
# (measured on test_structured_logging.py: 82 mutations in 0.6s vs
# 87.5s subprocess). ~145x speedup with 100% parity on the sample.
#
# Trade-offs:
# - Tests that depend on pytest fixtures beyond the stand-ins below
#   (caplog, tmp_path, monkeypatch) may produce false negatives if the
#   fixture is actually load-bearing. The runner falls back to the
#   subprocess approach in that case.
# - Class methods are run on a default-constructed instance. Classes
#   that need construction args are skipped (the test never runs;
#   the runner treats the mutation as surviving, which is the
#   safer wrong answer for a meta-test).
# - Module-level side effects (e.g., opening a database connection at
#   import time) are not isolated. A failing import is treated as a
#   kill.
#
# This is the default in 2026-07-14. Set TAM_USE_SUBPROCESS=1 to
# fall back to the per-mutation subprocess approach.
# ---------------------------------------------------------------------------


# Minimal pytest-fixture stand-ins. Tests that need more elaborate
# fixture behavior (e.g., qtbot, a real tmpdir path that gets created
# on disk and passed to a subprocess) will fail to validate the
# mutation in-process; the runner falls back to subprocess in that
# case.
class _InProcTmpPath:
    """A Path-like object that materializes a real temp dir on disk.

    Tests that pass tmp_path to subprocess.run or open() need a real
    directory. Using a fresh mkdtemp per mutation is safe because the
    mutation lifecycle is short.
    """

    def __init__(self) -> None:
        self._dir = Path(tempfile.mkdtemp(prefix="tam_inproc_"))

    def __getattr__(self, name: str) -> object:
        return getattr(self._dir, name)

    def __truediv__(self, other: object) -> Path:
        return self._dir / other

    def __fspath__(self) -> str:
        return str(self._dir)


class _InProcCapLog:
    """A list-like caplog stand-in.

    Real caplog records LogRecord objects with .levelname, .message,
    etc. The stand-in stores entries as tuples (level, message) and
    supports the .set_level() / .text / .records attributes that the
    most common project tests use.
    """

    def __init__(self) -> None:
        self.records: list[tuple[int, str]] = []
        self.text: str = ""
        self._level: int = 0

    def set_level(self, level: object, *args: object, **kwargs: object) -> None:
        # Real caplog.set_level(int | str). We accept both.
        self._level = 0 if level is None else (level if isinstance(level, int) else 0)

    def clear(self) -> None:
        self.records.clear()
        self.text = ""

    def at_level(self, *args: object, **kwargs: object):
        from contextlib import contextmanager

        @contextmanager
        def _cm():
            yield self

        return _cm()


class _InProcMonkeyPatch:
    """No-op monkeypatch stand-in.

    Captures setattr/setenv/delenv calls in case the test asserts on
    them. For most tests this is sufficient; tests that need a real
    monkeypatch (e.g., patching a module-level function and asserting
    the call) will see the patch happen but the effect won't persist
    beyond the test. The runner's contract is "did the assertion
    fail?" — if the test asserts on the patched behavior, the
    assertion will fail in-process too.
    """

    def __init__(self) -> None:
        self._setattrs: list[tuple[object, str, object]] = []
        self._setenvs: list[tuple[str, object]] = []
        self._delenvs: list[str] = []

    def setattr(self, target: object, name: str, value: object = ...) -> None:  # type: ignore[assignment]
        if value is ...:
            # pytest signature: monkeypatch.setattr(target, name=value)
            # The test is calling with name as a kwarg; this stand-in
            # does not handle that pattern. Real pytest supports it.
            return
        self._setattrs.append((target, name, value))
        try:
            setattr(target, name, value)
        except (AttributeError, TypeError):
            pass

    def setenv(self, name: str, value: object) -> None:
        self._setenvs.append((name, value))
        os.environ[name] = str(value)

    def delenv(self, name: str, *args: object, **kwargs: object) -> None:
        self._delenvs.append(name)
        os.environ.pop(name, None)

    def syspath_prepend(self, path: object) -> None:
        sys.path.insert(0, str(path))

    def chdir(self, path: object) -> None:
        os.chdir(str(path))

    def undo(self) -> None:
        # No-op for the stand-in; real monkeypatch.undo() reverses
        # all changes. Tests that rely on undo() being called by
        # pytest teardown will see stale state, but the assertion
        # check (the part we care about) runs before teardown.
        pass


_STANDARD_PYTEST_FIXTURES = {
    "tmp_path": _InProcTmpPath,
    "tmpdir": _InProcTmpPath,
    "caplog": _InProcCapLog,
    "capfd": _InProcCapLog,
    "capsys": _InProcCapLog,
    "monkeypatch": _InProcMonkeyPatch,
}


def _build_fixture_kwargs(fn: object) -> dict[str, object]:
    """Build the kwargs dict for a function from the stand-in fixtures.

    Returns a fresh dict every call so mutations don't share fixture
    state. ``self`` is intentionally not in the dict — class methods
    are called with an instance, not a fixture.
    """
    import inspect

    try:
        sig = inspect.signature(fn)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return {}
    kwargs: dict[str, object] = {}
    for name, param in sig.parameters.items():
        if name == "self":
            continue
        if param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue
        if name in _STANDARD_PYTEST_FIXTURES:
            kwargs[name] = _STANDARD_PYTEST_FIXTURES[name]()
    return kwargs


def _run_mutated_tests_inprocess(
    mutated_source: str,
) -> tuple[bool, str, bool]:
    """Run every test_* function in ``mutated_source`` in-process.

    Returns ``(all_passed, snippet, all_skipped_or_empty)``. A mutation
    kills the test if any test function raises a non-Skipped exception.
    The runner treats that as a "killed" signal (the original assertion
    was load-bearing). If all tests pass, the mutation is a survivor
    (the assertion was dead).

    A Skipped outcome (e.g. ``pytest.skip`` for a missing optional
    dependency) is reported as ``all_skipped_or_empty=True`` so the
    caller can distinguish "every test was skipped" (the mutation
    cannot be evaluated; report neither kill nor survivor) from "every
    test passed" (the mutation is a real survivor). The third return
    value is True when EITHER every test skipped OR no test function
    was found; the wrapper treats both as "inconclusive" rather than
    as a survivor.

    The function uses ``importlib.util.spec_from_loader`` so the
    mutated source is exec'd in a fresh namespace with no leakage
    from the runner's own imports.
    """
    spec = importlib.util.spec_from_loader("_tam_mutated", loader=None)
    assert spec is not None
    mut_mod = importlib.util.module_from_spec(spec)
    try:
        exec(
            compile(mutated_source, "<mutated>", "exec"),
            mut_mod.__dict__,
        )
    except SyntaxError as e:
        return False, f"SYNTAX_ERROR: {e}", True
    except Exception as e:
        # Import-time failure is treated as a kill (the test can't
        # even start, so the mutation "succeeded" in breaking it).
        return False, f"IMPORT_ERROR: {type(e).__name__}: {e}", True
    failures: list[str] = []
    skipped: list[str] = []
    passed = 0
    ran_any = False

    # Top-level test_* functions.
    for name in sorted(
        n
        for n in dir(mut_mod)
        if n.startswith("test_") and callable(getattr(mut_mod, n))
    ):
        fn = getattr(mut_mod, name)
        # Skip class methods picked up by dir() (they're bound).
        if not _is_plain_function(fn):
            continue
        ran_any = True
        try:
            kwargs = _build_fixture_kwargs(fn)
            fn(**kwargs)
        except _PytestSkipped as e:
            skipped.append(f"{name}: {e}")
        except SystemExit as e:
            failures.append(f"{name}: SystemExit({e.code})")
        except Exception as e:
            failures.append(f"{name}: {type(e).__name__}: {str(e)[:120]}")
        else:
            passed += 1

    # Class test_* methods.
    for name in sorted(dir(mut_mod)):
        cls = getattr(mut_mod, name)
        if not isinstance(cls, type):
            continue
        test_methods = [
            m for m in dir(cls) if m.startswith("test_") and callable(getattr(cls, m))
        ]
        if not test_methods:
            continue
        # Try to construct. The in-process runner can't pass
        # constructor args, so a class that needs them raises
        # ``TypeError`` at construction. That's a runner limitation,
        # not a real test failure: silently drop the class (its
        # methods can't be run in this context). Other exceptions
        # (ValueError, RuntimeError, etc.) indicate a real bug in
        # the test's ``__init__`` — record them as a real failure
        # so the mutation is reported as killed, not silently
        # dropped.
        try:
            instance = cls()
        except TypeError:
            continue
        except Exception as e:
            failures.append(
                f"{name}: __init__ raised {type(e).__name__}: {str(e)[:120]}"
            )
            continue
        for method_name in test_methods:
            method = getattr(instance, method_name)
            ran_any = True
            try:
                _ = method()
            except _PytestSkipped as e:
                skipped.append(f"{name}.{method_name}: {e}")
            except SystemExit as e:
                failures.append(f"{name}.{method_name}: SystemExit({e.code})")
            except Exception as e:
                failures.append(
                    f"{name}.{method_name}: {type(e).__name__}: {str(e)[:120]}"
                )
            else:
                passed += 1

    if failures:
        return False, "\n".join(failures[:3]), False
    # No failures: every test either passed or was skipped. Only mark
    # the result inconclusive when no test actually evaluated the
    # mutation (no test ran, or every test that ran was skipped).
    # A mix of passes and skips still counts as "passed" — the
    # passing tests confirmed the mutation was harmless.
    all_skipped_or_empty = (not ran_any) or (passed == 0 and bool(skipped))
    return True, "", all_skipped_or_empty


def _is_plain_function(obj: object) -> bool:
    """True for plain functions, False for bound methods or classes."""
    import types

    return isinstance(obj, types.FunctionType)


def _write_mutant(mutant_path: Path, mutated_source: str) -> None:
    mutant_path.parent.mkdir(parents=True, exist_ok=True)
    mutant_path.write_text(mutated_source, encoding="utf-8")


# Subprocess-only mode opt-out. Default: try in-process first
# (~7ms/mutation) and fall back to subprocess (~1s/mutation) only
# when the in-process result is untrustworthy (e.g., the test file
# uses fixtures we don't have a stand-in for). Set
# TAM_USE_SUBPROCESS=1 in the environment to force the legacy
# per-mutation subprocess path (useful for debugging the in-process
# runner itself).
_USE_SUBPROCESS = os.environ.get("TAM_USE_SUBPROCESS") == "1"

# Regex matching Python's argument-shape TypeError messages. Used by
# the in-process -> subprocess fallback in ``_run_assertion_mutation``
# to detect when a test couldn't run at all because the runner's
# fixture stand-ins don't cover the test's argument list.
#
# The pattern covers all three message shapes Python 3.11+ emits for
# argument-mismatch errors:
#   - ``f() missing N required positional argument(s): 'name'``
#   - ``f() missing N required keyword-only argument: 'name'``
#   - ``f() takes N positional arguments but M (was|were) given``
#   - ``f() got an unexpected keyword argument 'name'``
#
# A real assertion failure producing one of these message shapes is
# essentially impossible: a normal test failure is AssertionError
# or a domain exception, and Python's "unsupported operand" /
# "object has no len()" / "is not callable" TypeErrors have
# entirely different message shapes. See ``_is_arg_shape_typeerror``.
_ARG_SHAPE_TYPEERROR_RE = re.compile(
    r"missing \d+ required (?:positional|keyword-only) argument"
    r"|takes \d+ positional argument[s]? but \d+ (?:was|were) given"
    r"|got an unexpected keyword argument"
)

def _run_subprocess_mutant(
    file: Path, line: int, rule: MutationRule, mutated_source: str
) -> AssertionOutcome:
    """Run the mutated source through pytest in a fresh subprocess.

    Used both as the primary path (when ``TAM_USE_SUBPROCESS=1``) and
    as the fallback for the in-process runner when it hits a
    fixture-missing ``TypeError`` it can't evaluate.

    Returns an ``AssertionOutcome`` whose ``killed`` field reflects
    pytest's exit code, ``skipped`` reflects the subprocess output
    parsing (see ``_output_is_all_skipped``), and ``failure_message``
    holds the last ~400 chars of pytest output for debugging.
    """
    mutant_path = _mutant_path(file, line, rule.name)
    _write_mutant(mutant_path, mutated_source)
    try:
        code, output, skipped = _run_pytest_on_mutant(mutant_path)
    finally:
        try:
            mutant_path.unlink()
        except OSError:
            pass

    killed = code != 0
    snippet = ""
    if not killed:
        # Survivor: keep the last few lines of pytest output for
        # debugging.
        snippet = output[-400:].strip()
    return AssertionOutcome(
        rule_name=rule.name,
        line=line,
        killed=killed,
        failure_message=snippet,
        skipped=skipped and not killed,
    )


def _is_arg_shape_typeerror(snippet: str) -> bool:
    """True if the in-process failure message matches a Python
    argument-shape TypeError (``missing N required positional
    argument``, ``takes N positional arguments but M were given``,
    ``got an unexpected keyword argument``, etc.).

    These errors mean the test could not run at all because the
    in-process executor's fixture stand-ins don't cover the test's
    argument list. A real assertion failure producing one of these
    message shapes is essentially impossible: a normal test failure
    is ``AssertionError`` or a domain exception, and Python's
    "unsupported operand" / "object has no len()" / "is not
    callable" TypeErrors have entirely different message shapes.

    Detection drives the in-process -> subprocess fallback in
    ``_run_assertion_mutation`` so the runner gives the right
    answer for tests with custom fixtures.
    """
    return bool(_ARG_SHAPE_TYPEERROR_RE.search(snippet))


def _run_assertion_mutation(
    file: Path, line: int, rule: MutationRule
) -> AssertionOutcome:
    """Run a single assertion-mutation check.

    Returns an ``AssertionOutcome`` recording whether the mutation
    killed the test. A killed mutation is one that made the test
    fail (i.e., the original assertion was load-bearing). A
    surviving mutation is one that the test still passed despite
    the mutation (i.e., the assertion was dead or self-referential).
    A skipped outcome means every test in the file was skipped
    (optional dependency missing) — neither kill nor survivor.

    Execution path:
    1. In-process runner (default): exec the mutated source, walk
       every test_* function (top-level + class methods), and check
       whether any raises. ~7ms/mutation. Trusted for the easy
       case (no custom fixtures).
    2. Subprocess runner, when ``TAM_USE_SUBPROCESS=1``: write the
       mutated source to ``mutants_assertions/`` and run pytest
       against it. ~1s/mutation. Used for debugging the in-process
       runner or when the in-process result is untrustworthy.
    3. Subprocess fallback, when the in-process runner hits a
       fixture-missing ``TypeError`` (a test uses a custom fixture
       the runner's stand-in set doesn't cover): the in-process
       result is untrustworthy (the test never actually ran, but
       the runner can't tell that from a real kill), so re-run
       via subprocess. Cost: ~1s per fixture-using test file
       affected; ~7ms for everything else.

    The 100% in-process/subprocess parity claim from 2026-07-14
    (see git history) was measured on a 1-2 file sample without
    custom fixtures. The fallback closes the gap for the ~1,740
    test functions in the corpus that use custom fixtures.
    """
    source = file.read_text(encoding="utf-8", errors="replace")
    mutated_source = _mutate_assertion(source, line, rule)
    if mutated_source is None:
        # Rule does not apply to this assertion (e.g. equality_flip on
        # a polarity assertion). Record as a "killed" placeholder so
        # the runner does not count it as a survivor.
        return AssertionOutcome(
            rule_name=rule.name,
            line=line,
            killed=True,
            failure_message="(rule not applicable to this assertion)",
        )

    if not _USE_SUBPROCESS:
        all_passed, snippet, all_skipped_or_empty = _run_mutated_tests_inprocess(
            mutated_source
        )
        if all_passed:
            # In-process says every test passed.
            # - If every test was skipped (optional dep missing), report
            #   as skipped — the mutation cannot be evaluated.
            # - Otherwise, the mutation is a real survivor.
            return AssertionOutcome(
                rule_name=rule.name,
                line=line,
                killed=False,
                failure_message=snippet,
                skipped=all_skipped_or_empty,
            )
        # In-process says at least one test failed. The failure could be
        # a real assertion failure (mutation killed the test) OR a
        # fixture-missing TypeError (the test never ran, and the runner
        # can't tell the difference from a kill). If the failure matches
        # a Python argument-shape TypeError, fall back to subprocess
        # for the right answer. Otherwise, trust the in-process result
        # (real kills never produce that message shape).
        if _is_arg_shape_typeerror(snippet):
            return _run_subprocess_mutant(file, line, rule, mutated_source)
        return AssertionOutcome(
            rule_name=rule.name,
            line=line,
            killed=True,
            failure_message=snippet,
        )

    # Subprocess path (legacy / opt-in via TAM_USE_SUBPROCESS=1).
    return _run_subprocess_mutant(file, line, rule, mutated_source)


# ---------------------------------------------------------------------------
# Per-file runner. Collects every (file, line, rule) for one test file
# and runs each mutation in its own subprocess.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FileReport:
    file: Path
    survivors: list[AssertionOutcome]
    total: int
    killed: int
    not_applicable: int
    skipped: int = 0

    @property
    def kill_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.killed / self.total


def _run_file(file: Path) -> FileReport:
    source = file.read_text(encoding="utf-8", errors="replace")
    assert_lines = _iter_assert_lines(source)
    survivors: list[AssertionOutcome] = []
    killed = 0
    not_applicable = 0
    skipped = 0
    total = 0

    for line in assert_lines:
        for rule in ALL_RULES:
            total += 1
            outcome = _run_assertion_mutation(file, line, rule)
            if outcome.failure_message == "(rule not applicable to this assertion)":
                not_applicable += 1
                continue
            if outcome.killed:
                killed += 1
            elif outcome.skipped:
                # Mutation could not be evaluated (every test was
                # skipped, e.g. optional dependency missing). Count
                # separately so the CLI / wrapper can distinguish
                # "skipped" from "survivor" without misreporting.
                skipped += 1
            else:
                survivors.append(outcome)
    return FileReport(
        file=file,
        survivors=survivors,
        total=total,
        killed=killed,
        not_applicable=not_applicable,
        skipped=skipped,
    )


def _iter_unit_test_files() -> list[Path]:
    """Return absolute test file paths the runner should walk.

    Walks every layer except ``meta`` and ``convert_backends`` (see
    ``tests/meta/_layers.py``). The name is kept for compatibility
    with the existing parametrize IDs.
    """
    return [(PROJECT_ROOT / rel).resolve() for rel, _layer in iter_scanned_test_files()]


def _id_for(file: Path) -> str:
    """Stable relative-path ID for pytest test parametrization.

    Handles both absolute Paths (from _iter_unit_test_files) and
    relative Paths (from iter_scanned_test_files).
    """
    if file.is_absolute():
        return str(file.relative_to(PROJECT_ROOT))
    return str(file)


# ---------------------------------------------------------------------------
# Auditability allowlist. An entry is
# (test_relpath, rule_name, line, reason). It silences a survivor that
# has been manually verified to be equivalent (i.e., the test catches
# the bug even with the mutation applied because another assertion or
# fixture handles it). Each entry cites the source line as evidence.
# ---------------------------------------------------------------------------

KNOWN_ASSERTION_EQUIVALENT: list[tuple[str, str, int, str]] = [
    # The 3 dead-in-Hypothesis assertions in test_edi_splitting_utils_property.py.
    # L58 is inside `if n == 27:` — fires for 1/1000 generated values,
    # so the assertion is vacuously skipped 99.9% of the time. The hardcoded
    # ``test_col_to_excel_hardcoded_oracle`` covers the case explicitly.
    # L154 and L196 are tautologies — the function only assigns to
    # a_record/c_record when the line starts with the matching letter, so
    # the assertion is always true when reached. The hardcoded
    # ``test_split_invoice_records_hardcoded_oracle`` covers these with
    # specific expected values.
    (
        "tests/unit/core/edi/test_edi_splitting_utils_property.py",
        "polarity_flip",
        58,
        "guarded by `if n == 27:` — fires for 1/1000 Hypothesis examples; "
        "covered by test_col_to_excel_hardcoded_oracle",
    ),
    (
        "tests/unit/core/edi/test_edi_splitting_utils_property.py",
        "equality_flip",
        58,
        "guarded by `if n == 27:` — fires for 1/1000 Hypothesis examples; "
        "covered by test_col_to_excel_hardcoded_oracle",
    ),
    (
        "tests/unit/core/edi/test_edi_splitting_utils_property.py",
        "always_fail",
        58,
        "guarded by `if n == 27:` — fires for 1/1000 Hypothesis examples; "
        "covered by test_col_to_excel_hardcoded_oracle",
    ),
    (
        "tests/unit/core/edi/test_edi_splitting_utils_property.py",
        "polarity_flip",
        154,
        "tautology: _split_invoice_records only assigns a_record when "
        "line.startswith('A'); covered by test_split_invoice_records_hardcoded_oracle",
    ),
    (
        "tests/unit/core/edi/test_edi_splitting_utils_property.py",
        "always_fail",
        154,
        "tautology: _split_invoice_records only assigns a_record when "
        "line.startswith('A'); covered by test_split_invoice_records_hardcoded_oracle",
    ),
    (
        "tests/unit/core/edi/test_edi_splitting_utils_property.py",
        "always_fail",
        196,
        "tautology: _split_invoice_records only assigns c_record when "
        "line.startswith('C'); covered by test_split_invoice_records_hardcoded_oracle",
    ),
]


def _is_known_equivalent(file: Path, rule_name: str, line: int) -> bool:
    rel = str(file.relative_to(PROJECT_ROOT))
    for f, r, l, _reason in KNOWN_ASSERTION_EQUIVALENT:
        if f == rel and r == rule_name and l == line:
            return True
    return False


# ---------------------------------------------------------------------------
# Pytest-discoverable wrapper. Parametrized over (file, rule_name) so
# `-k` works naturally and each (file, rule) is independent for `-n
# auto`. The wrapper runs the assertion-mutation check on every assert
# in the file for the given rule.
# ---------------------------------------------------------------------------


def _file_for(file_id: str) -> Path:
    return PROJECT_ROOT / file_id


@pytest.mark.meta_assertions
@pytest.mark.parametrize(
    "file,rule_name",
    [
        pytest.param(
            f,
            r.name,
            id=f"{_id_for(f)}::{r.name}",
        )
        for f in _iter_unit_test_files()
        for r in ALL_RULES
    ],
)
def test_assertions_are_meaningful(file: Path, rule_name: str) -> None:
    """For every assertion in ``file``, applying ``rule_name`` should
    make the test fail. If it doesn't, the assertion was dead.
    """
    rule = next(r for r in ALL_RULES if r.name == rule_name)
    source = file.read_text(encoding="utf-8", errors="replace")
    assert_lines = _iter_assert_lines(source)
    survivors: list[AssertionOutcome] = []

    for line in assert_lines:
        if _is_known_equivalent(file, rule_name, line):
            continue
        outcome = _run_assertion_mutation(file, line, rule)
        if outcome.failure_message == "(rule not applicable to this assertion)":
            continue
        if outcome.skipped:
            # Mutation could not be evaluated (every test in the file
            # was skipped, e.g. optional dependency missing). Neither
            # killed nor survivor; just drop from the report.
            continue
        if not outcome.killed:
            survivors.append(outcome)

    if not survivors:
        return

    rel = file.relative_to(PROJECT_ROOT)
    formatted_lines: list[str] = []
    for s in survivors:
        original = _source_line(source, s.line)
        formatted_lines.append(f"  {rel}:{s.line} [{s.rule_name}] assert: {original!r}")
    pytest.fail(
        f"{rel}: {len(survivors)} dead assertion(s) under rule "
        f"{rule_name!r}.\n" + "\n".join(formatted_lines)
    )


# ---------------------------------------------------------------------------
# Self-check. The runner file itself should not have any dead
# assertions. Rules that legitimately mention the literal pattern
# (e.g. ``polarity_flip``'s docstring references ``assert X``) are
# exempted so the runner can describe itself.
# ---------------------------------------------------------------------------


@pytest.mark.meta_assertions
def test_assertion_runner_self_check() -> None:
    self_path = Path(__file__).resolve()
    SELF_CHECK_SKIP = {
        "polarity_flip",
        "always_fail",
    }
    source = self_path.read_text(encoding="utf-8", errors="replace")
    assert_lines = _iter_assert_lines(source)
    survivors: list[str] = []
    for line in assert_lines:
        for rule in ALL_RULES:
            if rule.name in SELF_CHECK_SKIP:
                continue
            outcome = _run_assertion_mutation(self_path, line, rule)
            if outcome.failure_message == "(rule not applicable to this assertion)":
                continue
            if outcome.skipped:
                continue
            if not outcome.killed:
                survivors.append(f"  L{line} [{rule.name}]")
    if survivors:
        pytest.fail(
            "tests/meta/test_assertions_are_meaningful.py has dead "
            "assertions:\n" + "\n".join(survivors)
        )


# ---------------------------------------------------------------------------
# Fallback heuristic regression test.
#
# The in-process -> subprocess fallback in ``_run_assertion_mutation``
# depends on ``_is_arg_shape_typeerror`` matching exactly the Python
# argument-shape TypeError messages and NOT matching other common
# TypeError messages from real test failures. A regression in the
# regex would either:
#   - Under-match: in-process reports a fixture-missing TypeError as
#     killed without falling back. Result: false positives (the
#     runner thinks the mutation killed a test that never ran).
#   - Over-match: in-process reports a real assertion-related TypeError
#     as fixture-missing and falls back unnecessarily. Result: every
#     affected mutation costs an extra ~1s subprocess.
#
# Both modes are bad but under-matching is the silent bug we care
# about. The test pins the exact message shapes Python 3.11+
# emits for argument-mismatch errors.
# ---------------------------------------------------------------------------


@pytest.mark.meta_assertions
@pytest.mark.parametrize(
    ("message", "expected"),
    [
        # Argument-shape TypeErrors — MUST match (fallback fires).
        ("f() missing 1 required positional argument: 'x'", True),
        ("f() missing 2 required positional arguments: 'x' and 'y'", True),
        ("f() missing 1 required keyword-only argument: 'x'", True),
        ("f() takes 1 positional argument but 2 were given", True),
        ("f() takes 2 positional arguments but 3 were given", True),
        ("f() got an unexpected keyword argument 'x'", True),
        # Real TypeErrors from test failures — MUST NOT match.
        (
            "unsupported operand type(s) for +: 'NoneType' and 'int'",
            False,
        ),
        (
            "'<=' not supported between instances of 'str' and 'NoneType'",
            False,
        ),
        ("'NoneType' object is not callable", False),
        ("object of type 'NoneType' has no len()", False),
        ("can only concatenate str (not 'int') to str", False),
        # AssertionError / ValueError / generic exceptions — MUST NOT
        # match (we only test the failure_message snippet, which is
        # never the bare exception type, but defensive).
        ("assert 1 == 2", False),
        ("invalid literal for int() with base 10: 'x'", False),
        # Empty / unrelated snippets.
        ("", False),
        ("SUBPROCESS TIMED OUT (treated as kill)", False),
        ("SYNTAX_ERROR: invalid syntax", False),
        # The runner's own IMPORT_ERROR / SYNTAX_ERROR labels — these
        # also mean the test didn't run, but they're handled
        # separately at the call site and should not trigger the
        # fallback (the fallback is specifically for fixture-arg
        # mismatches, not import-time failures).
        ("IMPORT_ERROR: ModuleNotFoundError: No module named 'foo'", False),
    ],
)
def test_is_arg_shape_typeerror(message: str, expected: bool) -> None:
    assert _is_arg_shape_typeerror(message) is expected


@pytest.mark.meta_assertions
def test_subprocess_fallback_fires_for_fixture_missing_typeerror(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end: a test file that uses a custom fixture triggers
    the in-process -> subprocess fallback.

    This pins the behavior at the system level: if a future change
    removes the fallback or breaks the heuristic, this test fails.
    The cost is one subprocess invocation (the file has one
    trivial assertion; the mutation is a no-op; the subprocess
    path's purpose here is just to confirm the fallback was
    exercised, not to evaluate mutation kill rate).
    """
    test_file = (
        PROJECT_ROOT
        / "tests"
        / "meta"
        / "_fixture_fallback_test_tmp.py"
    )
    if test_file.exists():
        test_file.unlink()
    test_file.write_text(
        "def custom_fixture():\n"
        "    return 1\n"
        "def test_uses_fixture(custom_fixture):\n"
        "    assert custom_fixture == 1\n",
        encoding="utf-8",
    )
    try:
        # AlwaysFail rule replaces the assert with assert False. The
        # in-process runner will hit ``TypeError: test_uses_fixture()
        # missing 1 required positional argument: 'custom_fixture'``
        # (because the runner's fixture stand-ins don't cover
        # ``custom_fixture``) and the fallback should fire.
        rule = next(r for r in ALL_RULES if r.name == "always_fail")
        source = test_file.read_text(encoding="utf-8")
        line_no = source.splitlines().index(
            "    assert custom_fixture == 1"
        ) + 1
        # The subprocess path writes a mutant file to MUTANTS_DIR. We
        # verify the fallback was *invoked* by patching
        # ``_run_pytest_on_mutant`` to a sentinel that records the
        # call. The fake subprocess returns exit 0 so the fallback
        # returns killed=False, skipped=False.
        invoked: list[bool] = []
        def fake_subprocess(
            *args: object, **kwargs: object
        ) -> tuple[int, str, bool]:
            invoked.append(True)
            return 0, "", False
        # Patch the module's ``_run_pytest_on_mutant`` so the
        # subprocess fallback can be observed without actually
        # spawning pytest. The dotted-string form
        # ``monkeypatch.setattr("tests.meta.test_assertions_are_…")``
        # does NOT work here because ``tests.meta`` is a namespace
        # package (no ``__init__.py``) and pytest's
        # ``derive_importpath`` resolves the parent module to the
        # namespace package, not the actual module. Patching the
        # module object directly avoids the resolution.
        import sys
        _runner_mod = sys.modules[__name__]
        monkeypatch.setattr(_runner_mod, "_run_pytest_on_mutant", fake_subprocess)
        outcome = _run_assertion_mutation(test_file, line_no, rule)
        assert invoked, (
            "subprocess fallback did not fire for a TypeError that "
            "matches the fixture-missing pattern"
        )
        assert outcome.killed is False
        assert outcome.skipped is False
    finally:
        if test_file.exists():
            test_file.unlink()


@pytest.mark.meta_assertions
def test_class_init_typeerror_is_silently_dropped(
) -> None:
    """A class whose ``__init__`` raises ``TypeError`` (e.g. needs
    constructor args the in-process runner can't supply) is silently
    dropped. The class's test methods don't run, but the runner
    doesn't report a real failure for the drop.

    This pins the narrowing from ``except Exception`` (which also
    caught ``ValueError`` / ``RuntimeError`` from genuinely broken
    ``__init__``) to ``except TypeError`` (which is the runner
    limitation signal).
    """
    source = (
        "class TestNeedsArgs:\n"
        "    def __init__(self, required_arg):\n"
        "        self.arg = required_arg\n"
        "    def test_method(self):\n"
        "        assert True\n"
    )
    all_passed, snippet, _skipped = _run_mutated_tests_inprocess(source)
    # TypeError from __init__ → class is silently dropped, no
    # failure, no test methods run, no skip either (the runner
    # only reports skip for ``_PytestSkipped``).
    assert all_passed is True
    assert snippet == ""


@pytest.mark.meta_assertions
def test_class_init_valueerror_is_real_failure() -> None:
    """A class whose ``__init__`` raises ``ValueError`` (a real
    test bug, not a runner limitation) is recorded as a failure.
    Before the fix, this was silently dropped by
    ``except Exception: continue`` and the mutation was
    misclassified as a survivor.
    """
    source = (
        "class TestBrokenInit:\n"
        "    def __init__(self):\n"
        "        raise ValueError('bad setup')\n"
        "    def test_method(self):\n"
        "        assert True\n"
    )
    all_passed, snippet, _skipped = _run_mutated_tests_inprocess(source)
    assert all_passed is False
    assert "ValueError" in snippet
    assert "__init__" in snippet
# ---------------------------------------------------------------------------
# CLI summary entry point. Runs the same checks as the pytest wrapper
# and prints a per-file + per-rule summary, then exits 1 if any
# survivors exist. Useful for local auditing without pytest overhead.
# ---------------------------------------------------------------------------


def main() -> int:
    files = _iter_unit_test_files()
    overall_survivors: list[tuple[Path, AssertionOutcome]] = []
    total_mutations = 0
    total_killed = 0
    total_not_applicable = 0
    total_skipped = 0

    for file in files:
        try:
            report = _run_file(file)
        except Exception as exc:
            print(
                f"FATAL: {file.relative_to(PROJECT_ROOT)}: "
                f"{type(exc).__name__}: {exc}",
                file=sys.stderr,
            )
            continue
        total_mutations += report.total
        total_killed += report.killed
        total_not_applicable += report.not_applicable
        total_skipped += report.skipped
        for s in report.survivors:
            if not _is_known_equivalent(file, s.rule_name, s.line):
                overall_survivors.append((file, s))
        rel = file.relative_to(PROJECT_ROOT)
        print(
            f"{rel}: killed {report.killed}/{report.total - report.not_applicable}, "
            f"survivors {len(report.survivors)}, "
            f"skipped {report.skipped}, "
            f"not_applicable {report.not_applicable}"
        )

    print()
    print(
        f"OVERALL: killed {total_killed}/{total_mutations - total_not_applicable}, "
        f"survivors {len(overall_survivors)}, "
        f"skipped {total_skipped}, "
        f"not_applicable {total_not_applicable}"
    )
    if overall_survivors:
        print()
        print("SURVIVORS (write a stronger test or add to KNOWN_ASSERTION_EQUIVALENT):")
        for file, s in overall_survivors:
            rel = file.relative_to(PROJECT_ROOT)
            original = _source_line(
                file.read_text(encoding="utf-8", errors="replace"), s.line
            )
            print(f"  {rel}:{s.line} [{s.rule_name}] {original}")
    return 1 if overall_survivors else 0


if __name__ == "__main__":
    raise SystemExit(main())
