"""EDI tweaks module for processing EDI files.

This module provides EDI file processing functionality including:
- PO number fetching
- C-record generation for split sales tax
- Various EDI record transformations

The module maintains backward compatibility while using the new
refactored classes from core.edi.
"""

import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

import utils
from query_runner import query_runner

# Import refactored classes
from core.edi.po_fetcher import POFetcher, POData
from core.edi.c_rec_generator import CRecGenerator, CRecordConfig


# Backward compatibility: Keep legacy class names as aliases
class poFetcher:
    """Legacy PO fetcher class for backward compatibility.
    
    This class wraps the new POFetcher class and provides
    the same interface as the original implementation.
    """
    
    DEFAULT_PO = POFetcher.DEFAULT_PO
    
    def __init__(self, settings_dict):
        """Initialize with settings dictionary.
        
        Args:
            settings_dict: Dictionary containing database connection settings
        """
        self.query_object = None
        self.settings = settings_dict
        self._fetcher: Optional[POFetcher] = None
    
    def _db_connect(self):
        """Establish database connection using legacy query_runner."""
        self.query_object = query_runner(
            self.settings["as400_username"],
            self.settings["as400_password"],
            self.settings["as400_address"],
            f"{self.settings['odbc_driver']}",
        )
        # Create adapter for the legacy query_runner
        self._fetcher = POFetcher(self._create_adapter())
    
    def _create_adapter(self):
        """Create an adapter that wraps legacy query_runner.
        
        Returns:
            Object implementing QueryRunnerProtocol
        """
        class QueryRunnerAdapter:
            def __init__(self, legacy_runner):
                self._runner = legacy_runner
            
            def run_query(self, query: str, params: tuple = None) -> list:
                # Legacy runner returns list of tuples
                return self._runner.run_arbitrary_query(query)
        
        return QueryRunnerAdapter(self.query_object)
    
    def fetch_po_number(self, invoice_number):
        """Fetch PO number for an invoice.
        
        Args:
            invoice_number: Invoice number to look up
            
        Returns:
            PO number string, or default if not found
        """
        if self._fetcher is None:
            self._db_connect()
        return self._fetcher.fetch_po_number(invoice_number)


class cRecGenerator:
    """Legacy C-record generator class for backward compatibility.
    
    This class wraps the new CRecGenerator class and provides
    the same interface as the original implementation.
    """
    
    def __init__(self, settings_dict):
        """Initialize with settings dictionary.
        
        Args:
            settings_dict: Dictionary containing database connection settings
        """
        self.query_object = None
        self._invoice_number = "0"
        self.unappended_records = False
        self.settings = settings_dict
        self._generator: Optional[CRecGenerator] = None
    
    def _db_connect(self):
        """Establish database connection using legacy query_runner."""
        self.query_object = query_runner(
            self.settings["as400_username"],
            self.settings["as400_password"],
            self.settings["as400_address"],
            f"{self.settings['odbc_driver']}",
        )
        # Create adapter for the legacy query_runner
        self._generator = CRecGenerator(self._create_adapter())
    
    def _create_adapter(self):
        """Create an adapter that wraps legacy query_runner.
        
        Returns:
            Object implementing QueryRunnerProtocol
        """
        class QueryRunnerAdapter:
            def __init__(self, legacy_runner):
                self._runner = legacy_runner
            
            def run_query(self, query: str, params: tuple = None) -> list:
                # Legacy runner returns list of tuples
                return self._runner.run_arbitrary_query(query)
        
        return QueryRunnerAdapter(self.query_object)
    
    def set_invoice_number(self, invoice_number):
        """Set the current invoice number.
        
        Args:
            invoice_number: Invoice number for subsequent operations
        """
        if self._generator is None:
            self._db_connect()
        self._generator.set_invoice_number(invoice_number)
        self._invoice_number = invoice_number
        self.unappended_records = True
    
    def fetch_splitted_sales_tax_totals(self, procfile):
        """Fetch and write split sales tax C records.
        
        Args:
            procfile: File handle to write C records to
        """
        if self._generator is None:
            self._db_connect()
        self._generator.fetch_splitted_sales_tax_totals(procfile)
        self.unappended_records = False


def edi_tweak(
    edi_process,
    output_filename,
    settings_dict,
    parameters_dict,
    upc_dict,
):
    """Apply EDI tweaks to process an EDI file.
    
    This function processes an EDI file, applying various transformations
    including date offsetting, UPC calculations, and C-record generation.
    
    Args:
        edi_process: Path to input EDI file
        output_filename: Path to output file
        settings_dict: Dictionary containing database and app settings
        parameters_dict: Dictionary containing processing parameters
        upc_dict: Dictionary containing UPC mappings
        
    Returns:
        Path to the output file
    """
    pad_arec = parameters_dict['pad_a_records']
    arec_padding = parameters_dict['a_record_padding']
    arec_padding_len = parameters_dict['a_record_padding_length']
    append_arec = parameters_dict['append_a_records']
    append_arec_text = parameters_dict['a_record_append_text']
    invoice_date_custom_format = parameters_dict['invoice_date_custom_format']
    invoice_date_custom_format_string = parameters_dict['invoice_date_custom_format_string']
    force_txt_file_ext = parameters_dict['force_txt_file_ext']
    calc_upc = parameters_dict['calculate_upc_check_digit']
    invoice_date_offset = parameters_dict['invoice_date_offset']
    retail_uom = parameters_dict['retail_uom']
    override_upc = parameters_dict['override_upc_bool']
    override_upc_level = parameters_dict['override_upc_level']
    override_upc_category_filter = parameters_dict['override_upc_category_filter']
    split_prepaid_sales_tax_crec = parameters_dict['split_prepaid_sales_tax_crec']
    upc_target_length = int(parameters_dict.get('upc_target_length', 11))
    upc_padding_pattern = parameters_dict.get('upc_padding_pattern', '           ')

    work_file = None
    read_attempt_counter = 1
    while work_file is None:
        try:
            work_file = open(edi_process)  # open work file, overwriting old file
        except Exception as error:
            if read_attempt_counter >= 5:
                time.sleep(read_attempt_counter*read_attempt_counter)
                read_attempt_counter += 1
                print(f"retrying open {edi_process}")
            else:
                print(f"error opening file for read {error}")
                raise
    # work_file = open(edi_process)  # open input file
    work_file_lined = [n for n in work_file.readlines()]  # make list of lines
    if force_txt_file_ext == "True":
        output_filename = output_filename + ".txt"

    f = None

    write_attempt_counter = 1
    while f is None:
        try:
            f = open(output_filename, "w", newline='\r\n')  # open work file, overwriting old file
        except Exception as error:
            if write_attempt_counter >= 5:
                time.sleep(write_attempt_counter*write_attempt_counter)
                write_attempt_counter += 1
                print(f"retrying open {output_filename}")
            else:
                print(f"error opening file for write {error}")
                raise

    crec_appender = cRecGenerator(settings_dict)

    po_fetcher = poFetcher(settings_dict)

    for line_num, line in enumerate(work_file_lined):  # iterate over work file contents
        input_edi_dict = utils.capture_records(line)
        writeable_line = line
        if writeable_line.startswith("A"):
            a_rec_edi_dict = input_edi_dict
            crec_appender.set_invoice_number(int(a_rec_edi_dict['invoice_number']))
            if invoice_date_offset != 0:
                invoice_date_string = a_rec_edi_dict["invoice_date"]
                if not invoice_date_string == "000000":
                    invoice_date = datetime.strptime(invoice_date_string, "%m%d%y")
                    print(invoice_date_offset)
                    offset_invoice_date = invoice_date + timedelta(
                        days=invoice_date_offset
                    )
                    a_rec_edi_dict['invoice_date'] = datetime.strftime(offset_invoice_date, "%m%d%y")
            if invoice_date_custom_format:
                invoice_date_string = a_rec_edi_dict["invoice_date"]
                try:
                    invoice_date = datetime.strptime(invoice_date_string, "%m%d%y")
                    a_rec_edi_dict['invoice_date'] = datetime.strftime(invoice_date, invoice_date_custom_format_string)
                except ValueError:
                    a_rec_edi_dict['invoice_date'] = "ERROR"
            if pad_arec == "True":
                padding = arec_padding
                fill = ' '
                align = '<'
                width = arec_padding_len
                a_rec_edi_dict['cust_vendor'] = f'{padding:{fill}{align}{width}}'
            a_rec_line_builder = [a_rec_edi_dict['record_type'],
                    a_rec_edi_dict['cust_vendor'],
                    a_rec_edi_dict['invoice_number'],
                    a_rec_edi_dict['invoice_date'],
                    a_rec_edi_dict['invoice_total']]
            if append_arec == "True":
                if "%po_str%" in append_arec_text:
                    append_arec_text = append_arec_text.replace("%po_str%", po_fetcher.fetch_po_number(a_rec_edi_dict['invoice_number']))
                a_rec_line_builder.append(append_arec_text)
            a_rec_line_builder.append("\n")
            writeable_line = "".join(a_rec_line_builder)
            f.write(writeable_line)
        if writeable_line.startswith("B"):
            b_rec_edi_dict = input_edi_dict
            try:
                if override_upc:
                    if override_upc_category_filter == "ALL":
                        b_rec_edi_dict['upc_number'] = upc_dict[int(b_rec_edi_dict['vendor_item'].strip())][override_upc_level]
                    else:
                        if upc_dict[int(b_rec_edi_dict['vendor_item'].strip())][0] in override_upc_category_filter.split(","):
                            b_rec_edi_dict['upc_number'] = upc_dict[int(b_rec_edi_dict['vendor_item'].strip())][override_upc_level]
            except KeyError:
                b_rec_edi_dict['upc_number'] = ""
            # Apply padding/truncating to UPC if retail_uom is enabled
            # This runs after override_upc, so padding is applied to whatever UPC is set
            if retail_uom:
                edi_line_pass = False
                try:
                    item_number = int(b_rec_edi_dict['vendor_item'].strip())
                    float(b_rec_edi_dict['unit_cost'].strip())
                    test_unit_multiplier = int(b_rec_edi_dict['unit_multiplier'].strip())
                    if test_unit_multiplier == 0:
                        raise ValueError
                    int(b_rec_edi_dict['qty_of_units'].strip())
                    edi_line_pass = True
                except Exception:
                    print("cannot parse b record field, skipping")
                if edi_line_pass:
                    # Apply padding/truncating to whatever UPC is already in the field
                    # This runs after override_upc, so we pad the existing UPC value
                    try:
                        fill_char = upc_padding_pattern[0] if upc_padding_pattern else ' '
                        current_upc = b_rec_edi_dict['upc_number'].strip()[:upc_target_length]
                        b_rec_edi_dict['upc_number'] = current_upc.rjust(upc_target_length, fill_char)
                    except (AttributeError, TypeError):
                        # Fallback: use padding pattern if UPC is empty/invalid
                        b_rec_edi_dict['upc_number'] = upc_padding_pattern[:upc_target_length]
                    try:
                        b_rec_edi_dict["unit_cost"] = str(Decimal((Decimal(b_rec_edi_dict['unit_cost'].strip()) / 100) / Decimal(b_rec_edi_dict['unit_multiplier'].strip())).quantize(Decimal('.01'))).replace(".", "")[-6:].rjust(6,'0')
                        b_rec_edi_dict['qty_of_units'] = str(int(b_rec_edi_dict['unit_multiplier'].strip()) * int(b_rec_edi_dict['qty_of_units'].strip())).rjust(5,'0')
                        b_rec_edi_dict['unit_multiplier'] = '000001'
                    except Exception as error:
                        print(error)
            if calc_upc == "True":
                blank_upc = False
                try:
                    _ = int(b_rec_edi_dict["upc_number"].rstrip())
                except ValueError:
                    blank_upc = True

                if blank_upc is False:
                    proposed_upc = b_rec_edi_dict["upc_number"].strip()
                    if len(str(proposed_upc)) == upc_target_length:
                        b_rec_edi_dict['upc_number'] = str(proposed_upc) + str(
                            utils.calc_check_digit(proposed_upc)
                        )
                    else:
                        if len(str(proposed_upc)) == 8:
                            b_rec_edi_dict['upc_number'] = str(
                                utils.convert_UPCE_to_UPCA(proposed_upc)
                            )
                else:
                    b_rec_edi_dict['upc_number'] = upc_padding_pattern[:upc_target_length]

            if len(writeable_line) < 77:
                b_rec_edi_dict["parent_item_number"] = ""

            digits_fields = [
            "unit_cost",
            "unit_multiplier",
            "qty_of_units",
            "suggested_retail_price",
            ]

            for field in digits_fields:
                tempfield = b_rec_edi_dict[field].replace("-", "")
                if len(tempfield) != len(b_rec_edi_dict[field]):
                    b_rec_edi_dict[field] = "-" + tempfield

            writeable_line = "".join((
                b_rec_edi_dict["record_type"],
                b_rec_edi_dict["upc_number"],
                b_rec_edi_dict["description"],
                b_rec_edi_dict["vendor_item"],
                b_rec_edi_dict["unit_cost"],
                b_rec_edi_dict["combo_code"],
                b_rec_edi_dict["unit_multiplier"],
                b_rec_edi_dict["qty_of_units"],
                b_rec_edi_dict["suggested_retail_price"],
                b_rec_edi_dict["price_multi_pack"],
                b_rec_edi_dict["parent_item_number"],
                "\n")
            )
            f.write(writeable_line)
        if writeable_line.startswith("C"):
            if split_prepaid_sales_tax_crec and crec_appender.unappended_records and writeable_line.startswith("CTABSales Tax"):
                crec_appender.fetch_splitted_sales_tax_totals(f)
            else:
                f.write(writeable_line)
    f.close()  # close output file
    return output_filename
