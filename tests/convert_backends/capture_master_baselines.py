#!/usr/bin/env python3
"""
Capture Master Baselines Script.

This script captures all outputs from the git master branch version
and stores them as official baselines in tests/convert_backends/baselines/.

Usage:
    # Capture baselines from master for non-DB plugins (default)
    python tests/convert_backends/capture_master_baselines.py

    # Capture baselines for specific plugins
    python tests/convert_backends/capture_master_baselines.py --plugins csv scannerware

    # Capture baselines for all plugins (including DB-dependent)
    python tests/convert_backends/capture_master_baselines.py --all-plugins

    # Dry run (show what would be captured without making changes)
    python tests/convert_backends/capture_master_baselines.py --dry-run
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.convert_backends.baseline_manager import BaselineManager, GitBaselineCapture


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Capture baselines from git master branch",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Capture non-DB plugin baselines from master
  %(prog)s --plugins csv scannerware # Capture specific plugins
  %(prog)s --all-plugins             # Capture all plugins (including DB-dependent)
  %(prog)s --dry-run                 # Show what would be captured
        """,
    )

    parser.add_argument(
        "--plugins",
        nargs="+",
        choices=list(BaselineManager.PLUGINS.keys()),
        help="Specific plugins to capture (default: non-DB plugins)",
    )

    parser.add_argument(
        "--all-plugins",
        action="store_true",
        help="Capture all plugins including DB-dependent ones",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be captured without making changes",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    # Determine which plugins to capture
    if args.all_plugins:
        plugins = list(BaselineManager.PLUGINS.keys())
    elif args.plugins:
        plugins = args.plugins
    else:
        plugins = BaselineManager.NON_DB_PLUGINS

    print("=" * 80)
    print("CAPTURE MASTER BASELINES")
    print("=" * 80)
    print()
    print(f"Plugins to capture: {', '.join(plugins)}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print()

    if args.dry_run:
        # In dry run mode, just show what would be captured
        manager = BaselineManager()

        print("Would capture the following combinations:")
        print("-" * 40)

        total_baselines = 0
        for plugin_id in plugins:
            if plugin_id not in manager.SETTINGS_COMBINATIONS:
                print(f"\n{plugin_id}: No settings combinations defined")
                continue

            combinations = manager.SETTINGS_COMBINATIONS[plugin_id]
            edi_files = manager.TEST_EDI_FILES

            print(f"\n{plugin_id}:")
            print(f"  Settings combinations: {len(combinations)}")
            print(f"  EDI files: {len(edi_files)}")
            print(f"  Total baselines: {len(combinations) * len(edi_files)}")

            for combo in combinations:
                settings_hash = manager._compute_settings_hash(combo.parameters)
                for edi_file in edi_files:
                    baseline_path = manager._get_baseline_path(
                        plugin_id, edi_file, settings_hash
                    )
                    print(f"    - {edi_file} ({combo.name}) -> {baseline_path.name}")
                    total_baselines += 1

        print()
        print(f"Total baselines to capture: {total_baselines}")
        print()
        print("Dry run complete. No changes made.")
        return 0

    # Live capture mode
    git_capture = GitBaselineCapture(project_root=str(project_root))

    # Verify we're in a git repository
    try:
        current_branch = git_capture.get_current_branch()
        print(f"Current branch: {current_branch}")
    except Exception as e:
        print(f"Error: Not in a git repository or git not available: {e}")
        return 1

    print()
    print("Starting baseline capture from master branch...")
    print("-" * 40)

    try:
        results = git_capture.capture_from_master(plugins=plugins)

        print()
        print("=" * 80)
        print("CAPTURE COMPLETE")
        print("=" * 80)
        print()

        total_captured = sum(len(paths) for paths in results.values())

        for plugin_id, paths in results.items():
            print(f"{plugin_id}: {len(paths)} baselines captured")
            if args.verbose:
                for path in paths:
                    print(f"  - {path}")

        print()
        print(f"Total baselines captured: {total_captured}")
        print()
        print(f"Baselines stored in: {git_capture.baseline_manager.baselines_dir}")

        return 0

    except Exception as e:
        print()
        print("=" * 80)
        print("ERROR DURING CAPTURE")
        print("=" * 80)
        print()
        print(f"Error: {e}")
        print()
        print("Note: Your repository should be returned to the original branch.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
