"""Unit tests for interface/ports.py.

Tests:
- UIServiceProtocol protocol definition
- ProgressServiceProtocol protocol definition
- NullUIService implements UIServiceProtocol
- NullUIService methods return correct defaults

The former Qt adapter (``QtUIService``) was removed with the Qt UI layer
in the webapp pivot; the headless ``NullUIService`` and the protocols
remain.
"""

import pytest

from interface.ports import (
    NullUIService,
    ProgressServiceProtocol,
    UIServiceProtocol,
)

pytestmark = [pytest.mark.unit]


class TestUIServiceProtocol:
    """Test suite for UIServiceProtocol."""

    def test_protocol_is_runtime_checkable(self):
        """Test that UIServiceProtocol is runtime checkable."""
        assert isinstance(UIServiceProtocol, type) and hasattr(
            UIServiceProtocol, "_is_protocol"
        )

    def test_null_service_satisfies_protocol(self):
        """Test that NullUIService satisfies the protocol."""
        null_service = NullUIService()
        assert isinstance(null_service, UIServiceProtocol)


class TestProgressServiceProtocol:
    """Test suite for ProgressServiceProtocol."""

    def test_protocol_is_runtime_checkable(self):
        """Test that ProgressServiceProtocol is runtime checkable."""
        assert isinstance(ProgressServiceProtocol, type) and hasattr(
            ProgressServiceProtocol, "_is_protocol"
        )


class TestNullUIService:
    """Test suite for NullUIService."""

    def test_show_info_is_noop(self):
        """Test that show_info() is a no-op (returns None)."""
        service = NullUIService()
        assert service.show_info("Title", "Message") is None

    def test_show_error_is_noop(self):
        """Test that show_error() is a no-op (returns None)."""
        service = NullUIService()
        assert service.show_error("Title", "Error") is None

    def test_show_warning_is_noop(self):
        """Test that show_warning() is a no-op (returns None)."""
        service = NullUIService()
        assert service.show_warning("Title", "Warning") is None

    def test_ask_yes_no_returns_false(self):
        """Test that ask_yes_no() returns False (safe default)."""
        service = NullUIService()
        result = service.ask_yes_no("Title", "Question?")
        assert not result

    def test_ask_ok_cancel_returns_false(self):
        """Test that ask_ok_cancel() returns False (safe default)."""
        service = NullUIService()
        result = service.ask_ok_cancel("Title", "Message")
        assert not result

    def test_ask_three_choices_returns_minus_one(self):
        """Test that ask_three_choices() returns -1 (safe default)."""
        service = NullUIService()
        result = service.ask_three_choices(
            "Title", "Message", "Choice 1", "Choice 2", "Cancel"
        )
        assert result == -1

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
        result = service.ask_open_filename(
            "Open File", "/home/user", [("Text", "*.txt")]
        )
        assert result == ""

    def test_ask_open_filename_with_defaults(self):
        """Test ask_open_filename() with default parameters."""
        service = NullUIService()
        result = service.ask_open_filename()
        assert result == ""

    def test_ask_save_filename_returns_empty_string(self):
        """Test that ask_save_filename() returns empty string."""
        service = NullUIService()
        result = service.ask_save_filename(
            "Save File", "/home/user", ".txt", [("Text", "*.txt")]
        )
        assert result == ""

    def test_ask_save_filename_with_defaults(self):
        """Test ask_save_filename() with default parameters."""
        service = NullUIService()
        result = service.ask_save_filename()
        assert result == ""

    def test_pump_events_is_noop(self):
        """Test that pump_events() is a no-op (returns None)."""
        service = NullUIService()
        assert service.pump_events() is None


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
        assert not result  # Default safe response

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
    """Test protocol compliance for the null service."""

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

    def test_services_satisfy_protocol_at_runtime(self):
        """Test that NullUIService satisfies UIServiceProtocol at runtime."""
        null_service = NullUIService()

        # Should satisfy the protocol
        assert isinstance(null_service, UIServiceProtocol)
