"""Pydantic schemas for the webapp folder-edit HTTP boundary.

These models are the wire format for ``GET/PUT /api/folders/{id}``. They
mirror the dataclasses in ``core.domain.models.folder`` field-for-field
so the browser can render a one-to-one editor. They are NOT the
authoritative validator — ``FolderConfiguration.from_dict`` /
``FolderConfiguration.validate_with_pydantic`` (the dataclass) stays
the source of truth for cross-field invariants like
``prepend_date_files`` requires ``split_edi``. The Pydantic layer
catches type / range / required-field mistakes at the HTTP boundary;
the dataclass catches everything that depends on the rest of the
folder being internally consistent.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# Field-name maps: the database stores backend settings as a flat set of
# columns (ftp_server, ftp_port, ftp_username, ...). The Pydantic schema
# nests them under "ftp"/"email"/"copy"/"http" objects so the browser can
# render a clean grouped form, and ``folder_row_to_schema`` /
# ``schema_to_folder_row`` translate between the two shapes.


class FTPConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    server: str = ""
    port: int = Field(default=21, ge=1, le=65535)
    username: str = ""
    password: str = ""
    folder: str = ""


class EmailConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recipients: str = ""
    subject_line: str = ""


class CopyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    destination_directory: str = ""


class HTTPConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str = ""
    headers: str = ""
    field_name: str = "file"
    auth_type: str = ""
    api_key: str = ""


class EDIConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

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


class UPCOverrideConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    level: int = 1
    category_filter: str = ""
    target_length: int = 11
    padding_pattern: str = "           "


class ARecordPaddingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    padding_text: str = ""
    padding_length: int = 6
    append_text: str = ""
    append_enabled: bool = False
    force_txt_extension: bool = False


class InvoiceDateConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    offset: int = Field(default=0, ge=-14, le=14)
    custom_format_enabled: bool = False
    custom_format_string: str = ""
    retail_uom: bool = False
    each_uom_categories: str = "ALL"
    each_uom_mode: str = "include"


class BackendSpecificConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    estore_store_number: str = ""
    estore_vendor_oid: str = ""
    estore_vendor_namevendoroid: str = ""
    estore_c_record_oid: str = ""
    fintech_division_id: str = ""


class CSVConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    include_headers: bool = False
    filter_ampersand: bool = False
    include_item_numbers: bool = False
    include_item_description: bool = False
    simple_csv_sort_order: str = ""
    split_prepaid_sales_tax_crec: bool = False


class FolderEditSchema(BaseModel):
    """Wire representation of a single folder row.

    Identity fields (``id``, ``folder_name``, ``folder_is_active``,
    ``alias``) live at the top level. Per-backend configs are nested so
    the browser can render grouped sections, but they are persisted as
    flat columns in the database.
    """

    model_config = ConfigDict(extra="forbid")

    # Identity
    id: int
    folder_name: str = ""
    folder_is_active: bool = True
    alias: str = ""

    # Backend toggles
    process_backend_copy: bool = False
    process_backend_ftp: bool = False
    process_backend_email: bool = False
    process_backend_http: bool = False

    # Alerting
    alert_on_failure: bool = True

    # Folder watcher: when watch_enabled is True, the dispatcher
    # polls folder_name every watch_interval_seconds and runs only
    # when a new file lands.
    watch_enabled: bool = False
    watch_interval_seconds: int = 30

    # Backend configurations (nested on the wire; flat in the DB)
    ftp: FTPConfig | None = None
    email: EmailConfig | None = None
    # ``copy`` would shadow Pydantic's BaseModel.copy() instance method,
    # so the wire field is named ``copy_backend``.
    copy_backend: CopyConfig | None = None
    http: HTTPConfig | None = None

    # Processing
    edi: EDIConfig | None = None
    upc_override: UPCOverrideConfig | None = None
    a_record_padding: ARecordPaddingConfig | None = None
    invoice_date: InvoiceDateConfig | None = None
    backend_specific: BackendSpecificConfig | None = None
    csv: CSVConfig | None = None

    # Plugin configurations: {format_name -> {field: value, ...}}.
    # Schema is intentionally permissive — the per-format shape is owned
    # by the dispatch converter registry and would require reflection
    # to validate generically. Operators editing these know what they
    # are doing.
    plugin_configurations: dict[str, dict[str, Any]] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Translation between the database row (flat columns) and the wire schema
# (nested). Lives next to the schema because both shapes change together.
# ---------------------------------------------------------------------------


def folder_row_to_schema(row: dict[str, Any]) -> FolderEditSchema:
    """Build a ``FolderEditSchema`` from a flat database row.

    Args:
        row: A folder row from ``db.folders_table.find_one(id=...)``.
            Keys are the database column names (``ftp_server``,
            ``email_to``, ``copy_to_directory``, etc.).

    Returns:
        A populated ``FolderEditSchema`` with backend configs nested
        under their respective keys. Fields not present in the row fall
        back to the Pydantic defaults — this keeps the schema tolerant
        of legacy rows that pre-date some columns.

    """

    def _has_any(keys: tuple[str, ...]) -> bool:
        return any(k in row for k in keys)


    def _to_int(value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _coerce_str(value: Any) -> str:
        """Normalize a DB cell to a string for the wire schema.

        The legacy desktop DB stores the backend-specific ids as
        integers (e.g. ``estore_c_record_OID = 10025``). The Pydantic
        schema types them as ``str``, so without coercion every
        imported folder would fail to load in the editor with a 500.
        """
        if value is None:
            return ""
        return str(value)

    ftp = None
    ftp_keys = ("ftp_server", "ftp_port", "ftp_username", "ftp_password", "ftp_folder")
    if _has_any(ftp_keys):
        ftp = FTPConfig(
            server=row.get("ftp_server", "") or "",
            port=row.get("ftp_port", 21) or 21,
            username=row.get("ftp_username", "") or "",
            password=row.get("ftp_password", "") or "",
            folder=row.get("ftp_folder", "") or "",
        )

    email = None
    if "email_to" in row or "email_subject_line" in row:
        email = EmailConfig(
            recipients=row.get("email_to", "") or "",
            subject_line=row.get("email_subject_line", "") or "",
        )

    copy_cfg = None
    if "copy_to_directory" in row:
        ddir = row.get("copy_to_directory", "") or ""
        copy_cfg = CopyConfig(destination_directory=ddir)

    http = None
    http_keys = (
        "http_url",
        "http_headers",
        "http_field_name",
        "http_auth_type",
        "http_api_key",
    )
    if _has_any(http_keys):
        http = HTTPConfig(
            url=row.get("http_url", "") or "",
            headers=row.get("http_headers", "") or "",
            field_name=row.get("http_field_name", "file") or "file",
            auth_type=row.get("http_auth_type", "") or "",
            api_key=row.get("http_api_key", "") or "",
        )

    edi = EDIConfig(
        process_edi=bool(row.get("process_edi")),
        split_edi=bool(row.get("split_edi")),
        split_edi_include_invoices=bool(row.get("split_edi_include_invoices")),
        split_edi_include_credits=bool(row.get("split_edi_include_credits")),
        prepend_date_files=bool(row.get("prepend_date_files")),
        tweak_edi=bool(row.get("tweak_edi")),
        convert_to_format=row.get("convert_to_format", "") or "",
        force_edi_validation=bool(row.get("force_edi_validation")),
        rename_file=row.get("rename_file", "") or "",
        split_edi_filter_categories=(
            row.get("split_edi_filter_categories", "ALL") or "ALL"
        ),
        split_edi_filter_mode=row.get("split_edi_filter_mode", "include") or "include",
    )

    upc_override = UPCOverrideConfig(
        enabled=bool(row.get("override_upc_bool")),
        level=row.get("override_upc_level", 1) or 1,
        category_filter=row.get("override_upc_category_filter", "") or "",
        target_length=row.get("upc_target_length", 11) or 11,
        padding_pattern=row.get("upc_padding_pattern", "           ") or "           ",
    )

    a_record_padding = ARecordPaddingConfig(
        enabled=bool(row.get("pad_a_records")),
        padding_text=row.get("a_record_padding", "") or "",
        padding_length=row.get("a_record_padding_length", 6) or 6,
        append_text=row.get("a_record_append_text", "") or "",
        append_enabled=bool(row.get("append_a_records")),
        force_txt_extension=bool(row.get("force_txt_file_ext")),
    )

    invoice_date = InvoiceDateConfig(
        offset=row.get("invoice_date_offset", 0) or 0,
        custom_format_enabled=bool(row.get("invoice_date_custom_format")),
        custom_format_string=row.get("invoice_date_custom_format_string", "") or "",
        retail_uom=bool(row.get("retail_uom")),
        each_uom_categories=row.get("each_uom_categories", "ALL") or "ALL",
        each_uom_mode=row.get("each_uom_mode", "include") or "include",
    )

    backend_specific = BackendSpecificConfig(
        estore_store_number=_coerce_str(row.get("estore_store_number")),
        estore_vendor_oid=_coerce_str(row.get("estore_Vendor_OId")),
        estore_vendor_namevendoroid=_coerce_str(row.get("estore_vendor_NameVendorOID")),
        estore_c_record_oid=_coerce_str(row.get("estore_c_record_OID")),
        fintech_division_id=_coerce_str(row.get("fintech_division_id")),
    )

    csv_cfg = CSVConfig(
        include_headers=bool(row.get("include_headers")),
        filter_ampersand=bool(row.get("filter_ampersand")),
        include_item_numbers=bool(row.get("include_item_numbers")),
        include_item_description=bool(row.get("include_item_description")),
        simple_csv_sort_order=row.get("simple_csv_sort_order", "") or "",
        split_prepaid_sales_tax_crec=bool(row.get("split_prepaid_sales_tax_crec")),
    )

    return FolderEditSchema(
        id=row["id"],
        folder_name=row.get("folder_name", "") or "",
        folder_is_active=bool(row.get("folder_is_active", True)),
        alias=row.get("alias", "") or "",
        process_backend_copy=bool(row.get("process_backend_copy")),
        process_backend_ftp=bool(row.get("process_backend_ftp")),
        process_backend_email=bool(row.get("process_backend_email")),
        process_backend_http=bool(row.get("process_backend_http")),
        alert_on_failure=bool(row.get("alert_on_failure", True)),
        watch_enabled=str(row.get("watch_enabled", "")).lower() in ("1", "true", "yes"),
        watch_interval_seconds=_to_int(row.get("watch_interval_seconds"), 30),
        ftp=ftp,
        email=email,
        copy_backend=copy_cfg,
        http=http,
        edi=edi,
        upc_override=upc_override,
        a_record_padding=a_record_padding,
        invoice_date=invoice_date,
        backend_specific=backend_specific,
        csv=csv_cfg,
        plugin_configurations=row.get("plugin_configurations") or {},
    )


def _emit_ftp(data: dict[str, Any], schema: FolderEditSchema) -> None:
    if schema.ftp is None:
        return
    data.update(
        {
            "ftp_server": schema.ftp.server,
            "ftp_port": schema.ftp.port,
            "ftp_username": schema.ftp.username,
            "ftp_password": schema.ftp.password,
            "ftp_folder": schema.ftp.folder,
        }
    )


def _emit_email(data: dict[str, Any], schema: FolderEditSchema) -> None:
    if schema.email is None:
        return
    data.update(
        {
            "email_to": schema.email.recipients,
            "email_subject_line": schema.email.subject_line,
        }
    )


def _emit_copy(data: dict[str, Any], schema: FolderEditSchema) -> None:
    if schema.copy_backend is None:
        return
    data["copy_to_directory"] = schema.copy_backend.destination_directory


def _emit_http(data: dict[str, Any], schema: FolderEditSchema) -> None:
    if schema.http is None:
        return
    data.update(
        {
            "http_url": schema.http.url,
            "http_headers": schema.http.headers,
            "http_field_name": schema.http.field_name,
            "http_auth_type": schema.http.auth_type,
            "http_api_key": schema.http.api_key,
        }
    )


def _emit_edi(data: dict[str, Any], schema: FolderEditSchema) -> None:
    if schema.edi is None:
        return
    data.update(
        {
            "process_edi": schema.edi.process_edi,
            "split_edi": schema.edi.split_edi,
            "split_edi_include_invoices": schema.edi.split_edi_include_invoices,
            "split_edi_include_credits": schema.edi.split_edi_include_credits,
            "prepend_date_files": schema.edi.prepend_date_files,
            "tweak_edi": schema.edi.tweak_edi,
            "convert_to_format": schema.edi.convert_to_format,
            "force_edi_validation": schema.edi.force_edi_validation,
            "rename_file": schema.edi.rename_file,
            "split_edi_filter_categories": schema.edi.split_edi_filter_categories,
            "split_edi_filter_mode": schema.edi.split_edi_filter_mode,
        }
    )


def _emit_upc_override(data: dict[str, Any], schema: FolderEditSchema) -> None:
    if schema.upc_override is None:
        return
    data.update(
        {
            "override_upc_bool": schema.upc_override.enabled,
            "override_upc_level": schema.upc_override.level,
            "override_upc_category_filter": schema.upc_override.category_filter,
            "upc_target_length": schema.upc_override.target_length,
            "upc_padding_pattern": schema.upc_override.padding_pattern,
        }
    )


def _emit_a_record_padding(data: dict[str, Any], schema: FolderEditSchema) -> None:
    if schema.a_record_padding is None:
        return
    data.update(
        {
            "pad_a_records": schema.a_record_padding.enabled,
            "a_record_padding": schema.a_record_padding.padding_text,
            "a_record_padding_length": schema.a_record_padding.padding_length,
            "a_record_append_text": schema.a_record_padding.append_text,
            "append_a_records": schema.a_record_padding.append_enabled,
            "force_txt_file_ext": schema.a_record_padding.force_txt_extension,
        }
    )


def _emit_invoice_date(data: dict[str, Any], schema: FolderEditSchema) -> None:
    if schema.invoice_date is None:
        return
    data.update(
        {
            "invoice_date_offset": schema.invoice_date.offset,
            "invoice_date_custom_format": schema.invoice_date.custom_format_enabled,
            "invoice_date_custom_format_string": (
                schema.invoice_date.custom_format_string
            ),
            "retail_uom": schema.invoice_date.retail_uom,
            "each_uom_categories": schema.invoice_date.each_uom_categories,
            "each_uom_mode": schema.invoice_date.each_uom_mode,
        }
    )


def _emit_backend_specific(data: dict[str, Any], schema: FolderEditSchema) -> None:
    if schema.backend_specific is None:
        return
    data.update(
        {
            "estore_store_number": schema.backend_specific.estore_store_number,
            "estore_Vendor_OId": schema.backend_specific.estore_vendor_oid,
            "estore_vendor_NameVendorOID": (
                schema.backend_specific.estore_vendor_namevendoroid
            ),
            "estore_c_record_OID": schema.backend_specific.estore_c_record_oid,
            "fintech_division_id": schema.backend_specific.fintech_division_id,
        }
    )


def _emit_csv(data: dict[str, Any], schema: FolderEditSchema) -> None:
    if schema.csv is None:
        return
    data.update(
        {
            "include_headers": schema.csv.include_headers,
            "filter_ampersand": schema.csv.filter_ampersand,
            "include_item_numbers": schema.csv.include_item_numbers,
            "include_item_description": schema.csv.include_item_description,
            "simple_csv_sort_order": schema.csv.simple_csv_sort_order,
            "split_prepaid_sales_tax_crec": schema.csv.split_prepaid_sales_tax_crec,
        }
    )


def schema_to_folder_row(schema: FolderEditSchema) -> dict[str, Any]:
    """Flatten a ``FolderEditSchema`` back to a database row dict.

    The result is meant to be merged into an existing row dict (or
    passed to ``folders_table.insert``). Top-level columns are always
    present; backend-config columns are only emitted when the
    corresponding nested object is non-None — matching the desktop
    app's behaviour of leaving backend columns NULL when the backend
    is not in use.

    Args:
        schema: The validated wire representation.

    Returns:
        A flat dict of column-name -> value suitable for the dataset
        wrapper's ``update`` / ``insert``.

    """
    data: dict[str, Any] = {
        "id": schema.id,
        "folder_name": schema.folder_name,
        "folder_is_active": schema.folder_is_active,
        "alias": schema.alias,
        "process_backend_copy": schema.process_backend_copy,
        "process_backend_ftp": schema.process_backend_ftp,
        "process_backend_email": schema.process_backend_email,
        "process_backend_http": schema.process_backend_http,
        "alert_on_failure": schema.alert_on_failure,
        "watch_enabled": schema.watch_enabled,
        "watch_interval_seconds": schema.watch_interval_seconds,
    }
    for emitter in (
        _emit_ftp,
        _emit_email,
        _emit_copy,
        _emit_http,
        _emit_edi,
        _emit_upc_override,
        _emit_a_record_padding,
        _emit_invoice_date,
        _emit_backend_specific,
        _emit_csv,
    ):
        emitter(data, schema)

    # ``if schema.plugin_configurations:`` would drop an explicit empty
    # dict — use ``is not None`` instead so the operator's intent
    # (clear vs. don't touch) survives the round-trip.
    if schema.plugin_configurations is not None:
        data["plugin_configurations"] = schema.plugin_configurations

    return data
