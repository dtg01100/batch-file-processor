# convert_to_estore_einvoice.py

## Purpose
Converts EDI files to Estore eInvoice CSV format, supporting custom row and shipper handling.

## Main Function
- `edi_convert(edi_process, output_filename_initial, settings_dict, parameters_dict, upc_lookup)`: Converts EDI to Estore eInvoice CSV.

## Usage
Call `edi_convert(...)` with the EDI file, output filename, settings, parameters, and UPC lookup.
