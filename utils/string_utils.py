"""
String and price conversion utilities.

This module provides functions for converting string representations of numbers,
prices, and other data transformations.
"""

import os


def dac_str_int_to_int(dacstr: str) -> int:
    """Convert DAC-style string integer to regular integer.

    Handles negative numbers that start with "-" in DAC format.

    Args:
        dacstr: DAC string integer

    Returns:
        Regular integer

    Examples:
        dac_str_int_to_int("123") → 123
        dac_str_int_to_int("-123") → -123
        dac_str_int_to_int("") → 0
    """
    if dacstr.strip() == "":
        return 0
    try:
        if dacstr.startswith("-"):
            return int(dacstr[1:]) - (int(dacstr[1:]) * 2)
        else:
            return int(dacstr)
    except ValueError:
        return 0


def convert_to_price(value: str) -> str:
    """Convert integer string to decimal price format.

    Args:
        value: Integer string representing price in cents

    Returns:
        Price string with decimal point

    Examples:
        convert_to_price("12345") → "123.45"
        convert_to_price("00123") → "1.23"
    """
    return (
        (value[:-2].lstrip("0") if not value[:-2].lstrip("0") == "" else "0")
        + "."
        + value[-2:]
    )


def do_clear_old_files(folder_path: str, maximum_files: int) -> None:
    """Remove oldest files from folder until maximum file count is reached.

    Args:
        folder_path: Path to folder to clean
        maximum_files: Maximum number of files to keep
    """
    while len(os.listdir(folder_path)) > maximum_files:
        oldest_file = min(
            os.listdir(folder_path),
            key=lambda f: os.path.getctime(os.path.join(folder_path, f)),
        )
        os.remove(os.path.join(folder_path, oldest_file))