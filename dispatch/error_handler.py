from io import StringIO
import os
import datetime
import record_error
import utils
from typing import List, Dict, Any, Optional


class ErrorLogger:
    """Handles error logging operations."""

    def __init__(self, errors_folder: str, run_log):
        self.errors_folder = errors_folder
        self.run_log = run_log
        self.folder_errors_log = StringIO()

    def log_error(self, error_message: str, filename: str, module: str):
        """
        Log an error with context.

        Args:
            error_message: Error message to log
            filename: Name of the file causing the error
            module: Name of the module where error occurred
        """
        record_error.do(
            self.run_log, self.folder_errors_log, error_message, filename, module
        )

    def log_folder_error(
        self, error_message: str, folder_name: str, module: str = "Dispatch"
    ):
        """
        Log a folder-related error.

        Args:
            error_message: Error message to log
            folder_name: Name of the folder causing the error
            module: Name of the module where error occurred
        """
        self.log_error(error_message, folder_name, module)

    def log_file_error(
        self, error_message: str, filename: str, module: str = "Dispatch"
    ):
        """
        Log a file-related error.

        Args:
            error_message: Error message to log
            filename: Name of the file causing the error
            module: Name of the module where error occurred
        """
        self.log_error(error_message, filename, module)

    def get_errors(self) -> str:
        """
        Get all logged errors.

        Returns:
            Errors as string
        """
        return self.folder_errors_log.getvalue()

    def has_errors(self) -> bool:
        """
        Check if there are any logged errors.

        Returns:
            True if there are errors, False otherwise
        """
        return len(self.folder_errors_log.getvalue()) > 0

    def close(self):
        """Close the error log."""
        self.folder_errors_log.close()


class ReportGenerator:
    """Generates error reports."""

    @staticmethod
    def generate_edi_validation_report(errors: str) -> str:
        """
        Generate EDI validation report.

        Args:
            errors: Validation errors

        Returns:
            Formatted validation report
        """
        timestamp = datetime.datetime.now().isoformat().replace(":", "-")
        report = f"EDI Validation Report - {timestamp}\r\n"
        report += "=" * 50 + "\r\n"
        report += errors
        return report

    @staticmethod
    def generate_processing_report(errors: str, version: str) -> str:
        """
        Generate processing report.

        Args:
            errors: Processing errors
            version: Program version

        Returns:
            Formatted processing report
        """
        report = f"Program Version = {version}\r\n\r\n"
        report += "Processing Errors\r\n"
        report += "=" * 30 + "\r\n"
        report += errors
        return report


class ErrorHandler:
    """Central error management system."""

    def __init__(self, errors_folder: str, run_log, run_log_directory: str):
        self.errors_folder = errors_folder
        self.run_log = run_log
        self.run_log_directory = run_log_directory
        self.logger = ErrorLogger(errors_folder, run_log)
        self.report_generator = ReportGenerator()

    def log_error(self, error_message: str, filename: str, module: str):
        """
        Log an error with context.

        Args:
            error_message: Error message to log
            filename: Name of the file causing the error
            module: Name of the module where error occurred
        """
        self.logger.log_error(error_message, filename, module)

    def log_folder_error(
        self, error_message: str, folder_name: str, module: str = "Dispatch"
    ):
        """
        Log a folder-related error.

        Args:
            error_message: Error message to log
            folder_name: Name of the folder causing the error
            module: Name of the module where error occurred
        """
        self.logger.log_folder_error(error_message, folder_name, module)

    def log_file_error(
        self, error_message: str, filename: str, module: str = "Dispatch"
    ):
        """
        Log a file-related error.

        Args:
            error_message: Error message to log
            filename: Name of the file causing the error
            module: Name of the module where error occurred
        """
        self.logger.log_file_error(error_message, filename, module)

    def write_validation_report(self, errors: str) -> str:
        """
        Write EDI validation report to file.

        Args:
            errors: Validation errors

        Returns:
            Path to the generated report file
        """
        validator_log_name = (
            f"Validator Log {datetime.datetime.now().isoformat().replace(':', '-')}.txt"
        )
        validator_log_path = os.path.join(self.run_log_directory, validator_log_name)

        with open(validator_log_path, "wb") as validator_log_file:
            validator_log_file.write(errors.encode())

        return validator_log_path

    def write_folder_errors_report(
        self, folder_name: str, folder_alias: str, version: str
    ) -> str:
        """
        Write folder errors report to file.

        Args:
            folder_name: Name of the folder with errors
            folder_alias: Alias of the folder
            version: Program version

        Returns:
            Path to the generated report file
        """
        cleaned_alias_string = ErrorHandler._clean_filename(folder_alias)
        log_name = f"{cleaned_alias_string} errors.{datetime.datetime.now().isoformat().replace(':', '-')}.txt"
        log_path = os.path.join(
            self.errors_folder, os.path.basename(folder_name), log_name
        )

        # Ensure errors directory exists
        if not os.path.exists(self.errors_folder):
            self.log_folder_error(
                "Base errors folder not found", folder_name, "Dispatch Error Logger"
            )
            os.mkdir(self.errors_folder)

        folder_errors_dir = os.path.dirname(log_path)
        if not os.path.exists(folder_errors_dir):
            self.log_folder_error(
                "Error folder not found", folder_name, "Dispatch Error Logger"
            )
            try:
                os.mkdir(folder_errors_dir)
            except IOError as e:
                self.log_folder_error(
                    f"Error creating errors folder: {str(e)}",
                    folder_name,
                    "Dispatch Error Logger",
                )
                log_path = os.path.join(self.run_log_directory, log_name)

        report_content = self.report_generator.generate_processing_report(
            self.logger.get_errors(), version
        )

        with open(log_path, "wb") as folder_errors_log_write:
            utils.do_clear_old_files(folder_errors_dir, 500)
            folder_errors_log_write.write(report_content.encode())

        return log_path

    @staticmethod
    def _clean_filename(filename: str) -> str:
        """
        Clean filename by removing invalid characters.

        Args:
            filename: Original filename

        Returns:
            Cleaned filename
        """
        return filename.replace(":", "-")

    def has_errors(self) -> bool:
        """
        Check if there are any logged errors.

        Returns:
            True if there are errors, False otherwise
        """
        return self.logger.has_errors()

    def get_errors(self) -> str:
        """
        Get all logged errors.

        Returns:
            Errors as string
        """
        return self.logger.get_errors()

    def close(self):
        """Close the error handler."""
        self.logger.close()
