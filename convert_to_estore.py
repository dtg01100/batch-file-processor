import line_from_mtc_edi_to_dict
import csv
import os
from datetime import datetime
from decimal import Decimal
from typing import List



class CustomerLookupError(Exception):
    pass


def edi_convert(edi_process, output_filename_initial, settings_dict, parameters_dict):

    def convert_to_price(value):
        retprice = (value[:-2].lstrip("0") if not value[:-2].lstrip("0") == "" else "0") + "." + value[-2:]
        try:
            return (Decimal(retprice))
        except Exception:
            return 0

    def qty_to_int(qty):
        if qty.startswith("-"):
            wrkqty = int(qty[1:])
            wrkqtyint = wrkqty - (wrkqty * 2)
        else:
            try:
                wrkqtyint = int(qty)
            except ValueError:
                wrkqtyint = 0
        return wrkqtyint

    def add_row(rowdict:dict):
        column_list = []
        for cell in rowdict.values():
            column_list.append(cell)
        csv_file.writerow(column_list)

    def flush_write_queue(rowlist:List[dict], invoice_total):
        for row in rowlist:
            add_row(row)
        # Add trailer
        if len(invoice_total) > 0:
            trailer_row = {
                'Record Type': 'T',
                'Invoice Cost': sum(invoice_total)
            }
            add_row(trailer_row)
        rowlist.clear()
        invoice_total.clear()
        return(rowlist)


    with open(edi_process) as work_file:  # open input file
        work_file_lined = [n for n in work_file.readlines()]  # make list of lines
        output_filename = os.path.join(os.path.dirname(output_filename_initial), f'eInvCCANDY.{datetime.strftime(datetime.now(), "%Y%B%d%H%M%S")}')
        f = open(
            output_filename, "w", newline=""
        )  # open work file, overwriting old file
        csv_file = csv.writer(f, dialect="excel", lineterminator="\r\n")

        row_dict_list:List[dict] = []
        shipper_mode = False
        shipper_parent_item = False
        shipper_accum = []
        invoice_accum = []

        current_invoice_no = 0
        invoice_index = 0
        for line_num, line in enumerate(
            work_file_lined
        ):  # iterate over work file contents
            input_edi_dict = line_from_mtc_edi_to_dict.capture_records(line)
            if input_edi_dict is not None:
                prev_row_dict = input_edi_dict
                if input_edi_dict["record_type"] == "A":
                    shipper_mode = False
                    invoice_index = 0
                    row_dict = {
                        'Record Type': 'H',
                        'Store Number': input_edi_dict['cust_vendor'],
                        'Vendor OId': 'ccandy',
                        'Invoice Number': input_edi_dict['invoice_number'],
                        'Purchase Order': '',
                        'Invoice Date': input_edi_dict['invoice_date']
                    }
                    add_row(row_dict)
                if input_edi_dict["record_type"] == "B":
                    row_dict = {
                        'Record Type': 'D',
                        'Detail Type': 'I',
                        'Subcategory OId': '',
                        'Vendor Item': input_edi_dict['vendor_item'],
                        'Vendor Pack': input_edi_dict['unit_multiplier'],
                        'Item Description': input_edi_dict['description'],
                        'Item Pack': '',
                        'GTIN': input_edi_dict['upc_number'],
                        'GTIN Type': '',
                        'QTY': qty_to_int(input_edi_dict['qty_of_units']),
                        'Unit Cost': input_edi_dict['unit_cost'],
                        'Unit Retail': input_edi_dict['suggested_retail_price'],
                        'Extended Cost': convert_to_price(input_edi_dict['unit_cost']) * qty_to_int(input_edi_dict['qty_of_units']),
                        'NULL': '',
                        'Extended Retail': ''
                    }

                    if input_edi_dict['parent_item_number'] == input_edi_dict['vendor_item']:
                        print("enter shipper mode")
                        shipper_mode = True
                        shipper_parent_item = True
                        row_dict['Detail Type'] = 'D'
                        shipper_line_number = invoice_index
                    if shipper_mode:
                        if sum(shipper_accum) != 0:
                            print(f"shipper accum is {str(sum(shipper_accum))}")
                        if input_edi_dict['parent_item_number'] not in ["000000",'\n']:
                            if shipper_parent_item:
                                shipper_parent_item = False
                            else:
                                row_dict['Detail Type'] = 'C'
                                shipper_accum.append(convert_to_price(input_edi_dict['unit_cost']) * qty_to_int(input_edi_dict['qty_of_units']))
                        else:
                            try:
                                row_dict_list[shipper_line_number]['Unit Cost'] = sum(shipper_accum)
                                row_dict_list[shipper_line_number]['QTY'] = len(shipper_accum)
                            except Exception as error:
                                print(error)
                            shipper_accum = []
                            print("leave shipper mode")
                            shipper_mode = False

                    row_dict_list.append(row_dict)

                    invoice_accum.append(row_dict['Extended Cost'])
                    invoice_index += 1
                if input_edi_dict["record_type"] != "B":
                    row_dict_list = flush_write_queue(row_dict_list, invoice_accum)
                    invoice_index = 0
        row_dict_list = flush_write_queue(row_dict_list, invoice_accum)


        f.close()  # close output file
    return output_filename
