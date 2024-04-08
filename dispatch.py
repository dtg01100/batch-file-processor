import concurrent.futures
import datetime
import hashlib
import os
import queue
import re
import shutil
import tempfile
import threading
import time
from io import StringIO

import clear_old_files
import convert_to_csv
import convert_to_estore
import convert_to_estore_generic
import convert_to_jolley_edi
import convert_to_scannerware
import convert_to_scansheet_type_a
import convert_to_simplified_csv
import copy_backend
import doingstuffoverlay
import edi_tweaks
import email_backend
import ftp_backend
import mtc_edi_validator
import record_error
import split_edi
from query_runner import query_runner


def generate_match_lists(files):
    """
    Creates dictionaries of file hashes and file names, as well as a set of
    file checksums for files flagged for resend.

    :param files: List of dictionaries containing file information
    :return: file_hashes, file_names, resend_flags
    """
    file_hashes = {}
    """Dictionary of file names and their corresponding file checksums"""
    file_names = {}
    """Dictionary of file checksums and their corresponding file names"""
    resend_flags = set()
    """Set of file checksums for files flagged for resend"""

    for file in files:
        file_hashes[file["file_name"]] = file["file_checksum"]
        """Add file name and its corresponding file checksum to the dictionary"""
        file_names[file["file_checksum"]] = file["file_name"]
        """Add file checksum and its corresponding file name to the dictionary"""
        if file["resend_flag"]:
            resend_flags.add(file["file_checksum"])
            """Add file checksum to the set if the file is flagged for resend"""

    return file_hashes, file_names, resend_flags


def generate_file_hash(source_file_struct):
    """
    Generates the file hash for a given file

    :param source_file_struct: tuple containing:
        file_path: str, path to the file to hash
        index: int, index of the file in the list of files to process
        processed_files: list of dicts, rows from the processed files table
        hashes: dict, file hashes and their corresponding file names
        names: dict, file checksums and their corresponding file names
        resend_flags: set, file checksums of files flagged for resend
    :return: tuple containing:
        file_name: str, absolute path to the file
        checksum: str, hexdigest of the file hash
        index: int, index of the file in the list of files to process
        send_file: bool, True if the file should be sent
    """
    file_path, index, processed_files, hashes, names, resend_flags = source_file_struct

    file_name = os.path.abspath(file_path)
    checksum = hashlib.md5()
    with open(file_name, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            checksum.update(chunk)
    checksum = checksum.hexdigest()

    match_found = checksum in hashes
    send_file = not match_found or checksum in resend_flags or os.path.basename(names.get(checksum, '')) != os.path.basename(file_name)

    return file_name, checksum, index, send_file




# this module iterates over all rows in the database, and attempts to process them with the correct backend

hash_counter = 0
file_count = 0
filename = ''
send_filename = ''
parameters_dict_list = []
hash_thread_return_list = []
hash_thread_return_queue = queue.Queue()


def process(database_connection, folders_database, run_log, emails_table, run_log_directory,
            reporting, processed_files, root, args, version, errors_folder, settings,
            simple_output=None):
    global hash_counter
    global file_count
    global parameters_dict_list
    global hash_thread_return_queue
    global edi_validator_errors
    global global_edi_validator_error_status
    global file_count
    global hash_counter
    global filename
    global send_filename
    hash_counter = 0
    file_count = 0
    hash_thread_return_queue = queue.Queue()

    query_object = query_runner(
    settings["as400_username"],
    settings["as400_password"],
    settings["as400_address"],
    f"{settings['odbc_driver']}",
    )

    each_upc_qreturn = []
    for itemno, upc in query_object.run_arbitrary_query("""
                        select dsanrep.anbacd, dsanrep.anbgcd
                    from dacdata.dsanrep dsanrep
                    """):
        each_upc_qreturn.append((int(itemno), upc))

    each_upc_dict = dict(each_upc_qreturn)

    # This function updates the overlay window with information about the current
    # processing status.
    #
    # Arguments:
    # dispatch_folder -- the current folder number being processed
    # total_folders -- the total number of folders being processed
    # dispatch_file -- the current file number being processed
    # total_files -- the total number of files being processed
    # footer_text -- additional text to display in the footer of the overlay
    def update_overlay(dispatch_folder, total_folders,
                       dispatch_file, total_files, footer_text):
        if args.automatic:
            simple_output.configure(text=f"Folder {dispatch_folder} of {total_folders}, "
                                          f"file {dispatch_file} of {total_files}")
        else:
            doingstuffoverlay.update_overlay(parent=root,
                                             overlay_text=f"Folder {dispatch_folder} of {total_folders}, "
                                                         f"file {dispatch_file} of {total_files}",
                                             footer=footer_text, overlay_height=120)
        root.update()


    edi_validator_errors = StringIO()
    global_edi_validator_error_status = False

    # This function validates an edi file and returns True if it has any errors,
    # and False otherwise.
    #
    # Arguments:
    # input_file -- the path to the edi file to be validated
    # file_name -- the name of the file being validated, used for error reporting
    #
    # Returns:
    # True if the input file has errors, False otherwise
    def validate_file(input_file, file_name):
        issues, has_errors = mtc_edi_validator.report_edi_issues(input_file)
        if has_errors and reporting['report_edi_errors']:
            edi_validator_errors.write(f"\r\nErrors for {file_name}:\r\n{issues}")
            global_edi_validator_error_status = True
        return has_errors


    parameters_dict_list = []
    for parameters_dict in folders_database.find(folder_is_active="True", order_by="alias"):
        try:
            parameters_dict['id'] = parameters_dict.pop('old_id')
        except KeyError:
            pass
        parameters_dict_list.append(parameters_dict)

    # This function is the target for the hash thread. It generates the file
    # hashes for each folder in the queue.
    def hash_thread_target():
        """Hash thread target"""
        global parameters_dict_list
        global hash_thread_return_list

        # Use a process pool executor to generate the hashes for each folder
        with concurrent.futures.ProcessPoolExecutor() as executor:
            for counter, entry_dict in enumerate(parameters_dict_list):
                # Get the folder path and the list of files in the folder
                folder_path = os.path.abspath(entry_dict["folder_name"])
                file_paths = [os.path.abspath(os.path.join(folder_path, file)) for file in os.listdir(folder_path)
                              if os.path.isfile(os.path.join(folder_path, file))]
                file_count = len(file_paths)
                print(f"Generating file hashes {counter + 1} of {len(parameters_dict_list)} ({folder_path})")

                # Try to get the old id from the dict, if it exists, otherwise
                # use the id
                try:
                    folder_id = entry_dict["old_id"]
                except KeyError:
                    folder_id = entry_dict["id"]

                # Get the processed files for the current folder
                processed_files = processed_files.find(folder_id=folder_id)

                # Create two lists, one for the filtered files which have already
                # been processed and have file hashes, and one for the files
                # which have not been processed and need to have their hashes
                # generated.
                filtered_files = []
                file_hashes = []

                for file_path, index_number in zip(file_paths, range(1, len(file_paths) + 1)):
                    # Find the first processed file with a matching index number
                    processed_file = next((file for file in processed_files if file["index_number"] == index_number), None)
                    if processed_file:
                        # If a matching processed file is found, add it to the
                        # filtered files list
                        filtered_files.append((index_number, os.path.basename(file_path), processed_file["file_hash"]))
                    else:
                        # If no matching processed file is found, add the file
                        # path to the list of files that need to have their hashes
                        # generated
                        file_hashes.append(file_path)

                # Use the process pool executor to generate the hashes for the
                # files which need to be processed
                results = executor.map(generate_file_hash_and_index, zip(file_hashes, range(1, len(file_hashes) + 1)))
                file_hashes_per_file = [(file_path, file_hash, index_number) for (index_number, file_hash, file_path) in results]

                # Put the results in a dict and add it to the hash thread return
                # list
                hash_thread_return_queue.put(dict(folder_name=entry_dict["folder_name"], files=file_paths,
                                                  file_count_total=file_count,
                                                  file_hashes=file_hashes_per_file, filtered_files=filtered_files))

    hash_thread_object = threading.Thread(target=hash_thread_target)

    error_counter = 0
    processed_counter = 0
    folder_count = 0
    folder_total_count = folders_database.count(folder_is_active="True")
    temp_processed_files_list = []

    for entry in processed_files.find():
        temp_processed_files_list.append(dict(entry))
    hash_thread_object.start()
    for parameters_dict in parameters_dict_list:
        folder_count += 1
        file_count = 0
        file_count_total = 0
        hash_counter = 0
        update_overlay("processing folder...\n\n", folder_count, folder_total_count, file_count, file_count_total, "")
        if os.path.isdir(parameters_dict['folder_name']) is True:
            print("processing folder " + parameters_dict['folder_name'] + ", aliased as " + parameters_dict['alias'])
            run_log.write(("\r\n\r\nentering folder " + parameters_dict['folder_name'] + ", aliased as " +
                           parameters_dict['alias'] + "\r\n\r\n").encode())
            # strip potentially invalid send_filename characters from alias string
            cleaned_alias_string = re.sub('[^a-zA-Z0-9 ]', '', parameters_dict['alias'])
            # add iso8601 date/time stamp to send_filename, but filter : for - due to send_filename constraints
            folder_error_log_name_constructor = \
                cleaned_alias_string + " errors." + str(time.ctime()).replace(":", "-") + ".txt"
            folder_error_log_name_full_path = os.path.join(errors_folder['errors_folder'],
                                                           os.path.basename(parameters_dict['folder_name']),
                                                           folder_error_log_name_constructor)
            folder_errors_log = StringIO()

            hash_thread_return_dict = hash_thread_return_queue.get()

            files = hash_thread_return_dict['files']

            filtered_files = hash_thread_return_dict['filtered_files']

            # print('files are' + str(files))

            if parameters_dict['folder_name'] == hash_thread_return_dict['folder_name']:
                print("Dictionaries Match")
            else:
                print("Dictionaries Mismatch")
                raise ValueError("desync between current folder {} and current entry in hashed queue {}".format(
                    parameters_dict['folder_name'], hash_thread_return_dict['folder_name']
                    ))
            assert parameters_dict['folder_name'] == hash_thread_return_dict['folder_name']

            # filtered_files = []

            run_log.write("Checking for new files\r\n".encode())
            print("Checking for new files")

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

            def process_files(file_index_number):
                process_files_log = []
                process_files_error_log = []
                errors = False
                input_filename = None
                input_file_checksum = None
                for process_row in filtered_files:
                    if process_row[0] == file_index_number:
                        input_filename = process_row[1]
                        input_file_checksum = process_row[2]
                assert input_file_checksum is not None
                global file_count
                with tempfile.TemporaryDirectory() as file_scratch_folder:
                    input_filename = os.path.join(os.path.abspath(parameters_dict['folder_name']), input_filename)
                    process_original_filename = input_filename
                    file_count += 1

                    valid_edi_file = True
                    if (parameters_dict['process_edi'] == "True"
                        or parameters_dict['tweak_edi']
                        or parameters_dict['split_edi']) \
                            or parameters_dict['force_edi_validation']:
                        print(input_filename)
                        if validate_file(input_filename, process_original_filename):
                            valid_edi_file = False
                    if parameters_dict['split_edi'] and valid_edi_file:
                        process_files_log.append(("Splitting edi file " + process_original_filename + "...\r\n"))
                        print("Splitting edi file " + process_original_filename + "...")
                        try:
                            split_edi_list = split_edi.do_split_edi(input_filename, file_scratch_folder, parameters_dict)
                            if len(split_edi_list) > 1:
                                process_files_log.append(
                                    ("edi file split into " + str(len(split_edi_list)) + " files\r\n\r\n"))
                                print("edi file split into " + str(len(split_edi_list)) + " files")
                        except Exception as process_error:
                            split_edi_list = [(input_filename, "", "")]
                            print(process_error)
                            process_files_log, process_files_error_log = \
                                record_error.do(process_files_log,
                                                process_files_error_log,
                                                "splitting edi file failed with error: " + str(
                                                    process_error), input_filename,
                                                "edi splitter", True)
                    else:
                        split_edi_list = [(input_filename, "", "")]
                    if len(split_edi_list) <= 1 and parameters_dict['split_edi']:
                        process_files_log.append("Cannot split edi file\r\n\r\n")
                        print("Cannot split edi file")
                    # Loop through list of split edi files
                    for output_send_filename, filename_prefix, filename_suffix in split_edi_list:
                        if errors is True:
                            # If there were errors, do not process any more files
                            break
                        # Build the renamed file name
                        renamed_file = "".join([
                            filename_prefix,
                            parameters_dict.get('rename_file', '').strip(),
                            '.',
                            os.path.basename(input_filename).split('.')[-1],
                            filename_suffix
                        ])

                        # If the split edi file exists
                        if os.path.exists(output_send_filename):

                            # If we are processing edi and it is valid
                            if parameters_dict['process_edi'] == "True" and valid_edi_file:
                                process_files_log.append(
                                    f"converting {output_send_filename} to {parameters_dict['convert_to_format']}\n")
                                # Build the output file name
                                output_filename = os.path.join(file_scratch_folder, renamed_file)
                                # Get the function to convert the file with
                                convert_fn = getattr(sys.modules[__name__], f'convert_to_{parameters_dict["convert_to_format"]}')
                                # Convert the file
                                convert_fn(output_send_filename, output_filename, each_upc_dict, parameters_dict, settings)
                                process_files_log.append("Success\n\n")
                                # If we are tweaking the edi file
                                if parameters_dict.get('tweak_edi', False):
                                    # Tweak the edi file
                                    output_send_filename = edi_tweaks.edi_tweak(output_send_filename, output_filename, each_upc_dict, parameters_dict, settings)

                            # If we are copying the file to the backend
                            if parameters_dict['process_backend_copy']:
                                copy_backend.do(parameters_dict, output_send_filename)
                            # If we are sending the file via ftp
                            if parameters_dict['process_backend_ftp']:
                                ftp_backend.do(parameters_dict, output_send_filename)
                            # If we are sending the file via email
                            if parameters_dict.get('process_backend_email', False) and settings['enable_email']:
                                email_backend.do(parameters_dict, settings, output_send_filename)
                        else:
                            # If the split edi file does not exist, log an error
                            errors = True
                            process_files_log, process_files_error_log = record_error.do(process_files_log,
                                                                                        process_files_error_log,
                                                                                        f"File {output_send_filename} does not exist",
                                                                                        str(output_send_filename),
                                                                                        "Output", True)
                return \
                    errors, process_original_filename, input_file_checksum, process_files_log, process_files_error_log

            index_number_list = [x[0] for x in filtered_files]

            db_updated_counter = 0

            processed_files_insert_list = []

            with concurrent.futures.ThreadPoolExecutor() as executor:
                for return_errors, original_filename, file_checksum, return_log, return_error_log in executor.map(
                        process_files, index_number_list):

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
                                       folder_total_count, db_updated_counter + 1, file_count_total,
                                       "Updating Records For: " + os.path.basename(original_filename))
                    if return_errors is False:
                        try:
                            if processed_files.count(file_name=str(original_filename),
                                                     resend_flag=True) > 0:
                                file_old_id = processed_files.find_one(file_name=str(original_filename),
                                                                       resend_flag=True)
                                processed_files_update = dict(resend_flag=False, id=file_old_id['id'])
                                processed_files.update(processed_files_update, ['id'])

                            processed_files_insert_list.append(dict(file_name=str(original_filename),
                                                                    folder_id=parameters_dict['id'],
                                                                    folder_alias=parameters_dict['alias'],
                                                                    file_checksum=file_checksum,
                                                                    sent_date_time=datetime.datetime.now(),
                                                                    copy_destination=parameters_dict[
                                                                        'copy_to_directory'] if
                                                                    parameters_dict[
                                                                        'process_backend_copy'] is True else "N/A",
                                                                    ftp_destination=parameters_dict['ftp_server'] +
                                                                    parameters_dict['ftp_folder'] if
                                                                    parameters_dict[
                                                                        'process_backend_ftp'] is True else "N/A",
                                                                    email_destination=parameters_dict['email_to'] if
                                                                    parameters_dict[
                                                                        'process_backend_email'] is True else "N/A",
                                                                    resend_flag=False))
                        except Exception as error:
                            record_error.do(run_log, folder_errors_log, str(error), str(original_filename), "Dispatch")
                            folder_errors = True
                    if return_errors is False:
                        processed_counter += 1
                        db_updated_counter += 1
                    else:
                        break
            processed_files.insert_many(processed_files_insert_list)
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
