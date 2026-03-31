from typing import Any


def normalize_bool(value: Any) -> bool:
    """Convert any value to Python boolean.

    Accepts:
    - bool: True/False (returned as-is)
    - str: "true"/"false" (case-insensitive), "1"/"0", "yes"/"no"
    - int: 1/0, any non-zero is True
    - None: False
    - list/dict: bool(value) checks if non-empty

    Args:
        value: Any value to normalize

    Returns:
        Python bool (True or False)

    Examples:
        normalize_bool("True") → True
        normalize_bool("false") → False
        normalize_bool(1) → True
        normalize_bool(0) → False
        normalize_bool(None) → False
        normalize_bool("") → False

    """
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        # Handle string booleans
        lower_val = value.strip().lower()
        if lower_val in ("true", "1", "yes", "on"):
            return True
        if lower_val in ("false", "0", "no", "off", ""):
            return False
        # Default: non-empty string is truthy
        return bool(value.strip())

    if value is None:
        return False

    # For int/float: 0 is False, non-zero is True
    return bool(value)


def to_db_bool(value: Any) -> int:
    """Convert any value to SQLite integer (0 or 1).

    Used when writing boolean values to database.

    Args:
        value: Any value to convert

    Returns:
        1 for truthy values, 0 for falsy values

    Examples:
        to_db_bool(True) → 1
        to_db_bool("True") → 1
        to_db_bool(False) → 0
        to_db_bool(None) → 0

    """
    return 1 if normalize_bool(value) else 0


def normalize_db_bool(value: Any) -> bool:
    """Normalize a boolean value from database storage.

    Stricter than normalize_bool — only accepts the formats actually stored
    in the database: True/False booleans, integer 1/0, and string "True",
    "False", "1", "0" (legacy SQLite TEXT affinity form). Rejects "yes"/"no"
    and other truthy strings that the database would never contain.

    Used when reading boolean columns from SQLite that may have been written
    as string "True"/"False" by legacy code.

    Args:
        value: Database value (bool, int, float, str, or None)

    Returns:
        Python bool

    Examples:
        normalize_db_bool("True") -> True
        normalize_db_bool("1") -> True
        normalize_db_bool(1) -> True
        normalize_db_bool("False") -> False
        normalize_db_bool("yes") -> False  # rejected
        normalize_db_bool(None) -> False

    """
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lower_val = value.strip().lower()
        if lower_val in ("true", "1"):
            return True
        if lower_val in ("false", "0", ""):
            return False
    return False


def from_db_bool(value: Any) -> bool:
    """Convert SQLite value to Python boolean.

    Handles both legacy string booleans ("True"/"False") and new
    integer booleans (0/1). Used when reading boolean values from
    database or older code that stores strings.

    Args:
        value: Database value (could be int, str, bool, or None)

    Returns:
        Python bool

    Examples:
        from_db_bool("True") → True   # Legacy string format
        from_db_bool(1) → True         # New integer format
        from_db_bool("1") → True
        from_db_bool(0) → False
        from_db_bool("False") → False

    """
    return normalize_bool(value)
