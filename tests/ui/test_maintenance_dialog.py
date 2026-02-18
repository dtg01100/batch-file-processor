"""
Aggressive unit tests for interface/ui/dialogs/maintenance_dialog.py.

Tests are designed to run headlessly using mocks for all tkinter objects.
Uses method-level testing to avoid complex dialog initialization.
"""

from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import dataclass

import pytest


class TestMaintenanceFunctionsSetInactive:
    """Tests for MaintenanceFunctions.set_all_inactive() method."""

    def test_set_all_inactive_calls_database_query(self):
        """Test that set_all_inactive executes database query."""
        from interface.ui.dialogs.maintenance_dialog import MaintenanceFunctions
        
        mock_db = MagicMock()
        mock_db.database_connection = MagicMock()
        
        maintenance = MaintenanceFunctions(mock_db)
        
        maintenance.set_all_inactive()
            
        mock_db.database_connection.query.assert_called_once()


class TestMaintenanceFunctionsSetActive:
    """Tests for MaintenanceFunctions.set_all_active() method."""

    def test_set_all_active_calls_database_query(self):
        """Test that set_all_active executes database query."""
        from interface.ui.dialogs.maintenance_dialog import MaintenanceFunctions
        
        mock_db = MagicMock()
        mock_db.database_connection = MagicMock()
        
        maintenance = MaintenanceFunctions(mock_db)
        
        maintenance.set_all_active()
            
        mock_db.database_connection.query.assert_called_once()


class TestMaintenanceFunctionsClearResendFlags:
    """Tests for MaintenanceFunctions.clear_resend_flags() method."""

    def test_clear_resend_flags_updates_database(self):
        """Test that clear_resend_flags executes database query."""
        from interface.ui.dialogs.maintenance_dialog import MaintenanceFunctions
        
        mock_db = MagicMock()
        
        maintenance = MaintenanceFunctions(mock_db)
        
        maintenance.clear_resend_flags()
            
        mock_db.database_connection.query.assert_called_once()


class TestMaintenanceFunctionsClearProcessedFilesLog:
    """Tests for MaintenanceFunctions.clear_processed_files_log() method."""

    def test_clear_processed_files_log_prompts_user(self):
        """Test that clear_processed_files_log deletes when confirmed."""
        from interface.ui.dialogs.maintenance_dialog import MaintenanceFunctions
        
        mock_db = MagicMock()
        
        maintenance = MaintenanceFunctions(
            mock_db,
            confirm_callback=lambda msg: True,
        )
        
        maintenance.clear_processed_files_log()
        
        mock_db.processed_files.delete.assert_called_once()

    def test_clear_processed_files_log_cancelled(self):
        """Test that clear_processed_files_log does nothing when cancelled."""
        from interface.ui.dialogs.maintenance_dialog import MaintenanceFunctions
        
        mock_db = MagicMock()
        
        maintenance = MaintenanceFunctions(
            mock_db,
            confirm_callback=lambda msg: False,
        )
        
        maintenance.clear_processed_files_log()
        
        mock_db.processed_files.delete.assert_not_called()


class TestMaintenanceFunctionsRemoveInactive:
    """Tests for MaintenanceFunctions.remove_inactive_folders() method."""

    def test_remove_inactive_folders_calls_callback(self):
        """Test that remove_inactive_folders calls delete callback."""
        from interface.ui.dialogs.maintenance_dialog import MaintenanceFunctions
        
        mock_db = MagicMock()
        mock_db.folders_table.count = MagicMock(return_value=1)
        mock_db.folders_table.find = MagicMock(return_value=[{'id': 1}])
        
        delete_called = []
        def delete_callback(folder_id):
            delete_called.append(folder_id)
        
        maintenance = MaintenanceFunctions(
            mock_db, 
            refresh_callback=MagicMock(),
            delete_folder_callback=delete_callback
        )
        
        maintenance.remove_inactive_folders()
            
        assert 1 in delete_called


class TestMaintenanceFunctionsDatabaseImport:
    """Tests for MaintenanceFunctions.database_import_wrapper() method."""

    def test_database_import_wrapper_success(self):
        """Test successful database import."""
        from interface.ui.dialogs.maintenance_dialog import MaintenanceFunctions
        
        mock_db = MagicMock()
        mock_settings = {'enable_email': False}
        mock_db.settings.find_one = MagicMock(return_value=mock_settings)
        mock_db.folders_table.find = MagicMock(return_value=[])
        mock_db.reload = MagicMock()
        
        maintenance = MaintenanceFunctions(
            mock_db,
            database_path='/test/path',
            running_platform='Linux',
            database_version='1.0'
        )
        
        with patch('interface.ui.dialogs.maintenance_dialog.database_import.import_interface', return_value=True):
            maintenance.database_import_wrapper('/backup/path')
                
            mock_db.reload.assert_called_once()


class TestMaintenanceFunctionsMarkActiveAsProcessed:
    """Tests for MaintenanceFunctions.mark_active_as_processed() method."""

    def test_mark_active_as_processed_with_no_folders(self):
        """Test mark_active_as_processed with no active folders."""
        from interface.ui.dialogs.maintenance_dialog import MaintenanceFunctions
        
        mock_db = MagicMock()
        mock_db.folders_table.find = MagicMock(return_value=[])
        
        maintenance = MaintenanceFunctions(mock_db)
        
        maintenance.mark_active_as_processed()
            
            # Should handle gracefully with no folders


class TestMaintenanceDialog:
    """Tests for show_maintenance_dialog function."""

    def test_show_maintenance_dialog_cancelled(self):
        """Test that show_maintenance_dialog returns None when cancelled."""
        from interface.ui.dialogs.maintenance_dialog import show_maintenance_dialog
        
        with patch('interface.ui.dialogs.maintenance_dialog.askokcancel', return_value=False):
            result = show_maintenance_dialog(
                root=MagicMock(),
                database_obj=MagicMock(),
                database_path='/test/path',
                running_platform='Linux',
                database_version='1.0',
                refresh_callback=MagicMock(),
                set_button_states_callback=MagicMock(),
                delete_folder_callback=MagicMock()
            )
            
            assert result is None


class TestMaintenanceFunctionsProgressCallback:
    """Tests for progress callback integration."""

    def test_set_all_active_uses_progress_callback(self):
        """Test that set_all_active calls progress callback."""
        from interface.ui.dialogs.maintenance_dialog import MaintenanceFunctions
        
        mock_db = MagicMock()
        mock_db.database_connection = MagicMock()
        mock_progress = MagicMock()
        
        maintenance = MaintenanceFunctions(mock_db, progress_callback=mock_progress)
        
        maintenance.set_all_active()
        
        mock_progress.show.assert_called_once_with("Working...")
        mock_progress.hide.assert_called_once()

    def test_operation_start_end_callbacks(self):
        """Test that on_operation_start/end callbacks are called."""
        from interface.ui.dialogs.maintenance_dialog import MaintenanceFunctions
        
        mock_db = MagicMock()
        mock_db.database_connection = MagicMock()
        on_start = MagicMock()
        on_end = MagicMock()
        
        maintenance = MaintenanceFunctions(
            mock_db,
            on_operation_start=on_start,
            on_operation_end=on_end,
        )
        
        maintenance.set_all_inactive()
        
        on_start.assert_called_once()
        on_end.assert_called_once()


class TestMaintenanceFunctionsCallbackIntegration:
    """Tests for callback integration in MaintenanceFunctions."""

    def test_set_all_active_calls_refresh_callback(self):
        """Test that set_all_active calls refresh callback."""
        from interface.ui.dialogs.maintenance_dialog import MaintenanceFunctions
        
        mock_db = MagicMock()
        mock_db.database_connection = MagicMock()
        
        refresh_called = []
        def refresh_callback():
            refresh_called.append(True)
        
        maintenance = MaintenanceFunctions(
            mock_db, 
            refresh_callback=refresh_callback
        )
        
        maintenance.set_all_active()
            
        assert len(refresh_called) == 1

    def test_set_all_inactive_calls_refresh_callback(self):
        """Test that set_all_inactive calls refresh callback."""
        from interface.ui.dialogs.maintenance_dialog import MaintenanceFunctions
        
        mock_db = MagicMock()
        mock_db.database_connection = MagicMock()
        
        refresh_called = []
        def refresh_callback():
            refresh_called.append(True)
        
        maintenance = MaintenanceFunctions(
            mock_db, 
            refresh_callback=refresh_callback
        )
        
        maintenance.set_all_inactive()
            
        assert len(refresh_called) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
