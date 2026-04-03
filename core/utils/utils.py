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
from typing import Callable

MAX_A_RECORD_COUNT = 700

# Import from core modules for backward compatibility
from core.edi.edi_parser import capture_records
from core.edi.edi_transformer import convert_to_price  # noqa: F401
from core.edi.edi_transformer import convert_to_price_decimal  # noqa: F401
from core.edi.edi_transformer import dac_str_int_to_int  # noqa: F401
from core.edi.edi_transformer import detect_invoice_is_credit  # noqa: F401
from core.edi.inv_fetcher import InvFetcher as invFetcher  # noqa: F401
from core.edi.upc_utils import calc_check_digit  # noqa: F401
from core.edi.upc_utils import (  # noqa: F401
    convert_upce_to_upca as convert_UPCE_to_UPCA,
)
from core.structured_logging import get_logger, log_file_operation
from core.utils.date_utils import dactime_from_datetime  # noqa: F401
from core.utils.date_utils import dactime_from_invtime  # noqa: F401
from core.utils.date_utils import datetime_from_dactime  # noqa: F401
from core.utils.date_utils import datetime_from_invtime  # noqa: F401

logger = get_logger(__name__)


def _col_to_excel(col: int) -> str:
    """Convert a 1-based column index to Excel column letters.

    Uses a base-26 conversion algorithm where 1->A, 2->B, ..., 26->Z,
    27->AA, 28->AB, etc.

    Args:
        col: 1-based column index (must be positive).

    Returns:
        Excel-style column letter(s), e.g., "A", "Z", "AA", "AB".

    Examples:
        >>> _col_to_excel(1)
        'A'
        >>> _col_to_excel(26)
        'Z'
        >>> _col_to_excel(27)
        'AA'

    """
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
    *,
    prepend_date_files: bool,
) -> tuple[str, str, str]:
    """Build output path and filename metadata for a split EDI invoice.

    Constructs the output file path and name components for a single
    invoice extracted from a multi-invoice EDI file. The filename includes
    an Excel-style column letter prefix (A, B, C, ...) and optionally
    the invoice date.

    Args:
        line_dict: Parsed A record fields containing invoice metadata.
        count: Invoice sequence number (1-based) within the EDI file.
        edi_process: Path to the original EDI file being processed.
        work_directory: Directory where split output files are written.
        prepend_date_files: If True, prefix filenames with formatted invoice date.

    Returns:
        Tuple of (output_file_path, file_name_prefix, file_name_suffix)
        where suffix is ".cr" for credit invoices or ".inv" for regular.

    """
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
    """Count total lines across multiple files.

    Args:
        file_paths: List of file paths to count lines in.

    Returns:
        Total number of lines across all files.

    """
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
    """Validate that split output file counts match the source input.

    Ensures data integrity by verifying that all lines from the input
    EDI file were written to output files and that the number of A records
    matches the number of output files.

    Args:
        lines_in_edi: Total line count in the original EDI file.
        write_counter: Total lines written to all output files.
        edi_send_list: List of (output_path, prefix, suffix) tuples for split files.
        a_record_count: Number of A records (invoices) in the original file.

    Raises:
        Exception: If line counts or A record counts don't match expectations.

    """
    output_paths = [output_file for output_file, _, _ in edi_send_list]
    edi_send_list_lines = _count_total_lines(output_paths)

    if lines_in_edi != write_counter:
        raise Exception("not all lines in input were written out")
    if lines_in_edi != edi_send_list_lines:
        raise Exception("total lines in output files do not match input file")
    if len(edi_send_list) != a_record_count:
        raise Exception('mismatched number of "A" records')
    if not edi_send_list:
        raise Exception("No Split EDIs")


def _write_split_edi_files(
    work_file_lined: list[str],
    edi_process: str,
    work_directory: str,
    *,
    prepend_date_files: bool,
) -> tuple[list[tuple[str, str, str]], int]:
    """Write split invoice files and return metadata list with written line count.

    Iterates through EDI lines, creating a new output file for each A record
    (invoice header) and writing subsequent B/C records to that file until
    the next A record is encountered.

    Args:
        work_file_lined: All lines from the input EDI file.
        edi_process: Path to the original EDI file (used for basename).
        work_directory: Directory where split output files are written.
        prepend_date_files: If True, prefix filenames with formatted invoice date.

    Returns:
        Tuple of (edi_send_list, write_counter) where edi_send_list is a list
        of (output_path, prefix, suffix) tuples and write_counter is total
        lines written across all output files.

    Raises:
        ValueError: If no A record is found before data lines, or if file has no A records.

    """
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
                if edi_send_list:
                    f.close()
                output_file_path, file_name_prefix, file_name_suffix = (
                    _build_split_file_metadata(
                        line_dict,
                        count,
                        edi_process,
                        work_directory,
                        prepend_date_files=prepend_date_files,
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


def do_split_edi(
    edi_process: str, work_directory: str, parameters_dict: dict
) -> list[tuple[str, str, str]]:
    """Split a multi-invoice EDI file into individual invoice files.

    Reads an EDI file containing multiple invoices (each starting with an A record)
    and splits it into separate files, one per invoice. Output filenames include
    an alphabetical prefix (A_, B_, C_, ...) and optionally the invoice date.

    Args:
        edi_process: Path to the input EDI file to split.
        work_directory: Directory where split output files will be written.
        parameters_dict: Configuration dictionary containing:
            - prepend_date_files (bool): Whether to prefix filenames with dates.

    Returns:
        List of tuples (output_path, file_prefix, file_suffix) for each split file,
        or empty list if the file exceeds MAX_A_RECORD_COUNT invoices.

    Raises:
        Exception: If output line counts or A record counts don't match input.
        ValueError: If the EDI file is malformed (missing A records).

    """

    if not os.path.exists(work_directory):
        os.mkdir(work_directory)
    with open(edi_process, encoding="utf-8") as work_file:  # open input file
        work_file_lined = work_file.readlines()  # make list of lines
        lines_in_edi = len(work_file_lined)
        a_record_count = sum(1 for line in work_file_lined if line.startswith("A"))
        if a_record_count > MAX_A_RECORD_COUNT:
            return []

        edi_send_list, write_counter = _write_split_edi_files(
            work_file_lined,
            edi_process,
            work_directory,
            prepend_date_files=parameters_dict["prepend_date_files"],
        )

        _validate_split_counts(
            lines_in_edi,
            write_counter,
            edi_send_list,
            a_record_count,
        )
    return edi_send_list


def do_clear_old_files(folder_path: str, maximum_files: int) -> None:
    """Delete oldest files in a folder until the count is at or below the maximum.

    Uses a while loop rather than a simple if check because files may be
    added concurrently by other processes. Each iteration re-scans the
    directory to get an accurate current count.

    Args:
        folder_path: Path to the folder to clean up.
        maximum_files: Maximum number of files to allow before deletion starts.

    """
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
        oldest_path = os.path.join(folder_path, oldest)
        try:
            os.remove(oldest_path)
            log_file_operation(
                logger,
                "delete",
                oldest_path,
                file_type="log",
                success=True,
                context={"reason": "cleanup", "max_files": maximum_files},
            )
        except FileNotFoundError:
            pass  # already deleted by another process
        except Exception as e:
            log_file_operation(
                logger,
                "delete",
                oldest_path,
                file_type="log",
                success=False,
                error=e,
                context={"reason": "cleanup", "max_files": maximum_files},
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


def add_row(csv_writer, rowdict: dict) -> None:
    """Write a dictionary row to a CSV file.

    Args:
        csv_writer: A csv.writer object to write to.
        rowdict: A dictionary whose values will be written as a row.

    """
    csv_writer.writerow(rowdict.values())


class CRecGenerator:
    """Class for generating split C records for prepaid/non-prepaid sales tax.

    This class queries the database to split sales tax totals into prepaid and
    non-prepaid amounts, then writes them as separate C records.
    """

    def __init__(self, settings_dict: dict) -> None:
        """Initialize the C record generator.

        Args:
            settings_dict: Dictionary containing database connection settings.
                Must include: as400_username, as400_password, as400_address.

        """
        self.query_object = None
        self._invoice_number = "0"
        self.unappended_records = False
        self.settings = settings_dict

    def _db_connect(self) -> None:
        """Establish database connection using the configured settings.

        Creates a query runner from the stored settings dictionary for
        executing SQL queries against the AS400 database.

        """
        from core.database.query_runner import create_query_runner_from_settings

        self.query_object = create_query_runner_from_settings(self.settings)

    def set_invoice_number(self, invoice_number: str) -> None:
        """Set the current invoice number and mark records as unappended.

        Args:
            invoice_number: The invoice number to query for sales tax data.

        """
        self._invoice_number = invoice_number
        self.unappended_records = True

    def fetch_splitted_sales_tax_totals(
        self, write_func: Callable[[str], None]
    ) -> None:
        """Fetch and write split sales tax totals as C records.

        Queries the database for prepaid and non-prepaid sales tax amounts
        for the current invoice number, then writes them as separate C records.

        Args:
            write_func: A callable that accepts a string to write (e.g., file.write).

        """
        if self.query_object is None:
            self._db_connect()

        qry_ret = self.query_object.run_query(
            """
            SELECT
                SUM(CASE odhst.buh6nb WHEN 1 THEN 0 ELSE odhst.bufgpr END) AS non_prepaid,
                SUM(CASE odhst.buh6nb WHEN 1 THEN odhst.bufgpr ELSE 0 END) AS prepaid
            FROM
                dacdata.odhst odhst
            WHERE
                odhst.BUHHNB = ?
            """,
            (self._invoice_number,),
        )

        if not qry_ret:
            return

        qry_ret_non_prepaid = qry_ret[0]["non_prepaid"]
        qry_ret_prepaid = qry_ret[0]["prepaid"]

        def _write_line(typestr: str, amount: int, wprocfile) -> None:
            descstr = typestr.ljust(25, " ")
            if amount < 0:
                amount_builder = amount - (amount * 2)
            else:
                amount_builder = amount

            amountstr = str(amount_builder).replace(".", "").rjust(9, "0")
            if amount < 0:
                amountstr = "-" + amountstr[1:]
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

    # Validate record fields can be parsed
    try:
        item_number = int(record["vendor_item"].strip())
        float(record["unit_cost"].strip())
        test_unit_multiplier = int(record["unit_multiplier"].strip())
        if test_unit_multiplier == 0:
            raise ValueError("unit_multiplier cannot be zero")
        int(record["qty_of_units"].strip())
    except Exception:
        logger.debug("cannot parse b record field, skipping")
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
        logger.debug("error applying retail UOM transform: %s", error)
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
