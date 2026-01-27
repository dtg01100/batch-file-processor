import csv
from decimal import Decimal

import utils
from convert_base import CSVConverter, create_edi_convert_wrapper


class CsvConverter(CSVConverter):
    """Converter for standard CSV output format.
    
    This converter produces a 7-column CSV file with the following columns:
    - UPC
    - Qty. Shipped
    - Cost
    - Suggested Retail
    - Description
    - Case Pack
    - Item Number
    
    The converter supports various options including conditional A/C record
    inclusion, UPC override from lookup tables, and retail UOM transformation.
    
    Required parameters:
        calculate_upc_check_digit: Whether to calculate check digits for UPCs.
        include_a_records: Whether to include A records in output.
        include_c_records: Whether to include C records in output.
        include_headers: Whether to include column headers.
        filter_ampersand: Whether to replace & with AND in descriptions.
        pad_a_records: Whether to pad A records with custom value.
        a_record_padding: The padding value for A records.
        override_upc_bool: Whether to override UPCs from lookup table.
        override_upc_level: Which level from lookup table to use.
        override_upc_category_filter: Category filter for UPC override.
        retail_uom: Whether to transform to retail UOM.
    """

    def __init__(
        self,
        edi_process: str,
        output_filename: str,
        settings_dict: dict,
        parameters_dict: dict,
        upc_lookup: dict,
    ) -> None:
        """Initialize the CSV converter.
        
        Args:
            edi_process: Path to the input EDI file.
            output_filename: Base path for the output file (without extension).
            settings_dict: Dictionary containing application settings.
            parameters_dict: Dictionary containing conversion parameters.
            upc_lookup: Dictionary mapping item numbers to UPC information.
        """
        super().__init__(
            edi_process, output_filename, settings_dict, parameters_dict, upc_lookup
        )
        # Extract parameters
        self.calc_upc = parameters_dict.get('calculate_upc_check_digit', 'False')
        self.inc_arec = parameters_dict.get('include_a_records', 'False')
        self.inc_crec = parameters_dict.get('include_c_records', 'False')
        self.inc_headers = parameters_dict.get('include_headers', 'False')
        self.filter_ampersand = parameters_dict.get('filter_ampersand', 'False')
        self.pad_arec = parameters_dict.get('pad_a_records', 'False')
        self.arec_padding = parameters_dict.get('a_record_padding', '')
        self.override_upc = parameters_dict.get('override_upc_bool', False)
        self.override_upc_level = parameters_dict.get('override_upc_level', 1)
        self.override_upc_category_filter = parameters_dict.get('override_upc_category_filter', 'ALL')
        self.retail_uom = parameters_dict.get('retail_uom', False)

    def initialize_output(self) -> None:
        """Initialize the CSV output file with headers if requested."""
        super().initialize_output()
        if self.inc_headers != 'False':
            self.write_header([
                'UPC',
                'Qty. Shipped',
                'Cost',
                'Suggested Retail',
                'Description',
                'Case Pack',
                'Item Number'
            ])

    def _apply_retail_uom(self, record: dict) -> bool:
        """Apply retail UOM transformation to a B record.
        
        Args:
            record: The B record dictionary to transform in place.
            
        Returns:
            True if transformation was successful, False otherwise.
        """
        try:
            item_number = int(record['vendor_item'].strip())
            float(record['unit_cost'].strip())
            test_unit_multiplier = int(record['unit_multiplier'].strip())
            if test_unit_multiplier == 0:
                raise ValueError
            int(record['qty_of_units'].strip())
        except Exception:
            print("cannot parse b record field, skipping")
            return False

        try:
            each_upc_string = self.upc_lookup[item_number][1][:11].ljust(11)
        except KeyError:
            each_upc_string = "           "

        try:
            record['unit_cost'] = str(
                Decimal(
                    (
                        Decimal(record['unit_cost'].strip()) / 100
                    ) / Decimal(record['unit_multiplier'].strip())
                ).quantize(Decimal('.01'))
            ).replace(".", "")[-6:].rjust(6, '0')
            record['qty_of_units'] = str(
                int(record['unit_multiplier'].strip()) * int(record['qty_of_units'].strip())
            ).rjust(5, '0')
            record['upc_number'] = each_upc_string
            record['unit_multiplier'] = '000001'
            return True
        except Exception as error:
            print(error)
            return False

    def _apply_upc_override(self, record: dict) -> None:
        """Apply UPC override from lookup table if configured.
        
        Args:
            record: The B record dictionary to modify in place.
        """
        try:
            vendor_item_int = int(record['vendor_item'].strip())
            if vendor_item_int in self.upc_lookup:
                do_updateupc = False
                if self.override_upc_category_filter == "ALL":
                    do_updateupc = True
                else:
                    if self.upc_lookup[vendor_item_int][0] in self.override_upc_category_filter.split(","):
                        do_updateupc = True
                if do_updateupc:
                    record['upc_number'] = self.upc_lookup[vendor_item_int][self.override_upc_level]
            else:
                record['upc_number'] = ""
        except (KeyError, ValueError):
            record['upc_number'] = ""

    def _process_upc_for_csv(self, upc_string: str) -> tuple[str, bool]:
        """Process UPC string for CSV output.
        
        Args:
            upc_string: The raw UPC string from the record.
            
        Returns:
            Tuple of (processed_upc, is_blank).
        """
        blank_upc = False
        result_upc = ""

        try:
            _ = int(upc_string.rstrip())
        except ValueError:
            blank_upc = True

        if not blank_upc:
            proposed_upc = upc_string.strip()
            if len(str(proposed_upc)) == 12:
                result_upc = str(proposed_upc)
            elif len(str(proposed_upc)) == 11:
                result_upc = str(proposed_upc) + str(utils.calc_check_digit(proposed_upc))
            elif len(str(proposed_upc)) == 8:
                result_upc = str(utils.convert_UPCE_to_UPCA(proposed_upc))

        return result_upc, blank_upc

    def process_record_a(self, record: dict) -> None:
        """Process an A record (invoice header).
        
        Args:
            record: Dictionary containing parsed A record fields.
        """
        if self.inc_arec == 'False':
            return

        if self.pad_arec == 'True':
            cust_vendor = self.arec_padding
        else:
            cust_vendor = record['cust_vendor']

        self.write_row([
            record['record_type'],
            cust_vendor,
            record['invoice_number'],
            record['invoice_date'],
            record['invoice_total']
        ])

    def process_record_b(self, record: dict) -> None:
        """Process a B record (line item).
        
        Args:
            record: Dictionary containing parsed B record fields.
        """
        # Apply retail UOM transformation if enabled
        if self.retail_uom:
            if not self._apply_retail_uom(record):
                return

        # Apply UPC override if enabled
        if self.override_upc:
            self._apply_upc_override(record)

        # Process UPC
        upc_string, blank_upc = self._process_upc_for_csv(record['upc_number'])

        # Format UPC for output
        if self.calc_upc != 'False' and not blank_upc:
            upc_in_csv = "\t" + upc_string
        else:
            upc_in_csv = record['upc_number']

        # Format quantity
        quantity_shipped_in_csv = record['qty_of_units'].lstrip("0")
        if quantity_shipped_in_csv == "":
            quantity_shipped_in_csv = record['qty_of_units']

        # Format cost and retail using base class method
        cost_in_csv = self.convert_to_price(record['unit_cost'])
        suggested_retail_in_csv = self.convert_to_price(record['suggested_retail_price'])

        # Format description with optional ampersand filtering
        if self.filter_ampersand != 'False':
            description_in_csv = record['description'].replace("&", "AND").rstrip(" ")
        else:
            description_in_csv = record['description'].rstrip(" ")

        # Format case pack
        case_pack_in_csv = record['unit_multiplier'].lstrip("0")
        if case_pack_in_csv == "":
            case_pack_in_csv = record['unit_multiplier']

        # Format item number
        item_number_in_csv = record['vendor_item'].lstrip("0")
        if item_number_in_csv == "":
            item_number_in_csv = record['vendor_item']

        self.write_row([
            upc_in_csv,
            quantity_shipped_in_csv,
            cost_in_csv,
            suggested_retail_in_csv,
            description_in_csv,
            case_pack_in_csv,
            item_number_in_csv
        ])

    def process_record_c(self, record: dict) -> None:
        """Process a C record (charge/adjustment).
        
        Args:
            record: Dictionary containing parsed C record fields.
        """
        if self.inc_crec == 'False':
            return

        self.write_row([
            record['record_type'],
            record['charge_type'],
            record['description'],
            record['amount']
        ])


# Backward-compatible wrapper function
edi_convert = create_edi_convert_wrapper(CsvConverter)
