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


def process(folders_database):
    for parameters_dict in folders_database.all():
        if parameters_dict['is_active'] == "True":
            os.chdir(parameters_dict['foldersname'])
            print (parameters_dict['foldersname'])
            try:
                os.stat(parameters_dict['foldersname'] + "/obe/")
            except:
                os.mkdir(parameters_dict['foldersname'] + "/obe/")
            try:
                os.stat(parameters_dict['foldersname'] + "/errors/")
            except:
                os.mkdir(parameters_dict['foldersname'] + "/errors/")
            error_log_name_constructor = "errors." + str(int(time.time())) + ".txt"
            error_log_name_fullpath = parameters_dict['foldersname'] + "/errors/" + error_log_name_constructor
            errors_log = open(error_log_name_fullpath, 'w')
            files = [f for f in os.listdir('.') if os.path.isfile(f)]
            errors = 0
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
                        except IOError:
                            print (IOError)
                            errors += errors + 1
                        filename = filename + ".csv"
                    except:
                        print Exception
                        errors += errors + 1
                        # error_handler.do(parameters_dict, filename)
                if parameters_dict['process_backend'] == "copy":
                    try:
                        copy_backend.do(parameters_dict, filename)
                    except Exception, error:
                        print error
                        errors_log.write("Copy Backend Error For File: " + filename + "\n")
                        errors_log.write(str(error) + "\n")
                        errors += errors + 1
                        # error_handler.do(parameters_dict, filename)
                if parameters_dict['process_backend'] == "ftp":
                    try:
                        ftp_backend.do(parameters_dict, filename)
                    except Exception, error:
                        print error
                        errors_log.write("FTP Backend Error For File: " + filename + "\n")
                        errors_log.write(str(error) + "\n")
                        errors += errors + 1
                        # error_handler.do(parameters_dict, filename)
                if parameters_dict['process_backend'] == "email":
                    try:
                        email_backend.do(parameters_dict, filename)
                    except Exception, error:
                        errors_log.write("Email Backend Error For File: " + filename + "\n")
                        errors_log.write(str(error) + "\n")
                        # error_handler.do(parameters_dict, filename)
                        errors += errors + 1
                if errors < 1:
                    try:
                        shutil.move(str(filename), parameters_dict['foldersname'] + "/obe/")
                    except Exception:
                        errors_log.write("Can't move file " + str(filename) + "\n")
            errors_log.close()
            if errors > 0:
                try:
                    error_handler.do(parameters_dict, error_log_name_fullpath)
                except Exception, error:
                    errors_log = open(error_log_name_fullpath, 'a')
                    errors_log.write("Error Sending Errors Log" + "\n")
                    errors_log.write(str(error))
                    errors_log.close()
