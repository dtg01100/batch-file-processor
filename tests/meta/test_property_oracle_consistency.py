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
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
# Layer registry. The runner walks every scanned layer but the
# enumerator filters to ``*_property.py`` files; see
# ``_iter_property_test_files``.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _layers import (  # type: ignore[import-not-found]
    iter_scanned_test_files,
)

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

    def flagged(
        self, allowlist: list[tuple[str, str, int, str, str]] | None = None
    ) -> bool:
        """True if this test has a flagged pattern not silenced by the allowlist.

        ``allowlist`` is a list of (relpath, test_name, line, kind, reason)
        tuples. Any (test, classification) pair matching an allowlist
        entry is treated as equivalent and not flagged.
        """
        for c in self.classifications:
            if c.kind in {"trivially_true", "self_referential_helper"}:
                if allowlist is not None and _is_known_oracle_equivalent(
                    self.file, self.test_name, c.line, c.kind
                ):
                    continue
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


def _build_local_var_defs(test: ast.FunctionDef) -> dict[str, ast.AST]:
    """Map local-variable names in ``test`` to their assigned RHS expression.

    Only simple single-target assignments are tracked
    (``x = expr``). Augment assignments (``x += 1``) and tuple unpacking
    (``a, b = ...``) are ignored. The result is a shallow map: a
    variable that is reassigned appears with its LATEST assignment
    RHS, which is sufficient for the oracle classifier because
    Hypothesis property tests follow a "compute then assert" pattern.
    """
    defs: dict[str, ast.AST] = {}
    for stmt in test.body:
        if not isinstance(stmt, ast.Assign):
            continue
        if len(stmt.targets) != 1:
            continue
        target = stmt.targets[0]
        if not isinstance(target, ast.Name):
            continue
        defs[target.id] = stmt.value
    return defs


def _resolve_local(node: ast.AST, local_defs: dict[str, ast.AST]) -> ast.AST:
    """If ``node`` is a local variable in ``local_defs``, return its RHS.

    Otherwise return ``node`` unchanged. Used by the classifier to
    follow one hop of variable assignment: an assertion like
    ``assert result == []`` where ``result = f(...)`` is
    transitively a call to ``f`` even though the assertion site
    itself contains no call.
    """
    if isinstance(node, ast.Name) and node.id in local_defs:
        return local_defs[node.id]
    return node


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
        stripped = stripped[len("test_") :]
    best = ""
    for imported in imports:
        if stripped.startswith(imported) and len(imported) > len(best):
            best = imported
    return best or stripped


def _is_pure_comparison(node: ast.Assert) -> bool:
    return isinstance(node.test, ast.Compare) and len(node.test.ops) == 1


def _classify_assertion(
    assert_node: ast.Assert,
    function_under_test: str,
    local_defs: dict[str, ast.AST] | None = None,
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

    # Resolve one hop of local-variable assignment so that
    # ``assert result == []`` where ``result = f(...)`` is classified
    # as ``oracle_uses_f_left`` rather than ``oracle_independent``.
    if local_defs is not None:
        left = _resolve_local(left, local_defs)
        right = _resolve_local(right, local_defs)

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
    local_defs = _build_local_var_defs(test)
    classifications = [
        _classify_assertion(assert_node, function_under_test, local_defs)
        for assert_node in _iter_asserts(test)
    ]
    return PropertyTestReport(
        file=file,
        test_name=test.name,
        line=test.lineno,
        classifications=classifications,
    )


# ---------------------------------------------------------------------------
# File enumeration + report.
# ---------------------------------------------------------------------------


def _iter_property_test_files() -> list[Path]:
    """Return every ``*_property.py`` in the scanned layers.

    Walks every layer except ``meta`` and ``convert_backends`` (see
    ``_layers.py``) and filters to files whose name ends in
    ``_property.py``. The filter keeps the runner scoped to property
    tests; non-property test files are not part of this runner's
    contract.
    """
    return sorted(
        (PROJECT_ROOT / rel).resolve()
        for rel, _layer in iter_scanned_test_files()
        if rel.name.endswith("_property.py")
    )


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
# Auditability allowlist. An entry is (test_relpath, test_name, line, kind, reason).
# It silences a flagged test whose pattern is intentional. Each entry
# cites the source line as evidence, not a summary. The same
# auditability contract as the mutation runner's KNOWN_EQUIVALENT
# (see test_property_tests_are_sufficient.py and tests/meta/README.md).
#
# Trivially_true entries: ``assert f(x) == f(x)`` is a tautology. A
# passing test only proves the function has no I/O side effects
# between the two calls, which Python already guarantees for pure
# functions. These are kept as documentation of the purity invariant;
# the hardcoded-oracle counterparts added in this push (e.g.
# test_calc_check_digit_hardcoded_oracle) provide the
# mutation-catching coverage.
# ---------------------------------------------------------------------------

KNOWN_ORACLE_EQUIVALENT: list[tuple[str, str, int, str, str]] = [
    # (file, test_name, line, kind, reason)
    (
        "tests/unit/core/edi/test_upc_utils_property.py",
        "test_calc_check_digit_is_deterministic",
        72,
        "trivially_true",
        "assert calc_check_digit(s) == calc_check_digit(s) — documented "
        "purity check. Coverage of actual values is in "
        "test_calc_check_digit_hardcoded_oracle (added 2026-07-13).",
    ),
    (
        "tests/unit/core/edi/test_upc_utils_property.py",
        "test_calc_check_digit_accepts_int_input",
        81,
        "self_referential_helper",
        "assert calc_check_digit(s) == calc_check_digit(int(s)) — the test "
        "intentionally compares two calls of the same function with "
        "different argument forms. Its purpose is to verify that "
        "int-coercion doesn't change the result, which is a property "
        "test of the int-coercion path, not a test of the function's "
        "correctness. Coverage of the function's actual correctness is "
        "in test_calc_check_digit_hardcoded_oracle (added 2026-07-13).",
    ),
    (
        "tests/unit/core/edi/test_upc_utils_property.py",
        "test_pad_upc_idempotent_when_already_target_length",
        197,
        "self_referential_helper",
        "assert pad_upc(s, t, fill) == pad_upc(pad_upc(s, t, fill), t, fill) "
        "— the test intentionally checks the idempotency property of "
        "pad_upc. Any consistent mutation to pad_upc that preserves "
        "the property would still pass. Coverage of actual values is in "
        "test_pad_upc_hardcoded_oracle (added 2026-07-13).",
    ),
    (
        "tests/unit/core/edi/test_edi_transformer_property.py",
        "test_convert_to_price_is_deterministic",
        191,
        "trivially_true",
        "assert convert_to_price(s) == convert_to_price(s) — documented "
        "purity check. No hardcoded counterpart is needed because the "
        "test_edi_transformer module's non-determinism property is "
        "exercised by the broader property tests above (L172-184) which "
        "compare convert_to_price to convert_to_price_decimal on real "
        "input. Adding a hardcoded pair would be redundant with those.",
    ),
    (
        "tests/unit/core/edi/test_edi_transformer_property.py",
        "test_convert_to_price_decimal_is_deterministic",
        198,
        "trivially_true",
        "assert convert_to_price_decimal(s) == convert_to_price_decimal(s) "
        "— documented purity check. Same reasoning as "
        "test_convert_to_price_is_deterministic above.",
    ),
    (
        "tests/unit/dispatch/test_file_utils_property.py",
        "test_strip_invalid_filename_chars_idempotent",
        99,
        "self_referential_helper",
        "assert strip(x) == strip(strip(x)) — the test intentionally "
        "checks the idempotency property of strip_invalid_filename_chars. "
        "Any consistent mutation that preserves idempotency would still "
        "pass. Coverage of actual values is in "
        "test_strip_invalid_filename_chars_hardcoded_oracle (added 2026-07-13).",
    ),
]


def _is_known_oracle_equivalent(
    file: Path, test_name: str, line: int, kind: str
) -> bool:
    rel = str(file.relative_to(PROJECT_ROOT))
    for f, t, l, k, _reason in KNOWN_ORACLE_EQUIVALENT:
        if f == rel and t == test_name and l == line and k == kind:
            return True
    return False


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
        local_defs = _build_local_var_defs(test)
        classifications = [
            _classify_assertion(a, function_under_test, local_defs)
            for a in _iter_asserts(test)
        ]
        for c in classifications:
            if c.kind in {"trivially_true", "self_referential_helper"}:
                if _is_known_oracle_equivalent(file, test.name, c.line, c.kind):
                    continue
                flagged_lines.append(
                    f"  {test.name} ({function_under_test}): {c.format()}"
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
        flagged_in_file = [r for r in reports if r.flagged(KNOWN_ORACLE_EQUIVALENT)]
        total_tests += len(reports)
        for r in reports:
            total_asserts += len(r.classifications)
        flagged_tests += len(flagged_in_file)
        for r in reports:
            for c in r.classifications:
                by_kind[c.kind] = by_kind.get(c.kind, 0) + 1
        print(f"{rel}: {len(reports)} test(s), {len(flagged_in_file)} flagged")
        for r in reports:
            if r.flagged(KNOWN_ORACLE_EQUIVALENT):
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
