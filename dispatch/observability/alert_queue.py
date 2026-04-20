# dispatch/observability/alert_queue.py
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class AlertQueue:
    def __init__(
        self,
        queue_path: str | Path | None = None,
        failures_path: str | Path | None = None,
    ) -> None:
        if queue_path is None:
            import appdirs

            queue_path = Path(appdirs.user_data_dir()) / "Batch File Sender" / "alert_queue.jsonl"
        self._queue_path = Path(queue_path)
        self._failures_path = Path(failures_path) if failures_path else self._queue_path.parent / "alert_failures.log"
        self._ensure_paths()

    def _ensure_paths(self) -> None:
        self._queue_path.parent.mkdir(parents=True, exist_ok=True)

    def enqueue(self, alert_record: dict[str, Any]) -> None:
        alert_record.setdefault("retry_count", 0)
        line = json.dumps(alert_record) + "\n"
        with open(self._queue_path, "a", encoding="utf-8") as f:
            f.write(line)

    def peek(self) -> list[dict[str, Any]]:
        if not self._queue_path.exists():
            return []
        with open(self._queue_path, "r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    def dequeue(self) -> dict[str, Any] | None:
        alerts = self.peek()
        if not alerts:
            return None
        first = alerts[0]
        with open(self._queue_path, "w", encoding="utf-8") as f:
            f.writelines(json.dumps(a) + "\n" for a in alerts[1:])
        return first

    def mark_failed(self, alert: dict[str, Any], error: str) -> None:
        self._failures_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._failures_path, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()} FAILED: {json.dumps(alert)} error: {error}\n")

    @property
    def queue_path(self) -> Path:
        return self._queue_path

    @property
    def failures_path(self) -> Path:
        return self._failures_path