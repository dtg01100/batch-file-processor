"""Core utilities package.

This package contains small, focused utility modules organized by functionality:

- bool_utils: Boolean normalization utilities
- date_utils: Date/time conversion utilities
- file_utils: File management utilities
- format_utils: Format conversion utilities
- safe_parse: Safe parsing utilities
- timing_utils: Timing and profiling utilities
- utils: Legacy utilities (deprecated, use specific modules above)
"""

from core.edi.edi_parser import EDIParseError

from .bool_utils import from_db_bool, normalize_bool, normalize_db_bool, to_db_bool
from .date_utils import (
    dactime_from_datetime,
    dactime_from_invtime,
    datetime_from_dactime,
    datetime_from_invtime,
    prettify_dates,
)
from .file_utils import clear_old_files
from .format_utils import normalize_convert_to_format
from .safe_parse import safe_float, safe_int
from .timing_utils import context_timer

# Legacy imports - DEPRECATED, use specific modules instead
from .utils import (
    add_row,
    apply_retail_uom_transform,
    apply_upc_override,
    calc_check_digit,
    capture_records,
    convert_to_price,
    convert_to_price_decimal,
    convert_UPCE_to_UPCA,
    dac_str_int_to_int,
    detect_invoice_is_credit,
    do_clear_old_files,  # Deprecated: use clear_old_files instead
    do_split_edi,
    filter_b_records_by_category,
    filter_edi_file_by_category,
    invFetcher,
    qty_to_int,
)

__all__ = [
    "context_timer",
    "normalize_bool",
    "normalize_db_bool",
    "normalize_convert_to_format",
    "to_db_bool",
    "from_db_bool",
    "dactime_from_datetime",
    "datetime_from_dactime",
    "datetime_from_invtime",
    "dactime_from_invtime",
    "prettify_dates",
    "safe_int",
    "safe_float",
    "clear_old_files",
    # Legacy utils - deprecated
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
