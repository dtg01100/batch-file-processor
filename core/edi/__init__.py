"""Core EDI processing module.

This module contains refactored EDI processing components:
- upc_utils: Pure UPC utility functions
- edi_parser: EDI record parsing utilities
- inv_fetcher: Invoice data fetcher with injectable dependencies
- edi_splitter: EDI file splitting logic
"""

from core.edi.upc_utils import calc_check_digit, convert_upce_to_upca, validate_upc
from core.edi.edi_parser import (
    capture_records,
    parse_a_record,
    parse_b_record,
    parse_c_record,
    build_a_record,
    build_b_record,
    build_c_record,
    ARecord,
    BRecord,
    CRecord,
)

__all__ = [
    # UPC utilities
    "calc_check_digit",
    "convert_upce_to_upca",
    "validate_upc",
    # EDI parsing
    "capture_records",
    "parse_a_record",
    "parse_b_record",
    "parse_c_record",
    "build_a_record",
    "build_b_record",
    "build_c_record",
    # Dataclasses
    "ARecord",
    "BRecord",
    "CRecord",
]
