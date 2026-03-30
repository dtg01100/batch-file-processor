"""EStore E-Invoice Generic CSV EDI Converter - Refactored to use Template Method Pattern.

This module converts EDI files to EStore E-Invoice Generic CSV format with support for
complex "shipper mode" handling and database lookups for PO numbers and UOM descriptions.
It has been refactored to use the BaseEDIConverter base class while maintaining the
exact same behavior and output format.

The converter features:
- Shipper mode: Parent items with child components
- Database lookups via invFetcher for PO numbers and UOM descriptions
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
    The invFetcher class provides cached database lookups for:
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
    as before: edi_convert(edi_process, output_filename_initial, settings_dict,
    parameters_dict, upc_lookup)

    The invFetcher class is also preserved for external use.
"""

import csv
import os
from datetime import datetime
from decimal import Decimal
from typing import Any

from core import utils
from core.database import create_query_runner
from core.edi.inv_fetcher import InvFetcher
from core.structured_logging import get_logger
from dispatch.converters.convert_base import (
    BaseEDIConverter,
    ConversionContext,
    EDIRecord,
)

logger = get_logger(__name__)


class invFetcher:
    """Adapter wrapping core InvFetcher for backward compatibility.

    This class provides the same interface as the original invFetcher
    while delegating to the core.edi.inv_fetcher.InvFetcher implementation.
    Uses dependency injection internally for better testability.

    Attributes:
        settings: Database connection settings
        _fetcher: The underlying InvFetcher instance

    """

    def __init__(self, settings_dict: dict[str, Any]) -> None:
        """Initialize the invoice fetcher adapter.

        Args:
            settings_dict: Dictionary containing database connection settings.
                Must include: as400_username, as400_password, as400_address

        """
        self.settings = settings_dict
        # Create a new QueryRunner for the core InvFetcher
        ssh_key_filename = self.settings.get("ssh_key_filename", "")
        runner = create_query_runner(
            username=self.settings["as400_username"],
            password=self.settings["as400_password"],
            dsn=self.settings["as400_address"],
            database="QGPL",
            ssh_key_filename=ssh_key_filename if ssh_key_filename else None,
        )
        # Create adapter for the core InvFetcher's protocol
        self._fetcher = InvFetcher(runner, settings_dict)

    @property
    def last_invoice_number(self):
        """Forward to core fetcher for compatibility."""
        return self._fetcher.last_invoice_number

    @property
    def uom_lut(self):
        """Forward to core fetcher for compatibility."""
        return self._fetcher.uom_lut

    @property
    def last_invno(self):
        """Forward to core fetcher for compatibility."""
        return self._fetcher.last_invno

    @property
    def po(self):
        """Forward to core fetcher for compatibility."""
        return self._fetcher.po

    @property
    def cust(self):
        """Forward to core fetcher's custname for compatibility."""
        return self._fetcher.custname

    def fetch_po(self, invoice_number: str) -> str:
        """Fetch PO number for an invoice, with caching.

        Args:
            invoice_number: The invoice number to look up (as string)

        Returns:
            The PO number string

        """
        return self._fetcher.fetch_po(int(invoice_number))

    def fetch_cust(self, invoice_number: str) -> str:
        """Fetch customer name for an invoice.

        Args:
            invoice_number: The invoice number to look up

        Returns:
            The customer name string

        """
        return self._fetcher.fetch_cust_name(int(invoice_number))

    def fetch_uom_desc(self, itemno: str, uommult: str, lineno: int, invno: str) -> str:
        """Fetch UOM description for an item.

        Args:
            itemno: The item number
            uommult: The UOM multiplier
            lineno: The line number
            invno: The invoice number

        Returns:
            The UOM description string (e.g., 'HI', 'LO', or specific UOM)

        """
        return self._fetcher.fetch_uom_desc(
            int(itemno), int(uommult), lineno, int(invno)
        )


class EStoreEInvoiceGenericConverter(BaseEDIConverter):
    """Converter for EStore E-Invoice Generic CSV format with shipper mode support.

    This class implements the hook methods required by BaseEDIConverter
    to produce EStore Generic-compatible CSV output. It features:
    - Shipper mode handling for parent/child item relationships
    - Database lookups via invFetcher for PO numbers
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
        # Get parameters
        params = context.parameters_dict
        self.store_number = params["estore_store_number"]
        self.vendor_oid = params["estore_Vendor_OId"]
        self.vendor_name = params["estore_vendor_NameVendorOID"]
        self.c_record_oid = params.get("estore_c_record_OID", "")
        self.upc_lookup = context.upc_lut

        # Initialize invFetcher for database lookups
        self.inv_fetcher = invFetcher(context.settings_dict)

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
            f"eInv{self.vendor_name}.{datetime.strftime(datetime.now(), '%Y%m%d%H%M%S')}.csv",
        )

        # Open output file and create CSV writer
        context.output_file = open(
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
        from dispatch.converters.convert_base import ConversionContext

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
        if len(self.invoice_accum) > 0:
            self.invoice_index += 1
            self.invoice_accum.clear()

        # Format invoice date
        if not record.fields["invoice_date"] == "000000":
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
                record.fields["invoice_number"]
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
            if record.fields["parent_item_number"] not in ["000000", "\n"]:
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
        return self.output_filename


# =============================================================================
# Backward Compatibility Wrapper
# =============================================================================


def edi_convert(
    edi_process: str,
    output_filename_initial: str,
    settings_dict: dict[str, Any],
    parameters_dict: dict[str, Any],
    upc_lookup: dict[int, tuple],
) -> str:
    """Convert EDI file to EStore E-Invoice Generic CSV format.

    This is the original function signature maintained for backward compatibility.
    It simply creates an EStoreEInvoiceGenericConverter instance and delegates to it.

    Args:
        edi_process: Path to the input EDI file
        output_filename_initial: Base path for output file (directory used for output)
        settings_dict: Application settings dictionary with DB credentials
        parameters_dict: Conversion parameters with estore_store_number,
                         estore_Vendor_OId, estore_vendor_NameVendorOID,
                         and estore_c_record_OID
        upc_lookup: UPC lookup table (item_number -> (category, upc_pack, upc_case))

    Returns:
        Path to the generated CSV file with eInv prefix and timestamp

    Example:
        >>> result = edi_convert(
        ...     "input.edi",
        ...     "/output/path/prefix",
        ...     {'as400_username': 'user', 'as400_password': 'pass', ...},
        ...     {
        ...         'estore_store_number': '001',
        ...         'estore_Vendor_OId': 'VENDOR123',
        ...         'estore_vendor_NameVendorOID': 'TestVendor',
        ...         'estore_c_record_OID': 'CHARGE001'
        ...     },
        ...     {123456: ('CAT1', '012345678905', '012345678900')}
        ... )
        >>> print(result)
        '/output/path/eInvTestVendor.20240101120000.csv'

    """
    converter = EStoreEInvoiceGenericConverter()
    return converter.edi_convert(
        edi_process, output_filename_initial, settings_dict, parameters_dict, upc_lookup
    )
