# tests/unit/dispatch/observability/test_alert_dispatcher.py
from unittest.mock import MagicMock

import pytest

from dispatch.observability.alert_dispatcher import AlertDispatcher
from dispatch.observability.alert_queue import AlertQueue


class TestAlertDispatcher:
    def test_dispatch_success_calls_send_alert(self, tmp_path):
        service = MagicMock()
        queue = AlertQueue(queue_path=str(tmp_path / "queue.jsonl"))
        dispatcher = AlertDispatcher(service, queue, {})
        dispatcher.dispatch_error_alert(
            error_record={"error_type": "Err", "error_message": "bad"},
            correlation_id="corr1",
            folder_alias="Folder",
            file_path="/path/file.edi",
            processing_context={},
        )
        service.send_alert.assert_called_once()
        queue.dequeue()  # should not have enqueued
        assert queue.peek() == []

    def test_dispatch_smtp_failure_enqueues(self, tmp_path):
        service = MagicMock()
        service.send_alert.side_effect = ConnectionRefusedError("SMTP down")
        queue = AlertQueue(queue_path=str(tmp_path / "queue.jsonl"))
        dispatcher = AlertDispatcher(service, queue, {})
        dispatcher.dispatch_error_alert(
            error_record={"error_type": "Err", "error_message": "bad"},
            correlation_id="corr1",
            folder_alias="Folder",
            file_path="/path/file.edi",
            processing_context={},
        )
        enqueued = queue.dequeue()
        assert enqueued is not None
        assert enqueued["alert_error"] == "SMTP down"
        assert enqueued["alert_retry_count"] == 1

    def test_dispatch_never_raises(self, tmp_path):
        service = MagicMock()
        service.send_alert.side_effect = RuntimeError("Unexpected")
        queue = AlertQueue(queue_path=str(tmp_path / "queue.jsonl"))
        dispatcher = AlertDispatcher(service, queue, {})
        dispatcher.dispatch_error_alert(
            error_record={"error_type": "Err"},
            correlation_id="x",
            folder_alias="F",
            file_path="/p.edi",
            processing_context={},
        )

    def test_dispatch_preserves_original_error_record(self, tmp_path):
        service = MagicMock()
        service.send_alert.side_effect = ConnectionError("SMTP down")
        queue = AlertQueue(queue_path=str(tmp_path / "queue.jsonl"))
        dispatcher = AlertDispatcher(service, queue, {})
        original = {"error_type": "TestError", "error_message": "original"}
        dispatcher.dispatch_error_alert(
            error_record=original,
            correlation_id="corr1",
            folder_alias="Folder",
            file_path="/path/file.edi",
            processing_context={},
        )
        enqueued = queue.dequeue()
        assert enqueued["error_type"] == "TestError"
        assert enqueued["error_message"] == "original"