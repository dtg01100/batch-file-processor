"""EDI Converters package.

Exports create_edi_convert_wrapper for all converter modules.
"""

from dispatch.converters.convert_base import create_edi_convert_wrapper

__all__ = [
    "create_edi_convert_wrapper",
]
