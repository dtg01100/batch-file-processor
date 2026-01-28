"""
Processing operations module for interface.py refactoring.

This module handles directory processing operations including backup management,
log setup, dispatch orchestration, and email report batching.
Refactored from interface.py (lines 2651-2950).

Usage:
    from interface.operations.processing import ProcessingOrchestrator
    orchestrator = ProcessingOrchestrator(db_manager)
    result = orchestrator.process_all(auto_mode=False)
"""

import copy
import datetime
import os
import sys
import time
import traceback
import zipfile
from dataclasses import dataclass
from io import StringIO
from typing import Any, Dict, List, Optional, Tuple

# Add parent directory to path for imports from root level modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import backup_increment
import batch_log_sender
import dispatch
import print_run_log
import utils

from interface.database.database_manager import DatabaseManager


@dataclass
class DispatchResult:
    """Result from the dispatch process.
    
    Attributes:
        error: Boolean indicating if an error occurred
        summary: Summary string of the processing run
    """
    error: bool
    summary: str


@dataclass
class ProcessingResult:
    """Result from the processing orchestrator.
    
    Attributes:
        success: Boolean indicating if processing completed successfully
        backup_path: Path to backup if created, None otherwise
        log_path: Path to the run log file
        error: Error message if processing failed, None otherwise
    """
    success: bool
    backup_path: Optional[str] = None
    log_path: Optional[str] = None
    error: Optional[str] = None


class ProcessingOrchestrator:
    """
    Orchestrator for batch directory processing operations.
    
    This class handles the complete processing workflow:
    1. Backup management
    2. Log directory setup
    3. Dispatch orchestration
    4. Email report batching/sending
    5. Error handling with fallback printing
    
    Attributes:
        db_manager: DatabaseManager instance for database operations
        database_path: Path to the database file
        args: Command-line arguments namespace
        version: Application version string
    """
    
    FALLBACK_ERROR_LOG = "C:\\Users\\Public\\batch_error_log.txt"
    MAX_EMAIL_BATCH_SIZE = 9000000  # 9MB
    MAX_EMAILS_PER_BATCH = 15
    
    def __init__(
        self,
        db_manager: DatabaseManager,
        database_path: str,
        args: Any,
        version: str
    ) -> None:
        """Initialize the ProcessingOrchestrator.
        
        Args:
            db_manager: DatabaseManager instance
            database_path: Path to the SQLite database file
            args: Parsed command-line arguments
            version: Application version string
        """
        self.db_manager = db_manager
        self.database_path = database_path
        self.args = args
        self.version = version
        self.errors_directory = None
        self.logs_directory = None
    
    def process_all(self, auto_mode: bool = False) -> ProcessingResult:
        """Main entry point for processing all active directories.
        
        Args:
            auto_mode: If True, running in automatic mode (no GUI)
            
        Returns:
            ProcessingResult with success status and details
        """
        original_folder = os.getcwd()
        
        try:
            # Step 1: Run backup if needed
            backup_path = self._run_backup()
            
            # Step 2: Setup logging
            log_path = self._setup_logging()
            if log_path is None:
                return ProcessingResult(
                    success=False,
                    error="Failed to setup logging directory"
                )
            
            # Step 3: Run dispatch
            dispatch_result = self._run_dispatch(log_path)
            
            # Step 4: Send email report
            if dispatch_result is not None:
                self._send_email_report(dispatch_result, log_path)
            
            return ProcessingResult(
                success=True,
                backup_path=backup_path,
                log_path=log_path
            )
            
        except Exception as error:
            error_msg = f"Processing failed: {str(error)}"
            self._handle_error(error)
            return ProcessingResult(
                success=False,
                error=error_msg
            )
        finally:
            os.chdir(original_folder)
    
    def _run_backup(self) -> Optional[str]:
        """Step 1: Manage backup operations.
        
        Creates a backup if the backup counter has reached its maximum.
        
        Returns:
            Path to backup file if created, None otherwise
        """
        settings_dict = self.db_manager.settings.find_one(id=1)
        
        if (
            settings_dict["enable_interval_backups"]
            and settings_dict["backup_counter"]
            >= settings_dict["backup_counter_maximum"]
        ):
            backup_increment.do_backup(self.database_path)
            settings_dict["backup_counter"] = 0
        
        settings_dict["backup_counter"] += 1
        self.db_manager.settings.update(settings_dict, ["id"])
        
        return None  # backup_increment.do_backup returns None in original code
    
    def _setup_logging(self) -> Optional[str]:
        """Step 2: Setup logging directory and create run log.
        
        Returns:
            Path to the run log file, or None if setup failed
        """
        settings_dict = self.db_manager.settings.find_one(id=1)
        reporting = self.db_manager.oversight_and_defaults.find_one(id=1)
        
        log_folder_creation_error = False
        start_time = str(datetime.datetime.now())
        
        # Get logs directory from settings
        logs_dir = self.logs_directory or reporting["logs_directory"]
        
        # Check for configured logs directory, and create it if necessary
        if not os.path.isdir(logs_dir):
            try:
                os.mkdir(logs_dir)
            except IOError:
                log_folder_creation_error = True
        
        # If logs directory is not writable, handle the error
        if self._check_logs_directory(logs_dir) is False or log_folder_creation_error:
            if not self.args.automatic:
                # In GUI mode, user would be prompted here
                # For now, return None to indicate failure
                return None
            else:
                # In automatic mode, log and exit
                try:
                    print(
                        "can't write into logs directory. in automatic mode, "
                        "so no prompt. this error will be stored in critical log"
                    )
                    with open("critical_error.log", "a", encoding="utf-8") as log:
                        log.write(
                            f"{datetime.datetime.now()}can't write into logs directory. "
                            "in automatic mode, so no prompt\r\n"
                        )
                    return None
                except IOError:
                    print("Can't write critical error log, aborting")
                    return None
        
        # Create run log file
        run_log_name = f"Run Log {time.ctime().replace(':', '-')}.txt"
        run_log_path = os.path.join(logs_dir, run_log_name)
        
        return run_log_path
    
    def _check_logs_directory(self, logs_dir: str) -> bool:
        """Check if logs directory is writable.
        
        Args:
            logs_dir: Path to logs directory
            
        Returns:
            True if writable, False otherwise
        """
        try:
            test_file = os.path.join(logs_dir, "test_log_file")
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("teststring")
            os.remove(test_file)
            return True
        except IOError:
            return False
    
    def _run_dispatch(self, run_log_path: str) -> Optional[DispatchResult]:
        """Step 3: Run dispatch to process active folders.
        
        Args:
            run_log_path: Path to the run log file
            
        Returns:
            DispatchResult or None if dispatch failed
        """
        settings_dict = self.db_manager.settings.find_one(id=1)
        reporting = self.db_manager.oversight_and_defaults.find_one(id=1)
        
        start_time = str(datetime.datetime.now())
        run_summary_string = ""
        
        with open(run_log_path, "wb") as run_log:
            utils.do_clear_old_files(reporting["logs_directory"], 1000)
            run_log.write(f"Batch File Sender Version {self.version}\r\n".encode())
            run_log.write(f"starting run at {time.ctime()}\r\n".encode())
            
            # Add run log to email queue if reporting is enabled
            if reporting["enable_reporting"] == "True":
                self.db_manager.emails_table.insert(
                    {"log": run_log_path, "folder_alias": os.path.basename(run_log_path)}
                )
            
            # Call dispatch module to process active folders
            try:
                run_error_bool, run_summary_string = dispatch.process(
                    self.db_manager.database_connection,
                    self.db_manager.folders_table,
                    run_log,
                    self.db_manager.emails_table,
                    reporting["logs_directory"],
                    reporting,
                    self.db_manager.processed_files,
                    None,  # root - not needed in operations module
                    self.args,
                    self.version,
                    self.errors_directory,
                    settings_dict,
                    None,  # simple_output - not needed in operations module
                )
                
                return DispatchResult(error=run_error_bool, summary=run_summary_string)
                
            except Exception as dispatch_error:
                # If processing runs into a serious error, report and log
                error_msg = (
                    f"Run failed, check your configuration \r\n"
                    f"Error from dispatch module is: \r\n{str(dispatch_error)}\r\n"
                )
                print(error_msg)
                traceback.print_exc()
                
                run_log.write(error_msg.encode())
                run_log.write(traceback.format_exc().encode())
                
                return DispatchResult(error=True, summary=error_msg)
    
    def _send_email_report(
        self,
        dispatch_result: DispatchResult,
        run_log_path: str
    ) -> bool:
        """Step 4: Send email reports with batched log files.
        
        Args:
            dispatch_result: Result from the dispatch process
            run_log_path: Path to the run log file
            
        Returns:
            True if email sending completed successfully, False otherwise
        """
        settings_dict = self.db_manager.settings.find_one(id=1)
        reporting = self.db_manager.oversight_and_defaults.find_one(id=1)
        start_time = str(datetime.datetime.now())
        
        if reporting["enable_reporting"] != "True":
            return True
        
        try:
            self.db_manager.sent_emails_removal_queue.delete()
            total_size = 0
            skipped_files = 0
            email_errors = StringIO()
            total_emails = self.db_manager.emails_table.count()
            self.db_manager.emails_table_batch.delete()
            emails_count = 0
            loop_count = 0
            batch_number = 1
            
            for log in self.db_manager.emails_table.all():
                emails_count += 1
                loop_count += 1
                
                if os.path.isfile(os.path.abspath(log["log"])):
                    send_log_file = copy.deepcopy(log)
                    
                    # Zip files larger than 9MB
                    if os.path.getsize(os.path.abspath(log["log"])) > self.MAX_EMAIL_BATCH_SIZE:
                        zip_path = os.path.abspath(log["log"]) + ".zip"
                        with zipfile.ZipFile(zip_path, "w") as zip_outfile:
                            zip_outfile.write(
                                os.path.abspath(log["log"]),
                                os.path.basename(log["log"]),
                                zipfile.ZIP_DEFLATED,
                            )
                        send_log_file["log"] = zip_path
                    
                    # Add size of current file to total
                    total_size += os.path.getsize(os.path.abspath(send_log_file["log"]))
                    self.db_manager.emails_table_batch.insert(
                        dict(log=send_log_file["log"])
                    )
                    
                    # If the total size is more than 9mb, send that set and reset
                    if (
                        total_size > self.MAX_EMAIL_BATCH_SIZE
                        or self.db_manager.emails_table_batch.count() >= self.MAX_EMAILS_PER_BATCH
                    ):
                        self._send_email_batch(
                            settings_dict, reporting, start_time,
                            batch_number, emails_count, total_emails,
                            dispatch_result.summary
                        )
                        self.db_manager.emails_table_batch.delete()
                        total_size = 0
                        loop_count = 0
                        batch_number += 1
                else:
                    email_errors.write(f"\r\n{log['log']} missing, skipping")
                    email_errors.write(
                        f"\r\n file was expected to be at {log['log']} "
                        "on the sending computer"
                    )
                    skipped_files += 1
                    self.db_manager.sent_emails_removal_queue.insert(log)
            
            # Send final batch
            self._send_email_batch(
                settings_dict, reporting, start_time,
                batch_number, emails_count, total_emails,
                dispatch_result.summary
            )
            self.db_manager.emails_table_batch.delete()
            
            # Clean up sent emails
            for line in self.db_manager.sent_emails_removal_queue.all():
                self.db_manager.emails_table.delete(log=str(line["log"]))
            self.db_manager.sent_emails_removal_queue.delete()
            
            # Log any skipped files
            if skipped_files > 0:
                self._log_skipped_emails(
                    email_errors, skipped_files, reporting["logs_directory"],
                    batch_number, emails_count, total_emails,
                    settings_dict, reporting, start_time
                )
            
            return True
            
        except Exception as email_error:
            print(email_error)
            self._handle_email_error(email_error, run_log_path, reporting)
            return False
    
    def _send_email_batch(
        self,
        settings_dict: Dict[str, Any],
        reporting: Dict[str, Any],
        start_time: str,
        batch_number: int,
        emails_count: int,
        total_emails: int,
        run_summary: str
    ) -> None:
        """Send a batch of email logs.
        
        Args:
            settings_dict: Application settings
            reporting: Reporting configuration
            start_time: Start time of the run
            batch_number: Current batch number
            emails_count: Total emails sent so far
            total_emails: Total emails to send
            run_summary: Summary string from dispatch
        """
        batch_log_sender.do(
            settings_dict,
            reporting,
            self.db_manager.emails_table_batch,
            self.db_manager.sent_emails_removal_queue,
            start_time,
            self.args,
            None,  # root - not needed in operations module
            batch_number,
            emails_count,
            total_emails,
            None,  # feedback_text - not needed in operations module
            run_summary,
        )
    
    def _log_skipped_emails(
        self,
        email_errors: StringIO,
        skipped_files: int,
        logs_dir: str,
        batch_number: int,
        emails_count: int,
        total_emails: int,
        settings_dict: Dict[str, Any],
        reporting: Dict[str, Any],
        start_time: str
    ) -> None:
        """Log and send notification about skipped emails.
        
        Args:
            email_errors: StringIO containing error messages
            skipped_files: Number of skipped files
            logs_dir: Logs directory path
            batch_number: Current batch number
            emails_count: Total emails count
            total_emails: Total emails to send
            settings_dict: Application settings
            reporting: Reporting configuration
            start_time: Start time of the run
        """
        batch_number += 1
        emails_count += 1
        email_errors.write(f"\r\n\r\n{skipped_files} emails skipped")
        
        errors_log_name = f"Email Errors Log {time.ctime().replace(':', '-')}.txt"
        errors_log_path = os.path.join(logs_dir, errors_log_name)
        
        with open(errors_log_path, "w", encoding="utf-8") as errors_log:
            errors_log.write(email_errors.getvalue())
        
        self.db_manager.emails_table_batch.insert(
            dict(log=errors_log_path, folder_alias=errors_log_name)
        )
        
        try:
            batch_log_sender.do(
                settings_dict,
                reporting,
                self.db_manager.emails_table,
                self.db_manager.sent_emails_removal_queue,
                start_time,
                self.args,
                None,
                batch_number,
                emails_count,
                total_emails,
                None,
                "Error, cannot send all logs. ",
            )
            self.db_manager.emails_table_batch.delete()
        except Exception as email_send_error:
            print(email_send_error)
            self.db_manager.emails_table_batch.delete()
    
    def _handle_email_error(
        self,
        error: Exception,
        run_log_path: str,
        reporting: Dict[str, Any]
    ) -> None:
        """Handle email sending errors with fallback to printing.
        
        Args:
            error: The exception that occurred
            run_log_path: Path to the run log file
            reporting: Reporting configuration
        """
        self.db_manager.emails_table_batch.delete()
        
        try:
            with open(run_log_path, "a", encoding="utf-8") as run_log:
                if reporting["report_printing_fallback"] == "True":
                    print(
                        f"Emailing report log failed with error: {str(error)}, "
                        "printing file\r\n"
                    )
                    run_log.write(
                        f"Emailing report log failed with error: {str(error)}, "
                        "printing file\r\n"
                    )
                else:
                    print(
                        f"Emailing report log failed with error: {str(error)}, "
                        "printing disabled, stopping\r\n"
                    )
                    run_log.write(
                        f"Emailing report log failed with error: {str(error)}, "
                        "printing disabled, stopping\r\n"
                    )
            
            # If printing fallback is enabled, print the run log
            if reporting["report_printing_fallback"] == "True":
                try:
                    with open(run_log_path, "r", encoding="utf-8") as run_log_file:
                        print_run_log.do(run_log_file)
                except Exception as printing_error:
                    print(f"printing error log failed with error: {str(printing_error)}\r\n")
                    with open(run_log_path, "a", encoding="utf-8") as run_log:
                        run_log.write(
                            f"Printing error log failed with error: {str(printing_error)}\r\n"
                        )
        except IOError:
            # Last resort: write to fallback location
            self._handle_error(error)
    
    def _handle_error(self, error: Exception) -> None:
        """Step 5: Error handling with fallback printing.
        
        Args:
            error: The exception that occurred
        """
        error_msg = str(error)
        print(error_msg)
        
        try:
            with open("critical_error.log", "a", encoding="utf-8") as error_log:
                error_log.write(
                    f"{datetime.datetime.now()}Error: {error_msg}\r\n"
                )
        except IOError:
            # Last resort: try to write to public directory
            try:
                with open(self.FALLBACK_ERROR_LOG, "a", encoding="utf-8") as fallback_log:
                    fallback_log.write(
                        f"{datetime.datetime.now()}Error: {error_msg}\r\n"
                    )
            except IOError:
                print(f"Failed to write to error log: {error_msg}")


def automatic_process_directories(
    db_manager: DatabaseManager,
    args: Any,
    version: str
) -> None:
    """Process directories automatically without GUI.
    
    This function is called when the application runs in automatic mode.
    
    Args:
        db_manager: Database manager instance.
        args: Parsed command-line arguments.
        version: Application version string.
    """
    database_path = db_manager._database_path  # Access protected path for backup
    
    if db_manager.folders_table.count(folder_is_active="True") > 0:
        print("batch processing configured directories")
        try:
            orchestrator = ProcessingOrchestrator(db_manager, database_path, args, version)
            result = orchestrator.process_all(auto_mode=True)
            
            if not result.success:
                print(f"Processing failed: {result.error}")
                with open("critical_error.log", "a", encoding="utf-8") as critical_log:
                    critical_log.write(
                        f"{datetime.datetime.now()}Processing failed: {result.error}\r\n"
                    )
            else:
                print("batch processing complete")
        except Exception as automatic_process_error:
            print(str(automatic_process_error))
            with open("critical_error.log", "a", encoding="utf-8") as critical_log:
                critical_log.write(
                    f"{datetime.datetime.now()}{str(automatic_process_error)}\r\n"
                )
    else:
        print("Error, No Active Folders")
    
    db_manager.close()
    raise SystemExit
