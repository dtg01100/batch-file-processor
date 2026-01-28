import csv
from decimal import Decimal

import utils
from convert_base import CSVConverter, create_edi_convert_wrapper


class CsvConverter(CSVConverter):
    """Converter for standard CSV output format.

    This converter produces a 7-column CSV file with the following columns:
    - UPC
    - Qty. Shipped
    - Cost
    - Suggested Retail
    - Description
    - Case Pack
    - Item Number

    The converter supports various options including conditional A/C record
    inclusion, UPC override from lookup tables, and retail UOM transformation.
    """

    PLUGIN_ID = "csv"
    PLUGIN_NAME = "Standard CSV"
    PLUGIN_DESCRIPTION = "Basic CSV format with UPC, quantity, cost, retail, description, case pack, and item number"

    CONFIG_FIELDS = [
        {
            "key": "include_headers",
            "label": "Include Headers",
            "type": "boolean",
            "default": False,
            "help": "Include column headers in the CSV output",
        },
        {
            "key": "calculate_upc_check_digit",
            "label": "Calculate UPC Check Digit",
            "type": "boolean",
            "default": False,
            "help": "Calculate and append check digit for 11-digit UPCs",
        },
        {
            "key": "include_a_records",
            "label": "Include A Records",
            "type": "boolean",
            "default": False,
            "help": "Include invoice header records in output",
        },
        {
            "key": "include_c_records",
            "label": "Include C Records",
            "type": "boolean",
            "default": False,
            "help": "Include charge/adjustment records in output",
        },
        {
            "key": "filter_ampersand",
            "label": "Replace & with AND",
            "type": "boolean",
            "default": False,
            "help": "Replace ampersand (&) with AND in descriptions",
        },
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
            "key": "override_upc_bool",
            "label": "Override UPC from Lookup",
            "type": "boolean",
            "default": False,
            "help": "Override UPC values from database lookup table",
        },
        {
            "key": "override_upc_level",
            "label": "UPC Lookup Level",
            "type": "integer",
            "default": 1,
            "min_value": 1,
            "max_value": 4,
            "help": "Which UPC level to use from lookup table (1-4)",
        },
        {
            "key": "override_upc_category_filter",
            "label": "UPC Category Filter",
            "type": "string",
            "default": "ALL",
            "placeholder": "ALL or comma-separated categories",
            "help": "Filter UPC override by category (ALL or comma-separated list)",
        },
        {
            "key": "retail_uom",
            "label": "Transform to Retail UOM",
            "type": "boolean",
            "default": False,
            "help": "Convert case-level data to each-level retail UOM",
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

        self.calc_upc = to_bool(
            self.get_config_value("calculate_upc_check_digit", False)
        )
        self.inc_arec = to_bool(self.get_config_value("include_a_records", False))
        self.inc_crec = to_bool(self.get_config_value("include_c_records", False))
        self.inc_headers = to_bool(self.get_config_value("include_headers", False))
        self.filter_ampersand = to_bool(
            self.get_config_value("filter_ampersand", False)
        )
        self.pad_arec = to_bool(self.get_config_value("pad_a_records", False))
        self.arec_padding = self.get_config_value("a_record_padding", "")
        self.override_upc = to_bool(self.get_config_value("override_upc_bool", False))
        self.override_upc_level = to_int(
            self.get_config_value("override_upc_level", 1), 1
        )
        self.override_upc_category_filter = self.get_config_value(
            "override_upc_category_filter", "ALL"
        )
        self.retail_uom = to_bool(self.get_config_value("retail_uom", False))

    def initialize_output(self) -> None:
        super().initialize_output()
        if self.inc_headers:
            self.write_header(
                [
                    "UPC",
                    "Qty. Shipped",
                    "Cost",
                    "Suggested Retail",
                    "Description",
                    "Case Pack",
                    "Item Number",
                ]
            )

    def _apply_retail_uom(self, record: dict) -> bool:
        """Apply retail UOM transformation to a B record.

        Args:
            record: The B record dictionary to transform in place.

        Returns:
            True if transformation was successful, False otherwise.
        """
        try:
            item_number = int(record["vendor_item"].strip())
            float(record["unit_cost"].strip())
            test_unit_multiplier = int(record["unit_multiplier"].strip())
            if test_unit_multiplier == 0:
                raise ValueError
            int(record["qty_of_units"].strip())
        except Exception:
            print("cannot parse b record field, skipping")
            return False

        try:
            each_upc_string = self.upc_lookup[item_number][1][:11].ljust(11)
        except KeyError:
            each_upc_string = "           "

        try:
            record["unit_cost"] = (
                str(
                    Decimal(
                        (Decimal(record["unit_cost"].strip()) / 100)
                        / Decimal(record["unit_multiplier"].strip())
                    ).quantize(Decimal(".01"))
                )
                .replace(".", "")[-6:]
                .rjust(6, "0")
            )
            record["qty_of_units"] = str(
                int(record["unit_multiplier"].strip())
                * int(record["qty_of_units"].strip())
            ).rjust(5, "0")
            record["upc_number"] = each_upc_string
            record["unit_multiplier"] = "000001"
            return True
        except Exception as error:
            print(error)
            return False

    def _apply_upc_override(self, record: dict) -> None:
        """Apply UPC override from lookup table if configured.

        Args:
            record: The B record dictionary to modify in place.
        """
        try:
            vendor_item_int = int(record["vendor_item"].strip())
            if vendor_item_int in self.upc_lookup:
                do_updateupc = False
                if self.override_upc_category_filter == "ALL":
                    do_updateupc = True
                else:
                    if self.upc_lookup[vendor_item_int][
                        0
                    ] in self.override_upc_category_filter.split(","):
                        do_updateupc = True
                if do_updateupc:
                    record["upc_number"] = self.upc_lookup[vendor_item_int][
                        self.override_upc_level
                    ]
            else:
                record["upc_number"] = ""
        except (KeyError, ValueError):
            record["upc_number"] = ""

    def _process_upc_for_csv(self, upc_string: str) -> tuple[str, bool]:
        """Process UPC string for CSV output.

        Args:
            upc_string: The raw UPC string from the record.

        Returns:
            Tuple of (processed_upc, is_blank).
        """
        blank_upc = False
        result_upc = ""

        try:
            _ = int(upc_string.rstrip())
        except ValueError:
            blank_upc = True

        if not blank_upc:
            proposed_upc = upc_string.strip()
            if len(str(proposed_upc)) == 12:
                result_upc = str(proposed_upc)
            elif len(str(proposed_upc)) == 11:
                result_upc = str(proposed_upc) + str(
                    utils.calc_check_digit(proposed_upc)
                )
            elif len(str(proposed_upc)) == 8:
                result_upc = str(utils.convert_UPCE_to_UPCA(proposed_upc))

        return result_upc, blank_upc

    def process_record_a(self, record: dict) -> None:
        if not self.inc_arec:
            return

        if self.pad_arec:
            cust_vendor = self.arec_padding
        else:
            cust_vendor = record["cust_vendor"]

        self.write_row(
            [
                record["record_type"],
                cust_vendor,
                record["invoice_number"],
                record["invoice_date"],
                record["invoice_total"],
            ]
        )

    def process_record_b(self, record: dict) -> None:
        if self.retail_uom:
            if not self._apply_retail_uom(record):
                return

        if self.override_upc:
            self._apply_upc_override(record)

        upc_string, blank_upc = self._process_upc_for_csv(record["upc_number"])

        if self.calc_upc and not blank_upc:
            upc_in_csv = "\t" + upc_string
        else:
            upc_in_csv = record["upc_number"]

        quantity_shipped_in_csv = record["qty_of_units"].lstrip("0")
        if quantity_shipped_in_csv == "":
            quantity_shipped_in_csv = record["qty_of_units"]

        cost_in_csv = self.convert_to_price(record["unit_cost"])
        suggested_retail_in_csv = self.convert_to_price(
            record["suggested_retail_price"]
        )

        if self.filter_ampersand:
            description_in_csv = record["description"].replace("&", "AND").rstrip(" ")
        else:
            description_in_csv = record["description"].rstrip(" ")

        case_pack_in_csv = record["unit_multiplier"].lstrip("0")
        if case_pack_in_csv == "":
            case_pack_in_csv = record["unit_multiplier"]

        item_number_in_csv = record["vendor_item"].lstrip("0")
        if item_number_in_csv == "":
            item_number_in_csv = record["vendor_item"]

        self.write_row(
            [
                upc_in_csv,
                quantity_shipped_in_csv,
                cost_in_csv,
                suggested_retail_in_csv,
                description_in_csv,
                case_pack_in_csv,
                item_number_in_csv,
            ]
        )

    def process_record_c(self, record: dict) -> None:
        if not self.inc_crec:
            return

        self.write_row(
            [
                record["record_type"],
                record["charge_type"],
                record["description"],
                record["amount"],
            ]
        )


# Backward-compatible wrapper function
edi_convert = create_edi_convert_wrapper(CsvConverter)
