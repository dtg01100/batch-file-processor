"""Port contract tests.

Parameterized assertions that run against the in-memory adapter AND
the SQLite adapter for each port. The SQLite adapter is exercised
end-to-end against a real temp_database fixture.

If a future adapter is added (async, db2ssh, etc.) it should be
added to the adapter_factories dict for its port and run through
the same assertions.
"""

from __future__ import annotations

import pytest

from adapters.inmemory import (
    InMemoryEmailQueueRepository,
    InMemoryFolderRepository,
    InMemoryProcessedFilesRepository,
    InMemorySettingsRepository,
)
from adapters.sqlite.repositories.sqlite_email_queue_repo import (
    SqliteEmailQueueRepository,
)
from adapters.sqlite.repositories.sqlite_folder_repo import (
    SqliteFolderRepository,
)
from adapters.sqlite.repositories.sqlite_processed_files_repo import (
    SqliteProcessedFilesRepository,
)
from adapters.sqlite.repositories.sqlite_settings_repo import (
    SqliteSettingsRepository,
)
from core.domain.models.folder import FolderConfiguration
from core.domain.models.processed_file import ProcessedFile
from core.ports.repositories import (
    IEmailQueueRepository,
    IFolderRepository,
    IProcessedFilesRepository,
    ISettingsRepository,
)

pytestmark = [pytest.mark.unit, pytest.mark.database]


# ---------------------------------------------------------------------------
# IFolderRepository contract
# ---------------------------------------------------------------------------


def _make_folder_repo(kind: str, temp_database=None) -> IFolderRepository:
    if kind == "inmemory":
        return InMemoryFolderRepository()
    if kind == "sqlite":
        return SqliteFolderRepository(temp_database)
    raise ValueError(kind)


@pytest.fixture(params=["inmemory", "sqlite"])
def folder_repo(request, temp_database) -> IFolderRepository:
    return _make_folder_repo(request.param, temp_database=temp_database)


class TestIFolderRepositoryContract:
    """Behavioural contract for IFolderRepository across adapters."""

    def test_insert_returns_primary_key(self, folder_repo: IFolderRepository) -> None:
        fc = FolderConfiguration(folder_name="/a", alias="a")
        pk = folder_repo.insert(fc)
        assert isinstance(pk, int)
        assert pk > 0

    def test_find_by_id_returns_inserted_folder(
        self, folder_repo: IFolderRepository
    ) -> None:
        fc = FolderConfiguration(folder_name="/a", alias="a")
        pk = folder_repo.insert(fc)
        got = folder_repo.find_by_id(pk)
        assert got is not None
        assert got.id == pk
        assert got.folder_name == "/a"
        assert got.alias == "a"

    def test_find_by_id_returns_none_for_missing(
        self, folder_repo: IFolderRepository
    ) -> None:
        assert folder_repo.find_by_id(99_999) is None

    def test_find_by_path_normalises_trailing_slash(
        self, folder_repo: IFolderRepository
    ) -> None:
        folder_repo.insert(FolderConfiguration(folder_name="/foo", alias="f"))
        assert folder_repo.find_by_path("/foo/") is not None
        assert folder_repo.find_by_path("/foo") is not None

    def test_find_by_alias(self, folder_repo: IFolderRepository) -> None:
        folder_repo.insert(FolderConfiguration(folder_name="/a", alias="alpha"))
        got = folder_repo.find_by_alias("alpha")
        assert got is not None and got.alias == "alpha"
        assert folder_repo.find_by_alias("nope") is None

    def test_find_all_active_only(self, folder_repo: IFolderRepository) -> None:
        folder_repo.insert(
            FolderConfiguration(folder_name="/a", alias="a", folder_is_active=True)
        )
        folder_repo.insert(
            FolderConfiguration(folder_name="/b", alias="b", folder_is_active=False)
        )
        active = folder_repo.find_all(active_only=True)
        all_folders = folder_repo.find_all(active_only=False)
        assert len(active) == 1
        assert active[0].alias == "a"
        assert len(all_folders) == 2

    def test_update_persists_changes(self, folder_repo: IFolderRepository) -> None:
        pk = folder_repo.insert(FolderConfiguration(folder_name="/a", alias="a"))
        folder_repo.update(FolderConfiguration(folder_name="/a-renamed", alias="a"), pk)
        got = folder_repo.find_by_id(pk)
        assert got is not None
        assert got.folder_name == "/a-renamed"

    def test_update_rejects_non_positive_id(
        self, folder_repo: IFolderRepository
    ) -> None:
        with pytest.raises(ValueError):
            folder_repo.update(FolderConfiguration(folder_name="/x"), 0)
        with pytest.raises(ValueError):
            folder_repo.update(FolderConfiguration(folder_name="/x"), -1)

    def test_delete_removes_record(self, folder_repo: IFolderRepository) -> None:
        pk = folder_repo.insert(FolderConfiguration(folder_name="/a", alias="a"))
        folder_repo.delete(pk)
        assert folder_repo.find_by_id(pk) is None

    def test_count_active_only(self, folder_repo: IFolderRepository) -> None:
        folder_repo.insert(
            FolderConfiguration(folder_name="/a", alias="a", folder_is_active=True)
        )
        folder_repo.insert(
            FolderConfiguration(folder_name="/b", alias="b", folder_is_active=False)
        )
        assert folder_repo.count() == 2
        assert folder_repo.count(active_only=True) == 1


# ---------------------------------------------------------------------------
# IProcessedFilesRepository contract
# ---------------------------------------------------------------------------


def _make_processed_repo(kind: str, temp_database=None) -> IProcessedFilesRepository:
    if kind == "inmemory":
        return InMemoryProcessedFilesRepository()
    if kind == "sqlite":
        return SqliteProcessedFilesRepository(temp_database)
    raise ValueError(kind)


@pytest.fixture(params=["inmemory", "sqlite"])
def processed_repo(request, temp_database) -> IProcessedFilesRepository:
    return _make_processed_repo(request.param, temp_database=temp_database)


class TestIProcessedFilesRepositoryContract:
    def test_mark_then_is_processed(
        self, processed_repo: IProcessedFilesRepository
    ) -> None:
        assert not processed_repo.is_processed("h1")
        processed_repo.mark_processed(
            ProcessedFile(file_checksum="h1", folder_id=3, filename="a.edi")
        )
        assert processed_repo.is_processed("h1")

    def test_find_by_checksum_returns_record(
        self, processed_repo: IProcessedFilesRepository
    ) -> None:
        processed_repo.mark_processed(
            ProcessedFile(file_checksum="h1", folder_id=3, filename="a.edi")
        )
        got = processed_repo.find_by_checksum("h1")
        assert got is not None
        assert got.file_checksum == "h1"
        assert got.folder_id == 3
        assert got.filename == "a.edi"

    def test_find_by_checksum_returns_none_when_missing(
        self, processed_repo: IProcessedFilesRepository
    ) -> None:
        assert processed_repo.find_by_checksum("nope") is None

    def test_clear_for_folder_only_removes_target(
        self, processed_repo: IProcessedFilesRepository
    ) -> None:
        processed_repo.mark_processed(
            ProcessedFile(file_checksum="h1", folder_id=1, filename="a")
        )
        processed_repo.mark_processed(
            ProcessedFile(file_checksum="h2", folder_id=2, filename="b")
        )
        deleted = processed_repo.clear_for_folder(1)
        assert deleted == 1
        assert not processed_repo.is_processed("h1")
        assert processed_repo.is_processed("h2")

    def test_clear_all(self, processed_repo: IProcessedFilesRepository) -> None:
        processed_repo.mark_processed(
            ProcessedFile(file_checksum="h1", folder_id=1, filename="a")
        )
        processed_repo.mark_processed(
            ProcessedFile(file_checksum="h2", folder_id=1, filename="b")
        )
        assert processed_repo.clear_all() == 2
        assert processed_repo.clear_all() == 0


# ---------------------------------------------------------------------------
# ISettingsRepository contract
# ---------------------------------------------------------------------------


def _make_settings_repo(kind: str, temp_database=None) -> ISettingsRepository:
    if kind == "inmemory":
        return InMemorySettingsRepository()
    if kind == "sqlite":
        return SqliteSettingsRepository(temp_database)
    raise ValueError(kind)


@pytest.fixture(params=["inmemory", "sqlite"])
def settings_repo(request, temp_database) -> ISettingsRepository:
    return _make_settings_repo(request.param, temp_database=temp_database)


class TestISettingsRepositoryContract:
    def test_get_defaults_returns_dict(
        self, settings_repo: ISettingsRepository
    ) -> None:
        defaults = settings_repo.get_defaults()
        assert isinstance(defaults, dict)

    def test_set_and_get_setting(self, settings_repo: ISettingsRepository) -> None:
        settings_repo.set_setting("custom_key", "custom_value")
        assert settings_repo.get_setting("custom_key") == "custom_value"

    def test_get_setting_returns_none_for_missing(
        self, settings_repo: ISettingsRepository
    ) -> None:
        assert settings_repo.get_setting("nonexistent_key_xyz") is None

    def test_update_defaults_merges(self, settings_repo: ISettingsRepository) -> None:
        original = settings_repo.get_defaults()
        before_count = len(original)
        # Use a real column from the administrative table schema; the table
        # is fixed-schema so update_defaults cannot introduce new columns.
        settings_repo.update_defaults({"enable_reporting": True})
        updated = settings_repo.get_defaults()
        assert updated["enable_reporting"] is True
        # id is forced to 1
        assert updated["id"] == 1
        # Other fields preserved
        assert len(updated) >= before_count


# ---------------------------------------------------------------------------
# IEmailQueueRepository contract
# ---------------------------------------------------------------------------


def _make_email_repo(kind: str, temp_database=None) -> IEmailQueueRepository:
    if kind == "inmemory":
        return InMemoryEmailQueueRepository()
    if kind == "sqlite":
        return SqliteEmailQueueRepository(temp_database)
    raise ValueError(kind)


@pytest.fixture(params=["inmemory", "sqlite"])
def email_repo(request, temp_database) -> IEmailQueueRepository:
    return _make_email_repo(request.param, temp_database=temp_database)


class TestIEmailQueueRepositoryContract:
    def test_enqueue_then_dequeue(self, email_repo: IEmailQueueRepository) -> None:
        # emails_to_send schema columns: folder_alias, log, folder_id
        email_repo.enqueue({"folder_alias": "a", "log": "log1", "folder_id": 1})
        email_repo.enqueue({"folder_alias": "b", "log": "log2", "folder_id": 1})
        batch = email_repo.dequeue_batch(max_size=10_000, max_count=10)
        assert len(batch) == 2
        assert {e["folder_alias"] for e in batch} == {"a", "b"}

    def test_dequeue_respects_max_count(
        self, email_repo: IEmailQueueRepository
    ) -> None:
        for i in range(5):
            email_repo.enqueue({"folder_alias": f"a{i}", "log": "x", "folder_id": 1})
        batch = email_repo.dequeue_batch(max_size=10_000, max_count=3)
        assert len(batch) == 3

    def test_mark_sent_removes_records(self, email_repo: IEmailQueueRepository) -> None:
        email_repo.enqueue({"folder_alias": "a", "log": "x", "folder_id": 1})
        batch = email_repo.dequeue_batch(max_size=10_000, max_count=10)
        ids = [int(e["id"]) for e in batch]
        email_repo.mark_sent(ids)
        # The queue is now empty; another dequeue returns nothing.
        assert email_repo.dequeue_batch(max_size=10_000, max_count=10) == []

    def test_clear_queue(self, email_repo: IEmailQueueRepository) -> None:
        for i in range(3):
            email_repo.enqueue({"folder_alias": f"a{i}", "log": "x", "folder_id": 1})
        assert email_repo.clear_queue() == 3
        assert email_repo.clear_queue() == 0
