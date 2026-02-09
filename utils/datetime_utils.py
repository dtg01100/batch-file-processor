"""
Date and time conversion utilities.

This module provides functions for converting between different date/time
formats used by the DAC system and standard Python datetime.
"""

from datetime import datetime


def dactime_from_datetime(date_time: datetime) -> str:
    """Convert Python datetime to DAC time format string.

    Args:
        date_time: Python datetime object

    Returns:
        DAC time string (format: YYMMDDD)

    Example:
        dactime_from_datetime(datetime(2026, 2, 9)) → "2602090"
    """
    dactime_date_century_digit = str(int(datetime.strftime(date_time, "%Y")[:2]) - 19)
    dactime_date = dactime_date_century_digit + str(
        datetime.strftime(date_time.date(), "%y%m%d")
    )
    return dactime_date


def datetime_from_dactime(dac_time: int) -> datetime:
    """Convert DAC time format to Python datetime.

    Args:
        dac_time: DAC time integer (format: YYMMDDD)

    Returns:
        Python datetime object

    Example:
        datetime_from_dactime(2602090) → datetime(2026, 2, 9)
    """
    dac_time_int = int(dac_time)
    return datetime.strptime(str(dac_time_int + 19000000), "%Y%m%d")


def datetime_from_invtime(invtime: str) -> datetime:
    """Convert invoice time string to Python datetime.

    Args:
        invtime: Invoice time string (format: MMDDYY)

    Returns:
        Python datetime object

    Example:
        datetime_from_invtime("020926") → datetime(2026, 2, 9)
    """
    return datetime.strptime(invtime, "%m%d%y")


def dactime_from_invtime(inv_no: str) -> str:
    """Convert invoice time string to DAC time format.

    Args:
        inv_no: Invoice time string (format: MMDDYY)

    Returns:
        DAC time string (format: YYMMDDD)

    Example:
        dactime_from_invtime("020926") → "2602090"
    """
    datetime_obj = datetime_from_invtime(inv_no)
    dactime = dactime_from_datetime(datetime_obj)
    return dactime