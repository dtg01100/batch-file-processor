"""
Repository interfaces (ports) for data access abstraction.

These interfaces define the contract for data access, allowing
different implementations (SQLite, in-memory, async, etc.) to be
substituted without changing business logic.

All concrete implementations live under adapters/.
"""

from abc import ABC, abstractmethod
from typing import Any


class IFolderRepository(ABC):
    """Abstract interface for folder configuration data access."""

    @abstractmethod
    def find_all(self, *, active_only: bool = False) -> list[dict[str, Any]]:
        """Get all folders, optionally filtered to active only.

        Args:
            active_only: If True, return only folders where folder_is_active is True.

        Returns:
            List of folder dicts.

        """
        ...

    @abstractmethod
    def find_by_id(self, folder_id: int) -> dict[str, Any] | None:
        """Get a folder by its ID.

        Args:
            folder_id: Primary key of the folder record.

        Returns:
            Folder dict, or None if not found.

        """
        ...

    @abstractmethod
    def find_by_path(self, path: str) -> dict[str, Any] | None:
        """Get a folder by its filesystem path (folder_name column).

        Args:
            path: Filesystem path to look up.

        Returns:
            Folder dict, or None if not found.

        """
        ...

    @abstractmethod
    def find_by_alias(self, alias: str) -> dict[str, Any] | None:
        """Get a folder by its alias.

        Args:
            alias: Display name / alias to look up.

        Returns:
            Folder dict, or None if not found.

        """
        ...

    @abstractmethod
    def insert(self, folder_data: dict[str, Any]) -> None:
        """Insert a new folder record.

        Args:
            folder_data: Dict of column values. Must not include 'id'.

        """
        ...

    @abstractmethod
    def update(self, folder_data: dict[str, Any]) -> None:
        """Update an existing folder record.

        Args:
            folder_data: Dict of column values. Must include 'id'.

        """
        ...

    @abstractmethod
    def delete(self, folder_id: int) -> None:
        """Delete a folder record by ID.

        Args:
            folder_id: Primary key of the folder to delete.

        """
        ...

    @abstractmethod
    def count(self, *, active_only: bool = False) -> int:
        """Count folder records.

        Args:
            active_only: If True, count only active folders.

        Returns:
            Integer count.

        """
        ...


class ISettingsRepository(ABC):
    """Abstract interface for application settings access.

    Settings are stored in the 'administrative' table as a singleton
    row (id=1) and also as key/value pairs in the 'settings' table.
    """

    @abstractmethod
    def get_defaults(self) -> dict[str, Any]:
        """Get the oversight/defaults singleton record (id=1 in administrative table).

        Returns:
            Dict with all defaults fields.  Never returns None — creates a
            default record if missing.

        """
        ...

    @abstractmethod
    def update_defaults(self, settings: dict[str, Any]) -> None:
        """Update the oversight/defaults singleton record.

        Args:
            settings: Dict of fields to update.  'id' will be forced to 1.

        """
        ...

    @abstractmethod
    def get_setting(self, key: str) -> Any | None:
        """Get a named setting value from the key/value settings table.

        Args:
            key: Setting key.

        Returns:
            Setting value or None if not found.

        """
        ...

    @abstractmethod
    def set_setting(self, key: str, value: Any) -> None:
        """Upsert a named setting value into the key/value settings table.

        Args:
            key: Setting key.
            value: Setting value.

        """
        ...


class IProcessedFilesRepository(ABC):
    """Abstract interface for processed-files tracking."""

    @abstractmethod
    def is_processed(self, file_hash: str) -> bool:
        """Check if a file hash has already been processed.

        Args:
            file_hash: Hash string identifying the file.

        Returns:
            True if the hash exists in the processed files table.

        """
        ...

    @abstractmethod
    def mark_processed(self, file_hash: str, folder_id: int, filename: str) -> None:
        """Record that a file has been processed.

        Args:
            file_hash: Hash string identifying the file.
            folder_id: ID of the folder the file belongs to.
            filename: Original filename (for display/audit).

        """
        ...

    @abstractmethod
    def clear_all(self) -> int:
        """Delete all processed-file records.

        Returns:
            Number of records deleted.

        """
        ...

    @abstractmethod
    def clear_for_folder(self, folder_id: int) -> int:
        """Delete all processed-file records for a specific folder.

        Args:
            folder_id: ID of the folder whose records should be cleared.

        Returns:
            Number of records deleted.

        """
        ...

    @abstractmethod
    def find_by_hash(self, file_hash: str) -> dict[str, Any] | None:
        """Find a processed-file record by its hash.

        Args:
            file_hash: Hash string to look up.

        Returns:
            Record dict, or None if not found.

        """
        ...


class IEmailQueueRepository(ABC):
    """Abstract interface for outbound email queue management."""

    @abstractmethod
    def enqueue(self, email_data: dict[str, Any]) -> None:
        """Add an email to the outbound queue.

        Args:
            email_data: Dict of email fields (to, subject, body, folder_id, …).

        """
        ...

    @abstractmethod
    def dequeue_batch(self, max_size: int, max_count: int) -> list[dict[str, Any]]:
        """Return a batch of emails ready to send.

        Args:
            max_size: Maximum total byte size of the batch.
            max_count: Maximum number of emails in the batch.

        Returns:
            List of email dicts.

        """
        ...

    @abstractmethod
    def mark_sent(self, email_ids: list[int]) -> None:
        """Mark emails as successfully sent.

        Args:
            email_ids: List of email primary keys to mark.

        """
        ...

    @abstractmethod
    def clear_queue(self) -> int:
        """Delete all queued (unsent) emails.

        Returns:
            Number of records deleted.

        """
        ...
