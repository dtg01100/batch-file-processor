"""Batch File Sender - Qt Entry Point.

This module serves as the Qt-based entry point for the Batch File Sender application.
It creates and runs the QtBatchFileSenderApp instance.
"""

import sys
from interface.qt.app import QtBatchFileSenderApp


def main():
    """Initialize and run the Batch File Sender application with Qt UI."""
    app = QtBatchFileSenderApp(
        appname="Batch File Sender",
        version="(Git Branch: Master)",
        database_version="33",
    )
    app.initialize()
    try:
        sys.exit(app.run())
    finally:
        app.shutdown()


if __name__ == "__main__":
    main()
