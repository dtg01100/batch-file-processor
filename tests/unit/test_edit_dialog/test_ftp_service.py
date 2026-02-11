"""FTP Service tests for EditFoldersDialog refactoring."""

import pytest
from unittest.mock import patch, MagicMock

import sys
import os

# Add the project root to the path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from interface.services.ftp_service import (
    FTPService,
    MockFTPService,
    FTPConnectionResult,
)


class TestMockFTPService:
    """Test suite for MockFTPService."""

    def test_successful_connection(self):
        """Test successful FTP connection simulation."""
        mock_service = MockFTPService(should_succeed=True)

        result = mock_service.test_connection(
            server="ftp.example.com",
            port=21,
            username="testuser",
            password="testpass",
            folder="/uploads/"
        )

        assert result.success is True
        assert result.error_message is None

    def test_failed_connection_server(self):
        """Test failed connection at server level."""
        mock_service = MockFTPService(
            should_succeed=False,
            fail_at="server",
            error_message="FTP Server or Port Field Incorrect"
        )

        result = mock_service.test_connection(
            server="invalid.server",
            port=99999,
            username="testuser",
            password="testpass",
            folder="/uploads/"
        )

        assert result.success is False
        assert result.error_type == "server"
        assert "FTP Server or Port Field Incorrect" in result.error_message

    def test_failed_connection_login(self):
        """Test failed connection at login level."""
        mock_service = MockFTPService(
            should_succeed=False,
            fail_at="login",
            error_message="FTP Username or Password Incorrect"
        )

        result = mock_service.test_connection(
            server="ftp.example.com",
            port=21,
            username="wronguser",
            password="wrongpass",
            folder="/uploads/"
        )

        assert result.success is False
        assert result.error_type == "login"

    def test_failed_connection_cwd(self):
        """Test failed connection at CWD level."""
        mock_service = MockFTPService(
            should_succeed=False,
            fail_at="cwd",
            error_message="FTP Folder Field Incorrect"
        )

        result = mock_service.test_connection(
            server="ftp.example.com",
            port=21,
            username="testuser",
            password="testpass",
            folder="/nonexistent/"
        )

        assert result.success is False
        assert result.error_type == "cwd"
        assert "FTP Folder Field Incorrect" in result.error_message

    def test_connection_attempts_recorded(self):
        """Test that connection attempts are recorded."""
        mock_service = MockFTPService(should_succeed=True)

        mock_service.test_connection(
            server="ftp.example.com",
            port=21,
            username="testuser",
            password="testpass",
            folder="/uploads/"
        )

        assert len(mock_service.connection_attempts) == 1
        assert mock_service.connection_attempts[0]["server"] == "ftp.example.com"
        assert mock_service.connection_attempts[0]["folder"] == "/uploads/"

    def test_multiple_connection_attempts(self):
        """Test multiple connection attempts are recorded."""
        mock_service = MockFTPService(should_succeed=True)

        mock_service.test_connection(
            server="ftp1.example.com",
            port=21,
            username="user1",
            password="pass1",
            folder="/folder1/"
        )

        mock_service.test_connection(
            server="ftp2.example.com",
            port=21,
            username="user2",
            password="pass2",
            folder="/folder2/"
        )

        assert len(mock_service.connection_attempts) == 2
        assert mock_service.connection_attempts[0]["server"] == "ftp1.example.com"
        assert mock_service.connection_attempts[1]["server"] == "ftp2.example.com"


class TestFTPConnectionResult:
    """Test suite for FTPConnectionResult dataclass."""

    def test_successful_result(self):
        """Test successful result creation."""
        result = FTPConnectionResult(success=True)

        assert result.success is True
        assert result.error_message is None
        assert result.error_type is None

    def test_failed_result(self):
        """Test failed result creation."""
        result = FTPConnectionResult(
            success=False,
            error_message="Connection refused",
            error_type="server"
        )

        assert result.success is False
        assert result.error_message == "Connection refused"
        assert result.error_type == "server"
