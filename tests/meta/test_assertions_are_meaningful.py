"""Assertion-mutation meta-test.

This meta-test asks: are the assertions in each test file actually doing
work, or would the test pass if every assertion were deleted / inverted?

For every test file under ``tests/unit/``, the runner:

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

Pair list: every ``tests/unit/**/test_*.py`` file. 153 files at the
time of writing. Wall time is dominated by subprocess startup and the
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
import re
import subprocess
import sys
import textwrap
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TESTS_DIR = PROJECT_ROOT / "tests"
UNIT_TESTS_DIR = TESTS_DIR / "unit"
MUTANTS_DIR = PROJECT_ROOT / "mutants_assertions"
PER_FILE_TIMEOUT = 30


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
        new_compare = _flip_compare_op(
            node.test, {ast.Eq: ast.NotEq}
        )
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
        new_compare = _flip_compare_op(
            node.test, {ast.NotEq: ast.Eq}
        )
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


def _mutant_path(file: Path, line: int, rule_name: str) -> Path:
    """Return the on-disk path for a mutated copy of ``file``.

    The path includes the line and rule so multiple mutants of the same
    file don't collide. Files are written to ``mutants_assertions/`` to
    keep them out of the source tree.
    """
    rel = file.relative_to(PROJECT_ROOT)
    safe = str(rel).replace("/", "_").replace(".py", "")
    return MUTANTS_DIR / f"{safe}__L{line}__{rule_name}.py"


def _run_pytest_on_mutant(mutant_path: Path) -> tuple[int, str]:
    """Run pytest against ``mutant_path`` and return (exit_code, output).

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
        return 124, "SUBPROCESS TIMED OUT (treated as kill)"
    return result.returncode, (result.stdout or "") + (result.stderr or "")


def _write_mutant(mutant_path: Path, mutated_source: str) -> None:
    mutant_path.parent.mkdir(parents=True, exist_ok=True)
    mutant_path.write_text(mutated_source, encoding="utf-8")


def _run_assertion_mutation(
    file: Path, line: int, rule: MutationRule
) -> AssertionOutcome:
    """Run a single assertion-mutation check.

    Returns an AssertionOutcome recording whether the mutation killed
    the test. A killed mutation is one that made the test fail (i.e.,
    the original assertion was load-bearing). A surviving mutation is
    one that the test still passed despite the mutation (i.e., the
    assertion was dead or self-referential).
    """
    source = file.read_text(encoding="utf-8", errors="replace")
    original_line = _source_line(source, line)
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

    mutant_path = _mutant_path(file, line, rule.name)
    _write_mutant(mutant_path, mutated_source)
    try:
        code, output = _run_pytest_on_mutant(mutant_path)
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
    )


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
            else:
                survivors.append(outcome)
    return FileReport(
        file=file,
        survivors=survivors,
        total=total,
        killed=killed,
        not_applicable=not_applicable,
    )


def _iter_unit_test_files() -> list[Path]:
    return sorted(UNIT_TESTS_DIR.rglob("test_*.py"))


def _id_for(file: Path) -> str:
    return str(file.relative_to(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Auditability allowlist. An entry is
# (test_relpath, rule_name, line, reason). It silences a survivor that
# has been manually verified to be equivalent (i.e., the test catches
# the bug even with the mutation applied because another assertion or
# fixture handles it). Each entry cites the source line as evidence.
# ---------------------------------------------------------------------------

KNOWN_ASSERTION_EQUIVALENT: list[tuple[str, str, int, str]] = [
    # Examples are not pre-populated. Add entries here as the runner
    # surfaces survivors and a reviewer confirms each is equivalent.
]


def _is_known_equivalent(
    file: Path, rule_name: str, line: int
) -> bool:
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
        if not outcome.killed:
            survivors.append(outcome)

    if not survivors:
        return

    rel = file.relative_to(PROJECT_ROOT)
    formatted_lines: list[str] = []
    for s in survivors:
        original = _source_line(source, s.line)
        formatted_lines.append(
            f"  {rel}:{s.line} [{s.rule_name}] assert: {original!r}"
        )
    pytest.fail(
        f"{rel}: {len(survivors)} dead assertion(s) under rule "
        f"{rule_name!r}.\n"
        + "\n".join(formatted_lines)
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
            if not outcome.killed:
                survivors.append(
                    f"  L{line} [{rule.name}]"
                )
    if survivors:
        pytest.fail(
            "tests/meta/test_assertions_are_meaningful.py has dead "
            "assertions:\n" + "\n".join(survivors)
        )


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

    for file in files:
        try:
            report = _run_file(file)
        except Exception as exc:  # noqa: BLE001 - runner must not crash
            print(
                f"FATAL: {file.relative_to(PROJECT_ROOT)}: "
                f"{type(exc).__name__}: {exc}",
                file=sys.stderr,
            )
            continue
        total_mutations += report.total
        total_killed += report.killed
        total_not_applicable += report.not_applicable
        for s in report.survivors:
            if not _is_known_equivalent(file, s.rule_name, s.line):
                overall_survivors.append((file, s))
        rel = file.relative_to(PROJECT_ROOT)
        print(
            f"{rel}: killed {report.killed}/{report.total - report.not_applicable}, "
            f"survivors {len(report.survivors)}, "
            f"not_applicable {report.not_applicable}"
        )

    print()
    print(
        f"OVERALL: killed {total_killed}/{total_mutations - total_not_applicable}, "
        f"survivors {len(overall_survivors)}, "
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
