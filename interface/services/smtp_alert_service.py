# interface/services/smtp_alert_service.py
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from core.structured_logging import redact_sensitive_data


class SMTPAlertService:
    def __init__(
        self, smtp_service: Any, settings: dict, recipients: str
    ) -> None:
        self._smtp = smtp_service
        self._settings = settings
        self._recipients = recipients

    def send_alert(
        self,
        error_record: dict,
        correlation_id: str,
        folder_alias: str,
        file_path: str,
        processing_context: dict,
    ) -> None:
        subject = self._format_subject(folder_alias, error_record, file_path)
        body = self._format_email_body(
            error_record,
            correlation_id,
            folder_alias,
            file_path,
            processing_context,
        )
        self._smtp.send_email(
            to_addresses=self._recipients,
            subject=subject,
            body=body,
        )

    def _format_subject(
        self, folder_alias: str, error_record: dict, file_path: str
    ) -> str:
        error_type = error_record.get("error_type", "Unknown")
        filename = Path(file_path).name
        return f"[BFS ALERT] {folder_alias} — {error_type} — {filename}"

    def _format_email_body(
        self,
        error_record: dict,
        correlation_id: str,
        folder_alias: str,
        file_path: str,
        processing_context: dict,
    ) -> str:
        lines = [
            "BATCH FILE PROCESSOR — PROCESSING FAILURE ALERT",
            "=" * 50,
            f"Timestamp: {datetime.now().isoformat()}",
            f"Correlation ID: {correlation_id}",
            "",
            "FOLDER",
            "-" * 30,
            folder_alias,
            "",
            "FILE",
            "-" * 30,
            file_path,
            "",
            "ERROR",
            "-" * 30,
            f"Type: {error_record.get('error_type', 'Unknown')}",
            f"Message: {error_record.get('error_message', 'No message')}",
            "",
            "STACK TRACE",
            "-" * 30,
            error_record.get("stack_trace", "No stack trace available"),
        ]

        if processing_context.get("validation_errors"):
            lines.extend(
                [
                    "",
                    "EDI VALIDATION ERRORS",
                    "-" * 30,
                    processing_context["validation_errors"],
                ]
            )

        if processing_context.get("settings"):
            sanitized = redact_sensitive_data(processing_context["settings"])
            lines.extend(
                ["", "PROCESSING CONTEXT", "-" * 30, str(sanitized)]
            )

        lines.extend(
            [
                "",
                "This is an automated alert from Batch File Processor.",
            ]
        )

        return "\n".join(lines)
