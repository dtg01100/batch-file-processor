# this function does a simple check to see if input file is an edi file, and returns false if it isn't


def check(input_file):

    file_to_test = open(input_file)
    for line in file_to_test:
        if line[0][0] != "A" and line[0] != "B" and line[0] != "C":
            return False
        else:
            try:
                if line[0] == "B":
                    line_check = int(line[1:10])
            except ValueError:
                print(repr(line[1:10]))
                if not line[1:10] == "         ":
                    return False
    return 1
