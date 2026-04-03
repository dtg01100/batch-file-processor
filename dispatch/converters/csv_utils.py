"""CSV Converter Utilities - Shared Utilities for CSV-Producing Converters.

This module provides utility functions and classes for converters that produce
CSV output, consolidating common patterns for UPC processing, retail UOM
transformation, and price formatting.

Functions:
- apply_retail_uom: Apply retail UOM transformation to B record fields
- apply_upc_override: Apply UPC override from lookup table
- process_upc_for_output: Process UPC field for CSV output
- format_retail_price: Format a price for retail output

Example:
    from dispatch.converters.csv_utils import apply_retail_uom

    def process_b_record(self, record, context):
        fields = dict(record.fields)
        if context.user_data.get("retail_uom"):
            fields = apply_retail_uom(fields, context.upc_lut,
                                      context.user_data["upc_target_length"])

"""

from decimal import Decimal, InvalidOperation
from typing import Any

from core.structured_logging import get_logger
from core.utils import calc_check_digit, convert_UPCE_to_UPCA, safe_int

logger = get_logger(__name__)


def apply_retail_uom(
    fields: dict[str, str],
    upc_lut: dict[int, tuple],
    upc_target_length: int = 11,
    upc_padding: str = "           ",
) -> dict[str, str]:
    """Apply retail UOM transformation to B record fields.

    Converts costs and quantities from case-level to each-level (retail) UOM.

    Args:
        fields: The B record fields dictionary (modified in place)
        upc_lut: UPC lookup table {vendor_item: (category, each_upc, case_upc, ...)}
        upc_target_length: Target length for UPC padding (default: 11)
        upc_padding: Padding pattern for missing UPCs

    Returns:
        Modified fields dictionary

    """
    # Validate fields can be parsed
    try:
        item_number = int(fields["vendor_item"].strip())
        float(fields["unit_cost"].strip())
        unit_multiplier = int(fields["unit_multiplier"].strip())
        if unit_multiplier == 0:
            raise ValueError("Unit multiplier cannot be zero")
        int(fields["qty_of_units"].strip())
    except (KeyError, ValueError, TypeError, AttributeError):
        return fields

    # Get UPC for each (retail) from lookup
    try:
        each_upc = upc_lut[item_number][1][:upc_target_length].ljust(upc_target_length)
    except (KeyError, IndexError):
        each_upc = upc_padding[:upc_target_length]

    # Apply conversion
    try:
        # Convert unit cost from case cost to each cost
        case_cost = Decimal(fields["unit_cost"].strip()) / 100
        each_cost = case_cost / Decimal(unit_multiplier)
        each_cost_cents = (
            str(each_cost.quantize(Decimal(".01"))).replace(".", "")[-6:].rjust(6, "0")
        )
        fields["unit_cost"] = each_cost_cents

        # Convert quantity from cases to eaches
        case_qty = int(fields["qty_of_units"].strip())
        each_qty = unit_multiplier * case_qty
        fields["qty_of_units"] = str(each_qty).rjust(5, "0")

        # Set UPC to each UPC and multiplier to 1
        fields["upc_number"] = each_upc
        fields["unit_multiplier"] = "000001"

    except (InvalidOperation, ValueError, TypeError, KeyError, ArithmeticError) as e:
        logger.debug("Retail UOM conversion skipped due to invalid data: %s", e)

    return fields


def apply_upc_override(
    fields: dict[str, str],
    upc_lut: dict[int, tuple],
    override_level: int = 1,
    category_filter: str = "ALL",
) -> dict[str, str]:
    """Apply UPC override from lookup table.

    Args:
        fields: The B record fields dictionary (modified in place)
        upc_lut: UPC lookup table {vendor_item: (category, pack_upc, case_upc, ...)}
        override_level: Which UPC level to use (1=pack, 2=case)
        category_filter: Comma-separated categories or "ALL"

    Returns:
        Modified fields dictionary

    """
    try:
        vendor_item = int(fields["vendor_item"].strip())

        if vendor_item not in upc_lut:
            fields["upc_number"] = ""
            return fields

        # Check category filter
        do_update = False
        upc_data = upc_lut[vendor_item]

        if category_filter == "ALL":
            do_update = True
        else:
            category = upc_data[0] if len(upc_data) > 0 else None
            if category in category_filter.split(","):
                do_update = True

        if do_update:
            override_level = safe_int(override_level)
            fields["upc_number"] = upc_data[override_level]

    except (KeyError, ValueError, IndexError):
        fields["upc_number"] = ""

    return fields


def process_upc_for_output(
    fields: dict[str, str],
    *,
    calc_check_digit_flag: bool = True,
    upc_target_length: int = 11,
    upc_padding: str = "           ",
) -> str:
    """Process UPC field for CSV output.

    Handles check digit calculation, UPC-E to UPC-A conversion,
    and formatting for output.

    Args:
        fields: The B record fields dictionary
        calc_check_digit_flag: Whether to calculate check digit
        upc_target_length: Target UPC length for padding
        upc_padding: Padding pattern for missing UPCs

    Returns:
        Processed UPC string for output

    """
    upc_field = fields.get("upc_number", "").strip()

    # Check if UPC is blank
    blank_upc = safe_int(upc_field, -1) == -1

    if blank_upc:
        return upc_padding[:upc_target_length]

    upc_string = ""
    proposed_upc = upc_field
    upc_len = len(str(proposed_upc))

    if upc_len == 12:
        upc_string = str(proposed_upc)
    elif upc_len == 11:
        upc_string = str(proposed_upc) + str(calc_check_digit(proposed_upc))
    elif upc_len == 8:
        converted = convert_UPCE_to_UPCA(proposed_upc)
        upc_string = converted if isinstance(converted, str) else ""
    elif upc_len < upc_target_length:
        # Pad short UPCs
        upc_string = str(proposed_upc).rjust(
            upc_target_length, upc_padding[0] if upc_padding else " "
        )

    return upc_string


def format_retail_price(
    unit_cost: str,
    unit_multiplier: str,
    *,
    as_string: bool = True,
) -> Any:
    """Calculate and format retail price from case cost.

    Converts case-level cost to each-level retail price.

    Args:
        unit_cost: Case unit cost (in cents, no decimal)
        unit_multiplier: Number of eaches per case
        as_string: Return as formatted string (True) or Decimal (False)

    Returns:
        Formatted price string (e.g., "5.99") or Decimal

    """
    try:
        case_cost = Decimal(unit_cost.strip()) / 100
        multiplier = int(unit_multiplier.strip())
        if multiplier == 0:
            return "0.00" if as_string else Decimal("0.00")
        retail_price = case_cost / Decimal(multiplier)
        result = retail_price.quantize(Decimal(".01"))
        return str(result) if as_string else result
    except (InvalidOperation, ValueError, TypeError, AttributeError, ArithmeticError):
        return "0.00" if as_string else Decimal("0.00")


def format_quantity(qty_str: str, *, allow_negative: bool = True) -> Any:
    """Format quantity string, stripping leading zeros.

    Args:
        qty_str: Raw quantity string
        allow_negative: Whether to handle negative quantities

    Returns:
        Integer quantity or original string if non-numeric

    """
    qty_str = qty_str.strip()

    if allow_negative and qty_str.startswith("-"):
        try:
            wrkqty = int(qty_str[1:])
            return wrkqty - (wrkqty * 2)
        except ValueError:
            return qty_str

    try:
        result = int(qty_str)
        return str(result) if result else qty_str  # Preserve original if zero
    except ValueError:
        return qty_str


def filter_description(desc: str, *, filter_ampersand: bool = False) -> str:
    """Process description field for output.

    Args:
        desc: Raw description string
        filter_ampersand: Whether to replace & with AND

    Returns:
        Processed description

    """
    desc = desc.rstrip()
    if filter_ampersand:
        desc = desc.replace("&", "AND")
    return desc
