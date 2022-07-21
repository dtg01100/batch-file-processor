import line_from_mtc_edi_to_dict
import csv
import upc_e_to_upc_a
from decimal import Decimal


class CustomerLookupError(Exception):
    pass

def edi_convert(edi_process, output_filename, each_upc_lut, parameters_dict):
    retail_uom = parameters_dict['retail_uom']
    inc_headers  = parameters_dict['include_headers']

    def convert_to_price(value):
        return (
            (value[:-2].lstrip("0") if not value[:-2].lstrip("0") == "" else "0")
            + "."
            + value[-2:]
        )

    with open(edi_process) as work_file:  # open input file
        work_file_lined = [n for n in work_file.readlines()]  # make list of lines
        f = open(
            output_filename, "w", newline=""
        )  # open work file, overwriting old file
        csv_file = csv.writer(f, dialect="excel", lineterminator="\r\n")

        if inc_headers != "False":  # include headers if flag is set
            csv_file.writerow(["UPC", "Quantity", "Cost"])

        def qty_to_int(qty):
            if qty.startswith('-'):
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
            input_edi_dict = line_from_mtc_edi_to_dict.capture_records(line)
            if input_edi_dict is not None:
                if input_edi_dict['record_type'] == 'B':
                    if retail_uom:
                        edi_line_pass = False
                        try:
                            item_number = int(input_edi_dict['vendor_item'].strip())
                            float(input_edi_dict['unit_cost'].strip())
                            test_unit_multiplier = int(input_edi_dict['unit_multiplier'].strip())
                            if test_unit_multiplier == 0:
                                raise ValueError
                            int(input_edi_dict['qty_of_units'].strip())
                            edi_line_pass = True
                        except Exception:
                            print("cannot parse b record field, skipping")
                        if edi_line_pass:
                            try:
                                each_upc_string = each_upc_lut[item_number][:11].ljust(11)
                            except KeyError:
                                each_upc_string = "           "
                            try:
                                input_edi_dict["unit_cost"] = str(Decimal((Decimal(input_edi_dict['unit_cost'].strip()) / 100) / Decimal(input_edi_dict['unit_multiplier'].strip())).quantize(Decimal('.01'))).replace(".", "")[-6:].rjust(6,'0')
                                input_edi_dict['qty_of_units'] = str(int(input_edi_dict['unit_multiplier'].strip()) * int(input_edi_dict['qty_of_units'].strip())).rjust(5,'0')
                                input_edi_dict['upc_number'] = each_upc_string
                                input_edi_dict['unit_multiplier'] = '000001'
                            except Exception as error:
                                print(error)

                    csv_file.writerow([
                        input_edi_dict['upc_number'],
                        qty_to_int(input_edi_dict['qty_of_units']),
                        convert_to_price(input_edi_dict['unit_cost'])
                    ])
        f.close()  # close output file
    return(output_filename)
