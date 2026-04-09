"""File management utilities.

This module provides file system operations like cleanup and maintenance.
"""

import os

from core.structured_logging import get_logger, log_file_operation

logger = get_logger(__name__)


def clear_old_files(folder_path: str, maximum_files: int) -> None:
    """Delete oldest files in a folder until the count is at or below the maximum.

    Uses a while loop rather than a simple if check because files may be
    added concurrently by other processes. Each iteration re-scans the
    directory to get an accurate current count.

    Args:
        folder_path: Path to the folder to clean up.
        maximum_files: Maximum number of files to allow before deletion starts.

    """
    while True:
        try:
            files = os.listdir(folder_path)
        except OSError:
            return  # Folder doesn't exist or not accessible

        if len(files) <= maximum_files:
            break

        def _safe_ctime(f):
            try:
                return os.path.getctime(os.path.join(folder_path, f))
            except OSError:
                return float("inf")

        oldest = min(files, key=_safe_ctime)
        oldest_path = os.path.join(folder_path, oldest)
        try:
            os.remove(oldest_path)
            log_file_operation(
                logger,
                "delete",
                oldest_path,
                file_type="log",
                success=True,
                context={"reason": "cleanup", "max_files": maximum_files},
            )
        except FileNotFoundError:
            pass  # already deleted by another process
        except Exception as e:
            log_file_operation(
                logger,
                "delete",
                oldest_path,
                file_type="log",
                success=False,
                error=e,
                context={"reason": "cleanup", "max_files": maximum_files},
            )
            logger.warning(
                "Failed to delete old file %s: %s", oldest_path, e
            )
            break  # Stop trying if we can't delete
