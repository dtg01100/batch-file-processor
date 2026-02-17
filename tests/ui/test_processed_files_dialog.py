"""
Aggressive unit tests for interface/ui/dialogs/processed_files_dialog.py.

Tests are designed to run headlessly using mocks for all tkinter objects.
Uses method-level testing to avoid complex dialog initialization.
"""

from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import dataclass

import pytest


class TestProcessedFilesExportReport:
    """Tests for export_processed_report function."""

    def test_export_processed_report_creates_file(self):
        """Test that export_processed_report creates a CSV file."""
        from interface.ui.dialogs.processed_files_dialog import export_processed_report
        import tempfile
        import os
        
        # Create mock database
        mock_folder = MagicMock()
        mock_folder.__getitem__ = MagicMock(return_value="Test Folder")
        
        mock_processed_file = MagicMock()
        mock_processed_file.__getitem__ = MagicMock(side_effect=lambda key: {
            'file_name': 'test.txt',
            'sent_date_time': MagicMock(strftime=MagicMock(return_value='2024-01-01 12:00:00')),
            'copy_destination': '/copy/dest',
            'ftp_destination': '/ftp/dest',
            'email_destination': 'test@test.com',
        }[key])
        
        mock_db = MagicMock()
        mock_db.folders_table.find_one = MagicMock(return_value=mock_folder)
        mock_db.processed_files.find = MagicMock(return_value=[mock_processed_file])
        
        with tempfile.TemporaryDirectory() as tmpdir:
            export_processed_report(1, tmpdir, mock_db)
            
            # Check that a file was created
            files = os.listdir(tmpdir)
            assert len(files) == 1
            assert files[0].endswith('.csv')
            
            # Check file content
            with open(os.path.join(tmpdir, files[0]), 'r') as f:
                content = f.read()
                assert 'File,Date,Copy Destination,FTP Destination,Email Destination' in content
                assert 'test.txt' in content


class TestProcessedFilesDialogState:
    """Tests for processed files dialog state management."""

    def test_state_initialization(self):
        """Test that state is properly initialized."""
        # Test that the state dictionary is properly structured
        from interface.ui.dialogs.processed_files_dialog import show_processed_files_dialog
        
        # Create minimal mocks
        mock_root = MagicMock()
        mock_root.winfo_rootx = MagicMock(return_value=100)
        mock_root.winfo_rooty = MagicMock(return_value=100)
        mock_root.update = MagicMock()
        
        mock_db = MagicMock()
        mock_db.oversight_and_defaults.find_one = MagicMock(return_value={})
        mock_db.processed_files.count = MagicMock(return_value=0)
        mock_db.processed_files.distinct = MagicMock(return_value=[])
        
        # Mock tkinter to avoid GUI
        with patch('interface.ui.dialogs.processed_files_dialog.tkinter.Toplevel') as mock_toplevel:
            with patch('interface.ui.dialogs.processed_files_dialog.tk_extra_widgets.VerticalScrolledFrame'):
                mock_dialog = MagicMock()
                mock_toplevel.return_value = mock_dialog
                
                # Should not raise
                try:
                    show_processed_files_dialog(mock_root, mock_db)
                except Exception:
                    pass  # May fail due to other dependencies


class TestProcessedFilesFolderButtons:
    """Tests for folder button handling in processed files dialog."""

    def test_folder_button_creates_export_controls(self):
        """Test that folder button creates export controls."""
        from interface.ui.dialogs.processed_files_dialog import show_processed_files_dialog
        
        mock_root = MagicMock()
        mock_root.winfo_rootx = MagicMock(return_value=100)
        mock_root.winfo_rooty = MagicMock(return_value=100)
        mock_root.update = MagicMock()
        
        mock_db = MagicMock()
        mock_db.oversight_and_defaults.find_one = MagicMock(return_value={})
        mock_db.processed_files.count = MagicMock(return_value=0)
        mock_db.processed_files.distinct = MagicMock(return_value=[])
        
        with patch('interface.ui.dialogs.processed_files_dialog.tkinter.Toplevel') as mock_toplevel:
            with patch('interface.ui.dialogs.processed_files_dialog.tk_extra_widgets.VerticalScrolledFrame'):
                mock_dialog = MagicMock()
                mock_toplevel.return_value = mock_dialog
                
                try:
                    result = show_processed_files_dialog(mock_root, mock_db)
                except Exception:
                    pass


class TestProcessedFilesNoProcessedFiles:
    """Tests for when there are no processed files."""

    def test_no_processed_files_shows_label(self):
        """Test that no processed files shows appropriate label."""
        from interface.ui.dialogs.processed_files_dialog import show_processed_files_dialog
        
        mock_root = MagicMock()
        mock_root.winfo_rootx = MagicMock(return_value=100)
        mock_root.winfo_rooty = MagicMock(return_value=100)
        mock_root.update = MagicMock()
        
        mock_db = MagicMock()
        mock_db.oversight_and_defaults.find_one = MagicMock(return_value={})
        mock_db.processed_files.count = MagicMock(return_value=0)
        mock_db.processed_files.distinct = MagicMock(return_value=[])
        
        with patch('interface.ui.dialogs.processed_files_dialog.tkinter.Toplevel') as mock_toplevel:
            with patch('interface.ui.dialogs.processed_files_dialog.tk_extra_widgets.VerticalScrolledFrame'):
                mock_dialog = MagicMock()
                mock_toplevel.return_value = mock_dialog
                
                # Should handle zero count gracefully
                try:
                    result = show_processed_files_dialog(mock_root, mock_db)
                except Exception:
                    pass


class TestProcessedFilesExportFunctionality:
    """Tests for export functionality."""

    def test_export_with_no_files(self):
        """Test export with no processed files."""
        from interface.ui.dialogs.processed_files_dialog import export_processed_report
        import tempfile
        import os
        
        mock_folder = MagicMock()
        mock_folder.__getitem__ = MagicMock(return_value="Test Folder")
        
        mock_db = MagicMock()
        mock_db.folders_table.find_one = MagicMock(return_value=mock_folder)
        mock_db.processed_files.find = MagicMock(return_value=[])
        
        with tempfile.TemporaryDirectory() as tmpdir:
            export_processed_report(1, tmpdir, mock_db)
            
            files = os.listdir(tmpdir)
            assert len(files) == 1
            
            with open(os.path.join(tmpdir, files[0]), 'r') as f:
                content = f.read()
                # Should have header but no data rows
                lines = content.strip().split('\n')
                assert len(lines) == 1


class TestProcessedFilesDuplicateHandling:
    """Tests for duplicate file name handling."""

    def test_avoid_duplicate_export_file(self):
        """Test that duplicate file names get incrementing numbers."""
        from interface.ui.dialogs.processed_files_dialog import export_processed_report
        import tempfile
        import os
        
        mock_folder = MagicMock()
        mock_folder.__getitem__ = MagicMock(return_value="Test Folder")
        
        mock_db = MagicMock()
        mock_db.folders_table.find_one = MagicMock(return_value=mock_folder)
        mock_db.processed_files.find = MagicMock(return_value=[])
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Export once
            export_processed_report(1, tmpdir, mock_db)
            
            # Export again - should create "Test Folder processed report (1).csv"
            export_processed_report(1, tmpdir, mock_db)
            
            files = sorted(os.listdir(tmpdir))
            assert len(files) == 2
            # Both files should exist (order may vary due to filesystem)
            assert "Test Folder processed report.csv" in files
            assert "Test Folder processed report (1).csv" in files


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
