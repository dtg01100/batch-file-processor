"""EDI Tweaker types for the dispatch pipeline.

This module provides type definitions for EDI tweak operations.
The actual tweak functionality is provided by convert_to_tweaks.py.
"""

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class TweakerResult:
    """Result of EDI tweak operation.

    Attributes:
        output_path: Path to tweaked output file
        success: True if tweaking succeeded
        was_tweaked: True if tweaking was actually applied
        errors: List of error messages

    """

    output_path: str = ""
    success: bool = False
    was_tweaked: bool = False
    errors: list[str] = field(default_factory=list)


@runtime_checkable
class TweakerInterface(Protocol):
    """Protocol for tweaker step implementations."""

    def tweak(
        self,
        input_path: str,
        output_dir: str,
        params: dict,
        settings: dict,
        upc_dict: dict,
    ) -> TweakerResult:
        """Apply EDI tweaks to a file.

        Args:
            input_path: Path to the input EDI file
            output_dir: Directory for output file
            params: Folder parameters dictionary
            settings: Global settings dictionary
            upc_dict: UPC dictionary for lookups

        Returns:
            TweakerResult with tweak outcome

        """
        ...


@runtime_checkable
class TweakFunctionProtocol(Protocol):
    """Protocol for the edi_tweak function."""

    def __call__(
        self,
        edi_process: str,
        output_filename: str,
        settings_dict: dict,
        parameters_dict: dict,
        upc_dict: dict,
    ) -> str:
        """Apply EDI tweaks to a file.

        Args:
            edi_process: Path to input EDI file
            output_filename: Path to output file
            settings_dict: Dictionary containing database and app settings
            parameters_dict: Dictionary containing processing parameters
            upc_dict: Dictionary containing UPC mappings

        Returns:
            Path to the output file

        """
        ...


class MockTweaker:
    """Mock tweaker for testing purposes.

    This tweaker can be configured to return specific results
    and allows inspection of tweak calls.

    Attributes:
        result: The result to return from tweak()
        call_count: Number of times tweak was called
        last_input_path: Last input path passed to tweak
        last_output_dir: Last output directory passed to tweak
        last_params: Last params dict passed to tweak
        last_settings: Last settings dict passed to tweak
        last_upc_dict: Last upc_dict passed to tweak

    """

    def __init__(
        self,
        result: TweakerResult | None = None,
        output_path: str = "",
        *,
        success: bool = True,
        was_tweaked: bool = True,
        errors: list[str] | None = None,
    ) -> None:
        """Initialize the mock tweaker.

        Args:
            result: Complete result to return (overrides other params)
            output_path: Output path to return
            success: Whether to report success
            was_tweaked: Whether to report was_tweaked
            errors: List of error messages

        """
        if result is not None:
            self._result = result
        else:
            self._result = TweakerResult(
                output_path=output_path,
                success=success,
                was_tweaked=was_tweaked,
                errors=errors or [],
            )
        self.call_count: int = 0
        self.last_input_path: str | None = None
        self.last_output_dir: str | None = None
        self.last_params: dict | None = None
        self.last_settings: dict | None = None
        self.last_upc_dict: dict | None = None

    def tweak(
        self,
        input_path: str,
        output_dir: str,
        params: dict,
        settings: dict,
        upc_dict: dict,
    ) -> TweakerResult:
        """Mock tweak method.

        Args:
            input_path: Path to the input EDI file
            output_dir: Directory for output file
            params: Folder parameters dictionary
            settings: Global settings dictionary
            upc_dict: UPC dictionary

        Returns:
            The configured TweakerResult

        """
        self.call_count += 1
        self.last_input_path = input_path
        self.last_output_dir = output_dir
        self.last_params = params
        self.last_settings = settings
        self.last_upc_dict = upc_dict
        return self._result

    def reset(self) -> None:
        """Reset the mock state to initial values.

        Clears call counts and recorded arguments. Useful for reusing
        the same mock instance across multiple test cases.

        """
        self.call_count = 0
        self.last_input_path = None
        self.last_output_dir = None
        self.last_params = None
        self.last_settings = None
        self.last_upc_dict = None

    def set_result(self, result: TweakerResult) -> None:
        """Set the result to return.

        Args:
            result: The TweakerResult to return

        """
        self._result = result
