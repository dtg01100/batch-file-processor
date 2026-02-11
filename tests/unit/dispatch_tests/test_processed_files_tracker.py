"""Tests for the ProcessedFilesTracker.

This module tests the refactored processed files tracker with mock database.
"""

import pytest
from datetime import datetime

from dispatch.processed_files_tracker import (
    ProcessedFileRecord,
    DatabaseProtocol,
    InMemoryDatabase,
    ProcessedFilesTracker,
    create_processed_files_tracker,
)


class TestProcessedFileRecord:
    """Tests for ProcessedFileRecord dataclass."""
    
    def test_record_creation(self):
        """Test creating a ProcessedFileRecord."""
        now = datetime.now()
        record = ProcessedFileRecord(
            file_name="test.txt",
            folder_id=1,
            file_checksum="abc123",
            sent_date_time=now,
            resend_flag=False
        )
        
        assert record.file_name == "test.txt"
        assert record.folder_id == 1
        assert record.file_checksum == "abc123"
        assert record.sent_date_time == now
        assert record.resend_flag is False
    
    def test_record_defaults(self):
        """Test default values for ProcessedFileRecord."""
        now = datetime.now()
        record = ProcessedFileRecord(
            file_name="test.txt",
            folder_id=1,
            file_checksum="abc123",
            sent_date_time=now
        )
        
        assert record.resend_flag is False
        assert record.additional_data == {}
    
    def test_to_dict(self):
        """Test converting record to dictionary."""
        now = datetime(2024, 1, 15, 10, 30, 0)
        record = ProcessedFileRecord(
            file_name="test.txt",
            folder_id=1,
            file_checksum="abc123",
            sent_date_time=now,
            resend_flag=True,
            additional_data={'key': 'value'}
        )
        
        result = record.to_dict()
        
        assert result['file_name'] == "test.txt"
        assert result['folder_id'] == 1
        assert result['file_checksum'] == "abc123"
        assert result['sent_date_time'] == "2024-01-15T10:30:00"
        assert result['resend_flag'] is True
        assert result['additional_data'] == {'key': 'value'}
    
    def test_from_dict(self):
        """Test creating record from dictionary."""
        data = {
            'file_name': 'test.txt',
            'folder_id': 2,
            'file_checksum': 'def456',
            'sent_date_time': '2024-01-15T10:30:00',
            'resend_flag': True,
            'additional_data': {'extra': 'info'}
        }
        
        record = ProcessedFileRecord.from_dict(data)
        
        assert record.file_name == "test.txt"
        assert record.folder_id == 2
        assert record.file_checksum == "def456"
        assert record.sent_date_time == datetime(2024, 1, 15, 10, 30, 0)
        assert record.resend_flag is True
        assert record.additional_data == {'extra': 'info'}
    
    def test_from_dict_with_datetime_object(self):
        """Test from_dict with datetime object instead of string."""
        now = datetime.now()
        data = {
            'file_name': 'test.txt',
            'folder_id': 1,
            'file_checksum': 'abc',
            'sent_date_time': now
        }
        
        record = ProcessedFileRecord.from_dict(data)
        
        assert record.sent_date_time == now
    
    def test_from_dict_with_missing_fields(self):
        """Test from_dict handles missing fields gracefully."""
        data = {'file_name': 'test.txt'}
        
        record = ProcessedFileRecord.from_dict(data)
        
        assert record.file_name == "test.txt"
        assert record.folder_id == 0
        assert record.file_checksum == ""
        assert record.resend_flag is False


class TestInMemoryDatabase:
    """Tests for InMemoryDatabase."""
    
    def test_insert_and_find(self):
        """Test inserting and finding records."""
        db = InMemoryDatabase()
        
        db.insert('test_table', {'name': 'Alice', 'age': 30})
        db.insert('test_table', {'name': 'Bob', 'age': 25})
        
        results = db.find('test_table')
        assert len(results) == 2
    
    def test_find_with_filter(self):
        """Test finding records with filter."""
        db = InMemoryDatabase()
        
        db.insert('test_table', {'name': 'Alice', 'age': 30})
        db.insert('test_table', {'name': 'Bob', 'age': 25})
        db.insert('test_table', {'name': 'Charlie', 'age': 30})
        
        results = db.find('test_table', age=30)
        
        assert len(results) == 2
        names = [r['name'] for r in results]
        assert 'Alice' in names
        assert 'Charlie' in names
        assert 'Bob' not in names
    
    def test_find_one(self):
        """Test finding a single record."""
        db = InMemoryDatabase()
        
        db.insert('test_table', {'name': 'Alice', 'id': 1})
        db.insert('test_table', {'name': 'Bob', 'id': 2})
        
        result = db.find_one('test_table', id=1)
        
        assert result['name'] == 'Alice'
    
    def test_find_one_returns_none(self):
        """Test find_one returns None when not found."""
        db = InMemoryDatabase()
        
        result = db.find_one('test_table', name='Nonexistent')
        
        assert result is None
    
    def test_update(self):
        """Test updating a record."""
        db = InMemoryDatabase()
        
        db.insert('test_table', {'id': 1, 'name': 'Alice', 'active': True})
        
        db.update('test_table', {'id': 1, 'name': 'Alice', 'active': False}, keys=['id'])
        
        result = db.find_one('test_table', id=1)
        assert result['active'] is False
    
    def test_delete(self):
        """Test deleting records."""
        db = InMemoryDatabase()
        
        db.insert('test_table', {'name': 'Alice', 'age': 30})
        db.insert('test_table', {'name': 'Bob', 'age': 25})
        
        db.delete('test_table', name='Alice')
        
        results = db.find('test_table')
        assert len(results) == 1
        assert results[0]['name'] == 'Bob'
    
    def test_delete_all(self):
        """Test deleting all records in a table."""
        db = InMemoryDatabase()
        
        db.insert('test_table', {'name': 'Alice'})
        db.insert('test_table', {'name': 'Bob'})
        
        db.delete('test_table')
        
        assert len(db.find('test_table')) == 0
    
    def test_count(self):
        """Test counting records."""
        db = InMemoryDatabase()
        
        db.insert('test_table', {'name': 'Alice', 'age': 30})
        db.insert('test_table', {'name': 'Bob', 'age': 25})
        db.insert('test_table', {'name': 'Charlie', 'age': 30})
        
        assert db.count('test_table') == 3
        assert db.count('test_table', age=30) == 2
    
    def test_clear_table(self):
        """Test clearing a specific table."""
        db = InMemoryDatabase()
        
        db.insert('table1', {'name': 'Alice'})
        db.insert('table2', {'name': 'Bob'})
        
        db.clear('table1')
        
        assert len(db.find('table1')) == 0
        assert len(db.find('table2')) == 1
    
    def test_clear_all(self):
        """Test clearing all tables."""
        db = InMemoryDatabase()
        
        db.insert('table1', {'name': 'Alice'})
        db.insert('table2', {'name': 'Bob'})
        
        db.clear()
        
        assert len(db.find('table1')) == 0
        assert len(db.find('table2')) == 0


class TestProcessedFilesTracker:
    """Tests for ProcessedFilesTracker."""
    
    @pytest.fixture
    def tracker(self):
        """Create a tracker with in-memory database."""
        db = InMemoryDatabase()
        return ProcessedFilesTracker(database=db)
    
    def test_record_sent_file(self, tracker):
        """Test recording a sent file."""
        record = ProcessedFileRecord(
            file_name="test.txt",
            folder_id=1,
            file_checksum="abc123",
            sent_date_time=datetime.now()
        )
        
        tracker.record_sent_file(record)
        
        assert tracker.count_files() == 1
    
    def test_record_sent_file_simple(self, tracker):
        """Test recording a sent file with simple parameters."""
        tracker.record_sent_file_simple(
            file_name="simple.txt",
            folder_id=2,
            file_checksum="def456"
        )
        
        assert tracker.count_files() == 1
        files = tracker.get_files_by_folder(2)
        assert len(files) == 1
        assert files[0].file_name == "simple.txt"
    
    def test_record_sent_file_simple_with_datetime(self, tracker):
        """Test recording with explicit datetime."""
        now = datetime(2024, 1, 15, 10, 30, 0)
        
        tracker.record_sent_file_simple(
            file_name="timed.txt",
            folder_id=1,
            file_checksum="xyz",
            sent_date_time=now
        )
        
        files = tracker.get_files_by_folder(1)
        assert files[0].sent_date_time == now
    
    def test_get_files_by_folder(self, tracker):
        """Test getting files by folder ID."""
        tracker.record_sent_file_simple("file1.txt", 1, "abc")
        tracker.record_sent_file_simple("file2.txt", 1, "def")
        tracker.record_sent_file_simple("file3.txt", 2, "ghi")
        
        files = tracker.get_files_by_folder(1)
        
        assert len(files) == 2
        names = [f.file_name for f in files]
        assert "file1.txt" in names
        assert "file2.txt" in names
        assert "file3.txt" not in names
    
    def test_get_files_by_checksum(self, tracker):
        """Test getting files by checksum."""
        tracker.record_sent_file_simple("file1.txt", 1, "checksum_a")
        tracker.record_sent_file_simple("file2.txt", 2, "checksum_a")
        tracker.record_sent_file_simple("file3.txt", 3, "checksum_b")
        
        files = tracker.get_files_by_checksum("checksum_a")
        
        assert len(files) == 2
        names = [f.file_name for f in files]
        assert "file1.txt" in names
        assert "file2.txt" in names
    
    def test_get_file_by_name_and_folder(self, tracker):
        """Test getting a specific file."""
        tracker.record_sent_file_simple("unique.txt", 1, "abc")
        
        result = tracker.get_file_by_name_and_folder("unique.txt", 1)
        
        assert result is not None
        assert result.file_name == "unique.txt"
    
    def test_get_file_by_name_and_folder_not_found(self, tracker):
        """Test getting a non-existent file."""
        result = tracker.get_file_by_name_and_folder("nonexistent.txt", 999)
        
        assert result is None
    
    def test_mark_for_resend(self, tracker):
        """Test marking a file for resend."""
        tracker.record_sent_file_simple("resend.txt", 1, "abc")
        
        result = tracker.mark_for_resend("resend.txt", 1)
        
        assert result is True
        files = tracker.get_files_for_resend()
        assert len(files) == 1
        assert files[0].file_name == "resend.txt"
    
    def test_mark_for_resend_not_found(self, tracker):
        """Test marking non-existent file for resend."""
        result = tracker.mark_for_resend("nonexistent.txt", 999)
        
        assert result is False
    
    def test_clear_resend_flag(self, tracker):
        """Test clearing resend flag."""
        tracker.record_sent_file_simple("clear.txt", 1, "abc")
        tracker.mark_for_resend("clear.txt", 1)
        
        result = tracker.clear_resend_flag("clear.txt", 1)
        
        assert result is True
        files = tracker.get_files_for_resend()
        assert len(files) == 0
    
    def test_clear_resend_flag_not_found(self, tracker):
        """Test clearing flag on non-existent file."""
        result = tracker.clear_resend_flag("nonexistent.txt", 999)
        
        assert result is False
    
    def test_get_files_for_resend_by_folder(self, tracker):
        """Test getting files for resend filtered by folder."""
        tracker.record_sent_file_simple("file1.txt", 1, "a")
        tracker.record_sent_file_simple("file2.txt", 2, "b")
        tracker.mark_for_resend("file1.txt", 1)
        tracker.mark_for_resend("file2.txt", 2)
        
        files = tracker.get_files_for_resend(folder_id=1)
        
        assert len(files) == 1
        assert files[0].file_name == "file1.txt"
    
    def test_file_exists(self, tracker):
        """Test checking if file exists."""
        tracker.record_sent_file_simple("exists.txt", 1, "abc")
        
        assert tracker.file_exists("exists.txt", 1) is True
        assert tracker.file_exists("nonexistent.txt", 1) is False
        assert tracker.file_exists("exists.txt", 999) is False
    
    def test_count_files(self, tracker):
        """Test counting files."""
        tracker.record_sent_file_simple("file1.txt", 1, "a")
        tracker.record_sent_file_simple("file2.txt", 1, "b")
        tracker.record_sent_file_simple("file3.txt", 2, "c")
        
        assert tracker.count_files() == 3
        assert tracker.count_files(folder_id=1) == 2
        assert tracker.count_files(folder_id=2) == 1
    
    def test_delete_file_record(self, tracker):
        """Test deleting a file record."""
        tracker.record_sent_file_simple("delete.txt", 1, "abc")
        
        tracker.delete_file_record("delete.txt", 1)
        
        assert tracker.file_exists("delete.txt", 1) is False


class TestProcessedFilesTrackerProtocol:
    """Tests for Protocol compliance."""
    
    def test_in_memory_database_implements_protocol(self):
        """Test that InMemoryDatabase implements DatabaseProtocol."""
        db = InMemoryDatabase()
        
        assert isinstance(db, DatabaseProtocol)


class TestCreateProcessedFilesTracker:
    """Tests for factory function."""
    
    def test_create_with_default_database(self):
        """Test creating tracker with default in-memory database."""
        tracker = create_processed_files_tracker()
        
        assert isinstance(tracker, ProcessedFilesTracker)
        assert isinstance(tracker.database, InMemoryDatabase)
    
    def test_create_with_custom_database(self):
        """Test creating tracker with custom database."""
        db = InMemoryDatabase()
        tracker = create_processed_files_tracker(database=db)
        
        assert tracker.database is db


class TestProcessedFilesTrackerIntegration:
    """Integration tests for ProcessedFilesTracker."""
    
    def test_full_workflow(self):
        """Test a complete workflow of tracking files."""
        db = InMemoryDatabase()
        tracker = ProcessedFilesTracker(database=db)
        
        # Record several files
        tracker.record_sent_file_simple("doc1.pdf", 1, "hash1")
        tracker.record_sent_file_simple("doc2.pdf", 1, "hash2")
        tracker.record_sent_file_simple("doc3.pdf", 2, "hash3")
        
        # Verify counts
        assert tracker.count_files() == 3
        assert tracker.count_files(folder_id=1) == 2
        
        # Mark one for resend
        tracker.mark_for_resend("doc1.pdf", 1)
        
        # Get files for resend
        resend_files = tracker.get_files_for_resend()
        assert len(resend_files) == 1
        
        # Clear resend flag
        tracker.clear_resend_flag("doc1.pdf", 1)
        assert len(tracker.get_files_for_resend()) == 0
        
        # Delete a file
        tracker.delete_file_record("doc2.pdf", 1)
        assert tracker.count_files() == 2
    
    def test_duplicate_file_handling(self):
        """Test handling duplicate file records."""
        db = InMemoryDatabase()
        tracker = ProcessedFilesTracker(database=db)
        
        # Record same file twice (different checksums for same name/folder)
        tracker.record_sent_file_simple("report.txt", 1, "hash1")
        tracker.record_sent_file_simple("report.txt", 1, "hash2")
        
        # Both records should exist
        files = tracker.get_files_by_folder(1)
        assert len(files) == 2
    
    def test_cross_folder_same_filename(self):
        """Test same filename in different folders."""
        db = InMemoryDatabase()
        tracker = ProcessedFilesTracker(database=db)
        
        # Same filename in different folders
        tracker.record_sent_file_simple("report.txt", 1, "hash1")
        tracker.record_sent_file_simple("report.txt", 2, "hash2")
        
        # Both should exist independently
        assert tracker.file_exists("report.txt", 1)
        assert tracker.file_exists("report.txt", 2)
        
        # Mark one for resend shouldn't affect the other
        tracker.mark_for_resend("report.txt", 1)
        
        resend_files = tracker.get_files_for_resend()
        assert len(resend_files) == 1
        assert resend_files[0].folder_id == 1
