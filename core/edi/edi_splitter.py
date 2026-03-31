"""EDI file splitting logic.

This module provides the EDISplitter class for splitting EDI files
into individual invoice files with support for category filtering.
"""

import os
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from core.edi.edi_parser import capture_records
from core.utils.utils import _col_to_excel, filter_b_records_by_category


@runtime_checkable
class FilesystemProtocol(Protocol):
    """Protocol for filesystem operations.

    This protocol enables testing without actual filesystem access.
    """

    def read_file(self, path: str, encoding: str = "utf-8") -> str:
        """Read file contents.

        Args:
            path: File path to read
            encoding: File encoding (default: utf-8)

        Returns:
            File contents as string

        """
        ...

    def write_file(self, path: str, content: str, encoding: str = "utf-8") -> None:
        """Write content to file.

        Args:
            path: File path to write
            content: Content to write
            encoding: File encoding (default: utf-8)

        """
        ...

    def write_binary(self, path: str, content: bytes) -> None:
        """Write binary content to file.

        Args:
            path: File path to write
            content: Binary content to write

        """
        ...

    def file_exists(self, path: str) -> bool:
        """Check if file exists.

        Args:
            path: File path to check

        Returns:
            True if file exists

        """
        ...

    def directory_exists(self, path: str) -> bool:
        """Check if directory exists.

        Args:
            path: Directory path to check

        Returns:
            True if directory exists

        """
        ...

    def create_directory(self, path: str) -> None:
        """Create directory if it doesn't exist.

        Args:
            path: Directory path to create

        """
        ...

    def remove_file(self, path: str) -> None:
        """Remove a file.

        Args:
            path: File path to remove

        """
        ...

    def list_files(self, path: str) -> list[str]:
        """List files in directory.

        Args:
            path: Directory path to list

        Returns:
            List of file names

        """
        ...


class RealFilesystem:
    """Real filesystem implementation using os module."""

    def read_file(self, path: str, encoding: str = "utf-8") -> str:
        """Read file contents."""
        with open(path, encoding=encoding) as f:
            return f.read()

    def write_file(self, path: str, content: str, encoding: str = "utf-8") -> None:
        """Write content to file."""
        with open(path, "w", encoding=encoding) as f:
            f.write(content)

    def write_binary(self, path: str, content: bytes) -> None:
        """Write binary content to file."""
        with open(path, "wb") as f:
            f.write(content)

    def file_exists(self, path: str) -> bool:
        """Check if file exists."""
        return os.path.isfile(path)

    def directory_exists(self, path: str) -> bool:
        """Check if directory exists."""
        return os.path.isdir(path)

    def create_directory(self, path: str) -> None:
        """Create directory if it doesn't exist."""
        os.makedirs(path, exist_ok=True)

    def remove_file(self, path: str) -> None:
        """Remove a file."""
        os.remove(path)

    def list_files(self, path: str) -> list[str]:
        """List files in directory."""
        return os.listdir(path)


@dataclass
class SplitConfig:
    """Configuration for EDI splitting.

    Attributes:
        output_directory: Directory to write split files
        prepend_date: Whether to prepend date to filenames
        max_invoices: Maximum number of invoices (0 = no limit)
        filename_stem: Original input file stem to prepend to split file names,
            ensuring uniqueness when multiple files are split to the same directory.
            If empty, split files are named A_split.inv, B_split.cr, etc.

    """

    output_directory: str
    prepend_date: bool = False
    max_invoices: int = 0
    filename_stem: str = ""


@dataclass
class SplitResult:
    """Result of EDI split operation.

    Attributes:
        output_files: List of tuples (file_path, prefix, suffix)
        skipped_invoices: Number of invoices skipped due to filtering
        total_lines_written: Total lines written across all files
        original_invoice_count: Number of invoices in source file before filtering

    """

    output_files: list[tuple[str, str, str]]
    skipped_invoices: int
    total_lines_written: int
    original_invoice_count: int = 0


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
    if filter_categories == "ALL":
        _copy_file(input_file, output_file)
        return False

    lines = _read_lines(input_file)
    if not lines:
        _write_invoices(output_file, [])
        return False

    invoices = _group_lines_by_invoice(lines)
    filtered_invoices, any_filtered = _filter_invoices(
        invoices,
        upc_dict,
        filter_categories,
        filter_mode,
    )
    _write_invoices(output_file, filtered_invoices)
    return any_filtered


def _copy_file(input_file: str, output_file: str) -> None:
    """Copy input text file to output file."""
    with open(input_file, "r", encoding="utf-8") as infile:
        content = infile.read()
    with open(output_file, "w", encoding="utf-8") as outfile:
        outfile.write(content)


def _read_lines(input_file: str) -> list[str]:
    """Read all text lines from an input file."""
    with open(input_file, "r", encoding="utf-8") as infile:
        return infile.readlines()


def _group_lines_by_invoice(lines: list[str]) -> list[list[str]]:
    """Group EDI lines into invoice chunks starting with A records."""
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
) -> tuple[str | None, list[str], list[str]]:
    """Split invoice lines into A record, B records, and C records."""
    a_record = None
    b_records = []
    c_records = []

    for line in invoice_lines:
        if line.startswith("A"):
            a_record = line
        elif line.startswith("B"):
            b_records.append(line)
        elif line.startswith("C"):
            c_records.append(line)

    return a_record, b_records, c_records


def _filter_invoices(
    invoices: list[list[str]],
    upc_dict: dict,
    filter_categories: str,
    filter_mode: str,
) -> tuple[list[list[str]], bool]:
    """Filter B records per invoice and drop invoices with no remaining B records."""
    filtered_invoices = []
    any_filtered = False

    for invoice_lines in invoices:
        a_record, b_records, c_records = _split_invoice_records(invoice_lines)
        filtered_b_records = filter_b_records_by_category(
            b_records, upc_dict, filter_categories, filter_mode
        )

        if len(filtered_b_records) != len(b_records):
            any_filtered = True

        if not filtered_b_records:
            any_filtered = True
            continue

        filtered_invoice = [a_record] + filtered_b_records
        if c_records:
            filtered_invoice.extend(c_records)
        filtered_invoices.append(filtered_invoice)

    return filtered_invoices, any_filtered


def _write_invoices(output_file: str, invoices: list[list[str]]) -> None:
    """Write invoice line groups to output file."""
    with open(output_file, "w") as outfile:
        for invoice in invoices:
            outfile.writelines(invoice)


def _build_split_filename(
    line_dict: dict,
    count: int,
    config: SplitConfig,
) -> tuple[str, str, str]:
    """Build output path, prefix, and suffix for a split invoice file."""
    prepend_letters = _col_to_excel(count)
    file_name_suffix = ".cr" if int(line_dict["invoice_total"]) < 0 else ".inv"

    file_name_prefix = prepend_letters + "_"

    if config.prepend_date:
        from datetime import datetime

        datetime_from_arec = datetime.strptime(line_dict["invoice_date"], "%m%d%y")
        inv_date = datetime.strftime(datetime_from_arec, "%d %b, %Y")
        file_name_prefix = inv_date + "_" + file_name_prefix

    middle_part = config.filename_stem if config.filename_stem else "split"
    output_path = os.path.join(
        config.output_directory,
        file_name_prefix + middle_part + file_name_suffix,
    )
    return output_path, file_name_prefix, file_name_suffix


def _write_invoice_binary(
    filesystem: FilesystemProtocol,
    output_path: str,
    a_record: str,
    b_records: list[str],
    c_records: list[str],
) -> int:
    """Write one invoice to binary output and return line count written."""
    output_chunks: list[bytes] = []
    output_chunks.append(_ensure_crlf(a_record).encode())

    for b_rec in b_records:
        output_chunks.append(_ensure_crlf(b_rec).encode())
    for c_rec in c_records:
        output_chunks.append(_ensure_crlf(c_rec).encode())

    filesystem.write_binary(output_path, b"".join(output_chunks))
    return 1 + len(b_records) + len(c_records)


def _ensure_crlf(line: str) -> str:
    """Ensure a line ends with CRLF, proper for EDI files.

    Handles lines that may have no line ending, CR only, LF only,
    or CRLF already present.
    """
    if line.endswith("\r\n"):
        return line
    if line.endswith("\r"):
        return line + "\n"
    if line.endswith("\n"):
        return line.rstrip("\n") + "\r\n"
    return line + "\r\n"


def _finalize_current_invoice(
    filesystem: FilesystemProtocol,
    current_a_record: str | None,
    current_b_records: list[str],
    current_c_records: list[str],
    current_output_path: str | None,
    output_files: list[tuple[str, str, str]],
    upc_dict: dict,
    filter_categories: str,
    filter_mode: str,
) -> tuple[int, int]:
    """Finalize current invoice; returns (skipped_delta, written_lines_delta)."""
    if current_a_record is None or current_output_path is None:
        return 0, 0

    filtered_b_records = filter_b_records_by_category(
        current_b_records, upc_dict, filter_categories, filter_mode
    )

    if not filtered_b_records:
        if output_files:
            output_files.pop()
        return 1, 0

    written_lines = _write_invoice_binary(
        filesystem,
        current_output_path,
        current_a_record,
        filtered_b_records,
        current_c_records,
    )
    return 0, written_lines


class EDISplitter:
    """Splits EDI files into individual invoice files.

    This class handles the splitting of EDI files by A records (invoices),
    with optional filtering of B records by category.
    """

    def __init__(self, filesystem: FilesystemProtocol) -> None:
        """Initialize EDISplitter with filesystem.

        Args:
            filesystem: Filesystem implementation for I/O operations

        """
        self.filesystem = filesystem

    def _start_new_invoice(
        self,
        line: str,
        count: int,
        config: SplitConfig,
    ) -> tuple[
        int,
        str | None,
        list[str],
        list[str],
        str | None,
        tuple[str, str, str] | None,
    ]:
        """Start a new invoice and return updated state.

        Args:
            line: The A record line
            count: Current invoice count
            config: Split configuration

        Returns:
            Tuple of (count, current_a_record, current_b_records,
                     current_c_records, current_output_path, output_file_entry)
            output_file_entry is None if the line couldn't be parsed

        """
        count += 1
        line_dict = capture_records(line)

        if line_dict is None:
            return count, None, [], [], None, None

        output_path, file_name_prefix, file_name_suffix = _build_split_filename(
            line_dict,
            count,
            config,
        )
        return (
            count,
            line,
            [],
            [],
            output_path,
            (output_path, file_name_prefix, file_name_suffix),
        )

    def _process_b_record(
        self,
        line: str,
        current_b_records: list[str],
    ) -> list[str]:
        """Append a B record to the current invoice."""
        current_b_records.append(line)
        return current_b_records

    def _process_c_record(
        self,
        line: str,
        current_c_records: list[str],
    ) -> list[str]:
        """Append a C record to the current invoice."""
        current_c_records.append(line)
        return current_c_records

    def split_edi(
        self,
        content: str,
        config: SplitConfig,
        upc_dict: dict = None,
        filter_categories: str = "ALL",
        filter_mode: str = "include",
    ) -> SplitResult:
        """Split EDI content into multiple invoice files.

        Args:
            content: EDI file content as string
            config: Split configuration
            upc_dict: Optional dictionary for category filtering
            filter_categories: Categories to filter ("ALL" or comma-separated)
            filter_mode: "include" or "exclude" for filtering

        Returns:
            SplitResult with output files and statistics

        Raises:
            ValueError: If no valid invoices after filtering

        """
        lines = content.splitlines()

        # Count A records to check max limit
        a_record_count = sum(1 for line in lines if line.startswith("A"))
        if config.max_invoices > 0 and a_record_count > config.max_invoices:
            return SplitResult([], 0, 0)

        # Ensure output directory exists
        if not self.filesystem.directory_exists(config.output_directory):
            self.filesystem.create_directory(config.output_directory)

        output_files: list[tuple[str, str, str]] = []
        skipped_invoices = 0
        write_counter = 0

        current_b_records: list[str] = []
        current_a_record: str | None = None
        current_c_records: list[str] = []
        current_output_path: str | None = None
        count = 0

        for line in lines:
            if line.startswith("A"):
                skipped_delta, written_delta = _finalize_current_invoice(
                    self.filesystem,
                    current_a_record,
                    current_b_records,
                    current_c_records,
                    current_output_path,
                    output_files,
                    upc_dict,
                    filter_categories,
                    filter_mode,
                )
                skipped_invoices += skipped_delta
                write_counter += written_delta

                result = self._start_new_invoice(line, count, config)
                (
                    count,
                    current_a_record,
                    current_b_records,
                    current_c_records,
                    current_output_path,
                    output_file_entry,
                ) = result
                if output_file_entry is not None:
                    output_files.append(output_file_entry)

            elif line.startswith("B"):
                current_b_records = self._process_b_record(line, current_b_records)
            elif line.startswith("C"):
                current_c_records = self._process_c_record(line, current_c_records)

        # Process last invoice
        skipped_delta, written_delta = _finalize_current_invoice(
            self.filesystem,
            current_a_record,
            current_b_records,
            current_c_records,
            current_output_path,
            output_files,
            upc_dict,
            filter_categories,
            filter_mode,
        )
        skipped_invoices += skipped_delta
        write_counter += written_delta

        if not output_files:
            raise ValueError("No Split EDIs (all invoices may have been filtered out)")

        original_invoice_count = count
        return SplitResult(
            output_files, skipped_invoices, write_counter, original_invoice_count
        )

    def do_split_edi(
        self,
        input_path: str,
        config: SplitConfig,
        upc_dict: dict = None,
        filter_categories: str = "ALL",
        filter_mode: str = "include",
    ) -> SplitResult:
        """Split EDI file from path.

        Args:
            input_path: Path to EDI file
            config: Split configuration
            upc_dict: Optional dictionary for category filtering
            filter_categories: Categories to filter
            filter_mode: "include" or "exclude"

        Returns:
            SplitResult with output files and statistics

        """
        content = self.filesystem.read_file(input_path)
        # Populate filename_stem from input path so split files get unique names
        # when multiple source files are split to the same output directory.
        if not config.filename_stem:
            config = SplitConfig(
                output_directory=config.output_directory,
                prepend_date=config.prepend_date,
                max_invoices=config.max_invoices,
                filename_stem=os.path.basename(input_path),
            )
        return self.split_edi(content, config, upc_dict, filter_categories, filter_mode)
