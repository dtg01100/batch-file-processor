"""Folder settings validation logic extracted from EditDialog.

This module provides validation logic for folder settings, extracted
from the EditDialog class to enable comprehensive unit testing.
"""

from typing import List, Dict, Optional, Tuple, Any, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum
import re

from interface.models.folder_configuration import (
    FolderConfiguration,
    FTPConfiguration,
    EmailConfiguration,
    CopyConfiguration,
    EDIConfiguration,
)
from interface.services.ftp_service import FTPServiceProtocol, FTPConnectionResult

if TYPE_CHECKING:
    from interface.operations.folder_data_extractor import ExtractedDialogFields


@dataclass
class ValidationError:
    """Structured validation error."""
    field: str
    message: str
    severity: str = "error"  # "error", "warning"


class ValidationResult:
    """Result of validation operation."""

    def __init__(self, is_valid: bool = True):
        self.is_valid = is_valid
        self.errors: List[ValidationError] = []
        self.warnings: List[ValidationError] = []

    def add_error(self, field: str, message: str):
        """Add an error to the result."""
        self.errors.append(ValidationError(field=field, message=message))
        self.is_valid = False

    def add_warning(self, field: str, message: str):
        """Add a warning to the result."""
        self.warnings.append(ValidationError(field=field, message=message))

    def get_all_messages(self) -> List[str]:
        """Get all error and warning messages."""
        return [e.message for e in self.errors + self.warnings]


class FolderSettingsValidator:
    """
    Validates folder settings with support for dependency injection.

    This class extracts validation logic from EditDialog to enable
    comprehensive unit testing.
    """

    def __init__(
        self,
        ftp_service: Optional[FTPServiceProtocol] = None,
        existing_aliases: Optional[List[str]] = None
    ):
        """
        Initialize validator with optional dependencies.

        Args:
            ftp_service: Optional FTP service for connection testing
            existing_aliases: List of existing folder aliases for uniqueness check
        """
        self.ftp_service = ftp_service
        self.existing_aliases = existing_aliases or []

    def validate_ftp_settings(
        self,
        server: str,
        port: str,
        folder: str,
        username: str,
        password: str,
        enabled: bool
    ) -> ValidationResult:
        """
        Validate FTP settings.

        Args:
            server: FTP server field value
            port: FTP port field value
            folder: FTP folder field value
            username: FTP username field value
            password: FTP password field value
            enabled: Whether FTP backend is enabled

        Returns:
            ValidationResult with any validation errors
        """
        result = ValidationResult()

        if not enabled:
            return result

        # Required field checks
        if not server:
            result.add_error("ftp_server", "FTP Server Field Is Required")

        if not port:
            result.add_error("ftp_port", "FTP Port Field Is Required")

        if not folder:
            result.add_error("ftp_folder", "FTP Folder Field Is Required")
        elif not folder.endswith("/"):
            result.add_error("ftp_folder", "FTP Folder Path Needs To End In /")

        if not username:
            result.add_error("ftp_username", "FTP Username Field Is Required")

        if not password:
            result.add_error("ftp_password", "FTP Password Field Is Required")

        # Port validation
        try:
            port_int = int(port)
            if not (1 <= port_int <= 65535):
                result.add_error("ftp_port", "FTP Port Field Needs To Be A Valid Port Number")
        except ValueError:
            result.add_error("ftp_port", "FTP Port Field Needs To Be A Number")

        # FTP connection test (if all fields valid and service available)
        if result.is_valid and self.ftp_service:
            conn_result = self.ftp_service.test_connection(
                server=server,
                port=int(port),
                username=username,
                password=password,
                folder=folder
            )
            if not conn_result.success:
                error_msg = conn_result.error_message or "FTP connection failed"
                result.add_error("ftp_connection", error_msg)

        return result

    def validate_email_settings(
        self,
        recipients: str,
        enabled: bool
    ) -> ValidationResult:
        """
        Validate email settings.

        Args:
            recipients: Email recipients field value
            enabled: Whether email backend is enabled

        Returns:
            ValidationResult with any validation errors
        """
        result = ValidationResult()

        if not enabled:
            return result

        if not recipients:
            result.add_error("email_recipient", "Email Destination Address Field Is Required")
            return result

        # Validate each recipient
        emails = recipients.split(", ")
        for email in emails:
            if not self._validate_email(email):
                result.add_error("email_recipient", f"Invalid Email Destination Address: {email}")

        return result

    def _validate_email(self, email: str) -> bool:
        """Basic email validation."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def validate_copy_settings(
        self,
        destination: str,
        enabled: bool
    ) -> ValidationResult:
        """
        Validate copy backend settings.

        Args:
            destination: Copy destination directory
            enabled: Whether copy backend is enabled

        Returns:
            ValidationResult with any validation errors
        """
        result = ValidationResult()

        if not enabled:
            return result

        if not destination:
            result.add_error("copy_destination", "Copy Backend Destination Is Currently Unset")

        return result

    def validate_alias(
        self,
        alias: str,
        folder_name: str,
        current_alias: Optional[str] = None
    ) -> ValidationResult:
        """
        Validate folder alias.

        Args:
            alias: Proposed alias value
            folder_name: Folder name (template check)
            current_alias: Current alias if editing existing

        Returns:
            ValidationResult with any validation errors
        """
        result = ValidationResult()

        if folder_name == "template":
            return result

        # Check length
        if len(alias) > 50:
            result.add_error("alias", "Alias Too Long")

        # Check uniqueness (exclude current alias if editing)
        if alias in self.existing_aliases:
            if alias != current_alias:
                result.add_error("alias", "Folder Alias Already In Use")

        return result

    def validate_invoice_date_offset(self, offset: int) -> ValidationResult:
        """
        Validate invoice date offset.

        Args:
            offset: Invoice date offset value

        Returns:
            ValidationResult with any validation errors
        """
        result = ValidationResult()

        if offset not in range(-14, 15):
            result.add_error("invoice_date_offset", "Invoice date offset not in valid range")

        return result

    def validate_a_record_padding(
        self,
        padding_text: str,
        padding_length: int,
        enabled: bool,
        convert_format: Optional[str] = None
    ) -> ValidationResult:
        """
        Validate A-record padding settings.

        Args:
            padding_text: A-record padding text
            padding_length: Maximum padding length
            enabled: Whether padding is enabled
            convert_format: Current convert format

        Returns:
            ValidationResult with any validation errors
        """
        result = ValidationResult()

        if not enabled:
            return result

        if len(padding_text) > padding_length:
            result.add_error(
                "a_record_padding",
                f'"A" Record Padding Needs To Be At Most {padding_length} Characters'
            )

        if len(padding_text) != 6:
            result.add_error("a_record_padding", '"A" Record Padding Needs To Be Six Characters')

        # ScannerWare specific
        if convert_format == "ScannerWare":
            if not enabled:
                result.add_error(
                    "a_record_padding",
                    '"A" Record Padding Needs To Be Enabled For ScannerWare Backend'
                )

        return result

    def validate_upc_override(
        self,
        enabled: bool,
        category_filter: str
    ) -> ValidationResult:
        """
        Validate UPC override settings.

        Args:
            enabled: Whether UPC override is enabled
            category_filter: Category filter string

        Returns:
            ValidationResult with any validation errors
        """
        result = ValidationResult()

        if not enabled:
            return result

        if not category_filter:
            result.add_error(
                "upc_category_filter",
                "Override UPC Category Filter Is Required"
            )
            return result

        # Validate each category
        for category in category_filter.split(","):
            if category != "ALL":
                try:
                    cat_int = int(category)
                    if cat_int not in range(1, 100):
                        result.add_error(
                            "upc_category_filter",
                            "Override UPC Category Filter Is Invalid"
                        )
                except ValueError:
                    result.add_error(
                        "upc_category_filter",
                        "Override UPC Category Filter Is Invalid"
                    )

        return result

    def validate_backend_specific(
        self,
        convert_format: str,
        division_id: Optional[str] = None
    ) -> ValidationResult:
        """
        Validate backend-specific settings.

        Args:
            convert_format: Current convert format
            division_id: Fintech division ID (if applicable)

        Returns:
            ValidationResult with any validation errors
        """
        result = ValidationResult()

        if convert_format == "fintech":
            if division_id:
                try:
                    int(division_id)
                except ValueError:
                    result.add_error(
                        "fintech_division_id",
                        "fintech divisionid needs to be a number"
                    )

        return result

    def validate_edi_split_requirements(
        self,
        convert_format: str,
        split_edi: bool,
        prepend_dates: bool,
        tweak_edi: bool
    ) -> ValidationResult:
        """
        Validate EDI split requirements.

        Args:
            convert_format: Current convert format
            split_edi: Whether EDI is split
            prepend_dates: Whether to prepend dates to files
            tweak_edi: Whether EDI tweaking is enabled

        Returns:
            ValidationResult with any validation errors
        """
        result = ValidationResult()

        # Prepend dates requires split EDI
        if prepend_dates and not split_edi:
            result.add_error("split_edi", "EDI needs to be split for prepending dates")

        # Jolley custom requires split EDI
        if convert_format == "jolley_custom" and not split_edi and not tweak_edi:
            result.add_error("split_edi", "EDI needs to be split for jolley_custom backend")

        return result

    def validate_complete(
        self,
        config: FolderConfiguration,
        current_alias: Optional[str] = None
    ) -> ValidationResult:
        """
        Validate complete folder configuration.

        Args:
            config: FolderConfiguration to validate
            current_alias: Current alias if editing existing

        Returns:
            ValidationResult with all validation errors
        """
        result = ValidationResult()

        # Validate FTP
        if config.ftp:
            ftp_result = self.validate_ftp_settings(
                server=config.ftp.server,
                port=str(config.ftp.port),
                folder=config.ftp.folder,
                username=config.ftp.username,
                password=config.ftp.password,
                enabled=config.process_backend_ftp
            )
            for error in ftp_result.errors:
                result.add_error(error.field, error.message)

        # Validate Email
        if config.email:
            email_result = self.validate_email_settings(
                recipients=config.email.recipients,
                enabled=config.process_backend_email
            )
            for error in email_result.errors:
                result.add_error(error.field, error.message)

        # Validate Copy
        if config.copy:
            copy_result = self.validate_copy_settings(
                destination=config.copy.destination_directory,
                enabled=config.process_backend_copy
            )
            for error in copy_result.errors:
                result.add_error(error.field, error.message)

        # Validate Alias
        alias_result = self.validate_alias(
            alias=config.alias,
            folder_name=config.folder_name,
            current_alias=current_alias
        )
        for error in alias_result.errors:
            result.add_error(error.field, error.message)

        # Validate Invoice Date
        if config.invoice_date:
            date_result = self.validate_invoice_date_offset(
                offset=config.invoice_date.offset
            )
            for error in date_result.errors:
                result.add_error(error.field, error.message)

        # Validate UPC Override
        if config.upc_override:
            upc_result = self.validate_upc_override(
                enabled=config.upc_override.enabled,
                category_filter=config.upc_override.category_filter
            )
            for error in upc_result.errors:
                result.add_error(error.field, error.message)

        # Validate Backend-Specific
        if config.backend_specific and config.edi:
            backend_result = self.validate_backend_specific(
                convert_format=config.edi.convert_to_format,
                division_id=config.backend_specific.fintech_division_id
            )
            for error in backend_result.errors:
                result.add_error(error.field, error.message)

        # Backend count check
        backend_count = sum([
            config.process_backend_copy,
            config.process_backend_ftp,
            config.process_backend_email
        ])
        if backend_count == 0 and config.folder_is_active == "True":
            result.add_error("backends", "No Backend Is Selected")

        return result

    def validate_extracted_fields(
        self,
        extracted_fields: "ExtractedDialogFields",
        current_alias: Optional[str] = None
    ) -> ValidationResult:
        """
        Validate extracted dialog fields.

        Args:
            extracted_fields: ExtractedDialogFields from the dialog
            current_alias: Current alias if editing existing folder

        Returns:
            ValidationResult with all validation errors
        """
        result = ValidationResult()

        # Validate FTP settings
        if extracted_fields.process_backend_ftp:
            ftp_result = self.validate_ftp_settings(
                server=extracted_fields.ftp_server,
                port=str(extracted_fields.ftp_port),
                folder=extracted_fields.ftp_folder,
                username=extracted_fields.ftp_username,
                password=extracted_fields.ftp_password,
                enabled=True
            )
            for error in ftp_result.errors:
                result.add_error(error.field, error.message)

        # Validate Email settings
        if extracted_fields.process_backend_email:
            email_result = self.validate_email_settings(
                recipients=extracted_fields.email_to,
                enabled=True
            )
            for error in email_result.errors:
                result.add_error(error.field, error.message)

        # Validate Copy settings
        if extracted_fields.process_backend_copy:
            copy_result = self.validate_copy_settings(
                destination=extracted_fields.copy_to_directory,
                enabled=True
            )
            for error in copy_result.errors:
                result.add_error(error.field, error.message)

        # Validate Alias
        alias_result = self.validate_alias(
            alias=extracted_fields.alias,
            folder_name=extracted_fields.folder_name,
            current_alias=current_alias
        )
        for error in alias_result.errors:
            result.add_error(error.field, error.message)

        # Backend count check
        backend_count = sum([
            extracted_fields.process_backend_copy,
            extracted_fields.process_backend_ftp,
            extracted_fields.process_backend_email
        ])
        if backend_count == 0 and extracted_fields.folder_is_active == "True":
            result.add_error("backends", "No Backend Is Selected")

        return result
