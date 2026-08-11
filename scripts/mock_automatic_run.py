#!/usr/bin/env python3
"""Run an automatic processing pass with mocked config, files, and database.

This script creates a temporary end-to-end environment and executes the
webapp's Qt-free runner (``webapp.runner``) with:

- temporary base directory (``config/`` + ``input/`` + ``logs/``)
- temporary SQLite database
- temporary input/log directories and sample files
- real dispatch processing with the copy backend (no FTP/email)

It is useful for smoke-testing the automatic flow without the browser UI
or external systems. The Qt desktop app it used to drive was removed in
the webapp pivot.
"""

from __future__ import annotations

import argparse
import contextlib
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

# Ensure project root is importable when run as a standalone script.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from webapp.config import Settings
from webapp.database import open_database
from webapp.runner import run_folders


@dataclass(frozen=True)
class MockRunResult:
    """Result details for a mocked automatic run."""

    exit_code: int
    base_dir: Path
    database_path: Path
    input_dir: Path
    logs_dir: Path
    total_processed: int
    total_failed: int


def run_mock_automatic(base_dir: str) -> MockRunResult:
    """Execute one automatic run inside ``base_dir`` (no backends configured)."""
    root = Path(base_dir)
    config_dir = root / "config"
    input_dir = root / "input"
    logs_dir = root / "logs"
    output_dir = root / "output"
    config_dir.mkdir(parents=True, exist_ok=True)
    input_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    (input_dir / "sample_001.edi").write_text("MOCK EDI CONTENT\n", encoding="utf-8")
    (input_dir / "sample_002.txt").write_text("MOCK TXT CONTENT\n", encoding="utf-8")

    settings = Settings(base_dir=root, data_dir=config_dir)
    db = open_database(settings)

    oversight = db.get_oversight_or_default()
    oversight["logs_directory"] = str(logs_dir)
    oversight["enable_reporting"] = False
    db.oversight_and_defaults.update(oversight, ["id"])

    settings_dict = db.get_settings_or_default()
    settings_dict["enable_interval_backups"] = False
    db.settings.update(settings_dict, ["id"])

    folder = {
        "folder_name": str(input_dir),
        "folder_is_active": "True",
        "alias": "mock-inbox",
        "process_backend_email": False,
        "process_backend_ftp": False,
        "process_backend_copy": True,
        "copy_to_directory": str(output_dir),
    }
    db.folders_table.insert(folder)
    with contextlib.suppress(Exception):
        db.close()

    report = run_folders(settings)
    exit_code = 0 if report.status == "completed" and report.total_failed == 0 else 1
    return MockRunResult(
        exit_code=exit_code,
        base_dir=root,
        database_path=settings.database_path,
        input_dir=input_dir,
        logs_dir=logs_dir,
        total_processed=report.total_processed,
        total_failed=report.total_failed,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a mocked automatic processing smoke test (webapp runner)",
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        help="Keep temporary artifacts and print their path",
    )
    parser.add_argument(
        "--base-dir",
        default="",
        help="Optional base directory to use instead of a temporary folder",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    temp_dir = None
    if args.base_dir:
        base_dir = Path(args.base_dir).resolve()
        base_dir.mkdir(parents=True, exist_ok=True)
        result = run_mock_automatic(str(base_dir))
    else:
        temp_dir = tempfile.mkdtemp(prefix="batch_mock_auto_")
        result = run_mock_automatic(temp_dir)

    print("Mock automatic run complete")
    print(f"Exit code    : {result.exit_code}")
    print(f"Base dir     : {result.base_dir}")
    print(f"Database     : {result.database_path}")
    print(f"Input dir    : {result.input_dir}")
    print(f"Logs dir     : {result.logs_dir}")
    print(f"Processed    : {result.total_processed}")
    print(f"Failed       : {result.total_failed}")

    if args.keep and temp_dir:
        retained_dir = Path(tempfile.mkdtemp(prefix="batch_mock_auto_kept_"))
        for child in Path(temp_dir).iterdir():
            target = retained_dir / child.name
            if child.is_dir():
                shutil.copytree(child, target)
            else:
                target.write_bytes(child.read_bytes())
        print(f"Artifacts kept at: {retained_dir}")

    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
