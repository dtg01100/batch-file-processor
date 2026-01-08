"""
Integration tests for database import
"""

import pytest
import tempfile
import os
import json
from fastapi.testclient import TestClient
from backend.main import app


class TestDatabaseImport:
    """Tests for database import functionality"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    def test_import_db_success(self, client, tmp_path):
        """Test successful database import"""
        # Create a temporary source database
        source_db = tmp_path / "test_source.db"

        # Create minimal source database
        import dataset

        source_conn = dataset.connect(f"sqlite:///{source_db}")

        source_conn["folders"].insert(
            {
                "alias": "Test Folder 1",
                "folder_name": "/tmp/test1",
                "folder_is_active": True,
                "connection_type": "local",
                "connection_params": "{}",
            }
        )

        source_conn["folders"].insert(
            {
                "alias": "Test Folder 2",
                "folder_name": "/tmp/test2",
                "folder_is_active": True,
                "connection_type": "local",
                "connection_params": "{}",
            }
        )

        # Create target database
        target_db = tmp_path / "test_target.db"

        response = client.post("/api/import/", json={"source_db_path": str(source_db)})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "folders_imported" in data
        assert data["folders_imported"] == 2
        assert data["total_imported"] == 2

    def test_import_db_with_windows_path(self, client, tmp_path):
        """Test Windows path conversion"""
        # Create a temporary source database
        source_db = tmp_path / "test_windows.db"

        # Create source database with Windows path
        import dataset

        source_conn = dataset.connect(f"sqlite:///{source_db}")

        source_conn["folders"].insert(
            {
                "alias": "Windows Folder",
                "folder_name": "\\\\\\server\\share\\folder",
                "folder_is_active": True,
            }
        )

        # Create target database
        target_db = tmp_path / "test_target.db"

        response = client.post("/api/import/", json={"source_db_path": str(source_db)})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["folders_imported"] == 1

        # Verify Windows path was converted to SMB
        target_conn = dataset.connect(f"sqlite:///{target_db}")
        imported_folder = target_conn.get_table("folders").find_one(
            alias="Windows Folder"
        )

        assert imported_folder is not None
        assert imported_folder["connection_type"] == "smb"
        assert "host" in json.loads(imported_folder.get("connection_params", "{}"))

    def test_import_db_file_not_found(self, client):
        """Test import with non-existent database file"""
        response = client.post(
            "/api/import/", json={"source_db_path": "/nonexistent.db"}
        )

        assert response.status_code != 200

    def test_import_db_no_folder_id_map(self, client, tmp_path):
        """Test import when folder aliases don't match"""
        # Create source with different alias
        source_db = tmp_path / "test_no_match.db"

        import dataset

        source_conn = dataset.connect(f"sqlite:///{source_db}")

        source_conn["folders"].insert(
            {
                "alias": "Orphan Folder",
                "folder_name": "/tmp/orphan",
                "folder_is_active": True,
            }
        )

        source_conn["processed_files"].insert(
            {
                "file_name": "/tmp/test.txt",
                "file_checksum": "abc123",
                "folder_id": 1,  # Wrong ID
                "sent_date_time": "2024-01-01",
            }
        )

        # Create target database
        target_db = tmp_path / "test_no_match.db"

        response = client.post("/api/import/", json={"source_db_path": str(source_db)})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert (
            data["folders_errors"] == 1
        )  # Should have error due to no matching folder
