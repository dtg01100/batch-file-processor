"""Stub for 1.47 ``utils.py`` used by the routing-harness tests.

Only the functions exercised by the 1.47 dispatch / converter pipeline are
implemented. Anything not called during the routing path is intentionally
absent; calling it will raise ``AttributeError`` so we notice if the surface
changes.

The 1.47 ``utils.py`` is much larger than this stub. The full file is 313
lines; this shadow is ~80 lines and covers only the surface used by
``dispatch.py`` (see ``dispatch.py:140-520``) and the vendored converters.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timedelta


def capture_records(line):
    """Capture records out of EDI segment line — minimal stub for split path."""
    return []


def detect_invoice_is_credit(edi_process):  # noqa: ARG001
    """Return False (treat as invoice, not credit) for routing tests."""
    return False


def do_split_edi(edi_process, work_directory, parameters_dict):  # noqa: ARG001
    """Return a single-element list -> 'do not split'. Matches the no-op branch
    in dispatch.process_files for split_edi=False."""
    return [(edi_process, "", "")]


def convert_to_price(value):
    """Format a numeric value as a price string."""
    if value is None:
        return ""
    return f"{value}"


def calc_check_digit(value):  # noqa: ARG001
    return 0


def convert_UPCE_to_UPCA(upce_value):  # noqa: ARG001
    return upce_value


def datetime_from_dactime(dac_time):  # noqa: ARG001
    return datetime(2000, 1, 1) + timedelta(seconds=int(dac_time or 0))


def dac_str_int_to_int(dacstr):  # noqa: ARG001
    return int(dacstr or 0)


def dactime_from_datetime(date_time):  # noqa: ARG001
    return ""


def datetime_from_invtime(invtime):  # noqa: ARG001
    return datetime(2000, 1, 1)


def dactime_from_invtime(inv_no):  # noqa: ARG001
    return ""


def do_clear_old_files(folder_path, maximum_files):  # noqa: ARG001
    """No-op error-log rotation stub."""
    return None


def is_valid_filename(filename):  # noqa: ARG001
    """Pass-through permissive filename check; the harness relies on the same
    regex the vendored dispatch uses at line ~367."""
    return re.match(r"^[A-Za-z0-9. _]+$", filename or "") is not None


class invFetcher:  # noqa: D401 - stub only
    """Placeholder for the 1.47 invFetcher; not exercised by routing tests."""

    def __init__(self, *args, **kwargs):  # noqa: ARG002
        pass


__all__ = [
    "capture_records",
    "detect_invoice_is_credit",
    "do_split_edi",
    "convert_to_price",
    "calc_check_digit",
    "convert_UPCE_to_UPCA",
    "datetime_from_dactime",
    "dac_str_int_to_int",
    "dactime_from_datetime",
    "datetime_from_invtime",
    "dactime_from_invtime",
    "do_clear_old_files",
    "is_valid_filename",
    "invFetcher",
]
