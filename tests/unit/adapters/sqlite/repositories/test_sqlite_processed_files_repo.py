"""
Unit tests for SqliteProcessedFilesRepository.
"""

from unittest.mock import MagicMock

from adapters.sqlite.repositories import SqliteProcessedFilesRepository
from core.ports.repositories import IProcessedFilesRepository


def _make_db():
    db = MagicMock()
    db.processed_files = MagicMock()
    return db


class TestIProcessedFilesRepositoryConformance:
    def test_is_instance_of_interface(self):
        repo = SqliteProcessedFilesRepository(_make_db())
        assert isinstance(repo, IProcessedFilesRepository)


class TestIsProcessed:
    def test_returns_true_when_record_found(self):
        db = _make_db()
        db.processed_files.find_one.return_value = {"id": 1, "file_hash": "abc123"}
        repo = SqliteProcessedFilesRepository(db)

        assert repo.is_processed("abc123") is True
        db.processed_files.find_one.assert_called_once_with(file_hash="abc123")

    def test_returns_false_when_not_found(self):
        db = _make_db()
        db.processed_files.find_one.return_value = None
        repo = SqliteProcessedFilesRepository(db)

        assert repo.is_processed("nope") is False


class TestMarkProcessed:
    def test_inserts_record(self):
        db = _make_db()
        repo = SqliteProcessedFilesRepository(db)

        repo.mark_processed("hash1", folder_id=3, filename="file.edi")

        db.processed_files.insert.assert_called_once_with(
            {"file_hash": "hash1", "folder_id": 3, "filename": "file.edi"}
        )


class TestClearAll:
    def test_deletes_all_and_returns_count(self):
        db = _make_db()
        db.processed_files.count.return_value = 7
        repo = SqliteProcessedFilesRepository(db)

        result = repo.clear_all()

        db.processed_files.count.assert_called_once_with()
        db.processed_files.delete.assert_called_once_with()
        assert result == 7


class TestClearForFolder:
    def test_deletes_by_folder_id_and_returns_count(self):
        db = _make_db()
        db.processed_files.count.return_value = 4
        repo = SqliteProcessedFilesRepository(db)

        result = repo.clear_for_folder(folder_id=2)

        db.processed_files.count.assert_called_once_with(folder_id=2)
        db.processed_files.delete.assert_called_once_with(folder_id=2)
        assert result == 4


class TestFindByHash:
    def test_delegates_to_find_one(self):
        db = _make_db()
        record = {"id": 5, "file_hash": "xyz"}
        db.processed_files.find_one.return_value = record
        repo = SqliteProcessedFilesRepository(db)

        result = repo.find_by_hash("xyz")

        db.processed_files.find_one.assert_called_once_with(file_hash="xyz")
        assert result == record

    def test_returns_none_when_not_found(self):
        db = _make_db()
        db.processed_files.find_one.return_value = None
        repo = SqliteProcessedFilesRepository(db)

        assert repo.find_by_hash("missing") is None
