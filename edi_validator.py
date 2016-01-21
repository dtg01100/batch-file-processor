import cStringIO


# this function does a simple check to see if input file is an edi file, and returns false if it isn't
def check(input_file):

    file_to_test = open(input_file)
    for line in file_to_test:
        if line[0][0] != "A" and line[0] != "B" and line[0] != "C":
            return False
        else:
            try:
                if line[0] == "B":
                    line_check = int(line[1:12])
            except Exception:
                if not line[1:12] == "           ":
                    return False
    return 1


def report_edi_issues(input_file):
    in_memory_log = cStringIO.StringIO()
    line_number = 0
    has_errors = False
    input_file_handle = open(input_file)
    if check(input_file):
        for line in input_file_handle:
            line_number += 1
            if line[0] == "B":
                proposed_upc = line[1:12]
                if len(str(proposed_upc).rstrip()) == 8:
                    has_errors = True
                    in_memory_log.write("Suppressed UPC in line " + str(line_number) + "\r\n")
                    in_memory_log.write("line is:\r\n")
                    in_memory_log.write(line)
                if line[1:12] == "           ":
                    has_errors = True
                    in_memory_log.write("Blank UPC in line " + str(line_number) + "\r\n")
                    in_memory_log.write("line is:\r\n")
                    in_memory_log.write(line)
    return in_memory_log, has_errors
