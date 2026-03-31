"""Integration tests using real EDI sample files from test_edi/.

Tests cover:
- File discovery and naming patterns
- EDI record parsing (A, B, C records)
- Validation via EDIValidationStep
- Splitting via EDISplitterStep
- FTP round-trip transport
- SMTP round-trip transport
- Structural integrity checks
"""

import ftplib
import io
import os
import re
import smtplib
import socket
import threading
import time
from email import encoders, message_from_bytes
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart

import pytest
try:
    from aiosmtpd.controller import Controller  # type: ignore
    AIOSMTPD_AVAILABLE = True
except Exception:
    AIOSMTPD_AVAILABLE = False
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

from core.edi.edi_parser import capture_records
from dispatch.pipeline.splitter import EDISplitterStep
from dispatch.pipeline.validator import EDIValidationStep

pytestmark = [pytest.mark.integration, pytest.mark.edi]

TEST_EDI_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "test_edi")


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _all_edi_files():
    """Return sorted list of all EDI file paths in TEST_EDI_DIR."""
    return sorted(
        os.path.join(TEST_EDI_DIR, f)
        for f in os.listdir(TEST_EDI_DIR)
        if os.path.isfile(os.path.join(TEST_EDI_DIR, f))
    )


def _edi_path(filename):
    return os.path.join(TEST_EDI_DIR, filename)


def _count_a_records(file_path):
    count = 0
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("A"):
                count += 1
    return count


# ---------------------------------------------------------------------------
# FTP fixtures and helpers
# ---------------------------------------------------------------------------


def _free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def live_ftp_server(tmp_path):
    root = str(tmp_path / "ftp_root")
    os.makedirs(root)
    port = _free_port()
    authorizer = DummyAuthorizer()
    authorizer.add_user("testuser", "testpass", root, perm="elradfmwMT")

    class _Handler(FTPHandler):
        pass

    _Handler.authorizer = authorizer
    _Handler.passive_ports = range(60000, 60100)
    server = FTPServer(("127.0.0.1", port), _Handler)
    t = threading.Thread(
        target=server.serve_forever,
        kwargs={"timeout": 0.5, "blocking": True},
        daemon=True,
    )
    t.start()
    time.sleep(0.05)
    yield ("127.0.0.1", port, root)
    server.close_all()


def _ftp_upload(host, port, filename, data: bytes):
    with ftplib.FTP() as ftp:
        ftp.connect(host, port, timeout=10)
        ftp.login("testuser", "testpass")
        ftp.storbinary(f"STOR {filename}", io.BytesIO(data))


def _ftp_read(host, port, filename) -> bytes:
    with ftplib.FTP() as ftp:
        ftp.connect(host, port, timeout=10)
        ftp.login("testuser", "testpass")
        buf = io.BytesIO()
        ftp.retrbinary(f"RETR {filename}", buf.write)
        return buf.getvalue()


# ---------------------------------------------------------------------------
# SMTP fixtures and helpers
# ---------------------------------------------------------------------------


class _RecordingHandler:
    def __init__(self):
        self.messages = []

    async def handle_DATA(self, server, session, envelope):
        self.messages.append(envelope)
        return "250 OK"


@pytest.fixture
def live_smtp_server():
    if not AIOSMTPD_AVAILABLE:
        pytest.skip("aiosmtpd not installed")
    handler = _RecordingHandler()
    port = _free_port()
    ctrl = Controller(handler, hostname="127.0.0.1", port=port)
    ctrl.start()
    yield ("127.0.0.1", port, handler)
    ctrl.stop()


def _smtp_send(host, port, subject, filename, data: bytes):
    msg = MIMEMultipart()
    msg["From"] = "sender@test.com"
    msg["To"] = "recv@test.com"
    msg["Subject"] = subject
    part = MIMEBase("application", "octet-stream")
    part.set_payload(data)
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
    msg.attach(part)
    with smtplib.SMTP(host, port, timeout=10) as s:
        s.send_message(msg)


# ===========================================================================
# 1. TestEDIFileDiscovery
# ===========================================================================


class TestEDIFileDiscovery:
    def test_edi_test_dir_exists(self):
        assert os.path.isdir(
            TEST_EDI_DIR
        ), f"test_edi directory not found: {TEST_EDI_DIR}"
        files = os.listdir(TEST_EDI_DIR)
        assert len(files) > 0, "test_edi directory is empty"

    def test_all_edi_files_are_readable(self):
        for file_path in _all_edi_files():
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            assert content is not None, f"Failed to read {file_path}"

    def test_edi_file_naming_pattern(self):
        for file_path in _all_edi_files():
            filename = os.path.basename(file_path)
            assert re.match(
                r"^\d{6}\.\d{3}$", filename
            ), f"File does not match naming pattern: {filename}"


# ===========================================================================
# 2. TestEDIFileParsing
# ===========================================================================


class TestEDIFileParsing:
    def test_all_files_start_with_a_record(self):
        for file_path in _all_edi_files():
            with open(file_path, "r", encoding="utf-8") as f:
                first_non_empty = None
                for line in f:
                    if line.strip():
                        first_non_empty = line
                        break
            assert first_non_empty is not None, f"File is empty: {file_path}"
            assert first_non_empty.startswith(
                "A"
            ), f"First non-empty line does not start with A: {file_path}"

    def test_a_record_field_widths(self):
        for file_path in _all_edi_files():
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.startswith("A"):
                        continue
                    record = capture_records(line)
                    assert record is not None
                    assert (
                        len(record["cust_vendor"]) == 6
                    ), f"cust_vendor wrong width in {file_path}: {record['cust_vendor']!r}"
                    assert (
                        len(record["invoice_number"]) == 10
                    ), f"invoice_number wrong width in {file_path}: {record['invoice_number']!r}"
                    assert (
                        len(record["invoice_date"]) == 6
                    ), f"invoice_date wrong width in {file_path}: {record['invoice_date']!r}"
                    assert (
                        len(record["invoice_total"]) == 10
                    ), f"invoice_total wrong width in {file_path}: {record['invoice_total']!r}"

    def test_b_record_field_widths(self):
        for file_path in _all_edi_files():
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.startswith("B"):
                        continue
                    record = capture_records(line)
                    assert record is not None
                    assert (
                        len(record["upc_number"]) == 11
                    ), f"upc_number wrong width in {file_path}: {record['upc_number']!r}"
                    assert (
                        len(record["description"]) == 25
                    ), f"description wrong width in {file_path}: {record['description']!r}"

    @pytest.mark.parametrize("filename", ["202002.003", "202002.006"])
    def test_negative_invoice_totals(self, filename):
        file_path = _edi_path(filename)
        a_record = None
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("A"):
                    a_record = capture_records(line)
                    break
        assert a_record is not None, f"No A record found in {filename}"
        assert a_record["invoice_total"].startswith(
            "-"
        ), f"Expected negative invoice_total in {filename}: {a_record['invoice_total']!r}"

    @pytest.mark.parametrize("filename", ["202006.003", "202007.001"])
    def test_multi_invoice_files(self, filename):
        file_path = _edi_path(filename)
        count = _count_a_records(file_path)
        assert count >= 2, f"Expected >= 2 A records in {filename}, got {count}"


# ===========================================================================
# 3. TestEDIValidation
# ===========================================================================


class TestEDIValidation:
    def test_all_sample_files_pass_validation(self):
        step = EDIValidationStep()
        failures = []
        for file_path in _all_edi_files():
            filename = os.path.basename(file_path)
            result = step.validate(file_path, filename)
            if not result.is_valid:
                failures.append(f"{filename}: {result.errors}")
        assert failures == [], f"Validation failures: {failures}"

    def test_validation_result_has_no_blocking_errors(self):
        step = EDIValidationStep()
        for file_path in _all_edi_files():
            filename = os.path.basename(file_path)
            result = step.validate(file_path, filename)
            assert (
                result.errors == []
            ), f"Unexpected blocking errors for {filename}: {result.errors}"

    def test_small_file_validates(self):
        file_path = _edi_path("351018.004")
        step = EDIValidationStep()
        result = step.validate(file_path, "351018.004")
        assert (
            result.is_valid
        ), f"Expected 351018.004 to be valid, errors: {result.errors}"

    def test_large_file_validates(self):
        all_files = _all_edi_files()
        largest = max(all_files, key=os.path.getsize)
        filename = os.path.basename(largest)
        step = EDIValidationStep()
        result = step.validate(largest, filename)
        assert (
            result.is_valid
        ), f"Expected largest file {filename} to be valid, errors: {result.errors}"

    @pytest.mark.parametrize("filename", ["202002.003", "202002.006"])
    def test_negative_amount_files_validate(self, filename):
        file_path = _edi_path(filename)
        step = EDIValidationStep()
        result = step.validate(file_path, filename)
        assert (
            result.is_valid is True
        ), f"Expected {filename} to be valid, errors: {result.errors}"

    @pytest.mark.parametrize("filename", ["202006.003", "202007.001"])
    def test_multi_invoice_files_validate(self, filename):
        file_path = _edi_path(filename)
        step = EDIValidationStep()
        result = step.validate(file_path, filename)
        assert (
            result.is_valid is True
        ), f"Expected {filename} to be valid, errors: {result.errors}"


# ===========================================================================
# 4. TestEDIFileSplitting
# ===========================================================================


class TestEDIFileSplitting:
    def test_single_invoice_file_not_split(self, tmp_path):
        input_path = _edi_path("202001.001")
        step = EDISplitterStep()
        result = step.split(input_path, str(tmp_path), {"split_edi": True}, {})
        assert result.was_split is True, "Single-invoice file should be marked as split"
        assert len(result.files) == 1, f"Expected 1 file, got {len(result.files)}"

    def test_multi_invoice_file_is_split(self, tmp_path):
        input_path = _edi_path("202007.001")
        step = EDISplitterStep()
        result = step.split(input_path, str(tmp_path), {"split_edi": True}, {})
        assert result.was_split is True, "Multi-invoice file should have been split"
        assert len(result.files) >= 2, f"Expected >= 2 files, got {len(result.files)}"

    def test_split_files_exist_on_disk(self, tmp_path):
        input_path = _edi_path("202007.001")
        step = EDISplitterStep()
        result = step.split(input_path, str(tmp_path), {"split_edi": True}, {})
        for file_path, _prefix, _suffix in result.files:
            assert os.path.isfile(
                file_path
            ), f"Split output file not found on disk: {file_path}"

    def test_split_files_each_have_one_a_record(self, tmp_path):
        input_path = _edi_path("202007.001")
        step = EDISplitterStep()
        result = step.split(input_path, str(tmp_path), {"split_edi": True}, {})
        for file_path, _prefix, _suffix in result.files:
            count = _count_a_records(file_path)
            assert (
                count == 1
            ), f"Expected exactly 1 A record in {file_path}, got {count}"

    def test_no_split_returns_original_path(self, tmp_path):
        input_path = _edi_path("202001.001")
        step = EDISplitterStep()
        result = step.split(input_path, str(tmp_path), {"split_edi": False}, {})
        assert (
            result.files[0][0] == input_path
        ), f"Expected original path {input_path!r}, got {result.files[0][0]!r}"


# ===========================================================================
# 5. TestEDIFTPTransport
# ===========================================================================


class TestEDIFTPTransport:
    def test_raw_edi_file_upload_via_ftp(self, live_ftp_server):
        host, port, _root = live_ftp_server
        file_path = _edi_path("202001.001")
        with open(file_path, "rb") as f:
            original_bytes = f.read()
        _ftp_upload(host, port, "202001.001", original_bytes)
        downloaded = _ftp_read(host, port, "202001.001")
        assert downloaded == original_bytes, "Downloaded bytes differ from original"

    def test_all_group_representative_files_upload(self, live_ftp_server):
        host, port, _root = live_ftp_server
        edi_files = os.listdir(TEST_EDI_DIR)
        # Pick one file from each group prefix
        groups = {}
        for f in edi_files:
            if os.path.isfile(os.path.join(TEST_EDI_DIR, f)):
                prefix = f.split(".")[0]
                if prefix not in groups:
                    groups[prefix] = f
        uploaded_names = []
        for _prefix, filename in sorted(groups.items()):
            file_path = os.path.join(TEST_EDI_DIR, filename)
            with open(file_path, "rb") as fh:
                data = fh.read()
            _ftp_upload(host, port, filename, data)
            uploaded_names.append(filename)
        # Verify all uploaded names are listed
        with ftplib.FTP() as ftp:
            ftp.connect(host, port, timeout=10)
            ftp.login("testuser", "testpass")
            listed = ftp.nlst()
        for name in uploaded_names:
            assert name in listed, f"Uploaded file {name!r} not found in FTP listing"

    def test_negative_amount_file_ftp_roundtrip(self, live_ftp_server):
        host, port, _root = live_ftp_server
        file_path = _edi_path("202002.003")
        with open(file_path, "rb") as f:
            original_bytes = f.read()
        _ftp_upload(host, port, "202002.003", original_bytes)
        downloaded = _ftp_read(host, port, "202002.003")
        text = downloaded.decode("utf-8")
        a_record_line = None
        for line in text.splitlines():
            if line.startswith("A"):
                a_record_line = line
                break
        assert a_record_line is not None, "No A record found in downloaded file"
        invoice_total = a_record_line[23:33]
        assert invoice_total.startswith(
            "-"
        ), f"Expected negative invoice_total, got: {invoice_total!r}"

    def test_multi_invoice_file_ftp_roundtrip(self, live_ftp_server):
        host, port, _root = live_ftp_server
        file_path = _edi_path("202007.001")
        with open(file_path, "rb") as f:
            original_bytes = f.read()
        _ftp_upload(host, port, "202007.001", original_bytes)
        downloaded = _ftp_read(host, port, "202007.001")
        text = downloaded.decode("utf-8")
        a_count = sum(1 for line in text.splitlines() if line.startswith("A"))
        assert (
            a_count >= 2
        ), f"Expected >= 2 A records in downloaded file, got {a_count}"


# ===========================================================================
# 6. TestEDISMTPTransport
# ===========================================================================


class TestEDISMTPTransport:
    def test_raw_edi_file_send_via_smtp(self, live_smtp_server):
        host, port, handler = live_smtp_server
        file_path = _edi_path("202001.001")
        with open(file_path, "rb") as f:
            original_bytes = f.read()
        _smtp_send(host, port, "Test EDI", "202001.001", original_bytes)
        time.sleep(0.1)
        assert (
            len(handler.messages) == 1
        ), f"Expected 1 message, got {len(handler.messages)}"
        envelope = handler.messages[0]
        msg = message_from_bytes(envelope.content)
        attachment_data = None
        for part in msg.walk():
            if part.get_content_disposition() == "attachment":
                attachment_data = part.get_payload(decode=True)
        assert attachment_data is not None, "No attachment found in received message"
        assert (
            attachment_data == original_bytes
        ), "Attachment bytes differ from original"

    def test_smtp_attachment_filename_preserved(self, live_smtp_server):
        host, port, handler = live_smtp_server
        file_path = _edi_path("202001.001")
        with open(file_path, "rb") as f:
            data = f.read()
        _smtp_send(host, port, "Test EDI Filename", "202001.001", data)
        time.sleep(0.1)
        assert len(handler.messages) >= 1
        envelope = handler.messages[0]
        msg = message_from_bytes(envelope.content)
        attachment_name = None
        for part in msg.walk():
            if part.get_content_disposition() == "attachment":
                attachment_name = part.get_filename()
        assert (
            attachment_name == "202001.001"
        ), f"Expected filename '202001.001', got {attachment_name!r}"

    def test_smtp_multi_attachment(self, live_smtp_server):
        host, port, handler = live_smtp_server
        filenames = ["202001.001", "202002.001", "202003.001"]
        for filename in filenames:
            file_path = _edi_path(filename)
            with open(file_path, "rb") as f:
                data = f.read()
            _smtp_send(host, port, f"EDI {filename}", filename, data)
        time.sleep(0.2)
        assert (
            len(handler.messages) == 3
        ), f"Expected 3 messages, got {len(handler.messages)}"

    def test_negative_amount_file_smtp_roundtrip(self, live_smtp_server):
        host, port, handler = live_smtp_server
        file_path = _edi_path("202002.006")
        with open(file_path, "rb") as f:
            original_bytes = f.read()
        _smtp_send(host, port, "Test Negative EDI", "202002.006", original_bytes)
        time.sleep(0.1)
        assert len(handler.messages) >= 1
        envelope = handler.messages[0]
        msg = message_from_bytes(envelope.content)
        attachment_data = None
        for part in msg.walk():
            if part.get_content_disposition() == "attachment":
                attachment_data = part.get_payload(decode=True)
        assert attachment_data is not None
        text = attachment_data.decode("utf-8")
        a_line = None
        for line in text.splitlines():
            if line.startswith("A"):
                a_line = line
                break
        assert a_line is not None, "No A record found in SMTP attachment"
        assert a_line[23:33].startswith(
            "-"
        ), f"Expected negative invoice_total field, got: {a_line[23:33]!r}"


# ===========================================================================
# 7. TestEDIStructuralIntegrity
# ===========================================================================


class TestEDIStructuralIntegrity:
    def test_all_lines_start_with_valid_record_type(self):
        violations = []
        for file_path in _all_edi_files():
            filename = os.path.basename(file_path)
            with open(file_path, "r", encoding="utf-8") as f:
                for lineno, line in enumerate(f, start=1):
                    if not line.strip():
                        continue
                    if line.strip() == "\x1a":
                        continue
                    if line[0] not in ("A", "B", "C"):
                        violations.append(
                            f"{filename}:{lineno}: invalid record type {line[0]!r}"
                        )
        assert violations == [], f"Lines with invalid record types: {violations}"

    def test_invoice_total_is_numeric(self):
        for file_path in _all_edi_files():
            filename = os.path.basename(file_path)
            with open(file_path, "r", encoding="utf-8") as f:
                for lineno, line in enumerate(f, start=1):
                    if not line.startswith("A"):
                        continue
                    record = capture_records(line)
                    if record is None:
                        continue
                    invoice_total = record["invoice_total"]
                    stripped = invoice_total.strip().lstrip("-")
                    assert stripped.isdigit(), (
                        f"{filename}:{lineno}: invoice_total is not numeric: "
                        f"{invoice_total!r}"
                    )

    def test_b_record_line_lengths(self):
        violations = []
        for file_path in _all_edi_files():
            filename = os.path.basename(file_path)
            with open(file_path, "r", encoding="utf-8") as f:
                for lineno, line in enumerate(f, start=1):
                    if not line.startswith("B"):
                        continue
                    stripped_len = len(line.rstrip("\n\r"))
                    if stripped_len not in (76, 70):
                        violations.append(
                            f"{filename}:{lineno}: B record length {stripped_len} not in {{76, 70}}"
                        )
        assert violations == [], f"B record line length violations: {violations}"

    def test_no_b_record_shorter_than_70(self):
        violations = []
        for file_path in _all_edi_files():
            filename = os.path.basename(file_path)
            with open(file_path, "r", encoding="utf-8") as f:
                for lineno, line in enumerate(f, start=1):
                    if not line.startswith("B"):
                        continue
                    stripped_len = len(line.rstrip("\n\r"))
                    if stripped_len < 70:
                        violations.append(
                            f"{filename}:{lineno}: B record shorter than 70 chars ({stripped_len})"
                        )
        assert violations == [], f"Short B record violations: {violations}"

    def test_files_end_with_newline_or_ctrl_z(self):
        for file_path in _all_edi_files():
            filename = os.path.basename(file_path)
            with open(file_path, "rb") as f:
                content = f.read()
            assert content, f"File is empty: {filename}"
            assert (
                content.endswith(b"\n")
                or content.endswith(b"\r\n")
                or content.endswith(b"\x1a")
            ), f"File does not end with newline or ctrl-z: {filename}"
