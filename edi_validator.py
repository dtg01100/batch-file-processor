# this function does a simple check to see if input file is an edi file, and returns false if it isn't


def check(input_file):

    input_file = open(input_file, 'r')
    if str(input_file.readline()[:1]) != "A":
        return False
    try:
        second_line = int(input_file.readline()[1:10])
    except ValueError:
        return False
    return 1
