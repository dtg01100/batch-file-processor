#!/usr/bin/env python3
"""
Simple test file to verify remote file system functionality
"""

import os
import tempfile
import shutil
from backend.remote_fs.factory import create_file_system
from backend.remote_fs.local import LocalFileSystem


def test_local_file_system_initialization():
    """Test that LocalFileSystem initializes correctly"""
    temp_dir = tempfile.mkdtemp()
    try:
        fs = LocalFileSystem(temp_dir)
        assert fs is not None
        assert hasattr(fs, "list_files")
        assert callable(getattr(fs, "list_files"))
    finally:
        shutil.rmtree(temp_dir)


def test_local_file_system_operations():
    """Test basic file operations on LocalFileSystem"""
    temp_dir = tempfile.mkdtemp()
    fs = LocalFileSystem(temp_dir)
    
    try:
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
        assert fs.file_exists("test.txt") == True
        
        # Get file info
        info = fs.get_file_info("test.txt")
        assert info["name"] == "test.txt"
        assert info["size"] == len(test_content)
        
        # Delete file
        assert fs.delete_file("test.txt") == True
        assert fs.file_exists("test.txt") == False
        
    finally:
        shutil.rmtree(temp_dir)


def test_factory_create_local():
    """Test creating local file system via factory"""
    temp_dir = tempfile.mkdtemp()
    try:
        params = {"path": temp_dir}
        fs = create_file_system("local", params)
        assert isinstance(fs, LocalFileSystem)
        assert fs is not None
    finally:
        shutil.rmtree(temp_dir)


def test_directory_operations():
    """Test directory operations on LocalFileSystem"""
    temp_dir = tempfile.mkdtemp()
    fs = LocalFileSystem(temp_dir)
    
    try:
        # Create directory
        assert fs.create_directory("test_dir") == True
        assert fs.directory_exists("test_dir") == True
        
        # Create subdirectory
        assert fs.create_directory("test_dir/subdir") == True
        assert fs.directory_exists("test_dir/subdir") == True
        
        # Delete directory
        assert fs.delete_directory("test_dir/subdir") == True
        assert fs.directory_exists("test_dir/subdir") == False
        
        assert fs.delete_directory("test_dir") == True
        assert fs.directory_exists("test_dir") == False
        
    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    print("Running remote file system tests...")
    test_local_file_system_initialization()
    print("✓ Initialization test passed")
    
    test_local_file_system_operations()
    print("✓ File operations test passed")
    
    test_factory_create_local()
    print("✓ Factory test passed")
    
    test_directory_operations()
    print("✓ Directory operations test passed")
    
    print("\nAll tests passed!")
