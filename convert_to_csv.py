import csv
from decimal import Decimal

import line_from_mtc_edi_to_dict
import upc_e_to_upc_a

def edi_convert(edi_process, output_filename, settings_dict, parameters_dict, each_upc_lut):
    # save input parameters as variables

    calc_upc = parameters_dict['calculate_upc_check_digit']
    inc_arec = parameters_dict['include_a_records']
    inc_crec = parameters_dict['include_c_records']
    inc_headers  = parameters_dict['include_headers']
    filter_ampersand = parameters_dict['filter_ampersand']
    pad_arec = parameters_dict['pad_a_records']
    arec_padding = parameters_dict['a_record_padding']
    force_each_upc= parameters_dict['force_each_upc']
    retail_uom = parameters_dict['retail_uom']

    conv_calc_upc = calc_upc
    conv_inc_arec = inc_arec
    conv_inc_crec = inc_crec
    conv_inc_headers = inc_headers

    def convert_to_price(value):
        return (value[:-2].lstrip("0") if not value[:-2].lstrip("0") == "" else "0") + "." + value[-2:]

    with open(edi_process, encoding="utf-8") as work_file:  # open input file
        work_file_lined = [n for n in work_file.readlines()]  # make list of lines
        with open(output_filename + ".csv", "w", newline="", encoding="utf-8") as f:  # open work file, overwriting old file
            csv_file = csv.writer(f, dialect="excel", lineterminator="\r\n", quoting=csv.QUOTE_ALL)

            if conv_inc_headers != "False":  # include headers if flag is set
                # write line out to file
                csv_file.writerow(["UPC", "Qty. Shipped", "Cost", "Suggested Retail",
                                "Description", "Case Pack", "Item Number"])

            for line_num, line in enumerate(work_file_lined):  # iterate over work file contents
                input_edi_dict = line_from_mtc_edi_to_dict.capture_records(line)
                if input_edi_dict is not None:

                    # if include "A" records flag is set and line starts with "A"
                    if input_edi_dict['record_type'] == "A" and conv_inc_arec != "False":
                        # write "A" line
                        if pad_arec == "True":
                            cust_vendor = arec_padding
                        else:
                            cust_vendor = input_edi_dict['cust_vendor'] 
                        csv_file.writerow([input_edi_dict['record_type'], cust_vendor, input_edi_dict['invoice_number'], input_edi_dict['invoice_date'], input_edi_dict['invoice_total']])

                    # the following block writes "B" lines, dependent on filter and convert settings
                    # ternary conditional operator: puts if-then-else statement in one line
                    # syntax: <expression1> if <condition> else <expression2>
                    # needs to be wrapped an parenthesis to separate statements

                    if input_edi_dict['record_type'] == "B":
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
                        blank_upc = False
                        upc_string = ""
                        if force_each_upc:
                            try:
                                input_edi_dict['upc_number'] = each_upc_lut[int(input_edi_dict['vendor_item'].strip())]
                            except KeyError:
                                input_edi_dict['upc_number'] = ""
                        try:
                            _ = int(input_edi_dict['upc_number'].rstrip())
                        except ValueError:
                            blank_upc = True

                        if blank_upc is False:
                            proposed_upc = input_edi_dict['upc_number'].strip()
                            if len(str(proposed_upc)) == 12:
                                upc_string = str(proposed_upc)
                            if len(str(proposed_upc)) == 11:
                                upc_string = str(proposed_upc) + str(upc_e_to_upc_a.calc_check_digit(proposed_upc))
                            if len(str(proposed_upc)) == 8:
                                upc_string = str(upc_e_to_upc_a.convert_UPCE_to_UPCA(proposed_upc))

                        upc_in_csv = "\t" + upc_string if conv_calc_upc != "False" and blank_upc is False \
                            else input_edi_dict['upc_number']

                        quantity_shipped_in_csv = input_edi_dict['qty_of_units'].lstrip("0") \
                            if not input_edi_dict['qty_of_units'].lstrip("0") == "" else input_edi_dict['qty_of_units']

                        cost_in_csv = convert_to_price(input_edi_dict['unit_cost'])

                        suggested_retail_in_csv = convert_to_price(input_edi_dict['suggested_retail_price'])

                        description_in_csv = (input_edi_dict['description'].replace("&", "AND").rstrip(" ")
                                            if filter_ampersand != "False" else
                                            input_edi_dict['description'].rstrip(" "))

                        case_pack_in_csv = input_edi_dict['unit_multiplier'].lstrip("0") \
                            if not input_edi_dict['unit_multiplier'].lstrip("0") == "" else input_edi_dict['unit_multiplier']

                        item_number_in_csv = input_edi_dict['vendor_item'].lstrip("0") \
                            if not input_edi_dict['vendor_item'].lstrip("0") == "" else input_edi_dict['vendor_item']

                        csv_file.writerow([upc_in_csv, quantity_shipped_in_csv, cost_in_csv, suggested_retail_in_csv,
                                description_in_csv, case_pack_in_csv, item_number_in_csv])

                    # if include "C" records flag is set and line starts with "C"

                    if line.startswith("C") and conv_inc_crec != "False":
                        csv_file.writerow([input_edi_dict['record_type'], input_edi_dict['charge_type'], input_edi_dict['description'], input_edi_dict['amount']])
        return output_filename + ".csv"
