"""Pure UPC utility functions.

These functions have no external dependencies and are easily testable.

Reference:
    Code from http://code.activestate.com/recipes/528911-barcodes-convert-upc-e-to-upc-a/
    Author: greg p (GPL3)
"""

from core.constants import (
    UPC_A_LENGTH,
    UPCE_7_DIGIT_LENGTH,
    UPCE_LENGTH,
    UPCE_SHORT_LENGTH,
)
from core.structured_logging import get_logger

logger = get_logger(__name__)


def calc_check_digit(value: str | int) -> int:
    """Calculate check digit for UPC codes.

    Works for both UPC-A and UPC-E formats.

    Args:
        value: UPC value without check digit

    Returns:
        Calculated check digit (0-9)

    Example:
        >>> calc_check_digit("04180000026")
        5

    """
    check_digit = 0
    odd_pos = True
    for char in str(value)[::-1]:
        if odd_pos:
            check_digit += int(char) * 3
        else:
            check_digit += int(char)
        odd_pos = not odd_pos
    check_digit = check_digit % 10
    check_digit = 10 - check_digit
    return check_digit % 10


def convert_upce_to_upca(upce_value: str) -> str:
    """Convert UPC-E to UPC-A format.

    Args:
        upce_value: UPC-E value (6, 7, or 8 digits)

    Returns:
        12-digit UPC-A value with check digit, or empty string if invalid

    Example:
        >>> convert_upce_to_upca("04182635")
        '041800000265'

    """
    if len(upce_value) == UPCE_SHORT_LENGTH:
        middle_digits = upce_value
    elif len(upce_value) == UPCE_7_DIGIT_LENGTH:
        middle_digits = upce_value[:6]
    elif len(upce_value) == UPCE_LENGTH:
        middle_digits = upce_value[1:7]
    else:
        return ""

    d1, d2, d3, d4, d5, d6 = list(middle_digits)

    if d6 in ["0", "1", "2"]:
        mfrnum = f"{d1}{d2}{d6}00"
        itemnum = (d3 + d4 + d5).zfill(5)
    elif d6 == "3":
        mfrnum = f"{d1}{d2}{d3}00"
        itemnum = (d4 + d5).zfill(5)
    elif d6 == "4":
        mfrnum = f"{d1}{d2}{d3}{d4}0"
        itemnum = d5.zfill(5)
    else:
        mfrnum = f"{d1}{d2}{d3}{d4}{d5}"
        itemnum = d6.zfill(5)

    newmsg = f"0{mfrnum}{itemnum}"
    check_digit = calc_check_digit(newmsg)
    return f"{newmsg}{check_digit}"


def validate_upc(upc: str) -> bool:
    """Validate a UPC code's check digit.

    Args:
        upc: Full UPC code including check digit

    Returns:
        True if check digit is valid, False otherwise

    Example:
        >>> validate_upc("041800000265")
        True
        >>> validate_upc("041800000260")
        False

    """
    if not upc or not upc.isdigit():
        return False

    if len(upc) < UPC_A_LENGTH:
        return False

    value = upc[:-1]
    expected_check = int(upc[-1])
    actual_check = calc_check_digit(value)

    return expected_check == actual_check


def pad_upc(upc: str, target_length: int, fill_char: str = " ") -> str:
    """Pad or truncate a UPC string to a target length.

    Args:
        upc: The UPC string to pad or truncate.
        target_length: The desired output length.
        fill_char: Character used for padding (default: space).

    Returns:
        Right-justified string of exactly target_length characters.
        If upc is longer than target_length, it is truncated to target_length.

    Example:
        >>> pad_upc("12345", 10)
        '     12345'
        >>> pad_upc("123456789", 5)
        '12345'

    """
    if len(upc) >= target_length:
        return upc[:target_length]
    return upc.rjust(target_length, fill_char)


def apply_retail_uom_transform(record: dict, upc_lookup: dict) -> bool:
    """Apply retail UOM transformation to a B record.

    Transforms B record from case-level to each-level retail UOM.
    Modifies record in place: unit_cost, qty_of_units, upc_number, unit_multiplier.

    Args:
        record: The B record dictionary to transform in place.
        upc_lookup: Dictionary mapping vendor item numbers to UPC data.
            Expected format: {vendor_item: [category, each_upc, ...]}

    Returns:
        True if transformation was applied, False otherwise.

    """
    from core.edi.retail_uom import apply_retail_uom_transform as _apply

    return _apply(record, upc_lookup)
