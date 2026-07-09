"""Brutally simple mutation meta-test.

The hypothesis property tests in tests/unit/**/*_property.py protect
production modules. This meta-test asks the question: are those property
from __future__ import annotations

import argparse
import ast
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
- The mutation set is a fixed small list. It is NOT exhaustive mutation
  testing (use mutmut for that). It is a smoke-test of the test suite
  itself.
- Performance is not a concern: this script runs once per meta-test
  invocation. A 5x slow test run is fine.
- The script is a single file, no plugin framework, no config files.
  Read the source, understand the result.

Usage:
    python tests/meta/test_property_tests_are_sufficient.py \
        --module core/edi/edi_parser.py \
        --tests tests/unit/core/edi/test_edi_parser_property.py
"""

from __future__ import annotations

import argparse
import pytest
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Mutation rules. Each is a (name, find_regex, replace_func) triple.
# find_regex is a compiled pattern; replace_func is a callable that takes
# a regex match and returns the replacement string.
# Keep this list small and obviously meaningful. If you find yourself
# adding a mutation that doesn't map to a real bug class, drop it.
# ---------------------------------------------------------------------------

MUTATIONS: list[tuple[str, re.Pattern[str], Callable[[re.Match[str]], str]]] = [
    # Comparison swaps. Each is a real bug a careless edit can introduce.
    ("lt_to_le", re.compile(r"\s*<\s*"), lambda m: re.sub(r"<\s*", "<= ", m.group(0), count=1)),
    ("le_to_lt", re.compile(r"\s*<=\s*"), lambda m: re.sub(r"<=\s*", "< ", m.group(0), count=1)),
    ("gt_to_ge", re.compile(r"\s*>\s*"), lambda m: re.sub(r">\s*", ">= ", m.group(0), count=1)),
    ("ge_to_gt", re.compile(r"\s*>=\s*"), lambda m: re.sub(r">=\s*", "> ", m.group(0), count=1)),
    # Equality swaps.
    ("eq_to_ne", re.compile(r"\s*==\s*"), lambda m: re.sub(r"==\s*", "!= ", m.group(0), count=1)),
    ("ne_to_eq", re.compile(r"\s*!=\s*"), lambda m: re.sub(r"!=\s*", "== ", m.group(0), count=1)),
    # Boolean flips. These are the most subtle bugs — they survive diff
    # review because the code "still looks right".
    ("true_to_false", re.compile(r"\bTrue\b"), lambda m: "False"),
    ("false_to_true", re.compile(r"\bFalse\b"), lambda m: "True"),
    # Connector swaps. A single `and` -> `or` is a classic branch-table
    # bug.
    ("and_to_or", re.compile(r"\band\b"), lambda m: "or"),
    ("or_to_and", re.compile(r"\bor\b"), lambda m: "and"),
    # return-statement swap. Returning the literal `None` instead of the
    # computed value is a common mistake when adding an early exit.
    (
        "return_none_instead_of_value",
        re.compile(r"return\s+(?!None\b)([A-Za-z_][A-Za-z0-9_\.\(\)]+)"),
        lambda m: "return None",
    ),
    # Drop an `if` guard's body. A regression that removes a validation
    # check.
    (
        "negate_if_condition",
        re.compile(r"if\s+(.+?):"),
        lambda m: f"if not ({m.group(1)}):",
    ),
    # Off-by-one in integer constants. Matches a literal int and flips
    # the last digit; the result is "close enough" to look like a
    # typo rather than a real change. Skip if the int is 0 or 1
    # (those often mean False/True or boundary constants we don't
    # want to perturb).
    (
        "int_constant_off_by_one",
        re.compile(r"\b([2-9]\d*|1\d+)\b"),
        lambda m: str(int(m.group(1)) + 1),
    ),
]


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
    outcomes: list[MutationOutcome] = field(default_factory=list)

    @property
    def kill_rate(self) -> float:
        return self.killed / self.total if self.total else 0.0


def _apply_mutation_once(
    source: str,
    pattern: re.Pattern[str],
    replace: Callable[[re.Match[str]], str],
) -> tuple[str, int] | None:
    """Apply `replace` to the first match of `pattern` in `source`.

    Returns (new_source, line_number) on success, or None if no match.
    Only the first match is mutated per call so we test one change at a time.
    """
    match = pattern.search(source)
    if match is None:
        return None
    new_source = source[: match.start()] + replace(match) + source[match.end():]
    line = source[: match.start()].count("\n") + 1
    return new_source, line


def _run_pytest(test_path: Path, cwd: Path) -> tuple[int, str]:
    """Run pytest on `test_path` and return (exit_code, combined_output).

    Force `-n0` so xdist workers do not isolate the mutation; force
    `--no-header -q` so output is short. We do NOT use `-x` — we want
    the full report, not a stop-on-first-failure.

    The subprocess timeout is generous: property tests do many
    examples, and a single mutation can be costly. We do not optimize
    for speed; the user explicitly asked for thorough-but-simple.
    A hang is reported as a kill (non-zero exit).
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


def run_meta_test(
    module: Path,
    test_path: Path,
    *,
    repo_root: Path,
) -> ModuleReport:
    """Run all mutations against `module`, observing whether each kills
    the property test at `test_path`. Returns a per-module report.
    """
    report = ModuleReport(module=module, test_path=test_path)
    original_source = module.read_text()
    # Sanity: the unmodified tests must pass on the original source.
    code, output = _run_pytest(test_path, repo_root)
    if code != 0:
        print(
            f"FATAL: property tests at {test_path} do not pass on the "
            f"UNMODIFIED source of {module}. Fix that first.",
            file=sys.stderr,
        )
        print(output, file=sys.stderr)
        raise SystemExit(2)

    for name, pattern, replace in MUTATIONS:
        mutation = _apply_mutation_once(original_source, pattern, replace)
        if mutation is None:
            # Pattern did not match — module does not contain the
            # target construct. Skip silently.
            continue
        mutated_source, line = mutation
        report.total += 1
        print(f"  [{module.name}] mutation {report.total}: {name} at line {line}", flush=True)
        with tempfile.TemporaryDirectory():
            backup = module.read_text()
            # We have to run pytest from a directory where the module
            # can be imported at its original path. Simplest approach:
            # write the mutated file over the original, run pytest,
            # restore. The restore is wrapped in try/finally.
            backup = module.read_text()
            try:
                module.write_text(mutated_source)
                code, output = _run_pytest(test_path, repo_root)
            finally:
                module.write_text(backup)
        if code == 0:
            report.survived += 1
            report.outcomes.append(
                MutationOutcome(name=name, line=line, killed=False)
            )
        else:
            report.killed += 1
            report.outcomes.append(
                MutationOutcome(
                    name=name, line=line, killed=True, failure_message=output[-200:]
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
    if report.survived:
        lines.append("")
        lines.append("SURVIVING MUTANTS (write a test to kill these):")
        for outcome in report.outcomes:
            if not outcome.killed:
                lines.append(
                    f"  - line {outcome.line:>4}: {outcome.name}"
                )
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
        help="Property test file that should detect the mutations. "
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

        report = run_meta_test(module, test_path, repo_root=args.repo_root)
        print(render_report(report))
        print()
        total_total += report.total
        total_killed += report.killed
        total_survived += report.survived
        for outcome in report.outcomes:
            if not outcome.killed:
                overall_survivors.append((module, outcome))

    if len(pairs) > 1:
        print("=" * 60)
        print(f"OVERALL: killed {total_killed}/{total_total} "
              f"({total_killed / total_total:.0%} if total else 0), "
              f"survived {total_survived}")
        print()
        if overall_survivors:
            print("ALL SURVIVING MUTANTS (write tests to kill these):")
            for module, outcome in overall_survivors:
                print(f"  {module.name}:{outcome.line}  {outcome.name}")

    return 1 if total_survived else 0


# ---------------------------------------------------------------------------
# Pytest-discoverable wrapper. When pytest collects this file, it picks up
# `test_property_tests_sufficient_for_default_modules`. The test runs the
# full meta-mutation suite against the default 9 module/test pairs and
# fails if any mutant survives. Survivors must be addressed by writing
# stronger property tests (or by documenting the mutant as equivalent).
# ---------------------------------------------------------------------------

DEFAULT_PAIRS: list[tuple[str, str]] = [
    # Original 9 property-test pairs.
    ("core/edi/edi_parser.py", "tests/unit/core/edi/test_edi_parser_property.py"),
    ("core/edi/edi_splitter.py", "tests/unit/core/edi/test_edi_splitter_property.py"),
    ("core/edi/edi_splitting_utils.py", "tests/unit/core/edi/test_edi_splitting_utils_property.py"),
    ("core/edi/c_rec_generator.py", "tests/unit/core/edi/test_c_rec_generator_property.py"),
    ("core/edi/edi_transformer.py", "tests/unit/core/edi/test_edi_transformer_property.py"),
    ("core/edi/upc_utils.py", "tests/unit/core/edi/test_upc_utils_property.py"),
    ("dispatch/feature_flags.py", "tests/unit/dispatch/test_feature_flags_property.py"),
    ("dispatch/file_utils.py", "tests/unit/dispatch/test_file_utils_property.py"),
    ("dispatch/hash_utils.py", "tests/unit/dispatch/test_hash_utils_property.py"),
    # Pure-Python core utility modules covered by their non-property tests.
    ("core/utils/format_utils.py", "tests/unit/core/utils/test_format_utils.py"),
    ("core/utils/bool_utils.py", "tests/unit/core/utils/test_bool_utils.py"),
    ("core/utils/date_utils.py", "tests/unit/core/utils/test_date_utils.py"),
    ("core/utils/safe_parse.py", "tests/unit/core/utils/test_safe_parse.py"),
    ("core/utils/timing_utils.py", "tests/unit/core/utils/test_timing_utils.py"),
    # Additional pure-Python EDI helpers covered by their non-property tests.
    ("core/edi/edi_tweaker.py", "tests/unit/core/edi/test_edi_tweaker.py"),
    # dispatch sub-modules with focused unit tests.
    ("core/structured_logging.py", "tests/unit/test_structured_logging.py"),
]

@pytest.mark.slow
def test_property_tests_sufficient_for_default_modules(tmp_path_factory) -> None:
    """Run meta-mutation against each default property-test pair and assert no survivors.

    A survivor is a mutation the property tests do NOT catch. Either the
    tests are too weak (write a stronger one) or the mutation is
    equivalent (no observable behavior change — record it and skip).
    """
    import pytest
    repo_root = Path(__file__).resolve().parent.parent.parent
    overall_survivors: list[tuple[str, str, int, str]] = []
    for module_rel, test_rel in DEFAULT_PAIRS:
        module = repo_root / module_rel
        test_path = repo_root / test_rel
        if not module.exists() or not test_path.exists():
            pytest.skip(f"missing {module_rel} or {test_rel}")
        report = run_meta_test(module, test_path, repo_root=repo_root)
        for outcome in report.outcomes:
            if not outcome.killed:
                overall_survivors.append(
                    (module.name, outcome.name, outcome.line, str(module))
                )
    if overall_survivors:
        msg_lines = ["Surviving mutants (write tests or document as equivalent):"]
        for fname, name, line, path in overall_survivors:
            msg_lines.append(f"  {fname}:{line}  {name}")
        pytest.fail("\n".join(msg_lines))


if __name__ == "__main__":
    sys.exit(main())
