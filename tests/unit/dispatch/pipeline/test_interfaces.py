"""Tests for dispatch.pipeline.interfaces module."""

from __future__ import annotations

import pytest

from dispatch.pipeline.interfaces import (
    LegacyValidatorAdapter,
    NoOpStep,
    PipelineStep,
    ValidatorStep,
    wrap_as_pipeline_step,
)


class MockValidator:
    """Mock validator for testing."""

    def __init__(self, is_valid: bool = True, errors: list[str] | None = None):
        self.is_valid = is_valid
        self.errors = errors or []

    def validate(self, file_path: str) -> tuple[bool, list[str]]:
        return self.is_valid, self.errors


class MockPipelineStep:
    """Mock pipeline step for testing."""

    def __init__(
        self,
        success: bool = True,
        output_path: str | None = None,
        errors: list[str] | None = None,
    ):
        self.success = success
        self.output_path = output_path or "/input"
        self.errors = errors or []

    def execute(self, input_path: str, context: dict) -> tuple[bool, str, list[str]]:
        return self.success, self.output_path, self.errors


class TestLegacyValidatorAdapter:
    """Tests for LegacyValidatorAdapter."""

    def test_execute_returns_tuple(self):
        """Test that execute returns expected tuple format."""
        validator = MockValidator(is_valid=True, errors=[])
        adapter = LegacyValidatorAdapter(validator)

        success, output_path, errors = adapter.execute("/test/file.txt", {})

        assert success is True
        assert output_path == "/test/file.txt"
        assert errors == []

    def test_execute_passes_through_errors(self):
        """Test that errors from legacy validator are passed through."""
        validator = MockValidator(is_valid=False, errors=["Invalid format"])
        adapter = LegacyValidatorAdapter(validator)

        success, _, errors = adapter.execute("/test/file.txt", {})

        assert success is False
        assert errors == ["Invalid format"]

    def test_execute_context_is_not_used(self):
        """Test that context parameter is accepted but not used."""
        validator = MockValidator(is_valid=True, errors=[])
        adapter = LegacyValidatorAdapter(validator)

        success, output_path, errors = adapter.execute(
            "/test/file.txt",
            {"folder": {}, "settings": {}},
        )

        assert success is True
        assert output_path == "/test/file.txt"


class TestValidatorStep:
    """Tests for ValidatorStep."""

    def test_execute_returns_tuple_format(self):
        """Test execute returns (success, path, errors) tuple."""
        validator = MockValidator(is_valid=True, errors=[])
        step = ValidatorStep(validator)

        result = step.execute("/input.edi", {})

        assert isinstance(result, tuple)
        assert len(result) == 3
        assert result[0] is True
        assert result[1] == "/input.edi"
        assert result[2] == []

    def test_execute_passes_validation_result(self):
        """Test that validation result is properly translated."""
        validator = MockValidator(is_valid=False, errors=["Missing UPC"])
        step = ValidatorStep(validator)

        success, _, errors = step.execute("/input.edi", {})

        assert success is False
        assert "Missing UPC" in errors


class TestNoOpStep:
    """Tests for NoOpStep."""

    def test_execute_returns_success_with_input_path(self):
        """Test no-op step passes input through unchanged."""
        step = NoOpStep()

        success, output_path, errors = step.execute("/input/file.txt", {})

        assert success is True
        assert output_path == "/input/file.txt"
        assert errors == []

    def test_execute_accepts_any_context(self):
        """Test no-op step accepts any context without error."""
        step = NoOpStep()

        success, _, _ = step.execute(
            "/file.txt",
            {"folder": {}, "settings": {}, "unknown_key": "value"},
        )

        assert success is True

    def test_noop_step_does_not_modify(self):
        """Test that no-op step doesn't modify anything."""
        step = NoOpStep()
        context = {"key": "value"}

        success, output, errors = step.execute("/path", context)

        assert success
        assert output == "/path"
        assert not errors


class TestWrapAsPipelineStep:
    """Tests for wrap_as_pipeline_step function."""

    def test_wrap_none_returns_noop(self):
        """Test wrapping None returns NoOpStep."""
        step = wrap_as_pipeline_step(None)

        assert isinstance(step, NoOpStep)

    def test_wrap_pipeline_step_returns_same(self):
        """Test wrapping a PipelineStep returns it unchanged."""
        original = MockPipelineStep()
        result = wrap_as_pipeline_step(original)

        assert result is original

    def test_wrap_legacy_validator_returns_adapter(self):
        """Test wrapping legacy validator returns adapter."""
        validator = MockValidator()
        result = wrap_as_pipeline_step(validator)

        assert isinstance(result, LegacyValidatorAdapter)

    def test_wrap_object_with_execute(self):
        """Test wrapping object with execute method."""

        class CustomStep:
            def execute(self, input_path: str, context: dict):
                return True, input_path, []

        obj = CustomStep()
        result = wrap_as_pipeline_step(obj)

        assert result is obj

    def test_wrap_invalid_raises_error(self):
        """Test wrapping invalid type raises TypeError."""
        with pytest.raises(TypeError):
            wrap_as_pipeline_step("not a step")

    def test_wrap_invalid_with_no_execute_raises(self):
        """Test wrapping object without proper interface raises error."""
        with pytest.raises(TypeError):
            wrap_as_pipeline_step(object())


class TestPipelineStepProtocol:
    """Tests to verify PipelineStep protocol compliance."""

    def test_noop_is_valid_pipeline_step(self):
        """Test NoOpStep satisfies PipelineStep protocol."""
        step: PipelineStep = NoOpStep()

        success, path, errors = step.execute("/test", {})

        assert success is True
        assert path == "/test"
        assert isinstance(errors, list)

    def test_mock_pipeline_step_is_valid(self):
        """Test MockPipelineStep satisfies protocol."""
        step: PipelineStep = MockPipelineStep()

        result = step.execute("/test", {})

        assert isinstance(result, tuple)
        assert len(result) == 3
