# tests/unit/dispatch/observability/test_package.py


class TestObservabilityPackage:
    def test_exports(self):
        from dispatch.observability import (
            AlertDispatcher,
            AlertQueue,
            AuditBackgroundWriter,
            AuditEvent,
            AuditLogger,
        )

        assert AlertDispatcher is not None
        assert AlertQueue is not None
        assert AuditEvent is not None
        assert AuditLogger is not None
        assert AuditBackgroundWriter is not None

    def test_audit_event_can_be_instantiated(self):
        from dispatch.observability import AuditEvent

        event = AuditEvent(
            correlation_id="test123",
            folder_id=1,
            file_name="test.edi",
            event_type="validation",
            event_status="success",
        )
        assert event.correlation_id == "test123"
        assert event.event_type == "validation"
