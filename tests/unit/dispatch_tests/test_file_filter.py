"""Tests for dispatch.services.file_filter module.

Covers:
- SQL-based skipped checksums extraction
- find()-based fallback for in-memory/mock tables
- Resend semantics: any record with resend_flag=1 prevents skipping
- mtime pre-filter behaviour
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from webapp.pipeline.services.file_filter import (
    filter_pending_files,
    get_skipped_checksums,
    record_file_mtime,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class InMemoryTable:
    """Minimal in-memory table that supports ``find()`` but not SQL."""

    def __init__(self):
        self.records: list[dict] = []

    def find(self, folder_id=None, **kwargs):
        result = list(self.records)
        if folder_id is not None:
            result = [r for r in result if r.get("folder_id") == folder_id]
        for k, v in kwargs.items():
            result = [r for r in result if r.get(k) == v]
        return result


class SQLTable:
    """In-memory SQLite-backed table that supports raw SQL."""

    def __init__(self):
        self._conn = sqlite3.connect(":memory:")
        self._conn.execute("""
            CREATE TABLE processed_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT,
                folder_id INTEGER,
                file_checksum TEXT,
                resend_flag INTEGER,
                file_mtime REAL
            )
            """)
        self._conn.commit()

    @property
    def raw_connection(self):
        return self._conn

    def find(self, folder_id=None, **kwargs):
        sql = "SELECT * FROM processed_files"
        conditions = []
        params = []
        if folder_id is not None:
            conditions.append("folder_id = ?")
            params.append(folder_id)
        for k, v in kwargs.items():
            conditions.append(f"{k} = ?")
            params.append(v)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        cur = self._conn.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def insert(self, record):
        cols = ", ".join(record.keys())
        placeholders = ", ".join("?" for _ in record)
        self._conn.execute(
            f"INSERT INTO processed_files ({cols}) VALUES ({placeholders})",
            tuple(record.values()),
        )
        self._conn.commit()


def _touch(path: Path, content: str = "data") -> str:
    path.write_text(content)
    return str(path)


# ---------------------------------------------------------------------------
# get_skipped_checksums — SQL mode
# ---------------------------------------------------------------------------


class TestGetSkippedChecksumsSQL:
    def test_empty_table(self):
        table = SQLTable()
        assert get_skipped_checksums(table, 1) == set()

    def test_single_record_no_resend(self):
        table = SQLTable()
        table.insert(
            {
                "file_name": "/f.txt",
                "folder_id": 1,
                "file_checksum": "abc",
                "resend_flag": 0,
            }
        )
        assert get_skipped_checksums(table, 1) == {"abc"}

    def test_single_record_with_resend(self):
        table = SQLTable()
        table.insert(
            {
                "file_name": "/f.txt",
                "folder_id": 1,
                "file_checksum": "abc",
                "resend_flag": 1,
            }
        )
        assert get_skipped_checksums(table, 1) == set()

    def test_multiple_records_any_resend_allows_checksum(self):
        """If ANY record for a checksum has resend_flag=1, the checksum
        must NOT be in the skipped set (fixes the legacy bug)."""
        table = SQLTable()
        table.insert(
            {
                "file_name": "/f.txt",
                "folder_id": 1,
                "file_checksum": "abc",
                "resend_flag": 0,
            }
        )
        table.insert(
            {
                "file_name": "/f.txt",
                "folder_id": 1,
                "file_checksum": "abc",
                "resend_flag": 1,
            }
        )
        # Because one record has resend_flag=1, "abc" must NOT be skipped
        assert get_skipped_checksums(table, 1) == set()

    def test_multiple_records_all_no_resend(self):
        table = SQLTable()
        table.insert(
            {
                "file_name": "/f.txt",
                "folder_id": 1,
                "file_checksum": "abc",
                "resend_flag": 0,
            }
        )
        table.insert(
            {
                "file_name": "/f.txt",
                "folder_id": 1,
                "file_checksum": "abc",
                "resend_flag": 0,
            }
        )
        assert get_skipped_checksums(table, 1) == {"abc"}

    def test_null_resend_flag_treated_as_no_resend(self):
        table = SQLTable()
        table.insert({"file_name": "/f.txt", "folder_id": 1, "file_checksum": "abc"})
        assert get_skipped_checksums(table, 1) == {"abc"}

    def test_null_checksum_ignored(self):
        table = SQLTable()
        table.insert(
            {
                "file_name": "/f.txt",
                "folder_id": 1,
                "file_checksum": None,
                "resend_flag": 0,
            }
        )
        assert get_skipped_checksums(table, 1) == set()

    def test_different_folders_isolated(self):
        table = SQLTable()
        table.insert(
            {
                "file_name": "/f.txt",
                "folder_id": 1,
                "file_checksum": "abc",
                "resend_flag": 0,
            }
        )
        table.insert(
            {
                "file_name": "/f.txt",
                "folder_id": 2,
                "file_checksum": "abc",
                "resend_flag": 1,
            }
        )
        # folder 1: no resend, so abc is skipped
        assert get_skipped_checksums(table, 1) == {"abc"}
        # folder 2: resend, so abc is NOT skipped
        assert get_skipped_checksums(table, 2) == set()


# ---------------------------------------------------------------------------
# get_skipped_checksums — find() fallback
# ---------------------------------------------------------------------------


class TestGetSkippedChecksumsFindFallback:
    def test_empty_table(self):
        table = InMemoryTable()
        assert get_skipped_checksums(table, 1) == set()

    def test_single_record_no_resend(self):
        table = InMemoryTable()
        table.records.append(
            {
                "file_name": "/f.txt",
                "folder_id": 1,
                "file_checksum": "abc",
                "resend_flag": 0,
            }
        )
        assert get_skipped_checksums(table, 1) == {"abc"}

    def test_single_record_with_resend(self):
        table = InMemoryTable()
        table.records.append(
            {
                "file_name": "/f.txt",
                "folder_id": 1,
                "file_checksum": "abc",
                "resend_flag": 1,
            }
        )
        assert get_skipped_checksums(table, 1) == set()

    def test_multiple_records_any_resend_allows_checksum(self):
        table = InMemoryTable()
        table.records.append(
            {
                "file_name": "/f.txt",
                "folder_id": 1,
                "file_checksum": "abc",
                "resend_flag": 0,
            }
        )
        table.records.append(
            {
                "file_name": "/f.txt",
                "folder_id": 1,
                "file_checksum": "abc",
                "resend_flag": 1,
            }
        )
        assert get_skipped_checksums(table, 1) == set()


# ---------------------------------------------------------------------------
# filter_pending_files — end-to-end
# ---------------------------------------------------------------------------


class TestFilterPendingFiles:
    def test_no_previous_records_returns_all(self, tmp_path: Path):
        table = InMemoryTable()
        f1 = _touch(tmp_path / "a.txt", "hello")
        f2 = _touch(tmp_path / "b.txt", "world")
        result = filter_pending_files(table, 1, [f1, f2])
        assert result == [f1, f2]

    def test_already_processed_is_skipped(self, tmp_path: Path):
        table = SQLTable()
        f1 = _touch(tmp_path / "a.txt", "hello")
        from core.utils.file_utils import calculate_file_checksum

        cs = calculate_file_checksum(f1)
        table.insert(
            {"file_name": f1, "folder_id": 1, "file_checksum": cs, "resend_flag": 0}
        )
        result = filter_pending_files(table, 1, [f1])
        assert result == []

    def test_resend_flag_bypasses_skip(self, tmp_path: Path):
        table = SQLTable()
        f1 = _touch(tmp_path / "a.txt", "hello")
        from core.utils.file_utils import calculate_file_checksum

        cs = calculate_file_checksum(f1)
        table.insert(
            {"file_name": f1, "folder_id": 1, "file_checksum": cs, "resend_flag": 1}
        )
        result = filter_pending_files(table, 1, [f1])
        assert result == [f1]


# ---------------------------------------------------------------------------
# mtime pre-filter
# ---------------------------------------------------------------------------


class TestMtimePreFilter:
    def test_mtime_match_skips_checksum_calc(self, tmp_path: Path):
        table = SQLTable()
        f1 = _touch(tmp_path / "a.txt", "hello")
        import os

        from core.utils.file_utils import calculate_file_checksum

        cs = calculate_file_checksum(f1)
        mt = os.path.getmtime(f1)
        table.insert(
            {
                "file_name": f1,
                "folder_id": 1,
                "file_checksum": cs,
                "resend_flag": 0,
                "file_mtime": mt,
            }
        )
        # Same mtime → skip without checksum calc
        result = filter_pending_files(table, 1, [f1])
        assert result == []

    def test_mtime_mismatch_falls_back_to_checksum(self, tmp_path: Path):
        table = SQLTable()
        f1 = _touch(tmp_path / "a.txt", "hello")
        from core.utils.file_utils import calculate_file_checksum

        cs = calculate_file_checksum(f1)
        # Store a stale mtime that doesn't match the current file
        table.insert(
            {
                "file_name": f1,
                "folder_id": 1,
                "file_checksum": cs,
                "resend_flag": 0,
                "file_mtime": 0.0,
            }
        )
        # mtime differs → checksum calc → skip (content unchanged)
        result = filter_pending_files(table, 1, [f1])
        assert result == []

    def test_mtime_mismatch_with_different_content(self, tmp_path: Path):
        table = SQLTable()
        f1 = _touch(tmp_path / "a.txt", "original")
        from core.utils.file_utils import calculate_file_checksum

        old_cs = calculate_file_checksum(f1)
        # Store a stale mtime that is guaranteed to differ
        stale_mtime = 1000000.0
        table.insert(
            {
                "file_name": f1,
                "folder_id": 1,
                "file_checksum": old_cs,
                "resend_flag": 0,
                "file_mtime": stale_mtime,
            }
        )
        # Modify file → new content → new checksum → should be processed
        f1_path = Path(f1)
        f1_path.write_text("modified content")
        result = filter_pending_files(table, 1, [f1])
        assert result == [f1]


# ---------------------------------------------------------------------------
# record_file_mtime
# ---------------------------------------------------------------------------


class TestRecordFileMtime:
    def test_existing_file(self, tmp_path: Path):
        f = _touch(tmp_path / "a.txt")
        result = record_file_mtime(f)
        assert result is not None
        assert result > 0

    def test_missing_file(self):
        assert record_file_mtime("/nonexistent/path/file.txt") is None
