"""Integration tests for file format integrity via mock FTP and SMTP clients.

Verifies that files sent via ftp_backend.do() / email_backend.do() using
MockFTPClient / MockSMTPClient arrive with byte-exact content, correct MIME
types, and valid structure (parseable JSON / well-formed XML / valid ZIP).
"""

import hashlib
import io
import json
import xml.etree.ElementTree as ET
import zipfile
from typing import Optional

import pytest

from backend import email_backend, ftp_backend
from backend.ftp_client import MockFTPClient
from backend.smtp_client import MockSMTPClient
from dispatch.send_manager import MockBackend, SendManager

pytestmark = [pytest.mark.integration, pytest.mark.backend]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def _make_file(tmp_path, name: str, content: bytes) -> str:
    """Write *content* to *tmp_path/name* and return the absolute path."""
    p = tmp_path / name
    p.write_bytes(content)
    return str(p)


def _default_ftp_params(folder: str = "/") -> dict:
    return {
        "ftp_server": "127.0.0.1",
        "ftp_port": 21,
        "ftp_username": "testuser",
        "ftp_password": "testpass",
        "ftp_folder": folder,
        "process_backend_ftp": True,
    }


def _default_email_params(
    recipient: str = "recipient@test.com",
    subject: str = "Test %filename%",
) -> dict:
    return {
        "email_to": recipient,
        "email_subject_line": subject,
        "process_backend_email": True,
    }


def _default_smtp_settings() -> dict:
    return {
        "email_address": "sender@test.com",
        "email_smtp_server": "127.0.0.1",
        "smtp_port": 1025,
        "email_username": "",
        "email_password": "",
    }


def _send_via_ftp_mock(
    tmp_path, filename: str, content: bytes, folder: str = "/"
) -> MockFTPClient:
    """Send *content* via ftp_backend using a fresh MockFTPClient; return the mock."""
    mock = MockFTPClient()
    filepath = _make_file(tmp_path, filename, content)
    params = _default_ftp_params(folder)
    result = ftp_backend.do(params, {}, filepath, ftp_client=mock)
    assert result is True, "ftp_backend.do() returned False"
    return mock


def _send_via_smtp_mock(tmp_path, filename: str, content: bytes) -> MockSMTPClient:
    """Send *content* as an email attachment using a fresh MockSMTPClient; return the mock."""
    mock = MockSMTPClient()
    filepath = _make_file(tmp_path, filename, content)
    params = _default_email_params()
    settings = _default_smtp_settings()
    result = email_backend.do(params, settings, filepath, smtp_client=mock)
    assert result is True, "email_backend.do() returned False"
    return mock


def _extract_attachment(smtp_mock: MockSMTPClient, index: int = 0) -> Optional[bytes]:
    """Walk the EmailMessage object from *smtp_mock.emails_sent[index]* and return the first attachment's payload."""
    msg = smtp_mock.emails_sent[index]["msg"]
    for part in msg.walk():
        if part.get_content_disposition() == "attachment":
            return part.get_payload(decode=True)
    return None


# ---------------------------------------------------------------------------
# FTP content-integrity tests
# ---------------------------------------------------------------------------


class TestFTPContentIntegrity:
    """Verify byte-exact content delivery for various file types via MockFTPClient."""

    def test_transform_txt_no_transform(self, tmp_path):
        """Plain text file is sent as-is with no modification."""
        content = b"Line 1\nLine 2\nSpecial chars: \xe2\x80\x99\n"
        mock = _send_via_ftp_mock(tmp_path, "notes.txt", content)

        assert len(mock.files_sent) == 1
        _, received = mock.files_sent[0]
        assert received == content
        assert _md5(received) == _md5(content)

    def test_transform_csv_no_transform(self, tmp_path):
        """CSV file is sent with byte-exact checksum preservation."""
        rows = ["id,name,qty,price"]
        for i in range(50):
            rows.append(f"{i},item_{i},{i * 2},{i * 1.5:.2f}")
        content = "\n".join(rows).encode("utf-8") + b"\n"
        mock = _send_via_ftp_mock(tmp_path, "inventory.csv", content)

        assert len(mock.files_sent) == 1
        _, received = mock.files_sent[0]
        assert received == content
        assert _md5(received) == _md5(content)

    def test_transform_xml_no_transform(self, tmp_path):
        """XML file is sent with content identical to the source."""
        content = (
            b'<?xml version="1.0" encoding="UTF-8"?>\n'
            b"<orders>\n"
            b'  <order id="001"><item>Widget</item><qty>5</qty></order>\n'
            b'  <order id="002"><item>Gadget</item><qty>3</qty></order>\n'
            b"</orders>\n"
        )
        mock = _send_via_ftp_mock(tmp_path, "orders.xml", content)

        assert len(mock.files_sent) == 1
        _, received = mock.files_sent[0]
        assert received == content

    def test_transform_json_validation(self, tmp_path):
        """JSON file is sent as-is and the received bytes are parseable JSON."""
        payload = {
            "version": 2,
            "items": [
                {"sku": "A001", "qty": 10, "price": 19.99},
                {"sku": "B002", "qty": 5, "price": 34.50},
            ],
        }
        content = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
        mock = _send_via_ftp_mock(tmp_path, "payload.json", content)

        _, received = mock.files_sent[0]
        decoded = json.loads(received.decode("utf-8"))
        assert decoded == payload

    def test_transform_xml_validation(self, tmp_path):
        """XML file received via FTP is well-formed (parseable by ElementTree)."""
        content = (
            b'<?xml version="1.0"?>\n'
            b"<catalog>\n"
            b'  <product sku="P1" name="Alpha"/>\n'
            b'  <product sku="P2" name="Beta"/>\n'
            b"</catalog>\n"
        )
        mock = _send_via_ftp_mock(tmp_path, "catalog.xml", content)

        _, received = mock.files_sent[0]
        root = ET.fromstring(received)
        assert root.tag == "catalog"
        products = list(root)
        assert len(products) == 2
        assert products[0].attrib["sku"] == "P1"

    def test_send_zip_archive(self, tmp_path):
        """Zip archive is sent intact; re-opened archive contains expected member files."""
        buf = io.BytesIO()
        members = {
            "readme.txt": b"Read me first.",
            "data/report.csv": b"col1,col2\n1,2\n",
            "data/extra.json": b'{"x": 1}',
        }
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, data in members.items():
                zf.writestr(name, data)
        content = buf.getvalue()
        mock = _send_via_ftp_mock(tmp_path, "bundle.zip", content)

        _, received = mock.files_sent[0]
        assert received == content
        with zipfile.ZipFile(io.BytesIO(received)) as zf:
            assert set(zf.namelist()) == set(members.keys())
            for name, expected in members.items():
                assert zf.read(name) == expected

    def test_binary_blob_integrity(self, tmp_path):
        """Random binary data is transmitted without any byte corruption."""
        import random

        rng = random.Random(42)
        content = bytes(rng.getrandbits(8) for _ in range(4096))
        mock = _send_via_ftp_mock(tmp_path, "random.bin", content)

        _, received = mock.files_sent[0]
        assert received == content
        assert _md5(received) == _md5(content)

    def test_large_csv_file(self, tmp_path):
        """1000-row CSV is sent without truncation; row count matches."""
        rows = ["id,category,value,note"]
        for i in range(1000):
            rows.append(f"{i},cat_{i % 10},{i * 3.14:.4f},note_{i}")
        content = "\n".join(rows).encode("utf-8") + b"\n"
        mock = _send_via_ftp_mock(tmp_path, "big.csv", content)

        _, received = mock.files_sent[0]
        lines = received.decode("utf-8").splitlines()
        # header + 1000 data rows
        assert len(lines) == 1001
        assert lines[0] == "id,category,value,note"

    def test_filename_preserved(self, tmp_path):
        """The STOR FTP command carries the correct original filename."""
        content = b"filename check"
        target_name = "my_special_report_2026.dat"
        mock = _send_via_ftp_mock(tmp_path, target_name, content)

        assert len(mock.files_sent) == 1
        cmd, _ = mock.files_sent[0]
        # Command is like "stor my_special_report_2026.dat"
        assert target_name in cmd


# ---------------------------------------------------------------------------
# SMTP MIME-type tests
# ---------------------------------------------------------------------------


class TestSMTPMIMETypes:
    """Verify correct MIME types and content for various file types via MockSMTPClient."""

    def test_mime_type_txt(self, tmp_path):
        """Plain text file attachment has MIME type text/plain."""
        content = b"Simple plain text content\n"
        mock = _send_via_smtp_mock(tmp_path, "plain.txt", content)

        msg = mock.emails_sent[0]["msg"]
        attachment_part = None
        for part in msg.walk():
            if part.get_content_disposition() == "attachment":
                attachment_part = part
                break
        assert attachment_part is not None
        assert attachment_part.get_content_type() == "text/plain"
        assert attachment_part.get_payload(decode=True) == content

    def test_mime_type_csv(self, tmp_path):
        """CSV file attachment has MIME type text/csv."""
        content = b"header1,header2\nvalue1,value2\n"
        mock = _send_via_smtp_mock(tmp_path, "data.csv", content)

        msg = mock.emails_sent[0]["msg"]
        attachment_part = None
        for part in msg.walk():
            if part.get_content_disposition() == "attachment":
                attachment_part = part
                break
        assert attachment_part is not None
        assert attachment_part.get_content_type() == "text/csv"
        assert attachment_part.get_payload(decode=True) == content

    def test_mime_type_json(self, tmp_path):
        """JSON file attachment has a JSON-compatible MIME type."""
        content = b'{"test": true, "value": 42}\n'
        mock = _send_via_smtp_mock(tmp_path, "payload.json", content)

        msg = mock.emails_sent[0]["msg"]
        attachment_part = None
        for part in msg.walk():
            if part.get_content_disposition() == "attachment":
                attachment_part = part
                break
        assert attachment_part is not None
        ct = attachment_part.get_content_type()
        # Depending on the system's mimetypes DB this may be application/json or text/json
        assert "json" in ct, f"Expected 'json' in content-type, got: {ct}"
        assert attachment_part.get_payload(decode=True) == content

    def test_mime_type_xml(self, tmp_path):
        """XML file attachment has an XML-compatible MIME type."""
        content = b'<?xml version="1.0"?><root><a>1</a></root>'
        mock = _send_via_smtp_mock(tmp_path, "feed.xml", content)

        msg = mock.emails_sent[0]["msg"]
        attachment_part = None
        for part in msg.walk():
            if part.get_content_disposition() == "attachment":
                attachment_part = part
                break
        assert attachment_part is not None
        ct = attachment_part.get_content_type()
        assert "xml" in ct, f"Expected 'xml' in content-type, got: {ct}"
        assert attachment_part.get_payload(decode=True) == content

    def test_mime_type_pdf(self, tmp_path):
        """PDF file attachment has MIME type application/pdf."""
        # Minimal valid PDF header so mimetypes can identify it
        content = (
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>"
            b"endobj\ntrailer<</Root 1 0 R>>\n%%EOF"
        )
        mock = _send_via_smtp_mock(tmp_path, "document.pdf", content)

        msg = mock.emails_sent[0]["msg"]
        attachment_part = None
        for part in msg.walk():
            if part.get_content_disposition() == "attachment":
                attachment_part = part
                break
        assert attachment_part is not None
        assert attachment_part.get_content_type() == "application/pdf"

    def test_mime_type_zip(self, tmp_path):
        """ZIP file attachment has MIME type application/zip."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("inner.txt", "inner content")
        content = buf.getvalue()
        mock = _send_via_smtp_mock(tmp_path, "archive.zip", content)

        msg = mock.emails_sent[0]["msg"]
        attachment_part = None
        for part in msg.walk():
            if part.get_content_disposition() == "attachment":
                attachment_part = part
                break
        assert attachment_part is not None
        ct = attachment_part.get_content_type()
        assert "zip" in ct, f"Expected 'zip' in content-type, got: {ct}"


# ---------------------------------------------------------------------------
# SendManager + MockBackend tests
# ---------------------------------------------------------------------------


class TestSendManagerWithMockBackend:
    """Test the full SendManager → MockBackend path for various file formats."""

    @pytest.fixture()
    def mock_backend(self):
        return MockBackend(should_succeed=True)

    @pytest.fixture()
    def send_manager(self, mock_backend):
        return SendManager(backends={"mock": mock_backend})

    @pytest.fixture()
    def folder_cfg(self):
        """Folder config that enables the injected 'mock' backend."""
        return {
            "process_backend_ftp": False,
            "process_backend_email": False,
            "process_backend_copy": False,
        }

    def _send(self, send_manager, folder_cfg, tmp_path, name, content):
        filepath = _make_file(tmp_path, name, content)
        enabled = send_manager.get_enabled_backends(folder_cfg)
        results = send_manager.send_all(enabled, filepath, folder_cfg, {})
        return filepath, results

    def test_mock_backend_receives_txt(
        self, send_manager, mock_backend, folder_cfg, tmp_path
    ):
        """MockBackend receives txt file send call."""
        content = b"plain text"
        filepath, results = self._send(
            send_manager, folder_cfg, tmp_path, "file.txt", content
        )

        assert results.get("mock") is True
        assert len(mock_backend.send_calls) == 1
        _, _, fn = mock_backend.send_calls[0]
        assert fn == filepath

    def test_mock_backend_receives_csv(
        self, send_manager, mock_backend, folder_cfg, tmp_path
    ):
        """MockBackend receives csv file send call with correct path."""
        content = b"a,b\n1,2\n"
        filepath, results = self._send(
            send_manager, folder_cfg, tmp_path, "report.csv", content
        )

        assert results.get("mock") is True
        _, _, fn = mock_backend.send_calls[0]
        assert fn.endswith("report.csv")

    def test_mock_backend_receives_xml(
        self, send_manager, mock_backend, folder_cfg, tmp_path
    ):
        """MockBackend receives xml file send call."""
        content = b"<root/>"
        filepath, results = self._send(
            send_manager, folder_cfg, tmp_path, "data.xml", content
        )

        assert results.get("mock") is True
        assert len(mock_backend.send_calls) == 1

    def test_mock_backend_receives_json(
        self, send_manager, mock_backend, folder_cfg, tmp_path
    ):
        """MockBackend receives json file send call; file is parseable JSON."""
        payload = {"key": "value"}
        content = json.dumps(payload).encode("utf-8")
        filepath, results = self._send(
            send_manager, folder_cfg, tmp_path, "data.json", content
        )

        assert results.get("mock") is True
        # Verify the file actually contains valid JSON
        with open(filepath, "rb") as fh:
            assert json.loads(fh.read()) == payload

    def test_mock_backend_receives_binary(
        self, send_manager, mock_backend, folder_cfg, tmp_path
    ):
        """MockBackend receives binary file send call with correct path."""
        content = bytes(range(256))
        filepath, results = self._send(
            send_manager, folder_cfg, tmp_path, "blob.bin", content
        )

        assert results.get("mock") is True
        _, _, fn = mock_backend.send_calls[0]
        assert fn == filepath

    def test_mock_backend_receives_zip(
        self, send_manager, mock_backend, folder_cfg, tmp_path
    ):
        """MockBackend receives zip file; the file remains a valid zip archive."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("a.txt", "aaa")
        content = buf.getvalue()
        filepath, results = self._send(
            send_manager, folder_cfg, tmp_path, "pkg.zip", content
        )

        assert results.get("mock") is True
        with open(filepath, "rb") as fh:
            received = fh.read()
        with zipfile.ZipFile(io.BytesIO(received)) as zf:
            assert "a.txt" in zf.namelist()

    def test_mock_backend_receives_large_csv(
        self, send_manager, mock_backend, folder_cfg, tmp_path
    ):
        """1000-row CSV passes through MockBackend without row loss."""
        rows = ["id,val"]
        for i in range(1000):
            rows.append(f"{i},{i * 2}")
        content = "\n".join(rows).encode("utf-8")
        filepath, results = self._send(
            send_manager, folder_cfg, tmp_path, "large.csv", content
        )

        assert results.get("mock") is True
        with open(filepath, "rb") as fh:
            lines = fh.read().decode("utf-8").splitlines()
        assert len(lines) == 1001

    def test_mock_backend_binary_blob_integrity(
        self, send_manager, mock_backend, folder_cfg, tmp_path
    ):
        """Binary blob checksum is unchanged after passing through SendManager/MockBackend."""
        import random

        rng = random.Random(99)
        content = bytes(rng.getrandbits(8) for _ in range(8192))
        original_md5 = _md5(content)
        filepath, results = self._send(
            send_manager, folder_cfg, tmp_path, "rand.bin", content
        )

        assert results.get("mock") is True
        with open(filepath, "rb") as fh:
            assert _md5(fh.read()) == original_md5

    def test_filename_preserved_in_ftp_stor(self, tmp_path):
        """The STOR command sent to MockFTPClient carries the exact source filename."""
        target_name = "unique_filename_2026_q1.dat"
        content = b"stor filename check"
        mock = _send_via_ftp_mock(tmp_path, target_name, content)

        cmd, _ = mock.files_sent[0]
        assert target_name in cmd, f"Expected '{target_name}' in STOR cmd '{cmd}'"
