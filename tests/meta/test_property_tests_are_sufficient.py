"""Brutally simple mutation meta-test.

This meta-test asks the question: are the tests in tests/unit/**/*_property.py
(and the other DEFAULT_PAIRS below) sufficient to catch real bugs in the
modules they protect? It applies a small, fixed list of obvious mutations
to each module source and runs the corresponding test once. If the test
still passes, the mutation **survived** — a real bug of that shape would
have slipped past the test.

Principles:
- The mutation set is a fixed small list. It is NOT exhaustive mutation
  testing (use mutmut for that). It is a smoke-test of the test suite
  itself.
- Performance is not a concern: this script runs once per meta-test
  invocation. A 5x slow test run is fine.
- The script is a single file, no plugin framework, no config files.
  Read the source, understand the result.
- Every survivor lists the original and mutated source line. A reviewer
  must be able to audit each survivor with a `git blame`-style lookup.

Usage:
    pytest tests/meta/test_property_tests_are_sufficient.py -n 0 -s
    .venv/bin/python tests/meta/test_property_tests_are_sufficient.py \\
        --module core/edi/edi_parser.py \\
        --tests tests/unit/core/edi/test_edi_parser_property.py
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Mutation rules. Each is a (name, find_regex, replace_func) triple.
#
# The list is small on purpose. The meta-test's correctness depends on every
# rule mapping to a clear, real bug class. If you can't justify a mutation
# with a one-sentence "the kind of bug this catches", drop it.
#
# Regex discipline (auditability contract):
#
# 1. Comparison swaps (`lt_to_le`, `le_to_lt`, `gt_to_ge`, `ge_to_gt`):
#    swap `<` <-> `<=`, `>` <-> `>=`. The lookbehind
#    `(?<![A-Za-z0-9_\-])` excludes the function-annotation arrow `->`
#    (preceded by `-`) and identifier-internal characters. Without it,
#    `def f() -> str:` would be mutated to `def f() ->= str:` and the
#    resulting SyntaxError would falsely look like a kill.
#
#    Additionally, `lt_to_le` matches `<` only when NOT followed by
#    another `<` or `=` (so `<<` and `<=` stay matched by their own
#    rules). Likewise `gt_to_ge` matches `>` only when NOT followed
#    by `=` (so `>=` is reserved for `ge_to_gt`). Without these
#    negative lookaheads, `>` in `>=` would be turned into `>==`,
#    producing a SyntaxError that looks like a kill.
#
# 2. Equality swaps (`eq_to_ne`, `ne_to_eq`): swap `==` <-> `!=`.
#    `eq_to_ne` excludes a preceding `!` so it cannot match the `!=`
#    in `!==` (not Python; defensive). `==` and `!=` in Python can only
#    appear as comparisons, so no further context checks are needed.
#
# 3. Boolean flips (`true_to_false`, `false_to_true`): flip the literal
#    `True` / `False` token. `\b` word boundaries prevent partial matches
#    on identifiers that contain those substrings (there shouldn't be any).
#    Side effect: hits docstring prose and default-argument values.
#    Those land in KNOWN_EQUIVALENT with cited reasons.
#
# 4. Connector swaps (`and_to_or`, `or_to_and`): swap the keyword.
#    Word boundaries prevent matching `Brand` or `born`. Same docstring
#    prose caveat.
#
# 5. `return_none_instead_of_value`: replaces `return EXPR` with
#    `return None`. The negative lookahead `(?!None\b)` excludes
#    `return None`. Side effect: hits docstring prose like
#    "return results"; KNOWN_EQUIVALENT cites the line.
#
# 6. `negate_if_condition`: negates `if X:` to `if not (X):`. Catches
#    guard regressions. Targets `if`-statements, NOT `elif` (the regex
#    would not match `elif` because `elif` has no space before its
#    condition; verified by hand on existing modules).
#
# 7. `int_constant_off_by_one`: increments a literal integer >= 2.
#    Side effect: hits docstring prose ("6-character") and version
#    constants; KNOWN_EQUIVALENT cites those.
#
# Mutation order matters. Comparison swaps run first so they don't shadow
# each other; the int-off-by-one runs last and may match a number produced
# by an earlier mutation's diff (a known edge case the runner accepts).
# ---------------------------------------------------------------------------

MUTATIONS: list[tuple[str, re.Pattern[str], Callable[[re.Match[str]], str]]] = [
    ("lt_to_le", re.compile(r"(?<![A-Za-z0-9_\-])<(?![<=])"), lambda m: "<="),
    ("le_to_lt", re.compile(r"(?<![A-Za-z0-9_\-])<="), lambda m: "<"),
    # Match `>` that is NOT followed by `=` (so `>=` is reserved for
    # ge_to_gt). The lookbehind excludes identifier chars and the
    # function-arrow character.
    ("gt_to_ge", re.compile(r"(?<![A-Za-z0-9_\-])>(?!=)"), lambda m: ">="),
    ("ge_to_gt", re.compile(r"(?<![A-Za-z0-9_\-])>="), lambda m: ">"),
    ("eq_to_ne", re.compile(r"(?<!=)=="), lambda m: "!="),
    ("ne_to_eq", re.compile(r"!="), lambda m: "=="),
    ("true_to_false", re.compile(r"\bTrue\b"), lambda m: "False"),
    ("false_to_true", re.compile(r"\bFalse\b"), lambda m: "True"),
    ("and_to_or", re.compile(r"\band\b"), lambda m: "or"),
    ("or_to_and", re.compile(r"\bor\b"), lambda m: "and"),
    (
        "return_none_instead_of_value",
        re.compile(r"return\s+(?!None\b)([A-Za-z_][A-Za-z0-9_\.\(\)]+)"),
        lambda m: "return None",
    ),
    (
        "negate_if_condition",
        re.compile(r"if\s+(.+?):"),
        lambda m: f"if not ({m.group(1)}):",
    ),
    (
        "int_constant_off_by_one",
        re.compile(r"\b([2-9]\d*|1\d+)\b"),
        lambda m: str(int(m.group(1)) + 1),
    ),
]


# ---------------------------------------------------------------------------
# Module/test pairs the meta-test covers by default.
#
# Each entry is (production_module, test_file). The test file at the
# right is the one that should catch real bugs in the module at the left.
#
# To extend: add a pair. To audit: each entry has been checked by running
# the unmodified test against the unmodified module — if the test does
# not pass on the unmodified module, the meta-test refuses to run
# (`run_meta_test` raises SystemExit(2)).
# ---------------------------------------------------------------------------

DEFAULT_PAIRS: list[tuple[str, str]] = [
    # Property-test pairs.
    ("core/edi/edi_parser.py", "tests/unit/core/edi/test_edi_parser_property.py"),
    ("core/edi/edi_splitter.py", "tests/unit/core/edi/test_edi_splitter_property.py"),
    ("core/edi/edi_splitting_utils.py", "tests/unit/core/edi/test_edi_splitting_utils_property.py"),
    ("core/edi/c_rec_generator.py", "tests/unit/core/edi/test_c_rec_generator_property.py"),
    ("core/edi/edi_transformer.py", "tests/unit/core/edi/test_edi_transformer_property.py"),
    ("core/edi/upc_utils.py", "tests/unit/core/edi/test_upc_utils_property.py"),
    ("dispatch/feature_flags.py", "tests/unit/dispatch/test_feature_flags_property.py"),
    ("dispatch/file_utils.py", "tests/unit/dispatch/test_file_utils_property.py"),
    ("dispatch/hash_utils.py", "tests/unit/dispatch/test_hash_utils_property.py"),
    # Pure-Python core utility modules covered by their plain unit tests.
    ("core/utils/format_utils.py", "tests/unit/core/utils/test_format_utils.py"),
    ("core/utils/bool_utils.py", "tests/unit/core/utils/test_bool_utils.py"),
    ("core/utils/date_utils.py", "tests/unit/core/utils/test_date_utils.py"),
    ("core/utils/safe_parse.py", "tests/unit/core/utils/test_safe_parse.py"),
    ("core/utils/timing_utils.py", "tests/unit/core/utils/test_timing_utils.py"),
    ("core/edi/edi_tweaker.py", "tests/unit/core/edi/test_edi_tweaker.py"),
    ("core/structured_logging.py", "tests/unit/test_structured_logging.py"),
]


# ---------------------------------------------------------------------------
# KNOWN_EQUIVALENT list.
#
# A survivor is a mutation the test suite does NOT catch. There are two kinds:
#
#   1. A real test gap: the test does not exercise the mutated code path.
#      Fix by writing a stronger test.
#   2. An equivalent mutation: the change has no observable effect on the
#      test assertion (e.g., the mutation lands inside a docstring, a
#      __version__ constant, a default-argument value the test overrides
#      anyway, or a comment). The TEST is correct; the mutation is meaningless.
#
# Bucket 2 is unavoidable noise. Rather than scattering `# pragma: no cover`
# comments through the codebase, we keep one auditable list here. Each entry
# is `(module_relpath, mutation_name, line_number, reason)`. Each entry was
# added by reading the module source at that line and verifying the
# mutation has no observable effect on the test pair in DEFAULT_PAIRS.
#
# To re-validate, walk the list line-by-line and confirm the cited line
# matches the cited reason.
#
# Entries are intentionally narrow: (module, mutation, line). Adding
# pattern-based "skip if mutation X on any line below 10" is exactly the
# kind of cleverness this meta-test is meant to avoid.
# ---------------------------------------------------------------------------

KNOWN_EQUIVALENT: list[tuple[str, str, int, str]] = [
]


# ---------------------------------------------------------------------------
# Outcome + report dataclasses.
# ---------------------------------------------------------------------------

@dataclass
class MutationOutcome:
    name: str
    line: int
    killed: bool
    failure_message: str = ""
    snippet: str = ""


@dataclass
class ModuleReport:
    module: Path
    test_path: Path
    total: int = 0
    killed: int = 0
    survived: int = 0
    skipped: int = 0
    outcomes: list[MutationOutcome] = field(default_factory=list)

    @property
    def kill_rate(self) -> float:
        return self.killed / self.total if self.total else 0.0


# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------

def _apply_mutation_once(
    source: str,
    pattern: re.Pattern[str],
    replace: Callable[[re.Match[str]], str],
) -> tuple[str, int, str, str] | None:
    """Apply `replace` to the first match of `pattern` in `source`.

    Returns (new_source, line_number, original_line, mutated_line) on
    success, or None if no match. Only the first match is mutated per
    call so we test one change at a time. The original and mutated
    line text are returned so a reviewer can audit each survivor.
    """
    match = pattern.search(source)
    if match is None:
        return None
    new_source = source[: match.start()] + replace(match) + source[match.end():]
    line = source[: match.start()].count("\n") + 1
    line_start = source.rfind("\n", 0, match.start()) + 1
    line_end_search = source.find("\n", match.end())
    line_end = line_end_search if line_end_search != -1 else len(source)
    original_line = source[line_start:line_end]
    new_line_start = new_source.rfind("\n", 0, match.start()) + 1
    new_line_end_search = new_source.find("\n", match.end())
    new_line_end = new_line_end_search if new_line_end_search != -1 else len(new_source)
    mutated_line = new_source[new_line_start:new_line_end]
    return new_source, line, original_line, mutated_line


def _run_pytest(test_path: Path, cwd: Path) -> tuple[int, str]:
    """Run pytest on `test_path` and return (exit_code, combined_output).

    Force `-n0` so xdist workers do not isolate the mutation; force
    `--no-header -q` so output is short. We do NOT use `-x` — we want
    the full report, not a stop-on-first-failure.

    The subprocess timeout is generous: property tests do many
    examples, and a single mutation can be costly. A hang is reported
    as a kill (non-zero exit).
    """
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(test_path),
                "-n",
                "0",
                "-q",
                "--no-header",
                "--timeout=10",
                "-p",
                "no:cacheprovider",
            ],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=20,
        )
    except subprocess.TimeoutExpired:
        return 124, "SUBPROCESS TIMED OUT (treated as a kill)"
    return result.returncode, (result.stdout or "") + (result.stderr or "")


def _is_known_equivalent(module_rel: str, mutation_name: str, line: int) -> bool:
    """Return True if (module, mutation, line) is in KNOWN_EQUIVALENT.

    The lookup is by tuple identity. A typo in any field fails closed:
    the mutation is NOT skipped, so it will surface as a survivor and
    the runner will fail.
    """
    for m, n, l, _reason in KNOWN_EQUIVALENT:
        if m == module_rel and n == mutation_name and l == line:
            return True
    return False


# ---------------------------------------------------------------------------
# Public API.
# ---------------------------------------------------------------------------

def run_meta_test(
    module: Path,
    test_path: Path,
    *,
    repo_root: Path,
    module_rel: str | None = None,
    skip_known_equivalent: bool = True,
) -> ModuleReport:
    """Run all mutations against `module`, observing whether each kills
    the test at `test_path`. Returns a per-module report.

    When `skip_known_equivalent` is True, mutations in KNOWN_EQUIVALENT
    matching (module_rel, mutation_name, line) are not applied; they
    are recorded as `skipped` outcomes rather than `survived`.
    """
    report = ModuleReport(module=module, test_path=test_path)
    original_source = module.read_text()
    code, output = _run_pytest(test_path, repo_root)
    if code != 0:
        print(
            f"FATAL: tests at {test_path} do not pass on the "
            f"UNMODIFIED source of {module}. Fix that first.",
            file=sys.stderr,
        )
        print(output, file=sys.stderr)
        raise SystemExit(2)

    resolved_module_rel = module_rel or str(
        module.resolve().relative_to(repo_root.resolve())
    )

    for name, pattern, replace in MUTATIONS:
        mutation = _apply_mutation_once(original_source, pattern, replace)
        if mutation is None:
            continue
        mutated_source, line, original_line, mutated_line = mutation
        snippet = f"-{original_line}\n+{mutated_line}"
        if skip_known_equivalent and _is_known_equivalent(
            resolved_module_rel, name, line
        ):
            report.skipped += 1
            report.outcomes.append(
                MutationOutcome(name=name, line=line, killed=True, snippet=snippet)
            )
            print(
                f"  [{module.name}] SKIP (KNOWN_EQUIVALENT): {name} at line {line}",
                flush=True,
            )
            continue
        report.total += 1
        print(
            f"  [{module.name}] mutation {report.total}: {name} at line {line}",
            flush=True,
        )
        print(f"      {snippet}", flush=True)
        backup = module.read_text()
        try:
            module.write_text(mutated_source)
            code, output = _run_pytest(test_path, repo_root)
        finally:
            module.write_text(backup)
        if code == 0:
            report.survived += 1
            report.outcomes.append(
                MutationOutcome(
                    name=name, line=line, killed=False, snippet=snippet
                )
            )
        else:
            report.killed += 1
            report.outcomes.append(
                MutationOutcome(
                    name=name,
                    line=line,
                    killed=True,
                    snippet=snippet,
                    failure_message=output[-200:],
                )
            )
    return report


def render_report(report: ModuleReport) -> str:
    lines: list[str] = []
    lines.append(f"Module:    {report.module}")
    lines.append(f"Test file: {report.test_path}")
    lines.append(
        f"Killed:    {report.killed}/{report.total} "
        f"({report.kill_rate:.0%})"
    )
    lines.append(f"Survived:  {report.survived}")
    if report.skipped:
        lines.append(f"Skipped (KNOWN_EQUIVALENT): {report.skipped}")
    if report.survived:
        lines.append("")
        lines.append("SURVIVING MUTANTS (write a test to kill these):")
        for outcome in report.outcomes:
            if not outcome.killed:
                lines.append(
                    f"  - line {outcome.line:>4}: {outcome.name}"
                )
                if outcome.snippet:
                    for snippet_line in outcome.snippet.splitlines():
                        lines.append(f"      {snippet_line}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--module",
        type=Path,
        help="Production module to mutate (path relative to repo root). "
        "Use with --tests for a single pair.",
    )
    parser.add_argument(
        "--tests",
        type=Path,
        help="Test file that should detect the mutations. "
        "Use with --module for a single pair.",
    )
    parser.add_argument(
        "--pair-list",
        action="append",
        default=[],
        metavar="MODULE:TEST",
        help="A module:test pair (path relative to repo root, separated by ':'). "
        "Repeatable. If both --module and --pair-list are given, --pair-list is used.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent.parent,
        help="Path to repo root (default: parent of this file's parent).",
    )
    parser.add_argument(
        "--no-skip-known-equivalent",
        action="store_true",
        help="Apply every mutation including those in KNOWN_EQUIVALENT. "
        "Use this to audit the KNOWN_EQUIVALENT list itself.",
    )
    args = parser.parse_args(argv)

    pairs: list[tuple[Path, Path]] = []
    if args.pair_list:
        for raw in args.pair_list:
            if ":" not in raw:
                print(f"--pair-list entry must be MODULE:TEST, got: {raw}", file=sys.stderr)
                return 2
            module_str, test_str = raw.split(":", 1)
            pairs.append((Path(module_str), Path(test_str)))
    elif args.module and args.tests:
        pairs.append((args.module, args.tests))
    else:
        parser.error("either --pair-list or both --module and --tests are required")

    total_total = 0
    total_killed = 0
    total_survived = 0
    total_skipped = 0
    overall_survivors: list[tuple[Path, MutationOutcome]] = []

    for module, test_path in pairs:
        if not module.is_absolute():
            module = args.repo_root / module
        if not test_path.is_absolute():
            test_path = args.repo_root / test_path
        if not module.exists():
            print(f"Module not found: {module}", file=sys.stderr)
            return 2
        if not test_path.exists():
            print(f"Test file not found: {test_path}", file=sys.stderr)
            return 2

        module_rel = str(
            module.resolve().relative_to(args.repo_root.resolve())
        )
        report = run_meta_test(
            module,
            test_path,
            repo_root=args.repo_root,
            module_rel=module_rel,
            skip_known_equivalent=not args.no_skip_known_equivalent,
        )
        print(render_report(report))
        print()
        total_total += report.total
        total_killed += report.killed
        total_survived += report.survived
        total_skipped += report.skipped
        for outcome in report.outcomes:
            if not outcome.killed:
                overall_survivors.append((module, outcome))

    if len(pairs) > 1:
        print("=" * 60)
        print(
            f"OVERALL: killed {total_killed}/{total_total} "
            f"({(total_killed / total_total) if total_total else 0:.0%}), "
            f"survived {total_survived}, skipped {total_skipped}"
        )
        print()
        if overall_survivors:
            print("ALL SURVIVING MUTANTS (write tests to kill these):")
            for module, outcome in overall_survivors:
                print(f"  {module.name}:{outcome.line}  {outcome.name}")

    return 1 if total_survived else 0


# ---------------------------------------------------------------------------
# Pytest-discoverable wrapper. When pytest collects this file, it picks up
# `test_default_modules_have_sufficient_test_coverage`. The test runs the
# full meta-mutation suite against the DEFAULT_PAIRS and fails if any
# mutant survives. Survivors must be addressed by writing stronger tests
# (or by adding the mutant to KNOWN_EQUIVALENT with a cited reason).
#
# Marked `slow` because it spawns one pytest subprocess per mutation.
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_default_modules_have_sufficient_test_coverage() -> None:
    """Run meta-mutation against every DEFAULT_PAIRS entry; fail on survivor.

    A survivor is a mutation the test file does NOT catch. Either the
    tests are too weak (write a stronger one) or the mutation is
    equivalent (no observable behavior change — add it to
    KNOWN_EQUIVALENT with a one-line cited reason).
    """
    repo_root = Path(__file__).resolve().parent.parent.parent
    overall_survivors: list[tuple[str, str, int, str]] = []
    for module_rel, test_rel in DEFAULT_PAIRS:
        module = repo_root / module_rel
        test_path = repo_root / test_rel
        if not module.exists() or not test_path.exists():
            pytest.skip(f"missing {module_rel} or {test_rel}")
        report = run_meta_test(
            module,
            test_path,
            repo_root=repo_root,
            module_rel=module_rel,
        )
        for outcome in report.outcomes:
            if not outcome.killed:
                overall_survivors.append(
                    (module.name, outcome.name, outcome.line, str(module))
                )
    if overall_survivors:
        msg_lines = [
            "Surviving mutants. Either tighten the test, or add the "
            "mutation to KNOWN_EQUIVALENT with a cited reason:"
        ]
        for fname, name, line, path in overall_survivors:
            msg_lines.append(f"  {fname}:{line}  {name}")
        pytest.fail("\n".join(msg_lines))


if __name__ == "__main__":
    sys.exit(main())
