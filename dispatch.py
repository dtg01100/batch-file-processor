import copy_backend
import ftp_backend
import email_backend
import converter
import os
import shutil
import time
import record_error
import cStringIO


# this module iterates over all rows in the database, and attempts to process them with the correct backend
# TODO: error handling
# TODO: error reporting


def process(folders_database, run_log, emails_table):
    for parameters_dict in folders_database.all():
        if parameters_dict['is_active'] == "True":
            os.chdir(parameters_dict['foldersname'])
            print (parameters_dict['foldersname'])
            try:
                os.stat(parameters_dict['foldersname'] + "/obe/")
            except Exception, error:
                print(str(error))
                print("Error folder not found for " + parameters_dict['foldersname'] + ", " + "making one")
                os.mkdir(parameters_dict['foldersname'] + "/obe/")
            try:
                os.stat(parameters_dict['foldersname'] + "/errors/")
            except Exception, error:
                print str(error)
                print("Error folder not found for " + parameters_dict['foldersname'] + ", " + "making one")
                os.mkdir(parameters_dict['foldersname'] + "/errors/")
            folder_error_log_name_constructor = parameters_dict['alias'] + " errors." + str(int(time.time())) + ".txt"
            folder_error_log_name_fullpath = parameters_dict['foldersname'] + "/errors/" + folder_error_log_name_constructor
            folder_errors_log = cStringIO.StringIO()
            files = [f for f in os.listdir('.') if os.path.isfile(f)]
            errors = False
            for filename in files:
                print filename
                if parameters_dict['process_edi'] == "True":
                    try:
                        converter.edi_convert(parameters_dict, filename, filename + ".csv", parameters_dict['calc_upc'],
                                              parameters_dict['inc_arec'], parameters_dict['inc_crec'],
                                              parameters_dict['inc_headers'],
                                              parameters_dict['filter_ampersand'],
                                              parameters_dict['pad_arec'],
                                              parameters_dict['arec_padding'])
                        try:
                            shutil.move(str(filename), parameters_dict['foldersname'] + "/obe/")
                        except Exception, error:
                            print str(error)
                            errors = True
                            record_error.do(run_log, folder_errors_log, str(error), str(filename), "EDI Processor")
                            run_log.write("Skipping File" + str(filename) + "\r\n")
                        filename = filename + ".csv"
                    except Exception, error:
                        print str(error)
                        errors = True
                        record_error.do(run_log, folder_errors_log, str(error), str(filename), "EDI Processor")
                if parameters_dict['process_backend'] == "copy" and errors is False:
                    try:
                        copy_backend.do(parameters_dict, filename)
                    except Exception, error:
                        print str(error)
                        record_error.do(run_log, folder_errors_log, str(error), str(filename), "Copy Backend")
                        errors = True
                        # error_handler.do(parameters_dict, filename)
                if parameters_dict['process_backend'] == "ftp" and errors is False:
                    try:
                        ftp_backend.do(parameters_dict, filename)
                    except Exception, error:
                        print str(error)
                        record_error.do(run_log, folder_errors_log, str(error), str(filename), "FTP Backend")
                        errors = True
                        # error_handler.do(parameters_dict, filename)
                if parameters_dict['process_backend'] == "email" and errors is False:
                    try:
                        email_backend.do(parameters_dict, filename)
                    except Exception, error:
                        record_error.do(run_log, folder_errors_log, str(error), str(filename), "Email Backend")
                        errors = True
                if errors is False:
                    try:
                        shutil.move(str(filename), parameters_dict['foldersname'] + "/obe/")
                    except Exception, error:
                        record_error.do(run_log, folder_errors_log, str(error), str(filename), "Dispatch")
                        errors = True
            if errors is True:
                folder_errors_log_write = open(folder_error_log_name_fullpath, 'w')
                folder_errors_log_write.write(folder_errors_log.getvalue())
                emails_table.insert(dict(log=folder_error_log_name_fullpath, folder_alias=parameters_dict['alias']))
            folder_errors_log.close()
