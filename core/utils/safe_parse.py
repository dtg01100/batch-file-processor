"""Safe parsing utilities for converting strings to numbers with defaults."""

from typing import Union


def safe_int(value: Union[str, int, float, None], default: int = 0) -> int:
    """Safely convert a value to an integer with a default fallback.

    Args:
        value: The value to convert (can be string, int, float, or None)
        default: The default value to return if conversion fails (default: 0)

    Returns:
        The integer value, or default if conversion fails

    Examples:
        safe_int("42") → 42
        safe_int(42) → 42
        safe_int("invalid") → 0
        safe_int(None) → 0
        safe_int("invalid", -1) → -1
        safe_int("-5") → -5
    """
    if value is None:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return default
        try:
            # Handle negative numbers
            if stripped.startswith("-"):
                return -int(stripped[1:].strip())
            return int(stripped)
        except ValueError:
            return default
    return default


def safe_float(value: Union[str, int, float, None], default: float = 0.0) -> float:
    """Safely convert a value to a float with a default fallback.

    Args:
        value: The value to convert (can be string, int, float, or None)
        default: The default value to return if conversion fails (default: 0.0)

    Returns:
        The float value, or default if conversion fails

    Examples:
        safe_float("42.5") → 42.5
        safe_float(42) → 42.0
        safe_float("invalid") → 0.0
        safe_float(None) → 0.0
        safe_float("invalid", -1.0) → -1.0
        safe_float("-3.14") → -3.14
    """
    if value is None:
        return default
    if isinstance(value, float):
        return value
    if isinstance(value, int):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return default
        try:
            return float(stripped)
        except ValueError:
            return default
    return default
