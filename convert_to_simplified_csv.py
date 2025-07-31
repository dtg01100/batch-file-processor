import csv
from decimal import Decimal
import os

import utils


class CustomerLookupError(Exception):
    pass


def convert_to_price(value):
    if isinstance(value, str):
        try:
            value = int(value)
        except ValueError:
            raise TypeError("Value must be a numeric string or an integer")

    value_str = str(abs(value)).zfill(3)  # Ensure at least 3 digits
    price = (
        (value_str[:-2].lstrip("0") if not value_str[:-2].lstrip("0") == "" else "0")
        + "."
        + value_str[-2:]
    )
    return f"-${price}" if value < 0 else f"${price}"


def add_row(rowdict, columnlayout, inc_item_desc, inc_item_numbers):
    column_list = []
    for column in columnlayout.split(","):
        if column in ["description", "vendor_item"]:
            if inc_item_desc and column == "description":
                column_list.append(rowdict.get(column, ""))
            if inc_item_numbers and column == "vendor_item":
                column_list.append(rowdict.get(column, ""))
        else:
            column_list.append(rowdict.get(column, ""))
    return column_list


def edi_convert(edi_process, output_filename, settings_dict, parameters_dict, upc_lookup):
    retail_uom = parameters_dict.get("retail_uom", "default_uom")
    inc_headers = parameters_dict.get("include_headers", False)
    inc_item_numbers = parameters_dict.get("include_item_numbers", False)
    inc_item_desc = parameters_dict.get("include_item_description", False)
    columnlayout = parameters_dict.get("simple_csv_sort_order", "")

    def add_row(rowdict):
        column_list = []
        for column in columnlayout.split(","):
            if column in ["description", "vendor_item"]:
                if inc_item_desc and column == "description":
                    column_list.append(rowdict.get(column, ""))
                if inc_item_numbers and column == "vendor_item":
                    column_list.append(rowdict.get(column, ""))
            else:
                column_list.append(rowdict.get(column, ""))
        csv_file.writerow(column_list)

    if isinstance(edi_process, (str, os.PathLike)) or hasattr(edi_process, "records"):
        if hasattr(edi_process, "records"):
            work_file_lined = edi_process.records
        else:
            with open(edi_process, encoding="utf-8") as work_file:
                work_file_lined = [n for n in work_file.readlines()]
    else:
        raise TypeError("edi_process must be a file path, PosixPath, or have a 'records' attribute")

    with open(str(output_filename) + ".csv", "w", newline="", encoding="utf-8") as f:
        csv_file = csv.writer(f, dialect="excel", lineterminator="\r\n")

        row_dict = dict(
            upc_number="UPC",
            qty_of_units="Quantity",
            unit_cost="Cost",
            description="Item Description",
            vendor_item="Item Number",
        )

        if inc_headers != "False":
            add_row(row_dict)

        def qty_to_int(qty):
            if qty.startswith("-"):
                wrkqty = int(qty[1:])
                wrkqtyint = wrkqty - (wrkqty * 2)
            else:
                try:
                    wrkqtyint = int(qty)
                except ValueError:
                    wrkqtyint = 0
            return wrkqtyint

        # Process each line in work_file_lined
        for line in work_file_lined:
            input_edi_dict = utils.capture_records(line)
            if input_edi_dict is not None:
                if input_edi_dict["record_type"] == "B":
                    if retail_uom:
                        edi_line_pass = False
                        item_number = None
                        try:
                            item_number = int(input_edi_dict["vendor_item"].strip())
                            float(input_edi_dict["unit_cost"].strip())
                            test_unit_multiplier = int(
                                input_edi_dict["unit_multiplier"].strip()
                            )
                            if test_unit_multiplier == 0:
                                raise ValueError
                            int(input_edi_dict["qty_of_units"].strip())
                            edi_line_pass = True
                        except Exception:
                            print("cannot parse b record field, skipping")
                        if edi_line_pass:
                            try:
                                each_upc_string = upc_lookup[item_number][1][:11].ljust(
                                    11
                                )
                            except KeyError:
                                each_upc_string = "           "
                            try:
                                input_edi_dict["unit_cost"] = (
                                    str(
                                        Decimal(
                                            (
                                                Decimal(
                                                    input_edi_dict["unit_cost"].strip()
                                                )
                                                / 100
                                            )
                                            / Decimal(
                                                input_edi_dict[
                                                    "unit_multiplier"
                                                ].strip()
                                            )
                                        ).quantize(Decimal(".01"))
                                    )
                                    .replace(".", "")[-6:]
                                    .rjust(6, "0")
                                )
                                input_edi_dict["qty_of_units"] = str(
                                    int(input_edi_dict["unit_multiplier"].strip())
                                    * int(input_edi_dict["qty_of_units"].strip())
                                ).rjust(5, "0")
                                input_edi_dict["upc_number"] = each_upc_string
                                input_edi_dict["unit_multiplier"] = "000001"
                            except Exception as error:
                                print(error)

                    try:
                        vendor_item_value = int(input_edi_dict["vendor_item"].strip())
                    except ValueError:
                        print(f"Skipping invalid vendor_item: {input_edi_dict['vendor_item']}")
                        continue

                    row_dict = dict(
                        upc_number=input_edi_dict["upc_number"],
                        qty_of_units=qty_to_int(input_edi_dict["qty_of_units"]),
                        unit_cost=convert_to_price(input_edi_dict["unit_cost"]),
                        description=input_edi_dict["description"],
                        vendor_item=vendor_item_value,
                    )

                    add_row(row_dict)

    return str(output_filename) + ".csv"
