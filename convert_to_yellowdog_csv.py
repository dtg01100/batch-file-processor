
import csv
from datetime import datetime
from typing import Dict

import line_from_mtc_edi_to_dict
import utils
from query_runner import query_runner


def edi_convert(edi_process, output_filename, settings_dict, parameters_dict, each_upc_lookup):

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
            self.invoice_date = datetime.strftime(utils.datetime_from_invtime(self.arec_line['invoice_date']), "%Y%m%d")
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
                        self.inv_fetcher.fetch_cust(self.arec_line['invoice_number']),
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
                output_filename+".csv",
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
