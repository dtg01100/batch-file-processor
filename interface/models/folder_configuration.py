"""Folder Configuration Data Model.

This module defines the data model for folder settings configuration.
It provides dataclasses for all folder configuration fields with
validation and serialization/deserialization methods.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, ValidationError, model_validator

from core.utils.bool_utils import normalize_bool


def _bool_from_data(data: dict[str, Any], key: str, *, default: bool = False) -> bool:
    return normalize_bool(data.get(key, default))


class BackendType(Enum):
    """Enum for backend types."""

    COPY = "copy"
    FTP = "ftp"
    EMAIL = "email"
    HTTP = "http"


def _discover_format_values() -> list[tuple[str, str]]:
    """Auto-discover convert formats from converters package.

    Returns tuples of (internal_name, displayValue).
    displayValue may differ from internalName for formats with specific casing.
    """
    import os
    import pkgutil

    # Mapping from internal names (from filenames) to display values
# (for legacy compatibility)
    DISPLAY_VALUES = {
        "scannerware": "ScannerWare",
        "scansheet_type_a": "ScanSheet_Type_A",
        "jolley_custom": "jolley_custom",
        "estore_einvoice": "eStore_eInvoice",
        "estore_einvoice_generic": "eStore_eInvoice_Generic",
    }

    values = [("do_nothing", "do_nothing")]
    converter_path = os.path.join("dispatch", "converters")
    if not os.path.isdir(converter_path):
        return values

    for _, module_name, is_pkg in pkgutil.iter_modules([converter_path]):
        if module_name.startswith("convert_to_") and not is_pkg:
            format_name = module_name.replace("convert_to_", "")
            display_value = DISPLAY_VALUES.get(format_name, format_name)
            values.append((format_name, display_value))
    return values


class _ConvertFormatMeta(type):
    """Metaclass to enable ConvertFormat class iteration."""

    def __iter__(cls):
        cls._ensure_discovered()
        for v in cls._discovered:
            yield cls(cls._display_values[v])

    def __len__(cls):
        cls._ensure_discovered()
        return len(cls._discovered)


class ConvertFormat(metaclass=_ConvertFormatMeta):
    """Enum-like class for EDI convert formats.

    Auto-populated from dispatch/converters/convert_to_*.py modules.
    """

    _discovered: list[str] = []

    def __init__(self, value: str):
        self._value = value

    @property
    def value(self) -> str:
        return self._value

    @property
    def name(self) -> str:
        return self._value.upper().replace("-", "_").replace(" ", "_")

    @classmethod
    def _ensure_discovered(cls):
        if not cls._discovered:
            discovered = _discover_format_values()
            cls._discovered = [v[0] for v in discovered]
            cls._display_values = {v[0]: v[1] for v in discovered}
            for v in discovered:
                key = v[0].upper().replace("-", "_").replace(" ", "_")
                setattr(cls, key, cls(v[1]))

    @classmethod
    def values(cls) -> list[str]:
        """Get all available format values."""
        cls._ensure_discovered()
        return list(cls._discovered)

    @classmethod
    def from_string(cls, s: str) -> "ConvertFormat | None":
        """Create a ConvertFormat from a string value."""
        if not s:
            return None
        cls._ensure_discovered()
        s_normalized = s.lower().replace(" ", "_").replace("-", "_")
        for v in cls._discovered:
            if v.lower() == s_normalized:
                return cls(cls._display_values.get(v, v))
        return None

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"ConvertFormat.{self.name}"

    def __eq__(self, other) -> bool:
        if isinstance(other, ConvertFormat):
            return self._value == other._value
        if isinstance(other, str):
            return self._value.lower() == other.lower()
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._value)


# Initialize - this populates the class attributes for all formats
ConvertFormat._ensure_discovered()


@dataclass
class FTPConfiguration:
    """FTP connection configuration."""

    server: str = ""
    port: int = 21
    username: str = ""
    password: str = ""
    folder: str = ""

    def validate(self) -> list[str]:
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
    sender_address: str | None = None

    def validate(self) -> list[str]:
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
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))


@dataclass
class CopyConfiguration:
    """Copy backend configuration."""

    destination_directory: str = ""

    def validate(self) -> list[str]:
        """Validate copy configuration."""
        errors = []
        if not self.destination_directory:
            errors.append("Copy Backend Destination Is Currently Unset")
        return errors


@dataclass
class HTTPConfiguration:
    """HTTP backend configuration."""

    url: str = ""
    headers: str = ""
    field_name: str = "file"
    auth_type: str = ""
    api_key: str = ""

    def validate(self) -> list[str]:
        """Validate HTTP configuration."""
        errors = []
        if not self.url:
            errors.append("HTTP URL Field Is Required")
        if self.auth_type and self.auth_type not in ("bearer", "query"):
            errors.append("HTTP Auth Type must be 'bearer' or 'query'")
        return errors


@dataclass
class EDIConfiguration:
    """EDI processing configuration."""

    process_edi: bool = False
    split_edi: bool = False
    split_edi_include_invoices: bool = False
    split_edi_include_credits: bool = False
    prepend_date_files: bool = False
    tweak_edi: bool = False
    convert_to_format: str = ""
    force_edi_validation: bool = False
    rename_file: str = ""
    split_edi_filter_categories: str = "ALL"
    split_edi_filter_mode: str = "include"

    def validate(self) -> list[str]:
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

    def validate(self) -> list[str]:
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

    def validate(self, convert_format: str | None = None) -> list[str]:
        """Validate A-record padding configuration."""
        errors = []
        if self.enabled:
            if len(self.padding_text) > self.padding_length:
                errors.append(
                    f'"A" Record Padding Needs To Be At Most '
                    f"{self.padding_length} Characters"
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

    def validate(self) -> list[str]:
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


class FolderConfigurationPydantic(BaseModel):
    folder_name: str = Field(default="")
    folder_is_active: bool = Field(default=False)
    alias: str = Field(default="")

    process_backend_copy: bool = Field(default=False)
    process_backend_ftp: bool = Field(default=False)
    process_backend_email: bool = Field(default=False)
    process_backend_http: bool = Field(default=False)

    process_edi: bool = Field(default=False)
    split_edi: bool = Field(default=False)
    split_edi_include_invoices: bool = Field(default=False)
    split_edi_include_credits: bool = Field(default=False)
    prepend_date_files: bool = Field(default=False)

    @model_validator(mode="after")
    def validate_edi_options(cls, values):  # noqa: N805
        if values.prepend_date_files and not values.split_edi:
            raise ValueError("prepend_date_files requires split_edi to be true")
        return values

    class Config:
        extra = "forbid"


@dataclass
class FolderConfiguration:
    """Complete folder configuration data model."""

    # Identity
    folder_name: str = ""
    folder_is_active: bool = False
    alias: str = ""
    is_template: bool = False

    # Backend toggles
    process_backend_copy: bool = False
    process_backend_ftp: bool = False
    process_backend_email: bool = False
    process_backend_http: bool = False

    # Alerting
    alert_on_failure: bool = True

    # Backend configurations
    ftp: FTPConfiguration | None = None
    email: EmailConfiguration | None = None
    copy: CopyConfiguration | None = None
    http: HTTPConfiguration | None = None

    # EDI
    edi: EDIConfiguration | None = None

    # UPC Override
    upc_override: UPCOverrideConfiguration | None = None

    # A-Record
    a_record_padding: ARecordPaddingConfiguration | None = None

    # Invoice Date
    invoice_date: InvoiceDateConfiguration | None = None

    # Backend-specific
    backend_specific: BackendSpecificConfiguration | None = None

    # CSV
    csv: CSVConfiguration | None = None

    # Plugin configurations - stored as dict of format -> config dict
    plugin_configurations: dict[str, dict[str, Any]] = field(default_factory=dict)

    def get_plugin_configuration(self, format_name: str) -> dict[str, Any] | None:
        """Get plugin configuration for a specific format.

        Args:
            format_name: The convert format name (e.g., "csv", "ScannerWare")

        Returns:
            Optional[Dict[str, Any]]: Plugin configuration for the format,
            or None if not found

        """
        return self.plugin_configurations.get(format_name.lower())

    def set_plugin_configuration(
        self, format_name: str, config: dict[str, Any]
    ) -> None:
        """Set plugin configuration for a specific format.

        Args:
            format_name: The convert format name (e.g., "csv", "ScannerWare")
            config: Plugin configuration to store

        """
        self.plugin_configurations[format_name.lower()] = config

    def remove_plugin_configuration(self, format_name: str) -> None:
        """Remove plugin configuration for a specific format.

        Args:
            format_name: The convert format name (e.g., "csv", "ScannerWare")

        """
        if format_name.lower() in self.plugin_configurations:
            del self.plugin_configurations[format_name.lower()]

    def has_plugin_configuration(self, format_name: str) -> bool:
        """Check if plugin configuration exists for a specific format.

        Args:
            format_name: The convert format name (e.g., "csv", "ScannerWare")

        Returns:
            bool: True if configuration exists, False otherwise

        """
        return format_name.lower() in self.plugin_configurations

    def validate_plugin_configurations(self) -> list[str]:
        """Validate all plugin configurations.

        Returns:
            List[str]: List of validation errors

        """
        errors = []
        from interface.plugins.plugin_manager import PluginManager
        from interface.plugins.validation_framework import ValidationResult

        try:
            plugin_manager = PluginManager()
            plugin_manager.discover_plugins()
            plugin_manager.initialize_plugins()

            for format_name, config in self.plugin_configurations.items():
                # Find the plugin for this format
                plugin = plugin_manager.get_configuration_plugin_by_format_name(
                    format_name
                )
                if plugin:
                    validation: ValidationResult = plugin.validate_config(config)
                    if not validation.success:
                        for error in validation.errors:
                            errors.append(f"Plugin config for {format_name}: {error}")
                else:
                    errors.append(
                        f"No configuration plugin found for format: {format_name}"
                    )
        except Exception as e:
            errors.append(f"Error validating plugin configurations: {str(e)}")

        return errors

    def validate_with_pydantic(self) -> None:
        """Validate current FolderConfiguration using Pydantic schema."""
        try:
            FolderConfigurationPydantic(
                folder_name=self.folder_name,
                folder_is_active=self.folder_is_active,
                alias=self.alias,
                process_backend_copy=self.process_backend_copy,
                process_backend_ftp=self.process_backend_ftp,
                process_backend_email=self.process_backend_email,
                process_backend_http=self.process_backend_http,
                process_edi=self.edi.process_edi if self.edi else False,
                split_edi=self.edi.split_edi if self.edi else False,
                split_edi_include_invoices=(
                    self.edi.split_edi_include_invoices if self.edi else False
                ),
                split_edi_include_credits=(
                    self.edi.split_edi_include_credits if self.edi else False
                ),
                prepend_date_files=self.edi.prepend_date_files if self.edi else False,
            )
        except ValidationError as exc:
            raise ValueError(f"FolderConfiguration pydantic validation failed: {exc}")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FolderConfiguration":
        """Create FolderConfiguration from dictionary."""
        # Extract nested configurations
        ftp = None
        if all(
            k in data
            for k in [
                "ftp_server",
                "ftp_port",
                "ftp_username",
                "ftp_password",
                "ftp_folder",
            ]
        ):
            ftp = FTPConfiguration(
                server=data.get("ftp_server", ""),
                port=data.get("ftp_port", 21),
                username=data.get("ftp_username", ""),
                password=data.get("ftp_password", ""),
                folder=data.get("ftp_folder", ""),
            )

        email = None
        if "email_to" in data:
            email = EmailConfiguration(
                recipients=data.get("email_to", ""),
                subject_line=data.get("email_subject_line", ""),
            )

        copy = None
        if "copy_to_directory" in data:
            copy = CopyConfiguration(
                destination_directory=data.get("copy_to_directory", "")
            )

        http = None
        if "http_url" in data:
            http = HTTPConfiguration(
                url=data.get("http_url", ""),
                headers=data.get("http_headers", ""),
                field_name=data.get("http_field_name", "file"),
                auth_type=data.get("http_auth_type", ""),
                api_key=data.get("http_api_key", ""),
            )

        # EDI configuration
        edi = EDIConfiguration(
            process_edi=_bool_from_data(data, "process_edi"),
            tweak_edi=_bool_from_data(data, "tweak_edi"),
            split_edi=_bool_from_data(data, "split_edi"),
            split_edi_include_invoices=_bool_from_data(
                data, "split_edi_include_invoices"
            ),
            split_edi_include_credits=_bool_from_data(
                data, "split_edi_include_credits"
            ),
            prepend_date_files=_bool_from_data(data, "prepend_date_files"),
            convert_to_format=data.get("convert_to_format", ""),
            force_edi_validation=_bool_from_data(data, "force_edi_validation"),
            rename_file=data.get("rename_file", ""),
            split_edi_filter_categories=data.get("split_edi_filter_categories", "ALL"),
            split_edi_filter_mode=data.get("split_edi_filter_mode", "include"),
        )

        # UPC override
        upc_override = None
        if _bool_from_data(data, "override_upc_bool"):
            upc_override = UPCOverrideConfiguration(
                enabled=True,
                level=data.get("override_upc_level", 1),
                category_filter=data.get("override_upc_category_filter", ""),
                target_length=data.get("upc_target_length", 11),
                padding_pattern=data.get("upc_padding_pattern", "           "),
            )

        # A-record padding
        a_record_padding = ARecordPaddingConfiguration(
            enabled=normalize_bool(data.get("pad_a_records", False)),
            padding_text=data.get("a_record_padding", ""),
            padding_length=data.get("a_record_padding_length", 6),
            append_text=data.get("a_record_append_text", ""),
            append_enabled=normalize_bool(data.get("append_a_records", False)),
            force_txt_extension=normalize_bool(data.get("force_txt_file_ext", False)),
        )

        # Invoice date
        invoice_date = InvoiceDateConfiguration(
            offset=data.get("invoice_date_offset", 0),
            custom_format_enabled=_bool_from_data(data, "invoice_date_custom_format"),
            custom_format_string=data.get("invoice_date_custom_format_string", ""),
            retail_uom=_bool_from_data(data, "retail_uom"),
        )

        # Backend-specific
        backend_specific = BackendSpecificConfiguration(
            estore_store_number=data.get("estore_store_number", ""),
            estore_vendor_oid=data.get("estore_Vendor_OId", ""),
            estore_vendor_namevendoroid=data.get("estore_vendor_NameVendorOID", ""),
            fintech_division_id=data.get("fintech_division_id", ""),
        )

        # CSV configuration
        csv = CSVConfiguration(
            include_headers=normalize_bool(data.get("include_headers", False)),
            filter_ampersand=normalize_bool(data.get("filter_ampersand", False)),
            include_item_numbers=_bool_from_data(data, "include_item_numbers"),
            include_item_description=_bool_from_data(data, "include_item_description"),
            simple_csv_sort_order=data.get("simple_csv_sort_order", ""),
            split_prepaid_sales_tax_crec=_bool_from_data(
                data, "split_prepaid_sales_tax_crec"
            ),
        )

        folder_config = cls(
            folder_name=data.get("folder_name", ""),
            folder_is_active=normalize_bool(data.get("folder_is_active", False)),
            alias=data.get("alias", ""),
            is_template=data.get("folder_name") == "template",
            process_backend_copy=_bool_from_data(data, "process_backend_copy"),
            process_backend_ftp=_bool_from_data(data, "process_backend_ftp"),
            process_backend_email=_bool_from_data(data, "process_backend_email"),
            process_backend_http=_bool_from_data(data, "process_backend_http"),
            alert_on_failure=_bool_from_data(data, "alert_on_failure", default=True),
            ftp=ftp,
            email=email,
            copy=copy,
            http=http,
            edi=edi,
            upc_override=upc_override,
            a_record_padding=a_record_padding,
            invoice_date=invoice_date,
            backend_specific=backend_specific,
            csv=csv,
            plugin_configurations=data.get("plugin_configurations", {}),
        )

        folder_config.validate_with_pydantic()
        return folder_config

    def to_dict(self) -> dict[str, Any]:
        """Convert FolderConfiguration to dictionary for database."""
        data = {
            "folder_name": self.folder_name,
            "folder_is_active": normalize_bool(self.folder_is_active),
            "alias": self.alias,
            "process_backend_copy": normalize_bool(self.process_backend_copy),
            "process_backend_ftp": normalize_bool(self.process_backend_ftp),
            "process_backend_email": normalize_bool(self.process_backend_email),
            "process_backend_http": normalize_bool(self.process_backend_http),
            "alert_on_failure": normalize_bool(self.alert_on_failure),
        }

        self._add_ftp_to_dict(data)
        self._add_email_to_dict(data)
        self._add_copy_to_dict(data)
        self._add_http_to_dict(data)
        self._add_edi_to_dict(data)
        self._add_upc_override_to_dict(data)
        self._add_a_record_padding_to_dict(data)
        self._add_invoice_date_to_dict(data)
        self._add_backend_specific_to_dict(data)
        self._add_csv_to_dict(data)

        # Plugin configurations
        if self.plugin_configurations:
            data["plugin_configurations"] = self.plugin_configurations

        return data

    def _add_ftp_to_dict(self, data: dict[str, Any]) -> None:
        """Add FTP settings to dictionary."""
        if self.ftp:
            data.update(
                {
                    "ftp_server": self.ftp.server,
                    "ftp_port": self.ftp.port,
                    "ftp_username": self.ftp.username,
                    "ftp_password": self.ftp.password,
                    "ftp_folder": self.ftp.folder,
                }
            )

    def _add_email_to_dict(self, data: dict[str, Any]) -> None:
        """Add email settings to dictionary."""
        if self.email:
            data.update(
                {
                    "email_to": self.email.recipients,
                    "email_subject_line": self.email.subject_line,
                }
            )

    def _add_copy_to_dict(self, data: dict[str, Any]) -> None:
        """Add copy backend settings to dictionary."""
        if self.copy:
            data["copy_to_directory"] = self.copy.destination_directory

    def _add_http_to_dict(self, data: dict[str, Any]) -> None:
        """Add HTTP backend settings to dictionary."""
        if self.http:
            data["http_url"] = self.http.url
            data["http_headers"] = self.http.headers
            data["http_field_name"] = self.http.field_name
            data["http_auth_type"] = self.http.auth_type
            data["http_api_key"] = self.http.api_key

    def _add_edi_to_dict(self, data: dict[str, Any]) -> None:
        """Add EDI settings to dictionary."""
        if self.edi:
            data.update(
                {
                    "process_edi": normalize_bool(self.edi.process_edi),
                    "split_edi": normalize_bool(self.edi.split_edi),
                    "split_edi_include_invoices": normalize_bool(
                        self.edi.split_edi_include_invoices
                    ),
                    "split_edi_include_credits": normalize_bool(
                        self.edi.split_edi_include_credits
                    ),
                    "prepend_date_files": normalize_bool(self.edi.prepend_date_files),
                    "tweak_edi": normalize_bool(self.edi.tweak_edi),
                    "convert_to_format": self.edi.convert_to_format,
                    "force_edi_validation": normalize_bool(
                        self.edi.force_edi_validation
                    ),
                    "rename_file": self.edi.rename_file,
                    "split_edi_filter_categories": self.edi.split_edi_filter_categories,
                    "split_edi_filter_mode": self.edi.split_edi_filter_mode,
                }
            )

    def _add_upc_override_to_dict(self, data: dict[str, Any]) -> None:
        """Add UPC override settings to dictionary."""
        if self.upc_override:
            data.update(
                {
                    "override_upc_bool": normalize_bool(self.upc_override.enabled),
                    "override_upc_level": self.upc_override.level,
                    "override_upc_category_filter": self.upc_override.category_filter,
                    "upc_target_length": self.upc_override.target_length,
                    "upc_padding_pattern": self.upc_override.padding_pattern,
                }
            )

    def _add_a_record_padding_to_dict(self, data: dict[str, Any]) -> None:
        """Add A-record padding settings to dictionary."""
        if self.a_record_padding:
            data.update(
                {
                    "pad_a_records": normalize_bool(self.a_record_padding.enabled),
                    "a_record_padding": self.a_record_padding.padding_text,
                    "a_record_padding_length": self.a_record_padding.padding_length,
                    "append_a_records": normalize_bool(
                        self.a_record_padding.append_enabled
                    ),
                    "a_record_append_text": self.a_record_padding.append_text,
                    "force_txt_file_ext": normalize_bool(
                        self.a_record_padding.force_txt_extension
                    ),
                }
            )

    def _add_invoice_date_to_dict(self, data: dict[str, Any]) -> None:
        """Add invoice date settings to dictionary."""
        if self.invoice_date:
            data.update(
                {
                    "invoice_date_offset": self.invoice_date.offset,
                    "invoice_date_custom_format": normalize_bool(
                        self.invoice_date.custom_format_enabled
                    ),
                    "invoice_date_custom_format_string": (
                self.invoice_date.custom_format_string
            ),
                    "retail_uom": normalize_bool(self.invoice_date.retail_uom),
                }
            )

    def _add_backend_specific_to_dict(self, data: dict[str, Any]) -> None:
        """Add backend-specific settings to dictionary."""
        if self.backend_specific:
            data.update(
                {
                    "estore_store_number": self.backend_specific.estore_store_number,
                    "estore_Vendor_OId": self.backend_specific.estore_vendor_oid,
                    "estore_vendor_NameVendorOID": (
                self.backend_specific.estore_vendor_namevendoroid
            ),
                    "fintech_division_id": self.backend_specific.fintech_division_id,
                }
            )

    def _add_csv_to_dict(self, data: dict[str, Any]) -> None:
        """Add CSV settings to dictionary."""
        if self.csv:
            data.update(
                {
                    "include_headers": normalize_bool(self.csv.include_headers),
                    "filter_ampersand": normalize_bool(self.csv.filter_ampersand),
                    "include_item_numbers": normalize_bool(
                        self.csv.include_item_numbers
                    ),
                    "include_item_description": normalize_bool(
                        self.csv.include_item_description
                    ),
                    "simple_csv_sort_order": self.csv.simple_csv_sort_order,
                    "split_prepaid_sales_tax_crec": normalize_bool(
                        self.csv.split_prepaid_sales_tax_crec
                    ),
                }
            )
