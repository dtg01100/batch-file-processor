"""
In-memory processed-files repository.

Pure-Python implementation of :class:`IProcessedFilesRepository` for
tests and ephemeral contexts. The store is a process-local dict keyed
by file_hash; collisions on the same hash are not allowed (the table's
PK is file_hash, so an existing record is treated as already processed).
"""

from core.domain.models.processed_file import ProcessedFile
from core.ports.repositories import IProcessedFilesRepository


class InMemoryProcessedFilesRepository(IProcessedFilesRepository):
    """Processed-files repository backed by an in-process dict."""

    def __init__(self) -> None:
        # file_hash -> ProcessedFile (id is auto-assigned per insert).
        self._records: dict[str, ProcessedFile] = {}
        self._next_id: int = 1

    def _next_pk(self) -> int:
        pk = self._next_id
        self._next_id += 1
        return pk

    # ------------------------------------------------------------------
    # IProcessedFilesRepository
    # ------------------------------------------------------------------

    def is_processed(self, file_hash: str) -> bool:
        return file_hash in self._records

    def mark_processed(self, record: ProcessedFile) -> None:
        pk = self._next_pk()
        self._records[record.file_hash] = ProcessedFile(
            id=pk,
            file_hash=record.file_hash,
            folder_id=record.folder_id,
            filename=record.filename,
        )

    def clear_all(self) -> int:
        count = len(self._records)
        self._records.clear()
        return count

    def clear_for_folder(self, folder_id: int) -> int:
        to_delete = [
            h for h, r in self._records.items() if r.folder_id == folder_id
        ]
        for h in to_delete:
            del self._records[h]
        return len(to_delete)

    def find_by_hash(self, file_hash: str) -> ProcessedFile | None:
        return self._records.get(file_hash)
