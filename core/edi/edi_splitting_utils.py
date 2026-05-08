"""EDI file splitting and category filtering utilities.

Extracted from core/utils/utils.py to colocate EDI-specific logic
with the rest of the EDI processing pipeline.
"""

import os
from datetime import datetime

from core.edi.edi_parser import capture_records
from core.structured_logging import get_logger

MAX_A_RECORD_COUNT = 700

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

    Logs are included for file creation and any path validation issues.

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
        ValueError: If no A record is found before data lines, or if
            file has no A records.

    """
    count = 0
    write_counter = 0
    edi_send_list = []
    current_file = None

    # Enforce stable absolute work directory path
    work_directory = os.path.abspath(work_directory)

    try:
        logger.debug(
            "_write_split_edi_files starting "
            "(source=%s, work_directory=%s, prepend_date_files=%s)",
            edi_process,
            work_directory,
            prepend_date_files,
        )

        for line_mum, line in enumerate(work_file_lined):
            writeable_line = line

            if writeable_line.startswith("A"):
                count += 1
                line_dict = capture_records(writeable_line)

                if current_file is not None:
                    current_file.close()

                output_file_path, file_name_prefix, file_name_suffix = (
                    _build_split_file_metadata(
                        line_dict,
                        count,
                        edi_process,
                        work_directory,
                        prepend_date_files=prepend_date_files,
                    )
                )
                logger.debug("create split file %s (count=%d)", output_file_path, count)

                if not os.path.abspath(output_file_path).startswith(
                    work_directory + os.sep
                ):
                    logger.error(
                        "Invalid output path generated (potential path traversal): %s",
                        output_file_path,
                    )
                    raise ValueError(
                        "Invalid output path generated (potential path traversal)"
                    )

                edi_send_list.append(
                    (output_file_path, file_name_prefix, file_name_suffix)
                )

                current_file = open(output_file_path, "wb")

            if current_file is None:
                raise ValueError(
                    f"[do_split_edi]: No A record found before line {line_mum}; "
                    "EDI file must start with an A record"
                )

            current_file.write(writeable_line.replace("\n", "\r\n").encode())
            write_counter += 1

        if current_file is None:
            raise ValueError("[do_split_edi]: EDI file contained no A records")

    finally:
        if current_file is not None and not current_file.closed:
            current_file.close()

    logger.info(
        "_write_split_edi_files complete (source=%s, outputs=%s, lines=%d)",
        edi_process,
        len(edi_send_list),
        write_counter,
    )

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

    work_directory = os.path.abspath(work_directory)
    os.makedirs(work_directory, exist_ok=True)

    if not os.path.exists(edi_process):
        raise FileNotFoundError(f"EDI source file not found: {edi_process}")

    logger.info(
        "do_split_edi start (source=%s, work_directory=%s)",
        edi_process,
        work_directory,
    )

    with open(edi_process, encoding="utf-8") as work_file:  # open input file
        work_file_lined = work_file.readlines()  # make list of lines
        lines_in_edi = len(work_file_lined)
        a_record_count = sum(1 for line in work_file_lined if line.startswith("A"))
        logger.debug(
            "do_split_edi counts: lines=%d, a_records=%d", lines_in_edi, a_record_count
        )
        if a_record_count > MAX_A_RECORD_COUNT:
            logger.warning(
                "do_split_edi abort, too many A records (%d > %d)",
                a_record_count,
                MAX_A_RECORD_COUNT,
            )
            return []

        prepended = parameters_dict.get("prepend_date_files", False)
        edi_send_list, write_counter = _write_split_edi_files(
            work_file_lined,
            edi_process,
            work_directory,
            prepend_date_files=prepended,
        )

        _validate_split_counts(
            lines_in_edi,
            write_counter,
            edi_send_list,
            a_record_count,
        )

    logger.info(
        "do_split_edi complete (source=%s, output_files=%d)",
        edi_process,
        len(edi_send_list),
    )
    return edi_send_list


def filter_b_records_by_category(
    b_records: list[str], upc_dict: dict, filter_categories: str, filter_mode: str
) -> list[str]:
    """Filter B records based on item category.

    Args:
        b_records: List of B record lines to filter
        upc_dict: Dictionary mapping item numbers to
            [category, upc1, upc2, upc3, upc4]
        filter_categories: String of comma-separated categories or "ALL"
        filter_mode: "include" (keep these) or "exclude" (remove these)

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
        upc_dict: Dictionary mapping item numbers to
            [category, upc1, upc2, upc3, upc4]
        filter_categories: Comma-separated categories or "ALL"
        filter_mode: "include" (keep only these categories) or
            "exclude" (remove these categories)

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
