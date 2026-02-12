"""Pure UPC utility functions.

These functions have no external dependencies and are easily testable.

Reference:
    Code from http://code.activestate.com/recipes/528911-barcodes-convert-upc-e-to-upc-a/
    Author: greg p (GPL3)
"""


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


def pad_upc(upc: str, target_length: int, fill_char: str = ' ') -> str:
    """Pad or truncate UPC to target length.
    
    Args:
        upc: UPC value to pad
        target_length: Desired length
        fill_char: Character to use for padding
        
    Returns:
        UPC padded/truncated to target length
    """
    if len(upc) >= target_length:
        return upc[:target_length]
    return upc.rjust(target_length, fill_char)


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
