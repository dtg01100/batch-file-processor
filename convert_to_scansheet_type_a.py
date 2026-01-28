import math
import os
import tempfile

import barcode
import openpyxl
import openpyxl.utils
from barcode.writer import ImageWriter
from openpyxl.drawing.image import Image as OpenPyXlImage
from PIL import Image as pil_Image
from PIL import ImageOps as pil_ImageOps

import utils
from convert_base import BaseConverter, create_edi_convert_wrapper
from query_runner import query_runner


class ScansheetTypeAConverter(BaseConverter):
    """Converter for generating Scansheet Type A Excel files with embedded barcodes."""

    PLUGIN_ID = "scansheet_type_a"
    PLUGIN_NAME = "Scansheet Type A"
    PLUGIN_DESCRIPTION = (
        "Converter for generating Scansheet Type A Excel files with embedded barcodes"
    )

    CONFIG_FIELDS = []

    def initialize_output(self) -> None:
        """Initialize Excel workbook and extract invoice list from EDI file."""
        # First pass: Extract all invoice numbers from EDI file
        self.invoice_list = []
        with open(self.edi_process, encoding="utf-8") as work_file:
            work_file_lined = [n for n in work_file.readlines()]
            for line_num, line in enumerate(work_file_lined):
                input_edi_dict = utils.capture_records(line)
                if input_edi_dict is not None:
                    try:
                        if input_edi_dict["record_type"] == "A":
                            self.invoice_list.append(
                                input_edi_dict["invoice_number"][-7:]
                            )
                    except TypeError:
                        pass
        print(self.invoice_list)

        # Initialize database connection
        self.query_object = query_runner(
            self.settings_dict["as400_username"],
            self.settings_dict["as400_password"],
            self.settings_dict["as400_address"],
            f"{self.settings_dict['odbc_driver']}",
        )

        # Create Excel workbook and worksheet
        self.output_spreadsheet = openpyxl.Workbook()
        self.output_worksheet = self.output_spreadsheet.worksheets[0]
        self.output_spreadsheet_name = self.output_filename + ".xlsx"

        # Initialize invoice tracking
        self.invoice_rows = []
        self.invoice_row_counter = 0

        # Query DB for each invoice and populate worksheet
        for invoice in self.invoice_list:
            # Validate invoice is numeric before SQL interpolation
            try:
                invoice_int = int(invoice)
            except (ValueError, TypeError):
                invoice_int = 0
            result = self.query_object.run_arbitrary_query(f"""SELECT buj4cd AS "UPC",
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
                WHERE odhst.buhhnb = {invoice_int}
                    AND bue4qt <> 0""")
            rows_for_export = []
            for row in result:
                trow = [""]
                for entry in row:
                    try:
                        trow.append(entry.strip())
                    except AttributeError:
                        trow.append(entry)
                rows_for_export.append(trow)
                print(trow)

            self.output_worksheet.append(["", invoice])
            self.invoice_row_counter += 1
            self.invoice_rows.append(self.invoice_row_counter)
            for items_list_entry in rows_for_export:
                self.output_worksheet.append(items_list_entry)
                self.invoice_row_counter += 1
            self.adjust_column_width(self.output_worksheet)

    def process_record_a(self, record: dict) -> None:
        """Process A record - not used since we did first pass extraction"""
        pass

    def process_record_b(self, record: dict) -> None:
        """Process B record - not used since we did DB querying"""
        pass

    def process_record_c(self, record: dict) -> None:
        """Process C record - not used since we did DB querying"""
        pass

    def finalize_output(self) -> str:
        """Add barcodes to Excel worksheet and save file"""
        self.do_process_workbook()
        return self.output_spreadsheet_name

    def adjust_column_width(self, adjust_worksheet):
        """Adjust column widths in Excel worksheet to fit content"""
        print(f"Adjusting column width for {adjust_worksheet.title} worksheet")
        for col in adjust_worksheet.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except Exception as resize_error:
                    print(resize_error)
            adjusted_width = (max_length + 2) * 1.2
            adjust_worksheet.column_dimensions[column].width = adjusted_width

    def generate_barcode(self, input_string, tempdir):
        """Generate UPC-A barcode image with specified dimensions"""
        ean = barcode.get_barcode_class("UPCA")
        options = {
            "dpi": 130,
            "module_height": 5.0,
            "text_distance": 2,
            "font_size": 6,
            "quiet_zone": 2,
        }

        with tempfile.NamedTemporaryFile(
            dir=tempdir, suffix=".png", delete=False
        ) as initial_temp_file:
            ean(input_string, writer=ImageWriter()).write(
                initial_temp_file, options=options
            )
            filename = initial_temp_file.name
        print(f"success, barcode image path is: {filename}")

        barcode_image = pil_Image.open(str(filename))
        img_save = pil_ImageOps.expand(barcode_image, border=0, fill="white")
        width, height = img_save.size

        with tempfile.NamedTemporaryFile(
            dir=tempdir, suffix=".png", delete=False
        ) as final_barcode_path:
            img_save.save(final_barcode_path.name)
            print(f"success, final barcode path is: {final_barcode_path.name}")

        return final_barcode_path.name, width, height

    def interpret_barcode_string(self, upc_barcode_string):
        """Convert input string to valid UPC-A format"""
        if not upc_barcode_string == "":
            try:
                _ = int(upc_barcode_string)
            except ValueError:
                raise ValueError("Input contents are not an integer")

            if len(upc_barcode_string) < 10:
                upc_barcode_string = upc_barcode_string.rjust(11, "0")
            if len(upc_barcode_string) <= 11:
                upc_barcode_string = upc_barcode_string.ljust(12, "0")
            else:
                raise ValueError("Input contents are more than 11 characters")
        else:
            raise ValueError("Input is empty")
        return upc_barcode_string

    def do_process_workbook(self):
        """Process workbook to add barcode images"""
        print("creating temp directory")
        with tempfile.TemporaryDirectory() as tempdir:
            print(f"temp directory created as: {tempdir}")
            count = 0
            save_counter = 0

            for _ in self.output_worksheet.iter_rows():
                try:
                    count += 1
                    if count not in self.invoice_rows:
                        upc_barcode_string = str(
                            self.output_worksheet["B" + str(count)].value
                        )
                        print(f"cell contents are: {upc_barcode_string}")
                        print(upc_barcode_string[-12:][:-1])
                        upc_barcode_string = self.interpret_barcode_string(
                            upc_barcode_string[-12:][:-1]
                        )
                        print(upc_barcode_string)
                        generated_barcode_path, width, height = self.generate_barcode(
                            upc_barcode_string, tempdir
                        )

                        self.output_worksheet.column_dimensions["A"].width = int(
                            math.ceil(float(width) * 0.15)
                        )
                        self.output_worksheet.row_dimensions[count].height = int(
                            math.ceil(float(height) * 0.75)
                        )

                        img = OpenPyXlImage(generated_barcode_path)
                        self.output_worksheet.add_image(img, anchor="A" + str(count))
                        save_counter += 1
                        print("success")
                except Exception as barcode_error:
                    print(barcode_error)

                if save_counter >= 100:
                    print("saving intermediate workbook to free file handles")
                    self.output_spreadsheet.save(self.output_spreadsheet_name)
                    print("success")
                    save_counter = 1

            print("saving workbook to file")
            self.output_spreadsheet.save(self.output_spreadsheet_name)
            print("success")


edi_convert = create_edi_convert_wrapper(ScansheetTypeAConverter)
