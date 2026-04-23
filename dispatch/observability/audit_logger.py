# dispatch/observability/audit_logger.py
from __future__ import annotations

import queue as queue_lib
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class AuditEvent:
    correlation_id: str
    folder_id: int
    file_name: str
    event_type: str
    event_status: str
    error_type: str | None = None
    error_message: str | None = None
    input_path: str | None = None
    output_path: str | None = None
    duration_ms: int | None = None
    timestamp: str | None = None
    details: dict | None = None

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        return result


class AuditLogger:
    def __init__(self) -> None:
        self._queue: queue_lib.Queue[AuditEvent] = queue_lib.Queue()

    def log_event(self, event: AuditEvent) -> None:
        self._queue.put(event)

    def log_step(
        self,
        correlation_id: str,
        folder_id: int,
        file_name: str,
        step: str,
        status: str,
        duration_ms: int | None = None,
        error: BaseException | None = None,
        input_path: str | None = None,
        output_path: str | None = None,
        details: dict | None = None,
    ) -> None:
        event = AuditEvent(
            correlation_id=correlation_id,
            folder_id=folder_id,
            file_name=file_name,
            event_type=step,
            event_status=status,
            duration_ms=duration_ms,
            error_type=type(error).__name__ if error else None,
            error_message=str(error) if error else None,
            input_path=input_path,
            output_path=output_path,
            details=details,
        )
        self.log_event(event)

    def drain(self) -> list[AuditEvent]:
        """Drain and return all queued events. Useful for testing."""
        events = []
        while not self._queue.empty():
            events.append(self._queue.get_nowait())
        return events
