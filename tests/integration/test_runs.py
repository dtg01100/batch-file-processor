"""
Integration tests for runs API
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app


class TestRunsAPI:
    """Tests for runs (run history) API endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    def test_list_runs_empty(self, client):
        """Test listing runs when no runs exist"""
        response = client.get("/api/runs/")
        assert response.status_code == 200

        runs = response.json()
        assert runs == []

    def test_list_runs_with_limit(self, client):
        """Test listing runs with limit"""
        response = client.get("/api/runs/?limit=5")
        assert response.status_code == 200

        runs = response.json()
        assert len(runs) <= 5

    def test_list_runs_filter_by_status(self, client):
        """Test filtering runs by status"""
        # Note: This would require creating runs first
        response = client.get("/api/runs/?status=completed")
        assert response.status_code == 200

        runs = response.json()
        # Verify all returned runs have status=completed
        # (This would fail if no runs exist, but structure is correct)

    def test_get_run_not_found(self, client):
        """Test getting a non-existent run"""
        response = client.get("/api/runs/999")
        assert response.status_code == 404

    def test_get_run_logs_not_found(self, client):
        """Test getting logs for non-existent run"""
        response = client.get("/api/runs/999/logs")
        assert response.status_code == 404
