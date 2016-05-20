import upc_e_to_upc_a
import line_from_mtc_edi_to_dict


def edi_convert(edi_process, output_filename, calc_upc, inc_arec, inc_crec,
                inc_headers, filter_ampersand, pad_arec, arec_padding):
    # save input parameters as variables
    conv_calc_upc = calc_upc
    conv_inc_arec = inc_arec
    conv_inc_crec = inc_crec
    conv_inc_headers = inc_headers
    with open(edi_process) as work_file:  # open input file
        work_file_lined = [n for n in work_file.readlines()]  # make list of lines
        f = open(output_filename, 'wb')  # open work file, overwriting old file

        if conv_inc_headers != "False":  # include headers if flag is set
            # write line out to file
            f.write("{}" "," "{}" "," "{}" "," "{}" "," "{}" "," "{}" "," "{}\r\n"
                    .format("UPC", "Qty. Shipped", "Cost", "Suggested Retail",
                            "Description", "Case Pack", "Item Number").encode())

        for line_num, line in enumerate(work_file_lined):  # iterate over work file contents
            input_edi_dict = line_from_mtc_edi_to_dict.capture_records(line)

            # if include "A" records flag is set and line starts with "A"
            if line.startswith("A") and conv_inc_arec != "False":
                # write "A" line
                f.write((line[0:1] + arec_padding[0:6] + line[7:]).encode()) if pad_arec == "True" else f.write(
                    line.encode())

            # the following block writes "B" lines, dependent on filter and convert settings
            # ternary conditional operator: puts if-then-else statement in one line
            # syntax: <expression1> if <condition> else <expression2>
            # needs to be wrapped an parenthesis to separate statements

            if line.startswith("B"):
                blank_upc = False
                upc_string = ""
                try:
                    _ = int(input_edi_dict['upc_number'].rstrip())
                except ValueError:
                    blank_upc = True

                if blank_upc is False:
                    proposed_upc = input_edi_dict['upc_number']
                    if len(str(proposed_upc).rstrip()) == 11:
                        upc_string = str(proposed_upc) + str(upc_e_to_upc_a.calc_check_digit(proposed_upc))
                    else:
                        if len(str(proposed_upc).rstrip()) == 8:
                            upc_string = str(upc_e_to_upc_a.convert_UPCE_to_UPCA(proposed_upc.rstrip()))

                upc_in_csv = "\t" + upc_string if conv_calc_upc != "False" and blank_upc is False \
                    else input_edi_dict['upc_number']

                quantity_shipped_in_csv = input_edi_dict['qty_of_units'].lstrip("0") if not \
                    input_edi_dict['qty_of_units'].lstrip("0") == "" else input_edi_dict['qty_of_units']

                cost_in_csv = input_edi_dict['unit_cost'][:-2].lstrip("0") + "." + input_edi_dict['unit_cost'][-2:]

                suggested_retail_in_csv = input_edi_dict['suggested_retail_price'][:-2].lstrip("0") + "." + \
                    input_edi_dict['suggested_retail_price'][-2:]

                description_in_csv = (input_edi_dict['description'].replace("&", "AND").rstrip(" ")
                                      if filter_ampersand != "False" else
                                      input_edi_dict['description'].rstrip(" "))

                case_pack_in_csv = input_edi_dict['unit_multiplier'].lstrip("0") \
                    if not input_edi_dict['unit_multiplier'].lstrip("0") == "" else input_edi_dict['unit_multiplier']

                item_number_in_csv = input_edi_dict['vendor_item'].lstrip("0") \
                    if not input_edi_dict['vendor_item'].lstrip("0") == "" else input_edi_dict['vendor_item']

                f.write(
                    '"'"{}"'"'","'"'"{}"'"'","'"'"{}"'"'","'"'"{}"'"'","'"'"{}"'"'","'"'"{}"'"'","'"'"{}"'"'"\r\n".
                    format(upc_in_csv, quantity_shipped_in_csv, cost_in_csv, suggested_retail_in_csv,
                           description_in_csv, case_pack_in_csv, item_number_in_csv).encode())

            # if include "C" records flag is set and line starts with "C"
            if line.startswith("C") and conv_inc_crec != "False":
                f.write(line.encode())  # write "C" line

        f.close()  # close output file
