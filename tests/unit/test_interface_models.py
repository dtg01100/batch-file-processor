"""
Unit tests for interface.models module.

Tests for Folder, ProcessedFile, and Settings dataclass models.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock

from interface.models.folder import Folder
from interface.models.processed_file import ProcessedFile
from interface.models.settings import Settings


class TestFolderModel:
    """Tests for Folder dataclass model."""

    def test_default_values(self):
        """Folder should have sensible defaults."""
        folder = Folder()

        assert folder.id is None
        assert folder.alias == ""
        assert folder.path == ""
        assert folder.active is True
        assert folder.processed is False
        assert folder.ftp_port == 21
        assert folder.ftp_passive is True

    def test_create_with_values(self):
        """Folder should accept all values."""
        folder = Folder(
            id=1,
            alias="Test Folder",
            path="/test/path",
            active=False,
            ftp_host="ftp.example.com",
            ftp_port=2121,
        )

        assert folder.id == 1
        assert folder.alias == "Test Folder"
        assert folder.path == "/test/path"
        assert folder.active is False
        assert folder.ftp_host == "ftp.example.com"
        assert folder.ftp_port == 2121

    def test_to_dict(self):
        """to_dict should return dictionary representation."""
        now = datetime.now()
        folder = Folder(
            id=1,
            alias="Test",
            path="/test",
            created_at=now,
            updated_at=now,
        )

        result = folder.to_dict()

        assert result["id"] == 1
        assert result["alias"] == "Test"
        assert result["path"] == "/test"
        assert result["created_at"] == now.isoformat()
        assert result["updated_at"] == now.isoformat()

    def test_to_dict_none_timestamps(self):
        """to_dict should handle None timestamps."""
        folder = Folder(id=1, alias="Test", path="/test")

        result = folder.to_dict()

        assert result["created_at"] is None
        assert result["updated_at"] is None

    def test_from_dict(self):
        """from_dict should create Folder from dictionary."""
        data = {
            "id": 1,
            "alias": "Test",
            "path": "/test",
            "active": True,
            "ftp_port": 2121,
        }

        folder = Folder.from_dict(data)

        assert folder.id == 1
        assert folder.alias == "Test"
        assert folder.path == "/test"
        assert folder.active is True
        assert folder.ftp_port == 2121

    def test_from_dict_with_string_datetime(self):
        """from_dict should parse ISO datetime strings."""
        now = datetime.now()
        data = {
            "id": 1,
            "alias": "Test",
            "path": "/test",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        folder = Folder.from_dict(data)

        assert folder.created_at == now
        assert folder.updated_at == now

    def test_from_dict_with_datetime_object(self):
        """from_dict should accept datetime objects."""
        now = datetime.now()
        data = {
            "id": 1,
            "alias": "Test",
            "path": "/test",
            "created_at": now,
            "updated_at": now,
        }

        folder = Folder.from_dict(data)

        assert folder.created_at == now
        assert folder.updated_at == now

    def test_from_dict_defaults(self):
        """from_dict should use defaults for missing keys."""
        data = {"id": 1}

        folder = Folder.from_dict(data)

        assert folder.alias == ""
        assert folder.path == ""
        assert folder.active is True
        assert folder.ftp_port == 21

    def test_is_valid_with_path_and_alias(self):
        """is_valid should return True when path and alias set."""
        folder = Folder(alias="Test", path="/test/path")

        assert folder.is_valid() is True

    def test_is_valid_without_path(self):
        """is_valid should return False when path missing."""
        folder = Folder(alias="Test")

        assert folder.is_valid() is False

    def test_is_valid_without_alias(self):
        """is_valid should return False when alias missing."""
        folder = Folder(path="/test/path")

        assert folder.is_valid() is False

    def test_roundtrip_dict_conversion(self):
        """Converting to dict and back should preserve data."""
        original = Folder(
            id=1,
            alias="Test",
            path="/test",
            active=False,
            ftp_host="ftp.example.com",
            ftp_port=2121,
            email_to="test@example.com",
        )

        result = Folder.from_dict(original.to_dict())

        assert result.id == original.id
        assert result.alias == original.alias
        assert result.path == original.path
        assert result.active == original.active
        assert result.ftp_host == original.ftp_host
        assert result.ftp_port == original.ftp_port
        assert result.email_to == original.email_to


class TestProcessedFileModel:
    """Tests for ProcessedFile dataclass model."""

    def test_default_values(self):
        """ProcessedFile should have sensible defaults."""
        pf = ProcessedFile()

        assert pf.id is None
        assert pf.folder_id == 0
        assert pf.filename == ""
        assert pf.status == "pending"

    def test_status_constants(self):
        """Status constants should be defined."""
        assert ProcessedFile.STATUS_PENDING == "pending"
        assert ProcessedFile.STATUS_PROCESSED == "processed"
        assert ProcessedFile.STATUS_FAILED == "failed"
        assert ProcessedFile.STATUS_SENT == "sent"

    def test_create_with_values(self):
        """ProcessedFile should accept all values."""
        pf = ProcessedFile(
            id=1,
            folder_id=5,
            filename="test.edi",
            original_path="/input/test.edi",
            processed_path="/output/test.csv",
            status="processed",
        )

        assert pf.id == 1
        assert pf.folder_id == 5
        assert pf.filename == "test.edi"
        assert pf.status == "processed"

    def test_to_dict(self):
        """to_dict should return dictionary representation."""
        now = datetime.now()
        pf = ProcessedFile(
            id=1,
            folder_id=5,
            filename="test.edi",
            status="pending",
            created_at=now,
        )

        result = pf.to_dict()

        assert result["id"] == 1
        assert result["folder_id"] == 5
        assert result["filename"] == "test.edi"
        assert result["status"] == "pending"
        assert result["created_at"] == now.isoformat()

    def test_from_dict(self):
        """from_dict should create ProcessedFile from dictionary."""
        data = {
            "id": 1,
            "folder_id": 5,
            "filename": "test.edi",
            "status": "processed",
        }

        pf = ProcessedFile.from_dict(data)

        assert pf.id == 1
        assert pf.folder_id == 5
        assert pf.filename == "test.edi"
        assert pf.status == "processed"

    def test_from_dict_with_string_datetime(self):
        """from_dict should parse ISO datetime strings."""
        now = datetime.now()
        data = {
            "id": 1,
            "folder_id": 5,
            "filename": "test.edi",
            "created_at": now.isoformat(),
            "processed_at": now.isoformat(),
        }

        pf = ProcessedFile.from_dict(data)

        assert pf.created_at == now
        assert pf.processed_at == now

    def test_from_dict_defaults(self):
        """from_dict should use defaults for missing keys."""
        data = {"id": 1}

        pf = ProcessedFile.from_dict(data)

        assert pf.folder_id == 0
        assert pf.filename == ""
        assert pf.status == ProcessedFile.STATUS_PENDING

    def test_get_by_folder_success(self):
        """get_by_folder should return list of ProcessedFiles."""
        mock_db = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            {"id": 1, "folder_id": 5, "filename": "test1.edi", "status": "pending"},
            {"id": 2, "folder_id": 5, "filename": "test2.edi", "status": "processed"},
        ]
        mock_db.execute.return_value = mock_cursor

        result = ProcessedFile.get_by_folder(mock_db, 5)

        assert len(result) == 2
        assert result[0].filename == "test1.edi"
        assert result[1].filename == "test2.edi"

    def test_get_by_folder_exception(self):
        """get_by_folder should return empty list on error."""
        mock_db = Mock()
        mock_db.execute.side_effect = Exception("DB Error")

        result = ProcessedFile.get_by_folder(mock_db, 5)

        assert result == []

    def test_get_by_status_success(self):
        """get_by_status should return list of ProcessedFiles."""
        mock_db = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            {"id": 1, "folder_id": 5, "filename": "test1.edi", "status": "pending"},
        ]
        mock_db.execute.return_value = mock_cursor

        result = ProcessedFile.get_by_status(mock_db, "pending")

        assert len(result) == 1
        assert result[0].status == "pending"

    def test_mark_as_processed_success(self):
        """mark_as_processed should return True on success."""
        mock_db = Mock()

        result = ProcessedFile.mark_as_processed(mock_db, 1, "/output/test.csv")

        assert result is True
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_mark_as_processed_failure(self):
        """mark_as_processed should return False on error."""
        mock_db = Mock()
        mock_db.execute.side_effect = Exception("DB Error")

        result = ProcessedFile.mark_as_processed(mock_db, 1, "/output/test.csv")

        assert result is False

    def test_mark_as_failed_success(self):
        """mark_as_failed should return True on success."""
        mock_db = Mock()

        result = ProcessedFile.mark_as_failed(mock_db, 1, "Conversion error")

        assert result is True
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_mark_as_sent_success(self):
        """mark_as_sent should return True on success."""
        mock_db = Mock()

        result = ProcessedFile.mark_as_sent(mock_db, 1, "ftp://example.com")

        assert result is True
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_create_success(self):
        """create should return ID on success."""
        mock_db = Mock()
        mock_cursor = Mock()
        mock_cursor.lastrowid = 42
        mock_db.execute.return_value = mock_cursor

        result = ProcessedFile.create(mock_db, 5, "test.edi", "/input/test.edi")

        assert result == 42
        mock_db.commit.assert_called_once()

    def test_create_failure(self):
        """create should return None on error."""
        mock_db = Mock()
        mock_db.execute.side_effect = Exception("DB Error")

        result = ProcessedFile.create(mock_db, 5, "test.edi", "/input/test.edi")

        assert result is None


class TestSettingsModel:
    """Tests for Settings dataclass model."""

    def test_default_values(self):
        """Settings should have sensible defaults."""
        settings = Settings()

        assert settings.id is None
        assert settings.key == ""
        assert settings.value == ""
        assert settings.category == "general"

    def test_setting_constants(self):
        """Setting constants should be defined."""
        assert Settings.AS400_HOST == "as400_host"
        assert Settings.SMTP_SERVER == "smtp_server"
        assert Settings.SMTP_PORT == "smtp_port"
        assert Settings.BACKUP_DIRECTORY == "backup_directory"

    def test_create_with_values(self):
        """Settings should accept all values."""
        settings = Settings(
            id=1,
            key="smtp_server",
            value="mail.example.com",
            category="email",
        )

        assert settings.id == 1
        assert settings.key == "smtp_server"
        assert settings.value == "mail.example.com"
        assert settings.category == "email"

    def test_to_dict(self):
        """to_dict should return dictionary representation."""
        now = datetime.now()
        settings = Settings(
            id=1,
            key="test_key",
            value="test_value",
            category="general",
            created_at=now,
        )

        result = settings.to_dict()

        assert result["id"] == 1
        assert result["key"] == "test_key"
        assert result["value"] == "test_value"
        assert result["created_at"] == now.isoformat()

    def test_from_dict(self):
        """from_dict should create Settings from dictionary."""
        data = {
            "id": 1,
            "key": "test_key",
            "value": "test_value",
            "category": "custom",
        }

        settings = Settings.from_dict(data)

        assert settings.id == 1
        assert settings.key == "test_key"
        assert settings.value == "test_value"
        assert settings.category == "custom"

    def test_from_dict_defaults(self):
        """from_dict should use defaults for missing keys."""
        data = {"id": 1}

        settings = Settings.from_dict(data)

        assert settings.key == ""
        assert settings.value == ""
        assert settings.category == "general"

    def test_get_success(self):
        """get should return value for key."""
        mock_db = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = ("test_value",)
        mock_db.execute.return_value = mock_cursor

        result = Settings.get(mock_db, "test_key")

        assert result == "test_value"

    def test_get_not_found(self):
        """get should return None when key not found."""
        mock_db = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None
        mock_db.execute.return_value = mock_cursor

        result = Settings.get(mock_db, "nonexistent_key")

        assert result is None

    def test_get_exception(self):
        """get should return None on error."""
        mock_db = Mock()
        mock_db.execute.side_effect = Exception("DB Error")

        result = Settings.get(mock_db, "test_key")

        assert result is None

    def test_set_insert_new(self):
        """set should insert new setting."""
        mock_db = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None  # Key doesn't exist
        mock_db.execute.return_value = mock_cursor

        result = Settings.set(mock_db, "new_key", "new_value")

        assert result is True
        assert mock_db.execute.call_count == 2  # Check + Insert
        mock_db.commit.assert_called_once()

    def test_set_update_existing(self):
        """set should update existing setting."""
        mock_db = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (1,)  # Key exists
        mock_db.execute.return_value = mock_cursor

        result = Settings.set(mock_db, "existing_key", "updated_value")

        assert result is True
        assert mock_db.execute.call_count == 2  # Check + Update
        mock_db.commit.assert_called_once()

    def test_set_failure(self):
        """set should return False on error."""
        mock_db = Mock()
        mock_db.execute.side_effect = Exception("DB Error")

        result = Settings.set(mock_db, "key", "value")

        assert result is False

    def test_get_as400_settings(self):
        """get_as400_settings should return AS400 settings dict."""
        mock_db = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.side_effect = [
            ("192.168.1.100",),  # as400_host
            ("MYLIB",),  # as400_library
            ("ADMIN",),  # as400_user
            ("iSeries Access",),  # as400_odbc_driver
        ]
        mock_db.execute.return_value = mock_cursor

        result = Settings.get_as400_settings(mock_db)

        assert Settings.AS400_HOST in result
        assert result[Settings.AS400_HOST] == "192.168.1.100"

    def test_get_email_settings(self):
        """get_email_settings should return email settings dict."""
        mock_db = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.side_effect = [
            ("smtp.gmail.com",),  # smtp_server
            ("587",),  # smtp_port
            ("user@gmail.com",),  # smtp_username
            ("from@example.com",),  # email_from
        ]
        mock_db.execute.return_value = mock_cursor

        result = Settings.get_email_settings(mock_db)

        assert Settings.SMTP_SERVER in result
        assert result[Settings.SMTP_SERVER] == "smtp.gmail.com"

    def test_get_all_by_category(self):
        """get_all_by_category should return settings for category."""
        mock_db = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            {"id": 1, "key": "key1", "value": "val1", "category": "email"},
            {"id": 2, "key": "key2", "value": "val2", "category": "email"},
        ]
        mock_db.execute.return_value = mock_cursor

        result = Settings.get_all_by_category(mock_db, "email")

        assert len(result) == 2
        assert result[0].key == "key1"
        assert result[1].key == "key2"

    def test_get_all(self):
        """get_all should return all settings."""
        mock_db = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            {"id": 1, "key": "key1", "value": "val1", "category": "general"},
            {"id": 2, "key": "key2", "value": "val2", "category": "email"},
        ]
        mock_db.execute.return_value = mock_cursor

        result = Settings.get_all(mock_db)

        assert len(result) == 2


class TestModelsIntegration:
    """Integration tests for model interactions."""

    def test_folder_with_processed_files_workflow(self):
        """Test workflow of folder with processed files."""
        # Create folder
        folder = Folder(id=1, alias="Test Folder", path="/test/input")
        assert folder.is_valid()

        # Create processed file for folder
        pf = ProcessedFile(
            id=1,
            folder_id=folder.id,
            filename="invoice.edi",
            original_path="/test/input/invoice.edi",
            status=ProcessedFile.STATUS_PENDING,
        )

        assert pf.folder_id == folder.id
        assert pf.status == ProcessedFile.STATUS_PENDING

    def test_settings_and_folder_configuration(self):
        """Test settings used with folder configuration."""
        # Simulate settings
        smtp_setting = Settings(
            key=Settings.SMTP_SERVER,
            value="smtp.example.com",
            category="email",
        )

        # Folder uses email backend
        folder = Folder(
            alias="Email Folder",
            path="/test/path",
            email_to="user@example.com",
        )

        # Both should serialize properly
        folder_dict = folder.to_dict()
        settings_dict = smtp_setting.to_dict()

        assert folder_dict["email_to"] == "user@example.com"
        assert settings_dict["value"] == "smtp.example.com"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
