"""
Integration tests for job execution
"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app


class TestJobExecution:
    """Tests for job execution functionality"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    def test_run_job_success(self, client):
        """Test running a job successfully"""
        # Create a folder first
        folder_data = {
            "alias": "Test Folder",
            "folder_name": "/tmp/test",
            "folder_is_active": True,
            "process_backend_copy': True,
        }
        folder_response = client.post("/api/folders/", json=folder_data)
        folder_id = folder_response.json()['id']

        # Create job
        job_data = {
            "folder_id": folder_id,
            "cron_expression": "0 9 * * *",  # Daily at 9am
            "enabled": True,
        }
        job_response = client.post("/api/jobs/", json=job_data)

        # Run job
        run_response = client.post(f"/api/jobs/{folder_id}/run")

        assert run_response.status_code == 200
        data = run_response.json()
        assert "message" in data

    def test_run_job_manual_disabled_folder(self, client):
        """Test running job on disabled folder should fail"""
        # Create a disabled folder
        folder_data = {
            "alias": "Disabled Folder",
            "folder_name": "/tmp/test",
            "folder_is_active": False,
        }
        folder_response = client.post("/api/folders/", json=folder_data)
        folder_id = folder_response.json()['id']

        # Create and enable job
        job_data = {
            "folder_id": folder_id,
            "cron_expression": "0 9 * * *",
            "enabled": True,
        }

        job_response = client.post("/api/jobs/", json=job_data)

        # Try to run job - should fail due to disabled folder
        run_response = client.post(f"/api/jobs/{folder_id}/run")

        assert run_response.status_code == 400  # Should fail

    def test_toggle_job(self, client):
        """Test toggling job enabled/disabled"""
        # Create a folder and job
        folder_data = {
            "alias": "Toggle Test",
            "folder_name": "/tmp/test",
            "folder_is_active": True,
        }
        folder_response = client.post("/api/folders/", json=folder_data)
        folder_id = folder_response.json()['id']

        # Create enabled job
        job_data = {
            "folder_id": folder_id,
            "cron_expression": "0 10 * * *",
            "enabled": True,
        }
        job_response = client.post("/api/jobs/", json=job_data)

        # Toggle to disable
        response = client.post(f"/api/jobs/{folder_id}/toggle")

        assert response.status_code == 200
        data = response.json()
        assert data['enabled'] is False

    def test_list_runs(self, client):
        """Test listing runs"""
        response = client.get("/api/runs/")
        assert response.status_code == 200

        runs = response.json()
        assert isinstance(runs, list)

    def test_get_run_logs(self, client):
        """Test getting run logs"""
        # Note: This will test the endpoint, but logs won't exist without actual runs
        response = client.get("/api/runs/1/logs")

        # Should return 404 since run doesn't exist
        assert response.status_code == 404
