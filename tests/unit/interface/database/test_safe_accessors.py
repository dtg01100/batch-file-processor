"""Tests for safe database accessor methods.

These tests validate that the new safe accessor methods properly handle
None returns and provide defaults where appropriate.
"""
import os
import tempfile
import pytest
from interface.database.database_obj import DatabaseObj


class TestSafeDatabaseAccessors:
    """Test suite for safe database accessor methods."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db = DatabaseObj(
                database_path=db_path,
                database_version="41",
                config_folder=tmpdir,
                running_platform="Linux"
            )
            yield db
            db.close()

    def test_get_settings_or_default_returns_settings_when_exists(self, temp_db):
        """Test that get_settings_or_default returns existing settings."""
        settings = temp_db.get_settings_or_default()
        
        assert settings is not None
        assert "id" in settings
        assert settings["id"] == 1
        
    def test_get_settings_or_default_creates_when_missing(self):
        """Test that get_settings_or_default creates settings if missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            
            # Create database but manually delete settings
            db = DatabaseObj(
                database_path=db_path,
                database_version="41",
                config_folder=tmpdir,
                running_platform="Linux"
            )
            
            # Delete settings
            db.settings.delete(id=1)
            
            # Now get_settings_or_default should recreate it
            settings = db.get_settings_or_default()
            
            assert settings is not None
            assert "id" in settings
            assert settings["id"] == 1
            assert "enable_email" in settings
            
            db.close()
    
    def test_get_oversight_or_default_returns_oversight_when_exists(self, temp_db):
        """Test that get_oversight_or_default returns existing oversight."""
        oversight = temp_db.get_oversight_or_default()
        
        assert oversight is not None
        assert "id" in oversight
        assert oversight["id"] == 1
        
    def test_get_oversight_or_default_creates_when_missing(self):
        """Test that get_oversight_or_default creates oversight if missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            
            # Create database but manually delete oversight
            db = DatabaseObj(
                database_path=db_path,
                database_version="41",
                config_folder=tmpdir,
                running_platform="Linux"
            )
            
            # Delete oversight
            db.oversight_and_defaults.delete(id=1)
            
            # Now get_oversight_or_default should recreate it
            oversight = db.get_oversight_or_default()
            
            assert oversight is not None
            assert "id" in oversight
            assert oversight["id"] == 1
            assert "logs_directory" in oversight
            
            db.close()
    
    def test_find_folder_required_raises_on_missing(self, temp_db):
        """Test that find_folder_required raises ValueError when folder not found."""
        with pytest.raises(ValueError, match="Required folder not found"):
            temp_db.find_folder_required(id=99999)
    
    def test_find_folder_required_returns_folder_when_exists(self, temp_db):
        """Test that find_folder_required returns folder when it exists."""
        # First add a folder
        temp_db.folders_table.insert({
            "folder_name": "/test/path",
            "alias": "test_folder",
            "folder_is_active": True
        })
        
        # Now find it
        folder = temp_db.find_folder_required(alias="test_folder")
        
        assert folder is not None
        assert folder["alias"] == "test_folder"
    
    def test_find_folder_optional_returns_none_on_missing(self, temp_db):
        """Test that find_folder_optional returns None when folder not found."""
        result = temp_db.find_folder_optional(id=99999)
        assert result is None
    
    def test_find_folder_optional_returns_folder_when_exists(self, temp_db):
        """Test that find_folder_optional returns folder when it exists."""
        # First add a folder
        temp_db.folders_table.insert({
            "folder_name": "/test/path",
            "alias": "test_folder_2",
            "folder_is_active": True
        })
        
        # Now find it
        folder = temp_db.find_folder_optional(alias="test_folder_2")
        
        assert folder is not None
        assert folder["alias"] == "test_folder_2"


class TestBackwardCompatibility:
    """Test that old code patterns still work."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db = DatabaseObj(
                database_path=db_path,
                database_version="41",
                config_folder=tmpdir,
                running_platform="Linux"
            )
            yield db
            db.close()
    
    def test_old_find_one_still_works(self, temp_db):
        """Test that old find_one() pattern still works."""
        # This should still work for backward compatibility
        settings = temp_db.settings.find_one(id=1)
        assert settings is not None
        
    def test_old_get_default_settings_still_works(self, temp_db):
        """Test that old get_default_settings() method still works."""
        settings = temp_db.get_default_settings()
        assert settings is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
