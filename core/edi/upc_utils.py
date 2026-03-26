"""Pure UPC utility functions.

These functions have no external dependencies and are easily testable.

Reference:
    Code from http://code.activestate.com/recipes/528911-barcodes-convert-upc-e-to-upc-a/
    Author: greg p (GPL3)
"""

import logging

from core.structured_logging import get_logger, log_with_context

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
    check_digit = check_digit % 10
    return check_digit


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
    if len(upce_value) == 6:
        middle_digits = upce_value
    elif len(upce_value) == 7:
        middle_digits = upce_value[:6]
    elif len(upce_value) == 8:
        middle_digits = upce_value[1:7]
    else:
        return ""

    d1, d2, d3, d4, d5, d6 = list(middle_digits)

    if d6 in ["0", "1", "2"]:
        mfrnum = d1 + d2 + d6 + "00"
        itemnum = "00" + d3 + d4 + d5
    elif d6 == "3":
        mfrnum = d1 + d2 + d3 + "00"
        itemnum = "000" + d4 + d5
    elif d6 == "4":
        mfrnum = d1 + d2 + d3 + d4 + "0"
        itemnum = "0000" + d5
    else:
        mfrnum = d1 + d2 + d3 + d4 + d5
        itemnum = "0000" + d6

    newmsg = "0" + mfrnum + itemnum
    check_digit = calc_check_digit(newmsg)
    return newmsg + str(check_digit)


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

    if len(upc) < 12:
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
    from decimal import Decimal

    # Validate record fields can be parsed
    try:
        item_number = int(record["vendor_item"].strip())
        float(record["unit_cost"].strip())
        test_unit_multiplier = int(record["unit_multiplier"].strip())
        if test_unit_multiplier == 0:
            raise ValueError("unit_multiplier cannot be zero")
        int(record["qty_of_units"].strip())
    except Exception as e:
        log_with_context(
            logger,
            logging.WARNING,
            "B record parse failed",
            operation="apply_retail_uom_transform",
            context={
                "error_type": type(e).__name__,
                "record_fields": list(record.keys()),
            },
        )
        return False

    # Get the each-level UPC from lookup
    try:
        each_upc_string = upc_lookup[item_number][1][:11].ljust(11)
        log_with_context(
            logger,
            logging.DEBUG,
            "UPC lookup successful",
            operation="apply_retail_uom_transform",
            context={
                "item_number": item_number,
                "upc_found": each_upc_string.strip() != "",
            },
        )
    except (KeyError, IndexError):
        each_upc_string = "           "
        log_with_context(
            logger,
            logging.DEBUG,
            "UPC lookup failed - item not in dictionary",
            operation="apply_retail_uom_transform",
            context={
                "item_number": item_number,
                "upc_dict_keys_count": len(upc_lookup),
            },
        )

    # Apply the transformation
    try:
        record["unit_cost"] = (
            str(
                Decimal(
                    (Decimal(record["unit_cost"].strip()) / 100)
                    / Decimal(record["unit_multiplier"].strip())
                ).quantize(Decimal(".01"))
            )
            .replace(".", "")[-6:]
            .rjust(6, "0")
        )
        record["qty_of_units"] = str(
            int(record["unit_multiplier"].strip()) * int(record["qty_of_units"].strip())
        ).rjust(5, "0")
        record["upc_number"] = each_upc_string
        record["unit_multiplier"] = "000001"
        return True
    except Exception as error:
        log_with_context(
            logger,
            logging.WARNING,
            "UPC transformation failed",
            operation="apply_retail_uom_transform",
            context={
                "item_number": item_number,
                "error_type": type(error).__name__,
                "error_message": str(error),
            },
        )
        return False
