import pytest
import tempfile
import os
import json
import sqlite3
from fastapi.testclient import TestClient
from unittest.mock import patch

# Import the main app
import sys
sys.path.insert(0, "/var/mnt/Disk2/projects/batch-file-processor")

from backend.main import app

def create_test_legacy_db():
    """Create a temporary legacy database for testing"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)  # Close the file descriptor to avoid locking issues
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    
    # Create folders table
    cursor.execute("""
        CREATE TABLE folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folder_name TEXT,
            alias TEXT,
            folder_is_active TEXT,
            connection_type TEXT,
            connection_params TEXT,
            schedule TEXT,
            enabled TEXT,
            process_edi TEXT,
            convert_to_format TEXT,
            tweak_edi TEXT,
            split_edi TEXT,
            force_edi_validation INTEGER,
            append_a_records TEXT,
            a_record_append_text TEXT,
            invoice_date_offset INTEGER,
            retail_uom INTEGER,
            force_each_upc INTEGER,
            include_item_numbers INTEGER,
            include_item_description INTEGER,
            process_backend_copy INTEGER,
            copy_to_directory TEXT,
            process_backend_ftp INTEGER,
            ftp_server TEXT,
            ftp_folder TEXT,
            ftp_username TEXT,
            ftp_password TEXT,
            ftp_port INTEGER,
            process_backend_email INTEGER,
            email_to TEXT,
            email_subject_line TEXT
        )
    """)
    
    # Insert test data
    test_folder = {
        "folder_name": "/test/input",
        "alias": "Integration Test Pipeline",
        "folder_is_active": "True",
        "connection_type": "local",
        "connection_params": json.dumps({"path": "/test/input"}),
        "schedule": "*/30 * * * *",
        "enabled": "True",
        "process_edi": "True",
        "convert_to_format": "csv",
        "tweak_edi": "True",
        "split_edi": "False",
        "force_edi_validation": 0,
        "append_a_records": "False",
        "a_record_append_text": "",
        "invoice_date_offset": 0,
        "retail_uom": 0,
        "force_each_upc": 0,
        "include_item_numbers": 1,
        "include_item_description": 0,
        "process_backend_copy": 1,
        "copy_to_directory": "/test/output",
        "process_backend_ftp": 0,
        "ftp_server": "",
        "ftp_folder": "",
        "ftp_username": "",
        "ftp_password": "",
        "ftp_port": 21,
        "process_backend_email": 0,
        "email_to": "",
        "email_subject_line": ""
    }
    
    placeholders = ", ".join(["?" for _ in test_folder])
    columns = ", ".join(test_folder.keys())
    sql = f"INSERT INTO folders ({columns}) VALUES ({placeholders})"
    cursor.execute(sql, list(test_folder.values()))
    
    # Create version table
    cursor.execute("""
        CREATE TABLE version (
            id INTEGER PRIMARY KEY,
            version TEXT,
            os TEXT
        )
    """)
    
    cursor.execute("INSERT INTO version (id, version, os) VALUES (1, '32', 'Linux')")
    
    conn.commit()
    conn.close()
    
    return path

def test_full_import_workflow():
    """Test the complete import workflow from preview to import"""
    client = TestClient(app)
    
    # Create a test legacy database
    db_path = create_test_legacy_db()
    
    # Step 1: Test preview functionality
    with open(db_path, "rb") as db_file:
        preview_response = client.post(
            "/api/legacy-import/preview-db",
            files={"file": ("test.db", db_file, "application/octet-stream")}
        )
    
    assert preview_response.status_code == 200
    preview_data = preview_response.json()
    assert isinstance(preview_data, list)
    assert len(preview_data) == 1
    assert preview_data[0]["name"] == "Integration Test Pipeline"
    assert preview_data[0]["has_errors"] is False
    
    # Step 2: Test actual import functionality
    with open(db_path, "rb") as db_file:
        import_response = client.post(
            "/api/legacy-import/import-db",
            files={"file": ("test.db", db_file, "application/octet-stream")}
        )
    
    assert import_response.status_code == 200
    import_data = import_response.json()
    assert import_data["success"] is True
    assert "imported_pipelines" in import_data
    assert "message" in import_data
    
    # Clean up
    os.unlink(db_path)

def test_import_with_multiple_folders():
    """Test import with a database containing multiple folders"""
    client = TestClient(app)
    
    # Create a temporary database with multiple folders
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("""
        CREATE TABLE folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folder_name TEXT,
            alias TEXT,
            folder_is_active TEXT,
            connection_type TEXT,
            connection_params TEXT,
            schedule TEXT,
            enabled TEXT,
            process_edi TEXT,
            convert_to_format TEXT,
            tweak_edi TEXT,
            split_edi TEXT,
            force_edi_validation INTEGER,
            append_a_records TEXT,
            a_record_append_text TEXT,
            invoice_date_offset INTEGER,
            retail_uom INTEGER,
            force_each_upc INTEGER,
            include_item_numbers INTEGER,
            include_item_description INTEGER,
            process_backend_copy INTEGER,
            copy_to_directory TEXT,
            process_backend_ftp INTEGER,
            ftp_server TEXT,
            ftp_folder TEXT,
            ftp_username TEXT,
            ftp_password TEXT,
            ftp_port INTEGER,
            process_backend_email INTEGER,
            email_to TEXT,
            email_subject_line TEXT
        )
    """)
    
    # Insert multiple test folders
    test_folders = [
        {
            "folder_name": "/test/input1",
            "alias": "First Pipeline",
            "folder_is_active": "True",
            "connection_type": "local",
            "connection_params": json.dumps({"path": "/test/input1"}),
            "schedule": "*/30 * * * *",
            "enabled": "True",
            "process_edi": "True",
            "convert_to_format": "csv",
            "tweak_edi": "False",
            "split_edi": "False",
            "force_edi_validation": 0,
            "append_a_records": "False",
            "a_record_append_text": "",
            "invoice_date_offset": 0,
            "retail_uom": 0,
            "force_each_upc": 0,
            "include_item_numbers": 0,
            "include_item_description": 0,
            "process_backend_copy": 1,
            "copy_to_directory": "/test/output1",
            "process_backend_ftp": 0,
            "ftp_server": "",
            "ftp_folder": "",
            "ftp_username": "",
            "ftp_password": "",
            "ftp_port": 21,
            "process_backend_email": 0,
            "email_to": "",
            "email_subject_line": ""
        },
        {
            "folder_name": "/test/input2",
            "alias": "Second Pipeline",
            "folder_is_active": "True",
            "connection_type": "sftp",
            "connection_params": json.dumps({"host": "sftp.example.com", "username": "user"}),
            "schedule": "0 9 * * *",
            "enabled": "True",
            "process_edi": "False",
            "convert_to_format": "json",
            "tweak_edi": "True",
            "split_edi": "True",
            "force_edi_validation": 1,
            "append_a_records": "True",
            "a_record_append_text": "APPEND_TEXT",
            "invoice_date_offset": 5,
            "retail_uom": 1,
            "force_each_upc": 1,
            "include_item_numbers": 1,
            "include_item_description": 1,
            "process_backend_copy": 0,
            "copy_to_directory": "",
            "process_backend_ftp": 1,
            "ftp_server": "ftp.example.com",
            "ftp_folder": "/upload",
            "ftp_username": "ftpuser",
            "ftp_password": "ftppass",
            "ftp_port": 22,
            "process_backend_email": 0,
            "email_to": "",
            "email_subject_line": ""
        }
    ]
    
    for folder in test_folders:
        placeholders = ", ".join(["?" for _ in folder])
        columns = ", ".join(folder.keys())
        sql = f"INSERT INTO folders ({columns}) VALUES ({placeholders})"
        cursor.execute(sql, list(folder.values()))
    
    # Create version table
    cursor.execute("""
        CREATE TABLE version (
            id INTEGER PRIMARY KEY,
            version TEXT,
            os TEXT
        )
    """)
    
    cursor.execute("INSERT INTO version (id, version, os) VALUES (1, '32', 'Linux')")
    
    conn.commit()
    conn.close()
    
    # Test preview
    with open(path, "rb") as db_file:
        preview_response = client.post(
            "/api/legacy-import/preview-db",
            files={"file": ("test.db", db_file, "application/octet-stream")}
        )
    
    assert preview_response.status_code == 200
    preview_data = preview_response.json()
    assert isinstance(preview_data, list)
    assert len(preview_data) == 2  # Two folders in our test DB
    
    # Check that both folders are present in preview
    preview_names = [item["name"] for item in preview_data]
    assert "First Pipeline" in preview_names
    assert "Second Pipeline" in preview_names
    
    # Test import
    with open(path, "rb") as db_file:
        import_response = client.post(
            "/api/legacy-import/import-db",
            files={"file": ("test.db", db_file, "application/octet-stream")}
        )
    
    assert import_response.status_code == 200
    import_data = import_response.json()
    assert import_data["success"] is True
    assert "imported_pipelines" in import_data
    assert "message" in import_data
    
    # Clean up
    os.unlink(path)

def test_import_with_inactive_folders():
    """Test that inactive folders are not imported"""
    client = TestClient(app)
    
    # Create a temporary database with both active and inactive folders
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("""
        CREATE TABLE folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folder_name TEXT,
            alias TEXT,
            folder_is_active TEXT,
            connection_type TEXT,
            connection_params TEXT,
            schedule TEXT,
            enabled TEXT,
            process_edi TEXT,
            convert_to_format TEXT,
            tweak_edi TEXT,
            split_edi TEXT,
            force_edi_validation INTEGER,
            append_a_records TEXT,
            a_record_append_text TEXT,
            invoice_date_offset INTEGER,
            retail_uom INTEGER,
            force_each_upc INTEGER,
            include_item_numbers INTEGER,
            include_item_description INTEGER,
            process_backend_copy INTEGER,
            copy_to_directory TEXT,
            process_backend_ftp INTEGER,
            ftp_server TEXT,
            ftp_folder TEXT,
            ftp_username TEXT,
            ftp_password TEXT,
            ftp_port INTEGER,
            process_backend_email INTEGER,
            email_to TEXT,
            email_subject_line TEXT
        )
    """)
    
    # Insert one active and one inactive folder
    active_folder = {
        "folder_name": "/test/active",
        "alias": "Active Pipeline",
        "folder_is_active": "True",
        "connection_type": "local",
        "connection_params": json.dumps({"path": "/test/active"}),
        "schedule": "*/30 * * * *",
        "enabled": "True",
        "process_edi": "True",
        "convert_to_format": "csv",
        "tweak_edi": "False",
        "split_edi": "False",
        "force_edi_validation": 0,
        "append_a_records": "False",
        "a_record_append_text": "",
        "invoice_date_offset": 0,
        "retail_uom": 0,
        "force_each_upc": 0,
        "include_item_numbers": 0,
        "include_item_description": 0,
        "process_backend_copy": 1,
        "copy_to_directory": "/test/output",
        "process_backend_ftp": 0,
        "ftp_server": "",
        "ftp_folder": "",
        "ftp_username": "",
        "ftp_password": "",
        "ftp_port": 21,
        "process_backend_email": 0,
        "email_to": "",
        "email_subject_line": ""
    }
    
    inactive_folder = {
        "folder_name": "/test/inactive",
        "alias": "Inactive Pipeline",
        "folder_is_active": "False",  # This should not be imported
        "connection_type": "local",
        "connection_params": json.dumps({"path": "/test/inactive"}),
        "schedule": "*/60 * * * *",
        "enabled": "False",
        "process_edi": "False",
        "convert_to_format": "",
        "tweak_edi": "False",
        "split_edi": "False",
        "force_edi_validation": 0,
        "append_a_records": "False",
        "a_record_append_text": "",
        "invoice_date_offset": 0,
        "retail_uom": 0,
        "force_each_upc": 0,
        "include_item_numbers": 0,
        "include_item_description": 0,
        "process_backend_copy": 0,
        "copy_to_directory": "",
        "process_backend_ftp": 0,
        "ftp_server": "",
        "ftp_folder": "",
        "ftp_username": "",
        "ftp_password": "",
        "ftp_port": 21,
        "process_backend_email": 0,
        "email_to": "",
        "email_subject_line": ""
    }
    
    for folder in [active_folder, inactive_folder]:
        placeholders = ", ".join(["?" for _ in folder])
        columns = ", ".join(folder.keys())
        sql = f"INSERT INTO folders ({columns}) VALUES ({placeholders})"
        cursor.execute(sql, list(folder.values()))
    
    # Create version table
    cursor.execute("""
        CREATE TABLE version (
            id INTEGER PRIMARY KEY,
            version TEXT,
            os TEXT
        )
    """)
    
    cursor.execute("INSERT INTO version (id, version, os) VALUES (1, '32', 'Linux')")
    
    conn.commit()
    conn.close()
    
    # Test preview - should only show active folder
    with open(path, "rb") as db_file:
        preview_response = client.post(
            "/api/legacy-import/preview-db",
            files={"file": ("test.db", db_file, "application/octet-stream")}
        )
    
    assert preview_response.status_code == 200
    preview_data = preview_response.json()
    assert isinstance(preview_data, list)
    assert len(preview_data) == 1  # Only active folder should be shown
    assert preview_data[0]["name"] == "Active Pipeline"
    
    # Test import - should only import active folder
    with open(path, "rb") as db_file:
        import_response = client.post(
            "/api/legacy-import/import-db",
            files={"file": ("test.db", db_file, "application/octet-stream")}
        )
    
    assert import_response.status_code == 200
    import_data = import_response.json()
    assert import_data["success"] is True
    # The imported count should reflect only active folders
    
    # Clean up
    os.unlink(path)

def test_error_handling_on_corrupted_db():
    """Test error handling when database is corrupted"""
    client = TestClient(app)
    
    # Create a corrupted database file
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    with open(path, "wb") as f:
        f.write(b"This is not a valid SQLite database")
    
    # Test preview with corrupted DB
    with open(path, "rb") as db_file:
        preview_response = client.post(
            "/api/legacy-import/preview-db",
            files={"file": ("corrupted.db", db_file, "application/octet-stream")}
        )
    
    # Should return an error, but gracefully
    assert preview_response.status_code in [400, 500]  # Either bad request or internal error
    
    # Test import with corrupted DB
    with open(path, "rb") as db_file:
        import_response = client.post(
            "/api/legacy-import/import-db",
            files={"file": ("corrupted.db", db_file, "application/octet-stream")}
        )
    
    # Should return an error, but gracefully
    assert import_response.status_code in [400, 500]  # Either bad request or internal error
    
    # Clean up
    os.unlink(path)

if __name__ == "__main__":
    test_full_import_workflow()
    test_import_with_multiple_folders()
    test_import_with_inactive_folders()
    test_error_handling_on_corrupted_db()
    print("All integration tests passed!")

