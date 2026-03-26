"""
SQLite email queue repository implementation.

Wraps the DatabaseObj / Table API to implement IEmailQueueRepository.
"""

import os
from typing import Any

from core.ports.repositories import IEmailQueueRepository


class SqliteEmailQueueRepository(IEmailQueueRepository):
    """Email queue repository backed by DatabaseObj.

    Args:
        database_obj: A ``DatabaseObj`` instance (or compatible mock).

    """

    def __init__(self, database_obj: Any) -> None:
        self._db = database_obj

    # ------------------------------------------------------------------
    # IEmailQueueRepository implementation
    # ------------------------------------------------------------------

    def enqueue(self, email_data: dict[str, Any]) -> None:
        """Add an email to the outbound queue.

        Args:
            email_data: Dict of email fields (folder_alias, log, folder_id).

        """
        self._db.emails_table.insert(email_data)

    def dequeue_batch(self, max_size: int, max_count: int) -> list[dict[str, Any]]:
        """Return a batch of emails ready to send.

        Args:
            max_size: Maximum total byte size of the batch.
            max_count: Maximum number of emails in the batch.

        Returns:
            List of email dicts.

        """
        all_emails = self._db.emails_table.all()
        batch = []
        total_size = 0

        for email in all_emails:
            if len(batch) >= max_count:
                break

            email_size = self._get_email_size(email)
            if total_size + email_size > max_size:
                break

            batch.append(email)
            total_size += email_size

        return batch

    def _get_email_size(self, email: dict[str, Any]) -> int:
        """Get the byte size of an email's log file.

        Args:
            email: Email dict containing 'log' field.

        Returns:
            Size in bytes, or 0 if file doesn't exist.

        """
        log_path = email.get("log")
        if log_path and os.path.isfile(log_path):
            return os.path.getsize(log_path)
        return 0

    def mark_sent(self, email_ids: list[int]) -> None:
        """Mark emails as successfully sent.

        Moves emails from emails_to_send to sent_emails_removal_queue.

        Args:
            email_ids: List of email primary keys to mark.

        """
        for email_id in email_ids:
            email = self._db.emails_table.find_one(id=email_id)
            if email is None:
                continue

            record = {
                "folder_alias": email["folder_alias"],
                "log": email["log"],
                "folder_id": email["folder_id"],
                "old_id": email_id,
            }
            self._db.sent_emails_removal_queue.insert(record)
            self._db.emails_table.delete(id=email_id)

    def clear_queue(self) -> int:
        """Delete all queued (unsent) emails.

        Returns:
            Number of records deleted.

        """
        count = self._db.emails_table.count()
        self._db.emails_table.delete()
        return count
