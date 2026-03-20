#!/usr/bin/env python3
"""Run automatic processing with mocked config, files, and database.

This script creates a temporary end-to-end environment and executes the
application's ``--automatic`` path with:

- temporary configuration folder
- temporary SQLite database
- temporary input/log directories and sample files
- mocked dispatch processing (no real backend calls)

It is useful for smoke-testing the automatic flow without requiring real
production configuration or external systems.
"""

from __future__ import annotations

import argparse
import os
import platform
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

# Ensure project root is importable when run as a standalone script.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database.database_obj import DatabaseObj
from core.constants import CURRENT_DATABASE_VERSION
from dispatch.orchestrator import FolderResult
from interface.operations.folder_manager import FolderManager
from interface.qt.app import QtBatchFileSenderApp


@dataclass(frozen=True)
class MockRunResult:
    """Result details for a mocked automatic run."""

    exit_code: int
    base_dir: Path
    config_dir: Path
    database_path: Path
    input_dir: Path
    logs_dir: Path
    run_log_files: list[Path]


def _mock_orchestrator_process_folder(*args, **kwargs):
    """Mock replacement for DispatchOrchestrator.process_folder used by harness."""
    # Bound-method patch can pass (self, folder, run_log, processed_files)
    # or (folder, run_log, processed_files) depending on call path.
    if len(args) >= 3 and hasattr(args[0], "config"):
        folder = args[1]
        run_log = args[2]
    else:
        folder = args[0]
        run_log = args[1]

    alias = folder.get("alias", folder.get("folder_name", "unknown"))
    run_log.write(
        f"[MOCK] DispatchOrchestrator.process_folder called for {alias}\n".encode()
    )
    run_log.write(b"[MOCK] no real conversions or backends were executed\n")

    return FolderResult(
        folder_name=folder.get("folder_name", ""),
        alias=folder.get("alias", ""),
        files_processed=1,
        files_failed=0,
        success=True,
    )


def run_mock_automatic(base_dir: str | os.PathLike[str]) -> MockRunResult:
    """Execute one mocked automatic run inside ``base_dir``."""
    root = Path(base_dir)
    config_dir = root / "config"
    input_dir = root / "input"
    logs_dir = root / "logs"
    config_dir.mkdir(parents=True, exist_ok=True)
    input_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    (input_dir / "sample_001.edi").write_text("MOCK EDI CONTENT\n", encoding="utf-8")
    (input_dir / "sample_002.txt").write_text("MOCK TXT CONTENT\n", encoding="utf-8")

    database_path = config_dir / "folders.db"
    db = DatabaseObj(
        database_path=str(database_path),
        database_version=CURRENT_DATABASE_VERSION,
        config_folder=str(config_dir),
        running_platform=platform.system(),
    )

    oversight = db.get_oversight_or_default()
    oversight["logs_directory"] = str(logs_dir)
    oversight["enable_reporting"] = False
    db.oversight_and_defaults.update(oversight, ["id"])

    settings = db.get_settings_or_default()
    settings["enable_interval_backups"] = False
    settings["backup_counter"] = 0
    settings["backup_counter_maximum"] = 100
    db.settings.update(settings, ["id"])

    folder_manager = FolderManager(db)
    folder_manager.add_folder(str(input_dir))
    folder = db.folders_table.find_one(folder_name=str(input_dir))
    if folder is None:
        raise RuntimeError("Failed to create mock folder entry")

    folder["folder_is_active"] = "True"
    folder["process_backend_email"] = False
    folder["process_backend_ftp"] = False
    folder["process_backend_copy"] = False
    db.folders_table.update(folder, ["id"])

    app = QtBatchFileSenderApp(
        appname="Batch File Sender",
        version="(Mock Automatic Run)",
        database_version=CURRENT_DATABASE_VERSION,
        database_obj=db,
    )

    exit_code = 0
    try:
        with patch(
            "interface.qt.app.appdirs.user_data_dir", return_value=str(config_dir)
        ):
            with patch(
                "dispatch.orchestrator.DispatchOrchestrator.process_folder",
                side_effect=_mock_orchestrator_process_folder,
            ):
                app.initialize(args=["--automatic"])
                app.run()
    except SystemExit as system_exit:
        if isinstance(system_exit.code, int):
            exit_code = system_exit.code

    run_log_files = sorted(logs_dir.glob("Run Log *.txt"))

    return MockRunResult(
        exit_code=exit_code,
        base_dir=root,
        config_dir=config_dir,
        database_path=database_path,
        input_dir=input_dir,
        logs_dir=logs_dir,
        run_log_files=run_log_files,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a mocked automatic processing smoke test",
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

    if args.base_dir:
        base_dir = Path(args.base_dir).resolve()
        base_dir.mkdir(parents=True, exist_ok=True)
        result = run_mock_automatic(base_dir)
        print("Mock automatic run complete")
        print(f"Exit code    : {result.exit_code}")
        print(f"Base dir     : {result.base_dir}")
        print(f"Database     : {result.database_path}")
        print(f"Input dir    : {result.input_dir}")
        print(f"Logs dir     : {result.logs_dir}")
        print(f"Run log files: {len(result.run_log_files)}")
        return result.exit_code

    with tempfile.TemporaryDirectory(prefix="batch_mock_auto_") as temp_dir:
        temp_path = Path(temp_dir)
        result = run_mock_automatic(temp_path)
        print("Mock automatic run complete")
        print(f"Exit code    : {result.exit_code}")
        print(f"Base dir     : {result.base_dir}")
        print(f"Database     : {result.database_path}")
        print(f"Input dir    : {result.input_dir}")
        print(f"Logs dir     : {result.logs_dir}")
        print(f"Run log files: {len(result.run_log_files)}")

        if args.keep:
            retained_dir = Path(tempfile.mkdtemp(prefix="batch_mock_auto_kept_"))
            for child in temp_path.iterdir():
                target = retained_dir / child.name
                if child.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    for file_child in child.rglob("*"):
                        rel = file_child.relative_to(child)
                        destination = target / rel
                        if file_child.is_dir():
                            destination.mkdir(parents=True, exist_ok=True)
                        else:
                            destination.parent.mkdir(parents=True, exist_ok=True)
                            destination.write_bytes(file_child.read_bytes())
                else:
                    target.write_bytes(child.read_bytes())
            print(f"Artifacts kept at: {retained_dir}")

        return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
