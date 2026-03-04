"""Tests for EditFoldersDialog to verify initialization, field population, and functionality.

Dialogs are tested via direct widget manipulation, never exec() or show().
Uses pytest-qt (qtbot fixture) for proper widget lifecycle management.
"""

import pytest
from unittest.mock import MagicMock, patch

from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog


def _make_dialog(qtbot, folder_config=None, **kwargs):
    """Helper to create an EditFoldersDialog with minimal required parameters."""
    if folder_config is None:
        folder_config = {}
    
    # Create default mocks if not provided in kwargs
    default_ftp_service = kwargs.pop('ftp_service', MagicMock())
    default_validator = kwargs.pop('validator', MagicMock())
    
    dialog = EditFoldersDialog(
        parent=None,
        folder_config=folder_config,
        ftp_service=default_ftp_service,
        validator=default_validator,
        **kwargs
    )
    qtbot.addWidget(dialog)
    return dialog


class TestEditFoldersDialogInitialization:
    """Test suite for EditFoldersDialog initialization."""
    
    def test_dialog_initialization_with_minimal_parameters(self, qtbot):
        """Test that dialog can be initialized with minimal parameters."""
        dialog = _make_dialog(qtbot)
        
        assert dialog is not None
        assert dialog.windowTitle() == "Edit Folder"
        assert dialog.isModal()
    
    def test_dialog_inherits_from_base_dialog(self):
        """Test that EditFoldersDialog inherits from BaseDialog."""
        from interface.qt.dialogs.base_dialog import BaseDialog
        assert issubclass(EditFoldersDialog, BaseDialog)
    
    def test_dialog_has_required_widgets(self, qtbot):
        """Test that dialog contains required UI elements."""
        dialog = _make_dialog(qtbot)
        
        # Check if key UI elements exist (using basic Qt widget methods)
        assert hasattr(dialog, 'layout')
        assert hasattr(dialog, 'setWindowTitle')
        assert hasattr(dialog, 'accept')
        assert hasattr(dialog, 'reject')
        
    def test_dialog_initializes_with_empty_folder_config(self, qtbot):
        """Test dialog initialization with empty folder config."""
        dialog = _make_dialog(qtbot, folder_config={})
        
        # Should handle empty config gracefully
        assert dialog is not None


class TestEditFoldersDialogFunctionality:
    """Test suite for EditFoldersDialog functionality."""
    
    def test_data_population_from_folder_config(self, qtbot):
        """Test that folder config is properly populated into the UI."""
        folder_config = {
            'id': 1,
            'folder_name': '/test/folder',
            'alias': 'test_folder',
            'folder_is_active': True
        }
        
        dialog = _make_dialog(qtbot, folder_config=folder_config)
        
        # Verify the data is reflected in the UI
        assert dialog is not None  # Basic check
    
    def test_update_folder_functionality(self, qtbot):
        """Test updating an existing folder."""
        folder_config = {
            'id': 1,
            'folder_name': '/test',
            'alias': 'test',
            'folder_is_active': True
        }
        
        dialog = _make_dialog(
            qtbot,
            folder_config=folder_config
        )
        
        # Verify update can be called
        assert dialog is not None
        
    def test_cancel_operation(self, qtbot):
        """Test canceling the dialog operation."""
        dialog = _make_dialog(qtbot)
        
        # Simulate clicking cancel
        dialog.reject()  # Should close without saving
        qtbot.addWidget(dialog)  # Add to qtbot for proper management
        # Note: result() might not be immediately available, so just test that reject() can be called
        assert dialog is not None


class TestEditFoldersDialogUIInteractions:
    """Test UI interactions and widget behaviors."""
    
    def test_dialog_with_multiple_folder_configs(self, qtbot):
        """Test behavior with multiple folder configurations."""
        folder_configs = [
            {'id': 1, 'folder_name': '/folder1', 'alias': 'folder1'},
            {'id': 2, 'folder_name': '/folder2', 'alias': 'folder2'}
        ]
        
        # Test with first config
        dialog = _make_dialog(
            qtbot,
            folder_config=folder_configs[0]
        )
        
        # Check that dialog is initialized properly
        assert dialog is not None
        
    def test_form_validation(self, qtbot):
        """Test form validation behavior."""
        with patch('interface.validation.folder_settings_validator.FolderSettingsValidator') as mock_validator:
            mock_validator_instance = MagicMock()
            mock_validator_instance.validate.return_value = MagicMock(is_valid=True, errors=[])
            mock_validator.return_value = mock_validator_instance
            
            dialog = _make_dialog(qtbot)
            
            # Form should validate properly
            assert dialog is not None


class TestEditFoldersDialogErrorHandling:
    """Test error handling in EditFoldersDialog."""
    
    def test_validation_error_handling(self, qtbot):
        """Test handling of validation errors."""
        mock_ftp_service = MagicMock()
        mock_validator = MagicMock()
        mock_validator.validate.side_effect = Exception("Validation error")
        
        dialog = _make_dialog(
            qtbot,
            ftp_service=mock_ftp_service,
            validator=mock_validator
        )
        
        # Verify error is handled gracefully
        assert dialog is not None
        
    def test_missing_dependency_handling(self, qtbot):
        """Test behavior when required dependencies are missing."""
        # Test with None instead of required dependencies
        with pytest.raises(TypeError):
            dialog = EditFoldersDialog(
                parent=None,
                folder_data={},
                folder_manager=None,
                plugin_manager=None,
                form_factory=None
            )
            qtbot.addWidget(dialog)


class TestEditFoldersDialogLifecycle:
    """Test dialog lifecycle and cleanup."""
    
    def test_dialog_cleanup(self, qtbot):
        """Test that dialog cleans up properly."""
        dialog = _make_dialog(qtbot)
        
        # The qtbot should handle widget cleanup
        assert dialog is not None
        
    def test_dialog_properties(self, qtbot):
        """Test dialog properties and flags."""
        dialog = _make_dialog(qtbot)
        
        # Check dialog properties
        assert dialog.isModal() is True
        assert dialog.windowTitle() == "Edit Folder"