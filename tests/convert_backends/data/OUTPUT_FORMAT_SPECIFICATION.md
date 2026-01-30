# Convert Plugin Output Format Specification

This document describes the official output formats for each convert plugin. These formats match the git master/production versions.

## Overview

Each convert plugin transforms EDI (Electronic Data Interchange) input files into specific output formats for different customer systems.

---

## CSV Plugin ([`convert_to_csv.py`](../../../convert_to_csv.py))

**Output Format**: Comma-Separated Values (CSV)
**File Extension**: `.csv`
**Default Delimiter**: Comma (`,`) with tab-separated values in UPC column

### Columns

| Position | Column Name | Description | Data Type |
|----------|-------------|-------------|-----------|
| 1 | `upc_number` | UPC code (may be empty if not in lookup table) | String |
| 2 | `qty_of_units` | Quantity of units | Integer |
| 3 | `unit_cost` | Unit cost (format: `0.` for zero, `X.XX` for values) | Decimal |
| 4 | `description` | Product description | String |
| 5 | `vendor_item` | Vendor item number | String |

### Example Output

```csv
012345678901,10,5.99,Product Description,123456
098765432101,20,12.99,Another Product,987654
,5,0.,Description for item not in lookup,111111
```

### Settings Effects

| Setting | Effect on Output |
|---------|------------------|
| `include_headers` | Adds header row with column names |
| `include_a_records` | Includes invoice header (A) records with blank UPC |
| `include_c_records` | Includes charge/tax (C) records with `upc_number=TAB` |
| `override_upc_bool` | Applies UPC lookup (always applied in master) |
| `calculate_upc_check_digit` | Calculates check digit for 11-digit UPCs |
| `filter_ampersand` | Replaces `&` with `AND` in descriptions |

### Special Behaviors

- **Empty UPC**: Items not found in UPC lookup table have empty `upc_number`
- **Price Format**: Zero prices show as `0.` (not `0.00`)
- **UPC Column**: When `calculate_upc_check_digit` is True, UPC is prefixed with tab (`\t`)

---

## Scannerware Plugin ([`convert_to_scannerware.py`](../../../convert_to_scannerware.py))

**Output Format**: Fixed-width text
**File Extension**: `.txt`
**Encoding**: ASCII

### Record Structure

Each line is exactly 70 characters (fixed-width):

| Position | Field | Length | Description |
|----------|-------|--------|-------------|
| 1-6 | Vendor/Customer Code | 6 | Padded with zeros or custom value |
| 7-16 | Invoice Number | 10 | Sequential number + "01" suffix |
| 17-24 | Invoice Date | 8 | MMDDYYYY format |
| 25-36 | UPC | 12 | Product UPC code |
| 37-46 | Quantity | 10 | Leading zeros |
| 47-56 | Unit Cost | 10 | Leading zeros, 4 decimal places |
| 57-66 | Pack Size | 10 | Leading zeros |
| 67-70 | Extra | 4 | Reserved |

### Example Output

```
00000100001010112022012345678901000000001000005990000000001
0000010000101011202209876543210000000020000012990000000001
000000000010101120221111111111000000005000000000000000001
```

### Settings Effects

| Setting | Effect on Output |
|---------|------------------|
| `pad_a_records` | Replaces vendor code with `a_record_padding` value |
| `append_a_records` | Appends `a_record_append_text` to each line |
| `force_txt_file_ext` | Forces `.txt` extension on output filename |
| `invoice_date_offset` | Adds/subtracts days from invoice date |

### Special Behaviors

- **Invoice Numbering**: Sequential numbering (00001, 00002, etc.) with "01" suffix
- **Zero Vendor**: When not using padding, vendor field is "000000"
- **Date Format**: MMDDYYYY (can be offset with `invoice_date_offset`)

---

## Simplified CSV Plugin ([`convert_to_simplified_csv.py`](../../../convert_to_simplified_csv.py))

**Output Format**: Comma-Separated Values (CSV)
**File Extension**: `.csv`

### Default Columns

| Position | Column Name | Description |
|----------|-------------|-------------|
| 1 | `upc_number` | UPC code |
| 2 | `qty_of_units` | Quantity |
| 3 | `unit_cost` | Unit cost |
| 4 | `description` | Product description |
| 5 | `vendor_item` | Vendor item number |

### Column Order Customization

The `simple_csv_sort_order` setting controls column order. Default: `upc_number,qty_of_units,unit_cost,description,vendor_item`

### Example Output

```csv
012345678901,10,5.99,Product Description,123456
098765432101,20,12.99,Another Product,987654
```

### Settings Effects

| Setting | Effect on Output |
|---------|------------------|
| `include_headers` | Adds header row |
| `include_item_numbers` | Includes `vendor_item` column |
| `include_item_description` | Includes `description` column |
| `retail_uom` | Transforms quantities to retail UOM |
| `simple_csv_sort_order` | Defines column order |

---

## eStore eInvoice Plugin ([`convert_to_estore_einvoice.py`](../../../convert_to_estore_einvoice.py))

**Output Format**: CSV with dynamic filename
**File Extension**: `.csv`
**Filename Format**: `Invoice_{shipper_name}_{vendor_OID}_{date}_{invoice_number}.csv`

### Columns

| Position | Column Name | Description |
|----------|-------------|-------------|
| 1 | Store Number | From `estore_store_number` setting |
| 2 | Vendor OID | From `estore_Vendor_OId` setting |
| 3 | Invoice Number | From EDI A record |
| 4 | Invoice Date | From EDI A record (YYYYMMDD) |
| 5 | UPC | Product UPC |
| 6 | Description | Product description |
| 7 | Quantity | Quantity shipped |
| 8 | Unit Cost | Cost per unit |
| 9 | Extended Cost | Quantity × Unit Cost |

### Example Output

```csv
12345,67890,INV00001,20220112,012345678901,Product Description,10,5.99,59.90
12345,67890,INV00001,20220112,098765432101,Another Product,20,12.99,259.80
```

### Settings Effects

| Setting | Effect on Output |
|---------|------------------|
| `estore_store_number` | Store number column value (required) |
| `estore_Vendor_OId` | Vendor OID column value (required) |
| `estore_vendor_NameVendorOID` | Used in filename (required) |

### Filename Generation

```
Invoice_{shipper_name}_{vendor_OID}_{YYYYMMDD}_{invoice_number}.csv
```

Example: `Invoice_TestVendor_67890_20220112_INV00001.csv`

---

## Format Comparison Summary

| Plugin | Format | Structure | Key Identifier |
|--------|--------|-----------|----------------|
| CSV | CSV | Flexible columns | UPC column with possible tab prefix |
| Scannerware | Fixed-width | 70 chars/line | Sequential invoice numbers |
| Simplified CSV | CSV | Configurable columns | Column order customization |
| eStore eInvoice | CSV | Dynamic filename | Filename contains metadata |

---

## Testing Output Formats

To verify output format against baselines:

```bash
source .venv/bin/activate
pytest tests/convert_backends/test_parity_verification.py -v
```

To view a baseline example:

```bash
cat tests/convert_backends/baselines/csv/basic_edi_99914b93.csv
cat tests/convert_backends/baselines/scannerware/basic_edi_99914b93.txt
```

## Related Documentation

- [`EDI_FORMAT_SPECIFICATION.md`](./EDI_FORMAT_SPECIFICATION.md) - Input EDI format
- [`PARITY_VERIFICATION.md`](../../PARITY_VERIFICATION.md) - Parity testing guide
