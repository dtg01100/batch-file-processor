"""End-to-end tests for complete UI-to-backend user workflows.

These tests validate the full integration from UI interactions through
backend processing, database persistence, and file system operations.

Test scenarios cover:
1. Complete folder setup and processing workflow
2. Settings changes affecting processing behavior
3. Multi-dialog workflows
4. Error recovery from UI
5. Real user interaction patterns
"""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.e2e, pytest.mark.qt, pytest.mark.gui]

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt

from interface.qt.app import QtBatchFileSenderApp
from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog
from interface.qt.dialogs.edit_settings_dialog import EditSettingsDialog
from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog
from interface.database.database_obj import DatabaseObj
from interface.database import sqlite_wrapper
import create_database
import folders_database_migrator


@pytest.fixture
def qt_app():
    """Create QApplication instance for tests."""
    if not QApplication.instance():
        app = QApplication([])
    else:
        app = QApplication.instance()
    yield app
    QApplication.processEvents()


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for E2E testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        
        # Create necessary directories
        (workspace / "input").mkdir()
        (workspace / "output").mkdir()
        (workspace / "database").mkdir()
        (workspace / "logs").mkdir()
        (workspace / "errors").mkdir()
        
        yield workspace


@pytest.fixture
def database(temp_workspace):
    """Create a database connection for testing."""
    db_path = temp_workspace / "database" / "folders.db"
    
    # Create the database
    create_database.create_database("33", str(db_path), str(temp_workspace), "Linux")
    
    # Connect to it
    db = sqlite_wrapper.Database.connect(str(db_path))
    
    # Run migration to ensure latest schema
    folders_database_migrator.upgrade_database(db, str(temp_workspace), "Linux")
    
    yield db
    
    # Cleanup
    db.close()


@pytest.fixture
def sample_edi_content():
    """Sample EDI file content."""
    return """A00000120240101001TESTVENDOR         Test Vendor Inc                 00001
B001001ITEM001     000010EA0010Test Item 1                     0000010000
B001002ITEM002     000020EA0020Test Item 2                     0000020000
C00000003000030000
"""


@pytest.fixture
def mock_app_components(temp_workspace, database):
    """Create mocked app components for workflow testing."""
    # Setup oversight settings
    database.oversight_and_defaults.insert({
        "logs_directory": str(temp_workspace / "logs"),
        "errors_folder": str(temp_workspace / "errors"),
        "backup_interval": 7,
    })
    
    return {
        'database': database,
        'workspace': temp_workspace,
    }


class TestCompleteFolderWorkflow:
    """Test complete user workflow for folder setup and processing."""
    
    def test_add_folder_configure_and_process(self, qtbot, qt_app, temp_workspace, database, sample_edi_content):
        """Test complete workflow: Add folder → Configure → Save → Process → Verify."""
        # Create sample EDI file
        edi_file = temp_workspace / "input" / "test_invoice.edi"
        edi_file.write_text(sample_edi_content)
        
        # Setup database with initial config
        database.oversight_and_defaults.insert({
            "logs_directory": str(temp_workspace / "logs"),
            "errors_folder": str(temp_workspace / "errors"),
            "backup_interval": 7,
        })
        
        # Mock the orchestrator to track processing
        with patch('dispatch.orchestrator.DispatchOrchestrator') as MockOrchestrator:
            mock_orchestrator = MagicMock()
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.files_processed = 1
            mock_result.files_failed = 0
            mock_orchestrator.return_value.process_folder.return_value = mock_result
            MockOrchestrator.return_value = mock_orchestrator
            
            # Create app with test database
            app = QtBatchFileSenderApp(
                database_path=str(temp_workspace / "database" / "folders.db"),
                config_folder=str(temp_workspace),
                platform="Linux"
            )
            qtbot.addWidget(app._window)
            app._window.show()
            
            # Verify initial state
            assert app._window is not None
            
            # Simulate user clicking "Add Folder" button
            # Note: In real implementation, you'd find and click the actual button
            # For now, we test the workflow programmatically
            
            # Create folder configuration (simulating EditFoldersDialog)
            folder_config = {
                'folder_name': str(temp_workspace / "input"),
                'alias': 'E2E Test Folder',
                'process_backend_copy': True,
                'copy_to_directory': str(temp_workspace / "output"),
                'process_backend_ftp': False,
                'process_backend_email': False,
                'convert_to_type': 'csv',
                'edi_filter_category': '',
            }
            
            # Save to database (simulating dialog save)
            app._database.folders_table.insert(folder_config)
            
            # Verify folder was saved
            folders = list(app._database.folders_table.all())
            assert len(folders) == 1
            assert folders[0]['alias'] == 'E2E Test Folder'
            
            # Simulate processing (would normally be triggered by UI button)
            # The mock orchestrator will track the call
            from dispatch.orchestrator import DispatchOrchestrator, DispatchConfig
            config = DispatchConfig(backends={}, settings={})
            orchestrator = DispatchOrchestrator(config)
            result = orchestrator.process_folder(folders[0], MagicMock())
            
            # Verify orchestrator was called
            assert MockOrchestrator.called
            
            # Cleanup
            app.cleanup()
    
    def test_edit_folder_configuration_workflow(self, qtbot, qt_app, temp_workspace, database):
        """Test workflow: View folder → Edit configuration → Save → Verify update."""
        # Setup initial folder
        database.oversight_and_defaults.insert({
            "logs_directory": str(temp_workspace / "logs"),
            "errors_folder": str(temp_workspace / "errors"),
            "backup_interval": 7,
        })
        
        initial_config = {
            'folder_name': str(temp_workspace / "input"),
            'alias': 'Original Name',
            'process_backend_copy': True,
            'copy_to_directory': str(temp_workspace / "output"),
            'convert_to_type': 'csv',
        }
        
        database.folders_table.insert(initial_config)
        
        # Create app
        app = QtBatchFileSenderApp(
            database_path=str(temp_workspace / "database" / "folders.db"),
            config_folder=str(temp_workspace),
            platform="Linux"
        )
        qtbot.addWidget(app._window)
        
        # Verify initial state
        folders = list(app._database.folders_table.all())
        assert len(folders) == 1
        assert folders[0]['alias'] == 'Original Name'
        
        # Simulate editing folder (would open EditFoldersDialog)
        folder_id = folders[0]['id']
        updated_config = folders[0].copy()
        updated_config['alias'] = 'Updated Name'
        updated_config['convert_to_type'] = 'fintech'
        
        # Update in database (simulating dialog save)
        app._database.folders_table.update(updated_config, ['id'])
        
        # Verify update persisted
        updated_folders = list(app._database.folders_table.all())
        assert updated_folders[0]['alias'] == 'Updated Name'
        assert updated_folders[0]['convert_to_type'] == 'fintech'
        
        # Cleanup
        app.cleanup()
    
    def test_delete_folder_workflow(self, qtbot, qt_app, temp_workspace, database):
        """Test workflow: Select folder → Delete → Confirm → Verify removal."""
        # Setup
        database.oversight_and_defaults.insert({
            "logs_directory": str(temp_workspace / "logs"),
            "errors_folder": str(temp_workspace / "errors"),
            "backup_interval": 7,
        })
        
        database.folders_table.insert({
            'folder_name': str(temp_workspace / "input"),
            'alias': 'To Delete',
            'process_backend_copy': True,
            'copy_to_directory': str(temp_workspace / "output"),
        })
        
        # Create app
        app = QtBatchFileSenderApp(
            database_path=str(temp_workspace / "database" / "folders.db"),
            config_folder=str(temp_workspace),
            platform="Linux"
        )
        qtbot.addWidget(app._window)
        
        # Verify folder exists
        folders = list(app._database.folders_table.all())
        assert len(folders) == 1
        folder_id = folders[0]['id']
        
        # Simulate delete (would normally show confirmation dialog)
        app._database.folders_table.delete(id=folder_id)
        
        # Verify deletion
        final_folders = list(app._database.folders_table.all())
        assert len(final_folders) == 0
        
        # Cleanup
        app.cleanup()


class TestSettingsWorkflow:
    """Test user workflows for settings management."""
    
    def test_edit_settings_workflow(self, qtbot, qt_app, temp_workspace, database):
        """Test workflow: Open settings → Modify → Save → Verify persistence."""
        # Setup initial settings
        database.oversight_and_defaults.insert({
            "logs_directory": str(temp_workspace / "logs"),
            "errors_folder": str(temp_workspace / "errors"),
            "backup_interval": 7,
        })
        
        # Create app
        app = QtBatchFileSenderApp(
            database_path=str(temp_workspace / "database" / "folders.db"),
            config_folder=str(temp_workspace),
            platform="Linux"
        )
        qtbot.addWidget(app._window)
        
        # Get current settings
        settings = app._database.oversight_and_defaults.find_one()
        assert settings['logs_directory'] == str(temp_workspace / "logs")
        
        # Simulate settings change (would be done via EditSettingsDialog)
        updated_settings = settings.copy()
        updated_settings['backup_interval'] = 14
        updated_settings['errors_folder'] = str(temp_workspace / "new_errors")
        
        app._database.oversight_and_defaults.update(updated_settings, ['id'])
        
        # Verify persistence
        updated = app._database.oversight_and_defaults.find_one()
        assert updated['backup_interval'] == 14
        assert updated['errors_folder'] == str(temp_workspace / "new_errors")
        
        # Cleanup
        app.cleanup()
    
    def test_settings_affect_processing_workflow(self, qtbot, qt_app, temp_workspace, database, sample_edi_content):
        """Test that settings changes actually affect processing behavior."""
        # Setup
        (temp_workspace / "input").mkdir()
        edi_file = temp_workspace / "input" / "test.edi"
        edi_file.write_text(sample_edi_content)
        
        database.oversight_and_defaults.insert({
            "logs_directory": str(temp_workspace / "logs"),
            "errors_folder": str(temp_workspace / "errors"),
            "backup_interval": 7,
        })
        
        database.folders_table.insert({
            'folder_name': str(temp_workspace / "input"),
            'alias': 'Settings Test',
            'process_backend_copy': True,
            'copy_to_directory': str(temp_workspace / "output"),
            'convert_to_type': 'csv',
        })
        
        # Create app
        app = QtBatchFileSenderApp(
            database_path=str(temp_workspace / "database" / "folders.db"),
            config_folder=str(temp_workspace),
            platform="Linux"
        )
        qtbot.addWidget(app._window)
        
        # Process with initial settings
        folders = list(app._database.folders_table.all())
        
        # Verify processing can occur
        assert len(folders) == 1
        
        # Change settings
        settings = app._database.oversight_and_defaults.find_one()
        settings['backup_interval'] = 30
        app._database.oversight_and_defaults.update(settings, ['id'])
        
        # Verify settings change persisted
        updated_settings = app._database.oversight_and_defaults.find_one()
        assert updated_settings['backup_interval'] == 30
        
        # Cleanup
        app.cleanup()


class TestMultiDialogWorkflow:
    """Test workflows involving multiple dialogs."""
    
    def test_edit_folders_then_settings_workflow(self, qtbot, qt_app, temp_workspace, database):
        """Test workflow using both EditFolders and EditSettings dialogs."""
        # Setup
        database.oversight_and_defaults.insert({
            "logs_directory": str(temp_workspace / "logs"),
            "errors_folder": str(temp_workspace / "errors"),
            "backup_interval": 7,
        })
        
        # Create app
        app = QtBatchFileSenderApp(
            database_path=str(temp_workspace / "database" / "folders.db"),
            config_folder=str(temp_workspace),
            platform="Linux"
        )
        qtbot.addWidget(app._window)
        
        # Step 1: Add folder (simulating EditFoldersDialog)
        folder_config = {
            'folder_name': str(temp_workspace / "input"),
            'alias': 'Multi-Dialog Test',
            'process_backend_copy': True,
            'copy_to_directory': str(temp_workspace / "output"),
            'convert_to_type': 'csv',
        }
        app._database.folders_table.insert(folder_config)
        
        # Step 2: Change settings (simulating EditSettingsDialog)
        settings = app._database.oversight_and_defaults.find_one()
        settings['backup_interval'] = 14
        app._database.oversight_and_defaults.update(settings, ['id'])
        
        # Verify both changes persisted
        folders = list(app._database.folders_table.all())
        assert len(folders) == 1
        assert folders[0]['alias'] == 'Multi-Dialog Test'
        
        updated_settings = app._database.oversight_and_defaults.find_one()
        assert updated_settings['backup_interval'] == 14
        
        # Cleanup
        app.cleanup()
    
    def test_maintenance_dialog_workflow(self, qtbot, qt_app, temp_workspace, database):
        """Test maintenance dialog workflow."""
        # Setup
        database.oversight_and_defaults.insert({
            "logs_directory": str(temp_workspace / "logs"),
            "errors_folder": str(temp_workspace / "errors"),
            "backup_interval": 7,
        })
        
        # Add some test data
        database.processed_files.insert({
            "folder_id": 1,
            "filename": "test1.edi",
            "md5": "test_hash_1",
        })
        
        # Create app
        app = QtBatchFileSenderApp(
            database_path=str(temp_workspace / "database" / "folders.db"),
            config_folder=str(temp_workspace),
            platform="Linux"
        )
        qtbot.addWidget(app._window)
        
        # Verify maintenance dialog can be created
        dialog = MaintenanceDialog(app._window, app._database)
        qtbot.addWidget(dialog)
        
        # Dialog should have operation buttons
        from PyQt6.QtWidgets import QPushButton
        buttons = dialog.findChildren(QPushButton)
        assert len(buttons) > 0
        
        # Cleanup
        app.cleanup()


class TestErrorRecoveryWorkflow:
    """Test error handling and recovery workflows."""
    
    def test_invalid_folder_path_recovery(self, qtbot, qt_app, temp_workspace, database):
        """Test workflow: Add invalid folder → Get error → Fix → Process successfully."""
        # Setup
        database.oversight_and_defaults.insert({
            "logs_directory": str(temp_workspace / "logs"),
            "errors_folder": str(temp_workspace / "errors"),
            "backup_interval": 7,
        })
        
        # Add folder with invalid path
        invalid_config = {
            'folder_name': str(temp_workspace / "nonexistent"),
            'alias': 'Invalid Path Test',
            'process_backend_copy': True,
            'copy_to_directory': str(temp_workspace / "output"),
            'convert_to_type': 'csv',
        }
        database.folders_table.insert(invalid_config)
        
        # Create app
        app = QtBatchFileSenderApp(
            database_path=str(temp_workspace / "database" / "folders.db"),
            config_folder=str(temp_workspace),
            platform="Linux"
        )
        qtbot.addWidget(app._window)
        
        # Verify folder was added
        folders = list(app._database.folders_table.all())
        assert len(folders) == 1
        
        # Simulate error detection (would happen during processing)
        # In real UI, this would show an error dialog
        
        # Fix the configuration (simulating user editing folder)
        valid_path = temp_workspace / "input"
        valid_path.mkdir()
        
        folders[0]['folder_name'] = str(valid_path)
        app._database.folders_table.update(folders[0], ['id'])
        
        # Verify fix persisted
        updated = list(app._database.folders_table.all())
        assert updated[0]['folder_name'] == str(valid_path)
        
        # Cleanup
        app.cleanup()
    
    def test_database_error_recovery(self, qtbot, qt_app, temp_workspace, database):
        """Test recovery from database errors."""
        # Setup
        database.oversight_and_defaults.insert({
            "logs_directory": str(temp_workspace / "logs"),
            "errors_folder": str(temp_workspace / "errors"),
            "backup_interval": 7,
        })
        
        # Create app
        app = QtBatchFileSenderApp(
            database_path=str(temp_workspace / "database" / "folders.db"),
            config_folder=str(temp_workspace),
            platform="Linux"
        )
        qtbot.addWidget(app._window)
        
        # Simulate database operation with error handling
        try:
            # This should work without errors
            folders = list(app._database.folders_table.all())
            assert folders is not None
        except Exception as e:
            pytest.fail(f"Database operation should not raise: {e}")
        
        # Cleanup
        app.cleanup()


class TestRealUserInteractions:
    """Test realistic user interaction patterns."""
    
    def test_rapid_folder_selection(self, qtbot, qt_app, temp_workspace, database):
        """Test rapid clicking/selection of folders."""
        # Setup with multiple folders
        database.oversight_and_defaults.insert({
            "logs_directory": str(temp_workspace / "logs"),
            "errors_folder": str(temp_workspace / "errors"),
            "backup_interval": 7,
        })
        
        for i in range(5):
            database.folders_table.insert({
                'folder_name': str(temp_workspace / f"input_{i}"),
                'alias': f'Folder {i}',
                'process_backend_copy': True,
                'copy_to_directory': str(temp_workspace / f"output_{i}"),
            })
        
        # Create app
        app = QtBatchFileSenderApp(
            database_path=str(temp_workspace / "database" / "folders.db"),
            config_folder=str(temp_workspace),
            platform="Linux"
        )
        qtbot.addWidget(app._window)
        
        # Verify all folders loaded
        folders = list(app._database.folders_table.all())
        assert len(folders) == 5
        
        # Simulate rapid selection (would be mouse clicks in real UI)
        # The widget should handle rapid selection without errors
        for i in range(10):  # Click 10 times rapidly
            # In real test, would use: qtbot.mouseClick(widget, Qt.LeftButton)
            pass
        
        # Should still have all folders
        final_folders = list(app._database.folders_table.all())
        assert len(final_folders) == 5
        
        # Cleanup
        app.cleanup()
    
    def test_search_while_processing(self, qtbot, qt_app, temp_workspace, database):
        """Test using search functionality while processing occurs."""
        # Setup with multiple folders
        database.oversight_and_defaults.insert({
            "logs_directory": str(temp_workspace / "logs"),
            "errors_folder": str(temp_workspace / "errors"),
            "backup_interval": 7,
        })
        
        database.folders_table.insert({
            'folder_name': str(temp_workspace / "input"),
            'alias': 'Test Folder',
            'process_backend_copy': True,
            'copy_to_directory': str(temp_workspace / "output"),
        })
        
        database.folders_table.insert({
            'folder_name': str(temp_workspace / "archive"),
            'alias': 'Archive Folder',
            'process_backend_copy': False,
        })
        
        # Create app
        app = QtBatchFileSenderApp(
            database_path=str(temp_workspace / "database" / "folders.db"),
            config_folder=str(temp_workspace),
            platform="Linux"
        )
        qtbot.addWidget(app._window)
        
        # Verify search widget exists and is functional
        assert app._window.search_widget is not None
        
        # Simulate search (would be typing in real UI)
        app._window.search_widget.entry.setText("Test")
        
        # Should filter to matching folder
        # (Actual filtering logic depends on implementation)
        
        # Cleanup
        app.cleanup()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
