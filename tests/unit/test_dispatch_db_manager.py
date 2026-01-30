"""
Comprehensive unit tests for the dispatch database manager module.

These tests cover the DBManager, ProcessedFilesTracker, and ResendFlagManager
classes with extensive mocking of database dependencies.
"""

import datetime
from io import StringIO
from unittest.mock import MagicMock, Mock, patch, call

import pytest

# Import the module under test
from dispatch.db_manager import (
    DBManager,
    ProcessedFilesTracker,
    ResendFlagManager,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_database_connection():
    """Create a mock database connection."""
    conn = MagicMock()
    conn.query = MagicMock()
    return conn


@pytest.fixture
def mock_processed_files_db():
    """Create a mock processed files database."""
    db = MagicMock()
    db.find = MagicMock(return_value=[])
    db.count = MagicMock(return_value=0)
    db.insert_many = MagicMock()
    db.find_one = MagicMock(return_value=None)
    db.update = MagicMock()
    return db


@pytest.fixture
def mock_folders_db():
    """Create a mock folders database."""
    db = MagicMock()
    db.find = MagicMock(return_value=[])
    db.count = MagicMock(return_value=0)
    return db


@pytest.fixture
def sample_processed_file_records():
    """Provide sample processed file records for testing."""
    return [
        {
            "id": 1,
            "file_name": "test_file1.txt",
            "folder_id": 1,
            "folder_alias": "Test Folder 1",
            "file_checksum": "abc123",
            "sent_date_time": datetime.datetime.now(),
            "copy_destination": "/output/copy",
            "ftp_destination": "ftp://server/folder",
            "email_destination": "test@example.com",
            "resend_flag": False,
        },
        {
            "id": 2,
            "file_name": "test_file2.txt",
            "folder_id": 1,
            "folder_alias": "Test Folder 1",
            "file_checksum": "def456",
            "sent_date_time": datetime.datetime.now(),
            "copy_destination": "N/A",
            "ftp_destination": "N/A",
            "email_destination": "N/A",
            "resend_flag": True,
        },
        {
            "id": 3,
            "file_name": "test_file3.txt",
            "folder_id": 2,
            "folder_alias": "Test Folder 2",
            "file_checksum": "ghi789",
            "sent_date_time": datetime.datetime.now(),
            "copy_destination": "/output/copy2",
            "ftp_destination": "N/A",
            "email_destination": "N/A",
            "resend_flag": False,
        },
    ]


@pytest.fixture
def sample_folder_configs():
    """Provide sample folder configurations for testing."""
    return [
        {
            "old_id": 1,
            "alias": "Test Folder 1",
            "folder_name": "/test/folder1",
            "folder_is_active": "True",
            "process_edi": "False",
        },
        {
            "old_id": 2,
            "alias": "Test Folder 2",
            "folder_name": "/test/folder2",
            "folder_is_active": "True",
            "process_edi": "True",
        },
        {
            "old_id": 3,
            "alias": "Inactive Folder",
            "folder_name": "/test/folder3",
            "folder_is_active": "False",
            "process_edi": "False",
        },
    ]


@pytest.fixture
def sample_parameters_dict():
    """Provide sample parameters dictionary for testing."""
    return {
        "process_backend_copy": True,
        "copy_to_directory": "/output/copy",
        "process_backend_ftp": True,
        "ftp_server": "ftp.example.com",
        "ftp_folder": "/remote/folder",
        "process_backend_email": True,
        "email_to": "recipient@example.com",
    }


@pytest.fixture
def sample_parameters_dict_no_backends():
    """Provide sample parameters dictionary with no backends enabled."""
    return {
        "process_backend_copy": False,
        "copy_to_directory": "/output/copy",
        "process_backend_ftp": False,
        "ftp_server": "ftp.example.com",
        "ftp_folder": "/remote/folder",
        "process_backend_email": False,
        "email_to": "recipient@example.com",
    }


@pytest.fixture
def processed_files_tracker(mock_processed_files_db):
    """Create a ProcessedFilesTracker instance with mocked database."""
    return ProcessedFilesTracker(mock_processed_files_db)


@pytest.fixture
def resend_flag_manager(mock_processed_files_db):
    """Create a ResendFlagManager instance with mocked database."""
    return ResendFlagManager(mock_processed_files_db)


@pytest.fixture
def db_manager(mock_database_connection, mock_processed_files_db, mock_folders_db):
    """Create a DBManager instance with mocked dependencies."""
    return DBManager(
        database_connection=mock_database_connection,
        processed_files_db=mock_processed_files_db,
        folders_db=mock_folders_db,
    )


# =============================================================================
# ProcessedFilesTracker Tests
# =============================================================================

class TestProcessedFilesTracker:
    """Tests for the ProcessedFilesTracker class."""

    def test_initialization(self, processed_files_tracker, mock_processed_files_db):
        """Test ProcessedFilesTracker initializes with correct database reference."""
        assert processed_files_tracker.processed_files_db is mock_processed_files_db

    def test_get_processed_files_empty(self, processed_files_tracker, mock_processed_files_db):
        """Test get_processed_files returns empty list when no files exist."""
        mock_processed_files_db.find.return_value = []

        result = processed_files_tracker.get_processed_files()

        assert result == []
        mock_processed_files_db.find.assert_called_once()

    def test_get_processed_files_with_data(self, processed_files_tracker, mock_processed_files_db, sample_processed_file_records):
        """Test get_processed_files returns list of processed file records."""
        mock_processed_files_db.find.return_value = sample_processed_file_records

        result = processed_files_tracker.get_processed_files()

        assert len(result) == 3
        assert result[0]["file_name"] == "test_file1.txt"
        assert result[1]["file_name"] == "test_file2.txt"
        assert result[2]["file_name"] == "test_file3.txt"

    def test_get_processed_files_converts_to_dict(self, processed_files_tracker, mock_processed_files_db):
        """Test get_processed_files converts records to dictionaries."""
        # Mock records that might come from database (as Row objects)
        mock_record = MagicMock()
        mock_record.__iter__ = MagicMock(return_value=iter({
            "id": 1,
            "file_name": "test.txt",
            "folder_id": 1,
        }.items()))
        mock_processed_files_db.find.return_value = [mock_record]

        result = processed_files_tracker.get_processed_files()

        assert len(result) == 1
        assert isinstance(result[0], dict)

    def test_mark_as_processed_with_all_backends(self, processed_files_tracker, sample_parameters_dict):
        """Test mark_as_processed creates correct record with all backends enabled."""
        with patch("dispatch.db_manager.datetime.datetime") as mock_datetime:
            mock_now = datetime.datetime(2024, 1, 15, 10, 30, 0)
            mock_datetime.now.return_value = mock_now

            result = processed_files_tracker.mark_as_processed(
                file_name="test_file.txt",
                folder_id=1,
                folder_alias="Test Folder",
                file_checksum="abc123",
                parameters_dict=sample_parameters_dict,
            )

        assert result["file_name"] == "test_file.txt"
        assert result["folder_id"] == 1
        assert result["folder_alias"] == "Test Folder"
        assert result["file_checksum"] == "abc123"
        assert result["sent_date_time"] == mock_now
        assert result["copy_destination"] == "/output/copy"
        assert result["ftp_destination"] == "ftp.example.com/remote/folder"
        assert result["email_destination"] == "recipient@example.com"
        assert result["resend_flag"] is False

    def test_mark_as_processed_with_no_backends(self, processed_files_tracker, sample_parameters_dict_no_backends):
        """Test mark_as_processed creates record with N/A for disabled backends."""
        with patch("dispatch.db_manager.datetime.datetime") as mock_datetime:
            mock_now = datetime.datetime(2024, 1, 15, 10, 30, 0)
            mock_datetime.now.return_value = mock_now

            result = processed_files_tracker.mark_as_processed(
                file_name="test_file.txt",
                folder_id=1,
                folder_alias="Test Folder",
                file_checksum="abc123",
                parameters_dict=sample_parameters_dict_no_backends,
            )

        assert result["copy_destination"] == "N/A"
        assert result["ftp_destination"] == "N/A"
        assert result["email_destination"] == "N/A"

    def test_mark_as_processed_file_name_conversion(self, processed_files_tracker, sample_parameters_dict):
        """Test mark_as_processed converts file_name to string."""
        result = processed_files_tracker.mark_as_processed(
            file_name=123,  # Non-string file name
            folder_id=1,
            folder_alias="Test Folder",
            file_checksum="abc123",
            parameters_dict=sample_parameters_dict,
        )

        assert result["file_name"] == "123"
        assert isinstance(result["file_name"], str)

    def test_is_resend_true(self, processed_files_tracker, mock_processed_files_db):
        """Test is_resend returns True when file has resend flag."""
        mock_processed_files_db.count.return_value = 1

        result = processed_files_tracker.is_resend("test_file.txt")

        assert result is True
        mock_processed_files_db.count.assert_called_once_with(
            file_name="test_file.txt", resend_flag=True
        )

    def test_is_resend_false(self, processed_files_tracker, mock_processed_files_db):
        """Test is_resend returns False when file has no resend flag."""
        mock_processed_files_db.count.return_value = 0

        result = processed_files_tracker.is_resend("test_file.txt")

        assert result is False
        mock_processed_files_db.count.assert_called_once_with(
            file_name="test_file.txt", resend_flag=True
        )

    def test_is_resend_with_path_object(self, processed_files_tracker, mock_processed_files_db):
        """Test is_resend handles Path objects by converting to string."""
        from pathlib import Path
        mock_processed_files_db.count.return_value = 0

        result = processed_files_tracker.is_resend(Path("/path/to/file.txt"))

        assert result is False
        mock_processed_files_db.count.assert_called_once_with(
            file_name="/path/to/file.txt", resend_flag=True
        )

    def test_clear_resend_flag_when_exists(self, processed_files_tracker, mock_processed_files_db):
        """Test clear_resend_flag clears flag when file has resend flag."""
        mock_processed_files_db.count.return_value = 1
        mock_processed_files_db.find_one.return_value = {"id": 42, "file_name": "test.txt"}

        processed_files_tracker.clear_resend_flag("test_file.txt")

        mock_processed_files_db.update.assert_called_once_with(
            {"resend_flag": False, "id": 42}, ["id"]
        )

    def test_clear_resend_flag_when_not_exists(self, processed_files_tracker, mock_processed_files_db):
        """Test clear_resend_flag does nothing when file has no resend flag."""
        mock_processed_files_db.count.return_value = 0

        processed_files_tracker.clear_resend_flag("test_file.txt")

        mock_processed_files_db.update.assert_not_called()

    def test_insert_many_with_records(self, processed_files_tracker, mock_processed_files_db):
        """Test insert_many inserts records into database."""
        records = [
            {"file_name": "file1.txt", "folder_id": 1},
            {"file_name": "file2.txt", "folder_id": 1},
        ]

        processed_files_tracker.insert_many(records)

        mock_processed_files_db.insert_many.assert_called_once_with(records)

    def test_insert_many_with_empty_list(self, processed_files_tracker, mock_processed_files_db):
        """Test insert_many does nothing with empty list."""
        processed_files_tracker.insert_many([])

        mock_processed_files_db.insert_many.assert_not_called()

    def test_insert_many_with_none(self, processed_files_tracker, mock_processed_files_db):
        """Test insert_many does nothing with None."""
        processed_files_tracker.insert_many(None)

        mock_processed_files_db.insert_many.assert_not_called()

    def test_update_by_folder(self, processed_files_tracker, mock_processed_files_db):
        """Test update_by_folder updates records for specific folder."""
        processed_files_tracker.update_by_folder(folder_id=5)

        mock_processed_files_db.update.assert_called_once_with(
            {"resend_flag": False, "folder_id": 5}, ["folder_id"]
        )


# =============================================================================
# ResendFlagManager Tests
# =============================================================================

class TestResendFlagManager:
    """Tests for the ResendFlagManager class."""

    def test_initialization(self, resend_flag_manager, mock_processed_files_db):
        """Test ResendFlagManager initializes with correct database reference."""
        assert resend_flag_manager.processed_files_db is mock_processed_files_db

    def test_check_resend_flag_true(self, resend_flag_manager):
        """Test check_resend_flag returns True when checksum is in resend set."""
        resend_set = {"abc123", "def456"}

        result = resend_flag_manager.check_resend_flag("abc123", resend_set)

        assert result is True

    def test_check_resend_flag_false(self, resend_flag_manager):
        """Test check_resend_flag returns False when checksum is not in resend set."""
        resend_set = {"abc123", "def456"}

        result = resend_flag_manager.check_resend_flag("xyz789", resend_set)

        assert result is False

    def test_check_resend_flag_empty_set(self, resend_flag_manager):
        """Test check_resend_flag returns False with empty resend set."""
        result = resend_flag_manager.check_resend_flag("abc123", set())

        assert result is False

    def test_get_resend_files_with_resend_flags(self, resend_flag_manager, sample_processed_file_records):
        """Test get_resend_files returns set of checksums with resend flag."""
        result = resend_flag_manager.get_resend_files(sample_processed_file_records)

        assert result == {"def456"}

    def test_get_resend_files_no_resend_flags(self, resend_flag_manager):
        """Test get_resend_files returns empty set when no resend flags."""
        records = [
            {"file_checksum": "abc123", "resend_flag": False},
            {"file_checksum": "def456", "resend_flag": False},
        ]

        result = resend_flag_manager.get_resend_files(records)

        assert result == set()

    def test_get_resend_files_multiple_resend_flags(self, resend_flag_manager):
        """Test get_resend_files handles multiple files with resend flags."""
        records = [
            {"file_checksum": "abc123", "resend_flag": True},
            {"file_checksum": "def456", "resend_flag": True},
            {"file_checksum": "ghi789", "resend_flag": False},
        ]

        result = resend_flag_manager.get_resend_files(records)

        assert result == {"abc123", "def456"}

    def test_get_resend_files_empty_list(self, resend_flag_manager):
        """Test get_resend_files returns empty set for empty list."""
        result = resend_flag_manager.get_resend_files([])

        assert result == set()

    def test_get_resend_files_missing_resend_flag_key(self, resend_flag_manager):
        """Test get_resend_files handles records without resend_flag key."""
        records = [
            {"file_checksum": "abc123"},  # No resend_flag key
            {"file_checksum": "def456", "resend_flag": True},
        ]

        result = resend_flag_manager.get_resend_files(records)

        assert result == {"def456"}

    def test_get_resend_files_with_none_resend_flag(self, resend_flag_manager):
        """Test get_resend_files handles records with None resend_flag."""
        records = [
            {"file_checksum": "abc123", "resend_flag": None},
            {"file_checksum": "def456", "resend_flag": True},
        ]

        result = resend_flag_manager.get_resend_files(records)

        assert result == {"def456"}


# =============================================================================
# DBManager Initialization Tests
# =============================================================================

class TestDBManagerInitialization:
    """Tests for DBManager initialization."""

    def test_init_with_dependencies(self, db_manager, mock_database_connection, mock_processed_files_db, mock_folders_db):
        """Test DBManager initializes with correct dependencies."""
        assert db_manager.database_connection is mock_database_connection
        assert db_manager.processed_files_db is mock_processed_files_db
        assert db_manager.folders_db is mock_folders_db

    def test_init_creates_tracker(self, db_manager, mock_processed_files_db):
        """Test DBManager creates ProcessedFilesTracker instance."""
        assert isinstance(db_manager.tracker, ProcessedFilesTracker)
        assert db_manager.tracker.processed_files_db is mock_processed_files_db

    def test_init_creates_resend_manager(self, db_manager, mock_processed_files_db):
        """Test DBManager creates ResendFlagManager instance."""
        assert isinstance(db_manager.resend_manager, ResendFlagManager)
        assert db_manager.resend_manager.processed_files_db is mock_processed_files_db


# =============================================================================
# DBManager Active Folders Tests
# =============================================================================

class TestDBManagerActiveFolders:
    """Tests for DBManager active folder operations."""

    def test_get_active_folders_empty(self, db_manager, mock_folders_db):
        """Test get_active_folders returns empty list when no active folders."""
        mock_folders_db.find.return_value = []

        result = db_manager.get_active_folders()

        assert result == []
        mock_folders_db.find.assert_called_once_with(
            folder_is_active="True", order_by="alias"
        )

    def test_get_active_folders_converts_old_id(self, db_manager, mock_folders_db):
        """Test get_active_folders converts old_id to id."""
        mock_folders_db.find.return_value = [
            {"old_id": 1, "alias": "Folder 1", "folder_name": "/test1"},
            {"old_id": 2, "alias": "Folder 2", "folder_name": "/test2"},
        ]

        result = db_manager.get_active_folders()

        assert len(result) == 2
        assert result[0]["id"] == 1
        assert "old_id" not in result[0]
        assert result[1]["id"] == 2
        assert "old_id" not in result[1]

    def test_get_active_folders_handles_missing_old_id(self, db_manager, mock_folders_db):
        """Test get_active_folders handles records without old_id."""
        mock_folders_db.find.return_value = [
            {"alias": "Folder 1", "folder_name": "/test1"},  # No old_id
        ]

        result = db_manager.get_active_folders()

        assert len(result) == 1
        # Should not raise KeyError, just skip the conversion
        assert "id" not in result[0]

    def test_get_active_folders_preserves_other_fields(self, db_manager, mock_folders_db):
        """Test get_active_folders preserves all other folder fields."""
        mock_folders_db.find.return_value = [
            {
                "old_id": 5,
                "alias": "Test Folder",
                "folder_name": "/test/path",
                "folder_is_active": "True",
                "process_edi": "True",
                "custom_field": "custom_value",
            },
        ]

        result = db_manager.get_active_folders()

        assert result[0]["id"] == 5
        assert result[0]["alias"] == "Test Folder"
        assert result[0]["folder_name"] == "/test/path"
        assert result[0]["folder_is_active"] == "True"
        assert result[0]["process_edi"] == "True"
        assert result[0]["custom_field"] == "custom_value"

    def test_get_active_folder_count(self, db_manager, mock_folders_db):
        """Test get_active_folder_count returns correct count."""
        mock_folders_db.count.return_value = 5

        result = db_manager.get_active_folder_count()

        assert result == 5
        mock_folders_db.count.assert_called_once_with(folder_is_active="True")

    def test_get_active_folder_count_zero(self, db_manager, mock_folders_db):
        """Test get_active_folder_count returns zero when no active folders."""
        mock_folders_db.count.return_value = 0

        result = db_manager.get_active_folder_count()

        assert result == 0


# =============================================================================
# DBManager Processed Files Tests
# =============================================================================

class TestDBManagerProcessedFiles:
    """Tests for DBManager processed file operations."""

    def test_get_processed_files_delegates_to_tracker(self, db_manager, mock_processed_files_db):
        """Test get_processed_files delegates to tracker."""
        mock_processed_files_db.find.return_value = [
            {"file_name": "test.txt", "folder_id": 1},
        ]

        result = db_manager.get_processed_files()

        assert len(result) == 1
        assert result[0]["file_name"] == "test.txt"

    def test_cleanup_old_records(self, db_manager, mock_database_connection):
        """Test cleanup_old_records executes correct SQL query."""
        db_manager.cleanup_old_records(folder_id=3)

        mock_database_connection.query.assert_called_once()
        call_args = mock_database_connection.query.call_args[0][0]
        assert "DELETE FROM processed_files" in call_args
        assert "folder_id=3" in call_args
        assert "ORDER BY id DESC LIMIT -1 OFFSET 5000" in call_args

    def test_cleanup_old_records_different_folder(self, db_manager, mock_database_connection):
        """Test cleanup_old_records with different folder ID."""
        db_manager.cleanup_old_records(folder_id=42)

        call_args = mock_database_connection.query.call_args[0][0]
        assert "folder_id=42" in call_args

    def test_insert_processed_files_delegates_to_tracker(self, db_manager, mock_processed_files_db):
        """Test insert_processed_files delegates to tracker."""
        records = [
            {"file_name": "file1.txt", "folder_id": 1},
            {"file_name": "file2.txt", "folder_id": 1},
        ]

        db_manager.insert_processed_files(records)

        mock_processed_files_db.insert_many.assert_called_once_with(records)

    def test_insert_processed_files_empty_list(self, db_manager, mock_processed_files_db):
        """Test insert_processed_files with empty list."""
        db_manager.insert_processed_files([])

        mock_processed_files_db.insert_many.assert_not_called()

    def test_update_folder_records_delegates_to_tracker(self, db_manager, mock_processed_files_db):
        """Test update_folder_records delegates to tracker."""
        db_manager.update_folder_records(folder_id=7)

        mock_processed_files_db.update.assert_called_once_with(
            {"resend_flag": False, "folder_id": 7}, ["folder_id"]
        )


# =============================================================================
# DBManager Integration Tests
# =============================================================================

class TestDBManagerIntegration:
    """Integration tests for DBManager workflows."""

    def test_full_workflow_get_active_and_processed(self, db_manager, mock_folders_db, mock_processed_files_db):
        """Test complete workflow of getting active folders and processed files."""
        # Setup mock data
        mock_folders_db.find.return_value = [
            {"old_id": 1, "alias": "Folder 1", "folder_name": "/test1"},
            {"old_id": 2, "alias": "Folder 2", "folder_name": "/test2"},
        ]
        mock_processed_files_db.find.return_value = [
            {"file_name": "file1.txt", "folder_id": 1, "file_checksum": "hash1", "resend_flag": False},
            {"file_name": "file2.txt", "folder_id": 2, "file_checksum": "hash2", "resend_flag": True},
        ]

        # Get active folders
        folders = db_manager.get_active_folders()
        assert len(folders) == 2

        # Get processed files
        processed = db_manager.get_processed_files()
        assert len(processed) == 2

        # Build resend set
        resend_set = db_manager.resend_manager.get_resend_files(processed)
        # Verify that hash2 is in the resend set (it has resend_flag=True)
        assert resend_set == {"hash2"}

    def test_resend_workflow(self, db_manager, mock_processed_files_db):
        """Test complete resend flag workflow."""
        # Setup: File has resend flag
        mock_processed_files_db.count.return_value = 1
        mock_processed_files_db.find_one.return_value = {"id": 10, "file_name": "test.txt"}

        # Check if should resend
        should_resend = db_manager.tracker.is_resend("test.txt")
        assert should_resend is True

        # Clear the resend flag
        db_manager.tracker.clear_resend_flag("test.txt")

        # Verify update was called
        mock_processed_files_db.update.assert_called_with(
            {"resend_flag": False, "id": 10}, ["id"]
        )

    def test_folder_cleanup_workflow(self, db_manager, mock_database_connection, mock_processed_files_db):
        """Test folder cleanup and update workflow."""
        folder_id = 5

        # Cleanup old records
        db_manager.cleanup_old_records(folder_id)
        assert mock_database_connection.query.called

        # Update folder records (clear resend flags)
        db_manager.update_folder_records(folder_id)
        mock_processed_files_db.update.assert_called_with(
            {"resend_flag": False, "folder_id": folder_id}, ["folder_id"]
        )

    def test_batch_insert_workflow(self, db_manager, mock_processed_files_db, sample_parameters_dict):
        """Test batch insert of processed files."""
        # Create multiple records
        records = []
        for i in range(5):
            record = db_manager.tracker.mark_as_processed(
                file_name=f"file{i}.txt",
                folder_id=1,
                folder_alias="Test Folder",
                file_checksum=f"hash{i}",
                parameters_dict=sample_parameters_dict,
            )
            records.append(record)

        # Insert all records
        db_manager.insert_processed_files(records)

        # Verify batch insert
        mock_processed_files_db.insert_many.assert_called_once_with(records)
        assert len(records) == 5


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Tests for error handling in database operations."""

    def test_processed_files_db_error_on_find(self, processed_files_tracker, mock_processed_files_db):
        """Test handling of database error during get_processed_files."""
        mock_processed_files_db.find.side_effect = Exception("Database error")

        with pytest.raises(Exception) as exc_info:
            processed_files_tracker.get_processed_files()

        assert "Database error" in str(exc_info.value)

    def test_processed_files_db_error_on_count(self, processed_files_tracker, mock_processed_files_db):
        """Test handling of database error during is_resend."""
        mock_processed_files_db.count.side_effect = Exception("Count error")

        with pytest.raises(Exception) as exc_info:
            processed_files_tracker.is_resend("test.txt")

        assert "Count error" in str(exc_info.value)

    def test_processed_files_db_error_on_insert(self, processed_files_tracker, mock_processed_files_db):
        """Test handling of database error during insert_many."""
        mock_processed_files_db.insert_many.side_effect = Exception("Insert error")

        with pytest.raises(Exception) as exc_info:
            processed_files_tracker.insert_many([{"file_name": "test.txt"}])

        assert "Insert error" in str(exc_info.value)

    def test_processed_files_db_error_on_update(self, processed_files_tracker, mock_processed_files_db):
        """Test handling of database error during update."""
        mock_processed_files_db.count.return_value = 1
        mock_processed_files_db.find_one.return_value = {"id": 1}
        mock_processed_files_db.update.side_effect = Exception("Update error")

        with pytest.raises(Exception) as exc_info:
            processed_files_tracker.clear_resend_flag("test.txt")

        assert "Update error" in str(exc_info.value)

    def test_folders_db_error_on_find(self, db_manager, mock_folders_db):
        """Test handling of database error during get_active_folders."""
        mock_folders_db.find.side_effect = Exception("Find error")

        with pytest.raises(Exception) as exc_info:
            db_manager.get_active_folders()

        assert "Find error" in str(exc_info.value)

    def test_folders_db_error_on_count(self, db_manager, mock_folders_db):
        """Test handling of database error during get_active_folder_count."""
        mock_folders_db.count.side_effect = Exception("Count error")

        with pytest.raises(Exception) as exc_info:
            db_manager.get_active_folder_count()

        assert "Count error" in str(exc_info.value)

    def test_database_connection_error_on_cleanup(self, db_manager, mock_database_connection):
        """Test handling of database error during cleanup_old_records."""
        mock_database_connection.query.side_effect = Exception("Query error")

        with pytest.raises(Exception) as exc_info:
            db_manager.cleanup_old_records(folder_id=1)

        assert "Query error" in str(exc_info.value)

    def test_clear_resend_flag_find_one_error(self, processed_files_tracker, mock_processed_files_db):
        """Test handling of error when find_one fails in clear_resend_flag."""
        mock_processed_files_db.count.return_value = 1
        mock_processed_files_db.find_one.side_effect = Exception("Find one error")

        with pytest.raises(Exception) as exc_info:
            processed_files_tracker.clear_resend_flag("test.txt")

        assert "Find one error" in str(exc_info.value)


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_get_resend_files_with_duplicate_checksums(self, resend_flag_manager):
        """Test get_resend_files handles duplicate checksums correctly."""
        records = [
            {"file_checksum": "abc123", "resend_flag": True},
            {"file_checksum": "abc123", "resend_flag": True},  # Duplicate
            {"file_checksum": "def456", "resend_flag": True},
        ]

        result = resend_flag_manager.get_resend_files(records)

        # Set should only contain unique checksums
        assert result == {"abc123", "def456"}
        assert len(result) == 2

    def test_mark_as_processed_with_empty_parameters(self, processed_files_tracker):
        """Test mark_as_processed with minimal parameters."""
        parameters_dict = {
            "process_backend_copy": False,
            "copy_to_directory": "",
            "process_backend_ftp": False,
            "ftp_server": "",
            "ftp_folder": "",
            "process_backend_email": False,
            "email_to": "",
        }

        result = processed_files_tracker.mark_as_processed(
            file_name="test.txt",
            folder_id=1,
            folder_alias="",
            file_checksum="",
            parameters_dict=parameters_dict,
        )

        assert result["copy_destination"] == "N/A"
        assert result["ftp_destination"] == "N/A"
        assert result["email_destination"] == "N/A"

    def test_check_resend_flag_with_empty_checksum(self, resend_flag_manager):
        """Test check_resend_flag with empty string checksum."""
        resend_set = {"", "abc123"}

        result = resend_flag_manager.check_resend_flag("", resend_set)

        assert result is True

    def test_get_active_folders_with_special_characters(self, db_manager, mock_folders_db):
        """Test get_active_folders with special characters in data."""
        mock_folders_db.find.return_value = [
            {
                "old_id": 1,
                "alias": "Folder with ñ and ü",
                "folder_name": "/test/path with spaces",
            },
            {
                "old_id": 2,
                "alias": "Folder\nwith\nnewlines",
                "folder_name": "/test/path\twith\ttabs",
            },
        ]

        result = db_manager.get_active_folders()

        assert len(result) == 2
        assert result[0]["alias"] == "Folder with ñ and ü"
        assert result[1]["alias"] == "Folder\nwith\nnewlines"

    def test_large_batch_insert(self, processed_files_tracker, mock_processed_files_db):
        """Test insert_many with large number of records."""
        records = [{"file_name": f"file{i}.txt", "folder_id": 1} for i in range(1000)]

        processed_files_tracker.insert_many(records)

        mock_processed_files_db.insert_many.assert_called_once_with(records)

    def test_is_resend_with_very_long_filename(self, processed_files_tracker, mock_processed_files_db):
        """Test is_resend with very long file name."""
        long_name = "a" * 1000 + ".txt"
        mock_processed_files_db.count.return_value = 0

        result = processed_files_tracker.is_resend(long_name)

        assert result is False
        mock_processed_files_db.count.assert_called_once_with(
            file_name=long_name, resend_flag=True
        )

    def test_cleanup_old_records_with_zero_folder_id(self, db_manager, mock_database_connection):
        """Test cleanup_old_records with folder_id of 0."""
        db_manager.cleanup_old_records(folder_id=0)

        call_args = mock_database_connection.query.call_args[0][0]
        assert "folder_id=0" in call_args

    def test_cleanup_old_records_with_negative_folder_id(self, db_manager, mock_database_connection):
        """Test cleanup_old_records with negative folder_id."""
        db_manager.cleanup_old_records(folder_id=-1)

        call_args = mock_database_connection.query.call_args[0][0]
        assert "folder_id=-1" in call_args


# =============================================================================
# Concurrency and Thread Safety Tests
# =============================================================================

class TestConcurrency:
    """Tests for concurrent access scenarios."""

    def test_multiple_tracker_instances_same_db(self, mock_processed_files_db):
        """Test multiple tracker instances using same database."""
        tracker1 = ProcessedFilesTracker(mock_processed_files_db)
        tracker2 = ProcessedFilesTracker(mock_processed_files_db)

        tracker1.insert_many([{"file_name": "file1.txt"}])
        tracker2.insert_many([{"file_name": "file2.txt"}])

        assert mock_processed_files_db.insert_many.call_count == 2

    def test_tracker_and_manager_share_db(self, mock_processed_files_db):
        """Test that tracker and resend manager share the same database reference."""
        tracker = ProcessedFilesTracker(mock_processed_files_db)
        manager = ResendFlagManager(mock_processed_files_db)

        assert tracker.processed_files_db is manager.processed_files_db

    def test_db_manager_components_share_db(self, db_manager, mock_processed_files_db):
        """Test that DBManager components share database references."""
        assert db_manager.tracker.processed_files_db is mock_processed_files_db
        assert db_manager.resend_manager.processed_files_db is mock_processed_files_db
        assert db_manager.processed_files_db is mock_processed_files_db


# =============================================================================
# Data Consistency Tests
# =============================================================================

class TestDataConsistency:
    """Tests for data consistency across operations."""

    def test_folder_id_consistency(self, db_manager, mock_folders_db, mock_processed_files_db):
        """Test that folder IDs remain consistent across operations."""
        mock_folders_db.find.return_value = [
            {"old_id": 42, "alias": "Test Folder", "folder_name": "/test"},
        ]
        mock_processed_files_db.find.return_value = [
            {"file_name": "file.txt", "folder_id": 42},
        ]

        folders = db_manager.get_active_folders()
        assert folders[0]["id"] == 42

        processed = db_manager.get_processed_files()
        assert processed[0]["folder_id"] == 42

    def test_resend_flag_consistency(self, resend_flag_manager, processed_files_tracker):
        """Test resend flag consistency between manager and tracker."""
        records = [
            {"file_checksum": "hash1", "resend_flag": True},
            {"file_checksum": "hash2", "resend_flag": False},
            {"file_checksum": "hash3", "resend_flag": True},
        ]

        resend_set = resend_flag_manager.get_resend_files(records)

        assert resend_flag_manager.check_resend_flag("hash1", resend_set) is True
        assert resend_flag_manager.check_resend_flag("hash2", resend_set) is False
        assert resend_flag_manager.check_resend_flag("hash3", resend_set) is True

    def test_timestamp_in_processed_record(self, processed_files_tracker, sample_parameters_dict):
        """Test that processed records have consistent timestamps."""
        fixed_time = datetime.datetime(2024, 6, 15, 12, 0, 0)

        with patch("dispatch.db_manager.datetime.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_time

            record1 = processed_files_tracker.mark_as_processed(
                file_name="file1.txt",
                folder_id=1,
                folder_alias="Folder",
                file_checksum="hash1",
                parameters_dict=sample_parameters_dict,
            )
            record2 = processed_files_tracker.mark_as_processed(
                file_name="file2.txt",
                folder_id=1,
                folder_alias="Folder",
                file_checksum="hash2",
                parameters_dict=sample_parameters_dict,
            )

        assert record1["sent_date_time"] == fixed_time
        assert record2["sent_date_time"] == fixed_time
        assert record1["sent_date_time"] == record2["sent_date_time"]


# =============================================================================
# Backward Compatibility Tests
# =============================================================================

class TestBackwardCompatibility:
    """Tests for backward compatibility with existing code."""

    def test_folder_id_conversion_backward_compatible(self, db_manager, mock_folders_db):
        """Test that folder ID conversion works for backward compatibility."""
        # Old format with old_id
        mock_folders_db.find.return_value = [
            {"old_id": 1, "alias": "Old Style"},
            {"id": 2, "alias": "New Style"},  # Already has id
        ]

        result = db_manager.get_active_folders()

        # Both should work
        assert result[0]["id"] == 1
        assert result[1].get("id") == 2 or result[1].get("old_id") is None

    def test_parameters_dict_with_extra_fields(self, processed_files_tracker):
        """Test mark_as_processed handles parameters dict with extra fields."""
        parameters_dict = {
            "process_backend_copy": True,
            "copy_to_directory": "/output",
            "process_backend_ftp": False,
            "ftp_server": "",
            "ftp_folder": "",
            "process_backend_email": False,
            "email_to": "",
            "extra_field_1": "extra_value_1",
            "extra_field_2": 12345,
        }

        result = processed_files_tracker.mark_as_processed(
            file_name="test.txt",
            folder_id=1,
            folder_alias="Test",
            file_checksum="hash",
            parameters_dict=parameters_dict,
        )

        # Should not fail and should set known fields
        assert result["copy_destination"] == "/output"
        assert result["ftp_destination"] == "N/A"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
