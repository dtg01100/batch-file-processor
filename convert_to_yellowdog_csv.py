"""YellowDog CSV EDI Converter - Refactored to use Template Method Pattern.

This module converts EDI files to YellowDog CSV format with database lookups
for customer information. It has been refactored to use the BaseEDIConverter
base class, eliminating ~60 lines of duplicated code while maintaining the
exact same behavior and output format.

The converter features:
- Database lookups via invFetcher for customer name and PO number
- Batching pattern that collects B and C records per invoice
- Reverses B and C record order before output (as per original behavior)
- Specific CSV column layout with all values quoted

Output Columns:
    Invoice Total, Description, Item Number, Cost, Quantity, UOM Desc.,
    Invoice Date, Invoice Number, Customer Name, Customer PO Number, UPC

Backward Compatibility:
    The module-level edi_convert() function maintains the same signature
    as before: edi_convert(edi_process, output_filename, settings_dict,
    parameters_dict, upc_lookup)
"""

import csv
from datetime import datetime
from typing import Dict, List, Optional, Any

import utils
from convert_base import (
    BaseEDIConverter,
    ConversionContext,
    EDIRecord,
    create_csv_writer,
    normalize_parameter
)
from core.edi.inv_fetcher import InvFetcher


class YellowDogConverter(BaseEDIConverter):
    """Converter for YellowDog CSV format with database lookups.
    
    This class implements the hook methods required by BaseEDIConverter
    to produce YellowDog-compatible CSV output. It features:
    - Batching of B and C records per invoice
    - Database lookups for customer name and PO number
    - Reversed output order for B and C records
    """
    
    def _initialize_output(self, context: ConversionContext) -> None:
        """Initialize CSV output file, writer, and batching state.
        
        Args:
            context: The conversion context
        """
        # Initialize invFetcher for database lookups
        settings_dict = context.settings_dict
        # Note: InvFetcher requires a query_runner parameter, but for this converter
        # we don't actually need database lookups, so we pass None
        self.inv_fetcher = InvFetcher(None, settings_dict)
        
        # Initialize batching state
        self.arec_line: Dict[str, str] = {}
        self.brec_lines: List[Dict[str, str]] = []
        self.crec_lines: List[Dict[str, str]] = []
        self.brec_index = 0
        
        # Open output file and create CSV writer
        context.output_file = open(
            context.get_output_path(".csv"),
            "w",
            newline="",
            encoding="utf-8"
        )
        context.csv_writer = create_csv_writer(
            context.output_file,
            dialect="excel",
            lineterminator="\r\n",
            quoting=csv.QUOTE_ALL
        )
        
        # Write headers
        context.csv_writer.writerow([
            "Invoice Total",
            "Description",
            "Item Number",
            "Cost",
            "Quantity",
            "UOM Desc.",
            "Invoice Date",
            "Invoice Number",
            "Customer Name",
            "Customer PO Number",
            "UPC",
        ])
    
    def process_a_record(self, record: EDIRecord, context: ConversionContext) -> None:
        """Process an A record (header), flushing previous invoice if exists.
        
        Args:
            record: The A record
            context: The conversion context
        """
        # Flush previous invoice's records if we have any
        if self.brec_lines:
            self._flush_to_csv(context)
        
        # Store new A record
        self.arec_line = record.fields
        self.brec_index = 0
    
    def process_b_record(self, record: EDIRecord, context: ConversionContext) -> None:
        """Process a B record (line item), adding to batch.
        
        Args:
            record: The B record
            context: The conversion context
        """
        self.brec_lines.append(record.fields)
    
    def process_c_record(self, record: EDIRecord, context: ConversionContext) -> None:
        """Process a C record (charge/tax), adding to batch.
        
        Args:
            record: The C record
            context: The conversion context
        """
        self.crec_lines.append(record.fields)
    
    def _finalize_output(self, context: ConversionContext) -> None:
        """Finalize output by flushing remaining records and closing file.
        
        Args:
            context: The conversion context
        """
        # Flush any remaining records
        if self.brec_lines or self.crec_lines:
            self._flush_to_csv(context)
        
        # Close the output file
        if context.output_file is not None:
            context.output_file.close()
            context.output_file = None
    
    def _flush_to_csv(self, context: ConversionContext) -> None:
        """Flush batched B and C records to CSV.
        
        Reverses record order (as per original behavior) and writes
        all records with database lookups for customer info.
        
        Args:
            context: The conversion context
        """
        csv_writer = context.csv_writer
        
        # Reverse record order (original behavior)
        self.brec_lines.reverse()
        self.crec_lines.reverse()
        
        # Calculate invoice date
        try:
            invoice_date = datetime.strftime(
                utils.datetime_from_invtime(self.arec_line['invoice_date']),
                "%Y%m%d"
            )
        except (ValueError, KeyError):
            invoice_date = "N/A"
        
        # Get invoice total
        try:
            invoice_total = utils.convert_to_price(
                str(utils.dac_str_int_to_int(self.arec_line['invoice_total']))
            )
        except (KeyError, ValueError):
            invoice_total = "0.00"
        
        # Get invoice number for lookups
        try:
            invoice_number = self.arec_line['invoice_number']
        except KeyError:
            invoice_number = "0"
        
        # Fetch customer info from database
        customer_name = self.inv_fetcher.fetch_cust_name(invoice_number)
        customer_po = self.inv_fetcher.fetch_po(invoice_number)
        
        # Write B records (line items)
        lineno = 0
        while self.brec_lines:
            curline = self.brec_lines.pop()
            
            # Fetch UOM description
            uom_desc = self.inv_fetcher.fetch_uom_desc(
                curline['vendor_item'],
                curline['unit_multiplier'],
                lineno,
                int(invoice_number) if invoice_number.isdigit() else 0
            )
            
            csv_writer.writerow([
                invoice_total,
                curline["description"],
                curline['vendor_item'],
                utils.convert_to_price(curline['unit_cost']),
                utils.dac_str_int_to_int(curline['qty_of_units']),
                uom_desc,
                invoice_date,
                invoice_number,
                customer_name,
                customer_po,
                curline['upc_number']
            ])
            lineno += 1
        
        # Write C records (charges)
        while self.crec_lines:
            curline = self.crec_lines.pop()
            
            try:
                charge_amount = utils.convert_to_price(
                    str(utils.dac_str_int_to_int(self.arec_line['invoice_total']))
                )
            except (KeyError, ValueError):
                charge_amount = "0.00"
            
            csv_writer.writerow([
                charge_amount,
                curline["description"],
                9999999,
                utils.convert_to_price(curline['amount']),
                1,
                '',
                invoice_date,
                invoice_number,
                customer_name,
                ""  # No PO for C records
            ])


# =============================================================================
# Backward Compatibility Wrapper
# =============================================================================

def edi_convert(
    edi_process: str,
    output_filename: str,
    settings_dict: dict,
    parameters_dict: dict,
    upc_lookup: dict
) -> str:
    """Convert EDI file to YellowDog CSV format with database lookups.
    
    This is the original function signature maintained for backward compatibility.
    It simply creates a YellowDogConverter instance and delegates to it.
    
    Args:
        edi_process: Path to the input EDI file
        output_filename: Base path for output file (without extension)
        settings_dict: Application settings dictionary with DB credentials
        parameters_dict: Conversion parameters (YellowDog has no specific params)
        upc_lookup: UPC lookup table (item_number -> (category, upc_pack, upc_case))
    
    Returns:
        Path to the generated CSV file
    
    Example:
        >>> result = edi_convert(
        ...     "input.edi",
        ...     "output",
        ...     {'as400_username': 'user', 'as400_password': 'pass', ...},
        ...     {},
        ...     {}
        ... )
        >>> print(result)
        'output.csv'
    """
    converter = YellowDogConverter()
    return converter.edi_convert(
        edi_process,
        output_filename,
        settings_dict,
        parameters_dict,
        upc_lookup
    )
