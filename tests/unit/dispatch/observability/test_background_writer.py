# tests/unit/dispatch/observability/test_background_writer.py
import queue
import threading
import time
from unittest.mock import MagicMock

from dispatch.observability.audit_logger import AuditEvent
from dispatch.observability.background_writer import AuditBackgroundWriter

class TestAuditBackgroundWriter:
    def test_start_creates_thread(self):
        q = queue.Queue()
        db = MagicMock()
        writer = AuditBackgroundWriter(q, db)
        writer.start()
        assert writer._thread is not None
        assert writer._thread.daemon is True
        writer.stop()

    def test_stop_signals_and_joins(self):
        q = queue.Queue()
        db = MagicMock()
        writer = AuditBackgroundWriter(q, db)
        writer.start()
        writer.stop(timeout=2.0)
        assert not writer._thread.is_alive()

    def test_writes_event_to_db(self):
        q = queue.Queue()
        db = MagicMock()
        db.audit_log_table = MagicMock()
        evt = AuditEvent(
            correlation_id="test",
            folder_id=1,
            file_name="x.edi",
            event_type="convert",
            event_status="success",
        )
        written = threading.Event()
        db.audit_log_table.insert.side_effect = lambda *_a, **_kw: written.set()
        writer = AuditBackgroundWriter(q, db)
        writer.start()
        q.put(evt)
        assert written.wait(timeout=2), "writer did not process event within 2s"
        db.audit_log_table.insert.assert_called_once()
        writer.stop()

    def test_does_not_crash_on_db_error(self):
        q = queue.Queue()
        db = MagicMock()
        attempted = threading.Event()
        def _raise(*_a, **_kw):
            attempted.set()
            raise RuntimeError("DB error")
        db.audit_log_table.insert.side_effect = _raise
        writer = AuditBackgroundWriter(q, db)
        writer.start()
        evt = AuditEvent(
            correlation_id="test",
            folder_id=1,
            file_name="x.edi",
            event_type="send",
            event_status="failure",
        )
        q.put(evt)
        assert attempted.wait(timeout=2), "writer never invoked insert (would hang test)"
        writer.stop()
