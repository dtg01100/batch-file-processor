#!/usr/bin/env python3
"""Test runner script for batch-file-processor.

Allows running tests in parts to avoid timeouts.
Cross-platform alternative to run_tests.sh.
"""

import argparse
import subprocess
import sys
from typing import List, Optional


# ANSI color codes
class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    NC = "\033[0m"  # No Color


# Test suite definitions
TEST_SUITES = {
    "unit": ("unit", "Unit Tests", "Fast, isolated tests"),
    "integration": ("integration", "Integration Tests", "Tests with real components"),
    "qt": ("qt", "Qt/UI Tests", "GUI tests using pytest-qt"),
    "e2e": ("e2e", "End-to-End Tests", "Full workflow tests"),
    "fast": ("fast", "Fast Tests", "Tests completing in < 5 seconds"),
    "slow": ("slow", "Slow Tests", "Tests taking > 30 seconds"),
    "database": ("database", "Database Tests", "Database-related tests"),
    "backend": ("backend", "Backend Tests", "FTP, Email, Copy backend tests"),
    "conversion": ("conversion", "Conversion Tests", "File conversion tests"),
    "dispatch": ("dispatch", "Dispatch Tests", "Orchestration tests"),
    "workflow": ("workflow", "Workflow Tests", "Complete workflow tests"),
    "upgrade": ("upgrade", "Upgrade Tests", "Database upgrade tests"),
    "pyinstaller": ("pyinstaller", "PyInstaller Tests", "Build integration tests"),
    "gui": ("gui", "GUI Tests", "User interface tests"),
}


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"{Colors.BLUE}{'=' * 50}{Colors.NC}")
    print(f"{Colors.BLUE}{text}{Colors.NC}")
    print(f"{Colors.BLUE}{'=' * 50}{Colors.NC}")
    print()


def print_success(text: str) -> None:
    """Print a success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.NC}")


def print_error(text: str) -> None:
    """Print an error message."""
    print(f"{Colors.RED}✗ {text}{Colors.NC}")


def print_warning(text: str) -> None:
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.NC}")


def build_pytest_command(
    marker: Optional[str],
    verbose: bool,
    exitfirst: bool,
    timeout: int,
    extra_args: List[str],
) -> List[str]:
    """Build the pytest command."""
    cmd = [sys.executable, "-m", "pytest", "tests", "-v"]

    if verbose:
        cmd.append("-v")

    if exitfirst:
        cmd.append("-x")

    if marker:
        cmd.extend(["-m", marker])

    cmd.extend(["--timeout", str(timeout)])
    cmd.extend(extra_args)

    return cmd


def run_tests(
    marker: Optional[str],
    description: str,
    args: argparse.Namespace,
    extra_args: Optional[List[str]] = None,
) -> int:
    """Run tests with the given marker."""
    print_header(description)

    cmd = build_pytest_command(
        marker=marker,
        verbose=args.verbose,
        exitfirst=args.exitfirst,
        timeout=args.timeout,
        extra_args=extra_args or [],
    )

    try:
        result = subprocess.run(cmd, check=False)
        print()

        if result.returncode == 0:
            print_success(f"{description} passed")
        else:
            print_error(f"{description} failed")

        return result.returncode
    except KeyboardInterrupt:
        print_warning("Test run interrupted")
        return 130
    except Exception as e:
        print_error(f"Error running tests: {e}")
        return 1


def list_suites() -> None:
    """List available test suites."""
    print(f"{Colors.BLUE}Available Test Suites:{Colors.NC}")
    print()
    for name, (marker, title, description) in TEST_SUITES.items():
        print(f"  {name:15} - {title}")
        print(f"{'':17}  {description}")
        print()


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run tests for batch-file-processor in parts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s unit -v                    # Run unit tests with verbose output
  %(prog)s integration --timeout 600  # Run integration tests with 10 min timeout
  %(prog)s ci -x                      # CI mode, exit on first failure
  %(prog)s quick                      # Run unit + fast tests
        """,
    )

    parser.add_argument(
        "suite",
        choices=list(TEST_SUITES.keys())
        + ["all", "quick", "ci", "list", "help"],
        help="Test suite to run",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose output",
    )

    parser.add_argument(
        "-x",
        "--exitfirst",
        action="store_true",
        help="Exit on first failure",
    )

    parser.add_argument(
        "-k",
        "--expression",
        metavar="EXPRESSION",
        help="Only run tests matching expression",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Test timeout in seconds (default: 300)",
    )

    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_suites",
        help="List available test suites",
    )

    args = parser.parse_args()

    if args.list_suites or args.suite == "list":
        list_suites()
        return 0

    if args.suite == "help":
        parser.print_help()
        return 0

    extra_args = []
    if args.expression:
        extra_args.extend(["-k", args.expression])

    # Handle special suites
    if args.suite == "all":
        print_warning("Running all tests may exceed timeout limits")
        return run_tests(None, "All Tests", args, extra_args)

    elif args.suite == "quick":
        print(f"{Colors.BLUE}Running quick test suite (unit + fast)...{Colors.NC}")
        return run_tests("unit or fast", "Quick Tests", args, extra_args)

    elif args.suite == "ci":
        print(f"{Colors.BLUE}Running CI test suite (excludes slow tests)...{Colors.NC}")
        return run_tests("not slow", "CI Tests", args, extra_args)

    else:
        marker, title, _ = TEST_SUITES[args.suite]
        return run_tests(marker, title, args, extra_args)


if __name__ == "__main__":
    sys.exit(main())
