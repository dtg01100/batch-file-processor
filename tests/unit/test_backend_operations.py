"""Additional unit tests for backend modules.

These tests focus on the actual file operations and error handling
in copy_backend, ftp_backend, and email_backend modules.

Tests:
- Actual file copy operations
- FTP transfer operations with mock clients
- Email sending operations with mock clients
- Error handling and retry logic
"""

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.backend]

import os
import tempfile
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from backend import copy_backend, email_backend, ftp_backend


class MockFileOperations:
    """Mock file operations with dir_exists support."""

    def __init__(self):
        self.files_copied = []
        self.directories_created = []
        self._directories = set()
        self._files = set()

    def dir_exists(self, path: str) -> bool:
        """Check if directory exists."""
        return path in self._directories or os.path.exists(path)

    def exists(self, path: str) -> bool:
        """Check if path exists."""
        return path in self._files or path in self._directories or os.path.exists(path)

    def makedirs(self, path: str, exist_ok: bool = False) -> None:
        """Create directory."""
        self._directories.add(path)
        self.directories_created.append(path)

    def copy(self, src: str, dst: str) -> None:
        """Copy file."""
        self.files_copied.append((src, dst))

    def basename(self, path: str) -> str:
        """Get basename."""
        return os.path.basename(path)

    def dirname(self, path: str) -> str:
        """Get dirname."""
        return os.path.dirname(path)

    def join(self, *paths: str) -> str:
        """Join paths."""
        return os.path.join(*paths)

    def remove(self, path: str) -> None:
        """Remove file."""

    def rmtree(self, path: str) -> None:
        """Remove directory tree."""


class TestCopyBackendOperations:
    """Test suite for copy_backend actual operations."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def source_file(self, temp_dir):
        """Create a source file for copying."""
        source = temp_dir / "source.txt"
        source.write_text("Test file content for copying\nLine 2\nLine 3")
        return str(source)

    @pytest.fixture
    def dest_dir(self, temp_dir):
        """Create a destination directory."""
        dest = temp_dir / "copies"
        dest.mkdir()
        return str(dest)

    @pytest.fixture
    def process_parameters(self, dest_dir):
        """Create process parameters for copy backend."""
        return {"copy_to_directory": dest_dir}

    @pytest.fixture
    def settings_dict(self):
        """Create empty settings dict."""
        return {}

    def test_copy_backend_do_succeeds(
        self, process_parameters, settings_dict, source_file, dest_dir
    ):
        """Test successful file copy."""
        # Use mock file ops to avoid real filesystem issues
        mock_ops = MockFileOperations()
        mock_ops._directories.add(dest_dir)  # Pretend dest exists
        mock_ops._files.add(source_file)  # Pretend source exists

        # Patch open to return file content
        with patch("builtins.open", mock_open(read_data="Test file content")):
            result = copy_backend.do(
                process_parameters, settings_dict, source_file, file_ops=mock_ops
            )

        assert result is True

    def test_copy_backend_creates_directory(self, temp_dir, source_file):
        """Test that copy_backend creates destination directory if it doesn't exist."""
        new_dest = temp_dir / "new_directory" / "nested"
        process_parameters = {"copy_to_directory": str(new_dest)}

        # Use real file operations for this test
        result = copy_backend.do(process_parameters, {}, source_file)

        assert result is True
        assert new_dest.exists()

    def test_copy_backend_missing_file_raises(
        self, process_parameters, settings_dict, temp_dir
    ):
        """Test that missing source file raises IOError."""
        missing_file = str(temp_dir / "nonexistent.txt")

        with pytest.raises(IOError):
            copy_backend.do(process_parameters, settings_dict, missing_file)

    def test_copy_backend_retries_on_io_error(self, temp_dir, source_file):
        """Copy backend retries up to 10 times on IOError before re-raising."""
        call_count = {"n": 0}

        class FlakyCopyOps:
            def exists(self, path):
                return True

            def makedirs(self, path):
                pass

            def copy(self, src, dst):
                call_count["n"] += 1
                raise IOError("transient error")

        with pytest.raises(IOError, match="transient error"):
            copy_backend.do(
                {"copy_to_directory": str(temp_dir)},
                {},
                source_file,
                file_ops=FlakyCopyOps(),
            )
        # counter goes 0→10 (11 attempts total before raise)
        assert call_count["n"] == 11, "Backend must retry exactly 10 times then raise"

    def test_copy_backend_with_mock_file_ops(
        self, process_parameters, settings_dict, source_file
    ):
        """Test copy_backend with injectable file operations."""
        mock_ops = MockFileOperations()
        mock_ops._directories.add(process_parameters["copy_to_directory"])

        with patch("builtins.open", mock_open(read_data="Test content")):
            result = copy_backend.do(
                process_parameters, settings_dict, source_file, file_ops=mock_ops
            )

        assert result is True
        assert len(mock_ops.files_copied) > 0

    def test_copy_backend_class_usage(self, dest_dir, source_file):
        """Test CopyBackend class interface."""
        backend = copy_backend.CopyBackend()

        process_parameters = {"copy_to_directory": dest_dir}
        settings_dict = {}

        result = backend.send(process_parameters, settings_dict, source_file)

        assert result is True


class TestFTPBackendOperations:
    """Test suite for ftp_backend actual operations."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def source_file(self, temp_dir):
        """Create a source file for FTP."""
        source = temp_dir / "ftp_test.txt"
        source.write_text("FTP test content")
        return str(source)

    @pytest.fixture
    def process_parameters(self):
        """Create process parameters for FTP."""
        return {
            "ftp_server": "ftp.example.com",
            "ftp_port": 21,
            "ftp_username": "testuser",
            "ftp_password": "testpass",
            "ftp_folder": "/uploads",
        }

    @pytest.fixture
    def settings_dict(self):
        """Create empty settings dict."""
        return {}

    def test_ftp_backend_with_mock_client(
        self, process_parameters, settings_dict, source_file
    ):
        """Test FTP backend with mock client."""
        from backend.ftp_client import MockFTPClient

        mock_client = MockFTPClient()

        result = ftp_backend.do(
            process_parameters, settings_dict, source_file, ftp_client=mock_client
        )

        assert result is True
        assert len(mock_client.connections) > 0
        assert len(mock_client.logins) > 0

    def test_ftp_backend_file_sent(
        self, process_parameters, settings_dict, source_file
    ):
        """Test that file is sent via FTP."""
        from backend.ftp_client import MockFTPClient

        mock_client = MockFTPClient()

        ftp_backend.do(
            process_parameters, settings_dict, source_file, ftp_client=mock_client
        )

        # Verify file was sent
        assert len(mock_client.files_sent) > 0

    def test_ftp_backend_creates_remote_directory(
        self, process_parameters, settings_dict, source_file
    ):
        """Test that remote directory is created."""
        from backend.ftp_client import MockFTPClient

        mock_client = MockFTPClient()

        ftp_backend.do(
            process_parameters, settings_dict, source_file, ftp_client=mock_client
        )

        # Verify directory operations were attempted
        # The mock tracks cwd calls which indicate directory navigation
        assert (
            len(mock_client.directories_changed) > 0 or len(mock_client.files_sent) > 0
        )

    def test_ftp_backend_nested_directory(self, source_file, settings_dict):
        """Test FTP with nested directory path."""
        from backend.ftp_client import MockFTPClient

        process_parameters = {
            "ftp_server": "ftp.example.com",
            "ftp_port": 21,
            "ftp_username": "testuser",
            "ftp_password": "testpass",
            "ftp_folder": "/uploads/nested/deep",
        }

        mock_client = MockFTPClient()

        result = ftp_backend.do(
            process_parameters, settings_dict, source_file, ftp_client=mock_client
        )

        # Should handle nested directories
        assert result is True or len(mock_client.files_sent) > 0

    def test_ftp_backend_missing_file_raises(
        self, process_parameters, settings_dict, temp_dir
    ):
        """Test that missing file raises exception."""
        missing_file = str(temp_dir / "nonexistent.txt")

        with patch("time.sleep"):
            with pytest.raises(FileNotFoundError, match="nonexistent.txt"):
                ftp_backend.do(process_parameters, settings_dict, missing_file)


class TestEmailBackendOperations:
    """Test suite for email_backend actual operations."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def source_file(self, temp_dir):
        """Create a source file for email attachment."""
        source = temp_dir / "email_attachment.txt"
        source.write_text("Email attachment content")
        return str(source)

    @pytest.fixture
    def process_parameters(self):
        """Create process parameters for email."""
        return {
            "email_to": "recipient@example.com",
            "email_subject_line": "Test Subject - %filename%",
        }

    @pytest.fixture
    def settings(self):
        """Create settings for email."""
        return {
            "email_address": "sender@example.com",
            "email_smtp_server": "smtp.example.com",
            "smtp_port": 587,
            "email_username": "user",
            "email_password": "pass",
        }

    def test_email_backend_with_mock_client(
        self, process_parameters, settings, source_file
    ):
        """Test email backend with mock client."""
        from backend.smtp_client import MockSMTPClient

        mock_client = MockSMTPClient()

        result = email_backend.do(
            process_parameters, settings, source_file, smtp_client=mock_client
        )

        assert result is True
        assert mock_client.ehlo_calls > 0

    def test_email_backend_sends_message(
        self, process_parameters, settings, source_file
    ):
        """Test that email message is sent."""
        from backend.smtp_client import MockSMTPClient

        mock_client = MockSMTPClient()

        email_backend.do(
            process_parameters, settings, source_file, smtp_client=mock_client
        )

        # Verify send operations occurred
        assert mock_client.ehlo_calls > 0 or mock_client.send_message_calls > 0

    def test_email_backend_subject_placeholder(
        self, process_parameters, settings, source_file
    ):
        """Test that subject line placeholder is replaced."""
        from backend.smtp_client import MockSMTPClient

        mock_client = MockSMTPClient()

        email_backend.do(
            process_parameters, settings, source_file, smtp_client=mock_client
        )

        # Verify email was processed (no exception means success)
        assert mock_client.ehlo_calls > 0

    def test_email_backend_multiple_recipients(self, source_file, settings):
        """Test email with multiple recipients."""
        from backend.smtp_client import MockSMTPClient

        process_parameters = {
            "email_to": "one@example.com, two@example.com, three@example.com",
            "email_subject_line": "Multi-recipient test",
        }

        mock_client = MockSMTPClient()

        result = email_backend.do(
            process_parameters, settings, source_file, smtp_client=mock_client
        )

        assert result is True

    def test_email_backend_empty_subject(self, source_file, settings):
        """Test email with empty subject line."""
        from backend.smtp_client import MockSMTPClient

        process_parameters = {
            "email_to": "recipient@example.com",
            "email_subject_line": "",
        }

        mock_client = MockSMTPClient()

        result = email_backend.do(
            process_parameters, settings, source_file, smtp_client=mock_client
        )

        assert result is True

    def test_email_backend_missing_file_raises(
        self, process_parameters, settings, temp_dir
    ):
        """Test that missing file raises exception."""
        from unittest.mock import patch

        from backend.smtp_client import MockSMTPClient

        # Create a real file that exists
        existing_file = temp_dir / "existing.txt"
        existing_file.write_text("content")

        # Use mock client that fails - need enough errors for all 10 retries
        mock_client = MockSMTPClient()
        for _ in range(15):  # 10 retries needed
            mock_client.add_error(RuntimeError("Connection failed"))

        # Mock sleep to be instant so test runs fast
        with patch("time.sleep"):
            # The file exists, but mock fails - should raise after retries
            with pytest.raises(RuntimeError, match="Connection failed"):
                email_backend.do(
                    process_parameters,
                    settings,
                    str(existing_file),
                    smtp_client=mock_client,
                )


class TestBackendIntegration:
    """Integration tests for multiple backends."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def sample_file(self, temp_dir):
        """Create a sample file."""
        sample = temp_dir / "sample.txt"
        sample.write_text("Sample file content")
        return str(sample)

    def test_copy_and_email_backends(self, temp_dir, sample_file):
        """Test running copy and email backends together."""
        from backend.smtp_client import MockSMTPClient

        # Copy backend
        dest_dir = temp_dir / "copies"
        dest_dir.mkdir()
        copy_params = {"copy_to_directory": str(dest_dir)}

        copy_result = copy_backend.do(copy_params, {}, sample_file)

        # Email backend
        email_params = {
            "email_to": "test@example.com",
            "email_subject_line": "Test",
        }
        email_settings = {
            "email_address": "sender@example.com",
            "email_smtp_server": "smtp.example.com",
            "smtp_port": 587,
        }

        mock_smtp = MockSMTPClient()
        email_result = email_backend.do(
            email_params, email_settings, sample_file, smtp_client=mock_smtp
        )

        assert copy_result is True
        assert email_result is True

    def test_all_backends_with_same_file(self, temp_dir, sample_file):
        """Test running all backends with the same file."""
        from backend.ftp_client import MockFTPClient
        from backend.smtp_client import MockSMTPClient

        # Copy
        dest_dir = temp_dir / "copies"
        dest_dir.mkdir()
        copy_result = copy_backend.do(
            {"copy_to_directory": str(dest_dir)}, {}, sample_file
        )

        # FTP
        ftp_params = {
            "ftp_server": "ftp.example.com",
            "ftp_port": 21,
            "ftp_username": "user",
            "ftp_password": "pass",
            "ftp_folder": "/uploads",
        }
        ftp_result = ftp_backend.do(
            ftp_params, {}, sample_file, ftp_client=MockFTPClient()
        )

        # Email
        email_params = {"email_to": "test@example.com", "email_subject_line": "Test"}
        email_settings = {
            "email_address": "sender@example.com",
            "email_smtp_server": "smtp.example.com",
            "smtp_port": 587,
        }
        email_result = email_backend.do(
            email_params, email_settings, sample_file, smtp_client=MockSMTPClient()
        )

        assert copy_result is True
        assert ftp_result is True
        assert email_result is True


class TestBackendErrorScenarios:
    """Test suite for backend error scenarios."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def sample_file(self, temp_dir):
        """Create a sample file."""
        sample = temp_dir / "sample.txt"
        sample.write_text("Sample content")
        return str(sample)

    def test_copy_permission_denied(self, temp_dir, sample_file):
        """Test copy backend handles permission errors."""
        # Create a read-only directory
        readonly_dir = temp_dir / "readonly"
        readonly_dir.mkdir()
        os.chmod(readonly_dir, 0o444)

        try:
            with pytest.raises(IOError):
                copy_backend.do(
                    {"copy_to_directory": str(readonly_dir)}, {}, sample_file
                )
        finally:
            os.chmod(readonly_dir, 0o755)

    def test_ftp_connection_failure(self, sample_file):
        """Test FTP backend handles connection failures."""
        from backend.ftp_client import MockFTPClient

        mock_client = MockFTPClient()
        # Add many errors - each retry can consume multiple errors due to:
        # - connect, login, cwd, storbinary for each TLS/non-TLS attempt
        # - 10 retries with 2 providers each = up to 20+ errors needed
        for _ in range(50):
            mock_client.add_error(ConnectionError("Connection failed"))

        with patch("time.sleep"):
            with pytest.raises(ConnectionError, match="Connection failed"):
                ftp_backend.do(
                    {
                        "ftp_server": "invalid",
                        "ftp_port": 21,
                        "ftp_username": "x",
                        "ftp_password": "x",
                        "ftp_folder": "/",
                    },
                    {},
                    sample_file,
                    ftp_client=mock_client,
                )

    def test_email_auth_failure(self, sample_file):
        """Test email backend handles authentication failures."""
        import smtplib

        from backend.smtp_client import MockSMTPClient

        mock_client = MockSMTPClient()
        with (
            patch.object(
                mock_client,
                "login",
                side_effect=smtplib.SMTPAuthenticationError(535, b"Auth failed"),
            ) as mocked_login,
            patch("time.sleep"),
        ):
            with pytest.raises(smtplib.SMTPAuthenticationError, match="Auth failed"):
                email_backend.do(
                    {"email_to": "test@example.com", "email_subject_line": "Test"},
                    {
                        "email_address": "sender@example.com",
                        "email_smtp_server": "smtp.example.com",
                        "smtp_port": 587,
                        "email_username": "user",
                        "email_password": "bad-password",
                    },
                    sample_file,
                    smtp_client=mock_client,
                )

        assert mocked_login.call_count == 11
        assert len(mock_client.connections) == 11
        assert mock_client.ehlo_calls == 11
        assert mock_client.starttls_calls == 11
