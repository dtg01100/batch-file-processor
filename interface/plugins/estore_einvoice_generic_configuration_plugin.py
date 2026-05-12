"""
eStore eInvoice Generic Configuration Plugin

Implements the ConfigurationPlugin interface for eStore eInvoice
Generic format configuration.
"""

from typing import Any

from ..models.folder_configuration import ConvertFormat
from .base_simple_configuration_plugin import BaseSimpleConfigurationPlugin
from .config_schemas import FieldDefinition, FieldType


class EStoreEInvoiceGenericConfiguration:
    """eStore eInvoice Generic configuration data class."""

    def __init__(
        self,
        estore_store_number: str = "",
        estore_vendor_oid: str = "",
        estore_vendor_namevendoroid: str = "",
        estore_c_record_oid: str = "",
    ) -> None:
        self.estore_store_number = estore_store_number
        self.estore_vendor_oid = estore_vendor_oid
        self.estore_vendor_namevendoroid = estore_vendor_namevendoroid
        self.estore_c_record_oid = estore_c_record_oid


class EStoreEInvoiceGenericConfigurationPlugin(BaseSimpleConfigurationPlugin):
    """eStore eInvoice Generic configuration plugin."""

    @classmethod
    def get_name(cls) -> str:
        return "eStore eInvoice Generic Configuration"

    @classmethod
    def get_identifier(cls) -> str:
        return "estore_einvoice_generic_configuration"

    @classmethod
    def get_format_name(cls) -> str:
        return "eStore eInvoice Generic"

    @classmethod
    def get_format_enum(cls) -> ConvertFormat:
        return ConvertFormat.ESTORE_EINVOICE_GENERIC

    @classmethod
    def get_config_fields(cls) -> list[FieldDefinition]:
        fields = [
            FieldDefinition(
                name="estore_store_number",
                field_type=FieldType.STRING,
                label="Store Number",
                description="The store number for eStore eInvoice Generic output",
                default="",
                min_length=1,
                max_length=50,
            ),
            FieldDefinition(
                name="estore_vendor_oid",
                field_type=FieldType.STRING,
                label="Vendor OID",
                description="The vendor OID for eStore eInvoice Generic output",
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
            FieldDefinition(
                name="estore_c_record_oid",
                field_type=FieldType.STRING,
                label="C-Record OID",
                description="The OID to use for C-records (charges) in the output",
                default="",
            ),
        ]
        return fields

    def create_config(self, data: dict[str, Any]) -> EStoreEInvoiceGenericConfiguration:
        return EStoreEInvoiceGenericConfiguration(
            estore_store_number=data.get("estore_store_number", ""),
            estore_vendor_oid=data.get("estore_vendor_oid", ""),
            estore_vendor_namevendoroid=data.get("estore_vendor_namevendoroid", ""),
            estore_c_record_oid=data.get("estore_c_record_oid", ""),
        )

    def serialize_config(
        self, config: EStoreEInvoiceGenericConfiguration
    ) -> dict[str, Any]:
        return {
            "estore_store_number": config.estore_store_number,
            "estore_vendor_oid": config.estore_vendor_oid,
            "estore_vendor_namevendoroid": config.estore_vendor_namevendoroid,
            "estore_c_record_oid": config.estore_c_record_oid,
        }

    def deserialize_config(
        self, data: dict[str, Any]
    ) -> EStoreEInvoiceGenericConfiguration:
        return self.create_config(data)
