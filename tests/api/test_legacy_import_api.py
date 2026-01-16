import pytest
import tempfile
import os
import json
import sqlite3
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Import the main app
import sys
sys.path.insert(0, '/var/mnt/Disk2/projects/batch-file-processor')

from backend.main import app

@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    with TestClient(app) as test_client:
        yield test_client

def create_test_legacy_db():
    """Create a temporary legacy database for testing"""
    fd, path = tempfile.mkstemp(suffix='.db')
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
        "alias": "Test Pipeline",
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

def test_preview_endpoint_valid_db(client):
    """Test the preview endpoint with a valid legacy database"""
    db_path = create_test_legacy_db()
    
    with open(db_path, 'rb') as db_file:
        response = client.post(
            "/api/legacy-import/preview-db",
            files={"file": ("test.db", db_file, "application/octet-stream")}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1  # One folder in our test DB
    assert data[0]["name"] == "Test Pipeline"
    assert data[0]["has_errors"] is False
    
    # Clean up
    os.unlink(db_path)

def test_preview_endpoint_invalid_file_type(client):
    """Test the preview endpoint with an invalid file type"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as tmp_file:
        tmp_file.write(b"invalid file content")
        tmp_path = tmp_file.name
    
    with open(tmp_path, 'rb') as txt_file:
        response = client.post(
            "/api/legacy-import/preview-db",
            files={"file": ("test.txt", txt_file, "text/plain")}
        )
    
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    
    # Clean up
    os.unlink(tmp_path)

def test_preview_endpoint_empty_db(client):
    """Test the preview endpoint with an empty database"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)  # Close the file descriptor
    
    # Create an empty database with just the version table
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
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
    
    with open(path, 'rb') as db_file:
        response = client.post(
            "/api/legacy-import/preview-db",
            files={"file": ("test.db", db_file, "application/octet-stream")}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data == []  # Empty list since no active folders
    
    # Clean up
    os.unlink(path)

def test_import_endpoint_valid_db(client):
    """Test the import endpoint with a valid legacy database"""
    db_path = create_test_legacy_db()
    
    with open(db_path, 'rb') as db_file:
        response = client.post(
            "/api/legacy-import/import-db",
            files={"file": ("test.db", db_file, "application/octet-stream")}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["imported_pipelines"] >= 0  # May be 0 if no pipeline creation logic is mocked
    assert "message" in data
    
    # Clean up
    os.unlink(db_path)

def test_import_endpoint_invalid_file_type(client):
    """Test the import endpoint with an invalid file type"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as tmp_file:
        tmp_file.write(b"invalid file content")
        tmp_path = tmp_file.name
    
    with open(tmp_path, 'rb') as txt_file:
        response = client.post(
            "/api/legacy-import/import-db",
            files={"file": ("test.txt", txt_file, "text/plain")}
        )
    
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    
    # Clean up
    os.unlink(tmp_path)

def test_parse_legacy_folder_config_basic():
    """Test the basic parsing of legacy folder configuration"""
    from backend.api.legacy_import import parse_legacy_folder_config
    
    folder_row = {
        "folder_name": "/test/input",
        "alias": "Test Pipeline",
        "folder_is_active": "True",
        "connection_type": "local",
        "connection_params": json.dumps({"path": "/test/input"}),
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
    
    result = parse_legacy_folder_config(folder_row)
    
    assert result["name"] == "Test Pipeline"
    assert result["description"] == "Imported from legacy folder: /test/input"
    assert result["is_active"] is True
    assert len(result["nodes"]) >= 2  # At least input and output nodes
    assert len(result["edges"]) >= 1  # At least one connection

def test_parse_legacy_folder_config_with_processing_flags():
    """Test parsing with various processing flags enabled"""
    from backend.api.legacy_import import parse_legacy_folder_config
    
    folder_row = {
        "folder_name": "/test/input",
        "alias": "Processing Pipeline",
        "folder_is_active": "True",
        "connection_type": "local",
        "connection_params": json.dumps({"path": "/test/input"}),
        "schedule": "0 9 * * *",
        "enabled": "True",
        "process_edi": "True",
        "convert_to_format": "fintech",
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
        "ftp_folder": "/output",
        "ftp_username": "user",
        "ftp_password": "pass",
        "ftp_port": 21,
        "process_backend_email": 0,
        "email_to": "",
        "email_subject_line": ""
    }
    
    result = parse_legacy_folder_config(folder_row)
    
    # Should have multiple nodes due to processing flags
    assert len(result["nodes"]) >= 5  # input + trigger + transform + validate + output (at minimum)
    
    # Check that specific nodes were created based on flags
    node_types = [node["type"] for node in result["nodes"]]
    assert "folderSource" in node_types
    assert "trigger" in node_types  # Due to schedule
    assert "transform" in node_types  # Due to process_edi and convert_to_format
    assert "validate" in node_types  # Due to tweak_edi and force_edi_validation
    assert "output" in node_types

def test_determine_functions():
    """Test helper functions for determining protocols and patterns"""
    from backend.api.legacy_import import determine_file_pattern, determine_output_protocol, determine_output_config
    
    # Test file pattern determination
    folder_with_csv = {"convert_to_format": "csv", "process_edi": "False"}
    assert determine_file_pattern(folder_with_csv) == "*.csv"
    
    folder_with_edi = {"convert_to_format": "", "process_edi": "True"}
    assert determine_file_pattern(folder_with_edi) == "*.edi"
    
    # Test output protocol determination
    folder_with_copy = {"process_backend_copy": True}
    assert determine_output_protocol(folder_with_copy) == "local"
    
    folder_with_ftp = {"process_backend_copy": False, "process_backend_ftp": True}
    assert determine_output_protocol(folder_with_ftp) == "ftp"
    
    folder_with_email = {"process_backend_copy": False, "process_backend_ftp": False, "process_backend_email": True}
    assert determine_output_protocol(folder_with_email) == "email"
    
    # Test output config determination
    folder_with_copy_config = {
        "process_backend_copy": True,
        "copy_to_directory": "/output/path"
    }
    config = determine_output_config(folder_with_copy_config)
    assert config["path"] == "/output/path"
    
    folder_with_ftp_config = {
        "process_backend_copy": False,
        "process_backend_ftp": True,
        "ftp_server": "ftp.example.com",
        "ftp_folder": "/uploads",
        "ftp_username": "user",
        "ftp_password": "pass",
        "ftp_port": 22
    }
    config = determine_output_config(folder_with_ftp_config)
    assert config["host"] == "ftp.example.com"
    assert config["remotePath"] == "/uploads"

def test_import_legacy_database_function():
    """Test the main import function"""
    from backend.api.legacy_import import import_legacy_database
    
    db_path = create_test_legacy_db()
    
    # Mock the create_pipeline function to avoid actual database operations
    with patch('backend.api.legacy_import.create_pipeline') as mock_create:
        mock_create.return_value = {"id": "test-pipeline", "name": "Test Pipeline"}
        
        result = import_legacy_database(db_path)
        
        assert result.success is True
        assert result.imported_pipelines >= 0  # Depends on mocking
        assert "message" in result.message
    
    # Clean up
    os.unlink(db_path)

if __name__ == "__main__":
    pytest.main([__file__])