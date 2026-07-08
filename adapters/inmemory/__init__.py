"""In-memory adapter implementations.

Pure-Python repositories for tests and ephemeral contexts. Not
thread-safe; not for production use.
"""

from adapters.inmemory.repositories.inmemory_email_queue_repo import (
    InMemoryEmailQueueRepository,
)
from adapters.inmemory.repositories.inmemory_folder_repo import (
    InMemoryFolderRepository,
)
from adapters.inmemory.repositories.inmemory_processed_files_repo import (
    InMemoryProcessedFilesRepository,
)
from adapters.inmemory.repositories.inmemory_settings_repo import (
    InMemorySettingsRepository,
)

__all__ = [
    "InMemoryEmailQueueRepository",
    "InMemoryFolderRepository",
    "InMemoryProcessedFilesRepository",
    "InMemorySettingsRepository",
]
