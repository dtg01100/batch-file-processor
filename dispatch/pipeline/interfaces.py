"""Pipeline step protocols for the dispatch processing pipeline.

This module defines Protocol classes that formalize the interface for
pipeline processing steps, enabling consistent implementations and
easy testing through dependency injection.

The pipeline step interface follows a simple contract:
1. All steps receive input (file path or previous output)
2. Steps return (success, output_path, errors)
3. Steps are stateless and can be composed
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


class ErrorRecordingMixin:
    """Mixin providing consistent error recording for pipeline steps.

    Pipeline steps that need to record errors to an ErrorHandler should
    include this mixin to avoid duplicating the record_error pattern.
    Subclasses must define ``_error_handler`` as an optional attribute
    accepting an error handler instance.
    """

    def _record_error(
        self,
        filename: str,
        error_msg: str,
        *,
        source: str = "PipelineStep",
        error_source: str = "Pipeline",
        error_type: type[Exception] = Exception,
    ) -> None:
        """Record a single error to the error handler.

        Args:
            filename: Filename being processed
            error_msg: Error message
            source: Context source identifier
            error_source: Error source identifier
            error_type: Exception type to wrap the message in

        """
        handler = getattr(self, "_error_handler", None)
        if handler is None:
            return

        handler.record_error(
            folder="",
            filename=filename,
            error=error_type(error_msg),
            context={"source": source},
            error_source=error_source,
        )


@runtime_checkable
class PipelineStep(Protocol):
    """Protocol for pipeline processing steps.

    A pipeline step represents a single transformation or validation
    stage in the file processing pipeline. Each step:
    - Receives an input (typically a file path)
    - Performs a single responsibility
    - Returns output path and any errors

    Implementations should be stateless to allow:
    - Easy testing
    - Parallel execution
    - Step reuse across pipelines
    """

    def execute(
        self,
        input_path: str,
        context: dict[str, Any],
    ) -> tuple[bool, str, list[str]]:
        """Execute the pipeline step.

        Args:
            input_path: Path to the input file or previous stage output
            context: Context dictionary with additional parameters

        Returns:
            Tuple of (success, output_path, errors)
        """
        ...
