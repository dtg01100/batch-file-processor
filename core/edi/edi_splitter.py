"""EDI file splitting logic.

This module provides the EDISplitter class for splitting EDI files
into individual invoice files with support for category filtering.
"""

import os
from dataclasses import dataclass
from typing import Protocol, runtime_checkable, Optional

from core.edi.edi_parser import capture_records
from core.edi.upc_utils import calc_check_digit


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
        with open(path, 'w', encoding=encoding) as f:
            f.write(content)
    
    def write_binary(self, path: str, content: bytes) -> None:
        """Write binary content to file."""
        with open(path, 'wb') as f:
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
    """
    output_directory: str
    prepend_date: bool = False
    max_invoices: int = 0


@dataclass
class SplitResult:
    """Result of EDI split operation.
    
    Attributes:
        output_files: List of tuples (file_path, prefix, suffix)
        skipped_invoices: Number of invoices skipped due to filtering
        total_lines_written: Total lines written across all files
    """
    output_files: list[tuple[str, str, str]]
    skipped_invoices: int
    total_lines_written: int


def _col_to_excel(col: int) -> str:
    """Convert column number to Excel-style letter.
    
    Args:
        col: 1-based column number
        
    Returns:
        Excel-style column letter (A, B, ..., Z, AA, AB, ...)
        
    Credit:
        Nodebody on StackOverflow: http://stackoverflow.com/a/19154642
    """
    excel_col = str()
    div = col
    while div:
        (div, mod) = divmod(div - 1, 26)
        excel_col = chr(mod + 65) + excel_col
    return excel_col


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
    
    categories_list = [c.strip() for c in filter_categories.split(",")]
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
                item_category = str(upc_dict[vendor_item][0])
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
        with open(input_file, 'r') as infile:
            content = infile.read()
        with open(output_file, 'w') as outfile:
            outfile.write(content)
        return False
    
    # Read input file
    with open(input_file, 'r') as infile:
        lines = infile.readlines()
    
    if not lines:
        # Empty file - just copy it
        with open(output_file, 'w') as outfile:
            pass
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
    with open(output_file, 'w') as outfile:
        for invoice in filtered_invoices:
            outfile.writelines(invoice)
    
    return any_filtered


class EDISplitter:
    """Splits EDI files into individual invoice files.
    
    This class handles the splitting of EDI files by A records (invoices),
    with optional filtering of B records by category.
    """
    
    def __init__(self, filesystem: FilesystemProtocol):
        """Initialize EDISplitter with filesystem.
        
        Args:
            filesystem: Filesystem implementation for I/O operations
        """
        self.filesystem = filesystem
    
    def split_edi(
        self,
        content: str,
        config: SplitConfig,
        upc_dict: dict = None,
        filter_categories: str = "ALL",
        filter_mode: str = "include"
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
        lines = content.split('\n')
        
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
        current_a_record: Optional[str] = None
        current_c_records: list[str] = []
        current_output_path: Optional[str] = None
        current_file_content: list[bytes] = []
        count = 0
        
        for line in lines:
            if line.startswith("A"):
                # Process previous invoice if exists
                if current_a_record is not None and current_output_path is not None:
                    filtered_b_records = filter_b_records_by_category(
                        current_b_records, upc_dict, filter_categories, filter_mode
                    )
                    
                    if filtered_b_records:
                        # Write A record
                        current_file_content.append(current_a_record.replace('\n', "\r\n").encode())
                        write_counter += 1
                        # Write filtered B records
                        for b_rec in filtered_b_records:
                            current_file_content.append(b_rec.replace('\n', "\r\n").encode())
                            write_counter += 1
                        # Write C records
                        for c_rec in current_c_records:
                            current_file_content.append(c_rec.replace('\n', "\r\n").encode())
                            write_counter += 1
                        # Write to filesystem
                        self.filesystem.write_binary(current_output_path, b''.join(current_file_content))
                    else:
                        # No B records after filtering - skip this invoice
                        skipped_invoices += 1
                        if output_files:
                            output_files.pop()
                
                # Start new invoice
                count += 1
                prepend_letters = _col_to_excel(count)
                line_dict = capture_records(line)
                
                if int(line_dict['invoice_total']) < 0:
                    file_name_suffix = '.cr'
                else:
                    file_name_suffix = '.inv'
                
                file_name_prefix = prepend_letters + "_"
                if config.prepend_date:
                    from datetime import datetime
                    datetime_from_arec = datetime.strptime(line_dict['invoice_date'], "%m%d%y")
                    inv_date = datetime.strftime(datetime_from_arec, "%d %b, %Y")
                    file_name_prefix = inv_date + "_" + file_name_prefix
                
                output_path = os.path.join(config.output_directory, file_name_prefix + "split" + file_name_suffix)
                output_files.append((output_path, file_name_prefix, file_name_suffix))
                
                # Reset for new invoice
                current_a_record = line
                current_b_records = []
                current_c_records = []
                current_output_path = output_path
                current_file_content = []
                
            elif line.startswith("B"):
                current_b_records.append(line)
            elif line.startswith("C"):
                current_c_records.append(line)
        
        # Process last invoice
        if current_a_record is not None and current_output_path is not None:
            filtered_b_records = filter_b_records_by_category(
                current_b_records, upc_dict, filter_categories, filter_mode
            )
            
            if filtered_b_records:
                # Write A record
                current_file_content.append(current_a_record.replace('\n', "\r\n").encode())
                write_counter += 1
                # Write filtered B records
                for b_rec in filtered_b_records:
                    current_file_content.append(b_rec.replace('\n', "\r\n").encode())
                    write_counter += 1
                # Write C records
                for c_rec in current_c_records:
                    current_file_content.append(c_rec.replace('\n', "\r\n").encode())
                    write_counter += 1
                # Write to filesystem
                self.filesystem.write_binary(current_output_path, b''.join(current_file_content))
            else:
                # No B records after filtering - skip this invoice
                skipped_invoices += 1
                if output_files:
                    output_files.pop()
        
        if not output_files:
            raise ValueError("No Split EDIs (all invoices may have been filtered out)")
        
        return SplitResult(output_files, skipped_invoices, write_counter)
    
    def do_split_edi(
        self,
        input_path: str,
        config: SplitConfig,
        upc_dict: dict = None,
        filter_categories: str = "ALL",
        filter_mode: str = "include"
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
        return self.split_edi(content, config, upc_dict, filter_categories, filter_mode)
