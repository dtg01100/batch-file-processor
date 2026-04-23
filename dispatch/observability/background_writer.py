# dispatch/observability/background_writer.py
from __future__ import annotations

import logging
import queue as queue_lib
import threading
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from dispatch.observability.audit_logger import AuditEvent

logger = logging.getLogger(__name__)


class AuditBackgroundWriter:
    def __init__(self, audit_queue: queue_lib.Queue[AuditEvent], db: Any) -> None:
        self._queue = audit_queue
        self._db = db
        self._shutdown = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._shutdown.clear()
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="AuditBackgroundWriter"
        )
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._shutdown.set()
        if self._thread:
            self._thread.join(timeout=timeout)

    def _run(self) -> None:
        while not self._shutdown.is_set():
            try:
                event = self._queue.get(timeout=1.0)
            except queue_lib.Empty:
                continue
            try:
                self._db.audit_log_table.insert(event.to_dict())
            except Exception:
                logger.error("Failed to write audit event", exc_info=True)
