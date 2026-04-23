# tests/unit/dispatch/observability/test_background_writer.py
import queue
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
        writer = AuditBackgroundWriter(q, db)
        writer.start()
        q.put(evt)
        time.sleep(0.5)
        db.audit_log_table.insert.assert_called_once()
        writer.stop()

    def test_does_not_crash_on_db_error(self):
        q = queue.Queue()
        db = MagicMock()
        db.audit_log_table.insert.side_effect = RuntimeError("DB error")
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
        time.sleep(0.5)
        writer.stop()
