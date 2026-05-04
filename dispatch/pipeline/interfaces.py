"""Pipeline step protocols for the dispatch processing pipeline.

This module defines Protocol classes that formalize the interface for
pipeline processing steps, enabling consistent implementations and
easy testing through dependency injection.

The pipeline step interface follows a simple contract:
1. All steps receive input (file path or previous output)
2. Steps return (success, output_path, errors)
3. Steps are stateless and can be composed

Example:
    >>> class MyValidator:
    ...     def validate(self, file_path: str) -> tuple[bool, list[str]]:
    ...         return True, []
    >>> # Wrap legacy validator as pipeline step
    >>> wrapped = LegacyValidatorAdapter(MyValidator())
    >>> success, output, errors = wrapped.execute("/path/to/file", {})
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


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

    Example:
        >>> class MyStep:
        ... def execute(
        ...     self, input_path: str, context: dict
        ... ) -> tuple[bool, str, list]:
        ...         return True, input_path, []
    """

    def execute(
        self,
        input_path: str,
        context: dict[str, Any],
    ) -> tuple[bool, str, list[str]]:
        """Execute the pipeline step.

        Args:
            input_path: Path to the input file or previous stage output
            context: Context dictionary with additional parameters:
                - folder: Folder configuration dict
                - settings: Application settings dict
                - upc_dict: UPC lookup dictionary
                - effective_folder: Effective folder configuration
                - Other step-specific parameters

        Returns:
            Tuple of (success, output_path, errors) where:
                - success: True if step completed successfully
                - output_path: Path to output (may be same as input for some steps)
                - errors: List of error messages (empty if successful)
        """
        ...


class LegacyValidatorAdapter:
    """Adapter to wrap legacy validators with .validate() interface.

    This adapter allows legacy validators that expose a .validate() method
    to be used uniformly by the pipeline, which expects .execute() method.

    The adapter translates:
    - .validate(file_path) -> tuple[bool, list[str]]
    Into:
    - .execute(input_path, context) -> tuple[bool, str, list[str]]

    Attributes:
        _validator: The wrapped validator with .validate() method

    Example:
        >>> legacy = SomeLegacyValidator()
        >>> adapter = LegacyValidatorAdapter(legacy)
        >>> success, path, errors = adapter.execute("/file.txt", {})
    """

    def __init__(self, validator: Any) -> None:
        """Initialize the adapter with a legacy validator.

        Args:
            validator: A validator with .validate(file_path) -> tuple[bool, list[str]]
        """
        self._validator = validator

    def execute(
        self,
        input_path: str,
        context: dict[str, Any],
    ) -> tuple[bool, str, list[str]]:
        """Execute validation via the legacy .validate() method.

        Args:
            input_path: Path to the file to validate
            context: Context (unused; required for PipelineStep protocol compatibility)

        Returns:
            Tuple of (success, input_path, errors) where errors come
            from the legacy validator
        """
        success, errors = self._validator.validate(input_path)
        return success, input_path, errors


class ValidatorStep:
    """Wrapper to make any validator compatible with PipelineStep interface.

    This class provides a clean way to wrap validators that return
    (is_valid, errors) tuples into the pipeline step format that
    returns (success, output_path, errors).

    Example:
        >>> validator = EDIValidator()
        >>> step = ValidatorStep(validator)
        >>> success, path, errors = step.execute("/file.edi", {})
    """

    def __init__(self, validator: Any) -> None:
        """Initialize with a validator.

        Args:
            validator: Validator with .validate(path) returning (bool, list[str])
        """
        self._validator = validator

    def execute(
        self,
        input_path: str,
        context: dict[str, Any],
    ) -> tuple[bool, str, list[str]]:
        """Execute validation step.

        Args:
            input_path: Path to file to validate
            context: Additional context (unused; required for PipelineStep protocol)

        Returns:
            Tuple of (success, input_path, errors)
        """
        is_valid, errors = self._validator.validate(input_path)
        return is_valid, input_path, errors


class NoOpStep:
    """A no-operation pipeline step that passes input through unchanged.

    This step is useful as a placeholder or default when a pipeline
    step is optional.

    Example:
        >>> step = NoOpStep()
        >>> success, path, errors = step.execute("/input.txt", {})
        >>> assert path == "/input.txt"
        >>> assert success is True
        >>> assert errors == []
    """

    def execute(
        self,
        input_path: str,
        context: dict[str, Any],
    ) -> tuple[bool, str, list[str]]:
        """Execute no-op step.

        Args:
            input_path: Path to pass through
            context: Additional context (unused; required for PipelineStep protocol)

        Returns:
            Tuple of (True, input_path, [])
        """
        return True, input_path, []


def wrap_as_pipeline_step(step: Any) -> PipelineStep:
    """Wrap an object as a PipelineStep if it isn't already.

    This function provides a unified way to get a pipeline-compatible
    step from either:
    - An object already implementing PipelineStep
    - A legacy validator with .validate() method
    - None (returns NoOpStep)

    Args:
        step: Either a PipelineStep, legacy validator, or None

    Returns:
        A PipelineStep implementation

    Example:
        >>> # With existing pipeline step
        >>> step1 = wrap_as_pipeline_step(MyPipelineStep())
        >>> # With legacy validator
        >>> step2 = wrap_as_pipeline_step(EDIValidator())
        >>> # With None
        >>> step3 = wrap_as_pipeline_step(None)
    """
    if step is None:
        return NoOpStep()

    if isinstance(step, PipelineStep):
        return step

    if hasattr(step, "validate") and callable(getattr(step, "validate")):
        return LegacyValidatorAdapter(step)

    if hasattr(step, "execute") and callable(getattr(step, "execute")):
        return step

    raise TypeError(
        f"Cannot wrap {type(step).__name__} as PipelineStep: "
        "must implement PipelineStep protocol or have .validate() or .execute() method"
    )
