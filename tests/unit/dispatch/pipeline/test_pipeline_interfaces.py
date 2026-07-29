"""Tests for dispatch.pipeline.interfaces module."""

from __future__ import annotations

from dispatch.pipeline.interfaces import ErrorRecordingMixin, PipelineStep


class TestPipelineStepProtocol:
    """Tests to verify PipelineStep protocol compliance."""

    def test_pipeline_step_can_be_checked(self):
        """Test that PipelineStep protocol can be used with isinstance."""

        class ValidStep:
            def execute(
                self, input_path: str, context: dict
            ) -> tuple[bool, str, list[str]]:
                return True, input_path, []

        step = ValidStep()
        assert isinstance(step, PipelineStep)

    def test_protocol_requires_execute_method(self):
        """Test that objects without execute method are not PipelineStep."""

        class InvalidStep:
            pass

        step = InvalidStep()
        assert not isinstance(step, PipelineStep)


class TestErrorRecordingMixin:
    """Tests for ErrorRecordingMixin.

    Regression tests for the end-to-end mutation run (2026-07-13).
    The mixin had 4 surviving mutations on real production code that
    the existing test suite didn't exercise.
    """

    def test_record_error_no_handler_silently_returns(self):
        """L47: ``if handler is None: return`` — the mixin must
        silently return when no error handler is set. With the
        mutation to ``if not (handler is None)``, the mixin would
        attempt to call ``record_error`` on None and raise
        AttributeError.
        """

        class HasMixinOnly(ErrorRecordingMixin):
            pass

        m = HasMixinOnly()
        # No _error_handler attribute set. Must not raise.
        m._record_error(filename="file.edi", error_msg="test error")
        # If we get here without exception, the test passes.

    def test_record_error_with_handler_invokes_handler(self):
        """L48: ``return`` from mixin is replaced with the
        record_error delegation. The mixin must invoke
        ``handler.record_error`` when a handler is set.
        """
        from unittest.mock import MagicMock

        class HasMixinAndHandler(ErrorRecordingMixin):
            _error_handler = None

        m = HasMixinAndHandler()
        handler = MagicMock()
        m._error_handler = handler

        m._record_error(filename="file.edi", error_msg="test error")

        handler.record_error.assert_called_once()
        call_kwargs = handler.record_error.call_args.kwargs
        assert call_kwargs.get("filename") == "file.edi"
        # error_msg is wrapped into an Exception in the call
        assert isinstance(call_kwargs.get("error"), Exception)
