# EDI Processing Design Document

**Version:** 1.0  
**Date:** 2026-05-18  
**Status:** DRAFT

---

## 1. Overview

EDI (Electronic Data Interchange) processing covers parsing, validation, splitting, tweaking, and conversion of EDI files.

## 2. EDI File Structure

EDI files use delimiters to separate segments and elements:

```
Segment Terminator: ~ (configurable)
Element Separator: * (configurable)
Sub-element Separator: : (configurable)
```

### Example EDI Transaction

```
ISA*00*          *00*          *ZZ*RECEIVER       *ZZ*SENDER         *...*...
GS*PO*SENDER*RECEIVER*...*...*X*004010
ST*850*0001
BEG*00*ORDER***...*...
PO1*1*100*EA*...**...*...*VN*...
CTT*1
SE*6*0001
GE*1*...*
IEA*1*...
```

## 3. Core EDI Modules

### 3.1 EDI Parser

**Module:** `core/edi/edi_parser.py`

```python
class EDIParser:
    def parse_file(self, file_path: str) -> EDIDocument:
        """Parse EDI file into structured document."""
    
    def parse_content(self, content: str) -> EDIDocument:
        """Parse EDI content string."""
    
    def get_segments(self) -> List[Segment]:
        """Get all segments from document."""
    
    def get_transaction_sets(self) -> List[TransactionSet]:
        """Get transaction sets (ST...SE blocks)."""
```

### 3.2 EDI Validator

**Module:** `dispatch/edi_validator.py` / `dispatch/pipeline/validator.py`

```python
class EDIValidator:
    def validate(self, file_path: str) -> ValidationResult:
        """Validate EDI file format."""
    
    def check_structure(self, content: str) -> bool:
        """Check ISA/IEA envelope integrity."""
    
    def check_syntax(self, segments: List[Segment]) -> List[str]:
        """Check segment syntax and required elements."""
```

### 3.3 EDI Splitter

**Module:** `core/edi/edi_splitter.py`

```python
def split_edi_file(input_path: str, output_dir: str = None) -> List[str]:
    """Split multi-transaction EDI into individual files.
    
    Returns:
        List of output file paths.
    """
```

### 3.4 EDI Tweaker

**Module:** `core/edi/edi_tweaker.py`

```python
def apply_tweaks(content: str, tweak_rules: List[TweakRule]) -> str:
    """Apply field-level modifications to EDI content."""
```

## 4. EDI Element Structure

### 4.1 Segment

```python
class Segment:
    tag: str           # e.g., "PO1", "N1", "REF"
    elements: List[List[str]]  # Composite elements
    position: int      # Line/record position
```

### 4.2 Transaction Set

```python
class TransactionSet:
    type_code: str     # e.g., "850" (PO), "810" (Invoice)
    control_number: str
    header_segments: List[Segment]
    detail_segments: List[Segment]
    summary_segments: List[Segment]
```

## 5. Common EDI Transaction Types

| Code | Name | Description |
|------|------|-------------|
| 850 | Purchase Order | Order from buyer to seller |
| 810 | Invoice | Billing/invoice document |
| 856 | ASN/Ship Notice | Advance ship notification |
| 820 | Payment Order | Payment instructions |
| 997 | Acknowledge | Functional acknowledgment |

## 6. Processing Flow

```
1. Read EDI file
2. Parse headers (ISA, GS)
3. Extract transaction sets (ST...SE)
4. For each transaction:
   a. Validate segment structure
   b. Extract required fields
   c. Apply tweaks
   d. Convert to target format
5. Write output
```

## 7. Related Documents

- [DATA_FLOW.md](DATA_FLOW.md) - Data flow overview
- [PROCESSING_PIPELINE.md](PROCESSING_PIPELINE.md) - Pipeline stages
- [CONVERTER_ARCHITECTURE.md](CONVERTER_ARCHITECTURE.md) - Format conversion
