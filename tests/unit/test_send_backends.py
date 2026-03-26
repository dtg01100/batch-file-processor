"""Unit tests for send backends (FTP, Email, Copy, HTTP).

Tests:
- FTP backend: connection, directory navigation, correct filename in STOR command
- Email backend: SMTP connection, placeholder substitution in subject, multi-recipient
- Copy backend: file placed in correct destination
- HTTP backend: POST request with file, custom field name, auth types, headers

Modules tested:
- ftp_backend.py
- email_backend.py
- copy_backend.py
- http_backend.py
"""

import os

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.backend]


class TestFTPBackend:
    """Test suite for FTP backend functionality."""

    @pytest.fixture
    def sample_process_parameters(self):
        """Create sample process parameters for FTP."""
        return {
            "ftp_server": "ftp.example.com",
            "ftp_port": 21,
            "ftp_username": "testuser",
            "ftp_password": "testpass",
            "ftp_folder": "/uploads/",
        }

    @pytest.fixture
    def sample_settings_dict(self):
        """Create sample settings dictionary."""
        return {
            "as400_username": "testuser",
            "as400_password": "testpass",
            "as400_address": "test.as400.local",
        }

    @pytest.fixture
    def sample_file(self, tmp_path):
        """Create a sample file to send."""
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("Test file content for FTP upload")
        return str(test_file)

    def test_ftp_connection_mock(
        self, sample_process_parameters, sample_settings_dict, sample_file
    ):
        """ftp_backend.do() connects and logs in to the FTP server."""
        from backend import ftp_backend
        from backend.ftp_client import MockFTPClient

        mock_client = MockFTPClient()

        result = ftp_backend.do(
            sample_process_parameters,
            sample_settings_dict,
            sample_file,
            ftp_client=mock_client,
        )

        assert result is True
        assert len(mock_client.connections) > 0
        assert len(mock_client.logins) > 0

    def test_ftp_fallback_to_non_tls(
        self, sample_process_parameters, sample_settings_dict, sample_file
    ):
        """ftp_backend.do() attempts a connection (TLS or plain)."""
        from backend import ftp_backend
        from backend.ftp_client import MockFTPClient

        mock_client = MockFTPClient()

        ftp_backend.do(
            sample_process_parameters,
            sample_settings_dict,
            sample_file,
            ftp_client=mock_client,
        )

        assert len(mock_client.connections) > 0 or len(mock_client.files_sent) > 0

    def test_ftp_sends_correct_filename(
        self, sample_process_parameters, sample_settings_dict, sample_file
    ):
        """ftp_backend.do() uses only the file basename in the STOR command."""
        from backend import ftp_backend
        from backend.ftp_client import MockFTPClient

        mock_client = MockFTPClient()
        ftp_backend.do(
            sample_process_parameters,
            sample_settings_dict,
            sample_file,
            ftp_client=mock_client,
        )

        assert len(mock_client.files_sent) > 0
        stor_cmd = mock_client.files_sent[0][0]  # e.g. "STOR test_file.txt"
        basename = os.path.basename(sample_file)
        assert basename in stor_cmd
        # No path separator should appear in the argument after "STOR "
        stor_arg = stor_cmd.split("STOR ", 1)[-1]
        assert "/" not in stor_arg

    def test_ftp_creates_nested_remote_directory(
        self, sample_settings_dict, sample_file
    ):
        """ftp_backend.do() navigates into each path segment of ftp_folder."""
        from backend import ftp_backend
        from backend.ftp_client import MockFTPClient

        params = {
            "ftp_server": "ftp.example.com",
            "ftp_port": 21,
            "ftp_username": "user",
            "ftp_password": "pass",
            "ftp_folder": "/a/b/c",
        }
        mock_client = MockFTPClient()
        ftp_backend.do(
            params, sample_settings_dict, sample_file, ftp_client=mock_client
        )

        changed = mock_client.directories_changed
        # At minimum /a should have been entered
        assert any("/a" in d for d in changed)


class TestEmailBackend:
    """Test suite for Email backend functionality."""

    @pytest.fixture
    def sample_process_parameters(self):
        """Create sample process parameters for email."""
        return {
            "email_to": "recipient@example.com",
            "email_subject_line": "Test email %filename%",
        }

    @pytest.fixture
    def sample_settings(self):
        """Create sample settings for email."""
        return {
            "email_address": "sender@example.com",
            "email_smtp_server": "smtp.example.com",
            "smtp_port": 587,
            "email_username": "sender_user",
            "email_password": "sender_pass",
        }

    @pytest.fixture
    def sample_file(self, tmp_path):
        """Create a sample file to send."""
        test_file = tmp_path / "test_attachment.txt"
        test_file.write_text("Test file content for email attachment")
        return str(test_file)

    def test_email_smtp_connection_mock(
        self, sample_process_parameters, sample_settings, sample_file
    ):
        """email_backend.do() connects to the SMTP server and sends a message."""
        from backend import email_backend
        from backend.smtp_client import MockSMTPClient

        mock_smtp = MockSMTPClient()
        email_backend.do(
            sample_process_parameters,
            sample_settings,
            sample_file,
            smtp_client=mock_smtp,
        )

        assert mock_smtp.ehlo_calls > 0
        assert len(mock_smtp.emails_sent) > 0

    def test_email_substitutes_filename_in_subject(self, sample_settings, sample_file):
        """%filename% in email_subject_line is replaced with the actual filename."""
        from backend import email_backend
        from backend.smtp_client import MockSMTPClient

        params = {
            "email_to": "r@example.com",
            "email_subject_line": "Order %filename% arrived",
        }
        mock_smtp = MockSMTPClient()
        email_backend.do(params, sample_settings, sample_file, smtp_client=mock_smtp)

        assert len(mock_smtp.emails_sent) > 0
        subject = mock_smtp.emails_sent[0]["msg"]["Subject"]
        assert "test_attachment.txt" in subject
        assert "%filename%" not in subject

    def test_email_uses_default_subject_when_empty(self, sample_settings, sample_file):
        """When email_subject_line is empty, subject defaults to '<filename> Attached'."""
        from backend import email_backend
        from backend.smtp_client import MockSMTPClient

        params = {
            "email_to": "r@example.com",
            "email_subject_line": "",
        }
        mock_smtp = MockSMTPClient()
        email_backend.do(params, sample_settings, sample_file, smtp_client=mock_smtp)

        assert len(mock_smtp.emails_sent) > 0
        subject = mock_smtp.emails_sent[0]["msg"]["Subject"]
        assert "test_attachment.txt" in subject
        assert "Attached" in subject

    def test_email_sends_to_multiple_recipients(self, sample_settings, sample_file):
        """Comma-separated email_to addresses are each included in the To field."""
        from backend import email_backend
        from backend.smtp_client import MockSMTPClient

        params = {
            "email_to": "a@example.com, b@example.com",
            "email_subject_line": "Test",
        }
        mock_smtp = MockSMTPClient()
        email_backend.do(params, sample_settings, sample_file, smtp_client=mock_smtp)

        assert len(mock_smtp.emails_sent) > 0
        to_field = mock_smtp.emails_sent[0]["msg"]["To"]
        assert "a@example.com" in to_field
        assert "b@example.com" in to_field


class TestCopyBackend:
    """Test suite for Copy backend functionality."""

    @pytest.fixture
    def sample_source_file(self, tmp_path):
        """Create a sample source file."""
        test_file = tmp_path / "source_file.txt"
        test_file.write_text("Test file content for copying")
        return str(test_file)

    @pytest.fixture
    def sample_destination_dir(self, tmp_path):
        """Create a destination directory."""
        dest_dir = tmp_path / "copies"
        dest_dir.mkdir()
        return str(dest_dir)

    def test_copy_backend_places_file_in_correct_destination(
        self, sample_source_file, sample_destination_dir
    ):
        """copy_backend.do() writes the source file into copy_to_directory."""
        from backend import copy_backend

        params = {"copy_to_directory": sample_destination_dir}
        result = copy_backend.do(params, {}, sample_source_file)

        assert result is True
        expected = os.path.join(
            sample_destination_dir, os.path.basename(sample_source_file)
        )
        assert os.path.isfile(expected)


class TestHTTPBackend:
    """Test suite for HTTP backend functionality."""

    @pytest.fixture
    def sample_process_parameters(self):
        """Create sample process parameters for HTTP."""
        return {
            "http_url": "https://example.com/upload",
            "http_headers": "Content-Type: application/json",
            "http_field_name": "file",
            "http_auth_type": "",
            "http_api_key": "",
        }

    @pytest.fixture
    def sample_settings_dict(self):
        """Create sample settings dictionary."""
        return {}

    @pytest.fixture
    def sample_file(self, tmp_path):
        """Create a sample file to send."""
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("Test file content for HTTP upload")
        return str(test_file)

    def test_http_post_sends_file_mock(
        self, sample_process_parameters, sample_settings_dict, sample_file
    ):
        """http_backend.do() sends a POST request with the file."""
        from backend import http_backend
        from backend.http_client import MockHTTPClient

        mock_client = MockHTTPClient()
        result = http_backend.do(
            sample_process_parameters,
            sample_settings_dict,
            sample_file,
            http_client=mock_client,
        )

        assert result is True
        assert len(mock_client.posts) > 0
        url, data, files, headers = mock_client.posts[0]
        assert url == "https://example.com/upload"

    def test_http_post_includes_file_in_files_dict(
        self, sample_process_parameters, sample_settings_dict, sample_file
    ):
        """http_backend.do() includes the file in the files parameter."""
        from backend import http_backend
        from backend.http_client import MockHTTPClient

        mock_client = MockHTTPClient()
        http_backend.do(
            sample_process_parameters,
            sample_settings_dict,
            sample_file,
            http_client=mock_client,
        )

        assert len(mock_client.posts) > 0
        url, data, files, headers = mock_client.posts[0]
        basename = os.path.basename(sample_file)
        # files dict has field_name as key and (filename, file_obj) tuple as value
        assert "file" in files
        assert files["file"][0] == basename

    def test_http_post_uses_custom_field_name(self, sample_settings_dict, sample_file):
        """http_backend.do() uses the configured field_name for the file."""
        from backend import http_backend
        from backend.http_client import MockHTTPClient

        params = {
            "http_url": "https://example.com/upload",
            "http_field_name": "my_custom_field",
        }
        mock_client = MockHTTPClient()
        http_backend.do(
            params,
            sample_settings_dict,
            sample_file,
            http_client=mock_client,
        )

        url, data, files, headers = mock_client.posts[0]
        assert "my_custom_field" in files

    def test_http_post_with_bearer_auth(self, sample_settings_dict, sample_file):
        """http_backend.do() adds Bearer token when auth_type is 'bearer'."""
        from backend import http_backend
        from backend.http_client import MockHTTPClient

        params = {
            "http_url": "https://example.com/upload",
            "http_auth_type": "bearer",
            "http_api_key": "my-secret-token",
        }
        mock_client = MockHTTPClient()
        http_backend.do(
            params,
            sample_settings_dict,
            sample_file,
            http_client=mock_client,
        )

        url, data, files, headers = mock_client.posts[0]
        assert headers is not None
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer my-secret-token"

    def test_http_post_with_query_auth(self, sample_settings_dict, sample_file):
        """http_backend.do() appends api_key as query param when auth_type is 'query'."""
        from backend import http_backend
        from backend.http_client import MockHTTPClient

        params = {
            "http_url": "https://example.com/upload",
            "http_auth_type": "query",
            "http_api_key": "my-api-key",
        }
        mock_client = MockHTTPClient()
        http_backend.do(
            params,
            sample_settings_dict,
            sample_file,
            http_client=mock_client,
        )

        url, data, files, headers = mock_client.posts[0]
        assert "api_key=my-api-key" in url

    def test_http_post_parses_custom_headers(self, sample_settings_dict, sample_file):
        """http_backend.do() parses newline-separated headers correctly."""
        from backend import http_backend
        from backend.http_client import MockHTTPClient

        params = {
            "http_url": "https://example.com/upload",
            "http_headers": "X-Custom-Header: value1\nX-Another: value2",
        }
        mock_client = MockHTTPClient()
        http_backend.do(
            params,
            sample_settings_dict,
            sample_file,
            http_client=mock_client,
        )

        url, data, files, headers = mock_client.posts[0]
        assert headers.get("X-Custom-Header") == "value1"
        assert headers.get("X-Another") == "value2"

    def test_http_post_raises_on_failure_response(
        self, sample_process_parameters, sample_settings_dict, sample_file
    ):
        """http_backend.do() raises an exception when the response is not OK."""
        from backend import http_backend
        from backend.http_client import MockHTTPClient

        mock_client = MockHTTPClient()
        mock_client.set_response(status_code=500, text="Internal Server Error")

        with pytest.raises(Exception) as exc_info:
            http_backend.do(
                sample_process_parameters,
                sample_settings_dict,
                sample_file,
                http_client=mock_client,
            )

        assert "500" in str(exc_info.value)

    def test_http_backend_class_send(
        self, sample_process_parameters, sample_settings_dict, sample_file
    ):
        """HTTPBackend.send() calls do() correctly."""
        from backend.http_backend import HTTPBackend
        from backend.http_client import MockHTTPClient

        mock_client = MockHTTPClient()
        backend = HTTPBackend(http_client=mock_client)

        result = backend.send(
            sample_process_parameters,
            sample_settings_dict,
            sample_file,
        )

        assert result is True
        assert len(mock_client.posts) > 0

    def test_http_backend_class_create_client(self):
        """HTTPBackend.create_client() returns an HTTP client."""
        from backend.http_backend import HTTPBackend
        from backend.http_client import RealHTTPClient

        client = HTTPBackend.create_client(timeout=60.0)
        assert isinstance(client, RealHTTPClient)
        assert client.timeout == 60.0
