import os
import number_to_letters


def do_split_edi(edi_process, work_directory):

    f = None
    output_file_path = None
    count = 0
    edi_send_list = []
    if not os.path.exists(work_directory):
        os.mkdir(work_directory)
    with open(edi_process) as work_file:  # open input file
        work_file_lined = [n for n in work_file.readlines()]  # make list of lines
        list_of_first_characters = []
        for line in work_file_lined:
            list_of_first_characters.append(line[0])
        if list_of_first_characters.count("A") == 1:
            return edi_send_list
        if list_of_first_characters.count("A") > 700:
            return edi_send_list
        for line_mum, line in enumerate(work_file_lined):  # iterate over work file contents
            writeable_line = line
            if writeable_line.startswith("A"):
                prepend_letters = number_to_letters.generate_letters(count)
                count += 1
                try:
                    f.close()
                except Exception:
                    pass
                edi_send_list.append(output_file_path)
                output_file_path = os.path.join(work_directory, prepend_letters + " " + os.path.basename(edi_process))
                f = open(output_file_path, 'wb')
            f.write(writeable_line.replace('\n', "\r\n"))
        f.close()  # close output file
        edi_send_list.append(output_file_path)
        edi_send_list.pop(0)
        assert len(edi_send_list) == list_of_first_characters.count("A")
        if len(edi_send_list) < 1:
            raise Exception("No Split EDIs")
    return edi_send_list
