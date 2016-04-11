import os


def do_split_edi(edi_process, work_directory):

    def _generate_prepend_letter(number):
        numbers_list = []
        _number = number
        while _number != 0:
            first_character_number = divmod(_number, 26)
            _number = first_character_number[0]
            if len(numbers_list) > 0 and first_character_number[0] == 0:
                number_to_insert = first_character_number[1] - 1
            else:
                number_to_insert = first_character_number[1]
            numbers_list.insert(0, number_to_insert)
        letters_list = []
        for letter_number in numbers_list:
            letter = chr(ord('A') + (letter_number))
            letters_list.append(letter)
        final_string = "".join(letters_list)
        return final_string

    if not os.path.exists(work_directory):
        os.mkdir(work_directory)
    with open(edi_process) as work_file:  # open input file
        work_file_lined = [n for n in work_file.readlines()]  # make list of lines
        f = None
        output_file_path = None
        count = 0
        edi_send_list = []
        for line_mum, line in enumerate(work_file_lined):  # iterate over work file contents
            writeable_line = line
            if writeable_line.startswith("A"):
                count += 1
                try:
                    f.close()
                except Exception:
                    pass
                edi_send_list.append(output_file_path)
                prepend_letters = _generate_prepend_letter(count)
                output_file_path = os.path.join(work_directory, prepend_letters + " " + os.path.basename(edi_process))
                f = open(output_file_path, 'wb')
            f.write(writeable_line.replace('\n', "\r\n"))
        f.close()  # close output file
        edi_send_list.append(output_file_path)
        edi_send_list.pop(0)
        if len(edi_send_list) < 1:
            raise Exception("No Split EDIs")
        return edi_send_list
