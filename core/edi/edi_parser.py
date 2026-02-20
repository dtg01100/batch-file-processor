"""EDI record parsing utilities.

Pure functions for parsing EDI A, B, and C records.
"""

from typing import Optional
from dataclasses import dataclass

_default_parser = None


def _get_default_parser():
    global _default_parser
    if _default_parser is None:
        try:
            from edi_format_parser import EDIFormatParser

            _default_parser = EDIFormatParser.get_default_parser()
        except Exception:
            _default_parser = False
    return _default_parser if _default_parser is not False else None


def capture_records(line, parser=None):
    if parser is None:
        parser = _get_default_parser()

    if parser is not None:
        result = parser.parse_line(line)
        if result is None and line and line.strip() != "":
            # Ignore standard EOF marker (Ctrl+Z)
            if line.strip() == "\x1a":
                return None
            raise Exception("Not An EDI")
        return result

    if not line or line.startswith("\x1a"):
        return None

    if line.startswith("A"):
        return {
            "record_type": line[0],
            "cust_vendor": line[1:7],
            "invoice_number": line[7:17],
            "invoice_date": line[17:23],
            "invoice_total": line[23:33],
        }
    elif line.startswith("B"):
        return {
            "record_type": line[0],
            "upc_number": line[1:12],
            "description": line[12:37],
            "vendor_item": line[37:43],
            "unit_cost": line[43:49],
            "combo_code": line[49:51],
            "unit_multiplier": line[51:57],
            "qty_of_units": line[57:62],
            "suggested_retail_price": line[62:67],
            "price_multi_pack": line[67:70],
            "parent_item_number": line[70:76],
        }
    elif line.startswith("C"):
        return {
            "record_type": line[0],
            "charge_type": line[1:4],
            "description": line[4:29],
            "amount": line[29:38],
        }
    else:
        return None  # Invalid record type


@dataclass
class ARecord:
    """EDI A record (invoice header).
    
    Attributes:
        record_type: Always 'A'
        cust_vendor: 6-character vendor code
        invoice_number: 10-character invoice number
        invoice_date: 6-character date (MMDDYY)
        invoice_total: 10-character total (cents as integer, may be negative)
    """
    record_type: str
    cust_vendor: str
    invoice_number: str
    invoice_date: str
    invoice_total: str


@dataclass
class BRecord:
    """EDI B record (line item).
    
    Attributes:
        record_type: Always 'B'
        upc_number: 11-character UPC code
        description: 25-character item description
        vendor_item: 6-character vendor item number
        unit_cost: 6-character unit cost
        combo_code: 2-character combo code
        unit_multiplier: 6-character unit multiplier
        qty_of_units: 5-character quantity
        suggested_retail_price: 5-character retail price
        price_multi_pack: 3-character multi-pack price
        parent_item_number: 6-character parent item number
    """
    record_type: str
    upc_number: str
    description: str
    vendor_item: str
    unit_cost: str
    combo_code: str
    unit_multiplier: str
    qty_of_units: str
    suggested_retail_price: str
    price_multi_pack: str
    parent_item_number: str


@dataclass
class CRecord:
    """EDI C record (charge/allowance).
    
    Attributes:
        record_type: Always 'C'
        charge_type: 3-character charge type code
        description: 25-character description
        amount: 9-character amount
    """
    record_type: str
    charge_type: str
    description: str
    amount: str


def capture_records(line: str) -> Optional[dict]:
    """Parse an EDI record line into a dictionary.
    
    Args:
        line: Single EDI record line
        
    Returns:
        Dictionary with record fields, or None for empty lines
        
    Raises:
        ValueError: If line doesn't match known record type
        
    Example:
        >>> capture_records("AVENDOR0000000001120240000000123\\n")
        {'record_type': 'A', 'cust_vendor': 'VENDOR', ...}
    """
    if not line or line.startswith("\x1a") or line.strip() == "":
        return None
    
    if line.startswith("A"):
        return {
            "record_type": line[0],
            "cust_vendor": line[1:7],
            "invoice_number": line[7:17],
            "invoice_date": line[17:23],
            "invoice_total": line[23:33],
        }
    elif line.startswith("B"):
        return {
            "record_type": line[0],
            "upc_number": line[1:12],
            "description": line[12:37],
            "vendor_item": line[37:43],
            "unit_cost": line[43:49],
            "combo_code": line[49:51],
            "unit_multiplier": line[51:57],
            "qty_of_units": line[57:62],
            "suggested_retail_price": line[62:67],
            "price_multi_pack": line[67:70],
            "parent_item_number": line[70:76],
        }
    elif line.startswith("C"):
        return {
            "record_type": line[0],
            "charge_type": line[1:4],
            "description": line[4:29],
            "amount": line[29:38],
        }
    else:
        return None  # Invalid record type


def parse_a_record(line: str) -> ARecord:
    """Parse an A record line into an ARecord dataclass.
    
    Args:
        line: Single A record line
        
    Returns:
        ARecord dataclass instance
        
    Raises:
        ValueError: If line is not an A record
    """
    fields = capture_records(line)
    if not fields or fields["record_type"] != "A":
        raise ValueError("Not an A record")
    return ARecord(**fields)


def parse_b_record(line: str) -> BRecord:
    """Parse a B record line into a BRecord dataclass.
    
    Args:
        line: Single B record line
        
    Returns:
        BRecord dataclass instance
        
    Raises:
        ValueError: If line is not a B record
    """
    fields = capture_records(line)
    if not fields or fields["record_type"] != "B":
        raise ValueError("Not a B record")
    return BRecord(**fields)


def parse_c_record(line: str) -> CRecord:
    """Parse a C record line into a CRecord dataclass.
    
    Args:
        line: Single C record line
        
    Returns:
        CRecord dataclass instance
        
    Raises:
        ValueError: If line is not a C record
    """
    fields = capture_records(line)
    if not fields or fields["record_type"] != "C":
        raise ValueError("Not a C record")
    return CRecord(**fields)


def build_a_record(
    cust_vendor: str,
    invoice_number: str,
    invoice_date: str,
    invoice_total: str,
    append_text: str = ""
) -> str:
    """Build an A record line from components.
    
    Args:
        cust_vendor: 6-character vendor code
        invoice_number: 10-character invoice number
        invoice_date: 6-character date (MMDDYY)
        invoice_total: 10-character total
        append_text: Optional text to append
        
    Returns:
        Complete A record line with newline
    """
    line = f"A{cust_vendor}{invoice_number}{invoice_date}{invoice_total}{append_text}\n"
    return line


def build_b_record(
    upc_number: str,
    description: str,
    vendor_item: str,
    unit_cost: str,
    combo_code: str,
    unit_multiplier: str,
    qty_of_units: str,
    suggested_retail_price: str,
    price_multi_pack: str = "   ",
    parent_item_number: str = "      "
) -> str:
    """Build a B record line from components.
    
    Args:
        upc_number: 11-character UPC code
        description: 25-character item description
        vendor_item: 6-character vendor item number
        unit_cost: 6-character unit cost
        combo_code: 2-character combo code
        unit_multiplier: 6-character unit multiplier
        qty_of_units: 5-character quantity
        suggested_retail_price: 5-character retail price
        price_multi_pack: 3-character multi-pack price (default: spaces)
        parent_item_number: 6-character parent item number (default: spaces)
        
    Returns:
        Complete B record line with newline
    """
    return (
        f"B{upc_number}{description}{vendor_item}{unit_cost}"
        f"{combo_code}{unit_multiplier}{qty_of_units}"
        f"{suggested_retail_price}{price_multi_pack}{parent_item_number}\n"
    )


def build_c_record(
    charge_type: str,
    description: str,
    amount: str
) -> str:
    """Build a C record line from components.
    
    Args:
        charge_type: 3-character charge type code
        description: 25-character description
        amount: 9-character amount
        
    Returns:
        Complete C record line with newline
    """
    return f"C{charge_type}{description}{amount}\n"
