# convert_to_estore_einvoice_generic.py

## Purpose
Converts EDI files to a generic Estore eInvoice CSV format, using database lookups for additional information.

## Main Classes/Functions
- `invFetcher`: Helper class for database queries related to invoices.
- `edi_convert(...)`: Main function to convert EDI to Estore eInvoice Generic CSV.

## Usage
Call `edi_convert(...)` with the EDI file, output filename, settings, parameters, and UPC lookup.
