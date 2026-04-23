# tests/unit/dispatch/test_error_handler_alert_integration.py
from unittest.mock import MagicMock

from dispatch.error_handler import ErrorHandler


class TestErrorHandlerAlertIntegration:
    def test_record_error_calls_alert_dispatcher_when_configured(self):
        mock_dispatcher = MagicMock()
        handler = ErrorHandler(alert_dispatcher=mock_dispatcher)
        handler.record_error(
            folder="/test",
            filename="test.edi",
            error=ValueError("test error"),
            context={
                "correlation_id": "test123",
                "folder_alias": "Test",
                "file_path": "/test.edi",
                "alert_on_failure": True,
            },
        )
        mock_dispatcher.dispatch_error_alert.assert_called_once()
        call_kwargs = mock_dispatcher.dispatch_error_alert.call_args.kwargs
        assert call_kwargs["correlation_id"] == "test123"
        assert call_kwargs["error_record"]["error_type"] == "ValueError"

    def test_record_error_skips_alert_when_dispatcher_none(self):
        handler = ErrorHandler(alert_dispatcher=None)
        handler.record_error(
            folder="/",
            filename="f.edi",
            error=ValueError("x"),
            context={"alert_on_failure": True},
        )

    def test_record_error_alert_never_crashes_processing(self):
        mock_dispatcher = MagicMock()
        mock_dispatcher.dispatch_error_alert.side_effect = RuntimeError("Dispatcher broken")
        handler = ErrorHandler(alert_dispatcher=mock_dispatcher)
        handler.record_error(
            folder="/",
            filename="f.edi",
            error=ValueError("x"),
            context={"alert_on_failure": True},
        )
        assert len(handler.errors) == 1

    def test_record_error_skips_alert_when_alert_on_failure_false(self):
        mock_dispatcher = MagicMock()
        handler = ErrorHandler(alert_dispatcher=mock_dispatcher)
        handler.record_error(
            folder="/",
            filename="f.edi",
            error=ValueError("x"),
            context={"alert_on_failure": False},
        )
        mock_dispatcher.dispatch_error_alert.assert_not_called()
