"""Tests for dispatch.pipeline.interfaces module."""

from __future__ import annotations

from dispatch.pipeline.interfaces import PipelineStep


class TestPipelineStepProtocol:
    """Tests to verify PipelineStep protocol compliance."""

    def test_pipeline_step_can_be_checked(self):
        """Test that PipelineStep protocol can be used with isinstance."""
        class ValidStep:
            def execute(self, input_path: str, context: dict) -> tuple[bool, str, list[str]]:
                return True, input_path, []

        step = ValidStep()
        assert isinstance(step, PipelineStep)

    def test_protocol_requires_execute_method(self):
        """Test that objects without execute method are not PipelineStep."""

        class InvalidStep:
            pass

        step = InvalidStep()
        assert not isinstance(step, PipelineStep)
