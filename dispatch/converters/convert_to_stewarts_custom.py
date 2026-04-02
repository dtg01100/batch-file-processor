"""Stewarts Custom CSV EDI Converter - Refactored to use Template Method Pattern.

This module converts EDI files to Stewarts Custom CSV format with database lookups
for customer information. It has been refactored to use:
- BaseEDIConverter base class for template method pattern
- DatabaseConnectionMixin for DB connection management
- CustomerLookupMixin for customer header lookups
- UOMLookupMixin for UOM resolution
- ItemProcessingMixin for item total and UPC calculations

The converter features:
- Database lookups via QueryRunner for customer information
- Customer address formatting with corporate/bill-to logic
- UPC code generation with check digit calculation
- UOM (Unit of Measure) lookup from database
- Item total calculations with proper decimal handling
- Date prettification for display

Output Format:
    Multi-section CSV with invoice details, ship/bill addresses,
    and line items with quantities, UOM, prices, and totals.

Backward Compatibility:
    The module-level edi_convert() function maintains the same signature
    as before: edi_convert(edi_process, output_filename, settings_dict,
    parameters_dict, upc_dict)
"""

import csv
from typing import Any

from core import utils
from core.utils import prettify_dates
from dispatch.converters.convert_base import (
    BaseEDIConverter,
    ConversionContext,
    EDIRecord,
)
from dispatch.converters.mixins import (
    STEWARTS_CUSTOMER_FIELDS_LIST,
    STEWARTS_CUSTOMER_QUERY_SQL,
    CustomerLookupMixin,
    DatabaseConnectionMixin,
    ItemProcessingMixin,
    UOMLookupMixin,
)


class StewartsCustomConverter(
    BaseEDIConverter,
    DatabaseConnectionMixin,
    CustomerLookupMixin,
    UOMLookupMixin,
    ItemProcessingMixin,
):
    """Converter for Stewarts Custom CSV format with database lookups.

    Uses shared mixins for database operations, customer lookups,
    UOM lookups, and item processing.
    """

    def _get_customer_query_sql(self) -> str:
        """Return the SQL query template for customer lookup."""
        return STEWARTS_CUSTOMER_QUERY_SQL

    def _get_customer_header_field_names(self) -> list[str]:
        """Return ordered list of field names for customer query results."""
        return list(STEWARTS_CUSTOMER_FIELDS_LIST)

    def _build_customer_header_dict(
        self, header_fields: dict[str, Any], header_fields_list: list[str]
    ) -> dict[str, Any]:
        """Build customer header dictionary from query results."""
        # Convert spaces to underscores in keys for compatibility
        result = {}
        for key, value in header_fields.items():
            new_key = key.replace(" ", "_")
            result[new_key] = value
        return result

    def _initialize_output(self, context: ConversionContext) -> None:
        """Initialize CSV output file, writer, and database connection.

        Args:
            context: The conversion context

        """
        # Initialize database connection using mixin
        self._init_db_connection(context.settings_dict)

        # Initialize state
        self.header_a_record: dict[str, str] = {}

        # Open output file and create CSV writer
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
        self.header_a_record = record.fields

        # Fetch customer data from database using mixin
        self._init_customer_lookup(record.fields["invoice_number"], self.query_object)

        # Fetch UOM lookup data using mixin
        self._init_uom_lookup(record.fields["invoice_number"], self.query_object)

        csv_writer = context.csv_writer

        # Write invoice header section
        csv_writer.writerow(["Invoice Details"])
        csv_writer.writerow([""])
        csv_writer.writerow(
            ["Delivery Date", "Terms", "Invoice Number", "Due Date", "PO Number"]
        )
        csv_writer.writerow(
            [
                prettify_dates(self.header_fields_dict["Invoice_Date"]),
                self.header_fields_dict["Terms_Code"],
                record.fields["invoice_number"],
                prettify_dates(
                    self.header_fields_dict["Invoice_Date"],
                    self.header_fields_dict["Terms_Duration"],
                    -1,
                ),
            ]
        )

        # Build bill-to segment
        if self.header_fields_dict.get("Corporate_Customer_Number") is not None:
            bill_to_segment = [
                str(self.header_fields_dict["Corporate_Customer_Number"])
                + "\n"
                + self.header_fields_dict["Corporate_Customer_Name"]
                + "\n"
                + self.header_fields_dict["Corporate_Customer_Address"]
                + "\n"
                + self.header_fields_dict["Corporate_Customer_Town"]
                + ", "
                + self.header_fields_dict["Corporate_Customer_State"]
                + ", "
                + self.header_fields_dict["Corporate_Customer_Zip"]
                + ", "
                + "\n"
                + "US",
            ]
        else:
            bill_to_segment = [
                str(self.header_fields_dict["Customer_Number"])
                + "\n"
                + self.header_fields_dict["Customer_Name"]
                + "\n"
                + self.header_fields_dict["Customer_Address"]
                + "\n"
                + self.header_fields_dict["Customer_Town"]
                + ", "
                + self.header_fields_dict["Customer_State"]
                + ", "
                + self.header_fields_dict["Customer_Zip"]
                + ", "
                + "\n"
                + "US",
            ]

        # Write ship-to/bill-to section
        csv_writer.writerow(
            [
                "Ship To:",
                str(self.header_fields_dict["Customer_Number"])
                + " "
                + str(self.header_fields_dict.get("Customer_Store_Number", ""))
                + "\n"
                + self.header_fields_dict["Customer_Name"]
                + "\n"
                + self.header_fields_dict["Customer_Address"]
                + "\n"
                + self.header_fields_dict["Customer_Town"]
                + ", "
                + self.header_fields_dict["Customer_State"]
                + ", "
                + self.header_fields_dict["Customer_Zip"]
                + ", "
                + "\n"
                + "US",
                "Bill To:",
            ]
            + bill_to_segment
        )
        csv_writer.writerow([""])
        csv_writer.writerow(
            [
                "Invoice Number",
                "Store Number",
                "Item Number",
                "Description",
                "UPC #",
                "Quantity",
                "UOM",
                "Price",
                "Amount",
            ]
        )

    def process_b_record(self, record: EDIRecord, context: ConversionContext) -> None:
        """Process a B record (line item), writing to CSV.

        Args:
            record: The B record
            context: The conversion context

        """
        total_price, qtyint = self._convert_to_item_total(
            record.fields["unit_cost"], record.fields["qty_of_units"]
        )
        context.csv_writer.writerow(
            [
                self.header_a_record["invoice_number"],
                self.header_fields_dict.get("Customer_Store_Number", ""),
                record.fields["vendor_item"],
                record.fields["description"],
                self._generate_full_upc(record.fields["upc_number"]),
                qtyint,
                self._get_uom(
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
        # Write total row
        if self.header_a_record:
            context.csv_writer.writerow(
                [
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "Total:",
                    "$"
                    + str(
                        utils.convert_to_price(
                            self.header_a_record["invoice_total"]
                        ).lstrip("0")
                    ),
                ]
            )

        # Close the output file
        if context.output_file is not None:
            context.output_file.close()
            context.output_file = None

        # Close database connection using mixin
        self._close_db_connection()


# =============================================================================
# Backward Compatibility Wrapper
# =============================================================================

from .convert_base import create_edi_convert_wrapper

# Auto-generated wrapper using the standard template
edi_convert = create_edi_convert_wrapper(
    StewartsCustomConverter, format_name="stewarts_custom"
)
