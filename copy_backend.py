import shutil

# this is a testing module for local file copies
# note: process_parameters is a dict from a row in the database, passed into this module


def do(process_parameters, settings_dict, filename):
    file_pass = False
    counter = 0
    while not file_pass:
        try:
            shutil.copy(filename, process_parameters['copy_to_directory'])
            file_pass = True
        except IOError:
            if counter == 10:
                raise
            counter += 1
