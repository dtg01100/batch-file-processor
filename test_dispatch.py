import os
import pytest
import tempfile
import hashlib
from dispatch import generate_match_lists, generate_file_hash

def test_generate_match_lists_basic():
    folder_temp_processed_files_list = [
        {'file_name': 'file1.txt', 'file_checksum': 'abc123', 'resend_flag': False},
        {'file_name': 'file2.txt', 'file_checksum': 'def456', 'resend_flag': True},
    ]
    folder_hash_dict, folder_name_dict, resend_flag_set = generate_match_lists(folder_temp_processed_files_list)
    assert ('file1.txt', 'abc123') in folder_hash_dict
    assert ('def456', 'file2.txt') in folder_name_dict
    assert 'def456' in resend_flag_set
    assert 'abc123' not in resend_flag_set

def test_generate_file_hash_new_file(tmp_path):
    # Create a temp file
    file_path = tmp_path / "testfile.txt"
    file_path.write_text("hello world")
    checksum = hashlib.md5(b"hello world").hexdigest()
    temp_processed_files_list = []
    folder_hash_dict = {}
    folder_name_dict = {}
    resend_flag_set = set()
    source_file_struct = (str(file_path), 0, temp_processed_files_list, folder_hash_dict, folder_name_dict, resend_flag_set)
    file_name, generated_file_checksum, index_number, send_file = generate_file_hash(source_file_struct)
    assert file_name == os.path.abspath(str(file_path))
    assert generated_file_checksum == checksum
    assert index_number == 0
    assert send_file is True  # Not in processed list, so should send

def test_generate_file_hash_existing_file(tmp_path):
    # Create a temp file
    file_path = tmp_path / "testfile2.txt"
    file_path.write_text("data123")
    checksum = hashlib.md5(b"data123").hexdigest()
    temp_processed_files_list = []
    folder_hash_dict = {}
    folder_name_dict = {checksum: "testfile2.txt"}
    resend_flag_set = set()
    source_file_struct = (str(file_path), 1, temp_processed_files_list, folder_hash_dict, folder_name_dict, resend_flag_set)
    file_name, generated_file_checksum, index_number, send_file = generate_file_hash(source_file_struct)
    assert send_file is False  # Already processed, not in resend

def test_generate_file_hash_resend_flag(tmp_path):
    file_path = tmp_path / "testfile3.txt"
    file_path.write_text("resendme")
    checksum = hashlib.md5(b"resendme").hexdigest()
    temp_processed_files_list = []
    folder_hash_dict = {}
    folder_name_dict = {checksum: "testfile3.txt"}
    resend_flag_set = {checksum}
    source_file_struct = (str(file_path), 2, temp_processed_files_list, folder_hash_dict, folder_name_dict, resend_flag_set)
    file_name, generated_file_checksum, index_number, send_file = generate_file_hash(source_file_struct)
    assert send_file is True  # resend_flag forces send