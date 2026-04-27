"""
SQLite repository implementations.

These adapters wrap DatabaseObj's Table API to satisfy the repository
interfaces defined in core.ports.repositories.
"""

from .sqlite_email_queue_repo import SqliteEmailQueueRepository
from .sqlite_folder_repo import SqliteFolderRepository
from .sqlite_processed_files_repo import SqliteProcessedFilesRepository
from .sqlite_settings_repo import SqliteSettingsRepository

__all__ = [
    "SqliteEmailQueueRepository",
    "SqliteFolderRepository",
    "SqliteProcessedFilesRepository",
    "SqliteSettingsRepository",
]
