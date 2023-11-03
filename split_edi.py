import os

import line_from_mtc_edi_to_dict


def do_split_edi(edi_process, work_directory):
    #  credit for the col_to_excel goes to Nodebody on stackoverflow, at this link: http://stackoverflow.com/a/19154642
    def col_to_excel(col):  # col is 1 based
        excel_col = str()
        div = col
        while div:
            (div, mod) = divmod(div - 1, 26)  # will return (x, 0 .. 25)
            excel_col = chr(mod + 65) + excel_col
        return excel_col

    f = None
    output_file_path = None
    count = 0
    write_counter = 0
    edi_send_list = []
    if not os.path.exists(work_directory):
        os.mkdir(work_directory)
    with open(edi_process, encoding="utf-8") as work_file:  # open input file
        lines_in_edi = sum(1 for _ in work_file)
        work_file.seek(0)
        work_file_lined = [n for n in work_file.readlines()]  # make list of lines
        list_of_first_characters = []
        for line in work_file_lined:
            list_of_first_characters.append(line[0])
        if list_of_first_characters.count("A") > 700:
            return edi_send_list
        for line_mum, line in enumerate(work_file_lined):  # iterate over work file contents
            writeable_line = line
            if writeable_line.startswith("A"):
                count += 1
                prepend_letters = col_to_excel(count)
                line_dict = line_from_mtc_edi_to_dict.capture_records(writeable_line)
                if int(line_dict['invoice_total']) < 0:
                    file_name_suffix = '.cr'
                else:
                    file_name_suffix = '.inv'
                if not len(edi_send_list) == 0:
                    f.close()
                edi_send_list.append(output_file_path)
                output_file_path = os.path.join(work_directory, prepend_letters + "_" + os.path.basename(edi_process) + file_name_suffix)
                f = open(output_file_path, 'wb')
            f.write(writeable_line.replace('\n', "\r\n").encode())
            write_counter += 1
        f.close()  # close output file
        edi_send_list.append(output_file_path)
        edi_send_list.pop(0)
        edi_send_list_lines = 0
        for output_file in edi_send_list:
            with open(output_file, encoding="utf-8") as file_handle:
                edi_send_list_lines += sum(1 for _ in file_handle)
        if not lines_in_edi == write_counter:
            raise Exception("not all lines in input were written out")
        if not lines_in_edi == edi_send_list_lines:
            raise Exception("total lines in output files do not match input file")
        if not len(edi_send_list) == list_of_first_characters.count("A"):
            raise Exception('mismatched number of "A" records')
        if len(edi_send_list) < 1:
            raise Exception("No Split EDIs")
    return edi_send_list
