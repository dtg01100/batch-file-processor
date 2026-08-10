
import csv
from datetime import datetime
from typing import Dict

import utils
from query_runner import query_runner


def edi_convert(edi_process, output_filename, settings_dict, parameters_dict, upc_lookup):

    invFetcher = utils.invFetcher

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
                    "Description",
                    "Item Number",
                    "Cost",
                    "Quantity",
                    "UOM Desc.",
                    "Invoice Date",
                    "Invoice Number",
                    "Customer Name",
                    "Customer PO Number",
                    "UPC",
                ]
            )
            self.brec_index = 0
            self.uom_desc = ""
            self.invoice_date = ""
            self.invoice_total = 0

        def flush_to_csv(self):
            self.brec_lines.reverse()
            self.crec_lines.reverse()
            try:
                self.invoice_date = datetime.strftime(utils.datetime_from_invtime(self.arec_line['invoice_date']), "%Y%m%d")
            except ValueError:
                self.invoice_date = "N/A"
            self.invoice_total = utils.convert_to_price(str(utils.dac_str_int_to_int(self.arec_line['invoice_total'])))
            lineno = 0
            while len(self.brec_lines) > 0:
                curline = self.brec_lines.pop()
                self.output_csv_writer.writerow(
                    [
                        self.invoice_total,
                        curline["description"],
                        curline['vendor_item'],
                        utils.convert_to_price(curline['unit_cost']),
                        utils.dac_str_int_to_int(curline['qty_of_units']),
                        self.inv_fetcher.fetch_uom_desc(curline['vendor_item'], curline['unit_multiplier'], lineno, int(self.arec_line['invoice_number'])),
                        self.invoice_date,
                        self.arec_line['invoice_number'],
                        self.inv_fetcher.fetch_cust_name(self.arec_line['invoice_number']),
                        self.inv_fetcher.fetch_po(self.arec_line['invoice_number']),
                        curline['upc_number']
                    ]
                )
                lineno += 1
            while len(self.crec_lines) > 0:
                curline = self.crec_lines.pop()
                self.output_csv_writer.writerow(
                    [
                        utils.convert_to_price(str(utils.dac_str_int_to_int(self.arec_line['invoice_total']))),
                        curline["description"],
                        9999999,
                        utils.convert_to_price(curline['amount']),
                        1,
                        '',
                        self.invoice_date,
                        self.arec_line['invoice_number'],
                        self.inv_fetcher.fetch_cust_name(self.arec_line['invoice_number']),
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
                output_filename+".csv",
                "w",
                newline="",
                encoding="utf-8"
        ) as outfile_obj:
            yellowdog_writer = YDogWriter(outfile_obj)
            for line in work_file.readlines():
                line_dict = utils.capture_records(line)
                yellowdog_writer.add_line(line_dict)
            yellowdog_writer.flush_to_csv()
    return output_filename+".csv"
