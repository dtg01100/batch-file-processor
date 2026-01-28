import csv
from decimal import Decimal

import utils
from convert_base import CSVConverter, create_edi_convert_wrapper


class SimplifiedCsvConverter(CSVConverter):
    """Converter for simplified CSV output format with dynamic column layout."""

    PLUGIN_ID = "simplified_csv"
    PLUGIN_NAME = "Simplified CSV"
    PLUGIN_DESCRIPTION = "Simplified CSV with configurable columns (UPC, quantity, cost, description, item number)"

    CONFIG_FIELDS = [
        {
            "key": "include_headers",
            "label": "Include Headers",
            "type": "boolean",
            "default": False,
            "help": "Include column headers in the CSV output",
        },
        {
            "key": "include_item_numbers",
            "label": "Include Item Numbers",
            "type": "boolean",
            "default": False,
            "help": "Include item numbers column in output",
        },
        {
            "key": "include_item_description",
            "label": "Include Item Description",
            "type": "boolean",
            "default": False,
            "help": "Include description column in output",
        },
        {
            "key": "retail_uom",
            "label": "Transform to Retail UOM",
            "type": "boolean",
            "default": False,
            "help": "Convert case-level data to each-level retail UOM",
        },
        {
            "key": "simple_csv_sort_order",
            "label": "Column Order",
            "type": "string",
            "default": "upc_number,qty_of_units,unit_cost,description,vendor_item",
            "placeholder": "comma-separated column names",
            "help": "Comma-separated list of columns in desired order",
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
        self.retail_uom = self.get_config_value("retail_uom", False)
        self.inc_headers = self.get_config_value("include_headers", False)
        self.inc_item_numbers = self.get_config_value("include_item_numbers", False)
        self.inc_item_desc = self.get_config_value("include_item_description", False)
        self.column_layout = self.get_config_value(
            "simple_csv_sort_order",
            "upc_number,qty_of_units,unit_cost,description,vendor_item",
        )

    def initialize_output(self) -> None:
        self.quoting = csv.QUOTE_MINIMAL
        super().initialize_output()

        if self.inc_headers:
            headers = self._build_row(
                {
                    "upc_number": "UPC",
                    "qty_of_units": "Quantity",
                    "unit_cost": "Cost",
                    "description": "Item Description",
                    "vendor_item": "Item Number",
                }
            )
            self.write_row(headers)

    def _build_row(self, row_dict: dict) -> list:
        column_list = []
        for column in self.column_layout.split(","):
            if column in ["description", "vendor_item"]:
                if self.inc_item_desc and column == "description":
                    column_list.append(row_dict[column])
                if self.inc_item_numbers and column == "vendor_item":
                    column_list.append(row_dict[column])
            else:
                column_list.append(row_dict[column])
        return column_list

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

    def process_record_a(self, record: dict) -> None:
        pass

    def process_record_b(self, record: dict) -> None:
        if self.retail_uom:
            if not self._apply_retail_uom(record):
                return

        try:
            vendor_item_int = int(record["vendor_item"].strip())
        except ValueError:
            print("cannot parse vendor_item as int")
            vendor_item_int = 0

        row_dict = {
            "upc_number": record["upc_number"],
            "qty_of_units": self.qty_to_int(record["qty_of_units"]),
            "unit_cost": self.convert_to_price(record["unit_cost"]),
            "description": record["description"],
            "vendor_item": vendor_item_int,
        }

        self.write_row(self._build_row(row_dict))

    def process_record_c(self, record: dict) -> None:
        pass

    def process_record_b(self, record: dict) -> None:
        """Process a B record (line item).

        Args:
            record: Dictionary containing parsed B record fields.
        """
        # Apply retail UOM transformation if enabled
        if self.retail_uom:
            if not self._apply_retail_uom(record):
                return

        # Build row dictionary
        try:
            vendor_item_int = int(record["vendor_item"].strip())
        except ValueError:
            print("cannot parse vendor_item as int")
            vendor_item_int = 0

        row_dict = {
            "upc_number": record["upc_number"],
            "qty_of_units": self.qty_to_int(record["qty_of_units"]),
            "unit_cost": self.convert_to_price(record["unit_cost"]),
            "description": record["description"],
            "vendor_item": vendor_item_int,
        }

        self.write_row(self._build_row(row_dict))

    def process_record_c(self, record: dict) -> None:
        """Process a C record (charge/adjustment).

        Args:
            record: Dictionary containing parsed C record fields.
        """
        # Simplified CSV does not include C records
        pass


# Backward-compatible wrapper function
edi_convert = create_edi_convert_wrapper(SimplifiedCsvConverter)
