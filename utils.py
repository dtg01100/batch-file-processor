"""Utility functions for batch file processing.

This module provides common utilities used across the application.
Many functions are now migrated to core modules for better organization:
- Boolean utilities: core.utils.bool_utils
- Date utilities: core.utils.date_utils
- EDI parsing: core.edi.edi_parser
- UPC utilities: core.edi.upc_utils
- Invoice fetching: core.edi.inv_fetcher

For backward compatibility, this module re-exports functions from core modules.
New code should import directly from the core modules.
"""

from datetime import datetime
from decimal import Decimal
import os
from typing import Any
import warnings

try:
    from query_runner import query_runner

    HAS_QUERY_RUNNER = True
except (ImportError, RuntimeError):
    HAS_QUERY_RUNNER = False
    query_runner = None

# Import from core modules for backward compatibility
from core.utils.bool_utils import normalize_bool, to_db_bool, from_db_bool
from core.utils.date_utils import (
    dactime_from_datetime,
    datetime_from_dactime,
    datetime_from_invtime,
    dactime_from_invtime,
    prettify_dates,
)
from core.edi.edi_parser import capture_records, _get_default_parser
from core.edi.upc_utils import calc_check_digit, convert_upce_to_upca as convert_UPCE_to_UPCA


# ============================================================================
# Backward Compatibility Re-exports
# ============================================================================
# These imports allow existing code to continue importing from utils.py
# New code should import directly from core modules

# Note: normalize_bool, to_db_bool, from_db_bool are imported above
# Note: date functions are imported above
# Note: capture_records, _get_default_parser are imported above
# Note: calc_check_digit, convert_UPCE_to_UPCA are imported above


# ============================================================================
# Legacy invFetcher Adapter (deprecated - use core.edi.inv_fetcher.InvFetcher)
# ============================================================================

class invFetcher:
    """Legacy invFetcher adapter for backward compatibility.
    
    .. deprecated:: 1.0
        Use `InvFetcher` from `core.edi.inv_fetcher` instead.
        This class delegates to the core implementation.
    """
    
    def __init__(self, settings_dict):
        """Initialize with settings dictionary."""
        warnings.warn(
            "utils.invFetcher is deprecated. Use core.edi.inv_fetcher.InvFetcher instead.",
            DeprecationWarning,
            stacklevel=2
        )
        from core.database import query_runner
        from core.edi.inv_fetcher import InvFetcher
        
        self.settings = settings_dict
        self._legacy_runner = query_runner(
            settings_dict["as400_username"],
            settings_dict["as400_password"],
            settings_dict["as400_address"],
            f"{settings_dict['odbc_driver']}",
        )
        self._fetcher = InvFetcher(self._legacy_runner, settings_dict)
    
    @property
    def last_invoice_number(self):
        return self._fetcher.last_invoice_number
    
    @property
    def uom_lut(self):
        return self._fetcher.uom_lut
    
    @property
    def last_invno(self):
        return self._fetcher.last_invno
    
    @property
    def po(self):
        return self._fetcher.po
    
    @property
    def custname(self):
        return self._fetcher.custname
    
    @property
    def custno(self):
        return self._fetcher.custno
    
    # Legacy aliases
    @property
    def cust(self):
        return self._fetcher.custname

    def fetch_po(self, invoice_number):
        return self._fetcher.fetch_po(int(invoice_number))

    def fetch_cust_name(self, invoice_number):
        return self._fetcher.fetch_cust_name(int(invoice_number))

    def fetch_cust_no(self, invoice_number):
        return self._fetcher.fetch_cust_no(int(invoice_number))

    def fetch_uom_desc(self, itemno, uommult, lineno, invno):
        return self._fetcher.fetch_uom_desc(
            int(itemno), int(uommult), lineno, int(invno)
        )


# ============================================================================
# Data Transformation Functions (not yet migrated to core)
# ============================================================================

def dac_str_int_to_int(dacstr: str) -> int:
    if dacstr.strip() == "":
        return 0
    try:
        if dacstr.startswith("-"):
            return int(dacstr[1:]) - (int(dacstr[1:]) * 2)
        else:
            return int(dacstr)
    except ValueError:
        return 0


def convert_to_price(value):
    return (
        (value[:-2].lstrip("0") if not value[:-2].lstrip("0") == "" else "0")
        + "."
        + value[-2:]
    )


def convert_to_price_decimal(value):
    retprice = (
        (value[:-2].lstrip("0") if not value[:-2].lstrip("0") == "" else "0")
        + "."
        + value[-2:]
    )
    try:
        return Decimal(retprice)
    except Exception:
        return 0


# Note: dactime_from_datetime, datetime_from_dactime, datetime_from_invtime, 
# dactime_from_invtime are now imported from core.utils.date_utils


def detect_invoice_is_credit(edi_process):
    """Detect if an invoice is a credit memo based on negative total."""
    with open(edi_process, encoding="utf-8") as work_file:
        fields = capture_records(work_file.readline())
        if fields["record_type"] != "A":
            raise ValueError(
                "[Invoice Type Detection]: Somehow ended up in the middle of a file, this should not happen"
            )
        if dac_str_int_to_int(fields["invoice_total"]) >= 0:
            return False
        else:
            return True


# Note: _get_default_parser and capture_records are now imported from core.edi.edi_parser

# Note: calc_check_digit and convert_UPCE_to_UPCA are now imported from core.edi.upc_utils


def do_split_edi(edi_process, work_directory, parameters_dict):
    """Split a multi-invoice EDI file into individual invoice files.
    
    Credit for the col_to_excel goes to Nodebody on stackoverflow, at this link: http://stackoverflow.com/a/19154642
    """
    def col_to_excel(col):  # col is 1 based
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
    with open(edi_process, encoding="utf-8") as work_file:  # open input file
        lines_in_edi = sum(1 for _ in work_file)
        work_file.seek(0)
        work_file_lined = [n for n in work_file.readlines()]  # make list of lines
        list_of_first_characters = []
        for line in work_file_lined:
            list_of_first_characters.append(line[0])
        if list_of_first_characters.count("A") > 700:
            return edi_send_list
        for line_mum, line in enumerate(
            work_file_lined
        ):  # iterate over work file contents
            writeable_line = line
            if writeable_line.startswith("A"):
                count += 1
                prepend_letters = col_to_excel(count)
                line_dict = capture_records(writeable_line)
                if int(line_dict["invoice_total"]) < 0:
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
        # edi_send_list.append((output_file_path, file_name_prefix, file_name_suffix))
        # edi_send_list.pop(0)
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


def do_clear_old_files(folder_path, maximum_files):
    while len(os.listdir(folder_path)) > maximum_files:
        os.remove(
            os.path.join(
                folder_path,
                min(
                    os.listdir(folder_path),
                    key=lambda f: os.path.getctime("{}/{}".format(folder_path, f)),
                ),
            )
        )


def qty_to_int(qty: str) -> int:
    """Convert a quantity string to an integer, handling negative values.

    Args:
        qty: A string representing a quantity, may start with '-' for negative values.

    Returns:
        The integer value of the quantity, or 0 if conversion fails.

    Examples:
        qty_to_int("5") → 5
        qty_to_int("-3") → -3
        qty_to_int("invalid") → 0
    """
    try:
        if qty.startswith("-"):
            return -int(qty[1:])
        return int(qty)
    except ValueError:
        return 0


def add_row(csv_writer, rowdict: dict):
    """Write a dictionary row to a CSV file.

    Args:
        csv_writer: A csv.writer object to write to.
        rowdict: A dictionary whose values will be written as a row.
    """
    column_list = []
    for cell in rowdict.values():
        column_list.append(cell)
    csv_writer.writerow(column_list)


class cRecGenerator:
    """Class for generating split C records for prepaid/non-prepaid sales tax.

    This class queries the database to split sales tax totals into prepaid and
    non-prepaid amounts, then writes them as separate C records.
    """

    def __init__(self, settings_dict):
        """Initialize the C record generator.

        Args:
            settings_dict: Dictionary containing database connection settings.
                Must include: as400_username, as400_password, as400_address, odbc_driver
        """
        self.query_object = None
        self._invoice_number = "0"
        self.unappended_records = False
        self.settings = settings_dict

    def _db_connect(self):
        """Establish database connection."""
        self.query_object = query_runner(
            self.settings["as400_username"],
            self.settings["as400_password"],
            self.settings["as400_address"],
            f"{self.settings['odbc_driver']}",
        )

    def set_invoice_number(self, invoice_number):
        """Set the current invoice number and mark records as unappended.

        Args:
            invoice_number: The invoice number to query for sales tax data.
        """
        self._invoice_number = invoice_number
        self.unappended_records = True

    def fetch_splitted_sales_tax_totals(self, write_func):
        """Fetch and write split sales tax totals as C records.

        Queries the database for prepaid and non-prepaid sales tax amounts
        for the current invoice number, then writes them as separate C records.

        Args:
            write_func: A callable that accepts a string to write (e.g., file.write).
        """
        if self.query_object is None:
            self._db_connect()

        qry_ret = self.query_object.run_arbitrary_query(
            f"""
            SELECT
                sum(CASE odhst.buh6nb WHEN 1 THEN 0 ELSE odhst.bufgpr END),
                sum(CASE odhst.buh6nb WHEN 1 THEN odhst.bufgpr ELSE 0 END)
            FROM
                dacdata.odhst odhst
            WHERE
                odhst.BUHHNB = {self._invoice_number}
            """
        )

        qry_ret_non_prepaid, qry_ret_prepaid = qry_ret[0]

        def _write_line(typestr: str, amount: int, wprocfile):
            descstr = typestr.ljust(25, " ")
            if amount < 0:
                amount_builder = amount - (amount * 2)
            else:
                amount_builder = amount

            amountstr = str(amount_builder).replace(".", "").rjust(9, "0")
            if amount < 0:
                temp_amount_list = list(amountstr)
                temp_amount_list[0] = "-"
                amountstr = "".join(temp_amount_list)
            linebuilder = f"CTAB{descstr}{amountstr}\n"
            wprocfile(linebuilder)

        if qry_ret_prepaid != 0 and qry_ret_prepaid is not None:
            _write_line("Prepaid Sales Tax", qry_ret_prepaid, write_func)
        if qry_ret_non_prepaid != 0 and qry_ret_non_prepaid is not None:
            _write_line("Sales Tax", qry_ret_non_prepaid, write_func)

        self.unappended_records = False


def apply_retail_uom_transform(record: dict, upc_lookup: dict) -> bool:
    """Apply retail UOM transformation to a B record.

    Transforms B record from case-level to each-level retail UOM.
    Modifies record in place: unit_cost, qty_of_units, upc_number, unit_multiplier.

    Args:
        record: The B record dictionary to transform in place.
        upc_lookup: Dictionary mapping vendor item numbers to UPC data.
            Expected format: {vendor_item: [category, each_upc, ...]}

    Returns:
        True if transformation was applied, False otherwise.
    """
    from decimal import Decimal

    # Validate record fields can be parsed
    try:
        item_number = int(record["vendor_item"].strip())
        float(record["unit_cost"].strip())
        test_unit_multiplier = int(record["unit_multiplier"].strip())
        if test_unit_multiplier == 0:
            raise ValueError("unit_multiplier cannot be zero")
        int(record["qty_of_units"].strip())
    except Exception:
        print("cannot parse b record field, skipping")
        return False

    # Get the each-level UPC from lookup
    try:
        each_upc_string = upc_lookup[item_number][1][:11].ljust(11)
    except (KeyError, IndexError):
        each_upc_string = "           "

    # Apply the transformation
    try:
        record["unit_cost"] = (
            str(
                Decimal(
                    (Decimal(record["unit_cost"].strip()) / 100)
                    / Decimal(record["unit_multiplier"].strip())
                ).quantize(Decimal(".01"))
            )
            .replace(".", "")[-6:]
            .rjust(6, "0")
        )
        record["qty_of_units"] = str(
            int(record["unit_multiplier"].strip()) * int(record["qty_of_units"].strip())
        ).rjust(5, "0")
        record["upc_number"] = each_upc_string
        record["unit_multiplier"] = "000001"
        return True
    except Exception as error:
        print(error)
        return False


def apply_upc_override(
    record: dict,
    upc_lookup: dict,
    override_level: int = 1,
    category_filter: str = "ALL",
) -> bool:
    """Override UPC from lookup table based on vendor_item.

    Modifies record in place: upc_number.

    Args:
        record: The B record dictionary to modify in place.
        upc_lookup: Dictionary mapping vendor item numbers to UPC data.
            Expected format: {vendor_item: [category, upc_level_1, upc_level_2, ...]}
        override_level: Which UPC level to use from lookup table (default: 1).
        category_filter: Comma-separated list of categories to filter by,
            or "ALL" to apply to all categories (default: "ALL").

    Returns:
        True if override was applied, False otherwise.
    """
    try:
        if not upc_lookup:
            return False

        vendor_item_int = int(record["vendor_item"].strip())

        if vendor_item_int not in upc_lookup:
            record["upc_number"] = ""
            return False

        do_updateupc = False
        if category_filter == "ALL":
            do_updateupc = True
        else:
            # Check if item's category is in the filter list
            item_category = upc_lookup[vendor_item_int][0]
            if item_category in category_filter.split(","):
                do_updateupc = True

        if do_updateupc:
            record["upc_number"] = upc_lookup[vendor_item_int][override_level]
            return True
        else:
            return False

    except (KeyError, ValueError, IndexError):
        record["upc_number"] = ""
        return False


def filter_b_records_by_category(
    b_records: list[str],
    upc_dict: dict,
    filter_categories: str,
    filter_mode: str
) -> list[str]:
    """Filter B records based on item category.
    
    Args:
        b_records: List of B record lines to filter
        upc_dict: Dictionary mapping item numbers to [category, upc1, upc2, upc3, upc4]
        filter_categories: String of comma-separated categories or "ALL"
        filter_mode: "include" (keep only these categories) or "exclude" (remove these categories)
        
    Returns:
        List of filtered B record lines
    """
    if filter_categories == "ALL":
        return b_records
    
    if not upc_dict:
        return b_records
    
    categories_list = [c.strip().lower() for c in filter_categories.split(",")]
    filtered_records = []
    
    for record in b_records:
        try:
            b_rec_dict = capture_records(record)
            if b_rec_dict is None:
                # Include unparsable records in output
                filtered_records.append(record)
                continue
            vendor_item = int(b_rec_dict['vendor_item'].strip())
            
            if vendor_item in upc_dict:
                item_category = str(upc_dict[vendor_item][0]).lower()
                category_in_list = item_category in categories_list
                
                if filter_mode == "include":
                    if category_in_list:
                        filtered_records.append(record)
                else:  # exclude mode
                    if not category_in_list:
                        filtered_records.append(record)
            else:
                # Item not in upc_dict - include by default (fail-open)
                filtered_records.append(record)
        except (ValueError, KeyError):
            # On error, include the record (fail-open)
            filtered_records.append(record)
    
    return filtered_records


def filter_edi_file_by_category(
    input_file: str,
    output_file: str,
    upc_dict: dict,
    filter_categories: str,
    filter_mode: str = "include"
) -> bool:
    """Filter EDI file by item category, dropping invoices without matching B records.
    
    Reads an EDI file, filters B records based on category, and writes the result
    to an output file. Invoices (A + B + C records) that have no B records after
    filtering are completely removed.
    
    Args:
        input_file: Path to input EDI file
        output_file: Path to output EDI file
        upc_dict: Dictionary mapping item numbers to [category, upc1, upc2, upc3, upc4]
        filter_categories: Comma-separated categories or "ALL"
        filter_mode: "include" (keep only these categories) or "exclude" (remove these categories)
        
    Returns:
        True if any filtering was applied, False if no filtering occurred
    """
    # Handle ALL mode - no filtering needed
    if filter_categories == "ALL":
        # Just copy file unchanged
        try:
            with open(input_file, 'r') as infile:
                content = infile.read()
            with open(output_file, 'w') as outfile:
                outfile.write(content)
            return False
        except (IOError, OSError) as e:
            raise ValueError(f"Failed to copy file: {e}")
    
    # Read input file
    try:
        with open(input_file, 'r') as infile:
            lines = infile.readlines()
    except (IOError, OSError) as e:
        raise ValueError(f"Failed to read input file: {e}")
    
    if not lines:
        # Empty file - just copy it
        try:
            with open(output_file, 'w') as outfile:
                pass
        except (IOError, OSError) as e:
            raise ValueError(f"Failed to create output file: {e}")
        return False
    
    # Group lines into invoices (each starts with 'A' record)
    invoices = []
    current_invoice = []
    
    for line in lines:
        if line.startswith('A'):
            # Start of new invoice - save previous if exists
            if current_invoice:
                invoices.append(current_invoice)
            current_invoice = [line]
        elif line.strip():  # Non-empty line
            current_invoice.append(line)
    
    # Don't forget last invoice
    if current_invoice:
        invoices.append(current_invoice)
    
    # Process each invoice
    filtered_invoices = []
    any_filtered = False
    
    for invoice_lines in invoices:
        # Separate A, B, and C records
        a_record = None
        b_records = []
        c_record = None
        
        for line in invoice_lines:
            if line.startswith('A'):
                a_record = line
            elif line.startswith('B'):
                b_records.append(line)
            elif line.startswith('C'):
                c_record = line
        
        # Filter B records by category
        filtered_b_records = filter_b_records_by_category(
            b_records, upc_dict, filter_categories, filter_mode
        )
        
        # Check if any B records were filtered out
        if len(filtered_b_records) != len(b_records):
            any_filtered = True
        
        # Only keep invoice if it has at least one B record after filtering
        if filtered_b_records:
            # Rebuild invoice with filtered B records
            filtered_invoice = [a_record] + filtered_b_records
            if c_record:
                filtered_invoice.append(c_record)
            filtered_invoices.append(filtered_invoice)
        else:
            # Invoice dropped because no matching B records
            any_filtered = True
    
    # Write output file
    try:
        with open(output_file, 'w') as outfile:
            for invoice in filtered_invoices:
                outfile.writelines(invoice)
    except (IOError, OSError) as e:
        raise ValueError(f"Failed to write output file: {e}")
    
    return any_filtered
