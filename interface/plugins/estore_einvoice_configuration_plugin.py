"""
eStore eInvoice Configuration Plugin

Implements the ConfigurationPlugin interface for eStore eInvoice format configuration.
"""

from typing import Any

from ..models.folder_configuration import ConvertFormat
from .base_simple_configuration_plugin import BaseSimpleConfigurationPlugin
from .config_schemas import FieldDefinition, FieldType


class EStoreEInvoiceConfiguration:
    """eStore eInvoice configuration data class."""

    def __init__(
        self,
        estore_store_number: str = "",
        estore_vendor_oid: str = "",
        estore_vendor_namevendoroid: str = "",
    ) -> None:
        self.estore_store_number = estore_store_number
        self.estore_vendor_oid = estore_vendor_oid
        self.estore_vendor_namevendoroid = estore_vendor_namevendoroid


class EStoreEInvoiceConfigurationPlugin(BaseSimpleConfigurationPlugin):
    """eStore eInvoice configuration plugin."""

    @classmethod
    def get_name(cls) -> str:
        return "eStore eInvoice Configuration"

    @classmethod
    def get_identifier(cls) -> str:
        return "estore_einvoice_configuration"

    @classmethod
    def get_format_name(cls) -> str:
        return "eStore eInvoice"

    @classmethod
    def get_format_enum(cls) -> ConvertFormat:
        return ConvertFormat.ESTORE_EINVOICE

    @classmethod
    def get_config_fields(cls) -> list[FieldDefinition]:
        fields = [
            FieldDefinition(
                name="estore_store_number",
                field_type=FieldType.STRING,
                label="Store Number",
                description="The store number for eStore eInvoice output",
                default="",
                min_length=1,
                max_length=50,
            ),
            FieldDefinition(
                name="estore_vendor_oid",
                field_type=FieldType.STRING,
                label="Vendor OID",
                description="The vendor OID for eStore eInvoice output",
                default="",
                min_length=1,
                max_length=50,
            ),
            FieldDefinition(
                name="estore_vendor_namevendoroid",
                field_type=FieldType.STRING,
                label="Vendor Name (Vendor OID)",
                description=(
                    "The vendor name or vendor OID identifier"
                    " for the output filename"
                ),
                default="",
            ),
        ]
        return fields

    def create_config(self, data: dict[str, Any]) -> EStoreEInvoiceConfiguration:
        return EStoreEInvoiceConfiguration(
            estore_store_number=data.get("estore_store_number", ""),
            estore_vendor_oid=data.get("estore_vendor_oid", ""),
            estore_vendor_namevendoroid=data.get("estore_vendor_namevendoroid", ""),
        )

    def serialize_config(self, config: EStoreEInvoiceConfiguration) -> dict[str, Any]:
        return {
            "estore_store_number": config.estore_store_number,
            "estore_vendor_oid": config.estore_vendor_oid,
            "estore_vendor_namevendoroid": config.estore_vendor_namevendoroid,
        }

    def deserialize_config(self, data: dict[str, Any]) -> EStoreEInvoiceConfiguration:
        return self.create_config(data)
