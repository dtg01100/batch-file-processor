import csv
from datetime import datetime
from typing import Dict

import utils
from convert_base import CSVConverter, create_edi_convert_wrapper


class YellowdogConverter(CSVConverter):
    """Converter for Yellowdog CSV format with deferred writing and DB lookups."""

    def initialize_output(self) -> None:
        """Initialize Yellowdog writer with CSV file and headers."""
        super().initialize_output()
        self.yellowdog_writer = self.YDogWriter(self.csv_file, self.settings_dict)

    def process_record_a(self, record: dict) -> None:
        """Process A record - triggers flush of previous invoice data"""
        self.yellowdog_writer.add_line(record)

    def process_record_b(self, record: dict) -> None:
        """Process B record - add to line item buffer"""
        self.yellowdog_writer.add_line(record)

    def process_record_c(self, record: dict) -> None:
        """Process C record - add to charge/adjustment buffer"""
        self.yellowdog_writer.add_line(record)

    def finalize_output(self) -> str:
        """Flush remaining data and close CSV file"""
        self.yellowdog_writer.flush_to_csv()
        return super().finalize_output()

    class YDogWriter:
        """Internal helper class for deferred writing of Yellowdog CSV records"""
        def __init__(self, csv_writer, settings_dict) -> None:
            self.inv_fetcher = utils.invFetcher(settings_dict)
            self.arec_line: Dict = {}
            self.brec_lines: list[Dict | None] = []
            self.crec_lines: list[Dict | None] = []
            self.output_csv_writer = csv_writer
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
            """Write buffered invoice data to CSV file"""
            self.brec_lines.reverse()
            self.crec_lines.reverse()
            try:
                self.invoice_date = datetime.strftime(
                    utils.datetime_from_invtime(self.arec_line.get('invoice_date', '000000')),
                    "%Y%m%d"
                )
            except ValueError:
                self.invoice_date = "N/A"
            self.invoice_total = utils.convert_to_price(
                str(utils.dac_str_int_to_int(self.arec_line.get('invoice_total', '000000')))
            )
            lineno = 0
            try:
                invoice_number_int = int(self.arec_line.get('invoice_number', '0'))
            except ValueError:
                invoice_number_int = 0

            while len(self.brec_lines) > 0:
                curline = self.brec_lines.pop()
                if curline is not None:
                    self.output_csv_writer.writerow(
                        [
                            self.invoice_total,
                            curline.get("description", ""),
                            curline.get('vendor_item', ''),
                            utils.convert_to_price(curline.get('unit_cost', '000000')),
                            utils.dac_str_int_to_int(curline.get('qty_of_units', '0')),
                            self.inv_fetcher.fetch_uom_desc(
                                curline.get('vendor_item', ''),
                                curline.get('unit_multiplier', '1'),
                                lineno,
                                invoice_number_int
                            ),
                            self.invoice_date,
                            self.arec_line.get('invoice_number', '0'),
                            self.inv_fetcher.fetch_cust_name(self.arec_line.get('invoice_number', '0')),
                            self.inv_fetcher.fetch_po(self.arec_line.get('invoice_number', '0')),
                            curline.get('upc_number', '')
                        ]
                    )
                    lineno += 1

            while len(self.crec_lines) > 0:
                curline = self.crec_lines.pop()
                if curline is not None:
                    self.output_csv_writer.writerow(
                        [
                            utils.convert_to_price(
                                str(utils.dac_str_int_to_int(self.arec_line.get('invoice_total', '0')))
                            ),
                            curline.get("description", ""),
                            9999999,
                            utils.convert_to_price(curline.get('amount', '000000')),
                            1,
                            '',
                            self.invoice_date,
                            self.arec_line.get('invoice_number', '0'),
                            self.inv_fetcher.fetch_cust_name(self.arec_line.get('invoice_number', '0')),
                            ""
                        ]
                    )

        def add_line(self, new_line):
            """Add line to buffer, flushing if new A record is encountered"""
            if new_line is not None:
                if new_line["record_type"] == "A":
                    if len(self.brec_lines) > 0:
                        self.flush_to_csv()
                    self.arec_line = new_line
                if new_line["record_type"] == "B":
                    self.brec_lines.append(new_line)
                if new_line["record_type"] == "C":
                    self.crec_lines.append(new_line)


edi_convert = create_edi_convert_wrapper(YellowdogConverter)
