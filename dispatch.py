import copy_backend
import ftp_backend
import email_backend

# this module iterates over all rows in the database, and attempts to process them with the correct backend
# TODO: error handling
# TODO: error reporting


def process(folders_database):
    for parameters_dict in folders_database.all():
        if parameters_dict['is_active'] == "True":
            if parameters_dict['process_backend'] == "copy":
                copy_backend.do(parameters_dict)
            if parameters_dict['process_backend'] == "ftp":
                ftp_backend.do(parameters_dict)
            if parameters_dict['process_backend'] == "email":
                email_backend.do(parameters_dict)
