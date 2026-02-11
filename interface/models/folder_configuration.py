"""Folder Configuration Data Model.

This module defines the data model for folder settings configuration.
It provides dataclasses for all folder configuration fields with
validation and serialization/deserialization methods.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Union
from enum import Enum
import re


class BackendType(Enum):
    """Enum for backend types."""
    COPY = "copy"
    FTP = "ftp"
    EMAIL = "email"


class ConvertFormat(Enum):
    """Enum for EDI convert formats."""
    CSV = "csv"
    SCANNERWARE = "ScannerWare"
    SCANSHEET_A = "ScanSheet_Type_A"
    JOLLEY_CUSTOM = "jolley_custom"
    ESTORE_EINVOICE = "eStore_eInvoice"
    ESTORE_EINVOICE_GENERIC = "eStore_eInvoice_Generic"
    FINTECH = "fintech"
    STEWARTS_CUSTOM = "stewarts_custom"
    YELLOWDOG_CSV = "yellowdog_csv"
    SIMPLIFIED_CSV = "simplified_csv"
    DO_NOTHING = "do_nothing"


@dataclass
class FTPConfiguration:
    """FTP connection configuration."""
    server: str = ""
    port: int = 21
    username: str = ""
    password: str = ""
    folder: str = ""

    def validate(self) -> List[str]:
        """Validate FTP configuration."""
        errors = []
        if not self.server:
            errors.append("FTP Server Field Is Required")
        if not self.username:
            errors.append("FTP Username Field Is Required")
        if not self.password:
            errors.append("FTP Password Field Is Required")
        if not self.folder:
            errors.append("FTP Folder Field Is Required")
        elif not self.folder.endswith("/"):
            errors.append("FTP Folder Path Needs To End In /")
        try:
            port_int = int(self.port)
            if not (1 <= port_int <= 65535):
                errors.append("FTP Port Field Needs To Be A Valid Port Number")
        except (ValueError, TypeError):
            errors.append("FTP Port Field Needs To Be A Number")
        return errors


@dataclass
class EmailConfiguration:
    """Email backend configuration."""
    recipients: str = ""
    subject_line: str = ""
    sender_address: Optional[str] = None

    def validate(self) -> List[str]:
        """Validate email configuration."""
        errors = []
        if not self.recipients:
            errors.append("Email Destination Address Field Is Required")
        else:
            emails = self.recipients.split(", ")
            for email in emails:
                if not self._validate_email(email):
                    errors.append(f"Invalid Email Destination Address: {email}")
        return errors

    def _validate_email(self, email: str) -> bool:
        """Basic email validation."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))


@dataclass
class CopyConfiguration:
    """Copy backend configuration."""
    destination_directory: str = ""

    def validate(self) -> List[str]:
        """Validate copy configuration."""
        errors = []
        if not self.destination_directory:
            errors.append("Copy Backend Destination Is Currently Unset")
        return errors


@dataclass
class EDIConfiguration:
    """EDI processing configuration."""
    process_edi: str = "False"  # "True", "False"
    tweak_edi: bool = False
    split_edi: bool = False
    split_edi_include_invoices: bool = False
    split_edi_include_credits: bool = False
    prepend_date_files: bool = False
    convert_to_format: str = ""
    force_edi_validation: bool = False
    rename_file: str = ""
    split_edi_filter_categories: str = "ALL"
    split_edi_filter_mode: str = "include"

    def validate(self) -> List[str]:
        """Validate EDI configuration."""
        errors = []
        if self.prepend_date_files and not self.split_edi:
            errors.append("EDI needs to be split for prepending dates")
        return errors


@dataclass
class UPCOverrideConfiguration:
    """UPC override configuration."""
    enabled: bool = False
    level: int = 1
    category_filter: str = ""
    target_length: int = 11
    padding_pattern: str = "           "

    def validate(self) -> List[str]:
        """Validate UPC override configuration."""
        errors = []
        if self.enabled and not self.category_filter:
            errors.append("Override UPC Category Filter Is Required")
        if self.enabled:
            for category in self.category_filter.split(","):
                if category != "ALL":
                    try:
                        cat_int = int(category)
                        if cat_int not in range(1, 100):
                            errors.append("Override UPC Category Filter Is Invalid")
                    except ValueError:
                        if category != "ALL":
                            errors.append("Override UPC Category Filter Is Invalid")
        return errors


@dataclass
class ARecordPaddingConfiguration:
    """A-record padding configuration."""
    enabled: bool = False
    padding_text: str = ""
    padding_length: int = 6
    append_text: str = ""
    append_enabled: bool = False
    force_txt_extension: bool = False

    def validate(self, convert_format: Optional[str] = None) -> List[str]:
        """Validate A-record padding configuration."""
        errors = []
        if self.enabled:
            if len(self.padding_text) > self.padding_length:
                errors.append(
                    f'"A" Record Padding Needs To Be At Most '
                    f'{self.padding_length} Characters'
                )
            if len(self.padding_text) != 6:
                errors.append('"A" Record Padding Needs To Be Six Characters')
            if convert_format == "ScannerWare" and self.padding_length != 6:
                pass  # ScannerWare handled separately
        return errors


@dataclass
class InvoiceDateConfiguration:
    """Invoice date configuration."""
    offset: int = 0
    custom_format_enabled: bool = False
    custom_format_string: str = ""
    retail_uom: bool = False

    def validate(self) -> List[str]:
        """Validate invoice date configuration."""
        errors = []
        if self.offset not in range(-14, 15):
            errors.append("Invoice date offset not in valid range (-14 to 14)")
        return errors


@dataclass
class BackendSpecificConfiguration:
    """Backend-specific configuration fields."""
    # Estore
    estore_store_number: str = ""
    estore_vendor_oid: str = ""
    estore_vendor_namevendoroid: str = ""
    estore_c_record_oid: str = ""
    # Fintech
    fintech_division_id: str = ""
    # ScannerWare specific handled in EDI


@dataclass
class CSVConfiguration:
    """CSV-specific configuration."""
    include_headers: bool = False
    filter_ampersand: bool = False
    include_item_numbers: bool = False
    include_item_description: bool = False
    simple_csv_sort_order: str = ""
    split_prepaid_sales_tax_crec: bool = False


@dataclass
class FolderConfiguration:
    """Complete folder configuration data model."""
    # Identity
    folder_name: str = ""
    folder_is_active: str = "False"
    alias: str = ""
    is_template: bool = False

    # Backend toggles
    process_backend_copy: bool = False
    process_backend_ftp: bool = False
    process_backend_email: bool = False

    # Backend configurations
    ftp: Optional[FTPConfiguration] = None
    email: Optional[EmailConfiguration] = None
    copy: Optional[CopyConfiguration] = None

    # EDI
    edi: Optional[EDIConfiguration] = None

    # UPC Override
    upc_override: Optional[UPCOverrideConfiguration] = None

    # A-Record
    a_record_padding: Optional[ARecordPaddingConfiguration] = None

    # Invoice Date
    invoice_date: Optional[InvoiceDateConfiguration] = None

    # Backend-specific
    backend_specific: Optional[BackendSpecificConfiguration] = None

    # CSV
    csv: Optional[CSVConfiguration] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FolderConfiguration":
        """Create FolderConfiguration from dictionary."""
        # Extract nested configurations
        ftp = None
        if all(k in data for k in ['ftp_server', 'ftp_port', 'ftp_username', 'ftp_password', 'ftp_folder']):
            ftp = FTPConfiguration(
                server=data.get('ftp_server', ''),
                port=data.get('ftp_port', 21),
                username=data.get('ftp_username', ''),
                password=data.get('ftp_password', ''),
                folder=data.get('ftp_folder', '')
            )

        email = None
        if all(k in data for k in ['email_to', 'email_subject_line']):
            email = EmailConfiguration(
                recipients=data.get('email_to', ''),
                subject_line=data.get('email_subject_line', '')
            )

        copy = None
        if 'copy_to_directory' in data:
            copy = CopyConfiguration(
                destination_directory=data.get('copy_to_directory', '')
            )

        # EDI configuration
        edi = EDIConfiguration(
            process_edi=data.get('process_edi', 'False'),
            tweak_edi=data.get('tweak_edi', False),
            split_edi=data.get('split_edi', False),
            split_edi_include_invoices=data.get('split_edi_include_invoices', False),
            split_edi_include_credits=data.get('split_edi_include_credits', False),
            prepend_date_files=data.get('prepend_date_files', False),
            convert_to_format=data.get('convert_to_format', ''),
            force_edi_validation=data.get('force_edi_validation', False),
            rename_file=data.get('rename_file', ''),
            split_edi_filter_categories=data.get('split_edi_filter_categories', 'ALL'),
            split_edi_filter_mode=data.get('split_edi_filter_mode', 'include')
        )

        # UPC override
        upc_override = None
        if data.get('override_upc_bool', False):
            upc_override = UPCOverrideConfiguration(
                enabled=True,
                level=data.get('override_upc_level', 1),
                category_filter=data.get('override_upc_category_filter', ''),
                target_length=data.get('upc_target_length', 11),
                padding_pattern=data.get('upc_padding_pattern', '           ')
            )

        # A-record padding
        a_record_padding = ARecordPaddingConfiguration(
            enabled=data.get('pad_a_records') == "True",
            padding_text=data.get('a_record_padding', ''),
            padding_length=data.get('a_record_padding_length', 6),
            append_text=data.get('a_record_append_text', ''),
            append_enabled=data.get('append_a_records') == "True",
            force_txt_extension=data.get('force_txt_file_ext') == "True"
        )

        # Invoice date
        invoice_date = InvoiceDateConfiguration(
            offset=data.get('invoice_date_offset', 0),
            custom_format_enabled=data.get('invoice_date_custom_format', False),
            custom_format_string=data.get('invoice_date_custom_format_string', ''),
            retail_uom=data.get('retail_uom', False)
        )

        # Backend-specific
        backend_specific = BackendSpecificConfiguration(
            estore_store_number=data.get('estore_store_number', ''),
            estore_vendor_oid=data.get('estore_Vendor_OId', ''),
            estore_vendor_namevendoroid=data.get('estore_vendor_NameVendorOID', ''),
            fintech_division_id=data.get('fintech_division_id', '')
        )

        # CSV configuration
        csv = CSVConfiguration(
            include_headers=data.get('include_headers') == "True",
            filter_ampersand=data.get('filter_ampersand') == "True",
            include_item_numbers=data.get('include_item_numbers', False),
            include_item_description=data.get('include_item_description', False),
            simple_csv_sort_order=data.get('simple_csv_sort_order', ''),
            split_prepaid_sales_tax_crec=data.get('split_prepaid_sales_tax_crec', False)
        )

        return cls(
            folder_name=data.get('folder_name', ''),
            folder_is_active=data.get('folder_is_active', 'False'),
            alias=data.get('alias', ''),
            is_template=data.get('folder_name') == 'template',
            process_backend_copy=data.get('process_backend_copy', False),
            process_backend_ftp=data.get('process_backend_ftp', False),
            process_backend_email=data.get('process_backend_email', False),
            ftp=ftp,
            email=email,
            copy=copy,
            edi=edi,
            upc_override=upc_override,
            a_record_padding=a_record_padding,
            invoice_date=invoice_date,
            backend_specific=backend_specific,
            csv=csv
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert FolderConfiguration to dictionary for database."""
        data = {
            'folder_name': self.folder_name,
            'folder_is_active': self.folder_is_active,
            'alias': self.alias,
            'process_backend_copy': self.process_backend_copy,
            'process_backend_ftp': self.process_backend_ftp,
            'process_backend_email': self.process_backend_email,
        }

        if self.ftp:
            data.update({
                'ftp_server': self.ftp.server,
                'ftp_port': self.ftp.port,
                'ftp_username': self.ftp.username,
                'ftp_password': self.ftp.password,
                'ftp_folder': self.ftp.folder,
            })

        if self.email:
            data.update({
                'email_to': self.email.recipients,
                'email_subject_line': self.email.subject_line,
            })

        if self.copy:
            data['copy_to_directory'] = self.copy.destination_directory

        if self.edi:
            data.update({
                'process_edi': self.edi.process_edi,
                'tweak_edi': self.edi.tweak_edi,
                'split_edi': self.edi.split_edi,
                'split_edi_include_invoices': self.edi.split_edi_include_invoices,
                'split_edi_include_credits': self.edi.split_edi_include_credits,
                'prepend_date_files': self.edi.prepend_date_files,
                'convert_to_format': self.edi.convert_to_format,
                'force_edi_validation': self.edi.force_edi_validation,
                'rename_file': self.edi.rename_file,
                'split_edi_filter_categories': self.edi.split_edi_filter_categories,
                'split_edi_filter_mode': self.edi.split_edi_filter_mode,
            })

        if self.upc_override:
            data.update({
                'override_upc_bool': self.upc_override.enabled,
                'override_upc_level': self.upc_override.level,
                'override_upc_category_filter': self.upc_override.category_filter,
                'upc_target_length': self.upc_override.target_length,
                'upc_padding_pattern': self.upc_override.padding_pattern,
            })

        if self.a_record_padding:
            data.update({
                'pad_a_records': str(self.a_record_padding.enabled),
                'a_record_padding': self.a_record_padding.padding_text,
                'a_record_padding_length': self.a_record_padding.padding_length,
                'append_a_records': str(self.a_record_padding.append_enabled),
                'a_record_append_text': self.a_record_padding.append_text,
                'force_txt_file_ext': str(self.a_record_padding.force_txt_extension),
            })

        if self.invoice_date:
            data.update({
                'invoice_date_offset': self.invoice_date.offset,
                'invoice_date_custom_format': self.invoice_date.custom_format_enabled,
                'invoice_date_custom_format_string': self.invoice_date.custom_format_string,
                'retail_uom': self.invoice_date.retail_uom,
            })

        if self.backend_specific:
            data.update({
                'estore_store_number': self.backend_specific.estore_store_number,
                'estore_Vendor_OId': self.backend_specific.estore_vendor_oid,
                'estore_vendor_NameVendorOID': self.backend_specific.estore_vendor_namevendoroid,
                'fintech_division_id': self.backend_specific.fintech_division_id,
            })

        if self.csv:
            data.update({
                'include_headers': str(self.csv.include_headers),
                'filter_ampersand': str(self.csv.filter_ampersand),
                'include_item_numbers': self.csv.include_item_numbers,
                'include_item_description': self.csv.include_item_description,
                'simple_csv_sort_order': self.csv.simple_csv_sort_order,
                'split_prepaid_sales_tax_crec': self.csv.split_prepaid_sales_tax_crec,
            })

        return data
