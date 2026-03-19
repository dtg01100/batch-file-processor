# Converter Output Formats Reference

This document provides a comprehensive reference for all converter plugins in the batch-file-processor project, detailing their output formats, configuration options, and behaviors.

## Overview

The batch-file-processor supports **10 converter plugins** that transform EDI input files into various output formats:

| Plugin ID | Name | Output Type | DB Access |
|-----------|------|-------------|-----------|
| `csv` | Standard CSV | CSV file | No |
| `fintech` | Fintech CSV | CSV file | Yes (AS400) |
| `scannerware` | ScannerWare | Fixed-width TXT | No |
| `simplified_csv` | Simplified CSV | CSV file | No |
| `estore_einvoice` | Estore eInvoice | CSV file | No |
| `estore_einvoice_generic` | Estore eInvoice Generic | CSV file | Yes (AS400) |
| `jolley_custom` | Jolley Custom | CSV file | Yes (AS400) |
| `scansheet_type_a` | Scansheet Type A | Excel XLSX | Yes (AS400) |
| `stewarts_custom` | Stewarts Custom | CSV file | Yes (AS400) |
| `yellowdog_csv` | Yellowdog CSV | CSV file | Yes (AS400) |

---

## 1. Standard CSV Converter (`csv`)

**File:** [`convert_to_csv.py`](convert_to_csv.py)

### Output Format

7-column CSV with the following columns:

| Column | Description | Example |
|--------|-------------|---------|
| UPC | Universal Product Code | `012345678901` |
| Qty. Shipped | Number of units shipped | `24` |
| Cost | Unit cost (DAC format) | `15.99` |
| Suggested Retail | Suggested retail price | `19.99` |
| Description | Product description | `Soda Pop 12pk` |
| Case Pack | Units per case | `12` |
| Item Number | Vendor item identifier | `12345` |

### Configuration Options

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `include_headers` | boolean | `False` | Include column headers in output |
| `calculate_upc_check_digit` | boolean | `False` | Calculate and append check digit for 11-digit UPCs |
| `include_a_records` | boolean | `False` | Include invoice header records |
| `include_c_records` | boolean | `False` | Include charge/adjustment records |
| `filter_ampersand` | boolean | `False` | Replace `&` with `AND` in descriptions |
| `pad_a_records` | boolean | `False` | Replace customer/vendor code with padding value |
| `a_record_padding` | string | `""` | Custom value for A record padding |
| `override_upc_bool` | boolean | `False` | Override UPC from database lookup |
| `override_upc_level` | integer | `1` | UPC lookup level (1-4) |
| `override_upc_category_filter` | string | `"ALL"` | Filter UPC override by category |
| `retail_uom` | boolean | `False` | Transform case-level to each-level retail UOM |

### Record Processing

- **A Records:** Optional. Contains: `record_type`, `cust_vendor`, `invoice_number`, `invoice_date`, `invoice_total`
- **B Records:** Core line items. Contains: `upc_number`, `qty_of_units`, `unit_cost`, `suggested_retail_price`, `description`, `unit_multiplier`, `vendor_item`
- **C Records:** Optional. Contains: `record_type`, `charge_type`, `description`, `amount`

---

## 2. Fintech CSV Converter (`fintech`)

**File:** [`convert_to_fintech.py`](convert_to_fintech.py)

### Output Format

11-column CSV with headers:

| Column | Description | Example |
|--------|-------------|---------|
| Division_id | Division identifier (config) | `123` |
| invoice_number | Invoice number | `12345` |
| invoice_date | Invoice date (MM/DD/YYYY) | `01/15/2025` |
| Vendor_store_id | Customer number from database | `98765` |
| quantity_shipped | Quantity shipped | `24` |
| Quantity_uom | Unit of measure (`EA` or `CS`) | `EA` |
| item_number | Vendor item number | `12345` |
| upc_pack | Case UPC from lookup | `012345678901` |
| upc_case | Each UPC from lookup | `012345678902` |
| product_description | Product description | `Soda Pop 12pk` |
| unit_price | Unit cost | `15.99` |

### Configuration Options

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `fintech_division_id` | string | `""` | **Required.** Division identifier for all rows |

### Database Dependencies

Requires AS400 database connection via `invFetcher` for customer number lookups:
- `fetch_cust_no(invoice_number)` - Get customer number for invoice

---

## 3. ScannerWare Converter (`scannerware`)

**File:** [`convert_to_scannerware.py`](convert_to_scannerware.py)

### Output Format

Fixed-width TXT file with line-based records:

#### A Records (Invoice Header)
```
A0000001234501   011525000123.45
```
| Position | Length | Content |
|----------|--------|---------|
| 1 | 1 | Record type (`A`) |
| 2-7 | 6 | Vendor code (padding or `000000`) |
| 8-14 | 7 | Invoice number + suffix (`01`) |
| 15-17 | 3 | Blank spaces |
| 18-23 | 6 | Invoice date (MMDDYY) |
| 24+ | Variable | Invoice total + optional appended text |

#### B Records (Line Items)
```
B01234567890123  Product Descri1234567890  24 001       ```
| Position | Length | Content |
|----------|--------|---------|
| 1 | 1 | Record type (`B`) |
| 2-15 | 14 | UPC (left-justified) |
| 16-40 | 25 | Description (max 25 chars) |
| 41-50 | 10 | Vendor item |
| 51-62 | 12 | Unit cost |
| 63-64 | 2 | Spaces |
| 65-69 | 5 | Unit multiplier |
| 70-74 | 5 | Quantity |
| 75-84 | 10 | Suggested retail |
| 85-87 | 3 | `001` |
| 88+ | 7 | Spaces |

#### C Records (Charges)
```
CCharge Description    12345.67
```
| Position | Length | Content |
|----------|--------|---------|
| 1 | 1 | Record type (`C`) |
| 2-26 | 25 | Description (left-justified) |
| 27-29 | 3 | Spaces |
| 30+ | Variable | Amount |

### Configuration Options

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `pad_a_records` | boolean | `False` | Replace customer/vendor code with padding |
| `a_record_padding` | string | `""` | Custom value for A record padding |
| `append_a_records` | boolean | `False` | Append custom text to A records |
| `a_record_append_text` | string | `""` | Text to append to A records |
| `force_txt_file_ext` | boolean | `False` | Force `.txt` file extension |
| `invoice_date_offset` | integer | `0` | Days to offset invoice date (-365 to 365) |

---

## 4. Simplified CSV Converter (`simplified_csv`)

**File:** [`convert_to_simplified_csv.py`](convert_to_simplified_csv.py)

### Output Format

Dynamic column CSV (configurable layout). Default columns:

| Column | Description | Example |
|--------|-------------|---------|
| UPC | Universal Product Code | `012345678901` |
| Quantity | Number of units | `24` |
| Cost | Unit cost | `15.99` |
| Item Description | Product description | `Soda Pop 12pk` |
| Item Number | Vendor item identifier | `12345` |

### Configuration Options

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `include_headers` | boolean | `False` | Include column headers |
| `include_item_numbers` | boolean | `False` | Include item numbers column |
| `include_item_description` | boolean | `False` | Include description column |
| `retail_uom` | boolean | `False` | Transform to retail UOM |
| `simple_csv_sort_order` | string | See below | Comma-separated column order |

**Default Column Order:**
```
upc_number,qty_of_units,unit_cost,description,vendor_item
```

### Record Processing

- **A Records:** Ignored (no output)
- **B Records:** Core line items with optional retail UOM transformation
- **C Records:** Ignored (no output)

---

## 5. Estore eInvoice Converter (`estore_einvoice`)

**File:** [`convert_to_estore_einvoice.py`](convert_to_estore_einvoice.py)

### Output Format

Dynamic filename: `eInv{vendor_name}.{timestamp}.csv`

CSV with record-type-prefixed rows:

| Record Type | Columns |
|-------------|---------|
| H (Header) | `Record Type`, `Store Number`, `Vendor OId`, `Invoice Number`, `Purchase Order`, `Invoice Date` |
| D (Detail) | `Record Type`, `Detail Type`, `Subcategory OId`, `Vendor Item`, `Vendor Pack`, `Item Description`, `Item Pack`, `GTIN`, `GTIN Type`, `QTY`, `Unit Cost`, `Unit Retail`, `Extended Cost`, `NULL`, `Extended Retail` |
| T (Trailer) | `Record Type`, `Invoice Cost` |

### Detail Type Values

- `I` - Individual item
- `D` - Shipper parent item
- `C` - Shipper child item

### Shipper Mode

Supports shipper/case pack relationships:
- Parent items marked with `Detail Type = D`
- Child items marked with `Detail Type = C`
- Shipper quantity = number of children in shipper

### Configuration Options

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `estore_store_number` | string | `""` | **Required.** Store number |
| `estore_Vendor_OId` | string | `""` | **Required.** Vendor OId |
| `estore_vendor_NameVendorOID` | string | `""` | **Required.** Vendor name/OID for filename |

### Database Dependencies

Uses UPC lookup table for GTIN generation.

---

## 6. Estore eInvoice Generic Converter (`estore_einvoice_generic`)

**File:** [`convert_to_estore_einvoice_generic.py`](convert_to_estore_einvoice_generic.py)

### Output Format

Dynamic filename: `eInv{vendor_name}.{timestamp}.csv`

18-column CSV with explicit headers:

| # | Column | Description |
|---|--------|-------------|
| 1 | Store # | Store number (config) |
| 2 | Vendor (OID) | Vendor OId (config) |
| 3 | Invoice # | Invoice number |
| 4 | Purchase Order # | PO from AS400 lookup |
| 5 | Invoice Date | Invoice date (YYYYMMDD) |
| 6 | Total Invoice Cost | Sum of line items |
| 7 | Detail Type | `I`, `D`, `C`, or `S` |
| 8 | Subcategory (OID) | Configurable OId |
| 9 | Vendor Item # | Vendor item number |
| 10 | Vendor Pack | Unit multiplier |
| 11 | Item Description | Product description |
| 12 | Pack | Item pack size |
| 13 | GTIN/PLU | GTIN from UPC lookup |
| 14 | GTIN Type | `UP` for UPC |
| 15 | Quantity | Quantity shipped |
| 16 | Unit Cost | Unit cost |
| 17 | Unit Retail | Suggested retail |
| 18 | Extended Cost | Quantity × Unit Cost |

### Detail Type Values

- `I` - Individual item
- `D` - Shipper parent item
- `C` - Shipper child item
- `S` - Charge/allowance (C records)

### Configuration Options

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `estore_store_number` | string | `""` | **Required.** Store number |
| `estore_Vendor_OId` | string | `""` | **Required.** Vendor OId |
| `estore_c_record_OID` | string | `""` | OId for C records |
| `estore_vendor_NameVendorOID` | string | `""` | **Required.** Vendor name/OID for filename |

### Database Dependencies

Requires AS400 database connection for:
- PO number lookup (`fetch_po`)
- Customer number lookup (`fetch_cust`)
- UOM description lookup (`fetch_uom_desc`)

---

## 7. Jolley Custom Converter (`jolley_custom`)

**File:** [`convert_to_jolley_custom.py`](convert_to_jolley_custom.py)

### Output Format

Multi-section CSV with structured invoice layout:

#### Invoice Details Section
```
Invoice Details

Delivery Date    Terms    Invoice Number    Due Date    PO Number
01/15/25         NET30    12345             02/14/25
```

#### Bill To / Ship To Section
```
Bill To:                     Ship To:
12345                        12345
Customer Name                Corporate Customer Name
123 Main St                  456 Corporate Blvd
City, State, Zip             City, State, Zip
US                           US
```

#### Line Items Section
```
Description    UPC #         Quantity    UOM    Price    Amount
Product 1      012345678901    24        HI     $15.99   $383.76
Charge 1       000000000000     1        EA     $10.00   $10.00

                                              Total:  $393.76
```

### Database Dependencies

Requires AS400 database connection for:
- Customer/salesperson data lookup
- UOM descriptions lookup
- Invoice terms and corporate customer info

### Queried Fields

| Field Category | Fields |
|----------------|--------|
| Salesperson | `Salesperson_Name` |
| Invoice | `Invoice_Date`, `Terms_Code`, `Terms_Duration` |
| Customer | `Customer_Number`, `Name`, `Address`, `Town`, `State`, `Zip`, `Phone`, `Email` |
| Corporate | Same as customer (fallback to regular customer if not set) |

---

## 8. Scansheet Type A Converter (`scansheet_type_a`)

**File:** [`convert_to_scansheet_type_a.py`](convert_to_scansheet_type_a.py)

### Output Format

Excel XLSX file with embedded UPC-A barcodes:

| Column | Description |
|--------|-------------|
| A | Barcode image (embedded) |
| B | UPC number |
| C | Item number |
| D | Description |
| E | Pack |
| F | U/M |
| G | Qty |
| H | Price |
| I | Retail |

### Features

- **Barcode Generation:** UPC-A barcodes embedded as images
- **Invoice Grouping:** Each invoice preceded by invoice number in column B
- **Automatic Width Adjustment:** Column widths adjusted to fit content

### Database Dependencies

Requires AS400 database connection for item details:

```sql
SELECT buj4cd AS "UPC",
       bubacd AS "Item",
       bufbtx AS "Description",
       ancctx AS "Pack",
       buhxtx AS "U/M",
       bue4qt AS "Qty",
       bud2pr AS "Price",
       bueapr AS "Retail"
FROM dacdata.odhst
INNER JOIN dacdata.dsanrep ON odhst.bubacd = dsanrep.anbacd
WHERE buhhnb = {invoice_number}
  AND bue4qt <> 0
```

---

## 9. Stewarts Custom Converter (`stewarts_custom`)

**File:** [`convert_to_stewarts_custom.py`](convert_to_stewarts_custom.py)

### Output Format

Multi-section CSV similar to Jolley but with different layout:

#### Invoice Details Section
```
Invoice Details

Delivery Date    Terms    Invoice Number    Due Date    PO Number
01/15/25         NET30    12345             02/14/25
```

#### Ship To / Bill To Section (Note: Ship To first!)
```
Ship To:                      Bill To:
12345 Store 001               12345
Customer Name                 Corporate Customer Name
123 Main St                   456 Corporate Blvd
City, State, Zip              City, State, Zip
US                            US
```

#### Line Items Section
```
Invoice Number    Store Number    Item Number    Description    UPC #    Quantity    UOM    Price    Amount
12345             001             12345          Product 1      0123456    24         HI      $15.99   $383.76

                                                                                      Total:  $383.76
```

### Key Differences from Jolley

1. **Store Number Column:** Additional column showing customer store number
2. **Address Order:** Ship To listed first, Bill To second (opposite of Jolley)
3. **Different SQL:** Includes `Customer_Store_Number` field from `dsabrep.abaknb`

### Database Dependencies

Requires AS400 database connection for:
- Customer/salesperson data with store number
- UOM descriptions lookup

---

## 10. Yellowdog CSV Converter (`yellowdog_csv`)

**File:** [`convert_to_yellowdog_csv.py`](convert_to_yellowdog_csv.py)

### Output Format

11-column CSV with headers:

| Column | Description | Example |
|--------|-------------|---------|
| Invoice Total | Total invoice cost | `$1234.56` |
| Description | Item/charge description | `Soda Pop 12pk` |
| Item Number | Vendor item number | `12345` |
| Cost | Unit cost | `15.99` |
| Quantity | Quantity shipped | `24` |
| UOM Desc. | Unit of measure description | `HI` (high) or `LO` (low) |
| Invoice Date | Invoice date (YYYYMMDD) | `20250115` |
| Invoice Number | Invoice number | `12345` |
| Customer Name | Customer name from database | `ABC Corp` |
| Customer PO Number | PO number from database | `PO-12345` |
| UPC | UPC number | `012345678901` |

### Features

- **Deferred Writing:** Buffers all records per invoice, writes on A record boundary
- **DB Lookups:** Fetches customer name, PO number, and UOM descriptions per item

### Database Dependencies

Requires AS400 database connection via `invFetcher` for:
- `fetch_cust_name(invoice_number)` - Get customer name
- `fetch_po(invoice_number)` - Get PO number
- `fetch_uom_desc(item_number, unit_mult, line_no, invoice_number)` - Get UOM description

---

## Common Patterns

### Price Conversion

Most converters use DAC format price conversion (6+ digit string where last 2 digits are cents):

```python
def convert_to_price(value: str) -> str:
    dollars = value[:-2].lstrip("0") or "0"
    cents = value[-2:]
    return f"{dollars}.{cents}"
```

Example: `0001599` → `$15.99`

### UPC Processing

Standard UPC processing handles:
- 12-digit UPCA (passed through)
- 11-digit UPCA (check digit calculated)
- 8-digit UPCE (converted to UPCA)
- Empty/invalid (returns empty string)

### Quantity Conversion

```python
def qty_to_int(qty: str) -> int:
    if qty.startswith("-"):
        return -(int(qty[1:]))
    return int(qty)
```

---

## Record Types

### A Records (Invoice Header)

| Field | Description |
|-------|-------------|
| `record_type` | Always `A` |
| `cust_vendor` | Customer/vendor identifier |
| `invoice_number` | Invoice number |
| `invoice_date` | Date in MMDDYY format |
| `invoice_total` | Total invoice amount (DAC format) |

### B Records (Line Items)

| Field | Description |
|-------|-------------|
| `record_type` | Always `B` |
| `upc_number` | UPC code |
| `vendor_item` | Vendor item number |
| `description` | Product description |
| `qty_of_units` | Quantity shipped (DAC format) |
| `unit_cost` | Unit cost (DAC format) |
| `unit_multiplier` | Units per case |
| `suggested_retail_price` | Suggested retail (DAC format) |
| `parent_item_number` | Parent item for shipper relationships |

### C Records (Charges/Adjustments)

| Field | Description |
|-------|-------------|
| `record_type` | Always `C` |
| `charge_type` | Type of charge |
| `description` | Charge description |
| `amount` | Charge amount (DAC format) |

---

## See Also

- [`convert_base.py`](convert_base.py) - Base converter classes
- [`utils.py`](utils.py) - Shared utility functions
- [`tests/convert_backends/`](tests/convert_backends/) - Converter tests and baselines
- [`PARITY_VERIFICATION.md`](PARITY_VERIFICATION.md) - Output parity testing
