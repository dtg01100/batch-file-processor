#!/usr/bin/env python3
"""Parse a JUnit XML file produced by pytest and write human-readable reports.

Usage
-----
    python scripts/generate_test_report.py <path/to/results.xml>

Outputs (written to the same directory as the XML file)
-------
    human_summary.txt        -- readable pass/fail summary with slow-test table
    enhancement_suggestions.txt -- static list of improvement ideas
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class TestCase:
    classname: str
    name: str
    time: float
    status: str  # "passed" | "failed" | "error" | "skipped"
    message: str = ""
    module: str = field(init=False)

    def __post_init__(self) -> None:
        # Derive module from classname (e.g. "tests.integration.test_foo::TestBar" → "test_foo")
        parts = self.classname.replace("::", ".").split(".")
        # Last dotted segment before the class name, or the classname itself
        self.module = parts[-1] if len(parts) == 1 else parts[-2]


@dataclass
class SuiteStats:
    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    elapsed: float = 0.0
    cases: list[TestCase] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def parse_junit_xml(xml_path: Path) -> SuiteStats:
    """Parse a JUnit XML file and return aggregated statistics."""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Support both <testsuites> wrapper and bare <testsuite>
    suites = root.findall(".//testsuite") if root.tag == "testsuites" else [root]

    stats = SuiteStats()
    for suite in suites:
        stats.total += int(suite.get("tests", 0))
        stats.failed += int(suite.get("failures", 0))
        stats.errors += int(suite.get("errors", 0))
        stats.skipped += int(suite.get("skipped", 0))
        try:
            stats.elapsed += float(suite.get("time", 0))
        except ValueError:
            pass

        for tc in suite.findall("testcase"):
            classname = tc.get("classname", "unknown")
            name = tc.get("name", "unknown")
            try:
                duration = float(tc.get("time", 0))
            except ValueError:
                duration = 0.0

            failure = tc.find("failure")
            error = tc.find("error")
            skipped = tc.find("skipped")

            if failure is not None:
                status = "failed"
                message = (failure.get("message") or failure.text or "").strip()
            elif error is not None:
                status = "error"
                message = (error.get("message") or error.text or "").strip()
            elif skipped is not None:
                status = "skipped"
                message = (skipped.get("message") or skipped.text or "").strip()
            else:
                status = "passed"
                message = ""

            stats.cases.append(
                TestCase(
                    classname=classname,
                    name=name,
                    time=duration,
                    status=status,
                    message=message,
                )
            )

    stats.passed = stats.total - stats.failed - stats.errors - stats.skipped
    return stats


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def _section(title: str, width: int = 60) -> str:
    bar = "=" * width
    return f"\n{bar}\n  {title}\n{bar}\n"


def build_human_summary(stats: SuiteStats, xml_path: Path) -> str:
    lines: list[str] = []

    lines.append("Batch File Processor -- Test Run Report")
    lines.append(f"Source XML : {xml_path}")
    lines.append("")

    # --- Totals -----------------------------------------------------------------
    lines.append(_section("Overall Results"))
    lines.append(f"  Total     : {stats.total}")
    lines.append(f"  Passed    : {stats.passed}")
    lines.append(f"  Failed    : {stats.failed}")
    lines.append(f"  Errors    : {stats.errors}")
    lines.append(f"  Skipped   : {stats.skipped}")
    lines.append(f"  Duration  : {stats.elapsed:.2f} s")
    pass_rate = (stats.passed / stats.total * 100) if stats.total else 0.0
    lines.append(f"  Pass rate : {pass_rate:.1f}%")

    # --- Failed / errored tests -------------------------------------------------
    bad = [c for c in stats.cases if c.status in ("failed", "error")]
    lines.append(_section(f"Failed / Errored Tests ({len(bad)})"))
    if not bad:
        lines.append("  (none)")
    else:
        for tc in bad:
            lines.append(f"  [{tc.status.upper()}] {tc.classname}::{tc.name}")
            if tc.message:
                # Indent the first 5 lines of the message
                msg_lines = tc.message.splitlines()[:5]
                for ml in msg_lines:
                    lines.append(f"      {ml}")
            lines.append("")

    # --- Top 5 slowest tests ----------------------------------------------------
    sorted_cases = sorted(stats.cases, key=lambda c: c.time, reverse=True)
    top5 = sorted_cases[:5]
    lines.append(_section("Top 5 Slowest Tests"))
    header = f"  {'Time (s)':>10}  {'Status':<8}  Test"
    lines.append(header)
    lines.append("  " + "-" * 56)
    for tc in top5:
        lines.append(f"  {tc.time:>10.3f}  {tc.status:<8}  {tc.classname}::{tc.name}")

    # --- Breakdown by module ----------------------------------------------------
    lines.append(_section("Results by Module"))
    module_map: dict[str, dict[str, int]] = {}
    for tc in stats.cases:
        mod = tc.module
        if mod not in module_map:
            module_map[mod] = {"passed": 0, "failed": 0, "error": 0, "skipped": 0}
        if tc.status in module_map[mod]:
            module_map[mod][tc.status] += 1
        else:
            module_map[mod]["passed"] += 1  # unknown → treat as passed

    col = f"  {'Module':<45} {'Pass':>5} {'Fail':>5} {'Err':>5} {'Skip':>5}"
    lines.append(col)
    lines.append("  " + "-" * 65)
    for mod in sorted(module_map):
        d = module_map[mod]
        lines.append(
            f"  {mod:<45} {d['passed']:>5} {d['failed']:>5} {d['error']:>5} {d['skipped']:>5}"
        )

    lines.append("")
    return "\n".join(lines)


ENHANCEMENT_SUGGESTIONS = """\
Batch File Processor -- Test Enhancement Suggestions
====================================================

The following improvements are recommended for the test suite:

1. Property-based testing with Hypothesis
   - Generate arbitrary file names, sizes, and content to stress-test the
     FTP / SMTP upload paths and the checksum deduplication logic.

2. Mutation testing with mutmut or cosmic-ray
   - Run mutation testing on core/ and dispatch/ to measure true test
     effectiveness and expose logic gaps not caught by coverage alone.

3. Contract tests for backend clients
   - Define explicit interface contracts (using pact or plain assertion
     helpers) so that MockFTPClient and MockSMTPClient can be validated
     against the real client classes automatically.

4. Load / stress tests for the orchestrator
   - Introduce a pytest-benchmark or locust scenario that exercises
     DispatchOrchestrator with 1,000+ files to detect performance
     regressions in _filter_processed_files and _record_processed_file.

5. Parallel-safe database fixtures
   - Replace the session-scoped db_template with a process-isolated variant
     so that xdist workers do not share a SQLite file, enabling full
     parallelism with pytest-xdist.

6. Flakiness detection
   - Run the test suite three times in CI (pytest --count=3 via
     pytest-repeat) and flag any test that changes result between runs as
     flaky.

7. Coverage enforcement
   - Add a coverage gate (--cov-fail-under=85) to the CI pipeline so that
     new pull requests cannot decrease overall coverage.

8. Snapshot / golden-file tests for EDI output
   - Capture known-good EDI file contents as golden fixtures and assert
     byte-for-byte equality after conversion, preventing silent regressions.

9. Timeout tightening
   - Reduce the global pytest timeout from 60 s to 30 s and add
     @pytest.mark.timeout(5) on unit tests to catch slow unit tests early.

10. Integration with a real FTP server in CI
    - Add an optional pytest mark (real_ftp) and a Docker-Compose service
      (e.g. stilliard/pure-ftpd) so that the full FTP path can be exercised
      on demand without affecting the default fast suite.
"""


def write_reports(stats: SuiteStats, xml_path: Path) -> None:
    out_dir = xml_path.parent

    summary_path = out_dir / "human_summary.txt"
    summary_path.write_text(build_human_summary(stats, xml_path), encoding="utf-8")
    print(f"Written: {summary_path}")

    suggestions_path = out_dir / "enhancement_suggestions.txt"
    suggestions_path.write_text(ENHANCEMENT_SUGGESTIONS, encoding="utf-8")
    print(f"Written: {suggestions_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <path/to/results.xml>", file=sys.stderr)
        return 2

    xml_path = Path(sys.argv[1])
    if not xml_path.is_file():
        print(f"Error: file not found: {xml_path}", file=sys.stderr)
        return 1

    stats = parse_junit_xml(xml_path)
    write_reports(stats, xml_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
