import os


def do_split_edi(edi_process, work_directory):
    os.chdir(work_directory)
    work_file = open(edi_process)  # open input file
    work_file_lined = [n for n in work_file.readlines()]  # make list of lines
    f = None
    output_file_path = None
    count = 0
    edi_send_list = []
    for line_mum, line in enumerate(work_file_lined):  # iterate over work file contents
        writeable_line = line
        if writeable_line.startswith("A"):
            edi_send_list.append(output_file_path)
            output_file_path = os.path.join(work_directory, edi_process + '_' + str(count))
            f = open(output_file_path)
        f.write(writeable_line.replace('\n', "\r\n"))
    f.close()  # close output file
    edi_send_list.append(output_file_path)
    return edi_send_list
