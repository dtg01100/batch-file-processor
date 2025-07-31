# convert_to_csv.py

## Purpose
Converts EDI files to CSV format, supporting various options for record inclusion, formatting, and UPC handling.

## Main Function
- `edi_convert(edi_process, output_filename, settings_dict, parameters_dict, upc_lut)`: Reads an EDI file and writes a CSV file according to the provided parameters.

## Usage
Call `edi_convert(...)` with the EDI file path, output filename, settings, parameters, and UPC lookup table.
