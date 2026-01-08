"""
Unit tests for remote file system implementations
"""

import pytest
import tempfile
import os
from backend.remote_fs.local import LocalFileSystem
from backend.remote_fs.smb import SMBFileSystem
from backend.remote_fs.sftp import SFTPFileSystem
from backend.remote_fs.ftp import FTPFileSystem
from backend.remote_fs.factory import create_file_system


class TestLocalFileSystem:
    """Tests for LocalFileSystem"""

    def test_list_files(self):
        """Test listing files in directory"""
        # Create temp directory with test file
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("test content")

            # Create file system and list files
            fs = LocalFileSystem(temp_dir)
            files = fs.list_files(".")

            assert len(files) == 1
            assert files[0]["name"] == "test.txt"
            assert files[0]["size"] > 0

    def test_download_file(self):
        """Test downloading file"""
        with tempfile.TemporaryDirectory() as source_dir:
            # Create test file
            source_file = os.path.join(source_dir, "source.txt")
            with open(source_file, "w") as f:
                f.write("source content")

            # Download file
            with tempfile.TemporaryDirectory() as dest_dir:
                fs = LocalFileSystem(source_dir)
                dest_file = os.path.join(dest_dir, "dest.txt")

                success = fs.download_file("source.txt", dest_file)
                assert success is True
                assert os.path.exists(dest_file)

                # Verify content
                with open(dest_file, "r") as f:
                    content = f.read()
                assert content == "source content"

    def test_file_exists(self):
        """Test checking file existence"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "exists.txt")
            with open(test_file, "w") as f:
                f.write("test")

            fs = LocalFileSystem(temp_dir)
            assert fs.file_exists("exists.txt") is True
            assert fs.file_exists("notexists.txt") is False

    def test_get_file_info(self):
        """Test getting file metadata"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "info.txt")
            with open(test_file, "w") as f:
                f.write("test")

            fs = LocalFileSystem(temp_dir)
            info = fs.get_file_info("info.txt")

            assert info["name"] == "info.txt"
            assert info["size"] > 0
            assert "modified" in info


class TestFileSystemFactory:
    """Tests for file system factory"""

    def test_create_local_filesystem(self):
        """Test creating LocalFileSystem"""
        fs = create_file_system("local", {"path": "/tmp"})
        assert isinstance(fs, LocalFileSystem)

    def test_create_smb_filesystem(self):
        """Test creating SMBFileSystem"""
        params = {
            "host": "example.com",
            "username": "user",
            "password": "pass",
            "share": "share",
        }
        fs = create_file_system("smb", params)
        assert isinstance(fs, SMBFileSystem)

    def test_create_sftp_filesystem(self):
        """Test creating SFTPFileSystem"""
        params = {"host": "example.com", "username": "user", "password": "pass"}
        fs = create_file_system("sftp", params)
        assert isinstance(fs, SFTPFileSystem)

    def test_create_ftp_filesystem(self):
        """Test creating FTPFileSystem"""
        params = {"host": "example.com", "username": "user", "password": "pass"}
        fs = create_file_system("ftp", params)
        assert isinstance(fs, FTPFileSystem)

    def test_invalid_connection_type(self):
        """Test that invalid connection type raises exception"""
        with pytest.raises(Exception):
            create_file_system("invalid", {})

    def test_missing_required_params(self):
        """Test that missing required params raises exception"""
        with pytest.raises(Exception):
            create_file_system(
                "sftp", {"host": "example.com"}
            )  # Missing username/password
