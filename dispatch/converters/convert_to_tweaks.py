"""Tweaks EDI Converter - EDI Tweaks as a Conversion Backend.

This module exposes EDI tweaks as a conversion backend, allowing tweaks
to be applied through the same module-loading mechanism as other converters.

The tweak functionality is applied through BaseEDIConverter's template method
pattern, delegating transformations to EDITweaker from core.edi.edi_tweaker.

Transformations applied:
- A-record padding
- A-record appending
- Invoice date offsetting
- UPC check digit calculation
- Retail UOM conversion
- UPC override from lookup table
- C-record generation for split prepaid sales tax

Backward Compatibility:
    The module-level edi_convert() function maintains the same signature
    as other converters: edi_convert(edi_process, output_filename,
    settings_dict, parameters_dict, upc_lut)
"""

from core.edi.edi_tweaker import EDITweaker, TweakerConfig
from dispatch.converters.convert_base import BaseEDIConverter, ConversionContext
from dispatch.converters.mixins import DatabaseConnectionMixin


class TweaksConverter(BaseEDIConverter, DatabaseConnectionMixin):
    """Converter that applies EDI tweaks using the template method pattern.

    This converter extends BaseEDIConverter to process EDI files through
    the standard template method, delegating record transformations to
    EDITweaker.
    """

    def __init__(self) -> None:
        """Initialize the tweaks converter."""
        self._tweaker = None

    def _initialize_output(self, context: ConversionContext) -> None:
        """Initialize output file and EDITweaker instance.

        Args:
            context: The conversion context

        """
        from core.edi.edi_tweaker import _create_query_runner_adapter

        config = TweakerConfig.from_params(context.parameters_dict)
        query_runner = _create_query_runner_adapter(context.settings_dict)
        self._tweaker = EDITweaker(query_runner, config)

        output_path = context.output_filename
        if config.force_txt_file_ext:
            output_path += ".txt"

        context.output_file = open(output_path, "w", encoding="utf-8", newline="\r\n")
        context.user_data["output_path"] = output_path

    def process_a_record(self, record, context: ConversionContext) -> None:
        """Process and transform an A record.

        Args:
            record: The EDIRecord containing A record fields
            context: The conversion context

        """
        transformed = self._tweaker._process_a_record(
            record.fields, context.output_file
        )
        context.output_file.write(transformed)

    def process_b_record(self, record, context: ConversionContext) -> None:
        """Process and transform a B record.

        Args:
            record: The EDIRecord containing B record fields
            context: The conversion context

        """
        transformed = self._tweaker._process_b_record(
            record.fields, context.output_file, context.upc_lut
        )
        context.output_file.write(transformed)

    def process_c_record(self, record, context: ConversionContext) -> None:
        """Process and transform a C record.

        Args:
            record: The EDIRecord containing C record fields
            context: The conversion context

        """
        transformed = self._tweaker._process_c_record(
            record.fields, context.output_file
        )
        if transformed:
            context.output_file.write(transformed)

    def _finalize_output(self, context: ConversionContext) -> None:
        """Close output file.

        Args:
            context: The conversion context

        """
        if context.output_file is not None:
            context.output_file.close()
            context.output_file = None

    def _get_return_value(self, context: ConversionContext) -> str:
        """Return the output file path.

        Args:
            context: The conversion context

        Returns:
            Path to the tweaked output file

        """
        return context.user_data.get("output_path", context.output_filename)


from .convert_base import create_edi_convert_wrapper

# Auto-generated wrapper using the standard template
edi_convert = create_edi_convert_wrapper(TweaksConverter, format_name="tweaks")
