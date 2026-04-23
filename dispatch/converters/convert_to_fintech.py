"""Fintech EDI Converter - Refactored to use Template Method Pattern.

This module converts EDI files to Fintech CSV format. It has been refactored
to use the BaseEDIConverter base class, eliminating ~50 lines of duplicated
code while maintaining the exact same behavior and output format.

The converter outputs a CSV with columns:
- Division_id
- invoice_number
- invoice_date
- Vendor_store_id
- quantity_shipped
- Quantity_uom
- item_number
- upc_pack
- upc_case
- product_description
- unit_price

Backward Compatibility:
    The module-level edi_convert() function maintains the same signature
    as before: edi_convert(edi_process, output_filename, settings_dict,
    parameters_dict, upc_lut)
"""

import csv

from core import utils
from core.edi.inv_fetcher import InvFetcher
from core.structured_logging import get_logger
from core.utils import safe_int
from dispatch.converters.convert_base import (
    BaseEDIConverter,
    ConversionContext,
    EDIRecord,
    create_csv_writer,
)

logger = get_logger(__name__)


class FintechConverter(BaseEDIConverter):
    """Converter for Fintech CSV format.

    This class implements the hook methods required by BaseEDIConverter
    to produce Fintech-compatible CSV output.

    The converter uses the following parameters from parameters_dict:
        - fintech_division_id: The division ID to include in output

    It uses utils.invFetcher to look up customer numbers from the database.
    """

    def _initialize_output(self, context: ConversionContext) -> None:
        """Initialize CSV output file and writer.

        Creates the output CSV file with Fintech-specific headers.

        Args:
            context: The conversion context with output_filename

        """
        # Store the division ID in user_data for use in record processing
        context.user_data["fintech_division_id"] = context.parameters_dict.get(
            "fintech_division_id", ""
        )

        # Initialize invoice fetcher for customer number lookups.
        # InvFetcher is used here only for fetch_cust_no(), which retrieves
        # the customer number associated with an invoice. Passing None for
        # query_runner is intentional: this converter doesn't require database
        # lookups beyond customer number, and InvFetcher handles a None
        # query_runner gracefully by returning empty/default values.
        context.user_data["inv_fetcher"] = InvFetcher(None, context.settings_dict)

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

        # Write Fintech header row
        context.csv_writer.writerow(
            [
                "Division_id",
                "invoice_number",
                "invoice_date",
                "Vendor_store_id",
                "quantity_shipped",
                "Quantity_uom",
                "item_number",
                "upc_pack",
                "upc_case",
                "product_description",
                "unit_price",
            ]
        )

    def process_b_record(self, record: EDIRecord, context: ConversionContext) -> None:
        """Process a B record (line item) for Fintech output.

        Writes a CSV row with line item details including UPC lookup
        and customer number retrieval from the database.

        Args:
            record: The B record containing line item fields
            context: The conversion context with arec_header and upc_lut

        """
        # Get the current A record header for invoice context
        arec_header = context.arec_header
        if arec_header is None:
            return  # Can't process B without A

        # Get required values
        fintech_division_id = context.user_data["fintech_division_id"]
        inv_fetcher = context.user_data["inv_fetcher"]

        # Get UPC data from lookup table
        vendor_item = safe_int(record.fields["vendor_item"])
        if vendor_item == 0 and record.fields["vendor_item"]:
            logger.warning(
                "Invalid vendor_item value %r; defaulting to 0",
                record.fields["vendor_item"],
            )
        upc_data = context.upc_lut.get(vendor_item, ("", "", ""))
        upc_pack = upc_data[1] if len(upc_data) > 1 else ""
        upc_case = upc_data[2] if len(upc_data) > 2 else ""

        invoice_number_int = safe_int(arec_header["invoice_number"])
        if invoice_number_int == 0 and arec_header["invoice_number"]:
            logger.warning(
                "Invalid invoice_number value %r; defaulting to 0",
                arec_header["invoice_number"],
            )

        qty_shipped = safe_int(record.fields["qty_of_units"])
        if qty_shipped == 0 and record.fields["qty_of_units"]:
            logger.warning(
                "Invalid qty_of_units value %r; defaulting to 0",
                record.fields["qty_of_units"],
            )

        unit_multiplier = safe_int(record.fields["unit_multiplier"])
        if unit_multiplier == 0 and record.fields["unit_multiplier"]:
            logger.warning(
                "Invalid unit_multiplier value %r; defaulting to 0",
                record.fields["unit_multiplier"],
            )

        # Write the CSV row
        context.csv_writer.writerow(
            [
                fintech_division_id,
                invoice_number_int,
                self._format_invoice_date(arec_header["invoice_date"]),
                inv_fetcher.fetch_cust_no(invoice_number_int),
                qty_shipped,
                self._uomdesc(unit_multiplier),
                record.fields["vendor_item"],
                upc_pack,
                upc_case,
                record.fields["description"],
                utils.convert_to_price(record.fields["unit_cost"]),
            ]
        )

    def process_c_record(self, record: EDIRecord, context: ConversionContext) -> None:
        """Process a C record (charge) for Fintech output.

        Writes a CSV row with charge details. C records are treated as
        line items with item_number=0 and quantity=1.

        Args:
            record: The C record containing charge fields
            context: The conversion context with arec_header

        """
        # Get the current A record header for invoice context
        arec_header = context.arec_header
        if arec_header is None:
            return  # Can't process C without A

        # Get required values
        fintech_division_id = context.user_data["fintech_division_id"]
        inv_fetcher = context.user_data["inv_fetcher"]

        invoice_number_int = safe_int(arec_header["invoice_number"])
        if invoice_number_int == 0 and arec_header["invoice_number"]:
            logger.warning(
                "Invalid invoice_number value %r; defaulting to 0",
                arec_header["invoice_number"],
            )

        # Write the CSV row for charge
        context.csv_writer.writerow(
            [
                fintech_division_id,
                invoice_number_int,
                self._format_invoice_date(arec_header["invoice_date"]),
                inv_fetcher.fetch_cust_no(invoice_number_int),
                1,
                "EA",
                0,
                "",
                "",
                record.fields["description"],
                utils.convert_to_price(record.fields["amount"]),
            ]
        )

    @staticmethod
    def _uomdesc(uommult: int) -> str:
        """Convert unit of measure multiplier to UOM description.

        Args:
            uommult: The unit multiplier value (number of units per case).

        Returns:
            "EA" (each) if multiplier > 1, "CS" (case) otherwise.

        """
        if uommult > 1:
            return "EA"
        else:
            return "CS"

    @staticmethod
    def _format_invoice_date(inv_date: str) -> str:
        """Format invoice date from MMDDYY to MM/DD/YYYY.

        Args:
            inv_date: Date string in MMDDYY format (e.g., "011524" for Jan 15, 2024).

        Returns:
            Formatted date string in MM/DD/YYYY format (e.g., "01/15/2024").

        Raises:
            ValueError: If the date string cannot be parsed as MMDDYY.

        """
        return utils.datetime_from_invtime(inv_date).strftime("%m/%d/%Y")


# =============================================================================
# Backward Compatibility Wrapper
# =============================================================================

from .convert_base import create_edi_convert_wrapper  # noqa: E402

# Auto-generated wrapper using the standard template
edi_convert = create_edi_convert_wrapper(FintechConverter, format_name="fintech")
