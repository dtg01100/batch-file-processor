import hashlib
import datetime
import copy_backend
import ftp_backend
import email_backend
import converter
import convert_to_insight
import os
import time
import record_error
import cStringIO
import re
import edi_validator
import doingstuffoverlay


# this module iterates over all rows in the database, and attempts to process them with the correct backend


def process(folders_database, run_log, emails_table, run_log_directory,
            reporting, processed_files, root, args, version, errors_folder, edi_converter_scratch_folder):
    def update_overlay(overlay_text, dispatch_folder_count, folder_total, dispatch_file_count, file_total):
        if not args.automatic:
            doingstuffoverlay.destroy_overlay()
            doingstuffoverlay.make_overlay(parent=root,
                                           overlay_text=overlay_text + " folder " + str(
                                               dispatch_folder_count) + " of " + str(folder_total) + " file " + str(
                                               dispatch_file_count) + " of " + str(file_total))

    def emptydir(top):
        if top == '/' or top == "\\":
            return
        else:
            for root, dirs, files in os.walk(top, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))

    error_counter = 0
    processed_counter = 0
    folder_count = 0
    folder_total_count = folders_database.count(folder_is_active="True")
    for parameters_dict in folders_database.find(folder_is_active="True"):  # loop over all known active folders
        global filename
        folder_count += 1
        file_count = 0
        file_count_total = 0
        update_overlay("processing folder...\n\n", folder_count, folder_total_count, file_count, file_count_total)
        if os.path.isdir(parameters_dict['folder_name']) is True:
            print("entering folder " + parameters_dict['folder_name'] + ", aliased as " + parameters_dict['alias'])
            run_log.write("\r\n\r\nentering folder " + parameters_dict['folder_name'] + ", aliased as " +
                          parameters_dict['alias'] + "\r\n\r\n")
            os.chdir(parameters_dict['folder_name'])
            # strip potentially invalid filename characters from alias string
            cleaned_alias_string = re.sub('[^a-zA-Z0-9 ]', '', parameters_dict['alias'])
            # add iso8601 date/time stamp to filename, but filter : for - due to filename constraints
            folder_error_log_name_constructor = \
                cleaned_alias_string + " errors." + str(time.ctime()).replace(":", "-") + ".txt"
            folder_error_log_name_full_path = os.path.join(errors_folder['errors_folder'],
                                                           os.path.basename(parameters_dict['folder_name']),
                                                           folder_error_log_name_constructor)
            folder_errors_log = cStringIO.StringIO()
            files = [f for f in os.listdir('.')]  # create list of all files in directory
            filtered_files = []
            file_count_total = len(files)
            for f in files:
                file_count += 1
                update_overlay("processing folder... (checking files)\n\n", folder_count, folder_total_count,
                               file_count, file_count_total)
                if processed_files.find_one(file_name=os.path.join(os.getcwd(), f), file_checksum=hashlib.md5(
                        open(f, 'rb').read()).hexdigest()) is None:
                    filtered_files.append(f)
            file_count = 0
            errors = False
            if len(files) == 0:  # if there are no files in directory, record in log
                run_log.write("No files in directory\r\n\r\n")
                print("No files in directory")
            file_count_total = len(files)
            for filename in filtered_files:  # iterate over all files in directory
                original_filename = filename
                file_count += 1
                update_overlay("processing folder...\n\n", folder_count, folder_total_count,
                               file_count, file_count_total)
                if parameters_dict['process_edi'] == "True" and errors is False:
                    if parameters_dict['convert_to_format'] == "csv":
                        if edi_validator.check(filename):
                            # if the current file is recognized as a valid edi file,
                            # then convert it to csv, otherwise log and carry on
                            output_filename = os.path.join(edi_converter_scratch_folder['edi_converter_scratch_folder'],
                                                           os.path.basename(filename) + ".csv")
                            if os.path.exists(os.path.dirname(output_filename)) is False:
                                os.mkdir(os.path.dirname(output_filename))
                            emptydir(edi_converter_scratch_folder['edi_converter_scratch_folder'])
                            try:
                                run_log.write("converting " + filename + " from EDI to CSV\r\n")
                                print("converting " + filename + " from EDI to CSV")
                                converter.edi_convert(filename, output_filename,
                                                      parameters_dict['calculate_upc_check_digit'],
                                                      parameters_dict['include_a_records'],
                                                      parameters_dict['include_c_records'],
                                                      parameters_dict['include_headers'],
                                                      parameters_dict['filter_ampersand'],
                                                      parameters_dict['pad_a_records'],
                                                      parameters_dict['a_record_padding'])
                                run_log.write("Success\r\n\r\n")
                                filename = output_filename
                            except Exception, error:
                                print str(error)
                                errors = True
                                record_error.do(run_log, folder_errors_log, str(error), str(filename), "EDI Processor")
                        else:
                            record_error.do(run_log, folder_errors_log, filename +
                                            " is not an edi file", filename, "edi validator")
                    if parameters_dict['convert_to_format'] == "insight":
                            output_filename = os.path.join(edi_converter_scratch_folder['edi_converter_scratch_folder'],
                                   os.path.basename(filename) + ".txt")
                            if os.path.exists(os.path.dirname(output_filename)) is False:
                                os.mkdir(os.path.dirname(output_filename))
                            emptydir(edi_converter_scratch_folder['edi_converter_scratch_folder'])
                            try:
                                run_log.write("converting " + filename + " from EDI to Insight\r\n")
                                print("converting " + filename + " from EDI to Insight")
                                convert_to_insight.edi_convert(filename, output_filename)
                                run_log.write("Success\r\n\r\n")
                                filename = output_filename
                            except Exception, error:
                                print str(error)
                                errors = True
                                record_error.do(run_log, folder_errors_log, str(error), str(filename), "EDI Processor")
                # the following blocks process the files using the specified backend, and log in the event of any errors
                if parameters_dict['process_backend_copy'] is True and errors is False:
                    try:
                        print("sending file " + str(filename) + " to " +
                              str(parameters_dict['copy_to_directory']) + " with copy backend")
                        run_log.write("sending file " + str(filename) + " to " +
                                      str(parameters_dict['copy_to_directory']) + " with copy backend\r\n\r\n")
                        copy_backend.do(parameters_dict, filename)
                        run_log.write("Success\r\n\r\n")
                    except Exception, error:
                        print str(error)
                        record_error.do(run_log, folder_errors_log, str(error), str(filename), "Copy Backend")
                        errors = True
                if parameters_dict['process_backend_ftp'] is True and errors is False:
                    try:
                        print("sending " + str(filename) + " to " + str(parameters_dict['ftp_server']) +
                              " with FTP backend")
                        run_log.write("sending " + str(filename) + " to " + str(parameters_dict['ftp_server']) +
                                      " with FTP backend\r\n\r\n")
                        ftp_backend.do(parameters_dict, filename)
                        run_log.write("Success\r\n\r\n")
                    except Exception, error:
                        print str(error)
                        record_error.do(run_log, folder_errors_log, str(error), str(filename), "FTP Backend")
                        errors = True
                if parameters_dict['process_backend_email'] is True and errors is False:
                    try:
                        print("sending " + str(filename) + " to " + str(parameters_dict['email_to']) +
                              " with email backend")
                        run_log.write("sending " + str(filename) + " to " + str(parameters_dict['email_to']) +
                                      " with email backend\r\n\r\n")
                        email_backend.do(parameters_dict, filename)
                        run_log.write("Success\r\n\r\n")
                    except Exception, error:
                        record_error.do(run_log, folder_errors_log, str(error), str(filename), "Email Backend")
                        errors = True
                if errors is False:
                    try:
                        processed_files.insert(dict(file_name=str(os.path.abspath(original_filename)),
                                                    folder_id=parameters_dict['id'],
                                                    folder_alias=parameters_dict['alias'],
                                                    file_checksum=hashlib.md5(
                                                        open(original_filename, 'rb').read()).hexdigest(),
                                                    sent_date_time=datetime.datetime.now(),
                                                    copy_destination=parameters_dict['copy_to_directory'] if
                                                    parameters_dict['process_backend_copy'] is True else "N/A",
                                                    ftp_destination=parameters_dict['ftp_server'] if
                                                    parameters_dict['process_backend_ftp'] is True else "N/A",
                                                    email_destination=parameters_dict['email_to'] if
                                                    parameters_dict['process_backend_email'] is True else "N/A"))
                        processed_counter += 1
                    except Exception, error:
                        record_error.do(run_log, folder_errors_log, str(error), str(filename), "Dispatch")
                        errors = True
            if errors is True:
                error_counter += 1
                if os.path.exists(errors_folder['errors_folder']) is False:
                    record_error.do(run_log, folder_errors_log, "Base errors folder not found",
                                    str(parameters_dict['folder_name']), "Dispatch Error Logger")
                    print("Base error folder not found, " + "making one")
                    os.mkdir(errors_folder['errors_folder'])
                if os.path.exists(os.path.dirname(folder_error_log_name_full_path)) is False:
                    record_error.do(run_log, folder_errors_log, "Error folder Not Found",
                                    str(parameters_dict['folder_name']),
                                    "Dispatch Error Logger")
                    print("Error folder not found for " + parameters_dict['folder_name'] + ", " + "making one")
                    try:
                        os.mkdir(os.path.dirname(folder_error_log_name_full_path))
                    except IOError:  # if we can't create error logs folder, put it in run log directory
                        record_error.do(run_log, folder_errors_log, "Error creating errors folder",
                                        str(parameters_dict['folder_name']), "Dispatch Error Logger")
                        folder_error_log_name_full_path = os.path.join(run_log_directory,
                                                                       folder_error_log_name_constructor)
                try:
                    folder_errors_log_write = open(folder_error_log_name_full_path, 'w')
                    folder_errors_log_write.write("Program Version = " + version + "\r\n\r\n")
                    folder_errors_log_write.write(folder_errors_log.getvalue())
                    if reporting['enable_reporting'] == "True":
                        emails_table.insert(dict(log=folder_error_log_name_full_path,
                                                 folder_alias=parameters_dict['alias'],
                                                 folder_id=parameters_dict['id']))
                except Exception, error:
                    # if file can't be created in either directory, put error log inline in the run log
                    print("can't open error log file,\r\n error is " + str(error) + "\r\ndumping to run log")
                    run_log.write("can't open error log file,\r\n error is " + str(error) +
                                  "\r\ndumping to run log\r\n")
                    run_log.write("error log name was: " + folder_error_log_name_constructor + "\r\n\r\n")
                    run_log.write(folder_errors_log.getvalue())
                    run_log.write("\r\n\r\nEnd of Error file\r\n\r\n")
            folder_errors_log.close()
        else:
            # if the folder doesn't exist anymore, mark it as inactive
            data = dict(id=parameters_dict['id'], folder_is_active="False")
            folders_database.update(data, ['id'])
            run_log.write("\r\nfolder missing for " + parameters_dict['alias'] + ", disabling\r\n\r\n")
            print("folder missing for " + parameters_dict['alias'] + ", disabling")
    print(str(processed_counter) + " processed, " + str(error_counter) + " errors")
    run_log.write("\r\n\r\n" + str(processed_counter) + " processed, " + str(error_counter) + " errors")
