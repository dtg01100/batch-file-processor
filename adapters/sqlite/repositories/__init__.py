"""
SQLite repository implementations.

These adapters wrap DatabaseObj's Table API to satisfy the repository
interfaces defined in core.ports.repositories.
"""

from .sqlite_email_queue_repo import SqliteEmailQueueRepository  # noqa: F401
from .sqlite_folder_repo import SqliteFolderRepository  # noqa: F401
from .sqlite_processed_files_repo import SqliteProcessedFilesRepository  # noqa: F401
from .sqlite_settings_repo import SqliteSettingsRepository  # noqa: F401
