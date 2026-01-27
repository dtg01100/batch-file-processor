import csv
from decimal import Decimal

import utils
from convert_base import CSVConverter, create_edi_convert_wrapper


class SimplifiedCsvConverter(CSVConverter):
    """Converter for simplified CSV output format with dynamic column layout.
    
    This converter produces a CSV file with configurable columns:
    - upc_number
    - qty_of_units
    - unit_cost
    - description
    - vendor_item
    
    The column layout is controlled by the simple_csv_sort_order parameter,
    and individual columns can be enabled/disabled via include_* parameters.
    
    Required parameters:
        retail_uom: Whether to transform to retail UOM.
        include_headers: Whether to include column headers.
        include_item_numbers: Whether to include item numbers column.
        include_item_description: Whether to include description column.
        simple_csv_sort_order: Comma-separated list of columns in desired order.
    """

    def __init__(
        self,
        edi_process: str,
        output_filename: str,
        settings_dict: dict,
        parameters_dict: dict,
        upc_lookup: dict,
    ) -> None:
        """Initialize the simplified CSV converter.
        
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
        self.retail_uom = parameters_dict.get('retail_uom', False)
        self.inc_headers = parameters_dict.get('include_headers', 'False')
        self.inc_item_numbers = parameters_dict.get('include_item_numbers', False)
        self.inc_item_desc = parameters_dict.get('include_item_description', False)
        self.column_layout = parameters_dict.get('simple_csv_sort_order', 'upc_number,qty_of_units,unit_cost,description,vendor_item')

    def initialize_output(self) -> None:
        """Initialize the CSV output file with headers if requested."""
        # Use minimal quoting for simplified CSV
        self.quoting = csv.QUOTE_MINIMAL
        super().initialize_output()
        
        if self.inc_headers != 'False':
            headers = self._build_row({
                'upc_number': 'UPC',
                'qty_of_units': 'Quantity',
                'unit_cost': 'Cost',
                'description': 'Item Description',
                'vendor_item': 'Item Number',
            })
            self.write_row(headers)

    def _build_row(self, row_dict: dict) -> list:
        """Build a CSV row based on column layout and inclusion settings.
        
        Args:
            row_dict: Dictionary containing all possible column values.
            
        Returns:
            List of values in the order specified by column_layout.
        """
        column_list = []
        for column in self.column_layout.split(","):
            if column in ["description", "vendor_item"]:
                if self.inc_item_desc and column == "description":
                    column_list.append(row_dict[column])
                if self.inc_item_numbers and column == "vendor_item":
                    column_list.append(row_dict[column])
            else:
                column_list.append(row_dict[column])
        return column_list

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

    def process_record_a(self, record: dict) -> None:
        """Process an A record (invoice header).
        
        Args:
            record: Dictionary containing parsed A record fields.
        """
        # Simplified CSV does not include A records
        pass

    def process_record_b(self, record: dict) -> None:
        """Process a B record (line item).
        
        Args:
            record: Dictionary containing parsed B record fields.
        """
        # Apply retail UOM transformation if enabled
        if self.retail_uom:
            if not self._apply_retail_uom(record):
                return

        # Build row dictionary
        try:
            vendor_item_int = int(record['vendor_item'].strip())
        except ValueError:
            print("cannot parse vendor_item as int")
            vendor_item_int = 0

        row_dict = {
            'upc_number': record['upc_number'],
            'qty_of_units': self.qty_to_int(record['qty_of_units']),
            'unit_cost': self.convert_to_price(record['unit_cost']),
            'description': record['description'],
            'vendor_item': vendor_item_int,
        }

        self.write_row(self._build_row(row_dict))

    def process_record_c(self, record: dict) -> None:
        """Process a C record (charge/adjustment).
        
        Args:
            record: Dictionary containing parsed C record fields.
        """
        # Simplified CSV does not include C records
        pass


# Backward-compatible wrapper function
edi_convert = create_edi_convert_wrapper(SimplifiedCsvConverter)
