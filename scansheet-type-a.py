import line_from_mtc_edi_to_dict
import openpyxl
import openpyxl.utils
import tempfile
import os
from query_runner import query_runner
from openpyxl.drawing.image import Image as OpenPyXlImage
from PIL import Image as pil_Image
import ImageOps as pil_ImageOps
from barcode.writer import ImageWriter
import barcode.pybarcode
import math


def edi_convert(edi_process, output_filename, settings_dict):

    def adjust_column_width(adjust_worksheet):
        print(
            "Adjusting column width for {} worksheet".format(adjust_worksheet.title)
        )
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

    work_file = open(edi_process)  # open input file
    work_file_lined = [n for n in work_file.readlines()]  # make list of lines
    invoice_list = []

    for line_num, line in enumerate(work_file_lined):  # iterate over work file contents
        input_edi_dict = line_from_mtc_edi_to_dict.capture_records(line)
        try:
            if input_edi_dict["record_type"] == "A":
                invoice_list.append(input_edi_dict["invoice_number"][-7:])
        except TypeError:
            pass

    print(invoice_list)

    query_object = query_runner(
        settings_dict["as400_username"],
        settings_dict["as400_password"],
        settings_dict["as400_address"],
        f"{settings_dict['odbc_driver']}",
    )

    output_spreadsheet = openpyxl.Workbook()
    output_worksheet = output_spreadsheet.worksheets[0]

    invoice_rows = []
    invoice_row_counter = 0

    for invoice in invoice_list:

        result = query_object.run_arbitrary_query(f"""SELECT buj4cd AS "UPC",
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
                AND bue4qt <> 0""")
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

        output_worksheet.append(['', invoice])
        invoice_row_counter += 1
        invoice_rows.append(invoice_row_counter)
        for items_list_entry in rows_for_export:
            output_worksheet.append(items_list_entry)
            invoice_row_counter += 1
        adjust_column_width(output_worksheet)
        output_spreadsheet_name = output_filename
        output_spreadsheet.save(output_spreadsheet_name)

    def generate_barcode(input_string, tempdir):
        ean = barcode.get("UPCA")
        # select output image size via dpi. internally, pybarcode renders as svg, then renders that as a png file.
        # dpi is the conversion from svg image size in mm, to what the image writer thinks is inches.
        options={
            'dpi': 130,
            'module_height': 5.0,
            'text_distance': 1,
            'font_size': 6,
            'quiet_zone': 2
        }
        # ean.default_writer_options['dpi'] = int(130)
        # # module height is the barcode bar height in mm
        # ean.default_writer_options['module_height'] = float(5)
        # # text distance is the distance between the bottom of the barcode, and the top of the text in mm
        # ean.default_writer_options['text_distance'] = 1
        # # font size is the text size in pt
        # ean.default_writer_options['font_size'] = int(6)
        # # quiet zone is the distance from the ends of the barcode to the ends of the image in mm
        # ean.default_writer_options['quiet_zone'] = 2
        # save barcode image with generated filename
        print("generating barcode image")
        with tempfile.NamedTemporaryFile(dir=tempdir, suffix='.png', delete=False) as initial_temp_file:
            ean(input_string, writer=ImageWriter()).write(initial_temp_file, options=options)
            filename = initial_temp_file.name
        print(filename)
        print("success, barcode image path is: " + filename)
        print("opening " + str(filename) + " to add border")
        barcode_image = pil_Image.open(str(filename))  # open image as pil object
        print("success")
        print("adding barcode and saving")
        img_save = pil_ImageOps.expand(barcode_image, border=0,
                                        fill='white')  # add border around image
        width, height = img_save.size  # get image size of barcode with border
        # write out image to file
        with tempfile.NamedTemporaryFile(dir=tempdir, suffix='.png', delete=False) as final_barcode_path:
            img_save.save(final_barcode_path.name)
            print("success, final barcode path is: " + final_barcode_path.name)
        return final_barcode_path.name, width, height

    def interpret_barcode_string(upc_barcode_string):
        if not upc_barcode_string == '':
            try:
                _ = int(upc_barcode_string)  # check that "upc_barcode_string" can be cast to int
            except ValueError:
                raise ValueError("Input contents are not an integer")
            # select barcode type, specify barcode, and select image writer to save as png
            if len(upc_barcode_string) < 10:
                upc_barcode_string = upc_barcode_string.rjust(11, '0')
            if len(upc_barcode_string) <= 11:
                upc_barcode_string = upc_barcode_string.ljust(12, '0')
            else:
                raise ValueError("Input contents are more than 11 characters")
        else:
            raise ValueError("Input is empty")
        return upc_barcode_string

    def do_process_workbook():
        # this is called as a background thread to ensure the interface is responsive
        print("creating temp directory")
        with tempfile.TemporaryDirectory() as tempdir:
            print("temp directory created as: " + tempdir)
            count = 0
            save_counter = 0

            for _ in output_worksheet.iter_rows():  # iterate over all rows in current worksheet
                try:
                    count += 1
                    if count not in invoice_rows:
                        # get code from column selected in input_colum_spinbox, on current row,
                        # add a zeroes to the end if option is selected to make seven or 12 digits
                        print("getting cell contents on line number " + str(count))
                        upc_barcode_string = str(output_worksheet["B" + str(count)].value)
                        print("cell contents are: " + upc_barcode_string)
                        print(upc_barcode_string[-12:][:-1])
                        upc_barcode_string = interpret_barcode_string(upc_barcode_string[-12:][:-1])
                        print(upc_barcode_string)
                        generated_barcode_path, width, height = generate_barcode(upc_barcode_string, tempdir)
                        # resize cell to size of image
                        output_worksheet.column_dimensions['A'].width = int(math.ceil(float(width) * .15))
                        output_worksheet.row_dimensions[count].height = int(math.ceil(float(height) * .75))

                        # open image with as openpyxl image object
                        print("opening " + generated_barcode_path + " to insert into output spreadsheet")
                        img = OpenPyXlImage(generated_barcode_path)
                        print("success")
                        # attach image to cell
                        print("adding image to cell")
                        # add image to cell
                        output_worksheet.add_image(img, anchor='A' + str(count))
                        save_counter += 1
                        print("success")
                except Exception as barcode_error:
                    print(barcode_error)
                # This save in the loop frees references to the barcode images,
                #  so that python's garbage collector can clear them
                if save_counter >= 100:
                    print("saving intermediate workbook to free file handles")
                    output_spreadsheet.save(output_spreadsheet_name)
                    print("success")
                    save_counter = 1
            print("saving workbook to file")
            output_spreadsheet.save(output_spreadsheet_name)
            print("success")

    do_process_workbook()
    return output_filename
