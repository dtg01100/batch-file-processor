# EDI Format Abstraction Guide

## Overview

The batch-file-processor now supports multiple EDI (Electronic Data Interchange) formats through a configuration-based abstraction layer. Instead of hardcoding field positions and record structures, EDI formats are defined in JSON configuration files.

## Quick Start

The system works out-of-the-box with the default format. No changes are needed to existing code - it will automatically use the configurable parser while maintaining backward compatibility.

### Using the Default Format

```python
import utils

line = "A000001INV00001011221251000012345"
record = utils.capture_records(line)
```

### Using Custom Formats

```python
from edi_format_parser import EDIFormatParser

parser = EDIFormatParser.load_format('custom_format')

record = parser.parse_line(line)
```

## Creating Custom EDI Formats

### Format Configuration File

Create a JSON file in the `edi_formats/` directory with the following structure:

```json
{
  "format_id": "my_custom_format",
  "format_name": "My Custom EDI Format",
  "format_version": "1.0",
  "description": "Description of what this format is used for",
  "encoding": "utf-8",
  "record_types": {
    "H": {
      "name": "Header Record",
      "description": "Invoice header information",
      "identifier": {
        "position": 0,
        "length": 1,
        "value": "H"
      },
      "fields": [
        {
          "name": "record_type",
          "position": 0,
          "length": 1,
          "type": "string",
          "description": "Record type identifier"
        },
        {
          "name": "invoice_number",
          "position": 1,
          "length": 10,
          "type": "string",
          "description": "Invoice number"
        }
      ]
    }
  },
  "validation_rules": {
    "file_must_start_with": "H",
    "allowed_record_types": ["H", "D", "T"]
  }
}
```

### Field Definitions

Each field requires:
- `name`: Field identifier used in the returned dictionary
- `position`: Starting character position (0-based)
- `length`: Number of characters
- `type`: Data type (currently "string")
- `description`: Human-readable field description

### Record Type Structure

Each record type must have:
- `name`: Human-readable name
- `description`: Purpose of this record type
- `identifier`: How to identify this record in a file
  - `position`: Where the identifier appears (usually 0)
  - `length`: Length of identifier (usually 1)
  - `value`: The actual identifier character(s)
- `fields`: Array of field definitions

### Validation Rules

Optional validation rules:
- `file_must_start_with`: Required first character of file
- `allowed_record_types`: List of valid record type identifiers
- `b_record_lengths`: For formats with variable-length records (like B records in default format)
- `upc_validation`: UPC-specific validation rules

## Using the API

### Loading Formats

```python
from edi_format_parser import EDIFormatParser

default_parser = EDIFormatParser.get_default_parser()

custom_parser = EDIFormatParser.load_format('custom_format')

from_file = EDIFormatParser.from_file('/path/to/format.json')

available = EDIFormatParser.list_available_formats()
for format_info in available:
    print(f"{format_info['id']}: {format_info['name']}")
```

### Parsing Records

```python
parser = EDIFormatParser.get_default_parser()

record = parser.parse_line("A000001INV00001011221251000012345")

if record:
    print(f"Invoice: {record['invoice_number']}")
    print(f"Date: {record['invoice_date']}")
    print(f"Total: {record['invoice_total']}")
```

### Backward Compatibility

The original `utils.capture_records()` function still works:

```python
import utils

record = utils.capture_records(line)

record_with_parser = utils.capture_records(line, parser=custom_parser)
```

### Validation

```python
parser = EDIFormatParser.get_default_parser()

is_valid = parser.validate_file_start("A000001...")

allowed = parser.get_allowed_record_types()

record_config = parser.get_record_type_config("A")

field_def = parser.get_field_definition("A", "invoice_number")
```

## Default Format Specification

The default format includes three record types:

### A Records (Invoice Header) - 33 characters
- Position 0-0: Record type ("A")
- Position 1-6: Customer/vendor code (6 chars)
- Position 7-16: Invoice number (10 chars)
- Position 17-22: Invoice date MMDDYY (6 chars)
- Position 23-32: Invoice total (10 chars)

### B Records (Line Items) - 76 characters (or 70 for short format)
- Position 0-0: Record type ("B")
- Position 1-11: UPC number (11 chars)
- Position 12-36: Product description (25 chars)
- Position 37-42: Vendor item number (6 chars)
- Position 43-48: Unit cost (6 chars)
- Position 49-50: Combo code (2 chars)
- Position 51-56: Unit multiplier (6 chars)
- Position 57-61: Quantity of units (5 chars)
- Position 62-66: Suggested retail price (5 chars)
- Position 67-69: Multi-pack price (3 chars)
- Position 70-75: Parent item number (6 chars)

### C Records (Charges/Fees) - 38 characters
- Position 0-0: Record type ("C")
- Position 1-3: Charge type code (3 chars)
- Position 4-28: Charge description (25 chars)
- Position 29-37: Charge amount (9 chars)

## Integration Points

### Converters

All converters automatically use the format parser through `utils.capture_records()`. No changes needed.

### Validators

The `mtc_edi_validator` module now accepts a parser parameter:

```python
from mtc_edi_validator import check, report_edi_issues

is_valid, line_count = check(input_file, parser=custom_parser)

report, has_errors, has_minor_errors = report_edi_issues(input_file, parser=custom_parser)
```

## Best Practices

1. **Format Naming**: Use descriptive format IDs (e.g., `vendor_x_format`, `legacy_2020`)
2. **Documentation**: Include detailed descriptions in the JSON file
3. **Testing**: Create test files for each custom format
4. **Versioning**: Increment `format_version` when making changes
5. **Validation**: Define comprehensive validation rules to catch malformed files early

## Example: Creating a New Format

Let's say you receive EDI files from a new vendor with this structure:
- H records: Header with invoice ID and date
- D records: Detail lines with product and quantity
- T records: Trailer with totals

Create `edi_formats/vendor_xyz_format.json`:

```json
{
  "format_id": "vendor_xyz",
  "format_name": "Vendor XYZ EDI Format",
  "format_version": "1.0",
  "description": "EDI format used by Vendor XYZ since 2024",
  "encoding": "utf-8",
  "record_types": {
    "H": {
      "name": "Header",
      "description": "Invoice header record",
      "identifier": {"position": 0, "length": 1, "value": "H"},
      "fields": [
        {"name": "record_type", "position": 0, "length": 1, "type": "string"},
        {"name": "invoice_id", "position": 1, "length": 12, "type": "string"},
        {"name": "invoice_date", "position": 13, "length": 8, "type": "string"}
      ]
    },
    "D": {
      "name": "Detail",
      "description": "Line item detail",
      "identifier": {"position": 0, "length": 1, "value": "D"},
      "fields": [
        {"name": "record_type", "position": 0, "length": 1, "type": "string"},
        {"name": "product_code", "position": 1, "length": 15, "type": "string"},
        {"name": "quantity", "position": 16, "length": 8, "type": "string"},
        {"name": "price", "position": 24, "length": 10, "type": "string"}
      ]
    },
    "T": {
      "name": "Trailer",
      "description": "Trailer with totals",
      "identifier": {"position": 0, "length": 1, "value": "T"},
      "fields": [
        {"name": "record_type", "position": 0, "length": 1, "type": "string"},
        {"name": "total_amount", "position": 1, "length": 12, "type": "string"},
        {"name": "record_count", "position": 13, "length": 6, "type": "string"}
      ]
    }
  },
  "validation_rules": {
    "file_must_start_with": "H",
    "allowed_record_types": ["H", "D", "T"]
  }
}
```

Then use it:

```python
from edi_format_parser import EDIFormatParser

parser = EDIFormatParser.load_format('vendor_xyz')

with open('vendor_xyz_invoice.edi', 'r') as f:
    for line in f:
        record = parser.parse_line(line)
        if record:
            if record['record_type'] == 'H':
                print(f"Processing invoice: {record['invoice_id']}")
            elif record['record_type'] == 'D':
                print(f"  Item: {record['product_code']} x {record['quantity']}")
            elif record['record_type'] == 'T':
                print(f"Total: {record['total_amount']}")
```

## Troubleshooting

### Format Not Found
```
EDIFormatError: Format 'my_format' not found
```
**Solution**: Ensure the file is named `my_format_format.json` or `my_format.json` and is in the `edi_formats/` directory.

### Invalid JSON
```
EDIFormatError: Invalid JSON in format file
```
**Solution**: Validate your JSON using a JSON validator. Common issues:
- Missing commas between elements
- Trailing commas after last element
- Unquoted keys or values
- Incorrect nesting

### Field Extraction Errors
If parsed fields don't match expected values:
1. Verify `position` and `length` values in format definition
2. Check that line length matches expected record length
3. Use a hex editor or character counter to verify positions

### Parser Fallback
If the parser can't be loaded (missing edi_formats directory), the system falls back to the original hardcoded parsing logic. This ensures backward compatibility but you won't get the benefits of the abstraction layer.

## Migration Path

Existing code requires no changes. The abstraction layer is:
- **Backward compatible**: `utils.capture_records()` works as before
- **Opt-in**: Use custom formats only when needed
- **Transparent**: Converters automatically use the new system

For new code, prefer using `EDIFormatParser` directly for clarity and explicit format handling.
