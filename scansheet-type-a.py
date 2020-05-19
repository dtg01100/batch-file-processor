import line_from_mtc_edi_to_dict
import openpyxl
from query_runner import query_runner


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
        for items_list_entry in rows_for_export:
            output_worksheet.append(items_list_entry)
        adjust_column_width(output_worksheet)
        output_spreadsheet_name = output_filename
        output_spreadsheet.save(output_spreadsheet_name)
