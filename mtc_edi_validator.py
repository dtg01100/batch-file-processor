from io import StringIO
import line_from_mtc_edi_to_dict


# this function does a simple check to see if input file is an edi file, and returns false if it isn't
def check(input_file):

    file_to_test = open(input_file)
    if file_to_test.read(1) != "A":
        return False, 1
    file_to_test.seek(0)
    line_number = 0
    for line in file_to_test:
        line_number += 1
        if line[0] != "A" and line[0] != "B" and line[0] != "C" and line[0] != "":
            return False, line_number
        else:
            try:
                if line[0] == "B":
                    if len(line) != 77:
                        return False, line_number
                    _ = int(line[1:12])
            except ValueError:
                if not line[1:12] == "           ":
                    return False, line_number

    return True, line_number


def report_edi_issues(input_file):
    def _insert_description_and_number(issue_line):
        line_dict = line_from_mtc_edi_to_dict.capture_records(issue_line)
        in_memory_log.write("Item description: " + line_dict['description'] + "\r\n")
        in_memory_log.write("Item number: " + line_dict['vendor_item'] + "\r\n\r\n")
    in_memory_log = StringIO()
    line_number = 0
    has_errors = False
    input_file_handle = open(input_file)
    check_pass, check_line_number = check(input_file)
    if check_pass is True:
        for line in input_file_handle:
            line_number += 1
            try:
                if line[0] == "B":
                    proposed_upc = line[1:12]
                    if len(str(proposed_upc).rstrip()) == 8:
                        has_errors = True
                        in_memory_log.write("Suppressed UPC in line " + str(line_number) + "\r\n")
                        in_memory_log.write("line is:\r\n")
                        in_memory_log.write(line)
                        _insert_description_and_number(line)
                    if line[1:12] == "           ":
                        has_errors = True
                        in_memory_log.write("Blank UPC in line " + str(line_number) + "\r\n")
                        in_memory_log.write("line is:\r\n")
                        in_memory_log.write(line)
                        _insert_description_and_number(line)
            except Exception as error:
                has_errors = True
                in_memory_log.write("Validator produced error " + str(error) + " in line " + str(line_number) + "\r\n")
                in_memory_log.write("line is:\r\n")
                in_memory_log.write(line)
                _insert_description_and_number(line)
    else:
        in_memory_log.write("EDI check failed on line number: " + str(check_line_number) + "\r\n")
        has_errors = True
    return in_memory_log, has_errors
