# Interface package
"""Interface package for Batch File Sender application.

This package contains the main application class, UI components,
database operations, and business logic for the batch file processor.

Key components:
- BatchFileSenderApp: Main application class (interface.app)
- DatabaseObj: Database operations (interface.database.database_obj)
- FolderManager: Folder management operations (interface.operations.folder_manager)
- Dialogs: UI dialogs (interface.ui.dialogs)
"""

from interface.app import BatchFileSenderApp

__all__ = ["BatchFileSenderApp"]
