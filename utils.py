"""Compatibility layer for utils module.

This file provides backward compatibility by importing and re-exporting
functions from the new module structure. This allows existing code that
imports from 'utils' to continue working.

Note: This is a temporary compatibility layer. New code should import
directly from the appropriate modules.
"""

from core.utils.bool_utils import normalize_bool, to_db_bool, from_db_bool
from core.utils.date_utils import (
    dactime_from_datetime,
    datetime_from_dactime,
    datetime_from_invtime,
    dactime_from_invtime,
)
from core.edi.edi_parser import capture_records, _get_default_parser
from core.edi.edi_transformer import (
    dac_str_int_to_int,
    convert_to_price,
    convert_to_price_decimal,
    detect_invoice_is_credit,
)
from core.edi.upc_utils import (
    calc_check_digit,
    convert_upce_to_upca,
    apply_retail_uom_transform,
    apply_upc_override,
)
from core.edi.edi_splitter import EDISplitter
from dispatch.file_utils import do_clear_old_files

# Import from core/edi for duplicate classes
from core.edi.inv_fetcher import InvFetcher
from core.edi.c_rec_generator import CRecGenerator

# Provide aliases for capitalized function names (for backward compatibility)
convert_UPCE_to_UPCA = convert_upce_to_upca


# Define the old function-based split function that matches the original signature
def do_split_edi(edi_process, work_directory, parameters_dict):
    """Compatibility wrapper for do_split_edi.

    This function provides the old API for splitting EDI files while
    internally using the new EDISplitter class.

    Args:
        edi_process: Path to EDI file to split
        work_directory: Output directory for split files
        parameters_dict: Dictionary with parameters (prepend_date_files)

    Returns:
        List of (file_path, prefix, suffix) tuples
    """
    from core.edi.edi_splitter import RealFilesystem, SplitConfig

    splitter = EDISplitter(RealFilesystem())
    config = SplitConfig(
        output_directory=work_directory,
        prepend_date=parameters_dict.get("prepend_date_files", False),
    )

    try:
        with open(edi_process, encoding="utf-8") as f:
            content = f.read()
        result = splitter.split_edi(content, config)
        return result.output_files
    except Exception as e:
        raise Exception(f"Error splitting EDI file: {str(e)}")


# Provide alias for InvFetcher (lowercase for backward compatibility)
class invFetcher(InvFetcher):
    """Compatibility alias for InvFetcher."""

    def __init__(self, settings_dict):
        super().__init__(settings_dict)


# Provide alias for CRecGenerator (lowercase for backward compatibility)
class cRecGenerator(CRecGenerator):
    """Compatibility alias for CRecGenerator."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


def filter_edi_file_by_category(
    input_file: str,
    output_file: str,
    upc_dict: dict,
    filter_categories: str,
    filter_mode: str = "include"
) -> bool:
    """Compatibility wrapper for filter_edi_file_by_category.
    
    This function provides the old API for filtering EDI files by category,
    delegating to the new implementation in core.edi.edi_splitter.
    """
    from core.edi.edi_splitter import filter_edi_file_by_category as new_filter_edi_file_by_category

    return new_filter_edi_file_by_category(
        input_file, output_file, upc_dict, filter_categories, filter_mode
    )


# Re-export all names
__all__ = [
    "filter_edi_file_by_category",
    # Boolean normalization
    "normalize_bool",
    "to_db_bool",
    "from_db_bool",
    # Date/time conversion
    "dactime_from_datetime",
    "datetime_from_dactime",
    "datetime_from_invtime",
    "dactime_from_invtime",
    # EDI parsing
    "capture_records",
    "_get_default_parser",
    # EDI transformation
    "dac_str_int_to_int",
    "convert_to_price",
    "convert_to_price_decimal",
    "detect_invoice_is_credit",
    # EDI splitting
    "do_split_edi",
    "EDISplitter",
    # UPC operations
    "calc_check_digit",
    "convert_upce_to_upca",
    "convert_UPCE_to_UPCA",
    "apply_retail_uom_transform",
    "apply_upc_override",
    # File management
    "do_clear_old_files",
    # Classes (with aliases)
    "InvFetcher",
    "invFetcher",
    "CRecGenerator",
    "cRecGenerator",
]
