"""EDI Tweaks converter plugin.

This module provides transformations for EDI files including:
- Date offsets and custom formatting for invoice dates
- A record padding and PO appending
- UPC override from lookup tables
- Retail UOM transformation (case to each)
- UPC check digit calculation
- Sales tax splitting for prepaid/non-prepaid amounts
"""

import time
from datetime import datetime, timedelta

import utils
from convert_base import BaseConverter
from plugin_config import PluginConfigMixin
from query_runner import query_runner


class EDITweaksConverter(BaseConverter, PluginConfigMixin):
    """Converter for applying EDI transformations.

    This converter reads EDI files and applies various transformations
    based on configuration settings, outputting modified EDI files.

    Transformations include:
    - Invoice date offsetting and custom formatting
    - A record padding and text appending
    - UPC override from lookup tables
    - Retail UOM transformation (case to each)
    - UPC check digit calculation
    - Sales tax splitting into prepaid/non-prepaid

    Attributes:
        output_file: File handle for the output EDI file.
        crec_appender: cRecGenerator instance for sales tax splitting.
        po_fetcher: invFetcher instance for PO number lookup.
        output_lines: List of lines to write to output file.
    """

    PLUGIN_ID = "edi_tweaks"
    PLUGIN_NAME = "EDI Tweaks"
    PLUGIN_DESCRIPTION = "Apply transformations to EDI files (date offsets, UPC calculations, padding, etc.)"

    CONFIG_FIELDS = [
        {"key": "pad_a_records", "label": "Pad A Records", "type": "boolean", "default": False},
        {"key": "a_record_padding", "label": "A Record Padding Value", "type": "string", "default": ""},
        {"key": "a_record_padding_length", "label": "A Record Padding Length", "type": "integer", "default": 6},
        {"key": "append_a_records", "label": "Append to A Records", "type": "boolean", "default": False},
        {"key": "a_record_append_text", "label": "A Record Append Text", "type": "string", "default": ""},
        {"key": "invoice_date_offset", "label": "Invoice Date Offset (Days)", "type": "integer", "default": 0},
        {"key": "invoice_date_custom_format", "label": "Custom Date Format", "type": "boolean", "default": False},
        {"key": "invoice_date_custom_format_string", "label": "Date Format String", "type": "string", "default": "%Y-%m-%d"},
        {"key": "calculate_upc_check_digit", "label": "Calculate UPC Check Digit", "type": "boolean", "default": False},
        {"key": "retail_uom", "label": "Transform to Retail UOM", "type": "boolean", "default": False},
        {"key": "override_upc_bool", "label": "Override UPC from Lookup", "type": "boolean", "default": False},
        {"key": "override_upc_level", "label": "UPC Lookup Level", "type": "integer", "default": 1},
        {"key": "override_upc_category_filter", "label": "UPC Category Filter", "type": "string", "default": "ALL"},
        {"key": "split_prepaid_sales_tax_crec", "label": "Split Prepaid Sales Tax", "type": "boolean", "default": False},
        {"key": "force_txt_file_ext", "label": "Force .txt Extension", "type": "boolean", "default": False},
    ]

    def __init__(
        self,
        edi_process: str,
        output_filename: str,
        settings_dict: dict,
        parameters_dict: dict,
        upc_lookup: dict,
    ) -> None:
        """Initialize the EDI Tweaks converter.

        Args:
            edi_process: Path to the input EDI file.
            output_filename: Base path for the output file.
            settings_dict: Dictionary containing application settings.
            parameters_dict: Dictionary containing conversion parameters.
            upc_lookup: Dictionary for UPC code lookups.
        """
        super().__init__(
            edi_process, output_filename, settings_dict, parameters_dict, upc_lookup
        )
        self._init_config()
        self.output_file = None
        self.crec_appender = None
        self.po_fetcher = None
        self.output_lines: list[str] = []

    def _init_config(self) -> None:
        """Parse all config values from parameters_dict with proper type conversion."""
        # Boolean configs - need to handle string "True"/"False" for backward compatibility
        self.pad_arec = self._get_bool_config("pad_a_records", False)
        self.append_arec = self._get_bool_config("append_a_records", False)
        self.invoice_date_custom_format = self._get_bool_config("invoice_date_custom_format", False)
        self.calc_upc = self._get_bool_config("calculate_upc_check_digit", False)
        self.retail_uom = self._get_bool_config("retail_uom", False)
        self.override_upc = self._get_bool_config("override_upc_bool", False)
        self.split_prepaid_sales_tax_crec = self._get_bool_config("split_prepaid_sales_tax_crec", False)
        self.force_txt_file_ext = self._get_bool_config("force_txt_file_ext", False)

        # String configs
        self.arec_padding = str(self.get_config_value("a_record_padding", ""))
        self.append_arec_text = str(self.get_config_value("a_record_append_text", ""))
        self.invoice_date_custom_format_string = str(self.get_config_value("invoice_date_custom_format_string", "%Y-%m-%d"))
        self.override_upc_category_filter = str(self.get_config_value("override_upc_category_filter", "ALL"))

        # Integer configs - parse from string or int
        self.arec_padding_len = self._get_int_config("a_record_padding_length", 6)
        self.invoice_date_offset = self._get_int_config("invoice_date_offset", 0)
        self.override_upc_level = self._get_int_config("override_upc_level", 1)

    def _get_bool_config(self, key: str, default: bool) -> bool:
        """Get a boolean config value, handling string representations."""
        value = self.get_config_value(key, default)
        if isinstance(value, str):
            return value.lower() == "true"
        return bool(value)

    def _get_int_config(self, key: str, default: int) -> int:
        """Get an integer config value."""
        value = self.parameters_dict.get(key, default)
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def initialize_output(self) -> None:
        """Initialize the output collection and database helpers.

        Sets up the cRecGenerator for sales tax splitting and
        invFetcher for PO number lookups.
        """
        # Initialize output lines collection
        self.output_lines = []

        # Initialize database helpers
        self.crec_appender = utils.cRecGenerator(self.settings_dict)
        self.po_fetcher = utils.invFetcher(self.settings_dict)

    def write_line(self, line: str) -> None:
        """Write a line to the output collection.

        Args:
            line: The line to write (should include newline if needed).
        """
        self.output_lines.append(line)

    def process_record_a(self, record: dict) -> None:
        """Process an A record (invoice header).

        Applies transformations including:
        - Invoice date offset
        - Custom date formatting
        - A record padding
        - PO text appending (with %po_str% placeholder)

        Args:
            record: Dictionary containing parsed A record fields.
        """
        # Set invoice number for sales tax splitting
        if self.split_prepaid_sales_tax_crec and self.crec_appender:
            try:
                self.crec_appender.set_invoice_number(int(record["invoice_number"]))
            except (ValueError, TypeError):
                pass  # Skip if invoice number is not numeric

        # Apply invoice date offset
        if self.invoice_date_offset != 0:
            invoice_date_string = record["invoice_date"]
            if invoice_date_string != "000000":
                try:
                    invoice_date = datetime.strptime(invoice_date_string, "%m%d%y")
                    offset_invoice_date = invoice_date + timedelta(
                        days=self.invoice_date_offset
                    )
                    record["invoice_date"] = datetime.strftime(offset_invoice_date, "%m%d%y")
                except ValueError:
                    pass  # Keep original date if parsing fails

        # Apply custom date formatting
        if self.invoice_date_custom_format:
            invoice_date_string = record["invoice_date"]
            try:
                invoice_date = datetime.strptime(invoice_date_string, "%m%d%y")
                record["invoice_date"] = datetime.strftime(
                    invoice_date, self.invoice_date_custom_format_string
                )
            except ValueError:
                record["invoice_date"] = "ERROR"

        # Apply A record padding
        if self.pad_arec:
            padding = self.arec_padding
            fill = " "
            align = "<"
            width = self.arec_padding_len
            record["cust_vendor"] = f"{padding:{fill}{align}{width}}"

        # Build A record line
        a_rec_line_builder = [
            record["record_type"],
            record["cust_vendor"],
            record["invoice_number"],
            record["invoice_date"],
            record["invoice_total"],
        ]

        # Apply text appending with PO placeholder
        if self.append_arec:
            append_text = self.append_arec_text
            if "%po_str%" in append_text:
                try:
                    invoice_num = int(record["invoice_number"])
                    po_number = self.po_fetcher.fetch_po_number_only(invoice_num)
                except (ValueError, TypeError):
                    po_number = "no_po_found    "
                append_text = append_text.replace("%po_str%", po_number)
            a_rec_line_builder.append(append_text)

        a_rec_line_builder.append("\n")
        writeable_line = "".join(a_rec_line_builder)
        self.write_line(writeable_line)

    def process_record_b(self, record: dict) -> None:
        """Process a B record (line item).

        Applies transformations including:
        - UPC override from lookup
        - Retail UOM transformation
        - UPC check digit calculation
        - Negative amount handling

        Args:
            record: Dictionary containing parsed B record fields.
        """
        # Apply UPC override
        if self.override_upc:
            utils.apply_upc_override(
                record,
                self.upc_lookup,
                override_level=self.override_upc_level,
                category_filter=self.override_upc_category_filter,
            )

        # Apply retail UOM transformation
        if self.retail_uom:
            utils.apply_retail_uom_transform(record, self.upc_lookup)

        # Apply UPC check digit calculation
        if self.calc_upc:
            blank_upc = False
            try:
                _ = int(record["upc_number"].rstrip())
            except ValueError:
                blank_upc = True

            if blank_upc is False:
                proposed_upc = record["upc_number"].strip()
                if len(str(proposed_upc)) == 11:
                    record["upc_number"] = str(proposed_upc) + str(
                        utils.calc_check_digit(proposed_upc)
                    )
                elif len(str(proposed_upc)) == 8:
                    record["upc_number"] = str(
                        utils.convert_UPCE_to_UPCA(proposed_upc)
                    )
            else:
                record["upc_number"] = "            "

        # Handle missing parent_item_number for short B records
        # B records should be 76 chars without newline; if parsed record has shorter line, clear parent_item_number
        if len(record.get("parent_item_number", "")) < 6:
            record["parent_item_number"] = ""

        # Handle negative amounts in numeric fields
        digits_fields = [
            "unit_cost",
            "unit_multiplier",
            "qty_of_units",
            "suggested_retail_price",
        ]

        for field in digits_fields:
            tempfield = record[field].replace("-", "")
            if len(tempfield) != len(record[field]):
                record[field] = "-" + tempfield

        # Build and write B record line
        writeable_line = "".join(
            (
                record["record_type"],
                record["upc_number"],
                record["description"],
                record["vendor_item"],
                record["unit_cost"],
                record["combo_code"],
                record["unit_multiplier"],
                record["qty_of_units"],
                record["suggested_retail_price"],
                record["price_multi_pack"],
                record["parent_item_number"],
            )
        )
        # Handle short input lines: strip any embedded newlines and ensure
        # the line ends with a single newline
        writeable_line = writeable_line.replace("\n", "").replace("\r", "")
        # For short records (less than 76 chars), add a blank line after
        # to match original edi_tweak behavior
        if len(writeable_line) < 76:
            writeable_line = writeable_line + "\n\n"
        else:
            writeable_line = writeable_line + "\n"
        self.write_line(writeable_line)

    def process_record_c(self, record: dict) -> None:
        """Process a C record (charge/adjustment).

        Handles sales tax splitting by checking if this is a sales tax
        record and if we need to split it into prepaid/non-prepaid amounts.

        Args:
            record: Dictionary containing parsed C record fields.
        """
        # Check if we need to split sales tax for this invoice
        if (
            self.split_prepaid_sales_tax_crec
            and self.crec_appender
            and self.crec_appender.unappended_records
        ):
            # Check if this is the Sales Tax record we want to split
            if (record.get("charge_type") == "TAB"
                and record.get("description", "").strip() == "Sales Tax"):
                # Write split sales tax records instead of original
                self.crec_appender.fetch_splitted_sales_tax_totals(self.write_line)
                return

        # Write the original C record
        # Use the original line from the input file (stripped of trailing newline)
        # to preserve exact formatting
        writeable_line = "".join(
            (
                record["record_type"],
                record["charge_type"],
                record["description"],
                record["amount"],
            )
        ).rstrip("\n\r") + "\n"
        self.write_line(writeable_line)

    def finalize_output(self) -> str:
        """Finalize the output and write the EDI file.

        Writes all collected lines to the output file with proper retry logic
        and CRLF line endings.

        Returns:
            The path to the generated output file.
        """
        # Determine output filename
        output_path = self.output_filename
        if self.force_txt_file_ext:
            output_path = output_path + ".txt"

        # Write output file with retry logic
        f = None
        write_attempt_counter = 1
        while f is None:
            try:
                f = open(output_path, "w", newline="\r\n")
            except Exception as error:
                if write_attempt_counter >= 5:
                    time.sleep(write_attempt_counter * write_attempt_counter)
                    write_attempt_counter += 1
                    print(f"retrying open {output_path}")
                else:
                    print(f"error opening file for write {error}")
                    raise

        try:
            for line in self.output_lines:
                f.write(line)
        finally:
            f.close()

        return output_path


def edi_tweak(
    edi_process,
    output_filename,
    settings_dict,
    parameters_dict,
    upc_dict,
):
    """Apply EDI tweaks transformations (backward-compatible wrapper).

    This function maintains backward compatibility with the original
    edi_tweak() function signature. It creates an EDITweaksConverter
    instance and runs the conversion.

    Args:
        edi_process: Path to the input EDI file.
        output_filename: Path for the output file.
        settings_dict: Dictionary containing application settings.
        parameters_dict: Dictionary containing tweak parameters.
        upc_dict: Dictionary for UPC code lookups.

    Returns:
        The path to the generated output file.
    """
    converter = EDITweaksConverter(
        edi_process, output_filename, settings_dict, parameters_dict, upc_dict
    )
    return converter.convert()
