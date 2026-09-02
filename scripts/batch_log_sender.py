"""Batch log-email sender.

Sends the per-run log files out as email attachments. Historically the
``interface.services.progress_service.ProgressCallback`` was injected by the
Qt UI; Phase 7b removed the ``interface/`` package (see
``specs/webapp-phase-7b-interface-retirement.md``) so this module defines a
minimal local protocol + null implementation. ``dispatch.log_sender`` remains
the actively-used path; this script is retained as a CLI entry point for
running the legacy batch send flow without the webapp.
"""

from __future__ import annotations

import mimetypes
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class ProgressCallback(Protocol):
    """Minimal progress-callback contract used by :func:`do`.

    Only ``update_message`` is exercised; the rest are no-ops to keep this
    script decoupled from the deleted ``interface/`` package.
    """

    def update_message(self, message: str) -> None:
        ...


class NullProgressCallback:
    """No-op progress callback used when the caller omits one."""

    def update_message(self, message: str) -> None:
        return None


def do(
    settings,
    reporting,
    emails_table,
    sent_emails_removal_queue,
    time,
    batch_number,
    emails_count,
    total_emails,
    run_summary_string,
    progress_callback: ProgressCallback | None = None,
) -> None:
    if progress_callback is None:
        progress_callback = NullProgressCallback()

    settings["email_address"]
    settings["email_username"]
    to_address = reporting["report_email_destination"]
    to_address_list = to_address.split(", ")

    if emails_table.count() != 1:
        subject_line = "Logs from run at: " + time
        email_body_text = run_summary_string + ". See attached logs"
    else:
        subject_line = "Log from run at: " + time
        email_body_text = run_summary_string + ". See attached log"

    progress_callback.update_message(
        "sending reports emails\r"
        + "email "
        + str(batch_number)
        + " attachment "
        + str(emails_count)
        + " of "
        + str(total_emails)
    )

    message = EmailMessage()
    message["Subject"] = subject_line
    message["From"] = settings["email_address"]
    message["To"] = to_address_list
    message.set_content(email_body_text)

    for log in emails_table.all():
        progress_callback.update_message(
            "sending reports emails\r"
            + "email "
            + str(batch_number)
            + " attachment "
            + str(emails_count)
            + " of "
            + str(total_emails)
        )

        filename = log["log"]

        attachmentpath = Path(filename)
        attachmentname = os.path.basename(filename)
        ctype, encoding = mimetypes.guess_type(attachmentpath)
        if ctype is None or encoding is not None:
            ctype = "application/octet-stream"
        maintype, subtype = ctype.split("/", 1)
        with open(attachmentpath, "rb") as fp:
            message.add_attachment(
                fp.read(), maintype=maintype, subtype=subtype, filename=attachmentname
            )

        log["old_id"] = log.pop("id")
        if log["log"].endswith(".zip"):
            log["log"] = log["log"][:-4]
        sent_emails_removal_queue.insert(log)

    print("sending " + str(subject_line + " to " + str(to_address_list)))

    server = smtplib.SMTP(
        str(settings["email_smtp_server"]), int(settings["smtp_port"])
    )
    server.ehlo()
    server.starttls()
    if settings["email_username"] != "" and settings["email_password"] != "":
        server.login(settings["email_username"], settings["email_password"])
    server.send_message(message)
    server.close()
