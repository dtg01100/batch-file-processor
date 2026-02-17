"""Reporting service for email batch sending and log file handling.

This module provides the ReportingService class which handles the email
reporting functionality after folder processing completes.

The class supports dependency injection for testability.
"""

import copy
import os
import time
import zipfile
from io import StringIO
from typing import Protocol, runtime_checkable, Optional, Any, Callable


@runtime_checkable
class TableProtocol(Protocol):
    """Protocol for database table operations."""
    
    def find_one(self, **kwargs) -> Optional[dict]:
        """Find a single record matching criteria."""
        ...
    
    def find(self, **kwargs) -> list[dict]:
        """Find all records matching criteria."""
        ...
    
    def all(self) -> list[dict]:
        """Get all records from the table."""
        ...
    
    def insert(self, record: dict) -> int:
        """Insert a new record."""
        ...
    
    def update(self, record: dict, keys: list) -> None:
        """Update an existing record."""
        ...
    
    def delete(self, **kwargs) -> None:
        """Delete records matching criteria."""
        ...
    
    def count(self, **kwargs) -> int:
        """Count records matching criteria."""
        ...


@runtime_checkable
class ReportingDatabaseProtocol(Protocol):
    """Protocol for database operations needed by ReportingService."""
    
    @property
    def emails_table(self) -> TableProtocol:
        """Access emails queue table."""
        ...
    
    @property
    def emails_table_batch(self) -> TableProtocol:
        """Access emails batch table."""
        ...
    
    @property
    def sent_emails_removal_queue(self) -> TableProtocol:
        """Access sent emails removal queue."""
        ...


class ReportingService:
    """Handles email reporting after folder processing.
    
    This service manages:
    - Adding run logs to email queue
    - Batching emails for sending
    - Compressing large log files
    - Handling email errors
    
    Attributes:
        MAX_EMAIL_SIZE: Maximum size in bytes for email attachments (9MB)
        MAX_BATCH_COUNT: Maximum number of attachments per batch email
    
    Example:
        >>> service = ReportingService(database)
        >>> service.send_report_emails(
        ...     settings_dict=settings,
        ...     reporting_config=reporting,
        ...     run_log_path="/path/to/logs",
        ...     start_time="2024-01-01 12:00:00",
        ...     run_summary="Processed 10 files"
        ... )
    """
    
    MAX_EMAIL_SIZE = 9000000  # 9MB
    MAX_BATCH_COUNT = 15
    
    def __init__(
        self,
        database: ReportingDatabaseProtocol,
        batch_log_sender_module: Any = None,
        print_run_log_module: Any = None,
        utils_module: Any = None,
    ):
        """Initialize the reporting service.
        
        Args:
            database: Database object implementing ReportingDatabaseProtocol
            batch_log_sender_module: Module for sending batch logs (injected for testing)
            print_run_log_module: Module for printing run logs (injected for testing)
            utils_module: Utils module with normalize_bool function (injected for testing)
        """
        self._db = database
        self._batch_log_sender = batch_log_sender_module
        self._print_run_log = print_run_log_module
        self._utils = utils_module
    
    def _normalize_bool(self, value: Any) -> bool:
        """Normalize a value to boolean.
        
        Args:
            value: Value to normalize
            
        Returns:
            Boolean representation of the value
        """
        if self._utils is not None:
            return self._utils.normalize_bool(value)
        # Fallback implementation
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return bool(value)
    
    def add_run_log_to_queue(
        self,
        run_log_path: str,
        run_log_name: str,
        enable_reporting: bool
    ) -> None:
        """Add a run log to the email queue if reporting is enabled.
        
        Args:
            run_log_path: Full path to the run log file
            run_log_name: Name of the run log for display
            enable_reporting: Whether reporting is enabled
        """
        if enable_reporting:
            self._db.emails_table.insert({
                "log": run_log_path,
                "folder_alias": run_log_name
            })
    
    def send_report_emails(
        self,
        settings_dict: dict,
        reporting_config: dict,
        run_log_path: str,
        start_time: str,
        run_summary: str,
        args: Any = None,
        root: Any = None,
        feedback_text: Any = None,
    ) -> None:
        """Send all queued report emails.
        
        This method handles:
        - Batching emails to stay under size limits
        - Compressing large log files
        - Tracking and reporting missing files
        - Sending error notifications
        
        Args:
            settings_dict: Application settings dictionary
            reporting_config: Reporting configuration dictionary
            run_log_path: Path to the log directory
            start_time: Start time string for the run
            run_summary: Summary string of the run
            args: Command line arguments (optional)
            root: Tkinter root window (optional)
            feedback_text: Feedback widget for status updates (optional)
        """
        try:
            self._db.sent_emails_removal_queue.delete()
            total_size = 0
            skipped_files = 0
            email_errors = StringIO()
            total_emails = self._db.emails_table.count()
            self._db.emails_table_batch.delete()
            emails_count = 0
            loop_count = 0
            batch_number = 1
            
            for log in self._db.emails_table.all():
                emails_count += 1
                loop_count += 1
                
                if os.path.isfile(os.path.abspath(log["log"])):
                    send_log_file = copy.deepcopy(log)
                    
                    # Compress if too large
                    if os.path.getsize(os.path.abspath(log["log"])) > self.MAX_EMAIL_SIZE:
                        send_log_file["log"] = str(
                            os.path.abspath(log["log"]) + ".zip"
                        )
                        with zipfile.ZipFile(
                            send_log_file["log"], "w"
                        ) as zip_outfile:
                            zip_outfile.write(
                                os.path.abspath(log["log"]),
                                os.path.basename(log["log"]),
                                zipfile.ZIP_DEFLATED,
                            )
                    
                    # Add size of current file to total
                    total_size += os.path.getsize(
                        os.path.abspath(send_log_file["log"])
                    )
                    self._db.emails_table_batch.insert(
                        dict(log=send_log_file["log"])
                    )
                    
                    # Send batch if size or count limit reached
                    if (
                        total_size > self.MAX_EMAIL_SIZE
                        or self._db.emails_table_batch.count() >= self.MAX_BATCH_COUNT
                    ):
                        self._send_batch(
                            settings_dict=settings_dict,
                            reporting_config=reporting_config,
                            start_time=start_time,
                            args=args,
                            root=root,
                            batch_number=batch_number,
                            emails_count=emails_count,
                            total_emails=total_emails,
                            feedback_text=feedback_text,
                            run_summary=run_summary,
                        )
                        self._db.emails_table_batch.delete()
                        total_size = 0
                        loop_count = 0
                        batch_number += 1
                else:
                    email_errors.write("\r\n" + log["log"] + " missing, skipping")
                    email_errors.write(
                        "\r\n file was expected to be at "
                        + log["log"]
                        + " on the sending computer"
                    )
                    skipped_files += 1
                    self._db.sent_emails_removal_queue.insert(log)
            
            # Send remaining batch
            self._send_batch(
                settings_dict=settings_dict,
                reporting_config=reporting_config,
                start_time=start_time,
                args=args,
                root=root,
                batch_number=batch_number,
                emails_count=emails_count,
                total_emails=total_emails,
                feedback_text=feedback_text,
                run_summary=run_summary,
            )
            self._db.emails_table_batch.delete()
            
            # Clean up sent emails
            for line in self._db.sent_emails_removal_queue.all():
                self._db.emails_table.delete(log=str(line["log"]))
            self._db.sent_emails_removal_queue.delete()
            
            # Handle skipped files
            if skipped_files > 0:
                self._handle_skipped_files(
                    skipped_files=skipped_files,
                    email_errors=email_errors,
                    run_log_path=run_log_path,
                    settings_dict=settings_dict,
                    reporting_config=reporting_config,
                    start_time=start_time,
                    args=args,
                    root=root,
                    batch_number=batch_number,
                    emails_count=emails_count,
                    total_emails=total_emails,
                    feedback_text=feedback_text,
                )
                
        except Exception as dispatch_error:
            self._db.emails_table_batch.delete()
            self._handle_email_error(
                error=dispatch_error,
                run_log_path=run_log_path,
                reporting_config=reporting_config,
            )
    
    def _send_batch(
        self,
        settings_dict: dict,
        reporting_config: dict,
        start_time: str,
        args: Any,
        root: Any,
        batch_number: int,
        emails_count: int,
        total_emails: int,
        feedback_text: Any,
        run_summary: str,
    ) -> None:
        """Send a batch of emails.
        
        Args:
            settings_dict: Application settings dictionary
            reporting_config: Reporting configuration dictionary
            start_time: Start time string for the run
            args: Command line arguments
            root: Tkinter root window
            batch_number: Current batch number
            emails_count: Current email count
            total_emails: Total emails to send
            feedback_text: Feedback widget for status updates
            run_summary: Summary string of the run
        """
        if self._batch_log_sender is not None:
            self._batch_log_sender.do(
                settings_dict,
                reporting_config,
                self._db.emails_table_batch,
                self._db.sent_emails_removal_queue,
                start_time,
                args,
                root,
                batch_number,
                emails_count,
                total_emails,
                feedback_text,
                run_summary,
            )
    
    def _handle_skipped_files(
        self,
        skipped_files: int,
        email_errors: StringIO,
        run_log_path: str,
        settings_dict: dict,
        reporting_config: dict,
        start_time: str,
        args: Any,
        root: Any,
        batch_number: int,
        emails_count: int,
        total_emails: int,
        feedback_text: Any,
    ) -> None:
        """Handle skipped files by creating and sending an error log.
        
        Args:
            skipped_files: Number of skipped files
            email_errors: StringIO with error messages
            run_log_path: Path to log directory
            settings_dict: Application settings dictionary
            reporting_config: Reporting configuration dictionary
            start_time: Start time string
            args: Command line arguments
            root: Tkinter root window
            batch_number: Current batch number
            emails_count: Current email count
            total_emails: Total emails
            feedback_text: Feedback widget
        """
        batch_number += 1
        emails_count += 1
        email_errors.write(
            "\r\n\r\n" + str(skipped_files) + " emails skipped"
        )
        
        email_errors_log_name = (
            "Email Errors Log "
            + str(time.ctime()).replace(":", "-")
            + ".txt"
        )
        email_errors_log_path = os.path.join(
            run_log_path, email_errors_log_name
        )
        
        with open(
            email_errors_log_path, "w", encoding="utf-8"
        ) as reporting_emails_errors:
            reporting_emails_errors.write(email_errors.getvalue())
        
        self._db.emails_table_batch.insert(
            dict(
                log=email_errors_log_path,
                folder_alias=email_errors_log_name,
            )
        )
        
        try:
            self._send_batch(
                settings_dict=settings_dict,
                reporting_config=reporting_config,
                start_time=start_time,
                args=args,
                root=root,
                batch_number=batch_number,
                emails_count=emails_count,
                total_emails=total_emails,
                feedback_text=feedback_text,
                run_summary="Error, cannot send all logs. ",
            )
            self._db.emails_table_batch.delete()
        except Exception as email_send_error:
            print(email_send_error)
            self._db.emails_table_batch.delete()
    
    def _handle_email_error(
        self,
        error: Exception,
        run_log_path: str,
        reporting_config: dict,
    ) -> None:
        """Handle email sending errors.
        
        Args:
            error: The exception that occurred
            run_log_path: Path to log directory
            reporting_config: Reporting configuration dictionary
        """
        # Find the run log file
        run_log_file = None
        for f in os.listdir(run_log_path):
            if f.startswith("Run Log"):
                run_log_file = os.path.join(run_log_path, f)
                break
        
        if run_log_file:
            with open(run_log_file, "a", encoding="utf-8") as run_log:
                if self._normalize_bool(reporting_config.get("report_printing_fallback")):
                    print(
                        "Emailing report log failed with error: "
                        + str(error)
                        + ", printing file\r\n"
                    )
                    run_log.write(
                        "Emailing report log failed with error: "
                        + str(error)
                        + ", printing file\r\n"
                    )
                else:
                    print(
                        "Emailing report log failed with error: "
                        + str(error)
                        + ", printing disabled, stopping\r\n"
                    )
                    run_log.write(
                        "Emailing report log failed with error: "
                        + str(error)
                        + ", printing disabled, stopping\r\n"
                    )
        
        if self._normalize_bool(reporting_config.get("report_printing_fallback")):
            if run_log_file and self._print_run_log is not None:
                try:
                    with open(run_log_file, "r", encoding="utf-8") as run_log:
                        self._print_run_log.do(run_log)
                except Exception as printing_error:
                    print(
                        "printing error log failed with error: "
                        + str(printing_error)
                        + "\r\n"
                    )
                    if run_log_file:
                        with open(run_log_file, "a", encoding="utf-8") as run_log:
                            run_log.write(
                                "Printing error log failed with error: "
                                + str(printing_error)
                                + "\r\n"
                            )
