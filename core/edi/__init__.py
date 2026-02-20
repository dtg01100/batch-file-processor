"""Core EDI processing module.

This module contains refactored EDI processing components:
- upc_utils: Pure UPC utility functions
- edi_parser: EDI record parsing utilities
- edi_transformer: EDI data transformation functions
- inv_fetcher: Invoice data fetcher with injectable dependencies
- edi_splitter: EDI file splitting logic
"""

from core.edi.upc_utils import (
    calc_check_digit,
    convert_upce_to_upca,
    validate_upc,
    apply_retail_uom_transform,
    apply_upc_override,
)
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
from core.edi.edi_transformer import (
    dac_str_int_to_int,
    convert_to_price,
    convert_to_price_decimal,
    detect_invoice_is_credit,
)

__all__ = [
    # UPC utilities
    "calc_check_digit",
    "convert_upce_to_upca",
    "validate_upc",
    "apply_retail_uom_transform",
    "apply_upc_override",
    # EDI parsing
    "capture_records",
    "parse_a_record",
    "parse_b_record",
    "parse_c_record",
    "build_a_record",
    "build_b_record",
    "build_c_record",
    # EDI transformation
    "dac_str_int_to_int",
    "convert_to_price",
    "convert_to_price_decimal",
    "detect_invoice_is_credit",
    # Dataclasses
    "ARecord",
    "BRecord",
    "CRecord",
]
