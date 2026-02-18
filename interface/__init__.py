# Interface package
"""Interface package for Batch File Sender application.

This package contains the main application class, UI components,
database operations, and business logic for the batch file processor.

Key components:
- QtBatchFileSenderApp: Main application class (interface.qt.app)
- DatabaseObj: Database operations (interface.database.database_obj)
- FolderManager: Folder management operations (interface.operations.folder_manager)
- Dialogs: UI dialogs (interface.qt.dialogs)
"""

from interface.qt.app import QtBatchFileSenderApp

__all__ = ["QtBatchFileSenderApp"]
