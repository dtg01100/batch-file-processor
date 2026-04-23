"""EStore E-Invoice CSV EDI Converter - Refactored to use Template Method Pattern.

This module converts EDI files to EStore E-Invoice CSV format with support for
complex "shipper mode" handling. It has been refactored to use the BaseEDIConverter
base class while maintaining the exact same behavior and output format.

The converter features:
- Shipper mode: Parent items with child components
- Row buffering with deferred writing
- Trailer records with invoice totals
- UPC lookup from the provided lookup table
- Date formatting

Shipper Mode Logic:
    When parent_item_number == vendor_item, the item is a "shipper" parent.
    Child items (sharing the same parent_item_number) are marked with Detail Type "C".
    The parent item is marked with Detail Type "D" and its quantity is set to
    the count of child items when leaving shipper mode.

Output Format:
    Header records (H) with store/vendor/invoice info
    Detail records (D) for regular items and shipper parents
    Component records (C) for shipper children
    Trailer records (T) with invoice totals

Backward Compatibility:
    The module-level edi_convert() function maintains the same signature
    as before: edi_convert(edi_process, output_filename_initial, settings_dict,
    parameters_dict, upc_lookup)
"""

import csv
import os
from datetime import datetime
from decimal import Decimal

from core import utils
from core.constants import EMPTY_DATE_MMDDYY, EMPTY_PARENT_ITEM
from core.structured_logging import get_logger
from dispatch.converters.convert_base import (
    BaseEDIConverter,
    ConversionContext,
    EDIRecord,
)

logger = get_logger(__name__)


class EStoreEInvoiceConverter(BaseEDIConverter):
    """Converter for EStore E-Invoice CSV format with shipper mode support.

    This class implements the hook methods required by BaseEDIConverter
    to produce EStore-compatible CSV output. It features:
    - Shipper mode handling for parent/child item relationships
    - Row buffering with deferred writing
    - Invoice trailer records with totals
    - UPC lookup from the provided lookup table
    """

    def _initialize_output(self, context: ConversionContext) -> None:
        """Initialize CSV output file, writer, and state.

        Args:
            context: The conversion context

        """
        # Get parameters
        params = context.parameters_dict
        self.store_number = params.get("estore_store_number", "")
        self.vendor_oid = params.get("estore_Vendor_OId", "")
        self.vendor_name = params.get("estore_vendor_NameVendorOID", "")
        self.upc_lookup = context.upc_lut

        # Initialize state
        self.row_dict_list: list[dict] = []
        self.shipper_mode = False
        self.shipper_parent_item = False
        self.shipper_accum: list[Decimal] = []
        self.invoice_accum: list[Decimal] = []
        self.shipper_line_number = 0
        self.invoice_index = 0
        self.output_filename = ""

        # Generate output filename with timestamp
        self.output_filename = os.path.join(
            os.path.dirname(context.output_filename),
            (
                f"eInv{self.vendor_name}"
                f".{datetime.strftime(datetime.now(), '%Y%m%d%H%M%S')}.csv"
            ),
        )

        # Open output file and create CSV writer
        context.output_file = open(
            self.output_filename, "w", newline="", encoding="utf-8"
        )
        context.csv_writer = csv.writer(
            context.output_file, dialect="excel", lineterminator="\r\n"
        )

    def _leave_shipper_mode(self) -> None:
        """Exit shipper mode and update parent item quantity."""
        if self.shipper_mode:
            # Update the parent item's quantity to the count of children.
            # shipper_line_number is set to invoice_index BEFORE the parent row
            # is appended, so row_dict_list[shipper_line_number] IS the parent.
            self.row_dict_list[self.shipper_line_number]["QTY"] = len(
                self.shipper_accum
            )
            self.shipper_accum.clear()
            logger.debug("leave shipper mode")
            self.shipper_mode = False

    def _flush_write_queue(self) -> None:
        """Flush buffered rows to CSV and write trailer."""
        self._leave_shipper_mode()

        for row in self.row_dict_list:
            utils.add_row(self._csv_file, row)

        # Add trailer record if there are invoice totals
        if len(self.invoice_accum) > 0:
            trailer_row = {"Record Type": "T", "Invoice Cost": sum(self.invoice_accum)}
            utils.add_row(self._csv_file, trailer_row)

        self.row_dict_list.clear()
        self.invoice_accum.clear()

    @property
    def _csv_file(self):
        """Get the CSV writer from context."""
        ctx = getattr(self, "_context", None)
        if ctx is not None and ctx.csv_writer is not None:
            return ctx.csv_writer
        return None

    def process_a_record(self, record: EDIRecord, context: ConversionContext) -> None:
        """Process an A record (header), handling shipper mode and creating header row.

        Args:
            record: The A record
            context: The conversion context

        """
        super().process_a_record(record, context)

        # Leave shipper mode if active
        self._leave_shipper_mode()

        # Write trailer for previous invoice if exists
        if len(self.invoice_accum) > 0:
            trailer_row = {
                "Record Type": "T",
                "Invoice Cost": sum(self.invoice_accum),
            }
            self.row_dict_list.append(trailer_row)
            self.invoice_index += 1
            self.invoice_accum.clear()

        # Format invoice date
        if not record.fields["invoice_date"] == EMPTY_DATE_MMDDYY:
            invoice_date = datetime.strptime(record.fields["invoice_date"], "%m%d%y")
            write_invoice_date = datetime.strftime(invoice_date, "%Y%m%d")
        else:
            write_invoice_date = "00000000"

        # Create header row
        row_dict = {
            "Record Type": "H",
            "Store Number": self.store_number,
            "Vendor OId": self.vendor_oid,
            "Invoice Number": record.fields["invoice_number"],
            "Purchase Order": "",
            "Invoice Date": write_invoice_date,
        }
        self.row_dict_list.append(row_dict)
        self.invoice_index += 1

    def process_b_record(self, record: EDIRecord, context: ConversionContext) -> None:
        """Process a B record (line item), handling shipper mode.

        Args:
            record: The B record
            context: The conversion context

        """
        # Lookup UPC from the lookup table
        try:
            upc_entry = self.upc_lookup[int(record.fields["vendor_item"])][1]
        except KeyError:
            logger.debug("cannot find each upc")
            upc_entry = record.fields["upc_number"]

        # Create detail row
        row_dict = {
            "Record Type": "D",
            "Detail Type": "I",
            "Subcategory OId": "",
            "Vendor Item": record.fields["vendor_item"],
            "Vendor Pack": record.fields["unit_multiplier"],
            "Item Description": record.fields["description"].strip(),
            "Item Pack": "",
            "GTIN": upc_entry.strip(),
            "GTIN Type": "",
            "QTY": utils.qty_to_int(record.fields["qty_of_units"]),
            "Unit Cost": utils.convert_to_price_decimal(record.fields["unit_cost"]),
            "Unit Retail": utils.convert_to_price_decimal(
                record.fields["suggested_retail_price"]
            ),
            "Extended Cost": utils.convert_to_price_decimal(record.fields["unit_cost"])
            * utils.qty_to_int(record.fields["qty_of_units"]),
            "NULL": "",
            "Extended Retail": "",
        }

        # Check if this is a shipper parent item
        if record.fields["parent_item_number"] == record.fields["vendor_item"]:
            self._leave_shipper_mode()
            logger.debug("enter shipper mode")
            self.shipper_mode = True
            self.shipper_parent_item = True
            row_dict["Detail Type"] = "D"
            self.shipper_line_number = self.invoice_index

        # Handle shipper mode logic
        if self.shipper_mode:
            if record.fields["parent_item_number"] not in [EMPTY_PARENT_ITEM, "\n"]:
                if self.shipper_parent_item:
                    self.shipper_parent_item = False
                else:
                    row_dict["Detail Type"] = "C"
                    self.shipper_accum.append(
                        utils.convert_to_price_decimal(record.fields["unit_cost"])
                        * utils.qty_to_int(record.fields["qty_of_units"])
                    )
            else:
                try:
                    self._leave_shipper_mode()
                except Exception as error:
                    logger.debug("error leaving shipper mode: %s", error)

        self.row_dict_list.append(row_dict)
        self.invoice_index += 1
        self.invoice_accum.append(row_dict["Extended Cost"])

    def _finalize_output(self, context: ConversionContext) -> None:
        """Finalize output by flushing remaining rows and closing file.

        Args:
            context: The conversion context

        """
        # Flush any remaining rows
        self._flush_write_queue()

        # Close the output file
        if context.output_file is not None:
            context.output_file.close()
            context.output_file = None

    def _get_return_value(self, context: ConversionContext) -> str:
        """Get the return value - the generated filename.

        Args:
            context: The conversion context

        Returns:
            Path to the generated CSV file

        """
        return self.output_filename


# =============================================================================
# Backward Compatibility Wrapper
# =============================================================================

from .convert_base import create_edi_convert_wrapper  # noqa: E402

# Auto-generated wrapper using the standard template
edi_convert = create_edi_convert_wrapper(
    EStoreEInvoiceConverter, format_name="estore_einvoice"
)
