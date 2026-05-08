"""Hash utility functions for file processing.

This module contains pure functions for generating and managing file hashes,
extracted from dispatch.py for testability.
"""

import hashlib
import os
import time

from core.constants import HASH_CALC_MAX_RETRIES
from core.structured_logging import get_logger

logger = get_logger(__name__)


def generate_match_lists(processed_files: list[dict]) -> tuple[list, list, set]:
    """Extract hash lists from processed files.

    Args:
        processed_files: List of dicts with file_name, file_checksum, resend_flag

    Returns:
        tuple of (hash_dict, name_dict, resend_set)
        - hash_dict: List of (file_name, file_checksum) tuples
        - name_dict: List of (file_checksum, file_name) tuples
        - resend_set: Set of checksums marked for resend

    """
    hash_dict = []
    name_dict = []
    resend_set = set()

    for entry in processed_files:
        hash_dict.append((entry["file_name"], entry["file_checksum"]))
        name_dict.append((entry["file_checksum"], entry["file_name"]))
        if entry.get("resend_flag") is True:
            resend_set.add(entry["file_checksum"])

    return hash_dict, name_dict, resend_set


def generate_file_hash(
    file_path: str,
    max_retries: int = HASH_CALC_MAX_RETRIES,
    retry_delay_base: float = 1.0,
) -> str:
    """Generate MD5 hash of file contents with retry logic.

    Args:
        file_path: Absolute or relative path to the file
        max_retries: Maximum number of retry attempts (default: 5)
        retry_delay_base: Base for exponential backoff delay (default: 1.0)

    Returns:
        Hexadecimal MD5 hash string of file contents

    Raises:
        FileNotFoundError: If file does not exist after retries
        PermissionError: If file cannot be read due to permissions
        IOError: If file cannot be read after max retries

    """
    absolute_path = os.path.abspath(file_path)
    generated_checksum: str | None = None
    checksum_attempt = 1

    while generated_checksum is None:
        try:
            with open(absolute_path, "rb") as f:
                h = hashlib.md5()
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
                generated_checksum = h.hexdigest()
        except Exception as e:
            if checksum_attempt < max_retries:
                logger.warning(
                    "Hash generation failed for %s on attempt %d/%d: %s",
                    absolute_path,
                    checksum_attempt,
                    max_retries,
                    e,
                )
                # Exponential backoff: 1s, 4s, 9s, 16s, 25s
                time.sleep(retry_delay_base * checksum_attempt * checksum_attempt)
                checksum_attempt += 1
            else:
                logger.error(
                    "Hash generation failed for %s after %d attempts: %s",
                    absolute_path,
                    checksum_attempt,
                    e,
                )
                raise

    return generated_checksum


def build_hash_dictionaries(
    folder_temp_processed_files_list: list[dict],
) -> tuple[dict[str, str], dict[str, str], set[str]]:
    """Build hash dictionaries from processed files list.

    Converts the output of generate_match_lists into dictionary format
    for efficient lookups.

    Args:
        folder_temp_processed_files_list: List of processed file records

    Returns:
        tuple of (folder_hash_dict, folder_name_dict, resend_flag_set)
        - folder_hash_dict: Maps file_name -> checksum
        - folder_name_dict: Maps checksum -> file_name
        - resend_flag_set: Set of checksums needing resend

    """
    hash_list, name_list, resend_set = generate_match_lists(
        folder_temp_processed_files_list
    )

    folder_hash_dict = dict(hash_list)
    folder_name_dict = dict(name_list)

    return folder_hash_dict, folder_name_dict, resend_set
