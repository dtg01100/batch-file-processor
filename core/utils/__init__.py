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

# Backward-compatible re-exports for widely-used helper functions.
# These are transitional and should be imported directly from their
# source modules in new code (core.edi.edi_parser, core.edi.upc_utils).
# Re-exports from core.edi modules for backward compatibility.
# Import directly from source modules in new code:
#   from core.edi.edi_parser import capture_records
#   from core.edi.edi_transformer import convert_to_price, etc.
#   from core.edi.upc_utils import calc_check_digit, etc.
from core.edi.edi_parser import EDIParseError, capture_records
from core.edi.edi_transformer import (
    convert_to_price,
    convert_to_price_decimal,
    dac_str_int_to_int,
    detect_invoice_is_credit,
)
from core.edi.upc_utils import (
    calc_check_digit,
    convert_upce_to_upca,
)

from .bool_utils import from_db_bool, normalize_bool, normalize_db_bool, to_db_bool
from .date_utils import (
    dactime_from_datetime,
    dactime_from_invtime,
    datetime_from_dactime,
    datetime_from_invtime,
    prettify_dates,
)
from .file_utils import (
    clear_old_files,
)
from .file_utils import (
    clear_old_files as do_clear_old_files,  # do_clear_old_files: compat alias
)
from .format_utils import normalize_convert_to_format
from .safe_parse import safe_float, safe_int
from .timing_utils import context_timer

# Legacy imports from utils.py - these are actually defined in core/utils/utils.py
# Functions from core.edi modules should be imported directly from their source modules:
#   from core.edi.edi_parser import capture_records
#   from core.edi.edi_transformer import convert_to_price, dac_str_int_to_int, etc.
#   from core.edi.upc_utils import calc_check_digit, convert_upce_to_upca, etc.
from .utils import (
    add_row,
    apply_retail_uom_transform,
    apply_upc_override,
    do_split_edi,
    filter_b_records_by_category,
    filter_edi_file_by_category,
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
    # Legacy utils - functions actually defined in core/utils/utils.py
    "apply_retail_uom_transform",
    "apply_upc_override",
    "do_split_edi",
    "filter_b_records_by_category",
    "filter_edi_file_by_category",
    "add_row",
    "qty_to_int",
    "EDIParseError",
    # Backward-compatible re-exports from core.edi
    "capture_records",
    "convert_to_price",
    "convert_to_price_decimal",
    "dac_str_int_to_int",
    "detect_invoice_is_credit",
    "calc_check_digit",
    "convert_upce_to_upca",
    "do_clear_old_files",
]
