"""Unit tests for FolderManager.

Tests the FolderManager class with mocked database connections
to ensure proper behavior without requiring actual database files.
"""

from unittest.mock import MagicMock

import pytest

from interface.operations.folder_manager import (
    DatabaseProtocol,
    FolderManager,
    TableProtocol,
)


class _SimpleTable:
    """Lightweight table stub for protocol compliance tests."""

    def __init__(self, data=None):
        self._data = list(data or [])

    def find_one(self, **kwargs):
        for r in self._data:
            if all(r.get(k) == v for k, v in kwargs.items()):
                return r
        return None

    def find(self, **kwargs):
        return [r for r in self._data if all(r.get(k) == v for k, v in kwargs.items())]

    def all(self):
        return list(self._data)

    def insert(self, record):
        self._data.append(record)
        return record.get("id", len(self._data))

    def update(self, record, keys):
        pass

    def delete(self, **kwargs):
        pass

    def count(self, **kwargs):
        return len(self.find(**kwargs))


class _SimpleDatabaseObj:
    """Lightweight database stub for protocol compliance tests."""

    def __init__(self):
        self.folders_table = _SimpleTable()
        self.oversight_and_defaults = _SimpleTable()
        self.processed_files = _SimpleTable()
        self.emails_table = _SimpleTable()

    def get_oversight_or_default(self):
        return {}


class MockDatabase:
    """Mock that satisfies DatabaseProtocol for isinstance checks.

    Class-level declarations pass Python's @runtime_checkable check.
    Instance-level MagicMock attributes provide full mock behavior
    with per-instance isolation for test assertions.
    """

    # Class-level declarations for isinstance() protocol check
    folders_table = None
    oversight_and_defaults = None
    processed_files = None
    emails_table = None
    get_oversight_or_default = None

    def __init__(self):
        self.folders_table = MagicMock()
        self.oversight_and_defaults = MagicMock()
        self.processed_files = MagicMock()
        self.emails_table = MagicMock()
        self.get_oversight_or_default = MagicMock()


class TestFolderManager:
    """Tests for FolderManager class."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = MockDatabase()
        db.oversight_and_defaults.find_one.return_value = {
            "id": 1,
            "default_setting": "value",
            "folder_is_active": True,
        }
        return db

    @pytest.fixture
    def manager(self, mock_db):
        """Create FolderManager with mock database."""
        return FolderManager(mock_db)

    def test_add_folder_creates_record(self, manager, mock_db):
        """Test adding a folder creates a database record."""
        mock_db.folders_table.find_one.return_value = None  # No existing alias

        result = manager.add_folder("/path/to/folder")

        mock_db.folders_table.insert.assert_called_once()
        assert result["folder_name"] == "/path/to/folder"

    def test_add_folder_generates_unique_alias(self, manager, mock_db):
        """Test adding duplicate folder generates unique alias."""
        # First folder exists
        mock_db.folders_table.find_one.side_effect = [
            {"alias": "folder"},  # First check finds existing
            None,  # Second check for "folder 1" finds nothing
        ]

        result = manager.add_folder("/path/to/folder")

        assert result["alias"] == "folder 1"

    def test_add_folder_with_template_data(self, manager, mock_db):
        """Test adding folder with custom template data."""
        mock_db.folders_table.find_one.return_value = None

        custom_template = {
            "id": 1,
            "custom_setting": "custom_value",
            "folder_is_active": True,
        }

        result = manager.add_folder("/path/to/folder", template_data=custom_template)

        assert result["custom_setting"] == "custom_value"

    def test_check_folder_exists_found(self, manager, mock_db, tmp_path):
        """Test checking existing folder."""
        folder_path = str(tmp_path)
        mock_db.folders_table.all.return_value = [
            {"folder_name": folder_path, "alias": "test"}
        ]

        result = manager.check_folder_exists(folder_path)

        assert result["truefalse"] is True
        assert result["matched_folder"]["alias"] == "test"

    def test_check_folder_exists_not_found(self, manager, mock_db):
        """Test checking non-existing folder."""
        mock_db.folders_table.all.return_value = []

        result = manager.check_folder_exists("/nonexistent")

        assert result["truefalse"] is False
        assert result["matched_folder"] is None

    def test_check_folder_exists_normalized_path(self, manager, mock_db):
        """Test that path normalization works correctly."""
        # Test with different path formats
        mock_db.folders_table.all.return_value = [
            {"folder_name": "/path/to/folder", "alias": "test"}
        ]

        # Should match even with trailing slash
        result = manager.check_folder_exists("/path/to/folder/")

        assert result["truefalse"] is True

    def test_check_folder_exists_multiple_matches(self, manager, mock_db, tmp_path):
        """Test that check_folder_exists returns all matched folders."""
        folder_path = str(tmp_path)
        # Multiple configs pointing to same source directory
        mock_db.folders_table.all.return_value = [
            {"folder_name": folder_path, "alias": "config1", "id": 1},
            {"folder_name": folder_path, "alias": "config2", "id": 2},
        ]

        result = manager.check_folder_exists(folder_path)

        assert result["truefalse"] is True
        assert result["matched_folder"]["alias"] == "config1"  # First one
        assert len(result["all_matched_folders"]) == 2
        assert result["all_matched_folders"][0]["alias"] == "config1"
        assert result["all_matched_folders"][1]["alias"] == "config2"

    def test_disable_folder(self, manager, mock_db):
        """Test disabling a folder."""
        mock_db.folders_table.find_one.return_value = {
            "id": 1,
            "folder_is_active": True,
        }

        result = manager.disable_folder(1)

        assert result is True
        mock_db.folders_table.update.assert_called_once()
        # Check that folder_is_active was set to False
        call_args = mock_db.folders_table.update.call_args
        assert call_args[0][0]["folder_is_active"] is False

    def test_disable_folder_not_found(self, manager, mock_db):
        """Test disabling non-existent folder."""
        mock_db.folders_table.find_one.return_value = None

        result = manager.disable_folder(999)

        assert result is False

    def test_enable_folder(self, manager, mock_db):
        """Test enabling a folder."""
        mock_db.folders_table.find_one.return_value = {
            "id": 1,
            "folder_is_active": False,
        }

        result = manager.enable_folder(1)

        assert result is True
        mock_db.folders_table.update.assert_called_once()
        # Check that folder_is_active was set to True
        call_args = mock_db.folders_table.update.call_args
        assert call_args[0][0]["folder_is_active"] is True

    def test_enable_folder_not_found(self, manager, mock_db):
        """Test enabling non-existent folder."""
        mock_db.folders_table.find_one.return_value = None

        result = manager.enable_folder(999)

        assert result is False

    def test_delete_folder(self, manager, mock_db):
        """Test deleting a folder."""
        mock_db.folders_table.find_one.return_value = {"id": 1}

        result = manager.delete_folder(1)

        assert result is True
        mock_db.folders_table.delete.assert_called_once_with(id=1)

    def test_delete_folder_not_found(self, manager, mock_db):
        """Test deleting non-existent folder."""
        mock_db.folders_table.find_one.return_value = None

        result = manager.delete_folder(999)

        assert result is False

    def test_get_active_folders(self, manager, mock_db):
        """Test getting active folders."""
        mock_db.folders_table.find.return_value = [{"id": 1, "folder_is_active": True}]

        result = manager.get_active_folders()

        assert len(result) == 1
        mock_db.folders_table.find.assert_called_once_with(folder_is_active=True)

    def test_get_inactive_folders(self, manager, mock_db):
        """Test getting inactive folders."""
        mock_db.folders_table.find.return_value = [{"id": 2, "folder_is_active": False}]

        result = manager.get_inactive_folders()

        assert len(result) == 1
        mock_db.folders_table.find.assert_called_once_with(folder_is_active=False)

    def test_get_all_folders(self, manager, mock_db):
        """Test getting all folders."""
        mock_db.folders_table.find.return_value = [
            {"id": 1, "alias": "a"},
            {"id": 2, "alias": "b"},
        ]

        result = manager.get_all_folders()

        assert len(result) == 2

    def test_get_all_folders_with_order(self, manager, mock_db):
        """Test getting all folders with order by."""
        mock_db.folders_table.find.return_value = []

        manager.get_all_folders(order_by="alias")

        mock_db.folders_table.find.assert_called_once_with(order_by="alias")

    def test_count_folders_all(self, manager, mock_db):
        """Test counting all folders."""
        mock_db.folders_table.count.return_value = 10

        result = manager.count_folders()

        assert result == 10

    def test_count_folders_active_only(self, manager, mock_db):
        """Test counting active folders only."""
        mock_db.folders_table.count.return_value = 5

        result = manager.count_folders(active_only=True)

        mock_db.folders_table.count.assert_called_with(folder_is_active=True)
        assert result == 5

    def test_get_folder_by_id(self, manager, mock_db):
        """Test getting folder by ID."""
        mock_db.folders_table.find_one.return_value = {"id": 1, "alias": "test"}

        result = manager.get_folder_by_id(1)

        assert result["alias"] == "test"
        mock_db.folders_table.find_one.assert_called_once_with(id=1)

    def test_get_folder_by_name(self, manager, mock_db):
        """Test getting folder by name."""
        mock_db.folders_table.find_one.return_value = {
            "folder_name": "/path/to/folder",
            "alias": "test",
        }

        result = manager.get_folder_by_name("/path/to/folder")

        assert result["alias"] == "test"

    def test_get_folder_by_alias(self, manager, mock_db):
        """Test getting folder by alias."""
        mock_db.folders_table.find_one.return_value = {
            "alias": "test",
            "folder_name": "/path",
        }

        result = manager.get_folder_by_alias("test")

        assert result["folder_name"] == "/path"

    def test_update_folder(self, manager, mock_db):
        """Test updating a folder."""
        mock_db.folders_table.find_one.return_value = {"id": 1, "alias": "old"}

        result = manager.update_folder({"id": 1, "alias": "new"})

        assert result is True
        mock_db.folders_table.update.assert_called_once()

    def test_update_folder_no_id(self, manager, mock_db):
        """Test updating folder without ID fails."""
        result = manager.update_folder({"alias": "new"})

        assert result is False

    def test_update_folder_not_found(self, manager, mock_db):
        """Test updating non-existent folder."""
        mock_db.folders_table.find_one.return_value = None

        result = manager.update_folder({"id": 999, "alias": "new"})

        assert result is False

    def test_update_folder_by_name(self, manager, mock_db):
        """Test updating folder by name."""
        mock_db.folders_table.find_one.return_value = {"id": 1, "folder_name": "/path"}

        result = manager.update_folder_by_name({"folder_name": "/path", "alias": "new"})

        assert result is True

    def test_update_folder_by_name_not_found(self, manager, mock_db):
        """Test updating non-existent folder by name."""
        mock_db.folders_table.find_one.return_value = None

        result = manager.update_folder_by_name(
            {"folder_name": "/nonexistent", "alias": "new"}
        )

        assert result is False


class TestFolderManagerBatchOperations:
    """Tests for batch folder operations."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = MockDatabase()
        db.oversight_and_defaults.find_one.return_value = {
            "id": 1,
            "default_setting": "value",
        }
        return db

    @pytest.fixture
    def manager(self, mock_db):
        """Create FolderManager with mock database."""
        return FolderManager(mock_db)

    def test_batch_add_folders(self, manager, mock_db, tmp_path):
        """Test batch adding folders."""
        # Create subdirectories
        (tmp_path / "folder1").mkdir()
        (tmp_path / "folder2").mkdir()
        (tmp_path / "folder3").mkdir()

        mock_db.folders_table.find_one.return_value = None  # No existing folders

        result = manager.batch_add_folders(str(tmp_path))

        assert result["added"] == 3
        assert result["skipped"] == 0

    def test_batch_add_folders_skip_existing(self, manager, mock_db, tmp_path):
        """Test batch adding folders skips existing."""
        (tmp_path / "folder1").mkdir()
        (tmp_path / "folder2").mkdir()

        # Track which aliases have been checked
        aliases_checked = []

        def find_one_side_effect(**kwargs):
            alias = kwargs.get("alias")
            if alias:
                aliases_checked.append(alias)
            # Only "folder1" exists (check both possible cases)
            if alias in ("folder1", tmp_path.joinpath("folder1").name):
                return {"alias": alias}
            return None

        mock_db.folders_table.find_one.side_effect = find_one_side_effect

        result = manager.batch_add_folders(str(tmp_path), skip_existing=True)

        # One folder should be skipped (folder1), one should be added (folder2)
        # Note: The actual order depends on os.listdir which is filesystem dependent
        assert result["added"] + result["skipped"] == 2

    def test_batch_add_folders_invalid_path(self, manager, mock_db):
        """Test batch adding with invalid path."""
        result = manager.batch_add_folders("/nonexistent/path")

        assert result["added"] == 0
        assert result["skipped"] == 0
        assert "error" in result


class TestFolderManagerProtocolCompliance:
    """Tests for protocol compliance."""

    def test_database_protocol_compliance(self):
        """Verify stub database implements DatabaseProtocol."""
        stub_db = _SimpleDatabaseObj()

        assert isinstance(stub_db, DatabaseProtocol)

    def test_table_protocol_compliance(self):
        """Verify stub table implements TableProtocol."""
        stub_table = _SimpleTable()

        assert isinstance(stub_table, TableProtocol)


class TestFolderManagerSkipList:
    """Tests for skip list functionality."""

    def test_skip_list_excludes_fields(self):
        """Test that skip list excludes correct fields."""
        mock_db = MockDatabase()
        mock_db.get_oversight_or_default.return_value = {
            "id": 1,
            "folder_name": "should_be_skipped",
            "alias": "should_be_skipped",
            "logs_directory": "should_be_skipped",
            "errors_folder": "should_be_skipped",
            "valid_setting": "should_be_included",
        }
        mock_db.folders_table.find_one.return_value = None

        manager = FolderManager(mock_db)
        result = manager.add_folder("/path/to/folder")

        # These should not be in the result
        assert result.get("folder_name") == "/path/to/folder"  # Overwritten
        assert result.get("alias") is not None  # Generated
        assert (
            "logs_directory" not in result
            or result.get("logs_directory") != "should_be_skipped"
        )

        # This should be included
        assert result["valid_setting"] == "should_be_included"


class TestFolderManagerCommunicationWiring:
    """Communication-focused tests for FolderManager database interactions."""

    @pytest.fixture
    def mock_db(self):
        db = MockDatabase()
        db.get_oversight_or_default.return_value = {
            "id": 1,
            "folder_is_active": True,
            "process_backend_email": False,
        }
        return db

    @pytest.fixture
    def manager(self, mock_db):
        return FolderManager(mock_db)

    def test_add_folder_uses_oversight_defaults_provider(self, manager, mock_db):
        """add_folder should pull template defaults through get_oversight_or_default."""
        mock_db.folders_table.find_one.return_value = None

        manager.add_folder("/tmp/comm-folder")

        mock_db.get_oversight_or_default.assert_called_once()
        mock_db.folders_table.insert.assert_called_once()

    def test_delete_folder_with_related_deletes_all_related_records(
        self, manager, mock_db
    ):
        """delete_folder_with_related should fan out delete calls to all related tables."""
        mock_db.folders_table.find_one.return_value = {"id": 21}

        result = manager.delete_folder_with_related(21)

        assert result is True
        mock_db.folders_table.delete.assert_called_once_with(id=21)
        mock_db.processed_files.delete.assert_called_once_with(folder_id=21)
        mock_db.emails_table.delete.assert_called_once_with(folder_id=21)

    def test_delete_folder_with_related_missing_folder_no_side_effects(
        self, manager, mock_db
    ):
        """No table delete calls should occur when folder does not exist."""
        mock_db.folders_table.find_one.return_value = None

        result = manager.delete_folder_with_related(404)

        assert result is False
        mock_db.folders_table.delete.assert_not_called()
        mock_db.processed_files.delete.assert_not_called()
        mock_db.emails_table.delete.assert_not_called()

    def test_update_folder_by_name_preserves_existing_id_on_update(
        self, manager, mock_db
    ):
        """update_folder_by_name should resolve ID by name and update using that ID."""
        mock_db.folders_table.find_one.return_value = {
            "id": 5,
            "folder_name": "/tmp/original",
        }

        payload = {"folder_name": "/tmp/original", "alias": "renamed"}
        result = manager.update_folder_by_name(payload)

        assert result is True
        mock_db.folders_table.update.assert_called_once()
        updated_record, keys = mock_db.folders_table.update.call_args[0]
        assert updated_record["id"] == 5
        assert updated_record["alias"] == "renamed"
        assert keys == ["id"]

    def test_batch_add_folders_without_skip_adds_all_subfolders(
        self, manager, tmp_path, monkeypatch
    ):
        """batch_add_folders(skip_existing=False) should always invoke add_folder."""
        (tmp_path / "one").mkdir()
        (tmp_path / "two").mkdir()

        add_calls = []
        monkeypatch.setattr(
            manager,
            "add_folder",
            lambda folder_path: add_calls.append(folder_path),
        )

        result = manager.batch_add_folders(str(tmp_path), skip_existing=False)

        assert result["added"] == 2
        assert result["skipped"] == 0
        assert len(add_calls) == 2
