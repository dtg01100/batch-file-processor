"""Comprehensive tests for retry and resend logic.

Tests cover:
- FTP backend retry behaviour using MockFTPClient
- Email backend retry behaviour using MockSMTPClient
- Resend flag processing via DispatchOrchestrator with an in-memory DB
"""

import errno
import ftplib
import os
import smtplib
import sys
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from backend import email_backend, ftp_backend
from backend.ftp_client import MockFTPClient
from backend.smtp_client import MockSMTPClient
from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator
from dispatch.send_manager import MockBackend

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FTP_PARAMS = {
    "ftp_server": "ftp.test.local",
    "ftp_port": 21,
    "ftp_username": "user",
    "ftp_password": "pass",
    "ftp_folder": "",
}

EMAIL_PARAMS = {
    "email_to": "recipient@test.com",
    "email_subject_line": "Test Subject",
}

EMAIL_SETTINGS = {
    "email_address": "sender@test.com",
    "email_smtp_server": "smtp.test.local",
    "smtp_port": 587,
    "email_username": "",
    "email_password": "",
}


@pytest.fixture
def temporary_test_file(tmp_path):
    """Create a small temporary file for send tests."""
    p = tmp_path / "temporary_test_file.txt"
    p.write_bytes(b"batch file processor test data\n")
    return str(p)


# ---------------------------------------------------------------------------
# In-memory processed-files DB
# ---------------------------------------------------------------------------


class InMemoryProcessedFiles:
    """Minimal in-memory replacement for the processed_files DB table."""

    def __init__(self):
        self.records = []
        self._next_id = 1

    def find(self, folder_id=None, **kwargs):
        result = list(self.records)
        if folder_id is not None:
            result = [r for r in result if r.get("folder_id") == folder_id]
        for k, v in kwargs.items():
            result = [r for r in result if r.get(k) == v]
        return result

    def find_one(self, **kwargs):
        for r in self.records:
            if all(r.get(k) == v for k, v in kwargs.items()):
                return r
        return None

    def insert(self, record):
        record = dict(record)
        record["id"] = self._next_id
        self._next_id += 1
        self.records.append(record)
        return record["id"]

    def update(self, record, keys):
        for r in self.records:
            if all(r.get(k) == record.get(k) for k in keys):
                r.update(record)
                return

    def count(self, **kwargs):
        return len(self.find(**kwargs))


# ---------------------------------------------------------------------------
# FTP retry tests
# ---------------------------------------------------------------------------


class TestFTPRetryLogic:
    """FTP backend retry behaviour verified with MockFTPClient."""

    def test_ftp_retry_after_connect_failure(self, temporary_test_file):
        """Two connect failures should trigger retries; the third attempt succeeds."""
        mock_client = MockFTPClient()
        # Inject 2 errors: first two connect() calls consume them and fail (not recorded).
        # Third connect() call succeeds → connections=[1 entry].
        mock_client.add_error(ftplib.error_temp("Connection refused"))
        mock_client.add_error(ftplib.error_temp("Connection refused"))

        with patch("backend.ftp_backend.time.sleep"):
            result = ftp_backend.do(FTP_PARAMS, {}, temporary_test_file, ftp_client=mock_client)

        assert result is True
        # Only the successful connect is recorded; 2 failed attempts are not.
        assert len(mock_client.connections) == 1

    def test_ftp_retry_after_login_failure(self, temporary_test_file):
        """A login failure should trigger a retry."""
        mock_client = MockFTPClient()
        mock_client.add_error(ftplib.error_perm("530 Login incorrect"))

        with patch("backend.ftp_backend.time.sleep"):
            result = ftp_backend.do(FTP_PARAMS, {}, temporary_test_file, ftp_client=mock_client)

        assert result is True
        # At least one successful login after the failure
        assert len(mock_client.logins) >= 1

    def test_ftp_succeeds_on_third_attempt(self, temporary_test_file):
        """Inject two failures; file should eventually be sent on the third attempt."""
        mock_client = MockFTPClient()
        mock_client.add_error(ftplib.error_temp("Temporary failure"))
        mock_client.add_error(ftplib.error_temp("Temporary failure"))

        with patch("backend.ftp_backend.time.sleep"):
            result = ftp_backend.do(FTP_PARAMS, {}, temporary_test_file, ftp_client=mock_client)

        assert result is True
        assert len(mock_client.files_sent) == 1
        sent_cmd, sent_data = mock_client.files_sent[0]
        assert "temporary_test_file.txt" in sent_cmd.lower() or "stor" in sent_cmd.lower()
        assert sent_data == b"batch file processor test data\n"

    def test_ftp_gives_up_after_10_retries(self, temporary_test_file):
        """Eleven consecutive failures should cause an exception after 10 retries."""
        mock_client = MockFTPClient()
        # Each outer-while iteration requires 2 errors (TLS + non-TLS both fail).
        # 11 outer failures × 2 errors each = 22 errors to reach counter==10 then raise.
        for _ in range(22):
            mock_client.add_error(ftplib.error_temp("Server unavailable"))

        with patch("backend.ftp_backend.time.sleep"):
            with pytest.raises(Exception):
                ftp_backend.do(FTP_PARAMS, {}, temporary_test_file, ftp_client=mock_client)

    def test_ftp_no_sleep_on_first_attempt(self, temporary_test_file):
        """Successful first attempt must not call time.sleep at all."""
        mock_client = MockFTPClient()

        with patch("backend.ftp_backend.time.sleep") as mock_sleep:
            result = ftp_backend.do(FTP_PARAMS, {}, temporary_test_file, ftp_client=mock_client)

        assert result is True
        mock_sleep.assert_not_called()

    def test_ftp_sleep_called_on_retry(self, temporary_test_file):
        """time.sleep(2) should be called once when one retry occurs."""
        mock_client = MockFTPClient()
        # One transient error should cause one retry and one sleep call.
        mock_client.add_error(ftplib.error_temp("Transient error"))

        with patch("backend.ftp_backend.time.sleep") as mock_sleep:
            result = ftp_backend.do(FTP_PARAMS, {}, temporary_test_file, ftp_client=mock_client)

        assert result is True
        mock_sleep.assert_called_once_with(2)

    def test_ftp_file_content_preserved_after_retry(self, temporary_test_file):
        """The file content sent on retry must match the original file."""
        mock_client = MockFTPClient()
        mock_client.add_error(ftplib.error_temp("Retry me"))

        with patch("backend.ftp_backend.time.sleep"):
            result = ftp_backend.do(FTP_PARAMS, {}, temporary_test_file, ftp_client=mock_client)

        assert result is True
        assert len(mock_client.files_sent) == 1
        _, data = mock_client.files_sent[0]
        assert data == b"batch file processor test data\n"

    def test_ftp_retry_counter_resets_between_calls(self, temporary_test_file):
        """Each call to ftp_backend.do() starts its own retry counter."""
        mock_client_a = MockFTPClient()
        mock_client_a.add_error(ftplib.error_temp("First call error"))

        mock_client_b = MockFTPClient()
        mock_client_b.add_error(ftplib.error_temp("Second call error"))

        with patch("backend.ftp_backend.time.sleep"):
            result_a = ftp_backend.do(
                FTP_PARAMS, {}, temporary_test_file, ftp_client=mock_client_a
            )
            result_b = ftp_backend.do(
                FTP_PARAMS, {}, temporary_test_file, ftp_client=mock_client_b
            )

        assert result_a is True
        assert result_b is True

    def test_ftp_exactly_10_retries_succeeds(self, temporary_test_file):
        """Exactly 10 failures followed by success should still complete."""
        mock_client = MockFTPClient()
        for _ in range(10):
            mock_client.add_error(ftplib.error_temp("Always failing"))

        with patch("backend.ftp_backend.time.sleep"):
            result = ftp_backend.do(FTP_PARAMS, {}, temporary_test_file, ftp_client=mock_client)

        assert result is True

    def test_ftp_storbinary_called_with_filename(self, temporary_test_file):
        """storbinary command must contain the base filename."""
        mock_client = MockFTPClient()

        with patch("backend.ftp_backend.time.sleep"):
            ftp_backend.do(FTP_PARAMS, {}, temporary_test_file, ftp_client=mock_client)

        assert len(mock_client.files_sent) == 1
        cmd, _ = mock_client.files_sent[0]
        assert "temporary_test_file.txt" in cmd


# ---------------------------------------------------------------------------
# Email retry tests
# ---------------------------------------------------------------------------


class TestEmailRetryLogic:
    """Email backend retry behaviour verified with MockSMTPClient."""

    def test_email_retry_after_smtp_failure(self, temporary_test_file):
        """A connect failure should trigger one retry."""
        mock_client = MockSMTPClient()
        mock_client.add_error(smtplib.SMTPConnectError(421, "Service unavailable"))

        with patch("backend.email_backend.time.sleep"):
            result = email_backend.do(
                EMAIL_PARAMS, EMAIL_SETTINGS, temporary_test_file, smtp_client=mock_client
            )

        assert result is True
        # First connect raised (not recorded), second connect succeeded (recorded)
        assert len(mock_client.connections) == 1

    def test_email_succeeds_on_second_attempt(self, temporary_test_file):
        """One injected failure; email is sent on the second attempt."""
        mock_client = MockSMTPClient()
        mock_client.add_error(smtplib.SMTPConnectError(421, "Try again"))

        with patch("backend.email_backend.time.sleep"):
            result = email_backend.do(
                EMAIL_PARAMS, EMAIL_SETTINGS, temporary_test_file, smtp_client=mock_client
            )

        assert result is True
        assert len(mock_client.emails_sent) == 1

    def test_email_gives_up_after_10_retries(self, temporary_test_file):
        """Eleven failures must cause an exception after 10 retries."""
        mock_client = MockSMTPClient()
        for _ in range(11):
            mock_client.add_error(smtplib.SMTPConnectError(421, "Unavailable"))

        with patch("backend.email_backend.time.sleep"):
            with pytest.raises(Exception):
                email_backend.do(
                    EMAIL_PARAMS, EMAIL_SETTINGS, temporary_test_file, smtp_client=mock_client
                )

    def test_email_no_retries_on_success(self, temporary_test_file):
        """time.sleep must not be called when the first attempt succeeds."""
        mock_client = MockSMTPClient()

        with patch("backend.email_backend.time.sleep") as mock_sleep:
            result = email_backend.do(
                EMAIL_PARAMS, EMAIL_SETTINGS, temporary_test_file, smtp_client=mock_client
            )

        assert result is True
        mock_sleep.assert_not_called()

    def test_email_sleep_exponential_backoff(self, temporary_test_file):
        """email_backend sleeps 2**counter seconds; verify for counter=1."""
        mock_client = MockSMTPClient()
        mock_client.add_error(smtplib.SMTPConnectError(421, "Temp fail"))

        with patch("backend.email_backend.time.sleep") as mock_sleep:
            result = email_backend.do(
                EMAIL_PARAMS, EMAIL_SETTINGS, temporary_test_file, smtp_client=mock_client
            )

        assert result is True
        # counter is 1 after first failure → sleep(2**1) = sleep(2)
        mock_sleep.assert_called_once_with(2)

    def test_email_attachment_sent_on_retry(self, temporary_test_file):
        """The file attachment must be present even when sent on a retry."""
        mock_client = MockSMTPClient()
        mock_client.add_error(smtplib.SMTPConnectError(421, "Try again"))

        with patch("backend.email_backend.time.sleep"):
            result = email_backend.do(
                EMAIL_PARAMS, EMAIL_SETTINGS, temporary_test_file, smtp_client=mock_client
            )

        assert result is True
        last = mock_client.emails_sent[-1]
        # The EmailMessage object carries the attachment
        msg = last["msg"]
        content_types = [p.get_content_type() for p in msg.iter_parts()]
        assert any("text" in ct or "application" in ct for ct in content_types)

    def test_email_subject_preserved_after_retry(self, temporary_test_file):
        """Subject line must be unchanged on a retry attempt."""
        params = dict(EMAIL_PARAMS)
        params["email_subject_line"] = "My Fixed Subject"

        mock_client = MockSMTPClient()
        mock_client.add_error(smtplib.SMTPConnectError(421, "Retry"))

        with patch("backend.email_backend.time.sleep"):
            result = email_backend.do(
                params, EMAIL_SETTINGS, temporary_test_file, smtp_client=mock_client
            )

        assert result is True
        msg = mock_client.emails_sent[-1]["msg"]
        assert msg["Subject"] == "My Fixed Subject"

    def test_email_exactly_10_retries_succeeds(self, temporary_test_file):
        """Exactly 10 failures followed by success should still complete."""
        mock_client = MockSMTPClient()
        for _ in range(10):
            mock_client.add_error(smtplib.SMTPConnectError(421, "Fail"))

        with patch("backend.email_backend.time.sleep"):
            result = email_backend.do(
                EMAIL_PARAMS, EMAIL_SETTINGS, temporary_test_file, smtp_client=mock_client
            )

        assert result is True

    def test_email_network_unreachable_fails_fast(self, temporary_test_file):
        """Errno 101 should fail immediately without retry backoff."""
        mock_client = MockSMTPClient()
        mock_client.add_error(OSError(errno.ENETUNREACH, "Network is unreachable"))

        with patch("backend.email_backend.time.sleep") as mock_sleep:
            with pytest.raises(RuntimeError, match="Network is unreachable"):
                email_backend.do(
                    EMAIL_PARAMS, EMAIL_SETTINGS, temporary_test_file, smtp_client=mock_client
                )

        mock_sleep.assert_not_called()


# ---------------------------------------------------------------------------
# Resend / orchestrator tests
# ---------------------------------------------------------------------------


def _make_folder(folder_path: str, folder_id: int = 1) -> dict:
    """Return a minimal folder config dict for orchestrator tests."""
    return {
        "id": folder_id,
        "folder_name": folder_path,
        "alias": f"TestFolder_{folder_id}",
        "folder_is_active": True,
        "process_backend_copy": False,
        "process_backend_ftp": False,
        "process_backend_email": False,
        "process_edi": False,
        "split_edi": False,
        "tweak_edi": False,
        "force_edi_validation": False,
        "convert_edi": False,
    }


class TestResendLogic:
    """Resend flag processing via DispatchOrchestrator with InMemoryProcessedFiles."""

    @pytest.fixture
    def folder_dir(self, tmp_path):
        """Create a temporary folder containing one test file."""
        d = tmp_path / "inbox"
        d.mkdir()
        (d / "data.txt").write_bytes(b"hello world")
        return d

    @pytest.fixture
    def mock_backend(self):
        return MockBackend(should_succeed=True)

    @pytest.fixture
    def orchestrator(self, mock_backend):
        config = DispatchConfig(backends={"mock": mock_backend})
        return DispatchOrchestrator(config)

    def test_processed_file_not_resent(self, folder_dir, mock_backend):
        """File already in processed_files with resend_flag=0 should be skipped."""
        processed = InMemoryProcessedFiles()
        folder = _make_folder(str(folder_dir))

        # Pre-populate as already processed
        file_path = str(folder_dir / "data.txt")
        import hashlib

        with open(file_path, "rb") as f:
            checksum = hashlib.md5(f.read()).hexdigest()

        processed.insert(
            {
                "file_name": file_path,
                "folder_id": 1,
                "folder_alias": "TestFolder_1",
                "file_checksum": checksum,
                "resend_flag": 0,
                "status": "processed",
            }
        )

        config = DispatchConfig(backends={"mock": mock_backend})
        orc = DispatchOrchestrator(config)
        run_log = []
        orc.process_folder(folder, run_log, processed_files=processed)

        # File was already processed → MockBackend must NOT have been called
        assert len(mock_backend.send_calls) == 0

    def test_file_with_resend_flag_is_resent(self, folder_dir, mock_backend):
        """File with resend_flag=1 must be processed again."""
        processed = InMemoryProcessedFiles()
        folder = _make_folder(str(folder_dir))

        file_path = str(folder_dir / "data.txt")
        import hashlib

        with open(file_path, "rb") as f:
            checksum = hashlib.md5(f.read()).hexdigest()

        processed.insert(
            {
                "file_name": file_path,
                "folder_id": 1,
                "folder_alias": "TestFolder_1",
                "file_checksum": checksum,
                "resend_flag": 1,
                "status": "processed",
            }
        )

        config = DispatchConfig(backends={"mock": mock_backend})
        orc = DispatchOrchestrator(config)
        run_log = []
        orc.process_folder(folder, run_log, processed_files=processed)

        assert len(mock_backend.send_calls) == 1

    def test_resend_updates_db_record(self, folder_dir, mock_backend):
        """After resend, the DB record should have resend_flag=0 and status='processed'."""
        processed = InMemoryProcessedFiles()
        folder = _make_folder(str(folder_dir))

        file_path = str(folder_dir / "data.txt")
        import hashlib

        with open(file_path, "rb") as f:
            checksum = hashlib.md5(f.read()).hexdigest()

        processed.insert(
            {
                "file_name": file_path,
                "folder_id": 1,
                "folder_alias": "TestFolder_1",
                "file_checksum": checksum,
                "resend_flag": 1,
                "status": "processed",
            }
        )

        config = DispatchConfig(backends={"mock": mock_backend})
        orc = DispatchOrchestrator(config)
        run_log = []
        orc.process_folder(folder, run_log, processed_files=processed)

        updated = processed.find_one(file_name=file_path, folder_id=1)
        assert updated is not None
        assert updated.get("resend_flag") == 0
        assert updated.get("status") == "processed"

    def test_new_file_always_sent(self, folder_dir, mock_backend):
        """A file not in processed_files must always be processed."""
        processed = InMemoryProcessedFiles()
        folder = _make_folder(str(folder_dir))

        config = DispatchConfig(backends={"mock": mock_backend})
        orc = DispatchOrchestrator(config)
        run_log = []
        orc.process_folder(folder, run_log, processed_files=processed)

        assert len(mock_backend.send_calls) == 1

    def test_new_file_added_to_db_after_send(self, folder_dir, mock_backend):
        """After a successful send, a new record must appear in processed_files."""
        processed = InMemoryProcessedFiles()
        folder = _make_folder(str(folder_dir))
        file_path = str(folder_dir / "data.txt")

        config = DispatchConfig(backends={"mock": mock_backend})
        orc = DispatchOrchestrator(config)
        run_log = []
        orc.process_folder(folder, run_log, processed_files=processed)

        record = processed.find_one(file_name=file_path, folder_id=1)
        assert record is not None

    def test_resend_flag_cleared_after_success(self, folder_dir, mock_backend):
        """resend_flag must be 0 after a successful resend."""
        processed = InMemoryProcessedFiles()
        folder = _make_folder(str(folder_dir))

        file_path = str(folder_dir / "data.txt")
        import hashlib

        with open(file_path, "rb") as f:
            checksum = hashlib.md5(f.read()).hexdigest()

        processed.insert(
            {
                "file_name": file_path,
                "folder_id": 1,
                "folder_alias": "TestFolder_1",
                "file_checksum": checksum,
                "resend_flag": 1,
                "status": "processed",
            }
        )

        config = DispatchConfig(backends={"mock": mock_backend})
        orc = DispatchOrchestrator(config)
        run_log = []
        orc.process_folder(folder, run_log, processed_files=processed)

        record = processed.find_one(file_name=file_path, folder_id=1)
        assert record["resend_flag"] == 0

    def test_multiple_files_some_resend(self, tmp_path):
        """Mix of new, processed, and resend files -- only correct ones sent."""
        folder_dir = tmp_path / "multi"
        folder_dir.mkdir()

        # Create 3 files
        (folder_dir / "new.txt").write_bytes(b"new file content")
        (folder_dir / "done.txt").write_bytes(b"already done")
        (folder_dir / "resend.txt").write_bytes(b"needs resend")

        import hashlib

        def md5(path):
            return hashlib.md5(open(path, "rb").read()).hexdigest()

        processed = InMemoryProcessedFiles()
        folder_id = 42
        folder = _make_folder(str(folder_dir), folder_id=folder_id)

        # "done.txt" is already processed, no resend
        processed.insert(
            {
                "file_name": str(folder_dir / "done.txt"),
                "folder_id": folder_id,
                "folder_alias": "TestFolder_42",
                "file_checksum": md5(str(folder_dir / "done.txt")),
                "resend_flag": 0,
                "status": "processed",
            }
        )
        # "resend.txt" is processed but marked for resend
        processed.insert(
            {
                "file_name": str(folder_dir / "resend.txt"),
                "folder_id": folder_id,
                "folder_alias": "TestFolder_42",
                "file_checksum": md5(str(folder_dir / "resend.txt")),
                "resend_flag": 1,
                "status": "processed",
            }
        )

        mock_be = MockBackend(should_succeed=True)
        config = DispatchConfig(backends={"mock": mock_be})
        orc = DispatchOrchestrator(config)
        run_log = []
        orc.process_folder(folder, run_log, processed_files=processed)

        sent_files = [os.path.basename(call[2]) for call in mock_be.send_calls]
        assert "done.txt" not in sent_files
        assert "new.txt" in sent_files
        assert "resend.txt" in sent_files

    def test_failed_backend_does_not_record_as_processed(self, folder_dir):
        """If the backend fails, the file should NOT be added to processed_files."""
        failing_backend = MockBackend(should_succeed=False)
        processed = InMemoryProcessedFiles()
        folder = _make_folder(str(folder_dir))

        config = DispatchConfig(backends={"mock": failing_backend})
        orc = DispatchOrchestrator(config)
        run_log = []
        orc.process_folder(folder, run_log, processed_files=processed)

        assert len(processed.records) == 0

    def test_no_backends_enabled_does_not_mark_processed(self, folder_dir):
        """When no backends are enabled, files should not appear in processed_files."""
        processed = InMemoryProcessedFiles()
        folder = _make_folder(str(folder_dir))

        # No backends injected, no default backends enabled
        config = DispatchConfig(backends={})
        orc = DispatchOrchestrator(config)
        run_log = []
        orc.process_folder(folder, run_log, processed_files=processed)

        assert len(processed.records) == 0

    def test_resend_sent_to_field_updated(self, folder_dir):
        """After resend, sent_to in the DB should reflect the active backend."""
        mock_be = MockBackend(should_succeed=True)
        processed = InMemoryProcessedFiles()
        folder = dict(_make_folder(str(folder_dir)))
        folder["process_backend_ftp"] = True
        folder["ftp_server"] = "ftp.example.com"

        file_path = str(folder_dir / "data.txt")
        import hashlib

        with open(file_path, "rb") as f:
            checksum = hashlib.md5(f.read()).hexdigest()

        processed.insert(
            {
                "file_name": file_path,
                "folder_id": 1,
                "folder_alias": "TestFolder_1",
                "file_checksum": checksum,
                "resend_flag": 1,
                "status": "processed",
            }
        )

        config = DispatchConfig(backends={"ftp": mock_be})
        orc = DispatchOrchestrator(config)
        run_log = []
        orc.process_folder(folder, run_log, processed_files=processed)

        record = processed.find_one(file_name=file_path, folder_id=1)
        assert record is not None
        # sent_to should mention FTP (folder has process_backend_ftp=True)
        assert "FTP" in record.get("sent_to", "")

    def test_empty_folder_no_records_added(self, tmp_path):
        """Processing an empty folder should not insert any records."""
        empty_dir = tmp_path / "empty_folder"
        empty_dir.mkdir()

        processed = InMemoryProcessedFiles()
        folder = _make_folder(str(empty_dir))
        mock_be = MockBackend(should_succeed=True)

        config = DispatchConfig(backends={"mock": mock_be})
        orc = DispatchOrchestrator(config)
        run_log = []
        orc.process_folder(folder, run_log, processed_files=processed)

        assert len(processed.records) == 0
        assert len(mock_be.send_calls) == 0

    def test_nonexistent_folder_returns_failure_result(self, tmp_path):
        """Processing a non-existent folder should return a failed FolderResult."""
        processed = InMemoryProcessedFiles()
        folder = _make_folder(str(tmp_path / "does_not_exist"))
        mock_be = MockBackend(should_succeed=True)

        config = DispatchConfig(backends={"mock": mock_be})
        orc = DispatchOrchestrator(config)
        run_log = []
        result = orc.process_folder(folder, run_log, processed_files=processed)

        assert result.success is False
        assert len(result.errors) > 0

    def test_orchestrator_summary_after_processing(self, folder_dir, mock_backend):
        """Orchestrator summary should count processed files correctly."""
        processed = InMemoryProcessedFiles()
        folder = _make_folder(str(folder_dir))

        config = DispatchConfig(backends={"mock": mock_backend})
        orc = DispatchOrchestrator(config)
        run_log = []
        orc.process_folder(folder, run_log, processed_files=processed)

        summary = orc.get_summary()
        assert "1 processed" in summary
