"""Null-safety tests for EStore converter modules.

Verifies that both estore converters handle a params dict missing the
estore_store_number, estore_Vendor_OId, and estore_vendor_NameVendorOID
keys without raising KeyError.
"""

import pytest

from dispatch.converters.convert_base import ConversionContext
from dispatch.converters.convert_to_estore_einvoice import EStoreEInvoiceConverter
from dispatch.converters.convert_to_estore_einvoice_generic import (
    EStoreEInvoiceGenericConverter,
)


@pytest.mark.unit
class TestEstoreNullSafety:
    """Estore converters must not raise KeyError when estore params are absent."""

    def test_einvoice_module_importable(self):
        """dispatch.converters.convert_to_estore_einvoice must import and expose edi_convert."""
        import dispatch.converters.convert_to_estore_einvoice as mod

        assert hasattr(mod, "edi_convert"), "Module must expose edi_convert function"

    def test_einvoice_generic_module_importable(self):
        """dispatch.converters.convert_to_estore_einvoice_generic must import and expose edi_convert."""
        import dispatch.converters.convert_to_estore_einvoice_generic as mod

        assert hasattr(mod, "edi_convert"), "Module must expose edi_convert function"

    def test_einvoice_initialize_output_no_key_error(self, tmp_path):
        """EStoreEInvoiceConverter._initialize_output must not raise KeyError with missing estore params."""
        converter = EStoreEInvoiceConverter()
        ctx = ConversionContext(
            edi_filename="test.edi",
            output_filename=str(tmp_path / "output"),
            settings_dict={},
            parameters_dict={},  # intentionally missing all estore_* keys
            upc_lut={},
        )
        converter._initialize_output(ctx)
        if ctx.output_file:
            ctx.output_file.close()

        # Params should default to empty strings, not raise KeyError
        assert converter.store_number == ""
        assert converter.vendor_oid == ""
        assert converter.vendor_name == ""

    def test_einvoice_generic_initialize_output_no_key_error(self, tmp_path):
        """EStoreEInvoiceGenericConverter._initialize_output must not raise KeyError with missing estore params.

        The DB connection will fail (ValueError), but KeyError must never be raised
        from the params access before that point.
        """
        converter = EStoreEInvoiceGenericConverter()
        ctx = ConversionContext(
            edi_filename="test.edi",
            output_filename=str(tmp_path / "output"),
            settings_dict={},
            parameters_dict={},  # intentionally missing all estore_* keys
            upc_lut={},
        )
        try:
            converter._initialize_output(ctx)
            if ctx.output_file:
                ctx.output_file.close()
        except KeyError as e:
            pytest.fail(
                f"_initialize_output raised KeyError with missing estore params: {e}"
            )
        except Exception:
            # ValueError from missing DB settings (as400_username etc.) is expected;
            # any other non-KeyError exception is also acceptable here.
            pass
