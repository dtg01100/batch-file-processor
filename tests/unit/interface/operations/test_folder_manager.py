"""Unit tests for FolderManager.

Exercises the FolderManager class against real in-memory adapters, so
the manager's CRUD/query/update operations are validated against an
actual repo state machine rather than hand-configured mocks.

Each test obtains a fresh FolderManager plus its three underlying
repos via the _make_manager helper. Tests that need a pre-populated
store call _insert_folder (or the equivalent on the settings or
processed-files repos) to set up state, then assert the post-condition
via the repos themselves.
"""

import pytest

from adapters.inmemory import (
    InMemoryFolderRepository,
    InMemoryProcessedFilesRepository,
    InMemorySettingsRepository,
)
from core.domain.models.folder import FolderConfiguration
from core.domain.models.processed_file import ProcessedFile
from interface.operations.folder_manager import FolderManager

pytestmark = [pytest.mark.unit, pytest.mark.database]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_manager(
    *,
    settings_defaults=None,
):
    """Build a FolderManager backed by in-memory repositories.

    Returns the manager and its three repos so tests can pre-populate
    state and inspect post-condition state.
    """
    folder_repo = InMemoryFolderRepository()
    settings_repo = (
        InMemorySettingsRepository(defaults=settings_defaults)
        if settings_defaults is not None
        else InMemorySettingsRepository()
    )
    processed_files_repo = InMemoryProcessedFilesRepository()
    manager = FolderManager(
        folder_repo=folder_repo,
        settings_repo=settings_repo,
        processed_files_repo=processed_files_repo,
    )
    return manager, folder_repo, settings_repo, processed_files_repo


def _insert_folder(
    folder_repo,
    *,
    folder_name="/path",
    alias="alias",
    folder_is_active=True,
):
    """Insert a FolderConfiguration and return the assigned PK."""
    return folder_repo.insert(
        FolderConfiguration(
            folder_name=folder_name,
            alias=alias,
            folder_is_active=folder_is_active,
        )
    )


# ---------------------------------------------------------------------------
# Core CRUD operations
# ---------------------------------------------------------------------------


class TestFolderManager:
    """Tests for FolderManager CRUD operations."""

    def test_add_folder_creates_record(self):
        manager, folder_repo, _, _ = _make_manager()

        result = manager.add_folder("/path/to/folder")

        assert result is not None
        assert result["folder_name"] == "/path/to/folder"
        assert result["alias"] == "folder"
        # the row was persisted under the returned PK
        persisted = folder_repo.find_by_id(result["id"])
        assert persisted is not None
        assert persisted.folder_name == "/path/to/folder"

    def test_add_folder_generates_unique_alias(self):
        manager, folder_repo, _, _ = _make_manager()
        # pre-populate with a folder that already uses the alias we'd derive
        _insert_folder(folder_repo, folder_name="/other", alias="folder")

        result = manager.add_folder("/path/to/folder")

        assert result["alias"] == "folder 1"

    def test_add_folder_with_template_data(self):
        """When template_data is supplied, its FC fields override settings_repo defaults."""
        manager, _, _, _ = _make_manager(
            settings_defaults={
                "process_backend_copy": False,
                "alert_on_failure": True,
            }
        )
        custom_template = {
            "id": 1,
            "process_backend_copy": True,
            "alert_on_failure": False,
        }

        result = manager.add_folder("/path/to/folder", template_data=custom_template)

        assert result is not None
        assert result["folder_name"] == "/path/to/folder"
        # template_data values override settings_repo defaults
        assert result["process_backend_copy"] is True
        assert result["alert_on_failure"] is False

    def test_check_folder_exists_found(self, tmp_path):
        manager, folder_repo, _, _ = _make_manager()
        folder_path = str(tmp_path)
        _insert_folder(folder_repo, folder_name=folder_path, alias="test")

        result = manager.check_folder_exists(folder_path)

        assert result["truefalse"] is True
        assert result["matched_folder"]["alias"] == "test"
        assert len(result["all_matched_folders"]) == 1

    def test_check_folder_exists_not_found(self):
        manager, _, _, _ = _make_manager()

        result = manager.check_folder_exists("/nonexistent")

        assert result["truefalse"] is False
        assert result["matched_folder"] is None
        assert result["all_matched_folders"] == []

    def test_check_folder_exists_normalized_path(self):
        manager, folder_repo, _, _ = _make_manager()
        _insert_folder(folder_repo, folder_name="/path/to/folder", alias="test")

        result = manager.check_folder_exists("/path/to/folder/")

        assert result["truefalse"] is True

    def test_check_folder_exists_multiple_matches(self, tmp_path):
        manager, folder_repo, _, _ = _make_manager()
        folder_path = str(tmp_path)
        _insert_folder(folder_repo, folder_name=folder_path, alias="config1")
        _insert_folder(folder_repo, folder_name=folder_path, alias="config2")

        result = manager.check_folder_exists(folder_path)

        assert result["truefalse"] is True
        assert result["matched_folder"]["alias"] == "config1"
        assert len(result["all_matched_folders"]) == 2
        assert result["all_matched_folders"][0]["alias"] == "config1"
        assert result["all_matched_folders"][1]["alias"] == "config2"

    def test_disable_folder(self):
        manager, folder_repo, _, _ = _make_manager()
        pk = _insert_folder(
            folder_repo, folder_name="/x", alias="x", folder_is_active=True
        )

        result = manager.disable_folder(pk)

        assert result is True
        assert folder_repo.find_by_id(pk).folder_is_active is False

    def test_disable_folder_not_found(self):
        manager, _, _, _ = _make_manager()

        result = manager.disable_folder(999)

        assert result is False

    def test_enable_folder(self):
        manager, folder_repo, _, _ = _make_manager()
        pk = _insert_folder(
            folder_repo, folder_name="/x", alias="x", folder_is_active=False
        )

        result = manager.enable_folder(pk)

        assert result is True
        assert folder_repo.find_by_id(pk).folder_is_active is True

    def test_enable_folder_not_found(self):
        manager, _, _, _ = _make_manager()

        result = manager.enable_folder(999)

        assert result is False

    def test_delete_folder(self):
        manager, folder_repo, _, _ = _make_manager()
        pk = _insert_folder(folder_repo, folder_name="/x", alias="x")

        result = manager.delete_folder(pk)

        assert result is True
        assert folder_repo.find_by_id(pk) is None

    def test_delete_folder_not_found(self):
        manager, _, _, _ = _make_manager()

        result = manager.delete_folder(999)

        assert result is False

    def test_get_active_folders(self):
        manager, folder_repo, _, _ = _make_manager()
        _insert_folder(folder_repo, folder_name="/a", alias="a", folder_is_active=True)
        _insert_folder(folder_repo, folder_name="/b", alias="b", folder_is_active=False)

        result = manager.get_active_folders()

        assert len(result) == 1
        assert result[0]["alias"] == "a"

    def test_get_inactive_folders(self):
        manager, folder_repo, _, _ = _make_manager()
        _insert_folder(folder_repo, folder_name="/a", alias="a", folder_is_active=True)
        _insert_folder(folder_repo, folder_name="/b", alias="b", folder_is_active=False)

        result = manager.get_inactive_folders()

        assert len(result) == 1
        assert result[0]["alias"] == "b"

    def test_get_all_folders(self):
        manager, folder_repo, _, _ = _make_manager()
        _insert_folder(folder_repo, folder_name="/a", alias="a")
        _insert_folder(folder_repo, folder_name="/b", alias="b")

        result = manager.get_all_folders()

        assert len(result) == 2
        assert {r["alias"] for r in result} == {"a", "b"}

    def test_get_all_folders_with_order(self):
        """_order_by is accepted for backward compatibility but ignored."""
        manager, folder_repo, _, _ = _make_manager()
        _insert_folder(folder_repo, folder_name="/a", alias="alpha")
        _insert_folder(folder_repo, folder_name="/b", alias="beta")

        result = manager.get_all_folders(_order_by="folder_name")

        assert len(result) == 2
        assert {r["alias"] for r in result} == {"alpha", "beta"}

    def test_count_folders_all(self):
        manager, folder_repo, _, _ = _make_manager()
        _insert_folder(folder_repo, folder_name="/a", alias="a")
        _insert_folder(folder_repo, folder_name="/b", alias="b")

        assert manager.count_folders() == 2

    def test_count_folders_active_only(self):
        manager, folder_repo, _, _ = _make_manager()
        _insert_folder(folder_repo, folder_name="/a", alias="a", folder_is_active=True)
        _insert_folder(folder_repo, folder_name="/b", alias="b", folder_is_active=False)

        assert manager.count_folders() == 2
        assert manager.count_folders(active_only=True) == 1

    def test_get_folder_by_id(self):
        manager, folder_repo, _, _ = _make_manager()
        pk = _insert_folder(folder_repo, folder_name="/x", alias="test")

        result = manager.get_folder_by_id(pk)

        assert result is not None
        assert result["alias"] == "test"
        assert result["id"] == pk

    def test_get_folder_by_name(self):
        manager, folder_repo, _, _ = _make_manager()
        _insert_folder(folder_repo, folder_name="/path/to/folder", alias="test")

        result = manager.get_folder_by_name("/path/to/folder")

        assert result is not None
        assert result["alias"] == "test"

    def test_get_folder_by_alias(self):
        manager, folder_repo, _, _ = _make_manager()
        _insert_folder(folder_repo, folder_name="/path", alias="test")

        result = manager.get_folder_by_alias("test")

        assert result is not None
        assert result["folder_name"] == "/path"

    def test_update_folder(self):
        manager, folder_repo, _, _ = _make_manager()
        pk = _insert_folder(folder_repo, folder_name="/x", alias="old")

        result = manager.update_folder({"id": pk, "alias": "new"})

        assert result is True
        assert folder_repo.find_by_id(pk).alias == "new"

    def test_update_folder_no_id(self):
        manager, _, _, _ = _make_manager()

        result = manager.update_folder({"alias": "new"})

        assert result is False

    def test_update_folder_not_found(self):
        manager, _, _, _ = _make_manager()

        result = manager.update_folder({"id": 999, "alias": "new"})

        assert result is False

    def test_update_folder_by_name(self):
        manager, folder_repo, _, _ = _make_manager()
        _insert_folder(folder_repo, folder_name="/path", alias="old")

        result = manager.update_folder_by_name({"folder_name": "/path", "alias": "new"})

        assert result is True
        assert folder_repo.find_by_path("/path").alias == "new"

    def test_update_folder_by_name_not_found(self):
        manager, _, _, _ = _make_manager()

        result = manager.update_folder_by_name(
            {"folder_name": "/nonexistent", "alias": "new"}
        )

        assert result is False


# ---------------------------------------------------------------------------
# Batch operations
# ---------------------------------------------------------------------------


class TestFolderManagerBatchOperations:
    """Tests for batch folder operations."""

    def test_batch_add_folders(self, tmp_path):
        (tmp_path / "folder1").mkdir()
        (tmp_path / "folder2").mkdir()
        (tmp_path / "folder3").mkdir()

        manager, folder_repo, _, _ = _make_manager()

        result = manager.batch_add_folders(str(tmp_path))

        assert result["added"] == 3
        assert result["skipped"] == 0
        assert folder_repo.count() == 3

    def test_batch_add_folders_skip_existing(self, tmp_path):
        (tmp_path / "folder1").mkdir()
        (tmp_path / "folder2").mkdir()

        manager, folder_repo, _, _ = _make_manager()
        _insert_folder(
            folder_repo,
            folder_name=str(tmp_path / "folder1"),
            alias="folder1",
        )

        result = manager.batch_add_folders(str(tmp_path), skip_existing=True)

        assert result["added"] + result["skipped"] == 2
        assert folder_repo.count() == 2

    def test_batch_add_folders_invalid_path(self):
        manager, folder_repo, _, _ = _make_manager()

        result = manager.batch_add_folders("/nonexistent/path")

        assert result["added"] == 0
        assert result["skipped"] == 0
        assert "error" in result
        assert folder_repo.count() == 0


# ---------------------------------------------------------------------------
# Skip-list semantics
# ---------------------------------------------------------------------------


class TestFolderManagerSkipList:
    """Tests for skip-list functionality."""

    def test_skip_list_overrides_defaults_for_canonical_fields(self):
        """SKIP_LIST excludes canonical-identity fields before folder construction.

        folder_name and alias are explicitly re-set by add_folder, so they
        appear in the result for that reason — not because they propagated
        from settings defaults.
        """
        manager, _, _, _ = _make_manager(
            settings_defaults={
                "id": 1,
                "folder_name": "should_be_overridden",
                "alias": "should_be_overridden",
                "logs_directory": "should_be_excluded",
                "errors_folder": "should_be_excluded",
                "alert_on_failure": False,
            }
        )

        result = manager.add_folder("/path/to/folder")

        # folder_name/alias are re-set by add_folder, not propagated from defaults
        assert result["folder_name"] == "/path/to/folder"
        assert result["alias"] == "folder"
        # Non-FC SKIP_LIST fields never appear in the result
        assert "logs_directory" not in result
        assert "errors_folder" not in result
        # Non-SKIP_LIST FC fields propagate from defaults
        assert result["alert_on_failure"] is False


# ---------------------------------------------------------------------------
# Communication wiring
# ---------------------------------------------------------------------------


class TestFolderManagerCommunicationWiring:
    """Communication-focused tests for FolderManager repo interactions."""

    def test_add_folder_uses_oversight_defaults_provider(self):
        manager, _, _, _ = _make_manager(
            settings_defaults={
                "id": 1,
                "folder_is_active": True,
                "process_backend_email": False,
            }
        )

        result = manager.add_folder("/tmp/comm-folder")

        # The settings_repo.get_defaults() values were read and applied;
        # add_folder does not override process_backend_email.
        assert result is not None
        assert result["process_backend_email"] is False

    def test_delete_folder_with_related_deletes_all_related_records(self):
        manager, folder_repo, _, processed_files_repo = _make_manager()
        pk = _insert_folder(folder_repo, folder_name="/x", alias="x")
        processed_files_repo.mark_processed(
            ProcessedFile(file_checksum="h1", folder_id=pk, filename="f1.edi")
        )
        processed_files_repo.mark_processed(
            ProcessedFile(file_checksum="h2", folder_id=pk, filename="f2.edi")
        )

        result = manager.delete_folder_with_related(pk)

        assert result is True
        assert folder_repo.find_by_id(pk) is None
        assert not processed_files_repo.is_processed("h1")
        assert not processed_files_repo.is_processed("h2")

    def test_delete_folder_with_related_missing_folder_no_side_effects(self):
        manager, folder_repo, _, processed_files_repo = _make_manager()
        # pre-populate an unrelated folder and an unrelated processed-file
        # record to detect any unintended deletion
        _insert_folder(folder_repo, folder_name="/other", alias="other")
        processed_files_repo.mark_processed(
            ProcessedFile(file_checksum="keepme", folder_id=999, filename="k.edi")
        )

        result = manager.delete_folder_with_related(404)

        assert result is False
        assert folder_repo.find_by_path("/other") is not None
        assert processed_files_repo.is_processed("keepme")

    def test_update_folder_by_name_preserves_existing_id_on_update(self):
        manager, folder_repo, _, _ = _make_manager()
        pk = _insert_folder(folder_repo, folder_name="/tmp/original", alias="old")

        result = manager.update_folder_by_name(
            {"folder_name": "/tmp/original", "alias": "renamed"}
        )

        assert result is True
        # The existing PK is preserved across the read-modify-write cycle.
        assert folder_repo.find_by_id(pk).alias == "renamed"
        assert folder_repo.find_by_path("/tmp/original").id == pk

    def test_batch_add_folders_without_skip_adds_all_subfolders(self, tmp_path):
        (tmp_path / "one").mkdir()
        (tmp_path / "two").mkdir()

        manager, folder_repo, _, _ = _make_manager()

        result = manager.batch_add_folders(str(tmp_path), skip_existing=False)

        assert result["added"] == 2
        assert result["skipped"] == 0
        assert folder_repo.count() == 2
