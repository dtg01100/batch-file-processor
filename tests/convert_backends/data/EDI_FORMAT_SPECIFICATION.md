# MTC Electronic Invoice Format Specification

## Overview

The MTC Electronic Invoice format is a fixed-length ASCII text format with no delimiters. This specification is based on the "DAC Implementation of MTC Electronic Invoice" document (Version 1.0, 10/7/2004).

## Format Rules

- **Format**: Plain ASCII text with fixed-length fields
- **Delimiters**: None (fields are position-based)
- **Numeric Fields**: Filled with leading zeros
- **Negative Numbers**: First position of the field will be "-"
- **Text Fields**: Left-aligned, space-padded

## Record Types

### Header Record (Type 'A')

Identifies the invoice header information.

| Field Name | Position | Length | Type | Precision | Description |
|------------|----------|--------|------|-----------|-------------|
| Record Type | 1 | 1 | A | - | Literal "A" |
| Cust/Vendor | 2-7 | 6 | A | - | Customer's identification of vendor |
| Invoice Number | 8-17 | 10 | N | - | MTC Invoice Number to Customer |
| Invoice Date | 18-23 | 6 | N | - | Date of Invoice (YYMMDD) |
| Invoice Total | 24-33 | 10 | N | 2 | Total Dollar amount of Invoice |

**Total Record Length: 33 characters**

#### Example Header Record
```
A000001INV00001011221251000012345
| |     |         |     |
| |     |         |     Invoice Total (0000123.45)
| |     |         Invoice Date (01/12/22)
| |     Invoice Number (INV00001)
| Cust/Vendor (000001)
Record Type (A)
```

### Detail Record (Type 'B')

Contains line item details for products on the invoice.

| Field Name | Position | Length | Type | Precision | Description |
|------------|----------|--------|------|-----------|-------------|
| Record Type | 1 | 1 | A | - | Literal "B" |
| UPC Number | 2-12 | 11 | N | - | UPC Code |
| Description | 13-37 | 25 | A | - | MTC Description of Item |
| Vendor Item | 38-43 | 6 | N | - | MTC Item Number |
| Unit Cost | 44-49 | 6 | N | 2 | Customer's price for sell unit |
| Combo Code | 50-51 | 2 | A | - | For combo: identifies parent record |
| Unit Multiplier | 52-57 | 6 | N | - | # of retail units in one MTC unit |
| Qty of Units | 58-62 | 5 | N | - | Number of MTC Units Shipped |
| Suggested Retail Price | 63-67 | 5 | N | 2 | MTC Suggested Retail Price |
| Price Multi-Pack | 68-70 | 3 | N | - | Multi-Pack Size for suggested retail (Always 1) |
| Parent Item# | 71-76 | 6 | N | - | For combo components: combo item# |

**Total Record Length: 76 characters**

#### Example Detail Record
```
B012345678901Product Description 1234561234567890100001000100050000
| |           |                     |     |     |    |    |
| |           |                     |     |     |    |    Parent Item#
| |           |                     |     |     |    Suggested Retail
| |           |                     |     |     Qty of Units
| |           |                     |     Unit Multiplier
| |           |                     Unit Cost
| |           Vendor Item
| | Description
| UPC Number
Record Type (B)
```

### Sales Tax Record (Type 'C')

Contains sales tax information for the invoice.

| Field Name | Position | Length | Type | Precision | Description |
|------------|----------|--------|------|-----------|-------------|
| Record Type | 1 | 1 | A | - | Literal "C" |
| Charge Type | 2-4 | 3 | A | - | Type of charge. Literal "TAB" |
| Description | 5-29 | 25 | A | - | Description of charge. Literal "Sales Tax" |
| Amount | 30-38 | 9 | N | 2 | Dollar Amount of Charge |

**Total Record Length: 38 characters**

#### Example Sales Tax Record
```
C00100000123
| |  |
| |  Amount (000001.23)
| Description (first 3 chars shown, actually 25 chars)
Record Type (C)
```

## Complete Example Invoice

```
A000001INV00001011221251000012345
B012345678901Product Description 1234561234567890100001000100050000
C00100000123
```

This represents:
- **Header (A)**: Vendor 000001, Invoice INV00001, Date 01/12/22, Total $123.45
- **Detail (B)**: UPC 012345678901, Description "Product Description", Item 123456, Cost $1234.56, Qty 10, Suggested Retail $50.00
- **Tax (C)**: Sales Tax $1.23

## Edge Cases and Special Values

### Zero Values
- Numeric fields with value 0 should be filled with zeros (e.g., "000000")
- Decimal fields: "00000000" represents 0.00

### Negative Values
- Negative values have "-" in the first position
- Example: -123.45 would be "-000012345" (in a 10-digit field with 2 decimals)

### Empty/Null Values
- Text fields: Space-padded to full length
- Numeric fields: Zero-filled to full length

### Special Characters
- Text fields may contain spaces (maintained as-is)
- No tabs or delimiters allowed within fields

## Test Data Files

The following test EDI files are provided in this directory:

| File | Description |
|------|-------------|
| `basic_edi.txt` | Single invoice with one item and tax |
| `complex_edi.txt` | Multiple invoices with multiple items each |
| `edge_cases_edi.txt` | Edge cases (zero values, empty descriptions, etc.) |
| `empty_edi.txt` | Empty file (no records) |
| `malformed_edi.txt` | Invalid/malformed records for error handling tests |
| `fintech_edi.txt` | Format suitable for fintech converter |

## Validation Notes

When creating test EDI files:
1. Ensure all records are exactly the specified length
2. Use proper zero-padding for numeric fields
3. Use space-padding for text fields
4. Include proper record type identifiers (A, B, C)
5. Each invoice should have one A record, one or more B records, and optional C records
