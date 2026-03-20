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

import os
from datetime import datetime
from decimal import Decimal

from core.database import LegacyQueryRunnerAdapter, create_query_runner

# Import from core modules for backward compatibility
from core.edi.edi_parser import capture_records
from core.edi.inv_fetcher import InvFetcher as invFetcher  # noqa: F401
from core.edi.upc_utils import (
    calc_check_digit,  # noqa: F401
    convert_upce_to_upca as convert_UPCE_to_UPCA,  # noqa: F401
)
from core.edi.edi_transformer import (
    detect_invoice_is_credit,  # noqa: F401
)
from core.utils.date_utils import (
    dactime_from_datetime,  # noqa: F401
    dactime_from_invtime,  # noqa: F401
    datetime_from_dactime,  # noqa: F401
    datetime_from_invtime,  # noqa: F401
)


def normalize_bool(value) -> bool:
    """Convert any value to Python boolean.

    Args:
        value: Value to convert to boolean

    Returns:
        Boolean representation of the value

    Examples:
        normalize_bool(True) → True
        normalize_bool(False) → False
        normalize_bool("true") → True
        normalize_bool("1") → True
        normalize_bool(0) → False
        normalize_bool(None) → False
    """
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        stripped = value.strip().lower()
        if stripped in ("true", "1", "yes", "on", "y"):
            return True
        if stripped in ("false", "0", "no", "off", ""):
            return False
        return bool(value.strip())
    return bool(value)


def to_db_bool(value) -> int:
    """Convert value to SQLite boolean integer (0 or 1).

    Args:
        value: Value to convert

    Returns:
        1 for True, 0 for False

    Examples:
        to_db_bool(True) → 1
        to_db_bool(False) → 0
        to_db_bool("yes") → 1
        to_db_bool(None) → 0
    """
    return 1 if normalize_bool(value) else 0


def from_db_bool(value) -> bool:
    """Convert SQLite boolean integer to Python boolean.

    Args:
        value: SQLite boolean value (0, 1, or similar)

    Returns:
        Boolean representation

    Examples:
        from_db_bool(1) → True
        from_db_bool(0) → False
        from_db_bool("1") → True
        from_db_bool("0") → False
    """
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.lower() in ("1", "true", "yes", "on")
    return bool(value)


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
        if fields is None:
            return False
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


def _col_to_excel(col: int) -> str:
    """Convert a 1-based column index to Excel letters."""
    excel_col = ""
    div = col
    while div:
        div, mod = divmod(div - 1, 26)
        excel_col = chr(mod + 65) + excel_col
    return excel_col


def _build_split_file_metadata(
    line_dict: dict,
    count: int,
    edi_process: str,
    work_directory: str,
    prepend_date_files: bool,
) -> tuple[str, str, str]:
    """Build output path and filename metadata for a split EDI invoice."""
    prepend_letters = _col_to_excel(count)
    file_name_suffix = ".cr" if int(line_dict["invoice_total"]) < 0 else ".inv"

    file_name_prefix = prepend_letters + "_"
    if prepend_date_files:
        datetime_from_arec = datetime.strptime(line_dict["invoice_date"], "%m%d%y")
        inv_date = datetime.strftime(datetime_from_arec, "%d %b, %Y")
        file_name_prefix = inv_date + "_" + file_name_prefix

    output_file_path = os.path.join(
        work_directory,
        file_name_prefix + os.path.basename(edi_process) + file_name_suffix,
    )
    return output_file_path, file_name_prefix, file_name_suffix


def _count_total_lines(file_paths: list[str]) -> int:
    """Count total lines across multiple files."""
    total_lines = 0
    for file_path in file_paths:
        with open(file_path, encoding="utf-8") as file_handle:
            total_lines += sum(1 for _ in file_handle)
    return total_lines


def _validate_split_counts(
    lines_in_edi: int,
    write_counter: int,
    edi_send_list: list[tuple[str, str, str]],
    a_record_count: int,
) -> None:
    """Validate that split output file counts match the source input."""
    output_paths = [output_file for output_file, _, _ in edi_send_list]
    edi_send_list_lines = _count_total_lines(output_paths)

    if lines_in_edi != write_counter:
        raise Exception("not all lines in input were written out")
    if lines_in_edi != edi_send_list_lines:
        raise Exception("total lines in output files do not match input file")
    if len(edi_send_list) != a_record_count:
        raise Exception('mismatched number of "A" records')
    if len(edi_send_list) < 1:
        raise Exception("No Split EDIs")


def _write_split_edi_files(
    work_file_lined: list[str],
    edi_process: str,
    work_directory: str,
    prepend_date_files: bool,
) -> tuple[list[tuple[str, str, str]], int]:
    """Write split invoice files and return metadata list with written line count."""
    f = None
    count = 0
    write_counter = 0
    edi_send_list = []

    try:
        for line_mum, line in enumerate(work_file_lined):
            writeable_line = line
            if writeable_line.startswith("A"):
                count += 1
                line_dict = capture_records(writeable_line)
                if len(edi_send_list) != 0:
                    f.close()
                output_file_path, file_name_prefix, file_name_suffix = (
                    _build_split_file_metadata(
                        line_dict,
                        count,
                        edi_process,
                        work_directory,
                        prepend_date_files,
                    )
                )
                edi_send_list.append(
                    (output_file_path, file_name_prefix, file_name_suffix)
                )
                f = open(output_file_path, "wb")

            if f is None:
                raise ValueError(
                    f"[do_split_edi]: No A record found before line {line_mum}; "
                    "EDI file must start with an A record"
                )

            f.write(writeable_line.replace("\n", "\r\n").encode())
            write_counter += 1

        if f is None:
            raise ValueError("[do_split_edi]: EDI file contained no A records")

        f.close()
    except Exception:
        if f is not None and not f.closed:
            f.close()
        raise

    return edi_send_list, write_counter


def do_split_edi(edi_process, work_directory, parameters_dict):
    """Split a multi-invoice EDI file into individual invoice files.

    Credit for the col_to_excel goes to Nodebody on stackoverflow, at this link: http://stackoverflow.com/a/19154642
    """

    if not os.path.exists(work_directory):
        os.mkdir(work_directory)
    with open(edi_process, encoding="utf-8") as work_file:  # open input file
        lines_in_edi = sum(1 for _ in work_file)
        work_file.seek(0)
        work_file_lined = [n for n in work_file.readlines()]  # make list of lines
        list_of_first_characters = []
        for line in work_file_lined:
            list_of_first_characters.append(line[0])
        a_record_count = list_of_first_characters.count("A")
        if a_record_count > 700:
            return []

        edi_send_list, write_counter = _write_split_edi_files(
            work_file_lined,
            edi_process,
            work_directory,
            parameters_dict["prepend_date_files"],
        )

        _validate_split_counts(
            lines_in_edi,
            write_counter,
            edi_send_list,
            a_record_count,
        )
    return edi_send_list


def do_clear_old_files(folder_path, maximum_files):
    while True:
        files = os.listdir(folder_path)
        if len(files) <= maximum_files:
            break

        def _safe_ctime(f):
            try:
                return os.path.getctime(os.path.join(folder_path, f))
            except OSError:
                return float("inf")

        oldest = min(files, key=_safe_ctime)
        try:
            os.remove(os.path.join(folder_path, oldest))
        except FileNotFoundError:
            pass  # already deleted by another process


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
        runner = create_query_runner(
            username=self.settings["as400_username"],
            password=self.settings["as400_password"],
            dsn=self.settings["as400_address"],
            database="QGPL",
            odbc_driver=f"{self.settings['odbc_driver']}",
        )
        self.query_object = LegacyQueryRunnerAdapter(runner)

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
            """
            SELECT
                sum(CASE odhst.buh6nb WHEN 1 THEN 0 ELSE odhst.bufgpr END),
                sum(CASE odhst.buh6nb WHEN 1 THEN odhst.bufgpr ELSE 0 END)
            FROM
                dacdata.odhst odhst
            WHERE
                odhst.BUHHNB = ?
            """,
            (self._invoice_number,),
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
    b_records: list[str], upc_dict: dict, filter_categories: str, filter_mode: str
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
            vendor_item = int(b_rec_dict["vendor_item"].strip())

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
    filter_mode: str = "include",
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
        _copy_edi_file(input_file, output_file)
        return False

    # Read input file
    lines = _read_edi_lines(input_file)

    if not lines:
        _write_filtered_invoices(output_file, [])
        return False

    invoices = _group_lines_by_invoice(lines)
    filtered_invoices, any_filtered = _filter_invoices_by_category(
        invoices,
        upc_dict,
        filter_categories,
        filter_mode,
    )
    _write_filtered_invoices(output_file, filtered_invoices)
    return any_filtered


def _copy_edi_file(input_file: str, output_file: str) -> None:
    """Copy an EDI file without applying filtering."""
    try:
        with open(input_file, "r") as infile:
            content = infile.read()
        with open(output_file, "w") as outfile:
            outfile.write(content)
    except (IOError, OSError) as e:
        raise ValueError(f"Failed to copy file: {e}")


def _read_edi_lines(input_file: str) -> list[str]:
    """Read all lines from an EDI file."""
    try:
        with open(input_file, "r") as infile:
            return infile.readlines()
    except (IOError, OSError) as e:
        raise ValueError(f"Failed to read input file: {e}")


def _group_lines_by_invoice(lines: list[str]) -> list[list[str]]:
    """Group EDI lines into invoice chunks starting at A records."""
    invoices = []
    current_invoice = []

    for line in lines:
        if line.startswith("A"):
            if current_invoice:
                invoices.append(current_invoice)
            current_invoice = [line]
        elif line.strip():
            current_invoice.append(line)

    if current_invoice:
        invoices.append(current_invoice)
    return invoices


def _split_invoice_records(
    invoice_lines: list[str],
) -> tuple[str | None, list[str], str | None]:
    """Split invoice lines into A, B, and C record collections."""
    a_record = None
    b_records = []
    c_record = None

    for line in invoice_lines:
        if line.startswith("A"):
            a_record = line
        elif line.startswith("B"):
            b_records.append(line)
        elif line.startswith("C"):
            c_record = line

    return a_record, b_records, c_record


def _filter_invoices_by_category(
    invoices: list[list[str]],
    upc_dict: dict,
    filter_categories: str,
    filter_mode: str,
) -> tuple[list[list[str]], bool]:
    """Filter invoice B records and drop invoices with no remaining B records."""
    filtered_invoices = []
    any_filtered = False

    for invoice_lines in invoices:
        a_record, b_records, c_record = _split_invoice_records(invoice_lines)
        filtered_b_records = filter_b_records_by_category(
            b_records, upc_dict, filter_categories, filter_mode
        )

        if len(filtered_b_records) != len(b_records):
            any_filtered = True

        if not filtered_b_records:
            any_filtered = True
            continue

        filtered_invoice = [a_record] + filtered_b_records
        if c_record:
            filtered_invoice.append(c_record)
        filtered_invoices.append(filtered_invoice)

    return filtered_invoices, any_filtered


def _write_filtered_invoices(output_file: str, invoices: list[list[str]]) -> None:
    """Write filtered invoice lines to the output EDI file."""
    try:
        with open(output_file, "w") as outfile:
            for invoice in invoices:
                outfile.writelines(invoice)
    except (IOError, OSError) as e:
        raise ValueError(f"Failed to write output file: {e}")
