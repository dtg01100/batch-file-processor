import csv
import os
from datetime import datetime
from decimal import Decimal
from typing import List
from query_runner import query_runner

import utils
from convert_base import CSVConverter, create_edi_convert_wrapper


class EstoreEinvoiceGenericConverter(CSVConverter):
    """Converter for generic eStore eInvoice CSV format with headers and C record support."""

    class invFetcher:
        """Internal helper class for fetching invoice-related data from database."""
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
                try:
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
                except ValueError:
                    print("cannot parse invoice_number")
                    qry_ret = []
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

    def initialize_output(self) -> None:
        """Initialize output file with dynamic filename and CSV writer"""
        timestamp = datetime.strftime(datetime.now(), "%Y%m%d%H%M%S")
        self.vendor_name = self.parameters_dict['estore_vendor_NameVendorOID']
        self.output_filename = os.path.join(
            os.path.dirname(self.output_filename),
            f'eInv{self.vendor_name}.{timestamp}.csv'
        )
        self.output_file = open(self.output_filename, "w", newline="", encoding="utf-8")
        self.csv_file = csv.writer(
            self.output_file, dialect="excel", lineterminator="\r\n"
        )

        # Initialize invFetcher for DB lookups
        self.inv_fetcher = self.invFetcher(self.settings_dict)

        # Initialize processing state
        self.row_dict_list: List[dict] = []
        self.shipper_mode = False
        self.shipper_parent_item = False
        self.shipper_accum = []
        self.invoice_accum = []
        self.shipper_line_number = 0
        self.invoice_index = 0

        # Write CSV header
        self.csv_file.writerow(
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

    def process_record_a(self, record: dict) -> None:
        """Process A record - flush previous invoice and start new one"""
        self.shipper_mode, self.row_dict_list, self.shipper_line_number, self.shipper_accum = \
            self.leave_shipper_mode(
                self.shipper_mode, self.row_dict_list, self.shipper_line_number, self.shipper_accum
            )

        if len(self.invoice_accum) > 0:
            self.invoice_index += 1
            self.invoice_accum.clear()

        if not record["invoice_date"] == "000000":
            try:
                invoice_date = datetime.strptime(record["invoice_date"], "%m%d%y")
                write_invoice_date = datetime.strftime(invoice_date, "%Y%m%d")
            except ValueError:
                print("cannot parse invoice_date")
                write_invoice_date = "00000000"
        else:
            write_invoice_date = "00000000"

        self.row_dict_header = {
            "Store Number": self.parameters_dict['estore_store_number'],
            "Vendor OId": self.parameters_dict['estore_Vendor_OId'],
            "Invoice Number": record["invoice_number"],
            "Purchase Order": self.inv_fetcher.fetch_po(record['invoice_number']),
            "Invoice Date": write_invoice_date,
            "Total Invoice Cost": utils.convert_to_price(
                str(utils.dac_str_int_to_int(record['invoice_total']))
            )
        }

        self.invoice_index += 1

    def process_record_b(self, record: dict) -> None:
        """Process B record - handle shipper mode and item relationships"""
        try:
            upc_entry = self.upc_lookup[int(record["vendor_item"])][1]
        except KeyError:
            print("cannot find each upc")
            upc_entry = record["upc_number"]
        except ValueError:
            print("cannot parse vendor_item as int")
            upc_entry = record["upc_number"]
        except Exception:
            print("error getting upc")
            upc_entry = record["upc_number"]

        row_dict = {
            "Detail Type": "I",
            "Subcategory OId": "",
            "Vendor Item": record["vendor_item"],
            "Vendor Pack": record["unit_multiplier"],
            "Item Description": record["description"].strip(),
            "Item Pack": "",
            "GTIN": upc_entry.strip(),
            "GTIN Type": "UP",
            "QTY": self._qty_to_int(record["qty_of_units"]),
            "Unit Cost": self._convert_to_price(record["unit_cost"]),
            "Unit Retail": self._convert_to_price(record["suggested_retail_price"]),
            "Extended Cost": self._convert_to_price(record["unit_cost"])
            * self._qty_to_int(record["qty_of_units"]),
            "Extended Retail": "",
        }

        if record["parent_item_number"] == record["vendor_item"]:
            self.shipper_mode, self.row_dict_list, self.shipper_line_number, self.shipper_accum = \
                self.leave_shipper_mode(
                    self.shipper_mode, self.row_dict_list, self.shipper_line_number, self.shipper_accum
                )
            print("enter shipper mode")
            self.shipper_mode = True
            self.shipper_parent_item = True
            row_dict["Detail Type"] = "D"
            self.shipper_line_number = self.invoice_index

        if self.shipper_mode:
            if record["parent_item_number"] not in ["000000", "\n"]:
                if self.shipper_parent_item:
                    self.shipper_parent_item = False
                else:
                    row_dict["Detail Type"] = "C"
                    self.shipper_accum.append(
                        self._convert_to_price(record["unit_cost"])
                        * self._qty_to_int(record["qty_of_units"])
                    )
            else:
                try:
                    self.shipper_mode, self.row_dict_list, self.shipper_line_number, self.shipper_accum = \
                        self.leave_shipper_mode(
                            self.shipper_mode, self.row_dict_list, self.shipper_line_number, self.shipper_accum
                        )
                except Exception as error:
                    print(error)

        self.row_dict_list.append({**self.row_dict_header, **row_dict})
        self.invoice_index += 1
        self.invoice_accum.append(row_dict["Extended Cost"])

    def process_record_c(self, record: dict) -> None:
        """Process C record - handle charge/adjustment records"""
        row_dict = {
            "Detail Type": "S",
            "Subcategory OId": self.parameters_dict["estore_c_record_OID"],
            "Vendor Item": "",
            "Vendor Pack": 1,
            "Item Description": record["description"].strip(),
            "Item Pack": "",
            "GTIN": "",
            "GTIN Type": "",
            "QTY": 1,
            "Unit Cost": self._convert_to_price(record["amount"]),
            "Unit Retail": 0,
            "Extended Cost": self._convert_to_price(record["amount"]),
            "Extended Retail": "",
        }

        self.row_dict_list.append({**self.row_dict_header, **row_dict})
        self.invoice_index += 1
        self.invoice_accum.append(row_dict["Extended Cost"])

    def finalize_output(self) -> str:
        """Flush remaining data and close output file"""
        self.flush_write_queue(
            self.row_dict_list,
            self.invoice_accum,
            self.shipper_line_number,
            self.shipper_accum,
            self.shipper_mode,
        )

        if self.output_file is not None:
            self.output_file.close()

        return self.output_filename

    def _convert_to_price(self, value):
        """Convert DAC price format to Decimal"""
        retprice = (
            (value[:-2].lstrip("0") if not value[:-2].lstrip("0") == "" else "0")
            + "."
            + value[-2:]
        )
        try:
            return Decimal(retprice)
        except Exception:
            return 0

    def _qty_to_int(self, qty):
        """Convert quantity string to integer"""
        if qty.startswith("-"):
            wrkqty = int(qty[1:])
            wrkqtyint = wrkqty - (wrkqty * 2)
        else:
            try:
                wrkqtyint = int(qty)
            except ValueError:
                wrkqtyint = 0
        return wrkqtyint

    def add_row(self, rowdict: dict):
        """Add row to CSV file from dictionary"""
        column_list = []
        for cell in rowdict.values():
            column_list.append(cell)
        self.csv_file.writerow(column_list)

    def leave_shipper_mode(
        self, shipper_mode, row_dict_list, shipper_line_number, shipper_accum
    ):
        """Exit shipper mode and finalize shipper data"""
        if shipper_mode:
            row_dict_list[shipper_line_number - 1]["QTY"] = len(shipper_accum)
            shipper_accum.clear()
            print("leave shipper mode")
            shipper_mode = False
        return shipper_mode, row_dict_list, shipper_line_number, shipper_accum

    def flush_write_queue(
        self, rowlist: List[dict], invoice_total, shipper_line_number, shipper_accum, shipper_mode
    ):
        """Flush all buffered data to CSV file"""
        shipper_mode, rowlist, shipper_line_number, shipper_accum = self.leave_shipper_mode(
            shipper_mode, rowlist, shipper_line_number, shipper_accum
        )
        for row in rowlist:
            self.add_row(row)

        rowlist.clear()
        invoice_total.clear()
        return (rowlist, shipper_mode, shipper_accum, shipper_line_number)


edi_convert = create_edi_convert_wrapper(EstoreEinvoiceGenericConverter)
