"""ScanSheet Type A Excel EDI Converter - Refactored with Class-Based Structure.

This module converts EDI files to ScanSheet Type A Excel format with database lookups
and barcode generation. Unlike other converters, this one uses the EDI file only to
extract invoice numbers, then fetches all item data from the database.

The converter features:
- Database queries for invoice item details
- Excel workbook creation with openpyxl
- Automatic barcode generation for each item
- Column width adjustment for readability
- Memory-efficient batch processing with periodic saves

Output Format:
    Excel (.xlsx) file with invoice numbers and item details,
    with barcode images in column A.

Architecture Note:
    This converter does not use the standard BaseEDIConverter template pattern
    because it processes data fundamentally differently - instead of processing
    A/B/C records from the EDI file, it extracts invoice numbers from the EDI
    and queries all item data from the database.

Backward Compatibility:
    The module-level edi_convert() function maintains the same signature
    as before: edi_convert(edi_process, output_filename, settings_dict,
    parameters_dict, upc_lookup)
"""

import math
import os
import tempfile
from typing import Any, Dict, List, Tuple

import barcode
import openpyxl
import openpyxl.utils
from barcode.writer import ImageWriter
from openpyxl.drawing.image import Image as OpenPyXlImage
from PIL import Image as pil_Image
from PIL import ImageOps as pil_ImageOps

import utils
from core.database import query_runner


class ScanSheetTypeAConverter:
    """Converter for ScanSheet Type A Excel format with barcodes.
    
    This converter extracts invoice numbers from the EDI file, queries the
    database for item details, creates an Excel workbook, and generates
    barcode images for each item.
    
    Unlike typical EDI converters, this does not process A/B/C records
    individually - instead it uses the EDI as an invoice list source
    and the database as the primary data source.
    """
    
    def __init__(self):
        """Initialize the converter."""
        self.query_object = None
        self.output_spreadsheet = None
        self.output_worksheet = None
        self.output_spreadsheet_name = ""
        self.invoice_rows: List[int] = []
        self.invoice_row_counter = 0
    
    def edi_convert(
        self,
        edi_process: str,
        output_filename: str,
        settings_dict: Dict[str, Any],
        parameters_dict: Dict[str, Any],
        upc_lookup: Dict[int, tuple]
    ) -> str:
        """Convert EDI file to ScanSheet Type A Excel format.
        
        Args:
            edi_process: Path to the input EDI file
            output_filename: Base path for output file (without extension)
            settings_dict: Application settings dictionary with DB credentials
            parameters_dict: Conversion parameters (not used)
            upc_lookup: UPC lookup table (not used - data comes from DB)
        
        Returns:
            Path to the generated Excel file
        """
        # Step 1: Extract invoice numbers from EDI file
        invoice_list = self._extract_invoices_from_edi(edi_process)
        
        # Step 2: Initialize database connection
        self._initialize_database(settings_dict)
        
        # Step 3: Create Excel workbook and populate with data
        self._initialize_workbook(output_filename)
        self._populate_workbook(invoice_list)
        
        # Step 4: Generate and insert barcodes
        self._process_barcodes()
        
        return self.output_spreadsheet_name
    
    def _extract_invoices_from_edi(self, edi_process: str) -> List[str]:
        """Extract invoice numbers from the EDI file.
        
        Args:
            edi_process: Path to the input EDI file
            
        Returns:
            List of invoice numbers (last 7 digits)
        """
        invoice_list = []
        with open(edi_process, encoding="utf-8") as work_file:
            work_file_lined = [n for n in work_file.readlines()]
            
            for line in work_file_lined:
                input_edi_dict = utils.capture_records(line)
                try:
                    if input_edi_dict["record_type"] == "A":
                        invoice_list.append(input_edi_dict["invoice_number"][-7:])
                except TypeError:
                    pass
        
        print(invoice_list)
        return invoice_list
    
    def _initialize_database(self, settings_dict: Dict[str, Any]) -> None:
        """Initialize database connection.
        
        Args:
            settings_dict: Application settings with DB credentials
        """
        self.query_object = query_runner(
            settings_dict["as400_username"],
            settings_dict["as400_password"],
            settings_dict["as400_address"],
            f"{settings_dict['odbc_driver']}",
        )
    
    def _initialize_workbook(self, output_filename: str) -> None:
        """Initialize the Excel workbook.
        
        Args:
            output_filename: Base path for output file (without extension)
        """
        self.output_spreadsheet = openpyxl.Workbook()
        self.output_worksheet = self.output_spreadsheet.worksheets[0]
        self.output_spreadsheet_name = output_filename + '.xlsx'
        self.invoice_rows = []
        self.invoice_row_counter = 0
    
    def _populate_workbook(self, invoice_list: List[str]) -> None:
        """Populate the workbook with data from the database.
        
        Args:
            invoice_list: List of invoice numbers to query
        """
        for invoice in invoice_list:
            result = self.query_object.run_arbitrary_query(
                f"""SELECT buj4cd AS "UPC",
                    bubacd AS "Item",
                    bufbtx AS "Description",
                    ancctx AS "Pack",
                    buhxtx AS "U/M",
                    bue4qt AS "Qty",
                    bud2pr AS "Price",
                    bueapr AS "Retail"
                    FROM dacdata.odhst odhst
                        INNER JOIN dacdata.dsanrep dsanrep
                            ON odhst.bubacd = dsanrep.anbacd
                    WHERE odhst.buhhnb = {invoice}
                        AND bue4qt <> 0"""
            )
            
            rows_for_export = []
            for row in result:
                trow = [""]
                # attempt to strip whitespace from entries in row
                for entry in row:
                    try:
                        trow.append(entry.strip())
                    except AttributeError:
                        trow.append(entry)
                rows_for_export.append(trow)
                print(trow)
            
            self.output_worksheet.append(['', invoice])
            self.invoice_row_counter += 1
            self.invoice_rows.append(self.invoice_row_counter)
            
            for items_list_entry in rows_for_export:
                self.output_worksheet.append(items_list_entry)
                self.invoice_row_counter += 1
            
            self._adjust_column_width(self.output_worksheet)
            self.output_spreadsheet.save(self.output_spreadsheet_name)
    
    def _adjust_column_width(self, adjust_worksheet) -> None:
        """Adjust column widths to fit content.
        
        Args:
            adjust_worksheet: The worksheet to adjust
        """
        print(f"Adjusting column width for {adjust_worksheet.title} worksheet")
        for col in adjust_worksheet.columns:
            max_length = 0
            column = col[0].column_letter  # Get the column name
            for cell in col:
                try:  # Necessary to avoid error on empty cells
                    if len(str(cell.value)) > max_length:
                        # Convert cell contents to str, cannot get len of int
                        max_length = len(str(cell.value))
                except Exception as resize_error:
                    print(resize_error)
            adjusted_width = (max_length + 2) * 1.2
            adjust_worksheet.column_dimensions[column].width = adjusted_width
    
    def _process_barcodes(self) -> None:
        """Generate and insert barcodes for each item in the workbook."""
        print("creating temp directory")
        with tempfile.TemporaryDirectory() as tempdir:
            print(f"temp directory created as: {tempdir}")
            count = 0
            save_counter = 0
            
            for _ in self.output_worksheet.iter_rows():
                try:
                    count += 1
                    if count not in self.invoice_rows:
                        print(f"getting cell contents on line number {count}")
                        upc_barcode_string = str(self.output_worksheet["B" + str(count)].value)
                        print(f"cell contents are: {upc_barcode_string}")
                        print(upc_barcode_string[-12:][:-1])
                        upc_barcode_string = self._interpret_barcode_string(upc_barcode_string[-12:][:-1])
                        print(upc_barcode_string)
                        
                        generated_barcode_path, width, height = self._generate_barcode(upc_barcode_string, tempdir)
                        
                        # resize cell to size of image
                        self.output_worksheet.column_dimensions['A'].width = int(math.ceil(float(width) * .15))
                        self.output_worksheet.row_dimensions[count].height = int(math.ceil(float(height) * .75))
                        
                        # open image with as openpyxl image object
                        print(f"opening {generated_barcode_path} to insert into output spreadsheet")
                        img = OpenPyXlImage(generated_barcode_path)
                        print("success")
                        
                        # attach image to cell
                        print("adding image to cell")
                        self.output_worksheet.add_image(img, anchor='A' + str(count))
                        save_counter += 1
                        print("success")
                except Exception as barcode_error:
                    print(barcode_error)
                
                # This save in the loop frees references to the barcode images,
                # so that python's garbage collector can clear them
                if save_counter >= 100:
                    print("saving intermediate workbook to free file handles")
                    self.output_spreadsheet.save(self.output_spreadsheet_name)
                    print("success")
                    save_counter = 1
            
            print("saving workbook to file")
            self.output_spreadsheet.save(self.output_spreadsheet_name)
            print("success")
    
    def _generate_barcode(self, input_string: str, tempdir: str) -> Tuple[str, int, int]:
        """Generate a barcode image for the given UPC string.
        
        Args:
            input_string: The 12-digit UPC string
            tempdir: Temporary directory for image files
            
        Returns:
            Tuple of (image_path, width, height)
        """
        ean = barcode.get_barcode_class("UPCA")
        options = {
            'dpi': 130,
            'module_height': 5.0,
            'text_distance': 2,
            'font_size': 6,
            'quiet_zone': 2
        }
        
        print("generating barcode image")
        with tempfile.NamedTemporaryFile(dir=tempdir, suffix='.png', delete=False) as initial_temp_file:
            ean(input_string, writer=ImageWriter()).write(initial_temp_file, options=options)
            filename = initial_temp_file.name
        
        print(filename)
        print(f"success, barcode image path is: {filename}")
        print(f"opening {filename} to add border")
        
        barcode_image = pil_Image.open(str(filename))
        print("success")
        print("adding barcode and saving")
        
        img_save = pil_ImageOps.expand(barcode_image, border=0, fill='white')
        width, height = img_save.size
        
        with tempfile.NamedTemporaryFile(dir=tempdir, suffix='.png', delete=False) as final_barcode_path:
            img_save.save(final_barcode_path.name)
            print(f"success, final barcode path is: {final_barcode_path.name}")
        
        return final_barcode_path.name, width, height
    
    def _interpret_barcode_string(self, upc_barcode_string: str) -> str:
        """Interpret and validate a barcode string.
        
        Args:
            upc_barcode_string: The input barcode string
            
        Returns:
            Validated 12-digit UPC string
            
        Raises:
            ValueError: If the input is empty or invalid
        """
        if not upc_barcode_string == '':
            try:
                _ = int(upc_barcode_string)
            except ValueError:
                raise ValueError("Input contents are not an integer")
            
            if len(upc_barcode_string) < 10:
                upc_barcode_string = upc_barcode_string.rjust(11, '0')
            if len(upc_barcode_string) <= 11:
                upc_barcode_string = upc_barcode_string.ljust(12, '0')
            else:
                raise ValueError("Input contents are more than 11 characters")
        else:
            raise ValueError("Input is empty")
        
        return upc_barcode_string


# =============================================================================
# Backward Compatibility Wrapper
# =============================================================================

def edi_convert(
    edi_process: str,
    output_filename: str,
    settings_dict: Dict[str, Any],
    parameters_dict: Dict[str, Any],
    upc_lookup: Dict[int, tuple]
) -> str:
    """Convert EDI file to ScanSheet Type A Excel format with barcodes.
    
    This is the original function signature maintained for backward compatibility.
    It simply creates a ScanSheetTypeAConverter instance and delegates to it.
    
    Args:
        edi_process: Path to the input EDI file
        output_filename: Base path for output file (without extension)
        settings_dict: Application settings dictionary with DB credentials
        parameters_dict: Conversion parameters (not used)
        upc_lookup: UPC lookup table (not used - data comes from DB)
    
    Returns:
        Path to the generated Excel file
    
    Example:
        >>> result = edi_convert(
        ...     "input.edi",
        ...     "output",
        ...     {'as400_username': 'user', 'as400_password': 'pass', ...},
        ...     {},
        ...     {}
        ... )
        >>> print(result)
        'output.xlsx'
    """
    converter = ScanSheetTypeAConverter()
    return converter.edi_convert(
        edi_process,
        output_filename,
        settings_dict,
        parameters_dict,
        upc_lookup
    )
