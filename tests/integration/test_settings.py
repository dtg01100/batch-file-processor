"""
Integration tests for settings API
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app


class TestSettingsAPI:
    """Tests for settings API endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    def test_get_settings(self, client):
        """Test getting settings"""
        response = client.get("/api/settings/")
        assert response.status_code == 200

        data = response.json()
        assert "email_address" in data
        assert "enable_email" in data

    def test_update_settings(self, client):
        """Test updating settings"""
        update_data = {
            "enable_email": True,
            "email_address": "test@example.com",
            "smtp_port": 587,
        }

        response = client.put("/api/settings/", json=update_data)
        assert response.status_code == 200

        data = response.json()
        assert data["enable_email"] == True
        assert data["email_address"] == "test@example.com"

    def test_update_settings_with_password(self, client):
        """Test updating settings with password (should be encrypted)"""
        update_data = {"email_password": "test_password"}

        response = client.put("/api/settings/", json=update_data)
        assert response.status_code == 200

        data = response.json()
        # Password should be masked
        assert data.get("email_password") != "test_password"
