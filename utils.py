"""Utility functions for EDI processing.

This module provides backward-compatible imports from the refactored
core.edi module. New code should import directly from core.edi.

Backward Compatibility:
    - All existing functions remain available
    - invFetcher class wraps core.edi.inv_fetcher.InvFetcher
    - UPC functions delegate to core.edi.upc_utils
    - EDI parsing functions delegate to core.edi.edi_parser
"""

from datetime import datetime
import os
from typing import Optional

# Import refactored components
from core.edi.upc_utils import (
    calc_check_digit,
    convert_upce_to_upca as _convert_upce_to_upca,
    validate_upc,
)
from core.edi.edi_parser import (
    capture_records,
    ARecord,
    BRecord,
    CRecord,
)
from core.edi.edi_splitter import (
    filter_b_records_by_category,
    RealFilesystem,
    EDISplitter,
    SplitConfig,
)
from core.database.query_runner import (
    QueryRunner,
    PyODBCConnection,
    ConnectionConfig,
)


# Legacy invFetcher class for backward compatibility
class invFetcher:
    """Legacy invoice fetcher class.
    
    This class provides backward compatibility with existing code.
    New code should use core.edi.inv_fetcher.InvFetcher directly.
    """
    
    def __init__(self, settings_dict):
        """Initialize invFetcher with settings dictionary.
        
        Args:
            settings_dict: Dictionary containing database connection settings
        """
        self.query_object = None
        self.settings = settings_dict
        self.last_invoice_number = 0
        self.uom_lut = {0: "N/A"}
        self.last_invno = 0
        self.po = ""
        self.custname = ""
        self.custno = 0

    def _db_connect(self):
        """Establish database connection using settings."""
        config = ConnectionConfig(
            username=self.settings["as400_username"],
            password=self.settings["as400_password"],
            dsn=self.settings["as400_address"],
        )
        connection = PyODBCConnection(config)
        self.query_object = QueryRunner(connection)

    def _run_qry(self, qry_str):
        """Run a query, connecting if necessary.
        
        Args:
            qry_str: SQL query string
            
        Returns:
            Query results as list of tuples
        """
        if self.query_object is None:
            self._db_connect()
        # Convert dict results to tuples for backward compatibility
        results = self.query_object.run_query(qry_str)
        # Return as list of tuples (legacy format)
        return [tuple(row.values()) if isinstance(row, dict) else row for row in results]

    def fetch_po(self, invoice_number):
        """Fetch PO number for invoice.
        
        Args:
            invoice_number: Invoice number to look up
            
        Returns:
            PO number string
        """
        if invoice_number == self.last_invoice_number:
            return self.po
        else:
            qry_ret = self._run_qry(
                f"""
                SELECT
            trim(ohhst.bte4cd),
                trim(ohhst.bthinb),
                ohhst.btabnb
            --PO Number
                FROM
            dacdata.ohhst ohhst
                WHERE
            ohhst.BTHHNB = {str(int(invoice_number))}
            """
            )
            self.last_invoice_number = invoice_number
            try:
                self.po = qry_ret[0][0]
                self.custname = qry_ret[0][1]
                self.custno = qry_ret[0][2]
            except IndexError:
                self.po = ""
            return self.po

    def fetch_cust_name(self, invoice_number):
        """Fetch customer name for invoice."""
        self.fetch_po(invoice_number)
        return self.custname
    
    def fetch_cust_no(self, invoice_number):
        """Fetch customer number for invoice."""
        self.fetch_po(invoice_number)
        return self.custno

    def fetch_uom_desc(self, itemno, uommult, lineno, invno):
        """Fetch unit of measure description."""
        if invno != self.last_invno:
            self.uom_lut = {0: "N/A"}
            qry = f"""
                SELECT
                    BUHUNB,
                    --lineno
                    BUHXTX
                    -- u/m desc
                FROM
                    dacdata.odhst odhst
                WHERE
                    odhst.BUHHNB = {str(int(invno))}
            """
            qry_ret = self._run_qry(qry)
            self.uom_lut = dict(qry_ret)
            self.last_invno = invno
        try:
            return self.uom_lut[lineno + 1]
        except KeyError as error:
            try:
                if int(uommult) > 1:
                    qry = f"""select dsanrep.ANB9TX
                            from dacdata.dsanrep dsanrep
                            where dsanrep.ANBACD = {str(int(itemno))}"""
                else:
                    qry = f"""select dsanrep.ANB8TX
                            from dacdata.dsanrep dsanrep
                            where dsanrep.ANBACD = {str(int(itemno))}"""
                uomqry_ret = self._run_qry(qry)
                return uomqry_ret[0][0]
            except Exception as error:
                try:
                    if int(uommult) > 1:
                        return "HI"
                    else:
                        return "LO"
                except ValueError:
                    return "NA"


def dac_str_int_to_int(dacstr: str) -> int:
    """Convert DAC string integer to Python int.
    
    Args:
        dacstr: DAC-format string (may have leading spaces or minus)
        
    Returns:
        Integer value
    """
    if dacstr.strip() == "":
        return 0
    if dacstr.startswith('-'):
        return int(dacstr[1:]) - (int(dacstr[1:]) * 2)
    else:
        return int(dacstr)


def convert_to_price(value):
    """Convert DAC price string to decimal format.
    
    Args:
        value: Price string (cents as integer)
        
    Returns:
        Price string with decimal point
    """
    return (value[:-2].lstrip("0") if not value[:-2].lstrip("0") == "" else "0") + "." + value[-2:]


def dactime_from_datetime(date_time: datetime) -> str:
    """Convert datetime to DAC time format.
    
    Args:
        date_time: Python datetime object
        
    Returns:
        DAC-format date string (7 digits: CYYMMDD)
    """
    dactime_date_century_digit = str(int(datetime.strftime(date_time, "%Y")[:2]) - 19)
    dactime_date = dactime_date_century_digit + str(
        datetime.strftime(date_time.date(), "%y%m%d")
    )
    return dactime_date


def datetime_from_dactime(dac_time: int) -> datetime:
    """Convert DAC time to datetime.
    
    Args:
        dac_time: DAC-format date (CYYMMDD)
        
    Returns:
        Python datetime object
    """
    dac_time_int = int(dac_time)
    return datetime.strptime(str(dac_time_int + 19000000), "%Y%m%d")


def datetime_from_invtime(invtime: str) -> datetime:
    """Convert invoice time string to datetime.
    
    Args:
        invtime: Invoice date string (MMDDYY)
        
    Returns:
        Python datetime object
    """
    return datetime.strptime(invtime, "%m%d%y")


def dactime_from_invtime(inv_no: str):
    """Convert invoice time to DAC time format.
    
    Args:
        inv_no: Invoice date string (MMDDYY)
        
    Returns:
        DAC-format date string
    """
    datetime_obj = datetime_from_invtime(inv_no)
    dactime = dactime_from_datetime(datetime_obj)
    return dactime


def detect_invoice_is_credit(edi_process):
    """Detect if an EDI file represents a credit invoice.
    
    Args:
        edi_process: Path to EDI file
        
    Returns:
        True if credit invoice, False otherwise
    """
    with open(edi_process, encoding="utf-8") as work_file:
        fields = capture_records(work_file.readline())
        if fields["record_type"] != 'A':
            raise ValueError("[Invoice Type Detection]: Somehow ended up in the middle of a file, this should not happen")
        if dac_str_int_to_int(fields["invoice_total"]) >= 0:
            return False
        else:
            return True


def convert_UPCE_to_UPCA(upce_value):
    """Convert UPC-E to UPC-A format.
    
    Args:
        upce_value: UPC-E value (6, 7, or 8 digits)
        
    Returns:
        12-digit UPC-A value with check digit, or False if invalid
        
    Note:
        This function returns False for invalid input for backward compatibility.
        New code should use convert_upce_to_upca() which returns empty string.
    """
    result = _convert_upce_to_upca(upce_value)
    return result if result else False


def filter_edi_file_by_category(input_file, output_file, upc_dict, filter_categories, filter_mode):
    """Filter an EDI file by item category without splitting.
    
    Drops invoices that have no B records after filtering (only A and C records remain).
    
    Args:
        input_file: Path to the input EDI file
        output_file: Path to write the filtered EDI file
        upc_dict: Dictionary mapping item numbers to [category, upc1, upc2, upc3, upc4]
        filter_categories: String of comma-separated categories or "ALL"
        filter_mode: "include" (keep only these categories) or "exclude" (remove these categories)
    
    Returns:
        True if filtering was applied, False if no filtering (ALL mode)
    """
    if filter_categories == "ALL":
        return False
    
    if not upc_dict:
        return False
    
    with open(input_file, encoding="utf-8") as work_file:
        lines = work_file.readlines()
    
    filtered_lines = []
    
    # Process invoice by invoice (A record + B records + C records)
    current_a_record = None
    current_b_records = []
    current_c_records = []
    
    def flush_invoice():
        """Write the current invoice to filtered_lines if it has B records."""
        nonlocal current_a_record, current_b_records, current_c_records
        if current_a_record is None:
            return
        
        # Filter B records
        filtered_b = filter_b_records_by_category(
            current_b_records, upc_dict, filter_categories, filter_mode
        )
        
        # Only include invoice if it has B records after filtering
        if filtered_b:
            filtered_lines.append(current_a_record)
            filtered_lines.extend(filtered_b)
            filtered_lines.extend(current_c_records)
        
        # Reset for next invoice
        current_a_record = None
        current_b_records = []
        current_c_records = []
    
    for line in lines:
        if line.startswith("A"):
            # Flush previous invoice before starting new one
            flush_invoice()
            current_a_record = line
        elif line.startswith("B"):
            current_b_records.append(line)
        elif line.startswith("C"):
            current_c_records.append(line)
        else:
            # Other record types (shouldn't happen in normal EDI)
            filtered_lines.append(line)
    
    # Flush final invoice
    flush_invoice()
    
    # Write output file with proper line endings
    with open(output_file, 'wb') as out_file:
        for line in filtered_lines:
            out_file.write(line.replace('\n', "\r\n").encode())
    
    return True


def do_split_edi(edi_process, work_directory, parameters_dict, upc_dict=None, filter_categories="ALL", filter_mode="include"):
    """Split EDI file by A records, optionally filtering B records by category.
    
    Invoices with no B records after filtering are dropped (not written to output).
    
    Args:
        edi_process: Path to the EDI file to process
        work_directory: Directory to write split files to
        parameters_dict: Dictionary of processing parameters
        upc_dict: Optional dictionary mapping item numbers to [category, upc1, upc2, upc3, upc4]
        filter_categories: Categories to filter ("ALL" or comma-separated like "1,5,12")
        filter_mode: "include" (keep only these categories) or "exclude" (remove these categories)
    
    Returns:
        List of tuples (output_file_path, file_name_prefix, file_name_suffix)
    
    Credit:
        col_to_excel function by Nodebody on StackOverflow: http://stackoverflow.com/a/19154642
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
    skipped_invoices = 0
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
        
        # Collect records for each invoice and apply category filtering
        current_b_records = []  # B records for current invoice
        current_a_record = None  # A record for current invoice
        current_c_records = []  # C records for current invoice
        current_output_file_path = None  # Output file for current invoice
        
        for line_mum, line in enumerate(work_file_lined):  # iterate over work file contents
            if line.startswith("A"):
                # Process previous invoice if exists
                if current_a_record is not None and current_output_file_path is not None:
                    # Filter B records by category
                    filtered_b_records = filter_b_records_by_category(
                        current_b_records, upc_dict, filter_categories, filter_mode
                    )
                    
                    # Only write invoice if it has B records after filtering
                    if filtered_b_records:
                        # Write A record
                        f.write(current_a_record.replace('\n', "\r\n").encode())
                        write_counter += 1
                        # Write filtered B records
                        for b_rec in filtered_b_records:
                            f.write(b_rec.replace('\n', "\r\n").encode())
                            write_counter += 1
                        # Write C records
                        for c_rec in current_c_records:
                            f.write(c_rec.replace('\n', "\r\n").encode())
                            write_counter += 1
                        f.close()
                    else:
                        # No B records after filtering - skip this invoice
                        f.close()
                        os.remove(current_output_file_path)
                        skipped_invoices += 1
                        # Remove from edi_send_list since we're skipping it
                        if edi_send_list:
                            edi_send_list.pop()
                
                # Start new invoice
                count += 1
                prepend_letters = col_to_excel(count)
                line_dict = capture_records(line)
                if int(line_dict['invoice_total']) < 0:
                    file_name_suffix = '.cr'
                else:
                    file_name_suffix = '.inv'
                file_name_prefix = prepend_letters + "_"
                if parameters_dict['prepend_date_files']:
                    datetime_from_arec = datetime.strptime(line_dict['invoice_date'], "%m%d%y")
                    inv_date = datetime.strftime(datetime_from_arec, "%d %b, %Y")
                    file_name_prefix = inv_date + "_" + file_name_prefix
                output_file_path = os.path.join(work_directory, file_name_prefix + os.path.basename(edi_process) + file_name_suffix)
                edi_send_list.append((output_file_path, file_name_prefix, file_name_suffix))
                f = open(output_file_path, 'wb')
                
                # Reset for new invoice
                current_a_record = line
                current_b_records = []
                current_c_records = []
                current_output_file_path = output_file_path
            elif line.startswith("B"):
                current_b_records.append(line)
            elif line.startswith("C"):
                current_c_records.append(line)
        
        # Process last invoice
        if current_a_record is not None and current_output_file_path is not None:
            # Filter B records by category
            filtered_b_records = filter_b_records_by_category(
                current_b_records, upc_dict, filter_categories, filter_mode
            )
            
            # Only write invoice if it has B records after filtering
            if filtered_b_records:
                # Write A record
                f.write(current_a_record.replace('\n', "\r\n").encode())
                write_counter += 1
                # Write filtered B records
                for b_rec in filtered_b_records:
                    f.write(b_rec.replace('\n', "\r\n").encode())
                    write_counter += 1
                # Write C records
                for c_rec in current_c_records:
                    f.write(c_rec.replace('\n', "\r\n").encode())
                    write_counter += 1
                f.close()  # close output file
            else:
                # No B records after filtering - skip this invoice
                f.close()
                os.remove(current_output_file_path)
                skipped_invoices += 1
                if edi_send_list:
                    edi_send_list.pop()
        
        # Validation: count output lines
        edi_send_list_lines = 0
        for output_file, _, _ in edi_send_list:
            with open(output_file, encoding="utf-8") as file_handle:
                edi_send_list_lines += sum(1 for _ in file_handle)
        if not write_counter == edi_send_list_lines:
            raise Exception("total lines written do not match output file line count")
        # Note: len(edi_send_list) may be less than A records count due to filtering
        if len(edi_send_list) < 1:
            raise Exception("No Split EDIs (all invoices may have been filtered out)")
    return edi_send_list


def do_clear_old_files(folder_path, maximum_files):
    """Clear old files from a folder, keeping only the newest ones.
    
    Args:
        folder_path: Path to folder to clean
        maximum_files: Maximum number of files to keep
    """
    while len(os.listdir(folder_path)) > maximum_files:
        os.remove(os.path.join(folder_path, min(os.listdir(folder_path),
                                                key=lambda f: os.path.getctime("{}/{}".format(folder_path, f)))))
