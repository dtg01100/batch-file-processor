
import csv
from datetime import datetime
from typing import Dict

import line_from_mtc_edi_to_dict
import utils
from query_runner import query_runner


def edi_convert(edi_process, output_filename, parameters_dict, settings_dict):

    class invFetcher:
        def __init__(self, settings_dict):
            self.query_object = None
            self.settings = settings_dict
            self.last_invoice_number = 0
            self.last_invoice_contents = []
            self.po = ""
            self.cust = 0

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

        def _fetch_data(self, invoice_number):
            if invoice_number == self.last_invoice_number:
                return
            else:
                qry_ret = self._run_qry(
                    f"""
                SELECT
                varchar(odhst.buhunb), --Line Number
                CASE odhst.buhvnb
                    WHEN 1 THEN dsanrep.anb8tx
                    WHEN 2 THEN dsanrep.anb9tx
                    WHEN 3 THEN dsanrep.ancatx
                    END, --U/M Description
                ohhst.btabnb, --Customer Number
                ohhst.bte4cd --PO Number
                FROM
                dacdata.ohhst ohhst
                INNER JOIN dacdata.odhst odhst ON
                ohhst.BTHHNB = odhst.BUHHNB
                INNER JOIN dacdata.dsanrep dsanrep ON
                odhst.BUBACD = dsanrep.ANBACD
                WHERE
                odhst.BUHHNB = {str(int(invoice_number))}
                """
                )
                self.last_invoice_number = invoice_number
                self.po = qry_ret[0][3]
                self.cust = qry_ret[0][2]
                self.last_invoice_contents = [i[0:2] for i in qry_ret]

        def fetch_po(self, invoice_number):
            self._fetch_data(invoice_number)
            return self.po

        def fetch_cust(self, invoice_number):
            self._fetch_data(invoice_number)
            return self.cust

        def fetch_uom_desc(self, lineno, invoice_number):
            self._fetch_data(invoice_number)
            last_invoice_lut = dict(self.last_invoice_contents)
            try:
                return last_invoice_lut[str(int(lineno) + 1)]
            except KeyError:
                return "?"

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
                    "Customer Number",
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
            self.invoice_date = datetime.strftime(utils.datetime_from_invtime(self.arec_line['invoice_date']), "%Y%m%d")
            self.invoice_total = utils.convert_to_price(str(utils.dac_str_int_to_int(self.arec_line['invoice_total'])))
            self.brec_index = 0
            self.uom_desc = self.inv_fetcher.fetch_uom_desc(self.brec_index, self.arec_line['invoice_number'])
            while len(self.brec_lines) > 0:
                curline = self.brec_lines.pop()
                self.output_csv_writer.writerow(
                    [
                        self.invoice_total,
                        curline["description"],
                        curline['vendor_item'],
                        utils.convert_to_price(curline['unit_cost']),
                        utils.dac_str_int_to_int(curline['qty_of_units']),
                        self.inv_fetcher.fetch_uom_desc(self.brec_index, self.arec_line['invoice_number']),
                        self.invoice_date,
                        self.arec_line['invoice_number'],
                        self.inv_fetcher.fetch_cust(self.arec_line['invoice_number']),
                        curline['upc_number']
                    ]
                )
                self.brec_index += 1
            while len(self.crec_lines) > 0:
                curline = self.crec_lines.pop()
                self.output_csv_writer.writerow(
                    [
                        utils.convert_to_price(str(utils.dac_str_int_to_int(self.arec_line['invoice_total']))),
                        curline["description"],
                        '',
                        utils.dac_str_int_to_int(curline['amount']),
                        1,
                        '',
                        self.invoice_date,
                        self.arec_line['invoice_number'],
                        self.inv_fetcher.fetch_cust(self.arec_line['invoice_number']),
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
