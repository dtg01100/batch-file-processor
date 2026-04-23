"""Jolley Custom CSV EDI Converter - Refactored to use Composition.

This module converts EDI files to Jolley Custom CSV format with database lookups
for customer information. It has been refactored to use:
- BaseEDIConverter base class for template method pattern
- DatabaseConnector for DB connection management
- CustomerLookupService for customer header lookups
- UOMLookupService for UOM resolution
- ItemProcessor for item total and UPC calculations

The converter features:
- Database lookups via QueryRunner for customer information
- Corporate customer fallback logic for ship-to addresses
- UPC code generation with check digit calculation
- UOM (Unit of Measure) lookup from database
- Item total calculations with proper decimal handling
- Date prettification for display

Output Format:
    Multi-section CSV with invoice details, bill/ship addresses,
    and line items with descriptions, UPC, quantities, UOM, prices, and totals.

Differences from Stewarts Custom:
    - No Customer_Store_Number in database query
    - Corporate customer fields fallback to customer fields if None
    - Bill To / Ship To layout swapped
    - Different column layout for line items

Backward Compatibility:
    The module-level edi_convert() function maintains the same signature
    as before: edi_convert(edi_process, output_filename, settings_dict,
    parameters_dict, upc_dict)
"""

import csv
from typing import Any, Optional

from core import utils
from core.utils import prettify_dates
from dispatch.converters.convert_base import (
    BaseEDIConverter,
    ConversionContext,
    EDIRecord,
)
from dispatch.converters.customer_queries import (
    BASIC_CUSTOMER_FIELDS_LIST,
    BASIC_CUSTOMER_QUERY_SQL,
)
from dispatch.converters.mixins import build_jolley_header_dict
from dispatch.services.database_connector import DatabaseConnector
from dispatch.services.item_processing import ItemProcessor
from dispatch.services.uom_lookup_service import UOMLookupService

__all__ = ["CustomerLookupError"]

from core.exceptions import CustomerLookupError
from dispatch.converters.convert_base import create_edi_convert_wrapper
from dispatch.services.customer_lookup_service import CustomerLookupService


class JolleyCustomConverter(BaseEDIConverter):
    """Converter for Jolley Custom CSV format with database lookups.

    Uses composable services for database operations, customer lookups,
    UOM lookups, and item processing.
    """

    def __init__(self):
        """Initialize the converter with service objects."""
        self._db_connector = DatabaseConnector()
        self._customer_service: Optional[CustomerLookupService] = None
        self._uom_service: Optional[UOMLookupService] = None
        self._item_processor = ItemProcessor()
        self._header_a_record: dict[str, str] = {}
        self._header_fields_dict: dict[str, Any] = {}

    def _initialize_output(self, context: ConversionContext) -> None:
        """Initialize CSV output file, writer, and database connection.

        Args:
            context: The conversion context

        """
        self._db_connector.init_connection(context.settings_dict)

        self._customer_service = CustomerLookupService(
            self._db_connector.query_runner, BASIC_CUSTOMER_QUERY_SQL
        )
        self._uom_service = UOMLookupService(self._db_connector.query_runner)

        context.output_file = open(
            context.get_output_path(".csv"), "w", newline="\n", encoding="utf-8"
        )
        context.csv_writer = csv.writer(context.output_file, dialect="unix")

    def process_a_record(self, record: EDIRecord, context: ConversionContext) -> None:
        """Process an A record (header), writing invoice header to CSV.

        Args:
            record: The A record
            context: The conversion context

        """
        super().process_a_record(record, context)
        self._header_a_record = record.fields

        self._customer_service.lookup(record.fields["invoice_number"])
        self._uom_service.init_uom_lookup(record.fields["invoice_number"])

        raw_header_dict = self._customer_service.header_dict
        self._header_fields_dict = build_jolley_header_dict(
            raw_header_dict, BASIC_CUSTOMER_FIELDS_LIST
        )

        csv_writer = context.csv_writer

        csv_writer.writerow(["Invoice Details"])
        csv_writer.writerow([""])
        csv_writer.writerow(
            ["Delivery Date", "Terms", "Invoice Number", "Due Date", "PO Number"]
        )
        csv_writer.writerow(
            [
                prettify_dates(self._header_fields_dict["Invoice_Date"]),
                self._header_fields_dict["Terms_Code"],
                record.fields["invoice_number"],
                prettify_dates(
                    self._header_fields_dict["Invoice_Date"],
                    self._header_fields_dict["Terms_Duration"],
                    -1,
                ),
            ]
        )

        ship_to_segment = [
            str(self._header_fields_dict["Corporate_Customer_Number"])
            + "\n"
            + self._header_fields_dict["Corporate_Customer_Name"]
            + "\n"
            + self._header_fields_dict["Corporate_Customer_Address"]
            + "\n"
            + self._header_fields_dict["Corporate_Customer_Town"]
            + ", "
            + self._header_fields_dict["Corporate_Customer_State"]
            + ", "
            + self._header_fields_dict["Corporate_Customer_Zip"]
            + ", "
            + "\n"
            + "US",
        ]

        csv_writer.writerow(
            [
                "Bill To:",
                str(self._header_fields_dict["Customer_Number"])
                + "\n"
                + self._header_fields_dict["Customer_Name"]
                + "\n"
                + self._header_fields_dict["Customer_Address"]
                + "\n"
                + self._header_fields_dict["Customer_Town"]
                + ", "
                + self._header_fields_dict["Customer_State"]
                + ", "
                + self._header_fields_dict["Customer_Zip"]
                + ", "
                + "\n"
                + "US",
                "Ship To:",
            ]
            + ship_to_segment
        )
        csv_writer.writerow([""])
        csv_writer.writerow(
            ["Description", "UPC #", "Quantity", "UOM", "Price", "Amount"]
        )

    def process_b_record(self, record: EDIRecord, context: ConversionContext) -> None:
        """Process a B record (line item), writing to CSV.

        Args:
            record: The B record
            context: The conversion context

        """
        total_price, qtyint = self._item_processor.convert_to_item_total(
            record.fields["unit_cost"], record.fields["qty_of_units"]
        )
        context.csv_writer.writerow(
            [
                record.fields["description"],
                self._item_processor.generate_full_upc(record.fields["upc_number"]),
                qtyint,
                self._uom_service.get_uom(
                    record.fields["vendor_item"], record.fields["unit_multiplier"]
                ),
                "$" + str(utils.convert_to_price(record.fields["unit_cost"])),
                "$" + str(total_price),
            ]
        )

    def process_c_record(self, record: EDIRecord, context: ConversionContext) -> None:
        """Process a C record (charge/tax), writing to CSV.

        Args:
            record: The C record
            context: The conversion context

        """
        context.csv_writer.writerow(
            [
                record.fields["description"],
                "000000000000",
                1,
                "EA",
                "$" + str(utils.convert_to_price(record.fields["amount"])),
                "$" + str(utils.convert_to_price(record.fields["amount"])),
            ]
        )

    def _finalize_output(self, context: ConversionContext) -> None:
        """Finalize output by writing total row and closing file.

        Args:
            context: The conversion context

        """
        if self._header_a_record:
            context.csv_writer.writerow(
                [
                    "",
                    "",
                    "",
                    "",
                    "Total:",
                    "$"
                    + str(
                        utils.convert_to_price(
                            self._header_a_record["invoice_total"]
                        ).lstrip("0")
                    ),
                ]
            )

        if context.output_file is not None:
            context.output_file.close()
            context.output_file = None

        self._db_connector.close()


edi_convert = create_edi_convert_wrapper(
    JolleyCustomConverter, format_name="jolley_custom"
)
