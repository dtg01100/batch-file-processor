"""File utility functions for dispatch processing.

This module contains pure functions for file operations,
extracted from dispatch.py for testability.
"""

import contextlib
import datetime
import os
import re
import shutil
import tempfile
from typing import Any

from core.structured_logging import get_logger

# Backward-compatible re-export: callers use do_clear_old_files from this module.
# Import directly from core.utils.file_utils in new code.
from core.utils.file_utils import clear_old_files as do_clear_old_files

logger = get_logger(__name__)

# Precompiled regex for stripping invalid filename characters
_INVALID_FILENAME_CHARS_RE = re.compile(r"[^A-Za-z0-9. _]+")
_INVALID_ALIAS_CHARS_RE = re.compile(r"[^a-zA-Z0-9 ]")


def build_output_filename(
    original: str,
    _format: str,
    params: dict,
    filename_prefix: str = "",
    filename_suffix: str = "",
) -> str:
    """Build output filename based on format and parameters.

    Args:
        original: Original filename (may include path)
        format: Output format name (e.g., "Fintech", "Simplified CSV")
        params: Dictionary of parameters including:
            - rename_file: Template for renaming (supports %datetime%)
            - Other format-specific parameters
        filename_prefix: Prefix to add to filename (from EDI splitting)
        filename_suffix: Suffix to add to filename (from EDI splitting)

    Returns:
        Constructed output filename (basename only, no path)

    """
    rename_template = params.get("rename_file", "").strip()

    if rename_template:
        date_time = datetime.datetime.strftime(datetime.datetime.now(), "%Y%m%d")
        rename_file = "".join(
            [
                filename_prefix,
                rename_template.replace("%datetime%", date_time),
                ".",
                original.rsplit(".", maxsplit=1)[-1],
                filename_suffix,
            ]
        )
    else:
        rename_file = original

    # Strip invalid characters
    stripped_filename = _INVALID_FILENAME_CHARS_RE.sub("", rename_file)

    return stripped_filename


def build_error_log_filename(
    alias: str, errors_folder: str, folder_name: str, timestamp: str | None = None
) -> str:
    """Build the full path for a folder error log file.

    Args:
        alias: Folder alias (will be cleaned of special chars)
        errors_folder: Base errors folder path
        folder_name: Name of the folder (for subdirectory)
        timestamp: Optional timestamp string (defaults to current time)

    Returns:
        Full path to error log file

    """
    # Strip invalid characters from alias
    cleaned_alias = _INVALID_ALIAS_CHARS_RE.sub("", alias)

    # Generate timestamp if not provided
    if timestamp is None:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Build filename
    log_name = f"{cleaned_alias} errors.{timestamp}.txt"

    # Build full path
    full_path = os.path.join(errors_folder, os.path.basename(folder_name), log_name)

    return full_path


def get_file_extension(filename: str) -> str:
    """Get the file extension from a filename.

    Args:
        filename: Filename or path

    Returns:
        File extension without the dot (e.g., "txt", "edi")

    """
    return os.path.splitext(filename)[1].lstrip(".")


def strip_invalid_filename_chars(filename: str) -> str:
    """Remove invalid characters from a filename.

    Args:
        filename: Original filename

    Returns:
        Filename with only alphanumeric, dots, spaces, and underscores

    """
    return re.sub("[^A-Za-z0-9. _]+", "", filename)


def ensure_directory_exists(path: str) -> bool:
    """Ensure a directory exists, creating it if necessary.

    Args:
        path: Directory path to ensure exists

    Returns:
        True if directory exists or was created, False on error

    """
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except OSError:
        return False


def list_files_in_directory(directory: str, *, files_only: bool = True) -> list[str]:
    """List all files in a directory.

    Args:
        directory: Path to directory
        files_only: If True, only return files (not subdirectories)

    Returns:
        List of absolute file paths

    """
    if not os.path.isdir(directory):
        return []

    files = []
    for item in os.listdir(path=directory):
        full_path = os.path.abspath(os.path.join(directory, item))
        if files_only:
            if os.path.isfile(full_path):
                files.append(full_path)
        else:
            files.append(full_path)

    return files


def build_processed_file_record(
    original_filename: str,
    folder_id: int,
    folder_alias: str,
    file_checksum: str,
    params: dict,
) -> dict:
    """Build a processed file record for database insertion.

    Args:
        original_filename: Original file path
        folder_id: ID of the folder
        folder_alias: Alias of the folder
        file_checksum: MD5 checksum of the file
        params: Dictionary with backend settings:
            - process_backend_copy: bool
            - copy_to_directory: str
            - process_backend_ftp: bool
            - ftp_server: str
            - ftp_folder: str
            - process_backend_email: bool
            - email_to: str

    Returns:
        Dictionary ready for database insertion

    """
    return {
        "file_name": str(original_filename),
        "folder_id": folder_id,
        "folder_alias": folder_alias,
        "file_checksum": file_checksum,
        "sent_date_time": datetime.datetime.now(),
        "copy_destination": (
            "N/A"
            if not params.get("process_backend_copy")
            else params.get("copy_to_directory", "N/A")
        ),
        "ftp_destination": (
            "N/A"
            if not params.get("process_backend_ftp")
            else params.get("ftp_server", "") + params.get("ftp_folder", "")
        ),
        "email_destination": (
            "N/A"
            if not params.get("process_backend_email")
            else params.get("email_to", "N/A")
        ),
        "resend_flag": False,
    }


def extract_invoice_numbers(
    file_path: str,
    file_system: Any = None,
) -> str:
    """Extract invoice numbers from EDI A-records in a file.

    Args:
        file_path: Path to the EDI file
        file_system: Optional file system interface (e.g., RealFileSystem).
            If None, uses built-in open().

    Returns:
        Comma-separated string of invoice numbers, or empty string

    """
    from core.edi.edi_parser import capture_records

    try:
        if file_system:
            content_bytes = file_system.read_file(file_path)
            content = (
                content_bytes.decode("utf-8", errors="replace")
                if isinstance(content_bytes, bytes)
                else content_bytes
            )
        else:
            with open(file_path, errors="replace") as f:
                content = f.read()

        seen: dict[str, None] = {}
        for line in content.splitlines():
            try:
                rec = capture_records(line)
                if rec and rec.get("record_type") == "A":
                    inv_num = rec.get("invoice_number", "").strip()
                    if inv_num:
                        seen[inv_num] = None
            except (ValueError, KeyError):
                continue

        return ", ".join(seen)
    except (OSError, ValueError, KeyError) as e:
        logger.exception("Failed to extract invoice numbers from %s: %s", file_path, e)
        return ""


def apply_file_rename(
    file_path: str,
    rename_template: str,
    temp_dirs: list[str],
) -> str:
    """Apply file rename if a template is configured.

    Creates a temp copy with the new name (tracked in temp_dirs for cleanup)
    and returns its path. If rename_template is empty, returns the original path.

    Args:
        file_path: Current file path
        rename_template: Template for new filename (supports %datetime%)
        temp_dirs: List to track created temp directories for cleanup

    Returns:
        Path to renamed file copy, or original path if no rename

    Raises:
        ValueError: If the template is absolute or contains path traversal

    """
    rename_template = rename_template.strip()
    if not rename_template:
        return file_path

    original_basename = os.path.basename(file_path)
    date_time = datetime.datetime.strftime(datetime.datetime.now(), "%Y%m%d")
    ext = original_basename.split(".")[-1] if "." in original_basename else ""
    new_name = rename_template.replace("%datetime%", date_time)
    if ext:
        new_name = f"{new_name}.{ext}"

    new_name = re.sub("[^A-Za-z0-9. _]+", "", new_name)

    temp_dir = tempfile.mkdtemp(prefix="edi_rename_")
    temp_dirs.append(temp_dir)

    if not new_name or new_name == ".." or os.path.isabs(new_name):
        raise ValueError(f"Invalid filename pattern in rename template: {new_name}")

    full_dest = os.path.join(temp_dir, new_name)
    real_full_dest = os.path.realpath(full_dest)
    if not real_full_dest.startswith(os.path.realpath(temp_dir) + os.sep):
        raise ValueError(f"Path traversal attempt detected: {new_name}")

    shutil.copy2(file_path, full_dest)
    logger.debug("Renamed %s → %s for send", original_basename, new_name)
    return full_dest


def write_to_run_log(run_log: Any, message: str, prefix: str = "") -> None:
    """Write a message to a run log buffer.

    Handles both StringIO (write/encode) and list (append) targets.

    Args:
        run_log: Log target (StringIO, list, or None)
        message: Message to write
        prefix: Optional prefix (e.g., "ERROR: ")

    """
    full_message = f"{prefix}{message}" if prefix else message
    if hasattr(run_log, "write"):
        with contextlib.suppress(Exception):
            run_log.write(f"{full_message}\r\n".encode())
    elif hasattr(run_log, "append"):
        run_log.append(full_message)


__all__ = [
    "apply_file_rename",
    "build_error_log_filename",
    "build_output_filename",
    "build_processed_file_record",
    "do_clear_old_files",
    "ensure_directory_exists",
    "extract_invoice_numbers",
    "get_file_extension",
    "list_files_in_directory",
    "strip_invalid_filename_chars",
    "write_to_run_log",
]
