# convert_to_jolley_custom.py

## Purpose
Converts EDI files to a custom Jolley CSV format, using database queries for customer and item details.

## Main Classes/Functions
- `CustomerLookupError`: Exception for customer lookup failures.
- `edi_convert(...)`: Main function to convert EDI to Jolley custom CSV.

## Usage
Call `edi_convert(...)` with the EDI file, output filename, settings, parameters, and UPC dictionary.
