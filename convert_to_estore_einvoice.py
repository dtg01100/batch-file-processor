import csv
import os
from datetime import datetime
from decimal import Decimal
from typing import List

import utils
from convert_base import CSVConverter, create_edi_convert_wrapper


class EstoreEinvoiceConverter(CSVConverter):
    """Converter for eStore eInvoice CSV format with shipper mode support."""

    PLUGIN_ID = "estore_einvoice"
    PLUGIN_NAME = "Estore eInvoice"
    PLUGIN_DESCRIPTION = (
        "eStore eInvoice format with dynamic filename and shipper mode support"
    )

    CONFIG_FIELDS = [
        {
            "key": "estore_store_number",
            "label": "Store Number",
            "type": "string",
            "default": "",
            "required": True,
            "placeholder": "Enter store number",
            "help": "The store number for eStore eInvoice",
        },
        {
            "key": "estore_Vendor_OId",
            "label": "Vendor OId",
            "type": "string",
            "default": "",
            "required": True,
            "placeholder": "Enter vendor OId",
            "help": "The vendor OId for eStore eInvoice",
        },
        {
            "key": "estore_vendor_NameVendorOID",
            "label": "Vendor Name/OID for Filename",
            "type": "string",
            "default": "",
            "required": True,
            "placeholder": "Enter vendor name",
            "help": "Vendor name/OID used in output filename",
        },
    ]

    def initialize_output(self) -> None:
        timestamp = datetime.strftime(datetime.now(), "%Y%m%d%H%M%S")
        self.vendor_name = self.get_config_value("estore_vendor_NameVendorOID", "")
        self.output_filename = os.path.join(
            os.path.dirname(self.output_filename),
            f"eInv{self.vendor_name}.{timestamp}.csv",
        )
        self.output_file = open(self.output_filename, "w", newline="", encoding="utf-8")
        self.csv_file = csv.writer(
            self.output_file, dialect="excel", lineterminator="\r\n"
        )

        self.row_dict_list: List[dict] = []
        self.shipper_mode = False
        self.shipper_parent_item = False
        self.shipper_accum = []
        self.invoice_accum = []
        self.shipper_line_number = 0
        self.invoice_index = 0

    def process_record_a(self, record: dict) -> None:
        """Process A record - flush previous invoice and start new one"""
        (
            self.shipper_mode,
            self.row_dict_list,
            self.shipper_line_number,
            self.shipper_accum,
        ) = self.leave_shipper_mode(
            self.shipper_mode,
            self.row_dict_list,
            self.shipper_line_number,
            self.shipper_accum,
        )

        if len(self.invoice_accum) > 0:
            trailer_row = {
                "Record Type": "T",
                "Invoice Cost": sum(self.invoice_accum),
            }
            self.row_dict_list.append(trailer_row)
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

        row_dict = {
            "Record Type": "H",
            "Store Number": self.get_config_value("estore_store_number", ""),
            "Vendor OId": self.get_config_value("estore_Vendor_OId", ""),
            "Invoice Number": record["invoice_number"],
            "Purchase Order": "",
            "Invoice Date": write_invoice_date,
        }
        self.row_dict_list.append(row_dict)
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
            "Record Type": "D",
            "Detail Type": "I",
            "Subcategory OId": "",
            "Vendor Item": record["vendor_item"],
            "Vendor Pack": record["unit_multiplier"],
            "Item Description": record["description"].strip(),
            "Item Pack": "",
            "GTIN": upc_entry.strip(),
            "GTIN Type": "",
            "QTY": self._qty_to_int(record["qty_of_units"]),
            "Unit Cost": self._convert_to_price(record["unit_cost"]),
            "Unit Retail": self._convert_to_price(record["suggested_retail_price"]),
            "Extended Cost": self._convert_to_price(record["unit_cost"])
            * self._qty_to_int(record["qty_of_units"]),
            "NULL": "",
            "Extended Retail": "",
        }

        if record["parent_item_number"] == record["vendor_item"]:
            (
                self.shipper_mode,
                self.row_dict_list,
                self.shipper_line_number,
                self.shipper_accum,
            ) = self.leave_shipper_mode(
                self.shipper_mode,
                self.row_dict_list,
                self.shipper_line_number,
                self.shipper_accum,
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
                    (
                        self.shipper_mode,
                        self.row_dict_list,
                        self.shipper_line_number,
                        self.shipper_accum,
                    ) = self.leave_shipper_mode(
                        self.shipper_mode,
                        self.row_dict_list,
                        self.shipper_line_number,
                        self.shipper_accum,
                    )
                except Exception as error:
                    print(error)

        self.row_dict_list.append(row_dict)
        self.invoice_index += 1
        self.invoice_accum.append(row_dict["Extended Cost"])

    def process_record_c(self, record: dict) -> None:
        """Process C record - not implemented for this format"""
        pass

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
        self,
        rowlist: List[dict],
        invoice_total,
        shipper_line_number,
        shipper_accum,
        shipper_mode,
    ):
        """Flush all buffered data to CSV file"""
        shipper_mode, rowlist, shipper_line_number, shipper_accum = (
            self.leave_shipper_mode(
                shipper_mode, rowlist, shipper_line_number, shipper_accum
            )
        )
        for row in rowlist:
            self.add_row(row)

        if len(invoice_total) > 0:
            trailer_row = {"Record Type": "T", "Invoice Cost": sum(invoice_total)}
            self.add_row(trailer_row)

        rowlist.clear()
        invoice_total.clear()
        return (rowlist, shipper_mode, shipper_accum, shipper_line_number)


edi_convert = create_edi_convert_wrapper(EstoreEinvoiceConverter)
