#!/usr/bin/env python3
"""
Entry point for Batch File Sender application.

This module provides a minimal entry point that initializes and runs the
application. All application logic has been refactored into separate modules:

- Application class: interface/app.py
- DatabaseObj: interface/database/database_obj.py
- FolderManager: interface/operations/folder_manager.py
- Email validation: interface/validation/email_validator.py
- UI protocols: interface/interfaces.py
- Dialogs: interface/ui/dialogs/
"""

import multiprocessing

from interface.app import BatchFileSenderApp


def main() -> None:
    """Main entry point for the Batch File Sender application."""
    multiprocessing.freeze_support()
    app = BatchFileSenderApp(
        appname="Batch File Sender",
        version="(Git Branch: Master)",
        database_version="33"
    )
    app.initialize()
    app.run()
    app.shutdown()


if __name__ == "__main__":
    main()
