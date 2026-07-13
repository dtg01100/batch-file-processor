"""Property-test oracle consistency meta-test.

This meta-test asks: for every Hypothesis property test, is the
test's "expected value" actually independent of the function-under-test,
or does the test use the function-under-test (directly or transitively)
to build its own oracle?

The bug pattern is the **self-referential test**:

1. Test generates random input ``x``.
2. Test computes the expected output using a hand-rolled oracle ``O(x)``.
3. Test asserts ``f(x) == O(x)``.
4. If ``O`` accidentally calls ``f`` (or vice versa), or if ``O`` is
   wrong in a way that always agrees with ``f``, the assertion passes
   trivially.

The existing mutation runner already caught one such bug
(``test_validate_upc_accepts_check_digit`` constructed its input
from the function-under-test; see ``docs/meta-test-findings.md``).
The fixed version uses a hardcoded oracle; the original was a
self-referential test that passed for any consistent mutation of
``calc_check_digit``.

This runner is in two phases:

- **Phase 3a (enumeration).** Walk every property test file, find
  each ``@given`` test, and for every assertion in the test, classify
  the assertion as:
    - ``trivially_true`` — both sides are identical (``f(x) == f(x)``)
    - ``oracle_uses_f`` — one side is a call to the function-under-test
      AND the other side ALSO uses the function-under-test (directly or
      through a local helper)
    - ``oracle_independent`` — the test computes an expected value
      without using the function-under-test
  Emit a report. This phase has no subprocess; it's pure AST.

- **Phase 3b (consistency).** For every test flagged as
  ``oracle_uses_f`` or ``trivially_true``, run the test with the oracle
  REPLACED by a hardcoded value or a non-``f`` computation, and verify
  the test still passes. If it does, the oracle was load-bearing in a
  bad way (the test is making circular claims about ``f``).

Phase 3a is the initial deliverable. Phase 3b is experimental and
landed separately.

Pair list: every ``tests/**/*_property.py`` file. 9 files at the time
of writing (one per in-scope module under ``core/edi/`` and the three
``dispatch/`` pure-helper modules).

Usage::

    # Run the enumeration report.
    pytest tests/meta/test_property_oracle_consistency.py -n auto

    # Audit a single property test file.
    pytest tests/meta/test_property_oracle_consistency.py -k test_upc_utils_property

    # CLI summary.
    python tests/meta/test_property_oracle_consistency.py
"""

from __future__ import annotations

import ast
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TESTS_DIR = PROJECT_ROOT / "tests"
UNIT_TESTS_DIR = TESTS_DIR / "unit"


# ---------------------------------------------------------------------------
# Classification. Each test gets a list of AssertionClassification, one
# per assert statement. The report groups by classification so a reviewer
# can see at a glance which property tests have suspicious oracles.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AssertionClassification:
    line: int
    kind: str
    detail: str

    def format(self) -> str:
        return f"L{self.line} [{self.kind}] {self.detail}"


@dataclass
class PropertyTestReport:
    file: Path
    test_name: str
    line: int
    classifications: list[AssertionClassification] = field(default_factory=list)
    input_uses_f: bool = False
    input_uses_helpers: list[str] = field(default_factory=list)

    @property
    def flagged(self) -> bool:
        if any(
            c.kind in {"trivially_true", "self_referential_helper"}
            for c in self.classifications
        ):
            return True
        # An assertion that uses f AND an input that was built using a
        # helper that itself calls f (a different f, but same call
        # graph) is a strong self-referential signal — the test could
        # be made stronger by replacing the input-construction helper
        # with a hardcoded value.
        if self.input_uses_f and self.input_uses_helpers:
            return True
        return False


# ---------------------------------------------------------------------------
# Per-test oracle analysis. For a given test function, we:
#
# 1. Identify the "function-under-test" by looking at the test's
#    imports. The first function imported from a `core.*` or
#    `dispatch.*` module is treated as ``f``. If no such import is
#    found, we use the function name as a fallback (e.g.
#    ``test_calc_check_digit`` -> ``calc_check_digit``).
#
# 2. For each Assert node in the test body, walk the test side and the
#    expected side (when there are exactly two operands) and check
#    whether either side contains a call to ``f``.
#
# 3. If the assertion has no Compare (e.g. ``assert 0 <= x <= 9``), or
#    if it has more than two operands, we classify it conservatively as
#    ``other``.
#
# 4. If both operands of a Compare are AST-identical (same unparse),
#    the test is trivially_true.
#
# 5. If one operand is a call to ``f`` and the OTHER operand is ALSO a
#    call to ``f`` (or the same call graph), the test is self-referential
#    (a "f == f" check with a different argument form). The classic case
#    is ``assert f(int(s)) == f(s)`` which only tests the int-coercion
#    path, but the test could be made stronger by replacing one side
#    with a hardcoded value.
# ---------------------------------------------------------------------------


def _unparse(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except Exception:
        return ""


def _contains_call_to(node: ast.AST, target_name: str) -> bool:
    """True if ``node`` contains a call to a function named ``target_name``.

    ``target_name`` is a bare name (e.g. ``calc_check_digit``). We also
    accept dotted names like ``module.calc_check_digit`` by matching
    against the trailing identifier.
    """
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            func = sub.func
            if isinstance(func, ast.Name) and func.id == target_name:
                return True
            if isinstance(func, ast.Attribute) and func.attr == target_name:
                return True
    return False


def _module_under_test(file: Path, test_name: str, imports: set[str]) -> str:
    """Return the bare function name we treat as the function-under-test.

    Heuristic: strip the ``test_`` prefix, then find the LONGEST
    prefix of the remaining name that is a function imported into
    this test file. For example, given imports
    ``{calc_check_digit, convert_upce_to_upca, pad_upc, validate_upc}``
    and test name ``test_validate_upc_accepts_check_digit``, the
    longest matching prefix is ``validate_upc`` (length 11). The
    function-under-test is therefore ``validate_upc``, not the
    verbose test name.

    Falls back to the test name minus ``test_`` if no imported
    function matches.
    """
    stripped = test_name
    if stripped.startswith("test_"):
        stripped = stripped[len("test_"):]
    best = ""
    for imported in imports:
        if stripped.startswith(imported) and len(imported) > len(best):
            best = imported
    return best or stripped


def _is_pure_comparison(node: ast.Assert) -> bool:
    return isinstance(node.test, ast.Compare) and len(node.test.ops) == 1


def _classify_assertion(
    assert_node: ast.Assert, function_under_test: str
) -> AssertionClassification:
    if not _is_pure_comparison(assert_node):
        return AssertionClassification(
            line=assert_node.lineno,
            kind="other",
            detail="non-binary assertion (chained compare or non-Compare)",
        )

    cmp = assert_node.test
    left = cmp.left
    right = cmp.comparators[0]
    op = type(cmp.ops[0]).__name__

    left_uses_f = _contains_call_to(left, function_under_test)
    right_uses_f = _contains_call_to(right, function_under_test)

    if left_uses_f and right_uses_f:
        # Both sides use f. Could be:
        #  - trivially_true: both sides are the SAME f call
        #  - self_referential_helper: both sides use f but with
        #    different args (e.g. f(s) == f(int(s)))
        left_text = _unparse(left)
        right_text = _unparse(right)
        if left_text == right_text:
            return AssertionClassification(
                line=assert_node.lineno,
                kind="trivially_true",
                detail=f"f(x) {op} f(x) — both operands identical",
            )
        return AssertionClassification(
            line=assert_node.lineno,
            kind="self_referential_helper",
            detail=(
                f"both operands use {function_under_test}() but with different args: "
                f"assert {left_text} {op} {right_text}"
            ),
        )

    if left_uses_f and not right_uses_f:
        return AssertionClassification(
            line=assert_node.lineno,
            kind="oracle_uses_f_left",
            detail=(
                f"left side calls {function_under_test}(); right side is independent. "
                f"Assertion shape: assert {function_under_test}(...) {op} <expected>"
            ),
        )

    if right_uses_f and not left_uses_f:
        return AssertionClassification(
            line=assert_node.lineno,
            kind="oracle_uses_f_right",
            detail=(
                f"right side calls {function_under_test}(); left side is independent. "
                f"Assertion shape: assert <expected> {op} {function_under_test}(...)"
            ),
        )

    return AssertionClassification(
        line=assert_node.lineno,
        kind="oracle_independent",
        detail=(
            f"assert <left> {op} <right> — neither operand uses "
            f"{function_under_test}()"
        ),
    )


# ---------------------------------------------------------------------------
# Property test file walker. Find every ``@given`` test and classify
# its assertions.
# ---------------------------------------------------------------------------


def _iter_given_tests(tree: ast.Module) -> Iterable[ast.FunctionDef]:
    """Yield every top-level test function that has a ``@given`` decorator."""
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith("test_"):
            continue
        for dec in node.decorator_list:
            if _is_given_decorator(dec):
                yield node
                break


def _is_given_decorator(dec: ast.AST) -> bool:
    """True if ``dec`` is a ``@given`` decorator (possibly via ``@pytest.mark.given``)."""
    if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name):
        return dec.func.id == "given"
    if isinstance(dec, ast.Name):
        return dec.id == "given"
    if isinstance(dec, ast.Attribute):
        return dec.attr == "given"
    return False


def _iter_asserts(test: ast.FunctionDef) -> Iterable[ast.Assert]:
    for stmt in ast.walk(test):
        if isinstance(stmt, ast.Assert):
            yield stmt


def _input_uses_f_or_helpers(
    test: ast.FunctionDef, function_under_test: str
) -> tuple[bool, list[str]]:
    """Inspect the test body for input construction that uses ``f``.

    Returns ``(uses_f_in_input, helper_names)``. ``uses_f_in_input`` is
    True if the test's INPUT (not the assertion) is built from a call
    to ``function_under_test``. This catches the self-referential
    pattern where a test uses ``f`` to construct the very value it
    then asserts ``f`` against — e.g.::

        full = d + str(calc_check_digit(d))  # input built from f
        assert validate_upc(full) is True    # assertion checks f

    The pre-fix ``test_validate_upc_accepts_check_digit`` had this
    exact pattern. The fix (the
    ``test_validate_upc_hardcoded_valid_oracle`` test added at the
    same time) replaced the input construction with hardcoded values
    so the test no longer depends on ``calc_check_digit``.

    The detection is intentionally narrow: it only counts
    **assignments** in the test body that compute a value via a call
    to ``f``. Method calls (``self.x = f(...)``) and asserts that
    call ``f`` directly are not counted; they're classified at the
    assertion level instead.

    ``helper_names`` is a sorted list of module-level helpers defined
    in the same test file (e.g. ``_fixed_digits``) that the test
    calls. A test whose input is built from a helper AND a function
    under test is a weaker self-referential signal (the helper
    might call ``f`` or might not), so we surface it but don't fail
    on it alone.
    """
    uses_f_in_input = False
    helper_calls: set[str] = set()
    for stmt in test.body:
        if isinstance(stmt, ast.Assign):
            for sub in ast.walk(stmt.value):
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
                    if sub.func.id == function_under_test:
                        uses_f_in_input = True
                    elif sub.func.id.startswith("_") and not sub.func.id.startswith("__"):
                        helper_calls.add(sub.func.id)
    return uses_f_in_input, sorted(helper_calls)


def _collect_imports(tree: ast.Module) -> set[str]:
    """Collect the set of function/class names imported in this module.

    We only consider top-level ``from X import Y`` statements — names
    that the test file explicitly pulls in. ``import X`` aliases are
    not tracked (they require call-graph traversal to map a call to
    the original function name).
    """
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "*":
                    continue
                names.add(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    names.add(alias.asname)
    return names


def _analyze_test(
    file: Path, test: ast.FunctionDef, imports: set[str]
) -> PropertyTestReport:
    function_under_test = _module_under_test(file, test.name, imports)
    classifications = [
        _classify_assertion(assert_node, function_under_test)
        for assert_node in _iter_asserts(test)
    ]
    input_uses_f, helpers = _input_uses_f_or_helpers(test, function_under_test)
    return PropertyTestReport(
        file=file,
        test_name=test.name,
        line=test.lineno,
        classifications=classifications,
        input_uses_f=input_uses_f,
        input_uses_helpers=helpers,
    )


# ---------------------------------------------------------------------------
# File enumeration + report.
# ---------------------------------------------------------------------------


def _iter_property_test_files() -> list[Path]:
    return sorted(p for p in UNIT_TESTS_DIR.rglob("*_property.py"))


def analyze_all() -> dict[Path, list[PropertyTestReport]]:
    """Return a mapping of property test file to its per-test reports.

    Used by both the pytest wrapper and the CLI entry point.
    """
    by_file: dict[Path, list[PropertyTestReport]] = {}
    for file in _iter_property_test_files():
        source = file.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        imports = _collect_imports(tree)
        reports: list[PropertyTestReport] = []
        for test in _iter_given_tests(tree):
            reports.append(_analyze_test(file, test, imports))
        by_file[file] = reports
    return by_file


# ---------------------------------------------------------------------------
# Pytest-discoverable wrapper. Parametrized over (file, test_name) so
# -k works. A test fails (with a clear report) if its assertions include
# ``trivially_true`` or ``self_referential_helper`` — those are the
# kinds of oracle bugs the existing mutation runner already found once.
# ---------------------------------------------------------------------------


def _id_for(file: Path) -> str:
    return str(file.relative_to(PROJECT_ROOT))


@pytest.mark.meta_oracle
@pytest.mark.parametrize(
    "file",
    [pytest.param(f, id=_id_for(f)) for f in _iter_property_test_files()],
)
def test_property_oracle_classification(file: Path) -> None:
    """For every ``@given`` test in ``file``, classify each assertion.

    Phase 3a deliverable: surface ``trivially_true`` and
    ``self_referential_helper`` assertions, which are the patterns
    the existing mutation runner already found as bugs.
    """
    source = file.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        pytest.skip(f"could not parse {file}")

    flagged_lines: list[str] = []
    imports = _collect_imports(tree)
    for test in _iter_given_tests(tree):
        function_under_test = _module_under_test(file, test.name, imports)
        classifications = [
            _classify_assertion(a, function_under_test) for a in _iter_asserts(test)
        ]
        uses_f_in_input, helpers = _input_uses_f_or_helpers(
            test, function_under_test
        )
        assertion_uses_f = any(
            c.kind.startswith("oracle_uses_f") for c in classifications
        )
        for c in classifications:
            if c.kind in {"trivially_true", "self_referential_helper"}:
                flagged_lines.append(
                    f"  {test.name} ({function_under_test}): {c.format()}"
                )
        if uses_f_in_input and assertion_uses_f:
            helper_list = ", ".join(helpers) if helpers else "(no module-level helpers)"
            flagged_lines.append(
                f"  {test.name} ({function_under_test}): L{test.lineno} "
                f"[input_self_referential] test uses {function_under_test}() "
                f"to build its input AND asserts against {function_under_test}(). "
                f"Replace input construction with hardcoded values. Helpers "
                f"called: {helper_list}. Reference fix: "
                f"test_validate_upc_hardcoded_valid_oracle in "
                f"test_upc_utils_property.py."
            )

    if flagged_lines:
        rel = file.relative_to(PROJECT_ROOT)
        pytest.fail(
            f"{rel}: {len(flagged_lines)} suspicious oracle pattern(s):\n"
            + "\n".join(flagged_lines)
        )


@pytest.mark.meta_oracle
def test_oracle_runner_self_check() -> None:
    """Sanity check: the runner file itself has no ``@given`` tests, so
    it has no oracles to classify. We just verify the runner parses.
    """
    self_path = Path(__file__).resolve()
    source = self_path.read_text(encoding="utf-8", errors="replace")
    try:
        ast.parse(source)
    except SyntaxError as exc:
        pytest.fail(f"self-parse failed: {exc}")


# ---------------------------------------------------------------------------
# CLI summary.
# ---------------------------------------------------------------------------


def main() -> int:
    by_file = analyze_all()
    total_tests = 0
    total_asserts = 0
    flagged_tests = 0
    by_kind: dict[str, int] = {}

    for file, reports in by_file.items():
        rel = file.relative_to(PROJECT_ROOT)
        if not reports:
            continue
        flagged_in_file = [r for r in reports if r.flagged]
        total_tests += len(reports)
        for r in reports:
            total_asserts += len(r.classifications)
        flagged_tests += len(flagged_in_file)
        for r in reports:
            for c in r.classifications:
                by_kind[c.kind] = by_kind.get(c.kind, 0) + 1
        print(f"{rel}: {len(reports)} test(s), {len(flagged_in_file)} flagged")
        for r in reports:
            if r.flagged:
                print(f"  test {r.test_name} (L{r.line}):")
                for c in r.classifications:
                    print(f"    {c.format()}")

    print()
    print(f"OVERALL: {total_tests} property test(s), {total_asserts} assertion(s)")
    print(f"Flagged tests: {flagged_tests}")
    for kind, count in sorted(by_kind.items()):
        print(f"  {kind}: {count}")
    return 1 if flagged_tests else 0


if __name__ == "__main__":
    raise SystemExit(main())
