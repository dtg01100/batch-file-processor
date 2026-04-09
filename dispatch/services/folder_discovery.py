"""Folder Discovery Service for dispatch orchestrator.

This module extracts folder discovery and filtering logic from the
orchestrator into a dedicated service, following the Single Responsibility
Principle.

Responsibilities:
- Discover files in folders
- Filter already-processed files
- Handle pre-discovered file lists
- Report discovery progress
"""

import hashlib
import os
from typing import Any

from core.structured_logging import get_logger
from dispatch.interfaces import DatabaseInterface

logger = get_logger(__name__)


class FolderDiscoveryService:
    """Service for discovering and filtering files in folders.

    This service encapsulates all logic related to:
    - Finding files in a folder
    - Filtering out already-processed files
    - Handling pre-discovered file lists
    - Progress reporting during discovery

    Attributes:
        file_system: File system interface for directory operations
        progress_reporter: Optional progress reporter for UI updates

    """

    def __init__(
        self,
        file_system: Any = None,
        progress_reporter: Any = None,
    ) -> None:
        """Initialize the folder discovery service.

        Args:
            file_system: File system interface (uses os module if None)
            progress_reporter: Optional progress reporter

        """
        self._file_system = file_system
        self._progress_reporter = progress_reporter

    def discover_pending_files(
        self,
        folders: list[dict],
        processed_files: DatabaseInterface | None = None,
    ) -> tuple[list[list[str]], int]:
        """Discover files pending send for each folder.

        Performs a lightweight pre-pass that identifies files to be sent for each
        active folder, including already-processed filtering. This enables a
        dedicated "finding files" progress phase and avoids duplicate discovery
        work during processing by reusing the returned file lists.

        Args:
            folders: Active folder configuration rows in processing order.
            processed_files: Optional processed-files table for resend filtering.

        Returns:
            Tuple of:
                - List of pending-file lists aligned with ``folders`` order.
                - Total number of pending files across all folders.

        """
        folder_total = len(folders)
        pending_lists: list[list[str]] = []
        total_pending = 0

        reporter = self._progress_reporter
        if reporter and hasattr(reporter, "start_discovery"):
            reporter.start_discovery(folder_total=folder_total)

        for folder_index, folder in enumerate(folders, start=1):
            alias = folder.get("alias", folder.get("folder_name", ""))
            pending = self._discover_for_folder(
                folder,
                processed_files=processed_files,
                folder_index=folder_index,
                folder_total=folder_total,
                progress_reporter=reporter,
            )

            pending_lists.append(pending)
            total_pending += len(pending)

            if self._progress_reporter and hasattr(
                self._progress_reporter, "update_discovery_progress"
            ):
                self._progress_reporter.update_discovery_progress(
                    folder_num=folder_index,
                    folder_total=folder_total,
                    folder_name=alias,
                    pending_for_folder=len(pending),
                    pending_total=total_pending,
                )

        if reporter and hasattr(reporter, "finish_discovery"):
            reporter.finish_discovery(total_pending=total_pending)

        return pending_lists, total_pending

    def discover_and_filter_files(
        self,
        folder_path: str,
        pre_discovered_files: list[str] | None,
        processed_files: DatabaseInterface | None,
        folder: dict,
        run_log: Any = None,
    ) -> list[str] | None:
        """Discover files to process and filter already-processed files.

        Args:
            folder_path: Path to the folder to scan.
            pre_discovered_files: Optional list of files already discovered.
            processed_files: Database table for tracking processed files.
            folder: Folder configuration dictionary.
            run_log: Optional run log for recording activity.

        Returns:
            List of file paths to process, or None if no files found.

        """
        files = list(pre_discovered_files) if pre_discovered_files is not None else None

        if files is None:
            files = self._get_files_in_folder(folder_path)

            if not files:
                self._log_message(run_log, f"No files in directory: {folder_path}")
                return None

            logger.debug(
                "Found %d files in %s, filtering for already-processed...",
                len(files),
                folder_path,
            )

            if processed_files:
                files = self._filter_processed_files(files, processed_files, folder)

        if not files:
            self._log_message(run_log, f"No new files in directory: {folder_path}")
            return None

        return files

    def _discover_for_folder(
        self,
        folder: dict,
        processed_files: DatabaseInterface | None = None,
        folder_index: int | None = None,
        folder_total: int | None = None,
        progress_reporter: Any | None = None,
    ) -> list[str]:
        """Discover pending files for a single folder."""
        folder_path = folder.get("folder_name", "")
        alias = folder.get("alias", folder_path)

        if not self._folder_exists(folder_path):
            return []

        pending = self._get_files_in_folder(folder_path)
        if processed_files and pending:
            pending = self._filter_processed_files(
                pending,
                processed_files,
                folder,
                folder_index=folder_index,
                folder_total=folder_total,
                folder_name=alias,
                progress_reporter=progress_reporter,
            )

        return pending

    def _folder_exists(self, folder_path: str) -> bool:
        """Check if a folder exists."""
        return os.path.isdir(folder_path)

    def _get_files_in_folder(self, folder_path: str) -> list[str]:
        """Get list of files in a folder."""
        try:
            return [
                os.path.join(folder_path, f)
                for f in os.listdir(folder_path)
                if os.path.isfile(os.path.join(folder_path, f))
            ]
        except OSError as e:
            logger.error("Failed to list files in %s: %s", folder_path, e)
            return []

    def _filter_processed_files(
        self,
        files: list[str],
        processed_files: DatabaseInterface,
        folder: dict,
        folder_index: int | None = None,
        folder_total: int | None = None,
        folder_name: str | None = None,
        progress_reporter: Any | None = None,
    ) -> list[str]:
        """Filter out files that have already been processed.

        Args:
            files: List of file paths to filter.
            processed_files: Database table of processed files.
            folder: Folder configuration dictionary.
            folder_index: Current folder index for progress reporting.
            folder_total: Total number of folders for progress reporting.
            folder_name: Folder name for progress reporting.
            progress_reporter: Optional progress reporter override.

        Returns:
            Filtered list of unprocessed file paths.

        """
        folder_id = folder.get("id") or folder.get("old_id")
        processed = processed_files.find(folder_id=folder_id)

        # Files that should be SKIPPED (already processed AND NOT marked for resend)
        skipped_checksums = {
            f.get("file_checksum") for f in processed if not f.get("resend_flag")
        }

        logger.debug(
            "Filtering %d files, %d already processed (skip %d checksums)",
            len(files),
            len(processed),
            len(skipped_checksums),
        )

        # Calculate checksums one at a time to enable per-file progress reporting
        file_checksums: dict[str, str] = {}
        for idx, file_path in enumerate(files):
            file_checksums[file_path] = self._calculate_checksum(file_path)

            if progress_reporter and hasattr(
                progress_reporter, "update_discovery_file"
            ):
                progress_reporter.update_discovery_file(
                    folder_num=folder_index,
                    folder_total=folder_total,
                    file_num=idx + 1,
                    file_total=len(files),
                    filename=os.path.basename(file_path),
                )

        pending_files = [f for f in files if file_checksums[f] not in skipped_checksums]

        logger.debug(
            "Filtered files: %d total -> %d pending",
            len(files),
            len(pending_files),
        )

        return pending_files

    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate MD5 checksum of a file."""
        md5_hash = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    md5_hash.update(chunk)
            return md5_hash.hexdigest()
        except OSError as e:
            logger.warning("Failed to calculate checksum for %s: %s", file_path, e)
            return ""

    def _log_message(self, run_log: Any, message: str) -> None:
        """Write a message to the run log if available."""
        if hasattr(run_log, "write"):
            try:
                run_log.write(f"{message}\r\n".encode())
            except Exception:
                logger.debug("Failed to write to run log: %s", message)
