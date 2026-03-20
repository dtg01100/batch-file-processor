"""
Unit tests for SqliteFolderRepository.

Uses a mock database_obj (no real DB connection required) to verify
the repository correctly delegates to the underlying Table API.
"""

from unittest.mock import MagicMock

import pytest

from adapters.sqlite.repositories import SqliteFolderRepository
from core.ports.repositories import IFolderRepository

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db(folders=None):
    """Return a mock database_obj with a mock folders_table.

    Args:
        folders: Optional list of folder dicts returned by all() / find().
    """
    db = MagicMock()
    table = MagicMock()
    db.folders_table = table

    if folders is not None:
        table.all.return_value = list(folders)
        table.find.return_value = [f for f in folders if f.get("folder_is_active")]
    else:
        table.all.return_value = []
        table.find.return_value = []

    return db, table


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


class TestIFolderRepositoryConformance:
    """SqliteFolderRepository must satisfy IFolderRepository."""

    def test_is_instance_of_interface(self):
        db, _ = _make_db()
        repo = SqliteFolderRepository(db)
        assert isinstance(repo, IFolderRepository)


# ---------------------------------------------------------------------------
# find_all
# ---------------------------------------------------------------------------


class TestFindAll:
    def test_find_all_returns_all_folders(self):
        folders = [
            {"id": 1, "folder_name": "/a", "folder_is_active": True},
            {"id": 2, "folder_name": "/b", "folder_is_active": False},
        ]
        db, table = _make_db(folders)
        repo = SqliteFolderRepository(db)

        result = repo.find_all()

        table.all.assert_called_once()
        assert len(result) == 2

    def test_find_all_active_only_uses_find(self):
        folders = [{"id": 1, "folder_name": "/a", "folder_is_active": True}]
        db, table = _make_db(folders)
        repo = SqliteFolderRepository(db)

        result = repo.find_all(active_only=True)

        table.find.assert_called_once_with(folder_is_active=True)
        assert len(result) == 1

    def test_find_all_not_active_only_does_not_call_find(self):
        db, table = _make_db()
        repo = SqliteFolderRepository(db)

        repo.find_all(active_only=False)

        table.find.assert_not_called()


# ---------------------------------------------------------------------------
# find_by_id
# ---------------------------------------------------------------------------


class TestFindById:
    def test_delegates_to_find_one(self):
        folder = {"id": 7, "folder_name": "/x"}
        db, table = _make_db()
        table.find_one.return_value = folder
        repo = SqliteFolderRepository(db)

        result = repo.find_by_id(7)

        table.find_one.assert_called_once_with(id=7)
        assert result == folder

    def test_returns_none_when_not_found(self):
        db, table = _make_db()
        table.find_one.return_value = None
        repo = SqliteFolderRepository(db)

        result = repo.find_by_id(999)

        assert result is None


# ---------------------------------------------------------------------------
# find_by_path
# ---------------------------------------------------------------------------


class TestFindByPath:
    def test_returns_matching_folder(self):
        folders = [
            {"id": 1, "folder_name": "/some/path"},
            {"id": 2, "folder_name": "/other/path"},
        ]
        db, table = _make_db(folders)
        repo = SqliteFolderRepository(db)

        result = repo.find_by_path("/some/path")

        assert result is not None
        assert result["id"] == 1

    def test_normalises_trailing_slash(self):
        folders = [{"id": 1, "folder_name": "/some/path"}]
        db, table = _make_db(folders)
        repo = SqliteFolderRepository(db)

        # os.path.normpath strips trailing slash
        result = repo.find_by_path("/some/path/")

        assert result is not None
        assert result["id"] == 1

    def test_returns_none_when_not_found(self):
        db, table = _make_db()
        repo = SqliteFolderRepository(db)

        result = repo.find_by_path("/nonexistent")

        assert result is None


# ---------------------------------------------------------------------------
# find_by_alias
# ---------------------------------------------------------------------------


class TestFindByAlias:
    def test_delegates_to_find_one(self):
        folder = {"id": 3, "alias": "MyFolder"}
        db, table = _make_db()
        table.find_one.return_value = folder
        repo = SqliteFolderRepository(db)

        result = repo.find_by_alias("MyFolder")

        table.find_one.assert_called_once_with(alias="MyFolder")
        assert result == folder


# ---------------------------------------------------------------------------
# insert
# ---------------------------------------------------------------------------


class TestInsert:
    def test_strips_id_before_inserting(self):
        db, table = _make_db()
        repo = SqliteFolderRepository(db)

        repo.insert({"id": 99, "folder_name": "/new", "alias": "new"})

        call_args = table.insert.call_args[0][0]
        assert "id" not in call_args
        assert call_args["folder_name"] == "/new"

    def test_inserts_without_id_unchanged(self):
        db, table = _make_db()
        repo = SqliteFolderRepository(db)

        repo.insert({"folder_name": "/new", "alias": "new"})

        call_args = table.insert.call_args[0][0]
        assert call_args == {"folder_name": "/new", "alias": "new"}


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


class TestUpdate:
    def test_calls_table_update_with_id_key(self):
        db, table = _make_db()
        repo = SqliteFolderRepository(db)

        repo.update({"id": 5, "alias": "Updated"})

        table.update.assert_called_once_with({"id": 5, "alias": "Updated"}, ["id"])

    def test_raises_if_no_id(self):
        db, table = _make_db()
        repo = SqliteFolderRepository(db)

        with pytest.raises(ValueError, match="must contain 'id'"):
            repo.update({"alias": "NoId"})


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


class TestDelete:
    def test_delegates_to_table_delete(self):
        db, table = _make_db()
        repo = SqliteFolderRepository(db)

        repo.delete(42)

        table.delete.assert_called_once_with(id=42)


# ---------------------------------------------------------------------------
# count
# ---------------------------------------------------------------------------


class TestCount:
    def test_count_all(self):
        db, table = _make_db()
        table.count.return_value = 5
        repo = SqliteFolderRepository(db)

        result = repo.count()

        table.count.assert_called_once_with()
        assert result == 5

    def test_count_active_only(self):
        db, table = _make_db()
        table.count.return_value = 3
        repo = SqliteFolderRepository(db)

        result = repo.count(active_only=True)

        table.count.assert_called_once_with(folder_is_active=True)
        assert result == 3
