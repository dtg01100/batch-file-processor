#!/usr/bin/env python3
"""
Entry point for Batch File Sender application.

This module provides a minimal entry point that initializes and runs the
application. All application logic has been refactored into separate modules:

- Application class: interface/qt/app.py
- DatabaseObj: interface/database/database_obj.py
- FolderManager: interface/operations/folder_manager.py
- Email validation: interface/validation/email_validator.py
- UI protocols: interface/interfaces.py
- Dialogs: interface/qt/dialogs/

This script can be run directly without installation:
    python main_interface.py

Or as a module (if installed):
    python -m main_interface
"""

from __future__ import annotations

import importlib
import os
import platform
import sys
import tempfile
import traceback
from pathlib import Path

# Ensure the project root is in sys.path so we can import 'interface' package
# when running as a script without installation
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

_SUPPORT_LOG_NAME = "batch-file-sender-startup-error.log"
_FROZEN_QT_PATHS = (
    Path("_internal") / "PyQt5" / "Qt5" / "bin",
    Path("_internal") / "PyQt5" / "plugins" / "platforms" / "qwindows.dll",
)


def _resolve_bundle_root() -> Path:
    if getattr(sys, "frozen", False):
        # Single-file mode: PyInstaller extracts to sys._MEIPASS at runtime
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent
    return Path(_script_dir)


def _build_startup_error_lines(exc: ImportError | OSError) -> list[str]:
    bundle_root = _resolve_bundle_root()
    lines = [
        "Batch File Sender could not start because the Qt runtime failed to load.",
        f"Error: {exc.__class__.__name__}: {exc}",
        "",
        "What to check:",
        (
            "- Install or repair the Microsoft Visual C++ 2015-2022 "
            "Redistributable (x64) and Windows UCRT."
        ),
        (
            "- This is a single-file executable; if the error persists, "
            "re-download the .exe."
        ),
    ]

    if getattr(sys, "frozen", False):
        lines.extend(
            [
                "- Verify these bundled Qt paths exist next to the executable:",
                *[f"  - {relative_path}" for relative_path in _FROZEN_QT_PATHS],
            ]
        )
        for relative_path in _FROZEN_QT_PATHS:
            resolved_path = bundle_root / relative_path
            lines.append(
                f"    {'OK' if resolved_path.exists() else 'MISSING'}: {resolved_path}"
            )
    else:
        lines.append(
            "- If running from source, confirm PyQt5 is installed and "
            "matches this Python environment."
        )

    lines.extend(
        [
            "",
            f"Executable directory: {bundle_root}",
        ]
    )

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        lines.append(f"PyInstaller extraction dir: {meipass}")

    return lines


def _write_startup_error_log(
    lines: list[str], exc: ImportError | OSError
) -> Path | None:
    candidate_dirs = []
    bundle_root = _resolve_bundle_root()
    if getattr(sys, "frozen", False):
        candidate_dirs.append(bundle_root)
    candidate_dirs.append(Path(tempfile.gettempdir()))

    log_body = "\n".join(
        [
            *lines,
            "",
            f"Platform: {platform.platform()}",
            f"Python: {sys.version}",
            "",
            "Traceback:",
            "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
        ]
    )

    for directory in candidate_dirs:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            log_path = directory / _SUPPORT_LOG_NAME
            log_path.write_text(log_body, encoding="utf-8")
            return log_path
        except OSError:
            continue

    return None


def _emit_startup_import_error(exc: ImportError | OSError) -> None:
    lines = _build_startup_error_lines(exc)
    log_path = _write_startup_error_log(lines, exc)
    if log_path is not None:
        lines.extend(["", f"Support log: {log_path}"])

    print("\n".join(lines), file=sys.stderr)


def _load_qt_app_class() -> type:
    try:
        module = importlib.import_module("interface.qt.app")
    except (ImportError, OSError) as exc:
        _emit_startup_import_error(exc)
        raise SystemExit(1) from exc
    return module.QtBatchFileSenderApp


def main() -> None:
    """Main entry point for the Batch File Sender application."""
    from core.constants import APP_VERSION

    qt_app_class = _load_qt_app_class()
    app = qt_app_class(
        appname="Batch File Sender",
        version=APP_VERSION,
    )
    app.initialize()
    try:
        sys.exit(app.run())
    finally:
        app.shutdown()


if __name__ == "__main__":
    main()
