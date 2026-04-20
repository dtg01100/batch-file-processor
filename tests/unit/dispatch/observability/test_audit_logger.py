# tests/unit/dispatch/observability/test_audit_logger.py
import queue as queue_lib

import pytest


class TestAuditLogger:
    def test_log_event_non_blocking(self):
        from dispatch.observability.audit_logger import AuditEvent, AuditLogger

        logger = AuditLogger()
        event = AuditEvent(
            correlation_id="abc",
            folder_id=1,
            file_name="test.edi",
            event_type="validation",
            event_status="success",
        )
        logger.log_event(event)
        assert not logger._queue.empty()

    def test_log_step_creates_event(self):
        from dispatch.observability.audit_logger import AuditEvent, AuditLogger

        logger = AuditLogger()
        logger.log_step(
            correlation_id="xyz",
            folder_id=2,
            file_name="foo.edi",
            step="convert",
            status="success",
            duration_ms=150,
        )
        evt = logger._queue.get_nowait()
        assert evt.correlation_id == "xyz"
        assert evt.event_type == "convert"
        assert evt.duration_ms == 150

    def test_log_step_with_error(self):
        from dispatch.observability.audit_logger import AuditEvent, AuditLogger

        logger = AuditLogger()
        err = ValueError("bad input")
        logger.log_step(
            correlation_id="err1",
            folder_id=1,
            file_name="bad.edi",
            step="validation",
            status="failure",
            error=err,
        )
        evt = logger._queue.get_nowait()
        assert evt.event_status == "failure"
        assert evt.error_type == "ValueError"
        assert evt.error_message == "bad input"

    def test_get_queue_returns_queue(self):
        from dispatch.observability.audit_logger import AuditLogger

        logger = AuditLogger()
        assert logger.get_queue() is logger._queue

    def test_audit_event_has_timestamp(self):
        from dispatch.observability.audit_logger import AuditEvent

        event = AuditEvent(
            correlation_id="abc",
            folder_id=1,
            file_name="test.edi",
            event_type="validation",
            event_status="success",
        )
        assert event.timestamp is not None
        assert "T" in event.timestamp  # ISO format

    def test_audit_event_to_dict(self):
        from dispatch.observability.audit_logger import AuditEvent

        event = AuditEvent(
            correlation_id="abc",
            folder_id=1,
            file_name="test.edi",
            event_type="validation",
            event_status="success",
        )
        d = event.to_dict()
        assert d["correlation_id"] == "abc"
        assert d["event_type"] == "validation"
        assert d["event_status"] == "success"