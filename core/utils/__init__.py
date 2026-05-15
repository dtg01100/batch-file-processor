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

import importlib
from typing import Any

from core.database.c_record_generator import CRecGenerator

from .bool_utils import from_db_bool, normalize_bool, normalize_db_bool, to_db_bool
from .csv_utils import add_row
from .date_utils import (
    dactime_from_datetime,
    dactime_from_invtime,
    datetime_from_dactime,
    datetime_from_invtime,
    prettify_dates,
)
from .file_utils import clear_old_files
from .format_utils import normalize_convert_to_format
from .safe_parse import qty_to_int, safe_float, safe_int
from .timing_utils import context_timer
from .utils import (
    apply_retail_uom_transform,
    apply_upc_override,
)

_EDI_REEXPORTS: dict[str, str] = {
    "capture_records": "core.edi.edi_parser",
    "EDIParseError": "core.edi.edi_parser",
    "do_split_edi": "core.edi.edi_splitting_utils",
    "filter_b_records_by_category": "core.edi.edi_splitting_utils",
    "filter_edi_file_by_category": "core.edi.edi_splitting_utils",
    "convert_to_price": "core.edi.edi_transformer",
    "convert_to_price_decimal": "core.edi.edi_transformer",
    "dac_str_int_to_int": "core.edi.edi_transformer",
    "detect_invoice_is_credit": "core.edi.edi_transformer",
    "calc_check_digit": "core.edi.upc_utils",
    "convert_upce_to_upca": "core.edi.upc_utils",
}


def __getattr__(name: str) -> Any:
    if name in _EDI_REEXPORTS:
        mod = importlib.import_module(_EDI_REEXPORTS[name])
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(__all__))


__all__ = [
    "CRecGenerator",
    "EDIParseError",
    "add_row",
    "apply_retail_uom_transform",
    "apply_upc_override",
    "calc_check_digit",
    "capture_records",
    "clear_old_files",
    "context_timer",
    "convert_to_price",
    "convert_to_price_decimal",
    "convert_upce_to_upca",
    "dac_str_int_to_int",
    "dactime_from_datetime",
    "dactime_from_invtime",
    "datetime_from_dactime",
    "datetime_from_invtime",
    "detect_invoice_is_credit",
    "do_split_edi",
    "filter_b_records_by_category",
    "filter_edi_file_by_category",
    "from_db_bool",
    "normalize_bool",
    "normalize_convert_to_format",
    "normalize_db_bool",
    "prettify_dates",
    "qty_to_int",
    "safe_float",
    "safe_int",
    "to_db_bool",
]
