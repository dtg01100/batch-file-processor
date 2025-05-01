import csv
from decimal import Decimal

import utils


class CustomerLookupError(Exception):
    pass


def edi_convert(edi_process, output_filename, settings_dict, parameters_dict, upc_lookup):
    retail_uom = parameters_dict["retail_uom"]
    inc_headers = parameters_dict["include_headers"]
    inc_item_numbers = parameters_dict["include_item_numbers"]
    inc_item_desc = parameters_dict["include_item_description"]
    columnlayout = parameters_dict["simple_csv_sort_order"]

    def convert_to_price(value):
        return (
            (value[:-2].lstrip("0") if not value[:-2].lstrip("0") == "" else "0")
            + "."
            + value[-2:]
        )

    def add_row(rowdict):
        column_list = []
        for column in columnlayout.split(","):
            if column in ["description", "vendor_item"]:
                if inc_item_desc and column == "description":
                    column_list.append(rowdict[column])
                if inc_item_numbers and column == "vendor_item":
                    column_list.append(rowdict[column])
            else:
                column_list.append(rowdict[column])
        csv_file.writerow(column_list)

    with open(edi_process, encoding="utf-8") as work_file:  # open input file
        work_file_lined = [n for n in work_file.readlines()]  # make list of lines
        with open(
            output_filename + ".csv", "w", newline="", encoding="utf-8"
        ) as f:  # open work file, overwriting old file
            csv_file = csv.writer(f, dialect="excel", lineterminator="\r\n")
            "upc_number,qty_of_units,unit_cost,description,vendor_item"

            row_dict = dict(
                upc_number="UPC",
                qty_of_units="Quantity",
                unit_cost="Cost",
                description="Item Description",
                vendor_item="Item Number",
            )

            if inc_headers != "False":  # include headers if flag is set
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

            for line_num, line in enumerate(
                work_file_lined
            ):  # iterate over work file contents
                input_edi_dict = utils.capture_records(line)
                if input_edi_dict is not None:
                    if input_edi_dict["record_type"] == "B":
                        if retail_uom:
                            edi_line_pass = False
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

                        row_dict = dict(
                            upc_number=input_edi_dict["upc_number"],
                            qty_of_units=qty_to_int(input_edi_dict["qty_of_units"]),
                            unit_cost=convert_to_price(input_edi_dict["unit_cost"]),
                            description=input_edi_dict["description"],
                            vendor_item=int(input_edi_dict["vendor_item"].strip()),
                        )

                        add_row(row_dict)

    return output_filename + ".csv"
