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

import os
import sys

# Ensure the project root is in sys.path so we can import 'interface' package
# when running as a script without installation
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

from interface.qt.app import QtBatchFileSenderApp


def main() -> None:
    """Main entry point for the Batch File Sender application."""
    from core.constants import CURRENT_DATABASE_VERSION

    app = QtBatchFileSenderApp(
        appname="Batch File Sender",
        version="(Git Branch: Master)",
        database_version=CURRENT_DATABASE_VERSION,
    )
    app.initialize()
    try:
        sys.exit(app.run())
    finally:
        app.shutdown()


if __name__ == "__main__":
    main()
