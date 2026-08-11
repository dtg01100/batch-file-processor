"""Import every module in the repository as the FIRST import of a fresh subprocess.

Import cycles in Python are order-dependent: ``import dispatch.results`` works
if ``dispatch.pipeline`` happens to load first in the same process, but crashes
as a first import in a fresh interpreter. Ordinary test runs mask these cycles,
so this script checks every module the way a fresh entry point would see it.

Usage::

    python scripts/import_check.py                  # production modules only
    python scripts/import_check.py --include-tests  # also check tests/ modules
    python scripts/import_check.py --jobs 16        # more parallelism

Exit code is 0 when every module imports cleanly, 1 otherwise.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import re
import subprocess
import sys
import time
from pathlib import Path

# Directories that are never part of the shipped import graph.
EXCLUDED_DIRS = {
    ".freebuff",
    ".git",
    ".pytest_temp",
    ".venv",
    "__pycache__",
    "archive",
    "build",
    "build_wine",
    "dist",
}

# Exception categories worth distinguishing in the report.
_ERROR_RE = re.compile(r"^([A-Za-z_][\w.]*(?:Error|Exception|Warning)):")

# Modules that are audited to fail as first imports for known, deliberate
# reasons (as of 2026-08-09). They are reported but do not fail the run, so
# the script can act as a CI guard for NEW import cycles. Each entry is the
# module path relative to the repo root, mapped to why it is expected to fail.
KNOWN_FAILURES: dict[str, str] = {}


def discover_modules(root: Path, include_tests: bool) -> list[tuple[str, str]]:
    """Return ``(relative_path, module_name)`` pairs for every importable module."""
    modules: list[tuple[str, str]] = []
    for py in sorted(root.rglob("*.py")):
        parts = list(py.relative_to(root).parts)
        if any(part in EXCLUDED_DIRS for part in parts):
            continue
        if not include_tests and parts[0] == "tests":
            continue
        if parts[-1] == "__main__.py":
            continue
        if parts[-1] == "__init__.py":
            name = ".".join(parts[:-1])
        else:
            name = ".".join((*parts[:-1], parts[-1][:-3]))
        if not name:
            continue
        # A dash in the module name (e.g. PyInstaller ``hook-*.py`` files) can
        # never be imported — skip rather than report a guaranteed failure.
        if any("-" in part for part in name.split(".")):
            continue
        modules.append((str(py.relative_to(root)), name))
    return modules


def classify_stderr(stderr: str) -> str:
    """Extract the exception type from a traceback's last lines, if any."""
    for line in reversed(stderr.splitlines()):
        line = line.strip()
        match = _ERROR_RE.match(line)
        if match:
            return match.group(1)
    return "UnknownError"


def check_module(
    root: Path, rel: str, name: str, timeout: int
) -> tuple[str, str, str, int]:
    """Import ``name`` as the first import of a fresh interpreter."""
    try:
        proc = subprocess.run(
            [sys.executable, "-c", f"import {name}"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return rel, name, "Timeout", 124
    if proc.returncode == 0:
        return rel, name, "", 0
    return rel, name, classify_stderr(proc.stderr), proc.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--include-tests",
        action="store_true",
        help="also check modules under tests/ (noisy: test modules can rely "
        "on pytest conftest state at import time)",
    )
    parser.add_argument(
        "--jobs", type=int, default=8, help="parallel subprocesses (default: 8)"
    )
    parser.add_argument(
        "--timeout", type=int, default=120, help="per-module timeout seconds"
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    modules = discover_modules(root, args.include_tests)
    if not modules:
        print("No modules found.", file=sys.stderr)
        return 1

    print(
        f"Checking {len(modules)} modules as first imports " f"({args.jobs} workers)..."
    )
    start = time.monotonic()
    failures: list[tuple[str, str, str, int]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {
            pool.submit(check_module, root, rel, name, args.timeout): (rel, name)
            for rel, name in modules
        }
        for future in concurrent.futures.as_completed(futures):
            rel, name, error, code = future.result()
            if error:
                failures.append((rel, name, error, code))
    elapsed = time.monotonic() - start

    known = [f for f in failures if f[0] in KNOWN_FAILURES]
    unknown = [f for f in failures if f[0] not in KNOWN_FAILURES]
    passed = len(modules) - len(failures)
    print(f"\n{passed}/{len(modules)} modules import cleanly " f"({elapsed:.1f}s)")

    if known:
        print("\n=== KNOWN-BENIGN FAILURES (audited, do not fail the run) ===")
        for rel, _name, error, _code in sorted(known):
            reason = KNOWN_FAILURES[rel]
            print(f"  {rel:<50} {error} ({reason})")

    if unknown:
        print("\n=== NEW FAILURES (by exception type) ===")
        by_type: dict[str, list[tuple[str, str, int]]] = {}
        for rel, name, error, code in unknown:
            by_type.setdefault(error, []).append((rel, name, code))
        for error in sorted(by_type):
            entries = by_type[error]
            print(f"\n{error} ({len(entries)}):")
            for rel, name, code in sorted(entries):
                print(f"  {rel:<65} -> import {name} (exit {code})")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
