"""Tests for dispatch/pipeline/tweaker.py - EDITweakerStep and TweakerResult classes."""

import pytest
from unittest.mock import MagicMock, Mock
from dispatch.pipeline.tweaker import (
    TweakerResult,
    MockTweaker,
    EDITweakerStep,
    TweakerInterface,
)


class TestTweakerResult:
    """Tests for TweakerResult dataclass."""

    def test_default_values(self):
        """Test TweakerResult with default values."""
        result = TweakerResult()

        assert result.output_path == ""
        assert result.success is False
        assert result.was_tweaked is False
        assert result.errors == []

    def test_custom_values(self):
        """Test TweakerResult with custom values."""
        errors = ["error1", "error2"]
        result = TweakerResult(
            output_path="/path/to/output.edi",
            success=True,
            was_tweaked=True,
            errors=errors
        )

        assert result.output_path == "/path/to/output.edi"
        assert result.success is True
        assert result.was_tweaked is True
        assert result.errors == ["error1", "error2"]


class TestMockTweaker:
    """Tests for MockTweaker class."""

    def test_initialization_with_default_result(self):
        """Test initialization with default result."""
        mock = MockTweaker()

        assert mock.call_count == 0
        assert mock.last_input_path is None
        assert mock.last_output_dir is None
        assert mock.last_params is None
        assert mock.last_settings is None
        assert mock.last_upc_dict is None
        assert mock._result.output_path == ""
        assert mock._result.success is True
        assert mock._result.was_tweaked is True

    def test_initialization_with_custom_result(self):
        """Test initialization with custom result."""
        custom_result = TweakerResult(
            output_path="/custom/output.edi",
            success=False,
            was_tweaked=False,
            errors=["custom error"]
        )
        mock = MockTweaker(result=custom_result)

        assert mock._result is custom_result
        assert mock._result.output_path == "/custom/output.edi"
        assert mock._result.success is False

    def test_initialization_with_individual_params(self):
        """Test initialization with individual parameters."""
        mock = MockTweaker(
            output_path="/test/output.edi",
            success=False,
            was_tweaked=False,
            errors=["test error"]
        )

        assert mock._result.output_path == "/test/output.edi"
        assert mock._result.success is False
        assert mock._result.was_tweaked is False
        assert mock._result.errors == ["test error"]

    def test_call_tracking(self):
        """Test call tracking in MockTweaker."""
        mock = MockTweaker()

        params = {"tweak_edi": True}
        settings = {"setting1": "value1"}
        upc_dict = {"upc1": "product1"}

        result = mock.tweak(
            "/input/file.edi",
            "/output/dir",
            params,
            settings,
            upc_dict
        )

        assert mock.call_count == 1
        assert mock.last_input_path == "/input/file.edi"
        assert mock.last_output_dir == "/output/dir"
        assert mock.last_params == params
        assert mock.last_settings == settings
        assert mock.last_upc_dict == upc_dict

    def test_reset(self):
        """Test reset method clears call tracking."""
        mock = MockTweaker()

        mock.tweak("/input.edi", "/output", {}, {}, {})
        assert mock.call_count == 1

        mock.reset()

        assert mock.call_count == 0
        assert mock.last_input_path is None
        assert mock.last_output_dir is None
        assert mock.last_params is None
        assert mock.last_settings is None
        assert mock.last_upc_dict is None

    def test_set_result(self):
        """Test set_result method updates the result."""
        mock = MockTweaker()
        assert mock._result.success is True

        new_result = TweakerResult(
            output_path="/new/output.edi",
            success=False,
            was_tweaked=False,
            errors=["new error"]
        )
        mock.set_result(new_result)

        assert mock._result is new_result
        assert mock._result.success is False


class TestEDITweakerStep:
    """Tests for EDITweakerStep class."""

    def test_initialization_with_defaults(self):
        """Test initialization with default values."""
        step = EDITweakerStep()

        assert step._tweak_function is not None
        assert step._error_handler is None
        assert step._file_system is None

    def test_initialization_with_injected_dependencies(self):
        """Test initialization with injected dependencies."""
        mock_tweak_func = Mock()
        mock_error_handler = Mock()
        mock_file_system = Mock()

        step = EDITweakerStep(
            tweak_function=mock_tweak_func,
            error_handler=mock_error_handler,
            file_system=mock_file_system
        )

        assert step._tweak_function is mock_tweak_func
        assert step._error_handler is mock_error_handler
        assert step._file_system is mock_file_system

    def test_tweak_with_tweak_edi_false(self):
        """Test tweak() with tweak_edi=False returns input path without tweaking."""
        mock_tweak_func = Mock()
        step = EDITweakerStep(tweak_function=mock_tweak_func)

        params = {"tweak_edi": False}
        result = step.tweak(
            "/input/file.edi",
            "/output/dir",
            params,
            {},
            {}
        )

        assert result.output_path == "/input/file.edi"
        assert result.success is True
        assert result.was_tweaked is False
        assert result.errors == []
        mock_tweak_func.assert_not_called()

    def test_tweak_with_tweak_edi_true(self):
        """Test tweak() with tweak_edi=True calls tweak function."""
        mock_tweak_func = Mock(return_value="/output/dir/file.edi")
        step = EDITweakerStep(tweak_function=mock_tweak_func)

        params = {"tweak_edi": True}
        result = step.tweak(
            "/input/file.edi",
            "/output/dir",
            params,
            {"setting": "value"},
            {"upc": "product"}
        )

        assert result.output_path == "/output/dir/file.edi"
        assert result.success is True
        assert result.was_tweaked is True

        mock_tweak_func.assert_called_once_with(
            "/input/file.edi",
            "/output/dir/file.edi",
            {"setting": "value"},
            params,
            {"upc": "product"}
        )

    def test_tweak_handles_exception_from_tweak_function(self):
        """Test tweak() handles exception from tweak function."""
        mock_tweak_func = Mock(side_effect=Exception("Tweak failed"))
        mock_error_handler = Mock()
        step = EDITweakerStep(
            tweak_function=mock_tweak_func,
            error_handler=mock_error_handler
        )

        params = {"tweak_edi": True}
        result = step.tweak(
            "/input/file.edi",
            "/output/dir",
            params,
            {},
            {}
        )

        assert result.output_path == "/input/file.edi"
        assert result.success is False
        assert result.was_tweaked is False
        assert "Tweak failed" in result.errors[0]

        mock_error_handler.record_error.assert_called_once()

    def test_tweak_with_tweak_edi_string_true(self):
        """Test tweak() with tweak_edi as string 'True'."""
        mock_tweak_func = Mock(return_value="/output/dir/file.edi")
        step = EDITweakerStep(tweak_function=mock_tweak_func)

        params = {"tweak_edi": "True"}
        result = step.tweak(
            "/input/file.edi",
            "/output/dir",
            params,
            {},
            {}
        )

        assert result.was_tweaked is True
        mock_tweak_func.assert_called_once()

    def test_tweak_with_tweak_edi_string_false(self):
        """Test tweak() with tweak_edi as string 'False'.

        Note: The string "False" is truthy in Python, so the tweak function
        is actually called. This is different from converter which explicitly
        checks for 'True'. This test documents the actual behavior.
        """
        mock_tweak_func = Mock(return_value="/output/dir/file.edi")
        step = EDITweakerStep(tweak_function=mock_tweak_func)

        params = {"tweak_edi": "False"}
        result = step.tweak(
            "/input/file.edi",
            "/output/dir",
            params,
            {},
            {}
        )

        assert result.was_tweaked is True
        mock_tweak_func.assert_called_once()

    def test_tweak_with_neither_tweak_edi_nor_process_edi_set(self):
        """Test tweak() with neither tweak_edi nor process_edi set."""
        mock_tweak_func = Mock()
        step = EDITweakerStep(tweak_function=mock_tweak_func)

        params = {}
        result = step.tweak(
            "/input/file.edi",
            "/output/dir",
            params,
            {},
            {}
        )

        assert result.was_tweaked is False
        assert result.output_path == "/input/file.edi"
        mock_tweak_func.assert_not_called()

    def test_tweak_with_process_edi_true_not_trigger(self):
        """Test tweak() with process_edi='True' does not trigger tweaking.

        Note: The tweaker only checks tweak_edi, not process_edi.
        This test verifies the current behavior.
        """
        mock_tweak_func = Mock()
        step = EDITweakerStep(tweak_function=mock_tweak_func)

        params = {"process_edi": "True"}
        result = step.tweak(
            "/input/file.edi",
            "/output/dir",
            params,
            {},
            {}
        )

        assert result.was_tweaked is False
        assert result.output_path == "/input/file.edi"
        mock_tweak_func.assert_not_called()

    def test_error_recording_to_error_handler(self):
        """Test error recording to error handler."""
        mock_error_handler = Mock()
        mock_file_system = Mock()
        mock_file_system.dir_exists.return_value = False
        mock_file_system.makedirs.side_effect = Exception("Cannot create dir")

        step = EDITweakerStep(
            error_handler=mock_error_handler,
            file_system=mock_file_system
        )

        params = {"tweak_edi": True}
        result = step.tweak(
            "/input/file.edi",
            "/output/dir",
            params,
            {},
            {}
        )

        assert result.success is False
        assert "Failed to create output directory" in result.errors[0]

        mock_error_handler.record_error.assert_called_once()
        call_kwargs = mock_error_handler.record_error.call_args
        assert call_kwargs[1]["filename"] == "/input/file.edi"
        assert call_kwargs[1]["context"]["source"] == "EDITweakerStep"


class TestProtocolTests:
    """Protocol tests for TweakerInterface."""

    def test_mock_tweaker_satisfies_tweaker_interface(self):
        """Test MockTweaker satisfies TweakerInterface."""
        mock = MockTweaker()

        assert isinstance(mock, TweakerInterface)

    def test_edi_tweaker_step_satisfies_tweaker_interface(self):
        """Test EDITweakerStep satisfies TweakerInterface."""
        step = EDITweakerStep()

        assert isinstance(step, TweakerInterface)


class TestIntegrationTests:
    """Integration tests for EDITweakerStep."""

    def test_full_tweak_flow_with_mock_function(self):
        """Test full tweak flow with mock function."""
        def mock_tweak(edi_process, output_filename, settings_dict, parameters_dict, upc_dict):
            return output_filename

        step = EDITweakerStep(tweak_function=mock_tweak)

        params = {"tweak_edi": True}
        result = step.tweak(
            "/input/test.edi",
            "/output",
            params,
            {"app_title": "Test App"},
            {"123456789012": "Test Product"}
        )

        assert result.success is True
        assert result.was_tweaked is True
        assert result.output_path == "/output/test.edi"

    def test_output_directory_handling(self):
        """Test output directory handling with file system."""
        mock_file_system = Mock()
        mock_file_system.dir_exists.return_value = True

        mock_tweak_func = Mock(return_value="/output/tweaked.edi")
        step = EDITweakerStep(
            tweak_function=mock_tweak_func,
            file_system=mock_file_system
        )

        params = {"tweak_edi": True}
        result = step.tweak(
            "/input/file.edi",
            "/output/dir",
            params,
            {},
            {}
        )

        mock_file_system.dir_exists.assert_called_with("/output/dir")
        mock_tweak_func.assert_called_once()

    def test_output_directory_creation(self):
        """Test output directory is created when it doesn't exist."""
        mock_file_system = Mock()
        mock_file_system.dir_exists.return_value = False
        mock_file_system.makedirs.return_value = None

        mock_tweak_func = Mock(return_value="/output/dir/file.edi")
        step = EDITweakerStep(
            tweak_function=mock_tweak_func,
            file_system=mock_file_system
        )

        params = {"tweak_edi": True}
        result = step.tweak(
            "/input/file.edi",
            "/output/dir",
            params,
            {},
            {}
        )

        mock_file_system.makedirs.assert_called_once_with("/output/dir")
        assert result.success is True
