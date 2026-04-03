"""Simplified CSV EDI Converter - Refactored to use Template Method Pattern.

This module converts EDI files to a simplified CSV format with configurable
column layout. It has been refactored to use the BaseEDIConverter base class,
eliminating ~80 lines of duplicated code while maintaining the exact same
behavior and output format.

The converter is configurable through parameters_dict:
- retail_uom: Convert costs/quantities to retail (each) UOM
- include_headers: Include column headers in output
- include_item_numbers: Include vendor item numbers in output
- include_item_description: Include item descriptions in output
- simple_csv_sort_order: Comma-separated list of column names defining output order

Backward Compatibility:
    The module-level edi_convert() function maintains the same signature
    as before: edi_convert(edi_process, output_filename, settings_dict,
    parameters_dict, upc_lookup)
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
from dispatch.converters.csv_utils import apply_retail_uom


class SimplifiedCSVConverter(BaseEDIConverter):
    """Converter for simplified CSV format with configurable column layout.

    This class implements the hook methods required by BaseEDIConverter
    to produce simplified CSV output with configurable columns. It supports:
    - Configurable column ordering via simple_csv_sort_order parameter
    - Optional headers, item numbers, and descriptions
    - Retail UOM conversion
    """

    def _initialize_output(self, context: ConversionContext) -> None:
        """Initialize CSV output file and writer with parameters.

        Args:
            context: The conversion context

        """
        # Extract and normalize parameters
        params = context.parameters_dict

        context.user_data["retail_uom"] = normalize_parameter(
            params.get("retail_uom"), default=False
        )
        context.user_data["inc_headers"] = normalize_parameter(
            params.get(
                "include_headers", params.get("simple_csv_include_headers", True)
            )
        )
        context.user_data["inc_item_numbers"] = normalize_parameter(
            params.get("include_item_numbers"), default=True
        )
        context.user_data["inc_item_desc"] = normalize_parameter(
            params.get("include_item_description"), default=True
        )
        context.user_data["column_layout"] = (
            params.get(
                "simple_csv_sort_order",
                "upc_number,qty_of_units,unit_cost,description,vendor_item",
            )
            or "upc_number,qty_of_units,unit_cost,description,vendor_item"
        )

        # Open output file and create CSV writer
        context.output_file = open(
            context.get_output_path(".csv"), "w", newline="", encoding="utf-8"
        )
        context.csv_writer = create_csv_writer(
            context.output_file,
            dialect="excel",
            lineterminator="\r\n",
            quoting=csv.QUOTE_MINIMAL,
        )

        # Write headers if enabled
        if context.user_data["inc_headers"]:
            self._write_headers(context)

    def _write_headers(self, context: ConversionContext) -> None:
        """Write column headers based on column layout configuration.

        Args:
            context: The conversion context

        """
        user_data = context.user_data
        column_layout = user_data["column_layout"]
        inc_item_desc = user_data["inc_item_desc"]
        inc_item_numbers = user_data["inc_item_numbers"]

        # Header mapping
        header_map = {
            "upc_number": "UPC",
            "qty_of_units": "Quantity",
            "unit_cost": "Cost",
            "description": "Item Description",
            "vendor_item": "Item Number",
        }

        headers = []
        for column in column_layout.split(","):
            column = column.strip()
            if column in ["description", "vendor_item"]:
                if inc_item_desc and column == "description":
                    headers.append(header_map[column])
                if inc_item_numbers and column == "vendor_item":
                    headers.append(header_map[column])
            else:
                headers.append(header_map.get(column, column))

        context.csv_writer.writerow(headers)

    def _add_row(self, rowdict: dict, context: ConversionContext) -> None:
        """Add a row to CSV with column layout filtering.

        Args:
            rowdict: Dictionary containing row data
            context: The conversion context

        """
        user_data = context.user_data
        column_layout = user_data["column_layout"]
        inc_item_desc = user_data["inc_item_desc"]
        inc_item_numbers = user_data["inc_item_numbers"]

        column_list = []
        for column in column_layout.split(","):
            column = column.strip()
            if column in ["description", "vendor_item"]:
                if inc_item_desc and column == "description":
                    column_list.append(rowdict.get(column, ""))
                if inc_item_numbers and column == "vendor_item":
                    column_list.append(rowdict.get(column, ""))
            else:
                column_list.append(rowdict.get(column, ""))

        context.csv_writer.writerow(column_list)

    def _should_process_record_type(
        self, record_type: str, context: ConversionContext
    ) -> bool:
        """Only process B records for simplified CSV.

        Args:
            record_type: The type of record
            context: The conversion context

        Returns:
            True only for B records

        """
        return record_type == "B"

    def process_b_record(self, record: EDIRecord, context: ConversionContext) -> None:
        """Process a B record (line item) with optional retail UOM conversion.

        Args:
            record: The B record
            context: The conversion context

        """
        user_data = context.user_data
        fields = dict(record.fields)  # Copy to allow modification

        # Apply retail UOM conversion if enabled
        if user_data["retail_uom"]:
            fields = self._apply_retail_uom_conversion(fields, context)

        # Build row dictionary
        row_dict = {
            "upc_number": fields["upc_number"],
            "qty_of_units": utils.qty_to_int(fields["qty_of_units"]),
            "unit_cost": utils.convert_to_price(fields["unit_cost"]),
            "description": fields["description"],
            "vendor_item": int(fields["vendor_item"].strip()),
        }

        self._add_row(row_dict, context)

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
        return apply_retail_uom(fields, context.upc_lut, upc_target_length=11)


# =============================================================================
# Backward Compatibility Wrapper
# =============================================================================

from .convert_base import create_edi_convert_wrapper

# Auto-generated wrapper using the standard template
edi_convert = create_edi_convert_wrapper(
    SimplifiedCSVConverter, format_name="simplified_csv"
)
