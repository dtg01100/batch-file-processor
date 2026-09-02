"""EStore E-Invoice Generic CSV EDI Converter
- Refactored to use Template Method Pattern.

This module converts EDI files to EStore E-Invoice Generic CSV format
with support for complex "shipper mode" handling and database lookups
for PO numbers and UOM descriptions.
It has been refactored to use the BaseEDIConverter base class while
maintaining the
exact same behavior and output format.

The converter features:
- Shipper mode: Parent items with child components
- Database lookups via InvFetcher for PO numbers and UOM descriptions
- Row buffering with deferred writing
- C record (charge) processing with configurable OID
- CSV header row with column names
- Header dict merging with detail rows

Shipper Mode Logic:
    When parent_item_number == vendor_item, the item is a "shipper" parent.
    Child items (sharing the same parent_item_number) are marked with Detail Type "C".
    The parent item is marked with Detail Type "D" and its quantity is set to
    the count of child items when leaving shipper mode.

Database Lookups:
    The InvFetcher class provides cached database lookups for:
    - PO numbers by invoice number
    - Customer names by invoice number
    - UOM descriptions by item number and multiplier

Output Format:
    CSV with header row, followed by data rows containing:
    Store #, Vendor, Invoice #, PO #, Invoice Date, Total Cost,
    Detail Type, Subcategory, Vendor Item #, Vendor Pack,
    Item Description, Pack, GTIN/PLU, GTIN Type, Quantity,
    Unit Cost, Unit Retail, Extended Cost, Extended Retail

Backward Compatibility:
    The module-level edi_convert() function maintains the same signature
    as before: edi_convert(edi_process, output_filename, settings_dict,
    parameters_dict, upc_lookup)
"""

CONVERTER_METADATA = {
    "format_name": "estore_einvoice_generic",
    "display_name": "eStore_eInvoice_Generic",
    "description": "Convert EDI to EStore E-Invoice Generic CSV format",
    "module_name": "webapp.pipeline.converters.convert_to_estore_einvoice_generic",
}


import csv
import os
from datetime import datetime
from decimal import Decimal
from typing import Any

from core import utils
from core.constants import EMPTY_DATE_MMDDYY, EMPTY_PARENT_ITEM
from core.edi.inv_fetcher import InvFetcher
from core.structured_logging import get_logger
from webapp.pipeline.converters.convert_base import (
    BaseEDIConverter,
    ConversionContext,
    EDIRecord,
    make_edi_convert,
)
from webapp.pipeline.converters.converters_config import (
    EStoreEInvoiceGenericConverterConfig,
)

logger = get_logger(__name__)


class EStoreEInvoiceGenericConverter(BaseEDIConverter):
    """Converter for EStore E-Invoice Generic CSV format with shipper mode support.

    This class implements the hook methods required by BaseEDIConverter
    to produce EStore Generic-compatible CSV output. It features:
    - Shipper mode handling for parent/child item relationships
    - Database lookups via InvFetcher for PO numbers
    - Row buffering with deferred writing
    - C record processing with configurable OID
    - CSV header row
    - Header dict merging with detail rows
    """

    def _initialize_output(self, context: ConversionContext) -> None:
        """Initialize CSV output file, writer, and state.

        Args:
            context: The conversion context

        """
        # Phase 11.x: typed config from parameters_dict.
        config = EStoreEInvoiceGenericConverterConfig.from_parameters(
            context.parameters_dict
        )
        self.store_number = config.store_number
        self.vendor_oid = config.vendor_oid
        self.vendor_name = config.vendor_name
        self.c_record_oid = config.c_record_oid
        self.upc_lookup = context.upc_lut

        # Initialize InvFetcher for database lookups
        from core.database.query_runner import create_query_runner_from_settings

        try:
            runner = create_query_runner_from_settings(context.settings_dict)
        except ValueError:
            runner = None
        self.inv_fetcher = InvFetcher(runner, context.settings_dict)

        # Initialize state
        self.row_dict_list: list[dict] = []
        self.shipper_mode = False
        self.shipper_parent_item = False
        self.shipper_accum: list[Decimal] = []
        self.invoice_accum: list[Decimal] = []
        self.shipper_line_number = 0
        self.invoice_index = 0
        self.row_dict_header: dict[str, Any] = {}
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
        context.output_file = open(  # noqa: SIM115 — lifecycle managed by BaseEDIConverter._finalize_output
            self.output_filename, "w", newline="", encoding="utf-8"
        )
        context.csv_writer = csv.writer(
            context.output_file, dialect="excel", lineterminator="\r\n"
        )

        # Write CSV header row
        context.csv_writer.writerow(
            [
                "Store #",
                "Vendor (OID)",
                "Invoice #",
                "Purchase Order #",
                "Invoice Date",
                "Total Invoice Cost",
                "Detail Type",
                "Subcategory (OID)",
                "Vendor Item #",
                "Vendor Pack",
                "Item Description",
                "Pack",
                "GTIN/PLU",
                "GTIN Type",
                "Quantity",
                "Unit Cost",
                "Unit Retail",
                "Extended Cost",
                "Extended Retail",
            ]
        )

    def _leave_shipper_mode(self) -> None:
        """Exit shipper mode and update parent item quantity."""
        if self.shipper_mode:
            # Update the parent item's quantity to the count of children.
            # A records increment invoice_index but do NOT append to row_dict_list,
            # so row_dict_list[shipper_line_number - 1] IS the parent row.
            self.row_dict_list[self.shipper_line_number - 1]["QTY"] = len(
                self.shipper_accum
            )
            self.shipper_accum.clear()
            logger.debug("leave shipper mode")
            self.shipper_mode = False

    def _flush_write_queue(self) -> None:
        """Flush buffered rows to CSV."""
        self._leave_shipper_mode()

        for row in self.row_dict_list:
            utils.add_row(self._context.csv_writer, row)

        self.row_dict_list.clear()
        self.invoice_accum.clear()

    def edi_convert(
        self,
        edi_process: str,
        output_filename: str,
        settings_dict: dict[str, Any],
        parameters_dict: dict[str, Any],
        upc_lut: dict[int, tuple],
    ) -> str:
        """Override to store context reference."""
        from webapp.pipeline.converters.convert_base import ConversionContext

        context = ConversionContext(
            edi_filename=edi_process,
            output_filename=output_filename,
            settings_dict=settings_dict,
            parameters_dict=parameters_dict,
            upc_lut=upc_lut,
        )
        self._context = context

        # Step 1: Initialize output (hook method)
        self._initialize_output(context)

        try:
            # Step 2: Process EDI file line by line
            self._process_edi_file(context)

            # Step 3: Finalize output (hook method)
            self._finalize_output(context)

        except Exception as e:
            # Ensure cleanup on error
            self._cleanup_on_error(context, e)
            raise

        return self._get_return_value(context)

    def process_a_record(self, record: EDIRecord, context: ConversionContext) -> None:
        """Process an A record (header), handling shipper mode and creating header dict.

        Args:
            record: The A record
            context: The conversion context

        """
        super().process_a_record(record, context)

        # Leave shipper mode if active
        self._leave_shipper_mode()

        # Clear invoice accum for new invoice
        if self.invoice_accum:
            self.invoice_index += 1
            self.invoice_accum.clear()

        # Format invoice date
        if record.fields["invoice_date"] != EMPTY_DATE_MMDDYY:
            invoice_date = datetime.strptime(record.fields["invoice_date"], "%m%d%y")
            write_invoice_date = datetime.strftime(invoice_date, "%Y%m%d")
        else:
            write_invoice_date = "00000000"

        # Create header dict (merged with each detail row)
        self.row_dict_header = {
            "Store Number": self.store_number,
            "Vendor OId": self.vendor_oid,
            "Invoice Number": record.fields["invoice_number"],
            "Purchase Order": self.inv_fetcher.fetch_po(
                int(record.fields["invoice_number"])
            ),
            "Invoice Date": write_invoice_date,
            "Total Invoice Cost": utils.convert_to_price(
                str(utils.dac_str_int_to_int(record.fields["invoice_total"]))
            ),
        }
        self.invoice_index += 1

    def process_b_record(self, record: EDIRecord, context: ConversionContext) -> None:
        """Process a B record (line item), handling shipper mode.

        Args:
            record: The B record
            context: The conversion context

        """
        del context  # unused in this method
        # Lookup UPC from the lookup table
        try:
            upc_entry = self.upc_lookup[int(record.fields["vendor_item"])][1]
        except KeyError:
            logger.debug("cannot find each upc")
            upc_entry = record.fields["upc_number"]

        # Create detail row
        row_dict = {
            "Detail Type": "I",
            "Subcategory OId": "",
            "Vendor Item": record.fields["vendor_item"],
            "Vendor Pack": record.fields["unit_multiplier"],
            "Item Description": record.fields["description"].strip(),
            "Item Pack": "",
            "GTIN": upc_entry.strip(),
            "GTIN Type": "UP",
            "QTY": utils.qty_to_int(record.fields["qty_of_units"]),
            "Unit Cost": utils.convert_to_price_decimal(record.fields["unit_cost"]),
            "Unit Retail": utils.convert_to_price_decimal(
                record.fields["suggested_retail_price"]
            ),
            "Extended Cost": utils.convert_to_price_decimal(record.fields["unit_cost"])
            * utils.qty_to_int(record.fields["qty_of_units"]),
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

        # Merge header with detail row and add to list
        self.row_dict_list.append({**self.row_dict_header, **row_dict})
        self.invoice_index += 1
        self.invoice_accum.append(row_dict["Extended Cost"])

    def process_c_record(self, record: EDIRecord, context: ConversionContext) -> None:
        """Process a C record (charge), writing to CSV.

        Args:
            record: The C record
            context: The conversion context

        """
        del context  # unused in this method
        row_dict = {
            "Detail Type": "S",
            "Subcategory OId": self.c_record_oid,
            "Vendor Item": "",
            "Vendor Pack": 1,
            "Item Description": record.fields["description"].strip(),
            "Item Pack": "",
            "GTIN": "",
            "GTIN Type": "",
            "QTY": 1,
            "Unit Cost": utils.convert_to_price_decimal(record.fields["amount"]),
            "Unit Retail": 0,
            "Extended Cost": utils.convert_to_price_decimal(record.fields["amount"]),
            "Extended Retail": "",
        }

        # Merge header with C record row and add to list
        self.row_dict_list.append({**self.row_dict_header, **row_dict})
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
        del context  # unused in this method
        return self.output_filename


edi_convert = make_edi_convert(EStoreEInvoiceGenericConverter)
