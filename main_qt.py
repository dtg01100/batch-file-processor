"""Batch File Sender - Qt Entry Point.

This module serves as the Qt-based entry point for the Batch File Sender application.
It creates and runs the QtBatchFileSenderApp instance.

This script can be run directly without installation:
    python main_qt.py
"""

import sys
import os

# Ensure the project root is in sys.path so we can import 'interface' package
# when running as a script without installation
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

from interface.qt.app import QtBatchFileSenderApp


def main():
    """Initialize and run the Batch File Sender application with Qt UI."""
    from batch_file_processor.constants import CURRENT_DATABASE_VERSION

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
