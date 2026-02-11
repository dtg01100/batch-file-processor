"""Tests for dispatch/hash_utils.py module."""

import hashlib
import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from dispatch.hash_utils import (
    generate_match_lists,
    generate_file_hash,
    check_file_against_processed,
    process_file_hash_entry,
    build_hash_dictionaries,
)


class TestGenerateMatchLists:
    """Tests for generate_match_lists function."""
    
    def test_empty_list(self):
        """Test with empty input list."""
        hash_dict, name_dict, resend_set = generate_match_lists([])
        
        assert hash_dict == []
        assert name_dict == []
        assert resend_set == set()
    
    def test_single_entry_no_resend(self):
        """Test with single entry without resend flag."""
        processed_files = [
            {'file_name': 'test.txt', 'file_checksum': 'abc123', 'resend_flag': False}
        ]
        
        hash_dict, name_dict, resend_set = generate_match_lists(processed_files)
        
        assert hash_dict == [('test.txt', 'abc123')]
        assert name_dict == [('abc123', 'test.txt')]
        assert resend_set == set()
    
    def test_single_entry_with_resend(self):
        """Test with single entry with resend flag."""
        processed_files = [
            {'file_name': 'test.txt', 'file_checksum': 'abc123', 'resend_flag': True}
        ]
        
        hash_dict, name_dict, resend_set = generate_match_lists(processed_files)
        
        assert hash_dict == [('test.txt', 'abc123')]
        assert name_dict == [('abc123', 'test.txt')]
        assert resend_set == {'abc123'}
    
    def test_multiple_entries_mixed_resend(self):
        """Test with multiple entries with mixed resend flags."""
        processed_files = [
            {'file_name': 'file1.txt', 'file_checksum': 'hash1', 'resend_flag': False},
            {'file_name': 'file2.txt', 'file_checksum': 'hash2', 'resend_flag': True},
            {'file_name': 'file3.txt', 'file_checksum': 'hash3', 'resend_flag': True},
            {'file_name': 'file4.txt', 'file_checksum': 'hash4', 'resend_flag': False},
        ]
        
        hash_dict, name_dict, resend_set = generate_match_lists(processed_files)
        
        assert len(hash_dict) == 4
        assert len(name_dict) == 4
        assert resend_set == {'hash2', 'hash3'}
    
    def test_missing_resend_flag(self):
        """Test with entries missing resend flag (should default to False)."""
        processed_files = [
            {'file_name': 'test.txt', 'file_checksum': 'abc123'}
        ]
        
        hash_dict, name_dict, resend_set = generate_match_lists(processed_files)
        
        assert resend_set == set()
    
    def test_resend_flag_none(self):
        """Test with resend_flag explicitly None."""
        processed_files = [
            {'file_name': 'test.txt', 'file_checksum': 'abc123', 'resend_flag': None}
        ]
        
        hash_dict, name_dict, resend_set = generate_match_lists(processed_files)
        
        assert resend_set == set()


class TestGenerateFileHash:
    """Tests for generate_file_hash function."""
    
    def test_generate_hash_success(self):
        """Test successful hash generation."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("test content")
            temp_path = f.name
        
        try:
            result = generate_file_hash(temp_path)
            
            # Verify it's a valid MD5 hash
            assert len(result) == 32
            assert all(c in '0123456789abcdef' for c in result)
            
            # Verify it matches expected hash
            expected = hashlib.md5(b"test content").hexdigest()
            assert result == expected
        finally:
            os.unlink(temp_path)
    
    def test_generate_hash_binary_file(self):
        """Test hash generation for binary file."""
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            f.write(b'\x00\x01\x02\x03\x04\x05')
            temp_path = f.name
        
        try:
            result = generate_file_hash(temp_path)
            
            expected = hashlib.md5(b'\x00\x01\x02\x03\x04\x05').hexdigest()
            assert result == expected
        finally:
            os.unlink(temp_path)
    
    def test_generate_hash_file_not_found(self):
        """Test hash generation for non-existent file."""
        with pytest.raises(FileNotFoundError):
            generate_file_hash('/nonexistent/path/file.txt')
    
    def test_generate_hash_empty_file(self):
        """Test hash generation for empty file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            temp_path = f.name
        
        try:
            result = generate_file_hash(temp_path)
            
            expected = hashlib.md5(b"").hexdigest()
            assert result == expected
        finally:
            os.unlink(temp_path)
    
    def test_generate_hash_with_retry(self):
        """Test hash generation with retry logic."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("test content")
            temp_path = f.name
        
        try:
            # Test with low max_retries to ensure it works
            result = generate_file_hash(temp_path, max_retries=1)
            assert len(result) == 32
        finally:
            os.unlink(temp_path)


class TestCheckFileAgainstProcessed:
    """Tests for check_file_against_processed function."""
    
    def test_new_file(self):
        """Test checking a new file (not in name_dict)."""
        name_dict = {'hash1': 'file1.txt'}
        resend_set = set()
        
        match_found, should_send = check_file_against_processed(
            'new_file.txt', 'new_hash', name_dict, resend_set
        )
        
        assert match_found is False
        assert should_send is True
    
    def test_existing_file_no_resend(self):
        """Test checking an existing file without resend flag."""
        name_dict = {'hash1': 'file1.txt'}
        resend_set = set()
        
        match_found, should_send = check_file_against_processed(
            'file1.txt', 'hash1', name_dict, resend_set
        )
        
        assert match_found is True
        assert should_send is False
    
    def test_existing_file_with_resend(self):
        """Test checking an existing file with resend flag."""
        name_dict = {'hash1': 'file1.txt'}
        resend_set = {'hash1'}
        
        match_found, should_send = check_file_against_processed(
            'file1.txt', 'hash1', name_dict, resend_set
        )
        
        assert match_found is True
        assert should_send is True
    
    def test_empty_dictionaries(self):
        """Test with empty dictionaries."""
        match_found, should_send = check_file_against_processed(
            'file.txt', 'hash1', {}, set()
        )
        
        assert match_found is False
        assert should_send is True


class TestProcessFileHashEntry:
    """Tests for process_file_hash_entry function."""
    
    def test_process_new_file(self):
        """Test processing a new file entry."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("test content")
            temp_path = f.name
        
        try:
            source_struct = (
                temp_path,  # file_path
                0,          # index_number
                [],         # processed_files_list
                {},         # hash_dict
                {},         # name_dict
                set()       # resend_set
            )
            
            file_name, file_checksum, index_number, send_file = process_file_hash_entry(source_struct)
            
            assert file_name == os.path.abspath(temp_path)
            assert len(file_checksum) == 32
            assert index_number == 0
            assert send_file is True  # New file should be sent
        finally:
            os.unlink(temp_path)
    
    def test_process_existing_file_no_resend(self):
        """Test processing an existing file without resend."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("test content")
            temp_path = f.name
        
        try:
            expected_hash = hashlib.md5(b"test content").hexdigest()
            
            source_struct = (
                temp_path,
                5,
                [],
                {},
                {expected_hash: 'existing_file.txt'},  # name_dict with this hash
                set()  # No resend
            )
            
            file_name, file_checksum, index_number, send_file = process_file_hash_entry(source_struct)
            
            assert file_checksum == expected_hash
            assert index_number == 5
            assert send_file is False  # Existing file, no resend
        finally:
            os.unlink(temp_path)
    
    def test_process_existing_file_with_resend(self):
        """Test processing an existing file with resend flag."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("test content")
            temp_path = f.name
        
        try:
            expected_hash = hashlib.md5(b"test content").hexdigest()
            
            source_struct = (
                temp_path,
                3,
                [],
                {},
                {expected_hash: 'existing_file.txt'},
                {expected_hash}  # Resend set includes this hash
            )
            
            file_name, file_checksum, index_number, send_file = process_file_hash_entry(source_struct)
            
            assert send_file is True  # Should send due to resend flag
        finally:
            os.unlink(temp_path)


class TestBuildHashDictionaries:
    """Tests for build_hash_dictionaries function."""
    
    def test_empty_list(self):
        """Test with empty input list."""
        hash_dict, name_dict, resend_set = build_hash_dictionaries([])
        
        assert hash_dict == {}
        assert name_dict == {}
        assert resend_set == set()
    
    def test_single_entry(self):
        """Test with single entry."""
        processed_files = [
            {'file_name': 'test.txt', 'file_checksum': 'abc123', 'resend_flag': False}
        ]
        
        hash_dict, name_dict, resend_set = build_hash_dictionaries(processed_files)
        
        assert hash_dict == {'test.txt': 'abc123'}
        assert name_dict == {'abc123': 'test.txt'}
        assert resend_set == set()
    
    def test_multiple_entries(self):
        """Test with multiple entries."""
        processed_files = [
            {'file_name': 'file1.txt', 'file_checksum': 'hash1', 'resend_flag': False},
            {'file_name': 'file2.txt', 'file_checksum': 'hash2', 'resend_flag': True},
        ]
        
        hash_dict, name_dict, resend_set = build_hash_dictionaries(processed_files)
        
        assert hash_dict == {'file1.txt': 'hash1', 'file2.txt': 'hash2'}
        assert name_dict == {'hash1': 'file1.txt', 'hash2': 'file2.txt'}
        assert resend_set == {'hash2'}
    
    def test_duplicate_checksums(self):
        """Test with duplicate checksums (later entry wins)."""
        processed_files = [
            {'file_name': 'file1.txt', 'file_checksum': 'same_hash', 'resend_flag': False},
            {'file_name': 'file2.txt', 'file_checksum': 'same_hash', 'resend_flag': False},
        ]
        
        hash_dict, name_dict, resend_set = build_hash_dictionaries(processed_files)
        
        # Later entry wins for name_dict
        assert name_dict == {'same_hash': 'file2.txt'}
        # Both entries in hash_dict
        assert len(hash_dict) == 2
