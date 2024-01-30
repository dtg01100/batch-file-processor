import csv
import datetime
from typing import Dict

import line_from_mtc_edi_to_dict
import utils
from query_runner import query_runner


def edi_convert(edi_process, output_filename, parameters_dict, settings_dict):

    class invFetcher:
        def __init__(self, settings_dict):
            self.query_object = None
            self.settings = settings_dict
            self.last_answer_dict = {
                "invoice_num": "0",
                "po": 0,
                "cust": 0,
            }

        def _db_connect(self):
            self.query_object = query_runner(
                self.settings["as400_username"],
                self.settings["as400_password"],
                self.settings["as400_address"],
                f"{self.settings['odbc_driver']}",
            )

        def fetch_numbers(self, invoice_number):
            if invoice_number == self.last_answer_dict['invoice_num']:
                return self.last_answer_dict
            if self.query_object is None:
                self._db_connect()
            qry_ret = self.query_object.run_arbitrary_query(
                f"""
                select ohhst.bte4cd, ohhst.btabnb
                from dacdata.ohhst ohhst
                where ohhst.bthhnb = {str(int(invoice_number))}
                """
            )
            self.last_answer_dict['invoice_num'] = invoice_number
            if len(qry_ret) == 0:
                self.last_answer_dict['po'] = "no_po_found"
                self.last_answer_dict['cust'] = "no_cust_found"
            else:
                self.last_answer_dict['po'] = str(qry_ret[0][0])
                self.last_answer_dict['cust'] = str(qry_ret[0][1])

        def fetch_po(self, invoice_number):
            self.fetch_numbers(invoice_number)
            return self.last_answer_dict['po']

        def fetch_cust(self, invoice_number):
            self.fetch_numbers(invoice_number)
            return self.last_answer_dict['cust']

    def dac_str_int_to_int(dacstr: str) -> int:
        if dacstr.strip() == "":
            return 0
        if dacstr.startswith('-'):
            return int(dacstr[1:]) - (int(dacstr[1:]) * 2)
        else:
            return int(dacstr)

    class YDogWriter:
        def __init__(self, outfile_obj) -> None:
            self.inv_fetcher = invFetcher(settings_dict)
            self.arec_line: Dict = {}
            self.brec_lines: list[Dict | None] = []
            self.crec_lines: list[Dict | None] = []
            self.output_csv_writer = csv.writer(
                outfile_obj,
                dialect="excel",
                lineterminator="\r\n",
                quoting=csv.QUOTE_ALL,
                )
            self.output_csv_writer.writerow(
                [
                    "Invoice Total",
                    "Unit Multiplier",
                    "Description",
                    "Item Number",
                    "Cost",
                    "Quantity",
                    "Invoice Date",
                    "Invoice Number",
                    "Customer Number",
                    "UPC",
                ]
            )

        def flush_to_csv(self):
            self.brec_lines.reverse()
            self.crec_lines.reverse()
            customer_number = self.inv_fetcher.fetch_cust(self.arec_line['invoice_number'])
            invoice_date = datetime.strftime(utils.datetime_from_invtime(self.arec_line['invoice_date']), "%Y%m%d")
            invoice_total = utils.convert_to_price(str(dac_str_int_to_int(self.arec_line['invoice_total'])))
            while len(self.brec_lines) > 0:
                curline = self.brec_lines.pop()
                self.output_csv_writer.writerow(
                    [
                        invoice_total,
                        curline["combo_code"].strip(),
                        curline["description"],
                        curline['vendor_item'],
                        utils.convert_to_price(curline['unit_cost']),
                        utils.dac_str_int_to_int(curline['qty_of_units']),
                        invoice_date,
                        self.arec_line['invoice_number'],
                        customer_number,
                        curline['upc_number']
                    ]
                )
            print("stub: csv writeout")
            while len(self.crec_lines) > 0:
                curline = self.crec_lines.pop()
                self.output_csv_writer.writerow(
                    [
                        utils.convert_to_price(str(dac_str_int_to_int(self.arec_line['invoice_total']))),
                        '',
                        curline["description"],
                        'changeme',
                        utils.dac_str_int_to_int(curline['amount']),
                        1,
                        invoice_total,
                        self.arec_line['invoice_number'],
                        customer_number,
                        ""
                    ]
                )

        def add_line(self, new_line):
            if new_line is not None:
                if new_line["record_type"] == "A":
                    self.arec_line = new_line
                    if len(self.brec_lines) > 0:
                        self.flush_to_csv()
                    self.arec_line = new_line
                if new_line["record_type"] == "B":
                    self.brec_lines.append(new_line)
                if new_line["record_type"] == "C":
                    self.crec_lines.append(new_line)

    with open(edi_process, encoding="utf-8") as work_file:  # open input file
        with open(
                output_filename,
                "w",
                newline="",
                encoding="utf-8"
        ) as outfile_obj:
            yellowdog_writer = YDogWriter(outfile_obj)
            for line in work_file.readlines():
                line_dict = line_from_mtc_edi_to_dict.capture_records(line)
                yellowdog_writer.add_line(line_dict)
            yellowdog_writer.flush_to_csv()
    return output_filename
