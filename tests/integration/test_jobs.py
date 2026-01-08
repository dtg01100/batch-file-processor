"""
Integration tests for jobs API
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app


class TestJobsAPI:
    """Tests for jobs API endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    def test_list_jobs(self, client):
        """Test listing jobs"""
        response = client.get("/api/jobs/")
        assert response.status_code == 200

        jobs = response.json()
        assert isinstance(jobs, list)

    def test_create_job_valid(self, client):
        """Test creating a valid job"""
        # First create a folder
        folder_data = {
            "alias": "Test Folder",
            "folder_name": "/tmp/test",
            "folder_is_active": True,
        }
        create_response = client.post("/api/folders/", json=folder_data)
        folder_id = create_response.json()["id"]

        # Create job
        job_data = {
            "folder_id": folder_id,
            "cron_expression": "0 9 * * *",  # Daily at 9am
            "enabled": True,
        }

        response = client.post("/api/jobs/", json=job_data)
        assert response.status_code == 200

        data = response.json()
        assert data["folder_alias"] == "Test Folder"
        assert data["enabled"] == True

    def test_create_job_invalid_cron(self, client):
        """Test creating job with invalid cron expression"""
        # Create folder first
        folder_data = {
            "alias": "Test Folder",
            "folder_name": "/tmp/test",
            "folder_is_active": True,
        }
        create_response = client.post("/api/folders/", json=folder_data)
        folder_id = create_response.json()["id"]

        # Create job with invalid cron
        job_data = {
            "folder_id": folder_id,
            "cron_expression": "invalid",
            "enabled": True,
        }

        response = client.post("/api/jobs/", json=job_data)
        assert response.status_code == 400

    def test_toggle_job(self, client):
        """Test toggling job enabled/disabled"""
        # Create folder and job
        folder_data = {
            "alias": "Toggle Test",
            "folder_name": "/tmp/test",
            "folder_is_active": True,
        }
        folder_response = client.post("/api/folders/", json=folder_data)
        folder_id = folder_response.json()["id"]

        job_data = {
            "folder_id": folder_id,
            "cron_expression": "0 9 * * *",
            "enabled": True,
        }
        job_response = client.post("/api/jobs/", json=job_data)

        # Toggle job
        response = client.post(f"/api/jobs/{folder_id}/toggle")
        assert response.status_code == 200

        data = response.json()
        assert data["enabled"] == False  # Should be disabled

    def test_delete_job(self, client):
        """Test deleting (disabling) a job"""
        # Create folder and job
        folder_data = {
            "alias": "Delete Test",
            "folder_name": "/tmp/test",
            "folder_is_active": True,
        }
        folder_response = client.post("/api/folders/", json=folder_data)
        folder_id = folder_response.json()["id"]

        job_data = {
            "folder_id": folder_id,
            "cron_expression": "0 9 * * *",
            "enabled": True,
        }
        job_response = client.post("/api/jobs/", json=job_data)

        # Delete job
        response = client.delete(f"/api/jobs/{folder_id}")
        assert response.status_code == 200

        data = response.json()
        assert "message" in data
