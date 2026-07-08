"""Unit tests for FolderManager.

Tests the FolderManager class with mocked database connections
to ensure proper behavior without requiring actual database files.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from core.ports.repositories import (
    IFolderRepository,
    IProcessedFilesRepository,
    ISettingsRepository,
)
from interface.operations.folder_manager import FolderManager

pytestmark = [pytest.mark.unit, pytest.mark.database]


class MockDatabase:
    """Helper to create mock repositories for FolderManager testing.

    Provides factory methods so existing test fixtures can create
    properly-typed mock repository objects.
    """

    @staticmethod
    def create_folder_repo() -> MagicMock:
        return MagicMock(spec=IFolderRepository)

    @staticmethod
    def create_settings_repo() -> MagicMock:
        return MagicMock(spec=ISettingsRepository)

    @staticmethod
    def create_processed_files_repo() -> MagicMock:
        return MagicMock(spec=IProcessedFilesRepository)

    @staticmethod
    def create_repos():
        class _Repos:
            pass

        repos = _Repos()
        repos.folder_repo = MockDatabase.create_folder_repo()
        repos.settings_repo = MockDatabase.create_settings_repo()
        repos.processed_files_repo = MockDatabase.create_processed_files_repo()
        return repos


class TestFolderManager:
    """Tests for FolderManager class."""

    @pytest.fixture
    def mock_db(self):
        repos = MockDatabase.create_repos()
        repos.settings_repo.get_defaults.return_value = {
            "id": 1,
            "default_setting": "value",
            "folder_is_active": True,
        }
        return repos

    @pytest.fixture
    def manager(self, mock_db):
        """Create FolderManager with mock repositories."""
        return FolderManager(
            folder_repo=mock_db.folder_repo,
            settings_repo=mock_db.settings_repo,
            processed_files_repo=mock_db.processed_files_repo,
        )

    def test_add_folder_creates_record(self, manager, mock_db):
        """Test adding a folder creates a database record."""
        mock_db.folder_repo.find_by_alias.return_value = None
        mock_db.folder_repo.insert.return_value = 42
        persisted = MagicMock()
        persisted.to_dict.return_value = {
            "folder_name": "/path/to/folder",
            "alias": "folder",
        }
        mock_db.folder_repo.find_by_id.return_value = persisted

        result = manager.add_folder("/path/to/folder")

        mock_db.folder_repo.insert.assert_called_once()
        assert result["folder_name"] == "/path/to/folder"

    def test_add_folder_generates_unique_alias(self, manager, mock_db):
        """Test adding duplicate folder generates unique alias."""
        mock_db.folder_repo.find_by_alias.side_effect = [
            {"alias": "folder"},
            None,
        ]
        mock_db.folder_repo.insert.return_value = 42
        persisted = MagicMock()
        persisted.to_dict.return_value = {
            "folder_name": "/path/to/folder",
            "alias": "folder 1",
        }
        mock_db.folder_repo.find_by_id.return_value = persisted

        result = manager.add_folder("/path/to/folder")

        assert result["alias"] == "folder 1"

    def test_add_folder_with_template_data(self, manager, mock_db):
        """Test adding folder with custom template data."""
        mock_db.folder_repo.find_by_alias.return_value = None
        mock_db.folder_repo.insert.return_value = 42
        persisted = MagicMock()
        persisted.to_dict.return_value = {
            "folder_name": "/path/to/folder",
            "alias": "folder",
            "custom_setting": "custom_value",
        }
        mock_db.folder_repo.find_by_id.return_value = persisted

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
        mock_db.folder_repo.find_all.return_value = [
            SimpleNamespace(folder_name=folder_path, alias="test")
        ]

        result = manager.check_folder_exists(folder_path)

        assert result["truefalse"] is True
        assert result["matched_folder"]["alias"] == "test"

    def test_check_folder_exists_not_found(self, manager, mock_db):
        """Test checking non-existing folder."""
        mock_db.folder_repo.find_all.return_value = []

        result = manager.check_folder_exists("/nonexistent")

        assert result["truefalse"] is False
        assert result["matched_folder"] is None

    def test_check_folder_exists_normalized_path(self, manager, mock_db):
        """Test that path normalization works correctly."""
        mock_db.folder_repo.find_all.return_value = [
            SimpleNamespace(folder_name="/path/to/folder", alias="test")
        ]

        result = manager.check_folder_exists("/path/to/folder/")

        assert result["truefalse"] is True

    def test_check_folder_exists_multiple_matches(self, manager, mock_db, tmp_path):
        """Test that check_folder_exists returns all matched folders."""
        folder_path = str(tmp_path)
        mock_db.folder_repo.find_all.return_value = [
            SimpleNamespace(folder_name=folder_path, alias="config1", id=1),
            SimpleNamespace(folder_name=folder_path, alias="config2", id=2),
        ]

        result = manager.check_folder_exists(folder_path)

        assert result["truefalse"] is True
        assert result["matched_folder"]["alias"] == "config1"
        assert len(result["all_matched_folders"]) == 2
        assert result["all_matched_folders"][0]["alias"] == "config1"
        assert result["all_matched_folders"][1]["alias"] == "config2"

    def test_disable_folder(self, manager, mock_db):
        """Test disabling a folder."""
        mock_db.folder_repo.find_by_id.return_value = {
            "id": 1,
            "folder_is_active": True,
        }

        result = manager.disable_folder(1)

        assert result is True
        mock_db.folder_repo.update.assert_called_once()
        call_args = mock_db.folder_repo.update.call_args
        assert call_args[0][0].to_dict()["folder_is_active"] is False

    def test_disable_folder_not_found(self, manager, mock_db):
        """Test disabling non-existent folder."""
        mock_db.folder_repo.find_by_id.return_value = None

        result = manager.disable_folder(999)

        assert result is False

    def test_enable_folder(self, manager, mock_db):
        """Test enabling a folder."""
        mock_db.folder_repo.find_by_id.return_value = {
            "id": 1,
            "folder_is_active": False,
        }

        result = manager.enable_folder(1)

        assert result is True
        mock_db.folder_repo.update.assert_called_once()
        call_args = mock_db.folder_repo.update.call_args
        assert call_args[0][0].to_dict()["folder_is_active"] is True

    def test_enable_folder_not_found(self, manager, mock_db):
        """Test enabling non-existent folder."""
        mock_db.folder_repo.find_by_id.return_value = None

        result = manager.enable_folder(999)

        assert result is False

    def test_delete_folder(self, manager, mock_db):
        """Test deleting a folder."""
        mock_db.folder_repo.find_by_id.return_value = {"id": 1}

        result = manager.delete_folder(1)

        assert result is True
        mock_db.folder_repo.delete.assert_called_once_with(1)

    def test_delete_folder_not_found(self, manager, mock_db):
        """Test deleting non-existent folder."""
        mock_db.folder_repo.find_by_id.return_value = None

        result = manager.delete_folder(999)

        assert result is False

    def test_get_active_folders(self, manager, mock_db):
        """Test getting active folders."""
        mock_db.folder_repo.find_all.return_value = [
            SimpleNamespace(id=1, folder_is_active=True)
        ]

        result = manager.get_active_folders()

        assert len(result) == 1
        mock_db.folder_repo.find_all.assert_called_once_with(active_only=True)

    def test_get_inactive_folders(self, manager, mock_db):
        """Test getting inactive folders."""
        mock_db.folder_repo.find_all.return_value = [
            SimpleNamespace(id=2, folder_is_active=False)
        ]

        result = manager.get_inactive_folders()

        assert len(result) == 1
        mock_db.folder_repo.find_all.assert_called_once_with(active_only=False)

    def test_get_all_folders(self, manager, mock_db):
        """Test getting all folders."""
        mock_db.folder_repo.find_all.return_value = [
            SimpleNamespace(id=1, alias="a"),
            SimpleNamespace(id=2, alias="b"),
        ]

        result = manager.get_all_folders()

        assert len(result) == 2

    def test_get_all_folders_with_order(self, manager, mock_db):
        """Test getting all folders with order by."""
        mock_db.folder_repo.find_all.return_value = []

        manager.get_all_folders()

        mock_db.folder_repo.find_all.assert_called_once_with()

    def test_count_folders_all(self, manager, mock_db):
        """Test counting all folders."""
        mock_db.folder_repo.count.return_value = 10

        result = manager.count_folders()

        assert result == 10

    def test_count_folders_active_only(self, manager, mock_db):
        """Test counting active folders only."""
        mock_db.folder_repo.count.return_value = 5

        result = manager.count_folders(active_only=True)

        mock_db.folder_repo.count.assert_called_with(active_only=True)
        assert result == 5

    def test_get_folder_by_id(self, manager, mock_db):
        """Test getting folder by ID."""
        mock_db.folder_repo.find_by_id.return_value = {"id": 1, "alias": "test"}

        result = manager.get_folder_by_id(1)

        assert result["alias"] == "test"
        mock_db.folder_repo.find_by_id.assert_called_once_with(1)

    def test_get_folder_by_name(self, manager, mock_db):
        """Test getting folder by name."""
        mock_db.folder_repo.find_by_path.return_value = {
            "folder_name": "/path/to/folder",
            "alias": "test",
        }

        result = manager.get_folder_by_name("/path/to/folder")

        assert result["alias"] == "test"

    def test_get_folder_by_alias(self, manager, mock_db):
        """Test getting folder by alias."""
        mock_db.folder_repo.find_by_alias.return_value = {
            "alias": "test",
            "folder_name": "/path",
        }

        result = manager.get_folder_by_alias("test")

        assert result["folder_name"] == "/path"

    def test_update_folder(self, manager, mock_db):
        """Test updating a folder."""
        mock_db.folder_repo.find_by_id.return_value = {"id": 1, "alias": "old"}

        result = manager.update_folder({"id": 1, "alias": "new"})

        assert result is True
        mock_db.folder_repo.update.assert_called_once()

    def test_update_folder_no_id(self, manager, mock_db):
        """Test updating folder without ID fails."""
        result = manager.update_folder({"alias": "new"})

        assert result is False

    def test_update_folder_not_found(self, manager, mock_db):
        """Test updating non-existent folder."""
        mock_db.folder_repo.find_by_id.return_value = None

        result = manager.update_folder({"id": 999, "alias": "new"})

        assert result is False

    def test_update_folder_by_name(self, manager, mock_db):
        """Test updating folder by name."""
        mock_db.folder_repo.find_by_path.return_value = {
            "id": 1,
            "folder_name": "/path",
        }

        result = manager.update_folder_by_name({"folder_name": "/path", "alias": "new"})

        assert result is True

    def test_update_folder_by_name_not_found(self, manager, mock_db):
        """Test updating non-existent folder by name."""
        mock_db.folder_repo.find_by_path.return_value = None

        result = manager.update_folder_by_name(
            {"folder_name": "/nonexistent", "alias": "new"}
        )

        assert result is False


class TestFolderManagerBatchOperations:
    """Tests for batch folder operations."""

    @pytest.fixture
    def mock_db(self):
        repos = MockDatabase.create_repos()
        repos.settings_repo.get_defaults.return_value = {
            "id": 1,
            "default_setting": "value",
        }
        return repos

    @pytest.fixture
    def manager(self, mock_db):
        """Create FolderManager with mock repositories."""
        return FolderManager(
            folder_repo=mock_db.folder_repo,
            settings_repo=mock_db.settings_repo,
            processed_files_repo=mock_db.processed_files_repo,
        )

    def test_batch_add_folders(self, manager, mock_db, tmp_path):
        """Test batch adding folders."""
        (tmp_path / "folder1").mkdir()
        (tmp_path / "folder2").mkdir()
        (tmp_path / "folder3").mkdir()

        mock_db.folder_repo.find_all.return_value = []
        mock_db.folder_repo.find_by_alias.return_value = None

        result = manager.batch_add_folders(str(tmp_path))

        assert result["added"] == 3
        assert result["skipped"] == 0

    def test_batch_add_folders_skip_existing(self, manager, mock_db, tmp_path):
        """Test batch adding folders skips existing."""
        (tmp_path / "folder1").mkdir()
        (tmp_path / "folder2").mkdir()

        mock_db.folder_repo.find_all.return_value = [
            SimpleNamespace(folder_name=str(tmp_path / "folder1"), alias="folder1"),
        ]
        mock_db.folder_repo.find_by_alias.return_value = None

        result = manager.batch_add_folders(str(tmp_path), skip_existing=True)

        assert result["added"] + result["skipped"] == 2

    def test_batch_add_folders_invalid_path(self, manager, mock_db):
        """Test batch adding with invalid path."""
        result = manager.batch_add_folders("/nonexistent/path")

        assert result["added"] == 0
        assert result["skipped"] == 0
        assert "error" in result


class TestFolderManagerSkipList:
    """Tests for skip list functionality."""

    def test_skip_list_excludes_fields(self):
        """Test that skip list excludes correct fields."""
        mock_folder_repo = MockDatabase.create_folder_repo()
        mock_settings_repo = MockDatabase.create_settings_repo()
        mock_settings_repo.get_defaults.return_value = {
            "id": 1,
            "folder_name": "should_be_skipped",
            "alias": "should_be_skipped",
            "logs_directory": "should_be_skipped",
            "errors_folder": "should_be_skipped",
            "valid_setting": "should_be_included",
        }
        mock_folder_repo.find_by_alias.return_value = None
        mock_folder_repo.insert.return_value = 42
        persisted = MagicMock()
        persisted.to_dict.return_value = {
            "folder_name": "/path/to/folder",
            "alias": "folder",
            "valid_setting": "should_be_included",
        }
        mock_folder_repo.find_by_id.return_value = persisted

        manager = FolderManager(
            folder_repo=mock_folder_repo,
            settings_repo=mock_settings_repo,
        )
        result = manager.add_folder("/path/to/folder")

        assert result.get("folder_name") == "/path/to/folder"
        assert result.get("alias") is not None
        assert (
            "logs_directory" not in result
            or result.get("logs_directory") != "should_be_skipped"
        )

        assert result["valid_setting"] == "should_be_included"


class TestFolderManagerCommunicationWiring:
    """Communication-focused tests for FolderManager database interactions."""

    @pytest.fixture
    def mock_db(self):
        repos = MockDatabase.create_repos()
        repos.settings_repo.get_defaults.return_value = {
            "id": 1,
            "folder_is_active": True,
            "process_backend_email": False,
        }
        return repos

    @pytest.fixture
    def manager(self, mock_db):
        return FolderManager(
            folder_repo=mock_db.folder_repo,
            settings_repo=mock_db.settings_repo,
            processed_files_repo=mock_db.processed_files_repo,
        )

    def test_add_folder_uses_oversight_defaults_provider(self, manager, mock_db):
        """add_folder should pull template defaults through get_oversight_or_default."""
        mock_db.folder_repo.find_by_alias.return_value = None

        manager.add_folder("/tmp/comm-folder")

        mock_db.settings_repo.get_defaults.assert_called_once()
        mock_db.folder_repo.insert.assert_called_once()

    def test_delete_folder_with_related_deletes_all_related_records(
        self, manager, mock_db
    ):
        """delete_folder_with_related should fan out delete calls to related repos."""
        mock_db.folder_repo.find_by_id.return_value = {"id": 21}

        result = manager.delete_folder_with_related(21)

        assert result is True
        mock_db.folder_repo.delete.assert_called_once_with(21)
        mock_db.processed_files_repo.clear_for_folder.assert_called_once_with(21)

    def test_delete_folder_with_related_missing_folder_no_side_effects(
        self, manager, mock_db
    ):
        """No repo delete calls should occur when folder does not exist."""
        mock_db.folder_repo.find_by_id.return_value = None

        result = manager.delete_folder_with_related(404)

        assert result is False
        mock_db.folder_repo.delete.assert_not_called()
        mock_db.processed_files_repo.clear_for_folder.assert_not_called()

    def test_update_folder_by_name_preserves_existing_id_on_update(
        self, manager, mock_db
    ):
        """update_folder_by_name should resolve ID by name and update using that ID."""
        mock_db.folder_repo.find_by_path.return_value = {
            "id": 5,
            "folder_name": "/tmp/original",
        }

        payload = {"folder_name": "/tmp/original", "alias": "renamed"}
        result = manager.update_folder_by_name(payload)

        assert result is True
        mock_db.folder_repo.update.assert_called_once()
        updated_config = mock_db.folder_repo.update.call_args[0][0]
        assert updated_config.id == 5
        assert updated_config.alias == "renamed"

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
