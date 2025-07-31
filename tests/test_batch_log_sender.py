import pytest
import batch_log_sender

from unittest.mock import MagicMock

from unittest.mock import patch, MagicMock

def test_send_log_empty_file(tmp_path, monkeypatch):
    # Patch smtplib.SMTP to prevent real network calls
    import smtplib
    monkeypatch.setattr(smtplib, 'SMTP', MagicMock())
    log_file = tmp_path / "empty.log"
    log_file.write_text("")
    # Prepare minimal dummy arguments for do()
    settings = {
        'email_address': 'test@example.com',
        'email_username': '',
        'email_smtp_server': 'localhost',
        'smtp_port': 25,
        'email_password': ''
    }
    reporting = {'report_email_destination': 'dest@example.com'}
    class DummyTable:
        def count(self): return 0
        def all(self): return []
    emails_table = DummyTable()
    sent_emails_removal_queue = DummyTable()
    time = 'now'
    class Args: automatic = True
    args = Args()
    class Dummy:
        def configure(self, **kwargs): pass
        def update(self): pass
    root = Dummy()
    batch_number = 1
    emails_count = 0
    total_emails = 0
    simple_output = Dummy()
    run_summary_string = ''
    # Should not raise, but should handle empty
    assert batch_log_sender.do(settings, reporting, emails_table, sent_emails_removal_queue, time, args, root, batch_number, emails_count, total_emails, simple_output, run_summary_string) is None
