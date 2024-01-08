import csv
import os
from decimal import Decimal
from typing import List, Dict, TextIO

import line_from_mtc_edi_to_dict
import upc_e_to_upc_a
from query_runner import query_runner


def edi_convert(edi_process, output_filename, parameters_dict, settings_dict):

    class poFetcher:
        def __init__(self, settings_dict):
            self.query_object = None
            self.settings = settings_dict

        def _db_connect(self):
            self.query_object = query_runner(
                self.settings["as400_username"],
                self.settings["as400_password"],
                self.settings["as400_address"],
                f"{self.settings['odbc_driver']}",
            )

        def fetch_po_number(self, invoice_number):
            if self.query_object is None:
                self._db_connect()
            qry_ret = self.query_object.run_arbitrary_query(
                f"""
                select ohhst.bte4cd
                from dacdata.ohhst ohhst
                where ohhst.bthhnb = {int(invoice_number)}
                """
            )
            if len(qry_ret) == 0:
                ret_str = "no_po_found    "
            else:
                ret_str = str(qry_ret[0][0])
            return ret_str


    def convert_to_price(value):
        return (value[:-2].lstrip("0") if not value[:-2].lstrip("0") == "" else "0") + "." + value[-2:]

    class YDogWriter:
        def __init__(self, outfile_obj) -> None:
            self.arec_line: Dict = {}
            self.brec_lines: list[Dict | None] = []
            self.crec_lines: list[Dict | None] = []
            self.output_csv_writer = csv.writer(
                outfile_obj,
                dialect="excel",
                lineterminator="\r\n",
                quoting=csv.QUOTE_ALL,
                )

        def flush_to_csv(self):
            expenselist = []
            self.brec_lines.reverse()
            self.crec_lines.reverse()
            while len(self.crec_lines) > 0:
                expenselist.append(convert_to_price(self.crec_lines.pop()['amount']))
            while len(self.brec_lines) > 0:
                curline = self.brec_lines.pop()
                self.output_csv_writer.writerow(
                    [
                        convert_to_price(self.arec_line['invoice_total']),
                        curline["unit_multiplier"],
                        curline["description"],
                        curline['qty_of_units'],
                        '',
                        self.arec_line['invoice_date'],
                        '',
                        self.arec_line['invoice_number'],
                        self.arec_line['cust_vendor'],
                        '',
                        '',
                        curline['upc_number']
                    ] + expenselist
                )
            print("stub: csv writeout")

        def add_line(self, new_line):
            if new_line is not None:
                if new_line["record_type"] == "A":
                    if len(self.brec_lines) > 0:
                        self.flush_to_csv()
                    self.arec_line = new_line
                if new_line["record_type"] == "B":
                    self.brec_lines.append(new_line)
                if new_line["record_type"] == "C":
                    self.crec_lines.append(new_line)
                    print("stub: crec_handling")


    with open(edi_process, encoding="utf-8") as work_file:  # open input file
        with open(output_filename, "w", newline="", encoding="utf-8") as outfile_obj:
            yellowdog_writer = YDogWriter(outfile_obj)
            for line in work_file.readlines():
                line_dict = line_from_mtc_edi_to_dict.capture_records(line)
                yellowdog_writer.add_line(line_dict)
            yellowdog_writer.flush_to_csv()
    return output_filename
