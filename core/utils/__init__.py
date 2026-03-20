"""Core utilities package.

This package contains small, focused utility modules organized by functionality:

- bool_utils: Boolean normalization utilities
- date_utils: Date/time conversion utilities
- utils: Legacy utilities (kept for backward compatibility)
"""

from .bool_utils import from_db_bool, normalize_bool, to_db_bool
from .date_utils import (
    dactime_from_datetime,
    dactime_from_invtime,
    datetime_from_dactime,
    datetime_from_invtime,
    prettify_dates,
)

# Import legacy utils for backward compatibility
from .utils import (
    apply_retail_uom_transform,
    apply_upc_override,
    calc_check_digit,
    capture_records,
    convert_to_price,
    convert_to_price_decimal,
    convert_UPCE_to_UPCA,
    dac_str_int_to_int,
    detect_invoice_is_credit,
    do_clear_old_files,
    do_split_edi,
    filter_b_records_by_category,
    filter_edi_file_by_category,
    invFetcher,
    add_row,
    qty_to_int,
)
from core.edi.edi_parser import EDIParseError

__all__ = [
    "normalize_bool",
    "to_db_bool",
    "from_db_bool",
    "dactime_from_datetime",
    "datetime_from_dactime",
    "datetime_from_invtime",
    "dactime_from_invtime",
    "prettify_dates",
    # Legacy utils
    "apply_retail_uom_transform",
    "apply_upc_override",
    "calc_check_digit",
    "capture_records",
    "convert_to_price",
    "convert_to_price_decimal",
    "convert_UPCE_to_UPCA",
    "dac_str_int_to_int",
    "detect_invoice_is_credit",
    "do_clear_old_files",
    "do_split_edi",
    "filter_b_records_by_category",
    "filter_edi_file_by_category",
    "invFetcher",
    "add_row",
    "qty_to_int",
    "EDIParseError",
]
