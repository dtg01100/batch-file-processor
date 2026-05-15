"""EDI Converters package.

Exports make_edi_convert for all converter modules.
"""

from dispatch.converters.convert_base import make_edi_convert

__all__ = [
    "make_edi_convert",
]
