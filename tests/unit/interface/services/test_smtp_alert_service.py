# tests/unit/interface/services/test_smtp_alert_service.py
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from interface.services.smtp_alert_service import SMTPAlertService


class TestSMTPAlertService:
    def test_send_alert_composes_correct_subject(self):
        smtp = MagicMock()
        service = SMTPAlertService(smtp, {}, "admin@example.com")
        service.send_alert(
            error_record={"error_type": "ValidationError", "error_message": "bad UPC"},
            correlation_id="corr123",
            folder_alias="Test Folder",
            file_path="/incoming/test.edi",
            processing_context={"step": "validation"},
        )
        smtp.send_email.assert_called_once()
        call_kwargs = smtp.send_email.call_args.kwargs
        assert "[BFS ALERT] Test Folder" in call_kwargs["subject"]
        assert "ValidationError" in call_kwargs["subject"]

    def test_send_alert_uses_recipients_from_constructor(self):
        smtp = MagicMock()
        service = SMTPAlertService(smtp, {}, "alerts@company.com,backup@company.com")
        service.send_alert(
            error_record={"error_type": "Error"},
            correlation_id="x",
            folder_alias="F",
            file_path="/f.edi",
            processing_context={},
        )
        assert (
            "alerts@company.com,backup@company.com"
            in smtp.send_email.call_args.kwargs["to_addresses"]
        )

    def test_send_alert_includes_correlation_id_in_body(self):
        smtp = MagicMock()
        service = SMTPAlertService(smtp, {}, "x@y.com")
        service.send_alert(
            error_record={"error_type": "Error"},
            correlation_id="corrXYZ",
            folder_alias="Folder",
            file_path="/data/file.edi",
            processing_context={},
        )
        body = smtp.send_email.call_args.kwargs["body"]
        assert "corrXYZ" in body

    def test_send_alert_reraises_on_smtp_failure(self):
        smtp = MagicMock()
        smtp.send_email.side_effect = ConnectionRefusedError("SMTP down")
        service = SMTPAlertService(smtp, {}, "x@y.com")
        with pytest.raises(ConnectionRefusedError):
            service.send_alert(
                error_record={},
                correlation_id="x",
                folder_alias="F",
                file_path="/f.edi",
                processing_context={},
            )

    def test_send_alert_includes_error_type_and_message(self):
        smtp = MagicMock()
        service = SMTPAlertService(smtp, {}, "x@y.com")
        service.send_alert(
            error_record={
                "error_type": "ValueError",
                "error_message": "invalid UPC format",
            },
            correlation_id="abc",
            folder_alias="Test",
            file_path="/data/test.edi",
            processing_context={},
        )
        body = smtp.send_email.call_args.kwargs["body"]
        assert "ValueError" in body
        assert "invalid UPC format" in body

    def test_send_alert_includes_stack_trace(self):
        smtp = MagicMock()
        service = SMTPAlertService(smtp, {}, "x@y.com")
        service.send_alert(
            error_record={
                "error_type": "RuntimeError",
                "stack_trace": "Traceback (most recent call last):\n  File 'test.py', line 10",
            },
            correlation_id="abc",
            folder_alias="Test",
            file_path="/data/test.edi",
            processing_context={},
        )
        body = smtp.send_email.call_args.kwargs["body"]
        assert "STACK TRACE" in body