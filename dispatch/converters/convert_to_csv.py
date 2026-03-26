"""CSV EDI Converter - Refactored to use Template Method Pattern.

This module converts EDI files to standard CSV format. It has been refactored
to use the BaseEDIConverter base class, eliminating ~90 lines of duplicated
code while maintaining the exact same behavior and output format.

The converter is highly configurable through parameters_dict:
- calculate_upc_check_digit: Prefix UPC with tab
- include_a_records: Include A (header) records in output
- include_c_records: Include C (charge) records in output
- include_headers: Include column headers in output
- filter_ampersand: Replace & with AND in descriptions
- pad_a_records: Pad A record vendor field
- a_record_padding: Padding value for A records
- override_upc_bool: Override UPC from lookup table
- override_upc_level: Which UPC level to use (1=pack, 2=case)
- override_upc_category_filter: Filter which categories to override
- retail_uom: Convert costs/quantities to retail (each) UOM
- upc_target_length: Target length for UPC padding (default: 11)
- upc_padding_pattern: Pattern for UPC padding

Backward Compatibility:
    The module-level edi_convert() function maintains the same signature
    as before: edi_convert(edi_process, output_filename, settings_dict,
    parameters_dict, upc_lut)
"""

import csv

from core import utils
from dispatch.converters.convert_base import (
    BaseEDIConverter,
    ConversionContext,
    EDIRecord,
    create_csv_writer,
    normalize_parameter,
)
from dispatch.converters.csv_utils import (
    apply_retail_uom,
    apply_upc_override,
    filter_description,
    format_quantity,
    process_upc_for_output,
)


class CSVConverter(BaseEDIConverter):
    """Converter for standard CSV format with configurable options.

    This class implements the hook methods required by BaseEDIConverter
    to produce configurable CSV output. It supports:
    - Optional A and C record inclusion
    - UPC calculation and override
    - Retail UOM conversion
    - Ampersand filtering
    """

    def _initialize_output(self, context: ConversionContext) -> None:
        """Initialize CSV output file and writer with parameters.

        Args:
            context: The conversion context

        """
        # Extract and normalize parameters
        params = context.parameters_dict

        context.user_data["calc_upc"] = normalize_parameter(
            params.get("calculate_upc_check_digit"), default=False
        )
        context.user_data["inc_arec"] = normalize_parameter(
            params.get("include_a_records"), default=False
        )
        context.user_data["inc_crec"] = normalize_parameter(
            params.get("include_c_records"), default=False
        )
        context.user_data["inc_headers"] = normalize_parameter(
            params.get("include_headers"), default=True
        )
        context.user_data["filter_ampersand"] = normalize_parameter(
            params.get("filter_ampersand"), default=False
        )
        context.user_data["pad_arec"] = normalize_parameter(
            params.get("pad_a_records"), default=False
        )
        context.user_data["arec_padding"] = params.get("a_record_padding", "")
        context.user_data["override_upc"] = normalize_parameter(
            params.get("override_upc_bool"), default=False
        )
        context.user_data["override_upc_level"] = params.get("override_upc_level", 1)
        context.user_data["override_upc_category_filter"] = params.get(
            "override_upc_category_filter", "ALL"
        )
        context.user_data["retail_uom"] = normalize_parameter(
            params.get("retail_uom"), default=False
        )
        context.user_data["upc_target_length"] = int(
            params.get("upc_target_length", 11) or 11
        )
        context.user_data["upc_padding_pattern"] = params.get(
            "upc_padding_pattern", "           "
        )

        # Open output file and create CSV writer
        context.output_file = open(
            context.get_output_path(".csv"), "w", newline="", encoding="utf-8"
        )
        context.csv_writer = create_csv_writer(
            context.output_file,
            dialect="excel",
            lineterminator="\r\n",
            quoting=csv.QUOTE_ALL,
        )

        # Write headers if enabled
        if context.user_data["inc_headers"]:
            context.csv_writer.writerow(
                [
                    "UPC",
                    "Qty. Shipped",
                    "Cost",
                    "Suggested Retail",
                    "Description",
                    "Case Pack",
                    "Item Number",
                ]
            )

    def _should_process_record_type(
        self, record_type: str, context: ConversionContext
    ) -> bool:
        """Determine if a record type should be processed.

        Filters A and C records based on include flags.

        Args:
            record_type: The type of record
            context: The conversion context

        Returns:
            True if the record should be processed

        """
        user_data = context.user_data

        if record_type == "A" and not user_data["inc_arec"]:
            return False
        if record_type == "C" and not user_data["inc_crec"]:
            return False

        return True

    def process_a_record(self, record: EDIRecord, context: ConversionContext) -> None:
        """Process an A record (header).

        Writes A record row if enabled, with optional padding.

        Args:
            record: The A record
            context: The conversion context

        """
        user_data = context.user_data

        # Apply padding if enabled
        if user_data["pad_arec"]:
            cust_vendor = user_data["arec_padding"]
        else:
            cust_vendor = record.fields["cust_vendor"]

        context.csv_writer.writerow(
            [
                record.fields["record_type"],
                cust_vendor,
                record.fields["invoice_number"],
                record.fields["invoice_date"],
                record.fields["invoice_total"],
            ]
        )

        # Store header in context for potential use by other records
        context.arec_header = record.fields

    def process_b_record(self, record: EDIRecord, context: ConversionContext) -> None:
        """Process a B record (line item) with all CSV options.

        Handles retail UOM conversion, UPC override/calculation,
        ampersand filtering, and all other CSV-specific options.

        Args:
            record: The B record
            context: The conversion context

        """
        user_data = context.user_data
        fields = dict(record.fields)  # Copy to allow modification

        # Apply retail UOM conversion if enabled
        if user_data["retail_uom"]:
            fields = self._apply_retail_uom_conversion(fields, context)

        # Apply UPC override if enabled
        if user_data["override_upc"]:
            fields = self._apply_upc_override(fields, context)

        # Process UPC for output
        upc_in_csv = self._process_upc_for_output(fields, user_data)

        # Process other fields
        quantity_shipped = self._process_quantity(fields["qty_of_units"])
        cost = utils.convert_to_price(fields["unit_cost"])
        suggested_retail = utils.convert_to_price(fields["suggested_retail_price"])
        description = self._process_description(
            fields["description"], filter_ampersand=user_data["filter_ampersand"]
        )
        case_pack = self._process_quantity(fields["unit_multiplier"])
        item_number = self._process_quantity(fields["vendor_item"])

        # Write the CSV row
        context.csv_writer.writerow(
            [
                upc_in_csv,
                quantity_shipped,
                cost,
                suggested_retail,
                description,
                case_pack,
                item_number,
            ]
        )

    def process_c_record(self, record: EDIRecord, context: ConversionContext) -> None:
        """Process a C record (charge/tax).

        Args:
            record: The C record
            context: The conversion context

        """
        context.csv_writer.writerow(
            [
                record.fields["record_type"],
                record.fields["charge_type"],
                record.fields["description"],
                record.fields["amount"],
            ]
        )

    def _apply_retail_uom_conversion(
        self, fields: dict, context: ConversionContext
    ) -> dict:
        """Apply retail UOM conversion to B record fields.

        Converts costs and quantities from case to each (retail) UOM.

        Args:
            fields: The B record fields
            context: The conversion context

        Returns:
            Modified fields dictionary

        """
        user_data = context.user_data
        return apply_retail_uom(
            fields,
            context.upc_lut,
            upc_target_length=user_data["upc_target_length"],
            upc_padding=user_data["upc_padding_pattern"],
        )

    def _apply_upc_override(self, fields: dict, context: ConversionContext) -> dict:
        """Apply UPC override from lookup table.

        Args:
            fields: The B record fields
            context: The conversion context

        Returns:
            Modified fields dictionary

        """
        user_data = context.user_data
        return apply_upc_override(
            fields,
            context.upc_lut,
            override_level=user_data["override_upc_level"],
            category_filter=user_data["override_upc_category_filter"],
        )

    def _process_upc_for_output(self, fields: dict, user_data: dict) -> str:
        """Process UPC field for CSV output.

        Handles check digit calculation and formatting.

        Args:
            fields: The B record fields
            user_data: User data with configuration

        Returns:
            Processed UPC string for output

        """
        calc_upc = user_data["calc_upc"]
        if calc_upc:
            return process_upc_for_output(
                fields,
                calc_check_digit_flag=True,
                upc_target_length=user_data["upc_target_length"],
                upc_padding=user_data["upc_padding_pattern"],
            )
        else:
            return fields["upc_number"]

    @staticmethod
    def _process_quantity(qty_str: str) -> str:
        """Process quantity field, stripping leading zeros.

        Args:
            qty_str: Raw quantity string

        Returns:
            Quantity with leading zeros stripped, or original if all zeros

        """
        return format_quantity(qty_str)

    @staticmethod
    def _process_description(desc: str, *, filter_ampersand: bool) -> str:
        """Process description field.

        Args:
            desc: Raw description
            filter_ampersand: Whether to replace & with AND

        Returns:
            Processed description

        """
        return filter_description(desc, filter_ampersand=filter_ampersand)


# =============================================================================
# Backward Compatibility Wrapper
# =============================================================================


def edi_convert(
    edi_process: str,
    output_filename: str,
    settings_dict: dict,
    parameters_dict: dict,
    upc_lut: dict,
) -> str:
    """Convert EDI file to CSV format with configurable options.

    This is the original function signature maintained for backward compatibility.
    It simply creates a CSVConverter instance and delegates to it.

    Args:
        edi_process: Path to the input EDI file
        output_filename: Base path for output file (without extension)
        settings_dict: Application settings dictionary
        parameters_dict: Conversion parameters (see module docstring for options)
        upc_lut: UPC lookup table (item_number -> (category, upc_pack, upc_case))

    Returns:
        Path to the generated CSV file

    Example:
        >>> result = edi_convert(
        ...     "input.edi",
        ...     "output",
        ...     settings_dict,
        ...     {'include_headers': 'True', 'include_c_records': 'False'},
        ...     {123456: ('CAT1', 'upc_pack', 'upc_case')}
        ... )
        >>> print(result)
        'output.csv'

    """
    converter = CSVConverter()
    return converter.edi_convert(
        edi_process, output_filename, settings_dict, parameters_dict, upc_lut
    )
