"""Tweaks EDI Converter - EDI Tweaks as a Conversion Backend.

This module exposes EDI tweaks as a conversion backend, allowing tweaks
to be applied through the same module-loading mechanism as other converters.

The tweak functionality is applied by the modern EDITweaker class in
core.edi.edi_tweaker, which performs various EDI transformations:
- A-record padding
- A-record appending
- Invoice date offsetting
- UPC check digit calculation
- Retail UOM conversion
- UPC override from lookup table
- C-record generation for split prepaid sales tax

The module maintains the standard converter interface with edi_convert() function.

Backward Compatibility:
    The module-level edi_convert() function maintains the same signature
    as other converters: edi_convert(edi_process, output_filename,
    settings_dict, parameters_dict, upc_lut)
"""

from core.edi.edi_tweaker import EDITweaker, _create_query_runner_adapter


def edi_convert(
    edi_process: str,
    output_filename: str,
    settings_dict: dict,
    parameters_dict: dict,
    upc_lut: dict,
) -> str:
    """Apply EDI tweaks to a file.

    This is the entry point for the conversion backend system. It uses
    the EDITweaker class from core.edi.edi_tweaker.

    Args:
        edi_process: Path to input EDI file
        output_filename: Path to output file (without extension - tweak adds it)
        settings_dict: Dictionary containing database and app settings
        parameters_dict: Dictionary containing tweak parameters:
            - pad_a_records: Whether to pad A records
            - a_record_padding: Padding text for A records
            - a_record_padding_length: Length for padding
            - append_a_records: Whether to append to A records
            - a_record_append_text: Text to append
            - invoice_date_custom_format: Use custom date format
            - invoice_date_custom_format_string: Custom date format string
            - force_txt_file_ext: Force .txt extension
            - calculate_upc_check_digit: Calculate UPC check digit
            - invoice_date_offset: Days to offset invoice date
            - retail_uom: Convert to retail UOM
            - override_upc_bool: Override UPC from lookup
            - override_upc_level: UPC level (1=pack, 2=case)
            - override_upc_category_filter: Category filter for UPC override
            - split_prepaid_sales_tax_crec: Split prepaid sales tax
            - upc_target_length: Target UPC length
            - upc_padding_pattern: UPC padding pattern
        upc_lut: UPC lookup table (item_number -> (category, upc_pack, upc_case))

    Returns:
        Path to the output file (may include .txt extension if force_txt_file_ext)

    Raises:
        Exception: Any exception raised by EDITweaker on failure
    """
    # Create query runner adapter from settings
    query_runner = _create_query_runner_adapter(settings_dict)

    # Create tweaker and apply tweaks
    tweaker = EDITweaker(query_runner)
    return tweaker.tweak(
        edi_process,
        output_filename,
        settings_dict,
        parameters_dict,
        upc_lut,
    )
