import copy_backend
import ftp_backend
import email_backend
import converter
import os
import shutil
import time
import error_handler

# this module iterates over all rows in the database, and attempts to process them with the correct backend
# TODO: error handling
# TODO: error reporting


def process(folders_database, reporting):
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
            error_log_name_constructor = "errors." + str(int(time.time())) + ".txt"
            error_log_name_fullpath = parameters_dict['foldersname'] + "/errors/" + error_log_name_constructor
            errors_log = open(error_log_name_fullpath, 'w')
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
                            errors_log.write("Error Moving " + filename + " To OBE Directory." + "\r\n")
                            errors_log.write("Error Message is:" + "\r\n")
                            errors_log.write(str(error) + "\r\n")
                            errors_log.write("Skipping File" + "\r\n")
                        filename = filename + ".csv"
                    except Exception, error:
                        print str(error)
                        errors = True
                        errors_log.write("Error Converting " + filename + " To CSV." + "\r\n")
                        errors_log.write("Error Message is:" + "\r\n")
                        errors_log.write(str(error) + "\r\n")
                        # error_handler.do(parameters_dict, filename)
                if parameters_dict['process_backend'] == "copy" and errors is False:
                    try:
                        copy_backend.do(parameters_dict, filename)
                    except Exception, error:
                        print str(error)
                        errors_log.write("Copy Backend Error For File: " + filename + "\r\n")
                        errors_log.write("Error Message is:" + "\r\n")
                        errors_log.write(str(error) + "\r\n")
                        errors = True
                        # error_handler.do(parameters_dict, filename)
                if parameters_dict['process_backend'] == "ftp" and errors is False:
                    try:
                        ftp_backend.do(parameters_dict, filename)
                    except Exception, error:
                        print str(error)
                        errors_log.write("FTP Backend Error For File: " + filename + "\r\n")
                        errors_log.write("Error Message is:" + "\r\n")
                        errors_log.write(str(error) + "\r\n")
                        errors = True
                        # error_handler.do(parameters_dict, filename)
                if parameters_dict['process_backend'] == "email" and errors is False:
                    try:
                        email_backend.do(parameters_dict, filename)
                    except Exception, error:
                        errors_log.write("Error Message is:" + "\r\n")
                        errors_log.write(str(error) + "\r\n")
                        # error_handler.do(parameters_dict, filename)
                        errors = True
                if errors is False:
                    try:
                        shutil.move(str(filename), parameters_dict['foldersname'] + "/obe/")
                    except Exception, error:
                        errors_log.write("Operation Successful, but can't move file " + str(filename) + "\r\n")
                        errors_log.write("Error Message is:" + "\r\n")
                        errors_log.write(str(error) + "\r\n")
                        errors = True
            errors_log.close()
            if errors is True:
                try:
                    print ("Sending Error Log.")
                    error_handler.do(parameters_dict, error_log_name_fullpath, reporting)
                except Exception, error:
                    print ("Sending Error Log Failed.")
                    errors_log = open(error_log_name_fullpath, 'a')
                    errors_log.write("Error Sending Errors Log" + "\r\n")
                    errors_log.write("Error Message is:" + "\r\n")
                    errors_log.write(str(error) + "\r\n")
                    errors_log.close()
