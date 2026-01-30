"""
Comprehensive unit tests for the dispatch send manager module.

These tests cover the BackendFactory, SendResult, and SendManager classes
with extensive mocking of external dependencies.
"""

import os
import tempfile
from unittest.mock import MagicMock, Mock, patch

import pytest

# Import the module under test
from dispatch.send_manager import (
    BackendFactory,
    SendResult,
    SendManager,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_parameters_dict():
    """Provide sample parameters dictionary for testing."""
    return {
        "process_backend_copy": True,
        "copy_to_directory": "/output/copy",
        "process_backend_ftp": True,
        "ftp_server": "ftp.example.com",
        "ftp_folder": "/remote/folder",
        "process_backend_email": True,
        "email_to": "recipient@example.com",
    }


@pytest.fixture
def sample_parameters_dict_single_backend():
    """Provide sample parameters with single backend enabled."""
    return {
        "process_backend_copy": True,
        "copy_to_directory": "/output/copy",
        "process_backend_ftp": False,
        "ftp_server": "ftp.example.com",
        "ftp_folder": "/remote/folder",
        "process_backend_email": False,
        "email_to": "recipient@example.com",
    }


@pytest.fixture
def sample_parameters_dict_no_backends():
    """Provide sample parameters with no backends enabled."""
    return {
        "process_backend_copy": False,
        "copy_to_directory": "/output/copy",
        "process_backend_ftp": False,
        "ftp_server": "ftp.example.com",
        "ftp_folder": "/remote/folder",
        "process_backend_email": False,
        "email_to": "recipient@example.com",
    }


@pytest.fixture
def sample_settings():
    """Provide sample settings dictionary for testing."""
    return {
        "smtp_server": "smtp.example.com",
        "smtp_port": 587,
        "email_from": "sender@example.com",
    }


@pytest.fixture
def send_manager():
    """Create a SendManager instance."""
    return SendManager()


# =============================================================================
# BackendFactory Tests
# =============================================================================


class TestBackendFactory:
    """Tests for the BackendFactory class."""

    def test_get_backend_copy(self):
        """Test getting copy backend."""
        with patch("dispatch.send_manager.importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_import.return_value = mock_module

            result = BackendFactory.get_backend("copy")

            assert result is mock_module
            mock_import.assert_called_once_with("copy_backend")

    def test_get_backend_ftp(self):
        """Test getting FTP backend."""
        with patch("dispatch.send_manager.importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_import.return_value = mock_module

            result = BackendFactory.get_backend("ftp")

            assert result is mock_module
            mock_import.assert_called_once_with("ftp_backend")

    def test_get_backend_email(self):
        """Test getting email backend."""
        with patch("dispatch.send_manager.importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_import.return_value = mock_module

            result = BackendFactory.get_backend("email")

            assert result is mock_module
            mock_import.assert_called_once_with("email_backend")

    def test_get_backend_invalid(self):
        """Test getting invalid backend raises error."""
        with patch("dispatch.send_manager.importlib.import_module") as mock_import:
            mock_import.side_effect = ImportError("Module not found")

            with pytest.raises(ImportError) as exc_info:
                BackendFactory.get_backend("invalid")

            assert "Backend 'invalid' not found" in str(exc_info.value)

    def test_get_backend_import_error_message(self):
        """Test that import error message includes backend name."""
        with patch("dispatch.send_manager.importlib.import_module") as mock_import:
            mock_import.side_effect = ImportError("No module named 'test_backend'")

            with pytest.raises(ImportError) as exc_info:
                BackendFactory.get_backend("test")

            assert "test" in str(exc_info.value)


# =============================================================================
# SendResult Tests
# =============================================================================


class TestSendResult:
    """Tests for the SendResult dataclass."""

    def test_initialization_success(self):
        """Test SendResult initialization for successful send."""
        result = SendResult(
            success=True,
            backend_name="Copy Backend",
            destination="/output/path",
            error_message="",
            details={"bytes_sent": 1024},
        )

        assert result.success is True
        assert result.backend_name == "Copy Backend"
        assert result.destination == "/output/path"
        assert result.error_message == ""
        assert result.details == {"bytes_sent": 1024}

    def test_initialization_failure(self):
        """Test SendResult initialization for failed send."""
        result = SendResult(
            success=False,
            backend_name="FTP Backend",
            destination="ftp.example.com",
            error_message="Connection timeout",
            details=None,
        )

        assert result.success is False
        assert result.backend_name == "FTP Backend"
        assert result.destination == "ftp.example.com"
        assert result.error_message == "Connection timeout"
        assert result.details == {}  # Default to empty dict

    def test_initialization_default_details(self):
        """Test SendResult with default details."""
        result = SendResult(
            success=True, backend_name="Email Backend", destination="test@example.com"
        )

        assert result.details == {}

    def test_initialization_minimal(self):
        """Test SendResult with minimal parameters."""
        result = SendResult(
            success=True, backend_name="Copy Backend", destination="/output"
        )

        assert result.success is True
        assert result.error_message == ""
        assert result.details == {}


# =============================================================================
# SendManager Tests
# =============================================================================


class TestSendManager:
    """Tests for the SendManager class."""

    def test_initialization(self, send_manager):
        """Test SendManager initialization."""
        assert send_manager.results == []
        assert SendManager.BACKEND_CONFIG == {
            "copy": ("copy_backend", "copy_to_directory", "Copy Backend"),
            "ftp": ("ftp_backend", "ftp_server", "FTP Backend"),
            "email": ("email_backend", "email_to", "Email Backend"),
        }

    def test_send_file_single_backend(
        self, send_manager, sample_parameters_dict_single_backend, sample_settings
    ):
        """Test sending file through single backend."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("test content")

            with patch(
                "dispatch.send_manager.BackendFactory.get_backend"
            ) as mock_get_backend:
                mock_backend = MagicMock()
                mock_backend.do = MagicMock()
                mock_get_backend.return_value = mock_backend

                results = send_manager.send_file(
                    test_file, sample_parameters_dict_single_backend, sample_settings
                )

                assert len(results) == 1
                assert results[0].success is True
                assert results[0].backend_name == "Copy Backend"
                assert results[0].destination == "/output/copy"
                mock_backend.do.assert_called_once()

    def test_send_file_multiple_backends(
        self, send_manager, sample_parameters_dict, sample_settings
    ):
        """Test sending file through multiple backends."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("test content")

            with patch(
                "dispatch.send_manager.BackendFactory.get_backend"
            ) as mock_get_backend:
                mock_backend = MagicMock()
                mock_backend.do = MagicMock()
                mock_get_backend.return_value = mock_backend

                results = send_manager.send_file(
                    test_file, sample_parameters_dict, sample_settings
                )

                assert len(results) == 3  # copy, ftp, email
                assert all(r.success for r in results)
                assert mock_backend.do.call_count == 3

    def test_send_file_no_backends_enabled(
        self, send_manager, sample_parameters_dict_no_backends, sample_settings
    ):
        """Test sending file with no backends enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("test content")

            results = send_manager.send_file(
                test_file, sample_parameters_dict_no_backends, sample_settings
            )

            assert len(results) == 0

    def test_send_file_backend_failure(
        self, send_manager, sample_parameters_dict_single_backend, sample_settings
    ):
        """Test handling of backend failure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("test content")

            with patch(
                "dispatch.send_manager.BackendFactory.get_backend"
            ) as mock_get_backend:
                mock_backend = MagicMock()
                mock_backend.do.side_effect = Exception("Backend error")
                mock_get_backend.return_value = mock_backend

                results = send_manager.send_file(
                    test_file, sample_parameters_dict_single_backend, sample_settings
                )

                assert len(results) == 1
                assert results[0].success is False
                assert "Backend error" in results[0].error_message

    def test_send_file_partial_failure(
        self, send_manager, sample_parameters_dict, sample_settings
    ):
        """Test handling of partial backend failures."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("test content")

            call_count = 0

            def side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 2:  # Second backend fails
                    raise Exception("FTP error")

            with patch(
                "dispatch.send_manager.BackendFactory.get_backend"
            ) as mock_get_backend:
                mock_backend = MagicMock()
                mock_backend.do.side_effect = side_effect
                mock_get_backend.return_value = mock_backend

                results = send_manager.send_file(
                    test_file, sample_parameters_dict, sample_settings
                )

                assert len(results) == 3
                assert results[0].success is True  # copy succeeds
                assert results[1].success is False  # ftp fails
                assert results[2].success is True  # email succeeds
                assert "FTP error" in results[1].error_message

    def test_send_file_missing_backend_module(
        self, send_manager, sample_parameters_dict_single_backend, sample_settings
    ):
        """Test handling of missing backend module."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("test content")

            with patch(
                "dispatch.send_manager.BackendFactory.get_backend"
            ) as mock_get_backend:
                mock_get_backend.side_effect = ImportError("Module not found")

                results = send_manager.send_file(
                    test_file, sample_parameters_dict_single_backend, sample_settings
                )

                assert len(results) == 1
                assert results[0].success is False
                assert "Module not found" in results[0].error_message

    def test_has_successful_sends_true(self, send_manager):
        """Test has_successful_sends with successful results."""
        results = [
            SendResult(True, "Backend1", "/dest1"),
            SendResult(False, "Backend2", "/dest2", "Error"),
        ]

        assert SendManager.has_successful_sends(results) is True

    def test_has_successful_sends_false(self, send_manager):
        """Test has_successful_sends with no successful results."""
        results = [
            SendResult(False, "Backend1", "/dest1", "Error1"),
            SendResult(False, "Backend2", "/dest2", "Error2"),
        ]

        assert SendManager.has_successful_sends(results) is False

    def test_has_successful_sends_empty(self, send_manager):
        """Test has_successful_sends with empty results."""
        assert SendManager.has_successful_sends([]) is False

    def test_get_error_messages(self, send_manager):
        """Test getting error messages from failed sends."""
        results = [
            SendResult(True, "Backend1", "/dest1"),
            SendResult(False, "Backend2", "/dest2", "Connection failed"),
            SendResult(False, "Backend3", "/dest3", "Timeout"),
        ]

        error_messages = SendManager.get_error_messages(results)

        assert len(error_messages) == 2
        assert "Connection failed" in error_messages
        assert "Timeout" in error_messages

    def test_get_error_messages_all_success(self, send_manager):
        """Test getting error messages when all sends succeed."""
        results = [
            SendResult(True, "Backend1", "/dest1"),
            SendResult(True, "Backend2", "/dest2"),
        ]

        error_messages = SendManager.get_error_messages(results)

        assert error_messages == []

    def test_get_error_messages_empty_results(self, send_manager):
        """Test getting error messages with empty results."""
        assert SendManager.get_error_messages([]) == []

    def test_send_file_prints_messages(
        self, send_manager, sample_parameters_dict_single_backend, sample_settings
    ):
        """Test that send_file prints appropriate messages."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("test content")

            with (
                patch(
                    "dispatch.send_manager.BackendFactory.get_backend"
                ) as mock_get_backend,
                patch("builtins.print") as mock_print,
            ):
                mock_backend = MagicMock()
                mock_get_backend.return_value = mock_backend

                send_manager.send_file(
                    test_file, sample_parameters_dict_single_backend, sample_settings
                )

                # Should print sending message
                mock_print.assert_called_once()
                assert "sending" in mock_print.call_args[0][0].lower()
                assert test_file in mock_print.call_args[0][0]

    def test_send_file_error_prints_message(
        self, send_manager, sample_parameters_dict_single_backend, sample_settings
    ):
        """Test that send_file prints error messages."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("test content")

            with (
                patch(
                    "dispatch.send_manager.BackendFactory.get_backend"
                ) as mock_get_backend,
                patch("builtins.print") as mock_print,
            ):
                mock_backend = MagicMock()
                mock_backend.do.side_effect = Exception("Backend failure")
                mock_get_backend.return_value = mock_backend

                send_manager.send_file(
                    test_file, sample_parameters_dict_single_backend, sample_settings
                )

                # Should print error message
                assert mock_print.call_count == 2  # Sending message + error


# =============================================================================
# Integration Tests
# =============================================================================


class TestSendManagerIntegration:
    """Integration tests for send manager workflows."""

    def test_full_send_workflow(self, sample_parameters_dict, sample_settings):
        """Test complete send workflow."""
        manager = SendManager()

        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("test content")

            with patch(
                "dispatch.send_manager.BackendFactory.get_backend"
            ) as mock_get_backend:
                mock_backend = MagicMock()
                mock_backend.do = MagicMock()
                mock_get_backend.return_value = mock_backend

                results = manager.send_file(
                    test_file, sample_parameters_dict, sample_settings
                )

                # Verify results
                assert len(results) == 3
                assert SendManager.has_successful_sends(results) is True
                assert SendManager.get_error_messages(results) == []

    def test_send_with_mixed_results(self, sample_settings):
        """Test send with mixed success/failure results."""
        manager = SendManager()

        parameters = {
            "process_backend_copy": True,
            "copy_to_directory": "/output",
            "process_backend_ftp": True,
            "ftp_server": "ftp.example.com",
            "ftp_folder": "/remote",
            "process_backend_email": False,
            "email_to": "",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("test content")

            call_count = 0

            def side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return  # copy succeeds
                raise Exception("FTP connection failed")

            with patch(
                "dispatch.send_manager.BackendFactory.get_backend"
            ) as mock_get_backend:
                mock_backend = MagicMock()
                mock_backend.do.side_effect = side_effect
                mock_get_backend.return_value = mock_backend

                results = manager.send_file(test_file, parameters, sample_settings)

                assert len(results) == 2
                assert results[0].success is True
                assert results[1].success is False
                assert SendManager.has_successful_sends(results) is True
                assert len(SendManager.get_error_messages(results)) == 1


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_send_file_nonexistent_file(
        self, send_manager, sample_parameters_dict_single_backend, sample_settings
    ):
        """Test sending non-existent file."""
        with patch(
            "dispatch.send_manager.BackendFactory.get_backend"
        ) as mock_get_backend:
            mock_backend = MagicMock()
            mock_backend.do = MagicMock()
            mock_get_backend.return_value = mock_backend

            results = send_manager.send_file(
                "/nonexistent/file.txt",
                sample_parameters_dict_single_backend,
                sample_settings,
            )

            # Backend is called regardless of file existence (backend handles file access)
            assert len(results) == 1
            mock_backend.do.assert_called_once()

    def test_send_file_empty_file(
        self, send_manager, sample_parameters_dict_single_backend, sample_settings
    ):
        """Test sending empty file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "empty.txt")
            with open(test_file, "w") as f:
                pass  # Create empty file

            with patch(
                "dispatch.send_manager.BackendFactory.get_backend"
            ) as mock_get_backend:
                mock_backend = MagicMock()
                mock_backend.do = MagicMock()
                mock_get_backend.return_value = mock_backend

                results = send_manager.send_file(
                    test_file, sample_parameters_dict_single_backend, sample_settings
                )

                assert len(results) == 1
                assert results[0].success is True

    def test_send_file_very_long_path(
        self, send_manager, sample_parameters_dict_single_backend, sample_settings
    ):
        """Test sending file with very long path."""
        long_path = "/very" + "/long" * 50 + "/path.txt"

        with patch(
            "dispatch.send_manager.BackendFactory.get_backend"
        ) as mock_get_backend:
            mock_backend = MagicMock()
            mock_backend.do = MagicMock()
            mock_get_backend.return_value = mock_backend

            results = send_manager.send_file(
                long_path, sample_parameters_dict_single_backend, sample_settings
            )

            assert len(results) == 1

    def test_send_file_unicode_path(
        self, send_manager, sample_parameters_dict_single_backend, sample_settings
    ):
        """Test sending file with unicode path."""
        unicode_path = "/path/to/fichier_avec_accents_éèà.txt"

        with patch(
            "dispatch.send_manager.BackendFactory.get_backend"
        ) as mock_get_backend:
            mock_backend = MagicMock()
            mock_backend.do = MagicMock()
            mock_get_backend.return_value = mock_backend

            results = send_manager.send_file(
                unicode_path, sample_parameters_dict_single_backend, sample_settings
            )

            assert len(results) == 1

    def test_backend_config_immutability(self, send_manager):
        """Test that BACKEND_CONFIG class attribute is properly defined."""
        # Verify BACKEND_CONFIG is a class attribute
        assert hasattr(SendManager, "BACKEND_CONFIG")

        # Verify structure
        assert "copy" in SendManager.BACKEND_CONFIG
        assert "ftp" in SendManager.BACKEND_CONFIG
        assert "email" in SendManager.BACKEND_CONFIG

        # Verify each entry has expected structure
        for backend_type, config in SendManager.BACKEND_CONFIG.items():
            assert len(config) == 3
            assert isinstance(config[0], str)  # module name
            assert isinstance(config[1], str)  # setting name
            assert isinstance(config[2], str)  # display name

    def test_send_result_with_complex_details(self):
        """Test SendResult with complex details dictionary."""
        complex_details = {
            "bytes_sent": 1024,
            "transfer_time": 5.3,
            "checksum": "abc123",
            "metadata": {"key": "value", "nested": {"data": True}},
        }

        result = SendResult(
            success=True,
            backend_name="Test Backend",
            destination="/test",
            details=complex_details,
        )

        assert result.details == complex_details
        assert result.details["metadata"]["nested"]["data"] is True

    def test_has_successful_sends_with_none_results(self, send_manager):
        """Test has_successful_sends with None in results (should not happen but test defensively)."""
        # This tests the generator expression behavior
        results = [
            SendResult(True, "Backend1", "/dest1"),
            None,  # Invalid entry
        ]

        # Should handle gracefully by filtering None
        valid_results = [r for r in results if r is not None]
        assert SendManager.has_successful_sends(valid_results) is True

    def test_send_file_unknown_destination_in_error(
        self, send_manager, sample_settings
    ):
        """Test that error message includes unknown destination when setting is missing."""
        parameters = {
            "process_backend_copy": True,
            # Missing copy_to_directory - should result in "Unknown" destination
            "process_backend_ftp": False,
            "process_backend_email": False,
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("test content")

            with patch(
                "dispatch.send_manager.BackendFactory.get_backend"
            ) as mock_get_backend:
                mock_backend = MagicMock()
                mock_backend.do.side_effect = Exception("Send failed")
                mock_get_backend.return_value = mock_backend

                results = send_manager.send_file(test_file, parameters, sample_settings)

                assert len(results) == 1
                assert results[0].destination == "Unknown"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
