#!/usr/bin/env python3
"""
Tests for remote file system implementations
"""

import os
import tempfile
import shutil
import pytest
from backend.remote_fs.factory import create_file_system
from backend.remote_fs.local import LocalFileSystem


def test_local_file_system_initialization():
    """Test that LocalFileSystem initializes correctly"""
    with tempfile.TemporaryDirectory() as temp_dir:
        fs = LocalFileSystem(temp_dir)
        assert fs is not None
        assert hasattr(fs, "list_files")
        assert callable(getattr(fs, "list_files"))


def test_local_file_system_operations():
    """Test basic file operations on LocalFileSystem"""
    with tempfile.TemporaryDirectory() as temp_dir:
        fs = LocalFileSystem(temp_dir)
        
        # Create test file
        test_content = b"test content"
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, "wb") as f:
            f.write(test_content)
        
        # List files
        files = fs.list_files("")
        assert len(files) == 1
        assert files[0]["name"] == "test.txt"
        assert files[0]["size"] == len(test_content)
        
        # File exists
        assert fs.file_exists("test.txt") is True
        
        # Get file info
        info = fs.get_file_info("test.txt")
        assert info["name"] == "test.txt"
        assert info["size"] == len(test_content)
        
        # Delete file
        assert fs.delete_file("test.txt") is True
        assert fs.file_exists("test.txt") is False


def test_factory_create_local():
    """Test creating local file system via factory"""
    with tempfile.TemporaryDirectory() as temp_dir:
        params = {"path": temp_dir}
        fs = create_file_system("local", params)
        assert isinstance(fs, LocalFileSystem)
        assert fs is not None


def test_directory_operations():
    """Test directory operations on LocalFileSystem"""
    with tempfile.TemporaryDirectory() as temp_dir:
        fs = LocalFileSystem(temp_dir)
        
        # Create directory
        assert fs.create_directory("test_dir") is True
        assert fs.directory_exists("test_dir") is True
        
        # Create subdirectory
        assert fs.create_directory("test_dir/subdir") is True
        assert fs.directory_exists("test_dir/subdir") is True
        
        # Delete directory
        assert fs.delete_directory("test_dir/subdir") is True
        assert fs.directory_exists("test_dir/subdir") is False
        
        assert fs.delete_directory("test_dir") is True
        assert fs.directory_exists("test_dir") is False


def test_upload_download_file():
    """Test file upload and download operations"""
    with tempfile.TemporaryDirectory() as temp_dir:
        fs = LocalFileSystem(temp_dir)
        
        # Create test file
        test_content = b"upload test content"
        local_source = tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.txt')
        local_source.write(test_content)
        local_source.close()
        
        try:
            remote_path = "uploaded_file.txt"
            
            # Upload file
            assert fs.upload_file(local_source.name, remote_path) is True
            assert fs.file_exists(remote_path) is True
            
            # Download file
            local_dest = tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.txt')
            local_dest.close()
            assert fs.download_file(remote_path, local_dest.name) is True
            
            # Verify content
            with open(local_dest.name, 'rb') as f:
                assert f.read() == test_content
                
        finally:
            os.unlink(local_source.name)
            if 'local_dest' in locals():
                os.unlink(local_dest.name)


def test_file_hash():
    """Test file hash calculation"""
    with tempfile.TemporaryDirectory() as temp_dir:
        fs = LocalFileSystem(temp_dir)
        
        # Create test file
        test_content = b"test content for hash calculation"
        test_file = os.path.join(temp_dir, "hash_test.txt")
        with open(test_file, "wb") as f:
            f.write(test_content)
        
        # Calculate hash
        md5_hash = fs.get_file_hash("hash_test.txt")
        assert isinstance(md5_hash, str)
        assert len(md5_hash) == 32
        
        sha1_hash = fs.get_file_hash("hash_test.txt", "sha1")
        assert isinstance(sha1_hash, str)
        assert len(sha1_hash) == 40
        
        sha256_hash = fs.get_file_hash("hash_test.txt", "sha256")
        assert isinstance(sha256_hash, str)
        assert len(sha256_hash) == 64


def test_directory_recursive_operations():
    """Test recursive directory operations"""
    with tempfile.TemporaryDirectory() as temp_dir:
        fs = LocalFileSystem(temp_dir)
        
        # Create test directory structure
        test_dir = tempfile.mkdtemp()
        try:
            subdir = os.path.join(test_dir, "subdir")
            os.makedirs(subdir)
            
            with open(os.path.join(test_dir, "file1.txt"), 'w') as f:
                f.write("content1")
            with open(os.path.join(subdir, "file2.txt"), 'w') as f:
                f.write("content2")
            
            # Upload directory
            remote_dir = "uploaded_dir"
            assert fs.upload_directory(test_dir, remote_dir) is True
            assert fs.directory_exists(remote_dir) is True
            
            # Check files were uploaded
            assert fs.file_exists(os.path.join(remote_dir, "file1.txt")) is True
            assert fs.file_exists(os.path.join(remote_dir, "subdir", "file2.txt")) is True
            
            # Download directory
            download_dir = tempfile.mkdtemp()
            assert fs.download_directory(remote_dir, download_dir) is True
            
            # Verify downloaded content
            with open(os.path.join(download_dir, "file1.txt"), 'r') as f:
                assert f.read() == "content1"
            with open(os.path.join(download_dir, "subdir", "file2.txt"), 'r') as f:
                assert f.read() == "content2"
                
            shutil.rmtree(download_dir)
            
        finally:
            shutil.rmtree(test_dir)
