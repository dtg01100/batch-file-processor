"""
EDI processing utilities.

This module provides functions for parsing, splitting, and processing EDI files
in the batch file processor system.
"""

import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable


def _get_default_parser():
    """Get the default EDI format parser."""
    try:
        from edi_format_parser import EDIFormatParser
        return EDIFormatParser.get_default_parser()
    except Exception:
        return None


def capture_records(line: str, parser=None) -> Optional[Dict[str, Any]]:
    """Parse a single EDI line into a dictionary of fields.

    Args:
        line: The EDI line to parse
        parser: Optional parser instance (uses default if None)

    Returns:
        Dictionary of parsed fields, or None for EOF

    Raises:
        Exception: If line is not valid EDI format
    """
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

    # Fallback manual parsing
    if line.startswith("A"):
        fields = {
            "record_type": line[0],
            "cust_vendor": line[1:7],
            "invoice_number": line[7:17],
            "invoice_date": line[17:23],
            "invoice_total": line[23:33],
        }
        return fields
    elif line.startswith("B"):
        fields = {
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
        return fields
    elif line.startswith("C"):
        fields = {
            "record_type": line[0],
            "charge_type": line[1:4],
            "description": line[4:29],
            "amount": line[29:38],
        }
        return fields
    elif line.startswith(""):
        return None
    else:
        raise Exception("Not An EDI")


def detect_invoice_is_credit(edi_process: str) -> bool:
    """Detect if an EDI file contains a credit invoice.

    Args:
        edi_process: Path to the EDI file

    Returns:
        True if invoice is credit (negative total), False if regular invoice

    Raises:
        ValueError: If file doesn't start with A record
    """
    with open(edi_process, encoding="utf-8") as work_file:
        fields = capture_records(work_file.readline())
        if fields["record_type"] != "A":
            raise ValueError(
                "[Invoice Type Detection]: Somehow ended up in the middle of a file, this should not happen"
            )
        from utils.string_utils import dac_str_int_to_int
        return dac_str_int_to_int(fields["invoice_total"]) < 0


def do_split_edi(edi_process: str, work_directory: str, parameters_dict: Dict[str, Any]) -> List[tuple]:
    """Split an EDI file into individual invoice files.

    Credit for the col_to_excel function goes to Nodebody on StackOverflow:
    http://stackoverflow.com/a/19154642

    Args:
        edi_process: Path to input EDI file
        work_directory: Directory to write split files
        parameters_dict: Processing parameters including prepend_date_files

    Returns:
        List of tuples: (output_file_path, file_name_prefix, file_name_suffix)

    Raises:
        Exception: For various validation errors
    """

    def col_to_excel(col: int) -> str:  # col is 1 based
        """Convert column number to Excel column letters."""
        excel_col = str()
        div = col
        while div:
            (div, mod) = divmod(div - 1, 26)  # will return (x, 0 .. 25)
            excel_col = chr(mod + 65) + excel_col
        return excel_col

    f = None
    output_file_path = None
    count = 0
    write_counter = 0
    edi_send_list = []
    
    if not os.path.exists(work_directory):
        os.mkdir(work_directory)
        
    with open(edi_process, encoding="utf-8") as work_file:
        lines_in_edi = sum(1 for _ in work_file)
        work_file.seek(0)
        work_file_lined = [n for n in work_file.readlines()]  # make list of lines
        list_of_first_characters = []
        for line in work_file_lined:
            list_of_first_characters.append(line[0])
        if list_of_first_characters.count("A") > 700:
            return edi_send_list
            
        for line_mum, line in enumerate(work_file_lined):
            writeable_line = line
            if writeable_line.startswith("A"):
                count += 1
                prepend_letters = col_to_excel(count)
                line_dict = capture_records(writeable_line)
                from utils.string_utils import dac_str_int_to_int
                
                if dac_str_int_to_int(line_dict["invoice_total"]) < 0:
                    file_name_suffix = ".cr"
                else:
                    file_name_suffix = ".inv"
                    
                if len(edi_send_list) != 0:
                    f.close()
                    
                file_name_prefix = prepend_letters + "_"
                if parameters_dict["prepend_date_files"]:
                    datetime_from_arec = datetime.strptime(
                        line_dict["invoice_date"], "%m%d%y"
                    )
                    inv_date = datetime.strftime(datetime_from_arec, "%d %b, %Y")
                    file_name_prefix = inv_date + "_" + file_name_prefix
                    
                output_file_path = os.path.join(
                    work_directory,
                    file_name_prefix + os.path.basename(edi_process) + file_name_suffix,
                )
                edi_send_list.append(
                    (output_file_path, file_name_prefix, file_name_suffix)
                )
                f = open(output_file_path, "wb")
            f.write(writeable_line.replace("\n", "\r\n").encode())
            write_counter += 1
            
        f.close()  # close output file
        
        # Validation
        edi_send_list_lines = 0
        for output_file, _, _ in edi_send_list:
            with open(output_file, encoding="utf-8") as file_handle:
                edi_send_list_lines += sum(1 for _ in file_handle)
                
        if not lines_in_edi == write_counter:
            raise Exception("not all lines in input were written out")
        if not lines_in_edi == edi_send_list_lines:
            raise Exception("total lines in output files do not match input file")
        if not len(edi_send_list) == list_of_first_characters.count("A"):
            raise Exception('mismatched number of "A" records')
        if len(edi_send_list) < 1:
            raise Exception("No Split EDIs")
            
    return edi_send_list