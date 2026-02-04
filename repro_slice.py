import sys
import os

sys.path.append(os.getcwd())
from edi_format_parser import EDIFormatParser


def test_slice():
    line = "A123456789012345012345000012345"
    print(f"Line length: {len(line)}")
    print(f"Slice [23:33]: '{line[23:33]}'")

    try:
        parser = EDIFormatParser.get_default_parser()
        result = parser.parse_line(line)
        print(f"Parser result invoice_total: '{result.get('invoice_total')}'")

        # Check B record too
        line_b = "B1234567890Test Description     123450123450012345012340123"
        result_b = parser.parse_line(line_b)
        print(f"Parser result B upc_number: '{result_b.get('upc_number')}'")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_slice()
