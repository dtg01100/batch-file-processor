def edi_tweak(edi_process, output_filename, pad_arec, arec_padding):
    work_file = open(edi_process)  # open input file
    work_file_lined = [n for n in work_file.readlines()]  # make list of lines
    f = open(output_filename, 'wb')  # open work file, overwriting old file
    for line_num, line in enumerate(work_file_lined):  # iterate over work file contents

        if line.startswith("A"):
            f.write(line[0:1] + arec_padding[0:6] + line[7:]) if pad_arec == "True" else f.write(line)  # write "A" line
        else:
            f.write(line)

    f.close()  # close output file
