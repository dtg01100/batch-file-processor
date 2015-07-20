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
            if os.path.isdir(parameters_dict['foldersname']) is True:
                os.chdir(parameters_dict['foldersname'])
                print (parameters_dict['foldersname'])
                try:
                    os.stat(os.path.join(parameters_dict['foldersname'], "obe"))
                except Exception, error:
                    print(str(error))
                    print("OBE folder not found for " + parameters_dict['foldersname'] + ", " + "making one\r\n")
                    run_log.write("OBE folder not found for " + parameters_dict['foldersname'] + ", " + "making one\r\n")
                    os.mkdir(os.path.join(parameters_dict['foldersname'], "obe"))
                folder_error_log_name_constructor = parameters_dict['alias'] + " errors." + str(time.ctime()).replace(":", "-") + ".txt"
                folder_error_log_name_fullpath = os.path.join(parameters_dict['foldersname'], "errors", folder_error_log_name_constructor)
                folder_errors_log = cStringIO.StringIO()
                print (str(parameters_dict))
                files = [f for f in os.listdir('.') if os.path.isfile(f)]
                errors = False
                for filename in files:
                    print filename
                    if parameters_dict['process_edi'] == "True":
                        try:
                            run_log.write("converting " + filename + " from EDI to CSV\r\n")
                            converter.edi_convert(parameters_dict, filename, filename + ".csv", parameters_dict['calc_upc'],
                                                  parameters_dict['inc_arec'], parameters_dict['inc_crec'],
                                                  parameters_dict['inc_headers'],
                                                  parameters_dict['filter_ampersand'],
                                                  parameters_dict['pad_arec'],
                                                  parameters_dict['arec_padding'])
                            try:
                                shutil.move(str(filename), os.path.join(parameters_dict['foldersname'], "obe"))
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
                            run_log.write("sending file " + str(filename) + " to " +
                                    str(parameters_dict['copy_to_directory']) + "with copy backend\r\n")
                            copy_backend.do(parameters_dict, filename)
                        except Exception, error:
                            print str(error)
                            record_error.do(run_log, folder_errors_log, str(error), str(filename), "Copy Backend\r\n")
                            errors = True
                            # error_handler.do(parameters_dict, filename)
                    if parameters_dict['process_backend'] == "ftp" and errors is False:
                        try:
                            run_log.write("sending " + str(filename) + " to " + str(parameters_dict['ftp_server']) + " with FTP backend\r\n")
                            ftp_backend.do(parameters_dict, filename)
                        except Exception, error:
                            print str(error)
                            record_error.do(run_log, folder_errors_log, str(error), str(filename), "FTP Backend")
                            errors = True
                            # error_handler.do(parameters_dict, filename)
                    if parameters_dict['process_backend'] == "email" and errors is False:
                        try:
                            run_log.write("sending " + str(filename) + " to " + str(parameters_dict['email_to']) + " with email backend\r\n")
                            email_backend.do(parameters_dict, filename)
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
                    if os.path.exists(os.path.join(parameters_dict['foldersname'], "errors")) is True:
                        if os.path.isfile(os.path.join(parameters_dict['foldersname'], "errors")) is True:
                            record_error.do(run_log, folder_errors_log,
                                            str(os.path.join(parameters_dict['foldersname'], "errors") +
                                                " is a file, deleting"), str(os.path.join(parameters_dict['foldersname'],
                                                "errors")), "Dispatch Error Logger")
                            os.remove(os.path.join(parameters_dict['foldersname'], "errors"))
                            try:
                                os.mkdir(os.path.join(parameters_dict['foldersname'], "errors"))
                            except Exception, error:
                                raise error
                    else:
                        record_error.do(run_log, folder_errors_log, str(error), str(parameters_dict['foldersname']),
                                    "Dispatch Error Logger")
                        print("Error folder not found for " + parameters_dict['foldersname'] + ", " + "making one")
                        try:
                            os.mkdir(os.path.join(parameters_dict['foldersname'], "errors"))
                        except Exception, error:
                            raise error
                    folder_errors_log_write = open(folder_error_log_name_fullpath, 'w')
                    print (folder_error_log_name_fullpath)
                    folder_errors_log_write.write(folder_errors_log.getvalue())
                    emails_table.insert(dict(log=folder_error_log_name_fullpath, folder_alias=parameters_dict['alias']))
                folder_errors_log.close()
            else:
                data = dict(id=parameters_dict['id'], is_active="False")
                folders_database.update(data, ['id'])
