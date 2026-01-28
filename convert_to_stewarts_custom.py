"""Converter for Stewarts Custom format CSV output.

This converter produces a multi-section CSV file with the following sections:
- Invoice Details (Delivery Date, Terms, Invoice Number, Due Date, PO Number)
- Ship To and Bill To addresses
- Line items (Invoice Number, Store Number, Item Number, Description, UPC, Quantity, UOM, Price, Amount)

The converter requires database access to fetch customer/salesperson data
and UOM lookups from the AS400 system.

This converter is very similar to JolleyCustomConverter but with different
output layout and additional Store Number column.
"""

import csv
import decimal
from datetime import date, timedelta
from typing import Any, Optional

from dateutil import parser

import utils
from convert_base import DBEnabledConverter, create_edi_convert_wrapper
from query_runner import query_runner


class CustomerLookupError(Exception):
    """Exception raised when customer data cannot be found in database."""

    pass


class StewartsCustomConverter(DBEnabledConverter):
    """Converter for Stewarts Custom format CSV output.

    This converter produces a multi-section CSV file with invoice details,
    shipping/billing addresses, and line item information. It requires
    database connectivity to fetch customer data from AS400.

    Similar to JolleyCustomConverter but with:
    - Additional Customer_Store_Number column
    - Different Bill To/Ship To layout
    - Different line item column order

    The output format includes:
    - Invoice Details section with delivery date, terms, invoice number, due date
    - Ship To and Bill To address sections
    - Line items with invoice number, store number, item number, description,
      UPC, quantity, UOM, price, and amount

    Attributes:
        header_fields_dict: Dictionary containing customer/salesperson data.
        uom_lookup_list: List of UOM data from database for current invoice.
        csv_dialect: Override to use 'unix' dialect for Stewarts format.
        lineterminator: Override to use Unix line endings.
    """

    PLUGIN_ID = "stewarts_custom"
    PLUGIN_NAME = "Stewarts Custom Format"
    PLUGIN_DESCRIPTION = "Converter for Stewarts Custom format CSV output with invoice details, addresses, and line items"

    CONFIG_FIELDS = []

    def __init__(
        self,
        edi_process: str,
        output_filename: str,
        settings_dict: dict,
        parameters_dict: dict,
        upc_lookup: dict,
    ) -> None:
        """Initialize the Stewarts Custom converter.

        Args:
            edi_process: Path to the input EDI file.
            output_filename: Base path for the output file (without extension).
            settings_dict: Dictionary containing application settings including
                database credentials.
            parameters_dict: Dictionary containing conversion parameters.
            upc_lookup: Dictionary mapping item numbers to UPC information.
        """
        super().__init__(
            edi_process, output_filename, settings_dict, parameters_dict, upc_lookup
        )
        self.header_fields_dict: dict = {}
        self.uom_lookup_list: list = []
        self.csv_dialect = "unix"
        self.lineterminator = "\n"
        self.quoting = csv.QUOTE_MINIMAL

    def _fetch_customer_data(self, invoice_number: str) -> dict:
        """Fetch customer/salesperson data from AS400 database.

        Executes a complex SQL query to retrieve invoice header information
        including customer details, salesperson, terms, corporate info,
        and customer store number.

        Args:
            invoice_number: The invoice number to look up.

        Returns:
            Dictionary containing customer/salesperson data.

        Raises:
            CustomerLookupError: If no data found for the invoice.
        """
        header_fields_list = [
            "Salesperson_Name",
            "Invoice_Date",
            "Terms_Code",
            "Terms_Duration",
            "Customer_Status",
            "Customer_Number",
            "Customer_Name",
            "Customer_Store_Number",
            "Customer_Address",
            "Customer_Town",
            "Customer_State",
            "Customer_Zip",
            "Customer_Phone",
            "Customer_Email",
            "Customer_Email_2",
            "Corporate_Customer_Status",
            "Corporate_Customer_Number",
            "Corporate_Customer_Name",
            "Corporate_Customer_Address",
            "Corporate_Customer_Town",
            "Corporate_Customer_State",
            "Corporate_Customer_Zip",
            "Corporate_Customer_Phone",
            "Corporate_Customer_Email",
            "Corporate_Customer_Email_2",
        ]

        query = f"""
    SELECT TRIM(dsadrep.adbbtx) AS "Salesperson Name",
        ohhst.btcfdt AS "Invoice Date",
        TRIM(ohhst.btfdtx) AS "Terms Code",
        dsagrep.agrrnb AS "Terms Duration",
        dsabrep.abbvst AS "Customer Status",
        dsabrep.ababnb AS "Customer Number",
        TRIM(dsabrep.abaatx) AS "Customer Name",
        dsabrep.abaknb AS "Customer Store Number",
        TRIM(dsabrep.ababtx) AS "Customer Address",
        TRIM(dsabrep.abaetx) AS "Customer Town",
        TRIM(dsabrep.abaftx) AS "Customer State",
        TRIM(dsabrep.abagtx) AS "Customer Zip",
        CONCAT(dsabrep.abadnb, dsabrep.abaenb) AS "Customer Phone",
        TRIM(cvgrrep.grm9xt) AS "Customer Email",
        TRIM(cvgrrep.grnaxt) AS "Customer Email 2",
        dsabrep_corp.abbvst AS "Corporate Customer Status",
        dsabrep_corp.ababnb AS "Corporate Customer Number",
        TRIM(dsabrep_corp.abaatx) AS "Corporate Customer Name",
        TRIM(dsabrep_corp.ababtx) AS "Corporate Customer Address",
        TRIM(dsabrep_corp.abaetx) AS "Corporate Customer Town",
        TRIM(dsabrep_corp.abaftx) AS "Corporate Customer State",
        TRIM(dsabrep_corp.abagtx) AS "Corporate Customer Zip",
        CONCAT(dsabrep_corp.abadnb, dsabrep.abaenb) AS "Corporate Customer Phone",
        TRIM(cvgrrep_corp.grm9xt) AS "Corporate Customer Email",
        TRIM(cvgrrep_corp.grnaxt) AS "Corporate Customer Email 2"
        FROM dacdata.ohhst ohhst
            INNER JOIN dacdata.dsabrep dsabrep
                ON ohhst.btabnb = dsabrep.ababnb
            left outer JOIN dacdata.cvgrrep cvgrrep
                ON dsabrep.ababnb = cvgrrep.grabnb
            INNER JOIN dacdata.dsadrep dsadrep
                ON dsabrep.abajcd = dsadrep.adaecd
                inner join dacdata.dsagrep dsagrep
                on ohhst.bta0cd = dsagrep.aga0cd
            LEFT outer JOIN dacdata.dsabrep dsabrep_corp
                ON dsabrep.abalnb = dsabrep_corp.ababnb
            LEFT outer JOIN dacdata.cvgrrep cvgrrep_corp
                ON dsabrep_corp.ababnb = cvgrrep_corp.grabnb
            LEFT outer JOIN dacdata.dsadrep dsadrep_corp
                ON dsabrep_corp.abajcd = dsadrep_corp.adaecd
        WHERE ohhst.bthhnb = {invoice_number.lstrip("0") if invoice_number else "0"}
            """

        header_fields = self.run_query(query)

        if len(header_fields) == 0:
            raise CustomerLookupError(f"Cannot Find Order {invoice_number} In History.")

        header_fields_dict = dict(zip(header_fields_list, header_fields[0]))

        return header_fields_dict

    def _lookup_uom(self, invoice_number: str) -> list:
        """Fetch UOM lookup data from database for the given invoice.

        Args:
            invoice_number: The invoice number to look up.

        Returns:
            List of tuples containing (itemno, uom_mult, uom_code).
        """
        query = f"""
            select distinct bubacd as itemno, bus3qt as uom_mult, buhxtx as uom_code from dacdata.odhst odhst
            where odhst.buhhnb = {invoice_number if invoice_number else "0"}
            """
        return self.run_query(query)

    def _get_uom(self, item_number: str, packsize: str) -> str:
        """Get UOM code for an item number and pack size.

        Searches the UOM lookup list for a matching item number and pack size.

        Args:
            item_number: The vendor item number.
            packsize: The unit multiplier/pack size.

        Returns:
            The UOM code string, or '?' if not found.
        """
        stage_1_list = []
        stage_2_list = []
        try:
            for entry in self.uom_lookup_list:
                if int(entry[0]) == int(item_number):
                    stage_1_list.append(entry)
            for entry in stage_1_list:
                try:
                    if int(entry[1]) == int(packsize):
                        stage_2_list.append(entry)
                except:
                    stage_2_list.append(entry)
                    break
            try:
                return stage_2_list[0][2]
            except IndexError:
                return "?"
        except (ValueError, IndexError) as e:
            print(f"Error in get_uom: {e}")
            return "?"

    @staticmethod
    def _prettify_dates(date_string: str, offset: int = 0, adj_offset: int = 0) -> str:
        """Format date string from AS400 format to display format.

        Args:
            date_string: Date string in AS400 format.
            offset: Days to add to the date.
            adj_offset: Additional adjustment offset.

        Returns:
            Formatted date string (MM/DD/YY), or 'Not Available' if parsing fails.
        """
        try:
            stripped_date_value = str(date_string).strip()
            calculated_date_string = (
                str(int(stripped_date_value[0]) + 19) + stripped_date_value[1:]
            )
            parsed_date_string = parser.isoparse(calculated_date_string).date()
            corrected_date_string = parsed_date_string + timedelta(
                days=int(offset) + adj_offset
            )
            return corrected_date_string.strftime("%m/%d/%y")
        except Exception:
            return "Not Available"

    def _convert_to_item_total(
        self, unit_cost: str, qty: str
    ) -> tuple[decimal.Decimal, int]:
        """Calculate item total from unit cost and quantity.

        Args:
            unit_cost: Unit cost in DAC format.
            qty: Quantity string (may be negative).

        Returns:
            Tuple of (item_total, qty_int).
        """
        qty_int = self.qty_to_int(qty)
        try:
            item_total = decimal.Decimal(self.convert_to_price(unit_cost)) * qty_int
        except (ValueError, decimal.InvalidOperation):
            item_total = decimal.Decimal()
        return item_total, qty_int

    def _write_invoice_sections(self) -> None:
        """Write the invoice header sections to CSV.

        Writes Invoice Details, Ship To, and Bill To sections.
        Note: Stewarts uses Ship To first, then Bill To (opposite of Jolley).
        """
        # Invoice Details section
        self.write_row(["Invoice Details"])
        self.write_row([""])
        self.write_row(
            ["Delivery Date", "Terms", "Invoice Number", "Due Date", "PO Number"]
        )
        self.write_row(
            [
                self._prettify_dates(self.header_fields_dict["Invoice_Date"]),
                self.header_fields_dict["Terms_Code"],
                self.current_a_record["invoice_number"]
                if self.current_a_record
                else "0",
                self._prettify_dates(
                    self.header_fields_dict["Invoice_Date"],
                    self.header_fields_dict["Terms_Duration"],
                    -1,
                ),
            ]
        )

        # Build Bill To segment (uses Corporate info for Stewarts)
        if self.header_fields_dict["Corporate_Customer_Number"] is not None:
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

        # Ship To and Bill To section (Ship To first for Stewarts)
        self.write_row(
            [
                "Ship To:",
                str(self.header_fields_dict["Customer_Number"])
                + " "
                + str(self.header_fields_dict["Customer_Store_Number"])
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

        # Line item headers (different columns for Stewarts)
        self.write_row([""])
        self.write_row(
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

    def initialize_output(self) -> None:
        """Initialize the CSV output file.

        Opens the output file. Headers are written during record processing
        after the A record is encountered.
        """
        super().initialize_output()

    def process_record_a(self, record: dict) -> None:
        """Process an A record (invoice header).

        Fetches customer data from database, loads UOM lookup data,
        and writes the invoice header sections.

        Args:
            record: Dictionary containing parsed A record fields.

        Raises:
            CustomerLookupError: If customer data cannot be found.
        """
        # Fetch customer/salesperson data from database
        self.header_fields_dict = self._fetch_customer_data(record["invoice_number"])

        # Load UOM lookup data
        self.uom_lookup_list = self._lookup_uom(record["invoice_number"])

        # Write invoice header sections
        self._write_invoice_sections()

    def process_record_b(self, record: dict) -> None:
        """Process a B record (line item).

        Writes a line item row with invoice number, store number, item number,
        description, UPC, quantity, UOM, price, and amount.

        Args:
            record: Dictionary containing parsed B record fields.
        """
        total_price, qtyint = self._convert_to_item_total(
            record["unit_cost"], record["qty_of_units"]
        )
        self.write_row(
            [
                self.current_a_record["invoice_number"]
                if self.current_a_record
                else "0",
                self.header_fields_dict["Customer_Store_Number"],
                record["vendor_item"],
                record["description"],
                self.process_upc(record["upc_number"]),
                qtyint,
                self._get_uom(record["vendor_item"], record["unit_multiplier"]),
                "$" + str(self.convert_to_price(record["unit_cost"])),
                "$" + str(total_price),
            ]
        )

    def process_record_c(self, record: dict) -> None:
        """Process a C record (charge/adjustment).

        Writes a charge row with fixed UPC of '000000000000' and UOM of 'EA'.
        Note: Stewarts C records have different columns than B records.

        Args:
            record: Dictionary containing parsed C record fields.
        """
        # C records in Stewarts have fewer columns than B records
        self.write_row(
            [
                record["description"],
                "000000000000",
                1,
                "EA",
                "$" + str(self.convert_to_price(record["amount"])),
                "$" + str(self.convert_to_price(record["amount"])),
            ]
        )

    def finalize_output(self) -> str:
        """Finalize the output and return the output filename.

        Writes the total row before closing.

        Returns:
            The path to the generated CSV file.
        """
        if self.current_a_record:
            # Stewarts has more columns before Total
            self.write_row(
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
                        self.convert_to_price(
                            self.current_a_record["invoice_total"]
                        ).lstrip("0")
                    ),
                ]
            )
        return super().finalize_output()


# Backward-compatible wrapper function
edi_convert = create_edi_convert_wrapper(StewartsCustomConverter)
