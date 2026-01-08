"""
Integration tests for API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app
import json


class TestFoldersAPI:
    """Tests for folders API endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    def test_list_folders_empty(self, client):
        """Test listing folders when database is empty"""
        response = client.get("/api/folders/")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_folder(self, client):
        """Test creating a folder"""
        folder_data = {
            "alias": "Test Folder",
            "folder_name": "/tmp/test",
            "folder_is_active": True,
            "connection_type": "local",
            "connection_params": {},
            "schedule": "0 9 * * *",
            "enabled": True
        }

        response = client.post("/api/folders/", json=folder_data)
        assert response.status_code == 200

        data = response.json()
        assert data['alias'] == "Test Folder"
        assert 'id' in data

    def test_get_folder_not_found(self, client):
        """Test getting a non-existent folder"""
        response = client.get("/api/folders/999")
        assert response.status_code == 404

    def test_update_folder(self, client):
        """Test updating a folder"""
        # Create folder first
        create_data = {
            "alias": "Original",
            "folder_name": "/tmp/test",
            "folder_is_active": True
        }
        create_response = client.post("/api/folders/", json=create_data)
        folder_id = create_response.json()['id']

        # Update folder
        update_data = {
            "alias": "Updated"
            "folder_is_active": False
        }
        response = client.put(f"/api/folders/{folder_id}", json=update_data)
        assert response.status_code == 200

        data = response.json()
        assert data['alias'] == "Updated"
        assert data['folder_is_active'] is False

    def test_delete_folder(self, client):
        """Test deleting a folder"""
        # Create folder first
        create_data = {
            "alias": "To Delete",
            "folder_name": "/tmp/test",
            "folder_is_active": True
        }
        create_response = client.post("/api/folders/", json=create_data)
        folder_id = create_response.json()['id']

        # Delete folder
        response = client.delete(f"/api/folders/{folder_id}")
        assert response.status_code == 200

        # Verify deletion
        get_response = client.get(f"/api/folders/{folder_id}")
        assert get_response.status_code == 404


class TestHealthCheck:
    """Tests for health check endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/api/health")
        assert response.status_code == 200

        data = response.json()
        assert data['status'] == 'healthy'
        assert 'scheduler_running' in data
