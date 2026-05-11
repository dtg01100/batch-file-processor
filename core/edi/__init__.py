"""Core EDI processing module.

This module contains refactored EDI processing components:
- upc_utils: Pure UPC utility functions
- edi_parser: EDI record parsing utilities
- edi_transformer: EDI data transformation functions
- inv_fetcher: Invoice data fetcher with injectable dependencies
- edi_splitter: EDI file splitting logic
- edi_tweaker: EDI tweak transformations (replaces legacy edi_tweaks)
"""

from core.edi.edi_parser import (
    ARecord,
    BRecord,
    CRecord,
    build_a_record,
    build_b_record,
    build_c_record,
    capture_records,
    parse_a_record,
    parse_b_record,
    parse_c_record,
)
from core.edi.edi_transformer import (
    convert_to_price,
    convert_to_price_decimal,
    dac_str_int_to_int,
    detect_invoice_is_credit,
)
from core.edi.edi_tweaker import EDITweaker, TweakerConfig
from core.edi.upc_utils import (
    apply_retail_uom_transform,
    calc_check_digit,
    convert_upce_to_upca,
    validate_upc,
)

__all__ = [
    # Dataclasses
    "ARecord",
    "BRecord",
    "CRecord",
    # EDI tweaking
    "EDITweaker",
    "TweakerConfig",
    "apply_retail_uom_transform",
    "build_a_record",
    "build_b_record",
    "build_c_record",
    # UPC utilities
    "calc_check_digit",
    # EDI parsing
    "capture_records",
    "convert_to_price",
    "convert_to_price_decimal",
    "convert_upce_to_upca",
    # EDI transformation
    "dac_str_int_to_int",
    "detect_invoice_is_credit",
    "parse_a_record",
    "parse_b_record",
    "parse_c_record",
    "validate_upc",
]
