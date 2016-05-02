import upc_e_to_upc_a


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
                            "Description", "Case Pack", "Item Number"))

        for line_num, line in enumerate(work_file_lined):  # iterate over work file contents

            # if include "A" records flag is set and line starts with "A"
            if line.startswith("A") and conv_inc_arec != "False":
                # write "A" line
                f.write(line[0:1] + arec_padding[0:6] + line[7:]) if pad_arec == "True" else f.write(line)

            # the following block writes "B" lines, dependent on filter and convert settings
            # ternary conditional operator: puts if-then-else statement in one line
            # syntax: <expression1> if <condition> else <expression2>
            # needs to be wrapped an parenthesis to separate statements

            if line.startswith("B"):
                blank_upc = False
                upc_string = ""
                try:
                    _ = int(line[1:12].rstrip())
                except ValueError:
                    blank_upc = True

                if blank_upc is False:
                    proposed_upc = line[1:12]
                    if len(str(proposed_upc).rstrip()) == 11:
                        upc_string = str(proposed_upc) + str(upc_e_to_upc_a.calc_check_digit(proposed_upc))
                    else:
                        if len(str(proposed_upc).rstrip()) == 8:
                            upc_string = str(upc_e_to_upc_a.convert_UPCE_to_UPCA(proposed_upc.rstrip()))

                f.write(
                    '"'"{}"'"'","'"'"{}"'"'","'"'"{}"'"'","'"'"{}"'"'","'"'"{}"'"'","'"'"{}"'"'","'"'"{}"'"'"\r\n".
                    format(("\t" + upc_string if conv_calc_upc != "False" and blank_upc is False
                            else line[1:12]),
                           line[59:62].lstrip("0") if not line[59:62].lstrip("0") == "" else line[61],
                           line[45:47].lstrip("0") + "." + line[47:49] if not line[45:47] == "00" else "{0}.{1}"
                           .format(line[46:47], line[47:49]),
                           line[63:65].lstrip("0") + "." + line[65:68] if not line[63:65] == "00" else "{0}.{1}"
                           .format(line[64:65], line[65:68]),
                           (line.replace("&", "AND")[12:37].rstrip(" ") if filter_ampersand != "False" else
                            line[12:37].rstrip(" ")),
                           line[53:57].lstrip("0") if not line[53:57].lstrip("0") == "" else line[57],
                           line[37:43].lstrip("0") if not line[37:43].lstrip("0") == "" else line[38:43]))

            # if include "C" records flag is set and line starts with "C"
            if line.startswith("C") and conv_inc_crec != "False":
                f.write(line)  # write "C" line

        f.close()  # close output file
