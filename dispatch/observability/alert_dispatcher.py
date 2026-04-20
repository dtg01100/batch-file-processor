# dispatch/observability/alert_dispatcher.py
from __future__ import annotations

from typing import Any

from dispatch.observability.alert_queue import AlertQueue


class AlertDispatcher:
    def __init__(
        self,
        alert_service: Any,
        alert_queue: AlertQueue,
        settings: dict,
    ) -> None:
        self._alert_service = alert_service
        self._queue = alert_queue
        self._settings = settings

    def dispatch_error_alert(
        self,
        error_record: dict,
        correlation_id: str,
        folder_alias: str,
        file_path: str,
        processing_context: dict,
    ) -> None:
        try:
            self._alert_service.send_alert(
                error_record=error_record,
                correlation_id=correlation_id,
                folder_alias=folder_alias,
                file_path=file_path,
                processing_context=processing_context,
            )
        except Exception as e:
            error_record_copy = dict(error_record)
            error_record_copy["alert_error"] = str(e)
            error_record_copy["alert_retry_count"] = error_record_copy.get(
                "alert_retry_count", 0
            ) + 1
            self._queue.enqueue(error_record_copy)