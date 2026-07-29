"""
Unit tests for SqliteProcessedFilesRepository.

Uses a mock database_obj (no real DB connection required) to verify
the repository correctly delegates to the underlying Table API and
maps row dicts to ProcessedFile domain objects.
"""

from unittest.mock import MagicMock

from adapters.sqlite.repositories.sqlite_processed_files_repo import (
    SqliteProcessedFilesRepository,
)
from backend.database.database_obj import DatabaseObj, TableProtocol
from core.domain.models.processed_file import ProcessedFile
from core.ports.repositories import IProcessedFilesRepository


def _make_db():
    db = MagicMock(spec=DatabaseObj)
    db.processed_files = MagicMock(spec=TableProtocol)
    return db


class TestIProcessedFilesRepositoryConformance:
    def test_is_instance_of_interface(self):
        repo = SqliteProcessedFilesRepository(_make_db())
        assert isinstance(repo, IProcessedFilesRepository)


class TestIsProcessed:
    def test_returns_true_when_record_found(self):
        db = _make_db()
        db.processed_files.find_one.return_value = {"id": 1, "file_checksum": "abc123"}
        repo = SqliteProcessedFilesRepository(db)

        assert repo.is_processed("abc123") is True
        db.processed_files.find_one.assert_called_once_with(file_checksum="abc123")

    def test_returns_false_when_not_found(self):
        db = _make_db()
        db.processed_files.find_one.return_value = None
        repo = SqliteProcessedFilesRepository(db)

        assert repo.is_processed("nope") is False


class TestMarkProcessed:
    def test_inserts_processedfile(self):
        db = _make_db()
        repo = SqliteProcessedFilesRepository(db)

        repo.mark_processed(
            ProcessedFile(file_checksum="hash1", folder_id=3, filename="file.edi")
        )

        db.processed_files.insert.assert_called_once_with(
            {"file_checksum": "hash1", "folder_id": 3, "filename": "file.edi"}
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


class TestFindByChecksum:
    def test_returns_processedfile_when_found(self):
        db = _make_db()
        db.processed_files.find_one.return_value = {
            "id": 5,
            "file_checksum": "xyz",
            "folder_id": 7,
            "filename": "x.edi",
        }
        repo = SqliteProcessedFilesRepository(db)

        result = repo.find_by_checksum("xyz")

        db.processed_files.find_one.assert_called_once_with(file_checksum="xyz")
        assert isinstance(result, ProcessedFile)
        assert result.id == 5
        assert result.file_checksum == "xyz"
        assert result.folder_id == 7
        assert result.filename == "x.edi"

    def test_returns_none_when_not_found(self):
        db = _make_db()
        db.processed_files.find_one.return_value = None
        repo = SqliteProcessedFilesRepository(db)

        assert repo.find_by_checksum("missing") is None
