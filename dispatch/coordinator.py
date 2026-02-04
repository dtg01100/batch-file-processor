import concurrent.futures
import datetime
import os
import queue
import re
import shutil
import tempfile
import threading
import time
from io import StringIO
from typing import Any, Dict, List, Optional, Tuple

import doingstuffoverlay
import record_error
import utils
from query_runner import query_runner
from edi_format_parser import EDIFormatParser
from .file_processor import FileDiscoverer, HashGenerator, FileFilter
from .edi_validator import EDIValidator
from .edi_processor import EDISplitter, EDIConverter, EDITweaker, FileNamer
from .send_manager import SendManager
from .error_handler import ErrorHandler, ErrorLogger
from .db_manager import DBManager


class ProcessingContext:
    """
    Encapsulates all processing state to replace global variables.
    This class holds all the state needed for a processing run.
    """

    def __init__(self):
        self.hash_counter = 0
        self.file_count = 0
        self.parameters_dict_list = []
        self.hash_thread_return_queue = queue.Queue()
        self.edi_validator_errors = StringIO()
        self.global_edi_validator_error_status = False
        self.upc_dict = {}

    def reset(self):
        """Reset all counters and queues."""
        self.hash_counter = 0
        self.file_count = 0
        self.hash_thread_return_queue = queue.Queue()
        self.edi_validator_errors = StringIO()
        self.global_edi_validator_error_status = False


class DispatchCoordinator:
    """
    Main coordinator for the batch file processing system.
    Orchestrates file discovery, EDI validation, EDI processing,
    file sending, and error handling.
    """

    def __init__(
        self,
        database_connection,
        folders_database,
        run_log,
        emails_table,
        run_log_directory,
        reporting,
        processed_files,
        root,
        args,
        version,
        errors_folder,
        settings,
        simple_output=None,
    ):
        """
        Initialize the DispatchCoordinator.

        Args:
            database_connection: Database connection object
            folders_database: Folders database
            run_log: Run log file
            emails_table: Emails table for reporting
            run_log_directory: Directory for run logs
            reporting: Reporting configuration
            processed_files: Processed files database
            root: Root UI element
            args: Command line arguments
            version: Program version
            errors_folder: Errors folder configuration
            settings: Application settings
            simple_output: Simple output UI element (optional)
        """
        self.database_connection = database_connection
        self.folders_database = folders_database
        self.run_log = run_log
        self.emails_table = emails_table
        self.run_log_directory = run_log_directory
        self.reporting = reporting
        self.processed_files = processed_files
        self.root = root
        self.args = args
        self.version = version
        self.errors_folder = errors_folder
        self.settings = settings
        self.simple_output = simple_output

        # Initialize components
        self.context = ProcessingContext()
        self.db_manager = DBManager(
            database_connection, processed_files, folders_database
        )
        self.error_handler = ErrorHandler(errors_folder, run_log, run_log_directory)
        self.send_manager = SendManager()
        self.edi_validator = EDIValidator()

        # Initialize UI update function
        self.update_overlay = self._create_overlay_updater()

    def _create_overlay_updater(self):
        """Create the overlay update function."""

        def update_overlay(
            overlay_text,
            dispatch_folder_count,
            folder_total,
            dispatch_file_count,
            file_total,
            footer,
        ):
            if not self.args.automatic:
                doingstuffoverlay.update_overlay(
                    parent=self.root,
                    overlay_text=overlay_text
                    + " folder "
                    + str(dispatch_folder_count)
                    + " of "
                    + str(folder_total)
                    + ","
                    + " file "
                    + str(dispatch_file_count)
                    + " of "
                    + str(file_total),
                    footer=footer,
                    overlay_height=120,
                )
            elif self.simple_output is not None:
                self.simple_output.configure(
                    text=overlay_text
                    + " folder "
                    + str(dispatch_folder_count)
                    + " of "
                    + str(folder_total)
                    + ","
                    + " file "
                    + str(dispatch_file_count)
                    + " of "
                    + str(file_total)
                )
            self.root.update()

        return update_overlay

    def process(self) -> Tuple[bool, str]:
        """
        Main processing function. Coordinates the entire batch processing workflow.

        Returns:
            Tuple of (has_errors, run_summary_string)
        """
        self.context.reset()

        # Load UPC data
        self._load_upc_data()

        # Load active folders
        self.context.parameters_dict_list = self.db_manager.get_active_folders()

        # Load processed files
        temp_processed_files_list = self.db_manager.get_processed_files()

        # Start hash thread
        hash_thread = self._create_hash_thread(temp_processed_files_list)
        hash_thread.start()

        # Process each folder
        error_counter = 0
        processed_counter = 0
        folder_count = 0
        folder_total_count = self.db_manager.get_active_folder_count()

        for parameters_dict in self.context.parameters_dict_list:
            folder_count += 1
            self.context.file_count = 0
            self.context.hash_counter = 0

            self.update_overlay(
                "processing folder...\n\n",
                folder_count,
                folder_total_count,
                self.context.file_count,
                0,
                "",
            )

            if os.path.isdir(parameters_dict["folder_name"]) is True:
                print(
                    f"processing folder {parameters_dict['folder_name']}, aliased as {parameters_dict['alias']}"
                )
                self.run_log.write(
                    f"\r\n\r\nentering folder {parameters_dict['folder_name']}, aliased as {parameters_dict['alias']}\r\n\r\n".encode()
                )

                # Get hash results
                hash_thread_return_dict = self.context.hash_thread_return_queue.get()
                files = hash_thread_return_dict["files"]
                filtered_files = hash_thread_return_dict["filtered_files"]

                # Validate folder match
                if (
                    parameters_dict["folder_name"]
                    != hash_thread_return_dict["folder_name"]
                ):
                    raise ValueError(
                        f"desync between current folder {parameters_dict['folder_name']} and current entry in hashed queue {hash_thread_return_dict['folder_name']}"
                    )

                # Process files in folder
                folder_errors = self._process_folder(
                    parameters_dict,
                    files,
                    filtered_files,
                    folder_count,
                    folder_total_count,
                )

                if folder_errors:
                    error_counter += 1
                else:
                    processed_counter += 1
            else:
                # Folder missing
                error_message = f"error: {os.path.abspath(parameters_dict['folder_name'])} is missing for {parameters_dict['alias']}"
                self.run_log.write(f"\r\n{error_message}\r\n\r\n".encode())
                print(error_message)
                error_counter += 1

        # Handle EDI validation errors
        if self.context.global_edi_validator_error_status:
            validator_log_path = self._write_validation_report()
            if self.reporting["enable_reporting"] == "True":
                self.emails_table.insert(dict(log=validator_log_path))

        # Generate summary
        print(f"{processed_counter} processed, {error_counter} errors")

        edi_validator_error_report_string = (
            ", has EDI validator errors"
            if self.context.global_edi_validator_error_status
            else ""
        )
        run_summary_string = f"{processed_counter} processed, {error_counter} errors{edi_validator_error_report_string}"

        self.run_log.write(f"\r\n\r\n{run_summary_string}\r\n\r\n".encode())

        return error_counter > 0, run_summary_string

    def _write_validation_report(self) -> str:
        """Write EDI validation report to file."""
        import datetime

        validator_log_name = (
            f"Validator Log {datetime.datetime.now().isoformat().replace(':', '-')}.txt"
        )
        validator_log_path = os.path.join(self.run_log_directory, validator_log_name)

        with open(validator_log_path, "wb") as validator_log_file:
            validator_log_file.write(
                self.context.edi_validator_errors.getvalue().encode()
            )

        self.context.edi_validator_errors.close()
        return validator_log_path

    def _load_upc_data(self):
        """Load UPC data from the database."""
        query_object = query_runner(
            self.settings["as400_username"],
            self.settings["as400_password"],
            self.settings["as400_address"],
            f"{self.settings['odbc_driver']}",
        )

        upc_qreturn = []
        for (
            itemno,
            category,
            upc1,
            upc2,
            upc3,
            upc4,
        ) in query_object.run_arbitrary_query("""
            select 
                dsanrep.anbacd,
                dsanrep.anbbcd,
                strip(dsanrep.anbgcd),
                strip(dsanrep.anbhcd),
                strip(dsanrep.anbicd),
                strip(dsanrep.anbjcd)
            from dacdata.dsanrep dsanrep
        """):
            upc_qreturn.append((int(itemno), [category, upc1, upc2, upc3, upc4]))

        self.context.upc_dict = dict(upc_qreturn)

    def _create_hash_thread(
        self, temp_processed_files_list: List[Dict[str, Any]]
    ) -> threading.Thread:
        """Create and return the hash generation thread."""

        def hash_thread_target():
            with concurrent.futures.ProcessPoolExecutor() as hash_executor:
                for counter, entry_dict in enumerate(self.context.parameters_dict_list):
                    # Discover files in folder
                    hash_files = FileDiscoverer.discover_files(
                        entry_dict["folder_name"]
                    )
                    hash_file_count_total = len(hash_files)
                    print(
                        f"Generating file hashes {counter + 1} of {len(self.context.parameters_dict_list)} ({entry_dict['folder_name']})"
                    )

                    # Get folder ID
                    try:
                        search_folder_id = entry_dict["old_id"]
                    except KeyError:
                        search_folder_id = entry_dict["id"]

                    # Get processed files for this folder
                    folder_temp_processed_files_list = [
                        f
                        for f in temp_processed_files_list
                        if f.get("folder_id") == search_folder_id
                    ]

                    # Generate match lists
                    folder_hash_dict, folder_name_dict, resend_flag_set = (
                        FileFilter.generate_match_lists(
                            folder_temp_processed_files_list
                        )
                    )

                    # Filter files
                    filtered_files = []
                    for i, file_path in enumerate(hash_files):
                        file_hash = HashGenerator.generate_file_hash(file_path)
                        if FileFilter.should_send_file(
                            file_hash, dict(folder_name_dict), resend_flag_set
                        ):
                            filtered_files.append(
                                (i, os.path.basename(file_path), file_hash)
                            )

                    # Queue results
                    self.context.hash_thread_return_queue.put(
                        dict(
                            folder_name=entry_dict["folder_name"],
                            files=hash_files,
                            file_count_total=hash_file_count_total,
                            filtered_files=filtered_files,
                        )
                    )

        return threading.Thread(target=hash_thread_target)

    def _process_folder(
        self,
        parameters_dict: Dict[str, Any],
        files: List[str],
        filtered_files: List[Tuple],
        folder_count: int,
        folder_total_count: int,
    ) -> bool:
        """
        Process a single folder.

        Args:
            parameters_dict: Folder configuration
            files: List of files in folder
            filtered_files: Files to process
            folder_count: Current folder number
            folder_total_count: Total folder count

        Returns:
            True if errors occurred, False otherwise
        """
        self.run_log.write("Checking for new files\r\n".encode())
        print("Checking for new files")

        file_count = 0
        folder_errors = False
        folder_errors_log = StringIO()

        if len(files) == 0:
            self.run_log.write("No files in directory\r\n\r\n".encode())
            print("No files in directory")
        if len(filtered_files) == 0 and len(files) > 0:
            self.run_log.write("No new files in directory\r\n\r\n".encode())
            print("No new files in directory")
        if len(filtered_files) != 0:
            self.run_log.write(f"{len(filtered_files)} found\r\n\r\n".encode())
            print(f"{len(filtered_files)} found")

        file_count_total = len(filtered_files)
        processed_files_insert_list = []

        with concurrent.futures.ThreadPoolExecutor() as executor:
            for result in executor.map(
                lambda idx: self._process_single_file(
                    idx, parameters_dict, filtered_files, folder_errors_log
                ),
                [x[0] for x in filtered_files],
            ):
                (
                    errors,
                    original_filename,
                    file_checksum,
                    return_log,
                    return_error_log,
                ) = result

                # Write logs
                self.run_log.writelines([row.encode() for row in return_log])
                if errors:
                    folder_errors_log.write(
                        str([row.encode() for row in return_error_log])
                    )
                    folder_errors = True

                # Update UI
                if not file_count == file_count_total:
                    self.update_overlay(
                        "processing folder...\n\n",
                        folder_count,
                        folder_total_count,
                        file_count,
                        file_count_total,
                        "Sending File: " + os.path.basename(original_filename),
                    )
                elif len(processed_files_insert_list) < file_count_total:
                    self.update_overlay(
                        "processing folder... (updating database records)\n\n",
                        folder_count,
                        folder_total_count,
                        len(processed_files_insert_list) + 1,
                        file_count_total,
                        "Updating Records For: " + os.path.basename(original_filename),
                    )

                if not errors:
                    processed_files_insert_list.append(
                        self.db_manager.tracker.mark_as_processed(
                            original_filename,
                            parameters_dict["id"],
                            parameters_dict["alias"],
                            file_checksum,
                            parameters_dict,
                        )
                    )

                    # Check for resend
                    if self.db_manager.tracker.is_resend(original_filename):
                        self.db_manager.tracker.clear_resend_flag(original_filename)

                    file_count += 1
                else:
                    folder_errors = True

        # Insert processed files
        self.db_manager.insert_processed_files(processed_files_insert_list)

        # Handle folder errors
        if folder_errors:
            self._write_folder_errors_report(
                parameters_dict, folder_errors_log.getvalue()
            )
            if self.reporting["enable_reporting"] == "True":
                self.emails_table.insert(
                    dict(
                        log=folder_errors_log.getvalue(),
                        folder_alias=parameters_dict["alias"],
                        folder_id=parameters_dict["id"],
                    )
                )
        else:
            # Cleanup old records
            self.db_manager.cleanup_old_records(parameters_dict["id"])
            self.db_manager.update_folder_records(parameters_dict["id"])

        folder_errors_log.close()
        return folder_errors

    def _write_folder_errors_report(self, parameters_dict: Dict[str, Any], errors: str):
        """Write folder errors report to file."""
        import datetime
        import re

        # Clean alias string
        cleaned_alias_string = re.sub("[^a-zA-Z0-9 ]", "", parameters_dict["alias"])
        folder_error_log_name_constructor = (
            cleaned_alias_string
            + " errors."
            + datetime.datetime.now().isoformat().replace(":", "-")
            + ".txt"
        )
        folder_error_log_name_full_path = os.path.join(
            self.errors_folder["errors_folder"],
            os.path.basename(parameters_dict["folder_name"]),
            folder_error_log_name_constructor,
        )

        # Ensure errors directory exists
        if not os.path.exists(self.errors_folder["errors_folder"]):
            record_error.do(
                self.run_log,
                self.run_log,
                "Base errors folder not found",
                parameters_dict["folder_name"],
                "Dispatch Error Logger",
            )
            os.mkdir(self.errors_folder["errors_folder"])

        folder_errors_dir = os.path.dirname(folder_error_log_name_full_path)
        if not os.path.exists(folder_errors_dir):
            record_error.do(
                self.run_log,
                self.run_log,
                "Error folder Not Found",
                parameters_dict["folder_name"],
                "Dispatch Error Logger",
            )
            try:
                os.mkdir(folder_errors_dir)
            except IOError:
                record_error.do(
                    self.run_log,
                    self.run_log,
                    "Error creating errors folder",
                    parameters_dict["folder_name"],
                    "Dispatch Error Logger",
                )
                folder_error_log_name_full_path = os.path.join(
                    self.run_log_directory, folder_error_log_name_constructor
                )

        with open(folder_error_log_name_full_path, "wb") as folder_errors_log_write:
            utils.do_clear_old_files(folder_errors_dir, 500)
            folder_errors_log_write.write(
                f"Program Version = {self.version}\r\n\r\n".encode()
            )
            folder_errors_log_write.write(errors.encode())

        return folder_error_log_name_full_path

    def _process_single_file(
        self,
        file_index: int,
        parameters_dict: Dict[str, Any],
        filtered_files: List[Tuple],
        folder_errors_log,
    ) -> Tuple:
        """
        Process a single file.

        Args:
            file_index: Index of the file to process
            parameters_dict: Folder configuration
            filtered_files: List of files to process
            folder_errors_log: Folder errors log

        Returns:
            Tuple of (errors, original_filename, file_checksum, process_log, error_log)
        """
        process_files_log = []
        process_files_error_log = []
        errors = False
        input_filename = None
        input_file_checksum = None

        for process_row in filtered_files:
            if process_row[0] == file_index:
                input_filename = process_row[1]
                input_file_checksum = process_row[2]

        with tempfile.TemporaryDirectory() as file_scratch_folder:
            input_filename = os.path.join(
                os.path.abspath(parameters_dict["folder_name"]), str(input_filename)
            )
            process_original_filename = input_filename
            self.context.file_count += 1

            # Validate EDI
            valid_edi_file = True
            if (
                parameters_dict["process_edi"] == "True"
                or parameters_dict["tweak_edi"]
                or parameters_dict["split_edi"]
                or parameters_dict["force_edi_validation"]
            ):
                print(input_filename)

                format_id = parameters_dict.get("edi_format", "default")
                try:
                    edi_parser = EDIFormatParser.load_format(format_id)
                except Exception:
                    edi_parser = None

                validation_result = self.edi_validator.validate_file(
                    input_filename, process_original_filename, edi_parser
                )
                if validation_result.has_errors or validation_result.has_minor_errors:
                    if validation_result.has_errors:
                        valid_edi_file = False

                    self.context.edi_validator_errors.write(
                        f"\r\nErrors for {process_original_filename}:\r\n"
                    )
                    self.context.edi_validator_errors.write(
                        validation_result.error_message
                    )
                    self.context.global_edi_validator_error_status = True

            # Process EDI
            split_edi_list = self._process_edi(
                input_filename,
                parameters_dict,
                valid_edi_file,
                file_scratch_folder,
                process_files_log,
                process_files_error_log,
            )

            # Process each EDI output file
            for (
                output_send_filename,
                filename_prefix,
                filename_suffix,
            ) in split_edi_list:
                skip_file = False
                if parameters_dict["split_edi"] and valid_edi_file:
                    if utils.detect_invoice_is_credit(output_send_filename):
                        if parameters_dict["split_edi_include_credits"] == 0:
                            skip_file = True
                    else:
                        if parameters_dict["split_edi_include_invoices"] == 0:
                            skip_file = True

                if errors:
                    break
                if not skip_file:
                    errors = self._send_file(
                        output_send_filename,
                        parameters_dict,
                        filename_prefix,
                        filename_suffix,
                        process_files_log,
                        process_files_error_log,
                        input_filename,
                        valid_edi_file,
                        file_scratch_folder,
                    )

        return (
            errors,
            process_original_filename,
            input_file_checksum,
            process_files_log,
            process_files_error_log,
        )

    def _process_edi(
        self,
        input_filename: str,
        parameters_dict: Dict[str, Any],
        valid_edi_file: bool,
        scratch_folder: str,
        process_files_log: List,
        process_files_error_log: List,
    ) -> List[Tuple]:
        """
        Process EDI file according to parameters.

        Args:
            input_filename: Path to the input file
            parameters_dict: Folder configuration
            valid_edi_file: Whether file is valid EDI
            scratch_folder: Temporary folder for processing
            process_files_log: Process log list
            process_files_error_log: Error log list

        Returns:
            List of (file_path, prefix, suffix) tuples
        """
        split_edi_list = [(input_filename, "", "")]

        if parameters_dict["split_edi"] and valid_edi_file:
            process_files_log.append(f"Splitting edi file {input_filename}...\r\n")
            print(f"Splitting edi file {input_filename}...")
            try:
                split_edi_list = EDISplitter.split_edi(
                    input_filename, scratch_folder, parameters_dict
                )
                if len(split_edi_list) > 1:
                    process_files_log.append(
                        f"edi file split into {len(split_edi_list)} files\r\n\r\n"
                    )
                    print(f"edi file split into {len(split_edi_list)} files")
            except Exception as process_error:
                split_edi_list = [(input_filename, "", "")]
                print(process_error)
                process_files_log, process_files_error_log = record_error.do(
                    process_files_log,
                    process_files_error_log,
                    f"splitting edi file failed with error: {str(process_error)}",
                    input_filename,
                    "edi splitter",
                    True,
                )

        if len(split_edi_list) <= 1 and parameters_dict["split_edi"]:
            process_files_log.append("Cannot split edi file\r\n\r\n")
            print("Cannot split edi file")

        return split_edi_list

    def _send_file(
        self,
        output_send_filename: str,
        parameters_dict: Dict[str, Any],
        filename_prefix: str,
        filename_suffix: str,
        process_files_log: List,
        process_files_error_log: List,
        input_filename: str,
        valid_edi_file: bool,
        scratch_folder: str,
    ) -> bool:
        """
        Send a file through configured backends.

        Args:
            output_send_filename: Path to the file to send
            parameters_dict: Folder configuration
            filename_prefix: Prefix for filename
            filename_suffix: Suffix for filename
            process_files_log: Process log list
            process_files_error_log: Error log list
            input_filename: Original input filename
            valid_edi_file: Whether file is valid EDI
            scratch_folder: Temporary folder for processing

        Returns:
            True if errors occurred, False otherwise
        """
        errors = False

        # Generate output filename
        rename_file = FileNamer.generate_output_filename(
            output_send_filename, parameters_dict, filename_prefix, filename_suffix
        )

        if os.path.exists(output_send_filename):
            if parameters_dict["process_edi"] != "True" and not errors:
                output_filename = os.path.join(
                    scratch_folder, os.path.basename(rename_file)
                )
                if os.path.exists(os.path.dirname(output_filename)) is False:
                    os.mkdir(os.path.dirname(output_filename))
                try:
                    shutil.copyfile(output_send_filename, output_filename)
                    output_send_filename = output_filename
                except Exception:
                    pass

            if valid_edi_file:
                if not errors:
                    output_filename = os.path.join(
                        scratch_folder, os.path.basename(rename_file)
                    )
                    if os.path.exists(os.path.dirname(output_filename)) is False:
                        os.mkdir(os.path.dirname(output_filename))
                    try:
                        # Convert EDI
                        if parameters_dict["process_edi"] == "True":
                            print(
                                f"Converting {output_send_filename} to {parameters_dict['convert_to_format']}"
                            )
                            process_files_log.append(
                                f"Converting {output_send_filename} to {parameters_dict['convert_to_format']}\r\n\r\n"
                            )
                            output_send_filename = EDIConverter.convert_edi(
                                output_send_filename,
                                output_filename,
                                self.settings,
                                parameters_dict,
                                self.context.upc_dict,
                            )
                            print("Success")
                            process_files_log.append("Success\r\n\r\n")

                        # Apply tweaks
                        if parameters_dict["tweak_edi"] is True:
                            print(f"Applying tweaks to {output_send_filename}")
                            process_files_log.append(
                                f"Applying tweaks to {output_send_filename}\r\n\r\n"
                            )
                            output_send_filename = EDITweaker.tweak_edi(
                                output_send_filename,
                                output_filename,
                                self.settings,
                                parameters_dict,
                                self.context.upc_dict,
                            )
                            print("Success")
                            process_files_log.append("Success\r\n\r\n")
                    except Exception as process_error:
                        print(str(process_error))
                        errors = True
                        process_files_log, process_files_error_log = record_error.do(
                            process_files_log,
                            process_files_error_log,
                            str(process_error),
                            str(output_send_filename),
                            "EDI Processor",
                            True,
                        )

        # Send through backends
        send_results = self.send_manager.send_file(
            output_send_filename, parameters_dict, self.settings
        )

        for result in send_results:
            if not result.success:
                errors = True
                print(result.error_message)
                process_files_log, process_files_error_log = record_error.do(
                    process_files_log,
                    process_files_error_log,
                    result.error_message,
                    str(output_send_filename),
                    result.backend_name,
                    True,
                )

        return errors


# Backward compatibility - keep the old function signature
def process(
    database_connection,
    folders_database,
    run_log,
    emails_table,
    run_log_directory,
    reporting,
    processed_files,
    root,
    args,
    version,
    errors_folder,
    settings,
    simple_output=None,
):
    """
    Main process function for backward compatibility.
    Creates a DispatchCoordinator and runs the processing.

    Args:
        Same as DispatchCoordinator.__init__

    Returns:
        Tuple of (has_errors, run_summary_string)
    """
    coordinator = DispatchCoordinator(
        database_connection=database_connection,
        folders_database=folders_database,
        run_log=run_log,
        emails_table=emails_table,
        run_log_directory=run_log_directory,
        reporting=reporting,
        processed_files=processed_files,
        root=root,
        args=args,
        version=version,
        errors_folder=errors_folder,
        settings=settings,
        simple_output=simple_output,
    )
    return coordinator.process()
