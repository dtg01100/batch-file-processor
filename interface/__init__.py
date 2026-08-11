# Interface package
"""Interface package for Batch File Sender application.

This package contains the Qt-free business-logic layer that the webapp
reuses: database operations, folder management, and data models. The
former Qt UI layer (``interface/qt``) was removed in the webapp pivot.

Key components:
- FolderManager: Folder management operations (interface.operations.folder_manager)
- DatabaseObj: Database operations (backend.database.database_obj)
"""

__all__: list[str] = []
