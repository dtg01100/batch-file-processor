from io import StringIO
import mtc_edi_validator
from typing import Tuple, Optional


class ValidationResult:
    """Encapsulates the results of EDI validation."""

    def __init__(
        self, has_errors: bool, error_message: str = "", has_minor_errors: bool = False
    ):
        self.has_errors = has_errors
        self.error_message = error_message
        self.has_minor_errors = has_minor_errors


class EDIValidator:
    """Validates EDI files using MTC validator."""

    def __init__(self):
        self.errors = StringIO()
        self.has_errors = False

    def validate_file(
        self, input_file: str, file_name: str, parser=None
    ) -> ValidationResult:
        """
        Validate an EDI file.

        Args:
            input_file: Path to the EDI file
            file_name: Name of the file for reporting purposes
            parser: Optional EDI format parser

        Returns:
            ValidationResult object containing validation status
        """
        try:
            edi_validator_output, edi_validator_error_status, minor_edi_errors = (
                mtc_edi_validator.report_edi_issues(input_file, parser)
            )

            if minor_edi_errors or (
                edi_validator_error_status and True
            ):  # reporting['report_edi_errors']
                self.errors.write("\r\nErrors for " + file_name + ":\r\n")
                self.errors.write(edi_validator_output.getvalue())
                edi_validator_output.close()
                self.has_errors = True

            return ValidationResult(
                has_errors=edi_validator_error_status,
                error_message=edi_validator_output.getvalue()
                if edi_validator_error_status
                else "",
                has_minor_errors=minor_edi_errors,
            )

        except Exception as e:
            error_msg = f"Error validating file: {str(e)}"
            self.errors.write(f"\r\nErrors for {file_name}:\r\n{error_msg}\r\n")
            self.has_errors = True
            return ValidationResult(has_errors=True, error_message=error_msg)

    def get_validation_report(self) -> str:
        """
        Get the complete validation report.

        Returns:
            Validation report as string
        """
        return self.errors.getvalue()

    def close(self):
        """Close the validation report file."""
        self.errors.close()
