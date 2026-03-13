"""ScannerWare EDI Converter - Refactored to use Template Method Pattern.

This module converts EDI files to ScannerWare fixed-width text format.
It has been refactored to use the BaseEDIConverter base class, eliminating
~50 lines of duplicated code while maintaining the exact same behavior
and output format.

The converter is configurable through parameters_dict:
- a_record_padding: Padding value for A records (6 characters)
- append_a_records: Whether to append custom text to A records
- a_record_append_text: Custom text to append to A records
- force_txt_file_ext: Force .txt extension instead of deriving from input
- invoice_date_offset: Days to offset the invoice date (for testing)

Output Format:
- A records: Fixed-width format with padding and optional append text
- B records: Fixed-width with UPC, description, item number, cost, etc.
- C records: Fixed-width with charge description and amount

Backward Compatibility:
    The module-level edi_convert() function maintains the same signature
    as before: edi_convert(edi_process, output_filename, settings_dict,
    parameters_dict, upc_lookup)
"""

from datetime import datetime, timedelta

from convert_base import (
    BaseEDIConverter,
    ConversionContext,
    EDIRecord,
    normalize_parameter,
)


class ScannerWareConverter(BaseEDIConverter):
    """Converter for ScannerWare fixed-width text format.

    This class implements the hook methods required by BaseEDIConverter
    to produce fixed-width text output compatible with ScannerWare systems.
    It supports:
    - A record padding and custom append text
    - Invoice date offset handling
    - Fixed-width field formatting for all record types
    """

    def _initialize_output(self, context: ConversionContext) -> None:
        """Initialize output file with parameters.

        Args:
            context: The conversion context
        """
        # Extract and normalize parameters
        params = context.parameters_dict

        context.user_data["arec_padding"] = params.get("a_record_padding", "")
        context.user_data["append_arec"] = normalize_parameter(
            params.get("append_a_records"), False
        )
        context.user_data["append_arec_text"] = params.get("a_record_append_text", "")
        context.user_data["force_txt_ext"] = normalize_parameter(
            params.get("force_txt_file_ext"), False
        )
        context.user_data["invoice_date_offset"] = params.get("invoice_date_offset", 0)

        # Determine output file extension
        if context.user_data["force_txt_ext"]:
            output_path = context.output_filename + ".txt"
        else:
            output_path = context.output_filename

        # Store output path for later use
        context.user_data["output_path"] = output_path

        # Open output file in binary mode (matching original behavior)
        context.output_file = open(output_path, "wb")

    def process_a_record(self, record: EDIRecord, context: ConversionContext) -> None:
        """Process an A record (header) with padding and date offset.

        Args:
            record: The A record
            context: The conversion context
        """
        user_data = context.user_data
        fields = record.fields

        # Build A record line
        line_builder_list = [
            fields["record_type"],
            user_data["arec_padding"].ljust(6),
            fields["invoice_number"],
            "   ",
        ]

        # Handle invoice date with optional offset
        write_invoice_date = fields["invoice_date"]
        invoice_date_offset = user_data["invoice_date_offset"]

        if invoice_date_offset != 0:
            invoice_date_string = fields["invoice_date"]
            if invoice_date_string != "000000":
                invoice_date = datetime.strptime(invoice_date_string, "%m%d%y")
                offset_invoice_date = invoice_date + timedelta(days=invoice_date_offset)
                write_invoice_date = datetime.strftime(offset_invoice_date, "%m%d%y")

        line_builder_list.append(write_invoice_date)
        line_builder_list.append(fields["invoice_total"])

        # Append custom text if enabled
        if user_data["append_arec"]:
            line_builder_list.append(user_data["append_arec_text"])

        # Write the line
        writeable_line = "".join(line_builder_list)
        context.output_file.write((writeable_line + "\r\n").encode())

        # Store header in context
        context.arec_header = fields

    def process_b_record(self, record: EDIRecord, context: ConversionContext) -> None:
        """Process a B record (line item) in fixed-width format.

        Args:
            record: The B record
            context: The conversion context
        """
        fields = record.fields

        line_builder_list = [
            fields["record_type"],
            fields["upc_number"].ljust(14),
            fields["description"][:25],
            fields["vendor_item"],
            fields["unit_cost"],
            "  ",
            fields["unit_multiplier"],
            fields["qty_of_units"],
            fields["suggested_retail_price"],
            "001",
            "       ",
        ]

        writeable_line = "".join(line_builder_list)
        context.output_file.write((writeable_line + "\r\n").encode())

    def process_c_record(self, record: EDIRecord, context: ConversionContext) -> None:
        """Process a C record (charge/tax) in fixed-width format.

        Args:
            record: The C record
            context: The conversion context
        """
        fields = record.fields

        line_builder_list = [
            fields["record_type"],
            fields["description"].ljust(25),
            "   ",
            fields["amount"],
        ]

        writeable_line = "".join(line_builder_list)
        context.output_file.write((writeable_line + "\r\n").encode())

    def _get_return_value(self, context: ConversionContext) -> str:
        """Get the return value for edi_convert().

        Returns the output file path (may be .txt or derived from input).

        Args:
            context: The conversion context

        Returns:
            The path to the generated output file
        """
        return context.user_data.get("output_path", context.output_filename)


# =============================================================================
# Backward Compatibility Wrapper
# =============================================================================


def edi_convert(
    edi_process: str,
    output_filename: str,
    settings_dict: dict,
    parameters_dict: dict,
    upc_lookup: dict,
) -> str:
    """Convert EDI file to ScannerWare fixed-width text format.

    This is the original function signature maintained for backward compatibility.
    It simply creates a ScannerWareConverter instance and delegates to it.

    Args:
        edi_process: Path to the input EDI file
        output_filename: Base path for output file (without extension)
        settings_dict: Application settings dictionary
        parameters_dict: Conversion parameters (see module docstring for options)
        upc_lookup: UPC lookup table (item_number -> (category, upc_pack, upc_case))

    Returns:
        Path to the generated text file

    Example:
        >>> result = edi_convert(
        ...     "input.edi",
        ...     "output",
        ...     settings_dict,
        ...     {'a_record_padding': 'PAD', 'append_a_records': 'True'},
        ...     {}
        ... )
        >>> print(result)
        'output.txt'
    """
    converter = ScannerWareConverter()
    return converter.edi_convert(
        edi_process, output_filename, settings_dict, parameters_dict, upc_lookup
    )


if __name__ == "__main__":
    import os
    import tempfile

    with tempfile.TemporaryDirectory() as workdir:
        infile_path = os.path.abspath(input("input file path: "))
        outfile_path = os.path.join(
            os.path.expanduser("~"), os.path.basename(infile_path)
        )
        new_outfile = edi_convert(
            infile_path,
            outfile_path,
            {},  # settings_dict
            {  # parameters_dict
                "a_record_padding": "CAPCDY",
                "append_a_records": "True",
                "a_record_append_text": "123456",
                "force_txt_file_ext": "False",
                "invoice_date_offset": 0,
            },
            {},  # upc_lookup
        )
        with open(new_outfile, "r", encoding="utf-8") as new_outfile_handle:
            for entry in new_outfile_handle.readlines():
                print(repr(entry))
