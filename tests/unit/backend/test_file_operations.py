"""Unit tests for file operations implementations."""

import os
import pytest
from unittest.mock import MagicMock, patch

from backend.file_operations import (
    RealFileOperations,
    MockFileOperations,
    create_file_operations,
)
from backend.protocols import FileOperationsProtocol


class TestRealFileOperations:
    """Tests for RealFileOperations implementation."""
    
    @pytest.fixture
    def file_ops(self):
        """Create a RealFileOperations instance."""
        return RealFileOperations()
    
    @pytest.fixture
    def temp_files(self, tmp_path):
        """Create temporary test files."""
        src_file = tmp_path / "source.txt"
        src_file.write_text("test content")
        dst_dir = tmp_path / "destination"
        dst_dir.mkdir()
        return {
            'src': str(src_file),
            'dst': str(dst_dir / "source.txt"),
            'dst_dir': str(dst_dir),
            'tmp_path': str(tmp_path)
        }
    
    def test_copy_copies_file(self, file_ops, temp_files):
        """Test copy copies a file."""
        file_ops.copy(temp_files['src'], temp_files['dst'])
        
        assert os.path.exists(temp_files['dst'])
        with open(temp_files['dst']) as f:
            assert f.read() == "test content"
    
    def test_copy2_preserves_metadata(self, file_ops, temp_files):
        """Test copy2 preserves file metadata."""
        file_ops.copy2(temp_files['src'], temp_files['dst'])
        
        assert os.path.exists(temp_files['dst'])
    
    def test_exists_returns_true_for_existing_path(self, file_ops, temp_files):
        """Test exists returns True for existing path."""
        assert file_ops.exists(temp_files['src']) is True
    
    def test_exists_returns_false_for_nonexistent_path(self, file_ops):
        """Test exists returns False for nonexistent path."""
        assert file_ops.exists('/nonexistent/path/file.txt') is False
    
    def test_makedirs_creates_directory(self, file_ops, tmp_path):
        """Test makedirs creates directory tree."""
        new_dir = str(tmp_path / "a" / "b" / "c")
        file_ops.makedirs(new_dir)
        
        assert os.path.isdir(new_dir)
    
    def test_makedirs_exist_ok(self, file_ops, tmp_path):
        """Test makedirs with exist_ok=True."""
        new_dir = str(tmp_path / "existing")
        file_ops.makedirs(new_dir)
        
        # Should not raise
        file_ops.makedirs(new_dir, exist_ok=True)
    
    def test_remove_deletes_file(self, file_ops, temp_files):
        """Test remove deletes a file."""
        file_ops.remove(temp_files['src'])
        
        assert not os.path.exists(temp_files['src'])
    
    def test_rmtree_removes_directory(self, file_ops, tmp_path):
        """Test rmtree removes directory and contents."""
        dir_path = tmp_path / "to_remove"
        dir_path.mkdir()
        (dir_path / "file.txt").write_text("content")
        
        file_ops.rmtree(str(dir_path))
        
        assert not os.path.exists(str(dir_path))
    
    def test_basename_returns_filename(self, file_ops):
        """Test basename returns final path component."""
        assert file_ops.basename('/path/to/file.txt') == 'file.txt'
        assert file_ops.basename('file.txt') == 'file.txt'
    
    def test_dirname_returns_directory(self, file_ops):
        """Test dirname returns directory path."""
        assert file_ops.dirname('/path/to/file.txt') == '/path/to'
    
    def test_join_combines_paths(self, file_ops):
        """Test join combines path components."""
        result = file_ops.join('path', 'to', 'file.txt')
        assert 'path' in result
        assert 'to' in result
        assert 'file.txt' in result
    
    def test_isfile_returns_true_for_file(self, file_ops, temp_files):
        """Test isfile returns True for files."""
        assert file_ops.isfile(temp_files['src']) is True
    
    def test_isfile_returns_false_for_directory(self, file_ops, temp_files):
        """Test isfile returns False for directories."""
        assert file_ops.isfile(temp_files['tmp_path']) is False
    
    def test_isdir_returns_true_for_directory(self, file_ops, temp_files):
        """Test isdir returns True for directories."""
        assert file_ops.isdir(temp_files['tmp_path']) is True
    
    def test_isdir_returns_false_for_file(self, file_ops, temp_files):
        """Test isdir returns False for files."""
        assert file_ops.isdir(temp_files['src']) is False
    
    def test_listdir_returns_directory_contents(self, file_ops, tmp_path):
        """Test listdir returns directory contents."""
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.txt").write_text("content2")
        
        contents = file_ops.listdir(str(tmp_path))
        
        assert 'file1.txt' in contents
        assert 'file2.txt' in contents
    
    def test_getsize_returns_file_size(self, file_ops, temp_files):
        """Test getsize returns file size in bytes."""
        size = file_ops.getsize(temp_files['src'])
        assert size == len("test content")
    
    def test_move_moves_file(self, file_ops, tmp_path):
        """Test move moves a file."""
        src = tmp_path / "move_src.txt"
        src.write_text("content")
        dst = tmp_path / "move_dst.txt"
        
        file_ops.move(str(src), str(dst))
        
        assert not os.path.exists(str(src))
        assert os.path.exists(str(dst))
    
    def test_rename_renames_file(self, file_ops, tmp_path):
        """Test rename renames a file."""
        src = tmp_path / "old_name.txt"
        src.write_text("content")
        dst = tmp_path / "new_name.txt"
        
        file_ops.rename(str(src), str(dst))
        
        assert not os.path.exists(str(src))
        assert os.path.exists(str(dst))
    
    def test_stat_returns_stat_result(self, file_ops, temp_files):
        """Test stat returns stat_result object."""
        stat_result = file_ops.stat(temp_files['src'])
        
        assert hasattr(stat_result, 'st_size')
        assert stat_result.st_size == len("test content")
    
    def test_abspath_returns_absolute_path(self, file_ops):
        """Test abspath returns absolute path."""
        result = file_ops.abspath('relative/path.txt')
        assert os.path.isabs(result)


class TestMockFileOperations:
    """Tests for MockFileOperations implementation."""
    
    @pytest.fixture
    def mock_ops(self):
        """Create a fresh MockFileOperations instance."""
        return MockFileOperations()
    
    def test_init_empty_state(self, mock_ops):
        """Test initial state is empty."""
        assert mock_ops.files_copied == []
        assert mock_ops.directories_created == []
        assert mock_ops.files_removed == []
        assert mock_ops.directories_removed == []
    
    def test_copy_records_operation(self, mock_ops):
        """Test copy records the operation."""
        mock_ops.copy('/src/file.txt', '/dst/file.txt')
        
        assert len(mock_ops.files_copied) == 1
        assert mock_ops.files_copied[0] == ('/src/file.txt', '/dst/file.txt')
    
    def test_copy_adds_to_existing_paths(self, mock_ops):
        """Test copy adds destination to existing paths."""
        mock_ops.copy('/src/file.txt', '/dst/file.txt')
        
        assert mock_ops.exists('/dst/file.txt')
    
    def test_copy_copies_file_content(self, mock_ops):
        """Test copy copies file content in mock filesystem."""
        mock_ops.add_file('/src/file.txt', 'test content')
        mock_ops.copy('/src/file.txt', '/dst/file.txt')
        
        assert '/dst/file.txt' in mock_ops._files
        assert mock_ops._files['/dst/file.txt'] == 'test content'
    
    def test_exists_returns_true_for_added_path(self, mock_ops):
        """Test exists returns True for added paths."""
        mock_ops.add_existing_path('/some/path')
        
        assert mock_ops.exists('/some/path') is True
    
    def test_exists_returns_false_for_unknown_path(self, mock_ops):
        """Test exists returns False for unknown paths."""
        assert mock_ops.exists('/unknown/path') is False
    
    def test_makedirs_records_operation(self, mock_ops):
        """Test makedirs records the operation."""
        mock_ops.makedirs('/new/directory', exist_ok=True)
        
        assert len(mock_ops.directories_created) == 1
        assert mock_ops.directories_created[0] == ('/new/directory', True)
    
    def test_makedirs_adds_to_directories(self, mock_ops):
        """Test makedirs adds to directories set."""
        mock_ops.makedirs('/new/directory')
        
        assert '/new/directory' in mock_ops._directories
    
    def test_remove_records_operation(self, mock_ops):
        """Test remove records the operation."""
        mock_ops.add_file('/file/to/remove.txt')
        mock_ops.remove('/file/to/remove.txt')
        
        assert '/file/to/remove.txt' in mock_ops.files_removed
        assert not mock_ops.exists('/file/to/remove.txt')
    
    def test_rmtree_records_operation(self, mock_ops):
        """Test rmtree records the operation."""
        mock_ops.add_directory('/dir/to/remove')
        mock_ops.rmtree('/dir/to/remove')
        
        assert '/dir/to/remove' in mock_ops.directories_removed
        assert not mock_ops.exists('/dir/to/remove')
    
    def test_basename_extracts_filename(self, mock_ops):
        """Test basename extracts final component."""
        assert mock_ops.basename('/path/to/file.txt') == 'file.txt'
        assert mock_ops.basename('file.txt') == 'file.txt'
        assert mock_ops.basename('C:\\path\\to\\file.txt') == 'file.txt'
    
    def test_dirname_extracts_directory(self, mock_ops):
        """Test dirname extracts directory path."""
        assert mock_ops.dirname('/path/to/file.txt') == '/path/to'
        assert mock_ops.dirname('file.txt') == ''
    
    def test_join_combines_paths(self, mock_ops):
        """Test join combines path components."""
        result = mock_ops.join('path', 'to', 'file.txt')
        assert result == 'path/to/file.txt'
    
    def test_isfile_returns_true_for_files(self, mock_ops):
        """Test isfile returns True for files."""
        mock_ops.add_file('/path/file.txt')
        
        assert mock_ops.isfile('/path/file.txt') is True
        assert mock_ops.isfile('/nonexistent') is False
    
    def test_isdir_returns_true_for_directories(self, mock_ops):
        """Test isdir returns True for directories."""
        mock_ops.add_directory('/path/to/dir')
        
        assert mock_ops.isdir('/path/to/dir') is True
        assert mock_ops.isdir('/nonexistent') is False
    
    def test_listdir_returns_directory_contents(self, mock_ops):
        """Test listdir returns directory contents."""
        mock_ops.add_file('/dir/file1.txt')
        mock_ops.add_file('/dir/file2.txt')
        mock_ops.add_directory('/dir/subdir')
        
        contents = mock_ops.listdir('/dir')
        
        assert 'file1.txt' in contents
        assert 'file2.txt' in contents
    
    def test_getsize_returns_file_size(self, mock_ops):
        """Test getsize returns file size."""
        mock_ops.add_file('/file.txt', 'test content')
        
        size = mock_ops.getsize('/file.txt')
        assert size == len('test content')
    
    def test_getsize_with_explicit_size(self, mock_ops):
        """Test getsize with explicitly set size."""
        mock_ops.add_file('/file.txt', 'content', size=1000)
        
        assert mock_ops.getsize('/file.txt') == 1000
    
    def test_move_records_operation(self, mock_ops):
        """Test move records the operation."""
        mock_ops.add_file('/src/file.txt', 'content')
        mock_ops.move('/src/file.txt', '/dst/file.txt')
        
        assert ('/src/file.txt', '/dst/file.txt') in mock_ops.files_moved
        assert not mock_ops.exists('/src/file.txt')
        assert mock_ops.exists('/dst/file.txt')
    
    def test_rename_records_operation(self, mock_ops):
        """Test rename records the operation."""
        mock_ops.rename('/old.txt', '/new.txt')
        
        assert ('/old.txt', '/new.txt') in mock_ops.files_renamed
    
    def test_stat_returns_mock_result(self, mock_ops):
        """Test stat returns mock stat result."""
        mock_ops.add_file('/file.txt', 'content')
        
        stat_result = mock_ops.stat('/file.txt')
        
        assert hasattr(stat_result, 'st_size')
        assert stat_result.st_size == len('content')
    
    def test_abspath_prefixes_relative_paths(self, mock_ops):
        """Test abspath prefixes relative paths with /."""
        assert mock_ops.abspath('relative/path.txt') == '/relative/path.txt'
        assert mock_ops.abspath('/absolute/path.txt') == '/absolute/path.txt'
    
    def test_add_error_raises_on_next_operation(self, mock_ops):
        """Test add_error raises exception on next operation."""
        mock_ops.add_error(PermissionError("Access denied"))
        
        with pytest.raises(PermissionError, match="Access denied"):
            mock_ops.copy('/src', '/dst')
    
    def test_reset_clears_all_state(self, mock_ops):
        """Test reset clears all tracking state."""
        mock_ops.copy('/src', '/dst')
        mock_ops.makedirs('/dir')
        mock_ops.remove('/file')
        mock_ops.add_file('/file.txt', 'content')
        
        mock_ops.reset()
        
        assert mock_ops.files_copied == []
        assert mock_ops.directories_created == []
        assert mock_ops.files_removed == []
        assert mock_ops._files == {}
        assert mock_ops._directories == set()


class TestCreateFileOperations:
    """Tests for create_file_operations factory function."""
    
    def test_creates_real_operations_by_default(self):
        """Test creates RealFileOperations by default."""
        ops = create_file_operations()
        assert isinstance(ops, RealFileOperations)
    
    def test_creates_mock_operations_when_requested(self):
        """Test creates MockFileOperations when mock=True."""
        ops = create_file_operations(mock=True)
        assert isinstance(ops, MockFileOperations)


class TestFileOperationsProtocolCompliance:
    """Tests for protocol compliance."""
    
    def test_real_operations_implements_protocol(self):
        """Verify RealFileOperations implements FileOperationsProtocol."""
        ops = RealFileOperations()
        assert isinstance(ops, FileOperationsProtocol)
    
    def test_mock_operations_implements_protocol(self):
        """Verify MockFileOperations implements FileOperationsProtocol."""
        ops = MockFileOperations()
        assert isinstance(ops, FileOperationsProtocol)
    
    def test_protocol_methods_exist(self):
        """Verify all protocol methods exist on implementations."""
        required_methods = [
            'copy', 'exists', 'makedirs', 'remove', 'rmtree',
            'basename', 'dirname', 'join'
        ]
        
        for ops_class in [RealFileOperations, MockFileOperations]:
            ops = ops_class()
            for method in required_methods:
                assert hasattr(ops, method), f"{ops_class.__name__} missing {method}"
                assert callable(getattr(ops, method)), f"{method} not callable"
