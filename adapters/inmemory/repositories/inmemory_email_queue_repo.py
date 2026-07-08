"""
In-memory email-queue repository.

Pure-Python implementation of :class:`IEmailQueueRepository` for tests
and ephemeral contexts. Each enqueued email is auto-assigned a
monotonic id; size estimation uses the byte length of the 'body'
field (defaulting to 0 when absent).
"""

import json
from typing import Any

from core.ports.repositories import IEmailQueueRepository


def _email_size(email: dict[str, Any]) -> int:
    body = email.get("body")
    if isinstance(body, (bytes, bytearray)):
        return len(body)
    if isinstance(body, str):
        return len(body.encode("utf-8"))
    # Fall back to JSON-serialised size for non-string payloads.
    try:
        return len(json.dumps(body, default=str).encode("utf-8"))
    except (TypeError, ValueError):
        return 0


class InMemoryEmailQueueRepository(IEmailQueueRepository):
    """Email-queue repository backed by an in-process list."""

    def __init__(self) -> None:
        self._queue: dict[int, dict[str, Any]] = {}
        self._next_id: int = 1

    def _next_pk(self) -> int:
        pk = self._next_id
        self._next_id += 1
        return pk

    # ------------------------------------------------------------------
    # IEmailQueueRepository
    # ------------------------------------------------------------------

    def enqueue(self, email_data: dict[str, Any]) -> None:
        pk = self._next_pk()
        record = {**email_data, "id": pk}
        self._queue[pk] = record

    def dequeue_batch(self, max_size: int, max_count: int) -> list[dict[str, Any]]:
        batch: list[dict[str, Any]] = []
        total_size = 0
        for record in list(self._queue.values()):
            if len(batch) >= max_count:
                break
            size = _email_size(record)
            if total_size + size > max_size and batch:
                break
            batch.append(record)
            total_size += size
        return batch

    def mark_sent(self, email_ids: list[int]) -> None:
        for eid in email_ids:
            self._queue.pop(eid, None)

    def clear_queue(self) -> int:
        count = len(self._queue)
        self._queue.clear()
        return count
