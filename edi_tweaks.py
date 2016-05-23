def edi_tweak(edi_process, output_filename, pad_arec, arec_padding):
    work_file = open(edi_process)  # open input file
    work_file_lined = [n for n in work_file.readlines()]  # make list of lines
    f = open(output_filename, 'w')  # open work file, overwriting old file
    for line_num, line in enumerate(work_file_lined):  # iterate over work file contents
        writeable_line = line
        if writeable_line.startswith("A") and pad_arec == "True":
            writeable_line = writeable_line[0:1] + arec_padding[0:6] + writeable_line[7:]  # write "A" line
        f.write(writeable_line.replace('\n', "\r\n"))
    else:
        f.write(chr(26))

    f.close()  # close output file
