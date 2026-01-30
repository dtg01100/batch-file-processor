from datetime import datetime, timedelta
from typing import Optional, BinaryIO

import utils
from convert_base import BaseConverter, create_edi_convert_wrapper


class ScannerWareConverter(BaseConverter):
    """Converter for ScannerWare format with fixed-width fields."""

    PLUGIN_ID = "scannerware"
    PLUGIN_NAME = "ScannerWare"
    PLUGIN_DESCRIPTION = (
        "ScannerWare fixed-width format with optional A record padding and date offset"
    )

    CONFIG_FIELDS = [
        {
            "key": "pad_a_records",
            "label": "Pad A Records",
            "type": "boolean",
            "default": False,
            "help": "Replace customer/vendor code with custom padding value",
        },
        {
            "key": "a_record_padding",
            "label": "A Record Padding Value",
            "type": "string",
            "default": "",
            "placeholder": "Enter padding value",
            "help": "Custom value to use for A record customer/vendor field",
        },
        {
            "key": "append_a_records",
            "label": "Append to A Records",
            "type": "boolean",
            "default": False,
            "help": "Append custom text to A records",
        },
        {
            "key": "a_record_append_text",
            "label": "A Record Append Text",
            "type": "string",
            "default": "",
            "placeholder": "Text to append",
            "help": "Text to append to the end of A records",
        },
        {
            "key": "force_txt_file_ext",
            "label": "Force .txt Extension",
            "type": "boolean",
            "default": False,
            "help": "Force output file to use .txt extension",
        },
        {
            "key": "invoice_date_offset",
            "label": "Invoice Date Offset (days)",
            "type": "integer",
            "default": 0,
            "min_value": -365,
            "max_value": 365,
            "help": "Number of days to add/subtract from invoice dates",
        },
    ]

    def __init__(
        self,
        edi_process: str,
        output_filename: str,
        settings_dict: dict,
        parameters_dict: dict,
        upc_lookup: dict,
    ) -> None:
        super().__init__(
            edi_process, output_filename, settings_dict, parameters_dict, upc_lookup
        )

        def to_bool(value):
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes")
            return bool(value)

        def to_int(value, default):
            if isinstance(value, int):
                return value
            if isinstance(value, str):
                try:
                    return int(value)
                except ValueError:
                    return default
            return default

        self.arec_padding = self.get_config_value("a_record_padding", "")
        self.pad_arec = to_bool(self.get_config_value("pad_a_records", False))
        self.append_arec = to_bool(self.get_config_value("append_a_records", False))
        self.append_arec_text = self.get_config_value("a_record_append_text", "")
        self.force_txt_ext = to_bool(self.get_config_value("force_txt_file_ext", False))
        self.invoice_date_offset = to_int(
            self.get_config_value("invoice_date_offset", 0), 0
        )
        self.output_file: Optional[BinaryIO] = None
        self._invoice_counter = 0

    def initialize_output(self) -> None:
        ext = ".txt" if self.force_txt_ext else ""
        self.output_file = open(self.output_filename + ext, "wb")

    def process_record_a(self, record: dict) -> None:
        self._invoice_counter += 1
        line_parts = []
        line_parts.append(record["record_type"])
        # Vendor field: use padding when configured, otherwise all zeros to match master
        if self.pad_arec:
            line_parts.append(self.arec_padding.ljust(6))
        else:
            line_parts.append("000000")
        # Use sequential invoice number (5 digits, zero-padded) + "01" suffix to match master
        line_parts.append(str(self._invoice_counter).zfill(5) + "01")
        line_parts.append("   ")

        write_invoice_date = record["invoice_date"]
        if self.invoice_date_offset != 0 and record["invoice_date"] != "000000":
            invoice_date = datetime.strptime(record["invoice_date"], "%m%d%y")
            offset_invoice_date = invoice_date + timedelta(
                days=self.invoice_date_offset
            )
            write_invoice_date = datetime.strftime(offset_invoice_date, "%m%d%y")

        line_parts.append(write_invoice_date)
        line_parts.append(record["invoice_total"])

        if self.append_arec:
            line_parts.append(self.append_arec_text)

        line = "".join(line_parts)
        self.output_file.write((line + "\r\n").encode())

    def process_record_b(self, record: dict) -> None:
        line_parts = []
        line_parts.append(record["record_type"])
        line_parts.append(record["upc_number"].ljust(14))
        line_parts.append(record["description"][:25])
        line_parts.append(record["vendor_item"])
        line_parts.append(record["unit_cost"])
        line_parts.append("  ")
        line_parts.append(record["unit_multiplier"])
        line_parts.append(record["qty_of_units"])
        line_parts.append(record["suggested_retail_price"])
        line_parts.append("001")
        line_parts.append("       ")

        line = "".join(line_parts)
        self.output_file.write((line + "\r\n").encode())

    def process_record_c(self, record: dict) -> None:
        line_parts = []
        line_parts.append(record["record_type"])
        line_parts.append(record["description"].ljust(25))
        line_parts.append("   ")
        line_parts.append(record["amount"])

        line = "".join(line_parts)
        self.output_file.write((line + "\r\n").encode())

    def finalize_output(self) -> str:
        if self.output_file is not None:
            self.output_file.close()
        ext = ".txt" if self.force_txt_ext else ""
        return self.output_filename + ext


edi_convert = create_edi_convert_wrapper(ScannerWareConverter)
