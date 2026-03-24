"""Folder settings validation logic extracted from EditDialog.

This module provides validation logic for folder settings, extracted
from the EditDialog class to enable comprehensive unit testing.
"""

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional

from core.utils.bool_utils import normalize_bool
from interface.models.folder_configuration import (
    BackendSpecificConfiguration,
    CopyConfiguration,
    EDIConfiguration,
    EmailConfiguration,
    FolderConfiguration,
    FTPConfiguration,
    InvoiceDateConfiguration,
    UPCOverrideConfiguration,
)
from interface.services.ftp_service import FTPServiceProtocol

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
        existing_aliases: Optional[List[str]] = None,
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
        enabled: bool,
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
        if port == "":
            result.add_error("ftp_port", "FTP Port Field Is Required")
        else:
            try:
                port_int = int(port)
                if not (1 <= port_int <= 65535):
                    result.add_error(
                        "ftp_port", "FTP Port Field Needs To Be A Valid Port Number"
                    )
            except ValueError:
                result.add_error("ftp_port", "FTP Port Field Needs To Be A Number")

        # FTP connection test (if all fields valid and service available)
        if result.is_valid and self.ftp_service:
            conn_result = self.ftp_service.test_connection(
                server=server,
                port=int(port),
                username=username,
                password=password,
                folder=folder,
            )
            if not conn_result.success:
                error_msg = conn_result.error_message or "FTP connection failed"
                result.add_error("ftp_connection", error_msg)

        return result

    def validate_email_settings(
        self, recipients: str, enabled: bool
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
            result.add_error(
                "email_recipient", "Email Destination Address Field Is Required"
            )
            return result

        # Validate each recipient
        emails = re.split(r"[;,]\s*", recipients.strip())
        for email in emails:
            if not self._validate_email(email):
                result.add_error(
                    "email_recipient", f"Invalid Email Destination Address: {email}"
                )

        return result

    def _validate_email(self, email: str) -> bool:
        """Basic email validation."""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,}$"
        return bool(re.match(pattern, email))

    def validate_copy_settings(
        self, destination: str, enabled: bool
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
            result.add_error(
                "copy_destination", "Copy Backend Destination Is Currently Unset"
            )

        return result

    def validate_alias(
        self, alias: str, folder_name: str, current_alias: Optional[str] = None
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
            result.add_error(
                "invoice_date_offset", "Invoice date offset not in valid range"
            )

        return result

    def validate_a_record_padding(
        self,
        padding_text: str,
        padding_length: int,
        enabled: bool,
        convert_format: Optional[str] = None,
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

        # ScannerWare specific - check before enabled return
        if convert_format == "ScannerWare" and not enabled:
            result.add_error(
                "a_record_padding",
                '"A" Record Padding Needs To Be Enabled For ScannerWare Backend',
            )
            return result

        if not enabled:
            return result

        if len(padding_text) > padding_length:
            result.add_error(
                "a_record_padding",
                f'"A" Record Padding Needs To Be At Most {padding_length} Characters',
            )

        if len(padding_text) != 6:
            result.add_error(
                "a_record_padding", '"A" Record Padding Needs To Be Six Characters'
            )

        return result

    def validate_upc_override(
        self, enabled: bool, category_filter: str
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
                "upc_category_filter", "Override UPC Category Filter Is Required"
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
                            "Override UPC Category Filter Is Invalid",
                        )
                except ValueError:
                    result.add_error(
                        "upc_category_filter", "Override UPC Category Filter Is Invalid"
                    )

        return result

    def validate_backend_specific(
        self, convert_format: str, division_id: Optional[str] = None
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
                        "fintech_division_id", "fintech divisionid needs to be a number"
                    )

        return result

    def validate_edi_split_requirements(
        self, convert_format: str, split_edi: bool, prepend_dates: bool
    ) -> ValidationResult:
        """
        Validate EDI split requirements.

        Args:
            convert_format: Current convert format
            split_edi: Whether EDI is split
            prepend_dates: Whether to prepend dates to files

        Returns:
            ValidationResult with any validation errors
        """
        result = ValidationResult()

        # Prepend dates requires split EDI
        if prepend_dates and not split_edi:
            result.add_error("split_edi", "EDI needs to be split for prepending dates")

        # Jolley custom requires split EDI
        if convert_format == "jolley_custom" and not split_edi:
            result.add_error(
                "split_edi", "EDI needs to be split for jolley_custom backend"
            )

        return result

    def validate_complete(
        self, config: FolderConfiguration, current_alias: Optional[str] = None
    ) -> ValidationResult:
        """
        Validate complete folder configuration.

        Args:
            config: FolderConfiguration to validate
            current_alias: Current alias if editing existing

        Returns:
            ValidationResult with all validation errors
        """
        return self._validate_config(
            config=config, current_alias=current_alias, include_extended_checks=True
        )

    def validate_extracted_fields(
        self,
        extracted_fields: "ExtractedDialogFields",
        current_alias: Optional[str] = None,
    ) -> ValidationResult:
        """
        Validate extracted dialog fields.

        Args:
            extracted_fields: ExtractedDialogFields from the dialog
            current_alias: Current alias if editing existing folder

        Returns:
            ValidationResult with all validation errors
        """
        config = self._to_folder_configuration(extracted_fields)
        return self._validate_config(
            config=config,
            current_alias=current_alias,
            include_extended_checks=False,
        )

    def _to_folder_configuration(
        self, extracted_fields: "ExtractedDialogFields"
    ) -> FolderConfiguration:
        """Convert extracted dialog fields into canonical FolderConfiguration."""
        return FolderConfiguration(
            folder_name=extracted_fields.folder_name,
            folder_is_active=extracted_fields.folder_is_active,
            alias=extracted_fields.alias,
            process_backend_copy=extracted_fields.process_backend_copy,
            process_backend_ftp=extracted_fields.process_backend_ftp,
            process_backend_email=extracted_fields.process_backend_email,
            ftp=FTPConfiguration(
                server=extracted_fields.ftp_server,
                port=extracted_fields.ftp_port,
                username=extracted_fields.ftp_username,
                password=extracted_fields.ftp_password,
                folder=extracted_fields.ftp_folder,
            ),
            email=EmailConfiguration(
                recipients=extracted_fields.email_to,
                subject_line=extracted_fields.email_subject_line,
            ),
            copy=CopyConfiguration(
                destination_directory=extracted_fields.copy_to_directory
            ),
            edi=EDIConfiguration(
                process_edi=extracted_fields.process_edi,
                split_edi=extracted_fields.split_edi,
                split_edi_include_invoices=extracted_fields.split_edi_include_invoices,
                split_edi_include_credits=extracted_fields.split_edi_include_credits,
                prepend_date_files=extracted_fields.prepend_date_files,
                convert_to_format=extracted_fields.convert_to_format,
                force_edi_validation=extracted_fields.force_edi_validation,
                rename_file=extracted_fields.rename_file,
                split_edi_filter_categories=extracted_fields.split_edi_filter_categories,
                split_edi_filter_mode=extracted_fields.split_edi_filter_mode,
            ),
            upc_override=UPCOverrideConfiguration(
                enabled=extracted_fields.override_upc_bool,
                level=extracted_fields.override_upc_level,
                category_filter=extracted_fields.override_upc_category_filter,
                target_length=extracted_fields.upc_target_length,
                padding_pattern=extracted_fields.upc_padding_pattern,
            ),
            invoice_date=InvoiceDateConfiguration(
                offset=extracted_fields.invoice_date_offset,
                custom_format_enabled=extracted_fields.invoice_date_custom_format,
                custom_format_string=extracted_fields.invoice_date_custom_format_string,
                retail_uom=extracted_fields.retail_uom,
            ),
            backend_specific=BackendSpecificConfiguration(
                estore_store_number=extracted_fields.estore_store_number,
                estore_vendor_oid=extracted_fields.estore_vendor_oid,
                estore_vendor_namevendoroid=extracted_fields.estore_vendor_namevendoroid,
                fintech_division_id=extracted_fields.fintech_division_id,
            ),
            plugin_configurations=extracted_fields.plugin_configurations,
        )

    def _merge_result(self, target: ValidationResult, source: ValidationResult) -> None:
        """Merge errors and warnings from source into target."""
        for error in source.errors:
            target.add_error(error.field, error.message)
        for warning in source.warnings:
            target.add_warning(warning.field, warning.message)

    def _validate_config(
        self,
        config: FolderConfiguration,
        current_alias: Optional[str],
        include_extended_checks: bool,
    ) -> ValidationResult:
        """Core validation path for full and extracted folder data."""
        result = ValidationResult()

        if config.ftp:
            self._merge_result(
                result,
                self.validate_ftp_settings(
                    server=config.ftp.server,
                    port=str(config.ftp.port),
                    folder=config.ftp.folder,
                    username=config.ftp.username,
                    password=config.ftp.password,
                    enabled=config.process_backend_ftp,
                ),
            )

        if config.email:
            self._merge_result(
                result,
                self.validate_email_settings(
                    recipients=config.email.recipients,
                    enabled=config.process_backend_email,
                ),
            )

        if config.copy:
            self._merge_result(
                result,
                self.validate_copy_settings(
                    destination=config.copy.destination_directory,
                    enabled=config.process_backend_copy,
                ),
            )

        self._merge_result(
            result,
            self.validate_alias(
                alias=config.alias,
                folder_name=config.folder_name,
                current_alias=current_alias,
            ),
        )

        if include_extended_checks and config.invoice_date:
            self._merge_result(
                result,
                self.validate_invoice_date_offset(offset=config.invoice_date.offset),
            )

        if include_extended_checks and config.upc_override:
            self._merge_result(
                result,
                self.validate_upc_override(
                    enabled=config.upc_override.enabled,
                    category_filter=config.upc_override.category_filter,
                ),
            )

        if include_extended_checks and config.backend_specific and config.edi:
            self._merge_result(
                result,
                self.validate_backend_specific(
                    convert_format=config.edi.convert_to_format,
                    division_id=config.backend_specific.fintech_division_id,
                ),
            )

        backend_count = sum(
            [
                config.process_backend_copy,
                config.process_backend_ftp,
                config.process_backend_email,
            ]
        )
        if backend_count == 0 and normalize_bool(config.folder_is_active):
            result.add_error("backends", "No Backend Is Selected")

        return result
