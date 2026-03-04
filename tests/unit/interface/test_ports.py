"""Unit tests for interface/ports.py.

Tests:
- UIServiceProtocol protocol definition
- ProgressServiceProtocol protocol definition
- NullUIService implements UIServiceProtocol
- NullUIService methods return correct defaults
- QtUIService implements UIServiceProtocol
- QtUIService._convert_filetypes() converts formats correctly
- QtUIService methods delegate to Qt classes correctly
"""

import pytest
from unittest.mock import MagicMock, patch, call
from interface.ports import (
    UIServiceProtocol,
    ProgressServiceProtocol,
    NullUIService,
    QtUIService,
)


class TestUIServiceProtocol:
    """Test suite for UIServiceProtocol."""

    def test_protocol_is_runtime_checkable(self):
        """Test that UIServiceProtocol is runtime checkable."""
        assert isinstance(UIServiceProtocol, type) and hasattr(UIServiceProtocol, '__is_protocol__')

    def test_null_service_satisfies_protocol(self):
        """Test that NullUIService satisfies the protocol."""
        null_service = NullUIService()
        assert isinstance(null_service, UIServiceProtocol)

    def test_qt_service_satisfies_protocol(self):
        """Test that QtUIService satisfies the protocol."""
        with patch('interface.ports.QApplication'):
            qt_service = QtUIService()
            assert isinstance(qt_service, UIServiceProtocol)


class TestProgressServiceProtocol:
    """Test suite for ProgressServiceProtocol."""

    def test_protocol_is_runtime_checkable(self):
        """Test that ProgressServiceProtocol is runtime checkable."""
        assert isinstance(ProgressServiceProtocol, type) and hasattr(ProgressServiceProtocol, '__is_protocol__')


class TestNullUIService:
    """Test suite for NullUIService."""

    def test_show_info_is_noop(self):
        """Test that show_info() is a no-op."""
        service = NullUIService()
        # Should not raise any exception
        service.show_info("Title", "Message")

    def test_show_error_is_noop(self):
        """Test that show_error() is a no-op."""
        service = NullUIService()
        # Should not raise any exception
        service.show_error("Title", "Error")

    def test_show_warning_is_noop(self):
        """Test that show_warning() is a no-op."""
        service = NullUIService()
        # Should not raise any exception
        service.show_warning("Title", "Warning")

    def test_ask_yes_no_returns_false(self):
        """Test that ask_yes_no() returns False (safe default)."""
        service = NullUIService()
        result = service.ask_yes_no("Title", "Question?")
        assert result is False

    def test_ask_ok_cancel_returns_false(self):
        """Test that ask_ok_cancel() returns False (safe default)."""
        service = NullUIService()
        result = service.ask_ok_cancel("Title", "Message")
        assert result is False

    def test_ask_directory_returns_empty_string(self):
        """Test that ask_directory() returns empty string."""
        service = NullUIService()
        result = service.ask_directory("Select Directory", "/home/user")
        assert result == ""

    def test_ask_directory_with_defaults(self):
        """Test ask_directory() with default parameters."""
        service = NullUIService()
        result = service.ask_directory()
        assert result == ""

    def test_ask_open_filename_returns_empty_string(self):
        """Test that ask_open_filename() returns empty string."""
        service = NullUIService()
        result = service.ask_open_filename("Open File", "/home/user", [("Text", "*.txt")])
        assert result == ""

    def test_ask_open_filename_with_defaults(self):
        """Test ask_open_filename() with default parameters."""
        service = NullUIService()
        result = service.ask_open_filename()
        assert result == ""

    def test_ask_save_filename_returns_empty_string(self):
        """Test that ask_save_filename() returns empty string."""
        service = NullUIService()
        result = service.ask_save_filename("Save File", "/home/user", ".txt", [("Text", "*.txt")])
        assert result == ""

    def test_ask_save_filename_with_defaults(self):
        """Test ask_save_filename() with default parameters."""
        service = NullUIService()
        result = service.ask_save_filename()
        assert result == ""

    def test_pump_events_is_noop(self):
        """Test that pump_events() is a no-op."""
        service = NullUIService()
        # Should not raise any exception
        service.pump_events()


class TestQtUIService:
    """Test suite for QtUIService."""

    def test_initialization_with_parent(self):
        """Test QtUIService initialization with parent widget."""
        with patch('interface.ports.QWidget'):
            mock_parent = MagicMock()
            with patch('interface.ports.QWidget', return_value=mock_parent):
                service = QtUIService(parent=mock_parent)
                assert service._parent == mock_parent

    def test_initialization_without_parent(self):
        """Test QtUIService initialization without parent widget."""
        with patch('interface.ports.QApplication'):
            service = QtUIService()
            assert service._parent is None

    @patch('interface.ports.QMessageBox')
    def test_show_info_delegates_to_qmessagebox(self, mock_qmessagebox):
        """Test that show_info() delegates to QMessageBox.information."""
        service = QtUIService()
        service.show_info("Test Title", "Test Message")
        mock_qmessagebox.information.assert_called_once_with(
            service._parent, "Test Title", "Test Message"
        )

    @patch('interface.ports.QMessageBox')
    def test_show_error_delegates_to_qmessagebox(self, mock_qmessagebox):
        """Test that show_error() delegates to QMessageBox.critical."""
        service = QtUIService()
        service.show_error("Test Title", "Test Error")
        mock_qmessagebox.critical.assert_called_once_with(
            service._parent, "Test Title", "Test Error"
        )

    @patch('interface.ports.QMessageBox')
    def test_show_warning_delegates_to_qmessagebox(self, mock_qmessagebox):
        """Test that show_warning() delegates to QMessageBox.warning."""
        service = QtUIService()
        service.show_warning("Test Title", "Test Warning")
        mock_qmessagebox.warning.assert_called_once_with(
            service._parent, "Test Title", "Test Warning"
        )

    @patch('interface.ports.QMessageBox')
    def test_ask_yes_no_returns_true_when_yes_clicked(self, mock_qmessagebox):
        """Test that ask_yes_no() returns True when Yes is clicked."""
        mock_qmessagebox.StandardButton = MagicMock()
        mock_qmessagebox.StandardButton.Yes = MagicMock()
        mock_qmessagebox.StandardButton.No = MagicMock()
        mock_qmessagebox.question.return_value = mock_qmessagebox.StandardButton.Yes

        service = QtUIService()
        result = service.ask_yes_no("Test Title", "Test Question")

        assert result is True
        mock_qmessagebox.question.assert_called_once()

    @patch('interface.ports.QMessageBox')
    def test_ask_yes_no_returns_false_when_no_clicked(self, mock_qmessagebox):
        """Test that ask_yes_no() returns False when No is clicked."""
        mock_qmessagebox.StandardButton = MagicMock()
        mock_qmessagebox.StandardButton.Yes = MagicMock()
        mock_qmessagebox.StandardButton.No = MagicMock()
        mock_qmessagebox.question.return_value = mock_qmessagebox.StandardButton.No

        service = QtUIService()
        result = service.ask_yes_no("Test Title", "Test Question")

        assert result is False

    @patch('interface.ports.QMessageBox')
    def test_ask_ok_cancel_returns_true_when_ok_clicked(self, mock_qmessagebox):
        """Test that ask_ok_cancel() returns True when OK is clicked."""
        mock_qmessagebox.StandardButton = MagicMock()
        mock_qmessagebox.StandardButton.Ok = MagicMock()
        mock_qmessagebox.StandardButton.Cancel = MagicMock()
        mock_qmessagebox.question.return_value = mock_qmessagebox.StandardButton.Ok

        service = QtUIService()
        result = service.ask_ok_cancel("Test Title", "Test Message")

        assert result is True

    @patch('interface.ports.QMessageBox')
    def test_ask_ok_cancel_returns_false_when_cancel_clicked(self, mock_qmessagebox):
        """Test that ask_ok_cancel() returns False when Cancel is clicked."""
        mock_qmessagebox.StandardButton = MagicMock()
        mock_qmessagebox.StandardButton.Ok = MagicMock()
        mock_qmessagebox.StandardButton.Cancel = MagicMock()
        mock_qmessagebox.question.return_value = mock_qmessagebox.StandardButton.Cancel

        service = QtUIService()
        result = service.ask_ok_cancel("Test Title", "Test Message")

        assert result is False

    @patch('interface.ports.QFileDialog')
    def test_ask_directory_returns_selected_path(self, mock_qfiledialog):
        """Test that ask_directory() returns selected directory path."""
        mock_qfiledialog.getExistingDirectory.return_value = "/selected/path"

        service = QtUIService()
        result = service.ask_directory("Select Directory", "/initial/path")

        assert result == "/selected/path"
        mock_qfiledialog.getExistingDirectory.assert_called_once_with(
            service._parent, "Select Directory", "/initial/path"
        )

    @patch('interface.ports.QFileDialog')
    def test_ask_directory_returns_empty_string_when_cancelled(self, mock_qfiledialog):
        """Test that ask_directory() returns empty string when cancelled."""
        mock_qfiledialog.getExistingDirectory.return_value = ""

        service = QtUIService()
        result = service.ask_directory("Select Directory")

        assert result == ""

    @patch('interface.ports.QFileDialog')
    def test_ask_directory_with_no_initial_dir(self, mock_qfiledialog):
        """Test ask_directory() with no initial directory."""
        mock_qfiledialog.getExistingDirectory.return_value = "/selected/path"

        service = QtUIService()
        result = service.ask_directory("Select Directory")

        assert result == "/selected/path"
        mock_qfiledialog.getExistingDirectory.assert_called_once_with(
            service._parent, "Select Directory", ""
        )

    @patch('interface.ports.QFileDialog')
    def test_ask_open_filename_returns_selected_path(self, mock_qfiledialog):
        """Test that ask_open_filename() returns selected file path."""
        mock_qfiledialog.getOpenFileName.return_value = ("/selected/path.txt", "")

        service = QtUIService()
        result = service.ask_open_filename("Open File", "/initial/path", [("Text", "*.txt")])

        assert result == "/selected/path.txt"

    @patch('interface.ports.QFileDialog')
    def test_ask_open_filename_returns_empty_string_when_cancelled(self, mock_qfiledialog):
        """Test that ask_open_filename() returns empty string when cancelled."""
        mock_qfiledialog.getOpenFileName.return_value = ("", "")

        service = QtUIService()
        result = service.ask_open_filename("Open File")

        assert result == ""

    @patch('interface.ports.QFileDialog')
    def test_ask_open_filename_with_no_filetypes(self, mock_qfiledialog):
        """Test ask_open_filename() with no filetypes."""
        mock_qfiledialog.getOpenFileName.return_value = ("/selected/path.txt", "")

        service = QtUIService()
        result = service.ask_open_filename("Open File", "/initial/path")

        assert result == "/selected/path.txt"

    @patch('interface.ports.QFileDialog')
    def test_ask_save_filename_returns_selected_path(self, mock_qfiledialog):
        """Test that ask_save_filename() returns selected file path."""
        mock_qfiledialog.getSaveFileName.return_value = ("/selected/path.txt", "")

        service = QtUIService()
        result = service.ask_save_filename("Save File", "/initial/path", ".txt", [("Text", "*.txt")])

        assert result == "/selected/path.txt"

    @patch('interface.ports.QFileDialog')
    def test_ask_save_filename_returns_empty_string_when_cancelled(self, mock_qfiledialog):
        """Test that ask_save_filename() returns empty string when cancelled."""
        mock_qfiledialog.getSaveFileName.return_value = ("", "")

        service = QtUIService()
        result = service.ask_save_filename("Save File")

        assert result == ""

    @patch('interface.ports.QFileDialog')
    def test_ask_save_filename_adds_extension_if_missing(self, mock_qfiledialog):
        """Test that ask_save_filename() adds extension if missing."""
        mock_qfiledialog.getSaveFileName.return_value = ("/selected/path", "")

        service = QtUIService()
        result = service.ask_save_filename(
            "Save File", "/initial/path", ".txt", [("Text", "*.txt")]
        )

        assert result == "/selected/path.txt"

    @patch('interface.ports.QFileDialog')
    def test_ask_save_filename_does_not_add_extension_if_present(self, mock_qfiledialog):
        """Test that ask_save_filename() doesn't add extension if already present."""
        mock_qfiledialog.getSaveFileName.return_value = ("/selected/path.txt", "")

        service = QtUIService()
        result = service.ask_save_filename(
            "Save File", "/initial/path", ".txt", [("Text", "*.txt")]
        )

        assert result == "/selected/path.txt"

    @patch('interface.ports.QApplication')
    def test_pump_events_delegates_to_process_events(self, mock_qapplication):
        """Test that pump_events() delegates to QApplication.processEvents()."""
        service = QtUIService()
        service.pump_events()
        mock_qapplication.processEvents.assert_called_once()


class TestQtUIServiceConvertFiletypes:
    """Test suite for QtUIService._convert_filetypes()."""

    def test_convert_empty_filetypes(self):
        """Test converting empty filetypes list."""
        result = QtUIService._convert_filetypes(None)
        assert result == ""

    def test_convert_single_filetype(self):
        """Test converting single filetype."""
        filetypes = [("Text files", "*.txt")]
        result = QtUIService._convert_filetypes(filetypes)
        assert result == "Text files (*.txt)"

    def test_convert_multiple_filetypes(self):
        """Test converting multiple filetypes."""
        filetypes = [
            ("Text files", "*.txt"),
            ("CSV files", "*.csv"),
            ("All files", "*.*")
        ]
        result = QtUIService._convert_filetypes(filetypes)
        assert result == "Text files (*.txt);;CSV files (*.csv);;All files (*.*)"

    def test_convert_filetype_with_multiple_patterns(self):
        """Test converting filetype with multiple patterns."""
        filetypes = [("Image files", "*.png;*.jpg;*.gif")]
        result = QtUIService._convert_filetypes(filetypes)
        assert result == "Image files (*.png;*.jpg;*.gif)"

    def test_convert_filetype_with_complex_pattern(self):
        """Test converting filetype with complex pattern."""
        filetypes = [("EDI files", "*.edi;*.001;*.002")]
        result = QtUIService._convert_filetypes(filetypes)
        assert result == "EDI files (*.edi;*.001;*.002)"


class TestQtUIServiceIntegration:
    """Integration tests for QtUIService."""

    @patch('interface.ports.QMessageBox')
    @patch('interface.ports.QFileDialog')
    @patch('interface.ports.QApplication')
    def test_all_methods_callable(self, mock_qapp, mock_qfiledialog, mock_qmessagebox):
        """Test that all protocol methods are callable."""
        # Setup mocks
        mock_qmessagebox.question.return_value = MagicMock()
        mock_qfiledialog.getExistingDirectory.return_value = ""
        mock_qfiledialog.getOpenFileName.return_value = ("", "")
        mock_qfiledialog.getSaveFileName.return_value = ("", "")

        service = QtUIService()

        # Call all methods to ensure they work
        service.show_info("Title", "Message")
        service.show_error("Title", "Error")
        service.show_warning("Title", "Warning")
        service.ask_yes_no("Title", "Question?")
        service.ask_ok_cancel("Title", "Message")
        service.ask_directory("Title", "/path")
        service.ask_open_filename("Title", "/path", [("Text", "*.txt")])
        service.ask_save_filename("Title", "/path", ".txt", [("Text", "*.txt")])
        service.pump_events()

        # Verify all Qt methods were called
        assert mock_qmessagebox.information.called
        assert mock_qmessagebox.critical.called
        assert mock_qmessagebox.warning.called
        assert mock_qmessagebox.question.called
        assert mock_qfiledialog.getExistingDirectory.called
        assert mock_qfiledialog.getOpenFileName.called
        assert mock_qfiledialog.getSaveFileName.called
        assert mock_qapp.processEvents.called


class TestNullUIServiceUseCases:
    """Use case tests for NullUIService."""

    def test_headless_operation_no_ui_needed(self):
        """Test that NullUIService allows headless operation."""
        service = NullUIService()

        # Simulate a workflow that would normally show dialogs
        service.show_info("Processing", "Starting...")
        service.pump_events()
        result = service.ask_yes_no("Continue", "Continue processing?")

        # All operations complete without errors
        assert result is False  # Default safe response

    def test_testing_environment_no_ui_interactions(self):
        """Test that NullUIService is suitable for testing."""
        service = NullUIService()

        # Simulate test scenario
        service.show_error("Test Error", "Simulated error for testing")
        service.show_warning("Test Warning", "Simulated warning for testing")
        file_path = service.ask_open_filename("Open File")

        # All operations complete without showing real UI
        assert file_path == ""

    def test_conservative_defaults_for_safety(self):
        """Test that NullUIService returns conservative defaults for safety."""
        service = NullUIService()

        # Question dialogs return False (safe default)
        assert service.ask_yes_no("Delete", "Delete all files?") is False
        assert service.ask_ok_cancel("Confirm", "Confirm destructive action?") is False

        # File dialogs return empty string (no selection)
        assert service.ask_directory() == ""
        assert service.ask_open_filename() == ""
        assert service.ask_save_filename() == ""


class TestProtocolCompliance:
    """Test protocol compliance for all services."""

    def test_null_service_implements_all_protocol_methods(self):
        """Test that NullUIService implements all UIServiceProtocol methods."""
        service = NullUIService()

        # Check all methods exist and are callable
        assert callable(service.show_info)
        assert callable(service.show_error)
        assert callable(service.show_warning)
        assert callable(service.ask_yes_no)
        assert callable(service.ask_ok_cancel)
        assert callable(service.ask_directory)
        assert callable(service.ask_open_filename)
        assert callable(service.ask_save_filename)
        assert callable(service.pump_events)

    def test_qt_service_implements_all_protocol_methods(self):
        """Test that QtUIService implements all UIServiceProtocol methods."""
        with patch('interface.ports.QApplication'):
            service = QtUIService()

            # Check all methods exist and are callable
            assert callable(service.show_info)
            assert callable(service.show_error)
            assert callable(service.show_warning)
            assert callable(service.ask_yes_no)
            assert callable(service.ask_ok_cancel)
            assert callable(service.ask_directory)
            assert callable(service.ask_open_filename)
            assert callable(service.ask_save_filename)
            assert callable(service.pump_events)

    def test_services_satisfy_protocol_at_runtime(self):
        """Test that services satisfy UIServiceProtocol at runtime."""
        null_service = NullUIService()
        with patch('interface.ports.QApplication'):
            qt_service = QtUIService()

        # Both should satisfy the protocol
        assert isinstance(null_service, UIServiceProtocol)
        assert isinstance(qt_service, UIServiceProtocol)