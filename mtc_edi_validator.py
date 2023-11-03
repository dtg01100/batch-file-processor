import time
from io import StringIO

import line_from_mtc_edi_to_dict


# this function does a simple check to see if input file is an edi file, and returns false if it isn't
def check(input_file):

    try:
        line_number = 0
        file_to_test = None
        validator_open_attempts = 1
        while file_to_test is None:
            try:
                file_to_test = open(input_file)
            except Exception as error:
                if validator_open_attempts >= 5:
                    time.sleep(validator_open_attempts*validator_open_attempts)
                    validator_open_attempts += 1
                    print(f"retrying open {input_file}")
                else:
                    print(f"error opening file for read {error}")
                    raise
        # file_to_test = open(input_file)
        if file_to_test.read(1) != "A":
            return False, 1
        file_to_test.seek(0)
        for line in file_to_test:
            line_number += 1
            if line[0] != "A" and line[0] != "B" and line[0] != "C" and line[0] != "":
                file_to_test.close()
                return False, line_number
            else:
                try:
                    if line[0] == "B":
                        if len(line) != 77 and len(line) != 71:
                            file_to_test.close()
                            return False, line_number
                        _ = int(line[1:12])
                        if len(line) == 71 and line[51:67] != "                ":
                            file_to_test.close()
                            return False, line_number
                except ValueError:
                    if not line[1:12] == "           ":
                        file_to_test.close()
                        return False, line_number

        file_to_test.close()
        return True, line_number
    except Exception as eerror:
        print(eerror)
        file_to_test.close()
        return False, line_number

def report_edi_issues(input_file):
    def _insert_description_and_number(issue_line):
        line_dict = line_from_mtc_edi_to_dict.capture_records(issue_line)
        in_memory_log.write("Item description: " + line_dict['description'] + "\r\n")
        in_memory_log.write("Item number: " + line_dict['vendor_item'] + "\r\n\r\n")
    in_memory_log = StringIO()
    line_number = 0
    has_errors = False
    has_minor_errors = False
    validator_open_attempts = 1
    input_file_handle = None
    while input_file_handle is None:
        try:
            input_file_handle = open(input_file)
        except Exception as error:
            if validator_open_attempts >= 5:
                time.sleep(validator_open_attempts * validator_open_attempts)
                validator_open_attempts += 1
                print(f"retrying open {input_file}")
            else:
                print(f"error opening file for read {error}")
                raise

    # input_file_handle = open(input_file)
    check_pass, check_line_number = check(input_file)
    if check_pass is True:
        for line in input_file_handle:
            line_number += 1
            try:
                if line[0] == "B":
                    proposed_upc = line[1:12]
                    if len(str(proposed_upc).strip()) == 8:
                        has_minor_errors = True
                        in_memory_log.write("Suppressed UPC in line " + str(line_number) + "\r\n")
                        in_memory_log.write("line is:\r\n")
                        in_memory_log.write(line + "\r\n")
                        _insert_description_and_number(line)
                    else:
                        if 11 > len(str(proposed_upc).strip()) > 0:
                            has_minor_errors = True
                            in_memory_log.write("Truncated UPC in line " + str(line_number) + "\r\n")
                            in_memory_log.write("line is:\r\n")
                            in_memory_log.write(line + "\r\n")
                            _insert_description_and_number(line)
                    if line[1:12] == "           ":
                        has_minor_errors = True
                        in_memory_log.write("Blank UPC in line " + str(line_number) + "\r\n")
                        in_memory_log.write("line is:\r\n")
                        in_memory_log.write(line + "\r\n")
                        _insert_description_and_number(line)
                    if len(line) == 71:
                        has_minor_errors = True
                        has_minor_errors = True
                        in_memory_log.write("Missing pricing information in line " + str(line_number) +
                                            ". Is this a sample?" + "\r\n")
                        in_memory_log.write("line is:\r\n")
                        in_memory_log.write(line + "\r\n")
                        _insert_description_and_number(line)
            except Exception as error:
                has_errors = True
                in_memory_log.write("Validator produced error " + str(error) + " in line " + str(line_number) + "\r\n")
                in_memory_log.write("line is:\r\n")
                in_memory_log.write(line + "\r\n")
                _insert_description_and_number(line)
    else:
        in_memory_log.write("EDI check failed on line number: " + str(check_line_number) + "\r\n")
        has_errors = True
    input_file_handle.close()
    return in_memory_log, has_errors, has_minor_errors
