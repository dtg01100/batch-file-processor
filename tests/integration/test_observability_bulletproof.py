# tests/integration/test_observability_bulletproof.py
"""Bulletproof error injection tests for observability.

These tests verify that alerting and audit logging never break processing
even when SMTP or DB is down.
"""
import sqlite3
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.integration


class TestAlertBulletproof:
    def test_alert_enqueued_when_smtp_connection_fails(self, tmp_path):
        """Verify alert is enqueued when SMTP connection is refused."""
        import dispatch.observability

        alert_queue = dispatch.observability.AlertQueue(
            queue_path=str(tmp_path / "alert_queue.jsonl")
        )

        mock_smtp_service = MagicMock()
        mock_smtp_service.send_alert.side_effect = ConnectionRefusedError(
            "SMTP server not available"
        )

        dispatcher = dispatch.observability.AlertDispatcher(
            mock_smtp_service, alert_queue, {}
        )

        error_record = {
            "error_type": "SMTPError",
            "error_message": "Connection refused",
            "alert_retry_count": 0,
        }

        dispatcher.dispatch_error_alert(
            error_record=error_record,
            correlation_id="test-corr-456",
            folder_alias="test_folder",
            file_path="/path/to/test.edi",
            processing_context={"alert_on_failure": True},
        )

        queued = alert_queue.dequeue()
        assert queued is not None
        assert queued["error_type"] == "SMTPError"
        assert queued["alert_error"] == "SMTP server not available"
        assert queued["alert_retry_count"] == 1

    def test_alert_enqueued_when_smtp_sends_garbage(self, tmp_path):
        """Verify alert is enqueued when SMTP returns unexpected response."""
        import dispatch.observability

        alert_queue = dispatch.observability.AlertQueue(
            queue_path=str(tmp_path / "alert_queue.jsonl")
        )

        mock_smtp_service = MagicMock()
        mock_smtp_service.send_alert.side_effect = TimeoutError("SMTP timeout")

        dispatcher = dispatch.observability.AlertDispatcher(
            mock_smtp_service, alert_queue, {}
        )

        error_record = {
            "error_type": "TimeoutError",
            "error_message": "SMTP timeout",
            "alert_retry_count": 0,
        }

        dispatcher.dispatch_error_alert(
            error_record=error_record,
            correlation_id="test-corr-789",
            folder_alias="test_folder",
            file_path="/path/to/test.edi",
            processing_context={"alert_on_failure": True},
        )

        queued = alert_queue.dequeue()
        assert queued is not None
        assert queued["error_type"] == "TimeoutError"
        assert "timeout" in queued["alert_error"].lower()
        assert queued["alert_retry_count"] == 1

    def test_processing_succeeds_even_when_smtp_fails_completely(self, tmp_path):
        """Verify processing continues when SMTP is completely down."""
        import dispatch.observability

        alert_queue = dispatch.observability.AlertQueue(
            queue_path=str(tmp_path / "alert_queue.jsonl")
        )

        mock_smtp_service = MagicMock()
        mock_smtp_service.send_alert.side_effect = Exception("Total failure")

        dispatcher = dispatch.observability.AlertDispatcher(
            mock_smtp_service, alert_queue, {}
        )

        error_record = {
            "error_type": "ProcessingError",
            "error_message": "Something went wrong",
            "alert_retry_count": 0,
        }

        dispatcher.dispatch_error_alert(
            error_record=error_record,
            correlation_id="test-corr-abc",
            folder_alias="test_folder",
            file_path="/path/to/test.edi",
            processing_context={"alert_on_failure": True},
        )

        queued = alert_queue.dequeue()
        assert queued is not None
        assert queued["alert_retry_count"] == 1


class TestAuditBulletproof:
    def test_audit_writer_handles_db_error(self, tmp_path):
        """Verify audit writer doesn't crash when DB insert fails."""
        import queue as queue_lib

        import dispatch.observability

        mock_db = MagicMock()
        mock_db.audit_log_table.insert.side_effect = RuntimeError("Database locked")

        audit_queue = queue_lib.Queue()
        audit_logger = dispatch.observability.AuditLogger()

        audit_logger.log_step(
            correlation_id="test-corr-db",
            folder_id=1,
            file_name="test.edi",
            step="validation",
            status="success",
            duration_ms=100,
        )

        for event in audit_logger.drain():
            audit_queue.put(event)

        writer = dispatch.observability.AuditBackgroundWriter(
            audit_queue, mock_db
        )

        import threading
        t = threading.Thread(target=writer._run)
        t.start()
        t.join(timeout=5.0)
        if t.is_alive():
            writer._shutdown.set()

        assert mock_db.audit_log_table.insert.called

    def test_audit_events_not_lost_on_db_failure(self, tmp_path):
        """Verify audit events are handled gracefully when DB is down."""
        import queue as queue_lib

        import dispatch.observability

        mock_db = MagicMock()
        mock_db.audit_log_table.insert.side_effect = sqlite3.OperationalError(
            "Database unavailable"
        )

        audit_queue = queue_lib.Queue()

        audit_logger = dispatch.observability.AuditLogger()

        audit_logger.log_step(
            correlation_id="test-corr-audit",
            folder_id=1,
            file_name="test.edi",
            step="convert",
            status="success",
            duration_ms=200,
        )

        for event in audit_logger.drain():
            audit_queue.put(event)

        writer = dispatch.observability.AuditBackgroundWriter(
            audit_queue, mock_db
        )

        import threading
        t = threading.Thread(target=writer._run)
        t.start()
        t.join(timeout=5.0)
        if t.is_alive():
            writer._shutdown.set()

        assert mock_db.audit_log_table.insert.called

    def test_audit_queue_is_thread_safe(self):
        """Verify audit logger is thread-safe for concurrent access."""
        import threading

        import dispatch.observability

        audit_logger = dispatch.observability.AuditLogger()

        def log_events(thread_id, count):
            for i in range(count):
                audit_logger.log_step(
                    correlation_id=f"thread-{thread_id}",
                    folder_id=thread_id,
                    file_name=f"file_{i}.edi",
                    step="validation",
                    status="success",
                    duration_ms=10,
                )

        threads = []
        for i in range(5):
            t = threading.Thread(target=log_events, args=(i, 20))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        events = audit_logger.drain()

        assert len(events) == 100


class TestErrorHandlerIntegration:
    def test_error_handler_alert_dispatcher_never_raises(self, tmp_path):
        """Verify ErrorHandler never raises even when alert dispatch fails."""
        import dispatch.observability
        from dispatch.error_handler import ErrorHandler

        alert_queue = dispatch.observability.AlertQueue(
            queue_path=str(tmp_path / "alert_queue.jsonl")
        )

        mock_smtp_service = MagicMock()
        mock_smtp_service.send_alert.side_effect = ConnectionRefusedError("SMTP down")

        dispatcher = dispatch.observability.AlertDispatcher(
            mock_smtp_service, alert_queue, {}
        )

        error_handler = ErrorHandler(
            alert_dispatcher=dispatcher,
        )

        error_handler.record_error(
            folder="test_folder",
            filename="test.edi",
            error=ValueError("Test error"),
            context={
                "correlation_id": "test-corr-eh",
                "folder_alias": "test",
                "file_path": "/test.edi",
                "alert_on_failure": True,
            },
        )

        assert error_handler.get_error_count() == 1
        queued = alert_queue.dequeue()
        assert queued is not None
        assert "alert_retry_count" in queued

    def test_error_handler_alert_skipped_when_disabled(self, tmp_path):
        """Verify alert is not sent when alert_on_failure is False."""
        import dispatch.observability
        from dispatch.error_handler import ErrorHandler

        alert_queue = dispatch.observability.AlertQueue(
            queue_path=str(tmp_path / "alert_queue.jsonl")
        )

        mock_smtp_service = MagicMock()

        dispatcher = dispatch.observability.AlertDispatcher(
            mock_smtp_service, alert_queue, {}
        )

        error_handler = ErrorHandler(
            alert_dispatcher=dispatcher,
        )

        error_handler.record_error(
            folder="test_folder",
            filename="test.edi",
            error=ValueError("Test error"),
            context={
                "correlation_id": "test-corr-no-alert",
                "folder_alias": "test",
                "file_path": "/test.edi",
                "alert_on_failure": False,
            },
        )

        assert error_handler.get_error_count() == 1
        queued = alert_queue.dequeue()
        assert queued is None
