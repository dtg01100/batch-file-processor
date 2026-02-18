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
"""

import sys
import multiprocessing

from interface.qt.app import QtBatchFileSenderApp


def main() -> None:
    """Main entry point for the Batch File Sender application."""
    app = QtBatchFileSenderApp(
        appname="Batch File Sender",
        version="(Git Branch: Master)",
        database_version="33"
    )
    app.initialize()
    try:
        sys.exit(app.run())
    finally:
        app.shutdown()


if __name__ == "__main__":
    main()
