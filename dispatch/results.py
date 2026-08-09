"""Shared result types for dispatch operations.

This module contains dataclasses returned by dispatch services,
extracted from orchestrator.py to break circular dependencies.

IMPORT NOTE (import cycle): this module MUST stay a leaf of the dispatch
import graph. It must never import from ``dispatch.services`` or
``dispatch.pipeline`` at runtime. ``ProgressReporter`` is only used as a
type annotation, so it is imported under ``TYPE_CHECKING``; a runtime import
here used to drag in ``dispatch.services`` -> ``dispatch.pipeline`` ->
back to this module, creating the cycle documented in
``docs/IMPORT_ARCHITECTURE.md``. See also the eager-re-export comments in
``dispatch/services/__init__.py`` and ``dispatch/pipeline/__init__.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from dispatch.interfaces import (
    BackendInterface,
    DatabaseInterface,
    ErrorHandlerInterface,
    FileSystemInterface,
    UPCDictionaryProvider,
)

if TYPE_CHECKING:
    from dispatch.services.progress_reporter import ProgressReporter


@dataclass
class DispatchConfig:
    """Configuration for the dispatch orchestrator.

    Attributes:
        database: Database interface for persistence
        file_system: File system interface for file operations
        backends: Dictionary of backend name to backend instance
        error_handler: Error handler instance
        settings: Global application settings
        upc_service: UPC service for dictionary fetching
        progress_reporter: Progress reporter
        validator_step: Pipeline validator step
        splitter_step: Pipeline splitter step
        converter_step: Pipeline converter step
        file_processor: File processor service
        upc_dict: Cached UPC dictionary

    """

    database: DatabaseInterface | None = None
    file_system: FileSystemInterface | None = None
    backends: dict[str, BackendInterface] = field(default_factory=dict)
    error_handler: ErrorHandlerInterface | None = None
    settings: dict = field(default_factory=dict)
    version: str = "1.0.0"
    upc_service: UPCDictionaryProvider | None = None
    progress_reporter: ProgressReporter | None = None
    validator_step: Any | None = None
    splitter_step: Any | None = None
    converter_step: Any | None = None
    file_processor: Any | None = None
    upc_dict: dict = field(default_factory=dict)


@dataclass
class FolderResult:
    """Result of processing a single folder.

    Attributes:
        folder_name: Name of the processed folder
        alias: Folder alias
        files_processed: Number of files successfully processed
        files_failed: Number of files that failed
        errors: List of error messages
        success: Whether the folder was processed successfully

    """

    folder_name: str
    alias: str
    files_processed: int = 0
    files_failed: int = 0
    errors: list[str] = field(default_factory=list)
    success: bool = True
