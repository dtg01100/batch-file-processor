import hashlib
import datetime
import copy_backend
import ftp_backend
import email_backend
import convert_to_csv
import os
import time
import record_error
from io import StringIO
import re
import mtc_edi_validator
import doingstuffoverlay
import edi_tweaks
import split_edi
import clear_old_files
import concurrent.futures

# this module iterates over all rows in the database, and attempts to process them with the correct backend

hash_counter = 0
file_count = 0


def process(database_connection, folders_database, run_log, emails_table, run_log_directory,
            reporting, processed_files, root, args, version, errors_folder, edi_converter_scratch_folder, settings,
            simple_output=None):
    def update_overlay(overlay_text, dispatch_folder_count, folder_total, dispatch_file_count, file_total, footer):
        if not args.automatic:
            doingstuffoverlay.update_overlay(parent=root,
                                             overlay_text=overlay_text + " folder " +
                                             str(dispatch_folder_count) + " of " +
                                             str(folder_total) + "," + " file " +
                                             str(dispatch_file_count) + " of " +
                                             str(file_total), footer=footer, overlay_height=120)
        elif simple_output is not None:
            simple_output.configure(text=overlay_text + " folder " +
                                    str(dispatch_folder_count) + " of " +
                                    str(folder_total) + "," + " file " +
                                    str(dispatch_file_count) + " of " +
                                    str(file_total))
        root.update()

    def empty_directory(top):
        for folder_root, dirs, files_delete in os.walk(top, topdown=False):
            for name in files_delete:
                os.remove(os.path.join(folder_root, name))
            for name in dirs:
                os.rmdir(os.path.join(folder_root, name))

    global edi_validator_errors
    global global_edi_validator_error_status
    global file_count
    edi_validator_errors = StringIO()
    global_edi_validator_error_status = False

    def validate_file(input_file, file_name):
        global edi_validator_errors
        global global_edi_validator_error_status
        edi_validator_output, edi_validator_error_status, minor_edi_errors = \
            mtc_edi_validator.report_edi_issues(input_file)
        if minor_edi_errors or edi_validator_error_status and reporting['report_edi_errors']:
            edi_validator_errors.write("\r\nErrors for " + file_name + ":\r\n")
            edi_validator_errors.write(edi_validator_output.getvalue())
            edi_validator_output.close()
            global_edi_validator_error_status = True
        return edi_validator_error_status

    def generate_file_hash(source_file_path):
        global hash_counter
        hash_counter += 1
        print(source_file_path)
        file_name = os.path.join(os.getcwd(), source_file_path)
        generated_file_checksum = hashlib.md5(open(source_file_path, 'rb').read()).hexdigest()
        print(file_name, generated_file_checksum)
        return file_name, generated_file_checksum

    error_counter = 0
    processed_counter = 0
    folder_count = 0
    folder_total_count = folders_database.count(folder_is_active="True")
    # loop over all known active folders, in order of alias name
    for parameters_dict in folders_database.find(folder_is_active="True", order_by="alias"):
        global hash_counter
        global filename
        global send_filename
        folder_count += 1
        file_count = 0
        file_count_total = 0
        hash_counter = 0
        update_overlay("processing folder...\n\n", folder_count, folder_total_count, file_count, file_count_total, "")
        if os.path.isdir(parameters_dict['folder_name']) is True:
            print("entering folder " + parameters_dict['folder_name'] + ", aliased as " + parameters_dict['alias'])
            run_log.write(("\r\n\r\nentering folder " + parameters_dict['folder_name'] + ", aliased as " +
                           parameters_dict['alias'] + "\r\n\r\n").encode())
            os.chdir(parameters_dict['folder_name'])
            # strip potentially invalid send_filename characters from alias string
            cleaned_alias_string = re.sub('[^a-zA-Z0-9 ]', '', parameters_dict['alias'])
            # add iso8601 date/time stamp to send_filename, but filter : for - due to send_filename constraints
            folder_error_log_name_constructor = \
                cleaned_alias_string + " errors." + str(time.ctime()).replace(":", "-") + ".txt"
            folder_error_log_name_full_path = os.path.join(errors_folder['errors_folder'],
                                                           os.path.basename(parameters_dict['folder_name']),
                                                           folder_error_log_name_constructor)
            folder_errors_log = StringIO()
            files = [f for f in os.listdir('.')]  # create list of all files in directory
            filtered_files = []
            file_count_total = len(files)
            run_log.write("Generating file hashes\r\n".encode())
            print("Generating file hashes")

            file_hashes = []

            doingstuffoverlay.update_overlay(parent=root,
                                             overlay_text="Generating File Hashes", overlay_height=120)

            with concurrent.futures.ThreadPoolExecutor() as executor:
                for file_path, file_hash in executor.map(generate_file_hash, files):
                    print(file_path)
                    file_hash_appender = [file_path, file_hash]
                    file_hashes.append(file_hash_appender)
                    update_overlay("processing folder... (generating file hash)\n\n", folder_count, folder_total_count,
                                   str(hash_counter), file_count_total, "")

            run_log.write("Checking for new files\r\n".encode())
            print("Checking for new files")
            for f in file_hashes:
                file_count += 1
                print(f)
                update_overlay("processing folder... (checking files)\n\n", folder_count, folder_total_count,
                               file_count, file_count_total, "Checking File: " + os.path.basename(f[0]))
                if processed_files.find_one(file_name=f[0],
                                            file_checksum=str(f[1])) is None or \
                        processed_files.find_one(file_name=str(f[0]), resend_flag=True):
                    filtered_files.append((os.path.basename(f[0]), f[1]))

            file_count = 0
            folder_errors = False
            if len(files) == 0:  # if there are no files in directory, record in log
                run_log.write("No files in directory\r\n\r\n".encode())
                print("No files in directory")
            if len(filtered_files) == 0 and len(files) > 0:
                run_log.write("No new files in directory\r\n\r\n".encode())
                print("No new files in directory")
            if len(filtered_files) != 0:
                run_log.write((str(len(filtered_files)) + " found\r\n\r\n").encode())
                print(str(len(filtered_files)) + " found")
            file_count_total = len(filtered_files)
            empty_directory(edi_converter_scratch_folder['edi_converter_scratch_folder'])

            def process_files(input_hash):
                process_files_log = []
                process_files_error_log = []
                errors = False
                input_filename = None
                for row in filtered_files:
                    if row[1] == input_hash:
                        input_filename = row[0]
                input_file_checksum = input_hash
                global file_count
                file_scratch_folder = os.path.join(edi_converter_scratch_folder['edi_converter_scratch_folder'],
                                                   input_filename)
                input_filename = os.path.abspath(input_filename)
                process_original_filename = input_filename
                file_count += 1

                valid_edi_file = True
                if (parameters_dict['process_edi'] == "True"
                    or parameters_dict['tweak_edi']
                    or parameters_dict['split_edi']) \
                        or parameters_dict['force_edi_validation']:
                    if validate_file(input_filename, process_original_filename):
                        valid_edi_file = False
                if parameters_dict['split_edi'] and valid_edi_file:
                    process_files_log.append(("Splitting edi file " + process_original_filename + "...\r\n"))
                    print("Splitting edi file " + process_original_filename + "...")
                    try:
                        split_edi_list = split_edi.do_split_edi(input_filename, file_scratch_folder)
                        if len(split_edi_list) > 1:
                            process_files_log.append(
                                ("edi file split into " + str(len(split_edi_list)) + " files\r\n\r\n"))
                            print("edi file split into " + str(len(split_edi_list)) + " files")
                    except Exception as process_error:
                        split_edi_list = [input_filename]
                        process_files_log, process_files_error_log = record_error.do(process_files_log, process_files_error_log,
                                        "splitting edi file failed with error: " + str(process_error), input_filename,
                                        "edi splitter", True)
                else:
                    split_edi_list = [input_filename]
                if len(split_edi_list) <= 1 and parameters_dict['split_edi']:
                    process_files_log.append("Cannot split edi file\r\n\r\n")
                    print("Cannot split edi file")
                    split_edi_list = [input_filename]
                for output_send_filename in split_edi_list:
                    if errors is True:
                        break
                    stripped_filename = re.sub('[^A-Za-z0-9. ]+', '', os.path.basename(output_send_filename))
                    if os.path.exists(output_send_filename):
                        if valid_edi_file:
                            if parameters_dict['process_edi'] == "True" and errors is False:
                                # if the current file is recognized as a valid edi file,
                                # then allow conversion, otherwise log and carry on
                                if parameters_dict['convert_to_format'] == "csv":
                                    output_filename = os.path.join(
                                        file_scratch_folder,
                                        os.path.basename(stripped_filename) + ".csv")
                                    if os.path.exists(os.path.dirname(output_filename)) is False:
                                        os.mkdir(os.path.dirname(output_filename))
                                    try:
                                        process_files_log.append(
                                            ("converting " + output_send_filename + " from EDI to CSV\r\n"))
                                        print("converting " + output_send_filename + " from EDI to CSV")
                                        convert_to_csv.edi_convert(output_send_filename, output_filename,
                                                                   parameters_dict['calculate_upc_check_digit'],
                                                                   parameters_dict['include_a_records'],
                                                                   parameters_dict['include_c_records'],
                                                                   parameters_dict['include_headers'],
                                                                   parameters_dict['filter_ampersand'],
                                                                   parameters_dict['pad_a_records'],
                                                                   parameters_dict['a_record_padding'])
                                        process_files_log.append("Success\r\n\r\n")
                                        output_send_filename = output_filename
                                    except Exception as process_error:
                                        print(str(process_error))
                                        errors = True
                                        process_files_log, process_files_error_log = record_error.do(process_files_log, process_files_error_log, str(process_error),
                                                        str(output_send_filename),
                                                        "EDI Processor", True)

                            if parameters_dict['tweak_edi'] is True:
                                output_filename = \
                                    os.path.join(file_scratch_folder,
                                                 os.path.basename(stripped_filename))
                                if os.path.exists(os.path.dirname(output_filename)) is False:
                                    os.mkdir(os.path.dirname(output_filename))
                                try:
                                    output_send_filename = edi_tweaks.edi_tweak(output_send_filename, output_filename,
                                                                                parameters_dict['pad_a_records'],
                                                                                parameters_dict['a_record_padding'],
                                                                                parameters_dict['append_a_records'],
                                                                                parameters_dict['a_record_append_text'],
                                                                                parameters_dict['force_txt_file_ext'])
                                except Exception as process_error:
                                    print(str(process_error))
                                    errors = True
                                    process_files_log, process_files_error_log = record_error.do(process_files_log, process_files_error_log, str(process_error),
                                                    str(output_send_filename), "EDI Processor", True)

                        # the following blocks process the files using the specified backend,
                        # and log in the event of any errors
                        if parameters_dict['process_backend_copy'] is True and errors is False:
                            try:
                                print("sending " + str(output_send_filename) + " to " +
                                      str(parameters_dict['copy_to_directory']) + " with copy backend")
                                process_files_log.append(("sending " + str(output_send_filename) + " to " +
                                               str(parameters_dict[
                                                       'copy_to_directory']) + " with copy backend\r\n\r\n"))
                                copy_backend.do(parameters_dict, output_send_filename)
                                process_files_log.append("Success\r\n\r\n")
                            except Exception as process_error:
                                print(str(process_error))
                                process_files_log, process_files_error_log = record_error.do(process_files_log, process_files_error_log, str(process_error),
                                                str(output_send_filename),
                                                "Copy Backend", True)
                                errors = True
                        if parameters_dict['process_backend_ftp'] is True and errors is False:
                            try:
                                print(
                                    "sending " + str(output_send_filename) + " to " + str(
                                        parameters_dict['ftp_server']) +
                                    str(parameters_dict['ftp_folder']) + " with FTP backend")
                                process_files_log.append(
                                    ("sending " + str(output_send_filename) + " to " + str(
                                        parameters_dict['ftp_server']) +
                                     str(parameters_dict['ftp_folder']) + " with FTP backend\r\n\r\n"))
                                ftp_backend.do(parameters_dict, output_send_filename)
                                process_files_log.append("Success\r\n\r\n")
                            except Exception as process_error:
                                print(str(process_error))
                                process_files_log, process_files_error_log = record_error.do(process_files_log, process_files_error_log, str(process_error),
                                                str(output_send_filename),
                                                "FTP Backend", True)
                                errors = True
                        if parameters_dict['process_backend_email'] is True and errors is False and \
                                settings['enable_email']:
                            try:
                                print(
                                    "sending " + str(output_send_filename) + " to " + str(parameters_dict['email_to']) +
                                    " with email backend")
                                process_files_log.append(
                                    ("sending " + str(output_send_filename) + " to " + str(
                                        parameters_dict['email_to']) +
                                     " with email backend\r\n\r\n"))
                                email_backend.do(parameters_dict, settings, output_send_filename)
                                process_files_log.append("Success\r\n\r\n")
                            except Exception as process_error:
                                process_files_log, process_files_error_log = record_error.do(process_files_log, process_files_error_log, str(process_error),
                                                str(output_send_filename),
                                                "Email Backend", True)
                                errors = True
                return errors, process_original_filename, input_file_checksum, process_files_log, process_files_error_log

            file_hash_list = [x[1] for x in filtered_files]

            db_updated_counter = 0

            with concurrent.futures.ThreadPoolExecutor() as executor:
                for return_errors, original_filename, file_checksum, return_log, return_error_log in executor.map(process_files, file_hash_list):

                    # for input_tuple in input_data_tuple_list:  # iterate over all files in directory
                    #     errors, original_filename, file_checksum = process_files(input_tuple)
                    for row in return_log:
                        run_log.write(row.encode())
                    if return_errors:
                        for row in return_error_log:
                            folder_errors_log.write(row)
                            folder_errors = True
                    if not file_count == file_count_total:
                        update_overlay("processing folder...\n\n", folder_count, folder_total_count,
                                       file_count, file_count_total,
                                       "Sending File: " + os.path.basename(original_filename))
                    else:
                        update_overlay("processing folder... (updating database records)\n\n", folder_count,
                                       folder_total_count, db_updated_counter, file_count_total,
                                       "Updating Records For: " + os.path.basename(original_filename))
                    if return_errors is False:
                        try:
                            if processed_files.count(file_name=str(original_filename),
                                                     resend_flag=True) > 0:
                                file_old_id = processed_files.find_one(file_name=str(original_filename),
                                                                       resend_flag=True)
                                processed_files_update = dict(resend_flag=False, id=file_old_id['id'])
                                processed_files.update(processed_files_update, ['id'])

                            processed_files.insert(dict(file_name=str(original_filename),
                                                        folder_id=parameters_dict['id'],
                                                        folder_alias=parameters_dict['alias'],
                                                        file_checksum=file_checksum,
                                                        sent_date_time=datetime.datetime.now(),
                                                        copy_destination=parameters_dict['copy_to_directory'] if
                                                        parameters_dict['process_backend_copy'] is True else "N/A",
                                                        ftp_destination=parameters_dict['ftp_server'] +
                                                                        parameters_dict['ftp_folder'] if
                                                        parameters_dict['process_backend_ftp'] is True else "N/A",
                                                        email_destination=parameters_dict['email_to'] if
                                                        parameters_dict['process_backend_email'] is True else "N/A",
                                                        resend_flag=False))
                        except Exception as error:
                            record_error.do(run_log, folder_errors_log, str(error), str(original_filename), "Dispatch")
                            folder_errors = True
                    if return_errors is False:
                        processed_counter += 1
                        db_updated_counter += 1
                    else:
                        break
            if folder_errors is True:
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
                    folder_errors_log_write = open(folder_error_log_name_full_path, 'wb')
                    clear_old_files.do_clear(os.path.dirname(folder_error_log_name_full_path), 500)
                    folder_errors_log_write.write(("Program Version = " + version + "\r\n\r\n").encode())
                    folder_errors_log_write.write(folder_errors_log.getvalue().encode())
                    if reporting['enable_reporting'] == "True":
                        emails_table.insert(dict(log=folder_error_log_name_full_path,
                                                 folder_alias=parameters_dict['alias'],
                                                 folder_id=parameters_dict['id']))
                except Exception as error:
                    # if file can't be created in either directory, put error log inline in the run log
                    print("can't open error log file,\r\n error is " + str(error) + "\r\ndumping to run log")
                    run_log.write(("can't open error log file,\r\n error is " + str(error) +
                                   "\r\ndumping to run log\r\n").encode())
                    run_log.write(("error log name was: " + folder_error_log_name_constructor + "\r\n\r\n").encode())
                    run_log.write(folder_errors_log.getvalue().encode())
                    run_log.write("\r\n\r\nEnd of Error file\r\n\r\n".encode())
            else:
                database_connection.query("DELETE FROM processed_files WHERE ROWID IN (SELECT id FROM processed_files"
                                          " WHERE folder_id=" + str(parameters_dict['id']) +
                                          " ORDER BY id DESC LIMIT -1 OFFSET 5000)")
                processed_files_update = dict(resend_flag=False, folder_id=parameters_dict['id'])
                processed_files.update(processed_files_update, ['folder_id'])
            folder_errors_log.close()
        else:
            # if the folder is missing, complain and increment error counter
            run_log.write(("\r\nerror: " + os.path.abspath(parameters_dict['folder_name']) + " is missing " + " for " +
                           parameters_dict['alias'] + "\r\n\r\n").encode())
            print("error: " + os.path.abspath(parameters_dict['folder_name']) + " is missing " + " for " +
                  parameters_dict['alias'])
            error_counter += 1
    if global_edi_validator_error_status is True:
        validator_log_name_constructor = "Validator Log " + str(time.ctime()).replace(":", "-") + ".txt"
        validator_log_path = os.path.join(run_log_directory, validator_log_name_constructor)
        validator_log_file = open(validator_log_path, 'wb')
        validator_log_file.write(edi_validator_errors.getvalue().encode())
        edi_validator_errors.close()
        validator_log_file.close()
        if reporting['enable_reporting'] == "True":
            emails_table.insert(dict(log=validator_log_path))
    print(str(processed_counter) + " processed, " + str(error_counter) + " errors")

    if global_edi_validator_error_status:
        edi_validator_error_report_string = ", has EDI validator errors"
    else:
        edi_validator_error_report_string = ""

    run_summary_string = "{0} processed, {1} errors{2}".format(str(processed_counter), str(error_counter),
                                                               edi_validator_error_report_string)
    run_log.write(
        ("\r\n\r\n" + run_summary_string + "\r\n\r\n").encode())
    if error_counter > 0:
        return True, run_summary_string
    else:
        return False, run_summary_string
