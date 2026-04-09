"""Progress Reporting Service for dispatch orchestrator.

This module extracts progress reporting logic from the orchestrator
into a dedicated service, following the Single Responsibility Principle.

Responsibilities:
- Initialize folder progress reporting
- Handle legacy vs modern progress reporter interfaces
- Report file processing progress
- Coordinate folder completion notifications
"""

from typing import Any

from core.structured_logging import get_logger

logger = get_logger(__name__)


class ProgressReportingService:
    """Service for managing progress reporting during dispatch operations.

    This service encapsulates all logic related to:
    - Starting folder processing with progress tracking
    - Handling both legacy and modern progress reporter interfaces
    - Reporting per-file progress
    - Completing folder processing notifications

    Attributes:
        progress_reporter: The progress reporter instance

    """

    def __init__(self, progress_reporter: Any = None) -> None:
        """Initialize the progress reporting service.

        Args:
            progress_reporter: Progress reporter instance (can be None)

        """
        self._progress_reporter = progress_reporter

    def start_folder(
        self,
        folder: dict,
        total_files: int,
        folder_num: int | None = None,
        folder_total: int | None = None,
    ) -> None:
        """Initialize progress reporter for folder processing.

        Calls the progress reporter's start_folder method with folder alias
        and file counts. Handles both old and new progress reporter interfaces
        (with/without folder_num and folder_total parameters).

        Args:
            folder: Folder configuration dictionary containing 'alias' or 'folder_name'.
            total_files: Number of files to process in this folder.
            folder_num: Current folder index (1-based), if available.
            folder_total: Total number of folders to process, if available.

        """
        if not self._progress_reporter:
            return

        progress = self._progress_reporter
        if not hasattr(progress, "start_folder"):
            return

        try:
            progress.start_folder(
                folder.get("alias", folder.get("folder_name", "")),
                total_files,
                folder_num=folder_num,
                folder_total=folder_total,
            )
        except TypeError:
            logger.warning(
                "Progress reporter start_folder() missing optional parameters "
                "(folder_num, folder_total). Update reporter signature."
            )
            progress.start_folder(
                folder.get("alias", folder.get("folder_name", "")), total_files
            )

    def complete_folder(self, success: bool) -> None:
        """Notify progress reporter that folder processing is complete.

        Args:
            success: Whether the folder was processed successfully

        """
        if self._progress_reporter and hasattr(
            self._progress_reporter, "complete_folder"
        ):
            self._progress_reporter.complete_folder(success=success)

    def update_file(self, current_file: int, total_files: int) -> None:
        """Report progress for a single file.

        Args:
            current_file: Current file index (1-based)
            total_files: Total number of files

        """
        if self._progress_reporter and hasattr(self._progress_reporter, "update_file"):
            self._progress_reporter.update_file(current_file, total_files)

    def set_folder_context(
        self,
        folder_num: int,
        folder_total: int,
        folder_name: str,
        file_total: int,
    ) -> None:
        """Set the context for folder processing progress.

        Args:
            folder_num: Current folder index (1-based)
            folder_total: Total number of folders
            folder_name: Name of the folder
            file_total: Number of files in this folder

        """
        if self._progress_reporter and hasattr(
            self._progress_reporter, "set_folder_context"
        ):
            self._progress_reporter.set_folder_context(
                folder_num=folder_num,
                folder_total=folder_total,
                folder_name=folder_name,
                file_total=file_total,
            )

    def start_sending(self, total_files: int, total_folders: int) -> None:
        """Notify that the sending phase is starting.

        Args:
            total_files: Total number of files to send
            total_folders: Total number of folders

        """
        if self._progress_reporter and hasattr(
            self._progress_reporter, "start_sending"
        ):
            self._progress_reporter.start_sending(
                total_files=total_files,
                total_folders=total_folders,
            )
