import csv
from datetime import datetime

import utils
from convert_base import CSVConverter, create_edi_convert_wrapper


class FintechConverter(CSVConverter):
    """Converter for Fintech format CSV output.
    
    This converter produces an 11-column CSV file with the following columns:
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
    
    The converter uses database lookups to fetch customer numbers and
    supports A records (headers), B records (line items), and C records
    (charges/adjustments).
    
    Required parameters:
        fintech_division_id: The division ID to include in output rows.
    """

    def __init__(
        self,
        edi_process: str,
        output_filename: str,
        settings_dict: dict,
        parameters_dict: dict,
        upc_lookup: dict,
    ) -> None:
        """Initialize the Fintech converter.
        
        Args:
            edi_process: Path to the input EDI file.
            output_filename: Base path for the output file (without extension).
            settings_dict: Dictionary containing application settings including
                database credentials.
            parameters_dict: Dictionary containing conversion parameters.
                Must include 'fintech_division_id'.
            upc_lookup: Dictionary mapping item numbers to UPC information.
        """
        super().__init__(
            edi_process, output_filename, settings_dict, parameters_dict, upc_lookup
        )
        self.fintech_division_id = parameters_dict['fintech_division_id']
        self._inv_fetcher = None

    def _uomdesc(self, uommult: int) -> str:
        """Convert unit multiplier to UOM description.
        
        Args:
            uommult: Unit multiplier value from EDI record.
            
        Returns:
            "EA" if multiplier > 1, otherwise "CS".
        """
        if uommult > 1:
            return "EA"
        else:
            return "CS"

    def _get_inv_fetcher(self):
        """Get or create the invoice fetcher for database lookups.
        
        Returns:
            invFetcher instance for database queries.
        """
        if self._inv_fetcher is None:
            self._inv_fetcher = utils.invFetcher(self.settings_dict)
        return self._inv_fetcher

    def _get_vendor_store_id(self, invoice_number: int) -> str:
        """Fetch vendor store ID (customer number) from database.
        
        Args:
            invoice_number: The invoice number to look up.
            
        Returns:
            The customer number associated with the invoice.
        """
        return str(self._get_inv_fetcher().fetch_cust_no(invoice_number))

    def initialize_output(self) -> None:
        """Initialize the CSV output file with headers.
        
        Opens the output file and writes the 11-column header row.
        """
        super().initialize_output()
        self.write_header([
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
            "unit_price"
        ])

    def process_record_a(self, record: dict) -> None:
        """Process an A record (invoice header).
        
        Stores the A record for use when processing B and C records.
        The A record contains invoice-level information like invoice
        number and date.
        
        Args:
            record: Dictionary containing parsed A record fields.
        """
        # A record is already stored in self.current_a_record by base class
        # No additional processing needed for Fintech format
        pass

    def process_record_b(self, record: dict) -> None:
        """Process a B record (line item).
        
        Writes a row to the CSV with line item details including
        invoice info from the stored A record, quantity, UPC codes,
        description, and unit price.
        
        Args:
            record: Dictionary containing parsed B record fields.
        """
        if self.current_a_record is None:
            return

        try:
            invoice_number = int(self.current_a_record['invoice_number'])
            vendor_item = int(record['vendor_item'])
            upc_data = self.upc_lookup.get(vendor_item, ["", "", ""])

            self.write_row([
                self.fintech_division_id,
                invoice_number,
                utils.datetime_from_invtime(
                    self.current_a_record['invoice_date']
                ).strftime("%m/%d/%Y"),
                self._get_vendor_store_id(invoice_number),
                self.qty_to_int(record['qty_of_units']),
                self._uomdesc(int(record['unit_multiplier'])),
                record['vendor_item'],
                upc_data[1],
                upc_data[2],
                record['description'],
                self.convert_to_price(record['unit_cost'])
            ])
        except (ValueError, KeyError) as e:
            print(f"Error processing B record: {e}")

    def process_record_c(self, record: dict) -> None:
        """Process a C record (charge/adjustment).
        
        Writes a row to the CSV with charge information including
        invoice info from the stored A record and charge details.
        
        Args:
            record: Dictionary containing parsed C record fields.
        """
        if self.current_a_record is None:
            return

        try:
            invoice_number = int(self.current_a_record['invoice_number'])

            self.write_row([
                self.fintech_division_id,
                invoice_number,
                utils.datetime_from_invtime(
                    self.current_a_record['invoice_date']
                ).strftime("%m/%d/%Y"),
                self._get_vendor_store_id(invoice_number),
                1,
                "EA",
                0,
                "",
                "",
                record['description'],
                self.convert_to_price(record['amount'])
            ])
        except (ValueError, KeyError) as e:
            print(f"Error processing C record: {e}")

    def finalize_output(self) -> str:
        """Finalize the output and return the output filename.
        
        Returns:
            The path to the generated CSV file.
        """
        return super().finalize_output()


# Backward-compatible wrapper function
edi_convert = create_edi_convert_wrapper(FintechConverter)
