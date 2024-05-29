import csv
import os
from datetime import datetime
from decimal import Decimal
from typing import List
from query_runner import query_runner

import line_from_mtc_edi_to_dict
import utils

class invFetcher:
    def __init__(self, settings_dict):
        self.query_object = None
        self.settings = settings_dict
        self.last_invoice_number = 0
        self.uom_lut = {0: "N/A"}
        self.last_invno = 0
        self.po = ""
        self.cust = ""

    def _db_connect(self):
        self.query_object = query_runner(
            self.settings["as400_username"],
            self.settings["as400_password"],
            self.settings["as400_address"],
            f"{self.settings['odbc_driver']}",
        )

    def _run_qry(self, qry_str):
        if self.query_object is None:
            self._db_connect()
        qry_return = self.query_object.run_arbitrary_query(qry_str)
        return qry_return

    def fetch_po(self, invoice_number):
        if invoice_number == self.last_invoice_number:
            return self.po
        else:
            qry_ret = self._run_qry(
                f"""
                SELECT
            trim(ohhst.bte4cd),
                trim(ohhst.bthinb)
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
                self.cust = qry_ret[0][1]
            except IndexError:
                self.po = ""
            return self.po

    def fetch_cust(self, invoice_number):
        self.fetch_po(invoice_number)
        return self.cust

    def fetch_uom_desc(self, itemno, uommult, lineno, invno):
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
                if int(uommult) > 1:
                    return "HI"
                else:
                    return "LO"


def edi_convert(edi_process, output_filename_initial, settings_dict, parameters_dict, each_upc_lookup):
    inv_fetcher = invFetcher(settings_dict)
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
            csv_file.writerow(
                [
                    "Store #",
                    "Vendor (OID)",
                    "Invoice #",
                    "Purchase Order #",
                    "Invoice Date",
                    "Total Invoice Cost",
                    "Detail Type",
                    "Subcategory (OID)",
                    "Vendor Item #",
                    "Vendor Pack",
                    "Item Description",
                    "Pack",
                    "GTIN/PLU",
                    "GTIN Type",
                    "Quantity",
                    "Unit Cost",
                    "Unit Retail",
                    "Extended Cost",
                    "Extended Retail",
                ]
            )
            for line_num, line in enumerate(
                work_file_lined
            ):  # iterate over work file contents
                input_edi_dict = line_from_mtc_edi_to_dict.capture_records(line)
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
                        row_dict_header = {
                            "Store Number": store_number,
                            "Vendor OId": vendor_oid,
                            "Invoice Number": input_edi_dict["invoice_number"],
                            "Purchase Order": inv_fetcher.fetch_po(input_edi_dict['invoice_number']),
                            "Invoice Date": write_invoice_date,
                            "Total Invoice Cost": utils.convert_to_price(str(utils.dac_str_int_to_int(input_edi_dict['invoice_total'])))
                        }
                        # row_dict_list.append(row_dict)
                        invoice_index += 1
                    if input_edi_dict["record_type"] == "B":
                        try:
                            upc_entry = each_upc_lookup[int(input_edi_dict["vendor_item"])]
                        except KeyError:
                            print("cannot find each upc")
                            upc_entry = input_edi_dict["upc_number"]
                        row_dict = {
                            "Detail Type": "I",
                            "Subcategory OId": "",
                            "Vendor Item": input_edi_dict["vendor_item"],
                            "Vendor Pack": input_edi_dict["unit_multiplier"],
                            "Item Description": input_edi_dict["description"].strip(),
                            "Item Pack": "",
                            "GTIN": upc_entry.strip(),
                            "GTIN Type": "UP",
                            "QTY": qty_to_int(input_edi_dict["qty_of_units"]),
                            "Unit Cost": convert_to_price(input_edi_dict["unit_cost"]),
                            "Unit Retail": convert_to_price(
                                input_edi_dict["suggested_retail_price"]
                            ),
                            "Extended Cost": convert_to_price(
                                input_edi_dict["unit_cost"]
                            )
                            * qty_to_int(input_edi_dict["qty_of_units"]),
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

                        row_dict_list.append({**row_dict_header, **row_dict})
                        invoice_index += 1

                        invoice_accum.append(row_dict["Extended Cost"])

                    if input_edi_dict["record_type"] == 'C':

                        row_dict = {
                            "Detail Type": "S",
                            "Subcategory OId": parameters_dict["estore_c_record_OID"],
                            "Vendor Item": "",
                            "Vendor Pack": 1,
                            "Item Description": input_edi_dict["description"].strip(),
                            "Item Pack": "",
                            "GTIN": "",
                            "GTIN Type": "",
                            "QTY": 1,
                            "Unit Cost": convert_to_price(input_edi_dict["amount"]),
                            "Unit Retail": 0,
                            "Extended Cost": convert_to_price(
                                input_edi_dict["amount"]
                            ),
                            "Extended Retail": "",
                        }

                        row_dict_list.append({**row_dict_header, **row_dict})
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
