# Spec: Format Output Specifications

## Overview

Define what "identical output" means for each converter format, accounting for format-specific requirements like line endings, whitespace handling, and field padding.

## ADDED Requirements

### Requirement: EDI line ending specification

EDI formats SHALL specify their line ending requirements.

#### Scenario: EDI formats use CRLF

**When** an EDI format (scannerware, csv, tweaks, etc.) produces output  
**Then** line endings SHALL be CR+LF (`\r\n`) unless the format specification explicitly allows LF-only

#### Scenario: Forced line ending override

**When** a folder parameter `force_crlf` is set  
**Then** the converter SHALL ensure all line endings are CRLF regardless of internal handling

#### Scenario: Forced TXT extension

**When** a folder parameter `force_txt_file_ext` is set  
**Then** the output filename SHALL have `.txt` extension instead of `.edi`

---

### Requirement: CSV line ending specification

CSV formats SHALL specify their line ending requirements.

#### Scenario: CSV uses platform-default or configurable

**When** a CSV format produces output  
**Then** line endings SHALL match the system default, OR be configurable via parameter

#### Scenario: CSV quoted field preservation

**When** a CSV format includes quoted fields  
**Then** the quotes SHALL be preserved exactly as written (no added/removed quotes)

---

### Requirement: Numeric field padding specification

Numeric fields SHALL follow format-specific padding rules.

#### Scenario: UPC check digit handling

**When** a converter processes UPC fields  
**Then** the check digit SHALL be calculated per the format specification (see `calculate_upc_check_digit` parameter)

#### Scenario: Leading zero preservation

**When** a numeric field has leading zeros  
**Then** the output SHALL preserve leading zeros as specified by the format

#### Scenario: Decimal precision

**When** a decimal field (price, quantity) is output  
**Then** the decimal places SHALL match the format specification (no rounding unless specified)

---

### Requirement: Whitespace handling specification

Whitespace in output SHALL follow format rules.

#### Scenario: Trailing whitespace removal

**When** a field has trailing spaces in the input  
**Then** the output SHALL have trailing whitespace removed unless the format requires padding

#### Scenario: Field delimiter handling

**When** a field contains the delimiter character  
**Then** the output SHALL quote the field or escape the delimiter per CSV RFC 4180 rules

---

### Requirement: Header/trailer record handling

EDI headers and trailers SHALL be handled according to format specifications.

#### Scenario: Include headers parameter

**When** `include_headers` is set to False  
**Then** the converter SHALL omit header records from output

#### Scenario: A-record inclusion

**When** `include_a_records` is set  
**Then** A-records SHALL be included/excluded per parameter

#### Scenario: C-record generation

**When** `include_c_records` is set  
**Then** C-records SHALL be generated or omitted per parameter

---

### Requirement: Character encoding specification

All formats SHALL specify their character encoding.

#### Scenario: UTF-8 encoding default

**When** no encoding is specified  
**Then** output SHALL use UTF-8 encoding

#### Scenario: ASCII fallback

**When** the format requires ASCII-only output  
**Then** non-ASCII characters SHALL be replaced with a substitution character or cause an error

#### Scenario: Ampersand filtering

**When** `filter_ampersand` is set  
**Then** ampersand characters SHALL be replaced with the configured substitution (default: `&amp;`)

---

### Requirement: Tweaks format specific requirements

The tweaks format SHALL apply transformations with exact preservation.

#### Scenario: A-record padding exact

**When** `a_record_padding` is configured  
**Then** padding SHALL be applied exactly as specified, character-for-character

#### Scenario: Invoice date offset

**When** `invoice_date_offset` is set  
**Then** dates SHALL be offset by exactly that many days

#### Scenario: Retail UOM conversion

**When** `retail_uom` is set  
**Then** UOM values SHALL be converted using the specified mapping