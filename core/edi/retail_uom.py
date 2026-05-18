"""Retail UOM transformation utilities.

This module provides the shared implementation for transforming B records
from case-level to each-level retail UOM. Used by converters and tweaker.
"""

from decimal import Decimal

from core.structured_logging import get_logger

logger = get_logger(__name__)


def apply_retail_uom_transform(
    record: dict,
    upc_lookup: dict,
    default_upc_padding: str = "           ",
) -> bool:
    """Apply retail UOM transformation to a B record.

    Transforms B record from case-level to each-level retail UOM.
    Modifies record in place: unit_cost, qty_of_units, upc_number, unit_multiplier.

    Args:
        record: The B record dictionary to transform in place.
        upc_lookup: Dictionary mapping vendor item numbers to UPC data.
            Expected format: {vendor_item: [category, each_upc, ...]}
        default_upc_padding: Default UPC string when lookup fails (11 spaces).

    Returns:
        True if transformation was applied, False otherwise.

    """
    try:
        item_number = int(record["vendor_item"].strip())
        float(record["unit_cost"].strip())
        unit_multiplier = int(record["unit_multiplier"].strip())
        if unit_multiplier == 0:
            raise ValueError("unit_multiplier cannot be zero")
        int(record["qty_of_units"].strip())
    except (ValueError, KeyError, TypeError):
        return False

    try:
        each_upc_string = upc_lookup[item_number][1][:11].ljust(11)
    except (KeyError, IndexError):
        each_upc_string = default_upc_padding[:11]

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
    except Exception:
        logger.debug("Retail UOM transformation failed for record")
        return False

    return True