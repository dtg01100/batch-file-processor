def edi_tweak(edi_process, output_filename, pad_arec, arec_padding, append_arec, append_arec_text):
    work_file = open(edi_process)  # open input file
    work_file_lined = [n for n in work_file.readlines()]  # make list of lines
    f = open(output_filename, 'wb')  # open work file, overwriting old file
    for line_num, line in enumerate(work_file_lined):  # iterate over work file contents
        writeable_line = line
        if writeable_line.startswith("A") and pad_arec == "True":
            writeable_line = writeable_line[0:1] + arec_padding[0:6] + writeable_line[7:]  # write "A" line
        if writeable_line.startswith("A") and append_arec == "True":
            writeable_line = writeable_line.rstrip() + append_arec_text + '\n'
        f.write(writeable_line.replace('\n', "\r\n").encode())
    else:
        f.write(chr(26).encode())

    f.close()  # close output file
