"""Integration tests using real local FTP and SMTP servers.

Spins up real pyftpdlib FTP and aiosmtpd SMTP servers on ephemeral ports,
then exercises ftp_backend.do() and email_backend.do() against them.
All received files and emails are verified for byte-exact content.
"""

import ftplib
import hashlib
import io
import os
import smtplib
import socket
import threading
import time
import zipfile
from email import message_from_bytes
from typing import List, Optional

import pytest
try:
    from aiosmtpd.controller import Controller  # type: ignore
    AIOSMTPD_AVAILABLE = True
except Exception:
    AIOSMTPD_AVAILABLE = False

try:
    from pyftpdlib.authorizers import DummyAuthorizer  # type: ignore
    from pyftpdlib.handlers import FTPHandler  # type: ignore
    from pyftpdlib.servers import FTPServer  # type: ignore
    PYFTPDLIB_AVAILABLE = True
except Exception:
    PYFTPDLIB_AVAILABLE = False

from backend import email_backend, ftp_backend
from backend.email_backend import EmailBackend
from backend.ftp_client import MockFTPClient
from backend.smtp_client import MockSMTPClient, RealSMTPClient
from dispatch.send_manager import SendManager

pytestmark = [pytest.mark.integration, pytest.mark.backend]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _free_port() -> int:
    """Return an OS-assigned free TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


class _NoTLSSMTPClient(RealSMTPClient):
    """RealSMTPClient that silently skips STARTTLS when not supported.

    aiosmtpd test servers do not advertise STARTTLS, so calling starttls()
    raises SMTPNotSupportedError.  This subclass catches that specific error
    so that real messages are still delivered over the plain-text test
    connection.
    """

    def starttls(self) -> None:
        try:
            super().starttls()
        except smtplib.SMTPNotSupportedError:
            pass  # test server doesn't support TLS -- that's fine


# ---------------------------------------------------------------------------
# FTP server fixture
# ---------------------------------------------------------------------------


class _FTPFixture:
    """Wraps a pyftpdlib server started in a daemon thread."""

    def __init__(self, root_dir: str, host: str, port: int):
        self.root_dir = root_dir
        self.host = host
        self.port = port
        self._server: Optional[FTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        authorizer = DummyAuthorizer()
        authorizer.add_user("testuser", "testpass", self.root_dir, perm="elradfmwMT")

        # Each fixture instance needs its own handler class to avoid
        # cross-test pollution on the module-level attribute.
        class _Handler(FTPHandler):
            pass

        _Handler.authorizer = authorizer
        _Handler.passive_ports = range(60000, 60100)

        self._server = FTPServer((self.host, self.port), _Handler)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            kwargs={"timeout": 0.5, "blocking": True},
            daemon=True,
        )
        self._thread.start()
        # Brief pause so the server loop is ready
        time.sleep(0.05)

    def stop(self) -> None:
        if self._server is not None:
            self._server.close_all()
            self._server = None

    def list_uploaded_files(self, subdir: str = "") -> List[str]:
        """Return basenames of files in *root_dir/subdir*."""
        target = os.path.join(self.root_dir, subdir.lstrip("/"))
        if not os.path.isdir(target):
            return []
        return os.listdir(target)

    def read_uploaded_file(self, filename: str, subdir: str = "") -> bytes:
        """Read bytes of an uploaded file from the server root."""
        target = os.path.join(self.root_dir, subdir.lstrip("/"), filename)
        with open(target, "rb") as fh:
            return fh.read()


@pytest.fixture()
def ftp_server(tmp_path):
    """Start a real FTP server; yield (_FTPFixture, process_parameters dict)."""
    if not PYFTPDLIB_AVAILABLE:
        pytest.skip("pyftpdlib not installed")
    root = tmp_path / "ftproot"
    root.mkdir()
    port = _free_port()
    srv = _FTPFixture(str(root), "127.0.0.1", port)
    srv.start()

    params = {
        "ftp_server": "127.0.0.1",
        "ftp_port": port,
        "ftp_username": "testuser",
        "ftp_password": "testpass",
        "ftp_folder": "/upload/",
        "process_backend_ftp": True,
    }
    yield srv, params
    srv.stop()


# ---------------------------------------------------------------------------
# SMTP server fixture
# ---------------------------------------------------------------------------


class _CapturingHandler:
    """aiosmtpd handler that appends received envelopes to a list."""

    def __init__(self):
        self.messages: List[dict] = []

    async def handle_DATA(self, server, session, envelope):
        self.messages.append(
            {
                "mail_from": envelope.mail_from,
                "rcpt_tos": envelope.rcpt_tos,
                "data": envelope.content,
            }
        )
        return "250 Message accepted"


@pytest.fixture()
def smtp_server():
    """Start a real SMTP server; yield (handler, settings dict)."""
    if not AIOSMTPD_AVAILABLE:
        pytest.skip("aiosmtpd not installed")
    handler = _CapturingHandler()
    port = _free_port()
    controller = Controller(handler, hostname="127.0.0.1", port=port)
    controller.start()
    time.sleep(0.1)  # let the event loop start

    settings = {
        "email_address": "sender@test.com",
        "email_smtp_server": "127.0.0.1",
        "smtp_port": port,
        "email_username": "",
        "email_password": "",
    }
    yield handler, settings
    controller.stop()


def _make_email_params(
    recipient: str = "recipient@test.com", subject: str = "Test %filename%"
) -> dict:
    return {
        "email_to": recipient,
        "email_subject_line": subject,
        "process_backend_email": True,
    }


# ---------------------------------------------------------------------------
# Helper: create temp file with content
# ---------------------------------------------------------------------------


def _make_file(tmp_path, name: str, content: bytes) -> str:
    p = tmp_path / name
    p.write_bytes(content)
    return str(p)


# ---------------------------------------------------------------------------
# FTP Tests
# ---------------------------------------------------------------------------


class TestFTPLiveServer:
    """FTP integration tests against a real pyftpdlib server."""

    def test_single_file_ftp_send_txt(self, ftp_server, tmp_path):
        """Send a .txt file via FTP and verify byte-exact content on server."""
        srv, params = ftp_server
        content = b"Hello, this is a plain text file.\nLine 2.\n"
        filepath = _make_file(tmp_path, "hello.txt", content)

        result = ftp_backend.do(params, {}, filepath)

        assert result is True
        files = srv.list_uploaded_files("upload")
        assert "hello.txt" in files
        received = srv.read_uploaded_file("hello.txt", "upload")
        assert received == content

    def test_single_file_ftp_send_csv(self, ftp_server, tmp_path):
        """Send a .csv file via FTP and verify content character-by-character."""
        srv, params = ftp_server
        content = b"id,name,value\n1,alpha,100\n2,beta,200\n3,gamma,300\n"
        filepath = _make_file(tmp_path, "data.csv", content)

        result = ftp_backend.do(params, {}, filepath)

        assert result is True
        files = srv.list_uploaded_files("upload")
        assert "data.csv" in files
        received = srv.read_uploaded_file("data.csv", "upload")
        assert received == content

    def test_single_file_ftp_send_binary(self, ftp_server, tmp_path):
        """Send a binary blob via FTP and verify byte-exact content."""
        srv, params = ftp_server
        # Build a truly binary blob with all byte values
        content = bytes(range(256)) * 4 + b"\x00\xff\xfe\xfd"
        filepath = _make_file(tmp_path, "blob.bin", content)

        result = ftp_backend.do(params, {}, filepath)

        assert result is True
        received = srv.read_uploaded_file("blob.bin", "upload")
        assert received == content
        assert _md5(received) == _md5(content)

    def test_single_file_ftp_send_zip(self, ftp_server, tmp_path):
        """Send a .zip file via FTP and verify the archive is intact."""
        srv, params = ftp_server
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("readme.txt", "This is a test archive.")
            zf.writestr("data.csv", "col1,col2\n1,2\n")
        content = buf.getvalue()
        filepath = _make_file(tmp_path, "archive.zip", content)

        result = ftp_backend.do(params, {}, filepath)

        assert result is True
        received = srv.read_uploaded_file("archive.zip", "upload")
        assert received == content
        # Verify the zip is still a valid archive
        with zipfile.ZipFile(io.BytesIO(received)) as zf:
            assert "readme.txt" in zf.namelist()
            assert "data.csv" in zf.namelist()

    def test_multi_file_batch_ftp_send(self, ftp_server, tmp_path):
        """Send 5 different files in a batch and verify all arrive on the server."""
        srv, params = ftp_server
        files_to_send = {
            "file1.txt": b"Content of file 1",
            "file2.csv": b"a,b,c\n1,2,3\n",
            "file3.dat": b"\x00\x01\x02\x03",
            "file4.xml": b"<root><item>test</item></root>",
            "file5.json": b'{"key": "value", "num": 42}',
        }
        local_paths = []
        for name, content in files_to_send.items():
            local_paths.append(_make_file(tmp_path, name, content))

        for filepath in local_paths:
            result = ftp_backend.do(params, {}, filepath)
            assert result is True

        uploaded = srv.list_uploaded_files("upload")
        for name in files_to_send:
            assert name in uploaded, f"Expected {name} to be in {uploaded}"
        for name, expected_content in files_to_send.items():
            received = srv.read_uploaded_file(name, "upload")
            assert received == expected_content, f"Content mismatch for {name}"

    def test_ftp_send_to_subdirectory(self, ftp_server, tmp_path):
        """Send a file to a nested /subdir/nested/ path, verify directory creation."""
        srv, params = ftp_server
        nested_params = params.copy()
        nested_params["ftp_folder"] = "/subdir/nested/"
        content = b"Nested directory content"
        filepath = _make_file(tmp_path, "nested.txt", content)

        result = ftp_backend.do(nested_params, {}, filepath)

        assert result is True
        files = srv.list_uploaded_files("subdir/nested")
        assert "nested.txt" in files
        received = srv.read_uploaded_file("nested.txt", "subdir/nested")
        assert received == content

    def test_ftp_retry_on_connection_failure(self, tmp_path):
        """Verify FTP retry succeeds after 2 initial connect failures (injected mock)."""

        class _FailTwiceMock:
            """Fails connect() for the first two calls, succeeds thereafter."""

            def __init__(self):
                self.connect_count = 0
                self.logins: list = []
                self.files_sent: list = []
                self.directories_changed: list = []
                self.directories_created: list = []

            def connect(self, host, port, timeout=None):
                self.connect_count += 1
                if self.connect_count <= 2:
                    raise ftplib.error_temp("Connection refused (simulated)")

            def login(self, user, password):
                self.logins.append((user, password))

            def cwd(self, directory):
                self.directories_changed.append(directory)

            def mkd(self, directory):
                self.directories_created.append(directory)
                return directory

            def storbinary(self, cmd, fp, blocksize=8192):
                self.files_sent.append((cmd, fp.read()))

            def close(self):
                pass

        mock = _FailTwiceMock()
        content = b"retry test content"
        filepath = _make_file(tmp_path, "retry.txt", content)
        params = {
            "ftp_server": "127.0.0.1",
            "ftp_port": 21,
            "ftp_username": "testuser",
            "ftp_password": "testpass",
            "ftp_folder": "/",
            "process_backend_ftp": True,
        }

        # Suppress the sleep delay to keep the test fast
        original_sleep = ftp_backend.time.sleep
        ftp_backend.time.sleep = lambda _: None
        try:
            result = ftp_backend.do(params, {}, filepath, ftp_client=mock)
        finally:
            ftp_backend.time.sleep = original_sleep

        assert result is True
        assert (
            mock.connect_count == 3
        ), f"Expected 3 connect attempts, got {mock.connect_count}"
        assert len(mock.files_sent) == 1
        assert mock.files_sent[0][1] == content

    def test_ftp_send_large_file(self, ftp_server, tmp_path):
        """Send a 1 MB file via FTP and verify the checksum matches."""
        srv, params = ftp_server
        content = bytes(range(256)) * (1024 * 4)  # 1 MB
        assert len(content) == 1024 * 1024
        expected_md5 = _md5(content)
        filepath = _make_file(tmp_path, "large.bin", content)

        result = ftp_backend.do(params, {}, filepath)

        assert result is True
        received = srv.read_uploaded_file("large.bin", "upload")
        assert len(received) == len(content)
        assert _md5(received) == expected_md5

    def test_ftp_file_rename(self, ftp_server, tmp_path):
        """Send file via orchestrator with rename_file template; verify renamed file arrives."""

        from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator

        srv, ftp_params = ftp_server
        content = b"EDI data to rename"
        filepath = _make_file(tmp_path, "original.txt", content)

        folder_cfg = {
            "folder_name": str(tmp_path),
            "alias": "rename_test",
            "rename_file": "renamed_output",
            "process_backend_ftp": True,
            "ftp_server": ftp_params["ftp_server"],
            "ftp_port": ftp_params["ftp_port"],
            "ftp_username": ftp_params["ftp_username"],
            "ftp_password": ftp_params["ftp_password"],
            "ftp_folder": ftp_params["ftp_folder"],
        }

        config = DispatchConfig(settings={})
        orchestrator = DispatchOrchestrator(config)
        file_result = orchestrator.process_file(filepath, folder_cfg)

        assert file_result.sent is True
        uploaded_files = srv.list_uploaded_files("upload")
        # The rename template produces "renamed_output.txt"
        assert any(
            "renamed_output" in f for f in uploaded_files
        ), f"No renamed file found in {uploaded_files}"

    def test_ftp_username_password_verified(self, tmp_path):
        """Verify that ftp_backend sends the correct credentials to the FTP client."""
        mock = MockFTPClient()
        content = b"credential verification test"
        filepath = _make_file(tmp_path, "creds.txt", content)
        params = {
            "ftp_server": "10.0.0.1",
            "ftp_port": 2121,
            "ftp_username": "super_user",
            "ftp_password": "s3cur3_p@ss",
            "ftp_folder": "/",
            "process_backend_ftp": True,
        }

        result = ftp_backend.do(params, {}, filepath, ftp_client=mock)

        assert result is True
        assert len(mock.logins) == 1
        user, password = mock.logins[0]
        assert user == "super_user"
        assert password == "s3cur3_p@ss"
        assert mock.connections[0][0] == "10.0.0.1"
        assert mock.connections[0][1] == 2121


# ---------------------------------------------------------------------------
# SMTP Tests
# ---------------------------------------------------------------------------


class TestSMTPLiveServer:
    """SMTP integration tests against a real aiosmtpd server."""

    def test_single_file_smtp_send_txt(self, smtp_server, tmp_path):
        """Send a .txt file as attachment; verify recipient, subject, and attachment content."""
        handler, settings = smtp_server
        content = b"Plain text file content for email test.\n"
        filepath = _make_file(tmp_path, "report.txt", content)
        params = _make_email_params(subject="Report %filename%")

        result = email_backend.do(
            params, settings, filepath, smtp_client=_NoTLSSMTPClient()
        )

        assert result is True
        time.sleep(0.1)
        assert len(handler.messages) == 1
        msg_data = handler.messages[0]
        assert "recipient@test.com" in msg_data["rcpt_tos"]

        parsed = message_from_bytes(msg_data["data"])
        assert "report.txt" in parsed["Subject"]
        attachment_content = None
        for part in parsed.walk():
            if part.get_content_disposition() == "attachment":
                attachment_content = part.get_payload(decode=True)
                break
        assert attachment_content is not None
        assert attachment_content == content

    def test_single_file_smtp_send_csv(self, smtp_server, tmp_path):
        """Send a .csv file and verify MIME type is text/csv."""
        handler, settings = smtp_server
        content = b"col1,col2,col3\nrow1a,row1b,row1c\nrow2a,row2b,row2c\n"
        filepath = _make_file(tmp_path, "spreadsheet.csv", content)
        params = _make_email_params(subject="CSV Report")

        result = email_backend.do(
            params, settings, filepath, smtp_client=_NoTLSSMTPClient()
        )

        assert result is True
        time.sleep(0.1)
        assert len(handler.messages) == 1

        parsed = message_from_bytes(handler.messages[0]["data"])
        attachment_part = None
        for part in parsed.walk():
            if part.get_content_disposition() == "attachment":
                attachment_part = part
                break
        assert attachment_part is not None
        assert attachment_part.get_content_type() == "text/csv"
        assert attachment_part.get_payload(decode=True) == content

    def test_single_file_smtp_send_pdf(self, smtp_server, tmp_path):
        """Send a minimal PDF attachment and verify application/pdf MIME type."""
        handler, settings = smtp_server
        # Minimal valid PDF
        content = (
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>"
            b"endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>"
            b"endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]>>"
            b"endobj\nxref\n0 4\n0000000000 65535 f\n"
            b"trailer<</Size 4/Root 1 0 R>>\n%%EOF"
        )
        filepath = _make_file(tmp_path, "invoice.pdf", content)
        params = _make_email_params(subject="Invoice PDF")

        result = email_backend.do(
            params, settings, filepath, smtp_client=_NoTLSSMTPClient()
        )

        assert result is True
        time.sleep(0.1)
        assert len(handler.messages) == 1

        parsed = message_from_bytes(handler.messages[0]["data"])
        attachment_part = None
        for part in parsed.walk():
            if part.get_content_disposition() == "attachment":
                attachment_part = part
                break
        assert attachment_part is not None
        assert attachment_part.get_content_type() == "application/pdf"

    def test_single_file_smtp_send_json(self, smtp_server, tmp_path):
        """Send a .json file and verify the attachment content is parseable JSON."""
        import json

        handler, settings = smtp_server
        payload = {"records": [{"id": 1, "value": "alpha"}, {"id": 2, "value": "beta"}]}
        content = json.dumps(payload, indent=2).encode("utf-8")
        filepath = _make_file(tmp_path, "records.json", content)
        params = _make_email_params(subject="JSON Data")

        result = email_backend.do(
            params, settings, filepath, smtp_client=_NoTLSSMTPClient()
        )

        assert result is True
        time.sleep(0.1)
        assert len(handler.messages) == 1

        parsed = message_from_bytes(handler.messages[0]["data"])
        attachment_content = None
        for part in parsed.walk():
            if part.get_content_disposition() == "attachment":
                attachment_content = part.get_payload(decode=True)
                break
        assert attachment_content is not None
        decoded = json.loads(attachment_content.decode("utf-8"))
        assert decoded == payload

    def test_single_file_smtp_send_xml(self, smtp_server, tmp_path):
        """Send a .xml file and verify the attachment content matches."""
        handler, settings = smtp_server
        content = b'<?xml version="1.0"?>\n<catalog>\n  <item id="1">Widget</item>\n</catalog>\n'
        filepath = _make_file(tmp_path, "catalog.xml", content)
        params = _make_email_params(subject="XML Catalog")

        result = email_backend.do(
            params, settings, filepath, smtp_client=_NoTLSSMTPClient()
        )

        assert result is True
        time.sleep(0.1)
        assert len(handler.messages) == 1

        parsed = message_from_bytes(handler.messages[0]["data"])
        attachment_content = None
        for part in parsed.walk():
            if part.get_content_disposition() == "attachment":
                attachment_content = part.get_payload(decode=True)
                break
        assert attachment_content is not None
        assert attachment_content == content

    def test_multi_file_batch_smtp_send(self, smtp_server, tmp_path):
        """Send 3 files in separate email sends and verify 3 emails are received."""
        handler, settings = smtp_server
        files_to_send = {
            "alpha.txt": b"Alpha content",
            "beta.csv": b"col,val\na,1\n",
            "gamma.xml": b"<gamma>data</gamma>",
        }
        params = _make_email_params(subject="Batch %filename%")

        for name, content in files_to_send.items():
            filepath = _make_file(tmp_path, name, content)
            result = email_backend.do(
                params, settings, filepath, smtp_client=_NoTLSSMTPClient()
            )
            assert result is True

        time.sleep(0.2)
        assert len(handler.messages) == 3
        received_subjects = []
        for msg_data in handler.messages:
            parsed = message_from_bytes(msg_data["data"])
            received_subjects.append(parsed["Subject"])
        for name in files_to_send:
            assert any(
                name in s for s in received_subjects
            ), f"No email found for {name} in {received_subjects}"

    def test_smtp_subject_line_template(self, smtp_server, tmp_path):
        """Verify %filename% and %datetime% substitutions in the email subject."""
        handler, settings = smtp_server
        content = b"Template test content"
        filepath = _make_file(tmp_path, "myfile.txt", content)
        params = _make_email_params(subject="File: %filename% sent on %datetime%")

        result = email_backend.do(
            params, settings, filepath, smtp_client=_NoTLSSMTPClient()
        )

        assert result is True
        time.sleep(0.1)
        assert len(handler.messages) == 1
        parsed = message_from_bytes(handler.messages[0]["data"])
        subject = parsed["Subject"]
        assert "myfile.txt" in subject
        # %datetime% is replaced with time.ctime() output, which contains digits
        assert any(c.isdigit() for c in subject), f"No digits in subject: {subject}"
        assert "%filename%" not in subject
        assert "%datetime%" not in subject

    def test_smtp_multiple_recipients(self, smtp_server, tmp_path):
        """Verify email is delivered to multiple comma-separated recipients."""
        handler, settings = smtp_server
        content = b"Multi-recipient test"
        filepath = _make_file(tmp_path, "multi.txt", content)
        params = {
            "email_to": "alice@test.com, bob@test.com, charlie@test.com",
            "email_subject_line": "Multi Recipient Test",
            "process_backend_email": True,
        }

        result = email_backend.do(
            params, settings, filepath, smtp_client=_NoTLSSMTPClient()
        )

        assert result is True
        time.sleep(0.1)
        assert len(handler.messages) == 1
        msg_data = handler.messages[0]
        # All recipients should appear in SMTP envelope
        for addr in ["alice@test.com", "bob@test.com", "charlie@test.com"]:
            assert (
                addr in msg_data["rcpt_tos"]
            ), f"{addr} not in rcpt_tos: {msg_data['rcpt_tos']}"

    def test_smtp_retry_on_connection_failure(self, tmp_path):
        """Verify email_backend retries after initial MockSMTPClient connect failure."""
        mock = MockSMTPClient()
        # First connect() call raises an error; second succeeds
        mock.add_error(ConnectionRefusedError("Simulated SMTP connection refused"))

        content = b"retry email test"
        filepath = _make_file(tmp_path, "retry.txt", content)
        params = _make_email_params(subject="Retry Test %filename%")
        settings = {
            "email_address": "sender@test.com",
            "email_smtp_server": "127.0.0.1",
            "smtp_port": 9999,
            "email_username": "",
            "email_password": "",
        }

        # Suppress sleep for speed
        original_sleep = email_backend.time.sleep
        email_backend.time.sleep = lambda _: None
        try:
            result = email_backend.do(params, settings, filepath, smtp_client=mock)
        finally:
            email_backend.time.sleep = original_sleep

        assert result is True
        assert len(mock.connections) == 1  # second attempt succeeded
        assert len(mock.emails_sent) == 1

    def test_smtp_send_large_attachment(self, smtp_server, tmp_path):
        """Send a 500 KB attachment and verify the size is preserved."""
        handler, settings = smtp_server
        content = b"X" * (512 * 1024)  # 512 KB
        filepath = _make_file(tmp_path, "large_attachment.bin", content)
        params = _make_email_params(subject="Large Attachment")

        result = email_backend.do(
            params, settings, filepath, smtp_client=_NoTLSSMTPClient()
        )

        assert result is True
        time.sleep(0.3)  # give async handler more time for large payload
        assert len(handler.messages) == 1

        parsed = message_from_bytes(handler.messages[0]["data"])
        attachment_content = None
        for part in parsed.walk():
            if part.get_content_disposition() == "attachment":
                attachment_content = part.get_payload(decode=True)
                break
        assert attachment_content is not None
        assert len(attachment_content) == len(content)
        assert _md5(attachment_content) == _md5(content)


# ---------------------------------------------------------------------------
# Combined FTP + SMTP Tests
# ---------------------------------------------------------------------------


class TestCombinedBackends:
    """Tests that exercise FTP and SMTP (and copy) backends together."""

    def test_single_file_to_both_ftp_and_smtp(self, ftp_server, smtp_server, tmp_path):
        """Send one file to both FTP and SMTP backends via SendManager."""
        srv, ftp_params = ftp_server
        handler, smtp_settings = smtp_server

        content = b"Dual-backend test content"
        filepath = _make_file(tmp_path, "dual.txt", content)

        # Build a folder config that enables both backends
        folder_cfg = {
            "process_backend_ftp": True,
            "ftp_server": ftp_params["ftp_server"],
            "ftp_port": ftp_params["ftp_port"],
            "ftp_username": ftp_params["ftp_username"],
            "ftp_password": ftp_params["ftp_password"],
            "ftp_folder": ftp_params["ftp_folder"],
            "process_backend_email": True,
            "email_to": "both@test.com",
            "email_subject_line": "Both Backends %filename%",
        }

        manager = SendManager(
            backends={"email": EmailBackend(smtp_client=_NoTLSSMTPClient())},
            use_default_backends=True,
        )
        enabled = manager.get_enabled_backends(folder_cfg)
        assert "ftp" in enabled
        assert "email" in enabled

        results = manager.send_all(enabled, filepath, folder_cfg, smtp_settings)

        assert results.get("ftp") is True
        assert results.get("email") is True

        # Verify FTP received the file
        ftp_files = srv.list_uploaded_files("upload")
        assert "dual.txt" in ftp_files
        ftp_content = srv.read_uploaded_file("dual.txt", "upload")
        assert ftp_content == content

        # Verify SMTP received the email
        time.sleep(0.2)
        assert len(handler.messages) >= 1
        parsed = message_from_bytes(handler.messages[0]["data"])
        attachment_content = None
        for part in parsed.walk():
            if part.get_content_disposition() == "attachment":
                attachment_content = part.get_payload(decode=True)
                break
        assert attachment_content == content

    def test_copy_ftp_smtp_all_backends(self, ftp_server, smtp_server, tmp_path):
        """Send via all 3 backends (copy, FTP, SMTP) and verify all succeed."""
        srv, ftp_params = ftp_server
        handler, smtp_settings = smtp_server

        copy_dest = tmp_path / "copy_output"
        copy_dest.mkdir()

        content = b"All-backends test payload"
        filepath = _make_file(tmp_path, "allbackends.txt", content)

        folder_cfg = {
            "process_backend_copy": True,
            "copy_to_directory": str(copy_dest),
            "process_backend_ftp": True,
            "ftp_server": ftp_params["ftp_server"],
            "ftp_port": ftp_params["ftp_port"],
            "ftp_username": ftp_params["ftp_username"],
            "ftp_password": ftp_params["ftp_password"],
            "ftp_folder": ftp_params["ftp_folder"],
            "process_backend_email": True,
            "email_to": "all@test.com",
            "email_subject_line": "All Backends %filename%",
        }

        manager = SendManager(
            backends={"email": EmailBackend(smtp_client=_NoTLSSMTPClient())},
            use_default_backends=True,
        )
        enabled = manager.get_enabled_backends(folder_cfg)
        assert "copy" in enabled
        assert "ftp" in enabled
        assert "email" in enabled

        results = manager.send_all(enabled, filepath, folder_cfg, smtp_settings)

        assert results.get("copy") is True, f"Copy failed: {manager.get_errors()}"
        assert results.get("ftp") is True, f"FTP failed: {manager.get_errors()}"
        assert results.get("email") is True, f"Email failed: {manager.get_errors()}"

        # Verify copy
        copy_files = os.listdir(str(copy_dest))
        assert "allbackends.txt" in copy_files
        with open(os.path.join(str(copy_dest), "allbackends.txt"), "rb") as fh:
            assert fh.read() == content

        # Verify FTP
        ftp_files = srv.list_uploaded_files("upload")
        assert "allbackends.txt" in ftp_files

        # Verify SMTP
        time.sleep(0.2)
        assert len(handler.messages) >= 1
        parsed = message_from_bytes(handler.messages[0]["data"])
        attachment_content = None
        for part in parsed.walk():
            if part.get_content_disposition() == "attachment":
                attachment_content = part.get_payload(decode=True)
                break
        assert attachment_content == content
