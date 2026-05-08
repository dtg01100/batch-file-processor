"""Utility functions for batch file processing.

This module provides backward-compatible re-exports for functions that have
been moved to more focused modules:

- EDI splitting/filtering → ``core.edi.edi_splitting_utils``
- C record generation → ``core.database.c_record_generator``
- Quantity parsing → ``core.utils.safe_parse``
- CSV utilities → ``core.utils.csv_utils``

Legacy functions remaining here:

- apply_retail_uom_transform: Apply retail UOM transformation to B records
- apply_upc_override: Override UPC from lookup table

Import from source modules in new code.
"""

# Backward-compatible re-exports from focused modules
from core.database.c_record_generator import CRecGenerator
from core.edi.edi_splitting_utils import (
    _col_to_excel,
    do_split_edi,
    filter_b_records_by_category,
    filter_edi_file_by_category,
)

# Legacy functions that remain in this module
from core.structured_logging import get_logger
from core.utils.csv_utils import add_row
from core.utils.safe_parse import qty_to_int

logger = get_logger(__name__)

__all__ = [
    # Re-exports from focused modules
    "CRecGenerator",
    "_col_to_excel",
    "do_split_edi",
    "filter_b_records_by_category",
    "filter_edi_file_by_category",
    "add_row",
    "qty_to_int",
    # Legacy functions
    "apply_retail_uom_transform",
    "apply_upc_override",
]


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
    except (ValueError, KeyError, TypeError) as e:
        logger.warning("Cannot parse B record field: %s", e)
        return False

    # Get the each-level UPC from lookup
    try:
        each_upc_string = upc_lookup[item_number][1][:11].ljust(11)
    except (KeyError, IndexError):
        each_upc_string = "           "

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
        logger.debug("error applying retail UOM transform: %s", error)
        return False


def apply_upc_override(
    record: dict,
    upc_lookup: dict,
    override_level: int = 1,
    category_filter: str = "ALL",
) -> bool:
    """Override UPC from lookup table based on vendor_item.

    Modifies record in place: upc_number.

    Args:
        record: The B record dictionary to modify in place.
        upc_lookup: Dictionary mapping vendor item numbers to UPC data.
            Expected format: {vendor_item: [category, upc_level_1, upc_level_2, ...]}
        override_level: Which UPC level to use from lookup table (default: 1).
        category_filter: Comma-separated list of categories to filter by,
            or "ALL" to apply to all categories (default: "ALL").

    Returns:
        True if override was applied, False otherwise.

    """
    try:
        if not upc_lookup:
            return False

        vendor_item_int = int(record["vendor_item"].strip())

        if vendor_item_int not in upc_lookup:
            record["upc_number"] = ""
            return False

        do_updateupc = False
        if category_filter == "ALL":
            do_updateupc = True
        else:
            # Check if item's category is in the filter list
            item_category = upc_lookup[vendor_item_int][0]
            if item_category in category_filter.split(","):
                do_updateupc = True

        if do_updateupc:
            record["upc_number"] = upc_lookup[vendor_item_int][override_level]
            return True
        else:
            return False

    except (KeyError, ValueError, IndexError):
        record["upc_number"] = ""
        return False
