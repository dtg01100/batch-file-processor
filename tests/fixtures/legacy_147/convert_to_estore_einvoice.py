import csv
import os
from datetime import datetime
from decimal import Decimal
from typing import List

import utils


def edi_convert(edi_process, output_filename_initial, settings_dict, parameters_dict, upc_lookup):
    def convert_to_price(value):
        retprice = (
            (value[:-2].lstrip("0") if not value[:-2].lstrip("0") == "" else "0")
            + "."
            + value[-2:]
        )
        try:
            return Decimal(retprice)
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

    def add_row(rowdict: dict):
        column_list = []
        for cell in rowdict.values():
            column_list.append(cell)
        csv_file.writerow(column_list)

    def leave_shipper_mode(
        shipper_mode, row_dict_list, shipper_line_number, shipper_accum
    ):
        if shipper_mode:
            # write out shipper
            # row_dict_list[shipper_line_number]['Unit Cost'] = sum(shipper_accum)
            row_dict_list[shipper_line_number - 1]["QTY"] = len(shipper_accum)
            shipper_accum.clear()
            print("leave shipper mode")
            shipper_mode = False
        return shipper_mode, row_dict_list, shipper_line_number, shipper_accum

    def flush_write_queue(
        rowlist: List[dict],
        invoice_total,
        shipper_line_number,
        shipper_accum,
        shipper_mode,
    ):
        shipper_mode, rowlist, shipper_line_number, shipper_accum = leave_shipper_mode(
            shipper_mode, rowlist, shipper_line_number, shipper_accum
        )
        for row in rowlist:
            add_row(row)
        # Add trailer
        if len(invoice_total) > 0:
            trailer_row = {"Record Type": "T", "Invoice Cost": sum(invoice_total)}
            add_row(trailer_row)
        rowlist.clear()
        invoice_total.clear()
        return (rowlist, shipper_mode, shipper_accum, shipper_line_number)

    store_number = parameters_dict['estore_store_number']
    vendor_oid = parameters_dict['estore_Vendor_OId']
    vendor_name = parameters_dict['estore_vendor_NameVendorOID']

    with open(edi_process, encoding="utf-8") as work_file:  # open input file
        work_file_lined = list(work_file.readlines())  # make list of lines
        output_filename = os.path.join(
            os.path.dirname(output_filename_initial),
            f'eInv{vendor_name}.{datetime.strftime(datetime.now(), "%Y%m%d%H%M%S")}.csv',
        )
        with open(
            output_filename, "w", newline="", encoding="utf-8"
        ) as f:  # open work file, overwriting old file
            csv_file = csv.writer(f, dialect="excel", lineterminator="\r\n")

            row_dict_list: List[dict] = []
            shipper_mode = False
            shipper_parent_item = False
            shipper_accum = []
            invoice_accum = []
            shipper_line_number = 0

            invoice_index = 0
            for line_num, line in enumerate(
                work_file_lined
            ):  # iterate over work file contents
                input_edi_dict = utils.capture_records(line)
                if input_edi_dict is not None:
                    if input_edi_dict["record_type"] == "A":
                        (
                            shipper_mode,
                            row_dict_list,
                            shipper_line_number,
                            shipper_accum,
                        ) = leave_shipper_mode(
                            shipper_mode,
                            row_dict_list,
                            shipper_line_number,
                            shipper_accum,
                        )
                        if len(invoice_accum) > 0:
                            trailer_row = {
                                "Record Type": "T",
                                "Invoice Cost": sum(invoice_accum),
                            }
                            row_dict_list.append(trailer_row)
                            invoice_index += 1
                            invoice_accum.clear()
                        if not input_edi_dict["invoice_date"] == "000000":
                            invoice_date = datetime.strptime(
                                input_edi_dict["invoice_date"], "%m%d%y"
                            )
                            write_invoice_date = datetime.strftime(
                                invoice_date, "%Y%m%d"
                            )
                        else:
                            write_invoice_date = "00000000"
                        row_dict = {
                            "Record Type": "H",
                            "Store Number": store_number,
                            "Vendor OId": vendor_oid,
                            "Invoice Number": input_edi_dict["invoice_number"],
                            "Purchase Order": "",
                            "Invoice Date": write_invoice_date,
                        }
                        row_dict_list.append(row_dict)
                        invoice_index += 1
                    if input_edi_dict["record_type"] == "B":
                        try:
                            upc_entry = upc_lookup[int(input_edi_dict["vendor_item"])][1]
                        except KeyError:
                            print("cannot find each upc")
                            upc_entry = input_edi_dict["upc_number"]
                        row_dict = {
                            "Record Type": "D",
                            "Detail Type": "I",
                            "Subcategory OId": "",
                            "Vendor Item": input_edi_dict["vendor_item"],
                            "Vendor Pack": input_edi_dict["unit_multiplier"],
                            "Item Description": input_edi_dict["description"].strip(),
                            "Item Pack": "",
                            "GTIN": upc_entry.strip(),
                            "GTIN Type": "",
                            "QTY": qty_to_int(input_edi_dict["qty_of_units"]),
                            "Unit Cost": convert_to_price(input_edi_dict["unit_cost"]),
                            "Unit Retail": convert_to_price(
                                input_edi_dict["suggested_retail_price"]
                            ),
                            "Extended Cost": convert_to_price(
                                input_edi_dict["unit_cost"]
                            )
                            * qty_to_int(input_edi_dict["qty_of_units"]),
                            "NULL": "",
                            "Extended Retail": "",
                        }

                        if (
                            input_edi_dict["parent_item_number"]
                            == input_edi_dict["vendor_item"]
                        ):
                            (
                                shipper_mode,
                                row_dict_list,
                                shipper_line_number,
                                shipper_accum,
                            ) = leave_shipper_mode(
                                shipper_mode,
                                row_dict_list,
                                shipper_line_number,
                                shipper_accum,
                            )
                            print("enter shipper mode")
                            shipper_mode = True
                            shipper_parent_item = True
                            row_dict["Detail Type"] = "D"
                            shipper_line_number = invoice_index
                        if shipper_mode:
                            if input_edi_dict["parent_item_number"] not in [
                                "000000",
                                "\n",
                            ]:
                                if shipper_parent_item:
                                    shipper_parent_item = False
                                else:
                                    row_dict["Detail Type"] = "C"
                                    shipper_accum.append(
                                        convert_to_price(input_edi_dict["unit_cost"])
                                        * qty_to_int(input_edi_dict["qty_of_units"])
                                    )
                            else:
                                try:
                                    (
                                        shipper_mode,
                                        row_dict_list,
                                        shipper_line_number,
                                        shipper_accum,
                                    ) = leave_shipper_mode(
                                        shipper_mode,
                                        row_dict_list,
                                        shipper_line_number,
                                        shipper_accum,
                                    )
                                except Exception as error:
                                    print(error)

                        row_dict_list.append(row_dict)
                        invoice_index += 1

                        invoice_accum.append(row_dict["Extended Cost"])

            (
                row_dict_list,
                shipper_mode,
                shipper_accum,
                shipper_line_number,
            ) = flush_write_queue(
                row_dict_list,
                invoice_accum,
                shipper_line_number,
                shipper_accum,
                shipper_mode,
            )

    return output_filename
