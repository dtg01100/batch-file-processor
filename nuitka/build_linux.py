#!/usr/bin/env python3
"""Linux dev build driver for the Nuitka transition.

Phase 5 step 5.3.1/5.3.2 of plans/QT6_AND_MODERN_PYTHON_MIGRATION_PLAN.md.
Per plan decision N3, this produces a STANDALONE (folder) build
for local smoke testing - same Python version, same dependencies,
no Windows MSVC dependency. The shipping Windows onefile build
will be handled by build_windows.py + Dockerfile.windows.build.

Usage:
    python nuitka/build_linux.py            # standalone, default
    python nuitka/build_linux.py --onefile  # onefile for parity testing
    python nuitka/build_linux.py --clean    # nuke build/ before building
    python nuitka/build_linux.py --output build/nuitka-app

Validation-only (no actual build):
    python nuitka/build_linux.py --dry-run  # print the command, don't run
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from nuitka_config import (
    COMPANY_NAME,
    ENABLED_PLUGINS,
    ENTRY_POINT,
    FILE_VERSION,
    INCLUDED_DATA_DIRS,
    INCLUDED_MODULES,
    INCLUDED_PACKAGES,
    PRODUCT_NAME,
    PRODUCT_VERSION,
)


def build_argparse() -> argparse.ArgumentParser:
    """Construct the CLI argument parser."""
    description = (
        "Linux dev build driver for the Nuitka transition. "
        "See plans/QT6_AND_MODERN_PYTHON_MIGRATION_PLAN.md Phase 5."
    )
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--onefile",
        action="store_true",
        help="Produce a onefile binary instead of standalone folder.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove the output directory before building.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("build/nuitka-app"),
        help="Output directory (default: build/nuitka-app).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the command that would be run, but don't run it.",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("build/nuitka-cache"),
        help="Nuitka cache directory (default: build/nuitka-cache).",
    )
    return parser


def build_command(args: argparse.Namespace) -> list[str]:
    """Construct the python -m nuitka invocation from the config + args."""
    cmd: list[str] = [
        sys.executable,
        "-m",
        "nuitka",
        f"--output-filename={args.output.name}",
        "--output-dir=" + str(args.output.parent),
        "--company-name=" + COMPANY_NAME,
        "--product-name=" + PRODUCT_NAME,
        "--file-version=" + FILE_VERSION,
        "--product-version=" + PRODUCT_VERSION,
    ]

    if args.onefile:
        cmd.append("--onefile")
    else:
        cmd.extend(["--standalone", "--no-onefile"])

    for plugin in ENABLED_PLUGINS:
        cmd.append(f"--enable-plugin={plugin}")

    for package in INCLUDED_PACKAGES:
        cmd.append(f"--include-package={package}")

    for module in INCLUDED_MODULES:
        cmd.append(f"--include-module={module}")

    for src, dest in INCLUDED_DATA_DIRS:
        cmd.append(f"--include-data-dir={src}={dest}")

    cmd.append(f"--cache-dir={args.cache_dir}")
    cmd.append(ENTRY_POINT)
    return cmd


def main() -> int:
    """Parse args, build the Nuitka command, and (optionally) run it."""
    args = build_argparse().parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.cache_dir.mkdir(parents=True, exist_ok=True)

    if args.clean and args.output.parent.exists():
        print(f"Cleaning {args.output.parent} ...")
        if args.output.parent.resolve() != Path.cwd().resolve():
            shutil.rmtree(args.output.parent)
        else:
            print("Refusing to clean cwd.")

    cmd = build_command(args)
    print("Command:")
    print("  " + " ".join(cmd))

    if args.dry_run:
        return 0

    result = subprocess.run(cmd, cwd=Path.cwd())
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
