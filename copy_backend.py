import shutil

# this is a testing module for local file copies
# note: process_parameters is a dict from a row in the database, passed into this module
# TODO: error handling


def do(process_parameters, filename):
    print("copying " + filename)
    shutil.copy(filename, process_parameters['copy_to_directory'])
