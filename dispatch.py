import copy_backend
import ftp_backend
import email_backend
import converter
import os
import shutil
import time
import record_error
import cStringIO
import re
import edi_validator


# this module iterates over all rows in the database, and attempts to process them with the correct backend


def process(folders_database, run_log, emails_table, run_log_directory, reporting):
    error_counter = 0
    processed_counter = 0
    for parameters_dict in folders_database.all():  # loop over all known folders
        if parameters_dict['is_active'] == "True":  # skip inactive ones
            # if the backend is invalid, deactivate
            if parameters_dict['process_backend'] != 'copy' and parameters_dict['process_backend'] != 'ftp' and parameters_dict['process_backend'] != 'email':
                print("invalid backend, setting to inactive")
                data = dict(id=parameters_dict['id'], is_active="False")
                folders_database.update(data, ['id'])
            else:
                if os.path.isdir(parameters_dict['foldersname']) is True:
                    os.chdir(parameters_dict['foldersname'])
                    try:
                        os.stat(os.path.join(parameters_dict['foldersname'], "obe"))
                    except Exception, error:
                        print(str(error))
                        print("OBE folder not found for " + parameters_dict['foldersname'] + ", " + "making one\r\n")
                        run_log.write("OBE folder not found for " + parameters_dict['foldersname'] + ", " + "making one\r\n\r\n")
                        os.mkdir(os.path.join(parameters_dict['foldersname'], "obe"))
                    cleaned_alias_string = re.sub('[^a-zA-Z0-9 ]', '', parameters_dict['alias'])  # strip potentially invalid filename characters from alias string
                    folder_error_log_name_constructor = cleaned_alias_string + " errors." + str(time.ctime()).replace(":", "-") + ".txt"  # add iso8601 date/time stamp to filename, but filter : for - due to filename constraints
                    folder_error_log_name_fullpath = os.path.join(parameters_dict['foldersname'], "errors", folder_error_log_name_constructor)
                    folder_errors_log = cStringIO.StringIO()
                    run_log.write("processing folder " + parameters_dict['foldersname'] + " with backend " + parameters_dict['process_backend'] + "\r\n\r\n")
                    print("processing folder " + parameters_dict['foldersname'] + " with backend " + parameters_dict['process_backend'])
                    files = [f for f in os.listdir('.') if os.path.isfile(f)]  # create list of all files in directory
                    errors = False
                    if len(files) == 0:  # if there are no files in directory, record in log
                        run_log.write("No files in directory\r\n\r\n")
                        print("No files in directory")
                    for filename in files:  # iterate over all files in directory
                        if parameters_dict['process_edi'] == "True":
                            if edi_validator.check(filename):
                                # if the current file is recognized as a valid edi file, then convert it to csv, otherwise log and carry on
                                try:
                                    run_log.write("converting " + filename + " from EDI to CSV\r\n")
                                    print("converting " + filename + " from EDI to CSV")
                                    converter.edi_convert(parameters_dict, filename, filename + ".csv", parameters_dict['calc_upc'],
                                                          parameters_dict['inc_arec'], parameters_dict['inc_crec'],
                                                          parameters_dict['inc_headers'],
                                                          parameters_dict['filter_ampersand'],
                                                          parameters_dict['pad_arec'],
                                                          parameters_dict['arec_padding'])
                                    run_log.write("Success\r\n\r\n")
                                    try:
                                        shutil.move(str(filename), os.path.join(parameters_dict['foldersname'], "obe"))
                                    except Exception, error:
                                        print str(error)
                                        errors = True
                                        record_error.do(run_log, folder_errors_log, str(error), str(filename), "EDI Processor")
                                    filename = filename + ".csv"
                                except Exception, error:
                                    print str(error)
                                    errors = True
                                    record_error.do(run_log, folder_errors_log, str(error), str(filename), "EDI Processor")
                            else:
                                record_error.do(run_log,folder_errors_log, filename + " is not an edi file", filename, "edi validator")
                        # the following blocks process the files using the specified backend, and log in the event of any errors
                        if parameters_dict['process_backend'] == "copy" and errors is False:
                            try:
                                print("sending file " + str(filename) + " to " +
                                        str(parameters_dict['copy_to_directory']) + " with copy backend")
                                run_log.write("sending file " + str(filename) + " to " +
                                        str(parameters_dict['copy_to_directory']) + " with copy backend\r\n\r\n")
                                copy_backend.do(parameters_dict, filename)
                                run_log.write("Success\r\n\r\n")
                                processed_counter = processed_counter + 1
                            except Exception, error:
                                print str(error)
                                record_error.do(run_log, folder_errors_log, str(error), str(filename), "Copy Backend")
                                errors = True
                        if parameters_dict['process_backend'] == "ftp" and errors is False:
                            try:
                                print("sending " + str(filename) + " to " + str(parameters_dict['ftp_server']) + " with FTP backend")
                                run_log.write("sending " + str(filename) + " to " + str(parameters_dict['ftp_server']) + " with FTP backend\r\n\r\n")
                                ftp_backend.do(parameters_dict, filename)
                                run_log.write("Success\r\n\r\n")
                                processed_counter = processed_counter + 1
                            except Exception, error:
                                print str(error)
                                record_error.do(run_log, folder_errors_log, str(error), str(filename), "FTP Backend")
                                errors = True
                        if parameters_dict['process_backend'] == "email" and errors is False:
                            try:
                                print("sending " + str(filename) + " to " + str(parameters_dict['email_to']) + " with email backend")
                                run_log.write("sending " + str(filename) + " to " + str(parameters_dict['email_to']) + " with email backend\r\n\r\n")
                                email_backend.do(parameters_dict, filename)
                                run_log.write("Success\r\n\r\n")
                                processed_counter = processed_counter + 1
                            except Exception, error:
                                record_error.do(run_log, folder_errors_log, str(error), str(filename), "Email Backend")
                                errors = True
                        if errors is False:
                            try:
                                shutil.move(str(filename), os.path.join(parameters_dict['foldersname'], "obe"))
                            except Exception, error:
                                record_error.do(run_log, folder_errors_log, str(error), str(filename), "Dispatch")
                                errors = True
                    if errors is True:
                        error_counter = error_counter + 1
                        # check for file blocking error log folder, attempt to clear it, record errors
                        if os.path.exists(os.path.join(parameters_dict['foldersname'], "errors")) is True:
                            if os.path.isfile(os.path.join(parameters_dict['foldersname'], "errors")) is True:
                                record_error.do(run_log, folder_errors_log,
                                                str(os.path.join(parameters_dict['foldersname'], "errors") +
                                                    " is a file, deleting"), str(os.path.join(parameters_dict['foldersname'],
                                                    "errors")), "Dispatch Error Logger")
                                try:
                                    os.remove(os.path.join(parameters_dict['foldersname'], "errors"))
                                except IOError:
                                    record_error.do(run_log, folder_errors_log,
                                                str(os.path.join(parameters_dict['foldersname'], "errors") +
                                                    "cannot be deleted"), str(os.path.join(parameters_dict['foldersname'],
                                                    "errors")), "Dispatch Error Logger")
                                try:
                                    os.mkdir(os.path.join(parameters_dict['foldersname'], "errors"))
                                except IOError:
                                    record_error.do(run_log, folder_errors_log,
                                                str(os.path.join(parameters_dict['foldersname'], "errors") +
                                                    " cannot be created as directory"), str(os.path.join(parameters_dict['foldersname'],
                                                    "errors")), "Dispatch Error Logger")
                        else:
                            record_error.do(run_log, folder_errors_log, "Error folder Not Found", str(parameters_dict['foldersname']),
                                        "Dispatch Error Logger")
                            print("Error folder not found for " + parameters_dict['foldersname'] + ", " + "making one")
                            try:
                                os.mkdir(os.path.join(parameters_dict['foldersname'], "errors"))
                            except IOError:  # if we can't create error logs folder, put it in run log directory
                                record_error.do(run_log, folder_errors_log, "Error creating errors folder",
                                                str(parameters_dict['foldersname']),"Dispatch Error Logger")
                                folder_error_log_name_fullpath = os.path.join(run_log_directory, folder_error_log_name_constructor)
                        try:
                            folder_errors_log_write = open(folder_error_log_name_fullpath, 'w')
                            folder_errors_log_write.write(folder_errors_log.getvalue())
                            if reporting['enable_reporting'] == "True":
                                emails_table.insert(dict(log=folder_error_log_name_fullpath, folder_alias=parameters_dict['alias']))
                        except Exception, error:
                            # if file can't be created in either directory, put error log inline in the run log
                            print("can't open error log file,\r\n error is " + str(error) + "\r\ndumping to run log")
                            run_log.write("can't open error log file,\r\n error is " + str(error) + "\r\ndumping to run log\r\n")
                            run_log.write("error log name was: " + folder_error_log_name_constructor + "\r\n\r\n")
                            run_log.write(folder_errors_log.getvalue())
                            run_log.write("\r\n\r\nEnd of Error file\r\n\r\n")
                    folder_errors_log.close()
                else:
                    # if the folder doesn't exist anymore, mark it as inactive
                    data = dict(id=parameters_dict['id'], is_active="False")
                    folders_database.update(data, ['id'])
                    run_log.write("\r\nfolder missing for " + parameters_dict['alias'] + ", disabling\r\n\r\n")
                    print("folder missing for " + parameters_dict['alias'] + ", disabling")
    print(str(processed_counter) + " processed, " + str(error_counter) + " errors")
    run_log.write("\r\n\r\n" + str(processed_counter) + " processed, " + str(error_counter) + " errors")
