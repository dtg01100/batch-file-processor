"""Compatibility shim for legacy dispatch.services.file_processor imports.

Phase 3 consolidates file processing orchestration into dispatch.orchestrator.
This module keeps a minimal API surface for import stability.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from core.utils.bool_utils import normalize_bool
from dispatch.orchestrator import DispatchOrchestrator


@dataclass
class FileProcessorResult:
    """Legacy result shape retained for compatibility.

    New code should consume dispatch.orchestrator.FileResult directly.
    """

    input_path: str = ""
    output_path: str = ""
    was_validated: bool = False
    validation_passed: bool = True
    was_split: bool = False
    was_converted: bool = False
    was_tweaked: bool = False
    files_sent: bool = False
    checksum: str = ""
    errors: list[str] = field(default_factory=list)


@runtime_checkable
class FileProcessorInterface(Protocol):
    """Legacy protocol retained for compatibility."""

    def process_file(
        self, file_path: str, folder: dict, settings: dict, upc_dict: dict
    ) -> FileProcessorResult: ...


class FileProcessor:
    """Adapter that delegates to DispatchOrchestrator as source of truth."""

    def __init__(self, orchestrator: DispatchOrchestrator | None = None, **_: Any):
        self._orchestrator = orchestrator

    def process(self, file_path: str, folder: dict) -> str | None:
        """Legacy helper retained for callers expecting processed path."""
        result = self.process_file(
            file_path, folder, folder.get("settings", {}), folder.get("upc_dict", {})
        )
        if result.files_sent or result.validation_passed:
            return result.output_path or file_path
        return None

    def process_file(
        self, file_path: str, folder: dict, settings: dict, upc_dict: dict
    ) -> FileProcessorResult:
        orchestrator = self._orchestrator
        if orchestrator is None:
            raise RuntimeError(
                "FileProcessor compatibility adapter requires an orchestrator instance"
            )

        orchestrator.config.settings = settings
        file_result = orchestrator._process_file_with_pipeline(
            file_path, folder, upc_dict
        )
        return FileProcessorResult(
            input_path=file_path,
            output_path=file_result.file_name,
            was_validated=True,
            validation_passed=file_result.validated,
            was_split=normalize_bool(folder.get("split_edi", False)),
            was_converted=file_result.converted,
            was_tweaked=(
                str(folder.get("convert_to_format", "")).strip().lower()
                == "tweaks"
            ),
            files_sent=file_result.sent,
            checksum=file_result.checksum,
            errors=list(file_result.errors),
        )


class MockFileProcessor:
    """Test double retained for compatibility with existing service tests."""

    def __init__(self, result: FileProcessorResult | None = None, **kwargs: Any):
        self._result = result or FileProcessorResult(**kwargs)
        self.call_count = 0
        self.last_file_path: str | None = None
        self.last_folder: dict | None = None
        self.last_settings: dict | None = None
        self.last_upc_dict: dict | None = None

    def process_file(
        self, file_path: str, folder: dict, settings: dict, upc_dict: dict
    ) -> FileProcessorResult:
        self.call_count += 1
        self.last_file_path = file_path
        self.last_folder = folder
        self.last_settings = settings
        self.last_upc_dict = upc_dict
        return self._result

    def reset(self) -> None:
        self.call_count = 0
        self.last_file_path = None
        self.last_folder = None
        self.last_settings = None
        self.last_upc_dict = None

    def set_result(self, result: FileProcessorResult) -> None:
        self._result = result
