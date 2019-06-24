import upc_e_to_upc_a
import line_from_mtc_edi_to_dict

def edi_tweak(edi_process, output_filename, pad_arec, arec_padding, append_arec, append_arec_text, force_txt_file_ext, calc_upc):
    work_file = open(edi_process)  # open input file
    work_file_lined = [n for n in work_file.readlines()]  # make list of lines
    if force_txt_file_ext == "True":
        output_filename = output_filename + ".txt"
    f = open(output_filename, 'wb')  # open work file, overwriting old file
    for line_num, line in enumerate(work_file_lined):  # iterate over work file contents
        input_edi_dict = line_from_mtc_edi_to_dict.capture_records(line)
        writeable_line = line
        if writeable_line.startswith("A"):
            if pad_arec == "True":
                writeable_line = writeable_line[0:1] + arec_padding[0:6] + writeable_line[7:]  # write "A" line
            if append_arec == "True":
                writeable_line = writeable_line.rstrip() + append_arec_text + '\n'
        if writeable_line.startswith("B"):
            if calc_upc == "True":
                blank_upc = False
                upc_string = ""
                try:
                    _ = int(input_edi_dict['upc_number'].rstrip())
                except ValueError:
                    blank_upc = True

                if blank_upc is False:
                    proposed_upc = input_edi_dict['upc_number'].strip()
                    if len(str(proposed_upc)) == 11:
                        upc_string = str(proposed_upc) + str(upc_e_to_upc_a.calc_check_digit(proposed_upc))
                    else:
                        if len(str(proposed_upc)) == 8:
                            upc_string = str(upc_e_to_upc_a.convert_UPCE_to_UPCA(proposed_upc))
                else:
                    upc_string = "            "
                writeable_line = writeable_line[0:1] + upc_string + writeable_line[12:]
        f.write(writeable_line.replace('\n', "\r\n").encode())
    else:
        f.write(chr(26).encode())

    f.close()  # close output file
    return output_filename
