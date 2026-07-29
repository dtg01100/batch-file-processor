#!/usr/bin/env python3
"""Windows build driver for the Nuitka transition.

Phase 5 of plans/QT6_AND_MODERN_PYTHON_MIGRATION_PLAN.md.

Status: scaffold only. The full Windows onefile build requires
MSVC build tools (plan decision N2), which are not available in
this environment. The Docker-based build path
(Dockerfile.windows.build.nuitka) and the build_windows.sh shim
that calls it are the production build targets and will land in a
follow-up.

Usage:
    python nuitka/build_windows.py            # onefile, default
    python nuitka/build_windows.py --dry-run  # print the command
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from nuitka_config import (
    COMPANY_NAME,
    DEFAULT_FLAVOR_WINDOWS,
    ENABLED_PLUGINS,
    ENTRY_POINT,
    FILE_VERSION,
    INCLUDED_DATA_DIRS,
    INCLUDED_MODULES,
    INCLUDED_PACKAGES,
    OUTPUT_FILENAME_WINDOWS,
    PRODUCT_NAME,
    PRODUCT_VERSION,
)


def build_argparse() -> argparse.ArgumentParser:
    """Construct the CLI argument parser."""
    description = (
        "Windows build driver for the Nuitka transition. "
        "Requires MSVC build tools on the host (or use the "
        "Dockerfile.windows.build.nuitka image). "
        "See plans/QT6_AND_MODERN_PYTHON_MIGRATION_PLAN.md Phase 5."
    )
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--onefile",
        action="store_true",
        help="Produce a onefile .exe (default for shipping builds).",
    )
    parser.add_argument(
        "--standalone",
        action="store_true",
        help="Produce a standalone folder instead of onefile.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove the output directory before building.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("build/nuitka-windows"),
        help="Output directory (default: build/nuitka-windows).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the command that would be run, but don't run it.",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("build/nuitka-cache-windows"),
        help="Nuitka cache directory.",
    )
    parser.add_argument(
        "--windows-icon",
        type=Path,
        default=None,
        help="Path to .ico file for the Windows binary.",
    )
    return parser


def build_command(args: argparse.Namespace) -> list[str]:
    """Construct the python -m nuitka invocation from the config + args."""
    # Default to onefile (plan decision N1).
    is_onefile = args.onefile or (
        not args.standalone and DEFAULT_FLAVOR_WINDOWS == "onefile"
    )

    cmd: list[str] = [
        sys.executable,
        "-m",
        "nuitka",
        f"--output-filename={OUTPUT_FILENAME_WINDOWS}",
        "--output-dir=" + str(args.output.parent),
        "--company-name=" + COMPANY_NAME,
        "--product-name=" + PRODUCT_NAME,
        "--file-version=" + FILE_VERSION,
        "--product-version=" + PRODUCT_VERSION,
        "--windows-disable-console",  # plan keeps console off by default
    ]

    if is_onefile:
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

    if args.windows_icon is not None:
        cmd.append(f"--windows-icon={args.windows_icon}")

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

    print(
        "WARNING: Windows builds require MSVC. Run inside the "
        "Dockerfile.windows.build.nuitka container for production use."
    )
    result = subprocess.run(cmd, cwd=Path.cwd())
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
