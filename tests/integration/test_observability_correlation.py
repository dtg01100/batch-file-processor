# tests/integration/test_observability_correlation.py
from unittest.mock import MagicMock

import pytest

import dispatch.observability

pytestmark = pytest.mark.integration


class TestObservabilityCorrelation:
    def test_correlation_id_propagates_through_processing(self, tmp_path):
        alert_queue = dispatch.observability.AlertQueue(
            queue_path=str(tmp_path / "alert_queue.jsonl")
        )
        audit_logger = dispatch.observability.AuditLogger()

        alert_service = MagicMock()
        dispatch.observability.AlertDispatcher(alert_service, alert_queue, {})

        correlation_id = "test-corr-123"
        folder_id = 1
        file_name = "test.edi"

        audit_logger.log_step(
            correlation_id=correlation_id,
            folder_id=folder_id,
            file_name=file_name,
            step="validation",
            status="success",
            duration_ms=100,
        )
        audit_logger.log_step(
            correlation_id=correlation_id,
            folder_id=folder_id,
            file_name=file_name,
            step="convert",
            status="success",
            duration_ms=200,
        )

        events = audit_logger.drain()

        assert len(events) == 2
        assert events[0].correlation_id == correlation_id
        assert events[1].correlation_id == correlation_id
        assert events[0].event_type == "validation"
        assert events[1].event_type == "convert"

    def test_alert_enqueued_when_smtp_fails(self, tmp_path):
        alert_queue = dispatch.observability.AlertQueue(
            queue_path=str(tmp_path / "alert_queue.jsonl")
        )
        error_record = {
            "error_type": "ValidationError",
            "error_message": "Invalid UPC",
        }

        alert_queue.enqueue(error_record)

        dequeued = alert_queue.dequeue()
        assert dequeued is not None
        assert dequeued["error_type"] == "ValidationError"
        assert dequeued["retry_count"] == 0

    def test_audit_event_to_dict(self):
        event = dispatch.observability.AuditEvent(
            correlation_id="corr-abc",
            folder_id=1,
            file_name="test.edi",
            event_type="validation",
            event_status="failure",
            error_type="ValueError",
            error_message="bad input",
            duration_ms=50,
        )

        d = event.to_dict()
        assert d["correlation_id"] == "corr-abc"
        assert d["folder_id"] == 1
        assert d["event_type"] == "validation"
        assert d["event_status"] == "failure"
        assert d["error_type"] == "ValueError"
        assert d["duration_ms"] == 50
