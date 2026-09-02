"""Typed configuration dataclasses for every converter (Phase 11.x).

Phase 11.x (per ``specs/webapp-phase-11-typed-config-and-records.md``
§6) replaces the legacy ``parameters_dict`` dict pattern with typed
dataclass configurations. Each converter owns one dataclass with a
``from_parameters(params: dict)`` constructor that normalises
boolean-ish strings (via ``normalize_parameter``), parses ``int``
fields with try/except fallback, and preserves legacy parameter
name capitalisation (e.g. ``estore_Vendor_OId`` mixed case).

This module consolidates what would otherwise be seven
``convert_to_<name>_config.py`` files into one. The converters
themselves remain split — only their configuration dataclasses
are co-located here, since dispatch/ pluggable-module drop-in is
no longer a design goal in the webapp-pivot era.

Migration scope per converter:

- **x810** (4 params, 2 required) — typed config + record-field
  attribute access via ``TypedRecordProxy``.
- **simplified_csv** (5 params, all optional) — typed config only.
  Record-field access stays dict-style because ``apply_retail_uom``
  in ``csv_utils`` mutates its dict argument in place.
- **standard CSV** (13 params, all optional) — typed config only,
  same rationale as simplified_csv.
- **scannerware** (5 params, all optional) — typed config + record
  attribute access. All field accesses are read-only.
- **estore_einvoice_generic** (4 params, all strings) — typed config
  only; the converter has ~30 read-only ``record.fields["x"]``
  accesses that stay dict-style for scope discipline.
- **estore_einvoice** (3 params, all strings) — same as
  estore_einvoice_generic minus ``c_record_oid``.
- **fintech** (1 param, ``fintech_division_id``) — typed config only.
"""

from __future__ import annotations

from dataclasses import dataclass

from webapp.pipeline.converters.convert_base import normalize_parameter

# =============================================================================
# X12 810 (Invoice)
# =============================================================================


@dataclass
class X810ConverterConfig:
    """Typed configuration for ``convert_to_x810``.

    The two IDs are required; the rest are optional with defaults.

    Attributes:
        sender_id: 15-character sender ID (required).
        receiver_id: 15-character receiver ID (required).
        bill_to_name: Optional N1*BT entity name.
        isa_control: Optional ISA13 (9 digits); auto-generated if empty.
        gs_control: Optional GS06; auto-generated if empty.
        st_control: Optional ST02; auto-generated if empty.
    """

    sender_id: str = ""
    receiver_id: str = ""
    bill_to_name: str = ""
    isa_control: str = ""
    gs_control: str = ""
    st_control: str = ""

    @classmethod
    def from_parameters(cls, params: dict) -> X810ConverterConfig:
        """Build a config from a flat ``parameters_dict``.

        Raises:
            ValueError: If ``x810_sender_id`` or ``x810_receiver_id``
                is missing or empty.
        """
        missing = [
            k for k in ("x810_sender_id", "x810_receiver_id") if not params.get(k)
        ]
        if missing:
            raise ValueError(
                f"x810 converter missing required parameters: {', '.join(missing)}"
            )
        return cls(
            sender_id=str(params["x810_sender_id"]),
            receiver_id=str(params["x810_receiver_id"]),
            bill_to_name=str(params.get("x810_bill_to_name", "") or ""),
            isa_control=str(params.get("x810_isa_control", "") or ""),
            gs_control=str(params.get("x810_gs_control", "") or ""),
            st_control=str(params.get("x810_st_control", "") or ""),
        )


# =============================================================================
# Simplified CSV
# =============================================================================


@dataclass
class SimplifiedCsvConverterConfig:
    """Typed configuration for ``convert_to_simplified_csv``.

    All five fields are optional with sensible defaults — the
    converter falls back to include_headers=True, item numbers on,
    descriptions on, retail_uom=False if the operator leaves them
    unset.

    Attributes:
        retail_uom: Convert costs/quantities to retail (each) UOM.
        include_headers: Write the column header row.
        include_item_numbers: Include vendor item numbers in output.
        include_item_description: Include item descriptions in output.
        column_layout: Comma-separated list of column names defining
            output order. Default keeps backward-compatible ordering.
        each_uom_categories: Categories filter for retail UOM.
        each_uom_mode: include/exclude filter for retail UOM.
    """

    retail_uom: bool = False
    include_headers: bool = True
    include_item_numbers: bool = True
    include_item_description: bool = True
    column_layout: str = "upc_number,qty_of_units,unit_cost,description,vendor_item"
    each_uom_categories: str = "ALL"
    each_uom_mode: str = "include"

    @classmethod
    def from_parameters(cls, params: dict) -> SimplifiedCsvConverterConfig:
        """Build a config from a flat ``parameters_dict``.

        Accepts the legacy alias ``simple_csv_include_headers`` for
        ``include_headers`` and ``simple_csv_sort_order`` for
        ``column_layout``. Boolean-ish strings are normalised via
        ``normalize_parameter``.
        """
        include_headers_raw = params.get(
            "include_headers",
            params.get("simple_csv_include_headers", True),
        )
        column_layout_raw = (
            params.get(
                "simple_csv_sort_order",
                "upc_number,qty_of_units,unit_cost,description,vendor_item",
            )
            or "upc_number,qty_of_units,unit_cost,description,vendor_item"
        )

        return cls(
            retail_uom=normalize_parameter(params.get("retail_uom"), default=False),
            include_headers=normalize_parameter(include_headers_raw, default=True),
            include_item_numbers=normalize_parameter(
                params.get("include_item_numbers"), default=True
            ),
            include_item_description=normalize_parameter(
                params.get("include_item_description"), default=True
            ),
            column_layout=str(column_layout_raw),
            each_uom_categories=str(params.get("each_uom_categories") or "ALL"),
            each_uom_mode=str(params.get("each_uom_mode") or "include"),
        )


# =============================================================================
# Standard CSV
# =============================================================================


@dataclass
class CSVConverterConfig:
    """Typed configuration for ``convert_to_csv``.

    Attributes:
        calculate_upc_check_digit: Prefix UPC with tab.
        include_a_records: Include A (header) records in output.
        include_c_records: Include C (charge) records in output.
        include_headers: Include column headers in output.
        filter_ampersand: Replace & with AND in descriptions.
        pad_a_records: Pad A record vendor field.
        a_record_padding: Padding value for A records.
        override_upc_bool: Override UPC from lookup table.
        override_upc_level: Which UPC level to use (1=pack, 2=case).
        override_upc_category_filter: Filter which categories to override.
        retail_uom: Convert costs/quantities to retail (each) UOM.
        upc_target_length: Target length for UPC padding.
        upc_padding_pattern: Pattern for UPC padding.
    """

    calculate_upc_check_digit: bool = False
    include_a_records: bool = False
    include_c_records: bool = False
    include_headers: bool = True
    filter_ampersand: bool = False
    pad_a_records: bool = False
    a_record_padding: str = ""
    override_upc_bool: bool = False
    override_upc_level: int = 1
    override_upc_category_filter: str = "ALL"
    retail_uom: bool = False
    upc_target_length: int = 11
    upc_padding_pattern: str = " " * 11

    @classmethod
    def from_parameters(cls, params: dict) -> CSVConverterConfig:
        """Build a config from a flat ``parameters_dict``.

        Boolean-ish strings are normalised via ``normalize_parameter``.
        ``upc_target_length`` is parsed as ``int`` with fallback to 11
        when the value is empty or non-numeric.
        """
        raw_upc_length = params.get("upc_target_length", 11)
        try:
            upc_target_length = int(raw_upc_length or 11)
        except (TypeError, ValueError):
            upc_target_length = 11

        return cls(
            calculate_upc_check_digit=normalize_parameter(
                params.get("calculate_upc_check_digit"), default=False
            ),
            include_a_records=normalize_parameter(
                params.get("include_a_records"), default=False
            ),
            include_c_records=normalize_parameter(
                params.get("include_c_records"), default=False
            ),
            include_headers=normalize_parameter(
                params.get("include_headers"), default=True
            ),
            filter_ampersand=normalize_parameter(
                params.get("filter_ampersand"), default=False
            ),
            pad_a_records=normalize_parameter(
                params.get("pad_a_records"), default=False
            ),
            a_record_padding=str(params.get("a_record_padding", "") or ""),
            override_upc_bool=normalize_parameter(
                params.get("override_upc_bool"), default=False
            ),
            override_upc_level=int(params.get("override_upc_level", 1) or 1),
            override_upc_category_filter=str(
                params.get("override_upc_category_filter", "ALL") or "ALL"
            ),
            retail_uom=normalize_parameter(params.get("retail_uom"), default=False),
            upc_target_length=upc_target_length,
            upc_padding_pattern=str(
                params.get("upc_padding_pattern", " " * 11) or " " * 11
            ),
        )


# =============================================================================
# ScannerWare
# =============================================================================


@dataclass
class ScannerWareConverterConfig:
    """Typed configuration for ``convert_to_scannerware``.

    Attributes:
        a_record_padding: Padding value for A records.
        append_a_records: Whether to append custom text to A records.
        a_record_append_text: Custom text to append to A records.
        force_txt_file_ext: Force ``.txt`` extension instead of
            deriving from input filename.
        invoice_date_offset: Days to offset the invoice date (for tests).
    """

    a_record_padding: str = ""
    append_a_records: bool = False
    a_record_append_text: str = ""
    force_txt_file_ext: bool = False
    invoice_date_offset: int = 0

    @classmethod
    def from_parameters(cls, params: dict) -> ScannerWareConverterConfig:
        """Build a config from a flat ``parameters_dict``."""
        raw_offset = params.get("invoice_date_offset", 0)
        try:
            invoice_date_offset = int(raw_offset or 0)
        except (TypeError, ValueError):
            invoice_date_offset = 0

        return cls(
            a_record_padding=str(params.get("a_record_padding", "") or ""),
            append_a_records=normalize_parameter(
                params.get("append_a_records"), default=False
            ),
            a_record_append_text=str(params.get("a_record_append_text", "") or ""),
            force_txt_file_ext=normalize_parameter(
                params.get("force_txt_file_ext"), default=False
            ),
            invoice_date_offset=invoice_date_offset,
        )


# =============================================================================
# EStore E-Invoice Generic
# =============================================================================


@dataclass
class EStoreEInvoiceGenericConverterConfig:
    """Typed configuration for ``convert_to_estore_einvoice_generic``.

    Attributes:
        store_number: Store number to embed in output.
        vendor_oid: Vendor OID (capitalisation matches legacy param).
        vendor_name: Vendor name as known to eStore.
        c_record_oid: OID written for C-record charge rows.
    """

    store_number: str = ""
    vendor_oid: str = ""
    vendor_name: str = ""
    c_record_oid: str = ""

    @classmethod
    def from_parameters(cls, params: dict) -> EStoreEInvoiceGenericConverterConfig:
        """Build a config from a flat ``parameters_dict``."""
        return cls(
            store_number=str(params.get("estore_store_number", "") or ""),
            vendor_oid=str(params.get("estore_Vendor_OId", "") or ""),
            vendor_name=str(params.get("estore_vendor_NameVendorOID", "") or ""),
            c_record_oid=str(params.get("estore_c_record_OID", "") or ""),
        )


# =============================================================================
# EStore E-Invoice
# =============================================================================


@dataclass
class EStoreEInvoiceConverterConfig:
    """Typed configuration for ``convert_to_estore_einvoice``.

    Attributes:
        store_number: Store number to embed in output.
        vendor_oid: Vendor OID (capitalisation matches legacy param).
        vendor_name: Vendor name as known to eStore.
    """

    store_number: str = ""
    vendor_oid: str = ""
    vendor_name: str = ""

    @classmethod
    def from_parameters(cls, params: dict) -> EStoreEInvoiceConverterConfig:
        """Build a config from a flat ``parameters_dict``."""
        return cls(
            store_number=str(params.get("estore_store_number", "") or ""),
            vendor_oid=str(params.get("estore_Vendor_OId", "") or ""),
            vendor_name=str(params.get("estore_vendor_NameVendorOID", "") or ""),
        )


# =============================================================================
# Fintech
# =============================================================================


@dataclass
class FintechConverterConfig:
    """Typed configuration for ``convert_to_fintech``.

    Attributes:
        division_id: The division ID to include in output.
    """

    division_id: str = ""

    @classmethod
    def from_parameters(cls, params: dict) -> FintechConverterConfig:
        """Build a config from a flat ``parameters_dict``."""
        return cls(
            division_id=str(params.get("fintech_division_id", "") or ""),
        )


# =============================================================================
# YellowDog CSV
# =============================================================================


@dataclass
class YellowDogConverterConfig:
    """Typed configuration for ``convert_to_yellowdog_csv``.

    Attributes:
        database_lookup_mode: Lower-cased lookup mode controlling
            InvFetcher behaviour. Values ``"strict"``, ``"required"``,
            and ``"test"`` enable strict mode (raises when AS400
            credentials are missing or query runner initialisation
            fails). All other values (including the empty string)
            are treated as ``"optional"``.
    """

    database_lookup_mode: str = "optional"

    STRICT_MODES: frozenset[str] = frozenset({"strict", "required", "test"})

    @property
    def strict(self) -> bool:
        """Return True when database_lookup_mode is strict/required/test."""
        return self.database_lookup_mode in self.STRICT_MODES

    @classmethod
    def from_parameters(
        cls,
        params: dict,
        settings_dict: dict | None = None,
    ) -> YellowDogConverterConfig:
        """Build a config from a flat ``parameters_dict`` (and settings_dict).

        The ``database_lookup_mode`` value is resolved via a fallback
        chain: ``parameters_dict["database_lookup_mode"]`` first, then
        ``settings_dict["database_lookup_mode"]``, finally the string
        ``"optional"``. The result is coerced to a lower-cased string.
        """
        settings = settings_dict or {}
        mode_raw = params.get(
            "database_lookup_mode",
            settings.get("database_lookup_mode", "optional"),
        )
        return cls(database_lookup_mode=str(mode_raw).strip().lower())


__all__ = [
    "CSVConverterConfig",
    "EStoreEInvoiceConverterConfig",
    "EStoreEInvoiceGenericConverterConfig",
    "FintechConverterConfig",
    "ScannerWareConverterConfig",
    "SimplifiedCsvConverterConfig",
    "X810ConverterConfig",
    "YellowDogConverterConfig",
]
